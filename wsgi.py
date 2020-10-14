import subprocess
import eventlet
eventlet.monkey_patch()

from app.core import app as application
from app.core import socketio

if __name__ == '__main__':
    subprocess.Popen(['venv/bin/celery',
                    '--app=app.core.celery',
                    'worker',
                    '-f', '/var/log/dvls-worker.log',
                    '-l', 'DEBUG', '-E'])
    socketio.run(application, debug=True)
