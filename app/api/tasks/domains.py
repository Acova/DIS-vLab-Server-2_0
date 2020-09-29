import subprocess
from flask_socketio import SocketIO

from app.core import celery, logger, app


@celery.task(bind=True)
def create_domain(self, data):
    cmd = ['virt-install',
           '--connect', app.config['LOCAL_QEMU_URI'],
           '--name', data['name'],
           '--memory', str(data['memory']),
           '--vcpus', str(data['vcpus']),
           '--os-variant', data['os_variant'],
           '--noautoconsole']
    if data['graphics']['vnc']:
        cmd.append('--graphics')
        cmd.append('vnc,listen='+data['graphics']['listen']+',password='+data['graphics']['password'])
    if data['installation_type'] == "iso":
        cmd.append('--disk')
        cmd.append('size='+str(data['disk']['size']))
        cmd.append('--cdrom')
        cmd.append(data['cdrom'])
    elif data['installation_type'] == "image":
        cmd.append('--disk')
        cmd.append(data['disk']['path'])
        cmd.append('--import')
    elif data['installation_type'] == "network":
        cmd.append('--disk')
        cmd.append('size='+str(data['disk']['size']))
        cmd.append('--location')
        cmd.append(data['location'])
    elif data['installation_type'] == "pxe":
        cmd.append('--disk')
        cmd.append('size='+str(data['disk']['size']))
        cmd.append('--network')
        cmd.append(data['network'])
        cmd.append('--pxe')
    else:
        logger.warn('El método de instalación no es correcto')
        socketio = SocketIO(message_queue=app.config['CELERY_BROKER_URL'])
        socketio.emit('task-finished', {'task_type': 'add-domain', 'task_id': self.request.id.__str__(), 'status': -1})
        return -1
    try:
        subprocess.check_call(cmd)
        logger.info('Dominio creado')
        socketio = SocketIO(message_queue=app.config['CELERY_BROKER_URL'])
        socketio.emit('task-finished', {'task_type': 'add-domain', 'task_id': self.request.id.__str__(), 'status': 0})
        return 0
    except Exception as e:
        logger.error('No se ha podido crear el dominio: %s', str(e))
        socketio = SocketIO(message_queue=app.config['CELERY_BROKER_URL'])
        socketio.emit('task-finished', {'task_type': 'add-domain', 'task_id': self.request.id.__str__(), 'status': -1})
        return -1
