import bpy
import typing
from enum import Enum

class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    @classmethod
    def to_bpy_items(cls):
        return [(enum, enum, "") for enum in cls]

    @classmethod
    def to_bpy_enum[T:bpy.types.bpy_struct](cls, name: str, *, default: typing.Self, update: typing.Callable[[T, bpy.types.Context], None] | None = None):
        return bpy.props.EnumProperty(name=name, items=cls.to_bpy_items(), default=default, update=update)
    


class IntEnum(int, Enum):
  def __str__(self):
      return str(self.value)
    
    

class FloatEnum(float, Enum):
  def __str__(self):
      return str(self.value)
    


class AlphaBlendMode(StrEnum):
    NONE = "None"
    PRE_MUL_ALPHA = "PreMulAlpha"
    ADD = "Add"
    ADD_ALPHA = "AddAlpha"
    LERP_ALPHA = "LerpAlpha"
    MUL = "Mul"
    SUB = "Sub"
    


