# /*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2023 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.eu"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import sys
import os
import numpy
import tempfile
import shutil
from PyMca5.tests import XrfData
from PyMca5.PyMcaPhysics.xrf import FastXRFLinearFit
from PyMca5.PyMcaPhysics.xrf.XRFBatchFitOutput import OutputBuffer

try:
    import h5py

    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

class testFastXRFLinearFit(unittest.TestCase):
    _rtolLegacy = 1e-5

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix="pymca")
        super(testFastXRFLinearFit, self).setUp()

    def tearDown(self):
        shutil.rmtree(self.path)

    @unittest.skipUnless(HAS_H5PY, "h5py not installed")
    def testCommand(self):
        from PyMca5.PyMcaIO import HDF5Stack1D

        # generate the data
        data, livetime = XrfData.generateXRFData()
        configuration = XrfData.generateXRFConfig()
        configuration["fit"]["stripalgorithm"] = 1

        # create HDF5 file
        fname = os.path.join(self.path, "FastXRF.h5")
        h5 = h5py.File(fname, "w")
        h5["/data"] = data
        h5["/data_int32"] = (data * 1000).astype(numpy.int32)
        h5.flush()
        h5.close()

        fastFit = FastXRFLinearFit.FastXRFLinearFit()
        fastFit.setFitConfiguration(configuration)

        outputDir = None
        outputRoot = ""
        fileEntry = ""
        fileProcess = ""
        refit = None
        filepattern = None
        begin = None
        end = None
        increment = None
        backend = None
        weight = 0
        tif = 0
        edf = 0
        csv = 0
        h5 = 1
        dat = 0
        concentrations = 0
        diagnostics = 0
        debug = 0
        overwrite = 1
        multipage = 0

        outbuffer = OutputBuffer(
            outputDir=outputDir,
            outputRoot=outputRoot,
            fileEntry=fileEntry,
            fileProcess=fileProcess,
            diagnostics=diagnostics,
            tif=tif,
            edf=edf,
            csv=csv,
            h5=h5,
            dat=dat,
            multipage=multipage,
            overwrite=overwrite,
        )

        # test standard reading
        scanlist = None
        selection = {"y": "/data"}
        dataStack = HDF5Stack1D.HDF5Stack1D([fname], selection, scanlist=scanlist)
        with outbuffer.saveContext():
            fastFit.fitMultipleSpectra(
                y=dataStack,
                weight=weight,
                refit=refit,
                concentrations=concentrations,
                outbuffer=outbuffer,
            )
        # test dynamic reading
        h5 = h5py.File(fname, "r")
        with outbuffer.saveContext():
            fastFit.fitMultipleSpectra(
                y=h5["/data"],
                weight=weight,
                refit=refit,
                concentrations=concentrations,
                outbuffer=outbuffer,
            )
        # test dynamic reading of integer data
        with outbuffer.saveContext():
            fastFit.fitMultipleSpectra(
                y=h5["/data_int32"],
                weight=weight,
                refit=refit,
                concentrations=concentrations,
                outbuffer=outbuffer,
            )

        h5.close()
        h5 = None

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(testFastXRFLinearFit)
        )
    else:
        # use a predefined order
        testSuite.addTest(testFastXRFLinearFit("testCommand"))
    return testSuite


def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    result = test(auto)
    sys.exit(not result.wasSuccessful())
