import numpy as np

class PackedVector:

    def __init__(self):
        self.element_count: int
        self.element_size: int
        self.data: bytes


    @classmethod
    def create_empty(cls):
        self = cls()
        self.element_count = 0
        self.element_size = 0
        self.data = bytes(bytearray(0))
        return self


    @classmethod
    def from_numpy_buffer(cls, array: np.ndarray, element_size = 1):
        self = cls()
        self.element_count = len(array)
        self.element_size = element_size * 4
        self.data = array.tobytes()
        return self


    def __iter__(self):
        for i in range(self.element_count):
            yield self[i]


    def __getitem__(self, index):
        start = index * self.element_size
        end = start + self.element_size
        return self.data[start:end]
    

    def to_numpy_buffer(self, type, size = 1):
        return np.frombuffer(self.data, type, self.element_count * size)


