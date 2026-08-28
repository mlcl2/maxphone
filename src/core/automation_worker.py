import os
import time
import traceback
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.adb import ADBDevice
from src.core.proxy_manager import ProxyManager
from src.core.profile_manager import DeviceProfileManager
from src.core.backup_manager import BackupRestoreManager
from src.core.scenario_executor import ScenarioExecutor


class AutomationWorker(QObject):
    log_signal = pyqtSignal(int, str, str)
    failed_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, account_data, serial_device, scenario_config, ip_mode="super_proxy", network_config=None):
        super().__init__()
        self.acc = account_data
        self.serial = serial_device
        self.scenario_config = scenario_config
        self.ip_mode = ip_mode
        self.network_config = network_config or {}
        self.error_message = None

    def run(self):
        try:
            self._run()
        except Exception as exc:
            acc_id = self.acc.get("id", 0)
            self.error_message = f"Lỗi chạy kịch bản: {exc}"
            error_log = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "automation_error.log",
            )
            try:
                with open(error_log, "a", encoding="utf-8") as log_file:
                    log_file.write(traceback.format_exc())
                    log_file.write("\n")
            except OSError:
                pass
            self.log_signal.emit(acc_id, "Error", self.error_message)
            self.failed_signal.emit(self.error_message)
        finally:
            self.finished_signal.emit()

    def _change_network(self, adb, send_log):
        proxy = self.acc.get("proxy", "").strip()
        if self.ip_mode == "airplane":
            send_log("Processing", "✈️ Đang bật chế độ máy bay trong 1 giây để đổi IP...")
            if not ProxyManager.toggle_airplane_mode(adb, delay_sec=1):
                raise RuntimeError("Không thể bật/tắt chế độ máy bay để đổi IP")
            return

        if self.ip_mode == "mobile_data":
            send_log("Processing", "📶 Đang tắt/bật dữ liệu di động để đổi IP...")
            if not ProxyManager.toggle_mobile_data(adb, delay_sec=1):
                raise RuntimeError("Không thể reset dữ liệu di động để đổi IP")
            return

        if self.ip_mode == "super_proxy":
            if proxy:
                send_log("Processing", f"🌐 Đang kết nối Super Proxy: {proxy}...")
                if not ProxyManager.connect_super_proxy(adb, proxy):
                    raise RuntimeError("Không thể kết nối Super Proxy")
                return
            send_log("Processing", "⚠️ Nick không có proxy, chuyển sang đổi IP bằng chế độ máy bay...")
            if not ProxyManager.toggle_airplane_mode(adb, delay_sec=1):
                raise RuntimeError("Không thể bật/tắt chế độ máy bay để đổi IP")
            return

        if self.ip_mode == "xproxy":
            reset_url = self.network_config.get("xproxy_api", "").strip()
            if not ProxyManager.change_xproxy_ip(reset_url):
                raise RuntimeError("Không thể đổi IP qua XProxy")
            return

        if self.ip_mode == "none":
            send_log("Processing", "ℹ️ Giữ nguyên kết nối mạng theo cấu hình.")
            return

        raise RuntimeError(f"Chế độ đổi IP không hợp lệ: {self.ip_mode}")

    def _run(self):
        acc_id = self.acc["id"]
        uid = self.acc["uid"]
        adb = ADBDevice(self.serial)

        def send_log(status, message):
            self.log_signal.emit(acc_id, status, message)

        send_log("Processing", f"📱 Bắt đầu xử lý UID [{uid}] trên Phone [{self.serial}]...")

        if not BackupRestoreManager.reset_facebook_app_data(
            adb, log_func=lambda message: send_log("Processing", message)
        ):
            raise RuntimeError("Không thể reset dữ liệu Facebook")

        if not BackupRestoreManager.restore_device_helper_profile(
            adb, uid, log_func=lambda message: send_log("Processing", message)
        ):
            raise RuntimeError("Không thể khôi phục profile thiết bị com.tlc.helper")

        device_profile = BackupRestoreManager.get_account_device_profile(uid, adb)
        DeviceProfileManager().apply_device_to_phone(
            adb,
            uid,
            device_info=device_profile,
            log_func=lambda message: send_log("Processing", message),
        )

        self._change_network(adb, send_log)

        if BackupRestoreManager.has_backup(uid):
            send_log("Processing", f"📁 Đã tìm thấy bản sao lưu backup cho UID [{uid}]. Tiến hành khôi phục...")
            if not BackupRestoreManager.restore_account_app_data(
                adb, uid, log_func=lambda message: send_log("Processing", message)
            ):
                raise RuntimeError("Không thể khôi phục backup Facebook")
        else:
            send_log("Processing", f"🔑 Chưa có backup cho UID [{uid}]. Tiến hành đăng nhập lần đầu tiên...")
            executor_login = ScenarioExecutor(adb, log_callback=lambda message: send_log("Processing", message), account_uid=uid)
            login_success = executor_login.first_time_login(
                uid=uid,
                password=self.acc.get("password", ""),
                fa2_secret=self.acc.get("fa2", ""),
                cookie=self.acc.get("cookie", "")
            )
            if not login_success:
                raise RuntimeError("Đăng nhập lần đầu thất bại! Không thể vào tới màn hình Home Facebook.")
            send_log("Processing", "🎉 Đăng nhập lần đầu thành công và đã vào Home; chuyển sang chạy kịch bản.")

        executor = ScenarioExecutor(adb, log_callback=lambda message: send_log("Processing", message), account_uid=uid)
        if BackupRestoreManager.has_backup(uid):
            if not adb.launch_facebook():
                raise RuntimeError("Không thể khởi chạy hoặc xác minh Facebook lên foreground sau 3 lần")
            send_log("Processing", "⏳ Đang đợi Facebook tải xong và tự bỏ qua đồng bộ danh bạ nếu có...")
            if not executor.wait_for_facebook_ready(timeout_sec=90, dismiss_setup_prompts=True):
                raise RuntimeError("Facebook chưa mở xong sau restore; dừng kịch bản để không backup sai trạng thái")

        send_log("Processing", "📜 Bắt đầu thực thi kịch bản tương tác...")
        if not executor.wait_for_screen("home", timeout_sec=45):
            raise RuntimeError("Màn hình Home chưa mở thành công! Dừng thao tác kịch bản để tránh bấm sai.")

        actions = self.scenario_config.get("actions", [])
        if not actions:
            send_log("Processing", "ℹ️ Kịch bản không có hành động; không tự chèn Newsfeed/Reels mặc định.")
        for action in actions:
            action_type = action.get("type") or action.get("action_type")
            action_config = action.get("config", {})
            if action_type == "seeding":
                action_completed = executor.execute_seeding(action_config)
            else:
                action_completed = executor.execute_action(action_type, action_config)
            if action_completed is False:
                raise RuntimeError(
                    f"Hành động [{action_type}] chưa hoàn tất xác minh; dừng trước khi backup"
                )

        backup_ok, backup_result = BackupRestoreManager.backup_account_app_data(
            adb, uid, log_func=lambda message: send_log("Processing", message)
        )
        if not backup_ok:
            raise RuntimeError(f"Không thể backup Facebook sau kịch bản: {backup_result}")

        send_log("LIVE", "✅ Hoàn tất kịch bản và backup dữ liệu Facebook.")
