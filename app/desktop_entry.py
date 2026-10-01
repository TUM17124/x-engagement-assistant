"""Packaged backend entry: localhost only, bundled Python, one workspace process."""
import argparse
import os
import sys
from pathlib import Path
import uvicorn

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8787)
    args=parser.parse_args()
    from app.paths import data_dir
    directory=data_dir()
    directory.mkdir(parents=True,exist_ok=True)
    lock=open(directory/"runtime.lock","a+b")
    lock.seek(0)
    if not lock.read(1):
        lock.write(b"0");lock.flush()
    lock.seek(0)
    try:
        if sys.platform=="win32":
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except (OSError,IOError):
        print("Another workspace backend is already running.",flush=True) if sys.stdout else None
        raise SystemExit(1)
    from app.main import app
    from app import desktop_control
    server=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=args.port,log_level="warning",access_log=False,log_config=None))
    desktop_control.shutdown_handler=lambda:setattr(server,"should_exit",True)
    try:
        server.run()
    finally:
        lock.close()

if __name__=="__main__":
    main()
