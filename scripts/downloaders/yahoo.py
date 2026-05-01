"""Yahoo! ストアクリエイターPro ダウンローダー"""

import os
from datetime import datetime, timedelta
from .base import BaseDownloader


class YahooDownloader(BaseDownloader):
    channel_id   = "yahoo"
    channel_name = "Yahoo!"
    login_url    = "https://pro.store.yahoo.co.jp/pro.yogibo-store/sales_manage/item_report"
    check_url    = "https://pro.store.yahoo.co.jp/pro.yogibo-store/sales_manage/item_report"
    check_success = "pro.store.yahoo.co.jp/pro.yogibo-store"

    async def download(self, start_date: str, end_date: str, out_dir: str) -> list[str]:
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date,   "%Y-%m-%d").date()

        ctx = await self._launch(headless=True)
        page = await ctx.new_page()
        saved = []

        d = s
        while d <= e:
            ymd = d.strftime("%Y年%m月%d日")
            print(f"  [Yahoo!] {ymd} をダウンロード中...")

            try:
                await page.goto(self.check_url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(2_000)

                # 日付を入力
                await page.fill("input[name='startDate']", d.strftime("%Y/%m/%d"))
                await page.fill("input[name='endDate']",   d.strftime("%Y/%m/%d"))
                await page.get_by_role("button", name="検索").click()
                await page.wait_for_timeout(3_000)

                # CSVダウンロード
                yymmdd = d.strftime("%y%m%d")
                out_path = os.path.join(out_dir, f"yogibo-store-item_report_{yymmdd}.csv")
                async with page.expect_download(timeout=30_000) as dl_info:
                    await page.get_by_role("link", name="CSVダウンロード").first.click()
                dl = await dl_info.value
                await dl.save_as(out_path)
                saved.append(out_path)
                print(f"    → 保存: {os.path.basename(out_path)}")

            except Exception as ex:
                print(f"    [警告] {ymd} 失敗: {ex}")

            d += timedelta(days=1)

        await self.close()
        return saved
