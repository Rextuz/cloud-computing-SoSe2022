import json

from fabric.context_managers import cd, settings, shell_env
from fabric.operations import local, put, run

LOCATION = "westeurope"
RESOURCE_GROUP = "myresourcegroup"
SUBSCRIPTION = "0be60f2e-ba63-4e12-92ac-7d8e49c57c95"  # from az login
USER = "azureuser"


def azure_login():
    with settings(warn_only=True):
        result = local("az account show")
    if result.return_code != 0:
        local("az login")
        local(f"az account set --subscription {SUBSCRIPTION}")


def create_resource_group():
    local(f"az group create --name {RESOURCE_GROUP} --location {LOCATION}")


def delete_resource_group():
    local(f"az group delete --yes --name {RESOURCE_GROUP}")


def create_vm(name, *ports):
    vm_ip = json.loads(
        local(
            f"az vm create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {name}"
            f" --size Standard_B1s"
            f" --image UbuntuLTS"
            f" --public-ip-sku Standard"
            f" --admin-username {USER}",
            capture=True,
        )
    )["publicIpAddress"]
    if ports:
        local(
            f"az vm open-port"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {name}"
            f" --port {','.join([str(port) for port in ports])}"
            f" --priority 100"
        )
    return vm_ip


def install_nodejs():
    run("sudo apt update")
    run("sudo apt install curl -y")
    run("curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -")
    run("sudo apt install -y nodejs")
    run("node --version")


def install_docker():
    run("sudo apt update")
    run("sudo apt install -y docker.io docker-compose")
    run("sudo systemctl enable docker")
    run("sudo systemctl start docker")
    run("sudo systemctl --no-pager status docker")
    run(f"sudo usermod -a -G docker {USER}")


def copy_backend(database_ip=None):
    run(f"mkdir -p /home/{USER}/backend")
    put("./app/backend", f"/home/{USER}")
    if database_ip:
        run(
            f"sed -i"
            f" s/DATABASE_IP/{database_ip}/g"
            f" /home/{USER}/backend/db/db.js"
        )


def copy_frontend(backend_ip=None):
    run(f"mkdir -p /home/{USER}/frontend")
    put("./app/frontend", f"/home/{USER}")
    if backend_ip:
        run(
            f"sed -i"
            f" s/BACKEND_IP/{backend_ip}/g"
            f" /home/{USER}/frontend/src/Components/ApiEndpoints.js"
        )


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
        run("node ./scripts/create_tables.js")

    run(f"chmod +x /home/{USER}/backend/backend.sh")

    run(f"sudo cp /home/{USER}/backend/backend.service /etc/systemd/system")
    run(f"sudo systemctl daemon-reload")
    run(f"sudo systemctl enable backend")
    run(f"sudo systemctl start backend")
    run(f"sudo systemctl --no-pager status backend")


def install_frontend():
    with cd(f"/home/{USER}/frontend"):
        run("npm install")

    run(f"chmod +x /home/{USER}/frontend/frontend.sh")

    run(f"sudo cp /home/{USER}/frontend/frontend.service /etc/systemd/system")
    run(f"sudo systemctl daemon-reload")
    run(f"sudo systemctl enable frontend")
    run(f"sudo systemctl start frontend")
    run(f"sudo systemctl --no-pager status frontend")


def start_database_service():
    run(
        f"sudo su - {USER} -c"
        f" 'cd /home/{USER}/database && docker-compose up -d main_db'"
    )


def deploy_all():
    azure_login()
    create_resource_group()
    db_ip = create_vm("database", 3306)
    with settings(host_string=f"{USER}@{db_ip}"):
        install_docker()
        copy_database_config()
        start_database_service()
    backend_ip = create_vm("backend", 3001, 8080)
    with settings(host_string=f"{USER}@{backend_ip}"):
        install_nodejs()
        copy_backend(database_ip=db_ip)
        install_backend()
    frontend_ip = create_vm("frontend", 3000)
    with settings(host_string=f"{USER}@{frontend_ip}"):
        install_nodejs()
        copy_frontend(backend_ip=backend_ip)
        install_frontend()


if __name__ == "__main__":
    print("Do not run this script directly!")
    print("Use `fab --list` to see available commands")
    print("Example:")
    print("  $ fab deploy_all")
