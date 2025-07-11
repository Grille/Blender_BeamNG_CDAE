import os
import bpy
import struct
import numpy as np

from . import cdae_serializer_binary as CdaeBinarySerializer
from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

from .cdae_v31 import CdaeV31
from .cdae_parser import CdaeParser

class ImportCdae(Operator, ImportHelper):
    bl_idname = "grille.import_beamng_cdae"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"

# pyright: reportInvalidTypeForm=false

    filter_glob: StringProperty(default="*.cdae", options={'HIDDEN'})


    def execute(self, context):
        cdae = CdaeBinarySerializer.read_from_file(self.filepath)
        cdae.print_debug()
        
        parser = CdaeParser()
        parser.parse(cdae)

        return {'FINISHED'}
    

    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ImportCdae.bl_idname, text="BeamNG (.cdae)")