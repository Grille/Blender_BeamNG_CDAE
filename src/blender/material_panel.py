import bpy

from .material_properties import *
from .material_operators import *

# pyright: reportInvalidTypeForm=false


class MaterialPanel(bpy.types.Panel):

    bl_label = "BeamNG CDAE"
    bl_idname = "MATERIAL_PT_beamng_cdae_matpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"


    @classmethod
    def poll(cls, context):
        return context.material is not None


    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = True

        mat = context.material

        gts = getattr(mat, MaterialProperties.GROUND_TYPE_SELECT)
        layout.prop(mat, MaterialProperties.GROUND_TYPE_SELECT)
        if gts == GROUNDMODEL_CUSTOM:
            layout.prop(mat, MaterialProperties.GROUND_TYPE)
            layout.separator()

        row = layout.row()
        args = row.operator(OT_CreateBeamNgMaterial.bl_idname, text="Setup V1.0")
        args.version = 1.0
        args = row.operator(OT_CreateBeamNgMaterial.bl_idname, text="Setup V1.5")
        args.version = 1.5