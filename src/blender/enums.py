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
    ReflectionEnabled = "Reflection Enabled"

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

    IsShadowRay = "Is Shadow Ray"
    Backfacing = "Backfacing"



class SocketIndex(IntEnum):
    MixFactor = 0
    MixFloatIn0 = 1
    MixFloatIn1 = 2
    MixFloatOut = 0
    MixColorIn0 = 6
    MixColorIn1 = 7
    MixColorOut = 2



class PrincipledSocketIndex(IntEnum):
    Emission_Color = 17
    Emission_Strength = 18



class SocketType(StrEnum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    Bool = "Bool"
    Float = "Float"
    Vector = "Vector"
    Color = "Color"
    Shader = "Shader"



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
    RGBA = 'RGBA'
    MIX = 'MIX'
    LINEAR_LIGHT = 'LINEAR_LIGHT'
    OVERLAY = 'OVERLAY'



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