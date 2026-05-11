"""GA4 自社EC ダウンローダー"""

import os
from datetime import datetime, timedelta
from .base import BaseDownloader


class OwnEcDownloader(BaseDownloader):
    channel_id   = "own_ec"
    channel_name = "自社EC(GA4)"
    login_url    = "https://accounts.google.com/"
    check_url    = "https://analytics.google.com/analytics/web/"
    check_success = "analytics.google.com/analytics/web"

    PROP = "a56611866p251080271"

    def __init__(self):
        super().__init__()
        try:
            from user_config import OWN_EC_SESSION_DIR
            if OWN_EC_SESSION_DIR:
                self.session_dir = OWN_EC_SESSION_DIR
        except (ImportError, AttributeError):
            pass

    async def download(self, start_date: str, end_date: str, out_dir: str) -> list[str]:
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date,   "%Y-%m-%d").date()

        ctx = await self._launch(headless=False)  # GA4はheadlessで動作しないことがある
        page = await ctx.new_page()
        saved = []

        d = s
        while d <= e:
            ymd = d.strftime("%Y年%m月%d日")
            print(f"  [GA4] {ymd} をダウンロード中...")

            try:
                yy = str(d.year)[2:]
                mm = str(d.month).zfill(2)
                dd = str(d.day).zfill(2)

                # eコマース購入レポートへ遷移
                base = f"https://analytics.google.com/analytics/web/#{self.PROP}/reports/home"
                await page.goto(base, wait_until="domcontentloaded", timeout=40_000)
                await page.wait_for_timeout(5_000)

                # 収益化 → eコマースの購入
                for text in ["収益化", "Monetization"]:
                    try:
                        await page.get_by_text(text, exact=True).first.click(timeout=5_000)
                        await page.wait_for_timeout(2_000)
                        break
                    except Exception:
                        continue

                for text in ["eコマースの購入", "Ecommerce purchases"]:
                    try:
                        await page.get_by_text(text, exact=False).first.click(timeout=5_000)
                        await page.wait_for_timeout(3_000)
                        break
                    except Exception:
                        continue

                # 日付を設定
                await self._set_date(page, d.isoformat(), d.isoformat())

                # エクスポート
                out_name = f"e_コマース購入数_イベント名_{yy}{mm}{dd}.csv"
                out_path = os.path.join(out_dir, out_name)
                async with page.expect_download(timeout=30_000) as dl_info:
                    # ダウンロードアイコン（共有ボタン → CSVをダウンロード）
                    await page.get_by_title("このレポートを共有").click(timeout=10_000)
                    await page.wait_for_timeout(1_000)
                    await page.get_by_text("CSVをダウンロード").click(timeout=10_000)
                dl = await dl_info.value
                await dl.save_as(out_path)
                saved.append(out_path)
                print(f"    → 保存: {os.path.basename(out_path)}")

            except Exception as ex:
                print(f"    [警告] {ymd} 失敗: {ex}")

            d += timedelta(days=1)

        await self.close()
        return saved

    async def _set_date(self, page, start: str, end: str):
        from datetime import datetime as dt
        s = dt.strptime(start, "%Y-%m-%d").strftime("%Y/%m/%d")
        e = dt.strptime(end,   "%Y-%m-%d").strftime("%Y/%m/%d")
        try:
            await page.locator("ga-date-range-selector").first.click(timeout=10_000)
            await page.wait_for_timeout(2_000)
            overlay = page.locator(".cdk-overlay-container")
            inputs  = overlay.locator("input[matInput], input[mat-input]")
            await inputs.nth(0).fill(s)
            await page.keyboard.press("Tab")
            await inputs.nth(1).fill(e)
            await page.keyboard.press("Tab")
            for name in ["適用", "Apply"]:
                try:
                    await overlay.get_by_role("button", name=name).click(timeout=3_000)
                    break
                except Exception:
                    continue
            await page.wait_for_timeout(4_000)
        except Exception as ex:
            print(f"    [警告] 日付設定失敗: {ex}")
