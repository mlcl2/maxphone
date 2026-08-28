import os
import subprocess
import time
import base64
import re
import xml.etree.ElementTree as ET

class ADBDevice:
    """Class điều khiển từng thiết bị Android qua ADB & App Helper"""
    def __init__(self, serial, adb_path="adb"):
        self.serial = serial
        self.adb_path = adb_path

    def run_cmd(self, cmd, timeout=30):
        """Chạy lệnh adb bất kỳ"""
        full_cmd = f"{self.adb_path} -s {self.serial} {cmd}"
        try:
            res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            stdout = res.stdout.strip()
            if res.returncode != 0:
                details = res.stderr.strip() or stdout or f"ADB command failed with code {res.returncode}"
                return f"ERROR: {details}"
            return stdout
        except Exception as e:
            return f"ERROR: {e}"

    def run_shell(self, shell_cmd, timeout=30):
        """Chạy adb shell"""
        return self.run_cmd(f"shell {shell_cmd}", timeout=timeout)

    def shell(self, cmd, timeout=30):
        return self.run_shell(cmd, timeout=timeout)

    def execute_adb(self, cmd, timeout=30):
        return self.run_cmd(cmd, timeout=timeout)

    def push_file(self, local_path, remote_path, timeout=60):
        """Push một file và chỉ trả thành công khi ADB không báo lỗi."""
        result = self.run_cmd(f'push "{local_path}" "{remote_path}"', timeout=timeout)
        return not str(result).lower().startswith("error:")

    def scan_media_file(self, remote_path):
        result = self.run_shell(
            f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file://{remote_path}"'
        )
        return not str(result).lower().startswith("error:")

    def run_root(self, root_cmd, timeout=30):
        """Chạy adb shell dưới quyền root su -c"""
        escaped_cmd = root_cmd.replace('"', '\"')
        return self.run_shell(f'su -c "{escaped_cmd}"', timeout=timeout)

    # --- KHU VỰC CÀI ĐẶT & KẾT NỐI APP HELPER ---
    def is_package_installed(self, package_name):
        res = self.run_shell(f"pm list packages {package_name}")
        return package_name in res

    def install_app(self, apk_path):
        """Cài đặt file APK với quyền tự động cấp (-g)"""
        if os.path.exists(apk_path):
            return self.run_cmd(f"install -r -g \"{apk_path}\"")
        return "File APK not found"

    def setup_adb_keyboard(self, apk_folder="apps"):
        """Tự động cài & bật bàn phím ADBKeyboard để gõ tiếng Việt / UTF-8"""
        pkg = "com.android.adbkeyboard"
        if not self.is_package_installed(pkg):
            apk = os.path.join(apk_folder, "ADBKeyboard.apk")
            self.install_app(apk)
        # Bật làm bàn phím mặc định
        self.run_shell(f"ime enable {pkg}/.AdbIME")
        self.run_shell(f"ime set {pkg}/.AdbIME")

    def input_text_utf8(self, text):
        """Gõ văn bản tiếng Việt/ký tự đặc biệt bằng ADBKeyboard"""
        encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        result = self.run_shell(f"am broadcast -a ADB_INPUT_B64 --es msg '{encoded}'")
        return not str(result).lower().startswith("error:")

    def setup_max_helpers(self, apk_folder="apps"):
        """Tự động cài đặt đầy đủ bộ trợ thủ (MaxChange, MaxHelper, ADBKeyboard)"""
        self.setup_adb_keyboard(apk_folder)
        for app_name, pkg in [("maxchange.apk", "com.minsoftware.maxchanger"), ("maxhelper.apk", "com.minsoftware.maxhelper")]:
            if not self.is_package_installed(pkg):
                self.install_app(os.path.join(apk_folder, app_name))

    # --- KHU VỰC THAO TÁC MÀN HÌNH ---
    def tap(self, x, y):
        result = self.run_shell(f"input tap {x} {y}")
        return not str(result).lower().startswith("error:")

    def dump_ui(self, remote_path="/sdcard/ui_dump.xml"):
        """Tạo snapshot XML mới; tuyệt đối không đọc lại file stale."""
        self.run_root(f"rm -f {remote_path}")
        for _ in range(3):
            dump_result = self.run_root(f"uiautomator dump {remote_path}", timeout=10)
            if not str(dump_result).lower().startswith("error:"):
                xml = self.run_root(f"cat {remote_path}", timeout=10)
                if xml and "<hierarchy" in xml and not str(xml).lower().startswith("error:"):
                    return xml
            time.sleep(1)
        return ""

    def swipe(self, x1, y1, x2, y2, duration=300):
        result = self.run_shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
        return not str(result).lower().startswith("error:")

    def press_home(self):
        self.run_shell("input keyevent 3")

    def press_back(self):
        self.run_shell("input keyevent 4")

    def screencap(self, timeout=30):
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                return None
            return result.stdout
        except Exception:
            return None

    # --- KHU VỰC SMART BACKUP & RESTORE DATA APP FACEBOOK ---
    FB_PACKAGE = "com.facebook.katana"

    def clear_facebook_app(self):
        """Xóa sạch dữ liệu cũ của App Facebook"""
        self.run_shell(f"pm clear {self.FB_PACKAGE}")

    def backup_facebook_profile(self, uid, output_dir="profiles"):
        """
        Backup toàn bộ phân vùng dữ liệu đăng nhập Facebook ra file <uid>.tar.gz
        và lưu thông tin thiết bị tương ứng.
        """
        os.makedirs(output_dir, exist_ok=True)
        tar_filename = f"{uid}.tar.gz"
        tar_remote_path = f"/sdcard/{tar_filename}"
        local_tar_path = os.path.join(output_dir, tar_filename)

        # 1. Đóng gói các mục nhạy cảm chứa phiên đăng nhập chuẩn 1:1 C# gốc (AC28BD29.cs line 2307)
        cmd_tar = (
            f"tar -czvpf {tar_remote_path} "
            f"/data/data/{self.FB_PACKAGE}/databases "
            f"/data/data/{self.FB_PACKAGE}/app_light_prefs "
            f"/data/data/{self.FB_PACKAGE}/shared_prefs "
            f"/data/data/{self.FB_PACKAGE}/files/mobileconfig"
        )
        self.run_root(cmd_tar)

        # 2. Pull file tar.gz về máy tính
        self.run_cmd(f"pull {tar_remote_path} \"{local_tar_path}\"")

        # 3. Dọn dẹp file tạm trên điện thoại
        self.run_shell(f"rm -f {tar_remote_path}")

        # 4. Kiểm tra xem đã tạo file backup thành công chưa
        return os.path.exists(local_tar_path) and os.path.getsize(local_tar_path) > 0

    def restore_facebook_profile(self, uid, profiles_dir="profiles"):
        """
        Restore phân vùng dữ liệu Facebook từ <uid>.tar.gz vào điện thoại
        để tự động đăng nhập không cần gõ Pass/OTP.
        """
        tar_filename = f"{uid}.tar.gz"
        local_tar_path = os.path.join(profiles_dir, tar_filename)

        if not os.path.exists(local_tar_path):
            return False, "File backup profile không tồn tại!"

        # 1. Xóa sạch app Facebook cũ
        self.clear_facebook_app()

        # 2. Push file backup lên /sdcard/
        tar_remote_path = f"/sdcard/{tar_filename}"
        self.run_cmd(f"push \"{local_tar_path}\" {tar_remote_path}")

        # 3. Copy & Giải nén vào /data/data/com.facebook.katana/
        self.run_root(f"cp {tar_remote_path} /data/data/{self.FB_PACKAGE}/{tar_filename}")
        self.run_root(f"tar -xpf /data/data/{self.FB_PACKAGE}/{tar_filename}")

        # 4. Lấy Owner UID của app Facebook và gán lại quyền (chown -R)
        owner_info = self.run_root(f"ls -l /data/data | grep {self.FB_PACKAGE} | awk '{{print $3\":\"$4}}'")
        if owner_info:
            self.run_root(f"chown -R {owner_info} /data/data/{self.FB_PACKAGE}")

        # 5. Dọn dẹp file rác
        self.run_root(f"rm -f /data/data/{self.FB_PACKAGE}/{tar_filename}")
        self.run_shell(f"rm -f {tar_remote_path}")

        return True, "Restore phân vùng tài khoản thành công!"

    def is_screen_on(self):
        """Kiểm tra màn hình điện thoại đang bật hay tắt (Display Power state)"""
        res = self.run_shell("dumpsys power | grep 'Display Power' | grep -oE '(ON|OFF)'")
        return "OFF" not in res.upper() if res else True

    def ensure_screen_on(self):
        """Mở sáng màn hình và mở khóa (Swipe/Keyevent 82) nếu màn hình đang tắt"""
        if not self.is_screen_on():
            self.run_shell("input keyevent 26")
            time.sleep(1)
        self.run_shell("input keyevent 82")

    def get_focused_activity(self):
        """Trả về package/activity đang được đưa ra trước màn hình nếu đọc được."""
        # Không dùng pipe/grep: run_cmd(shell=True) trên Windows có thể để host
        # shell nuốt ký tự | thay vì chuyển nó vào Android shell.
        output = self.shell("dumpsys window", timeout=30)
        if not output or output.lower().startswith("error:"):
            output = self.shell("dumpsys activity activities", timeout=30)
        if not output or output.lower().startswith("error:"):
            return ""

        focus_lines = "\n".join(
            line for line in output.splitlines()
            if any(marker in line for marker in ("mCurrentFocus", "mFocusedApp", "mResumedActivity"))
        )
        # Activity sau dấu / thường là tên đầy đủ có nhiều dấu chấm.
        match = re.search(r"([A-Za-z0-9._]+/[A-Za-z0-9_.$]+)", focus_lines)
        return match.group(1) if match else ""

    def is_facebook_login_screen(self):
        focused_activity = self.get_focused_activity().lower()
        login_markers = (
            "com.facebook.katana/.loginactivity",
            "com.facebook.katana/com.facebook.katana.loginactivity",
            "com.facebook.login",
        )
        return any(marker in focused_activity for marker in login_markers)

    def launch_facebook(self):
        """Mở ứng dụng Facebook"""
        for _ in range(3):
            result = self.run_shell(
                f"monkey -p {self.FB_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
            if not str(result).lower().startswith("error:"):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if self.get_focused_activity().lower().startswith(f"{self.FB_PACKAGE}/"):
                        return True
                    time.sleep(1)
            time.sleep(1)
        return False


def get_connected_devices(adb_path="adb"):
    """Lấy danh sách các serial điện thoại đang kết nối qua USB/Wifi"""
    try:
        res = subprocess.run(f"{adb_path} devices", shell=True, capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")[1:]
        devices = []
        for line in lines:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
        return devices
    except Exception:
        return []
