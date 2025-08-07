import struct
import math
import mathutils
import numpy as np

class Vec2F:
    
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y


    def unpack(self, data: bytes):
        (self.x, self.y) = struct.unpack("<2f", data)
    

    def pack(self):
        return struct.pack("<2f", self.x, self.y)
    

    @property
    def tuple2(self):
        return (self.x, self.y)
    


class Vec3F:

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z


    @classmethod
    def from_list3(cls, list: list[float]):
        self = cls(*list[:3])
        return self
    

    def unpack(self, data: bytes):
        (self.x, self.y, self.z) = struct.unpack("<3f", data)
    

    def pack(self):
        return struct.pack("<3f", self.x, self.y, self.z)
    

    @property
    def tuple3(self):
        return (self.x, self.y, self.z)
        


class Vec4F:

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.w: float = w


    @classmethod
    def from_list4(cls, list: list[float]):
        self = cls(*list[:4])
        return self


    def unpack(self, data: bytes):
        (self.x, self.y, self.z, self.w) = struct.unpack("<4f", data)
    

    def pack(self):
        return struct.pack("<4f", self.x, self.y, self.z, self.w)
    

    @property
    def tuple3(self):
        return (self.x, self.y, self.z)
    

    @property
    def tuple4(self):
        return (self.x, self.y, self.z, self.w)
        

    @property
    def list4(self):
        return [self.x, self.y, self.z, self.w]
    


class Quat4F(Vec4F):
    
    @classmethod
    def from_blender_quaternion(cls, quat: mathutils.Quaternion | tuple):
        if isinstance(quat, tuple): quat = mathutils.Quaternion(quat)
        self = cls()
        self.x = -quat.z
        self.y = quat.y
        self.z = -quat.x
        self.w = quat.w
        return self

    
    def to_collada_matrix(self):
        quat = mathutils.Quaternion((self.w, -self.z, self.y, -self.x))
        return quat.to_matrix().to_4x4()
    

    def to_blender_quaternion(self):
        return mathutils.Quaternion((self.w, -self.x, self.y, -self.z))
    
    

class Quat4I16(Quat4F):

    FP_SCALE = 32767.0


    def unpack(self, data: bytes):
        def cast(value: int): return value / Quat4I16.FP_SCALE
        array = np.frombuffer(data, dtype=np.int16, count=4)
        self.x = cast(array[0])
        self.y = cast(array[1])
        self.z = cast(array[2])
        self.w = cast(array[3])


    def pack(self):
        def cast(value: float): return int(value * Quat4I16.FP_SCALE)
        arr = np.array([cast(self.x), cast(self.y), cast(self.z), cast(self.w)], dtype=np.int16)
        return arr.tobytes()



class Box6F:

    def __init__(self, minx = 0.0, miny = 0.0, minz = 0.0, maxx = 0.0, maxy = 0.0, maxz = 0.0):
        self.min = Vec3F(minx, miny, minz)
        self.max = Vec3F(maxx, maxy, maxz)


class Color4F(Vec4F):

    def __init__(self, r = 0.0, g = 0.0, b = 0.0, a = 0.0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


    @property
    def linear(self):
        unit = Color4F.unit_srgb_to_linear
        return Color4F(unit(self.r), unit(self.g), unit(self.b), self.a)
    

    @property
    def srgb(self):
        unit = Color4F.unit_linear_to_srgb
        return Color4F(unit(self.r), unit(self.g), unit(self.b), self.a)
    

    @staticmethod
    def unit_srgb_to_linear(c: float):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


    @staticmethod
    def unit_linear_to_srgb(c: float):
        return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


    @property
    def r(self) -> float: return self.x
    @r.setter
    def r(self, value: float): self.x = value

    @property
    def g(self) -> float: return self.y
    @g.setter
    def g(self, value: float): self.y = value

    @property
    def b(self) -> float: return self.z
    @b.setter
    def b(self, value: float): self.z = value

    @property
    def a(self) -> float: return self.w
    @a.setter
    def a(self, value: float): self.w = value
    