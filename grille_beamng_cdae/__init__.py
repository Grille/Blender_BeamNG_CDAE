bl_info = {
    "name": "BeamNG CDAE",
    "author": "Grille",
    "version": (0, 5),
    "blender": (4, 5, 0),
    "location": "File > Import/Export",
    "category": "Import-Export",
    "description": "Import and Export BeamNG model format (.cdae)",
}


from .utils_ensure_package import ensure_package
ensure_package("msgpack")
ensure_package("zstandard")

import bpy

from .blender_msgbox import MessageBox
from .blender_object_properties import ObjectProperties
from .blender_object_panel import ObjectPanel
from .blender_material_properties import MaterialProperties
from .blender_material_panel import MaterialPanel
from .blender_import import ImportCdae
from .blender_export import ExportRegistry
from .blender_shader_nodes import ShaderNodeRegistry
from .blender_op_presets import OpPresetsUtils


def register():
    bpy.utils.register_class(MessageBox)

    ObjectProperties.register()
    bpy.utils.register_class(ObjectPanel)

    MaterialProperties.register()
    bpy.utils.register_class(MaterialPanel)

    bpy.utils.register_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.append(ImportCdae.menu_func)

    OpPresetsUtils.register()
    ExportRegistry.register()
    ShaderNodeRegistry.register()


def unregister():
    bpy.utils.unregister_class(MessageBox)

    ObjectProperties.unregister()
    bpy.utils.unregister_class(ObjectPanel)

    MaterialProperties.unregister()
    bpy.utils.unregister_class(MaterialPanel)

    bpy.utils.unregister_class(ImportCdae)
    bpy.types.TOPBAR_MT_file_import.remove(ImportCdae.menu_func)

    OpPresetsUtils.unregister()
    ExportRegistry.unregister()
    ShaderNodeRegistry.unregister()