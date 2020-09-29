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
    task = templates.clone_template.delay(template_uuid=template_uuid, data=request.json)
    return json_response(data=task.task_id)
