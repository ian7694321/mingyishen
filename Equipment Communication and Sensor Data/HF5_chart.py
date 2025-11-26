import csv
from datetime import datetime

import matplotlib.pyplot as plt

LOGFILE = "hf5_log.csv"   # 如果放別的路徑就改這裡

timestamps = []
rh_values = []
temp_values = []

# 1. 讀取 CSV
with open(LOGFILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # 解析時間字串，例如 "2025-11-17 09:45:12"
        ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        rh = float(row["humidity_%RH"])
        temp = float(row["temperature_C"])

        timestamps.append(ts)
        rh_values.append(rh)
        temp_values.append(temp)

# 2. 畫圖
plt.figure(figsize=(10, 5))

plt.plot(timestamps, rh_values, label="濕度 (%RH)")
plt.plot(timestamps, temp_values, label="溫度 (°C)")

plt.xlabel("時間")
plt.ylabel("數值")
plt.title("HF5 溫溼度變化")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.gcf().autofmt_xdate()  # 把時間刻度斜一點比較好看

plt.show()
