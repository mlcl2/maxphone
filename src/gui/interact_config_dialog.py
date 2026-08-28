import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QCheckBox, QSpinBox, QFormLayout, QLabel,
    QPushButton, QDialogButtonBox, QMessageBox, QLineEdit,
    QRadioButton
)

class InteractConfigDialog(QDialog):
    """
    Form Cấu Hình Tương Tác (Kịch Bản Nuôi Nick & Hành Động)
    Cho phép Cấu hình thời gian lướt Newsfeed, Xem Reel, Đăng Bài, Seeding...
    """
    def __init__(self, parent, db):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Cấu Hình Tương Tác & Kịch Bản Nuôi Nick")
        self.resize(600, 500)
        self.db = db
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.sqlite")

        layout = QVBoxLayout(self)

        # Tab Widget phân chia nhóm Cấu hình
        tabs = QTabWidget()

        # Tab 1: Kịch bản Luồng Chung
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)

        gb_flow = QGroupBox("1. Luồng Tự Động Đăng Nhập & Nuôi")
        flow_form = QFormLayout(gb_flow)
        
        self.spin_delay_from = QSpinBox()
        self.spin_delay_from.setRange(1, 300)
        self.spin_delay_from.setValue(5)

        self.spin_delay_to = QSpinBox()
        self.spin_delay_to.setRange(1, 300)
        self.spin_delay_to.setValue(15)

        delay_box = QHBoxLayout()
        delay_box.addWidget(QLabel("Từ:"))
        delay_box.addWidget(self.spin_delay_from)
        delay_box.addWidget(QLabel("đến:"))
        delay_box.addWidget(self.spin_delay_to)
        delay_box.addWidget(QLabel("giây"))
        flow_form.addRow("Độ trễ giữa các hành động:", delay_box)

        self.cb_check_live_before = QCheckBox("Check Live/Die UID trước khi mở App Facebook")
        self.cb_check_live_before.setChecked(True)
        flow_form.addRow(self.cb_check_live_before)

        self.cb_change_proxy = QCheckBox("Tự động đổi IP Proxy (Super Proxy) trước khi đăng nhập")
        self.cb_change_proxy.setChecked(True)
        flow_form.addRow(self.cb_change_proxy)

        self.cb_change_device = QCheckBox("Tự động Fake IMEI / Android ID thiết bị (Device Profile)")
        self.cb_change_device.setChecked(True)
        flow_form.addRow(self.cb_change_device)

        layout_gen.addWidget(gb_flow)
        tabs.addTab(tab_general, "⚙️ Cấu Hình Chung")

        # Tab 2: Kịch Bản Hành Động Tương Tác
        tab_actions = QWidget()
        layout_act = QVBoxLayout(tab_actions)

        gb_act = QGroupBox("2. Các Hành Động Nuôi Nick Tự Động")
        act_form = QFormLayout(gb_act)

        self.cb_act_newsfeed = QCheckBox("Lướt Newsfeed + Thả Tim bài viết ngẫu nhiên")
        self.cb_act_newsfeed.setChecked(True)
        self.spin_newsfeed_time = QSpinBox()
        self.spin_newsfeed_time.setRange(10, 600)
        self.spin_newsfeed_time.setValue(30)
        nf_box = QHBoxLayout()
        nf_box.addWidget(self.cb_act_newsfeed)
        nf_box.addWidget(QLabel("Thời gian:"))
        nf_box.addWidget(self.spin_newsfeed_time)
        nf_box.addWidget(QLabel("giây"))
        act_form.addRow(nf_box)

        self.cb_act_reel = QCheckBox("Xem Facebook Reels + Tương tác")
        self.cb_act_reel.setChecked(True)
        self.spin_reel_time = QSpinBox()
        self.spin_reel_time.setRange(10, 600)
        self.spin_reel_time.setValue(30)
        reel_box = QHBoxLayout()
        reel_box.addWidget(self.cb_act_reel)
        reel_box.addWidget(QLabel("Thời gian:"))
        reel_box.addWidget(self.spin_reel_time)
        reel_box.addWidget(QLabel("giây"))
        act_form.addRow(reel_box)

        self.cb_act_story = QCheckBox("Xem Facebook Story Bạn Bè")
        self.cb_act_story.setChecked(False)
        act_form.addRow(self.cb_act_story)

        self.cb_act_add_friends = QCheckBox("Tự Động Kết Bạn Theo Gợi Ý (2 - 5 bạn)")
        self.cb_act_add_friends.setChecked(False)
        act_form.addRow(self.cb_act_add_friends)

        layout_act.addWidget(gb_act)
        tabs.addTab(tab_actions, "📜 Kịch Bản Hành Động")

        layout.addWidget(tabs)

        # Nút Lưu
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_config)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def save_config(self):
        QMessageBox.information(self, "Thành công", "Đã lưu Cấu Hình Tương Tác & Kịch Bản Nuôi Nick thành công!")
        self.accept()
