from grille_cdae.common import *
from grille_cdae.common.basetypes import Panel

from .uilayout import UILayoutCtx
from .object_properties import ObjectProperties, ObjectRole


class ObjectPanel(Panel):

    bl_label = "BeamNG CDAE"
    bl_idname = "OBJECT_PT_grille_beamng_cdae_objpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"


    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type in {'EMPTY', 'MESH'}


    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        obj = not_none(context.object)
        role = ObjectProperties.role[obj]
        uses_mesh = role.uses_mesh
        has_mesh = ObjectProperties.has_mesh(obj)
    
        ui = UILayoutCtx(layout, obj)

        ui.prop(ObjectProperties.role)

        if role == ObjectRole.Generic:
            ui.prop(ObjectProperties.path)
            return
        
        if uses_mesh and not has_mesh:
            ui.label_error("Mesh missing, Object won't export.")

        elif not uses_mesh and has_mesh:
            ui.label_error("Empty expected, Mesh will be ignored.")

        if role.uses_lod:
            ui.prop(ObjectProperties.lod_size)

        if role == ObjectRole.Billboard:
            ui.prop(ObjectProperties.bb_flag0, text="Lock XY Axis")

        if role == ObjectRole.AutoBillboard:
            ui.prop(ObjectProperties.bb_dimension)
            ui.prop(ObjectProperties.bb_equator_steps)