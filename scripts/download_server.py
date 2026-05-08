"""
ダッシュボードからダウンロードスクリプトを起動するローカルサーバー
"""

import subprocess
import sys
import threading
import os
import json
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8765
SCRIPTS_DIR = Path(__file__).parent

# イベントリスト方式（全SSE接続が同じイベントを受け取れる）
_events: list = []
_events_cond = threading.Condition()
_process = None
_running = False


def _emit(item: dict):
    """イベントをリストに追加し、全SSE接続に通知する"""
    with _events_cond:
        _events.append(item)
        _events_cond.notify_all()


def run_download(params: dict):
    global _process, _running
    _running = True
    with _events_cond:
        _events.clear()

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

    _emit({"type": "log", "text": f"実行: {' '.join(cmd)}"})

    try:
        _process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(SCRIPTS_DIR.parent)
        )
        for line in _process.stdout:
            _emit({"type": "log", "text": line.rstrip()})
        _process.wait()
        code = _process.returncode
        _emit({"type": "done", "code": code,
               "text": "✓ 完了" if code == 0 else f"✗ エラー (code={code})"})
    except Exception as e:
        _emit({"type": "error", "text": str(e)})
    finally:
        _running = False
        _process = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

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
        if self.path in ("/login", "/download"):
            if _running:
                self._json({"error": "既に実行中です"}, 409)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            params = json.loads(body) if body else {}
            if self.path == "/login":
                params["login_only"] = True
            t = threading.Thread(target=run_download, args=(params,), daemon=True)
            t.start()
            self._json({"status": "started"})
        elif self.path == "/stop":
            if _process:
                _process.terminate()
                _emit({"type": "done", "code": -1, "text": "⏹ 停止しました"})
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

        pos = 0
        deadline = time.time() + 300
        while time.time() < deadline:
            item = None
            with _events_cond:
                if pos < len(_events):
                    item = _events[pos]
                    pos += 1
                else:
                    _events_cond.wait(timeout=0.5)

            try:
                if item is not None:
                    data = json.dumps(item, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode())
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
            except OSError:
                break

            if item is not None and item.get("type") in ("done", "error"):
                break


if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    print(f"ダウンロードサーバー起動完了")
    print(f"  ブラウザで開く: http://localhost:{PORT}")
    print(f"停止: Ctrl+C\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました")
