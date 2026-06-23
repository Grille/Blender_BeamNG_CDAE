import json

from io import TextIOWrapper
from dataclasses import *

from typing import Any
from ..packed_vector import PackedVector
from ..v31 import CdaeV31


class DebugWriter:
    
    @staticmethod
    def vec_to_dbg(vector: PackedVector):
        return vector.element_count

    @staticmethod 
    def to_dict(cdae: CdaeV31):

        def add_debug_fields(json: dict[str, Any]):
            nameIndex = json.get("nameIndex", None)
            if nameIndex is not None:
                 json["__NAME"] = cdae.names[nameIndex]
            return json
        
        def get_dict_list(items):
            dict_list = []
            for item in items:
                dict_list.append(add_debug_fields(asdict(item)))
            return dict_list
        
        json_mesh_list = []
        for mesh in cdae.meshes:
            json_mesh_list.append({
                "primitives": get_dict_list(mesh.unpack_regions()),
                "info": {
                    "type": mesh.type,
                    "numFrames": mesh.numFrames,
                    "numMatFrames": mesh.numMatFrames,
                    "parentMesh": mesh.parentMesh,
                    "bounds": mesh.bounds.tuple6,
                    "center": mesh.center.tuple3,
                    "radius": mesh.radius,
                    "vertsPerFrame": mesh.vertsPerFrame,
                    "flags": mesh.flags,
                },
                "vector_elements": {
                    "verts": DebugWriter.vec_to_dbg(mesh.verts),
                    "tverts0": DebugWriter.vec_to_dbg(mesh.tverts0),
                    "tverts1": DebugWriter.vec_to_dbg(mesh.tverts1),
                    "colors": DebugWriter.vec_to_dbg(mesh.colors),
                    "norms": DebugWriter.vec_to_dbg(mesh.norms),
                    "encoded_norms": DebugWriter.vec_to_dbg(mesh.encoded_norms),
                    "draw_regions": DebugWriter.vec_to_dbg(mesh.draw_regions),
                    "indices": DebugWriter.vec_to_dbg(mesh.indices),
                    "tangents": DebugWriter.vec_to_dbg(mesh.tangents),
                }
            })

        json_mat_list = []
        for mat in cdae.materials:
            json_mat_list.append({
                "name": mat.name,
                "flags": mat.flags,
            })

        json_seq_list = []
        for seq in cdae.sequences:
            json_seq_list.append(add_debug_fields({
                "nameIndex": seq.nameIndex,
                "flags": seq.flags,
                "numKeyframes": seq.numKeyframes,
                "duration": seq.duration,
                "priority": seq.priority,
                "firstGroundFrame": seq.firstGroundFrame,
                "numGroundFrames": seq.numGroundFrames,
                "baseRotation": seq.baseRotation,
                "baseTranslation": seq.baseTranslation,
                "baseScale": seq.baseScale,
                "baseObjectState": seq.baseObjectState,
                "baseDecalState": seq.baseDecalState,
                "firstTrigger": seq.firstTrigger,
                "numTriggers": seq.numTriggers,
                "toolBegin": seq.toolBegin,
                "rotationMatters": seq.rotationMatters,
                "translationMatters": seq.translationMatters,
                "scaleMatters": seq.scaleMatters,
                "visMatters": seq.visMatters,
                "frameMatters": seq.frameMatters,
                "matFrameMatters": seq.matFrameMatters,
            }))

        json = {
            "info": {
                "smallest_visible_size": cdae.smallest_visible_size,
                "smallest_visible_dl": cdae.smallest_visible_dl,
                "radius": cdae.radius,
                "tube_radius": cdae.tube_radius,
                "center": cdae.center.tuple3,
                "bounds": cdae.bounds.tuple6,
            },
            "vector_elements": {
                "defaultRotations": DebugWriter.vec_to_dbg(cdae.defaultRotations),
                "defaultTranslations": DebugWriter.vec_to_dbg(cdae.defaultTranslations),
                "nodeRotations": DebugWriter.vec_to_dbg(cdae.nodeRotations),
                "nodeTranslations": DebugWriter.vec_to_dbg(cdae.nodeTranslations),
                "nodeUniformScales": DebugWriter.vec_to_dbg(cdae.nodeUniformScales),
                "nodeAlignedScales": DebugWriter.vec_to_dbg(cdae.nodeAlignedScales),
                "nodeArbitraryScaleFactors": DebugWriter.vec_to_dbg(cdae.nodeArbitraryScaleFactors),
                "nodeArbitraryScaleRots": DebugWriter.vec_to_dbg(cdae.nodeArbitraryScaleRots),
                "groundTranslations": DebugWriter.vec_to_dbg(cdae.groundTranslations),
                "groundRotations": DebugWriter.vec_to_dbg(cdae.groundRotations),
            },
            "names": cdae.names,
            "nodes": get_dict_list(cdae.unpack_nodes()),
            "objects": get_dict_list(cdae.unpack_objects()),
            "details": get_dict_list(cdae.unpack_details()),
            "shapes": get_dict_list(cdae.unpack_subshapes()),
            "triggers": get_dict_list(cdae.unpack_triggers()),
            "states": get_dict_list(cdae.unpack_states()),
            "meshes": json_mesh_list,
            "materials": json_mat_list,
            "sequences": json_seq_list,
        }

        return json
    

    @staticmethod
    def write_to_stream(cdae: CdaeV31, f: TextIOWrapper):
        data = DebugWriter.to_dict(cdae)
        json.dump(data, f, indent=4, sort_keys=True)


    staticmethod
    def write_to_file(cdae: CdaeV31, filepath: str):
        with open(filepath, 'w') as f:
            DebugWriter.write_to_stream(cdae, f)