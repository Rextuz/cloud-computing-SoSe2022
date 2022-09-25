from fabric.context_managers import cd, shell_env
from fabric.operations import put, run


def install_nodejs():
    run("apt update")
    run("apt install curl -y")
    run("curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -")
    run("sudo apt install -y nodejs")
    run("node --version")


def copy_backend():
    run("mkdir -p /root/cloud_computing/backend")
    put("./app/backend", "/root/cloud_computing")


def copy_frontend():
    run("mkdir -p /root/cloud_computing/frontend")
    put("./app/frontend", "/root/cloud_computing")


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


def deploy_backend():
    install_nodejs()
    copy_backend()
    install_backend()
