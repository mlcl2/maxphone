import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt
from src.gui.action_config_dialog import ActionConfigDialog

class ScenarioManagerDialog(QDialog):
    """
    Quản Lý Danh Sách Kịch Bản & Thao Tác Chi Tiết (Tương tự fDanhSachKichBan / fThemHanhDong của MaxPhoneFarm gốc)
    """
    def __init__(self, parent, db):
        super().__init__(parent)
        self.setWindowTitle("📜 Quản Lý Kịch Bản Tương Tác & Thao Tác Nuôi Nick")
        self.resize(850, 520)
        self.db = db
        self.current_scenario_id = None

        layout = QHBoxLayout(self)

        # -------------------------------------------------------------
        # Cột Trái: Danh Sách Kịch Bản (Thêm, Sửa, Xóa Kịch bản)
        # -------------------------------------------------------------
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("<b>📋 Danh Sách Kịch Bản:</b>"))

        self.list_scenarios = QListWidget()
        self.list_scenarios.itemClicked.connect(self.on_scenario_selected)
        left_box.addWidget(self.list_scenarios)

        scen_btn_box = QHBoxLayout()
        self.btn_add_scen = QPushButton("➕ Thêm")
        self.btn_add_scen.clicked.connect(self.add_scenario)

        self.btn_dup_scen = QPushButton("📋 Nhân Bản")
        self.btn_dup_scen.clicked.connect(self.duplicate_scenario)

        self.btn_edit_scen = QPushButton("✏️ Đổi Tên")
        self.btn_edit_scen.clicked.connect(self.rename_scenario)

        self.btn_del_scen = QPushButton("❌ Xóa")
        self.btn_del_scen.clicked.connect(self.delete_scenario)

        scen_btn_box.addWidget(self.btn_add_scen)
        scen_btn_box.addWidget(self.btn_dup_scen)
        scen_btn_box.addWidget(self.btn_edit_scen)
        scen_btn_box.addWidget(self.btn_del_scen)
        left_box.addLayout(scen_btn_box)

        layout.addLayout(left_box, 3)

        # -------------------------------------------------------------
        # Cột Phải: Các Hành Động Trong Kịch Bản Được Chọn
        # -------------------------------------------------------------
        right_box = QVBoxLayout()
        self.lbl_scen_title = QLabel("<b>⚡ Các Hành Động Trong Kịch Bản: (Chưa chọn kịch bản)</b>")
        right_box.addWidget(self.lbl_scen_title)

        self.table_actions = QTableWidget()
        self.table_actions.setColumnCount(4)
        self.table_actions.setHorizontalHeaderLabels(["ID", "Tên Hành Động", "Loại", "Cấu Hình Chi Tiết"])
        self.table_actions.setColumnHidden(0, True)
        self.table_actions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_actions.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        right_box.addWidget(self.table_actions)

        act_btn_box = QHBoxLayout()
        self.btn_add_action = QPushButton("➕ Thêm Hành Động")
        self.btn_add_action.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_add_action.clicked.connect(self.show_add_action_menu)

        self.btn_edit_action = QPushButton("⚙️ Sửa Cấu Hình")
        self.btn_edit_action.clicked.connect(self.edit_action_config)

        self.btn_move_up = QPushButton("⬆️ Lên")
        self.btn_move_up.clicked.connect(lambda: self.move_action("up"))

        self.btn_move_down = QPushButton("⬇️ Xuống")
        self.btn_move_down.clicked.connect(lambda: self.move_action("down"))

        self.btn_del_action = QPushButton("❌ Xóa")
        self.btn_del_action.clicked.connect(self.delete_action)

        act_btn_box.addWidget(self.btn_add_action)
        act_btn_box.addWidget(self.btn_edit_action)
        act_btn_box.addWidget(self.btn_move_up)
        act_btn_box.addWidget(self.btn_move_down)
        act_btn_box.addWidget(self.btn_del_action)
        right_box.addLayout(act_btn_box)

        layout.addLayout(right_box, 5)

        self.load_scenarios()

    def load_scenarios(self):
        self.list_scenarios.clear()
        scenarios = self.db.get_all_scenarios()
        for sc in scenarios:
            item = QListWidgetItem(f"📜 {sc[1]}")
            item.setData(Qt.ItemDataRole.UserRole, sc[0])
            self.list_scenarios.addItem(item)
            
        if self.list_scenarios.count() > 0:
            self.list_scenarios.setCurrentRow(0)
            self.on_scenario_selected(self.list_scenarios.item(0))

    def add_scenario(self):
        name, ok = QInputDialog.getText(self, "Thêm Kịch Bản Mới", "Nhập tên kịch bản nuôi nick mới:")
        if ok and name.strip():
            sc_id = self.db.add_scenario(name.strip())
            if sc_id:
                self.load_scenarios()
            else:
                QMessageBox.warning(self, "Lỗi", "Kịch bản này đã tồn tại!")

    def duplicate_scenario(self):
        item = self.list_scenarios.currentItem()
        if not item:
            return
        sc_id = item.data(Qt.ItemDataRole.UserRole)
        old_name = item.text().replace("📜 ", "")
        new_name, ok = QInputDialog.getText(self, "Nhân Bản Kịch Bản", "Nhập tên cho bản sao kịch bản:", text=f"{old_name} (Copy)")
        if ok and new_name.strip():
            new_id = self.db.duplicate_scenario(sc_id, new_name.strip())
            if new_id:
                self.load_scenarios()
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể nhân bản kịch bản!")

    def move_action(self, direction="up"):
        row = self.table_actions.currentRow()
        if row < 0:
            return
        act_id_item = self.table_actions.item(row, 0)
        if not act_id_item:
            return
        act_id = int(act_id_item.text())
        if self.db.move_action_order(act_id, direction):
            self.load_actions()
            new_row = max(0, row - 1) if direction == "up" else min(self.table_actions.rowCount() - 1, row + 1)
            self.table_actions.setCurrentCell(new_row, 1)

    def rename_scenario(self):
        item = self.list_scenarios.currentItem()
        if not item:
            return
        sc_id = item.data(Qt.ItemDataRole.UserRole)
        old_name = item.text().replace("📜 ", "")
        
        new_name, ok = QInputDialog.getText(self, "Đổi Tên Kịch Bản", "Nhập tên kịch bản mới:", text=old_name)
        if ok and new_name.strip():
            self.db.rename_scenario(sc_id, new_name.strip())
            self.load_scenarios()

    def delete_scenario(self):
        item = self.list_scenarios.currentItem()
        if not item:
            return
        sc_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()

        reply = QMessageBox.question(self, "Xác nhận xóa", f"Bạn có chắc muốn xóa {name} và toàn bộ hành động bên trong?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_scenario(sc_id)
            self.load_scenarios()

    def on_scenario_selected(self, item):
        if not item:
            return
        self.current_scenario_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text().replace("📜 ", "")
        self.lbl_scen_title.setText(f"<b>⚡ Các Hành Động Trong Kịch Bản: [{name}]</b>")
        self.load_actions()

    def load_actions(self):
        if not self.current_scenario_id:
            self.table_actions.setRowCount(0)
            return

        actions = self.db.get_actions_by_scenario(self.current_scenario_id)
        self.table_actions.setRowCount(len(actions))

        for row, act in enumerate(actions):
            # act: (id, action_type, action_name, config_json, order_index)
            act_id = act[0]
            act_type = act[1]
            act_name = act[2]
            cfg_json = act[3]

            self.table_actions.setItem(row, 0, QTableWidgetItem(str(act_id)))
            self.table_actions.setItem(row, 1, QTableWidgetItem(act_name))
            self.table_actions.setItem(row, 2, QTableWidgetItem(act_type))
            self.table_actions.setItem(row, 3, QTableWidgetItem(cfg_json))

    def show_add_action_menu(self):
        if not self.current_scenario_id:
            QMessageBox.warning(self, "Chú ý", "Vui lòng chọn hoặc tạo kịch bản trước!")
            return

        menu = QMenu(self)
        act_newsfeed = menu.addAction("🌐 1. Lướt Newsfeed (% Like/Thả tim, % Comment, Max Like/CMT)")
        act_reel = menu.addAction("🎬 2. Xem Facebook Reels (Tổng thời gian, Thời gian mỗi Video, % Thả tim)")
        act_watch = menu.addAction("📺 3. Xem Facebook Watch (Video theo từ khóa, Like & Comment)")
        act_story = menu.addAction("📖 4. Xem Facebook Story")
        act_add_friends = menu.addAction("👥 5. Kết Bạn (Gợi ý / UID / Link / Từ khóa)")
        act_cancel_req = menu.addAction("❌ 6. Hủy lời mời kết bạn đã gửi")
        act_unfriend = menu.addAction("🚫 7. Hủy kết bạn không tương tác")
        act_poke = menu.addAction("👉 8. Chọc bạn bè")
        act_birthday = menu.addAction("🎂 9. Chúc mừng sinh nhật bạn bè")
        act_join_groups = menu.addAction("👨‍👩‍👧‍👦 10. Tham Gia Nhóm (UID / Link / Từ khóa, Tự đồng ý quy định)")
        act_invite_group = menu.addAction("📩 11. Mời bạn bè vào nhóm")
        act_leave_group = menu.addAction("🚪 12. Rời nhóm không tương tác")
        act_buff_page = menu.addAction("📄 13. Buff Like / Follow Fanpage")
        act_notifications = menu.addAction("🔔 14. Đọc thông báo")
        act_wall = menu.addAction("📝 15. Đăng bài lên tường cá nhân")
        act_group = menu.addAction("👥 16. Đăng bài lên nhóm")
        act_seeding = menu.addAction("📣 17. Seeding Bài Viết (Link bài, Thả cảm xúc, Comment ảnh, Đổi MD5)")
        act_msg_uid = menu.addAction("💬 18. Nhắn tin cho bạn bè / UID")
        act_auto_reply = menu.addAction("🤖 19. Tự động phản hồi tin nhắn mới")
        act_change_pass = menu.addAction("🔐 20. Đổi mật khẩu tài khoản")
        act_2fa = menu.addAction("🛡️ 21. Bật / Tắt 2FA")
        act_google = menu.addAction("🌐 22. Tìm kiếm Google (tạo cookie/lịch sử)")
        act_web = menu.addAction("🔗 23. Truy cập Website trực tiếp")
        act_delay = menu.addAction("☕ 24. Nghỉ giải lao ngẫu nhiên")

        action = menu.exec(self.btn_add_action.mapToGlobal(self.btn_add_action.rect().bottomLeft()))
        
        if action == act_newsfeed:
            self.create_action("newsfeed", "Lướt Newsfeed")
        elif action == act_reel:
            self.create_action("reel", "Xem Facebook Reels")
        elif action == act_watch:
            self.create_action("watch", "Xem Video Watch")
        elif action == act_story:
            self.create_action("story", "Xem Story Bạn Bè")
        elif action == act_add_friends:
            self.create_action("add_friends", "Kết Bạn (Gợi ý/UID/Link)")
        elif action == act_cancel_req:
            self.create_action("cancel_friend_requests", "Hủy Lời Mời Kết Bạn")
        elif action == act_unfriend:
            self.create_action("unfriend", "Hủy Kết Bạn")
        elif action == act_poke:
            self.create_action("poke_friends", "Chọc Bạn Bè")
        elif action == act_birthday:
            self.create_action("birthday_wishes", "Chúc Mừng Sinh Nhật")
        elif action == act_join_groups:
            self.create_action("join_groups", "Tham Gia Nhóm (Tự Động Duyệt)")
        elif action == act_invite_group:
            self.create_action("invite_friends_group", "Mời Bạn Bè Vào Nhóm")
        elif action == act_leave_group:
            self.create_action("leave_groups", "Rời Nhóm")
        elif action == act_buff_page:
            self.create_action("buff_like_page", "Buff Like Fanpage")
        elif action == act_notifications:
            self.create_action("notifications", "Đọc thông báo")
        elif action == act_wall:
            self.create_action("post_wall", "Đăng bài lên tường cá nhân")
        elif action == act_group:
            self.create_action("post_group", "Đăng bài lên nhóm")
        elif action == act_seeding:
            self.create_action("seeding", "Seeding Bài Viết (Đổi MD5 & Lật Ảnh)")
        elif action == act_msg_uid:
            self.create_action("send_messages_uid", "Nhắn Tin Bạn Bè / UID")
        elif action == act_auto_reply:
            self.create_action("auto_reply_message", "Tự Động Phản Hồi Tin Nhắn")
        elif action == act_change_pass:
            self.create_action("change_password", "Đổi Mật Khẩu")
        elif action == act_2fa:
            self.create_action("on_off_2fa", "Bật / Tắt 2FA")
        elif action == act_google:
            self.create_action("google_search", "Tìm Kiếm Google")
        elif action == act_web:
            self.create_action("access_website", "Truy Cập Website")
        elif action == act_delay:
            self.create_action("delay", "Nghỉ Giải Lao")

    def create_action(self, action_type, action_name):
        dialog = ActionConfigDialog(self, action_type, action_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cfg = dialog.get_config()
            cfg_json = json.dumps(cfg, ensure_ascii=False)
            self.db.add_action_to_scenario(self.current_scenario_id, action_type, action_name, cfg_json)
            self.load_actions()

    def edit_action_config(self):
        row = self.table_actions.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chú ý", "Vui lòng chọn hành động cần sửa!")
            return

        act_id = int(self.table_actions.item(row, 0).text())
        act_name = self.table_actions.item(row, 1).text()
        act_type = self.table_actions.item(row, 2).text()
        cfg_str = self.table_actions.item(row, 3).text()

        try:
            cfg_dict = json.loads(cfg_str)
        except Exception:
            cfg_dict = {}

        dialog = ActionConfigDialog(self, act_type, act_name, cfg_dict)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dialog.get_config()
            new_cfg_json = json.dumps(new_cfg, ensure_ascii=False)
            self.db.update_action_config(act_id, new_cfg_json)
            self.load_actions()

    def delete_action(self):
        row = self.table_actions.currentRow()
        if row < 0:
            return

        act_id = int(self.table_actions.item(row, 0).text())
        self.db.delete_action(act_id)
        self.load_actions()
