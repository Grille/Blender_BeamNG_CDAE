import os
import bpy
import struct

from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from .cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .material_libary import MaterialLibary


class ExportBase(Operator, ExportHelper):

# pyright: reportInvalidTypeForm=false

    write_geometry: BoolProperty(name="Write Geometry", default=True)

    material_write_mode: EnumProperty(
        name="Write Mode",
        description="How materials are written",
        items=[
            ('NONE', "None", "Don't write any materials"),
            ('APPEND', "Append", "Append new materials, keep existing"),
            ('OVERRIDE', "Override", "Override existing materials"),
            ('REPLACE', 'Replace', "Replace materials file")
        ],
        default='APPEND',
    )

    material_path: StringProperty(
        name="File Path",
        description="(Relative) Path to your materials folder",
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
    

    def export_materials(self, dirpath: str, materials: list[bpy.types.Material]):

        mode: str = self.material_write_mode
        if mode == "NONE":
            return

        if (os.path.isabs(self.material_path)):
            mat_filepath = os.path.abspath(self.material_path)
        else:
            mat_filepath = os.path.abspath(os.path.join(dirpath, self.material_path))

        print(mat_filepath)

        libary = MaterialLibary()
        if (mode != "REPLACE"):
            libary.try_load(mat_filepath)

        for bmat in materials:
            if mode == "APPEND":
                libary.append_bmat(bmat)
            else:
                libary.overwrite_bmat(bmat)

        libary.save(mat_filepath)
    

    def draw(self, context):

        layout = self.layout

        layout.prop(self, "write_geometry")

        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(self, "material_write_mode")
        box.prop(self, "material_path")
    

    def execute_write_geometry(self, cdae: CdaeV31, filepath: str):
        pass