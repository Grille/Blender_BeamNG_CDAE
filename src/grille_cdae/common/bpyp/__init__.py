import bpy as _bpy
from grille_cdae.common.bpyt import bpy_struct as _struct

from bpy.props import _PropertyDeferred as PropertyDeferred # pyright: ignore[reportPrivateUsage]

from bpy.props import BoolProperty as Bool
from bpy.props import FloatProperty as Float
from bpy.props import EnumProperty as Enum
from bpy.props import IntProperty as Int
from bpy.props import FloatVectorProperty as FloatVector
from bpy.props import PointerProperty as Pointer
from bpy.props import StringProperty as String

def anotate_properties[T:_struct](target: type[T], **props: PropertyDeferred): # pyright: ignore[reportPrivateUsage]
    target.__annotations__.update(props) 