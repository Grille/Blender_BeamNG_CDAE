from __future__ import annotations

import numpy as np

from typing import Protocol, Final, Self



class _PPackable(Protocol):
    @classmethod
    def unpack(cls, data: bytes) -> Self: ...
    def pack(self) -> bytes: ...



class _PackDisabled(_PPackable): ...


 
class PPackedVector(Protocol):
    element_count: int
    element_size: int
    data: bytes



class PackedVector[TNumpy: np.generic, TPack: _PPackable]:

    __slots__ = "_t_numpy", "_t_pack", "element_count", "element_size", "component_size", "component_count", "data"
    def __init__(self, tnumpy: type[TNumpy] = np.float32, tpack: type[TPack] = _PackDisabled, element_size: int | None = None):
        self._t_numpy: Final = tnumpy
        self._t_pack: Final = tpack
        
        self.component_size: Final = np.dtype(self._t_numpy).itemsize
        self.element_size: Final = self.component_size if element_size is None else element_size
        self.component_count: Final = self.element_size // self.component_size

        self.element_count: int = 0
        self.data = bytes()
    

    def unpack_list(self) -> list[TPack]:
        unpacked: list[TPack] = []
        for chunk in self:
            node = self._t_pack.unpack(chunk)
            unpacked.append(node)
        return unpacked
    

    def pack_list(self, list: list[TPack]):
        data_array = bytearray()
        for obj in list:
            chunk = obj.pack()
            data_array.extend(chunk)
 
        self.element_count = len(list)
        self.data = bytes(data_array)


    def __iter__(self):
        for i in range(self.element_count):
            yield self[i]


    def __len__(self): return self.element_count


    def __bool__(self): return self.element_count > 0


    def __getitem__(self, index: int):
        start = index * self.element_size
        end = start + self.element_size
        return self.data[start:end]
    

    def alloc(self, element_count: int):
        self.element_count = element_count
        self.data = bytes(bytearray(self.element_count * self.element_size))


    def new_array(self, element_count: int):
        return np.empty(element_count * self.component_count, dtype=self._t_numpy)
    

    def to_array(self) -> np.typing.NDArray[TNumpy]:
        return np.frombuffer(self.data, self._t_numpy, self.element_count * self.component_count)
    

    def set_array(self, array: np.typing.NDArray[TNumpy]):
        self.data = array.tobytes()
        self.element_count = len(self.data) // self.element_size


    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, PackedVector):
            return False
        return (
            self.element_count == other.element_count
            and self.element_size == other.element_size
            and self.data == other.data
        )
    

    def __hash__(self):
        return hash((self.element_count, self.element_size, self.data))