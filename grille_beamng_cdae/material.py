import bpy


class Material:

    def __init__(self, dict: dict[str, any] = None):
        self.dict = {} if dict is None else dict


    @classmethod
    def from_bmat(cls, bmat: bpy.types.Material):
        material = cls()

        material.name = bmat.name

        return material
    

    @property
    def name(self) -> str:
        return self.dict.get("name", "")

    @name.setter
    def name(self, value: str):
        self.dict["name"] = value