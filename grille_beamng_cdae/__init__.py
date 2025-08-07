bl_info = {
    "name": "BeamNG CDAE",
    "author": "Grille",
    "version": (0, 4),
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
from .blender_export_cdae import ExportCdae
from .blender_export_dae import ExportDae
from .blender_shader_nodes import BeamBSDF15, BeamStageMix, ShaderNodeTree


def register():

    ObjectProperties.register()
    bpy.utils.register_class(ObjectPanel)

    MaterialProperties.register()
    bpy.utils.register_class(MaterialPanel)

    bpy.utils.register_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.append(ImportCdae.menu_func)

    bpy.utils.register_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.append(ExportCdae.menu_func)

    bpy.utils.register_class(ExportDae)
    bpy.types.TOPBAR_MT_file_export.append(ExportDae.menu_func)

    ShaderNodeTree.register_nodes()
    bpy.utils.register_class(ShaderNodeTree)
    bpy.types.NODE_MT_add.append(ShaderNodeTree.addmenu_append)


def unregister():
    ObjectProperties.unregister()
    bpy.utils.unregister_class(ObjectPanel)

    MaterialProperties.unregister()
    bpy.utils.unregister_class(MaterialPanel)

    bpy.utils.unregister_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.remove(ImportCdae.menu_func)

    bpy.utils.unregister_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.remove(ExportCdae.menu_func)

    bpy.utils.unregister_class(ExportDae)
    bpy.types.TOPBAR_MT_file_export.remove(ExportDae.menu_func)

    bpy.types.NODE_MT_add.remove(ShaderNodeTree.addmenu_append)
    bpy.utils.unregister_class(ShaderNodeTree)
    ShaderNodeTree.unregister_nodes()