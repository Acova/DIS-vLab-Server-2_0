from app.api.utils import *
from app.models import models
from app.core import app, logger

# ======================================================================================================================
# ==========> SETTINGS METHODS <========================================================================================
# ======================================================================================================================

@app.route('api/settings', methods=['POST'])
@token_required
def get_settings(cu):
    logger.info("Obteniendo parámetros")
    try:
        parameters = models.Config.get()
        return json_response(parameters)
    except Exception as e:
        logger.error('Error obteniendo la configuración: %s', e)
        return json_response(status=500)
