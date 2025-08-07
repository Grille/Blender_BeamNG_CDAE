
import os
import json
import bpy

from enum import Enum

from .blender_material_properties import MaterialProperties
from .material import Material

class MaterialLibary:

    def __init__(self):
        self.materials: dict[str, Material] = {}
        self.new_materials: list[Material] = []
        self.default_version: float = 1.5


    def try_load(self, filepath: str):
        try:
            self.load(filepath)
            return True
        except:
            return False


    def load(self, filepath: str):
        with open(filepath, 'r') as f:
            data = json.load(f)

        if (not isinstance(data, dict)):
            raise Exception(f"Unexpected json data type.")
        
        rawdict: dict[str, dict[str, any]] = data

        for key, value in rawdict.items():
            self.materials[key] = Material(value)


    def save(self, filepath: str):
        rawdict = {}
        for key, material in self.materials.items():
            rawdict[key] = material.dict
        
        with open(filepath, 'w') as f:
            json.dump(rawdict, f, indent=4)


    def append_bmat(self, bmat: bpy.types.Material):
        if bmat.name in self.materials:
            return
        self.overwrite_bmat(bmat)


    def overwrite_bmat(self, bmat: bpy.types.Material):

        version = float(getattr(bmat, MaterialProperties.VERSION))
        if version == 0.0:
            version = self.default_version

        mat = Material.from_bmat(bmat, version)
        self.materials[mat.name] = mat
        self.new_materials.append(mat)