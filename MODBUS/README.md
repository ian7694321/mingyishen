# Modbus RTU 串列通訊示範程式（C 語言）

這個專案是使用 C 語言實作的 **Modbus RTU 串列通訊 Demo**，  
透過 Linux 下的序列埠（例如 `/dev/ttyM0`）與 Modbus 裝置進行通訊。

程式支援使用者互動輸入參數，包含：

- Slave Address（站號）
- Function Code（功能碼）
- Start Address（起始暫存器位址）
- Count（讀取暫存器數量）

接著會組出 Modbus RTU 訊框、送出至序列埠，並解析裝置回應的資料。

---

## 功能特色

-  互動式 CLI：執行程式後，輸入站號、功能碼、起始位址與暫存器數量即可測試
-  自行實作 Modbus RTU 封包組裝：
  - Address + Function + Start Addr High/Low + Count High/Low + CRC Low/High
-  內建 Modbus CRC-16 演算法：
  - 初始值：`0xFFFF`
  - 多項式：`0xA001`
-  封裝序列埠操作：
  - 開啟 `/dev/ttyM0`、設定 9600 8N1
  - 阻塞／非阻塞讀取
  - 調整 Baud rate、Parity、Data bits、Stop bits
-  回應解析（`RTUresponse`）：
  - 讀取 Byte Count
  - 逐筆解析 16-bit 暫存器數值
  - 顯示：
    - `valueN`（十進位）
    - `Hex`（十六進位）
    - `scale0.1`（數值除以 10，方便處理「一位小數」的設備）

---

## 專案結構

```text
modbus-rtu-serial-demo/
├─ Makefile        # 編譯設定
├─ demo.c          # 主程式：讀取使用者輸入、送出請求、接收與顯示回應
├─ RTU.c           # Modbus RTU 封包組裝、CRC、回應解析
├─ serial.c        # 串列埠開啟、設定、讀寫與相關工具
├─ serial.h        # 串列埠 API 宣告與常數定義
├─ calCRC.c        # 獨立的 CRC-16 (Modbus) 計算函式
└─ README.md       # 專案說明（本檔案）
```
---

## 主要檔案說明

### `demo.c`

- 整個 Demo 的「入口程式」
- 流程大致如下：
  - 呼叫 `SerialOpen(0)` 開啟 `/dev/ttyM0`，建立串列連線  
  - 使用 `scanf` 互動式讀取使用者輸入：
    - `slaveAddr`：Modbus 站號（`uint8_t`）
    - `functioncode`：功能碼（`uint8_t`，例如 `3 = Read Holding Registers`）
    - `Addr`：起始暫存器位址（`uint16_t`）
    - `count`：要讀取的暫存器數量（`uint16_t`）
  - 呼叫 RTU 協定相關函式：
    - `RTUsend(...)`：依上面輸入組出一筆 Modbus RTU 封包
    - `RTUshow(...)`：把組好的封包用十六進位印出來，方便確認格式
    - `SerialWrite(...)`：透過 `/dev/ttyM0` 送出封包給設備
    - `SerialBlockRead(...)`：阻塞讀取回應資料到 `data` 緩衝區
    - `RTUresponse(...)`：解析回應資料中的暫存器數值
- 輸出結果：
  - 先把接收到的每一個 byte 以十進位形式印出
  - 再印出每個暫存器的解析結果（整數值、十六進位值、以及除以 10 的工程數值）

---

### `RTU.c`

- 專門處理 **Modbus RTU 協定邏輯** 的檔案  
- 主要負責三件事：

1. **組 RTU 封包（`RTUsend`）**
   - 依據使用者輸入組出標準 Modbus RTU 訊框，包含：
     - Slave Address  
     - Function Code  
     - 起始暫存器位址（高位／低位）  
     - 讀取數量（高位／低位）  
     - CRC Low / CRC High（依 Modbus CRC-16 規則計算）
   - 把上述欄位填進 `request[0]` ～ `request[7]` 等陣列位置

2. **顯示封包內容（`RTUshow`）**
   - 將封包每個 byte 以十六進位格式印出來
   - 方便確認送出的 RTU 封包是否正確（位址、功能碼、CRC 等）

3. **解析設備回應（`RTUresponse`）**
   - 根據回應中的 Byte Count，逐 2 bytes 取出每個暫存器值（高位在前）
   - 將每個暫存器：
     - 以十進位顯示（`valueN`）
     - 以十六進位顯示（`Hex`）
     - 以 `value / 10` 顯示（`scale0.1`），方便對應「一位小數」的工程數值（例如 `253 → 25.3°C`）

---

### `serial.c` / `serial.h`

- 負責封裝 Linux 上的 **串列埠操作**，讓主程式不用直接碰 `termios`、`ioctl` 等底層 API  
- 特點與功能：

  - 使用 `/dev/ttyM%d` 當作實際裝置路徑：
    - 例如 `port = 0` → `/dev/ttyM0`
  - `SerialOpen(port)` 預設設定為：
    - Baud rate：`9600`（`B9600`）
    - Data bits：`8`（`CS8`）
    - Parity：`None`（無同位檢查）
    - Stop bits：`1`
    - `VMIN = 1`、`VTIME = 0` → 阻塞讀取，直到至少收到 1 byte

- 提供一組簡化的 API 讓上層使用：

  - **開啟／關閉：**
    - `SerialOpen(int port)`
    - `SerialClose(int port)`
  - **傳輸：**
    - `SerialWrite(int port, char *str, int len)`
    - `SerialBlockRead(int port, char *buf, int len)`（阻塞）
    - `SerialNonBlockRead(int port, char *buf, int len)`（非阻塞）
  - **連線狀態與參數設定：**
    - `SerialSetSpeed(int port, unsigned int speed)`：修改 baud rate（例如 19200 / 115200）
    - `SerialSetParam(int port, int parity, int databits, int stopbit)`：設定 parity / 資料位元數 / 停止位元
    - `SerialFlowControl(int port, int control)`：設定流量控制（無流控／硬體流控／軟體流控）
    - `SerialDataInInputQueue(int port)`：查詢 input queue 中有多少 byte 可讀
    - `SerialDataInOutputQueue(int port)`：查詢 output queue 中有多少 byte 尚未送出
    - `SerialFlushBuffer(int port)`：清掉輸入／輸出緩衝區

---

### `calCRC.c`

- 專門實作 **Modbus CRC-16 演算法** 的檔案  

- 功能說明：
  - 提供一個函式，用來對任意一段 byte 資料計算 CRC：
    - 初始值：`0xFFFF`
    - 多項式：`0xA001`
  - 計算結果可以用在：
    - 送出請求封包時填入 CRC 欄位
    - 收到回應後重新計算 CRC，確認資料是否正確（CRC 驗證）

- 在專案中的使用方式：
  - 可以由 `RTU.c` 直接呼叫這個 CRC 函式，取代重複撰寫 CRC 邏輯
  - 如果只想單獨測試 CRC 是否正確，可以保留此檔自己的 `main()` 測試程式
  - 正式整合到 Demo 專案時，通常會：
    - 移除 `main()`，或
    - 用 `#ifdef TEST ... #endif` 包起來，避免和 `demo.c` 的 `main()` 衝突

