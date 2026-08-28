import json
import os
import shutil
import tarfile
import tempfile
import time
from datetime import datetime, timezone

from src.core.profile_manager import DeviceProfileManager


class BackupRestoreManager:
    FB_PACKAGE = "com.facebook.katana"
    DEVICE_HELPER_PACKAGE = "com.tlc.helper"
    DEVICE_HELPER_FILES = (
        "data/data/com.tlc.helper/shared_prefs/Device.xml",
        "data/data/com.tlc.helper/shared_prefs/WebViewChromiumPrefs.xml",
    )
    FB_CORE_PATHS = (
        "com.facebook.katana/databases",
        "com.facebook.katana/app_light_prefs",
        "com.facebook.katana/shared_prefs",
        "com.facebook.katana/files/mobileconfig",
    )
    CORE_ARCHIVE_TYPE = "facebook-core4-v1"
    FULL_ARCHIVE_TYPE = "full-app-data"
    DEFAULT_ARCHIVE_TYPE = CORE_ARCHIVE_TYPE
    METADATA_VERSION = 2
    CORE_BOOTSTRAP_TIMEOUT_SEC = 60
    _UID_PATTERN = DeviceProfileManager._UID_PATTERN

    @classmethod
    def _normalize_uid(cls, uid):
        normalized_uid = str(uid or "").strip()
        if not normalized_uid or not cls._UID_PATTERN.fullmatch(normalized_uid):
            raise ValueError("UID không hợp lệ để thao tác backup")
        return normalized_uid

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get_backup_dir():
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        backup_path = os.path.join(project_root, "backups")
        os.makedirs(backup_path, exist_ok=True)
        return backup_path

    @classmethod
    def _archive_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.tar.gz")

    @classmethod
    def _manifest_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.manifest.json")

    @classmethod
    def _device_profile_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.device.json")

    @classmethod
    def _device_helper_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.device-helper.tar.gz")

    @classmethod
    def _full_fallback_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.full-fallback.tar.gz")

    @classmethod
    def _full_fallback_manifest_path(cls, uid):
        return os.path.join(cls.get_backup_dir(), f"{cls._normalize_uid(uid)}.full-fallback.manifest.json")

    @staticmethod
    def _command_failed(result):
        return isinstance(result, str) and result.strip().lower().startswith("error:")

    @staticmethod
    def _write_json_atomic(path, payload):
        folder = os.path.dirname(path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=folder
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _is_valid_archive(path):
        if not os.path.isfile(path) or os.path.getsize(path) <= 1024:
            return False
        try:
            with tarfile.open(path, "r:gz") as archive:
                return archive.next() is not None
        except (OSError, tarfile.TarError):
            return False

    @classmethod
    def _core_archive_layout(cls, archive_path):
        """Nhận diện hai bố cục archive nhẹ để tương thích backup cũ và mẫu tham chiếu."""
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                names = tuple(member.name.lstrip("./") for member in archive.getmembers())
        except (OSError, tarfile.TarError):
            return ""

        absolute_prefix = f"data/data/{cls.FB_PACKAGE}/"
        relative_prefix = f"{cls.FB_PACKAGE}/"
        if any(name.startswith(absolute_prefix) for name in names):
            return "data-root"
        if any(name.startswith(relative_prefix) for name in names):
            return "package-root"
        return ""

    @classmethod
    def _archive_type(cls, uid):
        manifest = cls._read_json(cls._manifest_path(uid))
        archive_type = manifest.get("archive_type") if isinstance(manifest, dict) else ""
        if archive_type in (cls.CORE_ARCHIVE_TYPE, cls.FULL_ARCHIVE_TYPE):
            return archive_type
        return cls.FULL_ARCHIVE_TYPE

    @classmethod
    def has_backup(cls, uid: str):
        """Chỉ nhận backup khi session và fingerprint cùng UID tạo thành bundle hợp lệ."""
        if not uid:
            return False
        try:
            normalized_uid = cls._normalize_uid(uid)
            archive_path = cls._archive_path(normalized_uid)
            manifest = cls._read_json(cls._manifest_path(normalized_uid))
            profile = cls._read_json(cls._device_profile_path(normalized_uid))
            if not cls._is_valid_archive(archive_path):
                return False
            if not isinstance(manifest, dict) or str(manifest.get("uid", "")) != normalized_uid:
                return False
            if manifest.get("archive_file") != os.path.basename(archive_path):
                return False
            try:
                DeviceProfileManager()._validate_device_info(profile)
            except (TypeError, ValueError):
                return False
            if manifest.get("device_profile_file") != os.path.basename(cls._device_profile_path(normalized_uid)):
                return False
            helper_name = manifest.get("device_helper_archive")
            if helper_name:
                if helper_name != os.path.basename(cls._device_helper_path(normalized_uid)):
                    return False
                if not cls._is_valid_archive(cls._device_helper_path(normalized_uid)):
                    return False
            return True
        except ValueError:
            return False

    @classmethod
    def get_account_device_profile(cls, uid, adb_device=None):
        """Ưu tiên sidecar profile của backup, sau đó dùng profile cục bộ."""
        profile_manager = DeviceProfileManager()
        sidecar_path = cls._device_profile_path(uid)
        sidecar_profile = cls._read_json(sidecar_path)
        if isinstance(sidecar_profile, dict):
            return profile_manager.save_device_info(uid, sidecar_profile)
        return profile_manager.load_or_capture_device_info(uid, adb_device)

    @classmethod
    def _save_backup_metadata(cls, uid, archive_path, device_profile, archive_type, device_helper_path=None):
        cls._write_json_atomic(cls._device_profile_path(uid), device_profile)
        manifest = {
            "schema_version": cls.METADATA_VERSION,
            "archive_type": archive_type,
            "app_package": cls.FB_PACKAGE,
            "uid": cls._normalize_uid(uid),
            "created_at": cls._now_iso(),
            "archive_file": os.path.basename(archive_path),
            "archive_size_bytes": os.path.getsize(archive_path),
            "device_profile_file": os.path.basename(cls._device_profile_path(uid)),
        }
        if archive_type == cls.CORE_ARCHIVE_TYPE:
            manifest.update(
                {
                    "included_paths": list(cls.FB_CORE_PATHS),
                    "restore_strategy": "direct_extract_after_reset",
                    "requires_app_scaffold": False,
                }
            )
        if device_helper_path and os.path.isfile(device_helper_path):
            manifest["device_helper_archive"] = os.path.basename(device_helper_path)
        cls._write_json_atomic(cls._manifest_path(uid), manifest)

    @classmethod
    def _preserve_full_fallback(cls, uid, archive_path):
        """Giữ một bản full cũ trước lần đầu chuyển account sang archive nhẹ."""
        fallback_path = cls._full_fallback_path(uid)
        if cls._is_valid_archive(fallback_path):
            return fallback_path
        try:
            os.link(archive_path, fallback_path)
        except OSError:
            shutil.copy2(archive_path, fallback_path)

        fallback_manifest = cls._read_json(cls._manifest_path(uid)) or {}
        fallback_manifest.update(
            {
                "schema_version": cls.METADATA_VERSION,
                "archive_type": cls.FULL_ARCHIVE_TYPE,
                "app_package": cls.FB_PACKAGE,
                "uid": cls._normalize_uid(uid),
                "archive_file": os.path.basename(fallback_path),
                "archive_size_bytes": os.path.getsize(fallback_path),
                "preserved_at": cls._now_iso(),
            }
        )
        cls._write_json_atomic(cls._full_fallback_manifest_path(uid), fallback_manifest)
        return fallback_path

    @classmethod
    def _backup_device_helper_profile(cls, adb_device, uid, log_func=print):
        target_file = cls._device_helper_path(uid)
        staging_file = f"{target_file}.tmp"
        remote_file = "/sdcard/fb_device_helper_temp.tar.gz"
        if not adb_device.is_package_installed(cls.DEVICE_HELPER_PACKAGE):
            log_func("ℹ️ Không có com.tlc.helper; dùng profile thiết bị JSON hiện có.")
            return True, None

        available = adb_device.run_root(
            "test -f /data/data/com.tlc.helper/shared_prefs/Device.xml "
            "-a -f /data/data/com.tlc.helper/shared_prefs/WebViewChromiumPrefs.xml "
            "&& echo ready"
        )
        if cls._command_failed(available):
            return False, available
        if available.strip() != "ready":
            log_func("ℹ️ com.tlc.helper chưa có profile thiết bị hoàn chỉnh để backup.")
            return True, None

        try:
            if os.path.exists(staging_file):
                os.unlink(staging_file)
            archive_result = adb_device.run_root(
                f"tar -czf {remote_file} -C / {' '.join(cls.DEVICE_HELPER_FILES)}", timeout=60
            )
            if cls._command_failed(archive_result):
                return False, archive_result
            pull_result = adb_device.execute_adb(
                f'pull "{remote_file}" "{staging_file}"', timeout=60
            )
            if cls._command_failed(pull_result) or not cls._is_valid_archive(staging_file):
                return False, pull_result or "Archive profile thiết bị không hợp lệ"
            os.replace(staging_file, target_file)
            return True, target_file
        except Exception as exc:
            return False, str(exc)
        finally:
            adb_device.shell(f"rm -f {remote_file}")
            if os.path.exists(staging_file):
                os.unlink(staging_file)

    @classmethod
    def restore_device_helper_profile(cls, adb_device, uid, log_func=print):
        """Khôi phục profile TLC và nạp lại helper trước khi áp dụng Android ID."""
        try:
            target_file = cls._device_helper_path(uid)
        except ValueError as exc:
            log_func(f"❌ Lỗi profile thiết bị: {exc}")
            return False
        if not cls._is_valid_archive(target_file):
            log_func("ℹ️ Không có archive com.tlc.helper cho tài khoản; dùng profile JSON.")
            return True
        if not adb_device.is_package_installed(cls.DEVICE_HELPER_PACKAGE):
            log_func("❌ Có archive com.tlc.helper nhưng app helper chưa được cài trên phone; không thể khôi phục đúng profile thiết bị.")
            return False

        remote_file = "/sdcard/fb_device_helper_restore.tar.gz"
        helper_root = f"/data/data/{cls.DEVICE_HELPER_PACKAGE}"
        helper_prefs = f"{helper_root}/shared_prefs"
        try:
            adb_device.shell(f"am force-stop {cls.DEVICE_HELPER_PACKAGE}")
            push_result = adb_device.execute_adb(
                f'push "{target_file}" "{remote_file}"', timeout=60
            )
            if cls._command_failed(push_result):
                log_func(f"❌ Không thể chuyển profile thiết bị sang phone: {push_result}")
                return False
            extract_result = adb_device.run_root(f"cd / && tar -xzpf {remote_file}", timeout=60)
            owner = adb_device.run_root(f"stat -c %u:%g {helper_root}").strip()
            if not owner or ":" not in owner or cls._command_failed(owner):
                log_func("❌ Không đọc được quyền sở hữu profile com.tlc.helper.")
                return False
            chown_result = adb_device.run_root(f"chown -R {owner} {helper_prefs}", timeout=60)
            restorecon_result = adb_device.run_root(f"restorecon -RF {helper_prefs}", timeout=60)
            if any(
                cls._command_failed(item)
                for item in (extract_result, chown_result, restorecon_result)
            ):
                log_func("❌ Không thể khôi phục profile com.tlc.helper.")
                return False
            adb_device.shell(
                f"monkey -p {cls.DEVICE_HELPER_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
            time.sleep(2)
            log_func("✅ Đã khôi phục và nạp lại profile thiết bị com.tlc.helper.")
            return True
        except Exception as exc:
            log_func(f"❌ Lỗi khôi phục profile thiết bị: {exc}")
            return False
        finally:
            adb_device.shell(f"rm -f {remote_file}")

    @classmethod
    def synchronize_backup_metadata(cls, uid, adb_device=None):
        """Tạo/cập nhật sidecar cho archive đã có mà không động tới archive."""
        target_file = cls._archive_path(uid)
        if not cls._is_valid_archive(target_file):
            return False, "Không có archive backup hợp lệ"
        try:
            device_profile = cls.get_account_device_profile(uid, adb_device)
            device_helper_path = cls._device_helper_path(uid)
            cls._save_backup_metadata(
                uid,
                target_file,
                device_profile,
                cls._archive_type(uid),
                device_helper_path if cls._is_valid_archive(device_helper_path) else None,
            )
            return True, cls._manifest_path(uid)
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def reset_facebook_app_data(cls, adb_device, log_func=print):
        log_func("🧹 Đang reset dữ liệu ứng dụng Facebook...")
        stop_result = adb_device.shell(f"am force-stop {cls.FB_PACKAGE}")
        clear_result = adb_device.shell(f"pm clear {cls.FB_PACKAGE}")
        if cls._command_failed(stop_result) or cls._command_failed(clear_result):
            log_func("❌ Không thể reset dữ liệu Facebook qua ADB.")
            return False
        if "success" not in clear_result.lower():
            log_func(f"❌ Reset dữ liệu Facebook không thành công: {clear_result or 'không có phản hồi'}")
            return False
        log_func("✅ Đã reset dữ liệu ứng dụng Facebook.")
        return True

    @classmethod
    def backup_account_app_data(cls, adb_device, uid: str, log_func=print, archive_type=None):
        try:
            normalized_uid = cls._normalize_uid(uid)
        except ValueError as exc:
            log_func(f"❌ Lỗi Backup: {exc}")
            return False, str(exc)

        archive_type = archive_type or cls.DEFAULT_ARCHIVE_TYPE
        if archive_type not in (cls.CORE_ARCHIVE_TYPE, cls.FULL_ARCHIVE_TYPE):
            return False, "Loại archive backup không hợp lệ"

        target_file = cls._archive_path(normalized_uid)
        staging_file = f"{target_file}.tmp"
        remote_file = "/sdcard/fb_backup_temp.tar.gz"
        label = "4 nhóm dữ liệu Facebook" if archive_type == cls.CORE_ARCHIVE_TYPE else "đầy đủ dữ liệu Facebook"
        log_func(f"📦 Đang sao lưu {label} cho UID: {normalized_uid}...")

        try:
            if os.path.exists(staging_file):
                os.unlink(staging_file)
            stop_result = adb_device.shell(f"am force-stop {cls.FB_PACKAGE}")
            if cls._command_failed(stop_result):
                return False, stop_result
            time.sleep(1)

            if archive_type == cls.CORE_ARCHIVE_TYPE:
                paths = " ".join(f"/data/data/{path}" for path in cls.FB_CORE_PATHS)
                # SQLite journal/WAL/SHM là file tạm và có thể biến mất ngay cả
                # sau force-stop. Không để race này làm hỏng toàn bộ archive.
                archive_command = (
                    f"tar --exclude='*-journal' --exclude='*-wal' --exclude='*-shm' "
                    f"-czpf {remote_file} {paths}"
                )
            else:
                archive_command = f"tar -czf {remote_file} -C /data/data/ {cls.FB_PACKAGE}"
            archive_result = adb_device.run_root(archive_command, timeout=180)
            if cls._command_failed(archive_result):
                return False, archive_result
            pull_result = adb_device.execute_adb(
                f'pull "{remote_file}" "{staging_file}"', timeout=180
            )
            if cls._command_failed(pull_result):
                return False, pull_result
            if not cls._is_valid_archive(staging_file):
                return False, "Archive backup không hợp lệ hoặc rỗng"

            device_profile = cls.get_account_device_profile(normalized_uid, adb_device)
            DeviceProfileManager().verify_device_on_phone(adb_device, device_profile)
            helper_ok, device_helper_path = cls._backup_device_helper_profile(adb_device, normalized_uid, log_func)
            if not helper_ok:
                return False, f"Không thể backup profile com.tlc.helper: {device_helper_path}"

            os.replace(staging_file, target_file)
            cls._save_backup_metadata(
                normalized_uid, target_file, device_profile, archive_type, device_helper_path
            )
            log_func(
                f"✅ Đã sao lưu UID [{normalized_uid}] ({os.path.getsize(target_file) / 1024 / 1024:.2f} MB)."
            )
            return True, target_file
        except Exception as exc:
            log_func(f"❌ Lỗi backup Facebook: {exc}")
            return False, str(exc)
        finally:
            adb_device.shell(f"rm -f {remote_file}")
            if os.path.exists(staging_file):
                os.unlink(staging_file)

    @classmethod
    def _restore_full_backup(cls, adb_device, target_file, uid, log_func):
        remote_file = "/sdcard/fb_backup_temp.tar.gz"
        try:
            adb_device.shell(f"am force-stop {cls.FB_PACKAGE}")
            push_result = adb_device.execute_adb(
                f'push "{target_file}" "{remote_file}"', timeout=180
            )
            if cls._command_failed(push_result):
                log_func(f"❌ Không thể chuyển backup sang phone: {push_result}")
                return False
            clear_result = adb_device.run_root(f"rm -rf /data/data/{cls.FB_PACKAGE}/*")
            extract_result = adb_device.run_root(f"tar -xzf {remote_file} -C /data/data/", timeout=180)
            restorecon_result = adb_device.run_root(
                f"restorecon -R /data/data/{cls.FB_PACKAGE}", timeout=180
            )
            if any(cls._command_failed(item) for item in (clear_result, extract_result, restorecon_result)):
                log_func("❌ Restore full backup Facebook thất bại.")
                return False
            return True
        finally:
            adb_device.shell(f"rm -f {remote_file}")

    @classmethod
    def _restore_core_backup(cls, adb_device, target_file, uid, log_func):
        """Khôi phục đúng 4 nhóm dữ liệu như profile nhẹ tham chiếu, không dựng app trước."""
        remote_file = "/sdcard/fb_core_restore_temp.tar.gz"
        package_root = f"/data/data/{cls.FB_PACKAGE}"
        archive_in_app = f"{package_root}/.fb_core_restore.tar.gz"
        core_paths = " ".join(f"{package_root}/{path.split('/', 1)[1]}" for path in cls.FB_CORE_PATHS)
        layout = cls._core_archive_layout(target_file)
        if layout not in ("data-root", "package-root"):
            log_func("❌ File backup nhẹ không có cấu trúc Facebook hợp lệ.")
            return False

        try:
            adb_device.shell(f"am force-stop {cls.FB_PACKAGE}")
            push_result = adb_device.execute_adb(
                f'push "{target_file}" "{remote_file}"', timeout=180
            )
            if cls._command_failed(push_result):
                log_func(f"❌ Không thể chuyển backup nhẹ sang phone: {push_result}")
                return False

            copy_result = adb_device.run_root(f"cp {remote_file} {archive_in_app}")
            if cls._command_failed(copy_result):
                log_func("❌ Không thể đặt backup nhẹ vào vùng dữ liệu Facebook.")
                return False

            if layout == "data-root":
                extract_command = f"cd / && tar -xzpf {archive_in_app}"
            else:
                extract_command = f"tar -xzpf {archive_in_app} -C /data/data/"
            extract_result = adb_device.run_root(extract_command, timeout=180)
            owner = adb_device.run_root(f"stat -c %u:%g {package_root}").strip()
            if not owner or ":" not in owner or cls._command_failed(owner):
                log_func("❌ Không đọc được quyền sở hữu dữ liệu Facebook sau restore.")
                return False
            chown_result = adb_device.run_root(f"chown -R {owner} {core_paths}", timeout=120)
            restorecon_result = adb_device.run_root(f"restorecon -RF {core_paths}", timeout=120)
            if any(
                cls._command_failed(item)
                for item in (extract_result, chown_result, restorecon_result)
            ):
                log_func("❌ Restore backup nhẹ Facebook thất bại khi đặt quyền dữ liệu.")
                return False
            log_func("✅ Đã khôi phục profile Facebook nhẹ; sẽ mở app và chờ tải xong trước kịch bản.")
            return True
        finally:
            adb_device.run_root(f"rm -f {archive_in_app}")
            adb_device.shell(f"rm -f {remote_file}")

    @classmethod
    def restore_account_app_data(cls, adb_device, uid: str, log_func=print):
        try:
            normalized_uid = cls._normalize_uid(uid)
        except ValueError as exc:
            log_func(f"❌ Lỗi restore: {exc}")
            return False

        target_file = cls._archive_path(normalized_uid)
        if not cls._is_valid_archive(target_file):
            log_func(f"⚠️ Không có backup hợp lệ cho UID [{normalized_uid}].")
            return False

        archive_type = cls._archive_type(normalized_uid)
        log_func(f"🔄 Đang khôi phục dữ liệu Facebook cho UID: {normalized_uid}...")
        try:
            if archive_type == cls.CORE_ARCHIVE_TYPE:
                restored = cls._restore_core_backup(adb_device, target_file, normalized_uid, log_func)
            else:
                restored = cls._restore_full_backup(adb_device, target_file, normalized_uid, log_func)
            if restored:
                log_func(f"✅ Đã khôi phục dữ liệu Facebook cho UID [{normalized_uid}].")
            return restored
        except Exception as exc:
            log_func(f"❌ Lỗi khôi phục Facebook: {exc}")
            return False

    @classmethod
    def delete_backup_file(cls, uid: str):
        try:
            paths = (
                cls._archive_path(uid),
                cls._manifest_path(uid),
                cls._device_profile_path(uid),
                cls._device_helper_path(uid),
                cls._full_fallback_path(uid),
                cls._full_fallback_manifest_path(uid),
            )
        except ValueError:
            return
        for path in paths:
            if os.path.isfile(path):
                os.remove(path)
