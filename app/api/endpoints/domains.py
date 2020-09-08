from app.api.utils import *
from app.core import app, logger
from app.api.tasks import domains
import libvirt
import time

# ======================================================================================================================
# ==========> DOMAINS METHODS <=========================================================================================
# ======================================================================================================================


# (C) Create new domain using virt-install
@app.route('/api/domains', methods=['POST'])
@token_required
def create_domain(cu):
    logger.info('Creando dominio')
    data = request.json
    task = domains.create_domain.delay(data)
    return json_response(data=task.task_id)


# (R) LIST ALL DOMAINS
@app.route('/api/domains', methods=['GET'])
@token_required
def get_all_domains(cu):
    logger.info('Obteniendo dominios')
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domains = conn.listAllDomains()
        domains_list = list()
        for dom in domains:
            is_active = True if dom.isActive() == 1 else False
            uuid = dom.UUIDString()
            name = dom.name()
            os_type = dom.OSType()
            total_memory = round(dom.info()[1] / 1024, 2)  # KB to MB
            used_memory = "-" if not is_active else round(dom.info()[2] / 1024, 2)  # KB to MB
            memory = dict(total=total_memory, used=used_memory)
            vcpus = dom.info()[3]
            state = dom.info()[0]
            vnc_port = get_vnc_port(dom)

            # ADDED SUPPORT FOR DISKS
            xml = ET.fromstring(dom.XMLDesc())
            devices = xml.findall('devices/disk')

            disk = {}

            for d in devices:
                if d.get('device') == 'disk':
                    file_path = d.find('source').get('file')
                    disk_info = dom.blockInfo(file_path)
                    disk['capacity'] = round(disk_info[0] / 1024 / 1024 / 1024, 2)
                    disk['allocation'] = round(disk_info[1] / 1024 / 1024 / 1024, 2)
                    disk['physical'] = round(disk_info[2] / 1024 / 1024 / 1024, 2)

            domains_list.append(dict(uuid=uuid,
                                     name=name,
                                     is_active=is_active,
                                     os_type=os_type,
                                     memory=memory,
                                     vcpus=vcpus,
                                     state=state,
                                     disk=disk,
                                     vnc_port=vnc_port))
        conn.close()
        return json_response(data=domains_list)
    except Exception as e:
        logger.error('No se pudo obtener los dominios: %s', str(e))
        return json_response(status=500)


# ##################################### #
# (D) DELETE A DOMAIN DESCRIBED BY NAME #
# 1) Look for domain disk devices       #
# 2) Remove disk devices from the fs    #
# 3) Undefine domain                    #
# ##################################### #
@app.route('/api/domains/<domain_uuid>', methods=['DELETE'])
@token_required
def delete_domain(cu, domain_uuid):
    logger.info('Eliminando dominio %s', domain_uuid)
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domain = conn.lookupByUUIDString(domain_uuid)
        xml = ET.fromstring(domain.XMLDesc())
        devices = xml.findall('devices/disk')
        for d in devices:
            if d.get('device') == 'disk':
                file_path = d.find('source').get('file')
                disk = conn.storageVolLookupByPath(file_path)
                disk.delete(libvirt.VIR_STORAGE_VOL_DELETE_NORMAL)
        domain.undefine()
        conn.close()
        return json_response()
    except Exception as e:
        logger.error('No se pudo eliminar el dominio %s: %s', domain_uuid, str(e))
        return json_response(status=500)


# START A DOMAIN DESCRIBED BY NAME
@app.route('/api/domains/<domain_uuid>/start', methods=['PUT'])
@token_required
def start_domain(cu, domain_uuid):
    logger.info('Encendiendo dominio %s', domain_uuid)
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domain = conn.lookupByUUIDString(domain_uuid)
        domain.create()
        time.sleep(3)
        domain = conn.lookupByUUIDString(domain_uuid)
        if domain.info()[0] != libvirt.VIR_DOMAIN_RUNNING:
            logger.error('No se pudo encender el dominio %s', domain_uuid)
            conn.close()
            return json_response(status=500)
        conn.close()
        return json_response()
    except Exception as e:
        logger.error('No se pudo encender el dominio %s: %s', domain_uuid, str(e))
        return json_response(status=500)


# REBOOT A DOMAIN DESCRIBED BY NAME
# TODO - Check if it has really rebooted
@app.route('/api/domains/<domain_uuid>/reboot', methods=['PUT'])
@token_required
def reboot_domain(cu, domain_uuid):
    logger.info('Reiniciando dominio %s', domain_uuid)
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domain = conn.lookupByUUIDString(domain_uuid)
        domain.reboot(libvirt.VIR_DOMAIN_REBOOT_DEFAULT)
        time.sleep(3)
        conn.close()
        return json_response()
    except Exception as e:
        logger.error('No se ha podido reiniciar el dominio %s: %s', domain_uuid, str(e))
        return json_response(status=500)


# SHUTDOWN A DOMAIN DESCRIBED BY NAME
@app.route('/api/domains/<domain_uuid>/shutdown', methods=['PUT'])
@token_required
def shutdown_domain(cu, domain_uuid):
    logger.info('Apagando el dominio %s', domain_uuid)
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domain = conn.lookupByUUIDString(domain_uuid)
        domain.destroy()
        time.sleep(3)
        domain = conn.lookupByUUIDString(domain_uuid)
        if domain.info()[0] != libvirt.VIR_DOMAIN_SHUTOFF:
            logger.error('No se pudo apagar el dominio %s', domain_uuid)
            conn.close()
            return json_response(status=500)
        conn.close()
        return json_response()
    except Exception as e:
        logger.error('No se ha podido apagar el dominio %s: %s', domain_uuid, str(e))
        return json_response(status=500)


# UPDATE A DOMAIN
@app.route('/api/domains/<domain_uuid>', methods=['PUT'])
@token_required
def update_domain(cu, domain_uuid):
    logger.info('Actualizando el dominio %s', domain_uuid)
    data = request.json
    try:
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        dom = conn.lookupByUUIDString(domain_uuid)
        dom.setMaxMemory(int(data['memory']) * 1024)
        dom.setVcpusFlags(int(data['vcpus']), libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_DOMAIN_VCPU_MAXIMUM)
        dom.setVcpusFlags(int(data['vcpus']))
    except Exception as e:
        logger.error("No se ha podido actualizar el dominio %s: %s", domain_uuid, str(e))
    return json_response(status=200)
