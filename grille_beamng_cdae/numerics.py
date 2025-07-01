class Vec2F:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class Vec3F:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    @staticmethod
    def create_empty():
        return Vec3F(0, 0, 0)


class Vec4F:
    def __init__(self, x: float, y: float, z: float, w: float):
        self.x = x
        self.y = y
        self.z = z
        self.w = w


class Quat4F(Vec4F):
    pass


class Box6F:
    def __init__(self, min: Vec3F, max: Vec3F):
        self.min = min
        self.max = max

    @staticmethod
    def create_empty():
        return Box6F(Vec3F.create_empty(), Vec3F.create_empty())
