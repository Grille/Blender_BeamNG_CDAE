from __future__ import annotations

from grille_cdae.common.imports import *
import enum



class StrEnumMetaDataDict[T]:

    def __init__(self, default: Callable[[StrEnum], T]) -> None:
        self._type_dict: dict[type[StrEnum], dict[StrEnum, T]] = {}
        self._default = default

    def _get_enum_dict_or_none[TEnum: StrEnum](self, type_key: type[TEnum]) -> dict[TEnum, T] | None:
        return self._type_dict.get(type_key, None) # type: ignore
    
    def _new_enum_dict[TEnum: StrEnum](self, type_key: type[TEnum]) -> dict[TEnum, T]:
        self._type_dict[type_key] = enum_dict = dict[StrEnum, T]()
        return enum_dict # type: ignore
    
    def get_enum_dict[TEnum: StrEnum](self, key: type[TEnum]) -> dict[TEnum, T]:
        enum_dict = self._get_enum_dict_or_none(key)
        return self._new_enum_dict(key) if enum_dict is None else enum_dict
             
    def __getitem__(self, key: StrEnum):
        enum_dict = self._get_enum_dict_or_none(type(key))
        if enum_dict is not None:
            value = enum_dict.get(key, None)
            if value is not None: return value
        return self._default(key)

    def __setitem__(self, key: StrEnum, value: T):
        self.get_enum_dict(type(key))[key] = value

    def update[TEnum: StrEnum](self, type_key: type[TEnum], src: dict[TEnum, T]):
        self.get_enum_dict(type_key).update(src)



class StrEnumMetaData:
    display_name = StrEnumMetaDataDict[str](lambda e: e.value)
    description = StrEnumMetaDataDict[str](lambda _: "")



class StrEnum(enum.StrEnum):
    def __str__(self):
        return self.value

    @classmethod 
    def to_bpy_items(cls) -> list[tuple[str, str, str]]:
        return [(enum.value, enum.display_name, enum.description) for enum in cls]

    @classmethod
    def to_bpy_enum[T:types.bpy_struct](cls, name: str, *, default: Self, update: Callable[[T, types.Context], None] | None = None):
        return bpy.props.EnumProperty(name=name, items=cls.to_bpy_items(), default=default, update=update)

    @property
    def display_name(self) -> str:
        return StrEnumMetaData.display_name[self]

    @property
    def description(self) -> str:
        return StrEnumMetaData.description[self]


    
class IntEnum(enum.IntEnum):
  def __str__(self):
      return str(self.value)
    
    

class FloatEnum(float, enum.Enum):
  def __str__(self):
      return str(self.value)



IntFlag = enum.IntFlag



__all__ = "StrEnum", "IntEnum", "FloatEnum", "IntFlag", "StrEnumMetaData"
    