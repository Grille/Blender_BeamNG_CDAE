import os
import shutil
import bpy
import struct

from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from enum import Enum

from .cdae_builder import CdeaBuilder
from .cdae_v31 import CdaeV31
from .material_libary import MaterialLibary

# pyright: reportInvalidTypeForm=false

class WriteMode(str, Enum):
    NONE = "NONE"
    APPEND = "APPEND"
    OVERRIDE = "OVERRIDE"
    REPLACE = "REPLACE"


def update_fps(self, ctx):
    fps = self.anim_samples / self.anim_duration
    if self.anim_fps != fps:
        self.anim_fps = fps


def update_samples(self, ctx):
    samples = round(self.anim_duration * self.anim_fps)
    if self.anim_samples != samples:
        self.anim_samples = samples


class ExportBase(Operator, ExportHelper):

    write_file: BoolProperty(name="Write File", default=True)
    use_transforms: BoolProperty(name="Use Transforms", default=True)
    build_scene_tree: BoolProperty(
        name="Build Scene Tree", default=True,
        description="Builds a BeamNG Scene Tree for LOD, Collision and Billboards, disable this if you just want to drop objects into BeamNG."
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
        default=WriteMode.REPLACE,
    )

    material_write_mode: EnumProperty(
        name="Write Mode",
        description="How materials are written",
        items=[
            (WriteMode.NONE, "None", "Don't write any materials"),
            (WriteMode.APPEND, "Append", "Append new materials, keep existing"),
            (WriteMode.OVERRIDE, "Override", "Override existing materials"),
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
        name="Default",
        items=[
            ("1.0", "V1",""),
            ("1.5", "V1.5 (PBR)", ""),
        ],
        default="1.5",
    )

    write_animations: BoolProperty(name="Enabled", default=False)
    anim_frame_start: IntProperty(name="Start Frame")
    anim_frame_end: IntProperty(name="End Frame", default=100)
    anim_samples: IntProperty(name="Samples", default=100, min=2, update=update_fps)
    anim_duration: FloatProperty(name="Duration (Seconds)", default=100, min=0.01, update=update_fps)
    anim_fps: FloatProperty(name="FPS", default=1, min=0, update=update_samples)


    def execute_write_geometry(self, cdae: CdaeV31, filepath: str):
        pass


    def execute(self, context):
        
        builder = CdeaBuilder()
        builder.use_transforms = self.use_transforms
        builder.tree.build_scene_tree = self.build_scene_tree
        self.builder_settings(builder)
        builder.tree.add_selected()
        builder.build()

        filepath: str = self.filepath
        dirpath = os.path.dirname(filepath)

        if self.write_file:
            self.execute_write_geometry(builder.cdae, filepath)

        self.export_materials(dirpath, builder.materials)

        return {'FINISHED'}
    

    def builder_settings(self, builder: CdeaBuilder):
        pass

    
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
        libary.default_version = float(self.material_default)
        if (material_mode != WriteMode.REPLACE):
            libary.try_load(mat_filepath)

        for bmat in materials:
            if material_mode == WriteMode.APPEND:
                libary.append_bmat(bmat)
            else:
                libary.overwrite_bmat(bmat)

        save_textures = WriteMode[self.save_textures]
        if save_textures != WriteMode.NONE:
            self.export_textures(tex_dirpath, libary, save_textures)

        for newmat in libary.new_materials:
            newmat.add_relpath(tex_relpath)

        libary.save(mat_filepath)
        print(f"Write materials.json: {mat_filepath}")
        

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        write_file = self.write_file

        scn_box = layout.box()
        scn_box.label(text="Scene", icon='SCENE_DATA')
        scn_box.prop(self, "write_file")
        if write_file:
            scn_box.prop(self, "build_scene_tree")
            scn_box.prop(self, "use_transforms")
            #geo_box = layout.box()
            #geo_box.label(text="Geometry", icon='MESH_DATA')
            #geo_box.prop(self, "apply_scale")

        mat_box = layout.box()
        mat_box.label(text="Materials", icon='MATERIAL')
        mat_box.prop(self, "material_write_mode")
        if self.material_write_mode != WriteMode.NONE:
            mat_box.prop(self, "material_default")
            mat_box.prop(self, "material_path")
            mat_box.label(text="Textures", icon='TEXTURE')
            mat_box.prop(self, "save_textures")
            if self.save_textures != WriteMode.NONE:
                mat_box.prop(self, "texture_path")

        if write_file:
            ani_box = layout.box()
            ani_box.label(text="Animations", icon='ANIM_DATA')
            ani_box.prop(self, "write_animations")
            ani_box.use_property_split = False
            if self.write_animations:
                ani_box.label(text="WIP", icon='ERROR')
                ani_box.prop(self, "anim_frame_start")
                ani_box.prop(self, "anim_frame_end")
                ani_box.prop(self, "anim_duration")
                ani_box.prop(self, "anim_samples")
                ani_box.prop(self, "anim_fps")