class CdeaTree:

    class Node:

        def __init__(self):

            self.name: str = ""
            self.nodes: list[CdeaTree.Node] = []
            self.objects: list[CdeaTree.Object] = []



    class Object:

        def __init__(self):

            self.name: str = ""
            self.meshes: int = 0


    class Mesh:

        def __init__(self):
            pass

    
    def __init__(self):
        pass