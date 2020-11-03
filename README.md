# DIS vLab Server

DIS vLab Server (DVLS) is a 'full-stack' application to manage virtual labs in the Computer Engineering School of the University of Las Palmas de Gran Canaria (ULPGC). Really, a virtual lab is just a room with a set of physical computers with a CentOS 7.x Desktop installation with libvirt and virt-manager. Also, DVLS runs on CentOS 7.x Minimal in a powerful computer or server. This workstation manages the local hypervisor to generate templates and connects remotely via SSH with the computers in virtual labs to deploy these templates and realize standard operations with virtual machines.

## Table of Contents

1. [Requirements](#requirements)<br>
2. [Repository and dependencies](#repository-and-dependencies)<br>
3. [Celery configuration](#celery-configuration)<br>
  i. [Installing RabbitMQ](#installing-rabbitmq)<br>
  ii. [Creating the Celery service](#creating-the-celery-service)<br>
4. [System configuration](#system-configuration)<br>
  i. [User and groups](#user-and-groups)<br>
  ii. [Firewall](#firewall)<br>
  ii. [PolicyKit](#policykit)<br>
  iii. [Pluggable Authentication Modules](#pluggable-authentication-modules)<br>
5. [DVLS Service](#dvls-service)<br>
6. [Nginx configuration](#nginx-configuration)<br>
  i. [Secure Socket Layer](#secure-sockets-layer)<br>
  ii. [Reverse proxy configuration](#reverse-proxy-configuration)<br>
7. [Accessing to web interface](#accessing-to-web-interface)<br>
8. [Troubleshooting](#troubleshooting)<br>
9. [License](#license)<br>
10. [Author information](#author-information)<br>

## Requirements
To deploy DVLS you will need have installed CentOS 7.x Minimal installation with [EPEL](https://fedoraproject.org/wiki/EPEL/es) and [IUS](https://ius.io/setup) repositories and these groups/packages:
* "Virtualization Platform" (group)
* "Virtualization Hypervisor" (group)
* "Virtualization Tools" (group)
* "Virtualization Client" (group)
* "Development" (group)
* "libvirt-devel.x86_64"
* "libguestfs-tools"
* "python36u"
* "python36u-devel"
* "python36u-pip"
* "nginx"
* "openssl"
* "erlang"
* "socat"

## Repository and dependencies

Clone the repository with source code into recommended directory **/usr/lib**:
```bash
# cd /usr/lib
# git clone https://github.com/Acova/DIS-vLab-Server-2_0
```
You need virtualenv to install Python dependencies. For it, use ```# pip3.6 install virtualenv```. Then, create a virtualenv inside DVLS folder:
```bash
# cd dvls
# virtualenv venv
```
Activate the virtual environment with ```# source venv/bin/activate```, and install the dependencies with ```(venv) # pip install -r requirements.txt```.

## Celery configuration

#### Installing RabbitMQ

In order for Celery to work, we need to install the RabbitMQ Broker:

```bash
# wget https://www.rabbitmq.com/releases/rabbitmq-server/v3.6.10/rabbitmq-server-3.6.10-1.el7.noarch.rpm
# rpm --import https://www.rabbitmq.com/rabbitmq-release-signing-key.asc
# rpm -Uvh rabbitmq-server-3.6.10-1.el7.noarch.rpm
```

#### Creating the Celery service

Next, we shall create a service so Celery can be used with Systemd. This file must be created under the **/etc/systemd/system/** directory. We will call it celery.service:

```bash
[Unit]
Description=Celery Service
After=network.target

[Service]
WorkingDirectory=/usr/lib/dvls
ExecStart=/bin/sh -c '/usr/lib/dvls/venv/bin/celery --app=app.core.celery worker -f /var/log/dvls-worker.log -l DEBUG -E'
```

## System configuration

#### User and groups

The DVLS service will be started by a non-root user named as "dvls" for security reasons, so you need to create if you didn't it at CentOS 7 installer. This will be the user that will access the application. Also, it should be part of nginx and libvirt groups.
```bash
# useradd dvls
# passwd dvls
# usermod -a -G libvirt dvls
```

#### Firewall

CentOS 7 has firewalld running, so you should add a rule for incoming HTTP or HTTPS traffic, depending if you'll configure SSL in Nginx:
```bash
# firewall-cmd --add-service=http --permanent
# firewall-cmd --add-service=https --permanent
```

In addition, connections to manage the domains will be made through VNC, so it's necessary to open a range of default ports:
```bash
# firewall-cmd --add-port=5900-5910/tcp --permanent
# firewall-cmd --add-port=6080/tcp --permanent
```

Finally, reload the rules:
```bash
# firewall-cmd --reload
```

#### PolicyKit

By default, all non-root users that be part of libvirt group have privileges to manage and use libvirt. You can find that rule file in **/usr/share/polkit-1/rules.d/50-libvirt.rules**.<br>
However, all resources handled by privileged connections will be owned by 'root' user and group, so, to use virt-sysprep, you need to add a PolicyKit action and rule
#### Pluggable Authentication Modules

DVLS uses a PAM Python library to authenticate the user against **/etc/shadow** file. So that it works correctly, you need to create a new PAM service called 'dvls': 
```bash
# echo "auth required pam_unix.so" > /etc/pam.d/dvls 
```

## DVLS service

Create a new file into **/etc/systemd/system/** directory, e.g. dvls.service, with these content to handle DVLS application as a system service:
```bash
[Unit]
Description=uWSGI instance for DIS vLab Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/usr/lib/dvls
ExecStart=/usr/lib/dvls/venv/bin/python3.6 /usr/lib/dvls/wsgi.py

[Install]
WantedBy=multi-user.target
```
Before **enable** and **start** dvls.service, change the owner of DVLS folder with: ```# chown dvls:dvls /usr/lib/dvls```

## Nginx configuration

#### Secure Sockets Layer

It's a good practise use HTTPS instead HTTP in web applications inside corporate environment that is susceptible to traffic monitoring, redirection and manipulation. For that reason, it's recommendable generate an auto-signed certificate using OpenSSL. First of all, make sure that exists **/etc/nginx/ssl** directory, where server certificate and its key will be stored. To generate the key and certificate, use this command: ```# openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt```.
> NOTE: Change the firewall rule if you configure SSL in Nginx.

#### Reverse proxy configuration

After the implementation of WebSockets, the usage of uWSGI was no longer necesary, as the Socket.IO package creates a production ready server. Anyways, we still neeed to configure Nginx as a reverse proxy, and to translate WebSockets into HTTP. Create the file **/etc/nginx/conf.d/dvls.conf**

```nginx
server {
    listen 443 ssl;
    server_name dvls.dis.ulpgc.es;
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:5000;
    }
    
    location /static {
        alias /usr/lib/dvls/static;
        expires 30d;
    }
    
    location /socket.io {
        include proxy_params;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_pass http://127.0.0.1:5000/socket.io;
    }
}
```

Make sure that the file **/etc/nginx/proxy_params** exists. If not, create it and write this:

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

## Accessing to web interface

Before to start both the DVLS and Celery services.

Open your preferred browser and navigate via HTTP or HTTPS, depending of your configuration, to ```<protocol>://dvls.dis.ulpgc.es/``` and enter the credentials of dvls user in login page.

## Troubleshooting

You can get a 502 Nginx error when accessing to web interface if you're using SELinux in enforcing mode. It happens due to wrong SELinux policy to use the dvls.sock. To fix that, you'll need to add the correct SELinux policy module. Once you get the error in browser, use ```audit2allow``` to generate the correct SELinux module. With CentOS 7 Minimal installation you should install ```policycoreutils-python``` to use it.
```bash
# grep nginx /var/log/audit/audit.log | audit2allow -M nginx
# semodule -i nginx.pp
```

## License

Pending

## Author Information

Alberto Sosa, student of Computer Engineering at University of Las Palmas de Gran Canaria, 2018.

