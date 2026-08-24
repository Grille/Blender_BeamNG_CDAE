import os

from typing import TypeVar, Generic

from ..numerics import *
from ...blender.enums import *


TDICT = TypeVar('TDICT', bound='_BaseDict')

class _BaseDict:

    def __init__(self, dict: dict[str], **kwargs):
        self._dict = dict


    def get_key(self, key: str) -> str | None: return key


    def new(self, type: type[TDICT], **kwargs):
        return type(self._dict, **kwargs)



class _KeyPtrDict(_BaseDict):

    def __init__(self, dict: dict[str], **kwargs: str):
        super().__init__(dict)
        self._key_dict = kwargs


    def get_key(self, key: str): return self._key_dict.get(key, key)



T = TypeVar('T')
class DictProperty(Generic[T]):

    def __init__(self, key: str, use_prefix = True):
        self.key = key
        self.use_prefix = use_prefix


    def _get_full_key(self, instance: _BaseDict):
        return instance.get_key(self.key)


    def __get__(self, instance: _BaseDict, owner) -> T | None:
        key = self._get_full_key(instance)
        if key is None: return None
        return instance._dict.get(self._get_full_key(instance), None)


    def __set__(self, instance: _BaseDict, value: T | None):
        key = self._get_full_key(instance)
        if key is None: raise KeyError(f"{self.key} not valid in this context")
        if value is None:
            instance._dict.pop(key, None)
        else:
            instance._dict[key] = value



class _TextureSocket(_KeyPtrDict):
    map = DictProperty[float]("map")
    uv = DictProperty[int]("uv")

class _TexStrengthSocket(_TextureSocket):
    strength = DictProperty[float]("value")

class _TexFactorSocket(_TextureSocket):
    factor = DictProperty[float]("value")

class _TexOpacitySocket(_TexFactorSocket):
    instance_enabled = DictProperty[bool]("instance")

class _TexPaletteSocket(_TextureSocket):
    color = DictProperty[bool]("paletteBaseColor")
    metallic = DictProperty[bool]("paletteMetallic")
    roughness = DictProperty[bool]("paletteRoughness")
    clear_coat = DictProperty[bool]("paletteClearCoat")
    clear_coat_roughness = DictProperty[bool]("paletteClearCoatRoughness")

class _TexColorSocket(_TextureSocket):
    factor = DictProperty[list[float]]("value")
    vertex_enabled = DictProperty[bool]("vertex")
    instance_enabled = DictProperty[bool]("instance")

class _TexEmissiveSocket(_TexColorSocket):
    intensity_nits = DictProperty[float]("emissiveIntensityNits")

class _TexSpecularSocket(_TextureSocket):
    enabled = DictProperty[bool]("pixelSpecular")
    factor = DictProperty[list[float]]("specular")
    roughness = DictProperty[float]("roughnessFactor")

class _TexCCSocket(_TexFactorSocket):
    roughness = DictProperty[float]("clearCoatRoughnessFactor")



class Stage(_BaseDict):

    class _Detail(_BaseDict):

        scale = DictProperty[list[float]]("detailScale")

        def __init__(self, parent: Stage):
            super().__init__(parent._dict) 

            def new(map, value, uv):
                return parent.new_socket(_TexStrengthSocket, map=map, value=value, uv=uv)

            self.color = new("detailMap", "detailBaseColorMapStrength", "detailMapUseUV")
            self.normal = new("detailNormalMap", "detailNormalMapStrength", "normalDetailMapUseUV")
            self.metallic = new("metallicDetailMap", "detailMetallicMapStrength", None)
            self.roughness = new("roughnessDetailMap", "detailRoughnessMapStrength", None)
            self.opacity = new("opacityDetailMap", "detailOpacityMapStrength", "opacityDetailMapUseUV")
            self.ambient_occlusion = new("ambientOcclusionDetailMap", "detailAoMapStrength", None)

    class _RetroReflective(_BaseDict):
        factor = DictProperty[float]("retroreflectivity")
        color = DictProperty[list[float]]("retroreflectiveColor")

    class _LegacyLight(_BaseDict):
        emissive_enabled = DictProperty[bool]("emissive")
        emissive_color = DictProperty[list[float]]("emissiveFactor")
        emissive_intensity_nits = DictProperty[float]("emissiveIntensityNits")
        glow_enabled = DictProperty[bool]("glow")
        glow_color = DictProperty[list[float]]("glowFactor")
        vert_lit = DictProperty[bool]("vertLit")
        minnaert_constant = DictProperty[float]("minnaertConstant")

    use_anisotropic = DictProperty[bool]("useAnisotropic")


    def __init__(self, dict: dict[str] | None):
        super().__init__(dict)

        self._sockets: list[_TextureSocket] = []
        self.detail = Stage._Detail(self)
        self.retro_reflectivity = self.new(Stage._RetroReflective)
        self.legacy_light = self.new(Stage._LegacyLight)

        def newvs(map, value, uv, type: type[TDICT] = _TexFactorSocket, **kwargs):
            return self.new_socket(type, map=map, value=value, uv=uv, **kwargs)

        def newcs(map, value, uv, instance, vertex, type: type[TDICT] = _TexColorSocket):
            return newvs(map, value, uv, type, instance=instance, vertex=vertex)

        def newos(map, value, uv, instance):
            return self.new_socket(_TexOpacitySocket, map=map, value=value, uv=uv, instance=instance)
        
        self.color = newcs("baseColorMap", "baseColorFactor", "diffuseMapUseUV", "instanceDiffuse", "vertColor")
        self.normal = newvs("normalMap", "normalMapStrength", "normalMapUseUV", _TexStrengthSocket)
        self.specular = newvs("specularMap", None, None, _TexSpecularSocket)
        self.metallic = newvs("metallicMap", "metallicFactor", "metallicMapUseUV")
        self.roughness = newvs("roughnessMap", "roughnessFactor", "roughnessMapUseUV")
        self.opacity = newos("opacityMap", "opacityFactor", "opacityMapUseUV", "instanceOpacity")
        self.ambient_occlusion = newvs("ambientOcclusionMap", None, "ambientOcclusionMapUseUV", _TextureSocket)
        self.emission = newcs("emissiveMap", "emissiveFactor", "emissiveMapUseUV", "instanceEmissive", "vertColorEmissive", _TexEmissiveSocket)
        self.palette = newvs("colorPaletteMap", None, "colorPaletteMapUseUV", _TexPaletteSocket)
        self.reflectivity = newvs("reflectivityMap", "reflectivityMapFactor", None)
        self.overlay = newvs("overlayMap", None, None, _TextureSocket)
        self.clear_coat = newvs("clearCoatMap", "clearCoatFactor", "clearCoatMapUseUV", _TexCCSocket)
        self.clear_coat_normal = newvs("clearCoatBottomNormalMap", "clearCoatBottomNormalMapStrength", None, _TexStrengthSocket)


    def new_socket(self, type: type[TDICT], **kwargs):
        socket = self.new(type, **kwargs)
        self._sockets.append(socket)
        return socket

    
    def add_texture_names_to(self, target: set[str]):
        for socket in self._sockets:
            if socket.map is not None: target.add(socket.map)


    def add_relpath(self, relpath):
        for socket in self._sockets:
            if socket.map is not None and relpath != ".":
                socket.map = os.path.join(relpath, socket.map)



class MaterialVersion(FloatEnum):
    NONE = 0.0
    V1 = 1.0
    V1_5 = 1.5



class Material(_BaseDict):

    class _Translucent(_BaseDict):
        enabled = DictProperty[bool]("translucent")
        blend_mode = DictProperty[AlphaBlendMode]("translucentBlendOp")
        zwrite = DictProperty[bool]("translucentZWrite")
        recv_shadows = DictProperty[bool]("translucentRecvShadows")

    class _Subsurface(_BaseDict):
        enabled = DictProperty[bool]("subSurface")
        intensity = DictProperty[float]("subSurfaceIntensity")

    _raw_stages = DictProperty[dict[str]]("Stages")

    name = DictProperty[str]("name")
    class_name = DictProperty[str]("class")
    ground_type = DictProperty[str]("groundType")
    map_to = DictProperty[str]("mapTo")

    version = DictProperty[MaterialVersion]("version")
    active_layers = DictProperty[int]("activeLayers")
    
    alpha_test = DictProperty[bool]("alphaTest")
    alpha_ref = DictProperty[int]("alphaRef")
    double_sided = DictProperty[bool]("doubleSided")
    invert_backface_normals = DictProperty[bool]("invertBackFaceNormals")
    cast_shadows = DictProperty[bool]("castShadows")
    dynamic_cubemap = DictProperty[bool]("dynamicCubemap")
    cubemap = DictProperty[str]("cubemap")


    def __init__(self, dict, **kwargs):
        super().__init__(dict, **kwargs)

        if self._raw_stages is None:
            self._raw_stages = [{},{},{},{}]

        raw_stages = self._raw_stages
        while len(raw_stages) < 4: raw_stages.append({})

        self.stages = [Stage(raw_stages[0]), Stage(raw_stages[1]), Stage(raw_stages[2]), Stage(raw_stages[3])]

        self.translucent = Material._Translucent(self._dict)
        self.subsurface = Material._Subsurface(self._dict)


    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)


    def add_relpath(self, relpath):
        for stage in self.stages:
            stage.add_relpath(relpath)