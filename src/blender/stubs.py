import bpy
import typing

# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=information


if typing.TYPE_CHECKING:

    class Operator(bpy.types.Operator):
        filepath: str
        layout: bpy.types.UILayout
        def execute(self, context: bpy.types.Context) -> set[str]:...
        def invoke(self, context: bpy.types.Context, event: bpy.types.Event)-> set[str]:...
        def draw(self, context: bpy.types.Context) -> None:...
        def check(self, context: bpy.types.Context) -> bool:...

    class Panel(bpy.types.Panel):
        layout: bpy.types.UILayout
        def draw(self, context: bpy.types.Context) -> None:...
        @classmethod
        def poll(cls, context: bpy.types.Context) -> bool:...

    class Menu(bpy.types.Menu):
        layout: bpy.types.UILayout
        def draw(self, context: bpy.types.Context) -> None:...
        @classmethod
        def poll(cls, context: bpy.types.Context) -> bool:...

    class ShaderNodeCustomGroup(bpy.types.ShaderNodeCustomGroup):
        def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):...


else:

    Operator = bpy.types.Operator
    Panel = bpy.types.Panel
    ShaderNodeCustomGroup = bpy.types.ShaderNodeCustomGroup
    Menu = bpy.types.Menu
