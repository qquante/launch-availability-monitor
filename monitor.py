from __future__ import annotations
import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from twice_monitor.core import Store, Detector, utc, BASE
from twice_monitor.service import Poller, Renderer, serve_dashboard, sound_worker, status_snapshot

ROOT = Path(__file__).resolve().parent

def run(args):
    runtime = Path(args.runtime).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    lock = open(runtime/"monitor.lock","a+b")
    if lock.tell() == 0:
        lock.write(b"0");lock.flush()
    lock.seek(0)
    if os.name == "nt":
        import msvcrt
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            raise SystemExit("O monitor já está ativo nesta pasta.")
    else:
        import fcntl
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stop = threading.Event()
    for signum in (signal.SIGINT,signal.SIGTERM):
        signal.signal(signum,lambda *unused:stop.set())
    logging.basicConfig(level=logging.INFO,format="%(asctime)sZ %(levelname)s %(message)s",
        handlers=[RotatingFileHandler(runtime/"monitor.log",maxBytes=2_000_000,backupCount=3,encoding="utf-8")])
    logging.Formatter.converter = time.gmtime
    store = Store(runtime/"monitor.sqlite3")
    detector = Detector(store,ROOT/"research"/"2026-09-13-twice-fun")
    poller = Poller(store,detector,stop)
    renderer = Renderer(store,detector,poller,stop)
    server = serve_dashboard(store,poller,ROOT,"127.0.0.1",args.port,stop)
    (runtime/"stop.request").unlink(missing_ok=True)
    pid_data={"pid":os.getpid(),"root":str(ROOT),"started_at":utc(),"url":f"http://127.0.0.1:{args.port}"}
    (runtime/"process.json").write_text(json.dumps(pid_data),encoding="utf-8")
    for url in (BASE+"/api/deployment",BASE+"/api/config",BASE+"/"):
        poller.add(url)
    renderer_thread=threading.Thread(target=renderer.worker,daemon=True,name="browser")
    renderer_thread.start()
    audio_thread=threading.Thread(target=sound_worker,args=(store,stop,args.no_sound),daemon=True,name="audio")
    audio_thread.start()
    logging.info("Monitor iniciado %s",pid_data)
    print(json.dumps({"started":True,**pid_data}),flush=True)
    try:
        while not stop.is_set():
            if (runtime/"stop.request").exists():
                break
            store.set("heartbeat",{**pid_data,"at":utc(),"running":True})
            snapshot=status_snapshot(store,poller)
            temporary=runtime/"status.tmp"
            temporary.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding="utf-8")
            temporary.replace(runtime/"status.json")
            stop.wait(1)
    finally:
        stop.set()
        server.shutdown()
        renderer_thread.join(timeout=15)
        audio_thread.join(timeout=10)
        for worker in list(poller.workers.values()):
            worker.join(timeout=0.2)
        store.set("heartbeat",{**pid_data,"at":utc(),"running":False})
        (runtime/"status.json").write_text(json.dumps(status_snapshot(store,poller),ensure_ascii=False,indent=2),encoding="utf-8")
        # Daemon workers may still be unwinding timed-out sockets; process exit closes DB.
        lock.close()
        logging.info("Monitor encerrado")

def main():
    parser=argparse.ArgumentParser(description="twice.fun — monitor local de leitura, 1 segundo.")
    parser.add_argument("command",choices=["run","status","stop","test-beep","pending","ack"])
    parser.add_argument("--runtime",default=str(ROOT/"runtime"))
    parser.add_argument("--port",type=int,default=8888)
    parser.add_argument("--no-sound",action="store_true",help="Som desativado só nesta execução (testes).")
    parser.add_argument("--ids",nargs="*",type=int,default=[])
    parser.add_argument("--channel",choices=["chat","sound","acknowledged"],default="chat")
    args=parser.parse_args()
    runtime=Path(args.runtime)
    if args.command=="run":
        return run(args)
    if args.command=="stop":
        runtime.mkdir(parents=True,exist_ok=True)
        (runtime/"stop.request").write_text(utc(),encoding="utf-8")
        print("Parada solicitada.")
        return
    if not (runtime/"monitor.sqlite3").exists():
        raise SystemExit("Estado do monitor ainda não existe.")
    store=Store(runtime/"monitor.sqlite3")
    if args.command=="status":
        print(json.dumps(status_snapshot(store),ensure_ascii=False,indent=2))
    elif args.command=="test-beep":
        event=store.emit("test","TESTE DO ALARME — NÃO É LANÇAMENTO","local",
                        {"count":8,"frequency_hz":888,"duration_ms":888})
        print(json.dumps({"test_event_id":event}))
    elif args.command=="pending":
        print(json.dumps(store.events(pending=args.channel if args.channel!="acknowledged" else None),ensure_ascii=False))
    elif args.command=="ack":
        store.ack(args.ids,args.channel)
        print(json.dumps({"acknowledged_ids":args.ids,"channel":args.channel}))
    store.close()

if __name__=="__main__":
    main()
