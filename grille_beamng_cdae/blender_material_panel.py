import bpy

from .blender_material_properties import *

# pyright: reportInvalidTypeForm=false


class MaterialPanel(bpy.types.Panel):

    bl_label = "BeamNG cdae"
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

        layout.prop(mat, MaterialProperties.VERSION)
        gts = getattr(mat, MaterialProperties.GROUND_TYPE_SELECT)
        layout.prop(mat, MaterialProperties.GROUND_TYPE_SELECT)
        if gts == GROUNDMODEL_CUSTOM:
            layout.prop(mat, MaterialProperties.GROUND_TYPE)
            layout.separator()
        layout.prop(mat, MaterialProperties.UV1_HINT)