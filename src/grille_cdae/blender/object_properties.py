from grille_cdae.common import *


class ObjectRole(StrEnum):

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



_pinfo = props.PropertyInfoFactory(types.Object)

class ObjectProperties:

    path = _pinfo.str("path", "Node Path", "base00.start01.obj", description="Node tree path inside the cdae file")
    role = _pinfo.enum("role", "Role", ObjectRole.Generic)
    lod_size = _pinfo.int("lod_size", "LOD Size (PX)")
    bb_flag0 = _pinfo.int("bb_flag0", "BB Dimension (PX)", 64)
    bb_dimension = _pinfo.int("bb_dimension", "BB Equator Steps", 16)
    bb_equator_steps = _pinfo.bool("bb_equator_steps", "BB Equator Steps")


    @staticmethod
    def has_mesh(obj: types.Object) -> bool:
        return obj.type == 'MESH'
    

    @staticmethod
    def register(): _pinfo.register()


    @staticmethod
    def unregister(): _pinfo.unregister()
