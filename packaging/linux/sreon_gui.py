#!/usr/bin/python3
"""Small cross-platform browser-host for Sreon's generated internal pages.

It starts the bundled SPRFST engine and opens the Sreon UI in the user's
installed web browser. External URLs are handed off to the default browser.
"""
import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RES = Path('/usr/share/sreon')
BIN = Path('/usr/lib/sreon/bin/sprfst')
ENGINE = None
ENGINE_LOCK = threading.Lock()


def start_engine():
    env = os.environ.copy()
    env['SREON_RES'] = str(RES)
    env['SPRFST_HOME'] = str(RES)
    proc = subprocess.Popen(
        [str(BIN), 'run', str(RES / 'engine/main.spf'), '--', '--serve'],
        cwd=str(RES), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, bufsize=1)
    hello = proc.stdout.readline()
    if not hello:
        raise RuntimeError('Sreon engine failed to start')
    return proc


def engine_request(obj):
    global ENGINE
    with ENGINE_LOCK:
        if ENGINE is None or ENGINE.poll() is not None:
            ENGINE = start_engine()
        ENGINE.stdin.write(json.dumps(obj, separators=(',', ':')) + '\n')
        ENGINE.stdin.flush()
        line = ENGINE.stdout.readline()
        if not line:
            raise RuntimeError('Sreon engine stopped unexpectedly')
        return json.loads(line)


class Handler(BaseHTTPRequestHandler):
    server_version = 'SreonUI/1.1'

    def log_message(self, *_):
        pass

    def send_body(self, status, content_type, body):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/page/sreon%3A%2F%2Fnewtab')
            self.end_headers()
            return
        if path.startswith('/assets/'):
            name = path[len('/assets/'):]
            if '/' in name or '..' in name:
                self.send_error(404)
                return
            result = engine_request({'op': 'page', 'url': 'sreon://assets/' + name})
            mime = result.get('mime', 'text/plain; charset=utf-8')
            text = result.get('body', '')
            if name == 'sreon.js':
                text = text.replace(
                    'var native = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.sreon;',
                    'var native = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.sreon;')
                text = text.replace(
                    'var tauriHost = window.sreonHost || (window.parent !== window ? window.parent.sreonHost : null);',
                    'var tauriHost = window.sreonHost || (window.parent !== window ? window.parent.sreonHost : null);')
                text = text.replace(
                    'if (tauriHost && typeof tauriHost.call === "function") return tauriHost.call(op, VIEW, data || {});',
                    'return fetch("/api", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({op:op,view:VIEW,data:data||{}})}).then(function(r){return r.json()}).then(function(r){(r.host||[]).forEach(function(a){if(a.do==="open"&&a.url){if(a.url.indexOf("sreon://")===0||a.url.indexOf("about:")===0) location.href="/page/"+encodeURIComponent(a.url); else window.open(a.url,"_blank","noopener")}});return r});')
            self.send_body(200 if result.get('status', 200) < 400 else result.get('status', 404), mime, text)
            return
        if path.startswith('/page/'):
            page_url = urllib.parse.unquote(path[len('/page/'):])
            result = engine_request({'op': 'page', 'url': page_url})
            html = result.get('body', '')
            html = html.replace('sreon://assets/', '/assets/')
            self.send_body(result.get('status', 200), 'text/html; charset=utf-8', html)
            return
        self.send_error(404)

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != '/api':
            self.send_error(404)
            return
        try:
            length = min(int(self.headers.get('Content-Length', '0')), 2_000_000)
            request = json.loads(self.rfile.read(length))
            result = engine_request(request)
            self.send_body(200, 'application/json; charset=utf-8', json.dumps(result))
        except Exception as exc:
            self.send_body(500, 'application/json; charset=utf-8', json.dumps({'ok': False, 'error': str(exc)}))


def main():
    global ENGINE
    ENGINE = start_engine()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    url = 'http://127.0.0.1:%d/' % server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Launch in an app-style window when Chromium is available, otherwise use
    # the user's normal browser. Never assume a particular browser is installed.
    chromium = next((shutil.which(c) for c in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable') if shutil.which(c)), None)
    if chromium:
        subprocess.Popen([chromium, '--app=' + url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif not webbrowser.open(url, new=1):
        raise RuntimeError('No desktop browser was found. Install Chromium or set a default browser.')
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        if ENGINE and ENGINE.poll() is None:
            ENGINE.terminate()


if __name__ == '__main__':
    main()
