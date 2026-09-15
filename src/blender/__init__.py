import bpy

from .msgbox import MessageBox
from .object_properties import ObjectProperties
from .object_panel import ObjectPanel
from .material_properties import MaterialProperties
from .material_panel import MaterialPanel
from .material_operators import MaterialOperators
from .import_operator import ImportRegistry
from .export_operator import ExportRegistry
from .shader_nodes import ShaderNodeRegistry
from .presets_operators import OpPresetsUtils
from .utils_sidepanel import UtilsSidepanel


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