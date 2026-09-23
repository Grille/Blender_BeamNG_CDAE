from grille_cdae.common import *

from .material_properties import *
from .material_operators import *



class MaterialPanel(basetypes.Panel):

    bl_label = "BeamNG CDAE"
    bl_idname = "MATERIAL_PT_beamng_cdae_matpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"


    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.material is not None


    def draw(self, context: bpy.types.Context):
        assert self.layout is not None

        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = True

        mat = context.material
        assert mat is not None

        gts = MaterialProperties.groundtype_select[mat]
        layout.prop(mat, MaterialProperties.groundtype_select.key)
        if gts == GROUNDMODEL_CUSTOM:
            layout.prop(mat, MaterialProperties.groundtype_custom.key)
            layout.separator()

        row = layout.row()
        args = row.operator(OT_CreateBeamNgMaterial.bl_idname, text="Setup V1.0")
        args.version = 1.0
        args = row.operator(OT_CreateBeamNgMaterial.bl_idname, text="Setup V1.5")
        args.version = 1.5