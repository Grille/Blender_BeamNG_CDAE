import os
import json

from io import TextIOWrapper
from dataclasses import dataclass, asdict

from ..v31 import CdaeV31


@dataclass
class Imposter:

    detailLevel: int = 0
    dimension: int = 256
    equatorSteps: int = 16
    includePoles: bool = False
    polarAngle: int = 0
    polarSteps: int = 0,
    size: int = 25

    def apply_detail(self, detail: CdaeV31.Detail):
        self.detailLevel = detail.bbDetailLevel
        self.dimension = detail.bbDimension
        self.equatorSteps = detail.bbEquatorSteps
        self.includePoles = detail.bbIncludePoles > 0
        self.polarAngle = detail.bbPolarAngle
        self.polarSteps = detail.bbPolarSteps
        self.size = int(detail.size)


class DaeAsset:

    def __init__(self):
        self.imposters: list[Imposter] = []


    def create_imposter_from_deatil(self, detail: CdaeV31.Detail):
        imp = Imposter()
        imp.apply_detail(detail)
        self.imposters.append(imp)


    def to_dict(self):
        json_imposters = []
        for imp in self.imposters:
            json_imposters.append(asdict(imp))
        json_body = {
            "imposters": json_imposters,
        }
        return json_body


    @staticmethod
    def get_path_from_dae(filepath: str):

        filename, ext = os.path.splitext(filepath)
        return f"{filename}.dae.asset.json"
    

    @staticmethod
    def get_bb_autobillboard(cdae: CdaeV31):

        for detail in cdae.unpack_details():
            if cdae.names[detail.nameIndex] == "bb_autobillboard":
                return detail
    

    @staticmethod
    def set_file(cdae: CdaeV31, filepath: str):

        assetpath = DaeAsset.get_path_from_dae(filepath)
        detail = DaeAsset.get_bb_autobillboard(cdae)

        if detail:
            asset = DaeAsset()
            asset.create_imposter_from_deatil(detail)
            with open(assetpath, 'w') as f:
                json.dump(asset.to_dict(), f, indent=4)
        else:
            if os.path.exists(assetpath):
                os.remove(assetpath)