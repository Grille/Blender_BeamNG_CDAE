import os
import shutil
import bpy
import struct
import time

from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from enum import Enum

from .blender_object_collector import ObjectCollector
from .beamng_asset import DaeAsset
from .cdae_builder_tree import CdaeTreeBuildMode
from .cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .material_libary import MaterialLibary
from .material_builder import MaterialBuilder
from .local_storage import LocalStorage
from .blender_op_presets import OpPresetsUtils
from . import cdae_serializer_text as CdaeTextSerializer
from . import cdae_serializer_binary as CdaeBinarySerializer

# pyright: reportInvalidTypeForm=false

class WriteMode(str, Enum):
    NONE = "NONE"
    APPEND = "APPEND"
    OVERRIDE = "OVERRIDE"
    REPLACE = "REPLACE"


class FileFormat(str, Enum):
    NONE = "NONE"
    DAE = ".dae"
    CDAE = ".cdae"
    DTS = ".dts"


def update_fps(self: 'ExportBase', ctx):
    fps = self.anim_samples / self.anim_duration
    if self.anim_fps != fps:
        self.anim_fps = fps


def update_samples(self: 'ExportBase', ctx):
    samples = round(self.anim_duration * self.anim_fps)
    if self.anim_samples != samples:
        self.anim_samples = samples



class ExportBase(Operator, ExportHelper):

    bl_idname = "grille.export_beamng_dae"
    bl_label = "Export BeamNG"
    filename_ext = ""
    initialized = False

    selection_only: BoolProperty(name="Selection Only", default=True, description="Use selected Objects.")
    include_children: BoolProperty(name="Include Children", default=False, description="Include all Children of selected Objects.")
    include_hidden: BoolProperty(name="Include Hidden", default=False, description="Include Objects that are hidden in Viewport.")

    temp_presets_file: StringProperty(default="export")
    temp_presets_selection: StringProperty()

    file_format: EnumProperty(
        name="Format",
        description="File format used for geometry",
        items=[
            (FileFormat.NONE, "None", ""),
            (FileFormat.DAE, "Text (.dae)", ""),
            (FileFormat.CDAE, "Binary (.cdae)", ""),
            #(FileFormat.DTS, "Torque3D (.dts)", ""),
        ],
        default=FileFormat.DAE,
    )
    file_readonly: BoolProperty(name="Readonly", default=False)

    limit_precision_enabled: BoolProperty(name="Limit Precision", default=False)
    limit_precision_dp: IntProperty(name="Decimal Places", default=4, min=0)
    asset_file_enabled: BoolProperty(name="Write '-.asset.json'", default=True)

    use_transforms: BoolProperty(name="Use Transforms", default=True)
    compression_enabled: BoolProperty(name="Compression", default=True)
    build_mode: EnumProperty(
        name="Build Mode",
        description="",
        items=[
            (CdaeTreeBuildMode.FLAT_DUMP, "Flat Dump", "Objects get added without any hierarchy, \nuse if you want to display all exported objects."),
            (CdaeTreeBuildMode.BLENDER_HIERARCHY, "Blender Hierarchy", "Uses Blender object hierarchy like in the legacy Collada addon."),
            (CdaeTreeBuildMode.DAE_NODE_TREE, "Collada Node Tree (R)", "Builds Collada (DAE/Text) node tree using assigned roles."),
        ],
        default=CdaeTreeBuildMode.BLENDER_HIERARCHY,
    )

    apply_scale: BoolProperty(name="Apply Scale", default=True)

    save_textures: EnumProperty(
        name="Write Mode",
        description="How textures are saved",
        items=[
            (WriteMode.NONE, "None", "Don't save any textures"),
            (WriteMode.APPEND, "Missing", "Save missing textures"),
            (WriteMode.REPLACE, "Replace", "Save all textures"),
        ],
        default=WriteMode.APPEND,
    )

    material_write_mode: EnumProperty(
        name="Write Mode",
        description="How materials are written",
        items=[
            (WriteMode.NONE, "None", "Don't write any materials"),
            (WriteMode.APPEND, "Append", "Append new materials, keep existing"),
            (WriteMode.OVERRIDE, "Override", "Override existing materials, keep other existing"),
            (WriteMode.REPLACE, 'Replace', "Replace materials file")
        ],
        default=WriteMode.APPEND,
    )

    material_path: StringProperty(
        name="Path",
        description="(Relative) Path to your materials file",
        default="./main.materials.json",
    )

    texture_path: StringProperty(
        name="Path",
        description="(Relative) Path to your textures",
        default="./image.tex",
    )

    material_default: EnumProperty(
        name="Default Ver",
        items=[
            ("0.0", "Auto Detect", ""),
            ("1.0", "V1", ""),
            ("1.5", "V1.5 (PBR)", ""),
        ],
        default="0.0",
    )

    write_animations: BoolProperty(name="Enabled", default=False)
    anim_frame_start: IntProperty(name="Start Frame")
    anim_frame_end: IntProperty(name="End Frame", default=100)
    anim_samples: IntProperty(name="Samples", default=100, min=2, update=update_fps)
    anim_duration: FloatProperty(name="Duration (Seconds)", default=100, min=0.01, update=update_fps)
    anim_fps: FloatProperty(name="FPS", default=1, min=0, update=update_samples)

    filter_glob: StringProperty(default="*.dae;*.cdae;*.json", options={'HIDDEN'})


    def execute_write_geometry(self, cdae: CdaeV31, filepath: str):

        CdaeTextSerializer.write_to_file(cdae, filepath)
        print(f"Write dae: {filepath}")


    def invoke(self, context, event):
        if not ExportBase.initialized:
            OpPresetsUtils.apply_default(self)
            ExportBase.initialized = True
        return super().invoke(context, event)


    def execute(self, context):
        
        now = time.time()

        def log(name: str):
            nonlocal now
            delta = time.time()-now
            now = time.time()
            print(f"{name}: {delta}")

        if self.file_format == FileFormat.NONE:
            build_mode = CdaeTreeBuildMode.NONE
        else:
            build_mode = self.build_mode

        collector = ObjectCollector()
        collector.include_hidden = self.include_hidden
        collector.include_children = self.include_children
        if self.selection_only:
            collector.collect_selected()
        else:
            collector.collect_scene()
        log("collect")

        builder = CdeaBuilder()
        builder.readonly = self.file_readonly
        builder.tree.build_mode = build_mode
        sampler = builder.sampler
        sampler.sample_transforms_enabled = self.use_transforms
        sampler.sample_keyframes_enabled = self.write_animations
        sampler.start = self.anim_frame_start
        sampler.end = self.anim_frame_end
        sampler.sample_count = self.anim_samples
        sampler.duration = self.anim_duration

        builder.tree.add_objects(collector.objects)
        builder.build()
        log("build")

        filepath: str = self.filepath
        dirpath = os.path.dirname(filepath)

        match self.file_format:
            case FileFormat.DAE:
                CdaeTextSerializer.limit_precision_enabled = self.limit_precision_enabled
                CdaeTextSerializer.limit_precision_dp = self.limit_precision_dp
                CdaeTextSerializer.write_to_file(builder.cdae, filepath)
            case FileFormat.CDAE:
                CdaeBinarySerializer.write_to_file(builder.cdae, filepath, self.compression_enabled)
        log("write file")

        if self.asset_file_enabled:
            self.write_asset_file(filepath, builder.cdae)

        self.export_materials(dirpath, builder.materials)
        log("misc")

        return {'FINISHED'}
    

    def check(self, context):
        format: FileFormat = self.file_format
        path: str = self.filepath
        filename, ext = os.path.splitext(path)

        if format != FileFormat.NONE and format != ext:
            self.filepath = f"{filename}{format}"
            return True
    

    def export_textures(self, dirpath: str, libary: MaterialLibary, mode: WriteMode):
        texture_names: set[str] = set()

        for mat in libary.new_materials:
            mat.add_texture_names_to(texture_names)

        for texname in texture_names:
            texpath = os.path.join(dirpath, texname)
            if not os.path.isfile(texpath) or mode != WriteMode.APPEND:
                texture: bpy.types.Image = bpy.data.images[texname]
                srcpath = bpy.path.abspath(texture.filepath)
                shutil.copy2(srcpath, texpath)


    def export_materials(self, dirpath: str, materials: list[bpy.types.Material]):

        material_mode = WriteMode[self.material_write_mode]
        if material_mode == WriteMode.NONE:
            return
        
        def get_abs(path, ext): 
            res_filepath = os.path.abspath(path if os.path.isabs(path) else os.path.join(dirpath, path)).lower()
            if not res_filepath.endswith(ext):
                res_filepath = os.path.join(res_filepath, ext)
                #res_filepath = f"{res_filepath}{ext}"
            res_dirpath = os.path.dirname(res_filepath)
            return (res_filepath, res_dirpath)


        mat_filepath, mat_dirpath = get_abs(self.material_path, "main.materials.json")
        tex_filepath, tex_dirpath = get_abs(self.texture_path, ".tex")
        tex_relpath = os.path.relpath(tex_dirpath, mat_dirpath)

        os.makedirs(mat_dirpath, exist_ok=True)
        os.makedirs(tex_dirpath, exist_ok=True)


        libary = MaterialLibary()

        if (material_mode != WriteMode.REPLACE):
            libary.try_load(mat_filepath)

        for bmat in materials:
            if material_mode == WriteMode.APPEND and libary.bmat_exists(bmat):
                continue

            builder = MaterialBuilder()
            builder.default_version = float(self.material_default)
            builder.build_from_bmat(bmat)
            libary.set_material(builder.material)

        save_textures = WriteMode[self.save_textures]
        if save_textures != WriteMode.NONE:
            self.export_textures(tex_dirpath, libary, save_textures)

        for newmat in libary.new_materials:
            newmat.add_relpath(tex_relpath)

        libary.save(mat_filepath)
        print(f"Write materials.json: {mat_filepath}")


    def write_asset_file(self, filepath: str, cdae: CdaeV31):

        filename, ext = os.path.splitext(filepath)
        assetpath = f"{filename}.dae.asset.json"

        def get_bb_autobillboard():
            for detail in cdae.unpack_details():
                print(f"Found {cdae.names[detail.nameIndex]}")
                if cdae.names[detail.nameIndex] == "bb_autobillboard":
                    return detail

        detail = get_bb_autobillboard()
        print(f"DETAIL {detail}")

        if detail:
            asset = DaeAsset()
            asset.create_imposter_from_deatil(detail)
            asset.save(assetpath)
        else:
            if os.path.exists(assetpath):
                os.remove(assetpath)
        

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        OpPresetsUtils.draw(self, layout)

        format = self.file_format
        write_file = format != FileFormat.NONE

        def alert(obj, text):
            row = obj.row()
            row.alert = True
            row.label(text=text, icon="ERROR")

        box = layout.box()
        box.label(text="Input (Object Collecton)", icon='RESTRICT_SELECT_ON')
        box.prop(self, "selection_only")
        if self.selection_only:
            box.prop(self, "include_children")
        box.prop(self, "include_hidden")
        
        box = layout.box()
        box.label(text="File", icon='FILE_NEW')
        box.prop(self, "file_format")

        if format == FileFormat.DAE:
            box.prop(self, "limit_precision_enabled")
            if self.limit_precision_enabled:
                box.prop(self, "limit_precision_dp")
            box.prop(self, "asset_file_enabled")

        if format == FileFormat.CDAE:
            box.prop(self, "compression_enabled")
            alert(box, f"Unstable, use 'Text (.dae)' instead.")

        if write_file:
            #box.prop(self, "file_readonly")
            box = layout.box()
            box.label(text="Scene", icon='SCENE_DATA')
            box.prop(self, "build_mode")
            box.prop(self, "use_transforms")
            box.label(text="Geometry", icon='MESH_DATA')
            box.prop(self, "apply_scale")

            box = layout.box()
            box.label(text="Animations", icon='ANIM_DATA')
            box.prop(self, "write_animations")
            box.use_property_split = False
            if self.write_animations:
                box.prop(self, "anim_frame_start")
                box.prop(self, "anim_frame_end")
                box.prop(self, "anim_duration")
                box.prop(self, "anim_samples")
                box.prop(self, "anim_fps")
                if self.anim_duration > 500:
                    alert(box, f"Long animations can break.")

        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(self, "material_write_mode")
        if self.material_write_mode != WriteMode.NONE:
            box.prop(self, "material_default")
            box.prop(self, "material_path")
            box = box.box()
            box.label(text="Textures", icon='TEXTURE')
            box.prop(self, "save_textures")
            if self.save_textures != WriteMode.NONE:
                box.prop(self, "texture_path")


    @staticmethod
    def menu_func(self, context):
        self.layout.operator(ExportBase.bl_idname, text="BeamNG (.dae/.cdae/.json)")



class ExportRegistry:

    @staticmethod
    def register():
        bpy.utils.register_class(ExportBase)
        bpy.types.TOPBAR_MT_file_export.append(ExportBase.menu_func)


    @staticmethod
    def unregister():
        bpy.types.TOPBAR_MT_file_export.remove(ExportBase.menu_func)
        bpy.utils.unregister_class(ExportBase)