#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019 European Synchrotron Radiation Facility
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
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import unittest
import tempfile
import shutil
import os
import sys
import numpy
from PyMca5.tests import XrfData
try:
    from PyMca5.PyMcaIO import HDF5Stack1D
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


class testXrfData(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix='pymca')

    def tearDown(self):
        shutil.rmtree(self.path)

    def testSpecMesh(self):
        filename = os.path.join(self.path, 'meshscan.dat')

        # SpecFileStack: only works with one detector
        nDet = 1
        info = XrfData.generateSpecMesh(filename, nDet=nDet, same=False)
        nDet0, nRows0, nColumns0, nChannels = info['data'].shape

        from PyMca5.PyMcaIO import SpecFileStack
        stack = SpecFileStack.SpecFileStack(filelist=[filename]).data
        self.assertEqual(nDet, nDet0)
        self.assertEqual(stack.shape, (1, nRows0*nColumns0, nChannels))

        for i in range(nRows0):
            for j in range(nColumns0):
                for k in range(1):
                    # C-order (row-major)
                    mca = stack[k, i*nColumns0+j]
                    numpy.testing.assert_array_equal(mca, info['data'][k, i, j])

        # SpecFileLayer: works with more than one detector
        nDet = 2
        info = XrfData.generateSpecMesh(filename, nDet=nDet, same=False)
        nDet0, nRows0, nColumns0, nChannels = info['data'].shape
        nCounters0 = 2

        from PyMca5.PyMcaCore import SpecFileLayer
        ffile = SpecFileLayer.SpecFileLayer()
        ffile.SetSource(filename)
        fileinfo = ffile.GetSourceInfo()
        scaninfo, counters = ffile.LoadSource('1.1')
        scan = ffile.Source.select('1.1')
        nCounters, nRows, nColumns = counters.shape
        self.assertEqual(scaninfo['NbMcaDet'], nDet)
        self.assertEqual(scaninfo['NbMca'], nDet*nColumns*nRows)
        self.assertEqual(nColumns, nColumns0)
        self.assertEqual(nRows, nRows0)
        self.assertEqual(nCounters, nCounters0)
        self.assertEqual(nDet, nDet0)

        for i in range(nRows):
            for j in range(nColumns):
                for k in range(nDet):
                    mca = scan.mca(i*nColumns*nDet+j*nDet+k+1)
                    # TODO: bug in specfile (reads one channel less)
                    numpy.testing.assert_array_equal(mca, info['data'][k, i, j])
        del ffile.Source

    def testEdfMap(self):
        filename = os.path.join(self.path, 'xrfmap.edf')
        nDet = 2
        info = XrfData.generateEdfMap(filename, nDet=nDet, same=False)
        nDet0, nRows0, nColumns0, nChannels = info['data'].shape

        from PyMca5.PyMcaIO import EDFStack
        files = [os.path.join(self.path, 'xrfmap_xia{:02d}_0001_0000_{:04d}.edf'.format(k, i))
                 for i in range(nRows0)
                 for k in range(nDet0)]
        stack = EDFStack.EDFStack(filelist=sorted(files)).data
        self.assertEqual(nDet, nDet0)
        self.assertEqual(stack.shape, (nDet0*nRows0, nColumns0, nChannels))

        for i in range(nRows0):
            for j in range(nColumns0):
                for k in range(nDet):
                    mca = stack[i+k*nRows0, j]
                    numpy.testing.assert_array_equal(mca, info['data'][k, i, j])

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testHdf5Map(self):
        from PyMca5.PyMcaIO import HDF5Stack1D
        filename = os.path.join(self.path, 'xrfmap.h5')
        # TODO: only works for 1 detector
        nDet = 1
        info = XrfData.generateHdf5Map(filename, nDet=nDet, same=False)
        nDet0, nRows0, nColumns0, nChannels = info['data'].shape

        datasets = ['/xrf/mca{:02d}/data'.format(k) for k in range(nDet)]
        selection = {'y': datasets[0]}
        stack = HDF5Stack1D.HDF5Stack1D([filename], selection).data
        self.assertEqual(stack.shape, (nRows0, nColumns0, nChannels))

        for i in range(nRows0):
            for j in range(nColumns0):
                for k in range(nDet):
                    numpy.testing.assert_array_equal(stack[i, j], info['data'][k, i, j])


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testXrfData))
    else:
        # use a predefined order
        testSuite.addTest(testXrfData("testSpecMesh"))
        testSuite.addTest(testXrfData("testEdfMap"))
        testSuite.addTest(testXrfData("testHdf5Map"))
    return testSuite


def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    result = test(auto)
    sys.exit(not result.wasSuccessful())
