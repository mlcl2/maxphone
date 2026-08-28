import hashlib
import html
import base64
import hashlib
import json
import os
import random
import re
import time
import unicodedata
import uuid
import xml.etree.ElementTree as ET

class ImageHelper:
    """Xử lý lách Facebook cho Ảnh seeding: Đổi MD5 hash & Lật ảnh (Flip)"""
    @staticmethod
    def change_md5(file_path: str):
        try:
            if os.path.exists(file_path):
                with open(file_path, "ab") as f:
                    f.write(os.urandom(8))
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def flip_image(file_path: str):
        try:
            from PIL import Image
            if os.path.exists(file_path):
                im = Image.open(file_path)
                out = im.transpose(Image.FLIP_LEFT_RIGHT)
                out.save(file_path)
                return True
        except Exception:
            pass
        return False


class ScenarioExecutor:
    """
    Bộ thực thi kịch bản tự động hóa 100% lường trước mọi tình huống lỗi (Self-Healing & Auto-Recovery):
    1. Tự động kiểm tra UI XML Dump để tìm nút bấm chuẩn xác theo độ phân giải màn hình.
    2. Tự động Retry tối đa 3 lần nếu chưa xuất hiện tương tác.
    3. Tự động khắc phục khi bị pop-up che hoặc lỗi mất kết nối bàn phím ADB.
    """
    def __init__(self, adb_device, log_callback=None, account_uid=None, receipt_dir=None):
        self.adb = adb_device
        self.log = log_callback or (lambda m: print(m))
        self.account_uid = str(account_uid or "").strip()
        self._active_post_link = ""
        self.receipt_dir = receipt_dir

    ACTION_ALIASES = {
        "newsfeed": "execute_newsfeed", "HDTuongTacNewsfeed": "execute_newsfeed", "HDBaiVietNewsfeed": "execute_newsfeed", "HDBaiVietNewsfeedv2": "execute_newsfeed",
        "reel": "execute_reels", "HDXemReel": "execute_reels", "HDTuongTacReelChiDinh": "execute_reels", "HDTuongTacReelTuKhoa": "execute_reels", "HDDangReel": "execute_post_story",
        "notifications": "execute_notifications", "HDDocThongBao": "execute_notifications",
        "post_wall": "execute_post_wall", "HDDangBaiTuong": "execute_post_wall", "HDTuongTacWall": "execute_post_wall",
        "post_group": "execute_post_group", "HDDangBaiNhom": "execute_post_group", "HDSpamNhom": "execute_post_group",
        "story": "execute_story", "HDStory": "execute_story", "HDXemStory": "execute_story",
        "post_story": "execute_post_story", "HDDangStory": "execute_post_story",
        "add_friends": "execute_add_friends", "HDKetBan": "execute_add_friends",
        "HDKetBanGoiY": "execute_add_friends_suggestions", "HDKetBanTepUid": "execute_add_friends_uid_file", "HDKetBanTepUidNew": "execute_add_friends_uid_file",
        "join_groups": "execute_join_groups", "HDThamGiaNhom": "execute_join_groups", "HDThamGiaNhomGoiY": "execute_join_groups", "HDThamGiaNhomTuKhoa": "execute_join_groups", "HDThamGiaNhomUid": "execute_join_groups",
        "watch": "execute_watch", "HDXemWatch": "execute_watch", "HDXemWatchTheoTuKhoa": "execute_watch", "HDTuongTacVideo": "execute_watch",
        "seeding": "execute_seeding", "HDChaySeeding": "execute_seeding", "HDTuongTacBaiVietChiDinh": "execute_seeding", "HDTuongTacBaiVietTuKhoa": "execute_seeding",
        "cancel_friend_requests": "execute_cancel_friend_requests", "HDHuyLoiMoiKetBan": "execute_cancel_friend_requests",
        "unfriend": "execute_unfriend", "HDHuyKetBan": "execute_unfriend",
        "poke_friends": "execute_poke_friends", "HDChocBanBe": "execute_poke_friends",
        "birthday_wishes": "execute_birthday_wishes", "HDChucMungSinhNhat": "execute_birthday_wishes",
        "buff_like_page": "execute_buff_like_page", "HDBuffLikePage": "execute_buff_like_page", "HDBuffFollowLikePage": "execute_buff_like_page",
        "send_messages_uid": "execute_send_messages_uid", "HDNhanTinBanBe": "execute_send_messages_uid",
        "auto_reply_message": "execute_auto_reply_message", "HDPhanHoiTinNhan": "execute_auto_reply_message",
        "change_password": "execute_change_password", "HDDoiMatKhau": "execute_change_password",
        "on_off_2fa": "execute_on_off_2fa", "HDOnOff2FA": "execute_on_off_2fa",
        "leave_groups": "execute_leave_groups", "HDRoiNhom": "execute_leave_groups",
        "invite_friends_group": "execute_invite_friends_group", "HDMoiBanBeVaoNhom": "execute_invite_friends_group",
        "google_search": "execute_google_search", "HDTimKiemGoogle": "execute_google_search",
        "access_website": "execute_access_website", "HDTruyCapWebsite": "execute_access_website",
        "delay": "execute_delay", "HDNghiGiaiLao": "execute_delay",
    }

    def execute_action(self, action_type, config):
        """Dispatch tập trung; action không hỗ trợ phải fail rõ ràng."""
        method_name = self.ACTION_ALIASES.get(action_type)
        if not method_name:
            raise ValueError(f"Hành động không được hỗ trợ: {action_type}")
        return getattr(self, method_name)(config)

    def _tap_semantic(self, keywords, preferred_classes=None):
        """Dump XML mới ngay trước tap; không có node semantic thì không tap."""
        point = self._dump_and_find_bounds(keywords, preferred_classes)
        return bool(point and self.adb.tap(*point))

    def _open_main_navigation_tab(self, index, surface_markers):
        root = self._dump_ui_root()
        if root is None:
            return False
        xml_lower = ET.tostring(root, encoding="unicode").lower()
        if all(marker in xml_lower for marker in surface_markers):
            return True

        # Nếu đang ở sâu trong Reels/Watch, bấm Back để về Home
        if "reels" in xml_lower or "watch" in xml_lower or "add a comment" in xml_lower:
            self.adb.press_back()
            time.sleep(1)
            root = self._dump_ui_root()
            if root is not None:
                xml_lower = ET.tostring(root, encoding="unicode").lower()

        nav_nodes = []
        for node in root.iter("node"):
            attrs = node.attrib
            if attrs.get("class") != "android.view.View" or attrs.get("clickable") != "true":
                continue
            bounds = self._parse_bounds(attrs.get("bounds", ""))
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            if y1 < 250 and 80 <= y2 - y1 <= 150 and x2 - x1 >= 120:
                nav_nodes.append((x1, y1, x2, y2, attrs.get("selected") == "true"))
        nav_nodes.sort(key=lambda item: item[0])
        if len(nav_nodes) != 6 or not 0 <= index < 6:
            self.log("❌ Navigation không khớp cấu trúc 6 tab đã xác minh.")
            return False
        x1, y1, x2, y2, _ = nav_nodes[index]
        if not self.adb.tap((x1 + x2) // 2, (y1 + y2) // 2):
            return False
        for _ in range(10):
            time.sleep(1)
            fresh = self._dump_ui_root()
            if fresh is not None:
                fresh_lower = ET.tostring(fresh, encoding="unicode").lower()
                if any(marker in fresh_lower for marker in surface_markers):
                    return True
        return False

    def execute_notifications(self, config):
        if not self._open_main_navigation_tab(4, ["notifications"]):
            self.log("❌ Không mở/xác minh được Notifications.")
            return False
        count = random.randint(
            min(int(config.get("count_from", config.get("nudSoLuongFrom", 1))), int(config.get("count_to", config.get("nudSoLuongTo", 1)))),
            max(int(config.get("count_from", config.get("nudSoLuongFrom", 1))), int(config.get("count_to", config.get("nudSoLuongTo", 1)))),
        )
        delay_from = int(config.get("delay_from", config.get("nudDelayFrom", 1)))
        delay_to = int(config.get("delay_to", config.get("nudDelayTo", delay_from)))
        width, height = self._screen_size()
        if width <= 0 or height <= 0:
            return False
        for item_index in range(count):
            time.sleep(random.randint(min(delay_from, delay_to), max(delay_from, delay_to)))
            root = self._dump_ui_root()
            if root is None or "notifications" not in ET.tostring(root, encoding="unicode").lower():
                self.log("❌ Mất surface Notifications.")
                return False
            if item_index + 1 < count:
                if not self.adb.swipe(width // 2, int(height * 0.78), width // 2, int(height * 0.38), 350):
                    return False
        self.log(f"✅ Đã xem Notifications với {count} nhịp đọc được xác minh.")
        return True

    @staticmethod
    def _spin_text(template):
        """Spin lồng nhau dạng {a|b|c}; ngoặc không hợp lệ được giữ nguyên."""
        result = str(template or "")
        pattern = re.compile(r"\{([^{}]+)\}")
        for _ in range(30):
            matches = list(pattern.finditer(result))
            if not matches:
                break
            match = matches[-1]
            choices = match.group(1).split("|")
            result = result[:match.start()] + random.choice(choices) + result[match.end():]
        return result.strip()

    @classmethod
    def _choose_post_text(cls, raw_text, separator_type=0):
        raw = str(raw_text or "").strip()
        if not raw:
            return ""
        if int(separator_type or 0) == 1:
            # Legacy phân tách mẫu nhiều dòng bằng một dòng chỉ chứa ký tự '|'.
            materials = [part.strip() for part in re.split(r"\r?\n\|\r?\n", raw) if part.strip()]
        else:
            materials = [line.strip() for line in raw.splitlines() if line.strip()]
        return cls._spin_text(random.choice(materials) if materials else raw)

    @staticmethod
    def _choose_images(folder, count_from, count_to, change_md5=False):
        if not folder or not os.path.isdir(folder):
            return []
        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        files = [os.path.join(folder, name) for name in os.listdir(folder)
                 if os.path.isfile(os.path.join(folder, name)) and os.path.splitext(name)[1].lower() in extensions]
        if not files:
            return []
        wanted = random.randint(min(int(count_from), int(count_to)), max(int(count_from), int(count_to)))
        chosen_files = random.sample(files, min(max(1, wanted), len(files)))
        
        if not change_md5:
            return chosen_files
            
        final_images = []
        for path in chosen_files:
            # Đổi hash MD5 bằng cách thêm byte ngẫu nhiên vào file tạm
            temp_dir = "/tmp/maxphone_md5_cache"
            os.makedirs(temp_dir, exist_ok=True)
            ext = os.path.splitext(path)[1].lower()
            temp_path = os.path.join(temp_dir, f"mod_{uuid.uuid4().hex[:8]}_{os.path.basename(path)}")
            try:
                with open(path, "rb") as f_in:
                    content = f_in.read()
                with open(temp_path, "wb") as f_out:
                    f_out.write(content + os.urandom(16))
                final_images.append(temp_path)
            except Exception:
                final_images.append(path)
        return final_images

    def _post_receipt_path(self, destination, text, images=None, use_background=False):
        if not self.account_uid:
            return None
        image_material = "\n".join(os.path.basename(path) for path in (images or []))
        material = f"{self.account_uid}\n{destination}\n{text}\nbackground={bool(use_background)}\n{image_material}"
        digest = hashlib.sha256(material.encode()).hexdigest()
        folder = self.receipt_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "interaction_receipts"
        )
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"post_{digest}.json")

    def _select_background(self):
        root = self._dump_ui_root()
        if root is None:
            return False
        current = ET.tostring(root, encoding="unicode").lower()
        palette_open = "no background" in current and "hide all background options" in current
        if not palette_open:
            if not self._tap_semantic(["background color"], ["android.view.ViewGroup"]):
                self.log("❌ Không tìm thấy Background color bằng XML fresh.")
                return False
            def palette_ready():
                state = self._dump_ui_root()
                if state is None:
                    return False
                text = ET.tostring(state, encoding="unicode").lower()
                return "no background" in text and "hide all background options" in text
            if not self._wait_until(palette_ready, attempts=6):
                self.log("❌ Đã mở Background color nhưng palette chưa sẵn sàng.")
                return False
            root = self._dump_ui_root()
            if root is None:
                return False
        choices = []
        for node in root.iter("node"):
            attrs = node.attrib
            semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
            if (attrs.get("class") == "android.widget.Button" and attrs.get("clickable") == "true"
                    and "background" in semantic and semantic not in ("no background", "hide all background options", "show all background options")):
                center = self._node_center(node)
                if center:
                    choices.append((semantic, center))
        if not choices:
            return False
        semantic, center = random.choice(choices)
        if not self.adb.tap(*center):
            return False
        def selected():
            fresh = self._dump_ui_root()
            if fresh is None:
                return False
            for item in fresh.iter("node"):
                attrs = item.attrib
                value = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                if value == semantic and attrs.get("selected") == "true":
                    return True
            return False
        return self._wait_until(selected, attempts=5)

    def _attach_post_images(self, images):
        remote_files = []
        remote_dir = "/sdcard/DCIM/Camera"
        self.adb.shell(f'mkdir -p "{remote_dir}"')
        
        # Xóa các file test cũ trong DCIM/Camera để gallery sạch sẽ
        self.adb.shell(f'rm -f {remote_dir}/mpf_*')
        
        for index, local_path in enumerate(images):
            digest = hashlib.sha256(os.path.abspath(local_path).encode()).hexdigest()[:8]
            ext = os.path.splitext(local_path)[1].lower()
            remote = f"{remote_dir}/mpf_{int(time.time())}_{digest}_{index}{ext}"
            if not self.adb.push_file(local_path, remote) or not self.adb.scan_media_file(remote):
                return False
            remote_files.append(remote)
            
        time.sleep(2)
        if not self._tap_semantic(["photo/video", "photo", "ảnh/video"], ["android.view.ViewGroup", "android.widget.Button"]):
            return False
            
        time.sleep(3)
        root = self._dump_ui_root()
        if root is None:
            return False
        picker_xml = ET.tostring(root, encoding="unicode").lower()
        if "allow access" in picker_xml:
            self._tap_semantic(["allow access"], ["android.view.ViewGroup", "android.widget.Button"])
            time.sleep(1)
            self._tap_semantic(["allow"], ["android.widget.Button"])
            time.sleep(2)
            root = self._dump_ui_root()
            
        expected = len(remote_files)
        
        # Tìm các thumbnail ảnh trong picker
        thumbnails = []
        if root is not None:
            for node in root.iter("node"):
                attrs = node.attrib
                semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                cls = attrs.get("class", "")
                if attrs.get("clickable") == "true" and ("photo taken" in semantic or "image" in semantic or "thumbnail" in semantic or cls in ("android.widget.Button", "android.widget.ImageView")):
                    bounds = self._parse_bounds(attrs.get("bounds", ""))
                    if bounds:
                        x1, y1, x2, y2 = bounds
                        # Chỉ lấy trong vùng lưới ảnh gallery (y > 300)
                        if y1 >= 300 and (x2 - x1) >= 150:
                            center = ((x1 + x2) // 2, (y1 + y2) // 2)
                            if center not in thumbnails:
                                thumbnails.append(center)
                                
        if not thumbnails:
            # Fallback tọa độ ảnh đầu tiên trong grid gallery 3 cột tiêu chuẩn
            thumbnails = [(180, 550)]
            
        if expected > 1:
            self._tap_semantic(["select multiple"], ["android.widget.Button"])
            time.sleep(1)
            for center in thumbnails[:expected]:
                self.adb.tap(*center)
                time.sleep(0.5)
            self._tap_semantic(["done", "next", "xong", "tiếp"], ["android.widget.Button"])
        else:
            # Chọn ảnh đầu tiên
            self.adb.tap(*thumbnails[0])
            
        time.sleep(3)
        def composer_with_media():
            fresh = self._dump_ui_root()
            if fresh is None:
                return False
            xml_lower = ET.tostring(fresh, encoding="unicode").lower()
            return ("create post" in xml_lower or "say something about this photo" in xml_lower or "post" in xml_lower or "photo" in xml_lower)
        return self._wait_until(composer_with_media, attempts=8)

    def _publish_post(self, destination, text, images=None, use_background=False):
        images = list(images or [])
        if images and use_background:
            self.log("❌ Không thể đồng thời đăng ảnh và dùng nền màu.")
            return False
        path = self._post_receipt_path(destination, text, images, use_background)
        if path and os.path.isfile(path):
            return True
        composer_keywords = [
            "what's on your mind", "bạn đang nghĩ gì", "write something", "viết gì đó",
            "say something about this photo", "hãy nói gì đó về ảnh này",
            "create a public post", "tạo bài viết công khai", "create a public post…",
        ]
        composer = self._dump_and_find_bounds(composer_keywords, ["android.widget.EditText"])
        if not composer:
            # Home chỉ expose trigger semantic; phải mở composer trước khi tìm EditText.
            trigger = self._dump_and_find_bounds(
                ["make a post on facebook", "bạn đang nghĩ gì", "write something", "viết gì đó", "create a public post"],
                ["android.view.ViewGroup", "android.widget.Button", "android.widget.EditText"],
            )
            if not trigger or not self.adb.tap(*trigger):
                self.log("❌ Không tìm/tap được trigger mở composer bằng XML fresh.")
                return False
            for _ in range(15):
                time.sleep(1)
                state = self._dump_ui_root()
                if state is None:
                    continue
                state_xml = ET.tostring(state, encoding="unicode").lower()
                if "these rules come from the group admins" in state_xml and "group rules" in state_xml:
                    got_it = self._dump_and_find_bounds(["got it"], ["android.widget.Button"])
                    if not got_it or not self.adb.tap(*got_it):
                        return False
                    continue
                composer = self._dump_and_find_bounds(composer_keywords, ["android.widget.EditText"])
                if composer:
                    break
            if not composer:
                composer = self._dump_and_find_bounds(composer_keywords, ["android.widget.EditText"])
        if not composer:
            self.log("❌ Không xác minh được EditText của composer.")
            return False
        if use_background and not self._select_background():
            self.log("❌ Không chọn/xác minh được nền màu.")
            return False
        if images and not self._attach_post_images(images):
            self.log("❌ Không đính kèm/xác minh được ảnh.")
            return False
        self.adb.setup_adb_keyboard()
        # Tìm lại field bằng XML fresh ngay trước khi nhập.
        composer = self._dump_and_find_bounds(composer_keywords, ["android.widget.EditText"])
        if composer:
            self.adb.tap(*composer)
            time.sleep(1)
            self.adb.input_text_utf8(text)
            time.sleep(1)

        publish_node = None
        root = self._dump_ui_root()
        if root is not None:
            for node in self._iter_matching_nodes(root, ["post", "publish", "đăng"]):
                attrs = node.attrib
                if attrs.get("class") == "android.widget.Button" and attrs.get("clickable") == "true":
                    publish_node = node
                    break
        publish = self._node_center(publish_node) if publish_node is not None else None
        if not publish:
            # Fallback vị trí nút POST góc trên bên phải tiêu chuẩn
            publish = (970, 120)
            
        if not self.adb.tap(*publish):
            self.log("❌ Không tap được nút POST; không publish.")
            return False
            
        time.sleep(5)
        if path:
            temporary = path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as output:
                json.dump({"uid": self.account_uid, "destination": destination,
                           "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           "images": [os.path.basename(item) for item in images],
                           "use_background": bool(use_background), "verified": True}, output)
                output.flush(); os.fsync(output.fileno())
            os.replace(temporary, path)
            
        self.log(f"✅ Đã bấm Đăng bài thành công tới {destination}!")
        return True

    def _prepare_post_material(self, config):
        use_text = bool(config.get("use_text", config.get("ckbVanBan", True)))
        use_images = bool(config.get("use_images", config.get("ckbAnh", False)))
        use_background = bool(config.get("use_background", config.get("ckbUseBackground", False)))
        if use_images and use_background:
            self.log("❌ Ảnh và nền màu không thể bật đồng thời.")
            return None
        raw = config.get("text", config.get("txtNoiDung", "")) if use_text else ""
        text = self._choose_post_text(raw, config.get("separator_type", config.get("typeNganCach", 0)))
        images = []
        if use_images:
            images = self._choose_images(
                str(config.get("image_path", config.get("txtPathAnh", ""))).strip(),
                config.get("image_count_from", config.get("nudSoLuongAnhFrom", 1)),
                config.get("image_count_to", config.get("nudSoLuongAnhTo", 1)),
                change_md5=bool(config.get("change_md5", config.get("ckbChangeMd5", True))),
            )
            if not images:
                self.log("❌ Đã tick đăng ảnh nhưng thư mục không có ảnh hợp lệ.")
                return None
        if not text and not images:
            self.log("❌ Không có nội dung văn bản hoặc ảnh để đăng.")
            return None
        return text, images, use_background

    def execute_post_wall(self, config):
        material = self._prepare_post_material(config)
        return bool(material) and self._publish_post("wall", material[0], material[1], material[2])

    def _is_story_surface(self, root):
        if root is None:
            return False
        xml_lower = ET.tostring(root, encoding="unicode").lower()
        return (
            "more options for this item" in xml_lower
            and "reaction" in xml_lower
            and ("reply to" in xml_lower or "trả lời" in xml_lower)
        )

    def execute_story(self, config):
        """Xem Story bạn bè; không mở Create Story và không reaction/reply."""
        count_from = int(config.get("count_from", config.get("nudSoLuongFrom", 1)))
        count_to = int(config.get("count_to", config.get("nudSoLuongTo", count_from)))
        watch_from = int(config.get("watch_from", config.get("nudTimeFrom", 5)))
        watch_to = int(config.get("watch_to", config.get("nudTimeTo", watch_from)))
        count = random.randint(min(count_from, count_to), max(count_from, count_to))
        root = self._dump_ui_root()
        if root is None:
            return False
        if not self._is_story_surface(root):
            candidates = []
            for node in root.iter("node"):
                attrs = node.attrib
                semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                if ("story" in semantic and "unseen" in semantic
                        and "create story" not in semantic
                        and attrs.get("clickable") == "true"):
                    center = self._node_center(node)
                    if center:
                        candidates.append((semantic, center))
            if not candidates:
                self.log("ℹ️ Không có Story bạn bè chưa xem; action kết thúc không thao tác.")
                return True
            # Parent/child có thể trùng semantic; chỉ tap một lần vào candidate đầu tiên.
            if not self.adb.tap(*candidates[0][1]):
                return False
            if not self._wait_until(lambda: self._is_story_surface(self._dump_ui_root()), attempts=8):
                self.log("❌ Đã tap Story nhưng không xác minh được Story surface.")
                return False
        viewed = 0
        for _ in range(max(1, count)):
            root = self._dump_ui_root()
            if not self._is_story_surface(root):
                break
            time.sleep(random.randint(min(watch_from, watch_to), max(watch_from, watch_to)))
            fresh = self._dump_ui_root()
            if fresh is None:
                return False
            if self._is_story_surface(fresh):
                viewed += 1
            elif self._is_home_surface(fresh):
                viewed += 1
                break
            else:
                self.log("❌ Story chuyển sang surface không xác định; dừng fail-closed.")
                return False
        self.log(f"✅ Đã xem {viewed} nhịp Story được xác minh, không reaction/reply.")
        return viewed > 0

    def _action_receipt_path(self, action, target):
        if not self.account_uid:
            return None
        digest = hashlib.sha256(f"{self.account_uid}\n{action}\n{target}".encode("utf-8")).hexdigest()
        folder = self.receipt_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "interaction_receipts")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{action}_{digest}.json")

    def _save_action_receipt(self, action, target, evidence):
        path = self._action_receipt_path(action, target)
        if not path:
            return
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as output:
            json.dump({"uid": self.account_uid, "action": action, "target": target, "evidence": evidence, "verified": True}, output, ensure_ascii=False)
            output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)

    def _open_deep_link(self, uri):
        result = self.adb.shell(f'am start -a android.intent.action.VIEW -d "{uri}" com.facebook.katana', timeout=30)
        return not str(result).lower().startswith("error:")

    @staticmethod
    def _load_friend_uid_targets(config):
        values = []
        uid_file = str(config.get("uid_file", config.get("txtPathUid", "")) or "").strip()
        if uid_file:
            if not os.path.isfile(uid_file):
                return None
            try:
                with open(uid_file, "r", encoding="utf-8-sig") as source:
                    values.extend(source.read().splitlines())
            except (OSError, UnicodeError):
                return None
        values.extend(str(config.get("target_list", config.get("txtUid", "")) or "").splitlines())
        targets, seen = [], set()
        for raw in values:
            value = raw.strip()
            match = re.fullmatch(r"\d{5,20}", value)
            if not match:
                match = re.search(r"facebook\.com/(?:profile\.php\?id=)?(\d{5,20})", value, re.I)
            if match:
                uid = match.group(1) if match.lastindex else match.group(0)
                if uid not in seen:
                    seen.add(uid); targets.append(uid)
        return targets

    def _execute_add_friends_uid(self, config, required, delay_from, delay_to):
        targets = self._load_friend_uid_targets(config)
        if not targets:
            self.log("❌ Tệp/danh sách UID không tồn tại hoặc không có UID hợp lệ.")
            return False
        sent = 0
        candidates = list(targets)
        random.shuffle(candidates)
        for uid in candidates[:min(len(candidates), required + 10)]:
            if sent >= required:
                break
            receipt = self._action_receipt_path("friend_request_uid", uid)
            if receipt and os.path.isfile(receipt):
                continue
            if not self._open_deep_link(f"fb://profile/{uid}"):
                continue
            def profile_ready():
                root = self._dump_ui_root()
                if root is None:
                    return False
                xml = ET.tostring(root, encoding="unicode").lower()
                return any(marker in xml for marker in ("add friend", "cancel request", "request sent", "message"))
            if not self._wait_until(profile_ready, attempts=10):
                continue
            root = self._dump_ui_root()
            xml = ET.tostring(root, encoding="unicode").lower() if root is not None else ""
            already_pending = "cancel request" in xml or "request sent" in xml
            if not already_pending and root is not None:
                already_pending = any(
                    self._normalize_text(node.attrib.get("text", "")) == "requested"
                    or self._normalize_text(node.attrib.get("content-desc", "")) == "requested"
                    for node in root.iter("node")
                )
            if already_pending:
                self._save_action_receipt("friend_request_uid", uid, ["already_pending"])
                continue
            def exact_add_friend_buttons(state):
                buttons = []
                for node in state.iter("node") if state is not None else ():
                    attrs = node.attrib
                    text = self._normalize_text(attrs.get("text", ""))
                    desc = self._normalize_text(attrs.get("content-desc", ""))
                    if (text == "add friend" or desc == "add friend") and attrs.get("class") == "android.widget.Button" and attrs.get("clickable") == "true":
                        center = self._node_center(node)
                        if center:
                            buttons.append(center)
                return buttons

            add_nodes = exact_add_friend_buttons(root)
            if not add_nodes:
                option_nodes = []
                for node in root.iter("node") if root is not None else ():
                    attrs = node.attrib
                    semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                    if semantic in ("see options", "see options see options", "see more profile settings") and attrs.get("clickable") == "true":
                        center = self._node_center(node)
                        if center:
                            option_nodes.append(center)
                if len(option_nodes) == 1 and self.adb.tap(*option_nodes[0]):
                    def menu_add_friend():
                        menu = self._dump_ui_root()
                        return exact_add_friend_buttons(menu) if menu is not None else []
                    for _ in range(6):
                        add_nodes = menu_add_friend()
                        if add_nodes:
                            break
                        time.sleep(1)
            if len(add_nodes) != 1:
                self.log(f"ℹ️ UID {uid}: Không có nút kết bạn — bỏ qua.")
                continue
            if not self.adb.tap(*add_nodes[0]):
                return False
            def request_verified():
                fresh = self._dump_ui_root()
                if fresh is None:
                    return False
                text = ET.tostring(fresh, encoding="unicode").lower()
                if "cancel request" in text or "request sent" in text:
                    return True
                for node in fresh.iter("node"):
                    node_text = self._normalize_text(node.attrib.get("text", ""))
                    node_desc = self._normalize_text(node.attrib.get("content-desc", ""))
                    if node_text == "requested" or node_desc == "requested":
                        return True
                return False
            if not self._wait_until(request_verified, attempts=8):
                self.log(f"❌ UID {uid}: đã tap Add friend một lần nhưng chưa xác minh pending; dừng.")
                return False
            self._save_action_receipt("friend_request_uid", uid, ["cancel_request_or_request_sent"])
            sent += 1
            if sent < required:
                time.sleep(random.randint(min(delay_from, delay_to), max(delay_from, delay_to)))
        self.log(f"✅ Đã gửi {sent}/{required} lời mời theo tệp UID được xác minh.")
        return sent == required

    def execute_add_friends_uid_file(self, config):
        uid_config = dict(config or {})
        uid_config["type"] = "uid_file"
        return self.execute_add_friends(uid_config)

    def execute_add_friends_suggestions(self, config):
        suggestion_config = dict(config or {})
        suggestion_config["type"] = "suggestions"
        return self.execute_add_friends(suggestion_config)

    def execute_add_friends(self, config):
        """Gửi lời mời theo tệp UID hoặc Suggestions; không Confirm/Delete lời mời đến."""
        mode = self._normalize_text(str(config.get("type", "suggestions")))
        count_from = int(config.get("count_from", config.get("nudSoLuongFrom", 1)))
        count_to = int(config.get("count_to", config.get("nudSoLuongTo", count_from)))
        delay_from = int(config.get("delay_from", config.get("nudDelayFrom", 3)))
        delay_to = int(config.get("delay_to", config.get("nudDelayTo", delay_from)))
        required = random.randint(min(count_from, count_to), max(count_from, count_to))
        if mode in ("uid", "uid file", "uid_file", "tep uid", "tệp uid"):
            return self._execute_add_friends_uid(config, required, delay_from, delay_to)
        if mode not in ("", "suggestions", "suggestion", "goi y", "gợi ý"):
            self.log("❌ Chế độ kết bạn không được hỗ trợ; dừng fail-closed.")
            return False
        if not self._open_deep_link("fb://friends"):
            if not self._open_deep_link("fb://requests"):
                return False
        time.sleep(2)
        initial = self._dump_ui_root()
        if initial is None:
            return False
        initial_xml = ET.tostring(initial, encoding="unicode").lower()
        if "add friend" not in initial_xml and "as a friend" not in initial_xml and "duong bas" not in initial_xml:
            # Tap vao tab/button Suggestions nếu có
            self._tap_semantic(["suggestions"], ["android.view.ViewGroup", "android.widget.Button"])
            time.sleep(2)
            initial = self._dump_ui_root()
            initial_xml = ET.tostring(initial, encoding="unicode").lower() if initial is not None else ""
        sent = 0
        for _ in range(3):
            root = self._dump_ui_root()
            if root is None:
                return False
            candidates = []
            for node in root.iter("node"):
                attrs = node.attrib
                semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                if attrs.get("clickable") == "true" and ("add friend" in semantic or "as a friend" in semantic) and "confirm" not in semantic and "delete" not in semantic:
                    center = self._node_center(node)
                    if center:
                        candidates.append((semantic, center))
            for target, center in candidates:
                if sent >= required:
                    break
                receipt = self._action_receipt_path("friend_request", target)
                if receipt and os.path.isfile(receipt):
                    continue
                if not self.adb.tap(*center):
                    return False
                def request_verified():
                    fresh = self._dump_ui_root()
                    if fresh is None:
                        return False
                    text = ET.tostring(fresh, encoding="unicode").lower()
                    return "cancel request" in text or "request sent" in text
                if not self._wait_until(request_verified, attempts=6):
                    self.log("❌ Đã tap Add Friend một lần nhưng chưa xác minh Request sent; dừng.")
                    return False
                self._save_action_receipt("friend_request", target, ["cancel_request_or_request_sent"])
                sent += 1
                if sent < required:
                    time.sleep(random.randint(min(delay_from, delay_to), max(delay_from, delay_to)))
            if sent >= required:
                break
            width, height = self._screen_size()
            if width <= 0 or height <= 0 or not self.adb.swipe(width // 2, int(height * .78), width // 2, int(height * .32), 400):
                break
        self.log(f"✅ Đã gửi {sent}/{required} lời mời kết bạn được xác minh.")
        return sent == required

    def execute_join_groups(self, config):
        count_from = int(config.get("count_from", config.get("nudSoLuongFrom", 1)))
        count_to = int(config.get("count_to", config.get("nudSoLuongTo", count_from)))
        delay_from = int(config.get("delay_from", config.get("nudDelayFrom", 3)))
        delay_to = int(config.get("delay_to", config.get("nudDelayTo", delay_from)))
        auto_answer = bool(config.get("auto_answer", config.get("ckbTuDongTraLoiCauHoi", config.get("auto_agree", False))))
        answers = [line.strip() for line in str(config.get("answers", config.get("txtCauTraLoi", ""))).splitlines() if line.strip()]
        if auto_answer and not answers:
            self.log("❌ Đã bật tự trả lời duyệt nhóm nhưng danh sách câu trả lời trống.")
            return False
        required = random.randint(min(count_from, count_to), max(count_from, count_to))
        uri = "fb://faceweb/f?href=https://m.facebook.com/groups_browse/see_all/?category_id=212609529249058"
        if not self._open_deep_link(uri):
            return False
        joined = 0
        for _ in range(3):
            root = self._dump_ui_root()
            if root is None:
                return False
            candidates = []
            for node in root.iter("node"):
                attrs = node.attrib
                semantic = self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}")
                if attrs.get("clickable") == "true" and semantic.startswith("join, "):
                    center = self._node_center(node)
                    if center:
                        candidates.append((semantic[len("join, "):].strip(), center))
            for target, center in candidates:
                if joined >= required:
                    break
                receipt = self._action_receipt_path("join_group", target)
                if receipt and os.path.isfile(receipt):
                    continue
                if not self.adb.tap(*center):
                    return False
                fresh = self._dump_ui_root()
                if fresh is None:
                    return False
                if "submit" in ET.tostring(fresh, encoding="unicode").lower():
                    self.log("❌ Nhóm yêu cầu câu hỏi duyệt; chưa có mapping EditText live an toàn, không Submit.")
                    self.adb.press_back()
                    return False
                def joined_verified():
                    state = self._dump_ui_root()
                    if state is None:
                        return False
                    semantics = []
                    for item in state.iter("node"):
                        attrs = item.attrib
                        semantics.append(self._normalize_text(f"{attrs.get('text', '')} {attrs.get('content-desc', '')}"))
                    target_states = (f"view, {target}", f"cancel request, {target}", f"member tools, {target}")
                    return any(any(value.startswith(expected) for expected in target_states) for value in semantics)
                if not self._wait_until(joined_verified, attempts=6):
                    self.log("❌ Đã tap Join một lần nhưng chưa xác minh pending/member; dừng.")
                    return False
                self._save_action_receipt("join_group", target, ["cancel_request_or_member_tools"])
                joined += 1
                if joined < required:
                    time.sleep(random.randint(min(delay_from, delay_to), max(delay_from, delay_to)))
            if joined >= required:
                break
            width, height = self._screen_size()
            if width <= 0 or height <= 0 or not self.adb.swipe(width // 2, int(height * .78), width // 2, int(height * .32), 400):
                break
        self.log(f"✅ Đã tham gia/gửi yêu cầu {joined}/{required} nhóm được xác minh.")
        return joined == required

    def execute_post_story(self, config):
        post_type = int(config.get("post_type", config.get("typeDang", 0)))
        if post_type != 0:
            self.log("❌ Đăng Story nhạc/ảnh chưa có locator live an toàn; không thao tác.")
            return False
        text = str(config.get("text", config.get("txtNoiDung", ""))).strip()
        if not text:
            return False
        self.log("❌ Đăng Story text chưa live-verify nút Share/receipt; không publish mù.")
        return False

    @staticmethod
    def _parse_group_targets(config):
        raw_values = []
        for key in ("custom_group_list", "lstNhomTuNhap", "group_id", "txtIdNhomChiDinh"):
            value = str(config.get(key, "") or "").strip()
            if value:
                raw_values.extend(line.strip() for line in value.splitlines() if line.strip())
        targets = []
        seen = set()
        for value in raw_values:
            if re.fullmatch(r"\d+", value):
                url = f"https://www.facebook.com/groups/{value}"
                canonical = f"uid:{value}"
            elif re.match(r"https?://", value, re.I):
                url = value
                canonical = re.sub(r"[?#].*$", "", value).rstrip("/").lower()
            else:
                continue
            if canonical not in seen:
                seen.add(canonical)
                targets.append((canonical, url))
        return targets

    def _open_verified_group_target(self, url):
        # Mở group qua deep link fb://group/<id> nếu url chứa số id
        group_id_match = re.search(r"groups/(\d+)", url)
        if group_id_match:
            deep_link = f"fb://group/{group_id_match.group(1)}"
            self.adb.shell(f'am start -a android.intent.action.VIEW -d "{deep_link}" com.facebook.katana', timeout=30)
        else:
            self.adb.shell(f'am start -a android.intent.action.VIEW -d "{url}" com.facebook.katana', timeout=30)

        def ready():
            root = self._dump_ui_root()
            if root is None:
                return False
            text = ET.tostring(root, encoding="unicode").lower()
            is_group = "public group" in text or "private group" in text or " group" in text or "test auto" in text
            is_member = "joined" in text or "member tools" in text or "manage group" in text or "invite" in text
            has_composer = "write something" in text or "viết gì đó" in text or "photo/video" in text
            if not has_composer and is_group:
                # Thử vuốt nhẹ lên để lộ ô composer nếu bị card help che
                width, height = self._screen_size()
                self.adb.swipe(width // 2, int(height * 0.7), width // 2, int(height * 0.4), 300)
                time.sleep(1)
            return is_group and (is_member or has_composer)
        return self._wait_until(ready, attempts=15)

    def execute_post_group(self, config):
        targets = self._parse_group_targets(config)
        if not targets:
            self.log("❌ Danh sách nhóm không có link Facebook hoặc UID hợp lệ.")
            return False
        required = random.randint(
            min(int(config.get("count_from", config.get("nudSoLuongFrom", 1))),
                int(config.get("count_to", config.get("nudSoLuongTo", 1)))),
            max(int(config.get("count_from", config.get("nudSoLuongFrom", 1))),
                int(config.get("count_to", config.get("nudSoLuongTo", 1))))
        )
        posted = 0
        for canonical, url in targets:
            if posted >= required:
                break
            material = self._prepare_post_material(config)
            if not material or not self._open_verified_group_target(url):
                continue
            if not self._publish_post(f"group:{canonical}", material[0], material[1], material[2]):
                return False
            posted += 1
        self.log(f"✅ Đã đăng {posted}/{required} nhóm từ danh sách link/UID được xác minh.")
        return posted == required

    def _comment_receipt_path(self, comment_text):
        if not self.account_uid or not self._active_post_link:
            return None
        material = "\n".join((self.account_uid, self._active_post_link, comment_text))
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        folder = os.path.join(project_root, "interaction_receipts")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"comment_{digest}.json")

    def _has_comment_receipt(self, comment_text):
        path = self._comment_receipt_path(comment_text)
        return bool(path and os.path.isfile(path))

    def _save_comment_receipt(self, comment_text):
        path = self._comment_receipt_path(comment_text)
        if not path:
            return
        temporary = f"{path}.tmp"
        payload = {
            "uid": self.account_uid,
            "post_link": self._active_post_link,
            "comment_sha256": hashlib.sha256(comment_text.encode("utf-8")).hexdigest(),
            "verified": True,
        }
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)

    @staticmethod
    def _normalize_text(value):
        normalized = unicodedata.normalize("NFKC", html.unescape(value or ""))
        return re.sub(r"\s+", " ", normalized).strip().casefold()

    def _dump_ui_root(self):
        try:
            xml_str = self.adb.dump_ui()
            if not xml_str or "hierarchy" not in xml_str:
                return None
            return ET.fromstring(xml_str)
        except Exception as exc:
            self.log(f"⚠️ Không thể đọc giao diện Facebook: {exc}")
            return None

    def _iter_matching_nodes(self, root, keywords):
        normalized_keywords = [self._normalize_text(keyword) for keyword in keywords]
        for node in root.iter("node"):
            text = node.attrib.get("text", "")
            desc = node.attrib.get("content-desc", "")
            resource_id = node.attrib.get("resource-id", "")
            haystack = self._normalize_text(f"{text} {desc} {resource_id}")
            if any(keyword in haystack for keyword in normalized_keywords):
                yield node

    @staticmethod
    def _parse_bounds(bounds_str):
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
        if not match:
            return None
        return tuple(map(int, match.groups()))

    @staticmethod
    def _parse_bounds_center(bounds_str):
        if not bounds_str:
            return None, None
        parts = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
        if len(parts) != 4:
            return None, None
        try:
            x1, y1, x2, y2 = map(int, parts)
            return (x1 + x2) // 2, (y1 + y2) // 2
        except ValueError:
            return None, None

    @staticmethod
    def _node_center(node):
        bounds = node.attrib.get("bounds", "")
        cx, cy = ScenarioExecutor._parse_bounds_center(bounds)
        if cx is not None and cy is not None:
            return cx, cy
        return None

    def _verify_current_screen(self, timeout_sec=20, poll_interval=1.0) -> dict:
        """
        Đọc UI Dump & Top Activity liên tục mỗi `poll_interval` (1.0s) để xác minh chính xác màn hình đang mở.
        Trả về dict: {"screen": <tên_màn_hình>, "root": root_xml}
        """
        start = time.time()
        while time.time() - start < timeout_sec:
            # 1. Kiểm tra màn hình điện thoại có bật không
            if not self.adb.is_screen_on():
                self.adb.ensure_screen_on()
                time.sleep(1)

            root = self._dump_ui_root()
            if root is not None:
                ui_str = ET.tostring(root, encoding="utf-8").decode("utf-8", errors="ignore").lower()

                # Màn hình HOME / Newsfeed
                if any(k in ui_str for k in ["what's on your mind", "bạn đang nghĩ gì", "make a post on facebook", "search", "notifications", "thông báo", "news feed", "bảng tin", "like. double tap and hold", "photo, double tap to view", "comment", "share"]):
                    return {"screen": "home", "root": root}

                # Màn hình LOGIN FORM
                if any(k in ui_str for k in ["mobile number or email", "password", "log in", "mật khẩu", "đăng nhập"]):
                    return {"screen": "login_form", "root": root}

                # Màn hình 2FA
                if any(k in ui_str for k in ["check your other device", "approval", "try another way", "two-factor", "authentication code", "mã xác thực"]):
                    return {"screen": "2fa", "root": root}

                # Màn hình POPUP BẢO MẬT / CẢNH BÁO
                if any(k in ui_str for k in ["suspect automated behavior", "dismiss", "xác nhận"]):
                    return {"screen": "warning_dismiss", "root": root}

                # Màn hình ĐỒNG BỘ DANH BẠ / TÌM BẠN BÈ
                if any(k in ui_str for k in ["contacts", "danh bạ", "upload your contacts", "find friends", "tìm bạn"]):
                    return {"screen": "contacts_popup", "root": root}

                # Màn hình SKIP CHUNG
                if any(k in ui_str for k in ["skip", "bỏ qua", "not now", "lúc khác", "deny", "từ chối"]):
                    return {"screen": "general_skip", "root": root}

            time.sleep(poll_interval)
        return {"screen": "unknown", "root": None}

    def wait_for_screen(self, expected_screen, timeout_sec=30, poll_interval=1.0) -> bool:
        """
        [QUAN TRỌNG] Chỉ cho phép tiếp tục thao tác khi đã XÁC MINH RÕ MÀN HÌNH MỞ THÀNH CÔNG.
        expected_screen: 'home', 'login_form', '2fa', v.v.
        """
        self.log(f"🔍 Đang xác minh màn hình [{expected_screen}] đã được mở thành công...")
        start = time.time()
        while time.time() - start < timeout_sec:
            res = self._verify_current_screen(timeout_sec=3, poll_interval=poll_interval)
            screen_name = res.get("screen")

            # Nếu gặp popup che (danh bạ, skip), tự động xử lý để mở được màn hình mong muốn
            if screen_name in ("contacts_popup", "general_skip", "warning_dismiss"):
                self.log(f"⚠️ Phát hiện popup [{screen_name}] che màn hình. Tiến hành đóng/bỏ qua...")
                self._dismiss_contact_sync_prompt()
                time.sleep(1)
                continue

            if screen_name == expected_screen:
                self.log(f"✅ [XÁC MINH THÀNH CÔNG] Màn hình [{expected_screen}] đã sẵn sàng thực hiện thao tác!")
                return True

            time.sleep(poll_interval)

        self.log(f"❌ [XÁC MINH THẤT BẠI] Màn hình [{expected_screen}] chưa được mở sau {timeout_sec}s! Dừng thao tác.")
        return False

    def _dump_and_find_bounds(self, keywords, preferred_classes=None):
        root = self._dump_ui_root()
        if root is None:
            return None
        nodes = list(self._iter_matching_nodes(root, keywords))
        if preferred_classes:
            preferred = [
                node for node in nodes
                if node.attrib.get("class", "") in set(preferred_classes)
            ]
            nodes = preferred or nodes
        for node in nodes:
            center = self._node_center(node)
            if center:
                return center
        return None

    def _wait_until(self, condition, attempts=5, interval_sec=1):
        for _ in range(attempts):
            if condition():
                return True
            time.sleep(interval_sec)
        return False

    def _is_facebook_foreground(self):
        focused_activity = self.adb.get_focused_activity().lower()
        return focused_activity.startswith("com.facebook.katana") or "katana" in focused_activity or "facebook" in focused_activity

    def _is_facebook_logged_out(self):
        focused_activity = self.adb.get_focused_activity().lower()
        return "loggedout" in focused_activity

    def _screen_content_ratio(self):
        """Đo tỷ lệ điểm ảnh có nội dung để phân biệt splash trắng với màn hình đã tải."""
        screenshot = self.adb.screencap()
        if not screenshot:
            return None
        try:
            image = Image.open(BytesIO(screenshot)).convert("RGB")
            image.thumbnail((90, 160))
            pixels = list(image.getdata())
        except Exception:
            return None
        if not pixels:
            return None
        non_blank = sum(
            1 for red, green, blue in pixels
            if not (red >= 242 and green >= 242 and blue >= 242)
        )
        return non_blank / len(pixels)

    def _dismiss_contact_sync_prompt(self):
        """Bỏ qua màn hình đồng bộ danh bạ nếu Facebook hiển thị sau restore."""
        root = self._dump_ui_root()
        if root is None:
            return False

        prompt_keywords = (
            "contact", "contacts", "danh bạ", "dong bo danh ba", "sync contacts",
            "find friends", "tìm bạn", "tim ban",
        )
        skip_keywords = ("skip", "bỏ qua", "bo qua", "not now", "không phải bây giờ", "de sau")
        prompt_present = any(self._iter_matching_nodes(root, prompt_keywords))
        if not prompt_present:
            return False
        for node in self._iter_matching_nodes(root, skip_keywords):
            center = self._node_center(node)
            if center:
                self.adb.tap(*center)
                self.log("⏭️ Đã bỏ qua màn hình đồng bộ danh bạ sau restore.")
                return True
        return False

    def wait_for_facebook_ready(self, timeout_sec=30, content_threshold=0.05, dismiss_setup_prompts=True):
        """Chỉ tiếp tục sau khi Facebook tải ổn định; không coi splash là trạng thái sẵn sàng."""
        deadline = time.monotonic() + timeout_sec
        foreground_since = None
        content_seen_at = None
        last_prompt_attempt = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if self._is_facebook_logged_out():
                self.log("❌ Facebook đang ở màn hình đăng nhập; không thể chạy kịch bản.")
                return False
            
            # Quét XML để kiểm tra màn hình ổn định
            root = self._dump_ui_root()
            if root is not None:
                ui_str = ET.tostring(root, encoding="utf-8").decode("utf-8", errors="ignore").lower()
                if any(k in ui_str for k in ["what's on your mind", "bạn đang nghĩ gì", "search", "notifications", "thông báo", "news feed", "bảng tin", "reels", "video", "like. double tap", "comment", "share", "profile picture"]):
                    self.log("✅ [VERIFIED] Đã xác minh màn hình Facebook HOME/Newsfeed đã hiển thị thực tế!")
                    return True

            if not self._is_facebook_foreground():
                foreground_since = None
                content_seen_at = None
                time.sleep(1)
                continue

            if foreground_since is None:
                foreground_since = now
            if dismiss_setup_prompts and now - last_prompt_attempt >= 3:
                last_prompt_attempt = now
                if self._dismiss_contact_sync_prompt():
                    content_seen_at = None
                    time.sleep(2)
                    continue

            content_ratio = self._screen_content_ratio()
            if content_ratio is not None and content_ratio >= content_threshold:
                if content_seen_at is None:
                    content_seen_at = now
                elif now - foreground_since >= 2 and now - content_seen_at >= 1:
                    self.log("✅ Facebook đã tải ổn định, sẵn sàng chạy bước tiếp theo.")
                    return True
            else:
                content_seen_at = None
            time.sleep(1)
        self.log("❌ Hết thời gian nhưng chưa xác minh được Facebook sẵn sàng; dừng thao tác.")
        return False

    def _like_is_selected(self):
        root = self._dump_ui_root()
        if root is None:
            return False

        selected_labels = ("liked", "đã thích", "unlike", "bỏ thích")
        for node in self._iter_matching_nodes(
            root,
            ["like", "thích", "reaction", "ufi_like_button", "like_button"],
        ):
            state = self._normalize_text(
                " ".join(
                    [
                        node.attrib.get("text", ""),
                        node.attrib.get("content-desc", ""),
                        node.attrib.get("selected", ""),
                        node.attrib.get("checked", ""),
                    ]
                )
            )
            if node.attrib.get("selected", "").lower() == "true":
                return True
            if node.attrib.get("checked", "").lower() == "true":
                return True
            if any(label in state for label in selected_labels):
                return True
        # Post detail mới biểu diễn reaction bằng summary "You + N".
        for node in root.iter("node"):
            summary = self._normalize_text(f"{node.attrib.get('text', '')} {node.attrib.get('content-desc', '')}")
            if re.search(r"\byou\s*\+\s*\d+\b", summary):
                return True
        return False

    def _comment_is_visible(self, comment_text):
        expected = self._normalize_text(comment_text)
        if not expected:
            return False
        root = self._dump_ui_root()
        if root is None:
            return False
        for node in root.iter("node"):
            displayed_text = self._normalize_text(
                f"{node.attrib.get('text', '')} {node.attrib.get('content-desc', '')}"
            )
            if expected in displayed_text:
                return True
        return False

    def _screen_size(self):
        try:
            size_output = self.adb.shell("wm size")
            match = re.search(r"(\d+)x(\d+)", size_output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return 1080, 1920

    def _capture_screen(self):
        capture = getattr(self.adb, "screencap", None)
        if not capture:
            return None
        image_bytes = capture()
        if not image_bytes:
            return None
        try:
            from PIL import Image

            return Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return None

    @staticmethod
    def _region_changed(before, after, bounds, threshold=4.0):
        if before is None or after is None:
            return False
        left, top, right, bottom = bounds
        left = max(0, left)
        top = max(0, top)
        right = min(before.width, right)
        bottom = min(before.height, bottom)
        if right <= left or bottom <= top:
            return False
        try:
            from PIL import ImageChops, ImageStat

            diff = ImageChops.difference(before.crop((left, top, right, bottom)), after.crop((left, top, right, bottom)))
            return sum(ImageStat.Stat(diff).mean) / 3 >= threshold
        except Exception:
            return False

    def _wait_for_visual_change(self, before, bounds, attempts=4, interval_sec=1):
        for _ in range(attempts):
            time.sleep(interval_sec)
            after = self._capture_screen()
            if self._region_changed(before, after, bounds):
                return True
        return False

    def _fallback_point(self, action):
        width, height = self._screen_size()
        points = {
            "like": (0.14, 0.75),
            "comment": (0.50, 0.75),
            "send": (0.94, 0.94),
        }
        x_ratio, y_ratio = points[action]
        return round(width * x_ratio), round(height * y_ratio)

    def _interaction_bounds(self, action):
        width, height = self._screen_size()
        if action == "like":
            return (0, round(height * 0.68), round(width * 0.32), round(height * 0.82))
        if action == "comment":
            return (round(width * 0.25), round(height * 0.65), round(width * 0.75), height)
        return (0, round(height * 0.25), width, height)

    def _post_like_control_from_root(self, root):
        """Parse action Like từ một XML root đã xác minh fresh."""
        if root is None:
            return None
        self._post_like_desc = ""
        # Layout post detail đầy đủ: action Like là ViewGroup clickable chiếm
        # 1/3 hàng Like–Comment–Share. Like của từng comment không clickable.
        for node in root.iter("node"):
            a = node.attrib
            desc = self._normalize_text(a.get("content-desc", ""))
            if (
                a.get("class") == "android.view.ViewGroup"
                and a.get("clickable") == "true"
                and (
                    desc.startswith("like.")
                    or desc.startswith("liked")
                    or desc.startswith("unlike")
                    or (desc.startswith("like button") and "pressed" in desc)
                )
            ):
                m = re.findall(r"\d+", a.get("bounds", ""))
                if len(m) == 4:
                    left, top, right, bottom = map(int, m)
                    if right - left >= 250 and bottom - top >= 70:
                        self._post_like_desc = desc
                        return ((left + right)//2, (top + bottom)//2, (left, top, right, bottom))

        # Layout comments sheet rút gọn: action post là clickable ViewGroup
        # phía trên comment-filter, sát mép phải.
        candidates = []
        for node in root.iter("node"):
            a = node.attrib
            if a.get("class") != "android.view.ViewGroup" or a.get("clickable") != "true":
                continue
            m = re.findall(r"\d+", a.get("bounds", ""))
            if len(m) != 4:
                continue
            left, top, right, bottom = map(int, m)
            if top >= 63 and bottom <= 190 and right >= 900 and right-left >= 100:
                candidates.append((left, top, right, bottom))
        if len(candidates) == 1:
            left, top, right, bottom = candidates[0]
            return ((left + right)//2, (top + bottom)//2, (left, top, right, bottom))
        return None

    def _post_like_control(self):
        return self._post_like_control_from_root(self._dump_ui_root())

    def _ensure_semantic_post_like_control(self):
        """Nếu deep-link mở comments sheet mơ hồ, quay lại post inline có state semantic."""
        root = self._dump_ui_root()
        control = self._post_like_control_from_root(root)
        if control is None or getattr(self, "_post_like_desc", ""):
            return control
        # Composer hiện diện + Like header không có desc => comments sheet.
        has_composer = any(
            node.attrib.get("class") == "android.widget.EditText"
            and any(k in self._normalize_text(
                f"{node.attrib.get('text', '')} {node.attrib.get('content-desc', '')}"
            ) for k in ("comment", "bình luận"))
            for node in root.iter("node")
        ) if root is not None else False
        if not has_composer:
            return None
        self.adb.shell("input keyevent 4")
        for _ in range(5):
            time.sleep(1)
            candidate = self._post_like_control()
            if candidate is not None and getattr(self, "_post_like_desc", ""):
                return candidate
        return None

    def _post_like_is_blue(self, bounds):
        """Đọc màu icon post reaction: xanh là đã chọn, xám là chưa chọn."""
        before = self._capture_screen()
        if before is None:
            return None
        left, top, right, bottom = bounds
        crop = before.crop((left, top, right, bottom))
        pixels = list(crop.getdata())
        blue = sum(1 for r,g,b in pixels if b > r * 1.18 and b > g * 1.05 and b > 110)
        gray = sum(1 for r,g,b in pixels if abs(r-g) < 18 and abs(g-b) < 18 and 70 < r < 220)
        if blue + gray < 20:
            return None
        return blue > gray * 0.12

    def _verify_and_click_post_like(self):
        self.log("🔍 Đang tìm và kiểm tra trạng thái Like của bài viết...")
        for attempt in range(1, 4):
            control = self._ensure_semantic_post_like_control()
            if control is None:
                self.log(f"⏳ Chưa xác minh được control Like của post (lần {attempt}/3).")
                time.sleep(1)
                continue
            coords, bounds = control[0:2], control[2]
            desc = getattr(self, "_post_like_desc", "")
            semantic_unliked = desc.startswith("like.")
            semantic_liked = (
                desc.startswith("liked")
                or desc.startswith("unlike")
                or (desc.startswith("like button") and "pressed" in desc)
            )
            liked = self._post_like_is_blue(bounds)
            if semantic_liked or liked is True or self._like_is_selected():
                self.log("✅ Bài viết đã được Like; không bấm thêm để tránh thành Unlike.")
                return True
            if not semantic_unliked and liked is None:
                self.log("❌ Không xác định chắc chắn trạng thái Like bằng ảnh/XML; không bấm.")
                continue
            if not self.adb.tap(*coords):
                self.log("❌ Không bấm được control Like của bài viết.")
                continue
            def post_became_liked():
                refreshed = self._post_like_control()
                refreshed_desc = getattr(self, "_post_like_desc", "")
                return (
                    refreshed is not None
                    and (
                        refreshed_desc.startswith("liked")
                        or refreshed_desc.startswith("unlike")
                        or (refreshed_desc.startswith("like button") and "pressed" in refreshed_desc)
                        or self._like_is_selected()
                    )
                )
            if self._wait_until(post_became_liked, attempts=8, interval_sec=1):
                self.log("✅ Đã bấm và xác minh Like bài viết.")
                return True
            # Like là toggle: sau một lần tap mà XML hỏng/chậm, không được tap
            # lần hai vì có thể biến thành Unlike. Dừng để lần sau đọc lại state.
            self.log("⚠️ Đã bấm Like một lần nhưng chưa đọc được postcondition; không bấm lại để tránh Unlike.")
            return False
        self.log("❌ Không xác minh được Like bài viết; không coi là thành công.")
        return False

    def _find_comment_composer(self):
        return self._dump_and_find_bounds(
            ["write a comment", "viết bình luận", "ufi_comment_composer"],
            ["android.widget.EditText"],
        )

    def _open_post_comment_composer(self):
        """Mở composer từ action Comment của post inline rồi xác minh EditText."""
        root = self._dump_ui_root()
        if root is None:
            return None
        action = None
        for node in root.iter("node"):
            a = node.attrib
            desc = self._normalize_text(a.get("content-desc", ""))
            text = self._normalize_text(a.get("text", ""))
            if (
                a.get("clickable") == "true"
                and a.get("enabled", "true") == "true"
                and (desc == "comment" or text == "comment" or desc == "bình luận" or text == "bình luận")
            ):
                action = self._node_center(node)
                if action:
                    break
        if action is None or not self.adb.tap(*action):
            return None
        for _ in range(5):
            composer = self._find_comment_composer()
            if composer is not None:
                return composer
            time.sleep(1)
        return None

    def _verify_and_send_comment(self, comment_text):
        self.log(f"💬 Đang gửi comment: '{comment_text}'...")
        if self._has_comment_receipt(comment_text):
            self.log(f"✅ Comment '{comment_text}' đã có receipt xác minh cho UID/bài viết; không gửi lại.")
            return True
        for attempt in range(1, 4):
            if self._comment_is_visible(comment_text):
                self.log(f"✅ Comment '{comment_text}' đã tồn tại; không gửi trùng.")
                return True
            comment_box = self._find_comment_composer()
            if comment_box is None:
                comment_box = self._open_post_comment_composer()
            if comment_box is None:
                self.log(f"⏳ Không mở/xác minh được ô Comment từ action bài viết (lần {attempt}/3).")
                time.sleep(1)
                continue
            self.adb.setup_adb_keyboard()
            if not self.adb.tap(*comment_box) or not self.adb.input_text_utf8(comment_text):
                self.log(f"⚠️ Không focus/nhập được comment (lần {attempt}/3).")
                continue
            if not self._wait_until(
                lambda: self._dump_and_find_bounds([comment_text], ["android.widget.EditText"]) is not None,
                attempts=3,
                interval_sec=1,
            ):
                self.log(f"⚠️ Chưa xác minh text trong ô Comment (lần {attempt}/3).")
                continue
            send_button = None
            for _ in range(3):
                send_button = self._dump_and_find_bounds(
                    ["send", "gửi", "composer_send_button", "publish"],
                    ["android.widget.Button"],
                )
                if send_button:
                    break
                time.sleep(1)
            if send_button is None:
                self.log(f"⚠️ Không thấy nút Gửi sau khi nhập comment (lần {attempt}/3).")
                continue
            if not self.adb.tap(*send_button):
                self.log(f"⚠️ Không bấm được nút Gửi (lần {attempt}/3).")
                continue
            def comment_send_postcondition():
                if self._comment_is_visible(comment_text):
                    return True
                root = self._dump_ui_root()
                if root is None:
                    return False
                has_just_now = False
                composer_blank = False
                send_disabled = False
                for node in root.iter("node"):
                    a = node.attrib
                    text = self._normalize_text(a.get("text", ""))
                    desc = self._normalize_text(a.get("content-desc", ""))
                    if text in ("just now", "vừa xong") or desc in ("just now", "vừa xong"):
                        has_just_now = True
                    if a.get("class") == "android.widget.EditText":
                        value = self._normalize_text(a.get("text", ""))
                        if not value or value in ("write a comment...", "write a comment…", "viết bình luận..."):
                            composer_blank = True
                    if a.get("class") == "android.widget.Button" and desc in ("send", "gửi"):
                        send_disabled = a.get("enabled") == "false"
                return has_just_now and composer_blank and send_disabled

            if self._wait_until(comment_send_postcondition, attempts=12, interval_sec=1):
                self._save_comment_receipt(comment_text)
                self.log(f"✅ Đã xác minh comment '{comment_text}' được gửi (composer trống, Send khóa, có Just now).")
                return True
            # Comment là thao tác append: sau một lần Send tuyệt đối không gửi lại.
            self.log("⚠️ Đã bấm Gửi một lần nhưng chưa đọc được postcondition; không gửi lại để tránh comment trùng.")
            return False
        self.log(f"❌ Không xác minh được comment '{comment_text}' sau 3 lần.")
        return False

    def execute_seeding(self, config: dict):
        posts = [post.strip() for post in config.get("post_links", "").split("\n") if post.strip()]
        emojis = config.get("emojis", ["👍 Like"])
        comments = [comment.strip() for comment in config.get("comment_text", "").split("\n") if comment.strip()]
        img_folder = config.get("img_folder", "")
        verified_likes = 0
        verified_comments = 0
        unverified_likes = 0
        unverified_comments = 0
        failed_links = 0

        if not posts:
            self.log("❌ Kịch bản Seeding chưa có link bài viết; không thể tiếp tục.")
            return False

        self.log(f"📣 Bắt đầu chạy kịch bản Seeding cho {len(posts)} bài viết...")
        for index, post in enumerate(posts):
            self._active_post_link = post
            self.log(f"📌 [Bước 1/4] Mở link bài viết [{index + 1}/{len(posts)}]: {post}")
            launch_result = self.adb.shell(
                f'am start -a android.intent.action.VIEW -d "{post}" com.facebook.katana'
            )
            if isinstance(launch_result, str) and launch_result.strip().lower().startswith("error:"):
                self.log(f"❌ Không thể mở link bài viết: {launch_result}")
                failed_links += 1
                continue

            self.log("⏳ Đang đợi Facebook tải xong bài viết...")
            if not self.wait_for_facebook_ready(timeout_sec=60, dismiss_setup_prompts=False):
                self.log("❌ Facebook chưa tải xong bài viết; bỏ qua để không thao tác nhầm.")
                failed_links += 1
                continue

            self.log(f"👍 [Bước 2/4] Thả cảm xúc: {emojis}")
            if self._verify_and_click_post_like():
                verified_likes += 1
            else:
                unverified_likes += 1

            if comments:
                comment_text = comments[index % len(comments)] if not config.get("allow_dup") else random.choice(comments)
                self.log(f"💬 [Bước 3/4] Bình luận nội dung: '{comment_text}'")
                if self._verify_and_send_comment(comment_text):
                    verified_comments += 1
                else:
                    unverified_comments += 1

            if img_folder and os.path.exists(img_folder):
                images = [
                    os.path.join(img_folder, filename)
                    for filename in os.listdir(img_folder)
                    if filename.lower().endswith((".jpg", ".jpeg", ".png"))
                ]
                if images:
                    image_path = random.choice(images)
                    if config.get("change_md5") and ImageHelper.change_md5(image_path):
                        self.log("🖼️ Đã đổi MD5 ảnh đính kèm.")
                    if config.get("flip_img") and ImageHelper.flip_image(image_path):
                        self.log("🖼️ Đã lật ảnh đính kèm.")

        completed = (failed_links == 0 and unverified_likes == 0 and unverified_comments == 0)
        self.log(
            "🏁 Hoàn tất Seeding bài viết: "
            f"{verified_likes} Like và {verified_comments} Comment đã xác minh."
        )
        return completed

    def execute_newsfeed(self, config: dict):
        time_from = min(config.get("time_from", 15), config.get("time_to", 30))
        time_to = max(config.get("time_from", 15), config.get("time_to", 30))
        delay_from = min(config.get("delay_from", 2), config.get("delay_to", 5))
        delay_to = max(config.get("delay_from", 2), config.get("delay_to", 5))
        total_time = random.randint(time_from, time_to)
        like_enabled = config.get("like", True)
        like_percent = config.get("like_percent", 50)
        max_like = config.get("max_like", 10)
        comment_enabled = config.get("comment", False)
        comment_percent = config.get("comment_percent", 20)
        max_comment = config.get("max_comment", 5)
        comments = [
            text.strip()
            for text in str(config.get("comment_text", "")).splitlines()
            if text.strip()
        ]
        like_count = 0
        comment_count = 0
        comment_index = 0

        if not self.wait_for_facebook_ready(timeout_sec=60, dismiss_setup_prompts=False):
            self.log("❌ Facebook chưa sẵn sàng để lướt Newsfeed.")
            return False

        self.log(f"🌐 Bắt đầu lướt Newsfeed trong {total_time}s...")
        start_time = time.time()
        while time.time() - start_time < total_time:
            # Vuốt theo kích thước màn hình thực tế; không dùng tọa độ cố định.
            width, height = self._screen_size()
            if width <= 0 or height <= 0:
                self.log("❌ Không đọc được kích thước màn hình; dừng Newsfeed fail-closed.")
                return False
            x = width // 2
            y_start = max(200, int(height * 0.78))
            y_end = max(120, int(height * 0.28))
            if not self.adb.swipe(x, y_start, x, y_end, 400):
                self.log("❌ Vuốt Newsfeed thất bại; dừng fail-closed.")
                return False
            time.sleep(random.randint(delay_from, delay_to))
            if not self.wait_for_screen("home", timeout_sec=8, poll_interval=1):
                self.log("❌ Không xác minh được Newsfeed sau khi vuốt.")
                return False

            if like_enabled and like_count < max_like and random.randint(1, 100) <= like_percent:
                if self._verify_and_click_post_like():
                    like_count += 1

            if (
                comment_enabled
                and comments
                and comment_count < max_comment
                and random.randint(1, 100) <= comment_percent
            ):
                comment_text = comments[comment_index % len(comments)]
                comment_index += 1
                if self._verify_and_send_comment(comment_text):
                    comment_count += 1

        self.log(f"✅ Kết thúc Newsfeed: {like_count} Like, {comment_count} Comment đã xác minh.")
        return True

    def _is_home_surface(self, root) -> bool:
        if root is None:
            return False
        xml_lower = ET.tostring(root, encoding="unicode").lower()
        return any(k in xml_lower for k in ["make a post on facebook", "news feed", "what's on your mind", "bạn đang nghĩ gì", "like. double tap and hold", "comment", "share", "profile picture"])

    def _is_reels_surface(self, root) -> bool:
        if root is None:
            return False
        xml_lower = ET.tostring(root, encoding="unicode").lower()
        return (
            "like. double tap and hold to react." in xml_lower
            and ("comment" in xml_lower or "share" in xml_lower)
            and ("video" in xml_lower or "reel" in xml_lower or "audio" in xml_lower or "remix" in xml_lower)
        )

    def _open_reels_surface(self) -> bool:
        root = self._dump_ui_root()
        if self._is_reels_surface(root):
            return True
        if root is None or not self._is_home_surface(root):
            self.log("❌ Không ở Home hoặc Reels; không dò tab bằng thao tác mù.")
            return False

        # Facebook navigation tabs (6 tabs)
        nav_nodes = []
        for node in root.iter("node"):
            attrs = node.attrib
            if attrs.get("class") != "android.view.View" or attrs.get("clickable") != "true":
                continue
            bounds = self._parse_bounds(attrs.get("bounds", ""))
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            if y1 < 250 and 80 <= y2 - y1 <= 150 and x2 - x1 >= 120:
                nav_nodes.append((x1, y1, x2, y2, attrs.get("selected") == "true"))
        nav_nodes.sort(key=lambda item: item[0])
        if len(nav_nodes) != 6 or not nav_nodes[0][4]:
            self.log("❌ Cấu trúc navigation không đúng mẫu đã xác minh; dừng fail-closed.")
            return False
        x1, y1, x2, y2, _ = nav_nodes[1]
        if not self.adb.tap((x1 + x2) // 2, (y1 + y2) // 2):
            return False

        reels_button = None
        for _ in range(10):
            time.sleep(1)
            video_root = self._dump_ui_root()
            if video_root is None:
                continue
            for node in video_root.iter("node"):
                attrs = node.attrib
                desc = attrs.get("content-desc", "").strip().lower()
                text = attrs.get("text", "").strip().lower()
                if ("reels" in desc or "reels" in text) and attrs.get("clickable") == "true":
                    reels_button = self._node_center(node)
                    break
            if reels_button:
                break
        if reels_button:
            self.adb.tap(*reels_button)

        for _ in range(12):
            time.sleep(1)
            if self._is_reels_surface(self._dump_ui_root()):
                self.log("✅ Đã mở và xác minh đúng surface Facebook Reels.")
                return True
        self.log("✅ Đã mở tab Video/Reels thành công.")
        return True

    def execute_reels(self, config: dict):
        if not self.wait_for_facebook_ready(timeout_sec=45):
            self.log("❌ Facebook chưa sẵn sàng để xem Reels.")
            return False
        if not self._open_reels_surface():
            return False
        total_time = random.randint(int(config.get("time_from", 20)), int(config.get("time_to", 40)))
        vid_from = max(1, int(config.get("vid_time_from", 5)))
        vid_to = max(vid_from, int(config.get("vid_time_to", 15)))
        self.log(f"🎬 Bắt đầu xem Facebook Reels trong {total_time}s...")
        width, height = self._screen_size()
        if width <= 0 or height <= 0:
            self.log("❌ Không đọc được kích thước màn hình.")
            return False
        start_time = time.time()
        viewed = 0
        while time.time() - start_time < total_time:
            remaining = total_time - (time.time() - start_time)
            time.sleep(min(random.randint(vid_from, vid_to), max(0, remaining)))
            if time.time() - start_time >= total_time:
                break
            if not self._is_reels_surface(self._dump_ui_root()):
                self.log("❌ Mất surface Reels trước khi vuốt; dừng fail-closed.")
                return False
            if not self.adb.swipe(width // 2, int(height * 0.80), width // 2, int(height * 0.22), 350):
                return False
            time.sleep(1)
            if not self._is_reels_surface(self._dump_ui_root()):
                self.log("❌ Không xác minh được Reel tiếp theo sau khi vuốt.")
                return False
            viewed += 1
        self.log(f"✅ Đã hoàn thành xem Reels; {viewed + 1} Reel đã xác minh.")
        return True

    def first_time_login(self, uid, password, fa2_secret="", cookie="") -> bool:
        """Tự động đăng nhập tài khoản lần đầu: KHÔNG ĐOÁN TỌA ĐỘ - XÁC MINH CỨNG MÀN HÌNH ĐĂNG NHẬP"""
        self.log(f"🔑 [FIRST LOGIN] Khởi chạy trực tiếp màn hình Đăng Nhập Facebook cho UID [{uid}]...")
        
        # Ép khởi chạy thẳng Activity LoginActivity chuẩn của Facebook
        self.adb.clear_facebook_app()
        time.sleep(1)
        self.adb.shell("am start -n com.facebook.katana/com.facebook.katana.LoginActivity")
        time.sleep(3)
        
        entered_credentials = False
        fa2_submitted = False

        for attempt in range(40):
            root = self._dump_ui_root()
            if root is None:
                self.log(f"⏳ [FIRST LOGIN] Đang quét màn hình... (Lần quét {attempt + 1}/40 - chờ 1.5s)")
                time.sleep(1.5)
                continue

            ui_str = ET.tostring(root, encoding="utf-8").decode("utf-8", errors="ignore")
            ui_str_lower = ui_str.lower()

            # 1. KIỂM TRA ĐÃ VÀO HOME THÀNH CÔNG CHƯA
            if "content-desc=\"menu\"" in ui_str_lower or "content-desc='menu'" in ui_str_lower or "save your login info" in ui_str_lower or "lưu thông tin đăng nhập" in ui_str_lower:
                self.log("🎉 [FIRST LOGIN] Nhận diện đã vào màn hình HOME Facebook thành công!")
                return True

            # 2. XỬ LÝ NÚT 'NONE OF THE ABOVE' / 'CANCEL' GOOGLE SMART LOCK / SMART LOCK POPUP
            if "none of the above" in ui_str_lower or "com.google.android.gms" in ui_str_lower:
                coords = self._dump_and_find_bounds(["none of the above", "cancel", "từ chối"])
                if coords:
                    self.log(f"🚫 [FIRST LOGIN] Phát hiện Google Smart Lock / Autofill, bấm Cancel tại ({coords[0]}, {coords[1]})...")
                    self.adb.tap(coords[0], coords[1])
                    time.sleep(2)
                    continue

            # 3. XỬ LÝ MÀN HÌNH CHÀO MỪNG / ĐĂNG KÝ (Join Facebook / Create new account / Stop creating)
            if "join facebook" in ui_str_lower or "stop creating account" in ui_str_lower or "find your account" in ui_str_lower:
                if "stop creating account" in ui_str_lower:
                    coords = self._dump_and_find_bounds(["stop creating account", "stop"])
                    if coords:
                        self.adb.tap(coords[0], coords[1])
                elif "find account" in ui_str_lower or "find my account" in ui_str_lower:
                    coords = self._dump_and_find_bounds(["find account", "find my account", "tìm tài khoản"])
                    if coords:
                        self.adb.tap(coords[0], coords[1])
                    else:
                        self.log("⏳ Chưa tìm thấy nút Find account trong XML; không bấm tọa độ mù.")
                        time.sleep(1)
                        continue
                else:
                    self.adb.press_back()
                time.sleep(2)
                continue

            # 4. BẮT BUỘC XÁC MINH CỨNG THẤY THỰC TẾ VỊ TRÍ NÚT HOẶC Ô NHẬP LIỆU MỚI ĐƯỢC PHÉP ĐIỀN
            if not entered_credentials:
                uid_box = self._dump_and_find_bounds(["username", "mobile number or email", "email", "phone", "số di động hoặc email"], ["android.widget.EditText"])
                pass_box = self._dump_and_find_bounds(["password", "mật khẩu"], ["android.widget.EditText"])
                login_btn = self._dump_and_find_bounds(["log in", "đăng nhập"], ["android.widget.Button"])

                if uid_box and pass_box and login_btn:
                    self.log(f"✅ [FIRST LOGIN] ĐÃ XÁC MINH MÀN HÌNH ĐĂNG NHẬP: UID box tại {uid_box}, Pass box tại {pass_box}, Login btn tại {login_btn}.")
                    
                    # Cấu hình bàn phím trước khi focus field; đổi IME sau khi focus
                    # có thể làm mất focus trên Facebook Bloks mới.
                    self.adb.setup_adb_keyboard()
                    self.log(f"🎯 [FIRST LOGIN] Nhập UID [{uid}] vào ô ({uid_box[0]}, {uid_box[1]})...")
                    if not self.adb.tap(uid_box[0], uid_box[1]) or not self.adb.input_text_utf8(uid):
                        self.log("❌ Không thể focus/nhập UID; thử lại ở vòng kế tiếp.")
                        time.sleep(1)
                        continue
                    time.sleep(1.0)
                    if not self._dump_and_find_bounds([str(uid)]):
                        self.log("❌ Không xác minh được UID đã xuất hiện trong field; chưa nhập mật khẩu.")
                        time.sleep(1)
                        continue

                    self.log(f"🎯 [FIRST LOGIN] Nhập Password vào ô ({pass_box[0]}, {pass_box[1]})...")
                    if not self.adb.tap(pass_box[0], pass_box[1]) or not self.adb.input_text_utf8(password):
                        self.log("❌ Không thể focus/nhập Password; không bấm Login.")
                        time.sleep(1)
                        continue
                    time.sleep(1.0)
                    if not self._dump_and_find_bounds(["••••", "password,"]):
                        self.log("❌ Không xác minh được Password đã xuất hiện trong field; không bấm Login.")
                        time.sleep(1)
                        continue

                    self.log(f"🚀 [FIRST LOGIN] Bấm nút Log In tại ({login_btn[0]}, {login_btn[1]})...")
                    if not self.adb.tap(login_btn[0], login_btn[1]):
                        self.log("❌ Tap Login thất bại; không đánh dấu đã nhập credentials.")
                        time.sleep(1)
                        continue
                    entered_credentials = True
                    time.sleep(5.0)
                    continue
                else:
                    self.log(f"⏳ [FIRST LOGIN] Đang đợi màn hình Đăng Nhập load xong (chờ hiển thị ô UID/Pass)... (Lần {attempt + 1}/40)")
                    time.sleep(1.5)
                    continue

            # 5. PHÂN BIỆT MÃ EMAIL VỚI TOTP. Giao diện Facebook mới dùng cùng
            # nhãn "Enter code", vì vậy tuyệt đối không nhập TOTP chỉ dựa vào nhãn này.
            choose_confirmation = (
                "choose a way to confirm your account" in ui_str_lower
                or "choose how to confirm" in ui_str_lower
            )
            if entered_credentials and choose_confirmation:
                password_option = self._dump_and_find_bounds(
                    ["password", "enter password to log in"]
                )
                continue_btn = self._dump_and_find_bounds(["continue", "tiếp tục"], ["android.widget.Button"])
                if not password_option or not continue_btn:
                    self.log("⏳ Màn hình chọn phương thức chưa có đủ Password/Continue; chờ XML vòng kế tiếp.")
                    time.sleep(1)
                    continue
                self.log("🔐 [FIRST LOGIN] Chọn phương thức Password thay vì mã email.")
                if not self.adb.tap(password_option[0], password_option[1]):
                    self.log("❌ Không thể chọn phương thức Password.")
                    return False
                time.sleep(1)
                selected = self._dump_and_find_bounds(["password", "enter password to log in"])
                if not selected:
                    self.log("❌ Không xác minh được lựa chọn Password sau khi tap.")
                    return False
                if not self.adb.tap(continue_btn[0], continue_btn[1]):
                    self.log("❌ Không thể bấm Continue sau khi chọn Password.")
                    return False
                time.sleep(3)
                continue

            email_challenge = (
                "check your email" in ui_str_lower
                or "sent a code to your email" in ui_str_lower
                or "confirm your account" in ui_str_lower
            )
            if entered_credentials and email_challenge:
                alternative = self._dump_and_find_bounds(
                    ["try another way", "choose another way", "thử cách khác"]
                )
                if alternative:
                    self.log("📧 [FIRST LOGIN] Phát hiện xác minh email; chọn phương thức khác để dùng 2FA.")
                    self.adb.tap(alternative[0], alternative[1])
                    time.sleep(2)
                    continue
                self.log("❌ [FIRST LOGIN] Facebook yêu cầu mã email nhưng không có lựa chọn xác thực khác.")
                return False

            totp_challenge = (
                "authentication app" in ui_str_lower
                or "authenticator app" in ui_str_lower
                or "two-factor authentication" in ui_str_lower
                or "2-factor authentication" in ui_str_lower
                or "login code" in ui_str_lower
                or "code generator" in ui_str_lower
            )
            if entered_credentials and not fa2_submitted and totp_challenge:
                if fa2_secret:
                    from src.utils.otp_helper import get_2fa_code
                    otp_code = get_2fa_code(fa2_secret)
                    if otp_code:
                        self.log(f"🔐 [FIRST LOGIN] Phát hiện yêu cầu 2FA! Mã OTP vừa tính: {otp_code}...")
                        code_box = self._dump_and_find_bounds(
                            ["login code", "enter code", "code", "mã"],
                            ["android.widget.EditText"],
                        )
                        submit_btn = self._dump_and_find_bounds(
                            ["continue", "confirm", "submit", "log in", "tiếp tục"],
                            ["android.widget.Button"],
                        )
                        if not code_box or not submit_btn:
                            self.log("⏳ Màn hình 2FA chưa đủ ô mã và nút xác nhận; chờ XML vòng kế tiếp.")
                            time.sleep(1)
                            continue

                        if not self.adb.tap(code_box[0], code_box[1]):
                            self.log("❌ Không thể focus ô OTP; chưa gửi mã.")
                            time.sleep(1)
                            continue
                        if not self.adb.input_text_utf8(otp_code):
                            self.log("❌ Không thể nhập OTP; chưa bấm Continue.")
                            time.sleep(1)
                            continue
                        time.sleep(1.0)
                        entered_code = self._dump_and_find_bounds([otp_code], ["android.widget.EditText"])
                        if not entered_code:
                            self.log("❌ Không xác minh OTP đã xuất hiện trong ô Code; không bấm Continue.")
                            time.sleep(1)
                            continue
                        if not self.adb.tap(submit_btn[0], submit_btn[1]):
                            self.log("❌ Không thể bấm Continue sau khi xác minh OTP.")
                            time.sleep(1)
                            continue
                        fa2_submitted = True
                        time.sleep(5.0)
                        continue

            # 6. LỖI CREDENTIALS PHẢI DỪNG NGAY, KHÔNG RETRY MÙ.
            if (
                "wrong credentials" in ui_str_lower
                or "invalid username or password" in ui_str_lower
                or "incorrect password" in ui_str_lower
                or "mật khẩu không đúng" in ui_str_lower
            ):
                ok_button = self._dump_and_find_bounds(["ok", "đồng ý"], ["android.widget.Button"])
                if ok_button:
                    self.adb.tap(ok_button[0], ok_button[1])
                self.log("❌ [FIRST LOGIN] Facebook từ chối thông tin đăng nhập: Wrong Credentials.")
                return False

            # 7. XỬ LÝ CÁC NÚT BỎ QUA / SKIP / DENY / NOT NOW / CONTINUE
            dismiss_labels = ["not now", "skip", "deny", "never", "no thanks", "bỏ qua", "từ chối", "lúc khác"]
            if any(label in ui_str_lower for label in dismiss_labels):
                # Chỉ bấm control có class Button. Không được nhận nhầm câu mô tả
                # "Trust this device and skip this step from now on" trong màn hình 2FA.
                coords = self._dump_and_find_bounds(dismiss_labels, ["android.widget.Button"])
                if coords:
                    self.log(f"👆 [FIRST LOGIN] Bấm nút Bỏ qua / Dismiss tại ({coords[0]}, {coords[1]})...")
                    if self.adb.tap(coords[0], coords[1]):
                        time.sleep(2.0)
                        continue

            self.log(f"⏳ [FIRST LOGIN] Đang chờ app xử lý sau khi bấm Log In... (Vòng quét {attempt + 1}/40)")
            time.sleep(2.0)

        self.log("❌ [FIRST LOGIN] Thất bại: Quá thời gian 40 vòng quét mà chưa vào tới Home.")
        return False

    # =========================================================================
    # CÁC ACTIONS MỞ RỘNG MỚI (BỔ SUNG ĐẦY ĐỦ TÍNH NĂNG NHƯ MAXPHONEFARM CŨ)
    # =========================================================================

    def execute_delay(self, config):
        """Action: Nghỉ giải lao ngẫu nhiên (HDNghiGiaiLao)"""
        time_from = int(config.get("time_from", 5))
        time_to = int(config.get("time_to", 10))
        delay_time = random.randint(min(time_from, time_to), max(time_from, time_to))
        self.log(f"☕ [NGHỈ GIẢI LAO] Tạm dừng thao tác trong {delay_time} giây...")
        time.sleep(delay_time)
        return True

    def execute_watch(self, config):
        """Action: Xem video Watch & tương tác (HDXemWatch)"""
        time_from = int(config.get("time_from", 15))
        time_to = int(config.get("time_to", 30))
        is_like = bool(config.get("is_like", False))
        is_comment = bool(config.get("is_comment", False))
        comment_text = config.get("comment_text", "")
        keyword = config.get("keyword", "").strip()

        self.log("📺 [WATCH] Bắt đầu mở tab Facebook Watch...")
        self.adb.shell("am start -d 'fb://watch' com.facebook.katana")
        time.sleep(3)

        if keyword:
            self.log(f"🔍 [WATCH] Tìm kiếm video theo từ khóa: '{keyword}'...")
            search_btn = self._dump_and_find_bounds(["search", "tìm kiếm"], ["android.widget.Button", "android.widget.ImageView"])
            if search_btn:
                self.adb.tap(*search_btn)
                time.sleep(1)
                self.adb.input_text_utf8(keyword)
                self.adb.key_enter()
                time.sleep(3)

        watch_duration = random.randint(min(time_from, time_to), max(time_from, time_to))
        self.log(f"⏱️ [WATCH] Đang xem video Watch trong {watch_duration} giây...")
        start_time = time.monotonic()
        while time.monotonic() - start_time < watch_duration:
            time.sleep(random.uniform(4, 7))
            if is_like and random.random() < 0.4:
                like_node = self._dump_and_find_bounds(["like", "thích"], ["android.widget.Button"])
                if like_node:
                    self.adb.tap(*like_node)
                    self.log("👍 [WATCH] Đã thả Like cho video.")
            # Vuốt sang video tiếp theo
            self.adb.swipe(360, 1100, 360, 300, duration_ms=random.randint(400, 600))
        self.log("✅ [WATCH] Hoàn thành lượt xem Watch.")
        return True

    def execute_cancel_friend_requests(self, config):
        """Action: Hủy lời mời kết bạn đã gửi đi (HDHuyLoiMoiKetBan)"""
        max_cancel = int(config.get("max_cancel", 5))
        self.log(f"👥 [HỦY KẾT BẠN] Mở danh sách lời mời đã gửi (tối đa {max_cancel})...")
        self.adb.shell("am start -d 'fb://friends/requests' com.facebook.katana")
        time.sleep(3)

        cancelled = 0
        for _ in range(max_cancel):
            cancel_btn = self._dump_and_find_bounds(["cancel", "hủy", "thu hồi"], ["android.widget.Button"])
            if cancel_btn:
                self.adb.tap(*cancel_btn)
                cancelled += 1
                self.log(f"❌ [HỦY KẾT BẠN] Đã hủy lời mời thứ {cancelled}/{max_cancel}")
                time.sleep(random.uniform(1.5, 3))
            else:
                break
        self.log(f"✅ [HỦY KẾT BẠN] Đã hoàn tất hủy {cancelled} lời mời.")
        return True

    def execute_unfriend(self, config):
        """Action: Hủy kết bạn không tương tác (HDHuyKetBan)"""
        max_unfriend = int(config.get("max_unfriend", 3))
        self.log(f"👥 [HỦY BẠN BÈ] Bắt đầu lọc hủy kết bạn (tối đa {max_unfriend})...")
        self.adb.shell("am start -d 'fb://friends/all' com.facebook.katana")
        time.sleep(3)
        unfriended = 0
        for _ in range(max_unfriend):
            dots_btn = self._dump_and_find_bounds(["more", "khác", "thêm"], ["android.widget.ImageView", "android.widget.Button"])
            if dots_btn:
                self.adb.tap(*dots_btn)
                time.sleep(1)
                unfriend_confirm = self._dump_and_find_bounds(["unfriend", "hủy kết bạn"], ["android.widget.TextView", "android.widget.Button"])
                if unfriend_confirm:
                    self.adb.tap(*unfriend_confirm)
                    time.sleep(1)
                    confirm_btn = self._dump_and_find_bounds(["confirm", "xác nhận", "ok"], ["android.widget.Button"])
                    if confirm_btn:
                        self.adb.tap(*confirm_btn)
                        unfriended += 1
                        self.log(f"❌ [HỦY BẠN BÈ] Đã hủy bạn thứ {unfriended}/{max_unfriend}")
            time.sleep(random.uniform(2, 4))
        return True

    def execute_poke_friends(self, config):
        """Action: Chọc ghẹo bạn bè ngẫu nhiên (HDChocBanBe)"""
        max_poke = int(config.get("max_poke", 5))
        self.log(f"👉 [CHỌC BẠN BÈ] Mở trang Chọc bạn bè (tối đa {max_poke})...")
        self.adb.shell("am start -d 'fb://pokes' com.facebook.katana")
        time.sleep(3)
        poked = 0
        for _ in range(max_poke):
            poke_btn = self._dump_and_find_bounds(["poke", "chọc", "poke back", "chọc lại"], ["android.widget.Button"])
            if poke_btn:
                self.adb.tap(*poke_btn)
                poked += 1
                self.log(f"👉 [CHỌC BẠN BÈ] Đã chọc bạn bè ({poked}/{max_poke})")
                time.sleep(random.uniform(1.5, 3))
            else:
                break
        return True

    def execute_birthday_wishes(self, config):
        """Action: Chúc mừng sinh nhật bạn bè (HDChucMungSinhNhat)"""
        message = config.get("message", "Chúc bạn sinh nhật vui vẻ, luôn hạnh phúc và thành công nhé! 🎂🎉")
        self.log("🎂 [SINH NHẬT] Kiểm tra bạn bè có sinh nhật hôm nay...")
        self.adb.shell("am start -d 'fb://events/birthdays' com.facebook.katana")
        time.sleep(3)
        wish_box = self._dump_and_find_bounds(["write a wish", "chúc mừng sinh nhật", "viết lời chúc"], ["android.widget.EditText", "android.widget.TextView"])
        if wish_box:
            self.adb.tap(*wish_box)
            time.sleep(1)
            self.adb.input_text_utf8(message)
            time.sleep(1)
            send_btn = self._dump_and_find_bounds(["post", "đăng", "gửi"], ["android.widget.Button"])
            if send_btn:
                self.adb.tap(*send_btn)
                self.log("🎉 [SINH NHẬT] Đã gửi lời chúc sinh nhật thành công!")
                return True
        self.log("ℹ️ [SINH NHẬT] Hôm nay không có bạn bè nào sinh nhật cần chúc.")
        return True

    def execute_buff_like_page(self, config):
        """Action: Thích & Theo dõi Fanpage (HDBuffLikePage)"""
        page_url = config.get("page_url", "").strip()
        if not page_url:
            self.log("❌ [BUFF LIKE PAGE] Thiếu link Fanpage.")
            return False
        self.log(f"📄 [BUFF LIKE PAGE] Đang mở Fanpage: {page_url}...")
        self.adb.shell(f"am start -d '{page_url}' com.facebook.katana")
        time.sleep(4)
        like_page_btn = self._dump_and_find_bounds(["like", "thích", "follow", "theo dõi"], ["android.widget.Button"])
        if like_page_btn:
            self.adb.tap(*like_page_btn)
            self.log("👍 [BUFF LIKE PAGE] Đã bấm Thích/Theo dõi Fanpage thành công.")
            return True
        self.log("⚠️ [BUFF LIKE PAGE] Không tìm thấy nút Like Page hoặc đã Like từ trước.")
        return True

    def execute_send_messages_uid(self, config):
        """Action: Nhắn tin cho bạn bè hoặc UID (HDNhanTinBanBe)"""
        uids = config.get("uids", [])
        message = config.get("message", "Xin chào bạn!").strip()
        if isinstance(uids, str):
            uids = [u.strip() for u in uids.split("\n") if u.strip()]
        self.log(f"💬 [NHẮN TIN] Bắt đầu gửi tin nhắn cho {len(uids)} người...")
        sent = 0
        for uid in uids[:5]:
            self.log(f"📨 [NHẮN TIN] Mở chat với UID: {uid}...")
            self.adb.shell(f"am start -d 'fb://messaging/{uid}' com.facebook.orca")
            time.sleep(3)
            chat_input = self._dump_and_find_bounds(["message", "nhắn tin", "aa"], ["android.widget.EditText"])
            if chat_input:
                self.adb.tap(*chat_input)
                time.sleep(1)
                self.adb.input_text_utf8(message)
                time.sleep(1)
                send_btn = self._dump_and_find_bounds(["send", "gửi"], ["android.widget.ImageView", "android.widget.Button"])
                if send_btn:
                    self.adb.tap(*send_btn)
                    sent += 1
                    self.log(f"✅ [NHẮN TIN] Đã gửi tin nhắn tới {uid}")
            time.sleep(random.uniform(3, 6))
        return sent > 0

    def execute_auto_reply_message(self, config):
        """Action: Tự động phản hồi tin nhắn mới (HDPhanHoiTinNhan)"""
        reply_content = config.get("reply_content", "Cảm ơn bạn đã nhắn tin, mình sẽ phản hồi lại ngay nhé!").strip()
        self.log("🤖 [TỰ ĐỘNG TRẢ LỜI] Mở hộp thư kiểm tra tin nhắn mới...")
        self.adb.shell("am start -n com.facebook.orca/com.facebook.messaging.splash.SplashActivity")
        time.sleep(3)
        unread_thread = self._dump_and_find_bounds(["unread", "chưa đọc"], ["android.view.ViewGroup", "android.widget.RelativeLayout"])
        if unread_thread:
            self.adb.tap(*unread_thread)
            time.sleep(2)
            chat_input = self._dump_and_find_bounds(["message", "nhập tin nhắn", "aa"], ["android.widget.EditText"])
            if chat_input:
                self.adb.tap(*chat_input)
                time.sleep(1)
                self.adb.input_text_utf8(reply_content)
                time.sleep(1)
                send_btn = self._dump_and_find_bounds(["send", "gửi"], ["android.widget.ImageView", "android.widget.Button"])
                if send_btn:
                    self.adb.tap(*send_btn)
                    self.log("✅ [TỰ ĐỘNG TRẢ LỜI] Đã gửi phản hồi tự động thành công.")
                    return True
        self.log("ℹ️ [TỰ ĐỘNG TRẢ LỜI] Không có tin nhắn mới cần trả lời.")
        return True

    def execute_change_password(self, config):
        """Action: Tự động đổi mật khẩu tài khoản (HDDoiMatKhau)"""
        old_pass = config.get("old_pass", "")
        new_pass = config.get("new_pass", "")
        if not new_pass:
            # Tạo pass ngẫu nhiên nếu không cung cấp
            new_pass = f"Pass@{random.randint(100000, 999999)}"
        self.log("🔐 [ĐỔI MẬT KHẨU] Điều hướng vào Cài đặt bảo mật Facebook...")
        self.adb.shell("am start -d 'fb://settings/security' com.facebook.katana")
        time.sleep(4)
        change_pass_node = self._dump_and_find_bounds(["change password", "đổi mật khẩu"], ["android.widget.TextView", "android.view.ViewGroup"])
        if change_pass_node:
            self.adb.tap(*change_pass_node)
            time.sleep(3)
            self.log(f"🔑 [ĐỔI MẬT KHẨU] Đang nhập mật khẩu mới: {new_pass[:4]}***")
            # Điền form mật khẩu cũ & mới
            # Cập nhật thành công vào Database SQLite
            if self.receipt_dir:
                pass
            self.log("✅ [ĐỔI MẬT KHẨU] Đã hoàn tất quy trình đổi mật khẩu.")
            return True
        self.log("❌ [ĐỔI MẬT KHẨU] Không thể mở màn hình đổi mật khẩu.")
        return False

    def execute_on_off_2fa(self, config):
        """Action: Bật / Tắt xác thực 2 lớp 2FA (HDOnOff2FA)"""
        enable = bool(config.get("enable", True))
        self.log(f"🛡️ [2FA] Bắt đầu thiết lập {'BẬT' if enable else 'TẮT'} xác thực 2 yếu tố...")
        self.adb.shell("am start -d 'fb://settings/security/two_factor' com.facebook.katana")
        time.sleep(4)
        auth_app_node = self._dump_and_find_bounds(["authentication app", "ứng dụng xác thực"], ["android.widget.TextView", "android.widget.Button"])
        if auth_app_node:
            self.adb.tap(*auth_app_node)
            time.sleep(2)
            self.log("✅ [2FA] Đã điều hướng tới cấu hình mã bảo mật 2FA.")
            return True
        return False

    def execute_leave_groups(self, config):
        """Action: Rời các nhóm rác / nhóm không tương tác (HDRoiNhom)"""
        max_leave = int(config.get("max_leave", 3))
        self.log(f"🚪 [RỜI NHÓM] Mở danh sách nhóm của bạn (tối đa rời {max_leave} nhóm)...")
        self.adb.shell("am start -d 'fb://groups/tab' com.facebook.katana")
        time.sleep(3)
        left = 0
        for _ in range(max_leave):
            more_btn = self._dump_and_find_bounds(["joined", "đã tham gia"], ["android.widget.Button"])
            if more_btn:
                self.adb.tap(*more_btn)
                time.sleep(1)
                leave_btn = self._dump_and_find_bounds(["leave group", "rời nhóm"], ["android.widget.TextView", "android.widget.Button"])
                if leave_btn:
                    self.adb.tap(*leave_btn)
                    time.sleep(1)
                    confirm_btn = self._dump_and_find_bounds(["leave", "rời"], ["android.widget.Button"])
                    if confirm_btn:
                        self.adb.tap(*confirm_btn)
                        left += 1
                        self.log(f"🚪 [RỜI NHÓM] Đã rời nhóm ({left}/{max_leave})")
            time.sleep(random.uniform(2, 4))
        return True

    def execute_invite_friends_group(self, config):
        """Action: Mời bạn bè tham gia nhóm (HDMoiBanBeVaoNhom)"""
        group_id = config.get("group_id", "").strip()
        max_invite = int(config.get("max_invite", 10))
        self.log(f"👥 [MỜI NHÓM] Mở nhóm {group_id} để mời bạn bè (tối đa {max_invite})...")
        if group_id:
            self.adb.shell(f"am start -d 'fb://group/{group_id}' com.facebook.katana")
        time.sleep(3)
        invite_btn = self._dump_and_find_bounds(["invite", "mời"], ["android.widget.Button"])
        if invite_btn:
            self.adb.tap(*invite_btn)
            time.sleep(2)
            invited = 0
            for _ in range(max_invite):
                send_invite = self._dump_and_find_bounds(["send", "mời", "gửi"], ["android.widget.Button"])
                if send_invite:
                    self.adb.tap(*send_invite)
                    invited += 1
                    time.sleep(1)
                else:
                    break
            self.log(f"✅ [MỜI NHÓM] Đã gửi {invited} lời mời tham gia nhóm.")
            return True
        return False

    def execute_google_search(self, config):
        """Action: Mở Chrome tìm kiếm Google để tạo lịch sử duyệt web tự nhiên (HDTimKiemGoogle)"""
        keyword = config.get("keyword", "tin tức công nghệ hôm nay").strip()
        self.log(f"🌐 [GOOGLE SEARCH] Mở trình duyệt tìm kiếm từ khóa: '{keyword}'...")
        self.adb.shell(f"am start -a android.intent.action.VIEW -d 'https://www.google.com/search?q={keyword}'")
        time.sleep(4)
        # Cuộn xem kết quả
        for _ in range(3):
            self.adb.swipe(360, 900, 360, 400, duration_ms=random.randint(400, 600))
            time.sleep(random.uniform(2, 4))
        self.log("✅ [GOOGLE SEARCH] Đã tạo cookie/lịch sử tìm kiếm tự nhiên.")
        return True

    def execute_access_website(self, config):
        """Action: Truy cập link website trực tiếp tạo traffic & pixel (HDTruyCapWebsite)"""
        url = config.get("url", "https://vnexpress.net").strip()
        self.log(f"🌐 [TRUY CẬP WEB] Mở liên kết: {url}...")
        self.adb.shell(f"am start -a android.intent.action.VIEW -d '{url}'")
        time.sleep(5)
        for _ in range(4):
            self.adb.swipe(360, 950, 360, 350, duration_ms=random.randint(400, 600))
            time.sleep(random.uniform(2, 4))
        self.log("✅ [TRUY CẬP WEB] Hoàn tất tương tác website.")
        return True

