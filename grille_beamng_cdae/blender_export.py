import os
import shutil
import bpy
import struct

from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from enum import Enum

from .cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .material_libary import MaterialLibary

# pyright: reportInvalidTypeForm=false

class WriteMode(Enum):
    NONE = 0
    APPEND = 1
    OVERRIDE = 2
    REPLACE = 3


class ExportBase(Operator, ExportHelper):

    write_geometry: BoolProperty(name="Write Geometry", default=True)

    save_textures: EnumProperty(
        name="Save Textures",
        description="How textures are saved",
        items=[
            (WriteMode.NONE.name, "None", "Don't save any textures"),
            (WriteMode.APPEND.name, "Missing", "Save missing textures"),
            (WriteMode.REPLACE.name, "Replace", "Save all textures"),
        ],
        default=WriteMode.REPLACE.name,
    )

    material_write_mode: EnumProperty(
        name="Write Mode",
        description="How materials are written",
        items=[
            (WriteMode.NONE.name, "None", "Don't write any materials"),
            (WriteMode.APPEND.name, "Append", "Append new materials, keep existing"),
            (WriteMode.OVERRIDE.name, "Override", "Override existing materials"),
            (WriteMode.REPLACE.name, 'Replace', "Replace materials file")
        ],
        default=WriteMode.APPEND.name,
    )

    material_path: StringProperty(
        name="File Path",
        description="(Relative) Path to your materials file",
        default="main.materials.json",
    )


    def execute(self, context):
        
        builder = CdeaBuilder()
        builder.tree.add_selected()
        builder.build()

        filepath: str = self.filepath
        dirpath = os.path.dirname(filepath)

        if self.write_geometry:
            self.execute_write_geometry(builder.cdae, filepath)

        self.export_materials(dirpath, builder.materials)

        return {'FINISHED'}
    

    def export_textures(self, dirpath: str, libary: MaterialLibary, mode: WriteMode):
        texture_names: set[str] = set()

        for mat in libary.new_materials:
            mat.add_texture_names_to(texture_names)

        for texname in texture_names:
            print(dirpath)
            print(texname)
            texpath = os.path.join(dirpath, texname)
            if not os.path.isfile(texpath) or mode != WriteMode.APPEND:
                texture: bpy.types.Image = bpy.data.images[texname]
                srcpath = bpy.path.abspath(texture.filepath)
                shutil.copy2(srcpath, texpath)


    def export_materials(self, dirpath: str, materials: list[bpy.types.Material]):

        material_mode = WriteMode[self.material_write_mode]
        if material_mode == WriteMode.NONE:
            return

        if (os.path.isabs(self.material_path)):
            mat_filepath = os.path.abspath(self.material_path)
        else:
            mat_filepath = os.path.abspath(os.path.join(dirpath, self.material_path))

        libary = MaterialLibary()
        if (material_mode != WriteMode.REPLACE):
            libary.try_load(mat_filepath)

        for bmat in materials:
            if material_mode == WriteMode.APPEND:
                libary.append_bmat(bmat)
            else:
                libary.overwrite_bmat(bmat)

        save_textures = WriteMode[self.save_textures]
        if save_textures != WriteMode.NONE:
            self.export_textures(dirpath, libary, save_textures)

        libary.save(mat_filepath)
        print(f"Write materials.json: {mat_filepath}")
        
    

    def draw(self, context):

        layout = self.layout

        layout.prop(self, "write_geometry")

        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(self, "material_write_mode")
        box.prop(self, "material_path")
        box.prop(self, "save_textures")
    

    def execute_write_geometry(self, cdae: CdaeV31, filepath: str):
        pass