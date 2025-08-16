import bpy

from enum import Enum
from bpy.props import StringProperty, EnumProperty, IntProperty, BoolProperty
from bpy.types import Object as BObj


class ObjectRole(str, Enum):

    Mesh = "Mesh"
    Collision = "Collision"
    Billboard = "Billboard"
    AutoBillboard = "AutoBillboard"
    NullDetail = "NullDetail"
    Generic = "Generic"


    @property
    def uses_lod(self):
        return self != ObjectRole.Collision
    

    @property
    def uses_mesh(self):
        return self not in (ObjectRole.AutoBillboard, ObjectRole.NullDetail)



class ObjectProperties(str, Enum):

    PREFIX = "grille_beamng_cdae_"
    PATH = f"{PREFIX}path"
    ROLE = f"{PREFIX}role"
    LOD_SIZE = f"{PREFIX}lod_size"
    BB_FLAG0 = f"{PREFIX}bb_flag0"
    BB_DIMENSION = f"{PREFIX}bb_dimension"
    BB_EQUATOR_STEPS = f"{PREFIX}bb_equator_steps"


    @staticmethod
    def has_mesh(obj: BObj) -> bool:
        return obj.type == 'MESH'
    

    @staticmethod
    def get_role(obj: BObj) -> ObjectRole:
        return ObjectRole(getattr(obj, ObjectProperties.ROLE))


    @staticmethod
    def get_lod(obj: BObj) -> int:
        return getattr(obj, ObjectProperties.LOD_SIZE)
    

    @staticmethod
    def register():
        def _set(key, property): setattr(bpy.types.Object, key, property)

        _set(ObjectProperties.PATH, bpy.props.StringProperty(
            name="Node Path",
            description="Node tree path inside the cdae file",
            default="base00.start01.obj"
        ))

        _set(ObjectProperties.ROLE, EnumProperty(
            name="Role",
            items=[
                (ObjectRole.Mesh, "Mesh", ""),
                (ObjectRole.Collision, "Collision", ""),
                (ObjectRole.Billboard, "Billboard", ""),
                (ObjectRole.AutoBillboard, "AutoBillboard", ""),
                (ObjectRole.NullDetail, "NullDetail", ""),
                (ObjectRole.Generic, "Generic", ""),
            ],
            default=ObjectRole.Mesh,
        ))

        _set(ObjectProperties.LOD_SIZE, IntProperty(
            name="LOD Size (PX)", 
            default=0,
        ))

        _set(ObjectProperties.BB_DIMENSION, IntProperty(
            name="BB Dimension (PX)", 
            default=64,
        ))

        _set(ObjectProperties.BB_EQUATOR_STEPS, IntProperty(
            name="BB Equator Steps", 
            default=16,
        ))

        _set(ObjectProperties.BB_FLAG0, BoolProperty(
            name="BB Equator Steps", 
            default=False,
        ))
    

    @staticmethod
    def unregister():
        def _del(key): delattr(bpy.types.Object, key)
        
        _del(ObjectProperties.PATH)