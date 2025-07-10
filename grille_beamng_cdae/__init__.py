bl_info = {
    "name": "BeamNG CDAE",
    "author": "Grille",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}


from .ensure_package import ensure_package
ensure_package("msgpack")
ensure_package("zstandard")
ensure_package("numpy")


import bpy
from .blender_object_properties import ObjectProperties
from .blender_object_panel import ObjectPanel
from .blender_import_cdae import ImportCdae
from .blender_export_cdae import ExportCdae
from .blender_export_dae import ExportDae


def register():
    ObjectProperties.register()

    bpy.utils.register_class(ObjectPanel)

    bpy.utils.register_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.append(ImportCdae.menu_func)

    bpy.utils.register_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.append(ExportCdae.menu_func)

    bpy.utils.register_class(ExportDae)
    bpy.types.TOPBAR_MT_file_export.append(ExportDae.menu_func)


def unregister():
    ObjectProperties.unregister()

    bpy.utils.unregister_class(ObjectPanel)

    bpy.utils.unregister_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.remove(ImportCdae.menu_func)

    bpy.utils.unregister_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.remove(ExportCdae.menu_func)

    bpy.utils.unregister_class(ExportDae)
    bpy.types.TOPBAR_MT_file_export.remove(ExportDae.menu_func)
