import os
import json

from dataclasses import dataclass, asdict


@dataclass
class Imposter:

    detailLevel: int = 0
    dimension: int = 256
    equatorSteps: int = 16
    includePoles: bool = False
    polarAngle: int = 0
    polarSteps: int = 0,
    size: int = 25


class DaeAsset:

    def __init__(self):
        self.imposters: list[Imposter] = []


    def save(self, filepath: str):
        json_imposters = []
        for imp in self.imposters:
            json_imposters.append(asdict(imp))
        json_body = {
            "imposters": json_imposters,
        }

        with open(filepath, 'w') as f:
            json.dump(json_body, f, indent=4)