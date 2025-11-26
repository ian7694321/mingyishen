# TSMC 工時系統自動撈取與排程工具（Python）

這個專案是使用 Python 實作的 **TSMC 工時系統工時自動撈取 Demo**，  
透過 ODBC / SQL 連線到工時資料庫，自動查詢每日或指定區間工時，輸出成文字檔或 log，  
可以搭配 Windows 工作排程或 Windows Service，做到「每天自動幫自己下載工時」。

---

## 功能特色

- ✅ 透過 **ODBC / SQL** 連線 TSMC 工時系統資料庫，自動執行查詢  
- ✅ 支援每天定時撈取，或手動執行當天／區間工時  
- ✅ 將查詢結果輸出為：
  - 純文字檔（.txt）
  - 或寫入 log（方便追蹤每次執行狀態）
- ✅ 可搭配：
  - Windows 工作排程（Task Scheduler）
  - Windows Service（`tsmc_time_service.py`）
- ✅ 可透過 `remove_list.txt` 過濾不需要的專案／文字，讓輸出更乾淨

---

## 專案結構

```text
tsmc-time-log-automation/   （實際資料夾名稱：Sql_time）
├─ tsmc_time_log.py        # 主程式：連線 DB 撈工時，輸出結果
├─ tsmc_time_log_exe.py    # 打包成 EXE 時用的入口程式（給 PyInstaller 使用）
├─ tsmc_time_service.py    # 將撈取腳本包成 Windows Service 的程式
├─ remove_list.txt         # 要從輸出結果中排除的關鍵字／專案清單
├─ run.log                 # 執行紀錄與錯誤訊息 log
└─ README.md               # 專案說明（本檔案，之後你會新增）
```

---
## 主要檔案說明

### `tsmc_time_log.py`

- 專案的核心程式，負責「連線資料庫 → 撈取工時 → 輸出結果」。
- 主要流程（示意）：
  - 建立 ODBC / SQL 連線（例如使用 `pyodbc`）。
  - 依目前日期（或程式設定）組出查詢工時的 SQL。
  - 執行查詢，取得「日期、專案、工時、備註」等欄位。
  - 讀取 `remove_list.txt`，把包含特定關鍵字的紀錄過濾掉（選用）。
  - 以固定格式寫出到輸出檔（例如 `tsmc_time.txt`）或追加到 `run.log`。
- 用途：
  - 取代每天登入系統查詢工時、手動匯出的動作。
  - 也可以當作其他自動化（EXE、Service）的核心模組被呼叫。

---

### `tsmc_time_log_exe.py`

- 給 PyInstaller 或其他打包工具使用的「EXE 入口檔」。
- 主要功能：
  - `from tsmc_time_log import main` 或等價方式，呼叫主程式邏輯。
  - 把路徑、設定檔位置調整為相對於 EXE 的模式（例如使用 `sys.executable`）。
- 用途：
  - 讓非技術同事在沒有安裝 Python 的情況下，也能執行工時撈取工具：
    - 只要點兩下 `tsmc_time_log.exe` 即可產生今日工時檔案。

---

### `tsmc_time_service.py`

- 將工時撈取功能包裝成 Windows Service 的程式。
- 典型功能（依你的實作為準）：
  - 定義 Windows Service 類別，於服務啟動時定期呼叫 `tsmc_time_log.py`。
  - 提供安裝／移除服務的命令列介面，例如：
    - `python tsmc_time_service.py install`
    - `python tsmc_time_service.py start`
    - `python tsmc_time_service.py stop`
- 用途：
  - 在背景長期執行，自動於每天某個時間點撈取工時。
  - 不需要使用者登入，只要電腦開機、服務啟動即可運作。

---

### `remove_list.txt`

- 純文字設定檔，用來列出「不要出現在輸出工時檔中的關鍵字」。
- 內容範例（每行一個條件，可依你實際使用情況修改）：
  - 特定專案代號
  - 特定備註文字
  - 測試用的紀錄關鍵字等
- 用途：
  - 讓輸出的工時檔只保留真正計入工時的紀錄。
  - 可以避免把「測試帳、錯誤操作」等雜訊寫入總表。

---

### `run.log`

- 程式執行時產生的 **執行紀錄檔**。
- 內容通常包含：
  - 每次執行的時間戳記
  - 查詢到多少筆工時紀錄
  - 成功／失敗訊息
  - 若發生例外（Exception），會在這裡輸出錯誤堆疊資訊
- 用途：
  - 方便日後追蹤：
    - 某天是否有成功撈取工時
    - 若失敗，是連線錯誤、SQL 錯誤還是權限問題。
