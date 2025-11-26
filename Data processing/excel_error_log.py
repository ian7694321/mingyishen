import os
import glob
import re
import calendar
from datetime import datetime, date
import pandas as pd
import sys

# ========= 路徑設定 =========
if getattr(sys, "frozen", False):
    # 打包成 EXE 時：抓 EXE 本身所在的資料夾
    base_dir = os.path.dirname(sys.executable)
else:
    # 抓.py 所在的資料夾
    base_dir = os.path.dirname(os.path.abspath(__file__))

folder_path = os.path.join(base_dir, "total")
output_dir = os.path.join(base_dir, "compare")
os.makedirs(output_dir, exist_ok=True)

print("base_dir =", base_dir)       # 實際路徑
print("folder_path =", folder_path)
print("output_dir  =", output_dir)

# ========= 抓取最新 TOTAL_YYYYMMDD_HHMM 檔 =========
excel_files = [f for f in glob.glob(os.path.join(folder_path, "*.xls*"))
               if not os.path.basename(f).startswith("~$")]
if not excel_files:
    raise FileNotFoundError(f"在 {folder_path} 找不到任何 Excel 檔案")

pattern = re.compile(r"TOTAL_(\d{8})_(\d{4})")
def extract_datetime(filename):
    m = pattern.search(os.path.basename(filename))
    if m:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M")
    return datetime.fromtimestamp(os.path.getmtime(filename))

latest_file = max(excel_files, key=extract_datetime)
print(f"最新檔案：{latest_file}")

# ========= 讀取資料 =========
df = pd.read_excel(latest_file, dtype=str)
df.columns = [str(c).strip() for c in df.columns]

# ========= 時間小工具 =========
def to_date(val):
    if pd.isna(val): return pd.NaT
    s = str(val).strip().replace(".", "-").replace("/", "-")
    return pd.to_datetime(s, errors="coerce").date()

def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))

def set_month_day(d: date, months_ahead: int, day: int) -> date:
    y = d.year + (d.month - 1 + months_ahead) // 12
    m = (d.month - 1 + months_ahead) % 12 + 1
    return date(y, m, day)

def month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)

# ========= 跳過條件 =========
SKIP_TERMS = {
    "月結30天(EXW date)",
    "月結60天(FCA date)",
    "請財務部確認付款日",
}

# ========= 規則主函式 =========
def expected_pay_date(doc_dt: date, term_name: str):
    """
    優先序：
    1) 跳過：SKIP_TERMS
    2) 當月15號 → 當月15
    3) 當月18號 → 當月18
    4) 次月15號付款 → 次月15
    5) 月結(18+30n)天 → 次月起 n 個月後的 18 日（18/48/78…）
    6) 月結30/60/120天 → +1/2/4 月取月底

    其餘 → 未支援
    """
    if pd.isna(doc_dt) or not term_name:
        return pd.NaT, "無單據日期或付款條件空白"

    term = str(term_name).strip()
    if term in SKIP_TERMS:
        return pd.NaT, "使用者指定：跳過比對"

    t = term.replace(" ", "")

    if re.fullmatch(r"當月15號", t):
        return date(doc_dt.year, doc_dt.month, 15), "當月15號 → 當月15日"

    if re.fullmatch(r"當月18號付款", t):
        # 單據日期 <= 18 號：當月 18 日
        if doc_dt.day <= 18:
            return date(doc_dt.year, doc_dt.month, 18), "當月18號付款（單據日≦18）→ 當月18日"
        # 單據日期 > 18 號：次月 18 日
        else:
            pay_dt = set_month_day(doc_dt, 1, 18)
            return pay_dt, "當月18號付款（單據日>18）→ 次月18日"

    if re.fullmatch(r"次月15號付款", t):
        return set_month_day(doc_dt, 1, 15), "次月15號付款 → 下個月15日"

    m_any = re.fullmatch(r"月結(\d+)天", t)
    if m_any:
        days = int(m_any.group(1))
        if days >= 18 and (days - 18) % 30 == 0:
            months_ahead = 1 + (days - 18) // 30
            return set_month_day(doc_dt, months_ahead, 18), f"月結{days}天 → +{months_ahead}個月的18日"
        mapping_month_end = {30: 1, 60: 2, 120: 4}
        if days in mapping_month_end:
            months = mapping_month_end[days]
            return month_end(add_months(doc_dt, months)), f"月結{days}天 → +{months}個月取月底"
        return pd.NaT, f"未支援：月結{days}天"

    return pd.NaT, "未支援（非月結X天/當月N號/次月N號）"

# ========= 欄位對應 =========
def pick_col(cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

DOC_COL   = pick_col(["單據日期", "憑單日期"])
TERM_COL  = pick_col(["付款條件名稱", "付款條件", "付款條件說明"])
PLAN_COL  = pick_col(["預計付款日", "應付日期", "付款日期"])
KEY_COL   = pick_col(["憑單單號", "單據編號", "憑單編號", "單號", "發票號碼"])
VEND_COL  = pick_col(["廠商簡稱", "廠商名稱", "供應商名稱", "供應商"])

if not DOC_COL or not TERM_COL:
    miss = []
    if not DOC_COL:  miss.append("單據日期/憑單日期")
    if not TERM_COL: miss.append("付款條件名稱/付款條件")
    raise ValueError("找不到必要欄位：" + "、".join(miss))

# ========= 計算與比對 =========
df["_單據日期(date)"] = df[DOC_COL].apply(to_date)
df["_付款條件"] = df[TERM_COL].astype(str)

exp_dates, reasons = [], []
for doc_dt, term in zip(df["_單據日期(date)"], df["_付款條件"]):
    pay, why = expected_pay_date(doc_dt, term)
    exp_dates.append(pay)
    reasons.append(why)

df["系統預計付款日"] = exp_dates
df["計算依據"] = reasons

if "廠商簡稱" in df.columns:
    special_mask = (
        df["廠商簡稱"].astype(str).str.strip().eq("南科管理局")
        & df["_付款條件"].astype(str).str.replace(" ", "").eq("次月15號付款")
        & df["_單據日期(date)"].notna()
    )

    def _nk_custom_pay(d: date) -> date:
        # 單據月份的 15 號
        return date(d.year, d.month, 15)

    df.loc[special_mask, "系統預計付款日"] = df.loc[special_mask, "_單據日期(date)"].apply(_nk_custom_pay)
    df.loc[special_mask, "計算依據"] = "南科管理局特例：次月15號付款 → 當月15日"
    

if PLAN_COL:
    df["_預計付款日(date)"] = df[PLAN_COL].apply(to_date)
    comparable_mask = df["系統預計付款日"].notna()
    df["是否一致"] = pd.NA
    df.loc[comparable_mask, "是否一致"] = (
        df.loc[comparable_mask, "_預計付款日(date)"] == df.loc[comparable_mask, "系統預計付款日"]
    )
else:
    df["_預計付款日(date)"] = pd.NaT
    df["是否一致"] = pd.NA

# ========= 顯示欄位/旗標 =========
def fmt(d):
    return "" if pd.isna(d) else d.strftime("%Y/%m/%d")

df["單據日期(顯示)"]       = df["_單據日期(date)"].apply(fmt)
df["預計付款日(顯示)"]     = df["_預計付款日(date)"].apply(fmt)
df["系統預計付款日(顯示)"] = df["系統預計付款日"].apply(fmt)

skip_mask = df["計算依據"].eq("使用者指定：跳過比對")
unsupported_mask = df["系統預計付款日"].isna() & ~skip_mask
mismatch_mask = (df["是否一致"] == False)

# 相差天數
df["相差天數"] = df.apply(
    lambda r: (pd.Timestamp(r["_預計付款日(date)"]) - pd.Timestamp(r["系統預計付款日"])).days
              if pd.notna(r["_預計付款日(date)"]) and pd.notna(r["系統預計付款日"]) else pd.NA,
    axis=1
)

# ========= 別名成指定欄名 & 補空欄 =========
if KEY_COL and KEY_COL != "憑單單號" and "憑單單號" not in df.columns:
    df["憑單單號"] = df[KEY_COL]
if DOC_COL and DOC_COL != "單據日期" and "單據日期" not in df.columns:
    df["單據日期"] = df[DOC_COL]
if TERM_COL and TERM_COL != "付款條件名稱" and "付款條件名稱" not in df.columns:
    df["付款條件名稱"] = df[TERM_COL]
if PLAN_COL and PLAN_COL != "預計付款日" and "預計付款日" not in df.columns:
    df["預計付款日"] = df[PLAN_COL]
if VEND_COL and VEND_COL != "廠商簡稱" and "廠商簡稱" not in df.columns:
    df["廠商簡稱"] = df[VEND_COL]

for col in ["憑單單號", "單據日期", "廠商代號", "廠商簡稱", "付款條件代號",
            "付款條件名稱", "預計付款日", "系統預計付款日(顯示)", "相差天數", "計算依據"]:
    if col not in df.columns:
        df[col] = ""

# ========= 報表 =========
# 1) 不一致明細（依單據日期排序：由早到晚）
mismatch_cols = [
    "憑單單號", "單據日期", "廠商代號", "廠商簡稱", "付款條件代號",
    "付款條件名稱", "預計付款日", "系統預計付款日(顯示)", "相差天數", "計算依據",
]
report_mismatch = df.loc[mismatch_mask, mismatch_cols].copy()
report_mismatch["_sort_date"] = pd.to_datetime(report_mismatch["單據日期"], errors="coerce")
report_mismatch = report_mismatch.sort_values(by="_sort_date", ascending=True).drop(columns=["_sort_date"])

# 2) 統計（僅可比對列）
total_mismatch = len(report_mismatch)
by_term = (df.loc[mismatch_mask]
             .groupby("付款條件名稱", dropna=False)
             .size().reset_index(name="數量")
             .sort_values("數量", ascending=False))
summary_rows = [{"項目": "不一致總筆數（可比對）", "數量": total_mismatch}]
if not by_term.empty:
    summary_rows.append({"項目": "（依付款條件分組統計）", "數量": ""})
summary_df = pd.DataFrame(summary_rows)

# 3) 已跳過 / 未支援或缺資料（同欄位順序）
report_skipped = df.loc[skip_mask, mismatch_cols].copy()
report_unsupported = df.loc[unsupported_mask, mismatch_cols].copy()

# 4) 全部檢查（原友善檢視）
view_cols = []
for c in ["憑單單號", "單據編號", "發票號碼", "供應商", "品名"]:
    if c in df.columns: view_cols.append(c)
view_cols += ["單據日期", "單據日期(顯示)", "付款條件名稱"]
if "預計付款日" in df.columns: view_cols.append("預計付款日")
view_cols += ["預計付款日(顯示)", "系統預計付款日(顯示)", "是否一致", "相差天數", "計算依據"]
report_all = df[view_cols].copy()

# ========= 輸出（清理控制字元 + xlsxwriter）=========
_ILLEGAL_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
def sanitize_df(df_in: pd.DataFrame) -> pd.DataFrame:
    out = df_in.copy()
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = (
                out[c].astype(str)
                      .map(lambda s: "" if s == "nan" else s)
                      .map(lambda s: _ILLEGAL_CTRL.sub("", s))
            )
    return out

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = os.path.join(output_dir, f"TERMS_COMPARE_{ts}.xlsx")

_to_write = {
    "不一致統計":          sanitize_df(summary_df),
    "不一致_依付款條件":    sanitize_df(by_term) if not by_term.empty else pd.DataFrame(columns=["（無分組資料）"]),
    "不一致明細":          sanitize_df(report_mismatch) if not report_mismatch.empty else pd.DataFrame(columns=["（恭喜！未發現不一致）"]),
    "已跳過條件":          sanitize_df(report_skipped) if not report_skipped.empty else pd.DataFrame(columns=["（依使用者設定跳過的列）"]),
    "未支援或缺資料":      sanitize_df(report_unsupported) if not report_unsupported.empty else pd.DataFrame(columns=["（提示：未支援規則或缺資料的列）"]),
    "全部檢查":            sanitize_df(report_all),
}

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    for sheet, data in _to_write.items():
        data.to_excel(writer, sheet_name=sheet[:31], index=False)

print(f"不一致筆數（可比對）：{total_mismatch}")
print(f"跳過筆數：{len(report_skipped)}")
print(f"已輸出報告：{out_path}")
