import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QSpinBox,
    QFormLayout, QLabel, QCheckBox, QDialogButtonBox, QMessageBox,
    QComboBox, QLineEdit
)

class GeneralConfigDialog(QDialog):
    """
    Cấu Hình Chung Hệ Thống (fCauHinhChung)
    Cấu hình luồng chạy, số luồng/thiết bị song song, Đổi IP Proxy / Mạng di động / Máy bay, delay quay vòng...
    """
    def __init__(self, parent, db):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Cấu Hình Chung Hệ Thống & Đổi IP (Proxy / 4G / Máy Bay)")
        self.resize(560, 480)
        self.db = db

        layout = QVBoxLayout(self)

        # 1. Cấu hình Luồng & Thiết Bị
        gb_threads = QGroupBox("1. Luồng Chạy & Thiết Bị ADB")
        form_threads = QFormLayout(gb_threads)

        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 100)
        self.spin_threads.setValue(5)
        form_threads.addRow("Số Phone/Luồng chạy song song:", self.spin_threads)

        self.spin_delay_turn_from = QSpinBox()
        self.spin_delay_turn_from.setRange(1, 600)
        self.spin_delay_turn_from.setValue(5)

        self.spin_delay_turn_to = QSpinBox()
        self.spin_delay_turn_to.setRange(1, 600)
        self.spin_delay_turn_to.setValue(15)

        box_delay = QHBoxLayout()
        box_delay.addWidget(self.spin_delay_turn_from)
        box_delay.addWidget(QLabel("đến"))
        box_delay.addWidget(self.spin_delay_turn_to)
        box_delay.addWidget(QLabel("giây"))
        form_threads.addRow("Delay giữa 2 tài khoản/lượt chạy:", box_delay)

        layout.addWidget(gb_threads)

        # 2. Cấu hình Đổi IP & Proxy Nâng Cao
        gb_proxy = QGroupBox("2. Tự Động Đổi IP & Kết Nối Proxy / Mạng 4G")
        form_proxy = QFormLayout(gb_proxy)

        self.cbo_change_ip_mode = QComboBox()
        self.cbo_change_ip_mode.addItems([
            "1. Sử dụng App Super Proxy (Proxy HTTP/Sock5 từng nick)",
            "2. Bật / Tắt Chế Độ Máy Bay (Airplane Mode trên Phone)",
            "3. Bật / Tắt Mạng Di Động (Mobile Data 4G/5G trên Phone)",
            "4. Gọi API XProxy / Dcom 4G Box",
            "5. Không đổi IP (Giữ nguyên kết nối)"
        ])
        form_proxy.addRow("Phương thức đổi IP:", self.cbo_change_ip_mode)

        self.txt_xproxy_api = QLineEdit()
        self.txt_xproxy_api.setPlaceholderText("Nhập Link API Reset XProxy / Dcom (nếu dùng loại 4)...")
        form_proxy.addRow("Link API XProxy:", self.txt_xproxy_api)

        self.cb_fake_device = QCheckBox("Dùng hồ sơ thiết bị cố định theo từng tài khoản")
        self.cb_fake_device.setToolTip("Hệ thống luôn áp dụng Android ID/hostname đã lưu của đúng tài khoản trước khi restore.")
        self.cb_fake_device.setChecked(True)
        self.cb_fake_device.setEnabled(False)
        form_proxy.addRow(self.cb_fake_device)

        self.cb_check_live = QCheckBox("Bật tự động Check Live/Die UID trước khi mở App Facebook")
        self.cb_check_live.setChecked(True)
        form_proxy.addRow(self.cb_check_live)

        layout.addWidget(gb_proxy)

        # Nút bấm
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_config)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.load_config()

    def load_config(self):
        if os.path.exists("general_config.json"):
            try:
                with open("general_config.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    ip_mode = cfg.get("ip_mode", "super_proxy")
                    if ip_mode == "super_proxy":
                        self.cbo_change_ip_mode.setCurrentIndex(0)
                    elif ip_mode == "airplane":
                        self.cbo_change_ip_mode.setCurrentIndex(1)
                    elif ip_mode == "mobile_data":
                        self.cbo_change_ip_mode.setCurrentIndex(2)
                    elif ip_mode == "xproxy":
                        self.cbo_change_ip_mode.setCurrentIndex(3)
                    elif ip_mode == "none":
                        self.cbo_change_ip_mode.setCurrentIndex(4)
                    self.txt_xproxy_api.setText(cfg.get("xproxy_api", ""))
            except Exception:
                pass

    def save_config(self):
        idx = self.cbo_change_ip_mode.currentIndex()
        ip_mode_map = {0: "super_proxy", 1: "airplane", 2: "mobile_data", 3: "xproxy", 4: "none"}
        cfg = {
            "threads": self.spin_threads.value(),
            "ip_mode": ip_mode_map.get(idx, "super_proxy"),
            "xproxy_api": self.txt_xproxy_api.text().strip(),
            "fake_device": self.cb_fake_device.isChecked(),
            "check_live": self.cb_check_live.isChecked()
        }
        with open("general_config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        QMessageBox.information(self, "Thành công", "Đã lưu Cấu Hình Chung & Phương Thức Đổi IP thành công!")
        self.accept()
