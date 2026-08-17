import math

from ..enums import *



class NodeName(StrEnum):
    ShaderNodeTree = "ShaderNodeTree"
    Group = "ShaderNodeGroup"
    GroupInput = "NodeGroupInput"
    GroupOutput = "NodeGroupOutput"
    OutputMaterial = "ShaderNodeOutputMaterial"
    BsdfPrincipled = "ShaderNodeBsdfPrincipled"
    BsdfDiffuse = "ShaderNodeBsdfDiffuse"
    BsdfMetallic = "ShaderNodeBsdfMetallic"
    BsdfTransparent = "ShaderNodeBsdfTransparent"
    Mix = "ShaderNodeMix"
    MixRGB = "ShaderNodeMixRGB"
    MixShader = "ShaderNodeMixShader"
    AddShader = "ShaderNodeAddShader"
    NormalMap = "ShaderNodeNormalMap"
    TexImage = "ShaderNodeTexImage"
    UVMap = "ShaderNodeUVMap"
    ShaderToRGB = "ShaderNodeShaderToRGB"
    SeparateColor = "ShaderNodeSeparateColor"
    SeperateXYZ = "SeperateXYZ"
    Math = "ShaderNodeMath"
    VectorMath = "ShaderNodeVectorMath"
    LightPath = "ShaderNodeLightPath"
    Geometry = "ShaderNodeNewGeometry"
    CombineXYZ = "ShaderNodeCombineXYZ"
    ColorAttribute = "ColorAttribute"
    SceneTime = "GeometryNodeInputSceneTime"

    RGB = "ShaderNodeRGB"
    Value = "ShaderNodeValue"

    CombineBundle = "NodeCombineBundle"
    SeparateBundle = "NodeSeparateBundle"

    ClosureInput = "NodeClosureInput"
    ClosureOutput = "NodeClosureOutput"
    EvaluateClosure = "NodeEvaluateClosure"



class SocketName(StrEnum):
    Color = "Color"
    ColorHDR = "Color HDR"
    BaseColor = "Base Color"
    VertexColor = "Vertex Color"
    VertexAlpha = "Vertex Alpha"
    InstanceColor = "Instance Color"
    Metallic = "Metallic"
    Roughness = "Roughness"
    Alpha = "Alpha"
    BaseAlpha = "Base Alpha"
    Normal = "Normal"
    NormalEnabled = "Normal Enabled"
    InvertBackfaceNormals = "Invert Backface Normals"
    ReflectionEnabled = "Reflection Enabled"
    SubsurfaceScattering = "Subsurface Scattering"

    DetailColor = "Detail Color"
    DetailNormal = "Detail Normal"
    AmbientOcclusion = "Ambient Occlusion"
    Palette = "Palette"
    Emissive = "Emissive"
    EmissiveVertexColor = "Emissive Vertex Color"
    ClearCoat = "Clear Coat"
    ClearCoatRoughness = "Clear Coat Roughness"

    EmissionColor = "Emission Color"
    EmissionStrength = "Emission Strength"
    EdgeTint = "Edge Tint"

    CoatWeight = "Coat Weight"
    CoatRoughness = "Coat Roughness"
    CoatNormal = "Coat Normal"

    BSDF = "BSDF"
    Shader = "Shader"
    BSDF_Alpha = "BSDF.Alpha"
    Shader_Alpha = "Shader.Alpha"
    Surface = "Surface"
    Closure = "Closure"

    IsShadowRay = "Is Shadow Ray"
    Backfacing = "Backfacing"

    BNGShader = "BNGS"
    TextureMap = "Texture Map"
    Factor = "Factor"
    UV = "UV"
    Data = "Data"
    Value = "Value"
    Epsilon = "Epsilon"
    Enabled = "Enabled"

    ThinWall = "Thin Wall"
    SubsurfaceWeight = "Subsurface Weight"
    SubsurfaceRadius = "Subsurface Radius"
    SubsurfaceScale = "Subsurface Scale"
    SubsurfaceIOR = "Subsurface IOR"
    SubsurfaceAnisotropy = "Subsurface Anisotropy"



class SocketShape(StrEnum):
    CIRCLE = 'CIRCLE' 
    SQUARE = 'SQUARE' 
    DIAMOND = 'DIAMOND' 
    CIRCLE_DOT = 'CIRCLE_DOT' 
    SQUARE_DOT = 'SQUARE_DOT' 
    DIAMOND_DOT = 'DIAMOND_DOT' 
    LINE = 'LINE'
    VOLUME_GRID = 'VOLUME_GRID'
    LIST = 'LIST'



class SocketIndex(IntEnum):
    MixFactor = 0
    MixFactorNU = 1
    MixFloatIn0 = 2
    MixFloatIn1 = 3
    MixFloatOut = 0
    MixVectorIn0 = 4
    MixVectorIn1 = 5
    MixVectorOut = 1
    MixColorIn0 = 6
    MixColorIn1 = 7
    MixColorOut = 2
    VecMathVecIn0 = 0
    VecMathVecIn1 = 1
    VecMathVecOut = 0
    VecMathFloatOut = 1



class PrincipledSocketIndex(IntEnum):
    Emission_Color = 17
    Emission_Strength = 18



class SocketIOType(StrEnum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class SocketType(StrEnum):
    Error = "Error"
    Bool = "Bool"
    Float = "Float"
    Integer = "Integer"
    Vector = "Vector"
    Color = "Color"
    Shader = "Shader"
    Menu = "Menu"
    Bundle = "Bundle"
    Closure = "Closure"

    @staticmethod
    def from_data_type(value):
        return _SOCKET_DATA_TYPE_INVERTED[value]

    @staticmethod
    def select_by_max_precedence(*types: 'SocketType'):

        length = len(types)
        if length < 1: return SocketType.Error
        type0 = types[0]
        if length == 1: return type0

        max_p = type0.precedence
        max_type = type0
        exclusive = max_p < 0
        all_equal = True

        for i in range(1, length):
            type = types[i]
            all_equal &= type0 == type

            p = type.precedence
            exclusive |= p < 0
            if p > max_p:
                max_p = p
                max_type = type

        if all_equal: return type0
        if exclusive: return SocketType.Error
        return max_type

    @property
    def full_name(self):
        return _SOCKET_FULL_NAME[self]
    
    @property
    def data_type(self):
        return _SOCKET_DATA_TYPE[self]

    @property
    def precedence(self):
        return _SOCKET_PRECEDENCE.get(self, -1)

    def simplify_value(self):
        return _SOCKET_SIMPLIFY_VALUE.get(self, self)
    
    def simplify_vector(self):
        return _SOCKET_SIMPLIFY_VECTOR.get(self, self)

    def simplify(self):
        return self.simplify_value().simplify_vector()
    
_SOCKET_FULL_NAME: dict[SocketType, str] = {}
_SOCKET_DATA_TYPE: dict[SocketType, str] = {}
_SOCKET_SIMPLIFY_VALUE = { 
    SocketType.Bool: SocketType.Float,
    SocketType.Float: SocketType.Float,
    SocketType.Integer: SocketType.Float,
}
_SOCKET_SIMPLIFY_VECTOR = { 
    SocketType.Vector: SocketType.Vector,
    SocketType.Color: SocketType.Vector,
}
_SOCKET_PRECEDENCE: dict[SocketType, int] = {
    SocketType.Bool: 0,
    SocketType.Integer: 1,
    SocketType.Float: 2,
    SocketType.Vector: 3,
    SocketType.Color: 4,
    SocketType.Shader: 5,
}

for key in SocketType:
    _SOCKET_FULL_NAME[key] = f"NodeSocket{key}"

    if key == SocketType.Bool: _SOCKET_DATA_TYPE[key] = "BOOLEAN"
    elif key == SocketType.Color: _SOCKET_DATA_TYPE[key] = "RGBA"
    else: _SOCKET_DATA_TYPE[key] = key.upper()

_SOCKET_DATA_TYPE_INVERTED = {value: key for key, value in _SOCKET_DATA_TYPE.items()}
_SOCKET_DATA_TYPE_INVERTED["VALUE"] = SocketType.Float



class SocketSubtype(StrEnum):
    FACTOR = "FACTOR"



class Operation(StrEnum):
    ADD = 'ADD'
    SUBTRACT = 'SUBTRACT'
    MULTIPLY = 'MULTIPLY'
    DIVIDE = 'DIVIDE'
    MULTIPLY_ADD = 'MULTIPLY_ADD'
    GREATER_THAN = 'GREATER_THAN'
    LESS_THAN = 'LESS_THAN'
    MINIMUM = 'MINIMUM'
    MAXIMUM = 'MAXIMUM'
    FLOAT = "FLOAT"
    VECTOR = "VECTOR"
    RGBA = 'RGBA'
    MIX = 'MIX'
    LINEAR_LIGHT = 'LINEAR_LIGHT'
    OVERLAY = 'OVERLAY'
    LENGTH = 'LENGTH'
    COMPARE = 'COMPARE'



class ColorSpace(StrEnum):
    SRGB = "sRGB"
    NON_COLOR = "Non-Color"


class OperatorResult(StrEnum):
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class GroupColorTag(StrEnum):
    NONE = "NONE"
    COLOR = "COLOR"
    CONVERTER = "CONVERTER"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    SCRIPT = "SCRIPT"
    SHADER = "SHADER"
    TEXTURE = "TEXTURE"
    VECTOR = "VECTOR"