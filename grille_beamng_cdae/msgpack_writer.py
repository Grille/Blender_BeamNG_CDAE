import struct
import msgpack
import zstandard

from io import BufferedWriter, BytesIO

from .numerics import *


class MsgpackWriter:

    def __init__(self):
        self.packer = msgpack.Packer()
        self.buffer = BytesIO()


    def to_bytes(self):
        return self.buffer.getvalue()
        

    def write(self, obj: any):
        data = self.packer.pack(obj)
        self.buffer.write(data)


    def write_float(self, value: float):
        self.write(float(value))


    def write_int32(self, value: int):
        self.write(int(value))


    def write_str(self, value: str):
        self.write(str(value))


    def write_bytes(self, value: bytes):
        self.write(value)


    def write_dict(self, value: dict):
        self.write(value)


    def write_integerset(self, value: set[int]):
        self.write(list(value))


    def write_vec2f(self, value: Vec2F):
        self.write([value.x, value.y])


    def write_vec3f(self, value: Vec3F):
        self.write([value.x, value.y, value.z])


    def write_box6f(self, value: Box6F):
        self.write([value.min.x, value.min.y, value.min.z, value.max.x, value.max.y, value.max.z])
