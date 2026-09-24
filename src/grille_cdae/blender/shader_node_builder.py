from __future__ import annotations

from grille_cdae.common import *
from grille_cdae.enums import *



type LinkSource = LinkBuilderBase | SocketValue
type LinkSourceSequence = LinkBuilderBase | Sequence[SocketValue]



def _get_input_type(src: LinkSource) -> SocketType:
    if isinstance(src, float): return SocketType.Float
    if isinstance(src, int): return SocketType.Integer
    if isinstance(src, tuple): return SocketType.Color if len(src) == 4 else SocketType.Vector
    if isinstance(src, str): return SocketType.Menu 
    if isinstance(src, LinkBuilderBase):
        return SocketType.from_data_type(src.get_output().type)
    else:
        raise TypeError(src)


def _get_input_type_tuple(*src: LinkSource):
    return tuple(_get_input_type(s) for s in src)


def _get_input_type_by_precedence(*src: LinkSource):
    return SocketType.select_by_max_precedence(*_get_input_type_tuple(*src))



class LinkBuilderBase:
    __slots__ = "ntb"

    def __init__(self, ntb: NodeTreeBuilder):
        self.ntb = ntb

    def __getitem__(self, key: SocketAccessor) -> Self:...
    def get_input(self) -> bpy.types.NodeSocket:...
    def get_output(self) -> bpy.types.NodeSocket:...


    @staticmethod
    def _cast_default_value(value: SocketValue, target: SocketType):
        if target == SocketType.Vector: return Vec3F.from_obj(value)
        if target == SocketType.Color: return Color4F.from_obj(value)

        return value


    def set_default_value(self, value: SocketValue):
        input = self.get_input()
        target_type = SocketType.from_data_type(input.type)
        value = self._cast_default_value(value, target_type)

        butils.set_default_value(input, value)


    def link_from(self, src: LinkSource) -> None:
        if isinstance(src, LinkBuilderBase):
            self.ntb.tree.links.new(src.get_output(), self.get_input())
        else:
            self.set_default_value(src)


    def link_to(self, dst: LinkBuilderBase):
        dst.link_from(self)


    def mix(self, other: LinkSource, factor: LinkSource):
        return self.ntb.nc.mix(factor, self, other)


    def clamp(self, min: LinkSource = 0, max: LinkSource = 1): return self.ntb.nc.clamp(self, min, max)

    def __rshift__(self, other: LinkBuilderBase) -> None: self.link_to(other)
    def __rrshift__(self, other: LinkSource) -> None: self.link_from(other)
    def __rlshift__(self, other: LinkBuilderBase) -> None: self.link_to(other)
    def __lshift__(self, other: LinkSource) -> None: self.link_from(other)

    def __add__(self, other: LinkSource): return self.ntb.nc.add(self, other)
    def __radd__(self, other: LinkSource): return self.ntb.nc.add(other, self)

    def __sub__(self, other: LinkSource): return self.ntb.nc.sub(self, other)
    def __rsub__(self, other: LinkSource): return self.ntb.nc.sub(other, self)

    def __mul__(self, other: LinkSource): return self.ntb.nc.mul(self, other)
    def __rmul__(self, other: LinkSource): return self.ntb.nc.mul(other, self)

    def __div__(self, other: LinkSource): return self.ntb.nc.div(self, other)
    def __rdiv__(self, other: LinkSource): return self.ntb.nc.div(other, self)

    def __and__(self, other: LinkSource): return self.ntb.nc.math(Operation.MINIMUM, self, other)
    def __rand__(self, other: LinkSource): return self.ntb.nc.math(Operation.MINIMUM, other, self)

    def __or__(self, other: LinkSource): return self.ntb.nc.math(Operation.MAXIMUM, self, other)
    def __ror__(self, other: LinkSource): return self.ntb.nc.math(Operation.MAXIMUM, other, self)

    def __lt__(self, other: LinkSource): return self.ntb.nc.math(Operation.LESS_THAN, self, other)
    def __gt__(self, other: LinkSource): return self.ntb.nc.math(Operation.GREATER_THAN, self, other)

    def __neg__(self): return 0 - self
    def __le__(self, other: LinkSource): return 1 - (self > other)
    def __ge__(self, other: LinkSource): return 1 - (self < other)

    def is_true(self): return self > 0
    def is_false(self): return self <= 0



type LinkBuilderOptional = LinkBuilderBase | None



class LinkBuilder[T: bpy.types.Node](LinkBuilderBase):
    __slots__ = "node", "key"

    def __init__(self, ntb: 'NodeTreeBuilder', node: T, key: SocketAccessor = 0):
        super().__init__(ntb)
        self.node = node
        self.key = key


    def __getitem__(self, key: SocketAccessor):
        return LinkBuilder(self.ntb, self.node, key)


    def get_input(self): return self.node.inputs[self.key]
    def get_output(self): return self.node.outputs[self.key]



class LinkBuilderPair[TIn: bpy.types.Node, TOut: bpy.types.Node](LinkBuilderBase):
    __slots__ = "input", "output", "swap_io"

    def __init__(self, ntb: NodeTreeBuilder, input: LinkBuilder[TIn], output: LinkBuilder[TOut], swap_io = False):
        super().__init__(ntb)
        self.input = input
        self.output = output
        self.swap_io = swap_io

    def __getitem__(self, key: SocketAccessor,  output_key: SocketAccessor | None = None):
        if output_key is None: output_key = key
        return LinkBuilderPair(self.ntb, self.input[key], self.output[output_key], self.swap_io)

    def get_input(self): return (self.output if self.swap_io else self.input).get_input()
    def get_output(self): return (self.input if self.swap_io else self.output).get_output()



class _NodeSignatureSocket(NamedTuple):
    name: str
    type: SocketType | NodeSignature

    def get_socket_type(self):
        if isinstance(self.type, SocketType):
            return self.type.data_type
        assert isinstance(self.type, NodeSignature)
        return SocketType.Bundle.data_type



class _PSocketCollection[T: str](Protocol):
    def new(self, socket_type: T, name: str) -> _PSocketItem: ...



class _PSocketItem(Protocol):
    name: str



class NodeSignature(tuple[_NodeSignatureSocket, ...]):

    class IO(NamedTuple):
        inputs: 'NodeSignature'
        outputs: 'NodeSignature'


    def __new__(cls, *sockets: tuple[str, SocketType | NodeSignature]):
        sockets = tuple(s if isinstance(s, _NodeSignatureSocket) else _NodeSignatureSocket(*s) for s in sockets)
        return super().__new__(cls, sockets)


    def apply_to_collection[T:str](self, collection: _PSocketCollection[T]):
        for socket in self:
            item = collection.new(cast(T, socket.get_socket_type()), socket.name)
            if item.name != socket.name: raise Exception(f"Invalid Socket Name '{socket.name}' converted to '{item.name}'")


    def forward(self, src: LinkBuilderBase, dst: LinkBuilderBase, exclude: Sequence[str] | None = None):
        for socket in self:
            name = socket.name
            if exclude is not None and name in exclude: continue
            src[name] >> dst[name]



class NodeTreeBuilder:

    class NodeCreator:

        __slots__ = "_ntb"
        def __init__(self, ntb: 'NodeTreeBuilder'):
            self._ntb = ntb


        @overload
        def node(self, node_type: str, *values: LinkSource | None, **dict: object) -> LinkBuilder[bpy.types.Node]: ...
        @overload
        def node[T: bpy.types.Node](self, node_type: type[T], *values: LinkSource | None, **dict: object) -> LinkBuilder[T]: ...

        def node[T: bpy.types.Node](self, node_type: str | type[T], *values: LinkSource | None, **dict: object):
            node = self._ntb.create_node(node_type, **dict)
            lb = LinkBuilder(self._ntb, node)
            for index, value in enumerate(values):
                if value is not None: lb[index].link_from(value)
            return lb


        def math(self, operation: str, *values: LinkSource, socket_type: SocketType | None = None) -> LinkBuilderBase:
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


        def compare(self, value0: LinkSource, value1: LinkSource, epsilon: LinkSource = 0):
            return self.math(Operation.COMPARE, value0, value1, epsilon)
        

        def mix(self, factor: LinkSource, a: LinkSource, b: LinkSource, op = Operation.MIX, clamp_factor = False, clamp_result = False, socket_type: SocketType | None = None) -> LinkBuilderBase:

            def mix_node(socket_type: SocketType):
                mix = self.node(bpy.types.ShaderNodeMix, data_type = socket_type.data_type, blend_type = op)
                mix.node.clamp_factor = clamp_factor
                mix.node.clamp_result = clamp_result
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
                            mix.node.factor_mode = "NON_UNIFORM"
                            factor >> mix[SocketIndex.MixFactorNU]
                        case _:
                            raise TypeError()
                        
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


        def invert(self, value: LinkBuilderBase):
            return 0 - value


        def teximage(self, image: types.Image | str | None = None, colorspace: str | None = None, uv: LinkBuilderOptional = None):
            lb = self.node(types.ShaderNodeTexImage)

            image = butils.get_image(image, colorspace)

            if image is not None:
                lb.node.image = image

            if uv is not None:
                uv >> lb[SocketName.Vector]

            return lb


        def closure(self, signatures: 'NodeSignature.IO'):
            input = self.node(bpy.types.NodeClosureInput)
            output = self.node(bpy.types.NodeClosureOutput)
            input.node.pair_with_output(output.node)
            output.node.define_signature = True
            signatures.inputs.apply_to_collection(output.node.input_items)
            signatures.outputs.apply_to_collection(output.node.output_items)
            return LinkBuilderPair(self._ntb, input, output, True)


        def eval_closure(self, signatures: 'NodeSignature.IO', closure: LinkBuilderBase | None = None):
            lb = self.node(bpy.types.NodeEvaluateClosure)
            lb.node.define_signature = True
            signatures.inputs.apply_to_collection(lb.node.input_items)
            signatures.outputs.apply_to_collection(lb.node.output_items)
            if closure is not None: closure >> lb
            return lb


        def menu_switch(self, type: SocketType, *items: str, menu: LinkSource | None = None):
            lb = self.node(bpy.types.GeometryNodeMenuSwitch)
            lb.node.data_type = type.data_type # type: ignore
            lb.node.enum_items.clear()
            for item in items: lb.node.enum_items.new(item)
            if menu is not None: menu >> lb
            return lb


        def combine_bundle(self, signature: 'NodeSignature', *input_sockets: 'LinkSource', output: LinkBuilderOptional = None):
            lb = self.node(bpy.types.NodeCombineBundle, define_signature = True)
            signature.apply_to_collection(lb.node.bundle_items)
            for index, socket in enumerate(input_sockets): socket >> lb[index]
            if output is not None: lb[0] >> output
            return lb
        

        def seperate_bundle(self, signature: 'NodeSignature', input: LinkBuilderOptional = None, *output_sockets: LinkBuilderBase):
            lb = self.node(bpy.types.NodeSeparateBundle, define_signature = True)
            signature.apply_to_collection(lb.node.bundle_items)
            for index, socket in enumerate(output_sockets): lb[index] >> socket
            if input is not None: input >> lb[0]
            return lb


        def mix_bundle(self, signature: NodeSignature, factor: LinkSource, a: LinkBuilderBase, b: LinkBuilderBase):
            a = self.seperate_bundle(signature, a)
            b = self.seperate_bundle(signature, b)
            result = self.combine_bundle(signature)
            for socket in signature:
                name = socket.name
                type = socket.type 
                a = a[name]
                b = b[name]
                result = result[name]
                if isinstance(type, NodeSignature): self.mix_bundle(type, factor, a, b) >> result
                self.mix(factor, a, b) >> result
            return result


        def mix_foreach[TDst:LinkBuilderBase](self, src0: LinkBuilderBase, src1: LinkSourceSequence, dst: TDst, count: int, operator: Callable[[LinkBuilderBase, LinkSource, int], LinkSource], src_offset: int = 0, dst_offset: int | None = None) -> TDst:
            if dst_offset is None: dst_offset = src_offset
            for i in range(count): 
                src_index = i + src_offset
                dst_index = i + dst_offset
                operator(src0[src_index], src1[src_index], i) >> dst[dst_index]
            return dst


        def mix_foreach_xyz(self, value0: LinkSource, value1: LinkSource, operator: Callable[[LinkBuilderBase, LinkSource, int], LinkSource]):
            xyz0 = self.node(types.ShaderNodeSeparateXYZ, value0)
            xyz1 = self.node(types.ShaderNodeSeparateXYZ, value1)
            return self.mix_foreach(xyz0, xyz1, self.node(types.ShaderNodeCombineXYZ), 3, operator)



    def __init__(self, tree: bpy.types.ShaderNodeTree):
        self.tree = tree
        assert self.tree.interface is not None
        self.interface = self.tree.interface
        self.nc = NodeTreeBuilder.NodeCreator(self)


    @overload
    def create_node(self, node_type: str, **dict: object) -> types.Node: ...
    @overload
    def create_node[T:types.Node](self, node_type: type[T], **dict: object) -> T: ...

    def create_node[T:types.Node](self, node_type: str | type[T], **dict: object) -> T | types.Node:

        idname = butils.get_idname(node_type)
        node = self.tree.nodes.new(idname)

        for key, value in dict.items():
            setattr(node, key, value)

        return node


    def clear(self):
        self.interface.clear()
        self.tree.nodes.clear()



    def link(self, node0: bpy.types.Node, socket0: str | int, node1: bpy.types.Node, socket1: str | int | None = None): 
        if socket1 is None: socket1 = socket0

        dbg_info = "Src"
        try:
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

        def get_depth(node: bpy.types.Node) -> int:
            if node in depths:
                return depths[node]

            depth = 0
            for inp in node.inputs:
                if inp.is_linked:
                    if inp.links is None: continue
                    for link in inp.links:
                        if link.from_node is None: continue
                        other = get_depth(link.from_node)
                        depth = max(depth, other + 1)

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

    __slots__ = "type", "shape", "hide_value", "hide_socket", "kwargs"
    def __init__(self, type = SocketType.Float, shape = SocketShape.CIRCLE, hide_value = False, hide_socket = False, **kwargs: Any):
        assert isinstance(type, SocketType)
        self.type = type
        self.shape = shape
        self.hide_value = hide_value
        self.hide_socket = hide_socket
        self.kwargs = kwargs


    @staticmethod
    def cast(value: 'SocketCreateInfo | SocketType'):
        if isinstance(value, SocketCreateInfo):
            return value
        return SocketCreateInfo(value)
    

SocketCreateInfo.BOOL = SocketCreateInfo(SocketType.Bool)
SocketCreateInfo.FLOAT = SocketCreateInfo(SocketType.Float)
SocketCreateInfo.INT = SocketCreateInfo(SocketType.Integer)
SocketCreateInfo.FACTOR = SocketCreateInfo(SocketType.Float, subtype = SocketSubtype.FACTOR, min_value = 0, max_value = 1)
SocketCreateInfo.VEC2 = SocketCreateInfo(SocketType.Vector, dimensions=2)
SocketCreateInfo.VEC3 = SocketCreateInfo(SocketType.Vector, dimensions=3)
SocketCreateInfo.COLOR = SocketCreateInfo(SocketType.Color)
SocketCreateInfo.SHADER = SocketCreateInfo(SocketType.Shader)



def _apply_kwargs(obj: object, **kwargs: object):
    for key in kwargs:
        setattr(obj, key, kwargs[key])



class NodeGroupData:

    @dataclass(slots=True)
    class SocketItem:

        shape: SocketShape = SocketShape.CIRCLE
        hide: bool = False
        default_value: SocketValue | None = None


        def serialize(self):
            data: dict[str, object] = {
                "shape": self.shape,
                "hide": self.hide,
            }
            if self.default_value is not None: data["value"] = self.default_value
            return data

                
        def deserialize(self, data: dict[str, Any]):
            self.shape = data.get("shape", SocketShape.CIRCLE)
            self.hide = data.get("hide", False) 
            self.default_value = data.get("value", None)


        def apply(self, dst: bpy.types.NodeSocket):
            dst.display_shape = self.shape # type: ignore
            dst.hide = self.hide
            if self.default_value is not None: butils.set_default_value(dst, self.default_value)



    class Sockets(dict[str, SocketItem]):

        def get_new(self, key: str):
            item = self.get(key, None)
            if item is not None: return item
            item = self[key] = NodeGroupData.SocketItem()
            return item


        def serialize(self):
            dict: dict[str, object] = {}
            for key in self:
                dict[key] = self[key].serialize()
            return dict


        def deserialize(self, data: dict[str, dict[str, object]]):
            for key in data: self.get_new(key).deserialize(data[key])


    __slots__ = "inputs", "outputs"
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


    def deserialize(self, data: dict[str, dict[str, dict[str, object]]]):
        self.inputs.deserialize(data["inputs"])
        self.outputs.deserialize(data["outputs"])


    def dump(self):
        return json.dumps(self.serialize())


    def load(self, text: str):
        self.deserialize(json.loads(text))



class NodeGroupBuilder(NodeTreeBuilder):

    def input(self, create_info: SocketCreateInfo | SocketType, name: str, default_value: SocketValue | None = None):
        assert self.inputs_node is not None
        self._create_socket(create_info, name, SocketIOType.INPUT, default_value)
        return LinkBuilder(self, self.inputs_node, name)

    
    def output(self, create_info: SocketCreateInfo | SocketType, name: str):
        assert self.output_node is not None
        self._create_socket(create_info, name, SocketIOType.OUTPUT)
        return LinkBuilder(self, self.output_node, name)



    def __init__(self, idname: str):
        tree = cast(bpy.types.ShaderNodeTree, bpy.data.node_groups.new(idname, NodeName.ShaderNodeTree.value))
        super().__init__(tree)
        self.current_panel: bpy.types.NodeTreeInterfacePanel | None = None
        self.current_panel_position: int = 0
        self.inputs_node: bpy.types.NodeGroupInput | None = None
        self.output_node: bpy.types.NodeGroupOutput | None = None
        self.ngdata = NodeGroupData()
        self._create_io()


    def _create_io(self):
        if self.inputs_node is None: self.inputs_node = self.create_node(bpy.types.NodeGroupInput)
        if self.output_node is None: self.output_node = self.create_node(bpy.types.NodeGroupOutput)
        return (self.inputs_node, self.output_node)


    def panel(self, name: str, description='', default_closed=True):
        self.current_panel = self.interface.new_panel(name, description=description, default_closed=default_closed)
        self.current_panel_position = 0


    def _move_to_panel(self, item: bpy.types.NodeTreeInterfaceItem):
        if self.current_panel is None: return
        self.interface.move_to_parent(item, self.current_panel, self.current_panel_position)
        self.current_panel_position += 1


    def _create_socket(self, create_info: SocketCreateInfo | SocketType, name: str, in_out: SocketIOType, default_value: SocketValue | None = None):

        create_info = SocketCreateInfo.cast(create_info)

        socket = self.interface.new_socket(name, in_out=in_out.value, socket_type=cast(Any, create_info.type.full_name))

        ngdata_target = self.ngdata.inputs if in_out == SocketIOType.INPUT else self.ngdata.outputs
        item = ngdata_target.get_new(name)

        socket.hide_value = create_info.hide_value
        item = NodeGroupData.SocketItem(create_info.shape, create_info.hide_socket)
        ngdata_target[name] = item
        _apply_kwargs(socket, **create_info.kwargs)

        self._move_to_panel(socket)
        
        if default_value is not None: butils.set_default_value(socket, default_value)

        return socket