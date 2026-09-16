from grille_cdae.common import *

from ..beamng.material.material_parser import MaterialParser, MaterialVersion



class OT_CreateBeamNgMaterial(bpyt.Operator):
    bl_idname = "grille.create_beamng_material"
    bl_label = "Create BeamNG Material"
    bl_description = "Save current settings as a preset"

    version: float

    def execute(self, context):
        parser = MaterialParser(MaterialVersion(self.version))
        parser.force_alpha_clip = True
        assert context.material is not None
        parser.convert_bmat(context.material)

        return {'FINISHED'}

bpyp.anotate_properties(OT_CreateBeamNgMaterial,
    version = bpy.props.FloatProperty(name="version", default=1.0)
)



class MaterialOperators:

  @staticmethod
  def register():
      bpy.utils.register_class(OT_CreateBeamNgMaterial)


  @staticmethod
  def unregister():
      bpy.utils.unregister_class(OT_CreateBeamNgMaterial)