import json
import os
import random
import re
import tempfile
from datetime import datetime, timezone


class DeviceProfileManager:
    """Lưu và áp dụng cấu hình thiết bị ổn định cho từng tài khoản."""

    PROFILE_VERSION = 1
    _UID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
    _ANDROID_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{16}$")
    _HOSTNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,63}$")

    def __init__(self, profiles_dir="profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)

    @classmethod
    def _normalize_uid(cls, uid):
        normalized_uid = str(uid or "").strip()
        if not normalized_uid or not cls._UID_PATTERN.fullmatch(normalized_uid):
            raise ValueError("UID không hợp lệ để lưu hồ sơ thiết bị")
        return normalized_uid

    def _profile_path(self, uid):
        return os.path.join(self.profiles_dir, f"{self._normalize_uid(uid)}_device.json")

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _command_failed(result):
        return isinstance(result, str) and result.strip().lower().startswith("error:")

    @staticmethod
    def _clean_adb_value(value):
        if not isinstance(value, str) or value.strip().lower().startswith("error:"):
            return ""
        return value.strip()

    @classmethod
    def _new_android_id(cls):
        return "".join(random.choices("0123456789abcdef", k=16))

    @classmethod
    def _new_hostname(cls):
        return f"android-{''.join(random.choices('0123456789abcdef', k=8))}"

    def generate_random_device(self):
        """Tạo profile dự phòng khi chưa thể đọc thông tin từ phone."""
        devices = [
            {"brand": "Samsung", "model": "Galaxy S21", "device": "o1s", "board": "exynos2100"},
            {"brand": "Xiaomi", "model": "Redmi Note 10", "device": "mojito", "board": "qualcomm"},
            {"brand": "OPPO", "model": "Reno 6", "device": "CPH2251", "board": "mt6877"},
            {"brand": "Realme", "model": "Realme 8", "device": "RMX3085", "board": "helioG95"},
        ]
        device = random.choice(devices)
        return {
            "schema_version": self.PROFILE_VERSION,
            "brand": device["brand"],
            "model": device["model"],
            "device": device["device"],
            "board": device["board"],
            "android_id": self._new_android_id(),
            "hostname": self._new_hostname(),
            "created_at": self._now_iso(),
        }

    def capture_device_info(self, adb_device):
        """Chụp thông tin thực tế của phone để dùng làm profile đầu tiên."""
        fallback = self.generate_random_device()
        values = {
            "brand": self._clean_adb_value(adb_device.shell("getprop ro.product.brand")),
            "model": self._clean_adb_value(adb_device.shell("getprop ro.product.model")),
            "device": self._clean_adb_value(adb_device.shell("getprop ro.product.device")),
            "board": self._clean_adb_value(adb_device.shell("getprop ro.product.board")),
            "android_id": self._clean_adb_value(adb_device.shell("settings get secure android_id")),
            "hostname": self._clean_adb_value(adb_device.shell("getprop net.hostname")),
        }
        for key, fallback_value in fallback.items():
            if key in ("schema_version", "created_at"):
                continue
            if not values.get(key):
                values[key] = fallback_value

        if not self._ANDROID_ID_PATTERN.fullmatch(values["android_id"]):
            values["android_id"] = fallback["android_id"]
        if not self._HOSTNAME_PATTERN.fullmatch(values["hostname"]):
            values["hostname"] = fallback["hostname"]

        return {
            "schema_version": self.PROFILE_VERSION,
            "brand": values["brand"],
            "model": values["model"],
            "device": values["device"],
            "board": values["board"],
            "android_id": values["android_id"].lower(),
            "hostname": values["hostname"],
            "created_at": self._now_iso(),
        }

    def _validate_device_info(self, device_info):
        if not isinstance(device_info, dict):
            raise ValueError("Hồ sơ thiết bị không đúng định dạng")

        normalized = dict(device_info)
        android_id = str(normalized.get("android_id", "")).strip().lower()
        if not self._ANDROID_ID_PATTERN.fullmatch(android_id):
            raise ValueError("Android ID trong hồ sơ thiết bị không hợp lệ")
        normalized["android_id"] = android_id

        hostname = str(normalized.get("hostname", "")).strip()
        if not self._HOSTNAME_PATTERN.fullmatch(hostname):
            hostname = f"android-{android_id[-8:]}"
        normalized["hostname"] = hostname

        for key in ("brand", "model", "device", "board"):
            normalized[key] = str(normalized.get(key, "")).strip()
        normalized["schema_version"] = self.PROFILE_VERSION
        normalized.setdefault("created_at", self._now_iso())
        return normalized

    def save_device_info(self, uid, device_info):
        """Ghi profile nguyên tử để không tạo file dở khi mất kết nối/đóng ứng dụng."""
        path = self._profile_path(uid)
        normalized = self._validate_device_info(device_info)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=self.profiles_dir
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(normalized, file, ensure_ascii=False, indent=2, sort_keys=True)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return normalized

    def load_device_info(self, uid):
        """Đọc profile đã lưu; nếu chưa có thì sinh profile mới và lưu ngay."""
        path = self._profile_path(uid)
        if not os.path.exists(path):
            return self.save_device_info(uid, self.generate_random_device())
        try:
            with open(path, "r", encoding="utf-8") as file:
                device_info = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Không thể đọc hồ sơ thiết bị cho UID {uid}: {exc}") from exc
        return self._validate_device_info(device_info)

    def load_or_capture_device_info(self, uid, adb_device=None):
        """Ưu tiên profile đã lưu; lần đầu sẽ lấy thông tin hiện có của phone."""
        path = self._profile_path(uid)
        if os.path.exists(path):
            return self.load_device_info(uid)
        if adb_device is not None:
            return self.save_device_info(uid, self.capture_device_info(adb_device))
        return self.save_device_info(uid, self.generate_random_device())

    def verify_device_on_phone(self, adb_device, device_info):
        """Xác minh phone vẫn mang đúng identity trước restore/backup."""
        profile = self._validate_device_info(device_info)
        current_android_id = self._clean_adb_value(
            adb_device.shell("settings get secure android_id")
        ).lower()
        current_hostname = self._clean_adb_value(adb_device.shell("getprop net.hostname"))
        if current_android_id != profile["android_id"]:
            raise RuntimeError("Android ID hiện tại không khớp profile của tài khoản")
        if current_hostname != profile["hostname"]:
            raise RuntimeError("Hostname hiện tại không khớp profile của tài khoản")
        return True

    def apply_device_to_phone(self, adb_device, uid, device_info=None, log_func=print):
        """Áp dụng các thuộc tính thiết bị có thể đặt ổn định qua ADB/root."""
        profile = self._validate_device_info(
            device_info if device_info is not None else self.load_or_capture_device_info(uid, adb_device)
        )
        if log_func:
            log_func("📱 Đang áp dụng hồ sơ thiết bị cố định của tài khoản...")

        android_id_result = adb_device.run_root(
            f"settings put secure android_id {profile['android_id']}"
        )
        hostname_result = adb_device.run_root(f"setprop net.hostname {profile['hostname']}")
        if self._command_failed(android_id_result) or self._command_failed(hostname_result):
            raise RuntimeError("Không thể áp dụng Android ID hoặc hostname của profile")

        current_android_id = self._clean_adb_value(adb_device.shell("settings get secure android_id")).lower()
        current_hostname = self._clean_adb_value(adb_device.shell("getprop net.hostname"))
        if current_android_id != profile["android_id"]:
            raise RuntimeError(
                "Android ID sau khi áp dụng không khớp profile; dừng để tránh restore nhầm môi trường"
            )
        if current_hostname != profile["hostname"]:
            raise RuntimeError(
                "Hostname sau khi áp dụng không khớp profile; dừng để tránh restore nhầm môi trường"
            )

        if log_func:
            log_func(
                "✅ Đã áp dụng và xác minh profile thiết bị cố định "
                f"(Android ID: {profile['android_id']}, hostname: {profile['hostname']})."
            )
        return profile
