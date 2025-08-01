import bpy

from bpy.props import StringProperty


class ObjectProperties:

    CDAE_PATH = "grille_beamng_cdae_path"


    @staticmethod
    def register():
        def _set(key, property): setattr(bpy.types.Object, key, property)

        property = bpy.props.StringProperty(
            name="Tree Path",
            description="Node tree path inside the cdae file",
            default=""
        )
        _set(ObjectProperties.CDAE_PATH, property)
    

    @staticmethod
    def unregister():
        def _del(key): delattr(bpy.types.Object, key)
        
        _del(ObjectProperties.CDAE_PATH)