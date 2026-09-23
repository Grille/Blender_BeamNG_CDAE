from grille_cdae.common import *


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


_pinfo = props.PropertyInfoFactory(types.Material)

class MaterialProperties:

    groundtype_custom = _pinfo.str("groundtype_custom", "", "")
    groundtype_select = _pinfo.enum("groundtype_select", "Ground Type", GROUNDMODEL_CUSTOM, GROUNDMODELS)


    @staticmethod
    def get_ground_type(bmat: bpy.types.Material):
        value = MaterialProperties.groundtype_select[bmat]
        if value == GROUNDMODEL_CUSTOM:
            return MaterialProperties.groundtype_custom[bmat]
        return value
    

    @staticmethod
    def register():
        _pinfo.register()


    @staticmethod
    def unregister():
        _pinfo.unregister()