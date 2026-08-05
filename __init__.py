import os
import sys

addon_dir = os.path.dirname(__file__)
modules_dir = os.path.join(addon_dir, "modules")

if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)

bl_info = {
    "name": "BeamNG CDAE",
    "author": "Paul Hirch",
    "version": (0, 10),
    "blender": (4, 5, 0),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}

from .src.blender import register, unregister

