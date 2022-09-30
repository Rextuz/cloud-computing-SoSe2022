import json
import time
from typing import List, Optional

from fabric.context_managers import cd, settings, shell_env
from fabric.operations import local, put, run

LOCATION = "westeurope"
RESOURCE_GROUP = "myresourcegroup"
SUBSCRIPTION = "0be60f2e-ba63-4e12-92ac-7d8e49c57c95"  # from az login
USER = "azureuser"

PUBLIC_IP_NAME = "public_ip"
LOAD_BALANCER_NAME = "load_balancer"
VNET_NAME = "lb_vnet"
SUBNET_NAME = "lb_subnet"
NETWORK_SECURITY_GROUP_NAME = "network_security_group"
BACKEND_POOL_NAME = LOAD_BALANCER_NAME + "_backend_pool"


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


def create_vm_with_nic(name, ports: Optional[List[int]] = None):
    public_ip_name = f"public_ip_{name}"
    public_ip = json.loads(
        local(
            f"az network public-ip create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {public_ip_name}"
            f" --allocation-method Static",
            capture=True,
        )
    )["publicIp"]["ipAddress"]
    network_security_group_name = f"security_group_{name}"
    local(
        f"az network nsg create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {network_security_group_name}"
    )
    for port in [22, *ports]:
        local(
            f"az network nsg rule create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --nsg-name {network_security_group_name}"
            f" --name {network_security_group_name}_{str(port)}_rule"
            f" --protocol tcp"
            f" --direction inbound"
            f" --priority 1001"
            f" --source-address-prefix '*'"
            f" --source-port-range '*'"
            f" --destination-address-prefix '*' "
            f" --destination-port-range {str(port)}"
            f" --access allow"
            f" --priority 2000"
        )
    nic_name = f"network_card_{name}"
    local(
        f"az network nic create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {nic_name}"
        f" --vnet-name {VNET_NAME}"
        f" --subnet {SUBNET_NAME}"
        f" --network-security-group {network_security_group_name}"
        f" --lb-name {LOAD_BALANCER_NAME}"
        f" --lb-address-pools {BACKEND_POOL_NAME}"
    )
    local(
        f"az vm create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {name}"
        f" --size Standard_B1s"
        f" --image UbuntuLTS"
        f" --public-ip-sku Standard"
        f" --admin-username {USER}"
        f" --nics {nic_name}"
    )
    return public_ip


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


def deploy_backend_load_balancer():
    # create_virtual_network and_subnet
    local(
        f"az network vnet create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --location {LOCATION}"
        f" --name {VNET_NAME}"
        f" --subnet-name {SUBNET_NAME}"
    )

    # create public ip address
    lb_ip_address = json.loads(
        local(
            f"az network public-ip create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {PUBLIC_IP_NAME}"
            f" --allocation-method Static",
            capture=True,
        )
    )["publicIp"]["ipAddress"]

    # create load balancer
    frontend_ip_name = LOAD_BALANCER_NAME + "_frontend_ip"
    local(
        f"az network lb create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {LOAD_BALANCER_NAME}"
        f" --public-ip-address {PUBLIC_IP_NAME}"
        f" --frontend-ip-name {frontend_ip_name}"
        f" --backend-pool-name {BACKEND_POOL_NAME}"
    )

    # create load balancer port probe to monitor the service health
    application_port_number = 3001
    probe_name = (
        LOAD_BALANCER_NAME + "_port_probe_" + str(application_port_number)
    )
    local(
        f"az network lb probe create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --lb-name {LOAD_BALANCER_NAME}"
        f" --name {probe_name}"
        f" --protocol tcp"
        f" --port {application_port_number}"
    )

    # create a load balancer port rule to rout traffic between the
    local(
        f"az network lb rule create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --lb-name {LOAD_BALANCER_NAME}"
        f" --name {LOAD_BALANCER_NAME}_rule"
        f" --protocol tcp"
        f" --frontend-port {application_port_number}"
        f" --backend-port {application_port_number}"
        f" --backend-pool-name {LOAD_BALANCER_NAME + '_backend_pool'}"
        f" --probe-name {probe_name}"
    )

    # create network security group
    local(
        f"az network nsg create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {NETWORK_SECURITY_GROUP_NAME}"
    )

    # create network security group rule for port 3001 for accessing the application server
    local(
        f"az network nsg rule create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --nsg-name {NETWORK_SECURITY_GROUP_NAME}"
        f" --name {NETWORK_SECURITY_GROUP_NAME}_rule"
        f" --protocol tcp"
        f" --direction inbound"
        f" --priority 1001"
        f" --source-address-prefix '*'"
        f" --source-port-range '*'"
        f" --destination-address-prefix '*' "
        f" --destination-port-range {application_port_number}"
        f" --access allow"
        f" --priority 2000"
    )

    return lb_ip_address


def deploy_all():
    azure_login()
    create_resource_group()
    lb_ip = deploy_backend_load_balancer()
    db_ip = create_vm_with_nic("database", ports=[3306])
    with settings(host_string=f"{USER}@{db_ip}"):
        install_docker()
        copy_database_config()
        start_database_service()
    for _ in range(3):
        upscale()
    frontend_ip = create_vm_with_nic("frontend", ports=[3000])
    with settings(host_string=f"{USER}@{frontend_ip}"):
        install_nodejs()
        copy_frontend(backend_ip=lb_ip)
        install_frontend()
    print(f"The app is running on http://{frontend_ip}:3001")


def upscale():
    azure_login()
    db_ip = json.loads(
        local(
            f"az network nic show"
            f" --name network_card_database"
            f" --resource-group {RESOURCE_GROUP}",
            capture=True,
        )
    )["publicIpAddress"]
    backend_ip = create_vm_with_nic(
        f"backend_{time.time()}", ports=[3001, 8080]
    )
    with settings(host_string=f"{USER}@{backend_ip}"):
        install_nodejs()
        copy_backend(database_ip=db_ip)
        install_backend()


def downscale():
    azure_login()
    vms = json.loads(
        local(f"az vm list --resource-group {RESOURCE_GROUP}", capture=True)
    )
    for vm in vms:
        if "backend" in vm["name"]:
            local(
                f"az vm delete"
                f" --resource-group {RESOURCE_GROUP}"
                f" --name {vm['name']}"
                f" --yes"
            )
            break


if __name__ == "__main__":
    print("Do not run this script directly!")
    print("Use `fab --list` to see available commands")
    print("Example:")
    print("  $ fab deploy_all")
