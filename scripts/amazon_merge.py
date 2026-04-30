"""
Amazon セラーセントラル 日別CSVを結合してダッシュボード用CSVに変換するスクリプト

使い方:
  python amazon_merge.py --folder "C:/Users/d.nakamura/Downloads/AMZ" --mapping "C:/Users/d.nakamura/Downloads/Amazon代表コードと親ASIN突合せ表.xlsx"

オプション:
  --folder   CSVファイルが入っているフォルダのパス
  --mapping  ASIN→代表コード変換用Excelファイルのパス（省略時: ASINをそのまま使用）
  --out      出力ファイルパス（省略時: フォルダ内に amazon_merged.csv を作成）
"""

import csv
import glob
import os
import re
import argparse

COLUMN_MAP = {
    "（親）ASIN":         "SKU",
    "タイトル":            "商品名",
    "セッション数 - 合計": "UU",
    "注文品目総数":         "注文件数",
    "注文商品の売上額":     "売上金額",
    "注文された商品点数":   "販売数量",
}

MAPPING_SHEET = "すべての出品商品のレポート_04-28-2026"

def load_asin_mapping(xlsx_path):
    """Excelから 子ASIN → 代表コード の辞書を作成する"""
    try:
        import openpyxl
    except ImportError:
        print("[警告] openpyxl が未インストールのため --mapping は無視されます（pip install openpyxl）")
        return {}

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[MAPPING_SHEET]
    mapping = {}
    unmapped = []

    for row in ws.iter_rows(min_row=3, values_only=True):
        asin = row[1]
        code = row[3]
        if not asin:
            continue
        if code and str(code) not in ("#N/A", "None"):
            mapping[asin] = str(code)
        else:
            unmapped.append(asin)

    print(f"  マッピング読み込み: {len(mapping)}件 有効 / {len(unmapped)}件 未マッピング（ASINをそのまま使用）")
    if unmapped:
        print(f"  未マッピングASINの一覧は unmapped_asins.txt に出力します")
    return mapping, unmapped

def clean_number(val):
    return re.sub(r"[￥¥,%\s]", "", val)

def extract_date(filename):
    """ファイル名から日付を抽出: BusinessReport-26-04-30.csv → 2026-04-30"""
    m = re.search(r"-(\d{2})-(\d{2})-(\d{2})\.csv$", filename)
    if not m:
        return None
    yy, month, day = m.group(1), m.group(2), m.group(3)
    return f"20{yy}-{month}-{day}"

def process_files(folder, out_path, asin_map):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    files = [f for f in files if os.path.basename(f) != os.path.basename(out_path)]

    if not files:
        print(f"CSVファイルが見つかりません: {folder}")
        return 0

    rows_out = []
    unmapped_in_data = set()

    for fpath in files:
        fname = os.path.basename(fpath)
        data_date = extract_date(fname)
        if not data_date:
            print(f"  スキップ（日付を抽出できません）: {fname}")
            continue
        print(f"  {fname} → {data_date}")

        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                out = {"date": data_date, "channel": "amazon"}
                for src_col, dst_col in COLUMN_MAP.items():
                    val = row.get(src_col, "").strip()
                    if dst_col in ("UU", "注文件数", "販売数量", "売上金額"):
                        val = clean_number(val)
                    out[dst_col] = val

                # ASINを代表コードに変換（マッピングなしはスキップ）
                if asin_map:
                    asin = out["SKU"]
                    if asin in asin_map:
                        out["SKU"] = asin_map[asin]
                    else:
                        unmapped_in_data.add(asin)
                        continue

                rows_out.append(out)

    if not rows_out:
        print("変換できる行がありませんでした")
        return 0

    fieldnames = ["date", "channel", "SKU", "商品名", "UU", "注文件数", "販売数量", "売上金額"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    if unmapped_in_data:
        warn_path = os.path.join(os.path.dirname(out_path), "unmapped_asins.txt")
        with open(warn_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(unmapped_in_data)))
        print(f"\n[警告] データ内の未マッピングASIN: {len(unmapped_in_data)}件 → {warn_path}")

    return len(rows_out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder",  required=True)
    parser.add_argument("--mapping", default=None)
    parser.add_argument("--out",     default=None)
    args = parser.parse_args()

    out_path = args.out or os.path.join(args.folder, "amazon_merged.csv")
    print(f"処理開始: {args.folder}\n")

    asin_map = {}
    unmapped = []
    if args.mapping:
        print(f"マッピングファイル読み込み: {args.mapping}")
        asin_map, unmapped = load_asin_mapping(args.mapping)
        if unmapped:
            warn_path = os.path.join(args.folder, "unmapped_asins.txt")
            with open(warn_path, "w", encoding="utf-8") as f:
                f.write("\n".join(unmapped))
        print()

    count = process_files(args.folder, out_path, asin_map)
    if count:
        print(f"\n完了: {count}行 → {out_path}")

if __name__ == "__main__":
    main()
