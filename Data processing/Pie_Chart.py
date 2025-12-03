# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
import urllib.request
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
from openpyxl.drawing.image import Image as XLImage
import sys

# =========================
# 基準路徑：支援 .py 與 PyInstaller EXE
# =========================
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# =========================
# 自動偵測目標資料夾
# =========================
def get_target_dirs(base: Path):
    exclude_exact = {"out", "__pycache__", ".git", ".venv", "venv"}
    exclude_contains = ["compare", "test", "backup", "_bak"]
    dirs = []
    for d in base.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        if name in exclude_exact or name.startswith("."):
            continue
        low = name.lower()
        if any(k in low for k in exclude_contains):
            continue
        dirs.append(name)
    return sorted(dirs)

# =========================
# 使用者設定
# =========================
CATEGORY_COL = "付款條件名稱"
VALUE_COL = "本幣貨款金額"
TOP_K = 10
IMG_SCALE = 0.5
ANCHOR_CELL = "E2"
PLACE_BELOW_DATA = False
PCT_MIN_IN_CHART = 2.0

# =========================
# 中文字型
# =========================
def set_chinese_font():
    candidates = [
        "Microsoft JhengHei", "Microsoft YaHei", "PMingLiU", "MingLiU",
        "SimHei", "SimSun", "PingFang TC", "Noto Sans CJK TC", "Noto Sans TC"
    ]
    avail = {f.name for f in font_manager.fontManager.ttflist}
    chosen = None
    for name in candidates:
        if name in avail:
            chosen = name
            break
    if not chosen:
        cache_dir = Path.home() / ".fonts" / "NotoSansCJK"
        cache_dir.mkdir(parents=True, exist_ok=True)
        ttf_path = cache_dir / "NotoSansCJKtc-Regular.otf"
        if not ttf_path.exists():
            print("下載中文字型 Noto Sans CJK TC ...")
            url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
            urllib.request.urlretrieve(url, str(ttf_path))
        font_manager.fontManager.addfont(str(ttf_path))
        chosen = "Noto Sans CJK TC"
    matplotlib.rcParams["font.sans-serif"] = [chosen]
    matplotlib.rcParams["axes.unicode_minus"] = False

# =========================
# 欄位對應工具
# =========================
def _normalize_name(s: str) -> str:
    """
    正規化欄位名稱：去空白、小寫、去掉常見符號與括號
    """
    s = str(s).strip().lower()
    for ch in [" ", "_", "-", "(", ")", "（", "）", "[", "]", "【", "】", ":", "："]:
        s = s.replace(ch, "")
    return s

_CATEGORY_ALIASES = {
    "付款條件名稱", "付款條件", "付款條件名稱", "付款條件代碼名稱",
    "付款條件說明",
    "paymentterms", "paymentterm", "terms", "termname", "paymenttermsname"
}
_VALUE_ALIASES = {
    "本幣貨款金額", "本幣金額", "本幣金額小計",
    "金額(本幣)", "金額本幣", "金額",
    "twd", "amounttwd", "amount(twd)", "amountntd",
    "ntdamount", "localamount",
    "amount", "amountlocal"
}

NORM_CATEGORY_KEYS = {_normalize_name(c) for c in _CATEGORY_ALIASES}
NORM_VALUE_KEYS = {_normalize_name(c) for c in _VALUE_ALIASES}

def try_standardize_columns(df: pd.DataFrame):
    norm_cols = {_normalize_name(c): c for c in df.columns}

    cat_src = None
    for cand in _CATEGORY_ALIASES:
        key = _normalize_name(cand)
        if key in norm_cols:
            cat_src = norm_cols[key]
            break

    val_src = None
    for cand in _VALUE_ALIASES:
        key = _normalize_name(cand)
        if key in norm_cols:
            val_src = norm_cols[key]
            break

    if not cat_src or not val_src:
        return None

    out = df.rename(columns={cat_src: CATEGORY_COL, val_src: VALUE_COL}).copy()
    return out

# =========================
# 從 sheet 中找出真正的表頭列
# =========================
def extract_table_from_sheet(df_raw: pd.DataFrame) -> pd.DataFrame | None:
    """
    df_raw 是 header=None 讀進來的整張工作表
    會掃每一列，找出包含「付款條件」/「金額」欄名的那一列當 header
    """
    header_row = None
    nrows = len(df_raw)

    for i in range(nrows):
        row = df_raw.iloc[i]
        hit_cat = False
        hit_val = False
        for v in row:
            if pd.isna(v):
                continue
            key = _normalize_name(v)
            if key in NORM_CATEGORY_KEYS:
                hit_cat = True
            if key in NORM_VALUE_KEYS:
                hit_val = True
        if hit_cat or hit_val:
            header_row = i
            break

    if header_row is None:
        return None

    header = df_raw.iloc[header_row]
    df = df_raw.iloc[header_row + 1 :].copy()
    df.columns = header

    # 刪掉完全空白列
    df = df.dropna(how="all")

    # 刪掉完全是 Unnamed 且全空的欄
    mask_keep = []
    for col in df.columns:
        col_str = str(col)
        if col_str.startswith("Unnamed"):
            if df[col].notna().any():
                mask_keep.append(True)
            else:
                mask_keep.append(False)
        else:
            mask_keep.append(True)
    df = df.loc[:, mask_keep]

    return df

# =========================
# 讀取最新 Excel（含 .xlsb）
# =========================
def _collect_excel_files(folder: Path):
    files = []
    for ext in ("*.xlsx", "*.xlsm", "*.xls", "*.xlsb"):
        files += list(folder.rglob(ext))
    return [f for f in files if not f.name.startswith("~$")]

def _read_one_excel_file(f: Path) -> dict:
    # header=None：讓我們自己找哪一列是欄名
    return pd.read_excel(f, sheet_name=None, header=None)

def read_latest_excel_in_dir(folder: Path) -> pd.DataFrame | None:
    files = _collect_excel_files(folder)
    if not files:
        # 這裡不要中斷整個程式，改成略過這個資料夾
        print(f"[SKIP] 資料夾 {folder.name} 中沒有 Excel 檔，已略過。")
        return None

    latest = max(files, key=lambda p: p.stat().st_mtime)
    print(f"使用最新檔：{latest.relative_to(folder).as_posix()}")

    frames = []
    xls = _read_one_excel_file(latest)
    for sheet, df_raw in (xls or {}).items():
        if df_raw is None or df_raw.empty:
            continue

        df = extract_table_from_sheet(df_raw)
        if df is None or df.empty:
            print(f"[SKIP] {latest.name}::{sheet} 找不到欄位列，已略過。")
            continue

        std = try_standardize_columns(df)
        if std is None:
            print(f"[SKIP] {latest.name}::{sheet} 欄位不符，已略過。")
            continue

        std["__source_file"] = latest.name
        std["__sheet"] = str(sheet)
        frames.append(std)

    if not frames:
        first_sheet, first_df = next(iter(xls.items()))
        print("==== 欄位對不到，請檢查這份檔案的欄位名稱 ====")
        print(f"檔案：{latest}")
        print(f"工作表：{first_sheet}")
        print("欄位清單：", list(first_df.iloc[0]))
        print("=======================================")
        # 這種屬於資料問題，維持 raise，讓你知道這個檔案有問題
        raise RuntimeError(f"{latest} 無任何符合欄位的工作表。")

    return pd.concat(frames, ignore_index=True)

# =========================
# 前處理與彙總
# =========================
def aggregate(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    1) 先把「含有『小結』字樣的列」略過（不要統計）
    2) 再把「單據日期 + 付款條件名稱 + 預計付款日 都空白」的列略過（如果有這些欄位）
    3) 最後把分類或金額為空白 / 非數字的列略過，做彙總
    """

    df = df_all.copy()

    # 0) 先略過「小結」列（例如某欄是 '小結:'、'小結' 等）
    subtotal_mask = df.apply(
        lambda row: row.astype(str)
                    .str.strip()
                    .str.startswith("小結")
                    .any(),
        axis=1,
    )
    skipped_subtotal = int(subtotal_mask.sum())
    if skipped_subtotal > 0:
        print(f"[INFO] 已略過 {skipped_subtotal} 筆『小結』小計列")

    df = df.loc[~subtotal_mask].copy()

    # 1) 三欄都空白就略過（如果這三欄存在）
    needed_cols = ["單據日期", CATEGORY_COL, "預計付款日"]
    if all(col in df.columns for col in needed_cols):

        def _is_blank(v) -> bool:
            s = str(v).strip()
            return s == "" or s.lower() in ("nan", "nat")

        mask_all_blank = (
            df["單據日期"].map(_is_blank) &
            df[CATEGORY_COL].map(_is_blank) &
            df["預計付款日"].map(_is_blank)
        )

        # 不再印出略過幾筆，只做過濾
        df = df.loc[~mask_all_blank].copy()

    # 2) 後續只看 分類 + 金額
    tmp = df[[CATEGORY_COL, VALUE_COL]].copy()

    # 分類：去空白，空字串 → NA
    tmp[CATEGORY_COL] = tmp[CATEGORY_COL].astype(str).str.strip()
    tmp.loc[tmp[CATEGORY_COL] == "", CATEGORY_COL] = pd.NA

    # 金額：去逗號 / 空白 → 轉數字
    raw_val = (
        tmp[VALUE_COL]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    raw_val = raw_val.replace("", pd.NA)
    tmp[VALUE_COL] = pd.to_numeric(raw_val, errors="coerce")

    before = len(tmp)
    tmp = tmp.dropna(subset=[CATEGORY_COL, VALUE_COL])
    dropped = before - len(tmp)
    if dropped > 0:
        print(f"[INFO] 已略過 {dropped} 筆「分類或金額為空白 / 非數字」的資料列")

    if tmp.empty:
        raise RuntimeError("全部資料列的『分類』或『金額』都是空白/非數字，無法繪製圓餅圖。")

    agg = tmp.groupby(CATEGORY_COL, dropna=False, as_index=False)[VALUE_COL].sum()
    agg = agg.sort_values(VALUE_COL, ascending=False, ignore_index=True)

    if TOP_K and len(agg) > TOP_K:
        head = agg.iloc[:TOP_K].copy()
        tail_sum = agg.iloc[TOP_K:][VALUE_COL].sum()
        head.loc[len(head)] = ["其他", tail_sum]
        agg = head

    return agg

# =========================
# 畫圖 + 嵌入 Excel
# =========================
def save_summary_and_plot(df_all: pd.DataFrame, agg: pd.DataFrame, out_dir: Path, tag: str, ts: str):
    """
    df_all : 原始明細（已經標準化欄位名稱，至少有 CATEGORY_COL / VALUE_COL）
    agg    : 依 CATEGORY_COL 彙總後的 DataFrame（aggregate() 的結果）
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    out_xlsx = out_dir / f"summary_{tag}_{ts}.xlsx"

    set_chinese_font()
    total = agg[VALUE_COL].sum()
    pct_list = (agg[VALUE_COL] / total * 100).tolist()

    # ========================
    # 主圓餅圖（維持原本樣式：圓餅 + 右表 + 總金額）
    # ========================
    fig, ax = plt.subplots(figsize=(11, 8))
    wedges, texts, autotexts = ax.pie(
        agg[VALUE_COL],
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p >= PCT_MIN_IN_CHART else "",
        startangle=90,
        pctdistance=0.78,
        wedgeprops={"width": 0.6, "edgecolor": "white"},
    )
    colors = [w.get_facecolor() for w in wedges]

    # 右側表格（全部分類）
    table_data = [
        ["■", cat, f"{val:,.0f} TWD", f"{pct:.1f}%"]
        for cat, val, pct in zip(agg[CATEGORY_COL], agg[VALUE_COL], pct_list)
    ]
    col_labels = ["", "分類名稱", "金額 (TWD)", "占比 (%)"]

    table = plt.table(
        cellText=table_data,
        colLabels=col_labels,
        colLoc="center",
        cellLoc="center",
        loc="right",
        bbox=[1.03, 0.05, 0.55, 0.82],  # 拉回比較高，跟原本類似
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    for i, color in enumerate(colors):
        cell = table[(i + 1, 0)]
        cell.get_text().set_color(color)
        cell.get_text().set_fontweight("bold")

    # 只留「總金額」這一行
    plt.text(
        1.03, 0.93, f"總金額：{total:,.0f} TWD",
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="left",
        va="center",
    )

    ax.set_title(f"{tag}｜{CATEGORY_COL} 對應 {VALUE_COL}", fontsize=13, pad=20)
    ax.axis("equal")

    # 主圓餅圖圖片檔
    out_png = img_dir / f"pie_{tag}_{ts}.png"
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # ========================
    # 前 3 名付款條件（只做計算，不在主圖上畫文字）
    # ========================
    top_n = min(3, len(agg))
    top_df = None
    if top_n > 0:
        top_rows = agg.iloc[:top_n].copy()
        pct_top = (top_rows[VALUE_COL] / total * 100) if total else 0

        top_df = pd.DataFrame({
            "排名": [i + 1 for i in range(top_n)],
            CATEGORY_COL: top_rows[CATEGORY_COL].tolist(),
            VALUE_COL: top_rows[VALUE_COL].tolist(),
            "占比 (%)": [round(p, 1) for p in pct_top.tolist()],
        })

    # ========================
    # 額外一張圖：前三名付款條件橫條圖（放在 Top3 工作表）
    # ========================
    out_png_top3 = None
    if top_n > 0 and top_df is not None:
        fig2, ax2 = plt.subplots(figsize=(6, 4))

        ax2.barh(top_df[CATEGORY_COL], top_df[VALUE_COL])
        ax2.invert_yaxis()  # 第一名在最上面
        ax2.set_xlabel("金額 (TWD)")
        ax2.set_title(f"{tag} 前 {top_n} 名付款條件")

        for i, (val, pct) in enumerate(zip(top_df[VALUE_COL], top_df["占比 (%)"])):
            ax2.text(
                val, i,
                f"{val:,.0f} TWD（{pct:.1f}%）",
                va="center",
                ha="left",
                fontsize=9,
            )

        fig2.tight_layout()
        out_png_top3 = img_dir / f"top3_{tag}_{ts}.png"
        fig2.savefig(out_png_top3, dpi=300, bbox_inches="tight")
        plt.close(fig2)

    # ========================
    # 每一個前 3 名付款條件內的「廠商佔比」
    # 佔比母體 = 該付款條件自己的金額小計
    # ========================
    VENDOR_COL_CANDIDATES = ["廠商簡稱", "廠商名稱", "供應商名稱", "廠商代號", "供應商代號"]
    vendor_col = None
    for c in VENDOR_COL_CANDIDATES:
        if c in df_all.columns:
            vendor_col = c
            break

    vendor_sections: list[tuple[str, pd.DataFrame]] = []

    if vendor_col is not None and top_n > 0:
        top3_terms = agg[CATEGORY_COL].head(top_n).tolist()

        for term in top3_terms:
            tmp = df_all[df_all[CATEGORY_COL] == term][[vendor_col, VALUE_COL]].copy()
            if tmp.empty:
                continue

            tmp[vendor_col] = tmp[vendor_col].astype(str).str.strip()
            tmp.loc[tmp[vendor_col] == "", vendor_col] = pd.NA

            raw_val = (
                tmp[VALUE_COL]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            raw_val = raw_val.replace("", pd.NA)
            tmp[VALUE_COL] = pd.to_numeric(raw_val, errors="coerce")

            tmp = tmp.dropna(subset=[vendor_col, VALUE_COL])
            if tmp.empty:
                continue

            df_term = (
                tmp
                .groupby(vendor_col, as_index=False)[VALUE_COL]
                .sum()
                .sort_values(VALUE_COL, ascending=False, ignore_index=True)
            )

            term_total = df_term[VALUE_COL].sum()
            if term_total > 0:
                df_term["占比 (%)"] = df_term[VALUE_COL] / term_total * 100
            else:
                df_term["占比 (%)"] = 0.0

            df_term.insert(0, CATEGORY_COL, term)
            vendor_sections.append((term, df_term))

    # ========================
    # 輸出 Excel：Summary + Top3
    # ========================
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        # Summary 工作表：全部彙總 + 主圓餅圖
        agg.to_excel(writer, index=False, sheet_name="Summary")
        wb = writer.book
        ws = writer.sheets["Summary"]

        ws.set_column("A:A", 20)
        ws.set_column("B:B", 18)

        try:
            scale = float(IMG_SCALE)
        except Exception:
            scale = 0.5
        scale = max(scale, 0.05)

        anchor = ANCHOR_CELL if not PLACE_BELOW_DATA else f"A{len(agg) + 3}"
        ws.insert_image(anchor, str(out_png), {
            "x_scale": scale,
            "y_scale": scale,
            "object_position": 1,
        })

        # Top3 工作表：前 3 名付款條件 + Top3 圖 + 各付款條件內廠商佔比
        if top_n > 0 and top_df is not None:
            sheet_name_top = "Top3"
            top_df.to_excel(writer, index=False, sheet_name=sheet_name_top)
            ws_top = writer.sheets[sheet_name_top]

            ws_top.set_column("A:A", 6)   # 排名
            ws_top.set_column("B:B", 25)  # 付款條件名稱
            ws_top.set_column("C:C", 18)  # 金額
            ws_top.set_column("D:D", 12)  # 占比

            if out_png_top3 is not None:
                ws_top.insert_image("F2", str(out_png_top3), {
                    "x_scale": scale,
                    "y_scale": scale,
                    "object_position": 1,
                })

            # 下面依序寫入每一個前 3 名付款條件的廠商佔比
            start_row = len(top_df) + 4

            for term, df_term in vendor_sections:
                title = f"{term} 內各廠商佔比（以該付款條件金額小計為母體）"
                ws_top.write(start_row, 0, title)

                df_term.to_excel(
                    writer,
                    sheet_name=sheet_name_top,
                    startrow=start_row + 1,
                    index=False
                )

                ws_top.set_column("A:A", 20)  # 付款條件名稱
                ws_top.set_column("B:B", 25)  # 廠商
                ws_top.set_column("C:C", 18)  # 金額
                ws_top.set_column("D:D", 12)  # 占比

                start_row += len(df_term) + 4

    print(f"{tag} 完成：{out_xlsx}")

# =========================
# 主程式
# =========================
def main():
    base = BASE_DIR
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dirs = get_target_dirs(base)
    print(f"Base: {base}")
    print(f"自動偵測到資料夾：{target_dirs}")

    for sub in target_dirs:
        folder = base / sub
        if not folder.exists():
            continue

        print(f"處理：{sub}（讀取模式：最新檔）")
        df_all = read_latest_excel_in_dir(folder)
        if df_all is None:
            # 例如該資料夾空的，就跳過
            continue

        agg = aggregate(df_all)
        save_summary_and_plot(df_all, agg, base / "out" / sub, sub, ts)

if __name__ == "__main__":
    main()
