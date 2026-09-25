from grille_cdae.common import *


class UILayoutCtx[TUI:types.UILayout, T: types.bpy_struct]:
    __slots__ = "layout", "target"

    def __init__(self, layout: TUI, target: T) -> None:
        self.layout = layout
        self.target = target


    def prop(self, prop: str | PropertyInfo[T], *, text: nstr = None):
        key = prop.key if isinstance(prop, PropertyInfo) else prop
        self.layout.prop(self.target, key, text=text)


    def label(self, text="", icon="NONE"):
        self.layout.label(text=text, icon=icon) #type: ignore
        

    def label_error(self, text = "", icon='ERROR'):
        row = self.layout.row()
        row.alert = True
        row.label(text=text, icon=icon) #type: ignore