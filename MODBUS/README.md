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
