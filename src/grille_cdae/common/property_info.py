from __future__ import annotations

from grille_cdae.common.imports import *
from grille_cdae.common.enums import *



def annotate_properties[T](target: type[T], **props: object):
    target.__annotations__.update(props) 



type EnumCtrItem = str | tuple[str, ...]
type EnumCtrSequence = Sequence[EnumCtrItem]
type nstr = str | None
type Update[T:types.bpy_struct] = Callable[[T, types.Context], None]



def _to_tuple3(value: EnumCtrItem) -> tuple[str, str, str]:
    if isinstance(value, str): return (value, value, value)
    length = len(value)
    if length == 1: return (value[0], value[0], "")
    if length == 2: return (value[0], value[1], "")
    if length == 3: return (value[0], value[1], value[2])
    raise ValueError(length)



class PropertyInfoFactory[T:types.bpy_struct = Any]:

    def __init__(self):
        self.items: list[PropertyInfo[T]] = []


    def _new[TValue](self, property: object, *, cast: Converter[TValue] | None = None, key: nstr = None, type_hint: type[TValue] | None = None):
        pinfo = PropertyInfo[T, TValue](property, cast)
        if key is not None: pinfo.set_key(key)
        self.items.append(pinfo)
        return pinfo


    def str(self, name: str, default: str = "", *, description: str = "", key: nstr = None, update: Update[T] | None = None):
        property = props.StringProperty(name=name, default=default, description=description, update=update)
        return self._new(property, cast=str, key=key)


    @overload
    def enum(self, name: str, *, default: str, items: EnumCtrSequence, description: str = "", update: Update[T] | None = None) -> PropertyInfo[T, str]:...

    @overload
    def enum[TEnum:StrEnum](self, name: str, *, default: TEnum, items: type[TEnum], description: str = "", update: Update[T] | None = None) -> PropertyInfo[T, TEnum]:...

    def enum[TEnum](self, name: str, *, default: TEnum, items: EnumCtrSequence | type[TEnum], description: str = "", update: Update[T] | None = None) -> PropertyInfo[T, TEnum]:

        if isinstance(items, type):
            etype = items
            if issubclass(etype, StrEnum):
                t3items = etype.to_bpy_items()
            else:
                raise TypeError(etype)

        else:
            etype = str
            t3items =  [_to_tuple3(item) for item in items]

        assert isinstance(default, etype)

        converter = cast(Converter[TEnum], etype)

        property = props.EnumProperty(name=name, default=default, items=t3items, description=description, update=update)
        return self._new(property, cast=converter)


    def int(self, name: str, default: int = 0, *, description: str = "", key: nstr = None, update: Update[T] | None = None):
        property = props.IntProperty(name=name, default=default, description=description, update=update)
        return self._new(property, cast=int, key=key)


    def bool(self, name: str, default: bool = False, *, description: str = "", key: nstr = None, update: Update[T] | None = None):
        property = props.BoolProperty(name=name, default=default, description=description, update=update)
        return self._new(property, cast=bool, key=key)


    def ptr[TValue:types.PropertyGroup | types.ID](self, type: type[TValue], *, key: nstr = None, update: Update[T] | None = None):
        property = props.PointerProperty(type=type, update=update)
        return self._new(property, key=key, type_hint=type)


    def register(self, target: type[T]):
        for pinfo in self.items: pinfo.register(target)


    def unregister(self, target: type[T]):
        for pinfo in self.items: pinfo.unregister(target)


    def annotate(self, target: type[T]):
        for pinfo in self.items: pinfo.annotate(target)



PREFIX = "grille_beamng_cdae_"

class PropertyInfo[T:types.bpy_struct = Any, TValue = Any]:

    PREFIX = PREFIX

    def __init__(self, property: object, cast: Converter[TValue] | None = None):
        self.property = property
        self.cast = cast


    def set_key(self, key: str, prefix: str = PREFIX):
        self.key = f"{prefix}{key}"


    def register(self, target: type[T]):
        setattr(target, self.key, self.property)


    def unregister(self, target: type[T]):
        delattr(target, self.key)


    def annotate(self, target: type[T]):
        target.__annotations__[self.key] = self.property


    def __getitem__(self, obj: T) -> TValue:
        attr = getattr(obj, self.key)
        return attr if self.cast is None else self.cast(attr)


    def __setitem__(self, obj: T, value: TValue):
        setattr(obj, self.key, value)



class PropertyInfoGroupMeta(type):

    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):

        cls = super().__new__(mcls, name, bases, namespace)

        for key, value in namespace.items():
            if isinstance(value, PropertyInfo):
                value.set_key(key)

        return cls



class PropertyInfoGroup[T:types.bpy_struct = Any](metaclass=PropertyInfoGroupMeta):
    pinfo: PropertyInfoFactory[T]
    target: type[T]

    @classmethod
    def register(cls): cls.pinfo.register(cls.target)

    @classmethod
    def unregister(cls): cls.pinfo.unregister(cls.target)

    @classmethod
    def annotate(cls): cls.pinfo.annotate(cls.target)



__all__ = "PropertyInfoFactory", "PropertyInfo", "PropertyInfoGroup", "annotate_properties"
