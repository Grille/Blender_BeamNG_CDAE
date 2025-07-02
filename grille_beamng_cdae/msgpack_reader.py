import struct
import msgpack
import zstandard

from io import BufferedReader

from .numerics import *


class MsgpackReader:

    def __init__(self, unpacker: msgpack.Unpacker):
        self.unpacker = unpacker


    @staticmethod
    def from_bytes(data: bytes) -> 'MsgpackReader':
        unpacker = msgpack.Unpacker()
        unpacker.feed(data)
        return MsgpackReader(unpacker)
        

    @staticmethod
    def from_stream(stream: BufferedReader) -> 'MsgpackReader':
        return MsgpackReader.from_bytes(stream.read())
    

    def read_next(self) -> any:
        try:
            return next(self.unpacker)
        except StopIteration:
            return None
        

    def read_bytes(self) -> bytes:
        return self.read_next()
        

    def read_str(self) -> str:
        return self.read_next()
        

    def read_dict(self) -> dict[str, any]:
        return self.read_next()
        

    def read_float(self):
        value = self.read_next()

        if isinstance(value, float):
            return value
        
        if isinstance(value, int):
            return float(value)
        
        raise Exception()


    def read_int32(self):
        value = self.read_next()

        if isinstance(value, float):
            return int(value)
        
        if isinstance(value, int):
            return value
        
        raise Exception()


    def read_float_list(self, size: int) -> list[float]:
        value = self.read_next()

        if isinstance(value, list):
            if (len(value) != size):
                raise Exception()
            return value
            
        elif isinstance(value, bytes):
            if (len(value) != size * 4):
                raise Exception()
            return list(struct.unpack(f"<{size}f", value))
            
        else:
            raise Exception("float array is neither list[float] nor bytes")
        

    def read_vec2f(self):
        values = self.read_float_list(2)
        return Vec2F(values[0], values[1])


    def read_vec3f(self):
        values = self.read_float_list(3)
        return Vec3F(values[0], values[1], values[2])
    

    def read_box6f(self):
        values = self.read_float_list(6)
        min = Vec3F(values[0], values[1], values[2])
        max = Vec3F(values[3], values[4], values[5])
        return Box6F(min, max)

