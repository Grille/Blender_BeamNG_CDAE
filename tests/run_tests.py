"""
Runs the test suite inside Blender (the addon code depends on bpy).

    blender -b --factory-startup --python tests/run_tests.py
    blender -b --factory-startup --python tests/run_tests.py -- <dir with .cdae files>

Passing a directory additionally reads and rewrites every .cdae found in it,
e.g. %LOCALAPPDATA%/BeamNG/BeamNG.drive/current/temp (BeamNG's shape cache).
"""

import os
import sys
import unittest

tests_dir = os.path.dirname(os.path.abspath(__file__))
addon_dir = os.path.dirname(tests_dir)

for path in (tests_dir, os.path.join(addon_dir, "src"), os.path.join(addon_dir, "modules")):
    if path not in sys.path: sys.path.insert(0, path)

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if args: os.environ["CDAE_SAMPLES_DIR"] = args[0]

suite = unittest.defaultTestLoader.discover(tests_dir, pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
