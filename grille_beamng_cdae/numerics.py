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
        

    @staticmethod
    def create_empty():
        return Vec3F()



class Vec4F:

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.w: float = w


    def unpack(self, data: bytes):
        (self.x, self.y, self.z, self.w) = struct.unpack("<4f", data)
    

    def pack(self):
        return struct.pack("<4f", self.x, self.y, self.z, self.w)
    

    def to_tuple(self):
        return (self.x, self.y, self.z, self.w)
    




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

    def __init__(self, min: Vec3F, max: Vec3F):
        self.min = min
        self.max = max


    @staticmethod
    def create_empty():
        return Box6F(Vec3F.create_empty(), Vec3F.create_empty())



class TSIntegerSet:
    pass
