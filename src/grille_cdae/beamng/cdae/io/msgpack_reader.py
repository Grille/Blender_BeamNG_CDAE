# pyright: reportUnknownMemberType=information

from grille_cdae.common import *
import struct
import msgpack

from io import BufferedReader



class MsgpackReader:

    def __init__(self, unpacker: Any):
        self.unpacker = unpacker


    @staticmethod
    def from_bytes(data: bytes) -> 'MsgpackReader':
        unpacker = cast(Any, msgpack.Unpacker(max_buffer_size=0))
        unpacker.feed(data)
        return MsgpackReader(unpacker)
        

    @staticmethod
    def from_stream(stream: BufferedReader) -> 'MsgpackReader':
        return MsgpackReader.from_bytes(stream.read())
    

    def read_next(self) -> Any:
        try:
            return next(self.unpacker)
        except StopIteration:
            return None
        

    def read_bytes(self) -> bytes:
        return self.read_next()
        

    def read_str(self) -> str:
        return self.read_next()
        

    def read_dict(self) -> dict[str, Any]:
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
        

    def read_integerset(self) -> list[bool]:
        value = self.read_next()

        if not isinstance(value, list):
            raise Exception()
        value = cast(list[int], value)
        
        bits: list[bool] = []
        chunk_count: int = value[0]
        chunks: list[int] = value

        if chunk_count != len(chunks):
            raise Exception(f"expected: {chunk_count}, actual: {len(chunks)}")
        
        for chunk in chunks:
            for i in range(32):
                bits.append(bool((chunk >> i) & 1))

        return bits
        
        
    def _read_float_list(self, size: int) -> list[float]:
        value = self.read_next()

        if isinstance(value, list):
            value = cast(list[float], value)
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
        return Vec2F.from_list(self._read_float_list(2))


    def read_vec3f(self):
        return Vec3F.from_list(self._read_float_list(3))
    

    def read_box6f(self):
        return Box6F.from_list(self._read_float_list(6))

