from app.api.utils import *
from app.core import app, logger
import subprocess
import signal
import time


@app.route('/api/novnc', methods=['PUT'])
@token_required
def startWebsockify(cu):
    logger.info('Iniciando conexión de WebSockify')
    port = request.json['port']
    conn_str = 'localhost:' + str(port)
    proc = subprocess.Popen(['./app/api/tools/websockify/run', 'localhost:6080', conn_str])
    time.sleep(2)
    return json_response(data=proc.pid)


@app.route('/api/novnc', methods=['POST'])
@token_required
def stopWebsockify(cu):
    logger.info('Acabando la conexión de WebSockify')
    pid = request.json['pid']
    subprocess.run(['kill', '-s', '9', str(pid)])
    return json_response()
