import grille_cdae.common.basetypes._stubs as _stubs
import grille_cdae.common.property_info as _pi



class _Extension():
    @classmethod
    def annotate(cls, **props: object):
        _pi.annotate_properties(cls, **props)



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
