from typing import Container as _Container
import bpy.types as _t
import grille_cdae.common.props as _props

# pyright: reportIncompatibleMethodOverride=information

type _Result = set[str]

class _Extension():
    @classmethod
    def anotate(cls, **props: _props._PropertyDeferred): # type: ignore
        _props.anotate_properties(cls, **props) # type: ignore

class Operator(_t.Operator, _Extension):
    filepath: str
    layout: _t.UILayout
    def execute(self, context: _t.Context) -> _Result: return super().execute(context) # type: ignore
    def invoke(self, context: _t.Context, event: _t.Event)-> _Result: return super().invoke(context, event) # type: ignore
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    def check(self, context: _t.Context) -> bool: return super().check(context)

class Panel(_t.Panel, _Extension):
    layout: _t.UILayout
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    @classmethod
    def poll(cls, context: _t.Context) -> bool: return super().poll(context)

class Menu(_t.Menu, _Extension):
    layout: _t.UILayout
    def draw(self, context: _t.Context) -> None: return super().draw(context)
    @classmethod
    def poll(cls, context: _t.Context) -> bool: return super().poll(context)

class ShaderNodeCustomGroup(_t.ShaderNodeCustomGroup, _Extension):
    def draw_buttons(self, context: _t.Context, layout: _t.UILayout): return super().draw_buttons(context, layout)

class PropertyGroup(_t.PropertyGroup, _Extension):
    pass
