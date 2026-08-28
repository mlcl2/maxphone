import random
import time
from src.core.adb import ADBDevice

class DeviceInfoChanger:
    """
    Module Đổi Thông Tin Thiết Bị (Change Device Info / Spoof Device)
    Giúp đổi Android ID, Mac Address, Device Model trước khi Đăng Nhập Facebook
    tránh bị Facebook quét trùng thiết bị / trùng IMEI / trùng Android ID.
    """
    @staticmethod
    def generate_random_android_id():
        return "".join(random.choices("0123456789abcdef", k=16))

    @staticmethod
    def change_device_info(adb: ADBDevice, log_func=None):
        if log_func:
            log_func("📱 Đang Fake / Change thông tin thiết bị (Android ID, Device Info)...")
        
        new_android_id = DeviceInfoChanger.generate_random_android_id()
        # Đổi android_id qua ADB settings
        adb.shell(f"settings put secure android_id {new_android_id}")
        
        # Đổi hostname ngẫu nhiên
        new_hostname = f"android-{''.join(random.choices('0123456789abcdef', k=8))}"
        adb.shell(f"setprop net.hostname {new_hostname}")
        
        time.sleep(1)
        if log_func:
            log_func(f"✅ Đã Change thông tin thiết bị thành công! Android ID mới: {new_android_id}")
        return True
