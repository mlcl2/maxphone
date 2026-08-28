import json
import sqlite3
import os
import sys

# Append project root
sys.path.append(r"C:\bs_flash\MaxPhoneFarm_Reborn")

from src.database.db import DatabaseManager
from src.core.adb import get_connected_devices, ADBDevice
from src.utils.fb_checker import FBChecker
from src.core.proxy_manager import ProxyManager
from src.core.profile_manager import DeviceProfileManager
from src.core.script_runner import ScriptRunner

DB_PATH = r"C:\bs_flash\MaxPhoneFarm_Reborn\database.sqlite"
PROFILES_DIR = r"C:\bs_flash\MaxPhoneFarm_Reborn\profiles"
APPS_DIR = r"C:\bs_flash\MaxPhoneFarm_Reborn\apps"

def get_devices():
    """Lấy danh sách các phone ADB đang kết nối"""
    devs = get_connected_devices()
    return {"success": True, "count": len(devs), "devices": devs}

def list_accounts(filter_status=None):
    """Danh sách toàn bộ nick Facebook trong tool và trạng thái (có thể lọc theo status)"""
    db = DatabaseManager(DB_PATH)
    accounts = db.get_all_accounts()
    result = []
    for acc in accounts:
        status = acc[6]
        if filter_status and filter_status.lower() not in status.lower():
            continue
        result.append({
            "id": acc[0],
            "uid": acc[1],
            "password": acc[2],
            "fa2": acc[3],
            "proxy": acc[5],
            "status": acc[6],
            "has_backup": bool(acc[7])
        })
    return {"success": True, "total": len(result), "accounts": result}

def add_accounts(account_lines):
    """Thêm nick mới dạng UID|Pass|2FA|Proxy (list chuỗi hoặc 1 chuỗi nhiều dòng)"""
    db = DatabaseManager(DB_PATH)
    lines = account_lines.strip().split("\n") if isinstance(account_lines, str) else account_lines

    added = 0
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) >= 1 and parts[0].strip():
            uid = parts[0].strip()
            pwd = parts[1].strip() if len(parts) > 1 else ""
            fa2 = parts[2].strip() if len(parts) > 2 else ""
            proxy = parts[3].strip() if len(parts) > 3 else ""
            db.add_account(uid, pwd, fa2, proxy=proxy)
            added += 1
    return {"success": True, "added_count": added}

def delete_account(uid):
    """Xóa 1 tài khoản khỏi Database"""
    db = DatabaseManager(DB_PATH)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE uid=?", (uid,))
        conn.commit()
    return {"success": True, "uid": uid, "message": f"Đã xóa tài khoản {uid}"}

def update_account(uid, password=None, fa2=None, proxy=None):
    """Cập nhật thông tin mật khẩu, 2FA hoặc Proxy cho tài khoản"""
    db = DatabaseManager(DB_PATH)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if password is not None:
            cursor.execute("UPDATE accounts SET password=? WHERE uid=?", (password, uid))
        if fa2 is not None:
            cursor.execute("UPDATE accounts SET fa2=? WHERE uid=?", (fa2, uid))
        if proxy is not None:
            cursor.execute("UPDATE accounts SET proxy=? WHERE uid=?", (proxy, uid))
        conn.commit()
    return {"success": True, "uid": uid, "message": f"Đã cập nhật thông tin tài khoản {uid}"}

def check_account_live(uid):
    """Kiểm tra Live/Die của một UID Facebook"""
    status, info = FBChecker.check_live_uid(uid)
    db = DatabaseManager(DB_PATH)
    db.update_account_status(uid, f"Status: {status}")
    return {"success": True, "uid": uid, "status": status, "info": info}

def check_all_live():
    """Kiểm tra Live/Die toàn bộ danh sách nick trong DB"""
    db = DatabaseManager(DB_PATH)
    accounts = db.get_all_accounts()
    summary = {"total": len(accounts), "live": 0, "die": 0, "unknown": 0, "details": []}
    for acc in accounts:
        uid = acc[1]
        status, info = FBChecker.check_live_uid(uid)
        db.update_account_status(uid, f"Status: {status}")
        if status == "LIVE":
            summary["live"] += 1
        elif status == "DIE":
            summary["die"] += 1
        else:
            summary["unknown"] += 1
        summary["details"].append({"uid": uid, "status": status, "info": info})
    summary["success"] = True
    return summary

def check_proxy(proxy_str):
    """Kiểm tra kết nối và địa chỉ IP của một Proxy"""
    is_live, ip_or_err = ProxyManager.check_proxy_live(proxy_str)
    return {"success": True, "proxy": proxy_str, "is_live": is_live, "result": ip_or_err}

def change_xproxy(api_url):
    """Gửi lệnh đổi IP qua API Reset XProxy/Dcom 4G"""
    ok = ProxyManager.change_xproxy_ip(api_url)
    return {"success": ok, "api_url": api_url, "message": "Đổi IP thành công" if ok else "Lỗi đổi IP XProxy"}

def trigger_backup(uid, serial=None):
    """Gửi lệnh backup phân vùng app Facebook cho UID chỉ định (nén .tar.gz)"""
    if not serial:
        devs = get_connected_devices()
        if not devs:
            return {"success": False, "error": "Không có phone nào đang cắm cáp ADB!"}
        serial = devs[0]

    adb = ADBDevice(serial)
    adb.setup_max_helpers(apk_folder=APPS_DIR)
    ok = adb.backup_facebook_profile(uid, profiles_dir=PROFILES_DIR)
    db = DatabaseManager(DB_PATH)
    if ok:
        db.update_account_status(uid, "Backup Thành Công", has_backup=1)
        return {"success": True, "uid": uid, "status": "Backup Thành Công"}
    else:
        db.update_account_status(uid, "Backup Lỗi", has_backup=0)
        return {"success": False, "uid": uid, "error": "Lỗi khi nén phân vùng tar.gz"}

def trigger_change_device(uid, serial=None):
    """Fake thông tin thiết bị (IMEI, Android ID, Model...) theo nick"""
    if not serial:
        devs = get_connected_devices()
        if not devs:
            return {"success": False, "error": "Không có phone nào đang cắm cáp ADB!"}
        serial = devs[0]

    adb = ADBDevice(serial)
    adb.setup_max_helpers(apk_folder=APPS_DIR)
    pm = DeviceProfileManager(profiles_dir=PROFILES_DIR)
    dev_info = pm.apply_device_to_phone(adb, uid)
    return {"success": True, "uid": uid, "device_info": dev_info}

def trigger_restore_and_run(uid, serial=None, run_script=True, duration=30):
    """Gửi lệnh Restore Data + Change Device + Tùy chọn chạy Kịch bản Nuôi Nick"""
    if not serial:
        devs = get_connected_devices()
        if not devs:
            return {"success": False, "error": "Không có phone nào đang cắm cáp ADB!"}
        serial = devs[0]

    db = DatabaseManager(DB_PATH)
    accounts = db.get_all_accounts()
    target_acc = None
    for acc in accounts:
        if acc[1] == uid:
            target_acc = acc
            break

    if not target_acc:
        return {"success": False, "error": f"Không tìm thấy UID {uid} trong database"}

    proxy = target_acc[5]
    adb = ADBDevice(serial)
    adb.setup_max_helpers(apk_folder=APPS_DIR)

    # 1. Đổi IP qua Proxy nếu có
    if proxy:
        is_live, ip = ProxyManager.check_proxy_live(proxy)
        if not is_live:
            return {"success": False, "uid": uid, "error": f"Proxy {proxy} bị DIE/Kẹt!"}

    # 2. Fake Device Info
    pm = DeviceProfileManager(profiles_dir=PROFILES_DIR)
    pm.apply_device_to_phone(adb, uid)

    # 3. Restore Data FB
    ok, msg = adb.restore_facebook_profile(uid, profiles_dir=PROFILES_DIR)
    if not ok:
        db.update_account_status(uid, "Restore Lỗi", has_backup=0)
        return {"success": False, "uid": uid, "error": msg}

    adb.launch_facebook()
    db.update_account_status(uid, "Đã Đăng Nhập", has_backup=1)

    # 4. Chạy kịch bản tự động nếu có yêu cầu
    if run_script:
        runner = ScriptRunner(adb)
        runner.run_full_scenario(uid)
        db.update_account_status(uid, "Hoàn Thành Kịch Bản", has_backup=1)
        return {"success": True, "uid": uid, "message": "Restore & Hoàn thành kịch bản nuôi nick!"}

    return {"success": True, "uid": uid, "message": "Restore & Mở Facebook thành công!"}

def get_system_status():
    """Báo cáo tổng quan hệ thống cho AI Agent: Số phone, Tổng số nick, Số nick đã backup, Số nick Die"""
    devs = get_connected_devices()
    db = DatabaseManager(DB_PATH)
    accounts = db.get_all_accounts()

    total_acc = len(accounts)
    backed_up = sum(1 for a in accounts if a[7] == 1)
    die_count = sum(1 for a in accounts if "DIE" in str(a[6]).upper())
    live_count = sum(1 for a in accounts if "LIVE" in str(a[6]).upper())

    return {
        "success": True,
        "phone_count": len(devs),
        "devices": devs,
        "total_accounts": total_acc,
        "backed_up_count": backed_up,
        "live_count": live_count,
        "die_count": die_count
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        sys.exit(1)

    action = sys.argv[1]
    
    if action == "status":
        print(json.dumps(get_system_status(), ensure_ascii=False))
    elif action == "get_devices":
        print(json.dumps(get_devices(), ensure_ascii=False))
    elif action == "list_accounts":
        filt = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(list_accounts(filt), ensure_ascii=False))
    elif action == "add_accounts":
        lines = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(add_accounts(lines), ensure_ascii=False))
    elif action == "delete_account":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(delete_account(uid), ensure_ascii=False))
    elif action == "update_account":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        pwd = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "None" else None
        fa2 = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "None" else None
        pxy = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "None" else None
        print(json.dumps(update_account(uid, pwd, fa2, pxy), ensure_ascii=False))
    elif action == "check_live":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(check_account_live(uid), ensure_ascii=False))
    elif action == "check_all_live":
        print(json.dumps(check_all_live(), ensure_ascii=False))
    elif action == "check_proxy":
        pxy = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(check_proxy(pxy), ensure_ascii=False))
    elif action == "change_xproxy":
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(change_xproxy(url), ensure_ascii=False))
    elif action == "backup":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        ser = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(trigger_backup(uid, ser), ensure_ascii=False))
    elif action == "change_device":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        ser = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(trigger_change_device(uid, ser), ensure_ascii=False))
    elif action == "restore":
        uid = sys.argv[2] if len(sys.argv) > 2 else ""
        ser = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(trigger_restore_and_run(uid, ser, run_script=True), ensure_ascii=False))
    else:
        print(json.dumps({"error": f"Unknown action {action}"}))
