from bpy.props import StringProperty

from . import cdae_serializer_text as CdaeTextSerializer
from .blender_export import ExportBase

# pyright: reportInvalidTypeForm=false



class ExportDae(ExportBase):
    
    bl_idname = "grille.export_beamng_dae"
    bl_label = "Export BeamNG"
    filename_ext = ".dae"

    filter_glob: StringProperty(default="*.dae", options={'HIDDEN'})


    def execute_write_geometry(self, cdae, filepath):
        CdaeTextSerializer.write_to_file(cdae, filepath)
        print(f"Write dae: {filepath}")

    
    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ExportDae.bl_idname, text="BeamNG (.dae)")