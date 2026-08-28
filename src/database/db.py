import sqlite3
import os

class DatabaseManager:
    """Quản lý Cơ sở dữ liệu SQLite cho MaxPhoneFarm Reborn"""
    def __init__(self, db_path="database.sqlite"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Khởi tạo các bảng chứa Nick Facebook, Nhóm Tài Khoản, Kịch bản & Cấu hình"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Bảng Groups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bảng Kịch Bản (Scenarios)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Bảng Hành Động trong Kịch Bản (Scenario Actions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenario_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id INTEGER,
                    action_type TEXT,
                    action_name TEXT,
                    config_json TEXT,
                    order_index INTEGER DEFAULT 0,
                    FOREIGN KEY(scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
                )
            """)
            # Bảng Phone Devices (Lưu danh sách thiết bị ADB & Tên gợi nhớ)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial TEXT UNIQUE,
                    name TEXT DEFAULT '',
                    status TEXT DEFAULT 'Ready',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("INSERT OR IGNORE INTO groups (id, name) VALUES (1, 'Mặc định')")

            # Bảng Accounts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER DEFAULT 1,
                    script_name TEXT DEFAULT '',
                    uid TEXT UNIQUE,
                    name TEXT DEFAULT '',
                    gender TEXT DEFAULT '',
                    friends TEXT DEFAULT '',
                    groups_count TEXT DEFAULT '',
                    password TEXT,
                    fa2 TEXT,
                    cookie TEXT,
                    token TEXT,
                    email TEXT,
                    pass_email TEXT,
                    useragent TEXT,
                    proxy TEXT,
                    status TEXT DEFAULT 'Ready',
                    has_backup INTEGER DEFAULT 0,
                    device_name TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(group_id) REFERENCES groups(id)
                )
            """)
            
            # Đảm bảo các cột cũ/mới tồn tại
            cursor.execute("PRAGMA table_info(accounts)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'group_id' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN group_id INTEGER DEFAULT 1")
            if 'script_name' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN script_name TEXT DEFAULT ''")
            if 'name' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN name TEXT DEFAULT ''")
            if 'gender' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN gender TEXT DEFAULT ''")
            if 'friends' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN friends TEXT DEFAULT ''")
            if 'groups_count' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN groups_count TEXT DEFAULT ''")
            if 'token' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN token TEXT")
            if 'email' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN email TEXT")
            if 'pass_email' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN pass_email TEXT")
            if 'useragent' not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN useragent TEXT")

            # Bảng Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get_all_groups(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM groups ORDER BY id ASC")
            return cursor.fetchall()

    # ---------------------------------------------------------
    # Quản Lý Thiết Bị Điện Thoại ADB (Phone Devices)
    # ---------------------------------------------------------
    def get_all_devices(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, serial, name, status FROM devices ORDER BY id ASC")
            return cursor.fetchall()

    def update_or_add_device(self, serial, name=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO devices (serial, name) VALUES (?, ?)", (serial, name))
            if name:
                cursor.execute("UPDATE devices SET name=? WHERE serial=?", (name, serial))
            conn.commit()

    def rename_device(self, serial, new_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE devices SET name=? WHERE serial=?", (new_name, serial))
            conn.commit()
    def get_all_scenarios(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM scenarios ORDER BY id ASC")
            return cursor.fetchall()

    def add_scenario(self, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO scenarios (name) VALUES (?)", (name,))
                conn.commit()
                return cursor.lastrowid
            except Exception:
                return None

    def rename_scenario(self, scenario_id, new_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE scenarios SET name=? WHERE id=?", (new_name, scenario_id))
            conn.commit()

    def delete_scenario(self, scenario_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenario_actions WHERE scenario_id=?", (scenario_id,))
            cursor.execute("DELETE FROM scenarios WHERE id=?", (scenario_id,))
            conn.commit()

    def duplicate_scenario(self, scenario_id, new_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO scenarios (name) VALUES (?)", (new_name,))
                new_sc_id = cursor.lastrowid
                actions = self.get_actions_by_scenario(scenario_id)
                for act in actions:
                    cursor.execute("""
                        INSERT INTO scenario_actions (scenario_id, action_type, action_name, config_json, order_index)
                        VALUES (?, ?, ?, ?, ?)
                    """, (new_sc_id, act[1], act[2], act[3], act[4]))
                conn.commit()
                return new_sc_id
            except Exception:
                return None

    def move_action_order(self, action_id, direction="up"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, scenario_id, order_index FROM scenario_actions WHERE id=?", (action_id,))
            current = cursor.fetchone()
            if not current:
                return False
            curr_id, sc_id, curr_idx = current
            if direction == "up":
                cursor.execute("SELECT id, order_index FROM scenario_actions WHERE scenario_id=? AND order_index < ? ORDER BY order_index DESC LIMIT 1", (sc_id, curr_idx))
            else:
                cursor.execute("SELECT id, order_index FROM scenario_actions WHERE scenario_id=? AND order_index > ? ORDER BY order_index ASC LIMIT 1", (sc_id, curr_idx))
            neighbor = cursor.fetchone()
            if not neighbor:
                return False
            neighbor_id, neighbor_idx = neighbor
            cursor.execute("UPDATE scenario_actions SET order_index=? WHERE id=?", (neighbor_idx, curr_id))
            cursor.execute("UPDATE scenario_actions SET order_index=? WHERE id=?", (curr_idx, neighbor_id))
            conn.commit()
            return True

    def get_actions_by_scenario(self, scenario_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, action_type, action_name, config_json, order_index FROM scenario_actions WHERE scenario_id=? ORDER BY order_index ASC", (scenario_id,))
            return cursor.fetchall()

    def add_action_to_scenario(self, scenario_id, action_type, action_name, config_json):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(order_index) FROM scenario_actions WHERE scenario_id=?", (scenario_id,))
            max_idx = cursor.fetchone()[0]
            new_idx = (max_idx + 1) if max_idx is not None else 0
            
            cursor.execute("""
                INSERT INTO scenario_actions (scenario_id, action_type, action_name, config_json, order_index)
                VALUES (?, ?, ?, ?, ?)
            """, (scenario_id, action_type, action_name, config_json, new_idx))
            conn.commit()
            return cursor.lastrowid

    def delete_action(self, action_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenario_actions WHERE id=?", (action_id,))
            conn.commit()

    def update_action_config(self, action_id, config_json):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE scenario_actions SET config_json=? WHERE id=?", (config_json, action_id))
            conn.commit()

    def add_group(self, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO groups (name) VALUES (?)", (name,))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

    def add_account(self, uid, password="", fa2="", cookie="", proxy="", group_id=1, token="", email="", pass_email="", useragent=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO accounts (uid, password, fa2, cookie, proxy, group_id, token, email, pass_email, useragent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uid, password, fa2, cookie, proxy, group_id, token, email, pass_email, useragent))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Đã tồn tại UID -> Cập nhật
                cursor.execute("""
                    UPDATE accounts SET password=?, fa2=?, cookie=?, proxy=?, group_id=?, token=?, email=?, pass_email=?, useragent=? WHERE uid=?
                """, (password, fa2, cookie, proxy, group_id, token, email, pass_email, useragent, uid))
                conn.commit()
                return True

    def get_accounts_by_group(self, group_id=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if group_id is None or group_id == 0 or group_id == "all":
                cursor.execute("""
                    SELECT a.id, a.group_id, a.uid, a.password, a.fa2, a.cookie, a.token, 
                           a.email, a.pass_email, a.useragent, a.proxy, a.status, a.has_backup, a.script_name, g.name,
                           a.name, a.gender, a.friends, a.groups_count
                    FROM accounts a LEFT JOIN groups g ON a.group_id = g.id
                """)
            else:
                cursor.execute("""
                    SELECT a.id, a.group_id, a.uid, a.password, a.fa2, a.cookie, a.token, 
                           a.email, a.pass_email, a.useragent, a.proxy, a.status, a.has_backup, a.script_name, g.name,
                           a.name, a.gender, a.friends, a.groups_count
                    FROM accounts a LEFT JOIN groups g ON a.group_id = g.id
                    WHERE a.group_id = ?
                """, (group_id,))
            return cursor.fetchall()

    def update_account(self, acc_id, uid, password, fa2, cookie, proxy, token, email, pass_email, useragent, script_name="", name="", gender="", friends="", groups_count=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts SET uid=?, password=?, fa2=?, cookie=?, proxy=?, token=?, email=?, pass_email=?, useragent=?, script_name=?, name=?, gender=?, friends=?, groups_count=?
                WHERE id=?
            """, (uid, password, fa2, cookie, proxy, token, email, pass_email, useragent, script_name, name, gender, friends, groups_count, acc_id))
            conn.commit()

    def update_account_script(self, uids, script_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for u in uids:
                cursor.execute("UPDATE accounts SET script_name=? WHERE uid=?", (script_name, u))
            conn.commit()

    def delete_accounts(self, uids):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for u in uids:
                cursor.execute("DELETE FROM accounts WHERE uid=?", (u,))
            conn.commit()

    def get_all_accounts(self):
        return self.get_accounts_by_group(group_id=None)

    def update_account_status(self, uid, status, has_backup=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if has_backup is not None:
                cursor.execute("UPDATE accounts SET status=?, has_backup=? WHERE uid=?", (status, has_backup, uid))
            else:
                cursor.execute("UPDATE accounts SET status=? WHERE uid=?", (status, uid))
            conn.commit()
