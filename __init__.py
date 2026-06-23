import os
import sys
import subprocess

addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")

if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)

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

bl_info = {
    "name": "BeamNG CDAE",
    "author": "Paul Hirch",
    "version": (0, 9),
    "blender": (5, 1, 2),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}

ensure_package("msgpack")
ensure_package("zstandard")

from .src import register, unregister

