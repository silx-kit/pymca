#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import sys
import os
import gc
import stat
import tempfile
from io import StringIO
try:
    import h5py
    HAS_H5PY = True
except Exception:
    HAS_H5PY = None

class testConfigDict(unittest.TestCase):
    def setUp(self):
        """
        import the module
        """
        try:
            from PyMca5.PyMcaIO import ConfigDict
            self._module = ConfigDict
        except Exception:
            self._module = None
        self._tmpFileName = None

    def tearDown(self):
        """clean up any possible files"""
        gc.collect()
        if self._tmpFileName is not None:
            if os.path.exists(self._tmpFileName):
                os.remove(self._tmpFileName)
            if os.path.exists(self._tmpFileName + ".h5"):
                os.remove(self._tmpFileName + ".h5")

    def testConfigDictImport(self):
        #"""Test successful import"""
        self.assertTrue(self._module is not None,\
                        "Unsuccessful PyMca.ConfigDict import")

    def testConfigDictIO(self):
        # create a dictionary
        from PyMca5.PyMcaIO import ConfigDict
        testDict = {}
        testDict['simple_types'] = {}
        testDict['simple_types']['float'] = 1.0
        testDict['simple_types']['int'] = 1
        testDict['simple_types']['string'] = "Hello World"
        testDict['simple_types']['string_with_1'] = "Hello World %"
        testDict['simple_types']['string_with_2'] = "Hello World %%"
        testDict['containers'] = {}
        testDict['containers']['list'] = [-1, 'string', 3.0]
        if ConfigDict.USE_NUMPY:
            import numpy
            testDict['containers']['array'] = numpy.array([1.0, 2.0, 3.0])
        testDict['containers']['dict'] = {'key1': 'Hello World',
                                          'key2': 2.0}

        tmpFile = tempfile.mkstemp(text=False)
        os.close(tmpFile[0])
        self._tmpFileName = tmpFile[1]

        writeInstance = ConfigDict.ConfigDict(initdict=testDict)
        writeInstance.write(self._tmpFileName)

        #read the data back
        readInstance = ConfigDict.ConfigDict()
        readInstance.read(self._tmpFileName)

        # get read key list
        testDictKeys = list(testDict.keys())
        readKeys = list(readInstance.keys())
        self.assertTrue(len(readKeys) == len(testDictKeys),
                    "Number of read keys not equal to number of written keys")

        topKey = 'simple_types'
        for key in testDict[topKey]:
            original = testDict[topKey][key]
            read = readInstance[topKey][key]
            self.assertTrue( read == original,
                            "Read <%s> instead of <%s>" % (read, original))

        topKey = 'containers'
        for key in testDict[topKey]:
            original = testDict[topKey][key]
            read = readInstance[topKey][key]
            if key == 'array':
                self.assertTrue( read.all() == original.all(),
                            "Read <%s> instead of <%s>" % (read, original))
            else:
                self.assertTrue( read == original,
                            "Read <%s> instead of <%s>" % (read, original))

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testHdf5Uri(self):
        # create a dictionary
        from PyMca5.PyMcaIO import ConfigDict
        testDict = {}
        testDict['simple_types'] = {}
        testDict['simple_types']['float'] = 1.0
        testDict['simple_types']['int'] = 1
        testDict['simple_types']['string'] = "Hello World"
        testDict['containers'] = {}
        testDict['containers']['list'] = [-1, 'string', 3.0]
        if ConfigDict.USE_NUMPY:
            import numpy
            testDict['containers']['array'] = numpy.array([1.0, 2.0, 3.0])
        testDict['containers']['dict'] = {'key1': 'Hello World',
                                          'key2': 2.0}

        tmpFile = tempfile.mkstemp(text=False)
        os.close(tmpFile[0])
        self._tmpFileName = tmpFile[1]

        writeInstance = ConfigDict.ConfigDict(initdict=testDict)
        writeInstance.write(self._tmpFileName)

        #read the data back into a string
        with open(self._tmpFileName, "r") as f:
            contentsAsText = f.read()
        f = None

        hdf5FileName = self._tmpFileName + ".h5"
        path = "/entry_1/process/data"

        with h5py.File(hdf5FileName, "w") as f:
            f[path] = contentsAsText
            f.flush()
        f = None

        uri = hdf5FileName + "::" + path
        readInstance = ConfigDict.ConfigDict()
        readInstance.read(uri)

        # get read key list
        testDictKeys = list(testDict.keys())
        readKeys = list(readInstance.keys())
        self.assertTrue(len(readKeys) == len(testDictKeys),
                    "Number of read keys not equal to number of written keys")

        topKey = 'simple_types'
        for key in testDict[topKey]:
            original = testDict[topKey][key]
            read = readInstance[topKey][key]
            self.assertTrue( read == original,
                            "Read <%s> instead of <%s>" % (read, original))

        topKey = 'containers'
        for key in testDict[topKey]:
            original = testDict[topKey][key]
            read = readInstance[topKey][key]
            if key == 'array':
                self.assertTrue( read.all() == original.all(),
                            "Read <%s> instead of <%s>" % (read, original))
            else:
                self.assertTrue( read == original,
                            "Read <%s> instead of <%s>" % (read, original))

    def testConfigDictIOError(self):
        from PyMca5.PyMcaIO import ConfigDict
        testDict = {}
        testDict['section'] = {}
        testDict['section']['value1'] = 1
        testDict['section']['value2'] = 2

        readInstance = ConfigDict.ConfigDict()
        writeInstance = ConfigDict.ConfigDict(initdict=testDict)

        with self.assertRaises(IOError):
            readInstance.read("__non_existing_file__.cfg")

        tmpFile = tempfile.mkstemp(text=False)
        os.close(tmpFile[0])
        self._tmpFileName = tmpFile[1]

        writeInstance.write(self._tmpFileName)

        os.chmod(self._tmpFileName, stat.S_IWRITE)
        if os.access(self._tmpFileName, os.R_OK):
            raise unittest.SkipTest(f"Cannot make file unreadable: {self._tmpFileName}")
        else:
            with self.assertRaises(IOError):
                readInstance.read(self._tmpFileName)

        os.chmod(self._tmpFileName, stat.S_IREAD | stat.S_IWRITE)
        readInstance.read(self._tmpFileName)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(\
            unittest.TestLoader().loadTestsFromTestCase(testConfigDict))
    else:
        # use a predefined order
        testSuite.addTest(testConfigDict("testConfigDictImport"))
        testSuite.addTest(testConfigDict("testConfigDictIO"))
        testSuite.addTest(testConfigDict("testHdf5Uri"))
        testSuite.addTest(testConfigDict("testConfigDictIOError"))
    return testSuite

def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    test()
