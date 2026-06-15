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
__author__ = "V. Armando Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import sys
import os
import gc
import tempfile

class testSpecfilewrapper(unittest.TestCase):
    def setUp(self):
        """
        import the module
        """
        try:
            from PyMca5.PyMcaIO import specfilewrapper as specfile
            self.specfileClass = specfile
        except Exception:
            self.specfileClass = None
        if self.specfileClass is not None:
            text = "1.3  1  1\n"
            text += "2.5  4  8\n"
            text += "3.7  9  27\n"
            text += "\n"
            tmpFile = tempfile.mkstemp(text=False)
            os.write(tmpFile[0], bytes(text, 'utf-8'))
            os.close(tmpFile[0])
            self.fname = tmpFile[1]

    def tearDown(self):
        """clean up any possible files"""
        # make sure the file handle is free
        self._sf = None
        self._scan = None
        # this should free the handle
        gc.collect()
        if self.specfileClass is not None:
            if os.path.exists(self.fname):
                os.remove(self.fname)

    def testSpecfilewrapperImport(self):
        #"""Test successful import"""
        self.assertTrue(self.specfileClass is not None,
                        'Unsuccessful PyMca5.PyMcaIO.specfilewrapper import')

    def testSpecfilewrapperReading(self):
        #"""Test specfile readout"""
        self.testSpecfilewrapperImport()
        self._sf = self.specfileClass.Specfile(self.fname)
        # test the number of found scans
        self.assertEqual(len(self._sf), 2,
                         'Expected to read 2 scans, read %s' %\
                         len(self._sf))
        self.assertEqual(self._sf.scanno(), 2,
                         'Expected to read 2 scans, got %s' %\
                         self._sf.scanno())
        # test scan iteration selection method
        self._scan = self._sf[0]
        labels = self._scan.alllabels()
        expectedLabels = ['Point', 'Column 0', 'Column 1', 'Column 2']
        self.assertEqual(len(labels), 4,
                         'Expected to read 4 labels, got %s' % len(labels))
        for i in range(3):
            self.assertEqual(labels[i], expectedLabels[i],
                    'Read "%s" instead of "%s"' %\
                     (labels[i], expectedLabels[i]))

        # test scan number selection method
        self._scan = self._sf.select('1.1')
        labels = self._scan.alllabels()
        expectedLabels = ['Point', 'Column 0', 'Column 1', 'Column 2']
        self.assertEqual(len(labels), 4,
                         'Expected to read 4 labels, got %s' % len(labels))
        for i in range(3):
            self.assertEqual(labels[i], expectedLabels[i],
                'Read "%s" instead of "%s"' %\
                (labels[i], expectedLabels[i]))

        # test scan number of mca
        self._scan = self._sf[0]
        nbmca = self._scan.nbmca()
        self.assertEqual(nbmca, 0,
                         'Expected to read 0 mca, got %s' % nbmca)

        self._scan = self._sf[1]
        nbmca = self._scan.nbmca()
        self.assertEqual(nbmca, 3,
                         'Expected to read 3 mca, got %s' % nbmca)

    def testSpecfilewrapperReadingCompatibleWithUserLocale(self):
        #"""Test specfile compatible with C locale"""
        self.testSpecfilewrapperImport()
        self._sf = self.specfileClass.Specfile(self.fname)
        self._scan = self._sf[0]
        datacol = self._scan.datacol(2)
        data = self._scan.data()
        self._sf = None
        self.assertEqual(datacol[0], 1.3,
                    'Read %f instead of %f' %\
                    (datacol[0], 1.3))
        self.assertEqual(datacol[1], 2.5,
                    'Read %f instead of %f' %\
                    (datacol[1], 2.5))
        self.assertEqual(datacol[2], 3.7,
                    'Read %f instead of %f' %\
                    (datacol[2], 3.7))
        self.assertEqual(datacol[1], data[1][1],
                    'Read %f instead of %f' %\
                    (datacol[1], data[1][1]))
        gc.collect()

    def testTrainingSpectrumReading(self):
        from PyMca5 import PyMcaDataDir
        import numpy
        fname = os.path.join(PyMcaDataDir.PYMCA_DATA_DIR,
                                  'XRFSpectrum.mca')
        self._sf = self.specfileClass.Specfile(fname)
        self._scan = self._sf[0]

        # I find awful that starts counting at 1
        # 1 is the point number
        # 2 is the actual spectal data
        datacol = self._scan.datacol(2)
        self._scan = self._sf[1]

        # The "second" scan is the readout as mca
        mca = self._scan.mca(1)
        self.assertTrue(numpy.all(datacol == mca))

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(\
            unittest.TestLoader().loadTestsFromTestCase(testSpecfilewrapper))
    else:
        # use a predefined order
        testSuite.addTest(testSpecfilewrapper("testSpecfilewrapperImport"))
        testSuite.addTest(testSpecfilewrapper("testSpecfilewrapperReading"))
        testSuite.addTest(\
            testSpecfilewrapper(\
                "testSpecfilewrapperReadingCompatibleWithUserLocale"))
        testSuite.addTest(testSpecfilewrapper("testTrainingSpectrumReading"))
    return testSuite

def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    test()
