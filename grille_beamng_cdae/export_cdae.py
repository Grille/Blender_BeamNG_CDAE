import os
import bpy
import struct

from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty

from .cdae_v31 import CdaeV31
from .cdae_components import *

class ExportCdae(Operator, ExportHelper):
    bl_idname = "export_scene.beamng"
    bl_label = "Export BeamNG"
    filename_ext = ".cdae"
    filter_glob = StringProperty(default="*.cdae", options={'HIDDEN'})

    def execute(self, context):
        cdae = CdaeV31()

        cdae.write_to_file(self.filepath)

        return {'FINISHED'}
    