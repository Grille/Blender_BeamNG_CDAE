import bpy

from enum import Enum
from bpy.props import BoolProperty, EnumProperty, StringProperty


GROUNDMODEL_CUSTOM = "<Custom>"
GROUNDMODELS = [
  "ASPHALT",
  "ASPHALT_WET",
  "ASPHALT_OLD",
  "ASPHALT_PREPPED",
  "RUMBLE_STRIP",
  "ROCK",
  "COBBLESTONE",
  "METAL",
  "METAL_TREAD",
  "WOOD",
  "PLASTIC",
  "DIRT",
  "DIRT_DUSTY",
  "DIRT_DUSTY_LOOSE",
  "GRAVEL",
  "GRAVEL_WET",
  "GRASS",
  "MUD",
  "SAND",
  "ICE",
  "FRICTIONLESS",
  "SPIKE_STRIP",
  "SNOW",
  "SLIPPERY",
  "KICKPLATE",
  "SHOCK_ABSORBER",
  "BRANCHES_STRONG",
  "LEAVES_STRONG",
  "LEAVES_THIN",
  "SOFT_COLLISION_GENERAL",
  "VOID",
  GROUNDMODEL_CUSTOM,
]



class MaterialProperties(str, Enum):

    PREFIX = "grille_beamng_cdae_"
    VERSION = f"{PREFIX}version"
    GROUND_TYPE = f"{PREFIX}groundtype"
    GROUND_TYPE_SELECT = f"{PREFIX}groundtype_select"
    UV1_HINT = f"{PREFIX}uv1hint"


    @staticmethod
    def get_ground_type(bmat: bpy.types.Material):
        value = getattr(bmat, MaterialProperties.GROUND_TYPE_SELECT)
        if value == GROUNDMODEL_CUSTOM:
            return getattr(bmat, MaterialProperties.GROUND_TYPE)
        return value
    

    @staticmethod
    def get_version(bmat: bpy.types.Material):
        return float(getattr(bmat, MaterialProperties.VERSION))


    @staticmethod
    def register():
        def _set(key, property): setattr(bpy.types.Material, key, property)

        groundmodels_items = [(item, item, "") for item in GROUNDMODELS]

        _set(MaterialProperties.GROUND_TYPE_SELECT, EnumProperty(
            name="Ground Type",
            items=groundmodels_items,
            default=GROUNDMODELS[0],
        ))

        _set(MaterialProperties.GROUND_TYPE, StringProperty(
            name="",
            default=""
        ))


    @staticmethod
    def unregister():
        def _del(key): delattr(bpy.types.Material, key)
        
        _del(MaterialProperties.GROUND_TYPE_SELECT)
        _del(MaterialProperties.GROUND_TYPE)