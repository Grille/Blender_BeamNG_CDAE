from grille_cdae.common import *

from bpy_extras.io_utils import ImportHelper

from ..beamng.cdae.io import *
from ..beamng.cdae.parser import CdaeParser
from .local_storage import LocalStorage
from .presets_operators import OpPresetsUtils, PresetOperator
from .uilayout import UILayoutCtx



class FileFormat(StrEnum):
    NONE = "NONE"
    DAE = ".dae"
    CDAE = ".cdae"
    DTS = ".dts"


class ImportCdae(PresetOperator, ImportHelper):
    
    bl_idname = "grille.import_beamng_cdae"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"



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

        pinfo = ImportCdaePInfo

        parser.validate = pinfo.validate_meshes[self]
        parser.debug = pinfo.debug_dump[self]
        parser.parse(cdae)

        if pinfo.debug_dump[self]:
            LocalStorage.set(pinfo.debug_dump_key[self], DebugWriter.to_dict(cdae))


        return {'FINISHED'}
    

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        OpPresetsUtils.draw(self, context)
        ui = UILayoutCtx(layout, self)
        pinfo = ImportCdaePInfo

        ui.prop(pinfo.validate_meshes)
        ui.prop(pinfo.debug_dump)
        if pinfo.debug_dump[self]:
            ui.prop(pinfo.debug_dump_key)


class ImportCdaePInfo(PropertyInfoGroup):
    pinfo = PropertyInfoFactory()

    filter_glob = pinfo.str("", "*.dae;*.cdae;*.json") #options={'HIDDEN'}
    validate_meshes = pinfo.bool("Validate Meshes", True)
    debug_dump = pinfo.bool("Debug Info Enabled", False)
    debug_dump_key = pinfo.str("Key", "debug_cdae")

ImportCdaePInfo.pinfo.annotate(ImportCdae)



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