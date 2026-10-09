import math
import unittest

import bpy
import numpy as np

from grille_cdae.common import *
from grille_cdae.beamng.cdae.builder import CdeaBuilder, CdaeMeshBuilder, MeshDataEvalMode
from grille_cdae.beamng.cdae.builder_tree import CdaeTreeBuildMode



def create_cube(name: str, scale: tuple[float, float, float]) -> bpy.types.Object:
    verts = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.scale = scale
    not_none(bpy.context.scene).collection.objects.link(obj)
    not_none(bpy.context.view_layer).update()
    return obj



class BuilderScaleTest(unittest.TestCase):

    def setUp(self):
        self.obj = create_cube("scaled_cube", (2.0, 3.0, 4.0))


    def tearDown(self):
        mesh = self.obj.data
        bpy.data.objects.remove(self.obj)
        bpy.data.meshes.remove(mesh) # pyright: ignore[reportArgumentType]


    def build(self, apply_scale: bool):
        builder = CdeaBuilder()
        builder.tree.build_mode = CdaeTreeBuildMode.BLENDER_HIERARCHY
        builder.mesh_builder.apply_scale = apply_scale
        builder.mesh_builder.eval_mode = MeshDataEvalMode.Depsgraph
        builder.tree.add_objects({self.obj})
        builder.build()
        return builder.cdae


    def test_apply_scale_bakes_into_mesh(self):
        cdae = self.build(apply_scale=True)
        mesh = cdae.meshes[0]

        verts = mesh.verts.to_array().reshape(-1, 3)
        np.testing.assert_allclose(verts.min(axis=0), [-2, -3, -4], atol=1e-5)
        np.testing.assert_allclose(verts.max(axis=0), [2, 3, 4], atol=1e-5)

        norms = mesh.norms.to_array().reshape(-1, 3)
        np.testing.assert_allclose(np.linalg.norm(norms, axis=1), 1.0, atol=1e-5)

        for scale in cdae.defaultAlignedScales.unpack_list():
            np.testing.assert_allclose(scale, [1, 1, 1], atol=1e-5)


    def test_without_apply_scale_keeps_node_scale(self):
        cdae = self.build(apply_scale=False)

        verts = cdae.meshes[0].verts.to_array().reshape(-1, 3)
        np.testing.assert_allclose(verts.max(axis=0), [1, 1, 1], atol=1e-5)
        np.testing.assert_allclose(cdae.defaultAlignedScales.unpack_list()[0], [2, 3, 4], atol=1e-5)


    def test_radius_is_half_diagonal(self):
        cdae = self.build(apply_scale=True)
        expected = math.sqrt(4**2 + 6**2 + 8**2) / 2
        self.assertAlmostEqual(cdae.meshes[0].radius, expected, places=4)
        self.assertAlmostEqual(cdae.radius, expected, places=4)
        self.assertAlmostEqual(CdaeMeshBuilder.get_radius(Box6F(Vec3F(0, 0, 0), Vec3F(3, 4, 0))), 2.5)
