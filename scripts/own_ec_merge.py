"""
GA4 eコマース購入数CSVをShopifyマッピングで変換してダッシュボード用CSVに出力するスクリプト

使い方:
  python own_ec_merge.py --folder "C:/Users/d.nakamura/Downloads/SPF" --mapping "C:/Users/d.nakamura/Downloads/Book2.csv"

オプション:
  --folder   GA4日別CSVのフォルダ
  --mapping  ShopifyのCSVファイル（Handle=代表コード, Title=商品名）
  --out      出力ファイルパス（省略時: フォルダ内に own_ec_merged.csv を作成）

ファイル名ルール:
  e_コマース購入数_イベント名_YYMMDD.csv（リネーム不要）
  例: e_コマース購入数_イベント名_260421.csv → 2026-04-21
"""

import csv
import glob
import os
import re
import argparse
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADER_ROW = 9  # 0始まり: 10行目がヘッダー

COLUMN_MAP = {
    'アイテム名':       'item_name',
    'セッション':       'UU',
    'アイテムの購入数':  '注文件数',
    'アイテムの収益':   '売上金額',
}

def load_shopify_mapping(path):
    """Shopify CSV から アイテム名(Title) → 代表コード(Handle) の辞書を作成
    Title が空の行はそのHandleで先に登録されたTitleを使用"""
    with open(path, encoding='shift-jis', errors='replace') as f:
        rows = list(csv.DictReader(f))

    # 1pass: Handle → Title を確定
    handle_to_title = {}
    for r in rows:
        if r['Title'].strip() and r['Handle'] not in handle_to_title:
            handle_to_title[r['Handle']] = r['Title'].strip()

    # 2pass: Title（空欄はHandleから補完） → Handle
    title_to_handle = {}
    for r in rows:
        title = r['Title'].strip() or handle_to_title.get(r['Handle'], '')
        handle = r['Handle'].strip()
        if title and handle:
            title_to_handle[title] = handle

    print(f'  マッピング: {len(title_to_handle)}件（Handle補完込み）')
    return title_to_handle

def resolve_sku(name, mapping):
    """アイテム名を代表コードに変換。色名付きバリアントは名前部分のみで再試行"""
    if not name or name == '(not set)':
        return None
    code = mapping.get(name)
    if code:
        return code
    # " - 色名" を除いて再試行
    base = re.sub(r'\s*-\s*.+$', '', name).strip()
    return mapping.get(base)

def extract_date(filename):
    """ファイル名から日付を抽出: e_コマース購入数_イベント名_260421.csv → 2026-04-21"""
    m = re.search(r'_(\d{2})(\d{2})(\d{2})\.csv$', filename)
    if not m:
        return None
    yy, mm, dd = m.group(1), m.group(2), m.group(3)
    return f'20{yy}-{mm}-{dd}'

def clean_number(val):
    return str(int(float(re.sub(r'[^\d.]', '', val) or '0')))

def process_files(folder, out_path, mapping):
    pattern = os.path.join(folder, 'e_*.csv')
    files = sorted(glob.glob(pattern))
    files = [f for f in files if os.path.basename(f) != os.path.basename(out_path)]

    if not files:
        print(f'CSVファイルが見つかりません: {folder}')
        return 0

    rows_out = []
    unmatched_all = set()

    for fpath in files:
        fname = os.path.basename(fpath)
        data_date = extract_date(fname)
        if not data_date:
            print(f'  スキップ（日付を抽出できません）: {fname}')
            continue

        with open(fpath, encoding='utf-8-sig') as f:
            raw = list(csv.reader(f))

        if len(raw) <= HEADER_ROW:
            continue

        headers = raw[HEADER_ROW]
        aggregated = {}

        for row in raw[HEADER_ROW + 1:]:
            if not row or not row[0]:
                continue
            rec = dict(zip(headers, row))
            name = rec.get('アイテム名', '').strip()
            sku = resolve_sku(name, mapping)
            if not sku:
                if name and name != '(not set)':
                    unmatched_all.add(name)
                continue

            key = (data_date, 'own', sku)
            uu  = int(float(rec.get('セッション', '0') or '0'))
            ord_ = int(float(rec.get('アイテムの購入数', '0') or '0'))
            rev  = int(float(re.sub(r'[^\d.]', '', rec.get('アイテムの収益', '0') or '0')))

            if key not in aggregated:
                aggregated[key] = {'date': data_date, 'channel': 'own', 'SKU': sku,
                                   '商品名': name, 'UU': uu, '注文件数': ord_,
                                   '販売数量': ord_, '売上金額': rev}
            else:
                aggregated[key]['UU']      += uu
                aggregated[key]['注文件数'] += ord_
                aggregated[key]['販売数量'] += ord_
                aggregated[key]['売上金額'] += rev

        rows_out.extend(aggregated.values())
        print(f'  {fname} → {data_date} ({len(aggregated)}件)')

    if unmatched_all:
        warn_path = os.path.join(os.path.dirname(out_path), 'own_ec_unmatched.txt')
        with open(warn_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(unmatched_all)))
        print(f'\n[警告] 未マッチ: {len(unmatched_all)}件 → {warn_path}')

    if not rows_out:
        print('変換できる行がありませんでした')
        return 0

    # 数値を文字列に戻してCSV出力
    fieldnames = ['date', 'channel', 'SKU', '商品名', 'UU', '注文件数', '販売数量', '売上金額']
    for r in rows_out:
        for col in ('UU', '注文件数', '販売数量', '売上金額'):
            r[col] = str(r[col])

    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    return len(rows_out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder',  required=True)
    parser.add_argument('--mapping', required=True)
    parser.add_argument('--out',     default=None)
    args = parser.parse_args()

    out_path = args.out or os.path.join(args.folder, 'own_ec_merged.csv')
    print(f'Shopifyマッピング読み込み: {args.mapping}')
    mapping = load_shopify_mapping(args.mapping)
    print(f'  {len(mapping)}件\n')

    print(f'処理開始: {args.folder}\n')
    count = process_files(args.folder, out_path, mapping)
    if count:
        print(f'\n完了: {count}行 → {out_path}')

if __name__ == '__main__':
    main()
