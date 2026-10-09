import bpy

from .blender.msgbox import MessageBox
from .blender.object_properties import ObjectProperties
from .blender.object_panel import ObjectPanel
from .blender.material_properties import MaterialProperties
from .blender.material_panel import MaterialPanel
from .blender.material_operators import MaterialOperators
from .blender.import_operator import ImportRegistry
from .blender.export_operator import ExportRegistry
from .blender.shader_nodes import ShaderNodeRegistry
from .blender.presets_operators import OpPresetsUtils
from .blender.utils_sidepanel import UtilsSidepanel


def register():
    bpy.utils.register_class(MessageBox)

    ObjectProperties.register()
    bpy.utils.register_class(ObjectPanel)

    MaterialOperators.register()
    MaterialProperties.register()
    bpy.utils.register_class(MaterialPanel)

    OpPresetsUtils.register()
    ExportRegistry.register()
    ImportRegistry.register()
    ShaderNodeRegistry.register()

    UtilsSidepanel.register()


def unregister():
    bpy.utils.unregister_class(MessageBox)

    ObjectProperties.unregister()
    bpy.utils.unregister_class(ObjectPanel)

    MaterialOperators.unregister()
    MaterialProperties.unregister()
    bpy.utils.unregister_class(MaterialPanel)

    OpPresetsUtils.unregister()
    ExportRegistry.unregister()
    ImportRegistry.unregister()
    ShaderNodeRegistry.unregister()

    UtilsSidepanel.unregister()