import argparse
from collections import Counter
from datetime import datetime
import numpy as np
import pandas as pd

COMMON_KEY_CANDIDATES = [
    ["憑單單", "憑單號", "憑單編號", "憑單No", "憑單NO", "單號", "單據號", "單據編號"],
    ["序號", "項次", "行號", "Line", "line"],
    ["供應商代碼", "廠商代碼", "廠商代碼(代號)", "廠商代號", "VendorCode"],
]

def normalize_df(df: pd.DataFrame, case_insensitive=False) -> pd.DataFrame:
    """移除 Unnamed；去空白；日期統一；文字可選忽略大小寫；NaN→''"""
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")].copy()
    df.columns = df.columns.astype(str)

    for c in df.columns:
        s = df[c]

        # 先處理真正的 datetime dtype
        if np.issubdtype(s.dtype, np.datetime64):
            df[c] = pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d")
            continue

        # 把字串/數值解析為日期字串
        s2 = pd.to_datetime(s, errors="coerce", format="%Y/%m/%d")
        mask = s2.isna()
        if mask.any():
            s3 = pd.to_datetime(s[mask], errors="coerce", format="%Y-%m-%d")
            s2.loc[mask] = s3
        mask = s2.isna() & pd.to_numeric(s, errors="coerce").notna()
        if mask.any():
            nums = pd.to_numeric(s[mask], errors="coerce")
            s4 = pd.to_datetime(nums, unit="D", origin="1899-12-30", errors="coerce")
            s2.loc[mask] = s4

        if s2.notna().any():
            out = s.astype(object).copy()
            ok = s2.notna()
            out.loc[ok] = s2.loc[ok].dt.strftime("%Y-%m-%d")
            s = out

        if s.dtype == object:
            s = s.fillna("").astype(str).str.strip()
            if case_insensitive:
                s = s.str.lower()

        df[c] = s.fillna("").astype(object)

    return df

def pick_keys(df_left: pd.DataFrame, df_right: pd.DataFrame):
    """從常見候選自動挑 key（盡量組合成複合鍵），回傳欄名清單或空清單。"""
    left_cols = {c.lower(): c for c in df_left.columns}
    right_cols = {c.lower(): c for c in df_right.columns}

    chosen = []
    for group in COMMON_KEY_CANDIDATES:
        found = None
        for name in group:
            low = name.lower()
            if low in left_cols and low in right_cols:
                found = (left_cols[low], right_cols[low])
                break
        if found:
            chosen.append(found)

    # 回傳左、右對應的欄名列表（順序一致）
    if not chosen:
        return [], []
    left_keys = [p[0] for p in chosen]
    right_keys = [p[1] for p in chosen]
    return left_keys, right_keys

def compare_with_keys(dfL, dfR, keysL, keysR):
    """依 keys merge 後做欄位差異比較。回傳 onlyL, onlyR, col_diff(DataFrame)。"""
    # 對齊欄位集合
    all_cols = sorted(set(dfL.columns) | set(dfR.columns))

    # 先內外連接，找到只在單邊的 key
    left_key_df = dfL[keysL].copy()
    right_key_df = dfR[keysR].copy()
    left_key_df.columns = [f"__k{i}" for i in range(len(keysL))]
    right_key_df.columns = [f"__k{i}" for i in range(len(keysR))]

    left_key_df["__join_key"] = left_key_df.apply(lambda r: tuple(r.values), axis=1)
    right_key_df["__join_key"] = right_key_df.apply(lambda r: tuple(r.values), axis=1)

    setL = Counter(left_key_df["__join_key"].tolist())
    setR = Counter(right_key_df["__join_key"].tolist())

    onlyL_keys = list((setL - setR).elements())
    onlyR_keys = list((setR - setL).elements())

    # 取出只在左/只在右的列
    def rows_by_keys(df, keys, key_tuples):
        if not key_tuples:
            return df.iloc[0:0].copy()
        mask = pd.Series(False, index=df.index)
        kdf = df[keys].apply(lambda r: tuple(r.values), axis=1)
        for k in set(key_tuples):
            # 若重複出現 n 次，就取前 n 列
            idx = kdf[kdf == k].index
            n = key_tuples.count(k)
            mask.loc[idx[:n]] = True
        return df.loc[mask].copy()

    only_in_left = rows_by_keys(dfL, keysL, onlyL_keys)
    only_in_right = rows_by_keys(dfR, keysR, onlyR_keys)

    # 對齊可一一對上的鍵（兩邊最小相同次數）
    common_keys = list((setL & setR).elements())

    # 建立「鍵 → 行列索引佇列」
    def build_index_map(df, keys):
        kseries = df[keys].apply(lambda r: tuple(r.values), axis=1)
        mp = {}
        for i, k in zip(df.index, kseries):
            mp.setdefault(k, []).append(i)
        return mp

    mapL = build_index_map(dfL, keysL)
    mapR = build_index_map(dfR, keysR)

    diffs = []
    # 逐鍵、逐筆配對，檢查所有共同欄位的值是否相同
    common_cols = [c for c in all_cols if c in dfL.columns and c in dfR.columns
                   and c not in keysL and c not in keysR]  # 避免把 key 欄也當成比較欄

    for k in common_keys:
        # 取兩邊對應的最小次數配對
        n = min(len(mapL[k]), len(mapR[k]))
        for t in range(n):
            iL = mapL[k][t]
            iR = mapR[k][t]
            rowL = dfL.loc[iL]
            rowR = dfR.loc[iR]
            ne = rowL[common_cols] != rowR[common_cols]
            if ne.any():
                for col in common_cols:
                    if ne[col]:
                        entry = { "key": k, "column": col, "left_value": rowL[col], "right_value": rowR[col] }
                        # 把 key 展開到欄位，方便篩選
                        for ix, kk in enumerate(k):
                            entry[f"key_{ix+1}"] = kk
                        diffs.append(entry)

    col_diff = pd.DataFrame(diffs, columns=["key"] + [f"key_{i+1}" for i in range(len(keysL))] + ["column", "left_value", "right_value"])
    return only_in_left, only_in_right, col_diff

def main():
    ap = argparse.ArgumentParser(description="Compare two Excel files with column-level diff.")
    ap.add_argument("left_file")
    ap.add_argument("right_file")
    ap.add_argument("--left-sheet", default="TOTAL", help="Sheet name in left file. Default: TOTAL")
    ap.add_argument("--right-sheet", default=None, help="Sheet name in right file. Default: first sheet")
    ap.add_argument("--keys", nargs="+", help="Column names (in both files) to use as join keys (order matters).")
    ap.add_argument("--case-insensitive", action="store_true", help="Case-insensitive for text comparison.")
    ap.add_argument("--output", default="excel_diff_report_detailed.xlsx", help="Output Excel filename.")
    args = ap.parse_args()

    # 讀左檔 & 指定工作表
    left_sheets = pd.read_excel(args.left_file, sheet_name=None)
    if args.left_sheet not in left_sheets:
        raise SystemExit(f"[Error] 左檔沒有工作表：{args.left_sheet}")
    dfL = left_sheets[args.left_sheet]

    # 讀右檔 & 工作表
    right_sheets = pd.read_excel(args.right_file, sheet_name=None)
    if args.right_sheet:
        if args.right_sheet not in right_sheets:
            raise SystemExit(f"[Error] 右檔沒有工作表：{args.right_sheet}")
        rs_name = args.right_sheet
    else:
        rs_name = next(iter(right_sheets))  # 第一張
    dfR = right_sheets[rs_name]

    # 正規化
    L = normalize_df(dfL, case_insensitive=args.case_insensitive)
    R = normalize_df(dfR, case_insensitive=args.case_insensitive)

    # 決定 keys
    if args.keys:
        keysL = []
        keysR = []
        # 使用者指定的 keys 必須同時存在於兩邊
        for k in args.keys:
            if k not in L.columns or k not in R.columns:
                raise SystemExit(f"[Error] 指定的 key 欄位 `{k}` 不同時存在於兩檔。")
            keysL.append(k); keysR.append(k)
    else:
        keysL, keysR = pick_keys(L, R)
        if not keysL:
            print("[Warn] 自動找不到合適的 key，將僅產生 ONLY_IN_LEFT / ONLY_IN_RIGHT，不做 COLUMN_DIFF。")
            keysL, keysR = [], []

    # 產出差異
    if keysL:
        onlyL, onlyR, col_diff = compare_with_keys(L, R, keysL, keysR)
    else:
        # 沒 key：只做集合差異
        cols = sorted(set(L.columns) | set(R.columns))
        for c in cols:
            if c not in L.columns: L[c] = ""
            if c not in R.columns: R[c] = ""
        L = L[cols]; R = R[cols]
        sigL = L.apply(lambda row: tuple(row.tolist()), axis=1)
        sigR = R.apply(lambda row: tuple(row.tolist()), axis=1)
        onlyL = L[~sigL.isin(sigR)]
        onlyR = R[~sigR.isin(sigL)]
        col_diff = pd.DataFrame(columns=["key", "column", "left_value", "right_value"])

    # 寫報告
    with pd.ExcelWriter(args.output, engine="openpyxl") as w:
        # Summary
        summary = pd.DataFrame([{
            "left_file": args.left_file,
            "left_sheet": args.left_sheet,
            "right_file": args.right_file,
            "right_sheet": rs_name,
            "keys_used": ", ".join(keysL) if keysL else "(無)",
            "same": bool(onlyL.empty and onlyR.empty and (col_diff is None or col_diff.empty)),
            "only_in_left_rows": int(len(onlyL)),
            "only_in_right_rows": int(len(onlyR)),
            "column_diff_rows": int(0 if (col_diff is None or col_diff.empty) else len(col_diff)),
        }])
        summary.to_excel(w, index=False, sheet_name="SUMMARY")
        onlyL.to_excel(w, index=False, sheet_name="ONLY_IN_LEFT")
        onlyR.to_excel(w, index=False, sheet_name="ONLY_IN_RIGHT")
        if col_diff is not None and not col_diff.empty:
            col_diff.to_excel(w, index=False, sheet_name="COLUMN_DIFF")

    print(f"已輸出：{args.output}")
    if not keysL:
        print("ℹ建議改用 --keys 指定主鍵欄位，才能得到 COLUMN_DIFF 欄位級報表。")

if __name__ == "__main__":
    main()
