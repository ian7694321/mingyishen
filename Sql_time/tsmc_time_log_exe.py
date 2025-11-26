import os
import sys
import traceback
from datetime import datetime
import pyodbc

# ========= 資料庫設定 =========
SERVER   = "192.168.208."
DATABASE = "FINEX"
UID      = ""
PWD      = ""
QUERY    = "SELECT TOP 100 * FROM View_TSMC_lotno"
TIMEOUT  = 10
# ============================

OUTPUT_DIR = r"\\10.0.0.10\storage"

def get_base_dir() -> str:
    """EXE 模式：回傳 EXE 所在資料夾；py 模式：回傳 .py 所在資料夾"""
    if OUTPUT_DIR:
        return OUTPUT_DIR
    if getattr(sys, "frozen", False):  # PyInstaller 打包後
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def ensure_parent(path: str) -> None:
    """確保檔案的上層資料夾存在"""
    os.makedirs(os.path.dirname(path), exist_ok=True)

def log_line(msg: str, run_log_path: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    ensure_parent(run_log_path)
    with open(run_log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    base = get_base_dir()
    # 固定檔名
    out_txt   = os.path.join(base, "remove_list.txt")
    run_log   = os.path.join(base, "run.log")
    error_log = os.path.join(base, "error.log")

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={UID};PWD={PWD};"
        "Encrypt=yes;TrustServerCertificate=yes;"
        "Authentication=SqlPassword;"
        f"Connection Timeout={TIMEOUT};"
    )

    try:
        log_line("開始連線 SQL Server …", run_log)
        with pyodbc.connect(conn_str) as conn:
            cur = conn.cursor()
            log_line(f"執行查詢：{QUERY}", run_log)
            cur.execute(QUERY)

            log_line(f"寫入資料到：{out_txt}", run_log)
            ensure_parent(out_txt)
            with open(out_txt, "w", encoding="utf-8", newline="") as f:
                for row in cur:  # 逐行寫入
                    f.write("\t".join(map(str, row)) + "\n")

        log_line("執行完成，資料已更新", run_log)

    except Exception as e:
        tb = traceback.format_exc()
        ensure_parent(error_log)
        with open(error_log, "a", encoding="utf-8") as ef:
            ef.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Exception: {e}\n{tb}\n")
        log_line(f"錯誤發生，詳細記錄已寫入 {error_log}", run_log)

if __name__ == "__main__":
    main()