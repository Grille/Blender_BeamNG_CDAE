from grille_cdae.common.types import *
import bpy.types as _types


def _get_str_or_none(obj: object, key: str):
     value = getattr(obj, key, None)
     if isinstance(value, str | None): return value
     raise TypeError(value)


def _get_str(obj: object, key: str):
     value = getattr(obj, key)
     if isinstance(value, str): return value
     raise TypeError(value)


def get_identifier(bpy_struct: type[_types.bpy_struct] | _types.bpy_struct):
    return _get_str(bpy_struct.bl_rna, "identifier")


def get_idname(obj: str | type[_types.bpy_struct] | _types.bpy_struct) -> str:

    if isinstance(obj, str): return obj

    assert obj is not type

    identifier = _get_str_or_none(obj, "bl_idname")
    if identifier is not None: return identifier

    return get_identifier(obj)


def set_default_value(socket: _types.NodeSocket | _types.NodeTreeInterfaceSocket, value: SocketValue):
    socket.default_value = value # type: ignore

def get_default_value(socket: _types.NodeSocket | _types.NodeTreeInterfaceSocket) -> SocketValue:
    return socket.default_value # type: ignore

