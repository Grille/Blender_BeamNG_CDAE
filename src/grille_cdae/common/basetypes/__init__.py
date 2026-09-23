import grille_cdae.common.basetypes._stubs as _stubs
import grille_cdae.common.props as _props



class _Extension():
    @classmethod
    def anotate(cls, **props: object):
        _props.anotate_properties(cls, **props)



class Operator(_stubs.Operator, _Extension):
    pass



class Panel(_stubs.Panel, _Extension):
    pass



class Menu(_stubs.Menu, _Extension):
    pass



class ShaderNodeCustomGroup(_stubs.ShaderNodeCustomGroup, _Extension):
    pass



class PropertyGroup(_stubs.PropertyGroup, _Extension):
    pass
