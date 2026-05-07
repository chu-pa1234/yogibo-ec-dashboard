"""
ダッシュボードからダウンロードスクリプトを起動するローカルサーバー

起動方法:
  python scripts/download_server.py

起動後はブラウザから http://localhost:8765 でアクセス可能
ダッシュボードの「ダウンロード」ボタンがこのサーバーを呼び出します
"""

import subprocess
import sys
import threading
import os
import json
import queue
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import date, timedelta
from pathlib import Path

PORT = 8765
SCRIPTS_DIR = Path(__file__).parent

# 実行中のプロセスとログキュー
_process = None
_log_queue = queue.Queue()
_running   = False


def run_download(params: dict):
    global _process, _running
    _running = True
    _log_queue.put({"type": "start", "params": params})

    cmd = [sys.executable, str(SCRIPTS_DIR / "download_all.py")]
    if params.get("start") and params.get("end"):
        cmd += ["--start", params["start"], "--end", params["end"]]
    elif params.get("days"):
        cmd += ["--days", str(params["days"])]
    if params.get("channels"):
        cmd += ["--channels"] + params["channels"]
    if params.get("login_only"):
        cmd += ["--login-only"]
    if params.get("skip_download"):
        cmd += ["--skip-download"]
    if params.get("skip_import"):
        cmd += ["--skip-import"]

    _log_queue.put({"type": "log", "text": f"実行: {' '.join(cmd)}"})

    try:
        _process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(SCRIPTS_DIR.parent)
        )
        for line in _process.stdout:
            _log_queue.put({"type": "log", "text": line.rstrip()})
        _process.wait()
        code = _process.returncode
        _log_queue.put({"type": "done", "code": code,
                        "text": "✓ 完了" if code == 0 else f"✗ エラー (code={code})"})
    except Exception as e:
        _log_queue.put({"type": "error", "text": str(e)})
    finally:
        _running = False
        _process = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # アクセスログを抑制

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._json({"running": _running, "pid": os.getpid()})
        elif self.path == "/logs":
            self._sse()
        elif self.path in ("/", "/index.html"):
            # ローカルのindex.htmlを配信（HTTPSブロック回避）
            html_path = Path(__file__).parent.parent / "index.html"
            if html_path.exists():
                content = html_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/login":
            if _running:
                self._json({"error": "既に実行中です"}, 409)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            params = json.loads(body) if body else {}
            params["login_only"] = True
            t = threading.Thread(target=run_download, args=(params,), daemon=True)
            t.start()
            self._json({"status": "started"})
        elif self.path == "/download":
            if _running:
                self._json({"error": "既に実行中です"}, 409)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            params = json.loads(body) if body else {}
            t = threading.Thread(target=run_download, args=(params,), daemon=True)
            t.start()
            self._json({"status": "started"})
        elif self.path == "/stop":
            if _process:
                _process.terminate()
                self._json({"status": "stopped"})
            else:
                self._json({"status": "not running"})
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        # キューを5秒間ポーリング
        import time
        end = time.time() + 300
        while time.time() < end:
            try:
                item = _log_queue.get(timeout=0.5)
                data = json.dumps(item, ensure_ascii=False)
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    print(f"ダウンロードサーバー起動完了")
    print(f"  ブラウザで開く: http://localhost:{PORT}")
    print(f"  （ダッシュボードが開きます）")
    print(f"停止: Ctrl+C\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました")
