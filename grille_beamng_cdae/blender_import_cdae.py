import os
import bpy
import struct
import numpy as np

from . import cdae_serializer_binary as CdaeBinarySerializer
from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty

from .cdae_v31 import CdaeV31
from .cdae_parser import CdaeParser

# pyright: reportInvalidTypeForm=false



class ImportCdae(Operator, ImportHelper):
    
    bl_idname = "grille.import_beamng_cdae"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"

    filter_glob: StringProperty(default="*.cdae", options={'HIDDEN'})
    validate_meshes: BoolProperty(name="Validate Meshes", default=True)
    debug_info: BoolProperty(name="Debug Info", default=False)


    def execute(self, context):
        cdae = CdaeBinarySerializer.read_from_file(self.filepath)
        cdae.print_debug()
        
        parser = CdaeParser()
        parser.validate = self.validate_meshes
        parser.debug = self.debug_info
        parser.parse(cdae)

        return {'FINISHED'}
    

    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ImportCdae.bl_idname, text="BeamNG (.cdae)")


    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "validate_meshes")
        layout.prop(self, "debug_info")