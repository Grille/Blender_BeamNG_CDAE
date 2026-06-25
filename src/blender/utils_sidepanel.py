import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, EnumProperty

from ..beamng.material.material import MaterialVersion
from ..beamng.material.material_parser import MaterialParser

# pyright: reportInvalidTypeForm=false

class UtilsPanelPropertyGroup(PropertyGroup):

    matconv_version: EnumProperty(
        name="Material Version",
        description="BeamNG material conversion version",
        items=[
            ("1.0", "V1", ""),
            ("1.5", "V1.5 (PBR)", ""),
        ],
        default="1.0",
    )

    matconv_aclip: BoolProperty(
        name="Enable Alpha Clip",
        description="",
        default=True,
    )

    matconv_force: BoolProperty(
        name="Force Conversion",
        description="Force conversion even if materials already seem valid",
        default=False,
    )



class OT_convert_materials(bpy.types.Operator):
    bl_idname = "beamng_cdae_utilspanel.convert_materials"
    bl_label = "Convert Materials"
    bl_description = "Convert materials to BeamNG format"

    def execute(self, context):
        properties = UtilsSidepanel.properties_from_scene(context.scene)

        target_version = MaterialVersion(float(properties.matconv_version))
        parser = MaterialParser(target_version)
        parser.force_alpha_clip = properties.matconv_aclip
        for bmat in bpy.data.materials:
            parser.convert_bmat(bmat, properties.matconv_force)

        return {'FINISHED'}
    


class PT_materials_panel(bpy.types.Panel):
    bl_label = "Materials"
    bl_idname = "PT_beamng_cdae_utilspanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BeamNG'

    def draw(self, context):
        layout = self.layout
        properties = UtilsSidepanel.properties_from_scene(context.scene)

        layout.prop(properties, "matconv_version")
        layout.prop(properties, "matconv_aclip")
        layout.prop(properties, "matconv_force")

        layout.separator()

        layout.operator(
            OT_convert_materials.bl_idname,
            text="Convert Materials",
            icon='MATERIAL'
        )


class UtilsSidepanel:

    classes = (
        UtilsPanelPropertyGroup,
        OT_convert_materials,
        PT_materials_panel,
    )


    @staticmethod
    def properties_from_scene(scene: bpy.types.Scene) -> UtilsPanelPropertyGroup:
        return scene.beamngcdae_utils_panel_properties
        

    @staticmethod
    def register():
        for cls in UtilsSidepanel.classes:
            bpy.utils.register_class(cls)
        bpy.types.Scene.beamngcdae_utils_panel_properties = bpy.props.PointerProperty(type=UtilsPanelPropertyGroup)


    @staticmethod
    def unregister():
        for cls in reversed(UtilsSidepanel.classes):
            bpy.utils.unregister_class(cls)
        del bpy.types.Scene.beamngcdae_utils_panel_properties