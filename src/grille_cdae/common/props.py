from __future__ import annotations

import grille_cdae.common.imports as _in
import grille_cdae.common.enums as _enums
import bpy.props as _props

if _in.TYPE_CHECKING:
    from bpy.props import *

from bpy.props import (
    BoolProperty as Bool,
    FloatProperty as Float,
    EnumProperty as Enum,
    IntProperty as Int,
    FloatVectorProperty as FloatVector,
    PointerProperty as Pointer,
    StringProperty as String,
)

def anotate_properties[T](target: type[T], **props: object):
    target.__annotations__.update(props) 



def _to_tuple3(value: str | tuple[str, ...]) -> tuple[str, str, str]:
    if isinstance(value, str): return (value, value, value)
    length = len(value)
    if length == 1: return (value[0], value[0], "")
    if length == 2: return (value[0], value[1], "")
    if length == 3: return (value[0], value[1], value[2])
    raise ValueError(length)



class PropertyInfoFactory[T:_in.types.bpy_struct]:

    def __init__(self, target: type[T]):
        self.target = target 
        self.items: list[PropertyInfo[T]] = []


    def _new[TValue](self, key: str, property: object, cast: _in.Converter[TValue] | None = None):
        pinfo = PropertyInfo(self.target, key, property, cast)
        self.items.append(pinfo)
        return pinfo


    def str(self, key: str, name: str, default: str = "", *, description: str = ""):
        property = String(name=name, default=default, description=description)
        return self._new(key, property, str)


    def enum[TEnum:str](self, key: str, name: str, default: TEnum, items: _in.Sequence[str|tuple[str,...]] | None = None, *, description: str = "") -> PropertyInfo[T, TEnum]:
        etype = type(default)

        if items is not None:
            items =  [_to_tuple3(item) for item in items]
        else:
            if issubclass(etype, _enums.StrEnum):
                items = etype.to_bpy_items()
            else:
                raise TypeError(etype)

        property = Enum(name=name, default=default, items=items, description=description)
        return self._new(key, property, etype)


    def int(self, key: str, name: str, default: int = 0, *, description: str = ""):
        property = Int(name=name, default=default, description=description)
        return self._new(key, property, int)


    def bool(self, key: str, name: str, default: bool = False, *, description: str = ""):
        property = Bool(name=name, default=default, description=description)
        return self._new(key, property, bool)


    def ptr[TValue:_in.types.PropertyGroup | _in.types.ID](self, key: str, type: type[TValue]):
        property = Pointer(type=type)
        pinfo = PropertyInfo[T,TValue](self.target, key, property)
        self.items.append(pinfo)
        return pinfo


    def register(self):
        for pinfo in self.items: pinfo.register()


    def unregister(self):
        for pinfo in self.items: pinfo.unregister()


    def anotate(self):
        for pinfo in self.items: pinfo.anotate()



class PropertyInfo[T:_in.types.bpy_struct, TValue = _in.Any]:

    PREFIX = "grille_beamng_cdae_"

    def __init__(self, target: type[T], key: str, property: object, cast: _in.Converter[TValue] | None = None):
        self.target = target
        self.key = f"{PropertyInfo.PREFIX}{key}"
        self.property = property
        self.cast = cast


    def register(self):
        setattr(self.target, self.key, self.property)


    def unregister(self):
        delattr(self.target, self.key)


    def anotate(self):
        self.target.__annotations__[self.key] = self.property


    def __getitem__(self, obj: T) -> TValue:
        attr = getattr(obj, self.key)
        return attr if self.cast is None else self.cast(attr)


    def __setitem__(self, obj: T, value: TValue):
        setattr(obj, self.key, value)



def __getattr__(name: str): return getattr(_props, name)