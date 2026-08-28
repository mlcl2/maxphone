import hmac
import hashlib
import time
import struct
import base64

def get_2fa_code(secret: str) -> str:
    """Tự động tính toán mã 6 số OTP (2FA) từ mã Secret Key dạng TOTP (RFC 6238)"""
    try:
        secret = secret.replace(" ", "").upper()
        # Thêm padding nếu thiếu
        missing_padding = len(secret) % 8
        if missing_padding:
            secret += '=' * (8 - missing_padding)
            
        key = base64.b32decode(secret, True)
        # Thời gian hiện tại theo block 30 giây
        current_time = int(time.time() // 30)
        msg = struct.pack(">Q", current_time)
        
        # Tính HMAC-SHA1
        hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        code = ((struct.unpack(">I", hmac_hash[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000)
        return f"{code:06d}"
    except Exception as e:
        return ""
