import bpy


class DictProperty:

    def __init__(self, key: str):
        self.key = key


    def __get__(self, instance: 'Material', owner):
        return instance.dict.get(self.key, None)


    def __set__(self, instance: 'Material', value):
        if value is None:
            instance.dict.pop(self.key, None)
        else:
            instance.dict[self.key] = value


class Stage:


        color_map: str = DictProperty("colorMap")
        base_color_map: str = DictProperty("baseColorMap")

        use_anisotropic: bool = DictProperty("useAnisotropic")
        alpha_test: bool = DictProperty("alphaTest")
        alpha_ref: int = DictProperty("alphaRef")


        def __init__(self, basedict: dict[str, any] = None):
            self.dict = {} if basedict is None else basedict


class Material:

    STAGES_KEY = "Stages"

    name: str = DictProperty("name")
    class_name: str = DictProperty("class")
    ground_type: str = DictProperty("groundType")

    version: float = DictProperty("version")
    active_layers: int = DictProperty("activeLayers")


    def __init__(self, basedict: dict[str, any] = None):
        self.dict = {} if basedict is None else basedict

        if Material.STAGES_KEY not in self.dict:
            self.dict[Material.STAGES_KEY] = [{},{},{},{}]

        raw_stages: list[dict] = self.dict[Material.STAGES_KEY]
        self.stages = [Stage(raw_stages[0]), Stage(raw_stages[1]), Stage(raw_stages[2]), Stage(raw_stages[3])]


    @classmethod
    def from_bmat(cls, bmat: bpy.types.Material):
        material = cls()

        material.name = bmat.name
        material.class_name = "Material"
        material.version = 1

        stage0 = material.stages[0]
        stage0.use_anisotropic = True

        return material