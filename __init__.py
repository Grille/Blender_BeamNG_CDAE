import os
import sys

addon_dir = os.path.dirname(__file__)

def add_path(path: str):
    dir = os.path.join(addon_dir, path)
    if dir not in sys.path: sys.path.insert(0, dir)

add_path("modules")
add_path("src")

bl_info: dict[str, object] = {
    "name": "BeamNG CDAE",
    "author": "Paul Hirch",
    "version": (0, 10),
    "blender": (4, 5, 0),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}

from grille_cdae.blender import register, unregister
__all__ = "bl_info", "register", "unregister"