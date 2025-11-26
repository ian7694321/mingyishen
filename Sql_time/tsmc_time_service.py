import win32serviceutil, win32service, win32event
import servicemanager
import socket, time, os, sys, shutil, traceback
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

# 路徑（NAS 不可達時，所有輸出都會在 LOCAL_DIR）
NAS_DIR   = r"\\10.0.0.10\storage"
LOCAL_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

# 每日固定執行時間（24h 制）
RUN_HOUR  = 8
RUN_MIN   = 0

# 巡檢頻率（秒）
CHECK_INTERVAL_SEC = 60

# 要同步的檔案清單
SYNC_FILENAMES = ["remove_list.txt", "run.log", "error.log"]
# ============================

def ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_line(msg: str):
    line = f"[{now_ts()}] {msg}"
    print(line, flush=True)
    try:
        log_path = os.path.join(LOCAL_DIR, "run.log")
        ensure_parent(log_path)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def is_nas_available() -> bool:
    try:
        return os.path.exists(NAS_DIR)
    except Exception:
        return False

def smart_sync_local_to_nas():
    """只同步更新過或 NAS 沒有的檔案，成功回傳 True"""
    if not is_nas_available():
        return False
    synced_any = False
    for fname in SYNC_FILENAMES:
        src = os.path.join(LOCAL_DIR, fname)
        dst = os.path.join(NAS_DIR, fname)
        if not os.path.exists(src):
            continue
        try:
            ensure_parent(dst)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                log_line(f"新檔案同步：{fname}")
                synced_any = True
            else:
                if os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(src, dst)
                    log_line(f"檔案更新，同步新版：{fname}")
                    synced_any = True
        except Exception as e:
            log_line(f"同步失敗 {fname}：{e}")
    return synced_any

def run_sql_and_output(base_dir: str):
    out_txt   = os.path.join(base_dir, "remove_list.txt")
    error_log = os.path.join(LOCAL_DIR, "error.log")  # error 保留在本地

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={SERVER};DATABASE={DATABASE};UID={UID};PWD={PWD};"
        "Encrypt=yes;TrustServerCertificate=yes;Authentication=SqlPassword;"
        f"Connection Timeout={TIMEOUT};"
    )
    try:
        log_line("開始連線 SQL Server …")
        with pyodbc.connect(conn_str) as conn:
            cur = conn.cursor()
            log_line(f"執行查詢：{QUERY}")
            cur.execute(QUERY)

            log_line(f"寫入資料到：{out_txt}")
            ensure_parent(out_txt)
            with open(out_txt, "w", encoding="utf-8", newline="") as f:
                for row in cur:
                    f.write("\t".join(map(str, row)) + "\n")
        log_line("執行完成，資料已更新")
    except Exception as e:
        tb = traceback.format_exc()
        try:
            ensure_parent(error_log)
            with open(error_log, "a", encoding="utf-8") as ef:
                ef.write(f"\n[{now_ts()}] Exception: {e}\n{tb}\n")
        except Exception:
            pass
        log_line(f"錯誤發生，詳細記錄已寫入 {error_log}")

def pick_output_dir() -> str:
    if is_nas_available():
        log_line("偵測到 NAS 可用，輸出至 NAS")
        return NAS_DIR
    log_line("NAS 不可用，改寫入本地")
    return LOCAL_DIR

def today_run_time():
    now = datetime.now()
    return now.replace(hour=RUN_HOUR, minute=RUN_MIN, second=0, microsecond=0)

class TSMCTimeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TSMCTimeService"
    _svc_display_name_ = "TSMC Time Job Service"
    _svc_description_ = "常駐執行：每日 08:00 擷取 SQL 並輸出，且隨時偵測 NAS 可達即智慧同步。"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        socket.setdefaulttimeout(60)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stop_requested = False
        self.last_run_date = None  # 記錄上次成功觸發的日期（避免一天多跑）

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_requested = True
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, "Started"))
        log_line("服務啟動")
        try:
            self.main_loop()
        except Exception as e:
            log_line(f"服務主循環出錯：{e}")
        log_line("服務結束")

    def main_loop(self):
        while not self.stop_requested:
            now = datetime.now()

            # 1) 隨時嘗試智慧同步（VPN 連上即刻生效）
            if is_nas_available():
                if smart_sync_local_to_nas():
                    log_line("✅ 同步完成")

            # 2) 每日排程：08:00 執行（若服務剛啟動且已過 08:00，會「補跑」一次）
            run_time = today_run_time()
            if (now >= run_time) and (self.last_run_date != now.date()):
                base = pick_output_dir()
                run_sql_and_output(base)
                # 輸出後再嘗試同步一次
                if is_nas_available():
                    smart_sync_local_to_nas()
                self.last_run_date = now.date()

            # 3) 等待或接收停止事件
            rc = win32event.WaitForSingleObject(self.hWaitStop, CHECK_INTERVAL_SEC * 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(TSMCTimeService)