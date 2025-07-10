import struct
import numpy as np

class Vec2F:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


    def unpack(self, data: bytes):
        (self.x, self.y) = struct.unpack("<2f", data)
    

    def pack(self):
        return struct.pack("<2f", self.x, self.y)
    


class Vec3F:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def unpack(self, data: bytes):
        (self.x, self.y, self.z) = struct.unpack("<3f", data)
    

    def pack(self):
        return struct.pack("<3f", self.x, self.y, self.z)
        

    @staticmethod
    def create_empty():
        return Vec3F(0, 0, 0)



class Vec4F:
    def __init__(self, x: float, y: float, z: float, w: float):
        self.x = x
        self.y = y
        self.z = z
        self.w = w


    def unpack(self, data: bytes):
        (self.x, self.y, self.z, self.w) = struct.unpack("<4f", data)
    

    def pack(self):
        return struct.pack("<4f", self.x, self.y, self.z, self.w)



class Quat4F(Vec4F):
    
    def to_euler(self) -> Vec3F:
        pass



class Quat4H(Quat4F):

    def unpack(self, data: bytes):
        arr = np.frombuffer(data, dtype=np.float16, count=4)
        self.x, self.y, self.z, self.w = map(float, arr)

    def pack(self):
        arr = np.array([self.x, self.y, self.z, self.w], dtype=np.float16)
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
