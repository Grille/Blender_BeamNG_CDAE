import numpy as np

from typing import Type, TypeVar

T = TypeVar('T')

class PackedVector:

    def __init__(self):
        self.element_count: int
        self.element_size: int
        self.data: bytes


    @classmethod
    def create_empty(cls, size: int):
        self = cls()
        self.element_count = 0
        self.element_size = size
        self.data = bytes(bytearray(0))
        return self
    

    def unpack_list(self, cls: type[T]) -> list[T]:
        unpacked = []
        for chunk in self:
            node = cls()
            node.unpack(chunk)
            unpacked.append(node)
        return unpacked
    

    def pack_list(self, list: list):
        data_array = bytearray()
        for obj in list:
            chunk = obj.pack()
            data_array.extend(chunk)

        self.element_count = len(list)
        self.data = bytes(data_array)


    def __iter__(self):
        for i in range(self.element_count):
            yield self[i]


    def __getitem__(self, index):
        start = index * self.element_size
        end = start + self.element_size
        return self.data[start:end]
    

    def alloc(self, element_count):
        self.element_count = element_count
        self.data = bytes(bytearray(self.element_count * self.element_size))
    

    def to_numpy_buffer(self, type, size = 1):
        return np.frombuffer(self.data, type, self.element_count * size)
    

    def set_numpy_buffer(self, array: np.ndarray):
        self.data = array.tobytes()
        self.element_count = len(self.data) // self.element_size


