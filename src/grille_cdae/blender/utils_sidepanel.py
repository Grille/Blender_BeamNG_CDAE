from grille_cdae.common import *
from grille_cdae.common.basetypes import PropertyGroup, Operator, Panel

from ..beamng.material.material import MaterialVersion
from ..beamng.material.material_parser import MaterialParser



class UtilsPanelPropertyGroup(PropertyGroup):
    matconv_version: str
    matconv_aclip: bool
    matconv_force: bool

props.anotate_properties(UtilsPanelPropertyGroup,
    matconv_version = props.Enum(
        name="Material Version",
        description="BeamNG material conversion version",
        items=[
            ("1.0", "V1", ""),
            ("1.5", "V1.5 (PBR)", ""),
        ],
        default="1.0",
    ),
    matconv_aclip = props.Bool(
        name="Enable Alpha Clip",
        description="",
        default=True,
    ),
    matconv_force = props.Bool(
        name="Force Conversion",
        description="Force conversion even if materials already seem valid",
        default=False,
    )
)



class OT_convert_materials(Operator):
    bl_idname = "grille_beamng_cdae_utilspanel.convert_materials"
    bl_label = "Convert Materials"
    bl_description = "Convert materials to BeamNG format"

    def execute(self, context):
        properties = UtilsSidepanel.properties_from_ctx(context)

        target_version = MaterialVersion(float(properties.matconv_version))
        parser = MaterialParser(target_version)
        parser.force_alpha_clip = properties.matconv_aclip
        for bmat in bpy.data.materials:
            parser.convert_bmat(bmat, properties.matconv_force)

        return {'FINISHED'}
    


class PT_materials_panel(Panel):
    bl_label = "Materials"
    bl_idname = "GRILLE_PT_beamng_cdae_utilspanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BeamNG'

    def draw(self, context):
        layout = self.layout
        properties = UtilsSidepanel.properties_from_ctx(context)

        layout.prop(properties, "matconv_version")
        layout.prop(properties, "matconv_aclip")
        layout.prop(properties, "matconv_force")

        layout.separator()

        layout.operator(
            OT_convert_materials.bl_idname,
            text="Convert Materials",
            icon='MATERIAL'
        )



_pinfo = props.PropertyInfoFactory(types.Scene)

class UtilsSidepanel:

    classes = (
        UtilsPanelPropertyGroup,
        OT_convert_materials,
        PT_materials_panel,
    )

    utils_panel_properties = _pinfo.ptr("utils_panel_properties", UtilsPanelPropertyGroup)


    @staticmethod
    def properties_from_ctx(ctx: types.Context):
        assert ctx.scene is not None
        return UtilsSidepanel.utils_panel_properties[ctx.scene]


    @staticmethod
    def register():
        for cls in UtilsSidepanel.classes:
            bpy.utils.register_class(cls)
        _pinfo.register()


    @staticmethod
    def unregister():
        for cls in reversed(UtilsSidepanel.classes):
            bpy.utils.unregister_class(cls)
        _pinfo.unregister()