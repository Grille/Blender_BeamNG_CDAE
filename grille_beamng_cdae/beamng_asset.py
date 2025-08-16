import os
import json

from dataclasses import dataclass, asdict

from .cdae_v31 import CdaeV31


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


    def save(self, filepath: str):
        json_imposters = []
        for imp in self.imposters:
            json_imposters.append(asdict(imp))
        json_body = {
            "imposters": json_imposters,
        }

        with open(filepath, 'w') as f:
            json.dump(json_body, f, indent=4)