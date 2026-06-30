import os
import bpy

from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty
from typing import Protocol

from .local_storage import LocalStorage

# pyright: reportInvalidTypeForm=false

class OT_SavePreset(Operator):
    bl_idname = "grille.presets_save"
    bl_label = "Save Preset"
    bl_description = "Save current settings as a preset"

    preset_name: bpy.props.StringProperty(
        name="Preset Name",
        description="Name for the new preset",
        default=""
    )

    def invoke(self, context, event):
        active_op = OpPresetsUtils.get_operator(context)
        self.preset_name = active_op.temp_presets_selection
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name")


    def execute(self, context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.store_annotations(self.preset_name, active_op)
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        active_op.temp_presets_selection = self.preset_name

        return {'FINISHED'}



class OT_LoadPreset(Operator):
    bl_idname = "grille.presets_load"
    bl_label = "Load Preset"
    bl_description = "Load selected preset"

    def execute(self, context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.apply_annotations(active_op.temp_presets_selection, active_op)
        return {'FINISHED'}



class OT_RemovePreset(Operator):
    bl_idname = "grille.presets_remove"
    bl_label = "Remove Preset"
    bl_description = "Delete the selected preset"

    def execute(self, context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.presets.pop(active_op.temp_presets_selection, None)
        presets.setup_default(active_op)
        active_op.temp_presets_selection = presets.default_key
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        return {'FINISHED'}
    


class OT_SetDefaultPreset(Operator):
    bl_idname = "grille.presets_set_default"
    bl_label = "Set Default Preset"
    bl_description = "Set the selected preset as default"

    def execute(self, context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.default_key = active_op.temp_presets_selection
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        return {'FINISHED'}
    


class OT_SelectPreset(bpy.types.Operator):
    bl_idname = "grille.presets_select"
    bl_label = "Select Preset"

    preset_name: bpy.props.StringProperty()


    def execute(self, context):
        active_op = OpPresetsUtils.get_operator(context)
        active_op.temp_presets_selection = self.preset_name
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.apply_annotations(active_op.temp_presets_selection, active_op)
        return {'FINISHED'}
    


class MT_PresetsMenu(bpy.types.Menu):
    bl_label = "Presets"
    bl_idname = "GRILLE_MT_presets_menu"

    new_preset_name: bpy.props.StringProperty()


    def draw(self, context):
        layout = self.layout
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        for name in presets.presets:
            icon = "SOLO_ON" if name == presets.default_key else "NONE"
            op: OT_SelectPreset = layout.operator(OT_SelectPreset.bl_idname, text=name, icon=icon)
            op.preset_name = name



class POperator(Protocol):
    layout: bpy.types.UILayout
    temp_presets_initalized: bool
    temp_presets_file: str
    temp_presets_selection: str



class OpPresetsUtils:

    @staticmethod
    def draw(self: POperator, context: bpy.types.Context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
    
        row = self.layout.row(align=True)
        row.menu("GRILLE_MT_presets_menu", text=self.temp_presets_selection)
        row.operator("grille.presets_save", text="", icon='FILE_TICK')
        sub = row.row(align=True)
        sub.enabled = len(presets.presets) > 1
        sub.operator("grille.presets_remove", text="", icon='TRASH')
        sub.operator("grille.presets_set_default", text="", icon='SOLO_ON')


    @staticmethod
    def setup(self: POperator):
        if not self.temp_presets_initalized:
            presets = LocalStorage.setup_presets(self.temp_presets_file, self)
            self.temp_presets_selection = presets.default_key
            self.temp_presets_initalized = True


    @staticmethod
    def get_operator(context: bpy.types.Context) -> POperator:
        return context.active_operator


    @staticmethod
    def register():
        bpy.utils.register_class(OT_SavePreset)
        bpy.utils.register_class(OT_LoadPreset)
        bpy.utils.register_class(OT_RemovePreset)
        bpy.utils.register_class(OT_SetDefaultPreset)
        bpy.utils.register_class(OT_SelectPreset)
        bpy.utils.register_class(MT_PresetsMenu)


    @staticmethod
    def unregister():
        bpy.utils.unregister_class(MT_PresetsMenu)
        bpy.utils.unregister_class(OT_SelectPreset)
        bpy.utils.unregister_class(OT_SetDefaultPreset)
        bpy.utils.unregister_class(OT_RemovePreset)
        bpy.utils.unregister_class(OT_LoadPreset)
        bpy.utils.unregister_class(OT_SavePreset)