import json

from fabric.context_managers import cd, settings, shell_env
from fabric.operations import local, put, run

LOCATION = "westeurope"
RESOURCE_GROUP = "myresourcegroup"
SUBSCRIPTION = "0be60f2e-ba63-4e12-92ac-7d8e49c57c95"
USER = "azureuser"


def azure_login():
    local("az login")
    local(f"az account set --subscription {SUBSCRIPTION}")


def create_resource_group():
    local(f"az group create --name {RESOURCE_GROUP} --location {LOCATION}")


def delete_resource_group():
    local(f"az group delete --yes --name {RESOURCE_GROUP}")


def create_vm(name):
    return json.loads(
        local(
            f"az vm create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {name}"
            f" --size Standard_B1ls"
            f" --image UbuntuLTS"
            f" --public-ip-sku Standard"
            f" --admin-username {USER}",
            capture=True,
        )
    )["publicIpAddress"]


def install_nodejs():
    run("sudo apt update")
    run("sudo apt install curl -y")
    run("curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -")
    run("sudo apt install -y nodejs")
    run("node --version")


def install_docker():
    run("sudo apt update")
    run("sudo apt install -y docker.io docker-compose")
    run("sudo systemctl enable --now docker")
    run(f"sudo usermod -a -G docker {USER}")


def copy_backend():
    run(f"mkdir -p /home/{USER}/backend")
    put("./app/backend", f"/home/{USER}")


def copy_frontend():
    run("mkdir -p /root/cloud_computing/frontend")
    put("./app/frontend", "/root/cloud_computing")


def copy_database_config():
    run(f"mkdir -p /home/{USER}/database")
    put("./app/database/docker-compose.yml", f"/home/{USER}/database")


def install_backend():
    run(f"mkdir -p /home/{USER}/profile_uploads")
    run(f"mkdir -p /home/{USER}/course_uploads")
    with shell_env(
        PROFILE_STORAGE=f"/home/{USER}/profile_uploads",
        COURSE_STORAGE=f"/home/{USER}/course_uploads",
    ), cd(f"/home/{USER}/backend"):
        run("npm install")
        run("node index.js")


def install_frontend():
    with shell_env(CI="true"), cd("/root/cloud_computing/frontend"):
        run("npm install")
        run("npm start")


def start_database_service():
    with cd(f"/home/{USER}/database"):
        run("docker-compose up -d")


def deploy_backend():
    azure_login()
    create_resource_group()
    backend_ip = create_vm("backend")
    with settings(host_string=f"{USER}@{backend_ip}"):
        install_nodejs()
        copy_backend()
        install_backend()


def deploy_database():
    azure_login()
    create_resource_group()
    db_ip = create_vm("database")
    with settings(host_string=f"{USER}@{db_ip}"):
        install_docker()
        copy_database_config()
        start_database_service()
