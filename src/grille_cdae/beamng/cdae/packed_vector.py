from __future__ import annotations

import numpy as np

from typing import Protocol


class _PPackable(Protocol):
    def unpack(self, data: bytes): ...
    def pack(self) -> bytes: ...



class _PackDisabled(_PPackable): ...


class PPackedVector(Protocol):
    element_count: int
    element_size: int
    data: bytes


class PackedVector[TNumpy: np.generic, TPack: _PPackable]:

    def __init__(self, tnumpy: type[TNumpy] = np.float32, tpack: type[TPack] = _PackDisabled, element_size = 4):
        self._t_numpy = tnumpy
        self._t_pack = tpack
        self.element_count: int = 0
        self.element_size: int = element_size
        self.data = bytes()
    

    def unpack_list(self) -> list[TPack]:
        unpacked: list[TPack] = []
        for chunk in self:
            node = self._t_pack()
            node.unpack(chunk)
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


    def __getitem__(self, index: int):
        start = index * self.element_size
        end = start + self.element_size
        return self.data[start:end]
    

    def alloc(self, element_count: int):
        self.element_count = element_count
        self.data = bytes(bytearray(self.element_count * self.element_size))
    

    def to_numpy_array(self) -> np.typing.NDArray[TNumpy]:
        size = (len(self.data) // self.element_count) // np.dtype(self._t_numpy).itemsize if self.element_count != 0 else 0
        return np.frombuffer(self.data, self._t_numpy, self.element_count * size)
    

    def set_numpy_array(self, array: np.typing.NDArray[TNumpy]):
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
        


vec = PackedVector()
