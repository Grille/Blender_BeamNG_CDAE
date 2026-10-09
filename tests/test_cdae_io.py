import glob
import io
import os
import unittest

import numpy as np

from grille_cdae.common import *
from grille_cdae.beamng.cdae.v31 import CdaeV31
from grille_cdae.beamng.cdae.io import CdaeReader, CdaeWriter
from grille_cdae.beamng.cdae.io.cdae_writer import get_body_bytes
from grille_cdae.beamng.cdae.io.msgpack_reader import MsgpackReader
from grille_cdae.beamng.cdae.io.msgpack_writer import MsgpackWriter


def roundtrip(cdae: CdaeV31, compress: bool = False) -> CdaeV31:
    stream = io.BytesIO()
    CdaeWriter.write_to_stream(cdae, stream, compress) # pyright: ignore[reportArgumentType]
    stream.seek(0)
    return CdaeReader.read_from_stream(stream) # pyright: ignore[reportArgumentType]


def make_sample() -> CdaeV31:
    cdae = CdaeV31()
    tree = cdae.unpack_tree()

    root_index, _ = tree.create_node("root")
    child_index, _ = tree.create_node("child", root_index, Transforms(Vec3F(1, 2, 3)))
    _, obj = tree.create_object("box", child_index)
    obj.startMeshIndex = 0
    obj.numMeshes = 2
    cdae.pack_tree(tree)
    cdae.pack_states([CdaeV31.ObjectState() for _ in tree.objects])
    cdae.pack_subshapes([CdaeV31.SubShape(0, 0, 2, 1)])

    detail = CdaeV31.Detail(nameIndex=cdae.get_name_index("detail2"), size=2.0)
    cdae.pack_details([detail])

    mesh = CdaeV31.Mesh()
    mesh.type = CdaeV31.MeshType.STANDARD
    mesh.numFrames = 1
    mesh.numMatFrames = 1
    mesh.verts.set_array(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32))
    mesh.norms.set_array(np.array([[0, 0, 1]] * 3, dtype=np.float32))
    mesh.tverts0.set_array(np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32))
    mesh.indices.set_array(np.array([0, 1, 2], dtype=np.int32))
    mesh.draw_regions.set_array(np.array([0, 3, CdaeV31.Mesh.DrawRegion.InfoMask.INDEXED], dtype=np.int32))
    mesh.vertsPerFrame = 3
    mesh.bounds = Box6F(Vec3F(0, 0, 0), Vec3F(1, 1, 0))
    mesh.center = mesh.bounds.center()
    mesh.radius = 0.75
    cdae.meshes.append(mesh)
    cdae.meshes.append(CdaeV31.Mesh())  # NULL mesh

    seq = CdaeV31.Sequence()
    seq.nameIndex = cdae.get_name_index("ambient")
    seq.numKeyframes = 4
    seq.duration = 2.5
    # 40 bits, crosses a 32 bit chunk boundary
    seq.rotationMatters = [i % 3 == 0 for i in range(40)]
    seq.translationMatters = [True, False, True]
    cdae.sequences.append(seq)
    cdae.sequences.append(CdaeV31.Sequence())

    cdae.materials.append(CdaeV31.Material("mat_a"))
    cdae.materials.append(CdaeV31.Material("mat_b"))
    return cdae



class IntegerSetTest(unittest.TestCase):

    def test_roundtrip(self):
        bits = [i % 5 == 0 for i in range(70)]
        writer = MsgpackWriter()
        writer.write_integerset(bits)
        read = MsgpackReader.from_bytes(writer.to_bytes()).read_integerset()
        self.assertEqual(len(read), 96)
        self.assertEqual(read[:70], bits)
        self.assertFalse(any(read[70:]))


    def test_beamng_layout(self):
        # layout found in BeamNG generated files: [chunk_count, [chunks...]]
        writer = MsgpackWriter()
        writer.write([1, [0b101]])
        writer.write([0, []])
        reader = MsgpackReader.from_bytes(writer.to_bytes())
        self.assertEqual(reader.read_integerset()[:4], [True, False, True, False])
        self.assertEqual(reader.read_integerset(), [])



class CdaeRoundtripTest(unittest.TestCase):

    def assert_roundtrip(self, compress: bool):
        cdae = make_sample()
        read = roundtrip(cdae, compress)

        self.assertEqual(get_body_bytes(read), get_body_bytes(cdae))
        self.assertEqual(read.names, cdae.names)
        self.assertEqual(read.unpack_nodes(), cdae.unpack_nodes())
        self.assertEqual(read.unpack_objects(), cdae.unpack_objects())
        self.assertEqual(read.unpack_details(), cdae.unpack_details())
        self.assertEqual([m.type for m in read.meshes], [CdaeV31.MeshType.STANDARD, CdaeV31.MeshType.NULL])
        np.testing.assert_array_equal(read.meshes[0].verts.to_array(), cdae.meshes[0].verts.to_array())
        self.assertEqual(len(read.sequences), 2)
        self.assertEqual(read.sequences[0].rotationMatters[:40], cdae.sequences[0].rotationMatters)
        self.assertEqual(read.sequences[0].translationMatters[:3], [True, False, True])
        self.assertEqual([m.name for m in read.materials], ["mat_a", "mat_b"])


    def test_uncompressed(self): self.assert_roundtrip(False)
    def test_compressed(self): self.assert_roundtrip(True)



@unittest.skipUnless(os.environ.get("BEAMNG_SAMPLES_DIR"), "pass a BeamNG directory to run_tests.py")
class CdaeSampleFilesTest(unittest.TestCase):

    def test_read_and_rewrite(self):
        root = os.environ["BEAMNG_SAMPLES_DIR"]
        files = glob.glob(os.path.join(root, "**", "*.cdae"), recursive=True)
        self.assertTrue(files, f"no .cdae files in {root}")

        for path in files:
            with self.subTest(file=os.path.relpath(path, root)):
                cdae = CdaeReader.read_from_file(path)
                self.assertEqual(len(cdae.unpack_nodes()), cdae.nodes.element_count)
                body = get_body_bytes(cdae)
                self.assertEqual(get_body_bytes(roundtrip(cdae, compress=True)), body)
