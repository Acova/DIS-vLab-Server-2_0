import eventlet
eventlet.monkey_patch()

from app.core import app as application
from app.core import socketio

if __name__ == '__main__':
    socketio.run(application, debug=True)
