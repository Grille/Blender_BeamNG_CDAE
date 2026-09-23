from grille_cdae.common import *
from grille_cdae.common.basetypes import Operator, Menu

from .local_storage import LocalStorage


# pyright: reportIncompatibleMethodOverride=information



class OT_SavePreset(Operator):
    bl_idname = "grille.presets_save"
    bl_label = "Save Preset"
    bl_description = "Save current settings as a preset"

    preset_name: str

    def invoke(self, context, event):
        active_op = OpPresetsUtils.get_operator(context)
        self.preset_name = active_op.temp_presets_selection
        return not_none(context.window_manager).invoke_props_dialog(self)


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

OT_SavePreset.__annotations__.update(
    preset_name = bpy.props.StringProperty(name="Preset Name", description="Name for the new preset", default="")
)



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

    def execute(self, context: bpy.types.Context):
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

    def execute(self, context: bpy.types.Context):
        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.default_key = active_op.temp_presets_selection
        LocalStorage.set_presets(active_op.temp_presets_file, presets)
        return {'FINISHED'}
    


class OT_SelectPreset(Operator):
    bl_idname = "grille.presets_select"
    bl_label = "Select Preset"

    preset_name: str


    def execute(self, context):
        assert context is not None

        active_op = OpPresetsUtils.get_operator(context)
        active_op.temp_presets_selection = self.preset_name
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        presets.apply_annotations(active_op.temp_presets_selection, active_op)
        return {'FINISHED'}

OT_SelectPreset.__annotations__.update(
    preset_name = bpy.props.StringProperty()
) 



class MT_PresetsMenu(Menu):
    bl_label = "Presets"
    bl_idname = "GRILLE_MT_presets_menu"

    new_preset_name: str


    def draw(self, context):
        assert self.layout is not None
        assert context is not None

        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
        for name in presets.presets:
            icon = "SOLO_ON" if name == presets.default_key else "NONE"
            op = cast(OT_SelectPreset, self.layout.operator(OT_SelectPreset.bl_idname, text=name, icon=icon))
            op.preset_name = name

MT_PresetsMenu.__annotations__.update(
    new_preset_name = bpy.props.StringProperty()
)



class PresetOperator(Operator):
    temp_presets_initalized: bool
    temp_presets_file: str
    temp_presets_selection: str

PresetOperator.__annotations__.update(
    temp_presets_initalized = bpy.props.BoolProperty(default=False),
    temp_presets_file = bpy.props.StringProperty(default="export"),
    temp_presets_selection = bpy.props.StringProperty(),
)



class OpPresetsUtils:

    @staticmethod
    def draw(operator: PresetOperator, context: bpy.types.Context):
        assert operator.layout is not None

        active_op = OpPresetsUtils.get_operator(context)
        presets = LocalStorage.get_presets(active_op.temp_presets_file)
    
        row = operator.layout.row(align=True)
        row.menu(MT_PresetsMenu.bl_idname, text=operator.temp_presets_selection)
        row.operator(OT_SavePreset.bl_idname, text="", icon='FILE_TICK')
        sub = row.row(align=True)
        sub.enabled = len(presets.presets) > 1
        sub.operator(OT_RemovePreset.bl_idname, text="", icon='TRASH')
        sub.operator(OT_SetDefaultPreset.bl_idname, text="", icon='SOLO_ON')


    @staticmethod
    def setup(operator: PresetOperator):
        if not operator.temp_presets_initalized:
            presets = LocalStorage.setup_presets(operator.temp_presets_file, operator)
            operator.temp_presets_selection = presets.default_key
            operator.temp_presets_initalized = True


    @staticmethod
    def get_operator(context: bpy.types.Context):
        return cast(PresetOperator, context.active_operator)


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