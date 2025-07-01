import os
import sys
import subprocess
import ensurepip

addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")

if modules_dir not in sys.path:
    sys.path.append(modules_dir)

def ensure_package(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
    except ImportError:
        ensurepip.bootstrap()
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package_name, "--target", modules_dir
        ])
        import importlib
        importlib.invalidate_caches()
        __import__(import_name)