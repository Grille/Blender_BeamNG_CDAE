import bpy

from .blender_object_properties import ObjectProperties, ObjectRole


# Define the panel
class ObjectPanel(bpy.types.Panel):

    bl_label = "BeamNG cdae"
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

        obj = context.object
        has_mesh = ObjectProperties.has_mesh(obj)

        layout.prop(obj, ObjectProperties.ROLE)

        role = ObjectRole.from_obj(obj)
        if role == ObjectRole.Generic:
            layout.prop(obj, ObjectProperties.PATH)
            return
        
        uses_mesh = role.uses_mesh
        warnmsg = None
        if uses_mesh and not has_mesh:
            warnmsg = "Mesh missing, Object won't export."
        elif not uses_mesh and has_mesh:
            warnmsg = "Empty expected, Mesh will be ignored."

        if warnmsg is not None:
            row = layout.row()
            row.alert = True
            row.label(text=warnmsg, icon='ERROR')


        if role.uses_lod:
            layout.prop(obj, ObjectProperties.LOD_SIZE)

        if role == ObjectRole.Billboard:
            layout.prop(obj, ObjectProperties.BB_FLAG0, text="Lock XY Axis")

        if role == ObjectRole.AutoBillboard:
            layout.prop(obj, ObjectProperties.BB_DIMENSION)
            layout.prop(obj, ObjectProperties.BB_EQUATOR_STEPS)