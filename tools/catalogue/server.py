"""Loopback-only listening and review interface; originals are never changed."""
import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import subprocess
import threading
from urllib.parse import urlparse

from .core import CREATE_NO_WINDOW, connect, records, native_path


def serve(root, port=8765):
    token = secrets.token_urlsafe(32)
    log_lock = threading.Lock()
    preview_lock = threading.Lock()
    previews = root / '_catalogue' / 'previews'
    previews.mkdir(exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def json_response(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def file_response(self, path, content_type):
            size = path.stat().st_size
            start, end = 0, size - 1
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                if not match or not any(match.groups()):
                    self.send_error(416)
                    return
                if match[1]:
                    start = int(match[1])
                    end = min(int(match[2]), end) if match[2] else end
                else:
                    start = max(0, size-int(match[2]))
                if start > end or start >= size:
                    self.send_error(416)
                    return
            self.send_response(206 if requested else 200)
            self.send_header('Content-Type', content_type)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end-start+1))
            if requested:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as f:
                f.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def do_GET(self):
            route = urlparse(self.path).path
            try:
                if route == '/':
                    page = Path(__file__).with_name('browser.html').read_text(encoding='utf-8').replace('__TOKEN__', token)
                    body = page.encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    self.wfile.write(body)
                elif route in {'/browser_logic.js', '/browser_app.js'}:
                    self.file_response(Path(__file__).with_name(route[1:]), 'text/javascript; charset=utf-8')
                elif route == '/api/records':
                    self.json_response(records(root))
                elif route == '/api/ucs':
                    self.json_response([dict(r) for r in connect(root).execute('SELECT * FROM ucs ORDER BY category,subcategory')])
                elif route == '/api/summary':
                    self.json_response(json.loads((root/'_catalogue'/'summary.json').read_text(encoding='utf-8')))
                elif route == '/catalogue.csv':
                    self.file_response(root/'_catalogue'/'catalogue.csv', 'text/csv; charset=utf-8')
                elif route.startswith('/audio/'):
                    ident = route.rsplit('/',1)[-1]
                    if not re.fullmatch('[a-f0-9]{24}', ident):
                        self.send_error(404)
                        return
                    row = next((r for r in records(root) if r['id'] == ident), None)
                    if not row:
                        self.send_error(404)
                        return
                    original = native_path(root/row['path']).resolve()
                    original.relative_to(native_path(root).resolve())
                    stat = original.stat()
                    if stat.st_size != row['size'] or stat.st_mtime_ns != row['mtime_ns']:
                        self.json_response({'error':'Source changed since inventory; rescan before playing'},409)
                        return
                    # Browsers cannot play all legacy WAV/AIFF codecs. Cache a full,
                    # untrimmed PCM preview on demand, without normalization.
                    key = row['sha256'] or hashlib.sha256(row['path'].encode()).hexdigest()
                    preview = previews/(key+'.wav')
                    with preview_lock:
                        if not preview.exists():
                            temp = preview.with_suffix('.tmp.wav')
                            p = subprocess.run(['ffmpeg','-v','error','-y','-i',str(original),'-map','0:a:0','-c:a','pcm_s16le','-ar','44100',str(temp)],capture_output=True,timeout=180,creationflags=CREATE_NO_WINDOW)
                            if p.returncode:
                                self.json_response({'error':'Could not decode preview'},422)
                                return
                            temp.replace(preview)
                    self.file_response(preview,'audio/wav')
                else:
                    self.send_error(404)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as exc:
                self.json_response({'error':str(exc)},500)

        def do_POST(self):
            if self.path != '/api/review':
                self.send_error(404)
                return
            if self.headers.get('X-Catalogue-Token') != token:
                self.send_error(403)
                return
            origin = self.headers.get('Origin')
            if origin and origin not in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}:
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 8192:
                    raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(length))
                ident, catid = data['id'], data.get('catid') or None
                if not any(r['id'] == ident for r in records(root)):
                    raise ValueError('Unknown recording description')
                if catid and not connect(root).execute('SELECT 1 FROM ucs WHERE catid=?',(catid,)).fetchone():
                    raise ValueError('Unknown UCS category')
                event = dict(id=secrets.token_hex(12),description_id=ident,catid=catid,time=datetime.datetime.now(datetime.timezone.utc).isoformat(),action='label',reviewer='local-user')
                with log_lock:
                    with (root/'_catalogue'/'overrides.jsonl').open('a',encoding='utf-8') as f:
                        f.write(json.dumps(event,ensure_ascii=False)+'\n')
                        f.flush()
                self.json_response(event)
            except (ValueError,KeyError) as exc:
                self.json_response({'error':str(exc)},400)

    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Catalogue browser: http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
