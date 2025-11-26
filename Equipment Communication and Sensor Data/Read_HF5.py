import socket

HF5_IP = "192.168.1.1"   # HF5 IP
HF5_PORT = 2101          # Raw TCP port
CMD = "{H00RDD}\r"       # 讀取位址 00 的即時值

def read_hf5_once():
    # 1. 建立 TCP 連線
    with socket.create_connection((HF5_IP, HF5_PORT), timeout=3) as s:
        s.settimeout(1.0)  # 每次 recv 最多等 1 秒
        # 2. 送指令
        s.sendall(CMD.encode("ascii"))

        # 3. 迴圈收資料，直到遇到 ']' 或 timeout
        chunks = []
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                # 一段時間沒新資料，就當作收完了
                break

            if not data:
                # 關連線
                break

            chunks.append(data)

            # HF5 的回應結尾有 ']'，有看到就可以停了
            if b']' in data or b'\r' in data or b'\n' in data:
                break

    if not chunks:
        raise RuntimeError("沒有收到 HF5 的任何資料")

    raw = b"".join(chunks)
    text = raw.decode("latin-1", errors="ignore")
    print("完整原始回應：", repr(text))

    # 4. 解析：先把前面的 '{H00rdd ' 標頭切掉，只留分號後面的 payload
    # 例：{H00rdd 1;50.330; %rh;0;+;27.010;  °C;...;HF5         ;000;]
    # 找第一個空白，把後面那段拿來 split(';')
    if "rdd" in text:
        payload = text.split("rdd", 1)[1]  # 拿 'rdd' 後面的那一段
    else:
        # 保險一點：找第一個空白
        parts_space = text.split(" ", 1)
        payload = parts_space[1] if len(parts_space) > 1 else text

    # 去掉收尾空白與 ']' 再用分號切
    payload = payload.strip(" ]\r\n")
    parts = [p.strip() for p in payload.split(";")]

    # 檢查欄位數
    # 範例：1;50.330; %rh;0;+;27.010;  °C;0;=;  ; --.--;    ;0; ;020;...
    if len(parts) < 7:
        raise ValueError(f"回應欄位太少，無法解析：{parts!r}")

    # 依照 HF5 的 RDD 格式：
    # index 0 : 狀態
    # index 1 : 濕度
    # index 2 : 濕度單位
    # index 3 : 狀態
    # index 4 : 符號(+/-)
    # index 5 : 溫度
    # index 6 : 溫度單位
    rh_str   = parts[1]
    temp_str = parts[5]

    rh   = float(rh_str)
    temp = float(temp_str)

    return rh, temp

if __name__ == "__main__":
    rh, temp = read_hf5_once()
    print(f"濕度: {rh:.3f} %RH, 溫度: {temp:.3f} °C")
