import json

from io import TextIOWrapper
from dataclasses import *

from ..v31 import CdaeV31


class DebugWriter:

    @staticmethod 
    def to_dict(cdae: CdaeV31):

        def get_dict_list(items):
            dict_list = []
            for item in items:
                dict_list.append(asdict(item))
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
                    "verts": mesh.verts.element_count,
                    "tverts0": mesh.tverts0.element_count,
                    "tverts1": mesh.tverts1.element_count,
                    "colors": mesh.colors.element_count,
                    "norms": mesh.norms.element_count,
                    "encoded_norms": mesh.encoded_norms.element_count,
                    "draw_regions": mesh.draw_regions.element_count,
                    "indices": mesh.indices.element_count,
                    "tangents": mesh.tangents.element_count,
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
            json_seq_list.append({
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
            })

        json = {
            "info": {
                "smallest_visible_size": cdae.smallest_visible_size,
                "smallest_visible_dl":cdae.smallest_visible_dl,
                "radius": cdae.radius,
                "tube_radius": cdae.tube_radius,
                "center": cdae.center.tuple3,
                "bounds": cdae.bounds.tuple6,
            },
            "vector_elements": {
                "defaultRotations": cdae.defaultRotations.element_count,
                "defaultTranslations": cdae.defaultTranslations.element_count,
                "nodeRotations": cdae.nodeRotations.element_count,
                "nodeTranslations": cdae.nodeTranslations.element_count,
                "nodeUniformScales": cdae.nodeUniformScales.element_count,
                "nodeAlignedScales": cdae.nodeAlignedScales.element_count,
                "nodeArbitraryScaleFactors": cdae.nodeArbitraryScaleFactors.element_count,
                "nodeArbitraryScaleRots": cdae.nodeArbitraryScaleRots.element_count,
                "groundTranslations": cdae.groundTranslations.element_count,
                "groundRotations": cdae.groundRotations.element_count,
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