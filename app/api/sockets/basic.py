from app.core import socketio, logger

from flask_socketio import emit


@socketio.on('connect')
def socketio_connect():
    logger.debug('Iniciada una conexión de WebSockets')


@socketio.on('disconnect')
def socketio_disconnect():
    logger.debug('Acabada una conexión de WebSockets')
