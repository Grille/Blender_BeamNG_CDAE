# pyright: reportUnusedImport = none

from grille_cdae.common.imports import *
from grille_cdae.common.type_alias import *
from grille_cdae.common.numerics import *
from grille_cdae.common.enums import *
from grille_cdae.common.property_info import *

import grille_cdae.common.butils as butils
import grille_cdae.common.basetypes as basetypes


def not_none[T](obj: T | None) -> T:
    assert obj is not None
    return obj