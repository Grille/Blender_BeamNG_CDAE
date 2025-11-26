import os
import bpy

from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty

from .utils_local_storage import LocalStorage

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
        active_op = context.active_operator
        self.preset_name = active_op.temp_presets_selection
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name")


    def execute(self, context):
        active_op = context.active_operator
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
        active_op = context.active_operator
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.apply_annotations(active_op.temp_presets_selection, active_op)
        return {'FINISHED'}



class OT_RemovePreset(Operator):
    bl_idname = "grille.presets_remove"
    bl_label = "Remove Preset"
    bl_description = "Delete the selected preset"

    def execute(self, context):
        active_op = context.active_operator
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.presets.pop(active_op.temp_presets_selection, None)
        active_op.temp_presets_selection = ""
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        return {'FINISHED'}
    


class OT_SetDefaultPreset(Operator):
    bl_idname = "grille.presets_set_default"
    bl_label = "Set Default Preset"
    bl_description = "Set the selected preset as default"

    def execute(self, context):
        active_op = context.active_operator
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.default_key = active_op.temp_presets_selection
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        return {'FINISHED'}
    


class OT_SelectPreset(bpy.types.Operator):
    bl_idname = "grille.presets_select"
    bl_label = "Select Preset"

    preset_name: bpy.props.StringProperty()


    def execute(self, context):
        active_op = context.active_operator
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
        active_op = context.active_operator
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        for name in presets.presets:
            icon = "SOLO_ON" if name == presets.default_key else "NONE"
            op = layout.operator("grille.presets_select", text=name, icon=icon)
            op.preset_name = name



class OpPresetsUtils:

    @staticmethod
    def draw(self, layout):
        row = layout.row(align=True)
        row.menu("GRILLE_MT_presets_menu", text=self.temp_presets_selection)
        row.operator("grille.presets_save", text="", icon='FILE_TICK')
        #row.operator("grille.presets_load", text="", icon='FILEBROWSER')
        row.operator("grille.presets_remove", text="", icon='TRASH')
        row.operator("grille.presets_set_default", text="", icon='SOLO_ON')


    @staticmethod
    def apply_default(self: Operator):
        presets = LocalStorage.get_presets(self.temp_presets_file)
        self.temp_presets_selection = presets.default_key
        presets.apply_annotations(self.temp_presets_selection, self)


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