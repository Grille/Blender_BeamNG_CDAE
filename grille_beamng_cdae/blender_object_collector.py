import bpy

class ObjectCollector:

    def __init__(self):
        self.objects: set[bpy.types.Object] = set()
        self.include_hidden: bool = False
        self.include_children: bool = False


    def add_object(self, obj: bpy.types.Object):
        if obj.hide_viewport and not self.include_hidden:
            return
        self.objects.add(obj)
        if self.include_children:
            self.add_objects(obj.children)


    def add_objects(self, objects: list[bpy.types.Object]):
        for obj in objects:
            self.add_object(obj)


    def collect_scene(self):
        self.add_objects(bpy.context.scene.objects)


    def collect_selected(self):
        self.add_objects(bpy.context.selected_objects)