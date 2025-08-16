from enum import Enum

class MaterialFlags(int, Enum):

    S_WRAP = 1 << 0          
    T_WRAP = 1 << 1      
    TRANSLUCENT = 1 << 2 
    ADDITIVE = 1 << 3  
    SUBTRACTIVE = 1 << 4 
    SELF_ILLUMINATING = 1 << 5 
    NEVER_ENV_MAP = 1 << 6   
    NO_MIP_MAP = 1 << 7    
    MIP_MAP_ZERO_BORDER = 1 << 8 
    AUXILIARY_MAP = 1 << 0   


    @staticmethod
    def decode(flags: int) -> 'MaterialFlags':
        pass


    @staticmethod
    def encode(obj: 'MaterialFlags') -> int:
        pass



class MeshFlags(int, Enum):

    BILLBOARD = 1 << 31,
    HAS_DETAIL_TEXTURE = 1 << 30,
    BILLBOARD_Z_AXIS = 1 << 29,
    USE_ENCODED_NORMALS = 1 << 28,


    @staticmethod
    def decode(flags: int) -> 'MeshFlags':
        pass


    @staticmethod
    def encode(obj: 'MeshFlags') -> int:
        pass



