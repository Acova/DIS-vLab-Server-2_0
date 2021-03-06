from app.api.utils import *
from app.core import app, logger
import subprocess
import time

startedWebsockify = False
websockifyPid = 0


@app.route('/api/novnc', methods=['PUT'])
@token_required
def startWebsockify(cu):
    logger.info('Iniciando conexión de WebSockify')
    global startedWebsockify
    global websockifyPid
    port = request.json['port']
    conn_str = 'localhost:' + str(port)
    if (startedWebsockify):
        kill_process(websockifyPid)
        startedWebsockify = False

    proc = subprocess.Popen(['./app/api/tools/websockify/run',
                             'localhost:6080',
                             conn_str,
                             '--cert',
                             '/etc/nginx/ssl/nginx.crt',
                             '--key',
                             '/etc/nginx/ssl/nginx.key'])
    websockifyPid = proc.pid
    time.sleep(2)
    startedWebsockify = True
    return json_response(data=proc.pid)


@app.route('/api/novnc', methods=['POST'])
@token_required
def stopWebsockify(cu):
    logger.info('Acabando la conexión de WebSockify')
    pid = request.json['pid']
    kill_process(pid)
    global startedWebsockify
    startedWebsockify = False
    return json_response()
