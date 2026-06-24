import bpy
from .enums import *
from .node_walker import NodeWalker
from .enums import *



class NodeLayoutValidator(NodeWalker):
    
    def __init__(self, node = None, stack = None):
        super().__init__(node, stack)
        self.raise_layout_errors = False


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