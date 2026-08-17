import os
import shutil
import sys
import subprocess

python_exe = sys.executable
addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")
bpy_dir = os.path.join(addon_dir, "bpy")


def install_package(modules_dir, package_name):
    try:
        print(f"Install {package_name} in {modules_dir}")
        subprocess.check_call([
            python_exe, "-m", "pip", "install",
            package_name, "--target", modules_dir
        ])
        print("Installed:", package_name)
    except Exception as e:
        print("Failed to install", package_name, e)


def cleanup_dir(dir):
    print(f"cleanup {dir}")
    shutil.rmtree(dir)
    os.mkdir(dir)


def setup():

    print(python_exe)
    print(sys.version)
    print(sys.prefix)

    try:
        subprocess.check_call([python_exe, "-m", "ensurepip", "--upgrade"])
    except subprocess.CalledProcessError:
        print("ensurepip failed")

    cleanup_dir(modules_dir)
    cleanup_dir(bpy_dir)
    install_package(modules_dir, "msgpack")
    install_package(bpy_dir, "fake-bpy-module-5.2")


if __name__ == "__main__": setup()