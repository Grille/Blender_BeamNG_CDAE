import os
import bpy
import struct
import numpy as np

from enum import Enum
from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty

from ..beamng.cdae.io import *
from ..beamng.cdae.parser import CdaeParser
from .local_storage import LocalStorage

from .presets_operators import OpPresetsUtils


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
    debug_dump: BoolProperty(name="Debug Info Enabled", default=False)
    debug_dump_key: StringProperty(name="Key", default="debug_cdae")

    temp_presets_initalized: BoolProperty(default=False)
    temp_presets_file: StringProperty(default="import")
    temp_presets_selection: StringProperty()


    def invoke(self, context, event):
        OpPresetsUtils.setup(self)
        return super().invoke(context, event)


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
        parser.debug = self.debug_dump
        parser.parse(cdae)

        if self.debug_dump:
            LocalStorage.set(self.debug_dump_key, DebugWriter.to_dict(cdae))


        return {'FINISHED'}
    

    @staticmethod
    def menu_func(self: 'ImportCdae', context: bpy.types.Context):
        self.layout.operator(ImportCdae.bl_idname, text="BeamNG (.dae/.cdae)")


    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        OpPresetsUtils.draw(self, context)

        layout.prop(self, "validate_meshes")
        layout.prop(self, "debug_dump")
        if self.debug_dump:
            layout.prop(self, "debug_dump_key")