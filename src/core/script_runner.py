import time
import random

class ScriptRunner:
    """
    Module quản lý & điều hành kịch bản nuôi nick / tương tác tự động
    (Tương tác Wall, Xem Reel, Đăng bài, Seeding, Kết bạn)
    """
    def __init__(self, adb_device, log_callback=None):
        self.adb = adb_device
        self.log_callback = log_callback

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(f"[{self.adb.serial}] {msg}")

    def run_tuong_tac_newsfeed(self, time_stay_seconds=30):
        """Kịch bản: Lướt Newsfeed, Thả tim, Đọc comment tự động"""
        self.log("Bắt đầu kịch bản: Lướt Newsfeed...")
        start = time.time()
        while time.time() - start < time_stay_seconds:
            # Swipe lướt ngẫu nhiên từ dưới lên
            self.adb.swipe(500, 1400, 500, 500, duration=random.randint(300, 600))
            time.sleep(random.uniform(2.0, 5.0))
            
            # 20% cơ hội thả tim/like
            if random.random() < 0.2:
                self.log("Like bài viết trên Newsfeed...")
                self.adb.tap(200, 1200) # Tọa độ nút Like tương đối
                time.sleep(1)

    def run_xem_reel(self, time_stay_seconds=30):
        """Kịch bản: Xem Facebook Reels"""
        self.log("Bắt đầu kịch bản: Xem Facebook Reels...")
        start = time.time()
        while time.time() - start < time_stay_seconds:
            # Lướt sang reel tiếp theo
            self.adb.swipe(500, 1500, 500, 300, duration=400)
            time.sleep(random.uniform(5.0, 10.0))

    def run_full_scenario(self, uid):
        """Chạy tổng hợp kịch bản nuôi nick hoàn chỉnh"""
        self.log(f"Khởi chạy kịch bản tự động cho UID: {uid}")
        self.run_tuong_tac_newsfeed(time_stay_seconds=20)
        self.run_xem_reel(time_stay_seconds=15)
        self.log("Hoàn thành kịch bản!")
