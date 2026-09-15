import os

from typing import cast

from ..numerics import *
from ...blender.enums import *



type Tuple4 = tuple[float, float, float, float]
type Tuple3 = tuple[float, float, float]
type Tuple2 = tuple[float, float]



class _BaseDict:
    __slots__ = "value_dict"

    def __init__(self, dict: dict[str, object], **kwargs: object):
        self.value_dict = dict


    def get_key(self, key: str) -> str | None: return key


    def new[T: '_BaseDict'](self, type: type[T], **kwargs: object):
        return type(self.value_dict, **kwargs)



class _KeyPtrDict(_BaseDict):
    __slots__ = "_key_dict"

    def __init__(self, dict: dict[str, object], **kwargs: str):
        super().__init__(dict)
        self._key_dict = kwargs


    def get_key(self, key: str): return self._key_dict.get(key, key)



class DictProperty[T]():
    __slots__ = "key", "default"

    def __init__(self, key: str, default: T | None = None):
        self.key = key
        self.default = default


    def _get_full_key(self, instance: _BaseDict):
        return instance.get_key(self.key)


    def __get__(self, instance: _BaseDict, owner: object) -> T | None:
        key = self._get_full_key(instance)
        if key is None: return None
        return cast(T, instance.value_dict.get(key, self.default))


    def __set__(self, instance: _BaseDict, value: T | None):
        key = self._get_full_key(instance)
        if key is None: raise KeyError(f"{self.key} not valid in this context")
        if value is None or value == self.default:
            instance.value_dict.pop(key, None)
        else:
            instance.value_dict[key] = value



class _TextureSocket(_KeyPtrDict):
    map = DictProperty[str]("map")
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

class _TexColorSocket[T](_TextureSocket):
    factor = DictProperty[T]("value")
    vertex_enabled = DictProperty[bool]("vertex")
    instance_enabled = DictProperty[bool]("instance")

class _TexEmissiveSocket(_TexColorSocket[Tuple3]):
    intensity_nits = DictProperty[float]("emissiveIntensityNits")

class _TexSpecularSocket(_TextureSocket):
    enabled = DictProperty[bool]("pixelSpecular")
    factor = DictProperty[Tuple4]("specular")
    roughness = DictProperty[float]("roughnessFactor")

class _TexCCSocket(_TexFactorSocket):
    roughness = DictProperty[float]("clearCoatRoughnessFactor")


class AnimationFlags(IntEnum):
    ROTATION = 2
    SCROLL = 1
    WAVE = 4
    SCALE = 8
    SEQUENCE = 16



class AnimationWaveType(StrEnum):
    SIN = "Sin"
    SQUARE = "Square"
    TRIANGLE = "Triangle"



class MaterialStage(_BaseDict):

    class _Detail(_BaseDict):

        scale = DictProperty[Tuple2]("detailScale")

        def __init__(self, parent: 'MaterialStage'):
            super().__init__(parent.value_dict) 

            def new(map: str, value: str, uv: str | None):
                return parent.new_socket(_TexStrengthSocket, map=map, value=value, uv=uv)

            self.color = new("detailMap", "detailBaseColorMapStrength", "detailMapUseUV")
            self.normal = new("detailNormalMap", "detailNormalMapStrength", "normalDetailMapUseUV")
            self.metallic = new("metallicDetailMap", "detailMetallicMapStrength", None)
            self.roughness = new("roughnessDetailMap", "detailRoughnessMapStrength", None)
            self.opacity = new("opacityDetailMap", "detailOpacityMapStrength", "opacityDetailMapUseUV")
            self.ambient_occlusion = new("ambientOcclusionDetailMap", "detailAoMapStrength", None)

    class _RetroReflective(_BaseDict):
        factor = DictProperty[float]("retroreflectivity")
        color = DictProperty[Tuple3]("retroreflectiveColor")

    class _LegacyLight(_BaseDict):
        emissive_enabled = DictProperty[bool]("emissive")
        emissive_color = DictProperty[Tuple3]("emissiveFactor")
        emissive_intensity_nits = DictProperty[float]("emissiveIntensityNits")
        glow_enabled = DictProperty[bool]("glow")
        glow_color = DictProperty[Tuple3]("glowFactor")
        vert_lit = DictProperty[bool]("vertLit")
        minnaert_constant = DictProperty[float]("minnaertConstant")

    class _Animation(_BaseDict):
        flags = DictProperty[AnimationFlags]("animFlags")
        scroll_speed = DictProperty[float]("scrollSpeed")
        scroll_direction = DictProperty[Tuple2]("scrollDir")
        rot_speed = DictProperty[float]("rotSpeed")
        rot_pivot_offset = DictProperty[Tuple2]("rotPivotOffset")
        seq_frames_per_sec = DictProperty[float]("sequenceFramePerSec")
        seq_segment_size = DictProperty[float]("sequenceSegmentSize")
        wave_amp = DictProperty[float]("waveAmp")
        wave_freq = DictProperty[float]("waveFreq")
        wave_type = DictProperty[AnimationWaveType]("waveType")

    use_anisotropic = DictProperty[bool]("useAnisotropic")


    def __init__(self, dict: dict[str, object]):
        super().__init__(dict)

        self._sockets: list[_TextureSocket] = []
        self.detail = MaterialStage._Detail(self)
        self.retro_reflectivity = self.new(MaterialStage._RetroReflective)
        self.legacy_light = self.new(MaterialStage._LegacyLight)
        self.animation = self.new(MaterialStage._Animation)

        def newvs[T:_TextureSocket](map: str, value: str | None, uv: str | None, type: type[T] = _TexFactorSocket, **kwargs: object):
            return self.new_socket(type, map=map, value=value, uv=uv, **kwargs)

        def newcs[T:_TextureSocket](map: str, value: str, uv: str, instance: str, vertex: str, type: type[T] = _TexColorSocket[Tuple4]):
            return newvs(map, value, uv, type, instance=instance, vertex=vertex)

        def newos(map: str, value: str, uv: str, instance: str):
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


    def new_socket[T:_TextureSocket](self, type: type[T], **kwargs: object):
        socket = self.new(type, **kwargs)
        self._sockets.append(socket)
        return socket

    
    def add_texture_names_to(self, target: set[str]):
        for socket in self._sockets:
            if socket.map is not None: target.add(socket.map)


    def add_relpath(self, relpath: str):
        for socket in self._sockets:
            if socket.map is not None and relpath != ".":
                socket.map = os.path.join(relpath, socket.map)



class MaterialVersion(FloatEnum):
    NONE = 0.0
    V1 = 1.0
    V1_5 = 1.5



type _RawStages = list[dict[str, object]]



class Material(_BaseDict):

    class _Translucent(_BaseDict):
        enabled = DictProperty[bool]("translucent")
        blend_mode = DictProperty[AlphaBlendMode]("translucentBlendOp")
        zwrite = DictProperty[bool]("translucentZWrite")
        recv_shadows = DictProperty[bool]("translucentRecvShadows")

    class _Subsurface(_BaseDict):
        enabled = DictProperty[bool]("subSurface")
        intensity = DictProperty[float]("subSurfaceIntensity")

    _raw_stages = DictProperty[_RawStages]("Stages")

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
            self._raw_stages = cast(_RawStages, [{},{},{},{}])

        raw_stages = self._raw_stages
        while len(raw_stages) < 4: raw_stages.append({})

        self.stages = [MaterialStage(raw_stages[0]), MaterialStage(raw_stages[1]), MaterialStage(raw_stages[2]), MaterialStage(raw_stages[3])]

        self.translucent = Material._Translucent(self.value_dict)
        self.subsurface = Material._Subsurface(self.value_dict)


    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)


    def add_relpath(self, relpath: str):
        for stage in self.stages:
            stage.add_relpath(relpath)