import bpy

def get_node_type_idname(node_type: str | type) -> str:
    if isinstance(node_type, str):
        return node_type
    elif isinstance(node_type, type):
        if issubclass(node_type, bpy.types.Node):
            if hasattr(node_type, "bl_idname"):
                return node_type.bl_idname
            else:
                return node_type.bl_rna.identifier
        else:
            raise TypeError("node_type not subclass of 'bpy.types.Node'.")
    else:
        raise TypeError(f"node_type must be str or type.")
