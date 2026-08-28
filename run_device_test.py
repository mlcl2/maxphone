import json
import os
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

from src.core.automation_worker import AutomationWorker

DB = os.path.join(ROOT, "database.sqlite")
SERIAL = "33005627a45094c1"
LOG = os.path.join(ROOT, "logs", f"test_{SERIAL}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

with sqlite3.connect(DB) as conn:
    account = conn.execute(
        "SELECT id, uid, password, fa2, cookie, token, proxy, script_name FROM accounts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not account:
        raise RuntimeError("Không tìm thấy tài khoản test trong database")
    acc_id, uid, password, fa2, cookie, token, proxy, script_name = account
    scenario_row = conn.execute(
        "SELECT id FROM scenarios WHERE name=?", (script_name or "tương tác nhẹ",)
    ).fetchone()
    if not scenario_row:
        raise RuntimeError("Không tìm thấy kịch bản được gán cho tài khoản test")
    actions = conn.execute(
        "SELECT action_type, config_json FROM scenario_actions WHERE scenario_id=? ORDER BY order_index",
        (scenario_row[0],),
    ).fetchall()

scenario = {"actions": [{"type": kind, "config": json.loads(config)} for kind, config in actions]}
account_data = {
    "id": acc_id, "uid": uid, "password": password or "", "fa2": fa2 or "",
    "cookie": cookie or "", "token": token or "", "proxy": proxy or "",
}

with open(LOG, "w", encoding="utf-8") as out:
    def log(status, message):
        line = f"[{datetime.now().isoformat(timespec='seconds')}] [{status}] {message}"
        print(line, flush=True)
        out.write(line + "\n")
        out.flush()

    def worker_log(acc_id, status, message):
        line = f"[{datetime.now().isoformat(timespec='seconds')}] [UID:{acc_id}] [{status}] {message}"
        print(line, flush=True)
        out.write(line + "\n")
        out.flush()

    log("START", f"Bắt đầu test UID {uid} trên thiết bị {SERIAL}; mode=airplane; actions={len(actions)}")
    worker = AutomationWorker(account_data, SERIAL, scenario, ip_mode="airplane")
    worker.log_signal.connect(worker_log)
    worker.failed_signal.connect(lambda message: log("FAILED", message))
    worker.run()
    log("END", f"finished error={worker.error_message or 'none'}")
    print(f"LOG_PATH={LOG}", flush=True)
    if worker.error_message:
        sys.exit(1)
