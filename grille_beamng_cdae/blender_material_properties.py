import bpy

from bpy.props import BoolProperty, EnumProperty, StringProperty


class MaterialProperties:

    VERSION = "grille_beamng_cdae_version"
    GROUND_TYPE = "grille_beamng_cdae_groundtype"
    UV1_HINT = "grille_beamng_cdae_uv1hint"


    @staticmethod
    def register():
        def _set(key, property): setattr(bpy.types.Material, key, property)

        _set(MaterialProperties.GROUND_TYPE, StringProperty(
            name="Ground Type",
            default=""
        ))

        _set(MaterialProperties.VERSION, EnumProperty(
            name="Version",
            items=[
                ("1.0", "V1",""),
                ("1.5", "V1.5 (PBR)", ""),
            ],
            default="1.0",
        ))

        _set(MaterialProperties.UV1_HINT, StringProperty(
            name="UV Map 1 Hint",
            default="1"
        ))


    @staticmethod
    def unregister():
        def _del(key): delattr(bpy.types.Material, key)
        
        _del(MaterialProperties.GROUND_TYPE)
        _del(MaterialProperties.VERSION)
        _del(MaterialProperties.UV1_HINT)