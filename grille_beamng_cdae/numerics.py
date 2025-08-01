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
    

    def to_tuple(self):
        return (self.x, self.y)
    


class Vec3F:

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def unpack(self, data: bytes):
        (self.x, self.y, self.z) = struct.unpack("<3f", data)
    

    def pack(self):
        return struct.pack("<3f", self.x, self.y, self.z)
    

    def to_tuple(self):
        return (self.x, self.y, self.z)
        


class Vec4F:

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.w: float = w


    @classmethod
    def from_list(cls, list: list[float]):
        self = cls(*list[:4])
        return self


    def unpack(self, data: bytes):
        (self.x, self.y, self.z, self.w) = struct.unpack("<4f", data)
    

    def pack(self):
        return struct.pack("<4f", self.x, self.y, self.z, self.w)
    

    def to_tuple(self):
        return (self.x, self.y, self.z, self.w)
    

    def to_list(self):
        return [self.x, self.y, self.z, self.w]
    


class Quat4F(Vec4F):
    
    @classmethod
    def from_blender_quaternion(cls, quat: mathutils.Quaternion | tuple):
        if isinstance(quat, tuple): quat = mathutils.Quaternion(quat)
        self = cls()
        self.x = quat.z
        self.y = quat.y
        self.z = quat.x
        self.w = quat.w

    
    def to_blender_quaternion(self):
        return mathutils.Quaternion((self.z, self.y, self.x, self.w))
    


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
    