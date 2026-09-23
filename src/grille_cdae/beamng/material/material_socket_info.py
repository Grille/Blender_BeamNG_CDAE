_socket_map_list: list[str] = []

def _new(map: str, value: str | None, uv: str | None, instance: str | None = None, vertex: str | None = None) -> dict[str, str | None]:
    _socket_map_list.append(map)
    return {"map":map, "value":value, "uv":uv, "instance":instance, "vertex":vertex}

DETAIL_COLOR = _new("detailMap", "detailBaseColorMapStrength", "detailMapUseUV")
DETAIL_NORMAL = _new("detailNormalMap", "detailNormalMapStrength", "normalDetailMapUseUV")
DETAIL_METALIC = _new("metallicDetailMap", "detailMetallicMapStrength", None)
DETAIL_ROUGHNES = _new("roughnessDetailMap", "detailRoughnessMapStrength", None)
DETAIL_OPACITY = _new("opacityDetailMap", "detailOpacityMapStrength", "opacityDetailMapUseUV")
DETAIL_AMBIENT_OCCLUSION = _new("ambientOcclusionDetailMap", "detailAoMapStrength", None)

COLOR = _new("baseColorMap", "baseColorFactor", "diffuseMapUseUV", "instanceDiffuse", "vertColor")
NORMAL = _new("normalMap", "normalMapStrength", "normalMapUseUV")
SPECULAR = _new("specularMap", None, None)
METALLIC = _new("metallicMap", "metallicFactor", "metallicMapUseUV")
ROUGHNESS = _new("roughnessMap", "roughnessFactor", "roughnessMapUseUV")
OPACITY = _new("opacityMap", "opacityFactor", "opacityMapUseUV", "instanceOpacity", None)
AMBIENT_OCCLUSION = _new("ambientOcclusionMap", None, "ambientOcclusionMapUseUV")
EMISSION = _new("emissiveMap", "emissiveFactor", "emissiveMapUseUV", "instanceEmissive", "vertColorEmissive")
PALETTE = _new("colorPaletteMap", None, "colorPaletteMapUseUV")
REFLECTIVITY = _new("reflectivityMap", "reflectivityMapFactor", None)
OVERLAY = _new("overlayMap", None, None)
CLEAR_COAT = _new("clearCoatMap", "clearCoatFactor", "clearCoatMapUseUV")
CLEAR_COAT_NORMAL = _new("clearCoatBottomNormalMap", "clearCoatBottomNormalMapStrength", None)

MAP_KEYS = _socket_map_list