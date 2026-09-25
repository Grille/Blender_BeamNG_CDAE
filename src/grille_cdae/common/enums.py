from grille_cdae.common.imports import *
from collections import defaultdict
import enum



_StrEnum_display_names: defaultdict[type, dict[str, str]] = defaultdict(dict)
_StrEnum_descriptions: defaultdict[type, dict[str, str]] = defaultdict(dict)



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
        return _StrEnum_display_names[type(self)].get(self.value, self.value)

    @property
    def description(self) -> str:
        return _StrEnum_descriptions[type(self)].get(self.value, "")


    
class IntEnum(enum.IntEnum):
  def __str__(self):
      return str(self.value)
    
    

class FloatEnum(float, enum.Enum):
  def __str__(self):
      return str(self.value)



IntFlag = enum.IntFlag



__all__ = "StrEnum", "IntEnum", "FloatEnum", "IntFlag"
    