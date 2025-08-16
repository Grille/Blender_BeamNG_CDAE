bl_info = {
    "name": "BeamNG CDAE",
    "author": "Grille",
    "version": (0, 5),
    "blender": (4, 5, 0),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}


from .ensure_package import ensure_package
ensure_package("msgpack")
ensure_package("zstandard")
ensure_package("numpy")


import bpy
import bl_ui
import nodeitems_utils as nutils
import nodeitems_builtins

from .blender_object_properties import ObjectProperties
from .blender_object_panel import ObjectPanel
from .blender_material_properties import MaterialProperties
from .blender_material_panel import MaterialPanel
from .blender_import_cdae import ImportCdae
from .blender_export import ExportBase
from .blender_shader_nodes import ShaderNodeRegistry


def register():

    ObjectProperties.register()
    bpy.utils.register_class(ObjectPanel)

    MaterialProperties.register()
    bpy.utils.register_class(MaterialPanel)

    bpy.utils.register_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.append(ImportCdae.menu_func)

    bpy.utils.register_class(ExportBase)
    bpy.types.TOPBAR_MT_file_export.append(ExportBase.menu_func)

    ShaderNodeRegistry.register()


def unregister():
    ObjectProperties.unregister()
    bpy.utils.unregister_class(ObjectPanel)

    MaterialProperties.unregister()
    bpy.utils.unregister_class(MaterialPanel)

    bpy.utils.unregister_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.remove(ImportCdae.menu_func)

    bpy.utils.unregister_class(ExportBase)
    bpy.types.TOPBAR_MT_file_export.remove(ExportBase.menu_func)

    ShaderNodeRegistry.unregister()