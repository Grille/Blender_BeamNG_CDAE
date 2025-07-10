import bpy

from .blender_object_properties import ObjectProperties


# Define the panel
class ObjectPanel(bpy.types.Panel):
    bl_label = "BeamNG cdae"
    bl_idname = "OBJECT_PT_grille_beamng_cdae_objpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.prop(obj, ObjectProperties.CDAE_PATH)