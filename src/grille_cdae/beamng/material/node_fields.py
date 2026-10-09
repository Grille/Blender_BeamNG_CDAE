"""
Mapping between BeamNG shader node sockets and the Material model.

Paths address the Material / MaterialStage wrappers (e.g. "metallic", "clear_coat.roughness"),
never JSON keys, those are owned by material.py and material_socket_info.py.
"""

from __future__ import annotations

from grille_cdae.common import *
from grille_cdae.enums import SocketName

from ...blender.shader_nodes import BaseShaderNode, BeamBSDF15, BeamBSDF15Detail, BeamBDSF10Basic, BeamMaterial, BeamPalette, BeamUVAnimation
from .material import MaterialVersion



def to_float(value: Any) -> float: return round(float(value), 6)
def to_bool(value: Any) -> bool: return bool(value)
def to_srgb(value: Any) -> Color4F: return Color4F(*(round(c, 6) for c in Color4F.from_obj(value).srgb))
def to_vec2(value: Any) -> Vec2F: return Vec2F(*(round(c, 6) for c in Vec2F.from_obj(list(value))))

def from_srgb(value: Any) -> tuple[float, ...]: return tuple(Color4F.from_obj(list(value) + [1.0] * (4 - len(value))).linear)
def from_vec2(value: Any) -> tuple[float, float]: vec = Vec2F.from_obj(value); return (vec.x, vec.y)

# node socket value from model value, for import
INVERSE: dict[Converter[object], Converter[object]] = {
    to_float: float,
    to_bool: bool,
    to_srgb: from_srgb,
    to_vec2: from_vec2,
}



class Tex(NamedTuple):
    """Texture socket in a stage: map + uv from the image linked to `map`, other fields from plain value sockets."""
    map: str
    path: str
    value: str | None = None
    conv: Converter[object] = to_float
    instance: str | None = None
    vertex: str | None = None
    normal: bool = False # value is the strength of the normal map in front of the image
    detail: bool = False # detail map (uses detail UVs and scale)



class Value(NamedTuple):
    """Plain value socket written to a single field."""
    socket: str
    path: str
    conv: Converter[object] = to_float



class Bundle(NamedTuple):
    """Socket linked to a helper node (e.g. detail, palette), whose own fields are applied to the same target."""
    socket: str
    node: type[BaseShaderNode]
    fields: tuple[Field, ...]
    detail: bool = False # maps of the helper node are detail maps (use detail UVs and scale)



type Field = Tex | Value | Bundle


_SD = BeamBSDF15Detail.Sockets

DETAIL_15: tuple[Field, ...] = (
    Tex(_SD.BASE_COLOR_MAP, "detail.color", _SD.BASE_COLOR_STRENGTH),
    Tex(_SD.NORMAL, "detail.normal", normal=True),
    Tex(_SD.METALLIC_MAP, "detail.metallic", _SD.METALLIC_STRENGTH),
    Tex(_SD.ROUGHNESS_MAP, "detail.roughness", _SD.ROUGHNESS_STRENGTH),
    Tex(_SD.OPACITY_MAP, "detail.opacity", _SD.OPACITY_STRENGTH),
    Tex(_SD.AO_MAP, "detail.ambient_occlusion", _SD.AO_STRENGTH),
)


_SP = BeamPalette.Sockets

PALETTE: tuple[Field, ...] = (
    Tex(_SP.PALETTE_MAP, "palette"),
    Value(_SP.COLOR, "palette.color", to_bool),
    Value(_SP.METALLIC, "palette.metallic", to_bool),
    Value(_SP.ROUGHNESS, "palette.roughness", to_bool),
    Value(_SP.CLEAR_COAT, "palette.clear_coat", to_bool),
    Value(_SP.CLEAR_COAT_ROUGHNESS, "palette.clear_coat_roughness", to_bool),
)


_S15 = BeamBSDF15.Sockets

STAGE_15: tuple[Field, ...] = (
    Tex(_S15.BASE_COLOR_MAP, "color", _S15.BASE_COLOR, to_srgb, instance=_S15.INSTANCE_COLOR, vertex=_S15.VERTEX_COLOR),
    Tex(_S15.NORMAL, "normal", normal=True),
    Tex(_S15.METALLIC_MAP, "metallic", _S15.METALLIC_FACTOR),
    Tex(_S15.ROUGHNESS_MAP, "roughness", _S15.ROUGHNESS_FACTOR),
    Tex(_S15.OPACITY_MAP, "opacity", _S15.OPACITY_FACTOR, instance=_S15.INSTANCE_OPACITY),
    Tex(_S15.AO_MAP, "ambient_occlusion"),
    Tex(_S15.EMISSIVE_MAP, "emission", _S15.EMISSIVE_FACTOR, to_srgb, instance=_S15.INSTANCE_EMISSIVE, vertex=_S15.VERTEX_EMISSIVE),
    Value(_S15.EMISSIVE_INTENSITY, "emission.intensity_nits"),
    Tex(_S15.CC_MAP, "clear_coat", _S15.CC_FACTOR),
    Value(_S15.CC_ROUGHNESS, "clear_coat.roughness"),
    Tex(_S15.CC_NORMAL, "clear_coat_normal", normal=True),
    Value(_S15.RETRO_REFLECTIVITY, "retro_reflectivity.factor"),
    Value(_S15.RETRO_REFLECTIVITY_COLOR, "retro_reflectivity.color", to_srgb),
    Bundle(_S15.DETAIL, BeamBSDF15Detail, DETAIL_15, detail=True),
    Bundle(_S15.PALETTE, BeamPalette, PALETTE),
)

_S10 = BeamBDSF10Basic.Sockets

# glow (color + enabled) is derived in code
STAGE_10: tuple[Field, ...] = (
    Tex(_S10.COLOR_MAP, "color", _S10.COLOR_FACTOR, to_srgb, instance=SocketName.InstanceColor, vertex=SocketName.VertexColor),
    Tex(SocketName.Normal, "normal", normal=True),
    Tex(_S10.DETAIL_COLOR, "detail.color", detail=True),
    Tex(SocketName.DetailNormal, "detail.normal", normal=True, detail=True),
    Tex(_S10.RM, "reflectivity", _S10.RM_FACTOR),
    Tex(_S10.OVERLAY_MAP, "overlay"),
    Tex(_S10.OPACITY_MAP, "opacity"),
    Tex(_S10.SPECULAR_MAP, "specular"),
    Value(_S10.SPECULAR_ENABLED, "specular.enabled", to_bool),
    Value(_S10.SPECULAR_COLOR, "specular.factor", to_srgb),
    Value(_S10.SPECULAR_ROUGHNESS, "specular.roughness"),
    Value(_S10.EMISIVE, "legacy_light.emissive_enabled", to_bool),
    Bundle(_S10.PALETTE, BeamPalette, PALETTE),
)

STAGE_FIELDS: dict[type, tuple[Field, ...]] = {
    BeamBSDF15: STAGE_15,
    BeamBDSF10Basic: STAGE_10,
}

STAGE_VERSION: dict[type, MaterialVersion] = {
    BeamBSDF15: MaterialVersion.V1_5,
    BeamBDSF10Basic: MaterialVersion.V1,
}

STAGE_NODE: dict[MaterialVersion, type[BaseShaderNode]] = {version: node for node, version in STAGE_VERSION.items()}


_SA = BeamUVAnimation.Sockets

# wave type, flags and sequence segment size are derived in code
UV_ANIMATION: tuple[Field, ...] = (
    Value(_SA.ROTATION_SPEED, "animation.rot_speed"),
    Value(_SA.ROTATION_PIVOT_OFFSET, "animation.rot_pivot_offset", to_vec2),
    Value(_SA.SCROLL_SPEED, "animation.scroll_speed"),
    Value(_SA.SCROLL_FACTOR, "animation.scroll_direction", to_vec2),
    Value(_SA.WAVE_AMPLITUDE, "animation.wave_amp"),
    Value(_SA.WAVE_FREQUENCY, "animation.wave_freq"),
    Value(_SA.FRAMES_SEC, "animation.seq_frames_per_sec"),
)


_SM = BeamMaterial.Sockets

MATERIAL_FIELDS: tuple[Field, ...] = (
    Value(_SM.CLIP, "alpha_test", to_bool),
    Value(_SM.DOUBLE_SIDED, "double_sided", to_bool),
    Value(_SM.INVERT_BACKFACE_NORMALS, "invert_backface_normals", to_bool),
    Value(_SM.SHADOWS, "cast_shadows", to_bool),
)
