import subprocess
import paramiko
import libvirt
import pickle

from app.api.utils import *
from app.models import *
from app.core import celery, app, logger


@celery.task()
def create_template(data):
    try:
        domain_uuid = data['domain_uuid']
        template_name = data['template_name']
        template_description = data['template_description']
        do_sysprep = data['do_sysprep']

        # Check domain state
        conn = libvirt.open(app.config['LOCAL_QEMU_URI'])
        domain = conn.lookupByUUIDString(domain_uuid)
        if domain.isActive():
            logger.error('No se pudo crear la plantilla: el dominio debe estar apagado')
            return -1

        # Domain cloning (get disks paths and some hardware stuff)
        info = domain.info()
        memory = info[2]
        vcpus = info[3]

        xml = ET.fromstring(domain.XMLDesc())
        devices = xml.findall('devices/disk')
        disks = list()
        for d in devices:
            if d.get('device') == 'disk':
                file_path = d.find('source').get('file')
                disks.append(file_path)

        cmd = ['virt-clone',
               '--connect', app.config['LOCAL_QEMU_URI'],
               '--original', domain.name(),
               '--name', template_name]
        template_images_path = list()
        for count in range(disks.__len__()):
            template_image_path = app.config['TEMPLATE_IMAGES_DIR'] + template_name + '-disk' + str(count) + '.qcow2'
            template_images_path.append(template_image_path)
            cmd.append('--file')
            cmd.append(template_image_path)
        subprocess.check_call(cmd)

        if do_sysprep:
            # Decontextualize the template and dumps XML --> USING POLICYKIT WITH 'virt-sysprep'
            subprocess.check_call(['pkexec', '/usr/bin/virt-sysprep',
                                   '--connect', app.config['LOCAL_QEMU_URI'],
                                   '--domain', template_name])
        template_xml = str(app.config['TEMPLATE_DEFINITIONS_DIR'] + template_name + '.xml')
        proc = subprocess.Popen(['virsh', '--connect', app.config['LOCAL_QEMU_URI'], 'dumpxml', template_name],
                                stdout=subprocess.PIPE)
        out = proc.stdout.read().decode('utf-8')
        # print(out)

        file = open(str(template_xml), 'w')
        file.write(out)
        file.close()

        # Undefine template
        template = conn.lookupByName(template_name)
        template.undefine()

        # Add template to database

        data = dict(name=template_name,
                    description=template_description,
                    vcpus=vcpus,
                    memory=memory,
                    xml_path=template_xml,
                    images_path=template_images_path)
        template = Template(data)
        template.save()
        print("Plantilla creada")
        return 0
    except Exception as e:
        # TODO - Delete template on fs if Exception is instance of sqlite3.OperationalError
        logger.error('No se pudo crear la plantilla: %s', str(e))
        return -1


@celery.task()
def clone_template(template_uuid, data):
    try:
        template = Template.get(template_uuid).to_dict()
        domain_name = data['domain_name']
        lab_uuid = data['lab_uuid']

        lab = Lab.get(lab_uuid)
        hosts = lab.hosts

        if hosts.__len__() == 0:
            logger.error('El laboratorio no tiene ningún host asociado')
            return -1

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
            return -1
        return 0
    except Exception as e:
        logger.error('No se pudo desplegar la plantilla: %s', str(e))
        return -1
