# /*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2026 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import contextlib
import importlib
import io
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Type

import numpy

from PyMca5.PyMcaIO.EdfFile import EdfFile
from PyMca5.PyMcaMisc import CliUtils

_logger = logging.getLogger(__name__)


@dataclass
class CliScenario:
    name: str
    args: List[str]
    return_code: int = 0
    expect_files: List[str] = field(default_factory=list)
    forbid_files: List[str] = field(default_factory=list)
    use_data_dir: bool = False
    qt_app: bool = False
    post_check: Optional[Callable] = None


CLI_SPECS = {
    "PyMca5.PyMcaPhysics.XRayTubeEbel": [
        CliScenario("help", ["--help"]),
        CliScenario("default_generates_txt", [], expect_files=["Tube_*.txt"]),
    ],
    "PyMca5.PyMcaPhysics.xrf.ConcentrationsTool": [
        CliScenario("help", ["--help"]),
        CliScenario("noargs", []),
    ],
    "PyMca5.PyMcaGui.physics.xrf.ConcentrationsWidget": [
        CliScenario("help", ["--help"]),
        CliScenario("noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.physics.xrf.ElementsInfo": [
        CliScenario("help", ["--help"]),
        CliScenario("noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.physics.xrf.PeakIdentifier": [
        CliScenario("help", ["--help"]),
        CliScenario("noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.StackSelector": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.QStackWidget": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.RGBCorrelatorWidget": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.RGBCorrelator": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.PyMcaPostBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.PyMcaBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.PyMcaMdi": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.PyMcaMain": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.Mca2Edf": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.LegacyPyMcaBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.Fit2Spec": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.pymca.EdfFileSimpleViewer": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.plotting.ImageView": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test", "test.edf"], qt_app=True),
    ],
    "PyMca5.PyMcaGui.plotting.MaskImageWidget": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaCore.XiaCorrect": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaCore.StackROIBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaCore.LegacyStackROIBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("noargs", []),
    ],
    "PyMca5.PyMcaGui.physics.xrf.McaCalWidget": [
        CliScenario("help", ["--help"]),
        CliScenario("qt_noargs", ["--cli-test"], qt_app=True),
    ],
    "PyMca5.PyMcaPhysics.McaAdvancedFitBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("requires_cfg", ["--cfg", "dummy.cfg"]),
    ],
    "PyMca5.PyMcaPhysics.FastXRFLinearFit": [
        CliScenario("help", ["--help"]),
        CliScenario("requires_cfg", ["--cfg", "dummy.cfg"]),
    ],
    "PyMca5.PyMcaPhysics.LegacyMcaAdvancedFitBatch": [
        CliScenario("help", ["--help"]),
        CliScenario("requires_cfg", ["--cfg", "dummy.cfg"]),
    ],
    "PyMca5.PyMcaPhysics.LegacyFastXRFLinearFit": [
        CliScenario("help", ["--help"]),
        CliScenario("requires_cfg", ["--cfg", "dummy.cfg"]),
    ],
    "PyMca5.PyMcaPhysics.xrf.ClassMcaTheory": [
        CliScenario("help", ["--help"]),
        CliScenario(
            "requires_existing_data",
            ["--cfg", "__STEEL_CFG__", "--file", "__STEEL_SPE__"],
            use_data_dir=True,
        ),
    ],
}


class TestCliModules(unittest.TestCase):

    def setUp(self):
        self._orig_cwd = None
        self._temporary_cwd = None
        self._original_data_dir = None
        self._current_data_dir = None

        super().setUp()
        self._setup_pymca_data_dir()
        self._setup_cwd()

    def tearDown(self):
        self._restore_cwd()
        self._restore_pymca_data_dir()
        super().tearDown()

    def _setup_cwd(self):
        """Ensure all CLI tests run in a temporary directory
        so the current working directory does not get cluttered
        with files.
        """
        self._temporary_cwd = tempfile.TemporaryDirectory()
        self._orig_cwd = os.getcwd()
        os.chdir(self._temporary_cwd.name)
        self._create_files()

    def _restore_cwd(self):
        if self._orig_cwd:
            os.chdir(self._orig_cwd)
        if self._temporary_cwd:
            self._temporary_cwd.cleanup()
            self._temporary_cwd = None

    def _setup_pymca_data_dir(self):
        """Ensure PYMCA_DATA_DIR is an absolute path before
        we change the current working directory.
        """
        try:
            from PyMca5 import PyMcaDataDir
        except Exception:
            self._original_data_dir = None
            self._current_data_dir = None
            return

        self._original_data_dir = PyMcaDataDir.PYMCA_DATA_DIR
        self._current_data_dir = os.path.abspath(self._original_data_dir)
        PyMcaDataDir.PYMCA_DATA_DIR = self._current_data_dir

    def _restore_pymca_data_dir(self):
        try:
            from PyMca5 import PyMcaDataDir
        except Exception:
            return
        if self._original_data_dir is None:
            return
        PyMcaDataDir.PYMCA_DATA_DIR = self._original_data_dir
        self._original_data_dir = None
        self._current_data_dir = None

    def _create_files(self):
        """Create files in the current working directory."""
        image = numpy.arange(10 * 20).reshape((10, 20))
        edf = EdfFile("test.edf", "wb+")
        edf.WriteImage({}, image)
        del edf

    def _run_scenario(self, module: Type, scenario: CliScenario):
        args = list(scenario.args)

        # Replace placeholders
        if scenario.use_data_dir:
            for i, value in enumerate(args):
                if value == "__STEEL_CFG__":
                    args[i] = self._get_data_file("Steel.cfg")
                elif value == "__STEEL_SPE__":
                    args[i] = self._get_data_file("Steel.spe")

        # Check execution
        return_code = self._call_cli(module, args, scenario)
        self.assertEqual(return_code, scenario.return_code)

        # Check expected files
        for pattern in scenario.expect_files:
            self.assertTrue(
                self._glob_count(pattern) > 0,
                f"Expected file pattern '{pattern}' not created",
            )

        # Check forbidden files
        for pattern in scenario.forbid_files:
            self.assertEqual(
                self._glob_count(pattern),
                0,
                f"Unexpected file pattern '{pattern}' created",
            )

        if scenario.post_check:
            scenario.post_check(self)

    def _call_cli(self, module, args, scenario):
        # Call the CLI in a sub-process.
        cmd = self._subprocess_cmd(module, args)
        if cmd:
            return self._run_cli_main_subprocess(cmd)

        # Do not test Qt CLI's in the current process
        # to avoid the need to handle the Qt application
        # life-cycle.
        if scenario.qt_app:
            self.skipTest("Qt CLI only tested in a subprocess")

        # Test the CLI in the current process.
        return self._run_cli_main(module, args)

    def _run_cli_main_subprocess(self, cmd):
        """Call CLI in a sub-process."""
        _logger.info("Execute command: %s", " ".join(cmd))

        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if completed.returncode != 0:
            print("\n--- Subprocess Output ---")
            print(completed.stdout)
            print("--- End Subprocess Output ---\n")

        return completed.returncode

    def _run_cli_main(self, module, args):
        """Call CLI in the current process."""
        _logger.info(
            "Execute CLI main from %s with arguments %s",
            module.__name__,
            args,
        )

        parser = module.build_parser()

        buffer = io.StringIO()

        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                return_code = CliUtils.cli_main(module.main, parser, args=args)
            except SystemExit as ex:
                return_code = ex.code

        self.assertIsInstance(return_code, int)

        if return_code != 0:
            print("\n--- CLI Output ---")
            print(buffer.getvalue())
            print("--- End CLI Output ---\n")

        return return_code

    def _subprocess_cmd(self, module, args):
        """Sub-process command to call the CLI."""
        # Python CLI subprocess command if available.
        frozen = getattr(sys, "frozen", False)
        if not frozen:
            return [sys.executable, "-m", module.__name__, *args]

        # Frozen binary subprocess command if available.
        name = module.__name__.split(".")[-1]
        exe_dir = Path(sys.executable).parent
        executables = {exe.stem: exe for exe in exe_dir.iterdir() if exe.is_file()}
        if name in executables:
            return [str(executables[name]), *args]

        # No subprocess command available.
        return None

    def _glob(self, pattern):
        return list(Path(self._temporary_cwd.name).glob(pattern))

    def _glob_count(self, pattern):
        return len(self._glob(pattern))

    def _get_data_file(self, *parts):
        if self._current_data_dir is None:
            self.skipTest("PyMca Data Directory cannot be found")
        return str(Path(self._current_data_dir).joinpath(*parts))


# Add tests dynamically on import because `subTest` does not print each test
# separately which is important to see what is skipped and why and to run individual tests.
def _make_test(module_path, scenario):
    def test(self):
        try:
            module = importlib.import_module(module_path)
        except Exception as ex:
            self.skipTest(f"Cannot import {module_path}: {ex}")

        self._run_scenario(module, scenario)

    module_name = module_path.split(".")[-1]
    test.__name__ = f"test_{module_name}_{scenario.name}".replace(" ", "_")
    return test


for module_path, scenarios in CLI_SPECS.items():
    for scenario in scenarios:
        test_method = _make_test(module_path, scenario)
        setattr(TestCliModules, test_method.__name__, test_method)


def getSuite(auto=True):
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestCliModules))
    return suite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == "__main__":
    test()
