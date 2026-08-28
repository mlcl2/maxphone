import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QSpinBox,
    QFormLayout, QLabel, QCheckBox, QDialogButtonBox, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QComboBox
)

class ActionConfigDialog(QDialog):
    """
    Form cấu hình chi tiết thông số cho 1 hành động (Lướt Newsfeed, Xem Reel, Kết bạn, Tham gia nhóm, Seeding)
    """
    def __init__(self, parent, action_type, action_name, config_dict=None):
        super().__init__(parent)
        self.setWindowTitle(f"⚙️ Cấu Hình Hành Động: {action_name}")
        self.resize(550, 520)
        self.action_type = action_type
        self.config_dict = config_dict or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # -------------------------------------------------------------
        # 1. LƯỚT NEWSFEED
        # -------------------------------------------------------------
        if action_type == "newsfeed":
            # Thời gian lướt
            self.spin_time_from = QSpinBox(); self.spin_time_from.setRange(5, 1800); self.spin_time_from.setValue(self.config_dict.get("time_from", 30))
            self.spin_time_to = QSpinBox(); self.spin_time_to.setRange(5, 1800); self.spin_time_to.setValue(self.config_dict.get("time_to", 60))
            box_time = QHBoxLayout()
            box_time.addWidget(self.spin_time_from); box_time.addWidget(QLabel("đến")); box_time.addWidget(self.spin_time_to); box_time.addWidget(QLabel("giây"))
            form.addRow("Thời gian lướt Newsfeed:", box_time)

            # Delay vuốt
            self.spin_delay_from = QSpinBox(); self.spin_delay_from.setRange(1, 60); self.spin_delay_from.setValue(self.config_dict.get("delay_from", 2))
            self.spin_delay_to = QSpinBox(); self.spin_delay_to.setRange(1, 60); self.spin_delay_to.setValue(self.config_dict.get("delay_to", 5))
            box_delay = QHBoxLayout()
            box_delay.addWidget(self.spin_delay_from); box_delay.addWidget(QLabel("đến")); box_delay.addWidget(self.spin_delay_to); box_delay.addWidget(QLabel("giây"))
            form.addRow("Delay giữa các lần vuốt:", box_delay)

            # Cấu hình Like (% & Tối đa)
            self.cb_like = QCheckBox("Tự động Like / Thả Tim bài viết")
            self.cb_like.setChecked(self.config_dict.get("like", True))
            self.spin_like_percent = QSpinBox(); self.spin_like_percent.setRange(1, 100); self.spin_like_percent.setValue(self.config_dict.get("like_percent", 50))
            self.spin_max_like = QSpinBox(); self.spin_max_like.setRange(1, 100); self.spin_max_like.setValue(self.config_dict.get("max_like", 10))
            
            box_like = QHBoxLayout()
            box_like.addWidget(self.cb_like)
            box_like.addWidget(QLabel("Tỷ lệ:"))
            box_like.addWidget(self.spin_like_percent)
            box_like.addWidget(QLabel("% bài | Tối đa:"))
            box_like.addWidget(self.spin_max_like)
            box_like.addWidget(QLabel("like"))
            form.addRow(box_like)

            # Cấu hình Comment (% & Tối đa)
            self.cb_comment = QCheckBox("Tự động Bình Luận bài viết")
            self.cb_comment.setChecked(self.config_dict.get("comment", False))
            self.spin_comment_percent = QSpinBox(); self.spin_comment_percent.setRange(1, 100); self.spin_comment_percent.setValue(self.config_dict.get("comment_percent", 20))
            self.spin_max_comment = QSpinBox(); self.spin_max_comment.setRange(1, 100); self.spin_max_comment.setValue(self.config_dict.get("max_comment", 5))
            
            box_cmt = QHBoxLayout()
            box_cmt.addWidget(self.cb_comment)
            box_cmt.addWidget(QLabel("Tỷ lệ:"))
            box_cmt.addWidget(self.spin_comment_percent)
            box_cmt.addWidget(QLabel("% bài | Tối đa:"))
            box_cmt.addWidget(self.spin_max_comment)
            box_cmt.addWidget(QLabel("cmt"))
            form.addRow(box_cmt)

            self.txt_comment_content = QTextEdit()
            self.txt_comment_content.setPlaceholderText("Nhập nội dung comment (mỗi dòng 1 nội dung)...")
            self.txt_comment_content.setText(self.config_dict.get("comment_text", "Tuyệt vời quá!\nQuan tâm!\nInbox mình nhé"))
            form.addRow("Nội dung comment:", self.txt_comment_content)

        # -------------------------------------------------------------
        # 2. XEM REELS
        # -------------------------------------------------------------
        elif action_type == "reel":
            # Tổng thời gian xem Reels
            self.spin_time_from = QSpinBox(); self.spin_time_from.setRange(10, 1800); self.spin_time_from.setValue(self.config_dict.get("time_from", 60))
            self.spin_time_to = QSpinBox(); self.spin_time_to.setRange(10, 1800); self.spin_time_to.setValue(self.config_dict.get("time_to", 120))
            box_time = QHBoxLayout()
            box_time.addWidget(self.spin_time_from); box_time.addWidget(QLabel("đến")); box_time.addWidget(self.spin_time_to); box_time.addWidget(QLabel("giây"))
            form.addRow("Tổng thời gian xem Reels:", box_time)

            # Thời gian xem mỗi Video Reel
            self.spin_vid_time_from = QSpinBox(); self.spin_vid_time_from.setRange(2, 300); self.spin_vid_time_from.setValue(self.config_dict.get("vid_time_from", 5))
            self.spin_vid_time_to = QSpinBox(); self.spin_vid_time_to.setRange(2, 300); self.spin_vid_time_to.setValue(self.config_dict.get("vid_time_to", 15))
            box_vid_time = QHBoxLayout()
            box_vid_time.addWidget(self.spin_vid_time_from); box_vid_time.addWidget(QLabel("đến")); box_vid_time.addWidget(self.spin_vid_time_to); box_vid_time.addWidget(QLabel("giây"))
            form.addRow("Thời gian xem mỗi Video (sau đó vuốt):", box_vid_time)

            # Cấu hình Thả tim Reel (%)
            self.cb_like = QCheckBox("Tự động Thả tim Video Reel")
            self.cb_like.setChecked(self.config_dict.get("like", True))
            self.spin_like_percent = QSpinBox(); self.spin_like_percent.setRange(1, 100); self.spin_like_percent.setValue(self.config_dict.get("like_percent", 30))
            
            box_like = QHBoxLayout()
            box_like.addWidget(self.cb_like)
            box_like.addWidget(QLabel("Tỷ lệ thả tim:"))
            box_like.addWidget(self.spin_like_percent)
            box_like.addWidget(QLabel("% số Reel"))
            form.addRow(box_like)

        # -------------------------------------------------------------
        # 3. XEM STORY
        # -------------------------------------------------------------
        elif action_type == "story":
            self.spin_count_from = QSpinBox(); self.spin_count_from.setRange(1, 100); self.spin_count_from.setValue(self.config_dict.get("count_from", self.config_dict.get("nudSoLuongFrom", 1)))
            self.spin_count_to = QSpinBox(); self.spin_count_to.setRange(1, 100); self.spin_count_to.setValue(self.config_dict.get("count_to", self.config_dict.get("nudSoLuongTo", 3)))
            box_count = QHBoxLayout(); box_count.addWidget(self.spin_count_from); box_count.addWidget(QLabel("đến")); box_count.addWidget(self.spin_count_to)
            form.addRow("Số Story xem:", box_count)
            self.spin_watch_from = QSpinBox(); self.spin_watch_from.setRange(1, 60); self.spin_watch_from.setValue(self.config_dict.get("watch_from", self.config_dict.get("nudTimeFrom", 5)))
            self.spin_watch_to = QSpinBox(); self.spin_watch_to.setRange(1, 60); self.spin_watch_to.setValue(self.config_dict.get("watch_to", self.config_dict.get("nudTimeTo", 8)))
            box_watch = QHBoxLayout(); box_watch.addWidget(self.spin_watch_from); box_watch.addWidget(QLabel("đến")); box_watch.addWidget(self.spin_watch_to); box_watch.addWidget(QLabel("giây"))
            form.addRow("Thời gian mỗi Story:", box_watch)

        # -------------------------------------------------------------
        # 4. KẾT BẠN (Gợi ý, UID/Link, Từ khóa)
        # -------------------------------------------------------------
        elif action_type == "add_friends":
            self.cmb_friend_type = QComboBox()
            self.cmb_friend_type.addItem("Kết bạn theo gợi ý", "suggestions")
            self.cmb_friend_type.addItem("Kết bạn theo tệp UID", "uid_file")
            saved_type = str(self.config_dict.get("type", "suggestions")).lower()
            self.cmb_friend_type.setCurrentIndex(1 if saved_type in ("uid", "uid_file", "tệp uid", "tep uid") else 0)
            form.addRow("Chế độ kết bạn:", self.cmb_friend_type)

            self.txt_uid_file = QLineEdit(str(self.config_dict.get("uid_file", self.config_dict.get("txtPathUid", ""))))
            self.btn_uid_file = QPushButton("Chọn tệp UID…")
            self.btn_uid_file.clicked.connect(self._choose_uid_file)
            uid_file_row = QHBoxLayout(); uid_file_row.addWidget(self.txt_uid_file); uid_file_row.addWidget(self.btn_uid_file)
            form.addRow("Tệp UID (.txt):", uid_file_row)

            self.spin_count_from = QSpinBox(); self.spin_count_from.setRange(1, 100); self.spin_count_from.setValue(self.config_dict.get("count_from", 2))
            self.spin_count_to = QSpinBox(); self.spin_count_to.setRange(1, 100); self.spin_count_to.setValue(self.config_dict.get("count_to", 5))
            box_count = QHBoxLayout()
            box_count.addWidget(self.spin_count_from); box_count.addWidget(QLabel("đến")); box_count.addWidget(self.spin_count_to); box_count.addWidget(QLabel("bạn"))
            form.addRow("Số lượng kết bạn:", box_count)

            self.txt_list = QTextEdit()
            self.txt_list.setPlaceholderText("Nhập danh sách UID / Link / Từ khóa (mỗi dòng 1 item)...")
            self.txt_list.setText(self.config_dict.get("target_list", self.config_dict.get("txtUid", "")))
            form.addRow("Danh sách UID (mỗi dòng một UID):", self.txt_list)
            self.cb_remove_used_uid = QCheckBox("Tự động xóa UID đã xử lý thành công")
            self.cb_remove_used_uid.setChecked(bool(self.config_dict.get("remove_used_uid", self.config_dict.get("ckbTuDongXoaUid", False))))
            self.cb_remove_used_uid.setEnabled(False)
            self.cb_remove_used_uid.setToolTip("Tạm khóa: chưa có cơ chế ghi lại scenario/file UID atomically sau postcondition.")
            form.addRow(self.cb_remove_used_uid)
            self.spin_delay_from = QSpinBox(); self.spin_delay_from.setRange(0, 999999); self.spin_delay_from.setValue(self.config_dict.get("delay_from", self.config_dict.get("nudDelayFrom", 3)))
            self.spin_delay_to = QSpinBox(); self.spin_delay_to.setRange(0, 999999); self.spin_delay_to.setValue(self.config_dict.get("delay_to", self.config_dict.get("nudDelayTo", 5)))
            box_delay = QHBoxLayout(); box_delay.addWidget(self.spin_delay_from); box_delay.addWidget(QLabel("đến")); box_delay.addWidget(self.spin_delay_to)
            form.addRow("Delay giữa lời mời:", box_delay)
            self.spin_delay_check = QSpinBox(); self.spin_delay_check.setRange(0, 999999); self.spin_delay_check.setValue(self.config_dict.get("delay_check", self.config_dict.get("nudDelayCheck", 10)))
            form.addRow("Delay kiểm tra:", self.spin_delay_check)
            self.cb_accented_name_only = QCheckBox("Chỉ kết bạn tên có dấu"); self.cb_accented_name_only.setChecked(self.config_dict.get("accented_name_only", self.config_dict.get("ckbChiKetBanTenCoDau", False))); form.addRow(self.cb_accented_name_only)
            self.cb_mutual_only = QCheckBox("Chỉ kết bạn người có bạn chung"); self.cb_mutual_only.setChecked(self.config_dict.get("mutual_only", self.config_dict.get("ckbOnlyAddFriendWithMutualFriends", False))); form.addRow(self.cb_mutual_only)
            self.spin_warning_times = QSpinBox(); self.spin_warning_times.setRange(1, 999999); self.spin_warning_times.setValue(self.config_dict.get("warning_times", self.config_dict.get("nudTimesWarning", 3)))
            form.addRow("Số lần cảnh báo tối đa:", self.spin_warning_times)

        # -------------------------------------------------------------
        # 4. THAM GIA NHÓM (UID/Link, Từ khóa, Trả lời tự động)
        # -------------------------------------------------------------
        elif action_type == "join_groups":
            self.spin_count_from = QSpinBox(); self.spin_count_from.setRange(1, 50); self.spin_count_from.setValue(self.config_dict.get("count_from", 1))
            self.spin_count_to = QSpinBox(); self.spin_count_to.setRange(1, 50); self.spin_count_to.setValue(self.config_dict.get("count_to", 3))
            box_count = QHBoxLayout()
            box_count.addWidget(self.spin_count_from); box_count.addWidget(QLabel("đến")); box_count.addWidget(self.spin_count_to); box_count.addWidget(QLabel("nhóm"))
            form.addRow("Số lượng nhóm tham gia:", box_count)
            self.spin_delay_from = QSpinBox(); self.spin_delay_from.setRange(0, 999999); self.spin_delay_from.setValue(self.config_dict.get("delay_from", self.config_dict.get("nudDelayFrom", 3)))
            self.spin_delay_to = QSpinBox(); self.spin_delay_to.setRange(0, 999999); self.spin_delay_to.setValue(self.config_dict.get("delay_to", self.config_dict.get("nudDelayTo", 5)))
            box_delay = QHBoxLayout(); box_delay.addWidget(self.spin_delay_from); box_delay.addWidget(QLabel("đến")); box_delay.addWidget(self.spin_delay_to)
            form.addRow("Delay giữa các nhóm:", box_delay)

            self.cb_auto_agree = QCheckBox("Tự động Tick Đồng ý quy định nhóm")
            self.cb_auto_agree.setChecked(self.config_dict.get("auto_agree", True))
            form.addRow(self.cb_auto_agree)

            self.txt_answers = QTextEdit()
            self.txt_answers.setPlaceholderText("Cài đặt câu trả lời tự động nếu có câu hỏi duyệt (mỗi dòng 1 câu)...")
            self.txt_answers.setText(self.config_dict.get("answers", "Tôi đồng ý quy định nhóm\nOK\nĐã hiểu"))
            form.addRow("Câu trả lời tự động kiểm duyệt:", self.txt_answers)

            self.txt_group_list = QTextEdit()
            self.txt_group_list.setPlaceholderText("Nhập danh sách UID Nhóm / Link / Từ khóa (mỗi dòng 1 item)...")
            self.txt_group_list.setText(self.config_dict.get("group_list", ""))
            form.addRow("Danh sách UID/Link/Từ khóa Nhóm:", self.txt_group_list)

        # -------------------------------------------------------------
        # 5. SEEDING BÀI VIẾT (Link, Cảm xúc, Comment, Ảnh MD5/Lật)
        # -------------------------------------------------------------
        elif action_type == "seeding":
            self.txt_posts = QTextEdit()
            self.txt_posts.setPlaceholderText("Dán danh sách Link bài viết cần Seeding (mỗi dòng 1 link)...")
            self.txt_posts.setText(self.config_dict.get("post_links", ""))
            form.addRow("Danh sách Link bài viết:", self.txt_posts)

            # Checkbox các Cảm xúc Thả Tim / Reaction
            self.cb_emoji_like = QCheckBox("👍 Like")
            self.cb_emoji_love = QCheckBox("❤️ Love (Thả tim)")
            self.cb_emoji_care = QCheckBox("🥰 Care (Thương thương)")
            self.cb_emoji_haha = QCheckBox("😆 Haha")
            self.cb_emoji_wow = QCheckBox("😲 Wow")
            self.cb_emoji_sad = QCheckBox("😢 Sad (Buồn)")
            self.cb_emoji_angry = QCheckBox("😡 Angry (Phẫn nộ)")

            saved_emojis = self.config_dict.get("emojis", ["👍 Like", "❤️ Love (Thả tim)"])
            self.cb_emoji_like.setChecked("👍 Like" in saved_emojis or "Like" in saved_emojis)
            self.cb_emoji_love.setChecked("❤️ Love (Thả tim)" in saved_emojis or "Love" in saved_emojis)
            self.cb_emoji_care.setChecked("🥰 Care (Thương thương)" in saved_emojis or "Care" in saved_emojis)
            self.cb_emoji_haha.setChecked("😆 Haha" in saved_emojis or "Haha" in saved_emojis)
            self.cb_emoji_wow.setChecked("😲 Wow" in saved_emojis or "Wow" in saved_emojis)
            self.cb_emoji_sad.setChecked("😢 Sad (Buồn)" in saved_emojis or "Sad" in saved_emojis)
            self.cb_emoji_angry.setChecked("😡 Angry (Phẫn nộ)" in saved_emojis or "Angry" in saved_emojis)

            box_emojis1 = QHBoxLayout()
            box_emojis1.addWidget(self.cb_emoji_like)
            box_emojis1.addWidget(self.cb_emoji_love)
            box_emojis1.addWidget(self.cb_emoji_care)
            box_emojis1.addWidget(self.cb_emoji_haha)

            box_emojis2 = QHBoxLayout()
            box_emojis2.addWidget(self.cb_emoji_wow)
            box_emojis2.addWidget(self.cb_emoji_sad)
            box_emojis2.addWidget(self.cb_emoji_angry)

            box_emojis_all = QVBoxLayout()
            box_emojis_all.addLayout(box_emojis1)
            box_emojis_all.addLayout(box_emojis2)

            form.addRow("Cảm xúc thả (Tick chọn):", box_emojis_all)

            self.txt_comments = QTextEdit()
            self.txt_comments.setPlaceholderText("Nhập danh sách comment (mỗi dòng 1 comment)...")
            self.txt_comments.setText(self.config_dict.get("comment_text", "Sản phẩm dùng tốt lắm\nIb giá bạn ơi\nShop uy tín ghê"))
            form.addRow("Danh sách Comment:", self.txt_comments)

            self.cb_allow_dup = QCheckBox("Cho phép Comment trùng lặp khi hết danh sách")
            self.cb_allow_dup.setChecked(self.config_dict.get("allow_dup", False))
            form.addRow(self.cb_allow_dup)

            self.txt_img_folder = QLineEdit(self.config_dict.get("img_folder", ""))
            form.addRow("Thư mục Ảnh đính kèm (nếu có):", self.txt_img_folder)

            self.cb_change_md5 = QCheckBox("Tự động Thay đổi MD5 của Ảnh đính kèm")
            self.cb_change_md5.setChecked(self.config_dict.get("change_md5", True))

            self.cb_flip_img = QCheckBox("Tự động Lật ảnh (Flip image) tránh trùng lặp Facebook")
            self.cb_flip_img.setChecked(self.config_dict.get("flip_img", True))

            box_img_opt = QHBoxLayout()
            box_img_opt.addWidget(self.cb_change_md5)
            box_img_opt.addWidget(self.cb_flip_img)
            form.addRow("Xử lý Ảnh lách FB:", box_img_opt)

        elif action_type in ("notifications", "post_wall", "post_group"):
            value = lambda key, legacy, default: self.config_dict.get(key, self.config_dict.get(legacy, default))

            def spin(name, key, legacy, default, maximum=100):
                widget = QSpinBox(); widget.setRange(0, maximum); widget.setValue(value(key, legacy, default))
                setattr(self, name, widget); return widget

            def check(name, label, key, legacy, default=False):
                widget = QCheckBox(label); widget.setChecked(bool(value(key, legacy, default)))
                setattr(self, name, widget); form.addRow(widget); return widget

            def line(name, label, key, legacy, default=""):
                widget = QLineEdit(str(value(key, legacy, default)))
                setattr(self, name, widget); form.addRow(label, widget); return widget

            def text(name, label, key, legacy, default=""):
                widget = QTextEdit(); widget.setPlainText(str(value(key, legacy, default)))
                setattr(self, name, widget); form.addRow(label, widget); return widget

            form.addRow("Số lượng từ:", spin("spin_count_from", "count_from", "nudSoLuongFrom", 1))
            form.addRow("Số lượng đến:", spin("spin_count_to", "count_to", "nudSoLuongTo", 1))

            if action_type == "notifications":
                form.addRow("Delay từ (giây):", spin("spin_delay_from", "delay_from", "nudDelayFrom", 1, 3600))
                form.addRow("Delay đến (giây):", spin("spin_delay_to", "delay_to", "nudDelayTo", 1, 3600))
                check("cb_delete_spam_notifications", "Xóa thông báo spam sau khi đọc",
                      "delete_spam_notifications", "ckbXoaThongBaoSpam")
            else:
                form.addRow("Khoảng cách từ (giây):", spin("spin_interval_from", "interval_from", "nudKhoangCachFrom", 1, 86400))
                form.addRow("Khoảng cách đến (giây):", spin("spin_interval_to", "interval_to", "nudKhoangCachTo", 1, 86400))

                if action_type == "post_group":
                    form.addRow("Kiểu chọn nhóm (0/1/2):", spin("spin_group_type", "group_type", "typeNhom", 0, 2))
                    check("cb_only_unmoderated_groups", "Chỉ nhóm không kiểm duyệt", "only_unmoderated_groups", "ckbChiShareNhomKKD")
                    check("cb_prioritize_large_groups", "Ưu tiên nhóm nhiều thành viên", "prioritize_large_groups", "ckbUuTienShareNhomNhieuThanhVien")
                    check("cb_backup_group_list", "Backup danh sách nhóm", "backup_group_list", "ckbBackupDanhSachNhom")
                    check("cb_avoid_duplicate_groups", "Không đăng trùng nhóm", "avoid_duplicate_groups", "ckbKhongShareTrungNhom")
                    check("cb_only_listed_groups", "Chỉ nhóm thuộc danh sách", "only_listed_groups", "ckbChiShareNhomThuocDanhSach")
                    text("txt_custom_group_list", "Danh sách nhóm — mỗi dòng là link hoặc UID:", "custom_group_list", "lstNhomTuNhap")
                    line("txt_group_id", "Link/UID nhóm chỉ định (tương thích cũ):", "group_id", "txtIdNhomChiDinh")
                    check("cb_auto_remove_group_id", "Tự động xóa UID đã dùng", "auto_remove_group_id", "ckbTuDongXoaUid")
                    line("txt_new_group_name", "Tên nhóm mới:", "new_group_name", "txtTenNhom")

                check("cb_use_text", "Đăng văn bản", "use_text", "ckbVanBan", True)
                check("cb_use_background", "Dùng nền màu cho bài text", "use_background", "ckbUseBackground")
                check("cb_delete_used_content", "Xóa nội dung đã dùng", "delete_used_content", "ckbXoaNguyenLieuDaDung")
                text("txt_post", "Nội dung:", "text", "txtNoiDung")
                form.addRow("Kiểu ngăn cách (0/1):", spin("spin_separator_type", "separator_type", "typeNganCach", 0, 1))
                check("cb_use_images", "Đăng kèm ảnh", "use_images", "ckbAnh")
                self.cb_use_images.toggled.connect(self._sync_post_mode_controls)
                self.cb_use_text.toggled.connect(self._sync_post_mode_controls)
                self._sync_post_mode_controls()
                self.txt_image_path = QLineEdit(str(value("image_path", "txtPathAnh", "")))
                self.btn_image_path = QPushButton("Chọn thư mục…")
                self.btn_image_path.clicked.connect(self._choose_image_folder)
                image_path_row = QHBoxLayout(); image_path_row.addWidget(self.txt_image_path); image_path_row.addWidget(self.btn_image_path)
                form.addRow("Thư mục ảnh:", image_path_row)
                form.addRow("Số ảnh từ:", spin("spin_image_count_from", "image_count_from", "nudSoLuongAnhFrom", 1))
                form.addRow("Số ảnh đến:", spin("spin_image_count_to", "image_count_to", "nudSoLuongAnhTo", 1))
                check("cb_post_link", "Đăng link", "post_link", "ckbDangLink")
                text("txt_share_links", "Danh sách link:", "share_links", "txtLinkShare")
                check("cb_remove_link_preview", "Xóa link sau thumbnail", "remove_link_preview", "ckbXoaLink")

                if action_type == "post_group":
                    check("cb_use_event", "Bật nội dung event", "use_event", "ckbEvent")
                    text("txt_event", "Nội dung event:", "event_text", "txtEvent")
                    check("cb_export_post_links", "Xuất link bài viết", "export_post_links", "ckbXuatLinkBaiViet")
        # -------------------------------------------------------------
        # 5. CÁC ACTIONS MỞ RỘNG (WATCH, CANCEL, UNFRIEND, POKE, BIRTHDAY, BUFF PAGE, MSG, 2FA, DELAY...)
        # -------------------------------------------------------------
        elif action_type == "watch":
            self.spin_time_from = QSpinBox(); self.spin_time_from.setRange(5, 1800); self.spin_time_from.setValue(self.config_dict.get("time_from", 15))
            self.spin_time_to = QSpinBox(); self.spin_time_to.setRange(5, 1800); self.spin_time_to.setValue(self.config_dict.get("time_to", 30))
            box_time = QHBoxLayout(); box_time.addWidget(self.spin_time_from); box_time.addWidget(QLabel("đến")); box_time.addWidget(self.spin_time_to); box_time.addWidget(QLabel("giây"))
            form.addRow("Thời gian xem Watch:", box_time)
            self.txt_keyword = QLineEdit(self.config_dict.get("keyword", ""))
            form.addRow("Từ khóa tìm kiếm (để trống nếu xem ngẫu nhiên):", self.txt_keyword)
            self.cb_like = QCheckBox("Tự động Like video Watch")
            self.cb_like.setChecked(self.config_dict.get("is_like", True))
            form.addRow(self.cb_like)

        elif action_type == "delay":
            self.spin_time_from = QSpinBox(); self.spin_time_from.setRange(1, 600); self.spin_time_from.setValue(self.config_dict.get("time_from", 5))
            self.spin_time_to = QSpinBox(); self.spin_time_to.setRange(1, 600); self.spin_time_to.setValue(self.config_dict.get("time_to", 10))
            box_time = QHBoxLayout(); box_time.addWidget(self.spin_time_from); box_time.addWidget(QLabel("đến")); box_time.addWidget(self.spin_time_to); box_time.addWidget(QLabel("giây"))
            form.addRow("Thời gian nghỉ ngơi:", box_time)

        elif action_type == "cancel_friend_requests":
            self.spin_count = QSpinBox(); self.spin_count.setRange(1, 100); self.spin_count.setValue(self.config_dict.get("max_cancel", 5))
            form.addRow("Số lượng lời mời hủy:", self.spin_count)

        elif action_type == "unfriend":
            self.spin_count = QSpinBox(); self.spin_count.setRange(1, 100); self.spin_count.setValue(self.config_dict.get("max_unfriend", 3))
            form.addRow("Số lượng bạn bè hủy:", self.spin_count)

        elif action_type == "poke_friends":
            self.spin_count = QSpinBox(); self.spin_count.setRange(1, 100); self.spin_count.setValue(self.config_dict.get("max_poke", 5))
            form.addRow("Số lượng bạn bè chọc:", self.spin_count)

        elif action_type == "birthday_wishes":
            self.txt_message = QTextEdit()
            self.txt_message.setText(self.config_dict.get("message", "Chúc bạn sinh nhật vui vẻ, luôn hạnh phúc và thành công nhé! 🎂🎉"))
            form.addRow("Lời chúc sinh nhật:", self.txt_message)

        elif action_type == "buff_like_page":
            self.txt_page_url = QLineEdit(self.config_dict.get("page_url", ""))
            form.addRow("Link Fanpage Facebook:", self.txt_page_url)

        elif action_type == "send_messages_uid":
            self.txt_uids = QTextEdit()
            self.txt_uids.setPlaceholderText("Dán danh sách UID hoặc link Messenger (mỗi dòng 1 người)...")
            self.txt_uids.setText(self.config_dict.get("uids", ""))
            form.addRow("Danh sách UID nhận tin:", self.txt_uids)
            self.txt_msg = QTextEdit()
            self.txt_msg.setText(self.config_dict.get("message", "Xin chào bạn!"))
            form.addRow("Nội dung tin nhắn:", self.txt_msg)

        elif action_type == "auto_reply_message":
            self.txt_reply = QTextEdit()
            self.txt_reply.setText(self.config_dict.get("reply_content", "Cảm ơn bạn đã nhắn tin, mình sẽ phản hồi lại ngay nhé!"))
            form.addRow("Nội dung phản hồi tự động:", self.txt_reply)

        elif action_type == "change_password":
            self.txt_old_pass = QLineEdit(self.config_dict.get("old_pass", ""))
            form.addRow("Mật khẩu cũ (để trống nếu tự lấy):", self.txt_old_pass)
            self.txt_new_pass = QLineEdit(self.config_dict.get("new_pass", ""))
            form.addRow("Mật khẩu mới (để trống nếu sinh ngẫu nhiên):", self.txt_new_pass)

        elif action_type == "on_off_2fa":
            self.cb_2fa = QCheckBox("Bật mã xác thực 2 yếu tố (2FA TOTP)")
            self.cb_2fa.setChecked(self.config_dict.get("enable", True))
            form.addRow(self.cb_2fa)

        elif action_type == "leave_groups":
            self.spin_count = QSpinBox(); self.spin_count.setRange(1, 100); self.spin_count.setValue(self.config_dict.get("max_leave", 3))
            form.addRow("Số lượng nhóm rời:", self.spin_count)

        elif action_type == "invite_friends_group":
            self.txt_group_id = QLineEdit(self.config_dict.get("group_id", ""))
            form.addRow("ID Nhóm / Link Nhóm:", self.txt_group_id)
            self.spin_count = QSpinBox(); self.spin_count.setRange(1, 100); self.spin_count.setValue(self.config_dict.get("max_invite", 10))
            form.addRow("Số bạn bè mời:", self.spin_count)

        elif action_type == "google_search":
            self.txt_keyword = QLineEdit(self.config_dict.get("keyword", "tin tức công nghệ hôm nay"))
            form.addRow("Từ khóa tìm kiếm:", self.txt_keyword)

        elif action_type == "access_website":
            self.txt_url = QLineEdit(self.config_dict.get("url", "https://vnexpress.net"))
            form.addRow("Đường dẫn Website:", self.txt_url)

        else:
            self.spin_time_from = QSpinBox(); self.spin_time_from.setRange(5, 600); self.spin_time_from.setValue(self.config_dict.get("time_from", 15))
            form.addRow("Thời gian thực hiện (giây):", self.spin_time_from)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _sync_post_mode_controls(self):
        if not hasattr(self, "cb_use_background") or not hasattr(self, "cb_use_images"):
            return
        allowed = self.cb_use_text.isChecked() and not self.cb_use_images.isChecked()
        if not allowed:
            self.cb_use_background.setChecked(False)
        self.cb_use_background.setEnabled(allowed)

    def _choose_uid_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp UID", self.txt_uid_file.text(), "Text files (*.txt);;All files (*)")
        if path:
            self.txt_uid_file.setText(path)

    def _choose_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh", self.txt_image_path.text())
        if folder:
            self.txt_image_path.setText(folder)

    def get_config(self):
        if self.action_type == "newsfeed":
            return {
                "time_from": self.spin_time_from.value(),
                "time_to": self.spin_time_to.value(),
                "delay_from": self.spin_delay_from.value(),
                "delay_to": self.spin_delay_to.value(),
                "like": self.cb_like.isChecked(),
                "like_percent": self.spin_like_percent.value(),
                "max_like": self.spin_max_like.value(),
                "comment": self.cb_comment.isChecked(),
                "comment_percent": self.spin_comment_percent.value(),
                "max_comment": self.spin_max_comment.value(),
                "comment_text": self.txt_comment_content.toPlainText()
            }
        elif self.action_type == "reel":
            return {
                "time_from": self.spin_time_from.value(),
                "time_to": self.spin_time_to.value(),
                "vid_time_from": self.spin_vid_time_from.value(),
                "vid_time_to": self.spin_vid_time_to.value(),
                "like": self.cb_like.isChecked(),
                "like_percent": self.spin_like_percent.value()
            }
        elif self.action_type == "story":
            return {
                "count_from": self.spin_count_from.value(),
                "count_to": self.spin_count_to.value(),
                "watch_from": self.spin_watch_from.value(),
                "watch_to": self.spin_watch_to.value(),
            }
        elif self.action_type == "add_friends":
            return {
                "type": self.cmb_friend_type.currentData(),
                "uid_file": self.txt_uid_file.text().strip(),
                "count_from": self.spin_count_from.value(),
                "count_to": self.spin_count_to.value(),
                "target_list": self.txt_list.toPlainText(),
                "txtUid": self.txt_list.toPlainText(),
                "remove_used_uid": self.cb_remove_used_uid.isChecked(),
                "ckbTuDongXoaUid": self.cb_remove_used_uid.isChecked(),
                "delay_from": self.spin_delay_from.value(),
                "delay_to": self.spin_delay_to.value(),
                "delay_check": self.spin_delay_check.value(),
                "accented_name_only": self.cb_accented_name_only.isChecked(),
                "mutual_only": self.cb_mutual_only.isChecked(),
                "warning_times": self.spin_warning_times.value(),
            }
        elif self.action_type == "join_groups":
            return {
                "count_from": self.spin_count_from.value(),
                "count_to": self.spin_count_to.value(),
                "delay_from": self.spin_delay_from.value(),
                "delay_to": self.spin_delay_to.value(),
                "auto_agree": self.cb_auto_agree.isChecked(),
                "answers": self.txt_answers.toPlainText(),
                "group_list": self.txt_group_list.toPlainText()
            }
        elif self.action_type == "seeding":
            selected_emojis = []
            if self.cb_emoji_like.isChecked(): selected_emojis.append("👍 Like")
            if self.cb_emoji_love.isChecked(): selected_emojis.append("❤️ Love")
            if self.cb_emoji_care.isChecked(): selected_emojis.append("🥰 Care")
            if self.cb_emoji_haha.isChecked(): selected_emojis.append("😆 Haha")
            if self.cb_emoji_wow.isChecked(): selected_emojis.append("😲 Wow")
            if self.cb_emoji_sad.isChecked(): selected_emojis.append("😢 Sad")
            if self.cb_emoji_angry.isChecked(): selected_emojis.append("😡 Angry")

            return {
                "post_links": self.txt_posts.toPlainText(),
                "emojis": selected_emojis,
                "comment_text": self.txt_comments.toPlainText(),
                "allow_dup": self.cb_allow_dup.isChecked(),
                "img_folder": self.txt_img_folder.text(),
                "change_md5": self.cb_change_md5.isChecked(),
                "flip_img": self.cb_flip_img.isChecked()
            }
        elif self.action_type in ("notifications", "post_wall", "post_group"):
            config = {"count_from": self.spin_count_from.value(), "count_to": self.spin_count_to.value()}
            if self.action_type == "notifications":
                config.update({
                    "delay_from": self.spin_delay_from.value(),
                    "delay_to": self.spin_delay_to.value(),
                    "delete_spam_notifications": self.cb_delete_spam_notifications.isChecked(),
                })
                return config

            config.update({
                "interval_from": self.spin_interval_from.value(),
                "interval_to": self.spin_interval_to.value(),
                "use_text": self.cb_use_text.isChecked(),
                "use_background": self.cb_use_background.isChecked(),
                "delete_used_content": self.cb_delete_used_content.isChecked(),
                "text": self.txt_post.toPlainText(),
                "separator_type": self.spin_separator_type.value(),
                "use_images": self.cb_use_images.isChecked(),
                "image_path": self.txt_image_path.text(),
                "image_count_from": self.spin_image_count_from.value(),
                "image_count_to": self.spin_image_count_to.value(),
                "post_link": self.cb_post_link.isChecked(),
                "share_links": self.txt_share_links.toPlainText(),
                "remove_link_preview": self.cb_remove_link_preview.isChecked(),
            })
            if self.action_type == "post_group":
                config.update({
                    "group_type": self.spin_group_type.value(),
                    "only_unmoderated_groups": self.cb_only_unmoderated_groups.isChecked(),
                    "prioritize_large_groups": self.cb_prioritize_large_groups.isChecked(),
                    "backup_group_list": self.cb_backup_group_list.isChecked(),
                    "avoid_duplicate_groups": self.cb_avoid_duplicate_groups.isChecked(),
                    "only_listed_groups": self.cb_only_listed_groups.isChecked(),
                    "custom_group_list": self.txt_custom_group_list.toPlainText(),
                    "group_id": self.txt_group_id.text(),
                    "auto_remove_group_id": self.cb_auto_remove_group_id.isChecked(),
                    "new_group_name": self.txt_new_group_name.text(),
                    "use_event": self.cb_use_event.isChecked(),
                    "event_text": self.txt_event.toPlainText(),
                    "export_post_links": self.cb_export_post_links.isChecked(),
                })
            return config
        elif self.action_type == "watch":
            return {
                "time_from": self.spin_time_from.value(),
                "time_to": self.spin_time_to.value(),
                "keyword": self.txt_keyword.text().strip(),
                "is_like": self.cb_like.isChecked()
            }
        elif self.action_type == "delay":
            return {
                "time_from": self.spin_time_from.value(),
                "time_to": self.spin_time_to.value()
            }
        elif self.action_type == "cancel_friend_requests":
            return {"max_cancel": self.spin_count.value()}
        elif self.action_type == "unfriend":
            return {"max_unfriend": self.spin_count.value()}
        elif self.action_type == "poke_friends":
            return {"max_poke": self.spin_count.value()}
        elif self.action_type == "birthday_wishes":
            return {"message": self.txt_message.toPlainText()}
        elif self.action_type == "buff_like_page":
            return {"page_url": self.txt_page_url.text().strip()}
        elif self.action_type == "send_messages_uid":
            return {
                "uids": self.txt_uids.toPlainText(),
                "message": self.txt_msg.toPlainText()
            }
        elif self.action_type == "auto_reply_message":
            return {"reply_content": self.txt_reply.toPlainText()}
        elif self.action_type == "change_password":
            return {
                "old_pass": self.txt_old_pass.text().strip(),
                "new_pass": self.txt_new_pass.text().strip()
            }
        elif self.action_type == "on_off_2fa":
            return {"enable": self.cb_2fa.isChecked()}
        elif self.action_type == "leave_groups":
            return {"max_leave": self.spin_count.value()}
        elif self.action_type == "invite_friends_group":
            return {
                "group_id": self.txt_group_id.text().strip(),
                "max_invite": self.spin_count.value()
            }
        elif self.action_type == "google_search":
            return {"keyword": self.txt_keyword.text().strip()}
        elif self.action_type == "access_website":
            return {"url": self.txt_url.text().strip()}
        else:
            return {"time_from": getattr(self, 'spin_time_from', QSpinBox()).value()}
