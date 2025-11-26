#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import csv
from pathlib import Path
from datetime import datetime
import argparse

# ============ 基本設定 ============
HF5_IP = "192.168.1.1"     # HF5 IP
HF5_PORT = 2101            # HF5 / Digi 上的 Raw TCP Port
CMD = "{H00RDD}\r"         # 讀取 HF5 位址 00 即時值指令

LOGFILE = "hf5_log.csv"    # 紀錄 CSV 檔名


# ============ 讀取 HF5 一次 ============

def read_hf5_once():
    """連線 HF5，一次讀回溫濕度，回傳 (rh, temp, raw_text)"""
    with socket.create_connection((HF5_IP, HF5_PORT), timeout=3) as s:
        s.settimeout(1.0)
        s.sendall(CMD.encode("ascii"))

        chunks = []
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                # 一段時間沒新資料，當作收完
                break

            if not data:
                # 對方關閉連線
                break

            chunks.append(data)

            # HF5 回應結尾會有 ']' 或 CR/LF，看到就可以停
            if b"]" in data or b"\r" in data or b"\n" in data:
                break

    if not chunks:
        raise RuntimeError("沒有收到 HF5 的任何資料")

    raw = b"".join(chunks)
    text = raw.decode("latin-1", errors="ignore")

    # 把單位符號換成純 ASCII，比較不會亂碼
    text = text.replace("°C", "degC").replace("%rh", "%RH")
    print("完整原始回應：", repr(text))

    # ---- 解析 payload ----
    # 範例：{H00rdd 1;48.120; %RH;0;-;27.520;  degC; ... ;HF5         ;000;)\r
    first_space = text.find(" ")
    payload = text[first_space + 1:] if first_space != -1 else text

    payload = payload.strip(" ]\r\n")
    parts = [p.strip() for p in payload.split(";")]

    # index 0 : 狀態1
    # index 1 : 濕度數值
    # index 2 : 濕度單位 (%RH)
    # index 3 : 狀態2
    # index 4 : 溫度符號 (+/-)
    # index 5 : 溫度數值
    # index 6 : 溫度單位 (degC)
    if len(parts) < 7:
        raise ValueError(f"回應欄位太少，無法解析：{parts!r}")

    rh = float(parts[1])
    temp = float(parts[5])

    return rh, temp, text


# ============ 紀錄成 CSV ============

def ensure_log_header(path: Path):
    """如果 CSV 不存在就先寫表頭"""
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "humidity_%RH", "temperature_C"])


def log_loop(interval_sec: int):
    """每 interval_sec 秒讀一次 HF5，附加寫入 CSV"""
    log_path = Path(LOGFILE)
    ensure_log_header(log_path)

    print(f"開始紀錄 HF5 資料，每 {interval_sec} 秒一次，寫入 {log_path.resolve()}")
    print("停止請按 Ctrl + C\n")

    while True:
        try:
            rh, temp, _raw = read_hf5_once()
            # 跟Excel 顯示一樣，只留到分鐘
            ts = datetime.now().strftime("%Y/%m/%d %H:%M")

            print(f"[{ts}] RH={rh:.3f} %RH, T={temp:.3f} °C")

            with log_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([ts, rh, temp])

        except Exception as e:
            print("讀取或寫入失敗：", e)

        try:
            time.sleep(interval_sec)
        except KeyboardInterrupt:
            # 在 sleep 時按 Ctrl+C 的情況，優雅結束
            print("\n偵測到 Ctrl+C，停止紀錄。")
            break


# ============ 主程式入口 ============

def main():
    parser = argparse.ArgumentParser(description="HF5 溫溼度讀取 / 紀錄工具（無 chart）")
    parser.add_argument(
        "--log",
        action="store_true",
        help="啟動連續紀錄模式，資料寫入 hf5_log.csv",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="連續紀錄模式下，每幾秒讀取一次 (預設 10 秒)",
    )
    args = parser.parse_args()

    if args.log:
        try:
            log_loop(args.interval)
        except KeyboardInterrupt:
            print("\n偵測到 Ctrl+C，停止紀錄。")
    else:
        # 沒帶 --log 就只讀一次
        rh, temp, _raw = read_hf5_once()
        print(f"濕度: {rh:.3f} %RH, 溫度: {temp:.3f} °C")


if __name__ == "__main__":
    main()
