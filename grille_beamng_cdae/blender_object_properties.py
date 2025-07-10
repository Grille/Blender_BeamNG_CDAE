import bpy

from bpy.props import StringProperty


class ObjectProperties:

    CDAE_PATH = "grille_beamng_cdae_path"


    @staticmethod
    def register():

        property = bpy.props.StringProperty(
            name="Tree Path",
            description="Node tree path inside the cdae file",
            default=""
        )
        setattr(bpy.types.Object, ObjectProperties.CDAE_PATH, property)
    

    @staticmethod
    def unregister():

        delattr(bpy.types.Object, ObjectProperties.CDAE_PATH)