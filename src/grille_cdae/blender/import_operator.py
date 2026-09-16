from grille_cdae.common import *

from bpy_extras.io_utils import ImportHelper

from ..beamng.cdae.io import *
from ..beamng.cdae.parser import CdaeParser
from .local_storage import LocalStorage
from .presets_operators import OpPresetsUtils, PresetOperator



class FileFormat(StrEnum):
    NONE = "NONE"
    DAE = ".dae"
    CDAE = ".cdae"
    DTS = ".dts"


class ImportCdae(PresetOperator, ImportHelper):
    
    bl_idname = "grille.import_beamng_cdae"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"

    filter_glob: str

    validate_meshes: bool
    debug_dump: bool
    debug_dump_key: str

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
    

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        OpPresetsUtils.draw(self, context)

        layout.prop(self, "validate_meshes")
        layout.prop(self, "debug_dump")
        if self.debug_dump:
            layout.prop(self, "debug_dump_key")

ImportCdae.anotate(
    filter_glob = props.String(default="*.dae;*.cdae;*.json", options={'HIDDEN'}),
    validate_meshes = props.Bool(name="Validate Meshes", default=True),
    debug_dump = props.Bool(name="Debug Info Enabled", default=False),
    debug_dump_key = props.String(name="Key", default="debug_cdae"),
)



class ImportRegistry:
    __slots__ = ()


    @staticmethod
    def menu_func(menu: basetypes.Menu, context: bpy.types.Context):
        menu.layout.operator(ImportCdae.bl_idname, text="BeamNG (.dae/.cdae)")


    @staticmethod
    def register():
        bpy.utils.register_class(ImportCdae)
        bpy.types.TOPBAR_MT_file_import.append(ImportRegistry.menu_func) # pyright: ignore[reportArgumentType]


    @staticmethod
    def unregister():
        bpy.types.TOPBAR_MT_file_import.remove(ImportRegistry.menu_func) # pyright: ignore[reportArgumentType]
        bpy.utils.unregister_class(ImportCdae)