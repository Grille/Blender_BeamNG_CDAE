import os
import sys
import subprocess

addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")


def install_package(package_name):
    python_exe = sys.executable
    try:
        print(f"Install {package_name} in {modules_dir}")
        subprocess.check_call([
            python_exe, "-m", "pip", "install",
            package_name, "--target", modules_dir
        ])
        print("Installed:", package_name)
    except Exception as e:
        print("Failed to install", package_name, e)


def ensure_package(package_name):
    package_dir = os.path.join(modules_dir, package_name)
    if not os.path.isdir(package_dir): install_package(package_name)


def setup():
    ensure_package("msgpack")


if __name__ == "__main__": setup()