# SKILL: MaxPhoneFarm Reborn Pro Agent Controller
Description: Skill hướng dẫn AI Agent (Hermes/Claude/GPT) tự động điều khiển, kiểm tra và quản lý phần mềm MaxPhoneFarm Reborn Pro bằng lệnh CLI JSON API.

---

## 🛠 HƯỚNG DẪN ĐIỀU KHIỂN PHẦN MỀM MAXPHONEFARM CHO AI AGENT

Phần mềm được tích hợp sẵn cổng API dòng lệnh `cli_api.py` trả về định dạng JSON cực kỳ dễ dàng cho AI Agent đọc & xử lý.

### 1. Báo cáo Tổng quan Hệ thống (System Health Check):
Chạy lệnh này để xem tổng số Phone đang cắm, số Nick, số nick Die, số nick đã Backup:
`python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py status`

### 2. Xem Danh Sách Tài Khoản:
- Lấy tất cả nick: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py list_accounts`
- Lọc theo nick DIE/Lỗi: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py list_accounts DIE`

### 3. Thêm / Sửa / Xóa Tài Khoản:
- Thêm nick: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py add_accounts "1000888999|Pass123|2FAKEY|1.2.3.4:8080"`
- Cập nhật Proxy: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py update_account 1000888999 None None "5.6.7.8:8080"`
- Xóa nick: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py delete_account 1000888999`

### 4. Kiểm Tra Trạng Thái (Live/Die & Proxy):
- Check Live 1 nick: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py check_live 1000888999`
- Check Live toàn bộ nick trong Database: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py check_all_live`
- Check Proxy có sống không: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py check_proxy "1.2.3.4:8080"`
- Đổi IP XProxy/Dcom: `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py change_xproxy "http://xproxy-ip:8080/reset"`

### 5. Thực Thi Luồng Tự Động Hóa Phone Farm:
- **Backup phân vùng App FB thành file `.tar.gz`:**
  `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py backup 1000888999`
- **Fake Device Info theo Nick:**
  `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py change_device 1000888999`
- **Tự động Đổi IP -> Fake Device -> Restore Data FB -> Mở App & Nuôi Nick:**
  `python C:/bs_flash/MaxPhoneFarm_Reborn/cli_api.py restore 1000888999`

---

## 📌 THƯ MỤC LƯU TRỮ DỮ LIỆU
- Cơ sở dữ liệu SQLite: `C:\bs_flash\MaxPhoneFarm_Reborn\database.sqlite`
- Thư mục nén phân vùng App (.tar.gz) & Profile Thiết bị: `C:\bs_flash\MaxPhoneFarm_Reborn\profiles\`
- Thư mục chứa các App Trợ Thủ Android (.apk): `C:\bs_flash\MaxPhoneFarm_Reborn\apps\`
