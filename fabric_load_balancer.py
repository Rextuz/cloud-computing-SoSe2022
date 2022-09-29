import json
import uuid

from fabric.operations import local

LOCATION = "westeurope"
RESOURCE_GROUP = "myresourcegroup"
USER = "azureuser"


def deploy_backend_load_balancer():
    # create_virtual_network and_subnet
    vnet_name = "lb_vnet_" + uuid.uuid4().hex
    subnet_name = "lb_subnet_" + uuid.uuid4().hex
    local(
        f"az network vnet create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --location {LOCATION}"
        f" --name {vnet_name}"
        f" --subnet-name {subnet_name}"
    )

    # create public ip address
    public_ip_name = 'public_ip_' + uuid.uuid4().hex
    local(
        f"az network public-ip create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {public_ip_name}"
    )

    # create load balancer
    load_balancer_name = "lb_" + uuid.uuid4().hex
    frontend_ip_name = load_balancer_name + "_frontend_ip"
    backend_pool_name = load_balancer_name + "_backend_pool"
    local(
        f"az network lb create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --name {load_balancer_name}"
        f" --public-ip-address {public_ip_name}"
        f" --frontend-ip-name {frontend_ip_name}"
        f" --backend-pool-name {backend_pool_name}"
    )

    # create load balancer port probe to monitor the service health
    application_port_number = 3001
    probe_name = load_balancer_name + "_port_probe_" + application_port_number
    local(
        f"az network lb probe create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --lb-name {load_balancer_name}"
        f" --name {probe_name}"
        f" --protocol http "
        f"--port {application_port_number}"
    )

    # create a load balancer port rule to rout traffic between the
    rule_name = load_balancer_name + "_port_rule_" + uuid.uuid4().hex
    local(
        f"az network lb rule create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --lb-name {load_balancer_name}"
        f" --name {rule_name}"
        f" --protocol http"
        f" --frontend-port 80"
        f" --backend-port {application_port_number}"
        f" --frontend-ip-name {public_ip_name}"
        f" --backend-pool-name {load_balancer_name + 'backend_pool'}"
        f" --probe-name {probe_name}"
    )

    # create a NAT rule to map ssh port on load balancer to VMs in pool
    for i in range(3):
        nat_rule_name = load_balancer_name + '_nat_ssh_rule_' + (i + 1)
        local(
            f"az network lb inbound-nat-rule create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --lb-name {load_balancer_name}"
            f" --name {nat_rule_name}"
            f" --protocol tcp"
            f" --frontend-port 422{i + 1}"  # port 4221 maps to vm 1, 4222 to vm 2 and so on ToDo: change to a better solution problematic if we have more than 99 vm
            f" --backend-port 22"
            f" --frontend-ip-name {public_ip_name}"
        )

    # create network security group
    network_security_group_name = 'network_security_group_' + uuid.uuid4().hex
    local(
        f"az network nsg create"
        f" --resource-group $resourceGroup"
        f" --name {network_security_group_name}"
    )

    # create network security group rule for port 22 for sshing to Vms
    local(
        f"az network nsg rule create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --nsg-name {network_security_group_name}"
        f" --name {network_security_group_name + 'ssh_rule'} --protocol tcp --direction inbound "
        f"--source-address-prefix '*' --source-port-range '*'  --destination-address-prefix '*' "
        f"--destination-port-range 22 --access allow --priority 1000 "
    )

    # create network security group rule for port 3001 for accessing the application server
    local(
        f"az network nsg rule create"
        f" --resource-group {RESOURCE_GROUP}"
        f" --nsg-name {network_security_group_name}"
        f" --name {network_security_group_name + 'web_rule'} --protocol tcp --direction inbound "
        f" --priority 1001 --source-address-prefix '*' --source-port-range '*' --destination-address-prefix '*' "
        f" --destination-port-range {application_port_number} --access allow --priority 2000 "
    )

    # create three virtual network card
    for i in range(3):
        local(
            f"az network nic create"
            f" --resource-group {RESOURCE_GROUP}"
            f" --name {'network_card_' + uuid.uuid4().hex}"
            f" --vnet-name {vnet_name}"
            f" --subnet {subnet_name}"
            f" --network-security-group {network_security_group_name}"
            f" --lb-name {load_balancer_name}"
            f" --lb-address-pools {backend_pool_name}"
            f" --lb-inbound-nat-rules {load_balancer_name + '_nat_ssh_rule_' + (i + 1)}"
        )

    # create an availability set.
    local(
        f"az vm availability-set create --resource-group {RESOURCE_GROUP}"
        f" --name {load_balancer_name + '_availability_set'} "
        f"--platform-fault-domain-count 3 --platform-update-domain-count 3 "
    )

    # create virtual machines and attach to them the virtual network cards and the availability set

