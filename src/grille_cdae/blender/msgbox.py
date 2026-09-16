from grille_cdae.common import *

# pyright: reportInvalidTypeForm=false

class MessageBox(basetypes.Operator):
    bl_idname = "grille_beamng_cdae.msgbox"
    bl_label = "My Message Box"

    message: str

    def execute(self, context):
        print("YES clicked")

        return {'FINISHED'}

    def cancel(self, context):
        print("NO clicked")

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.message)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    @staticmethod
    def show_dialog():
        bpy.ops.grille_beamng_cdae.msgbox('INVOKE_DEFAULT', message="Do you want to continue?") # type: ignore

MessageBox.anotate(message = bpy.props.StringProperty(default="Are you sure?"))