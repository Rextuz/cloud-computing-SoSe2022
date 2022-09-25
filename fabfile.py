from fabric.context_managers import cd, shell_env
from fabric.operations import local, put, run

RESOURCE_GROUP = "myresourcegroup"
LOCATION = "westeurope"
SUBSCRIPTION = "0be60f2e-ba63-4e12-92ac-7d8e49c57c95"


def azure_login():
    local("az login")
    local(f"az account set --subscription {SUBSCRIPTION}")


def create_resource_group():
    local(f"az group create --name {RESOURCE_GROUP} --location {LOCATION}")


def delete_resource_group():
    local(f"az group delete --yes --name {RESOURCE_GROUP}")


def create_vm(name):
    local(f"az vm create"
          f" --resource-group {RESOURCE_GROUP}"
          f" --name {name}"
          f" --size Standard_B1ls"
          f" --image UbuntuLTS"
          f" --public-ip-sku Standard"
          f" --admin-username azureuser")


def install_nodejs():
    run("apt update")
    run("apt install curl -y")
    run("curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -")
    run("sudo apt install -y nodejs")
    run("node --version")


# from https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
def install_docker():
    run("sudo apt-get update")
    run("sudo apt-get install ca-certificates curl gnupg lsb-release")
    run("sudo mkdir -p /etc/apt/keyrings")
    run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
        )
    run("echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"
        )
    run("sudo apt-get update")
    run("sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin"
        )
    #run("sudo systemctl enable docker") # uncomment if necessary


def copy_backend():
    run("mkdir -p /root/cloud_computing/backend")
    put("./app/backend", "/root/cloud_computing")


def copy_frontend():
    run("mkdir -p /root/cloud_computing/frontend")
    put("./app/frontend", "/root/cloud_computing")


def copy_database():
    run("mkdir -p /root/cloud_computing/database")
    put("./app/database/docker-compose.yml", "/root/cloud_computing/database")


def install_backend():
    run("mkdir -p /storage/profile_uploads")
    run("mkdir -p /storage/course_uploads")
    with shell_env(
            PROFILE_STORAGE="/storage/profile_uploads",
            COURSE_STORAGE="/storage/course_uploads",
    ), cd("/root/cloud_computing/backend"):
        run("npm install")
        run("node index.js")


def install_frontend():
    with shell_env(CI="true"), cd("/root/cloud_computing/frontend"):
        run("npm install")
        run("npm start")


def start_docker():
    run("docker compose up")


def deploy_backend():
    azure_login()
    create_resource_group()
    create_vm("backend")
    install_nodejs()
    copy_backend()
    install_backend()


def deploy_database():
    install_docker()
    copy_database()
    start_docker()