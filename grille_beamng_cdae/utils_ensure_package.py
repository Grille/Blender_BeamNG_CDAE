import os
import sys
import subprocess

addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")

if modules_dir not in sys.path:
    sys.path.append(modules_dir)

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

def ensure_package(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
    except ImportError:
        install_package(package_name)