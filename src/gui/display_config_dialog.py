import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QCheckBox, QPushButton, QMessageBox
)

COLUMNS = [
    ("chk_select", "☑️ Checkbox Chọn"),
    ("uid", "UID Facebook"),
    ("script_name", "📜 Kịch Bản Gán"),
    ("password", "Mật Khẩu"),
    ("fa2", "Mã 2FA"),
    ("cookie", "Cookie"),
    ("token", "Token"),
    ("name", "Tên Facebook"),
    ("gender", "Giới Tính"),
    ("friends", "Bạn Bè"),
    ("groups_count", "Nhóm"),
    ("proxy", "Proxy IP"),
    ("status", "Trạng Thái Live/Die"),
    ("action_status", "⚡ Trạng Thái Hành Động (Realtime)")
]

CONFIG_FILE = "display_config.json"

class DisplayConfigDialog(QDialog):
    """Cửa sổ Cấu Hình Hiển Thị các cột dữ liệu trong Bảng Tài Khoản"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👁️ Cấu Hình Hiển Thị Cột Bảng Tài Khoản")
        self.setFixedSize(460, 320)
        self.checkboxes = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Tick Chọn Các Cột Muốn Hiển Thị Bảng Tài Khoản:")
        grid = QGridLayout(group)

        current_config = self.load_config()

        for idx, (col_key, col_label) in enumerate(COLUMNS):
            chk = QCheckBox(col_label)
            chk.setChecked(current_config.get(col_key, True))
            self.checkboxes[col_key] = chk
            row = idx // 2
            col = idx % 2
            grid.addWidget(chk, row, col)

        layout.addWidget(group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Lưu Cấu Hình")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    @staticmethod
    def load_config():
        default_config = {col_key: True for col_key, _ in COLUMNS}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except Exception:
                pass
        return default_config

    def save(self):
        config_data = {col_key: chk.isChecked() for col_key, chk in self.checkboxes.items()}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Thành công", "Đã lưu cài đặt cấu hình hiển thị cột!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu file cấu hình: {e}")
