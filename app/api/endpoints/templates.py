import subprocess
import paramiko
import libvirt
import pickle
from app.api.utils import *
from app.api.tasks import templates
from app.models import *
from app.core import app, logger


# ======================================================================================================================
# ==========> TEMPLATE METHODS <========================================================================================
# ======================================================================================================================

# (C) Create a template from domain
@app.route('/api/templates', methods=['POST'])
@token_required
def create_template(cu):
    logger.info('Creando plantilla')
    task = templates.create_template.delay(data=request.json)
    return json_response(data=task.task_id)


# (R) Get all templates
@app.route('/api/templates', methods=['GET'])
@token_required
def get_templates(cu):
    logger.info('Obteniendo plantillas')
    try:
        templates = Template.get()
        data = [t.to_dict() for t in templates]
        return json_response(data=data)
    except Exception as e:
        logger.error('No se pudo obtener las plantillas: %s', str(e))
        return json_response(status=500)


# (D) Delete a template
@app.route('/api/templates/<template_uuid>', methods=['DELETE'])
@token_required
def delete_template(cu, template_uuid):
    logger.info('Eliminando plantilla')
    try:
        template = Template.get(template_uuid)
        for image_path in pickle.loads(template.images_path):
            subprocess.check_call(['rm', '-f', image_path])
        subprocess.check_call(['rm', '-f', template.xml_path])
        Template.delete(template)
        return json_response()
    except Exception as e:
        logger.error('No se pudo eliminar la plantilla: %s', str(e))
        return json_response(status=500)


# Clone template into domain, in other words, it generates a new domain from a template
@app.route('/api/templates/<template_uuid>', methods=['POST'])
@token_required
def clone_template(cu, template_uuid):
    logger.info('Desplegando plantilla')
    try:
        template = Template.get(template_uuid).to_dict()
        domain_name = request.json['domain_name']
        lab_uuid = request.json['lab_uuid']

        lab = Lab.get(lab_uuid)
        hosts = lab.hosts

        if hosts.__len__() == 0:
            logger.error('El laboratorio no tiene ningún host asociado')
            return json_response(status=500)

        cmd = ['virt-clone',
               '--connect', app.config['LOCAL_QEMU_URI'],
               '--original-xml', template['xml_path'],
               '--name', domain_name]

        for count in range(template['images_path'].__len__()):
            cmd.append('--file')
            cmd.append(app.config['DOMAIN_IMAGES_DIR'] + domain_name + '-disk' + str(count) + '.qcow2')

        ssh = paramiko.SSHClient()
        # Surrounds 'known_hosts' error
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        errors = list()
        for h in hosts:
            host = h.ip_address
            username = h.conn_user
            try:
                # NO PASSWORD!! Server SSH key is previously distributed among lab PCs
                ssh.connect(hostname=host.compressed, username=username, timeout=4)
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(' '.join(cmd))
                errors = [b.rstrip() for b in ssh_stderr.readlines()]
                if len(errors) > 0:
                    logger.error('No se pudo desplegar la plantilla en el host %s (%s)', h.code, h.ip_address.compressed)
                    logger.error(e for e in errors)
            except Exception as e:
                logger.error('No se pudo desplegar la plantilla en el host %s (%s): %s', h.code, h.ip_address.compressed, str(e))
                errors = True
            finally:
                ssh.close()
        if errors or len(errors) > 0:
            return json_response(status=500)
        return json_response()
    except Exception as e:
        logger.error('No se pudo desplegar la plantilla: %s', str(e))
        return json_response(status=500)
