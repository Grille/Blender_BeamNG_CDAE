import os
import bpy
import struct
import numpy as np

from enum import Enum
from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty

from .io_dae_reader import DaeReader
from .io_cdae_reader import CdaeReader
from .cdae_parser import CdaeParser
from .utils_debug import CdaeJsonDebugger

# pyright: reportInvalidTypeForm=false
class FileFormat(str, Enum):
    NONE = "NONE"
    DAE = ".dae"
    CDAE = ".cdae"
    DTS = ".dts"


class ImportCdae(Operator, ImportHelper):
    
    bl_idname = "grille.import_beamng_cdae"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"

    filter_glob: StringProperty(default="*.dae;*.cdae;*.json", options={'HIDDEN'})

    validate_meshes: BoolProperty(name="Validate Meshes", default=True)
    debug_info: BoolProperty(name="Debug Info", default=False)


    def execute(self, context):
        filepath: str = self.filepath
        filename, extension = os.path.splitext(filepath)
        format = FileFormat(extension.lower())

        match format:
            case FileFormat.DAE:
                cdae = DaeReader.read_from_file(filepath)
            case FileFormat.CDAE:
                cdae = CdaeReader.read_from_file(filepath)
            case _:
                raise Exception()

        cdae.print_debug()
        
        parser = CdaeParser()
        parser.validate = self.validate_meshes
        parser.debug = self.debug_info
        parser.parse(cdae)

        if self.debug_info:
            CdaeJsonDebugger.store(cdae)


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