from __future__ import annotations
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import requests
from .core import BASE, utc, digest, beep_sequence

LOG = logging.getLogger("twice")
MAX_BYTES = 2_000_000
FORBIDDEN = ("/api/admin", "/api/auth", "/api/test-launch", "/api/pool-intents")
ALERT_KINDS = {"enabled","address","token","listing","header","test"}

def public_url(url):
    part = urlsplit(url)
    return part.scheme == "https" and part.netloc == "twice.fun" and not part.username and not part.path.startswith(FORBIDDEN)

def retry_delay(headers, failures):
    delay = min(60, 2 ** min(failures, 6))
    value = headers.get("Retry-After", "")
    if value:
        try:
            delay = max(delay, float(value))
        except ValueError:
            try:
                delay = max(delay, (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError):
                pass
    return max(1, delay)

class Poller:
    def __init__(self, store, detector, stop):
        self.store, self.detector, self.stop = store, detector, stop
        self.lock = threading.RLock()
        self.cache, self.workers = {}, {}
        self.total_requests = 0

    def add(self, url):
        url = urljoin(BASE+"/", url)
        if not public_url(url):
            return
        with self.lock:
            if url in self.workers or len(self.workers) >= 20:
                return
            thread = threading.Thread(target=self.worker, args=(url,), daemon=True, name="poll:"+url)
            self.workers[url] = thread
            thread.start()

    def cached(self, url):
        with self.lock:
            return self.cache.get(url)

    def worker(self, url):
        session = requests.Session()
        session.headers.update({"User-Agent":"TwiceFunLocalMonitor/1.0", "Accept":"*/*",
                                "Cache-Control":"no-cache"})
        meta = {}
        failures, requests_count = 0, 0
        info = self.store.get("source:"+url, {})
        while not self.stop.is_set():
            started = time.monotonic()
            delay, response = 1.0, None
            requests_count += 1
            with self.lock:
                self.total_requests += 1
            info.update({"last_attempt":utc(),"requests_this_run":requests_count,"interval_target_ms":1000})
            try:
                response = session.get(url, headers=meta, timeout=(3,5), stream=True, allow_redirects=False)
                if response.status_code == 304:
                    if not self.cached(url):
                        raise ValueError("304 recebido sem conteúdo local")
                    with self.lock:
                        self.cache[url] = {**self.cache[url], "fetched_mono":time.monotonic()}
                else:
                    response.raise_for_status()
                    if response.status_code != 200:
                        raise ValueError("Resposta HTTP inesperada: "+str(response.status_code))
                    body = bytearray()
                    for chunk in response.iter_content(65536):
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise ValueError("Resposta ultrapassou limite de 2 MB")
                    text = bytes(body).decode("utf-8", errors="replace")
                    content_type = response.headers.get("Content-Type","text/plain")
                    if urlsplit(url).path.startswith("/api/"):
                        payload = json.loads(text)
                        if urlsplit(url).path == "/api/deployment":
                            self.detector.deployment(payload)
                        self.detector.scan_json(payload, url)
                    else:
                        self.detector.scan_text(text, url, "script" if ".js" in url else "html")
                    self.accept(url, text, content_type)
                    meta = {}
                    if response.headers.get("ETag"):
                        meta["If-None-Match"] = response.headers["ETag"]
                    if response.headers.get("Last-Modified"):
                        meta["If-Modified-Since"] = response.headers["Last-Modified"]
                failures = 0
                info.update({"ok":True,"status":response.status_code,"last_success":utc(),
                             "error":None,"failures":0})
            except Exception as exc:
                failures += 1
                delay = retry_delay(response.headers if response is not None else {}, failures)
                info.update({"ok":False,"error":str(exc)[:400],"failures":failures,
                             "status":response.status_code if response is not None else None})
                if failures == 3:
                    self.store.emit("monitor_error","FONTE TEMPORARIAMENTE INDISPONÍVEL",url,
                                    {"error":str(exc)[:500]})
                LOG.warning("%s: %s", url, exc)
            finally:
                if response is not None:
                    response.close()
            info["latency_ms"] = round((time.monotonic()-started)*1000)
            info["next_delay_seconds"] = delay
            self.store.source(url, dict(info))
            self.stop.wait(max(0, delay-(time.monotonic()-started)))
        session.close()

    def accept(self, url, text, content_type):
        revision = digest(text)
        with self.lock:
            old = self.cache.get(url)
            self.cache[url] = {"text":text,"content_type":content_type,"hash":revision,
                               "fetched_mono":time.monotonic()}
        if url.rstrip("/") == BASE and (not old or old["hash"] != revision):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, "html.parser")
            for tag in soup.find_all("script", src=True):
                self.add(tag["src"])

class Renderer:
    def __init__(self, store, detector, poller, stop):
        self.store, self.detector, self.poller, self.stop = store, detector, poller, stop
        self.browser = None
        self.page = None
        self.responses = []
        self.blocked = set()

    def route(self, route):
        request = route.request
        if request.method not in ("GET","HEAD","OPTIONS"):
            self.blocked.add(request.method+" "+request.url)
            return route.abort()
        if request.resource_type in ("image","media","font") or urlsplit(request.url).path == "/scene.js":
            return route.abort()
        if not public_url(request.url):
            return route.abort()
        cached = self.poller.cached(request.url)
        if cached and time.monotonic()-cached["fetched_mono"] <= 3:
            return route.fulfill(status=200, content_type=cached["content_type"], body=cached["text"])
        route.continue_()

    def response(self, response):
        # Discovery comes only from actual anonymous GETs made by the public page.
        if response.request.method == "GET" and public_url(response.url) and response.status == 200:
            if urlsplit(response.url).path.startswith("/api/"):
                self.poller.add(response.url)

    def scan(self):
        self.page.goto(BASE+"/", wait_until="domcontentloaded", timeout=12000)
        self.page.locator("#markets").wait_for(timeout=5000)
        self.page.wait_for_timeout(150)
        snapshots = {}
        for value in ("all","new","saved"):
            control = self.page.locator('[data-filter="'+value+'"]')
            if not control.count():
                raise ValueError("Filtro "+value+" desapareceu: estrutura pública mudou")
            control.click(timeout=2000)
            self.page.wait_for_timeout(70)
            snapshots[value] = self.detector.board(
                self.page.locator("#markets").inner_html(),
                self.page.locator("#market-count").inner_text(), value)
        self.page.locator('[data-filter="all"]').click(timeout=2000)
        header_el = self.page.locator(".hero-copy .eyebrow")
        if header_el.count():
            header = header_el.inner_text().strip()
            previous = self.store.get("site_header", "NO CA LIVE YET")
            if header != previous and header.upper() != "NO CA LIVE YET":
                self.store.emit("header","AVISO PRINCIPAL DO SITE MUDOU",BASE+"/",
                    {"previous":previous,"current":header}, unique="header:"+digest(header))
            self.store.set("site_header",header)
        self.detector.scan_text(self.page.content(),BASE+"/#rendered","rendered_page")
        self.store.set("boards", snapshots)
        return snapshots

    def worker(self):
        from playwright.sync_api import sync_playwright
        failures, scans = 0, 0
        info = self.store.get("renderer", {})
        with sync_playwright() as playwright:
            while not self.stop.is_set():
                started = time.monotonic()
                try:
                    if self.browser is None:
                        self.browser = playwright.chromium.launch(channel="msedge",headless=True)
                        self.context = self.browser.new_context(service_workers="block")
                        self.context.route("**/*",self.route)
                        self.page = self.context.new_page()
                        self.page.on("response",self.response)
                    scans += 1
                    self.scan()
                    failures = 0
                    info.update({"ok":True,"last_success":utc(),"error":None})
                except Exception as exc:
                    failures += 1
                    info.update({"ok":False,"error":str(exc)[:400]})
                    LOG.warning("Renderização: %s",exc)
                    if failures == 3:
                        self.store.emit("monitor_error","LEITURA DO EXPLORE COM FALHA",BASE+"/#explore",
                                        {"error":str(exc)[:500]})
                    if self.browser:
                        try:
                            self.browser.close()
                        except Exception:
                            pass
                    self.browser = self.page = None
                info.update({"last_attempt":utc(),"scans":scans,"failures":failures,
                             "latency_ms":round((time.monotonic()-started)*1000),
                             "interval_target_ms":1000,"blocked_writes":sorted(self.blocked)})
                self.store.set("renderer",dict(info))
                self.stop.wait(max(0, (1 if not failures else min(30,2**failures))-(time.monotonic()-started)))
            if self.browser:
                self.browser.close()

def sound_worker(store, stop, disabled=False):
    while not stop.is_set():
        try:
            pending = store.events(limit=10000, pending="sound")
            silent = [e["id"] for e in pending if e["kind"] not in ALERT_KINDS]
            if silent:
                store.ack(silent,"sound")
            audible = [e for e in pending if e["kind"] in ALERT_KINDS]
            if audible and not disabled and not store.get("sound_muted",False):
                ids = [e["id"] for e in audible]
                store.set("sound",{"status":"playing","at":utc(),"event_ids":ids,
                                   "count":8,"frequency_hz":888,"duration_ms":888})
                import winsound
                beep_sequence(winsound.Beep,time.sleep)
                store.ack(ids,"sound")
                store.set("sound",{"status":"completed","at":utc(),"event_ids":ids,
                                   "count":8,"frequency_hz":888,"duration_ms":888})
        except Exception as exc:
            store.set("sound",{"status":"failed","at":utc(),"error":str(exc)})
            LOG.exception("Falha no som")
            stop.wait(15)
        stop.wait(0.2)

def status_snapshot(store, poller=None):
    return {"heartbeat":store.get("heartbeat"),"deployment":store.get("deployment"),
            "boards":store.get("boards",{}),"renderer":store.get("renderer",{}),
            "sources":store.sources(),"sound":store.get("sound",{}),
            "sound_muted":store.get("sound_muted",False),"interval_seconds":1,
            "requests_this_run":poller.total_requests if poller else None,
            "server_time":utc()}

def serve_dashboard(store, poller, root, host, port, stop):
    token = secrets.token_urlsafe(24)
    template = (root/"dashboard.html").read_text(encoding="utf-8")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, value, status=200, mime="application/json; charset=utf-8"):
            body = value.encode("utf-8") if isinstance(value,str) else json.dumps(value,ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host","") in (f"127.0.0.1:{port}", f"localhost:{port}")

        def do_GET(self):
            if not self.valid_host():
                return self.send({"error":"Host inválido"},403)
            path = urlsplit(self.path).path
            if path == "/":
                self.send(template.replace("__CSRF__",token),mime="text/html; charset=utf-8")
            elif path == "/api/status":
                self.send(status_snapshot(store,poller))
            elif path == "/api/events":
                self.send(store.events())
            else:
                self.send({"error":"Não encontrado"},404)

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self.valid_host() or self.headers.get("X-Monitor-Token") != token or (
                origin and origin not in (f"http://127.0.0.1:{port}",f"http://localhost:{port}")):
                return self.send({"error":"Solicitação local inválida"},403)
            length = int(self.headers.get("Content-Length","0"))
            if length > 8192:
                return self.send({"error":"Payload grande"},413)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/test-beep":
                    store.emit("test","TESTE DO ALARME — NÃO É LANÇAMENTO","local",
                               {"count":8,"frequency_hz":888,"duration_ms":888})
                elif self.path == "/api/ack":
                    store.ack(data.get("ids",[]))
                elif self.path == "/api/mute":
                    store.set("sound_muted",data.get("muted") is True)
                else:
                    return self.send({"error":"Não encontrado"},404)
                self.send({"ok":True})
            except (ValueError,TypeError) as exc:
                self.send({"error":str(exc)},400)
    server = ThreadingHTTPServer((host,port),Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever,daemon=True,name="dashboard").start()
    return server
