"""
Mapping between BeamNG shader node sockets and the Material model.

Paths address the Material / MaterialStage wrappers (e.g. "metallic", "clear_coat.roughness"),
never JSON keys, those are owned by material.py and material_socket_info.py.
"""

from __future__ import annotations

from grille_cdae.common import *

from ...blender.shader_nodes import BeamBSDF15, BeamMaterial



def to_float(value: Any) -> float: return round(float(value), 6)
def to_bool(value: Any) -> bool: return bool(value)
def to_srgb(value: Any) -> Color4F: return Color4F(*(round(c, 6) for c in Color4F.from_obj(value).srgb))



class Tex(NamedTuple):
    """Texture socket in a stage: map + uv from the image linked to `map`, other fields from plain value sockets."""
    map: str
    path: str
    value: str | None = None
    conv: Converter[object] = to_float
    instance: str | None = None
    vertex: str | None = None
    normal: bool = False # value is the strength of the normal map in front of the image



class Value(NamedTuple):
    """Plain value socket written to a single field."""
    socket: str
    path: str
    conv: Converter[object] = to_float



type Field = Tex | Value


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
)

STAGE_FIELDS: dict[type, tuple[Field, ...]] = {
    BeamBSDF15: STAGE_15,
}

# sockets of stage nodes that are not exported yet
STAGE_UNSUPPORTED: dict[type, tuple[str, ...]] = {
    BeamBSDF15: (_S15.DETAIL, _S15.PALETTE),
}


_SM = BeamMaterial.Sockets

MATERIAL_FIELDS: tuple[Field, ...] = (
    Value(_SM.CLIP, "alpha_test", to_bool),
    Value(_SM.DOUBLE_SIDED, "double_sided", to_bool),
    Value(_SM.INVERT_BACKFACE_NORMALS, "invert_backface_normals", to_bool),
    Value(_SM.SHADOWS, "cast_shadows", to_bool),
)
