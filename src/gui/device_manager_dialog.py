import os
import concurrent.futures
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QHeaderView, QMenu,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.adb import get_connected_devices, ADBDevice

class InstallApkWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()

    def __init__(self, serials):
        super().__init__()
        self.serials = serials

    def run(self):
        def install_one(serial):
            adb = ADBDevice(serial)
            self.log_signal.emit(serial, "Đang cài đặt App Trợ thủ & Super Proxy...")
            adb.setup_max_helpers(apk_folder="apps")
            self.log_signal.emit(serial, "✅ Cài đặt hoàn tất APK hỗ trợ!")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(install_one, s) for s in self.serials]
            concurrent.futures.wait(futures)

        self.finished_signal.emit()


class DeviceManagerDialog(QDialog):
    """
    Quản Lý Danh Sách Điện Thoại ADB (Giống fDeviceList trong MaxPhoneFarm gốc)
    - Quét phát hiện Phone ADB
    - Đặt tên gợi nhớ cho từng Phone
    - Cài đặt hàng loạt App APK hỗ trợ (Super Proxy & Max Helper)
    - Checkbox Tiêu Đề Cột Chọn Tất Cả / Bỏ Chọn Tất Cả
    """
    def __init__(self, parent, db):
        super().__init__(parent)
        self.setWindowTitle("📱 Quản Lý Danh Sách Điện Thoại ADB (Device Manager)")
        self.resize(780, 480)
        self.db = db
        self.device_cache = {}

        layout = QVBoxLayout(self)

        # Thanh công cụ top
        top_box = QHBoxLayout()
        self.btn_scan = QPushButton("🔄 Quét Thiết Bị ADB")
        self.btn_scan.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 6px;")
        self.btn_scan.clicked.connect(self.scan_devices)

        self.btn_install_apk = QPushButton("📲 Cài Đặt APK Hỗ Trợ (Các Phone Được Tick)")
        self.btn_install_apk.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_install_apk.clicked.connect(self.install_all_apks)

        self.btn_save_selected = QPushButton("💾 LƯU DANH SÁCH PHONE ĐÃ CHỌN")
        self.btn_save_selected.setStyleSheet("background-color: #e65100; color: white; font-weight: bold; padding: 6px;")
        self.btn_save_selected.clicked.connect(self.save_selected_devices)

        top_box.addWidget(self.btn_scan)
        top_box.addWidget(self.btn_install_apk)
        top_box.addWidget(self.btn_save_selected)
        top_box.addStretch()
        layout.addLayout(top_box)

        # Bảng danh sách Phone
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["☑️", "Serial ADB", "Tên Điện Thoại", "Trạng Thái", "Ứng Dụng Hỗ Trợ"])
        self.table.setColumnWidth(0, 45)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Checkbox Chọn Tất Cả trên tiêu đề cột 0
        self.chk_all = QCheckBox()
        self.chk_all.setChecked(False)
        self.chk_all.stateChanged.connect(self.toggle_select_all)
        self.table.setCellWidget(0, 0, self.chk_all) # Đặt tạm widget vào giao diện header

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        self.lbl_status = QLabel("Số lượng điện thoại: 0")
        layout.addWidget(self.lbl_status)

        self.scan_devices()

    def toggle_select_all(self, state):
        chk_state = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(chk_state)

    def scan_devices(self):
        import json
        saved_serials = []
        if os.path.exists("selected_devices.json"):
            try:
                with open("selected_devices.json", "r", encoding="utf-8") as f:
                    saved_serials = json.load(f)
            except Exception:
                pass

        serials = get_connected_devices()
        self.table.setRowCount(len(serials))
        self.device_cache.clear()

        db_devices = {d[1]: d[2] for d in self.db.get_all_devices()}

        for row, serial in enumerate(serials):
            self.db.update_or_add_device(serial)
            name = db_devices.get(serial, f"Phone_{row+1}")

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            # Giữ nguyên trạng thái đã lưu trước đó nếu có
            is_checked = (serial in saved_serials) if saved_serials else False
            chk_item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk_item)

            self.table.setItem(row, 1, QTableWidgetItem(serial))
            self.table.setItem(row, 2, QTableWidgetItem(name))
            self.table.setItem(row, 3, QTableWidgetItem("🟢 Đã Kết Nối"))
            self.table.setItem(row, 4, QTableWidgetItem("Đã sẵn sàng"))

        self.lbl_status.setText(f"Phát hiện qua ADB: {len(serials)} điện thoại đang kết nối")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        act_select_all = menu.addAction("☑️ Tick Chọn Tất Cả")
        act_deselect_all = menu.addAction("⬜ Bỏ Tick Tất Cả")
        menu.addSeparator()
        act_rename = menu.addAction("✏️ Đặt Tên Gợi Nhớ Cho Điện Thoại Này")
        act_install_one = menu.addAction("📲 Cài Đặt APK Hỗ Trợ Cho Phone Này")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_select_all:
            self.chk_all.setChecked(True)
        elif action == act_deselect_all:
            self.chk_all.setChecked(False)
        elif action == act_rename:
            self.rename_selected_device()
        elif action == act_install_one:
            self.install_selected_apks()

    def rename_selected_device(self):
        row = self.table.currentRow()
        if row < 0:
            return
        serial = self.table.item(row, 1).text()
        old_name = self.table.item(row, 2).text()

        new_name, ok = QInputDialog.getText(self, "Đặt Tên Điện Thoại", f"Nhập tên gợi nhớ mới cho Phone [{serial}]:", text=old_name)
        if ok and new_name.strip():
            self.db.rename_device(serial, new_name.strip())
            self.table.setItem(row, 2, QTableWidgetItem(new_name.strip()))
            QMessageBox.information(self, "Thành công", f"Đã đặt tên Phone thành '{new_name.strip()}'!")

    def install_all_apks(self):
        serials = []
        for r in range(self.table.rowCount()):
            item_chk = self.table.item(r, 0)
            if item_chk and item_chk.checkState() == Qt.CheckState.Checked:
                serials.append(self.table.item(r, 1).text())

        if not serials:
            QMessageBox.warning(self, "Chú ý", "Vui lòng tick chọn ít nhất 1 điện thoại!")
            return

        self.btn_install_apk.setEnabled(False)
        self.lbl_status.setText(f"Đang cài đặt APK hỗ trợ cho {len(serials)} điện thoại đã chọn...")

        self.worker = InstallApkWorker(serials)
        self.worker.log_signal.connect(self.on_install_log)
        self.worker.finished_signal.connect(self.on_install_finished)
        self.worker.start()

    def install_selected_apks(self):
        row = self.table.currentRow()
        if row < 0:
            return
        serial = self.table.item(row, 1).text()
        self.worker = InstallApkWorker([serial])
        self.worker.log_signal.connect(self.on_install_log)
        self.worker.finished_signal.connect(self.on_install_finished)
        self.worker.start()

    def on_install_log(self, serial, msg):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == serial:
                self.table.setItem(row, 4, QTableWidgetItem(msg))
                break

    def on_install_finished(self):
        self.btn_install_apk.setEnabled(True)
        self.lbl_status.setText("Cài đặt APK hỗ trợ thành công 100%!")
        QMessageBox.information(self, "Thành công", "Đã cài đặt thành công APK Super Proxy & Helper cho các điện thoại đã chọn!")

    def get_selected_devices(self):
        selected_serials = []
        for r in range(self.table.rowCount()):
            item_chk = self.table.item(r, 0)
            if item_chk and item_chk.checkState() == Qt.CheckState.Checked:
                selected_serials.append(self.table.item(r, 1).text())
        return selected_serials

    def save_selected_devices(self):
        selected_serials = self.get_selected_devices()
        if not selected_serials:
            QMessageBox.warning(self, "Chú ý", "Vui lòng tick chọn ít nhất 1 điện thoại để sử dụng!")
            return

        # Lưu danh sách serials được chọn vào file config json
        import json
        with open("selected_devices.json", "w", encoding="utf-8") as f:
            json.dump(selected_serials, f, ensure_ascii=False, indent=4)

        QMessageBox.information(self, "Thành công", f"Đã lưu xác nhận {len(selected_serials)} điện thoại sẽ sử dụng chạy tương tác!")
        self.accept()
