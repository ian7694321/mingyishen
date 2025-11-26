# mingyishen
個人工作成就

# Ming-Yi Shen – Work Automation & IoT Project Portfolio
沈明毅｜資料處理自動化與設備通訊專案整理

This document summarizes several side projects I developed during work, focusing on:
- Excel / data processing automation
- Equipment communication & sensor data logging
- SQL-based time logging
- Windows service & task scheduling

Most of these tools were created to solve real problems in finance, manufacturing, and engineering workflows.  
All sample data in the public repositories will be sanitized or simulated to avoid confidential information.

---

## 1. Data Processing & Excel Automation Tools

### 1.1 Excel Invoice Merge and Expected Payment Date Checker (Python)
**Excel 憑單合併與「預計付款日」自動計算工具**

**Role:** Sole developer – internal automation tool for accounting workflow.

**Description:**
A Python tool that automatically merges multiple Excel invoice files and calculates the *expected payment date* based on business rules.  
It also compares the calculated date with the existing “system expected payment date” and generates a discrepancy report.

**Key Features:**
- Automatically scans a target folder and loads all invoice Excel files.
- Supports multiple header formats and column name variants.
- Automatically detects the header row containing fields such as:
  - `憑單日期`, `憑單單號`, `廠商簡稱`, `付款條件名稱`, ...
- Calculates expected payment dates based on **付款條件** rules, for example:
  - **Current month 18th payment**  
    - If document date ≤ 18th → same month 18th  
    - If document date > 18th → next month 18th
  - **Next month 15th payment** (e.g., for 南科管理局)
    - Expected payment date = document date’s next month 15th
- Outputs:
  - **Merged summary**: `TOTAL_YYYYMMDD_HHMM.xlsx`
  - **Mismatch report** showing:
    - System expected payment date vs. recalculated date
    - Difference in days
    - 基準與計算依據（哪一條付款條件規則）

**Tech Stack:**
- Python, `pandas`, `openpyxl`, `datetime`

**Impact:**
- Reduced manual checking time from **1–2 hours** to **a few minutes**.
- Standardized payment-day rules and made them transparent in code and reports.

---

### 1.2 Excel Invoice Statistics and Automatic Pie Chart Report
**Excel 憑單統計與圓餅圖自動產生工具**

**Role:** Sole developer – reporting automation for financial data.

**Description:**
A reporting tool that reads merged invoice data, performs aggregation, and automatically generates charts (e.g., pie charts) embedded into Excel reports.

**Key Features:**
- Uses `pandas` to:
  - Aggregate amounts by category (vendor, cost center, payment term, etc.).
- Uses `matplotlib` to:
  - Generate visualization such as pie charts or bar charts.
- Uses `openpyxl` to:
  - Insert generated charts into specific sheets and cells in the Excel file.
- Designed to be used after the invoice merge tool, forming a small automation pipeline.

**Tech Stack:**
- Python, `pandas`, `matplotlib`, `openpyxl`

**Value:**
- Automates repetitive monthly/weekly reporting.
- Provides visual reports that can be directly shared with non-technical colleagues and management.

---

### 1.3 Batch Excel Merge and Automatic Column Alignment Tool
**多 Excel 檔批次合併與欄位自動對齊工具**

**Role:** Sole developer – generic data cleaning and merging tool.

**Description:**
A flexible Excel merging script designed to handle inconsistent formats from different sources.

**Key Features:**
- Supports multiple file name patterns and multiple sheets (`.xlsx`, `.xls`).
- Automatically detects possible date columns, such as:
  - `憑單日期`, `憑單日`, `憑單日期(西元)`
- Normalizes date values into a consistent format (`yyyy/mm/dd`).
- Automatically adjusts column widths for readability.
- Cleans invalid XML characters to avoid Excel warning messages like
  - 「部分內容有問題，是否要嘗試修復？」

**Tech Stack:**
- Python, `pandas`, `openpyxl`, `re`, `datetime`

**Usage Scenario:**
- A standard “data cleaning + consolidation” utility that can be reused in various internal reporting tasks.

---

## 2. Equipment Communication & Sensor Data Logging

### 2.1 HF5 Temperature and Humidity Sensor TCP Data Logger
**HF5 溫溼度感測器 TCP 讀值與紀錄程式**

**Role:** Sole developer – TCP communication test and logging tool for HF5 devices.

**Description:**
A Python script that connects to a Rotronic HF5 temperature–humidity device via TCP socket, sends commands, parses the response, and logs sensor readings.

**Key Features:**
- Connects to HF5 using:
  - IP: `HF5_IP`
  - Port: `HF5_PORT`
- Sends commands such as:
  - `{00RDD}\r`  
  to request readings from a specific address.
- Parses raw ASCII responses and extracts:
  - Relative humidity (`%RH`)
  - Temperature (`°C`)
- Periodically reads values in a loop and:
  - Prints formatted readings to console
  - Logs them to a file for later analysis

**Tech Stack:**
- Python, `socket`, `time`, string parsing

**Use Case:**
- Serves as an **environmental sensor logging demo**.
- Can be open-sourced using fake IP and sample data to avoid confidential information.

---

### 2.2 Serial Communication and Logging for Temperature–Humidity Devices
**Rotronic HC2 / SATO 等溫溼度設備串口通訊與資料記錄程式**

**Role:** Developer and tester – research and prototype scripts for serial-based devices.

**Description:**
A collection of prototypes and test scripts for communicating with various temperature–humidity devices (Rotronic HC2, SATO, etc.) over serial ports.

**Key Features:**
- Uses Python `serial` library to connect to:
  - `/dev/ttyS*` on Linux
  - `COMx` on Windows
- Implements and tests:
  - RO-ASCII and other vendor-specific serial protocols.
- Parses device responses to display real-time:
  - Temperature
  - Humidity
  - (Optional) Dew point
- Includes a function to compute **dew point** from temperature and relative humidity.

**Tech Stack:**
- Python, `pyserial`, `math`, `datetime`

**Value:**
- Provides a small, practical example of:
  - Serial communication
  - Protocol parsing
  - Basic scientific calculation (dew point)

---

### 2.3 HF4 / Other Device Log Auto-Download and Analysis (Prototype)
**HF4 / 其他設備 Log 自動下載與分析原型工具**

**Role:** Troubleshooting and tool development.

**Description:**
An experimental project aiming to automate the download and parsing of log files from HF4 or similar devices, overcoming limitations of vendor tools (e.g., batch file constraints).

**Key Points:**
- Investigated vendor software behavior and limitations.
- Explored possible ways to:
  - Automate log download process
  - Parse log formats into structured data
- Planned to extend into a **generic device log downloader** once more device details are available.

**Potential Future Work:**
- Wrap into a reusable library or CLI tool.
- Provide unified interface for multiple device types.

---

## 3. SQL-Based Time Logging Automation

### 3.1 TSMC Time Logging Automation Tool (`tsmc_time_log.py`)
**TSMC 工時系統資料自動撈取工具**

**Role:** Sole developer – internal tool for time logging and productivity tracking.

**Description:**
A Python script that connects to a time logging database (e.g., TSMC internal system) via ODBC/SQL, queries daily or range-based records, and exports the results.

**Key Features:**
- Uses ODBC/SQL to connect to the time logging database.
- Executes parameterized SQL queries to:
  - Retrieve work hours for a specific date or date range.
- Writes output to:
  - Text file (`.txt`)
  - Or Excel file (for further analysis)
- Designed to run automatically via:
  - Windows Task Scheduler (定時排程)
  - Windows Service (using `pywin32`)

**Tech Stack:**
- Python, `pyodbc` or equivalent ODBC library
- SQL (SELECT queries)
- Windows environment integration

**Impact:**
- Reduces manual login and export operations.
- Helps track personal and project-based work hours more systematically.

---

## 4. Deployment, Windows Service, and Scheduling

### 4.1 Python Automation Script as Windows Service / Scheduled Task
**Python 自動化腳本服務化與排程**

**Role:** Developer and maintainer.

**Description:**
A set of experiments and configurations to run Python scripts reliably in production-like environments on Windows.

**Key Actions:**
- Convert standalone Python scripts into:
  - Windows services using `pywin32`
  - Scheduled tasks via Windows Task Scheduler
- Explore packaging with `pyinstaller` to generate `.exe` files:
  - Allows non-technical users to run tools without installing Python.
- Handle permission and environment issues during installation and execution.

**Value:**
- Shows not only the ability to write scripts, but also:
  - How to integrate them into real-world IT environments.
  - How to consider deployment, stability, and usability for colleagues.

---

## Contact

**Author:** Ming-Yi Shen (沈明毅)  
**Location:** Tainan, Taiwan  
**GitHub:** _to be added_  
**Email:** _to be added (optional)_


