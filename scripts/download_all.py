"""
全チャネル一括ダウンロード → マージ → Firestoreインポート

使い方:
  python download_all.py                      # 昨日1日分
  python download_all.py --days 7             # 過去7日分
  python download_all.py --start 2026-04-01 --end 2026-04-30

オプション:
  --days N            過去N日分（デフォルト: 1）
  --start YYYY-MM-DD  開始日
  --end   YYYY-MM-DD  終了日
  --skip-download     ダウンロードをスキップ（マージ・インポートのみ）
  --skip-import       Firestoreインポートをスキップ
  --channels          対象チャネル（例: rakuten yahoo）デフォルト: 全て
"""

import asyncio
import argparse
import subprocess
import sys
import os
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from user_config import DOWNLOAD_DIRS, AMAZON_MAPPING_FILE, SHOPIFY_MAPPING_FILE
except ImportError:
    print("[エラー] scripts/user_config.py が見つかりません。")
    print("  scripts/user_config.example.py を user_config.py にコピーして設定してください。")
    sys.exit(1)

# マージスクリプトと引数
MERGE_COMMANDS = {
    "amazon": lambda dirs: [
        sys.executable, str(SCRIPTS_DIR / "amazon_merge.py"),
        "--folder", dirs["amazon"],
        "--mapping", AMAZON_MAPPING_FILE,
        "--year", str(date.today().year),
        "--out", str(Path(dirs["amazon"]) / "amazon_merged.csv"),
    ],
    "yahoo": lambda dirs: [
        sys.executable, str(SCRIPTS_DIR / "yahoo_merge.py"),
        "--folder", dirs["yahoo"],
        "--out", str(Path(dirs["yahoo"]) / "yahoo_merged.csv"),
    ],
    "rakuten": lambda dirs: [
        sys.executable, str(SCRIPTS_DIR / "rakuten_merge.py"),
        "--folder", dirs["rakuten"],
        "--out", str(Path(dirs["rakuten"]) / "rakuten_merged.csv"),
    ],
    "own_ec": lambda dirs: [
        sys.executable, str(SCRIPTS_DIR / "own_ec_merge.py"),
        "--folder", dirs["own_ec"],
        "--mapping", SHOPIFY_MAPPING_FILE,
        "--out", str(Path(dirs["own_ec"]) / "own_ec_merged.csv"),
    ],
}

MERGED_FILES = {
    "amazon":  lambda dirs: str(Path(dirs["amazon"])  / "amazon_merged.csv"),
    "yahoo":   lambda dirs: str(Path(dirs["yahoo"])   / "yahoo_merged.csv"),
    "rakuten": lambda dirs: str(Path(dirs["rakuten"]) / "rakuten_merged.csv"),
    "own_ec":  lambda dirs: str(Path(dirs["own_ec"])  / "own_ec_merged.csv"),
}


async def check_and_login(downloaders: dict):
    """全チャネルのセッションを確認し、必要なものをまとめてログインさせる"""
    print("=" * 50)
    print("セッション確認中...")
    print("=" * 50)

    needs_login = []
    for ch, dl in downloaders.items():
        print(f"  [{dl.channel_name}] 確認中...", end=" ", flush=True)
        ok = await dl.check_session()
        print("✓ ログイン済み" if ok else "⚠ ログインが必要")
        if not ok:
            needs_login.append(dl)

    if not needs_login:
        print("\n全チャネル ログイン済みです。\n")
        return

    print(f"\n以下のモールへのログインが必要です:")
    for dl in needs_login:
        print(f"  ・{dl.channel_name}")
    print()

    for dl in needs_login:
        print(f"[{dl.channel_name}] ブラウザを開きます...")
        await dl.do_login()
        print(f"[{dl.channel_name}] ログイン完了\n")


async def download_phase(downloaders: dict, start_date: str, end_date: str):
    """全チャネルのデータをダウンロード"""
    print("=" * 50)
    print(f"ダウンロード開始: {start_date} 〜 {end_date}")
    print("=" * 50)

    for ch, dl in downloaders.items():
        print(f"\n[{dl.channel_name}]")
        out_dir = DOWNLOAD_DIRS[ch]
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        await dl.download(start_date, end_date, out_dir)


def merge_phase(channels: list):
    """マージスクリプトを実行"""
    print("\n" + "=" * 50)
    print("マージ処理")
    print("=" * 50)

    for ch in channels:
        print(f"\n[{ch}] マージ中...")
        cmd = MERGE_COMMANDS[ch](DOWNLOAD_DIRS)
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.stdout:
            print(result.stdout.strip())
        if result.returncode != 0:
            print(f"  [エラー] {result.stderr[:200]}")


def import_phase(channels: list):
    """Firestoreへインポート"""
    print("\n" + "=" * 50)
    print("Firestoreインポート")
    print("=" * 50)

    csv_args = []
    for ch in channels:
        path = MERGED_FILES[ch](DOWNLOAD_DIRS)
        if Path(path).exists():
            csv_args += ["--csv", path]
        else:
            print(f"  [スキップ] {ch}: {path} が見つかりません")

    if not csv_args:
        print("  インポートするファイルがありません")
        return

    cmd = [sys.executable, str(SCRIPTS_DIR / "firestore_import.py")] + csv_args
    result = subprocess.run(cmd, capture_output=False, text=True, encoding="utf-8", errors="replace")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",  type=int, default=1)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end",   default=None)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-import",   action="store_true")
    parser.add_argument("--channels", nargs="+",
                        default=["amazon", "yahoo", "rakuten", "own_ec"],
                        choices=["amazon", "yahoo", "rakuten", "own_ec"])
    args = parser.parse_args()

    # 日付範囲を決定
    if args.start and args.end:
        start_date, end_date = args.start, args.end
    else:
        end_dt   = date.today() - timedelta(days=1)
        start_dt = end_dt - timedelta(days=args.days - 1)
        start_date, end_date = start_dt.isoformat(), end_dt.isoformat()

    print(f"\nYogibo EC ダウンロードパイプライン")
    print(f"対象チャネル: {', '.join(args.channels)}")
    print(f"期間: {start_date} 〜 {end_date}\n")

    # ダウンローダーを初期化
    from downloaders import AmazonDownloader, YahooDownloader, RakutenDownloader, OwnEcDownloader
    all_downloaders = {
        "amazon":  AmazonDownloader(),
        "yahoo":   YahooDownloader(),
        "rakuten": RakutenDownloader(),
        "own_ec":  OwnEcDownloader(),
    }
    downloaders = {ch: all_downloaders[ch] for ch in args.channels}

    # ① セッション確認 + ログイン
    if not args.skip_download:
        await check_and_login(downloaders)

        # ② ダウンロード
        await download_phase(downloaders, start_date, end_date)

    # ③ マージ
    merge_phase(args.channels)

    # ④ Firestoreインポート
    if not args.skip_import:
        import_phase(args.channels)

    print("\n✓ 全処理完了")


if __name__ == "__main__":
    asyncio.run(main())
