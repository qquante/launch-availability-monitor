"""Persistent detection and alerts. All timestamps are UTC; no chain writes."""
from __future__ import annotations
import hashlib
import html
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://twice.fun"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ADDRESS = re.compile(r"(?<![A-Za-z0-9_])(?:0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})(?![A-Za-z0-9_])")
INFRA = {"0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e", "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"}

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def addresses(text):
    text = html.unescape(text)
    result = {}
    for match in ADDRESS.finditer(text):
        value = match.group()
        if value.startswith("0x"):
            chain, key = "EVM", value.lower()
        else:
            number = 0
            for c in value:
                number = number * 58 + B58.index(c)
            size = (number.bit_length() + 7) // 8 + len(value) - len(value.lstrip("1"))
            if size != 32:
                continue
            chain, key = "SOL", value
        result[key] = {"address": value, "chain": chain,
                       "context": text[max(0, match.start()-100):match.end()+100]}
    return result

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=10000;
            CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS seen(key TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,kind TEXT NOT NULL,
              title TEXT NOT NULL,source TEXT NOT NULL,details TEXT NOT NULL,
              acknowledged_at TEXT,sound_at TEXT,chat_at TEXT);
        """)
        self.db.commit()

    def get(self, key, default=None):
        with self.lock:
            row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO state VALUES(?,?)",
                            (key, json.dumps(value, ensure_ascii=False)))

    def mark(self, key):
        with self.lock, self.db:
            return self.db.execute("INSERT OR IGNORE INTO seen VALUES(?)", (key,)).rowcount > 0

    def emit(self, kind, title, source, details, unique=None):
        with self.lock, self.db:
            if unique and not self.db.execute("INSERT OR IGNORE INTO seen VALUES(?)", (unique,)).rowcount:
                return None
            return self.db.execute(
                "INSERT INTO events(at,kind,title,source,details) VALUES(?,?,?,?,?)",
                (utc(), kind, title, source, json.dumps(details, ensure_ascii=False))).lastrowid

    def events(self, limit=150, pending=None):
        clauses = {"sound": "sound_at IS NULL", "chat": "chat_at IS NULL"}
        where = " WHERE " + clauses[pending] if pending else ""
        with self.lock:
            rows = self.db.execute("SELECT * FROM events"+where+" ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(row), "details": json.loads(row["details"])} for row in rows]

    def ack(self, ids, channel="acknowledged"):
        column = {"acknowledged": "acknowledged_at", "sound": "sound_at", "chat": "chat_at"}[channel]
        with self.lock, self.db:
            self.db.executemany("UPDATE events SET "+column+"=? WHERE id=?", [(utc(), int(i)) for i in ids])

    def source(self, url, info):
        self.set("source:"+url, info)

    def sources(self):
        with self.lock:
            return {r["key"][7:]: json.loads(r["value"]) for r in self.db.execute(
                "SELECT * FROM state WHERE key LIKE 'source:%'")}

    def close(self):
        self.db.close()

class Detector:
    def __init__(self, store, baseline=None):
        self.store = store
        self.lock = threading.RLock()
        if not store.get("baseline_initialized"):
            # The previous real inspection is the baseline, never the first new live data.
            keys = set(INFRA)
            if baseline and Path(baseline).exists():
                for path in Path(baseline).iterdir():
                    if path.suffix in (".js", ".html", ".json") and path.name != "manifest.json":
                        keys.update(addresses(path.read_text(encoding="utf-8")))
            for key in keys:
                store.mark("address:"+key)
            store.set("baseline_initialized", {"at": utc(), "addresses": len(keys)})

    def deployment(self, payload):
        if not isinstance(payload, dict) or type(payload.get("enabled")) is not bool:
            raise ValueError("Resposta deployment sem enabled booleano")
        with self.lock:
            old = self.store.get("deployment")
            if payload["enabled"] is True and (old is None or old["enabled"] is not True):
                # Every observed OFF -> ON transition is distinct, including across restarts.
                self.store.emit("enabled", "ENABLED LIGOU", BASE+"/api/deployment",
                                {"previous": old, "current": payload})
            self.store.set("deployment", {**payload, "observed_at": utc()})

    def scan_text(self, text, source, role="public"):
        revision = digest(text)
        with self.lock:
            if self.store.get("hash:"+source) == revision:
                return
            for key, found in addresses(text).items():
                self.store.emit("address", "NOVO ENDEREÇO "+found["chain"], source,
                    {**found, "classification": "candidato publicado; não validado on-chain",
                     "role": role}, unique="address:"+key)
            self.store.set("hash:"+source, revision)

    def scan_json(self, payload, source):
        self.scan_text(json.dumps(payload, ensure_ascii=False), source, "json")
        def walk(value, trail=""):
            if isinstance(value, dict):
                name = value.get("name")
                symbol = value.get("symbol") or value.get("ticker")
                if isinstance(name, str) and isinstance(symbol, str) and (
                    re.search(r"tokens|launches|markets|items|results", trail, re.I)
                    or any(k in value for k in ("mint","tokenAddress","contractAddress","legs"))
                ):
                    ident = value.get("id") or name.casefold()+":"+symbol.casefold()
                    self.token(str(ident), name, symbol, source, {"json_path": trail})
                for key, item in value.items():
                    walk(item, trail+"."+str(key))
            elif isinstance(value, list):
                for i, item in enumerate(value[:2000]):
                    walk(item, trail+"["+str(i)+"]")
        walk(payload)

    def token(self, ident, name, symbol, source, details):
        return self.store.emit("token", "TOKEN NA LISTA: "+name, source,
            {"id": ident, "name": name, "symbol": symbol, **details}, unique="token:"+ident)

    def board(self, board_html, count_text, filter_name):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(board_html, "html.parser")
        for tag in soup(["script","style"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        source = BASE+"/#explore["+filter_name+"]"
        self.scan_text(board_html, source, "rendered_board")
        rows = soup.select(".launch-row,.token-card,[data-token-id],[data-launch-id]")
        tokens = []
        for row in rows:
            heading = row.select_one("h3,h2,h4,[data-token-name]")
            name = heading.get_text(" ", strip=True) if heading else "Token"
            id_el = row.select_one("[data-market],[data-token-id],[data-launch-id]")
            ident = row.get("data-token-id") or row.get("data-launch-id")
            if not ident and id_el:
                ident = id_el.get("data-market") or id_el.get("data-token-id") or id_el.get("data-launch-id")
            ticker_el = row.select_one(".row-meta span,[data-symbol],.ticker")
            symbol = ticker_el.get_text(" ", strip=True).lstrip("$") if ticker_el else ""
            ident = ident or name.casefold()+":"+symbol.casefold()
            detail = {"filter": filter_name, "text": row.get_text(" ",strip=True)[:1600],
                      "addresses": list(addresses(str(row)).values())}
            self.token(str(ident), name, symbol, source, detail)
            tokens.append({"id": str(ident), "name": name, "symbol": symbol, **detail})
        number = re.search(r"(\d+)\s+tokens?\s+listed", count_text, re.I)
        count = int(number.group(1)) if number else len(tokens)
        empty = bool(soup.select_one(".empty-state")) and bool(re.search(
            r"no tokens|no saved|no matching", text, re.I))
        if not tokens and ((count > 0) or (text and not empty)):
            # A changed future card structure still raises an alert; no silent loss.
            self.store.emit("listing", "CONTEÚDO NOVO NO EXPLORE", source,
                {"filter": filter_name, "count": count, "text": text[:2000]},
                unique="listing:"+digest(text))
        return {"filter":filter_name,"count":count,"text":text[:2000],"tokens":tokens,"at":utc()}

def beep_sequence(beep, sleep):
    for i in range(8):
        beep(888, 888)
        if i < 7:
            sleep(0.12)
