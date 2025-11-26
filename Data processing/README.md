# invoice-payment-date-checker（Excel 憑單合併與預計付款日檢查工具）

這個專案是使用 Python 實作的 **Excel 憑單合併與「預計付款日」自動計算／比對工具**，  
搭配統計圖表與錯誤紀錄，協助會計或財務人員加速月結作業。

主要由四支腳本組成：

- `merge_all_data.py`：合併多個憑單 Excel 檔
- `compare.py`：依付款條件計算「預計付款日」，並與系統日期比對
- `Pie_Chart.py`：根據合併結果產生統計圖表（例如圓餅圖）
- `excel_error_log.py`：處理 Excel 修復訊息與錯誤紀錄

---

## 功能特色

- ✅ 自動掃描資料夾中的全部憑單 Excel 檔並合併
- ✅ 自動偵測表頭列（包含 `憑單日期、憑單單號、廠商簡稱、付款條件名稱…`）
- ✅ 支援多種欄位名稱格式（`憑單日期 / 憑單日 / 憑單日期(西元)` 等）
- ✅ 依「付款條件名稱」自動計算預計付款日（例如：當月 18 號付款、次月 15 號付款）
- ✅ 產出：
  - 合併總表：`TOTAL_YYYYMMDD_HHMM.xlsx`
  - 不一致明細：系統預計付款日 vs 程式計算日期＋相差天數
- ✅ 額外產出統計圖表（圓餅圖等），直接嵌入 Excel
- ✅ 清理不合法字元、紀錄 Excel 修復錯誤，避免開啟時跳出「部分內容有問題」

---

## 專案結構

```text
Data processing/
├─ merge_all_data.py   # 合併多個 Excel 憑單檔，產生 TOTAL_YYYYMMDD_HHMM.xlsx
├─ compare.py          # 依付款條件計算預計付款日，產出不一致明細
├─ Pie_Chart.py        # 對合併結果做統計，產生圓餅圖並嵌入 Excel
├─ excel_error_log.py  # 處理 Excel 錯誤／修復訊息的輔助工具（選用）
└─ README.md           # 專案說明（本檔案）

