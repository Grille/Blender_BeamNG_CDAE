import bpy
import json

from dataclasses import dataclass, asdict
from functools import singledispatchmethod

from typing import NamedTuple, Any, Callable, Generic, TypeVar, overload
from .enums import *
from .node_walker import NodeWalker
from .enums import *



type SocketAccessor = str | int
type SocketValue = bool | float | int | tuple[float] | str
type LinkSource = 'NodeTreeBuilder.LinkBuilder | SocketValue'
type NTB = 'NodeTreeBuilder'

TNODE = TypeVar('TNODE', bound='bpy.types.Node')


def _get_input_type(src: LinkSource) -> SocketType:
    if isinstance(src, float): return SocketType.Float
    if isinstance(src, int): return SocketType.Integer
    if isinstance(src, tuple): return SocketType.Color if len(src) == 4 else SocketType.Vector
    if isinstance(src, str): return SocketType.Menu
    if isinstance(src, NodeTreeBuilder.LinkBuilder):
        return SocketType.from_data_type(src.get_output().type)
    else:
        raise TypeError(src)


def _get_input_type_tuple(*src: LinkSource):
    return tuple(_get_input_type(s) for s in src)


def _get_input_type_by_precedence(*src: LinkSource):
    return SocketType.select_by_max_precedence(*_get_input_type_tuple(*src))


 
class NodeTreeBuilder:

    class NodeCreator:

        def __init__(self, ntb: 'NodeTreeBuilder'):
            self._ntb = ntb


        @overload
        def node(self, node_type: str, *values: LinkSource | None, **dict) -> 'NTB.LinkBuilder[bpy.types.Node]': ...
        @overload
        def node(self, node_type: type[TNODE], *values: LinkSource | None, **dict) -> 'NTB.LinkBuilder[TNODE]': ...

        def node(self, node_type: str | type, *values: LinkSource | None, **dict):
            node = self._ntb.create_node(node_type, **dict)
            lb = NodeTreeBuilder.LinkBuilder(self._ntb, node)
            for index, value in enumerate(values):
                if value is not None: lb[index].link_from(value)
            return lb


        def math(self, operation: Operation, *values: LinkSource, socket_type: SocketType | None = None):
            match _get_input_type_by_precedence(*values).simplify() if socket_type is None else socket_type:
                case SocketType.Float:
                    return self.node(bpy.types.ShaderNodeMath, *values, operation=operation)
                case SocketType.Vector:
                    return self.node(bpy.types.ShaderNodeVectorMath, *values, operation=operation)
                case SocketType.Shader:
                    if operation != Operation.ADD: raise ValueError("Shader only supports Operation.Add")
                    return self.node(bpy.types.ShaderNodeAddShader, *values)
                case _: raise ValueError()


        def abs(self, value: LinkSource): return self.math(Operation.ABSOLUTE, value)

        def clamp(self, value: LinkSource, min: LinkSource = 0, max: LinkSource = 1): return self.math(Operation.MAXIMUM, self.math(Operation.MINIMUM, value, max), min)


        def mul(self, value0: LinkSource, value1: LinkSource): return self.math(Operation.MULTIPLY, value0, value1)

        def div(self, value0: LinkSource, value1: LinkSource): return self.math(Operation.DIVIDE, value0, value1)

        def add(self, value0: LinkSource, value1: LinkSource): return self.math(Operation.ADD, value0, value1)

        def sub(self, value0: LinkSource, value1: LinkSource): return self.math(Operation.SUBTRACT, value0, value1)


        def mix(self, factor: LinkSource, a: LinkSource, b: LinkSource, op = Operation.MIX, clamp_factor = False, clamp_result = False, socket_type: SocketType | None = None):

            def mix_node(data_type: SocketType):
                mix = self.node(bpy.types.ShaderNodeMix)
                mix.input_node.data_type = data_type.data_type
                mix.input_node.blend_type = op
                mix.input_node.clamp_factor = clamp_factor
                mix.input_node.clamp_result = clamp_result
                return mix

            socket_type = _get_input_type_by_precedence(a, b).simplify_value() if socket_type is None else socket_type
            match socket_type:

                case SocketType.Float:
                    mix = mix_node(SocketType.Float)
                    factor >> mix[SocketIndex.MixFactor]
                    a >> mix[SocketIndex.MixFloatIn0]
                    b >> mix[SocketIndex.MixFloatIn1]
                    return mix[SocketIndex.MixFloatOut]

                case SocketType.Vector:
                    mix = mix_node(SocketType.Vector)
                    match _get_input_type(factor).simplify():
                        case SocketType.Float:
                            factor >> mix[SocketIndex.MixFactor]
                        case SocketType.Vector:
                            mix.input_node.factor_mode = "NON_UNIFORM"
                            factor >> mix[SocketIndex.MixFactorNU]
                    a >> mix[SocketIndex.MixVectorIn0]
                    b >> mix[SocketIndex.MixVectorIn1]
                    return mix[SocketIndex.MixVectorOut]

                case SocketType.Color:
                    mix = mix_node(SocketType.Color)
                    factor >> mix[SocketIndex.MixFactor]
                    a >> mix[SocketIndex.MixColorIn0]
                    b >> mix[SocketIndex.MixColorIn1]
                    return mix[SocketIndex.MixColorOut]

                case SocketType.Shader:
                    mix = self.node(bpy.types.ShaderNodeMixShader)
                    factor >> mix[0]
                    a >> mix[1]
                    b >> mix[2]
                    return mix[0]

                case _: raise ValueError(f"Unexpected SocketType {socket_type}")


        def bool(self, value: LinkSource, invert = False):
            op = Operation.LESS_THAN if invert else Operation.GREATER_THAN
            return self.node(bpy.types.ShaderNodeMath, value, 0.5, operation=op)


        def closure(self, signatures: 'NodeTreeBuilder.Signature.IO'):
            input = self._ntb.create_node(bpy.types.NodeClosureInput)
            output = self._ntb.create_node(bpy.types.NodeClosureOutput)
            input.pair_with_output(output)
            output.define_signature = True
            signatures.inputs.apply_to_collection(output.input_items)
            signatures.outputs.apply_to_collection(output.output_items)
            return NodeTreeBuilder.ClosureLinkBuilder(self._ntb, input, output)


        def eval_closure(self, signatures: 'NodeTreeBuilder.Signature.IO', closure: 'NodeTreeBuilder.LinkBuilder | None' = None):
            lb = self.node(bpy.types.NodeEvaluateClosure)
            lb.input_node.define_signature = True
            signatures.inputs.apply_to_collection(lb.input_node.input_items)
            signatures.outputs.apply_to_collection(lb.input_node.output_items)
            if closure is not None: closure >> lb
            return lb


        def menu_switch(self, type: SocketType, *items: str):
            lb = self.node(bpy.types.GeometryNodeMenuSwitch)
            lb.input_node.data_type = type.data_type
            lb.input_node.enum_items.clear()
            for item in items: lb.input_node.enum_items.new(item)
            return lb


        def combine_bundle(self, signature: 'NodeTreeBuilder.Signature', *input_sockets: 'NodeTreeBuilder.LinkBuilder', output: 'NodeTreeBuilder.LinkBuilder | None' = None):
            lb = self.node(bpy.types.NodeCombineBundle, define_signature = True)
            signature.apply_to_collection(lb.input_node.bundle_items)
            for index, socket in enumerate(input_sockets): socket >> lb[index]
            if output is not None: lb[0] >> output
            return lb
        

        def seperate_bundle(self, signature: 'NodeTreeBuilder.Signature', input: 'NodeTreeBuilder.LinkBuilder | None' = None, *output_sockets: 'NodeTreeBuilder.LinkBuilder'):
            lb = self.node(bpy.types.NodeSeparateBundle, define_signature = True)
            signature.apply_to_collection(lb.input_node.bundle_items)
            for index, socket in enumerate(output_sockets): lb[index] >> socket
            if input is not None: input >> lb[0]
            return lb
    


    class LinkBuilder(Generic[TNODE]):

        def __init__(self, ntb: 'NodeTreeBuilder', input_node: TNODE, input_key: SocketAccessor = 0, output_node: TNODE = None, output_key: SocketAccessor | None = None):
            self.ntb = ntb
            self.input_node = input_node
            self.output_node = input_node if output_node is None else output_node
            self.input_key = input_key
            self.output_key = input_key if output_key is None else output_key


        def __getitem__(self, key: SocketAccessor):
            return NodeTreeBuilder.LinkBuilder(self.ntb, self.input_node, key, self.output_node, key)


        @property
        def node(self):
            return self.input_node


        def get_input(self): return self.input_node.inputs[self.input_key]
        def get_output(self): return self.output_node.outputs[self.output_key]


        def set_default_value(self, value: SocketValue):
            input = self.input_node.inputs[self.input_key]
            input_type = SocketType.from_data_type(input.type)
            value_type = _get_input_type(value).simplify_value()

            if (input_type == SocketType.Vector and value_type == SocketType.Float):
                value = (value, value, value)

            self.input_node.inputs[self.input_key].default_value = value


        def link_from(self_dst, src: LinkSource):
            if isinstance(src, NodeTreeBuilder.LinkBuilder):
                self_dst.ntb.link(src.output_node, src.output_key, self_dst.input_node, self_dst.input_key)
            else:
                self_dst.set_default_value(src)
            return self_dst[0]


        def link_to(self_src, dst: 'NodeTreeBuilder.LinkBuilder'):
            return dst.link_from(self_src)


        def mix(self, other: LinkSource, factor: LinkSource):
            return self.ntb.nc.mix(factor, self, other)


        def clamp(self, min: LinkSource = 0, max: LinkSource = 1): return self.ntb.nc.clamp(self, min, max)


        def is_true(self): return self > 0.5
        def is_false(self): return self < 0.5


        def __rshift__(self, other: 'NodeTreeBuilder.LinkBuilder'): return self.link_to(other)
        def __rrshift__(self, other: LinkSource): return self.link_from(other)
        def __rlshift__(self, other: 'NodeTreeBuilder.LinkBuilder'): return self.link_to(other)
        def __lshift__(self, other: LinkSource): return self.link_from(other)

        def __add__(self, other): return self.ntb.nc.add(self, other)
        def __radd__(self, other): return self.ntb.nc.add(other, self)

        def __sub__(self, other): return self.ntb.nc.sub(self, other)
        def __rsub__(self, other): return self.ntb.nc.sub(other, self)

        def __mul__(self, other): return self.ntb.nc.mul(self, other)
        def __rmul__(self, other): return self.ntb.nc.mul(other, self)

        def __div__(self, other): return self.ntb.nc.div(self, other)
        def __rdiv__(self, other): return self.ntb.nc.div(other, self)

        def __and__(self, other): return self.ntb.nc.math(Operation.MINIMUM, self, other)
        def __rand__(self, other): return self.ntb.nc.math(Operation.MINIMUM, other, self)

        def __or__(self, other): return self.ntb.nc.math(Operation.MAXIMUM, self, other)
        def __ror__(self, other): return self.ntb.nc.math(Operation.MAXIMUM, other, self)

        def __lt__(self, other): return self.ntb.nc.math(Operation.LESS_THAN, self, other)
        def __gt__(self, other): return self.ntb.nc.math(Operation.GREATER_THAN, self, other)



    class ClosureLinkBuilder(LinkBuilder[bpy.types.NodeClosureInput|bpy.types.NodeClosureOutput]):

        def __init__(self, ntb, input_node, output_node):
            super().__init__(ntb, output_node, 0, input_node, 0)
            self.input = NodeTreeBuilder.LinkBuilder(ntb, input_node, 0)
            self.output = NodeTreeBuilder.LinkBuilder(ntb, output_node, 0)



    class Signature:

        class IO(NamedTuple):
            inputs: 'NodeTreeBuilder.Signature'
            outputs: 'NodeTreeBuilder.Signature'


        @dataclass
        class Socket:
            name: str
            type: SocketType


        def __init__(self, *sockets: 'Socket'):
            self.sockets = sockets
    

        def apply_to_collection(self, collection: bpy.types.NodeCombineBundleItems):
            for socket in self.sockets:
                item = collection.new(socket.type.data_type, socket.name)
                if item.name != socket.name: raise Exception(f"Invalid Socket Name '{socket.name}' converted to '{item.name}'")


        def forward(self, src: 'NodeTreeBuilder.LinkBuilder', dst: 'NodeTreeBuilder.LinkBuilder'):
            for socket in self.sockets:
                src[socket.name] >> dst[socket.name]


    
    def __init__(self, tree: bpy.types.ShaderNodeTree):
        self.tree = tree
        self.interface = self.tree.interface
        self.nc = NodeTreeBuilder.NodeCreator(self)


    def _get_node_type_idname(self, node_type: str | type) -> str:
        if isinstance(node_type, str):
            return node_type
        elif isinstance(node_type, type):
            if issubclass(node_type, bpy.types.Node):
                if hasattr(node_type, "bl_idname"):
                    return node_type.bl_idname
                else:
                    return node_type.bl_rna.identifier
            else:
                raise TypeError("node_type not subclass of 'bpy.types.Node'.")
        else:
            raise TypeError(f"node_type must be str or type.")

        
    @overload
    def create_node(self, node_type: str, default_values: list = None, **dict) -> bpy.types.Node: ...
    @overload
    def create_node(self, node_type: type[TNODE], default_values: list = None, **dict) -> TNODE: ...
        
    def create_node(self, node_type: str | type, default_values: list = None, **dict):

        idname = self._get_node_type_idname(node_type)
        node = self.tree.nodes.new(idname)

        for key, value in dict.items():
            setattr(node, key, value)

        if default_values is not None:
            for idx, value in enumerate(default_values):
                if value is not None:
                    node.inputs[idx].default_value = value

        return node


    def clear(self):
        self.interface.clear()
        self.tree.nodes.clear()


    def create_math(self, operation: Operation, value0: float = None, value1: float = None, value2: float = None):
        default_values = [value0, value1, value2]
        node: bpy.types.ShaderNodeMath = self.create_node(NodeName.Math, default_values, operation=operation)
        return node


    def create_menu_switch(self, type: SocketType, *items: str):
        menu: bpy.types.GeometryNodeMenuSwitch = self.create_node("GeometryNodeMenuSwitch")
        menu.data_type = type.data_type
        menu.enum_items.clear()
        for item in items: menu.enum_items.new(item)
        return menu



    def link(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None): 
        if socket1 is None: socket1 = socket0

        try:
            dbg_info = "Src"
            out_socket = node0.outputs[socket0]
            dbg_info = "Dst"
            in_socket = node1.inputs[socket1]
            
        except (KeyError, IndexError, AttributeError) as e:
            raise ValueError(f"Invalid {dbg_info} socket index or name: {e}")

        self.tree.links.new(out_socket, in_socket)


    def arrange_nodes(self, x_spacing=250, y_spacing=150):
        nodes = list(self.tree.nodes)

        # Find depth of each node by walking backwards through inputs
        depths: dict[bpy.types.Node, int] = {}

        def get_depth(node: bpy.types.Node):
            if node in depths:
                return depths[node]

            depth = 0
            for inp in node.inputs:
                if inp.is_linked:
                    for link in inp.links:
                        depth = max(depth, get_depth(link.from_node) + 1)

            depths[node] = depth
            return depth

        for node in nodes:
            get_depth(node)

        # Group nodes by depth
        levels: dict[int, list[bpy.types.Node]] = {}
        for node, depth in depths.items():
            levels.setdefault(depth, []).append(node)

        # Place nodes
        for depth, level_nodes in levels.items():
            for index, node in enumerate(level_nodes):
                node.location.x = depth * x_spacing
                node.location.y = -index * y_spacing

        return levels


class SocketCreateInfo:

    BOOL: 'SocketCreateInfo'
    FLOAT: 'SocketCreateInfo'
    INT: 'SocketCreateInfo'
    FACTOR: 'SocketCreateInfo'
    VEC2: 'SocketCreateInfo'
    VEC3: 'SocketCreateInfo'
    COLOR: 'SocketCreateInfo'
    SHADER: 'SocketCreateInfo'

    def __init__(self, type = SocketType.Float, shape = SocketShape.CIRCLE, hide_value = False, hide_socket = False, **kwargs):
        self.type = type
        self.shape = shape
        self.hide_value = hide_value
        self.hide_socket = hide_socket
        self.kwargs = kwargs

SocketCreateInfo.BOOL = SocketCreateInfo(SocketType.Bool)
SocketCreateInfo.FLOAT = SocketCreateInfo(SocketType.Float)
SocketCreateInfo.INT = SocketCreateInfo(SocketType.Integer)
SocketCreateInfo.FACTOR = SocketCreateInfo(SocketType.Float, subtype = SocketSubtype.FACTOR, min_value = 0, max_value = 1)
SocketCreateInfo.VEC2 = SocketCreateInfo(SocketType.Vector, dimensions=2)
SocketCreateInfo.VEC3 = SocketCreateInfo(SocketType.Vector, dimensions=3)
SocketCreateInfo.COLOR = SocketCreateInfo(SocketType.Color)
SocketCreateInfo.SHADER = SocketCreateInfo(SocketType.Shader)



def _apply_kwargs(obj, **kwargs):
    for key in kwargs:
        setattr(obj, key, kwargs[key])



class NodeGroupData:

    @dataclass
    class SocketItem:
        shape: SocketShape = SocketShape.CIRCLE
        hide: bool = False

        def serialize(self): return asdict(self)
                
        def deserialize(self, data: dict[str, Any]):
            self.shape = data.get("shape", SocketShape.CIRCLE)
            self.hide = data.get("hide", False)

        def apply(self, dst: bpy.types.NodeSocket):
            dst.display_shape = self.shape
            dst.hide = self.hide


    class Sockets(dict[str, SocketItem]):

        def get_new(self, key: str):
            item = self.get(key, None)
            if item is not None: return item
            item = self[key] = NodeGroupData.SocketItem()
            return item

        def serialize(self):
            dict = {}
            for key in self:
                dict[key] = self[key].serialize()
            return dict

        def deserialize(self, data: dict[str, dict[str, Any]]):
            for key in data: self.get_new(key).deserialize(data[key])


    def __init__(self):
        self.inputs = NodeGroupData.Sockets()
        self.outputs = NodeGroupData.Sockets()

    def clear(self):
        self.inputs.clear()
        self.outputs.clear()

    @classmethod
    def from_text(cls, text: str):
        self = cls()
        self.load(text)
        return self

    def serialize(self):
        return {
            "inputs": self.inputs.serialize(),
            "outputs": self.outputs.serialize(),
        }

    def deserialize(self, data: dict):
        self.inputs.deserialize(data["inputs"])
        self.outputs.deserialize(data["outputs"])

    def dump(self):
        return json.dumps(self.serialize())

    def load(self, text: str):
        self.deserialize(json.loads(text))



class NodeGroupBuilder(NodeTreeBuilder):


    def input(self, create_info: SocketCreateInfo | SocketType, name: str, default_value: SocketValue | None = None):
        self._create_socket(create_info, name, SocketIOType.INPUT, default_value)
        return NodeGroupBuilder.LinkBuilder(self, self.inputs_node, name)

    
    def output(self, create_info: SocketCreateInfo | SocketType, name: str):
        self._create_socket(create_info, name, SocketIOType.OUTPUT)
        return NodeGroupBuilder.LinkBuilder(self, self.output_node, name)



    def __init__(self, idname: str):
        tree = bpy.data.node_groups.new(idname, NodeName.ShaderNodeTree)
        super().__init__(tree)
        self.current_panel: bpy.types.NodeTreeInterfacePanel | None = None
        self.current_panel_position: int = 0
        self.inputs_node: bpy.types.NodeGroupInput = None
        self.output_node: bpy.types.NodeGroupOutput = None
        self.ngdata = NodeGroupData()
        self._create_io()


    def _create_io(self):
        if self.output_node is not None: return (self.inputs_node, self.output_node)
        self.inputs_node = self.create_node(NodeName.GroupInput)
        self.output_node = self.create_node(NodeName.GroupOutput)
        return (self.inputs_node, self.output_node)


    def panel(self, name: str, description='', default_closed=True):
        self.current_panel = self.interface.new_panel(name, description=description, default_closed=default_closed)
        self.current_panel_position = 0


    def _move_to_panel(self, item: bpy.types.NodeTreeInterfaceItem):
        if self.current_panel is None: return
        self.interface.move_to_parent(item, self.current_panel, self.current_panel_position)
        self.current_panel_position += 1


    def _create_socket(self, create_info: SocketCreateInfo | SocketType, name: str, in_out: SocketIOType, default_value: SocketValue | None = None):

        if isinstance(create_info, SocketCreateInfo):
            socket_type = create_info.type
        elif isinstance(create_info, SocketType):
            socket_type = create_info
        else: raise TypeError()

        socket: bpy.types.NodeSocket = self.interface.new_socket(name, in_out=in_out, socket_type=socket_type.full_name)

        if isinstance(create_info, SocketCreateInfo):
            socket.hide_value = create_info.hide_value
            item = NodeGroupData.SocketItem(create_info.shape, create_info.hide_socket)
            (self.ngdata.inputs if in_out == SocketIOType.INPUT else self.ngdata.outputs)[name] = item
            _apply_kwargs(socket, **create_info.kwargs)

        self._move_to_panel(socket)

        if default_value is not None: socket.default_value = default_value

        return socket


    def create_any_input(self, name: str, type: SocketType, hide_value: bool = False, default_value = None, subtype: str = None):
        input: bpy.types.NodeSocket = self.interface.new_socket(name, in_out=SocketIOType.INPUT, socket_type=type.full_name)
        input.hide_value = hide_value
        if default_value is not None:
            input.default_value = default_value
        if subtype is not None:
            input.subtype = subtype

        self._move_to_panel(input)

        return input
    

    def create_bool_input(self, name: str, hide_value = False, default_value = False):
        input = self.create_any_input(name, SocketType.Bool, hide_value, default_value)
        return input
    

    def create_float_input(self, name: str, hide_value = False, default_value: float = 1.0, subtype = "FACTOR", range: tuple[float,float] = (0.0, 1.0)):
        input: bpy.types.NodeSocketFloat = self.create_any_input(name, SocketType.Float, hide_value, default_value, subtype)
        if range is not None:
            input.min_value = range[0]
            input.max_value = range[1]
        return input
    

    def create_vector_input(self, name: str, hide_value = False, default_value: float = (0.0,0.0,0.0), subtype: str = None, dimensions: int = 3):
        input: bpy.types.NodeSocketVector = self.create_any_input(name, SocketType.Vector, hide_value, default_value, subtype)
        if hasattr(input, "dimensions"): input.dimensions = dimensions
        return input
    

    def create_color_input(self, name: str, hide_value = False, default_value = (1.0,1.0,1.0,1.0)):
        input = self.create_any_input(name, SocketType.Color, hide_value, default_value)
        return input
    

    def create_shader_input(self, name: str):
        return self.create_any_input(name, SocketType.Shader)
    

    def create_bundle_input(self, name: str) -> bpy.types.NodeSocketBundle:
        return self.create_any_input(name, SocketType.Bundle)


    def create_closure_input(self, name: str) -> bpy.types.NodeSocketClosure:
        return self.create_any_input(name, SocketType.Closure)


    def create_menu_input(self, name: str) -> bpy.types.NodeSocketMenu:
        return self.create_any_input(name, SocketType.Menu)
    

    def create_any_output(self, name: str, type: SocketType):
        output: bpy.types.NodeSocket = self.interface.new_socket(name, in_out=SocketIOType.OUTPUT, socket_type=f"NodeSocket{type.value}")
        self._move_to_panel(output)
        return output
    

    def create_float_output(self, name: str):
        return self.create_any_output(name, SocketType.Float)
    

    def create_vector_output(self, name: str):
        return self.create_any_output(name, SocketType.Vector)
    

    def create_color_output(self, name: str):
        return self.create_any_output(name, SocketType.Color)
    

    def create_shader_output(self, name: str):
        return self.create_any_output(name, SocketType.Shader)
    

    def create_bundle_output(self, name: str):
        return self.create_any_output(name, SocketType.Bundle)


    def create_closure_output(self, name: str):
        return self.create_any_output(name, SocketType.Closure)