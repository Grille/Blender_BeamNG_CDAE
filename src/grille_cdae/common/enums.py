from grille_cdae.common.imports import *
import enum as _enum



class StrEnum(_enum.StrEnum):
    def __str__(self):
        return self.value

    @classmethod
    def to_bpy_items(cls):
        return [(enum, enum, "") for enum in cls]

    @classmethod
    def to_bpy_enum[T:types.bpy_struct](cls, name: str, *, default: Self, update: Callable[[T, types.Context], None] | None = None):
        return bpy.props.EnumProperty(name=name, items=cls.to_bpy_items(), default=default, update=update)


    
class IntEnum(_enum.IntEnum):
  def __str__(self):
      return str(self.value)
    
    

class FloatEnum(float, _enum.Enum):
  def __str__(self):
      return str(self.value)



IntFlag = _enum.IntFlag



__all__ = "StrEnum", "IntEnum", "FloatEnum", "IntFlag"
    