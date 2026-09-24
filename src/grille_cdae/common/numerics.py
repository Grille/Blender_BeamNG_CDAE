from __future__ import annotations

import struct as _struct
from typing_extensions import Self

from grille_cdae.common.imports import *
from grille_cdae.common.type_alias import *



type _Number = float | int
type FloatSequence = Sequence[float] | mathutils.Vector | mathutils.Quaternion



def _new_tuple[T](cls: type[T], iterable: Iterable) -> T: # type: ignore
    return tuple.__new__(cls, iterable) # type: ignore



class Numeric:
    __slots__ = ()

    FIELDS: tuple[str,...] = ()
    LENGTH = 0
    STRUCT = ""
    SIZE = 0


    def __getitem__(self, index: int) -> float: 
        raise NotImplementedError

    
    def __len__(self) -> int: 
        raise NotImplementedError

    
    @classmethod
    def from_seq(cls, seq: FloatSequence, offset: int = 0, default: float | None = None) -> Self:
        seq_length = len(seq) 
        type_length = cls.LENGTH

        if seq_length == type_length and offset == 0 and isinstance(seq, tuple | list):
            return _new_tuple(cls, seq)

        def get(index: int) -> float:
            index += offset
            if index < 0 or index >= seq_length: 
                if default is None: raise IndexError(index)
                return default
            return seq[index]

        return _new_tuple(cls, (get(i) for i in range(type_length)))


    @classmethod
    def from_value(cls, value: float = 0.0) -> Self:
       return _new_tuple(cls, (value  for _ in range(cls.LENGTH)))


    @classmethod
    def from_obj(cls, obj: object) -> Self:
        if isinstance(obj, float | int): return cls.from_value(obj)
        return cls.from_seq(cast(FloatSequence, obj), 0, 0.0)


    @classmethod
    def unpack(cls, data: bytes):
        return cls.from_seq(_struct.unpack(cls.STRUCT, data))
    

    def pack(self):
        return _struct.pack(self.STRUCT, *self)


    def as_vector(self):
        return mathutils.Vector(cast(Sequence[float], self))



class _Vec2FMixin(Numeric):
    __slots__ = ()

    FIELDS = "x", "y", "z", "w"
    LENGTH = 2
    STRUCT = "<2f"
    SIZE = 8


    @property
    def x(self): return self[0]

    @property 
    def y(self): return self[1]
    


class _Vec3FMixin(_Vec2FMixin):
    __slots__ = ()

    LENGTH = 3
    STRUCT = "<3f"
    SIZE = 12

    @property 
    def z(self): return self[2]



class _Vec4FMixin(_Vec3FMixin):
    __slots__ = ()

    LENGTH = 4
    STRUCT = "<4f"
    SIZE = 16

    @property 
    def w(self): return self[3]

    

class Vec2F(tuple[float, float], _Vec2FMixin):
    __slots__ = ()

    def __new__(cls, x: float = 0.0, y: float = 0.0):
        return _new_tuple(cls, (x, y))

    def __str__(self):
        return f"<{self.__class__.__name__} (x={self.x:.2f}, y={self.y:.2f})>"


    ZERO: Vec2F
    ONE: Vec2F

Vec2F.ZERO = Vec2F.from_value(0.0)
Vec2F.ONE = Vec2F.from_value(1.0)

    
    
class Vec3F(tuple[float, float, float], _Vec3FMixin):
    __slots__ = ()

    def __new__(cls, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        return _new_tuple(cls, (x, y, z))


    def min(self, other: 'Vec3F'):
        return Vec3F(min(self.x, other.x), min(self.y, other.y), min(self.z, other.z))
    

    def max(self, other: 'Vec3F'):
        return Vec3F(max(self.x, other.x), max(self.y, other.y), max(self.z, other.z))
    

    def dot(self, other: 'Vec3F') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    

    def max_unit(self) -> float:
        return max(self.x, self.y, self.z)
    

    def __str__(self):
        return f"<{self.__class__.__name__} (x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f})>"


    ZERO: Vec3F
    ONE: Vec3F

Vec3F.ZERO = Vec3F(0.0, 0.0, 0.0)
Vec3F.ONE = Vec3F(1.0, 1.0, 1.0)

        

class _Vec4F(tuple[float, float, float, float], _Vec4FMixin):
    __slots__ = ()


    def __new__(cls, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0):
        return _new_tuple(cls, (x, y, z, w))


    def __str__(self):
        return f"<{self.__class__.__name__} (x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f}, w={self.w:.2f})>"



class Vec4F(_Vec4F):
    __slots__ = ()

    ZERO: Vec4F
    ONE: Vec4F

Vec4F.ZERO = Vec4F(0.0, 0.0, 0.0, 0.0)
Vec4F.ONE = Vec4F(1.0, 1.0, 1.0, 0.0)



class _Quat4F(_Vec4F):
    __slots__ = ()

    @classmethod
    def from_blender_quaternion(cls, quat: mathutils.Quaternion | Tuple4F):
        if isinstance(quat, tuple): quat = mathutils.Quaternion(quat)
        return cls(quat.x, quat.y, quat.z, -quat.w)
    

    @classmethod
    def from_collada_quaternion(cls, quat: mathutils.Quaternion | Tuple4F):
        if isinstance(quat, tuple): quat = mathutils.Quaternion(quat)
        return cls(-quat.w, quat.x, quat.y, quat.z)
    
    
    def to_collada_quaternion(self):
        return mathutils.Quaternion((-self.w, self.x, self.y, self.z))
    
    
    def to_blender_quaternion(self):
        return mathutils.Quaternion((self.x, self.y, self.z, -self.w))
    


class Quat4F(_Quat4F):
    __slots__ = ()

    IDENTITY: Quat4F

Quat4F.IDENTITY = Quat4F(0.0, 0.0, 0.0, -1.0)


    
class Quat4I16(_Quat4F):
    __slots__ = ()

    STRUCT = None 
    SIZE = 8
    FP_SCALE = 32767.0


    @classmethod
    def unpack(cls, data: bytes):
        def cast(value: int): return value / Quat4I16.FP_SCALE
        array = np.frombuffer(data, dtype=np.int16, count=4)
        return cls(cast(array[0]), cast(array[1]), cast(array[2]), cast(array[3]))


    def pack(self):
        def cast(value: float): return int(value * Quat4I16.FP_SCALE)
        arr = np.array([cast(self.x), cast(self.y), cast(self.z), cast(self.w)], dtype=np.int16)
        return arr.tobytes()


    IDENTITY: Quat4I16

Quat4I16.IDENTITY = Quat4I16(0.0, 0.0, 0.0, -1.0)



class Box6F(tuple[Vec3F, Vec3F]):
    __slots__ = ()

    SIZE = 24


    @property
    def min(self): return self[0]

    @property
    def max(self): return self[1]


    def __new__(cls, min = Vec3F.ZERO, max = Vec3F.ZERO):
        return _new_tuple(cls, (min, max))


    @classmethod
    def from_seq(cls, list: FloatSequence, offset: int = 0, default: float | None = None):
        return cls(Vec3F.from_seq(list, offset, default), Vec3F.from_seq(list, offset + 3, default))


    def extended(self, other: Box6F):
        min = self.min.min(other.min)
        max = self.max.max(other.max)
        return Box6F(min, max)
    

    def center(self):
        return Vec3F((self.min.x + self.max.x)/2,(self.min.y + self.max.y)/2,(self.min.z + self.max.z)/2)
    

    def range(self):
        return Vec3F(abs(self.min.x - self.max.x),abs(self.min.y - self.max.y),abs(self.min.z - self.max.z))
    

    def __str__(self):
        return f"<{self.min}, {self.max}>"
    

    @property
    def tuple6(self):
        return (self.min.x, self.min.y, self.min.z, self.max.x, self.max.y, self.max.z)
        


class Color4F(_Vec4F):
    __slots__ = ()

    FIELDS = "r", "g", "b", "a"


    def __new__(cls, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0):
        return _new_tuple(cls, (r, g, b, a))


    @property
    def linear(self): return self.apply_to_rgb(Color4F.unit_srgb_to_linear)
    

    @property
    def srgb(self): return self.apply_to_rgb(Color4F.unit_linear_to_srgb)


    def apply_to_rgb(self, func: Callable[[float], float]):
        return Color4F(func(self.r), func(self.g), func(self.b), self.a)
    

    @staticmethod
    def unit_srgb_to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


    @staticmethod
    def unit_linear_to_srgb(c: float) -> float:
        return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


    @property
    def r(self): return self.x

    @property
    def g(self): return self.y

    @property
    def b(self): return self.z

    @property
    def a(self): return self.w 


    ZERO: Color4F
    ONE: Color4F
    WHITE: Color4F
    BLACK: Color4F

Color4F.ZERO = Color4F.from_value(0.0)
Color4F.ONE = Color4F.from_value(1.0)
Color4F.WHITE = Color4F.ONE
Color4F.BLACK = Color4F(0.0 ,0.0 ,0.0 ,1.0)



class Transforms(tuple[Vec3F, Vec3F, Quat4I16]):
    __slots__ = ()

    IDENTITY: Transforms

    @property
    def translation(self): return self[0]

    @property
    def scale(self): return self[1]

    @property
    def rotation(self): return self[2]


    def __new__(cls, translation: Vec3F = Vec3F.ZERO, scale: Vec3F = Vec3F.ONE, rotation: Quat4I16 = Quat4I16.IDENTITY):
        return _new_tuple(cls, (translation, scale, rotation))


    @classmethod
    def from_blender_matrix(cls, matrix: mathutils.Matrix):
        translation = Vec3F.from_seq(matrix.to_translation())
        rotation = Quat4I16.from_blender_quaternion(matrix.to_quaternion())
        scale = Vec3F.from_seq(matrix.to_scale())
        return cls(translation, scale, rotation)
    

Transforms.IDENTITY = Transforms()



__all__ = "Numeric", "Vec2F", "Vec3F", "Vec4F", "Quat4F", "Quat4I16", "Box6F", "Color4F", "Transforms"