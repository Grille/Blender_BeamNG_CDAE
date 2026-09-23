import typing as _typing
import bpy.types as _t

# pyright: reportIncompatibleMethodOverride=information

type _Result = set[_typing.Any]


class Operator(_t.Operator):
    filepath: str
    layout: _t.UILayout
    def execute(self, context: _t.Context) -> _Result: return super().execute(context)
    def invoke(self, context: _t.Context, event: _t.Event)-> _Result: return super().invoke(context, event)
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    def check(self, context: _t.Context) -> bool: return super().check(context)

class Panel(_t.Panel):
    layout: _t.UILayout
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    @classmethod
    def poll(cls, context: _t.Context) -> bool: return super().poll(context)

class Menu(_t.Menu):
    layout: _t.UILayout
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    @classmethod
    def poll(cls, context: _t.Context) -> bool: return super().poll(context)

class ShaderNodeCustomGroup(_t.ShaderNodeCustomGroup):
    def draw_buttons(self, context: _t.Context, layout: _t.UILayout): return super().draw_buttons(context, layout)

class PropertyGroup(_t.PropertyGroup):
    pass
