import sys
import os
import json
import shutil
import concurrent.futures
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox, QLabel,
    QHeaderView, QMessageBox, QMenu, QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QBrush, QIcon

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database.db import DatabaseManager
from src.core.adb import get_connected_devices, ADBDevice
from src.utils.account_parser import SmartAccountParser
from src.utils.fb_checker import check_fb_live
from src.utils.otp_helper import get_2fa_code
from src.gui.general_config_dialog import GeneralConfigDialog
from src.gui.scenario_manager_dialog import ScenarioManagerDialog
from src.gui.device_manager_dialog import DeviceManagerDialog
from src.gui.display_config_dialog import DisplayConfigDialog
from src.gui.action_config_dialog import ActionConfigDialog
from src.core.backup_manager import BackupRestoreManager
from src.core.profile_manager import DeviceProfileManager
from src.core.automation_worker import AutomationWorker
from src.core.scenario_executor import ScenarioExecutor

# Các dialog cập nhật dữ liệu
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox

class EditAccountDialog(QDialog):
    def __init__(self, parent, account_data):
        super().__init__(parent)
        self.setWindowTitle("✏️ Sửa Thông Tin Tài Khoản Facebook")
        self.resize(480, 520)
        self.acc = account_data

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_uid = QLineEdit(str(self.acc.get("uid", "")))
        self.txt_pass = QLineEdit(str(self.acc.get("pass", "")))
        self.txt_2fa = QLineEdit(str(self.acc.get("fa2", "")))
        self.txt_cookie = QLineEdit(str(self.acc.get("cookie", "")))
        self.txt_token = QLineEdit(str(self.acc.get("token", "")))
        self.txt_name = QLineEdit(str(self.acc.get("name", "")))
        self.txt_gender = QLineEdit(str(self.acc.get("gender", "")))
        self.txt_friends = QLineEdit(str(self.acc.get("friends", 0)))
        self.txt_groups = QLineEdit(str(self.acc.get("groups_count", 0)))
        self.txt_proxy = QLineEdit(str(self.acc.get("proxy", "")))

        form.addRow("UID:", self.txt_uid)
        form.addRow("Mật Khẩu:", self.txt_pass)
        form.addRow("Mã 2FA:", self.txt_2fa)
        form.addRow("Cookie:", self.txt_cookie)
        form.addRow("Token:", self.txt_token)
        form.addRow("Tên FB:", self.txt_name)
        form.addRow("Giới Tính:", self.txt_gender)
        form.addRow("Số Bạn Bè:", self.txt_friends)
        form.addRow("Số Nhóm:", self.txt_groups)
        form.addRow("Proxy:", self.txt_proxy)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_data(self):
        return {
            "uid": self.txt_uid.text().strip(),
            "pass": self.txt_pass.text().strip(),
            "fa2": self.txt_2fa.text().strip(),
            "cookie": self.txt_cookie.text().strip(),
            "token": self.txt_token.text().strip(),
            "name": self.txt_name.text().strip(),
            "gender": self.txt_gender.text().strip(),
            "friends": int(self.txt_friends.text().strip() or 0),
            "groups_count": int(self.txt_groups.text().strip() or 0),
            "proxy": self.txt_proxy.text().strip()
        }


class PasteAccountDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("📥 Dán Danh Sách Nick Facebook (Tự Nhận Diện Format)")
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Dán danh sách nick vào ô bên dưới (Mỗi nick 1 dòng, hỗ trợ phân tách bằng |, tab, c_user...):"))

        self.txt_input = QTextEdit()
        layout.addWidget(self.txt_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_text(self):
        return self.txt_input.toPlainText()


class BatchCheckLiveWorker(QThread):
    result_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()

    def __init__(self, accounts_to_check):
        super().__init__()
        self.accounts = accounts_to_check

    def run(self):
        def check_one(acc):
            acc_id, uid = acc
            is_live, status_msg = check_fb_live(uid)
            status_str = "LIVE" if is_live else f"DIE ({status_msg})"
            self.result_signal.emit(acc_id, status_str)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_one, a) for a in self.accounts]
            concurrent.futures.wait(futures)

        self.finished_signal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 MaxPhoneFarm Reborn Pro - Hệ Thống Phone Farm Tự Động Hóa (Tích Hợp AI Agent)")
        self.resize(1280, 720)

        self.db = DatabaseManager()
        self.devices = []
        self.account_rows = {}
        self.visible_columns = ["uid", "pass", "fa2", "cookie", "token", "name", "gender", "friends", "groups_count", "proxy", "status"]

        self.init_ui()
        self.load_groups_to_filter()
        self.load_data_to_table()
        self.refresh_devices()

    def refresh_devices(self):
        saved_serials = []
        if os.path.exists("selected_devices.json"):
            try:
                with open("selected_devices.json", "r", encoding="utf-8") as f:
                    saved_serials = json.load(f)
            except Exception:
                pass

        connected = get_connected_devices()
        if saved_serials:
            self.devices = [s for s in saved_serials if s in connected]
            if not self.devices and connected:
                self.devices = connected
        else:
            self.devices = connected

        if self.devices:
            self.lbl_status.setText(f"Trạng thái: Sẵn sàng | Đã chọn {len(self.devices)} Phone ADB vận hành -> [{', '.join(self.devices)}]")
        else:
            self.lbl_status.setText("Trạng thái: Chưa chọn hoặc chưa kết nối điện thoại ADB nào!")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 1. Thanh lọc nhóm
        group_bar = QHBoxLayout()
        group_bar.addWidget(QLabel("📂 Lọc Nhóm Tài Khoản:"))
        
        self.cbo_filter_group = QComboBox()
        self.cbo_filter_group.currentIndexChanged.connect(self.load_data_to_table)
        group_bar.addWidget(self.cbo_filter_group)

        self.btn_add_group = QPushButton("➕ Thêm Nhóm")
        self.btn_add_group.clicked.connect(self.add_group)
        group_bar.addWidget(self.btn_add_group)

        group_bar.addStretch()
        layout.addLayout(group_bar)

        # 2. Thanh công cụ nút bấm (Toolbar Top)
        top_bar = QHBoxLayout()

        self.btn_refresh_dev = QPushButton("📱 Danh Sách Điện Thoại ADB")
        self.btn_refresh_dev.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 6px;")
        self.btn_refresh_dev.clicked.connect(self.open_device_manager)

        self.btn_general_cfg = QPushButton("⚙️ Cấu Hình Chung & Đổi IP")
        self.btn_general_cfg.setStyleSheet("background-color: #7b1fa2; color: white; font-weight: bold; padding: 6px;")
        self.btn_general_cfg.clicked.connect(self.open_general_config)

        self.btn_display_cfg = QPushButton("👁️ Cấu Hình Hiển Thị")
        self.btn_display_cfg.clicked.connect(self.open_display_config)

        self.btn_scenario_mgr = QPushButton("📜 Quản Lý Kịch Bản Nuôi")
        self.btn_scenario_mgr.setStyleSheet("background-color: #e65100; color: white; font-weight: bold; padding: 6px;")
        self.btn_scenario_mgr.clicked.connect(self.open_scenario_manager)

        self.btn_start_run = QPushButton("▶️ CHẠY TƯƠNG TÁC KỊCH BẢN")
        self.btn_start_run.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_start_run.clicked.connect(self.start_automation_run)

        self.btn_add_acc = QPushButton("➕ Thêm Nick")
        self.btn_add_acc.clicked.connect(self.add_accounts_paste)

        top_bar.addWidget(self.btn_refresh_dev)
        top_bar.addWidget(self.btn_general_cfg)
        top_bar.addWidget(self.btn_display_cfg)
        top_bar.addWidget(self.btn_scenario_mgr)
        top_bar.addWidget(self.btn_start_run)
        top_bar.addWidget(self.btn_add_acc)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 3. Bảng hiển thị danh sách nick
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "☑️", "UID", "Kịch Bản", "Mật Khẩu", "2FA", "Cookie", "Token",
            "Tên FB", "Giới Tính", "Bạn Bè", "Nhóm", "Proxy", "Trạng Thái", "⚡ Trạng Thái Hành Động"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setColumnWidth(0, 45)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(13, QHeaderView.ResizeMode.Stretch)

        # Checkbox tiêu đề cột góc trên cùng (Header Checkbox)
        self.chk_all_accs = QCheckBox()
        self.chk_all_accs.setChecked(False)
        self.chk_all_accs.stateChanged.connect(self.toggle_select_all_header)
        self.table.setCellWidget(0, 0, self.chk_all_accs)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # Thanh trạng thái footer
        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        layout.addWidget(self.lbl_status)

    def load_groups_to_filter(self):
        self.cbo_filter_group.blockSignals(True)
        self.cbo_filter_group.clear()
        self.cbo_filter_group.addItem("All (Tất Cả Nhóm)", "all")
        groups = self.db.get_all_groups()
        for g in groups:
            self.cbo_filter_group.addItem(f"{g[1]}", g[0])
        self.cbo_filter_group.blockSignals(False)

    def add_group(self):
        name, ok = QInputDialog.getText(self, "Thêm Nhóm", "Nhập tên nhóm mới:")
        if ok and name.strip():
            g_id = self.db.add_group(name.strip())
            if g_id:
                self.load_groups_to_filter()
                QMessageBox.information(self, "Thành công", f"Đã thêm nhóm '{name.strip()}'!")

    def open_device_manager(self):
        dialog = DeviceManagerDialog(self, self.db)
        dialog.exec()
        self.refresh_devices()

    def open_general_config(self):
        dialog = GeneralConfigDialog(self, self.db)
        dialog.exec()

    def open_display_config(self):
        dialog = DisplayConfigDialog(self)
        if dialog.exec():
            self.apply_display_config()

    def apply_display_config(self):
        cfg = DisplayConfigDialog.load_config()
        mapping = [
            ("chk_select", 0), ("uid", 1), ("script_name", 2), ("password", 3),
            ("fa2", 4), ("cookie", 5), ("token", 6), ("name", 7),
            ("gender", 8), ("friends", 9), ("groups_count", 10), ("proxy", 11),
            ("status", 12), ("action_status", 13)
        ]
        for key, col_idx in mapping:
            is_visible = cfg.get(key, True)
            self.table.setColumnHidden(col_idx, not is_visible)

    def open_scenario_manager(self):
        dialog = ScenarioManagerDialog(self, self.db)
        dialog.exec()

    def load_data_to_table(self):
        group_id = self.cbo_filter_group.currentData()
        accounts = self.db.get_accounts_by_group(group_id)

        self.table.setRowCount(len(accounts))
        self.account_rows.clear()

        for row, acc in enumerate(accounts):
            acc_id = acc[0]
            uid = acc[2]
            status = acc[11] or "Ready"

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk_item)

            script_name = acc[13] or "Mặc định"
            group_name = acc[14] or "Mặc định"
            self.table.setItem(row, 1, QTableWidgetItem(str(uid)))
            self.table.setItem(row, 2, QTableWidgetItem(str(script_name)))
            self.table.setItem(row, 3, QTableWidgetItem(str(acc[3] or "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(acc[4] or "")))
            self.table.setItem(row, 5, QTableWidgetItem(str(acc[5] or "")))
            self.table.setItem(row, 6, QTableWidgetItem(str(acc[6] or "")))
            self.table.setItem(row, 7, QTableWidgetItem(str(acc[15] or ""))) # Name
            self.table.setItem(row, 8, QTableWidgetItem(str(acc[16] or ""))) # Gender
            self.table.setItem(row, 9, QTableWidgetItem(str(acc[17] or 0)))  # Friends
            self.table.setItem(row, 10, QTableWidgetItem(str(acc[18] or 0)))  # Groups (Group Count)
            self.table.setItem(row, 11, QTableWidgetItem(str(acc[10] or ""))) # Proxy

            item_status = QTableWidgetItem(status)
            if "LIVE" in status.upper():
                item_status.setBackground(QColor("#c8e6c9")) # Màu Xanh Lá
                item_status.setForeground(QColor("#1b5e20"))
            elif "DIE" in status.upper():
                item_status.setBackground(QColor("#ffcdd2")) # Màu Đỏ
                item_status.setForeground(QColor("#b71c1c"))

            self.table.setItem(row, 12, item_status)

            # Cột 13: Trạng thái hành động Realtime
            item_act = QTableWidgetItem("Ready (Đang chờ)")
            self.table.setItem(row, 13, item_act)

            self.account_rows[acc_id] = {
                "row": row, "id": acc_id, "uid": uid, "pass": acc[3], "fa2": acc[4],
                "cookie": acc[5], "token": acc[6], "proxy": acc[10], "status": status,
                "script_name": script_name
            }

        self.apply_display_config()

    def add_accounts_paste(self):
        dialog = PasteAccountDialog(self)
        if dialog.exec():
            raw_text = dialog.get_text()
            if not raw_text.strip():
                return
            parsed_list = SmartAccountParser.parse_bulk(raw_text)
            added_count = 0
            for acc in parsed_list:
                uid = acc.get("uid")
                if uid:
                    try:
                        self.db.add_account(
                            uid=uid,
                            password=acc.get("password", ""),
                            fa2=acc.get("fa2", ""),
                            cookie=acc.get("cookie", ""),
                            proxy=acc.get("proxy", ""),
                            token=acc.get("token", ""),
                            email=acc.get("email", ""),
                            pass_email=acc.get("pass_email", ""),
                            useragent=acc.get("useragent", "")
                        )
                        added_count += 1
                    except Exception as e:
                        print(f"Lỗi thêm nick {uid}:", e)
            self.load_data_to_table()
            QMessageBox.information(self, "Thành công", f"Đã thêm {added_count} tài khoản vào hệ thống!")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        act_select_all = menu.addAction("☑️ Tick Chọn Tất Cả")
        act_deselect_all = menu.addAction("⬜ Bỏ Tick Tất Cả")
        menu.addSeparator()

        # Dynamic Sub-menu Gán Kịch Bản
        scenarios = self.db.get_all_scenarios()
        menu_assign_script = menu.addMenu("📜 Gán Kịch Bản Tương Tác Nuôi")
        script_actions = {}
        if scenarios:
            for sc in scenarios:
                sc_id, sc_name = sc[0], sc[1]
                act_sc = menu_assign_script.addAction(f"▶️ {sc_name}")
                script_actions[act_sc] = sc_name
        else:
            menu_assign_script.addAction("⚠️ Chưa có kịch bản nào (Vui lòng tạo kịch bản trước)").setEnabled(False)

        menu.addSeparator()
        act_edit = menu.addAction("✏️ Sửa Thông Tin Nick Được Chọn")
        act_delete = menu.addAction("❌ Xóa Nick (Xóa Luôn Backup Data)")
        menu.addSeparator()
        act_check_live = menu.addAction("🔍 Check Live/Die UID Facebook")
        act_get_2fa = menu.addAction("🔑 Lấy Mã 2FA (OTP)")
        act_backup = menu.addAction("📦 Backup App Data Facebook (Lưu Phiên Đăng Nhập)")
        act_restore = menu.addAction("🔄 Restore App Data Facebook (Không Cần Pass/Cookie)")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action in script_actions:
            selected_script_name = script_actions[action]
            self.assign_script_to_selected_rows(selected_script_name)
        elif action == act_select_all:
            self.toggle_select_all(True)
        elif action == act_deselect_all:
            self.toggle_select_all(False)
        elif action == act_edit:
            self.edit_selected_account()
        elif action == act_delete:
            self.delete_selected_accounts()
        elif action == act_check_live:
            self.check_live_selected()
        elif action == act_get_2fa:
            self.get_2fa_selected()
        elif action == act_backup:
            self.backup_selected()
        elif action == act_restore:
            self.restore_selected()

    def assign_script_to_selected_rows(self, script_name):
        selected_indexes = self.table.selectionModel().selectedRows()
        selected_uids = []
        
        # Nếu dùng Ctrl/Shift bôi đen hàng
        if selected_indexes:
            for idx in selected_indexes:
                r = idx.row()
                uid_item = self.table.item(r, 1)
                if uid_item:
                    selected_uids.append(uid_item.text())
        else:
            # Nếu nhấp chuột phải trên 1 hàng
            row = self.table.currentRow()
            if row >= 0:
                uid_item = self.table.item(row, 1)
                if uid_item:
                    selected_uids.append(uid_item.text())

        if not selected_uids:
            # Ngược lại lấy các hàng có ô Checkbox tick chọn
            for r in range(self.table.rowCount()):
                chk = self.table.item(r, 0)
                if chk and chk.checkState() == Qt.CheckState.Checked:
                    selected_uids.append(self.table.item(r, 1).text())

        if not selected_uids:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn hoặc bôi đen ít nhất 1 tài khoản để gán kịch bản!")
            return

        self.db.update_account_script(selected_uids, script_name)
        self.load_data_to_table()
        QMessageBox.information(self, "Thành công", f"Đã gán kịch bản '{script_name}' cho {len(selected_uids)} tài khoản!")

    def toggle_select_all_header(self, state):
        chk_state = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(chk_state)

    def toggle_select_all(self, select=True):
        state = Qt.CheckState.Checked if select else Qt.CheckState.Unchecked
        self.chk_all_accs.blockSignals(True)
        self.chk_all_accs.setChecked(select)
        self.chk_all_accs.blockSignals(False)
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(state)

    def edit_selected_account(self):
        row = self.table.currentRow()
        if row < 0:
            return
        uid = self.table.item(row, 1).text()
        acc_data = None
        for acc in self.account_rows.values():
            if acc["uid"] == uid:
                acc_data = acc; break

        if acc_data:
            dialog = EditAccountDialog(self, acc_data)
            if dialog.exec():
                new_data = dialog.get_data()
                self.db.update_account(acc_data["id"], new_data)
                self.load_data_to_table()
                QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin tài khoản!")

    def delete_selected_accounts(self):
        selected_uids = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                item_uid = self.table.item(r, 1)
                if item_uid and item_uid.text().strip():
                    selected_uids.append(item_uid.text().strip())

        if not selected_uids:
            QMessageBox.warning(self, "Chú ý", "Vui lòng chọn ít nhất 1 nick để xóa!")
            return

        reply = QMessageBox.question(self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa {len(selected_uids)} nick đã chọn và XÓA SẠCH file Backup tương ứng?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # 1. Gọi hàm xóa trực tiếp trong CSDL theo danh sách UID
            try:
                self.db.delete_accounts(selected_uids)
            except Exception as e:
                print("Lỗi xóa DB:", e)

            # 2. Dọn dẹp file backup tương ứng
            for uid in selected_uids:
                try:
                    BackupRestoreManager.delete_backup_file(uid)
                except Exception:
                    pass

            # 3. Reload lại dữ liệu bảng
            self.load_data_to_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa thành công {len(selected_uids)} tài khoản và dọn dẹp file backup!")

    def check_live_selected(self):
        accounts_to_check = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                uid = self.table.item(r, 1).text()
                acc_id = None
                for a in self.account_rows.values():
                    if a["uid"] == uid:
                        acc_id = a["id"]; break
                if acc_id:
                    accounts_to_check.append((acc_id, uid))

        if not accounts_to_check:
            QMessageBox.warning(self, "Chú ý", "Vui lòng chọn nick để Check Live!")
            return

        self.lbl_status.setText(f"Đang Check Live/Die cho {len(accounts_to_check)} nick...")
        self.checker_thread = BatchCheckLiveWorker(accounts_to_check)
        self.checker_thread.result_signal.connect(self.on_check_live_result)
        self.checker_thread.finished_signal.connect(lambda: self.lbl_status.setText("Check Live/Die hoàn tất!"))
        self.checker_thread.start()

    def on_check_live_result(self, acc_id, status_str):
        self.db.update_account_status(acc_id, status_str)
        if acc_id in self.account_rows:
            row = self.account_rows[acc_id]["row"]
            item_status = QTableWidgetItem(status_str)
            if "LIVE" in status_str.upper():
                item_status.setBackground(QColor("#c8e6c9"))
                item_status.setForeground(QColor("#1b5e20"))
            else:
                item_status.setBackground(QColor("#ffcdd2"))
                item_status.setForeground(QColor("#b71c1c"))
            self.table.setItem(row, 11, item_status)

    def get_2fa_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        fa2_secret = self.table.item(row, 3).text()
        if not fa2_secret:
            QMessageBox.warning(self, "Chú ý", "Tài khoản này chưa có Mã Secret 2FA!")
            return
        code = get_2fa_code(fa2_secret)
        QMessageBox.information(self, "Mã 2FA OTP", f"Mã OTP 6 số hiện tại là: {code}")

    def backup_selected(self):
        if not self.devices:
            QMessageBox.warning(self, "Chú ý", "Không tìm thấy thiết bị Phone ADB!")
            return
        row = self.table.currentRow()
        if row < 0:
            return
        uid = self.table.item(row, 1).text()
        adb = ADBDevice(self.devices[0])
        success, res = BackupRestoreManager.backup_account_app_data(adb, uid, log_func=lambda m: self.lbl_status.setText(m))
        if success:
            QMessageBox.information(self, "Thành công", f"Đã Backup App Data Facebook thành công cho UID [{uid}]!")

    def restore_selected(self):
        if not self.devices:
            QMessageBox.warning(self, "Chú ý", "Không tìm thấy thiết bị Phone ADB!")
            return
        row = self.table.currentRow()
        if row < 0:
            return
        uid = self.table.item(row, 1).text()
        adb = ADBDevice(self.devices[0])
        log_func = lambda message: self.lbl_status.setText(message)
        if not BackupRestoreManager.reset_facebook_app_data(adb, log_func=log_func):
            QMessageBox.warning(self, "Lỗi", "Không thể reset dữ liệu Facebook trước khi restore.")
            return
        if not BackupRestoreManager.restore_device_helper_profile(adb, uid, log_func=log_func):
            QMessageBox.warning(self, "Lỗi", "Không thể khôi phục profile thiết bị của tài khoản.")
            return
        try:
            device_profile = BackupRestoreManager.get_account_device_profile(uid, adb)
            DeviceProfileManager().apply_device_to_phone(adb, uid, device_profile, log_func=log_func)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể áp dụng profile thiết bị: {exc}")
            return
        success = BackupRestoreManager.restore_account_app_data(adb, uid, log_func=log_func)
        if not success:
            QMessageBox.warning(self, "Lỗi", "Không thể khôi phục dữ liệu Facebook.")
            return

        adb.launch_facebook()
        executor = ScenarioExecutor(adb, log_callback=log_func)
        log_func("Đang đợi Facebook tải xong sau restore...")
        if not executor.wait_for_facebook_ready(timeout_sec=90, dismiss_setup_prompts=True):
            QMessageBox.warning(
                self,
                "Chưa sẵn sàng",
                "Facebook chưa tải ổn định sau restore. Dữ liệu backup được giữ nguyên; hãy kiểm tra lại kết nối mạng rồi thử mở Facebook.",
            )
            return
        QMessageBox.information(self, "Thành công", f"Đã khôi phục và mở Facebook thành công cho UID [{uid}]!")

    def start_automation_run(self):
        if not self.devices:
            QMessageBox.warning(self, "Lỗi", "Vui lòng kết nối ít nhất một điện thoại Android qua ADB!")
            return

        selected_accounts = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.item(row, 0)
            if not checkbox or checkbox.checkState() != Qt.CheckState.Checked:
                continue

            uid_item = self.table.item(row, 1)
            uid = uid_item.text() if uid_item else ""
            account_data = next(
                (account for account in self.account_rows.values() if str(account.get("uid")) == str(uid)),
                None,
            )
            if account_data is None:
                account_data = {
                    "row": row,
                    "id": row + 1,
                    "uid": uid,
                    "pass": self.table.item(row, 3).text() if self.table.item(row, 3) else "",
                    "fa2": self.table.item(row, 4).text() if self.table.item(row, 4) else "",
                    "cookie": self.table.item(row, 5).text() if self.table.item(row, 5) else "",
                    "proxy": self.table.item(row, 11).text() if self.table.item(row, 11) else "",
                    "script_name": self.table.item(row, 2).text() if self.table.item(row, 2) else "",
                }
            selected_accounts.append(account_data)

        if not selected_accounts:
            QMessageBox.warning(self, "Chú ý", "Vui lòng tick chọn tài khoản để chạy kịch bản!")
            return

        selected_devices = []
        if os.path.exists("selected_devices.json"):
            try:
                with open("selected_devices.json", "r", encoding="utf-8") as file:
                    selected_devices = json.load(file)
            except (OSError, json.JSONDecodeError):
                selected_devices = []
        if not selected_devices:
            selected_devices = [self.devices[0]]

        target_serial = selected_devices[0]
        if target_serial not in self.devices:
            QMessageBox.warning(
                self,
                "Lỗi",
                f"Thiết bị [{target_serial}] không còn kết nối qua ADB. Vui lòng chọn lại thiết bị.",
            )
            return

        general_config = self._read_general_config()
        available_serials = [s for s in selected_devices if s in self.devices]
        if not available_serials:
            QMessageBox.warning(self, "Lỗi", "Không có thiết bị ADB nào khả dụng trong danh sách đã chọn.")
            return

        queue = []
        for index, account in enumerate(selected_accounts):
            scenario_config = self._build_scenario_config(account)
            if scenario_config is None:
                return
            # Phân bổ luân phiên vòng tròn (Round-Robin) giữa các điện thoại được chọn
            assigned_serial = available_serials[index % len(available_serials)]
            queue.append(
                {
                    "account": account,
                    "serial": assigned_serial,
                    "scenario": scenario_config,
                    "ip_mode": general_config.get("ip_mode", "super_proxy"),
                    "network_config": general_config,
                }
            )

        self._automation_queue = queue
        self._automation_results = []
        self._automation_total = len(queue)
        self._start_next_automation_job()

    def _read_general_config(self):
        config = {"ip_mode": "super_proxy", "xproxy_api": "", "fake_device": False}
        if not os.path.exists("general_config.json"):
            return config
        try:
            with open("general_config.json", "r", encoding="utf-8") as file:
                config.update(json.load(file))
        except (OSError, json.JSONDecodeError):
            pass
        return config

    def _build_scenario_config(self, account):
        scenarios = self.db.get_all_scenarios()
        target_scenario_id = None
        script_name = account.get("script_name", "")
        if script_name:
            target_scenario_id = next(
                (scenario[0] for scenario in scenarios if scenario[1] == script_name),
                None,
            )
        if target_scenario_id is None and scenarios:
            target_scenario_id = scenarios[0][0]

        scenario_config = {"actions": []}
        if target_scenario_id is None:
            return scenario_config

        for action in self.db.get_actions_by_scenario(target_scenario_id):
            try:
                action_config = json.loads(action[3]) if action[3] else {}
            except (TypeError, json.JSONDecodeError) as exc:
                QMessageBox.critical(
                    self,
                    "Lỗi kịch bản",
                    f"Cấu hình của hành động [{action[1]}] không hợp lệ: {exc}",
                )
                return None
            scenario_config["actions"].append({"type": action[1], "config": action_config})
        return scenario_config

    def _start_next_automation_job(self):
        if not self._automation_queue:
            total = getattr(self, "_automation_total", 0)
            success_count = sum(1 for result in self._automation_results if result["success"])
            self.lbl_status.setText(f"Đã hoàn tất {success_count}/{total} tài khoản.")
            QMessageBox.information(
                self,
                "Hoàn tất",
                f"Đã chạy và backup thành công {success_count}/{total} tài khoản.",
            )
            return

        job = self._automation_queue.pop(0)
        account = job["account"]
        self._current_automation_job = job
        self.current_running_row = account.get("row", 0)
        self.lbl_status.setText(
            f"Đang xử lý UID {account['uid']} trên Phone [{job['serial']}] "
            f"({len(self._automation_results) + 1}/{self._automation_total})..."
        )

        worker = AutomationWorker(
            account,
            job["serial"],
            job["scenario"],
            ip_mode=job["ip_mode"],
            network_config=job["network_config"],
        )
        thread = QThread(self)
        self.auto_worker = worker
        self.auto_thread = thread
        worker.moveToThread(thread)
        worker.log_signal.connect(self.on_automation_log)
        worker.failed_signal.connect(self.on_automation_failed)
        thread.started.connect(worker.run)
        worker.finished_signal.connect(thread.quit)
        thread.finished.connect(
            lambda current_job=job, current_worker=worker, current_thread=thread: self._on_automation_thread_finished(
                current_job, current_worker, current_thread
            )
        )
        thread.finished.connect(worker.deleteLater)
        thread.start()

    def _on_automation_thread_finished(self, job, worker, thread):
        account = job["account"]
        error_message = worker.error_message
        if error_message:
            self._automation_results.append({"account": account, "success": False, "error": error_message})
            self._automation_queue = []
            self.lbl_status.setText(f"Đã dừng tại UID {account['uid']}: {error_message}")
            QMessageBox.critical(
                self,
                "Đã dừng hàng đợi",
                f"UID [{account['uid']}] gặp lỗi: {error_message}\n\n"
                "Các tài khoản tiếp theo không được chạy để bảo toàn backup và trạng thái phiên.",
            )
            thread.deleteLater()
            return

        self._automation_results.append({"account": account, "success": True})
        thread.deleteLater()
        self._start_next_automation_job()

    def on_automation_failed(self, error_message):
        self.lbl_status.setText(f"Lỗi khi chạy kịch bản: {error_message}")

    def on_automation_log(self, acc_id, status_str, log_msg):
        self.lbl_status.setText(f"[{acc_id}] {log_msg}")
        if hasattr(self, "current_running_row") and self.current_running_row is not None:
            item_act = QTableWidgetItem(log_msg)
            if "lỗi" in log_msg.lower() or "error" in log_msg.lower() or "thất bại" in log_msg.lower():
                item_act.setBackground(QColor("#ffcdd2"))
                item_act.setForeground(QColor("#b71c1c"))
            elif "thành công" in log_msg.lower() or "hoàn tất" in log_msg.lower() or "hoàn thành" in log_msg.lower():
                item_act.setBackground(QColor("#c8e6c9"))
                item_act.setForeground(QColor("#1b5e20"))
            else:
                item_act.setBackground(QColor("#fff9c4"))
                item_act.setForeground(QColor("#f57f17"))
            self.table.setItem(self.current_running_row, 13, item_act)

        account = getattr(self, "_current_automation_job", {}).get("account", {})
        uid = account.get("uid")
        if uid:
            try:
                self.db.update_account_status(uid, status_str)
            except Exception:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
