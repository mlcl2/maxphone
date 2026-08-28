import requests

class FBChecker:
    """Module kiểm tra trạng thái Live/Die của UID Facebook chuẩn xác"""
    @staticmethod
    def check_live_uid(uid: str):
        """
        Kiểm tra UID qua Graph API Avatar Redirect URL
        Returns: (status: str, details: str)
        """
        uid = str(uid).strip()
        if not uid:
            return "DIE", "UID rỗng"

        try:
            url = f"https://graph.facebook.com/{uid}/picture?type=normal"
            res = requests.get(url, timeout=7, allow_redirects=False)
            
            if res.status_code == 302:
                location = res.headers.get("Location", "")
                if "static.xx.fbcdn.net" in location or "rsrc.php" in location:
                    return "DIE", "Tài khoản Die / Checkpoint"
                else:
                    return "LIVE", "Tài khoản đang Hoạt Động (Live)"
            elif res.status_code == 400:
                return "DIE", "UID không tồn tại / Die"
            else:
                return FBChecker._check_live_fallback(uid)

        except Exception as e:
            return "UNKNOWN", f"Lỗi mạng: {str(e)}"

    @staticmethod
    def _check_live_fallback(uid: str):
        try:
            url = f"https://mbasic.facebook.com/{uid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=5)
            if "Phải đăng nhập" in res.text or "Log In" in res.text or "profile_id" in res.text:
                return "LIVE", "Live (mbasic)"
            return "DIE", "Die / Checkpoint"
        except Exception:
            return "UNKNOWN", "Không kiểm tra được"

def check_fb_live(uid: str):
    status, msg = FBChecker.check_live_uid(uid)
    return (status == "LIVE"), msg
