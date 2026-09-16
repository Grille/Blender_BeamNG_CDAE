from grille_cdae.common import *
import json


DEFAULT = "default"
PRESETS = "presets"
CONFIG_DIR_PATH = "addons/grille_beamng_cdae/config"



type _ObjDict = dict[str, object]
type _DictDict = dict[str, _ObjDict]



class Presets:

    def __init__(self, default_key: str, presets: _DictDict):
        self.default_key = default_key
        self.presets = presets


    def store_annotations(self, preset_key: str, obj: bpy.types.Operator):
        preset = {}
        for key in obj.__annotations__:
            if key.startswith("temp_"):
                continue
            preset[key] = getattr(obj, key)
        self.presets[preset_key] = preset


    def apply_annotations(self, preset_key: str, obj: bpy.types.Operator):
        if not preset_key in self.presets:
            return
        preset = self.presets[preset_key]
        for key, value in preset.items():
            try:
                setattr(obj, key, value)
            except Exception as e:
                print(e)


    def setup_default(self, obj: bpy.types.Operator) -> bool:

        if (len(self.presets) > 0):
            if self.default_key not in self.presets:
                self.default_key = next(iter(self.presets))
            self.apply_annotations(self.default_key, obj)
            return False

        self.store_annotations(DEFAULT, obj)
        self.default_key = DEFAULT

        return True
        


class LocalStorage:

    cache: _DictDict = {}

    @staticmethod
    def _get_file_path(key: str):
        config_dir = bpy.utils.user_resource('SCRIPTS', path=CONFIG_DIR_PATH, create=True)
        return os.path.join(config_dir, f"{key}.json")


    @staticmethod
    def get(key: str) -> _ObjDict:

        if key in LocalStorage.cache:
            return LocalStorage.cache[key]

        data: _ObjDict
        filepath = LocalStorage._get_file_path(key)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(e)
            data = {}

        LocalStorage.cache[key] = data
        return data


    @staticmethod
    def set(key: str, data: _ObjDict | None):
        filepath = LocalStorage._get_file_path(key)
        if (data is None or len(data) == 0) and os.path.isfile(filepath):
            LocalStorage.cache[key] = {}
            os.remove(filepath)
            return

        assert data is not None
        
        LocalStorage.cache[key] = data
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)


    @staticmethod
    def get_presets(key: str):
        data = LocalStorage.get(key)
        default = data.get(DEFAULT)
        if not isinstance(default, str): raise TypeError()
        presets = data.get(PRESETS)
        if not isinstance(presets, dict): raise TypeError()
        return Presets(default, cast(_DictDict, presets))
    

    @staticmethod
    def set_presets(key: str, presets: Presets):
        data: dict[str, object] = {
            DEFAULT: presets.default_key,
            PRESETS: presets.presets,
        }
        LocalStorage.set(key, data)


    @staticmethod
    def setup_presets(key: str, obj: bpy.types.Operator):
            presets = LocalStorage.get_presets(key)
            if presets.setup_default(obj):
                LocalStorage.set_presets(key, presets)
            return presets

