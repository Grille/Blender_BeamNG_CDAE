from grille_cdae.common import *

import json

from .material import Material



class MaterialLibary:

    def __init__(self):
        # loaded entries stay raw so entries that aren't touched (incl. non Material classes) are saved unchanged
        self.materials: dict[str, SDict] = {}
        self.new_materials: list[Material] = []


    def try_load(self, filepath: str):
        try:
            self.load(filepath)
            return True
        except FileNotFoundError:
            return False


    def load(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if (not isinstance(data, dict)):
            raise Exception(f"Unexpected json data type in {filepath}.")

        rawdict = cast(dict[str, SDict], data)

        for key, value in rawdict.items():
            self.materials[key] = value


    def save(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.materials, f, indent=4, ensure_ascii=False)


    def bmat_exists(self, bmat: bpy.types.Material):
        return bmat.name in self.materials


    def get_material(self, name: str) -> Material | None:
        value = self.materials.get(name)
        return None if value is None else Material(value)


    def set_material(self, mat: Material):
        name = mat.name
        if name is None: raise ValueError()
        self.materials[name] = mat.value_dict
        self.new_materials.append(mat)
