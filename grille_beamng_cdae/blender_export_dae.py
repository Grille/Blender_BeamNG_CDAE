import os
import bpy
import struct

from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty

from . import cdae_serializer_text as CdaeTextSerializer
from.cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .cdae_components import *


class ExportDae(Operator, ExportHelper):
    bl_idname = "grille.export_beamng_dae"
    bl_label = "Export BeamNG"
    filename_ext = ".dae"
    filter_glob = StringProperty(default="*.dae", options={'HIDDEN'})

    def execute(self, context):
        builder = CdeaBuilder()
        builder.tree.add_objects(set(bpy.context.selected_objects))
        builder.build()

        CdaeTextSerializer.write_to_file(builder.cdae, self.filepath)

        return {'FINISHED'}
    