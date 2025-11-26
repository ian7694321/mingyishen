
# HF5 溫溼度感測器 TCP 讀值與紀錄工具（Python）

這個專案是使用 Python 實作的 **HF5 溫溼度感測器 TCP／Modbus 讀值與紀錄 Demo**，  
透過網路連線到 HF5（或相容裝置），讀取溫度與相對溼度，並支援長時間紀錄與圖表顯示。

主要功能包含：

- 透過 TCP 對 HF5 發送 `{00RDD}\r` 等指令，讀取即時溫溼度
- 將讀值結果定期寫入 CSV 檔，作為 datalogger
- 從紀錄檔產生溫度／濕度趨勢圖
- 以 Modbus 方式嘗試讀取 HF5 暫存器（探測用）
- 針對既有 log 檔進行再次解析或檢視

---

## 功能特色

- ✅ **TCP 連線 Demo**：直接對 HF5 IP／Port 建立 socket，送出讀值指令並解析回應
- ✅ **資料紀錄（Logger）**：週期性讀取 HF5 數值，寫入 `hf5_log.csv`
- ✅ **圖表呈現**：從 CSV 紀錄繪製溫度／濕度時間序列圖
- ✅ **Modbus Probe**：以 Modbus 方式嘗試讀取暫存器，確認通訊與暫存器配置
- ✅ **工具分工清楚**：讀值、紀錄、畫圖、解析各自一支程式，方便說明與維護

---

## 專案結構

```text
hf5-sensor-tcp-logger/
├─ HF5.py               # 基本 TCP 連線與單次讀值 Demo
├─ HF5_log.py           # 週期性讀值並寫入 log / CSV 的 datalogger
├─ HF5_chart.py         # 讀取 hf5_log.csv，產生溫溼度變化圖表
├─ HF5_modbus_probe.py  # 以 Modbus 方式讀取 HF5 / 相關設備的測試程式
├─ Read_HF5.py          # 讀取既有 log、做簡單解析／檢視用的小工具
├─ hf5_log.csv          # 由 HF5_log.py 產生的範例紀錄檔
└─ README.md            # 專案說明（本檔案）
```

---
## 主要檔案說明

### `HF5.py`

- 專案中最基本的 **HF5 TCP 讀值 Demo**
- 主要流程：
  - 在程式開頭設定：
    - `HF5_IP`：HF5 裝置 IP 位址（例如 `"192.168.1.1"`）
    - `HF5_PORT`：HF5 提供的 TCP Port（例如 `2101`）
    - `CMD`：讀值指令（例如 `{00RDD}\r`，其中 `00` 為 HF5 位址）
  - 使用 `socket.create_connection()` 建立 TCP 連線
  - 送出讀值指令，等待回應後呼叫 `recv()` 取得原始 ASCII 字串
  - 解析回應內容，取出：
    - 相對溼度 `%RH`
    - 溫度 `°C`
  - 以人類可讀格式印出，例如：
    - `[2025/11/17 10:30] RH=47.250 %RH, T=27.650 °C`
- 用途：
  - 確認 HF5 網路連線／通訊設定是否正確
  - 作為後續 logger／圖表工具的基礎程式

---

### `HF5_log.py`

- 在 `HF5.py` 基礎上，加上 **週期性讀值與紀錄功能**，當作簡易 datalogger
- 主要功能：
  - 以固定時間間隔（例如每 10 秒或每 1 分鐘）向 HF5 讀取一次資料
  - 每筆資料包含：
    - 時間戳記（日期＋時間）
    - 溫度（°C）
    - 相對溼度（%RH）
  - 將結果以列的形式追加寫入 `hf5_log.csv`
- 用途：
  - 長時間記錄實驗室／機房／生產環境的溫溼度變化
  - 為 `HF5_chart.py` 提供輸入資料來源

---

### `HF5_chart.py`

- 負責從 `hf5_log.csv` 讀取歷史紀錄並產生圖表
- 主要功能：
  - 使用 `pandas` 讀取 `hf5_log.csv`，取得時間、溫度、溼度欄位
  - 使用 `matplotlib` 繪製：
    - 溫度折線圖
    - 濕度折線圖
    - 或同一張圖顯示兩條曲線的時間序列圖
  - 將圖表顯示在視窗中，或輸出為 PNG 等圖檔
- 用途：
  - 快速檢視一整天／一週的溫溼度趨勢
  - 作為報告或簡報中的圖表素材

---

### `HF5_modbus_probe.py`

- 針對 HF5 或相容設備進行 **Modbus 通訊測試** 的小工具
- 可能的功能（依實作為準）：
  - 設定：
    - Modbus Slave ID
    - Function Code（例如 `0x03` Read Holding Registers）
    - 起始暫存器位址與讀取長度
  - 透過 TCP 或 RTU 建立 Modbus 連線，發送讀取請求
  - 解析回應暫存器值並印出，以確認：
    - 通訊是否正常
    - 暫存器對應的實際工程數值是否合理
- 用途：
  - 探勘 HF5 暫存器配置
  - 驗證之後若要用 PLC / SCADA 讀 HF5 時的設定值

---

### `Read_HF5.py`

- 用來「讀取既有 HF5 log 或做簡單解析」的輔助腳本
- 常見用途（可依實際程式調整 README）：
  - 開啟既有的 `hf5_log.csv` 或文字 log
  - 過濾出特定日期／時間區間的資料
  - 計算簡單統計值，例如：
    - 平均溫度、平均濕度
    - 最大值 / 最小值
  - 將整理後的結果印在終端機或另存為新的檔案

---

### `hf5_log.csv`

- 由 `HF5_log.py` 產生的 **範例溫溼度紀錄檔**
- 一般欄位示意：
  - `timestamp`：測量時間
  - `temperature`：溫度（°C）
  - `humidity`：相對溼度（%RH）
- 用途：
  - 可直接用 Excel / LibreOffice 開啟查看
  - 作為 `HF5_chart.py` 繪圖以及 `Read_HF5.py` 分析的資料來源

