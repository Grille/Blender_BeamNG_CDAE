import typing as _typing
import bpy.types as _bpyt

from bpy.types import *
if _typing.TYPE_CHECKING: from grille_cdae.common.bpyt.stubs import *

def __getattr__(name: str): return getattr(_bpyt, name)