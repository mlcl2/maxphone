import re

class SmartAccountParser:
    """Tự động nhận diện các trường thông tin nick Facebook từ một dòng dữ liệu bất kỳ"""
    
    @staticmethod
    def parse_line(line: str) -> dict:
        line = line.strip()
        if not line:
            return {}
            
        # Phân tách theo dấu | hoặc tab hoặc comma
        parts = [p.strip() for p in re.split(r'[|\t]', line) if p.strip()]
        
        info = {
            "uid": "",
            "password": "",
            "fa2": "",
            "cookie": "",
            "token": "",
            "email": "",
            "pass_email": "",
            "proxy": "",
            "useragent": ""
        }
        
        remaining_parts = list(parts)
        
        # 1. Tìm Cookie
        for p in list(remaining_parts):
            if "c_user=" in p or "xs=" in p or "fr=" in p:
                info["cookie"] = p
                remaining_parts.remove(p)
                # Trích xuất UID từ cookie nếu chưa có
                m = re.search(r'c_user=(\d+)', p)
                if m and not info["uid"]:
                    info["uid"] = m.group(1)
                break
                
        # 2. Tìm Token
        for p in list(remaining_parts):
            if p.startswith("EAA") or p.startswith("EAAG") or p.startswith("EAAB"):
                info["token"] = p
                remaining_parts.remove(p)
                break
                
        # 3. Tìm Email & Pass Email
        for p in list(remaining_parts):
            if "@" in p and "." in p and not p.startswith("http"):
                info["email"] = p
                remaining_parts.remove(p)
                break
                
        # 4. Tìm Proxy
        for p in list(remaining_parts):
            # Proxy thường dạng ip:port, ip:port:user:pass, http://...
            if re.match(r'^(http://|socks5://)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+', p):
                info["proxy"] = p
                remaining_parts.remove(p)
                break
                
        # 5. Tìm Mã 2FA (Secret key 16-32 ký tự viết hoa/số)
        for p in list(remaining_parts):
            clean_p = p.replace(" ", "")
            if len(clean_p) in (16, 24, 32) and clean_p.isalnum() and clean_p.isupper():
                info["fa2"] = clean_p
                remaining_parts.remove(p)
                break
                
        # 6. Tìm UserAgent
        for p in list(remaining_parts):
            if "Mozilla/" in p or "Dalvik/" in p or "FBAV/" in p:
                info["useragent"] = p
                remaining_parts.remove(p)
                break

        # 7. Phân định UID và Password trong các phần còn lại
        for p in list(remaining_parts):
            if not info["uid"] and p.isdigit() and len(p) >= 8:
                info["uid"] = p
                remaining_parts.remove(p)
                break
                
        # Phần còn lại có độ dài vừa phải thường là Password hoặc Pass Email
        if remaining_parts:
            if not info["password"]:
                # Nếu password bị trùng với UID vừa nhận diện, lấy phần tử tiếp theo
                pwd_candidate = remaining_parts.pop(0)
                if pwd_candidate == info["uid"] and remaining_parts:
                    info["password"] = remaining_parts.pop(0)
                else:
                    info["password"] = pwd_candidate
            elif info["email"] and not info["pass_email"]:
                info["pass_email"] = remaining_parts.pop(0)

        return info

    @staticmethod
    def parse_bulk(raw_text: str) -> list:
        results = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line:
                parsed = SmartAccountParser.parse_line(line)
                if parsed and parsed.get("uid"):
                    results.append(parsed)
        return results
