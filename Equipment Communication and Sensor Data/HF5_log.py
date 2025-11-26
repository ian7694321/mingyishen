import socket
import time
import csv
from pathlib import Path

HF5_IP = "192.168.1.1"
HF5_PORT = 2101
CMD = "{H00RDD}\r"

def read_hf5_once():
    with socket.create_connection((HF5_IP, HF5_PORT), timeout=3) as s:
        s.settimeout(1.0)
        s.sendall(CMD.encode("ascii"))

        chunks = []
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            chunks.append(data)
            if b']' in data or b'\r' in data or b'\n' in data:
                break

    if not chunks:
        raise RuntimeError("沒有收到 HF5 的任何資料")

    raw = b"".join(chunks)
    text = raw.decode("latin-1", errors="ignore")

    # 解析
    if "rdd" in text:
        payload = text.split("rdd", 1)[1]
    else:
        parts_space = text.split(" ", 1)
        payload = parts_space[1] if len(parts_space) > 1 else text

    payload = payload.strip(" ]\r\n")
    parts = [p.strip() for p in payload.split(";")]

    if len(parts) < 7:
        raise ValueError(f"回應欄位太少，無法解析：{parts!r}")

    rh   = float(parts[1])
    temp = float(parts[5])
    return rh, temp, text

def log_loop(interval_sec=10, logfile="hf5_log.csv"):
    log_path = Path(logfile)
    # 如果檔案不存在，就寫表頭
    if not log_path.exists():
        with log_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "humidity_%RH", "temperature_C"])

    while True:
        try:
            rh, temp, _raw = read_hf5_once()
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] RH={rh:.3f} %RH, T={temp:.3f} °C")

            with log_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([ts, rh, temp])

        except Exception as e:
            print("讀取或寫入失敗：", e)

        time.sleep(interval_sec)

if __name__ == "__main__":
    log_loop(interval_sec=10, logfile="hf5_log.csv")
