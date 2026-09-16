from grille_cdae.common import *

type SocketAccessor = str | int
type SocketValue = bool | float | int | Tuple3F | Tuple4F | str


def get_node_type_idname(node_type: str | type) -> str:
    if isinstance(node_type, str):
        return node_type
    elif isinstance(node_type, type):
        if issubclass(node_type, bpyt.Node):
            if hasattr(node_type, "bl_idname"):
                return node_type.bl_idname
            else:
                return node_type.bl_rna.identifier # type: ignore
        else:
            raise TypeError("node_type not subclass of 'bpy.types.Node'.")
    else:
        raise TypeError(f"node_type must be str or type.")


def set_default_value(socket: bpy.types.NodeSocket | bpy.types.NodeTreeInterfaceSocket, value: SocketValue):
    socket.default_value = value # pyright: ignore[reportAttributeAccessIssue]

def get_default_value(socket: bpy.types.NodeSocket | bpy.types.NodeTreeInterfaceSocket) -> SocketValue:
    return socket.default_value # type: ignore

