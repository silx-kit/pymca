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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import sys
import os
import gc
import tempfile
import numpy

class testEdfFile(unittest.TestCase):
    def setUp(self):
        """
        import the EdfFile module
        """
        tmpFile = tempfile.mkstemp(text=False)
        os.close(tmpFile[0])
        self.fname = tmpFile[1]
        try:
            from PyMca5.PyMcaIO.EdfFile import EdfFile
            self.fileClass = EdfFile
        except Exception:
            self.fileClass = None

    def tearDown(self):
        """clean up any possible files"""
        gc.collect()
        if self.fileClass is not None:
            if os.path.exists(self.fname):
                os.remove(self.fname)

    def testEdfFileImport(self):
        #"""Test successful import"""
        self.assertTrue(self.fileClass is not None)

    def testEdfFileReadWrite(self):
        # create a file
        self.assertTrue(self.fileClass is not None)
        data = numpy.arange(10000).astype(numpy.int32)
        data = data.reshape(100, 100)
        edf = self.fileClass(self.fname, 'wb+')
        edf.WriteImage({'Title': "title",
                        'key': 'key'}, data)
        edf = None

        # read it
        edf = self.fileClass(self.fname, 'rb')
        # the number of images
        nImages = edf.GetNumImages()
        self.assertEqual(nImages, 1)
        # the header information
        header = edf.GetHeader(0)
        self.assertEqual(header['Title'], "title")
        self.assertEqual(header['key'], "key")

        #the data information
        readData = edf.GetData(0)
        self.assertEqual(readData.dtype, numpy.int32,
                         'Read type %s instead of %s' %\
                        (readData.dtype, numpy.int32))
        self.assertEqual(readData[10,20], data[10,20])
        self.assertEqual(readData[20,10], data[20,10])
        edf =None

        # add a second Image
        edf = self.fileClass(self.fname, 'rb+')
        edf.WriteImage({'Title': "title2", 'key': 'key2'},
                       data.astype(numpy.float32), Append=1)
        edf = None

        # read it
        edf = self.fileClass(self.fname, 'rb')
        # the number of images
        nImages = edf.GetNumImages()
        self.assertEqual(nImages, 2)

        # the header information
        header = edf.GetHeader(1)
        self.assertEqual(header['Title'], "title2")
        self.assertEqual(header['key'], "key2")

        # the data information
        readData = edf.GetData(1)
        self.assertEqual(readData.dtype, numpy.float32)
        self.assertTrue(abs(readData[10,20]-data[10,20]) < 0.00001)
        self.assertTrue(abs(readData[20,10]-data[20,10]) < 0.00001)
        edf =None
        gc.collect()

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(\
            unittest.TestLoader().loadTestsFromTestCase(testEdfFile))
    else:
        # use a predefined order
        testSuite.addTest(testEdfFile("testEdfFileImport"))
        testSuite.addTest(testEdfFile("testEdfFileReadWrite"))
    return testSuite

def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    test()
