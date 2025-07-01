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
from .import_cdae import ImportCdae
from .export_cdae import ExportCdae


def menu_func_import(self, context):
    self.layout.operator(ImportCdae.bl_idname, text="BeamNG (.cdae)")


def menu_func_export(self, context):
    self.layout.operator(ExportCdae.bl_idname, text="BeamNG (.cdae)")


def register():
    bpy.utils.register_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

    bpy.utils.register_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    bpy.utils.unregister_class(ExportCdae)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
