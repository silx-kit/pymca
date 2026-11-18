#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2026 European Synchrotron Radiation Facility
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
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import unittest
from PyMca5.PyMcaGui.io.hdf5 import HDF5SmartSelectionDialog as smart


class testHDF5SmartSelection(unittest.TestCase):
    def testParseNumberSpec(self):
        available = list(range(1, 51))
        self.assertEqual(smart.parseNumberSpec("1,3,7", available), [1, 3, 7])
        self.assertEqual(smart.parseNumberSpec("10-20", available),
                         list(range(10, 21)))
        self.assertEqual(smart.parseNumberSpec("10-40:5", available),
                         list(range(10, 41, 5)))
        self.assertEqual(smart.parseNumberSpec("3::5", available),
                         list(range(3, 51, 5)))
        self.assertEqual(smart.parseNumberSpec("", available), available)
        with self.assertRaises(ValueError):
            smart.parseNumberSpec("abc", available)

    def testParseEntryNames(self):
        # common text before the first number: first numbers
        self.assertEqual(smart.parseEntryNames(
            ["1_sample5A", "4_sampleB", "6_ref"]), [(1,), (4,), (6,)])
        # common text after the last number: last numbers
        self.assertEqual(smart.parseEntryNames(
            ["sample5A_1", "sampleB_2"]), [(1,), (2,)])
        # no scan number
        self.assertEqual(smart.parseEntryNames(["a", "b1"]), [(), ()])

    def testMatchEntries(self):
        names = ["1.1", "1.2", "2.1", "2.2", "3.1", "4.1", "4.2", "5.1"]
        self.assertEqual(smart.matchEntries(names, ["4", ""]),
                         ["4.1", "4.2"])
        self.assertEqual(smart.matchEntries(names, ["2-4", "1"]),
                         ["2.1", "3.1", "4.1"])
        self.assertEqual(smart.matchEntries(names, ["2,8"], positions=True),
                         ["1.2", "5.1"])
        with self.assertRaises(ValueError):
            smart.matchEntries(names, ["6", ""])
        with self.assertRaises(ValueError):
            smart.matchEntries(names, ["", "", ""])


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(testHDF5SmartSelection))
    else:
        # use a predefined order
        testSuite.addTest(testHDF5SmartSelection("testParseNumberSpec"))
        testSuite.addTest(testHDF5SmartSelection("testParseEntryNames"))
        testSuite.addTest(testHDF5SmartSelection("testMatchEntries"))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == "__main__":
    test()
