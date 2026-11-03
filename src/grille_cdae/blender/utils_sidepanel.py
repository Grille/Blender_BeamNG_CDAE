from grille_cdae.common import *
from grille_cdae.common.basetypes import PropertyGroup, Operator, Panel

from ..beamng.material.material import MaterialVersion
from ..beamng.material.material_parser import MaterialParser, ImageNodeMode
from .uilayout import UILayoutCtx

class UtilsPanelPropertyGroup(PropertyGroup):
    pass

class UtilsPanelPInfo(PropertyInfoGroup[UtilsPanelPropertyGroup]):
    pinfo = PropertyInfoFactory()
    
    matconv_version = pinfo.enum("Material Version", description="BeamNG material conversion version", items=[("1.0", "V1"), ("1.5", "V1.5 (PBR)")], default="1.0")
    matconv_aclip = pinfo.bool("Enable Alpha Clip", True)
    matconv_force = pinfo.bool("Force Conversion", False)
    matconv_image_nodes = pinfo.enum("Image Nodes", description="Nodes created for image maps", items=[
        (ImageNodeMode.CONVERTER.value, "Image + Converter", "Blender image texture with a BNG image converter, all images share one node group"),
        (ImageNodeMode.BEAM_IMAGE_TEX.value, "BNG Image Texture", "One BNG image texture per image, each image gets its own node group"),
    ], default=ImageNodeMode.CONVERTER.value)

UtilsPanelPInfo.pinfo.annotate(UtilsPanelPropertyGroup)



class OT_convert_materials(Operator):
    bl_idname = "grille_beamng_cdae_utilspanel.convert_materials"
    bl_label = "Convert Materials"
    bl_description = "Convert materials to BeamNG format"

    def execute(self, context):
        properties = UtilsSidepanel.properties_from_ctx(context)
        pinfo = UtilsPanelPInfo

        target_version = MaterialVersion(float(pinfo.matconv_version[properties]))
        parser = MaterialParser(target_version)
        parser.force_alpha_clip = pinfo.matconv_aclip[properties]
        parser.image_nodes = ImageNodeMode(pinfo.matconv_image_nodes[properties])
        for bmat in bpy.data.materials:
            parser.convert_bmat(bmat, pinfo.matconv_force[properties])

        for issue in parser.issues: print(f"Material: {issue}")
        if parser.issues:
            self.report({'WARNING'}, f"{len(parser.issues)} material issue(s), see system console.")

        return {'FINISHED'}
    


class PT_materials_panel(Panel):
    bl_label = "Materials"
    bl_idname = "GRILLE_PT_beamng_cdae_utilspanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BeamNG'

    def draw(self, context):
        layout = self.layout
        ui = UILayoutCtx(layout, UtilsSidepanel.properties_from_ctx(context))
        pinfo = UtilsPanelPInfo

        ui.prop(pinfo.matconv_version)
        ui.prop(pinfo.matconv_aclip)
        ui.prop(pinfo.matconv_force)
        ui.prop(pinfo.matconv_image_nodes)

        layout.separator()

        layout.operator(
            OT_convert_materials.bl_idname,
            text="Convert Materials",
            icon='MATERIAL'
        )





class UtilsSidepanel(PropertyInfoGroup[types.Scene]):
    pinfo = PropertyInfoFactory()

    classes = (
        UtilsPanelPropertyGroup,
        OT_convert_materials,
        PT_materials_panel,
    )

    utils_panel_properties = pinfo.ptr(UtilsPanelPropertyGroup, key="utils_panel_properties")


    @classmethod
    def properties_from_ctx(cls, ctx: types.Context):
        assert ctx.scene is not None
        return cls.utils_panel_properties[ctx.scene]


    @classmethod
    def register(cls, target = types.Scene):
        for rcls in cls.classes:
            bpy.utils.register_class(rcls)
        cls.pinfo.register(target)


    @classmethod
    def unregister(cls, target = types.Scene):
        for rcls in reversed(cls.classes):
            bpy.utils.unregister_class(rcls)
        cls.pinfo.unregister(target)