#/*##########################################################################
# Copyright (C) 2004-2026 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
"""
Optional dependencies (i.e. silx) must never be needed to start PyMca.
"""
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import importlib
import sys
import unittest

# the modules executed by the scripts (from setup.py)
ENTRY_POINT_MODULES = [
    "PyMca5.PyMcaGui.pymca.PyMcaMain",              # pymca
    "PyMca5.PyMcaGui.pymca.QStackWidget",           # pymcaroitool
    "PyMca5.PyMcaGui.pymca.PyMcaPostBatch",         # rgbcorrelator, pymcapostbatch
    "PyMca5.PyMcaGui.pymca.PyMcaBatch",             # pymcabatch
    "PyMca5.PyMcaGui.pymca.EdfFileSimpleViewer",    # edfviewer
    "PyMca5.PyMcaGui.pymca.Mca2Edf",                # mca2edf
    "PyMca5.PyMcaGui.physics.xrf.ElementsInfo",     # elementsinfo
    "PyMca5.PyMcaGui.physics.xrf.PeakIdentifier",   # peakidentifier
]


class testImport(unittest.TestCase):
    @unittest.skipIf(getattr(sys, 'frozen', False), "skipped running as frozen binary")
    def testEntryPointModules(self):
        for name in ENTRY_POINT_MODULES:
            # TestAll and CliTest ignores import errors because of OS differences
            # this test is exactly about catching import errors in particular places
            with self.subTest(module=name):
                importlib.import_module(name)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(testImport))
    else:
        if not getattr(sys, 'frozen', False):
            testSuite.addTest(testImport("testEntryPointModules"))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    test()
