import os
import bpy

from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty

from ..beamng.material.material_builder import MaterialBuilder
from ..beamng.material.material_parser import MaterialParser

# pyright: reportInvalidTypeForm=false

class OT_CreateBeamNgMaterial(Operator):
    bl_idname = "grille.create_beamng_material"
    bl_label = "Create BeamNG Material"
    bl_description = "Save current settings as a preset"

    version: bpy.props.FloatProperty(name="version", default=1.0)

    def execute(self, context):
        bmat = context.material
        version: float = self.version

        builder = MaterialBuilder(version)
        mat = builder.build_from_bmat(bmat)
        parser = MaterialParser(version)
        parser.parse_to_bmat(mat, bmat)

        return {'FINISHED'}



class MaterialOperators:

  @staticmethod
  def register():
      bpy.utils.register_class(OT_CreateBeamNgMaterial)


  @staticmethod
  def unregister():
      bpy.utils.unregister_class(OT_CreateBeamNgMaterial)