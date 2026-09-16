from bpy.types import bpy_struct as _struct
import bpy.props as _props
import typing as _typing

if _typing.TYPE_CHECKING:
    from bpy.props import *

from bpy.props import (
    _PropertyDeferred, # pyright: ignore[reportPrivateUsage]
    BoolProperty as Bool,
    FloatProperty as Float,
    EnumProperty as Enum,
    IntProperty as Int,
    FloatVectorProperty as FloatVector,
    PointerProperty as Pointer,
    StringProperty as String,
)

def anotate_properties[T:_struct](target: type[T], **props: _PropertyDeferred): # pyright: ignore[reportPrivateUsage]
    target.__annotations__.update(props) 

def __getattr__(name: str): return getattr(_props, name)