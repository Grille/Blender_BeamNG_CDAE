import bpy
from .enums import *
from .node_walker import NodeWalker
from .enums import *



class NodeLayoutValidator(NodeWalker):
    
    def __init__(self, node = None, stack = None, messages: list[str] | None = None):
        super().__init__(node, stack)
        self.raise_layout_errors = False
        self.messages = messages


    def log(self, msg: str):
        if self.messages is not None: self.messages.append(msg)


    def assert_image_colorspace(self, input_key: str | int, cs: ColorSpace, maxdepth = 8) -> bool:
        if not self.try_follow(input_key):
            return True
        
        depth = 0
        while True:
            if self.is_node_idname(NodeName.TexImage):
                image = self.current.image
                if image is None:
                    return True
                return cs.value == image.colorspace_settings.name
            if not self.try_follow(0) or depth > maxdepth:
                return True
            depth += 1


    def assert_is_float_value(self, input_key: str | int):
        if self.get_float_value(input_key) is None:
            self.messages.append(f"{input_key} is not static")
