# TÀI LIỆU ĐẶC TẢ KIẾN TRÚC & LUỒNG VẬN HÀNH TOÀN DIỆN HỆ THỐNG PHONE FARM
## PHÂN TÍCH CHUYÊN SÂU DỰ ÁN GỐC MAXPHONEFARM (v23.06.20) & BLUEPRINT TÁI CẤU TRÚC THẾ HỆ MỚI (CROSS-PLATFORM MAC/WIN)

---

## MỤC LỤC
1. [TỔNG QUAN VÀ MỤC TIÊU KIẾN TRÚC](#1-tổng-quan-và-mục-tiêu-kiến-trúc)
2. [KIẾN TRÚC TỔNG THỂ HỆ THỐNG (SYSTEM ARCHITECTURE)](#2-kiến-trúc-tổng-thể-hệ-thống)
3. [LÕI ĐIỀU KHIỂN THIẾT BỊ & PHẦN CỨNG (DEVICE & HARDWARE LAYER)](#3-lõi-điều-khiển-thiết-bị--phần-cứng)
4. [HỆ THỐNG CƠ SỞ DỮ LIỆU & QUẢN TRỊ TÀI KHOẢN (DATABASE SCHEMA)](#4-hệ-thống-cơ-sở-dữ-liệu--quản-trị-tài-khoản)
5. [HỆ THỐNG MẠNG & XOAY PROXY ĐA NHÀ CUNG CẤP (PROXY & NETWORK LAYER)](#5-hệ-thống-mạng--xoay-proxy-đa-nhà-cung-cấp)
6. [ĐẶC TẢ CHI TIẾT 90 MODULE HÀNH ĐỘNG (90 ACTION MODULES)](#6-đặc-tả-chi-tiết-90-module-hành-động)
7. [LUỒNG VẬN HÀNH THỰC THI TOÀN VÒNG ĐỜI (END-TO-END WORKFLOW)](#7-luồng-vận-hành-thực-thi-toàn-vòng-đời)
8. [CƠ CHẾ PHÒNG CHỐNG CHECKPOINT & BẢO VỆ TÀI KHOẢN (ANTI-DETECTION)](#8-cơ-chế-phòng-chống-checkpoint--bảo-vệ-tài-khoản)
9. [KHUNG SƯỜN & LỘ TRÌNH PHÁT TRIỂN HỆ THỐNG MỚI (NEXT-GEN BLUEPRINT)](#9-khung-sườn--lộ-trình-phát-triển-hệ-thống-mới)

---

## 1. TỔNG QUAN VÀ MỤC TIÊU KIẾN TRÚC

### 1.1. Bối cảnh dự án gốc
* **MaxPhoneFarm** là giải pháp nuôi và tự động hóa tài khoản mạng xã hội (tập trung vào Facebook cá nhân, Fanpage, Hội nhóm, Video Reels) trên dàn điện thoại Android thật kết nối qua cổng USB / Wi-Fi.
* Bản gốc được viết bằng **C# (.NET Framework 4.8 / WinForms)**, phụ thuộc chặt vào Windows API, giao diện WinForms cổ điển và xử lý đa luồng qua `Thread`/`BackgroundWorker` truyền thống.

### 1.2. Mục tiêu tái cấu trúc (Next-Gen Phone Farm)
1. **Chạy đa nền tảng độc lập (Cross-Platform):** Chạy mượt mà trên **macOS (Apple Silicon M-series)**, **Windows 10/11**, và **Linux Server (Headless/Docker)** từ đúng một bộ mã nguồn duy nhất.
2. **Hiệu năng cao & Tiết kiệm tài nguyên:** Điều khiển đồng thời 20 – 100+ thiết bị với độ trễ thấp (<30ms), tiêu thụ CPU/RAM cực thấp thông qua kiến trúc **Asynchronous I/O (Python Asyncio / Go)** và **Pure ADB TCP Sockets**.
3. **Stream màn hình mượt mà (Ultra-Low Latency):** Truyền hình ảnh thời gian thực 60fps qua **Scrcpy Core / WebRTC / H.264** thay cho việc chụp ảnh tĩnh từng khung (`screencap`) chậm chạp.
4. **Tích hợp Trí tuệ nhân tạo (AI-Driven Automation):** 
   - Nhận diện giao diện thông minh bằng **AI Vision (YOLO / OCR)** thay vì tọa độ cứng hoặc XPath tĩnh.
   - Tự động sinh nội dung bài viết, bình luận, và trả lời tin nhắn hội thoại tự nhiên 100% bằng **LLM (Hermes / GPT / Claude)**.

---

## 2. KIẾN TRÚC TỔNG THỂ HỆ THỐNG (SYSTEM ARCHITECTURE)

```
+-----------------------------------------------------------------------------------------------+
|                       LỚP GIAO DIỆN ĐIỀU KHIỂN (FRONTEND DASHBOARD)                           |
|       - Công nghệ: Flutter Desktop / Web  HOẶC  React + TypeScript + Vite + Tailwind / Tauri  |
|       - Chức năng: Quản lý thiết bị Grid View, Thiết kế kịch bản kéo thả, Quản lý tài khoản  |
+-----------------------------------------------------------------------------------------------+
                                               │ (WebSocket RPC & REST API JSON)
                                               ▼
+-----------------------------------------------------------------------------------------------+
|                      LỚP LÕI ĐIỀU PHỐI TRUNG TÂM (CORE ORCHESTRATION ENGINE)                  |
|       - Công nghệ: Python 3.12 (FastAPI + Asyncio)  HOẶC  Golang (Goroutines + Channels)      |
|       - Thành phần: Task Scheduler, Device Pool Manager, Account Pool, Proxy Pool Leaser      |
+-----------------------------------------------------------------------------------------------+
        │                                  │                                  │
        ▼                                  ▼                                  ▼
+-----------------------+      +-----------------------+      +-------------------------------+
| DEVICE CONTROL BRIDGE |      |   NETWORK & PROXY     |      | DATA & PERSISTENCE LAYER      |
+-----------------------+      +-----------------------+      +-------------------------------+
| - Pure ADB Socket     |      | - Rotating Proxy APIs |      | - SQLite / PostgreSQL         |
| - Scrcpy H.264 Stream |      | - Static HTTP/SOCKS5  |      | - Account Creds, 2FA, Cookies |
| - AdbKeyboard IME     |      | - XProxy / 4G Dongle  |      | - Script Pipelines & Actions  |
| - Hardware Changer    |      | - IP Lease & Cooldown |      | - Execution Logs & Stats      |
+-----------------------+      +-----------------------+      +-------------------------------+
        │                                                                     │
        ▼                                                                     ▼
+-----------------------------------------------------------------------------------------------+
|                       THIẾT BỊ VẬT LÝ & HỆ ĐIỀU HÀNH ANDROID (FARM HARDWARE)                 |
|   - 10 - 100+ Điện thoại Android (Samsung, Xiaomi, LG, Android Box, Allwinner Robot...)      |
|   - Giao tiếp qua USB 3.0 Powered Hub hoặc Mạng nội bộ Wi-Fi 5GHz / Ethernet OTG             |
+-----------------------------------------------------------------------------------------------+
```

---

## 3. LÕI ĐIỀU KHIỂN THIẾT BỊ & PHẦN CỨNG (DEVICE & HARDWARE LAYER)

Lớp này kế thừa và nâng cấp các cơ chế điều khiển của module gốc `AC28BD29.cs`:

### 3.1. Giao tiếp ADB Direct Socket
* Không tạo process con `subprocess.run("adb -s ...")` lặp đi lặp lại (gây tràn bộ nhớ và nghẽn CPU khi chạy nhiều máy).
* Mở trực tiếp kết nối TCP Socket tới `127.0.0.1:5037` (ADB Server) và gửi trực tiếp các gói lệnh:
  - `input tap <x> <y>`: Chạm tọa độ ngẫu nhiên trong vùng nút bấm (Human-like Random Offset ±3px).
  - `input swipe <x1> <y1> <x2> <y2> <duration>`: Vuốt màn hình mô phỏng gia tốc ngón tay theo đường cong Bezier.
  - `input keyevent <keycode>`: `KEYCODE_BACK` (4), `KEYCODE_HOME` (3), `KEYCODE_APP_SWITCH` (187).
  - `am start -n <package>/<activity>`: Khởi chạy trực tiếp ứng dụng Facebook (`com.facebook.katana` hoặc `com.facebook.lite`).
  - `pm clear <package>`: Xóa trắng dữ liệu ứng dụng trước khi đổi acc mới.

### 3.2. Bộ gõ Tiếng Việt `AdbKeyboard`
* **Vấn đề:** Lệnh `input text` của Android không hỗ trợ ký tự Unicode có dấu (Tiếng Việt, icon emoji) và thường làm mất dấu/sai chữ.
* **Giải pháp chuẩn:**
  1. Cài đặt sẵn APK `AdbKeyboard.apk` vào thiết bị.
  2. Kích hoạt bàn phím: `ime set com.android.adbkeyboard/.AdbIME`.
  3. Gửi văn bản trực tiếp qua Broadcast Intent:
     ```bash
     am broadcast -a ADB_INPUT_TEXT --es msg "Chào bạn! Đây là nội dung test có dấu."
     ```
  4. Hỗ trợ xóa text nhanh: `am broadcast -a ADB_CLEAR_TEXT`.

### 3.3. Xử lý Thị giác & Nhận diện Giao diện (Vision & UI Inspector)
Hệ thống sử dụng cơ chế lai 3 tầng (Hybrid 3-Tier Resolution):
1. **Tầng 1 - Cây giao diện UiAutomator (Nhanh nhất):** Dump XML layout (`/dev/null` hoặc qua local port) để tìm phần tử qua thuộc tính `text`, `content-desc`, `resource-id` hoặc `XPath`.
2. **Tầng 2 - Khớp mẫu hình ảnh OpenCV (Độ tin cậy cao):** Sử dụng hàm `Cv2.MatchTemplate` với thuật toán `CCoeffNormed` (ngưỡng tương đồng `0.92 - 0.95`) để tìm kiếm các icon Facebook (Thích, Bình luận, Chia sẻ, Theo dõi, Thông báo) khi Facebook làm mờ/ẩn ID.
3. **Tầng 3 - OCR & AI Vision (Dự phòng thông minh):** Sử dụng PaddleOCR / EasyOCR / YOLO để đọc văn bản và nút bấm khi giao diện Facebook thay đổi vị trí.

### 3.4. Module Fake Thông Tin Thiết Bị (Hardware Identity Changer)
* Gọi API của công cụ `MaxChanger` hoặc module Xposed/LSPosed (`com.minsoftware.maxchanger/.AdbCaller`) để thay đổi danh tính phần cứng sau mỗi lần đổi tài khoản:
  - `Android ID` (`settings put secure android_id <new_id>`)
  - `IMEI / MEID / Serial Number`
  - `MAC Address Wi-Fi / Bluetooth`
  - `Device Model / Brand / Build Fingerprint`
  - `Google Advertising ID (GAID)`

---

## 4. HỆ THỐNG CƠ SỞ DỮ LIỆU & QUẢN TRỊ TÀI KHOẢN (DATABASE SCHEMA)

Cơ sở dữ liệu SQLite (`data.sqlite`) được thiết kế chuẩn hóa và tối ưu hóa truy vấn:

```sql
-- 1. BẢNG QUẢN LÝ THƯ MỤC / DANH MỤC TÀI KHOẢN
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1
);

-- 2. BẢNG QUẢN LÝ TÀI KHOẢN FACEBOOK (ACCOUNTS)
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_file INTEGER REFERENCES files(id) ON DELETE CASCADE,
    uid TEXT UNIQUE NOT NULL,
    password TEXT,
    two_fa TEXT,           -- Secret key 16/32 ký tự để sinh mã OTP
    cookie TEXT,           -- Chuỗi cookie đăng nhập c_user=...; xs=...
    token TEXT,            -- Token EAAB/EAAA phục vụ truy vấn Graph API ngầm
    email TEXT,
    passmail TEXT,
    device_id TEXT,        -- Serial thiết bị Android đang gán tài khoản này
    proxy TEXT,            -- Proxy riêng chỉ định (IP:Port:User:Pass)
    useragent TEXT,
    status TEXT,           -- Trạng thái (Live, Checkpoint 282, Checkpoint 956, Sai Pass, Die)
    info TEXT,             -- Tên, Ngày sinh, Giới tính, Bạn bè, Nhóm
    friends_count INTEGER DEFAULT 0,
    groups_count INTEGER DEFAULT 0,
    interact_time DATETIME,-- Lần cuối cùng thực thi tương tác
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. BẢNG QUẢN LÝ KỊCH BẢN TƯƠNG TÁC (SCRIPTS)
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. BẢNG CHI TIẾT HÀNH ĐỘNG TRONG KỊCH BẢN (SCRIPT_ACTIONS)
CREATE TABLE IF NOT EXISTS script_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER REFERENCES scripts(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- Tên module hành động (vd: fHDTuongTacNewsfeed)
    action_order INTEGER NOT NULL, -- Thứ tự chạy (1, 2, 3...)
    settings_json TEXT NOT NULL   -- Toàn bộ tham số cấu hình (delay, like, comment, UID list)
);

-- 5. BẢNG QUẢN LÝ DANH SÁCH THIẾT BỊ PHẦN CỨNG (DEVICES)
CREATE TABLE IF NOT EXISTS devices (
    serial TEXT PRIMARY KEY,
    model TEXT,
    android_version TEXT,
    ip_address TEXT,
    port INTEGER DEFAULT 5555,
    status TEXT DEFAULT 'Offline', -- Online, Running, Error, Offline
    current_account_uid TEXT,
    battery_level INTEGER,
    last_seen DATETIME
);
```

---

## 5. HỆ THỐNG MẠNG, XOAY PROXY ĐA NHÀ CUNG CẤP & ĐỔI IP QUA SIM (NETWORK & IP ISOLATION)

Hệ thống Phone Farm chuyên nghiệp hỗ trợ 2 cơ chế đổi IP chính: **(1) Đổi IP thông qua SIM 3G/4G trên từng điện thoại (Chế độ máy bay)** và **(2) Gán Proxy riêng cho từng tài khoản qua ứng dụng Proxy/VPN hoặc Lệnh Hệ thống Android**.

```
                           +-----------------------------------+
                           |      IP & Network Controller      |
                           +-----------------------------------+
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
   [CƠ CHẾ 1: ĐỔI IP QUA SIM 3G/4G TRÊN MÁY]               [CƠ CHẾ 2: GÁN PROXY CHO TỪNG NICK]
   - Bật/Tắt Chế độ máy bay (Airplane Mode)                - Proxy không User/Pass: `settings global`
   - Tắt Wi-Fi, chỉ dùng Data di động qua SIM              - Proxy có User/Pass: Ứng dụng CollegeProxy/SuperProxy
   - Đổi IP cấp tốc 3-5 giây cho mỗi lần đổi Nick          - Proxy xoay API (MinProxy, TMProxy, Tinsoft, XProxy)
```

---

### 5.1. CƠ CHẾ 1: ĐỔI IP QUA SIM 3G/4G TRÊN ĐIỆN THOẠI (AIRPLANE MODE RESET)

Đây là phương pháp nuôi nick hiệu quả và sạch nhất vì IP 4G của nhà mạng (Viettel, VinaPhone, MobiFone) có điểm uy tín (Trust Score) cao nhất đối với Facebook.

#### Luồng hoạt động chi tiết khi chạy từng nick qua SIM:
1. **Tắt kết nối Wi-Fi:**
   ```bash
   adb shell su -c 'svc wifi disable'
   ```
2. **Kích hoạt Dữ liệu di động (Mobile Data):**
   ```bash
   adb shell su -c 'svc data enable'
   ```
3. **Thực hiện đổi IP qua Chế độ máy bay (Bật -> Chờ 2s -> Tắt):**
   * *Bật Airplane Mode:*
     ```bash
     adb shell settings put global airplane_mode_on 1
     adb shell su -c am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true
     ```
   * *Tắt Airplane Mode để nhận IP mới từ trạm phát sóng:*
     ```bash
     adb shell settings put global airplane_mode_on 0
     adb shell su -c am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false
     ```
4. **Kiểm tra kết nối mạng và đối soát IP mới:**
   * Gửi request kiểm tra IP qua `https://api.myip.com/` để xác nhận IP đã được làm mới trước khi mở app Facebook.

---

### 5.2. CƠ CHẾ 2: GÁN PROXY RIÊNG KHI CHẠY TỪNG TÀI KHOẢN

Khi mỗi tài khoản Facebook được gán 1 Proxy cố định (`IP:Port` hoặc `IP:Port:User:Pass`), hệ thống sẽ tự động gán Proxy trước khi mở Facebook và gỡ Proxy ngay sau khi kết thúc phiên.

#### A. Đối với Proxy không có User/Pass (Dạng `IP:Port`):
Sử dụng trực tiếp lệnh hệ thống Android (không cần mở app ngoài):
```bash
# Gán Proxy:
adb shell settings put global http_proxy IP:PORT

# Gỡ Proxy khi xong phiên:
adb shell settings put global http_proxy :0
adb shell settings delete global http_proxy
adb shell settings delete global global_http_proxy_host
adb shell settings delete global global_http_proxy_port
```

#### B. Đối với Proxy có xác thực User/Password (Dạng `IP:Port:User:Pass`):
Android thuần không hỗ trợ auth trong settings, do đó hệ thống tự động cài đặt và điều khiển ứng dụng Proxy chuyên dụng:

1. **Ứng dụng `CollegeProxy` (`com.cell47.College_Proxy`) / `SuperProxy`:**
   * Tự động cài đặt file `collegeproxy.apk` vào máy nếu chưa có:
     ```bash
     adb install -r ./app/collegeproxy.apk
     ```
   * Mở ứng dụng và tự động điền thông số qua UI / ADB Intent:
     - Điền `Proxy Host` = `IP`
     - Điền `Proxy Port` = `Port`
     - Điền `Username` = `User`
     - Điền `Password` = `Pass`
   * Bấm nút **START SERVICE** để kích hoạt mạng VPN Proxy toàn máy.
   * Khi hoàn tất phiên làm việc: Tự động bấm **STOP PROXY SERVICE** và dọn dẹp data `pm clear com.cell47.College_Proxy`.

2. **Ứng dụng Drony / Postern / V2Ray (Dành cho SOCKS5 & Shadowsocks):**
   * Hỗ trợ cấu hình tunnel routing chỉ proxy riêng cho package Facebook (`com.facebook.katana` / `com.facebook.lite`).

---

### 5.3. DANH SÁCH CÁC NHÀ CUNG CẤP PROXY XOAY API TÍCH HỢP SẴN

Hệ thống tích hợp sẵn endpoint và cơ chế lấy IP mới tự động cho 6 nhà cung cấp phổ biến nhất:

1. **MinProxy (Việt Nam):**
   * Lấy IP hiện tại: `http://dash.minproxy.vn/api/rotating/v1/proxy/get-current-proxy?api_key={key}`
   * Đổi IP mới: `http://dash.minproxy.vn/api/rotating/v1/proxy/get-new-proxy?api_key={key}`
2. **TMProxy (Việt Nam):**
   * Đổi IP mới (POST JSON): `https://tmproxy.com/api/proxy/get-new-proxy` (Body: `{"api_key": "{key}"}`)
3. **Tinsoft Proxy:**
   * Đổi IP: `http://proxy.tinsoftsv.com/api/changeProxy.php?key={key}&location={loc}`
4. **ShopLike Proxy:**
   * Đổi IP: `http://proxy.shoplike.vn/Api/getNewProxy?access_token={token}`
5. **ProxyV6:**
   * Reset IP thủ công: `https://api.proxyv6.net/api/reset-ip-manual?api_key={key}`
6. **Dàn USB 4G Hub / XProxy Server:**
   * Reset từng cổng USB 4G: `http://{xproxy_ip}:{port}/reset?proxy={proxy_name}`
7. **Dcom 4G HiLink (Huawei):**
   * Reset mạng: `http://192.168.8.1/api/dialup/mobile-dataswitch` (gửi payload toggle tắt/bật data).

---

## 6. ĐẶC TẢ CHI TIẾT 90 MODULE HÀNH ĐỘNG (90 ACTION MODULES)

Toàn bộ 90 hành động được chuẩn hóa thành 7 nhóm chức năng với đầy đủ tham số đầu vào và luồng thực thi:

### NHÓM 1: BẢNG TIN, TƯỜNG NHÀ & THÔNG BÁO (13 ACTIONS)
1. **`fHDBaiVietNewsfeed`:** Lướt bảng tin theo số lượng bài viết (`SoLuongFrom` - `SoLuongTo`). Tự động Like, thả Tym, lướt đọc bình luận, đăng comment theo nội dung mẫu (hỗ trợ spin text `{A|B|C}`).
2. **`fHDBaiVietNewsfeedv2`:** Lướt bảng tin theo khoảng thời gian (`TimeFrom` - `TimeTo` giây). Tương tác ngẫu nhiên theo xác suất người dùng thật.
3. **`fHDTuongTacNewsfeed`:** Lướt Newsfeed kết hợp xem bài viết dài, click "Xem thêm", dừng lại đọc bình luận trước khi thả cảm xúc.
4. **`fHDTuongTacWall`:** Truy cập tường trang cá nhân của chính mình, cuộn xem lịch sử bài đăng cũ, like lại bài của mình để tăng tương tác.
5. **`fHDBaiVietBanBe`:** Tự động vào trang cá nhân của danh sách bạn bè, like và bình luận bài viết mới nhất trên tường bạn bè.
6. **`fHDTuongTacBaiVietChiDinh`:** Nhập danh sách ID bài viết Facebook cần tương tác, tự động truy cập link và thực hiện Like/Tym/Bình luận/Chia sẻ.
7. **`fHDTuongTacBaiVietTuKhoa`:** Tìm kiếm bài viết trên Facebook theo từ khóa (hashtag), cuộn kết quả và tương tác các bài viết tìm được.
8. **`fHDTuongTacBaiVietIA`:** Tương tác với các bài viết dạng Instant Article (bài báo nhanh) và click tương tác quảng cáo hợp lệ.
9. **`fHDDocThongBao`:** Mở tab chuông thông báo, click đọc `N` thông báo mới nhất để xóa badge đỏ, tự động mở chi tiết bài viết trong thông báo.
10. **`fHDNghiGiaiLao`:** Chèn khoảng thời gian nghỉ ngơi (`DelayFrom` - `DelayTo` giây) giữa các hành động để không bị hệ thống AI Facebook đánh dấu là spam máy móc.
11. **`fHDBatCheDoChuyenNghiep`:** Tự động vào Cài đặt Profile và kích hoạt "Bật Chế độ chuyên nghiệp" (Professional Mode) cho tài khoản.
12. **`fHDDanhGiaPage`:** Vào Fanpage chỉ định, chọn tab Đánh giá (Review), bấm Đề xuất 5 sao và viết bài nhận xét kèm hình ảnh.
13. **`fHDChiaSeLivestream`:** Lấy link livestream đang phát, tự động chia sẻ về tường cá nhân hoặc chia sẻ vào các nhóm không kiểm duyệt.

---

### NHÓM 2: VIDEO, WATCH, REEL, STORY & LIVESTREAM (14 ACTIONS)
14. **`fHDXemWatch`:** Mở tab Video Watch, xem video ngẫu nhiên trong khoảng thời gian quy định, tự động Like và bình luận video.
15. **`fHDXemWatchTheoTuKhoa`:** Tìm kiếm video Watch theo chủ đề (ví dụ: "Review xe hơi", "Nấu ăn"), xem video tìm được để tạo tệp sở thích.
16. **`fHDXemWatch_Old`:** Thuật toán xem Watch phiên bản cổ điển (hỗ trợ các dòng máy Android đời cũ).
17. **`fHDXemReel`:** Mở tab Facebook Reels, vuốt xem từng video ngắn (`TimeFrom` - `TimeTo`), thả tim và follow kênh sáng tạo.
18. **`fHDTuongTacReelChiDinh`:** Xem đúng video Reel theo danh sách link/ID cung cấp và gửi bình luận seeding.
19. **`fHDTuongTacReelTuKhoa`:** Tìm kiếm Reels theo hashtag/từ khóa và tương tác.
20. **`fHDDangReel`:** Tự động lấy video trong thư mục máy tính, copy vào điện thoại, mở giao diện tạo Reel, viết caption, gắn hashtag và bấm Đăng.
21. **`fHDXoaReel`:** Quét danh sách Reels đã đăng trên trang cá nhân và xóa các video ít view/video vi phạm.
22. **`fHDXemStory`:** Mở tab Story của bạn bè ở đầu Newsfeed, xem lần lượt các tin, thả biểu tượng cảm xúc (Thương thương, Wow, Tim).
23. **`fHDDangStory`:** Đăng tin Story dạng hình ảnh hoặc video ngắn kèm văn bản/âm nhạc thịnh hành.
24. **`fHDTuongTacVideo`:** Tương tác chuyên sâu với các bài đăng chứa video trên tường hoặc nhóm.
25. **`fHDTuongTacLivestream`:** Vào xem Livestream bán hàng, giữ mắt xem trong `N` phút, tự động spam bình luận đặt hàng theo cú pháp `{SĐT|Mã SP}`.
26. **`fHDSeedingByVideo`:** Seeding bình luận kèm tệp video/ảnh mẫu vào bài viết.
27. **`fHDReportVideo`:** Tự động gửi báo cáo vi phạm bản quyền hoặc nội dung xấu đối với video chỉ định.

---

### NHÓM 3: HỘI NHÓM FACEBOOK (GROUPS) (9 ACTIONS)
28. **`fHDThamGiaNhomGoiY`:** Tham gia các nhóm do Facebook đề xuất trên tab Nhóm (`SoLuongFrom` - `SoLuongTo`).
29. **`fHDThamGiaNhomTuKhoa`:** Tìm kiếm nhóm theo từ khóa ngách, tự động trả lời các câu hỏi kiểm duyệt (dùng danh sách câu trả lời chuẩn bị trước).
30. **`fHDThamGiaNhomUid`:** Tham gia nhóm theo danh sách ID nhóm chỉ định, tự động vượt câu hỏi duyệt và chấp nhận quy tắc nhóm.
31. **`fHDBaiVietNhom`:** Lướt xem bài viết trong các nhóm đã tham gia, like và bình luận xây dựng tương tác thành viên tích cực.
32. **`fHDTuongTacNhom` & `fHDTuongTacNhomV2`:** Thuật toán tương tác nhóm tối ưu theo thuật toán mới của Facebook.
33. **`fHDDangBaiNhom`:** Tự động đăng bài viết (kèm tối đa 4 ảnh) vào danh sách các nhóm đã tham gia (ưu tiên nhóm duyệt bài tự động).
34. **`fHDSpamNhom`:** Đăng bài/bình luận hàng loạt vào nhóm theo tệp nội dung spin.
35. **`fHDMoiBanBeVaoNhom`:** Mời toàn bộ bạn bè của tài khoản tham gia vào nhóm của Đại Ca để xây dựng cộng đồng.
36. **`fHDRoiNhom`:** Tự động quét và thoát khỏi các nhóm bị đổi tên, nhóm rác hoặc nhóm có bài đăng bị duyệt quá lâu.
37. **`fHDTaoNhom`:** Tự động tạo nhóm Facebook mới (đặt tên nhóm, chọn quyền riêng tư công khai/kín, mời bạn bè ban đầu).

---

### NHÓM 4: BẠN BÈ & MỞ RỘNG TỆP KHÁCH HÀNG (19 ACTIONS)
38. **`fHDKetBanGoiY`:** Gửi lời mời kết bạn cho những người trong mục "Những người bạn có thể biết" (ưu tiên người có bạn chung, tên có dấu).
39. **`fHDKetBanNewfeed`:** Quét bài viết trên bảng tin và gửi lời mời kết bạn với những người like/comment bài viết đó.
40. **`fHDKetBanTepUid` & `fHDKetBanTepUidNew`:** Gửi lời mời kết bạn chính xác theo tệp danh sách UID khách hàng tiềm năng đã quét từ trước.
41. **`fHDKetBanTheoTuKhoa`:** Tìm kiếm người dùng theo tên/từ khóa chức danh và kết bạn.
42. **`fHDKetBanThanhVienNhom`:** Mở danh sách thành viên của một nhóm mục tiêu và gửi kết bạn với các thành viên mới tham gia.
43. **`fHDKetBanVoiBanBeCuaUid` & `fHDKetBanVoiBanCuaBanBe`:** Quét tệp bạn bè công khai của một tài khoản KOL/đối thủ và kết bạn với tệp đó.
44. **`fHDXacNhanKetBan`:** Tự động đồng ý các lời mời kết bạn gửi đến tài khoản (lọc điều kiện bạn chung, có avatar thật).
45. **`fHDHuyLoiMoiKetBan`:** Tự động hủy các lời mời kết bạn đã gửi đi quá 7 ngày mà đối phương không đồng ý để không bị đầy giới hạn 1000 lời mời.
46. **`fHDHuyKetBan`:** Lọc và hủy kết bạn với những người không tương tác hoặc tài khoản bị khóa/bị checkpoint.
47. **`fHDChocBanBe`:** Sử dụng tính năng "Chọc" (Poke) bạn bè ngẫu nhiên để kích thích họ bấm vào xem profile của mình.
48. **`fHDChucMungSinhNhat`:** Quét danh sách bạn bè có sinh nhật hôm nay, tự động gửi tin nhắn hoặc đăng lên tường lời chúc mừng sinh nhật ấm áp.
49. **`fHDDongBoDanhBa`:** Nạp danh bạ số điện thoại ảo vào máy Android (`contacts2.db`), kích hoạt tính năng "Đồng bộ danh bạ" trên Facebook để thuật toán Facebook gợi ý toàn bộ chủ nhân số điện thoại đó.
50. **`fHDBuffFollowUID`:** Sử dụng dàn tài khoản con đồng loạt bấm Theo dõi (Follow) cho một Profile chính của Đại Ca.
51. **`fHDMoiBanBeLikePage`:** Mời danh sách bạn bè Like trang Fanpage của mình.
52. **`fHDSpamBanBe`:** Tương tác liên hoàn trên tường của bạn bè thân thiết.

---

### NHÓM 5: FANPAGE, SEEDING & TƯƠNG TÁC CHỈ ĐỊNH (11 ACTIONS)
53. **`fHDBuffLikePage`:** Dàn tài khoản tự động truy cập link Fanpage và bấm Thích trang.
54. **`fHDBuffFollowLikePage`:** Kết hợp vừa bấm Thích vừa bấm Theo dõi Fanpage ở chế độ Yêu thích.
55. **`fHDBaiVietFanpage`:** Tương tác lướt xem các bài viết mới trên Fanpage của doanh nghiệp/đối tác.
56. **`fHDTuongTacPage`:** Tương tác tổng hợp trên Fanpage mục tiêu.
57. **`fHDTaoPage`:** Tự động lập Fanpage vệ tinh mới (đặt tên trang, chọn danh mục, mô tả, ảnh đại diện).
58. **`fHDDangBaiPage`:** Đăng bài viết kèm hashtag lên các Fanpage do tài khoản nắm quyền quản trị viên/biên tập viên.
59. **`fHDChaySeeding`:** Điều phối dàn tài khoản vào một bài viết bán hàng chỉ định để comment mồi, khen sản phẩm, hỏi giá tạo hiệu ứng đám đông.
60. **`fHDBuffLikeComment`:** Thả cảm xúc Like/Tym/Haha cho một bình luận cụ thể để đẩy bình luận đó lên Top 1 bài viết.
61. **`fHDSeedingEvents`:** Tự động bấm "Tham gia" hoặc "Quan tâm" các sự kiện do trang tổ chức.
62. **`fHDBuffTinNhanProfile`:** Gửi tin nhắn mồi vào hộp thư Fanpage để tăng tỷ lệ phản hồi tin nhắn của Page.
63. **`fHDNhanTinPage`:** Nhắn tin trực tiếp tới Fanpage theo kịch bản hỏi mua hàng.

---

### NHÓM 6: TIN NHẮN & CHĂM SÓC KHÁCH HÀNG (MESSENGER / DM) (5 ACTIONS)
64. **`fHDNhanTinBanBe`:** Nhắn tin hàng loạt cho danh sách bạn bè với nội dung cá nhân hóa (gọi tên bạn bè `{name}`).
65. **`fHDPhanHoiTinNhan`:** Tự động kiểm tra hòm thư Messenger, đọc tin nhắn mới từ khách hàng và tự động phản hồi theo từ khóa hoặc chuyển tiếp cho AI trả lời.
66. **`fHDSpamNewfeed`:** Đăng bài tiếp thị nhanh chóng lên Newfeed cá nhân.
67. **`fHDDangBaiTuong`:** Đăng bài viết chính thức lên tường cá nhân (hỗ trợ đăng kèm ảnh, chọn phông nền màu sắc Background status, gắn tag bạn bè).
68. **`fHDShareBaiNangCao`:** Chia sẻ bài viết từ nguồn chỉ định về tường nhà hoặc các nhóm với caption tùy biến.

---

### NHÓM 7: BẢO MẬT, QUẢN TRỊ TÀI KHOẢN & TIỆN ÍCH (19 ACTIONS)
69. **`fHDDoiMatKhau`:** Tự động vào Cài đặt bảo mật, đổi sang mật khẩu mới ngẫu nhiên (hoặc mật khẩu chỉ định) và cập nhật ngay vào database SQLite.
70. **`fHDDoiTen`:** Đổi tên hiển thị Facebook theo danh sách họ tên chuẩn Việt Nam.
71. **`fHDCapNhatThongTin`:** Cập nhật thông tin tiểu sử (Bio), trường học cấp 3, đại học, quê quán, thành phố hiện tại, tình trạng quan hệ (Độc thân/Đã kết hôn).
72. **`fHDUpAvatar`:** Lấy ảnh trong thư mục chỉ định trên PC, copy vào điện thoại, đổi avatar tài khoản và tự động xóa ảnh đã dùng để tránh trùng lặp.
73. **`fHDUpCover`:** Đổi ảnh bìa trang cá nhân.
74. **`fHDAddMail`:** Thêm email phụ (Hotmail/Mail domain) vào tài khoản Facebook, tự động đọc mã OTP từ hộp thư qua giao thức IMAP (`ImapHelper.cs`) để xác nhận và đặt làm email chính.
75. **`fHDXoaSdt`:** Gỡ bỏ các số điện thoại rác/SIM thuê đã hết hạn khỏi tài khoản để tránh bị người khác khôi phục tài khoản.
76. **`fHDOnOff2FA`:** Tự động bật mã xác thực 2 lớp (Two-Factor Authentication), lấy chuỗi Secret Key 16/32 ký tự, sinh mã OTP 6 số xác nhận và lưu key 2FA vào database.
77. **`fHDDangXuatThietBiCu`:** Đăng xuất khỏi toàn bộ các phiên đăng nhập trên trình duyệt/thiết bị cũ để bảo vệ tài khoản khi mới mua via/clone về.
78. **`fHDXoaThietBiTinCay`:** Xóa sạch danh sách thiết bị tin cậy cũ.
79. **`fHDVerifyAccount`:** Tự động xử lý các màn hình xác minh danh tính đơn giản khi Facebook yêu cầu.
80. **`fHDKhangSpam`:** Tự động gửi biểu mẫu kháng nghị khi tài khoản bị Facebook chặn tính năng like/comment tạm thời.
81. **`fHDBackupData`:** Tự động tải và sao lưu danh sách bạn bè (tên + avatar), tin nhắn gần nhất và ngày sinh để phục vụ vượt Checkpoint hình ảnh bạn bè (Photo Checkpoint).
82. **`fHDCauHinhTaiKhoan`:** Cấu hình quyền riêng tư tổng thể (ai có thể xem bài viết, ai có thể gửi kết bạn).
83. **`fHDTimKiemGoogle`:** Mở trình duyệt Chrome trên điện thoại, tìm kiếm từ khóa trên Google Search và click vào website mục tiêu để tạo lịch sử duyệt web tự nhiên.
84. **`fHDTruyCapWebsite`:** Truy cập trực tiếp link website ngoài để kích hoạt pixel theo dõi, tạo cookie duyệt web bên thứ ba.
85. **`fHDSpamBaiViet`:** Đăng bài/bình luận nhanh theo tệp dữ liệu.
86. **`fHDTuongTacReelTuKhoa`:** Tìm kiếm Reels theo từ khóa chủ đề.
87. **`fHDSeedingEvents`:** Đăng ký sự kiện.
88. **`fHDReport`:** Báo cáo bài viết/trang vi phạm.
89. **`fHDTuongTacNhomV2`:** Thuật toán tương tác nhóm chuyên sâu.
90. **`fHDBuffFollowLikePage`:** Tương tác toàn diện Fanpage.

---

## 7. LUỒNG VẬN HÀNH THỰC THI TOÀN VÒNG ĐỜI (END-TO-END WORKFLOW)

```
[BƯỚC 1: KHỞI TẠO HỆ THỐNG]
  │- Đọc cấu hình luồng (Thread count, Max concurrent devices).
  │- Khởi tạo kết nối SQLite Database Pool & Proxy Pool.
  │- Quét danh sách thiết bị Android đang cắm qua ADB Socket (`adb devices`).
  ▼
[BƯỚC 2: PHÂN BỔ TÀI KHOẢN & THIẾT BỊ (ALLOCATION LOOP)]
  │- Lấy tài khoản kế tiếp có trạng thái 'Live' và đã đủ thời gian chờ (Cooldown).
  │- Gán tài khoản vào một thiết bị Android đang rảnh rỗi.
  ▼
[BƯỚC 3: THIẾT LẬP MẠNG & XOAY PROXY (NETWORK ISOLATION)]
  │- Kiểm tra loại Proxy (Tĩnh hay Xoay API).
  │- Gọi API lấy IP mới -> Kiểm tra IP qua `https://api.myip.com/`.
  │- Set Proxy cho thiết bị (qua app SuperProxy / Drony / Adb proxy / VpnService).
  ▼
[BƯỚC 4: CHUẨN BỊ MÔI TRƯỜNG THIẾT BỊ (DEVICE PROVISIONING)]
  │- Xóa cache ứng dụng Facebook: `pm clear com.facebook.katana`.
  │- Đổi Device ID (Android ID, IMEI, Model) qua MaxChanger/LSPosed.
  │- Khởi động bàn phím gõ tiếng Việt `AdbIME`.
  ▼
[BƯỚC 5: ĐĂNG NHẬP & BẢO MẬT (AUTHENTICATION & BYPASS)]
  │- Mở app Facebook.
  │- Nhập UID / Password qua ADB Intent.
  │- Nếu yêu cầu mã 2FA: Tự động tính mã TOTP 6 số từ `two_fa secret` qua thuật toán RFC 6238 và điền vào ô xác thực.
  │- Kiểm tra trạng thái đăng nhập (Thành công -> Lưu Cookie mới; Checkpoint -> Ghi nhận trạng thái vào DB).
  ▼
[BƯỚC 6: THỰC THI ĐƯỜNG ỐNG KỊCH BẢN (PIPELINE SCRIPT EXECUTION)]
  │- Duyệt qua từng hành động trong Kịch bản được chọn:
  │    ├── Action 1: Lướt Newsfeed (5-10 phút, Like 3 bài, Comment 1 bài).
  │    ├── Action 2: Nghỉ giải lao ngẫu nhiên (15-30 giây).
  │    ├── Action 3: Xem Reels theo từ khóa (3-5 phút).
  │    └── Action 4: Kết bạn theo tệp UID mục tiêu (Gửi 5 lời mời).
  ▼
[BƯỚC 7: KẾT THÚC PHIÊN & GIẢI PHÓNG TÀI NGUYÊN]
  │- Trích xuất Cookie / Token mới nhất lưu lại vào SQLite.
  │- Cập nhật thời gian tương tác `interact_time = NOW()`.
  │- Đóng app Facebook, ngắt Proxy, giải phóng thiết bị để tiếp nhận tài khoản kế tiếp.
```

---

## 8. CƠ CHẾ PHÒNG CHỐNG CHECKPOINT & BẢO VỆ TÀI KHOẢN (ANTI-DETECTION)

Hệ thống kế thừa và bổ sung các kỹ thuật chống phát hiện tiên tiến nhất:
1. **Human-like Bezier Gesture Simulation:** Các thao tác vuốt không đi theo đường thẳng tuyệt đối mà có độ cong ngẫu nhiên và tốc độ thay đổi gia tốc (mô phỏng đúng hành vi ngón tay người dùng).
2. **Cơ chế Cooldown thông minh:** Mỗi tài khoản sau khi chạy tương tác sẽ được đưa vào hàng đợi nghỉ tối thiểu 6 – 12 tiếng trước khi chạy phiên kế tiếp.
3. **Phân tách Fingerprint tuyệt đối:** Mỗi tài khoản được liên kết cố định với 1 bộ thông tin phần cứng giả lập (Device Profile) và 1 dải IP Proxy riêng biệt, không bao giờ dùng chung 1 IP cùng thời điểm cho 2 tài khoản khác nhau.
4. **Xác thực 2FA OTP tự động:** Xử lý toàn bộ các lớp bảo mật OTP ngầm trong vòng dưới 2 giây bằng thư viện sinh mã `Otp.NET` / `pyotp`.

---

## 9. KHUNG SƯỜN & LỘ TRÌNH PHÁT TRIỂN HỆ THỐNG MỚI (NEXT-GEN BLUEPRINT)

### 9.1. Cấu trúc thư mục dự án mới đề xuất (Single Codebase):

```
nextgen-phonefarm/
├── backend/                       # LÕI XỬ LÝ TRUNG TÂM (Python 3.12 / FastAPI / Asyncio)
│   ├── app/
│   │   ├── api/                   # REST API Endpoints (Quản lý Acc, Device, Script, Proxy)
│   │   ├── core/                  # Cấu hình hệ thống, Database Session, Async Tasks
│   │   ├── database/              # SQLite Models, Migrations (SQLAlchemy / Tortoise-ORM)
│   │   ├── devices/               # Lõi ADB Socket Bridge, Scrcpy Streaming, Keyboards
│   │   ├── actions/               # Triển khai 90 Action Modules (Kế thừa từ phân tích fHD)
│   │   │   ├── newsfeed/
│   │   │   ├── video_reels/
│   │   │   ├── groups/
│   │   │   ├── friends/
│   │   │   ├── fanpage/
│   │   │   └── security/
│   │   ├── proxy/                 # Quản lý và tích hợp 10+ nhà cung cấp Proxy
│   │   └── ai_vision/             # YOLOv8 + OCR + LLM Text Generator
│   ├── requirements.txt
│   └── main.py
│
├── frontend/                      # GIAO DIỆN NGƯỜI DÙNG HIỆN ĐẠI (Flutter Desktop / Web)
│   ├── lib/
│   │   ├── screens/               # Device Grid View, Account Manager, Script Builder
│   │   ├── widgets/               # Scrcpy Screen Canvas, Log Viewers, Metric Charts
│   │   ├── providers/             # State Management (Riverpod / Bloc)
│   │   └── services/              # WebSocket Client, REST Client
│   └── pubspec.yaml
│
└── deploy/                        # BỘ CÀI ĐẶT TỰ ĐỘNG
    ├── macos/                     # Script cài ADB, dependencies, đóng gói .dmg / .app
    ├── windows/                   # Script build .exe Portable cho dàn máy PC
    └── docker-compose.yml         # Chạy Server Headless trên VPS / Mac Mini
```

### 9.2. Lộ trình triển khai 5 giai đoạn:
* **Giai đoạn 1 (Tuần 1):** Xây dựng Backend Core, Device Bridge qua Pure ADB Socket, nhận diện kết nối thiết bị và tích hợp Stream Scrcpy 60fps lên giao diện.
* **Giai đoạn 2 (Tuần 2):** Xây dựng Database SQLite, hoàn thiện module Quản lý Tài khoản (Import/Export Cookie/UID/2FA/Proxy) và Bộ nạp Proxy xoay.
* **Giai đoạn 3 (Tuần 3):** Triển khai 20 Actions nền tảng (Lướt Newsfeed, Xem Reels/Watch, Đăng bài, Kết bạn, Đổi Pass, Bật 2FA).
* **Giai đoạn 4 (Tuần 4):** Triển khai toàn bộ 70 Actions còn lại (Nhóm, Fanpage, Seeding, Tin nhắn Messenger, Kháng Checkpoint).
* **Giai đoạn 5 (Tuần 5):** Tích hợp AI Engine (LLM tạo nội dung bình luận tự động + AI Vision) và đóng gói bản phát hành đa nền tảng (macOS App & Windows Setup).
