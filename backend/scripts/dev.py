"""Start all three independent applications from the backend virtual environment."""
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

backend=Path(__file__).resolve().parents[1]
root=backend.parent
processes=[]

def stop(*_):
    for process in processes:
        if process.poll() is None: process.terminate()
    for process in processes:
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()

if __name__=='__main__':
    # A global `python scripts/dev.py` should still use installed project
    # dependencies instead of silently starting a different API environment.
    venv=backend/'.venv'
    runtime=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if runtime.exists() and Path(sys.prefix).resolve()!=venv.resolve():
        sys.exit(subprocess.call([str(runtime),str(Path(__file__).resolve()),*sys.argv[1:]]))
    for port in (8000,5173,5174):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:
                sys.exit(f'Port {port} is already in use. Stop the existing service or run the applications individually.')
    for folder in ('frontend','admin'):
        if not (root/folder/'node_modules'/'vite'/'bin'/'vite.js').exists():
            sys.exit(f'Run npm ci in {folder} before starting the workspace.')
    signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGTERM,stop)
    try:
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--no-access-log'],cwd=backend))
        for folder,port in (('frontend',5173),('admin',5174)):
            processes.append(subprocess.Popen(['node',str(root/folder/'node_modules'/'vite'/'bin'/'vite.js'),'--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=root/folder))
        print('\nCustomer app: http://127.0.0.1:5173\nAdministration: http://127.0.0.1:5174\nAPI: http://127.0.0.1:8000\nPress Ctrl+C to stop all three.\n',flush=True)
        while all(process.poll() is None for process in processes): time.sleep(.5)
    finally: stop()
