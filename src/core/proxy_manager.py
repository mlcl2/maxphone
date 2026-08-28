import time
import requests
import xml.etree.ElementTree as ET
from src.core.adb import ADBDevice


class ProxyManager:
    """
    Quản lý Toàn diện Mạng, Proxy và Đổi IP cho Dàn Phone Farm:
    1. Đổi IP qua SIM (Bật/tắt Airplane Mode, kích hoạt Mobile Data, tắt Wi-Fi).
    2. Gán Proxy không User/Pass qua Android Global Settings.
    3. Gán Proxy có User/Pass qua ứng dụng CollegeProxy (com.cell47.College_Proxy) / SuperProxy.
    4. Tích hợp API xoay IP tự động: MinProxy, TMProxy, Tinsoft, ShopLike, ProxyV6, XProxy, Dcom HiLink.
    """

    @staticmethod
    def _command_failed(result):
        return isinstance(result, str) and result.strip().lower().startswith("error:")

    @staticmethod
    def _wait_for_setting(adb_device: ADBDevice, setting_name: str, expected_value: str, timeout_sec=5):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            value = adb_device.shell(f"settings get global {setting_name}").strip()
            if value == expected_value:
                return True
            time.sleep(0.25)
        return False

    @staticmethod
    def check_proxy_live(proxy_str):
        """Kiểm tra proxy có live không và trả về IP public."""
        if not proxy_str or not proxy_str.strip():
            return False, "Thiếu Proxy"

        proxy_str = proxy_str.strip()
        try:
            parts = proxy_str.split(":")
            if len(parts) == 4:
                # ip:port:user:pass -> http://user:pass@ip:port
                ip, port, user, pwd = parts
                proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
            elif proxy_str.startswith(("http://", "socks5://")):
                proxy_url = proxy_str
            else:
                proxy_url = f"http://{proxy_str}"

            response = requests.get(
                "https://api.ipify.org?format=json",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json().get("ip")
        except Exception as exc:
            return False, str(exc)
        return False, "Die"

    # =========================================================================
    # 1. ĐỔI IP QUA SIM 3G/4G TRÊN MÁY (AIRPLANE MODE & MOBILE DATA)
    # =========================================================================

    @staticmethod
    def reset_sim_ip(adb_device: ADBDevice, delay_sec=2, reconnect_sec=4):
        """
        Quy trình chuẩn đổi IP SIM 4G:
        1. Tắt Wi-Fi
        2. Bật Mobile Data
        3. Toggle Airplane Mode (Bật -> Chờ -> Tắt)
        4. Chờ nhận mạng và cấp IP mới từ trạm phát sóng
        """
        # Tắt wifi, bật data
        adb_device.run_root("svc wifi disable")
        adb_device.run_root("svc data enable")

        # Bật chế độ máy bay
        adb_device.shell("settings put global airplane_mode_on 1")
        adb_device.run_root("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true")
        time.sleep(max(1, delay_sec))

        # Tắt chế độ máy bay
        adb_device.shell("settings put global airplane_mode_on 0")
        adb_device.run_root("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false")
        time.sleep(max(2, reconnect_sec))
        return True

    @staticmethod
    def toggle_airplane_mode(adb_device: ADBDevice, delay_sec=1, reconnect_sec=3):
        return ProxyManager.reset_sim_ip(adb_device, delay_sec, reconnect_sec)

    @staticmethod
    def toggle_mobile_data(adb_device: ADBDevice, delay_sec=1, reconnect_sec=3):
        disable_result = adb_device.run_root("svc data disable")
        if ProxyManager._command_failed(disable_result):
            return False
        time.sleep(delay_sec)

        enable_result = adb_device.run_root("svc data enable")
        if ProxyManager._command_failed(enable_result):
            return False
        time.sleep(reconnect_sec)
        return True

    # =========================================================================
    # 2. GÁN & GỠ PROXY CHO TỪNG TÀI KHOẢN (GLOBAL SETTINGS & COLLEGEPROXY)
    # =========================================================================

    @staticmethod
    def set_system_proxy(adb_device: ADBDevice, host: str, port: int):
        """Gán Proxy tĩnh không user/pass qua Android Global Settings."""
        adb_device.shell(f"settings put global http_proxy {host}:{port}")
        adb_device.shell(f"settings put global global_http_proxy_host {host}")
        adb_device.shell(f"settings put global global_http_proxy_port {port}")
        return True

    @staticmethod
    def remove_proxy(adb_device: ADBDevice):
        """Gỡ toàn bộ Proxy trên máy (cả Global Settings và CollegeProxy)."""
        adb_device.shell("settings put global http_proxy :0")
        adb_device.shell("settings delete global http_proxy")
        adb_device.shell("settings delete global global_http_proxy_host")
        adb_device.shell("settings delete global global_http_proxy_port")
        # Dừng và clear app CollegeProxy nếu đang chạy
        adb_device.shell("am force-stop com.cell47.College_Proxy")
        adb_device.shell("pm clear com.cell47.College_Proxy")
        adb_device.shell("am force-stop com.scheler.superproxy")
        return True

    @staticmethod
    def connect_college_proxy(adb_device: ADBDevice, proxy_str: str, apk_path=None):
        """
        Cấu hình Proxy có User/Password qua ứng dụng CollegeProxy (com.cell47.College_Proxy).
        Định dạng proxy_str: IP:Port hoặc IP:Port:User:Pass
        """
        if not proxy_str:
            return False

        parts = proxy_str.strip().split(":")
        if len(parts) < 2:
            return False

        ip = parts[0]
        port = parts[1]
        user = parts[2] if len(parts) > 2 else ""
        pwd = parts[3] if len(parts) > 3 else ""

        # Kiểm tra app đã cài chưa
        installed = "com.cell47.College_Proxy" in adb_device.shell("pm list packages")
        if not installed and apk_path:
            adb_device.shell(f"pm install -r {apk_path}")
            time.sleep(2)

        # Clear và mở CollegeProxy
        adb_device.shell("pm clear com.cell47.College_Proxy")
        adb_device.shell("am start -n com.cell47.College_Proxy/.MainActivity")
        time.sleep(2)

        # Tương tác giao diện CollegeProxy
        # 1. Nhập Host & Port
        # Lấy XML dump để tìm ô nhập
        xml_dump = adb_device.dump_ui_xml()
        if xml_dump:
            # Fallback tương tác nhanh qua broadcast hoặc ADB text
            pass

        # Gõ thông tin qua ADB
        adb_device.shell(f"am startservice -n com.cell47.College_Proxy/.ProxyService --es host {ip} --ei port {port} --es user {user} --es pass {pwd}")
        return True

    @staticmethod
    def apply_account_proxy(adb_device: ADBDevice, proxy_str: str):
        """Tự động phân loại và áp dụng Proxy phù hợp cho tài khoản."""
        if not proxy_str or not proxy_str.strip():
            ProxyManager.remove_proxy(adb_device)
            return True

        parts = proxy_str.strip().split(":")
        if len(parts) == 2:
            # Proxy không user/pass -> dùng thẳng system settings
            return ProxyManager.set_system_proxy(adb_device, parts[0], int(parts[1]))
        elif len(parts) == 4:
            # Proxy có user/pass -> dùng CollegeProxy / SuperProxy
            return ProxyManager.connect_college_proxy(adb_device, proxy_str)
        return False

    # =========================================================================
    # 3. TÍCH HỢP CÁC DỊCH VỤ PROXY XOAY API (ROTATING PROXY PROVIDERS)
    # =========================================================================

    @staticmethod
    def get_minproxy_ip(api_key: str, get_new=True):
        """MinProxy: Lấy IP hiện tại hoặc đổi IP mới."""
        endpoint = "get-new-proxy" if get_new else "get-current-proxy"
        url = f"http://dash.minproxy.vn/api/rotating/v1/proxy/{endpoint}?api_key={api_key}"
        try:
            res = requests.get(url, timeout=15).json()
            if res.get("code") == 1 or res.get("status") == "success":
                data = res.get("data", {})
                return True, data.get("http_proxy") or data.get("proxy")
            return False, res.get("message", "Lỗi lấy MinProxy")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_tmproxy_ip(api_key: str):
        """TMProxy: Đổi IP mới."""
        url = "https://tmproxy.com/api/proxy/get-new-proxy"
        try:
            res = requests.post(url, json={"api_key": api_key}, timeout=15).json()
            if res.get("code") == 0:
                data = res.get("data", {})
                return True, data.get("https") or data.get("http_ipv4")
            return False, res.get("message", "Lỗi lấy TMProxy")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_tinsoft_ip(api_key: str, location=0):
        """Tinsoft Proxy: Đổi IP."""
        url = f"http://proxy.tinsoftsv.com/api/changeProxy.php?key={api_key}&location={location}"
        try:
            res = requests.get(url, timeout=15).json()
            if res.get("success"):
                return True, res.get("proxy")
            return False, res.get("description", "Lỗi lấy Tinsoft")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_shoplike_ip(access_token: str):
        """ShopLike Proxy: Đổi IP mới."""
        url = f"http://proxy.shoplike.vn/Api/getNewProxy?access_token={access_token}"
        try:
            res = requests.get(url, timeout=15).json()
            if res.get("status") == "success":
                data = res.get("data", {})
                return True, data.get("proxy")
            return False, res.get("mess", "Lỗi lấy ShopLike")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_proxyv6_ip(api_key: str):
        """ProxyV6: Reset IP thủ công."""
        url = f"https://api.proxyv6.net/api/reset-ip-manual?api_key={api_key}"
        try:
            res = requests.get(url, timeout=15).json()
            if res.get("status") == "SUCCESS":
                return True, res.get("data", {}).get("proxy")
            return False, res.get("message", "Lỗi lấy ProxyV6")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def change_xproxy_ip(reset_api_url: str):
        """XProxy: Reset cổng USB 4G Dongle theo URL."""
        if not reset_api_url:
            return False
        try:
            response = requests.get(reset_api_url, timeout=15)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def change_dcom_hilink_ip(hilink_ip="192.168.8.1"):
        """Dcom 4G HiLink Huawei: Reset mạng di động."""
        try:
            # Đổi IP qua API Hilink
            url = f"http://{hilink_ip}/api/dialup/mobile-dataswitch"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            # Tắt data
            requests.post(url, data="<?xml version='1.0' encoding='UTF-8'?><request><dataswitch>0</dataswitch></request>", headers=headers, timeout=5)
            time.sleep(2)
            # Bật lại data
            requests.post(url, data="<?xml version='1.0' encoding='UTF-8'?><request><dataswitch>1</dataswitch></request>", headers=headers, timeout=5)
            return True
        except Exception:
            return False
