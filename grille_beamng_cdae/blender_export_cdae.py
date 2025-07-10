import os
import bpy
import struct

from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty

from . import cdae_serializer_binary as CdaeBinarySerializer
from.cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .cdae_components import *


class ExportCdae(Operator, ExportHelper):
    bl_idname = "grille.export_beamng_cdae"
    bl_label = "Export BeamNG"
    filename_ext = ".cdae"
    filter_glob = StringProperty(default="*.cdae", options={'HIDDEN'})


    def execute(self, context):
        builder = CdeaBuilder()
        builder.tree.add_selected()
        builder.build()

        CdaeBinarySerializer.write_to_file(builder.cdae, self.filepath)

        return {'FINISHED'}
    
    
    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ExportCdae.bl_idname, text="BeamNG (.cdae)")
        