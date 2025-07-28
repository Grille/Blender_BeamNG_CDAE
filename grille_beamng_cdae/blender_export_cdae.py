from bpy.props import StringProperty

from . import cdae_serializer_binary as CdaeBinarySerializer
from .blender_export import ExportBase


class ExportCdae(ExportBase):
    bl_idname = "grille.export_beamng_cdae"
    bl_label = "Export BeamNG"
    filename_ext = ".cdae"

# pyright: reportInvalidTypeForm=false

    filter_glob: StringProperty(default="*.cdae", options={'HIDDEN'})


    def execute_write_geometry(self, cdae, filepath):
        CdaeBinarySerializer.write_to_file(cdae, filepath)
        print(f"Write cdae: {filepath}")

    
    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ExportCdae.bl_idname, text="BeamNG (.cdae)")
        