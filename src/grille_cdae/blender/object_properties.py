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



class ObjectProperties(PropertyInfoGroup[types.Object]):
    pinfo = PropertyInfoFactory(types.Object)

    path = pinfo.str("Node Path", "base00.start01.obj", description="Node tree path inside the cdae file")
    role = pinfo.enum("Role", items=ObjectRole, default=ObjectRole.Generic)
    lod_size = pinfo.int("LOD Size (PX)")
    bb_flag0 = pinfo.int("BB Dimension (PX)", 64)
    bb_dimension = pinfo.int("BB Equator Steps", 16)
    bb_equator_steps = pinfo.bool("BB Equator Steps")

    @staticmethod
    def has_mesh(obj: types.Object): return obj.type == 'MESH'
