"""
各モールダウンローダーの基底クラス
セッション管理・ログイン確認の共通処理
"""

import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SESSION_BASE = Path(__file__).parent.parent / "sessions"

class BaseDownloader:
    channel_id: str       # 'amazon' | 'yahoo' | 'rakuten' | 'own_ec'
    channel_name: str     # 表示名
    login_url: str        # ログインページURL
    check_url: str        # セッション確認用URL（要認証ページ）
    check_success: str    # ログイン成功を示すURLパターン

    def __init__(self):
        self.session_dir = str(SESSION_BASE / self.channel_id)
        Path(self.session_dir).mkdir(parents=True, exist_ok=True)
        self._context: BrowserContext = None

    async def _launch(self, headless: bool = True):
        p = await async_playwright().start()
        self._pw = p
        self._context = await p.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
            ignore_default_args=["--enable-automation"],
        )
        return self._context

    async def close(self):
        if self._context:
            await self._context.close()
        if hasattr(self, '_pw'):
            await self._pw.stop()

    async def check_session(self) -> bool:
        """セッションが有効かチェック。True=ログイン済み"""
        try:
            ctx = await self._launch(headless=True)
            page = await ctx.new_page()
            await page.goto(self.check_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(3_000)
            is_logged_in = self.check_success in page.url
            await self.close()
            return is_logged_in
        except Exception:
            await self.close()
            return False

    async def do_login(self):
        """ブラウザを開いてユーザーにログインを促す"""
        ctx = await self._launch(headless=False)
        page = await ctx.new_page()
        await page.goto(self.login_url, wait_until="domcontentloaded", timeout=30_000)
        print(f"  [{self.channel_name}] ブラウザでログインしてください")
        print(f"  ログイン完了後 Enter を押してください...", end="", flush=True)
        await asyncio.get_event_loop().run_in_executor(None, input)
        # セッションを保存して閉じる
        await self._context.close()
        await self._pw.stop()
        self._context = None

    async def download(self, start_date: str, end_date: str, out_dir: str) -> list[str]:
        """
        データをダウンロードして保存されたファイルパスのリストを返す
        サブクラスでオーバーライドする
        """
        raise NotImplementedError
