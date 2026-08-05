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
    MixFloatIn0 = 1
    MixFloatIn1 = 2
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
    Bool = "Bool"
    Float = "Float"
    Integer = "Integer"
    Vector = "Vector"
    Color = "Color"
    Shader = "Shader"
    Menu = "Menu"
    Bundle = "Bundle"
    Closure = "Closure"

    def to_data_type(self):
        if self == SocketType.Bool: return "BOOLEAN"
        return self.upper()



class Operation(StrEnum):
    SUBTRACT = 'SUBTRACT'
    MULTIPLY = 'MULTIPLY'
    ADD = 'ADD'
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