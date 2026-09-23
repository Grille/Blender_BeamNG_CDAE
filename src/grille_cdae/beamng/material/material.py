from __future__ import annotations

from grille_cdae.common import *
from grille_cdae.enums import *

import grille_cdae.beamng.material.material_socket_info as _SI



type _nstr = str | None



class _BaseDict:
    __slots__ = "value_dict"

    def __init__(self, dict: SDict | _BaseDict):
        self.value_dict = dict.value_dict if isinstance(dict, _BaseDict) else dict


    def get_key(self, key: str) -> str: return key


    def __getitem__(self, key: str):
        return self.value_dict.get(self.get_key(key))


    def __setitem__(self, key: str, value: object | None):
        full_key = self.get_key(key)
        if value is None:
            self.value_dict.pop(full_key)
        else:
            self.value_dict[full_key] = value


    def pop(self, key: str):
        return self.value_dict.pop(self.get_key(key))



class _KeyPtrDict(_BaseDict):
    __slots__ = "_key_dict"

    def __init__(self, dict: SDict | _BaseDict, key_dict: SDict[str | None]):
        super().__init__(dict)
        self._key_dict = key_dict


    def get_key(self, key: str): 
        real_key = self._key_dict.get(key, key)
        if real_key is None: raise KeyError(f"{key} not valid in this context")
        return real_key



class DictProperty[T=object|None]:
    __slots__ = "key", "default"

    def __init__(self, key: str, default: T):
        self.key = key
        self.default = default


    def _convert_in(self, value: T) -> object: 
        return value


    def _convert_out(self, value: object) -> T:
        return cast(T, value)


    def __get__(self, instance: _BaseDict, owner: object) -> T:
        value = instance[self.key]
        if value is None: return self.default
        return self._convert_out(value)


    def __set__(self, instance: _BaseDict, value: T | None):
        if value is None or value == self.default: 
            instance.pop(self.key)
        else:
            instance[self.key] = self._convert_in(value)



class _Converter[T](DictProperty[T]):
    __slots__="converter"
    def __init__(self, key: str, default: T, converter: Callable[[Any], T]):
        super().__init__(key, default)
        self.converter = converter
    def _convert_out(self, value): return self.converter(value)



class _NStr(DictProperty[_nstr]):
    __slots__=()
    def __init__(self, key: str, default = None): super().__init__(key, default)



class _Str[T:str](_Converter[T]):
    __slots__=()
    def __init__(self, key: str, default: T, converter = str): super().__init__(key, default, converter)
    def _convert_in(self, value): return str(value)



class _Bool(DictProperty[bool]):
    __slots__=()
    def _convert_in(self, value): return bool(value)
    def _convert_out(self, value): return bool(value)


class _Float[T:float](_Converter[T]):
    __slots__=()
    def __init__(self, key: str, default: T, converter = float): super().__init__(key, default, converter)
    def _convert_in(self, value): return float(value)


class _Int[T:int](_Converter[T]):
    __slots__=()
    def __init__(self, key: str, default: T, converter = int): super().__init__(key, default, converter)
    def _convert_in(self, value): return int(value)


class _Vec2(DictProperty[Vec2F]):
    __slots__=()
    def _convert_in(self, value): return value
    def _convert_out(self, value): return Vec2F.from_obj(value)


class _Color3(DictProperty[Color4F]):
    __slots__=()
    def _convert_in(self, value): return value[:3]
    def _convert_out(self, value): return Color4F.from_obj(value)


class _Color4(DictProperty[Color4F]):
    __slots__=()
    def _convert_in(self, value): return value
    def _convert_out(self, value): return Color4F.from_obj(value)



class _TextureSocket(_KeyPtrDict):
    __slots__=()
    map = _Str("map", "")
    uv = _Int("uv", 0)

class _TexStrengthSocket(_TextureSocket):
    __slots__=()
    strength = _Float("value", 1.0)

class _TexFactorSocket(_TextureSocket):
    __slots__=()
    factor = _Float("value", -1)

class _TexOpacitySocket(_TexFactorSocket):
    __slots__=()
    instance_enabled = _Bool("instance", False)

class _TexPaletteSocket(_TextureSocket):
    __slots__=()
    color = _Bool("paletteBaseColor", True)
    metallic = _Bool("paletteMetallic", True)
    roughness = _Bool("paletteRoughness", True)
    clear_coat = _Bool("paletteClearCoat", True)
    clear_coat_roughness = _Bool("paletteClearCoatRoughness", True)

class _TexColorSocket(_TextureSocket):
    __slots__=()
    factor = _Color4("value", Color4F.WHITE)
    vertex_enabled = _Bool("vertex", False)
    instance_enabled = _Bool("instance", False)

class _TexEmissiveSocket(_TextureSocket):
    __slots__=()
    factor = _Color4("value", Color4F.BLACK)
    vertex_enabled = _Bool("vertex", False)
    instance_enabled = _Bool("instance", False)
    intensity_nits = _Float("emissiveIntensityNits", -1.0)

class _TexSpecularSocket(_TextureSocket):
    __slots__=()
    enabled = _Bool("pixelSpecular", False)
    factor = _Color4("specular", Color4F.WHITE)
    roughness = _Float("roughnessFactor", 1.0)

class _TexCCSocket(_TexFactorSocket):
    __slots__=()
    roughness = _Float("clearCoatRoughnessFactor", 1.0)



class AnimationFlags(IntFlag):
    NONE = 0
    ROTATION = 2
    SCROLL = 1
    WAVE = 4
    SCALE = 8
    SEQUENCE = 16



class AnimationWaveType(StrEnum):
    SIN = "Sin"
    SQUARE = "Square"
    TRIANGLE = "Triangle"



_DEFAULT_DETAIL_SCALE = Vec2F(2.0, 2.0)


class MaterialStage(_BaseDict):

    class _Detail(_BaseDict):
        scale = _Vec2("detailScale", _DEFAULT_DETAIL_SCALE)
        def __init__(self, parent: MaterialStage):
            super().__init__(parent) 
            self.color = _TexStrengthSocket(self, _SI.DETAIL_COLOR)
            self.normal = _TexStrengthSocket(self, _SI.DETAIL_NORMAL)
            self.metallic = _TexStrengthSocket(self, _SI.DETAIL_METALIC)
            self.roughness = _TexStrengthSocket(self, _SI.DETAIL_ROUGHNES)
            self.opacity = _TexStrengthSocket(self, _SI.DETAIL_OPACITY)
            self.ambient_occlusion = _TexStrengthSocket(self, _SI.DETAIL_AMBIENT_OCCLUSION)

    class _RetroReflective(_BaseDict):
        factor = _Float("retroreflectivity", 0.0)
        color = _Color3("retroreflectiveColor", Color4F.BLACK)

    class _LegacyLight(_BaseDict):
        emissive_enabled = _Bool("emissive", False)
        emissive_color = _Color3("emissiveFactor", Color4F.BLACK)
        emissive_intensity_nits = _Float("emissiveIntensityNits", -1.0)
        glow_enabled = _Bool("glow", False)
        glow_color = _Color3("glowFactor", Color4F.WHITE)
        vert_lit = _Bool("vertLit", False)
        minnaert_constant = _Float("minnaertConstant", -1.0)

    class _Animation(_BaseDict):
        flags = _Int("animFlags", AnimationFlags.NONE, AnimationFlags)
        scroll_speed = _Float("scrollSpeed", 0.0)
        scroll_direction = _Vec2("scrollDir", Vec2F.ZERO)
        rot_speed = _Float("rotSpeed", 0.0)
        rot_pivot_offset = _Vec2("rotPivotOffset", Vec2F.ZERO)
        seq_frames_per_sec = _Float("sequenceFramePerSec", 0.0)
        seq_segment_size = _Float("sequenceSegmentSize", 0.0)
        wave_amp = _Float("waveAmp", 0.0)
        wave_freq = _Float("waveFreq", 0.0)
        wave_type = _Str("waveType", AnimationWaveType.SIN, AnimationWaveType)

    use_anisotropic = _Bool("useAnisotropic", True)


    def __init__(self, dict: SDict):
        super().__init__(dict)

        self.detail = MaterialStage._Detail(self)
        self.retro_reflectivity = MaterialStage._RetroReflective(self)
        self.legacy_light = MaterialStage._LegacyLight(self)
        self.animation = MaterialStage._Animation(self)

        self.color = _TexColorSocket(self, _SI.COLOR)
        self.normal = _TexStrengthSocket(self, _SI.NORMAL)
        self.specular = _TexSpecularSocket(self, _SI.SPECULAR)
        self.metallic = _TexFactorSocket(self, _SI.METALLIC)
        self.roughness = _TexFactorSocket(self, _SI.ROUGHNESS)
        self.opacity = _TexOpacitySocket(self, _SI.OPACITY)
        self.ambient_occlusion = _TextureSocket(self, _SI.AMBIENT_OCCLUSION)
        self.emission = _TexEmissiveSocket(self, _SI.EMISSION)
        self.palette = _TexPaletteSocket(self, _SI.PALETTE)
        self.reflectivity = _TexFactorSocket(self, _SI.REFLECTIVITY)
        self.overlay = _TextureSocket(self, _SI.OVERLAY)
        self.clear_coat = _TexCCSocket(self, _SI.CLEAR_COAT)
        self.clear_coat_normal = _TexStrengthSocket(self, _SI.CLEAR_COAT_NORMAL)


    def enumerate_used_maps(self):
        for key in _SI.MAP_KEYS:
            value = self[key]
            if isinstance(value, str) and len(value) > 0:
                yield (key, value)


    def add_texture_names_to(self, target: set[str]):
        for _, value in self.enumerate_used_maps():
            target.add(value)


    def add_relpath(self, relpath: str):
        if relpath == ".": return
        for key, value in self.enumerate_used_maps():
            self[key] = os.path.join(relpath, value)



class MaterialVersion(FloatEnum):
    NONE = 0.0
    V1 = 1.0
    V1_5 = 1.5



type _RawStages = list[SDict]



class Material(_BaseDict):

    class _Translucent(_BaseDict):
        __slots__=()
        enabled = _Bool("translucent", False)
        blend_mode = _Str("translucentBlendOp", AlphaBlendMode.NONE, AlphaBlendMode)
        zwrite = _Bool("translucentZWrite", False)
        recv_shadows = _Bool("translucentRecvShadows", False)

    class _Subsurface(_BaseDict):
        __slots__=()
        enabled = _Bool("subSurface", False)
        intensity = _Float("subSurfaceIntensity", 0.2)

    _raw_stages = DictProperty[_RawStages | None]("Stages", None)

    name = _NStr("name")
    class_name = _NStr("class")
    ground_type = _NStr("groundType")
    map_to = _NStr("mapTo")

    version = _Float("version", MaterialVersion.NONE, MaterialVersion)
    active_layers = _Int("activeLayers", 1)
    
    alpha_test = _Bool("alphaTest", False)
    alpha_ref = _Int("alphaRef", 1)
    double_sided = _Bool("doubleSided", False)
    invert_backface_normals = _Bool("invertBackFaceNormals", False)
    cast_shadows = _Bool("castShadows", True)
    dynamic_cubemap = _Bool("dynamicCubemap", True)
    cubemap = _Str("cubemap", "")

    __slots__=()
    def __init__(self, dict):
        super().__init__(dict)

        if self._raw_stages is None:
            self._raw_stages = cast(_RawStages, [{},{},{},{}])

        raw_stages = self._raw_stages
        while len(raw_stages) < 4: raw_stages.append({})

        self.stages = [MaterialStage(raw_stages[0]), MaterialStage(raw_stages[1]), MaterialStage(raw_stages[2]), MaterialStage(raw_stages[3])]

        self.translucent = Material._Translucent(self)
        self.subsurface = Material._Subsurface(self)


    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)


    def add_relpath(self, relpath: str):
        for stage in self.stages:
            stage.add_relpath(relpath)