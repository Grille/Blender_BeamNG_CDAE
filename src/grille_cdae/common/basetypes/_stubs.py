import typing as _typing
import bpy.types as _types


if _typing.TYPE_CHECKING:
    from ._stubs_override import *


def __getattr__(name: str): return getattr(_types, name)