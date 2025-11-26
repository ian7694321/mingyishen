import pyodbc
from datetime import datetime

# 連線字串
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=192.168.208.;'              
    'DATABASE=FINEX;'
    'UID=;'
    'PWD=;'
    'TrustServerCertificate=yes;'  
)

# 建立 cursor 操作資料庫
cursor = conn.cursor()

# 執行查詢
cursor.execute("SELECT TOP 100 * FROM View_TSMC_lotno")

# 取得欄位名稱
columns = [column[0] for column in cursor.description]

# 取得查詢結果
rows = cursor.fetchall()

# 絕對路徑
output_path = "/home/mingyi/ming/ming/Work/Sql_time/tsmc_time.txt"

with open(output_path, "w", encoding="utf-8") as f:
    # 寫每一筆資料
    for row in rows:
        f.write("\t".join(map(str, row)) + "\n")

#print("ok")

# 關閉連線
conn.close()

print("log執行時間：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))