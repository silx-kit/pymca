#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
import locale
current_locale = locale.getlocale()
for l in ['de_DE.utf8', 'fr_FR.utf8']:
    try:
        locale.setlocale(locale.LC_ALL, l)
    except Exception:
        other_locale = False
    else:
        other_locale = l
        break

if other_locale:
    try:
        locale.setlocale(locale.LC_ALL, current_locale)
    except locale.Error:
        # cleanup python 3.12 issue on same machines
        if isinstance(current_locale, tuple):
            # if the returned tuple is (None, 'UTF-8') it cannot restore the locale
            current_as_list = list(current_locale)
            for i in range(len(current_as_list)):
                if current_as_list[i] is None:
                    print(f"Returned locale <{current_locale}> reset to None")
                    current_locale = None
                else:
                    current_locale = current_as_list[0]
            locale.setlocale(locale.LC_ALL, current_locale)

class testSpecfile(unittest.TestCase):
    def setUp(self):
        """
        import the module
        """
        try:
            from PyMca5.PyMcaIO import specfile
            self.specfileClass = specfile
        except Exception:
            self.specfileClass = None
        if self.specfileClass is not None:
            text  = "#F \n"
            text += "\n"
            text += "#S 10  Undefined command 0\n"
            text += "#N 3\n"
            text += "#L First label  Second label  Third label\n"
            text += "10  100  1000\n"
            text += "20  400  8000\n"
            text += "30  900  270000\n"
            text += "\n"
            text += "#S 20  Undefined command 1\n"
            text += "#N 3\n"
            text += "#L First  Second  Third\n"
            text += "1.3  1  1\n"
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
        # restore saved locale
        if other_locale:
            locale.setlocale(locale.LC_ALL, current_locale)
        
        if self.specfileClass is not None:
            if os.path.exists(self.fname):
                os.remove(self.fname)

    def testSpecfileImport(self):
        #"""Test successful import"""
        self.assertTrue(self.specfileClass is not None,
                        'Unsuccessful PyMca5.PyMcaIO.specfile import')

    def testSpecfileReading(self):
        #"""Test specfile readout"""
        self.testSpecfileImport()
        self._sf = self.specfileClass.Specfile(self.fname)
        # test the number of found scans
        self.assertEqual(len(self._sf), 2,
                         'Expected to read 2 scans, read %s' %\
                         len(self._sf))
        self.assertEqual(self._sf.scanno(), 2,
                         'Expected to read 2 scans, got %s' %\
                         self._sf.scanno())
        # test scan iteration selection method
        self._scan = self._sf[1]
        labels = self._scan.alllabels()
        expectedLabels = ['First', 'Second', 'Third']
        self.assertEqual(len(labels), 3,
                         'Expected to read 3 scans, got %s' % len(labels))
        for i in range(3):
            self.assertEqual(labels[i], expectedLabels[i],
                    'Read "%s" instead of "%s"' %\
                     (labels[i], expectedLabels[i]))
        # test scan number selection method
        self._scan = self._sf.select('20.1')
        labels = self._scan.alllabels()
        sf = None
        expectedLabels = ['First', 'Second', 'Third']
        self.assertEqual(len(labels), 3,
                         'Expected to read 3 labels, got %s' % len(labels))
        for i in range(3):
            self.assertEqual(labels[i], expectedLabels[i],
                'Read "%s" instead of "%s"' %\
                (labels[i], expectedLabels[i]))
        gc.collect()

    def testSpecfileReadingCompatibleWithUserLocale(self):
        #"""Test specfile compatible with C locale"""
        self.testSpecfileImport()
        self._sf = self.specfileClass.Specfile(self.fname)
        self._scan = self._sf[1]
        datacol = self._scan.datacol(1)
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
        self.assertEqual(datacol[1], data[0][1],
                    'Read %f instead of %f' %\
                    (datacol[1], data[0][1]))
        gc.collect()

    @unittest.skipIf(not other_locale, "other locale not installed")
    def testSpecfileReadingCompatibleWithOtherLocale(self):
        self.testSpecfileImport()
        self._sf = self.specfileClass.Specfile(self.fname)
        locale.setlocale(locale.LC_ALL, other_locale)
        self._scan = self._sf[1]
        datacol = self._scan.datacol(1)
        data = self._scan.data()
        locale.setlocale(locale.LC_ALL, current_locale)
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
        self.assertEqual(datacol[1], data[0][1],
                    'Read %f instead of %f' %\
                    (datacol[1], data[0][1]))
        gc.collect()

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(\
            unittest.TestLoader().loadTestsFromTestCase(testSpecfile))
    else:
        # use a predefined order
        testSuite.addTest(testSpecfile("testSpecfileImport"))
        testSuite.addTest(testSpecfile("testSpecfileReading"))
        testSuite.addTest(\
            testSpecfile("testSpecfileReadingCompatibleWithUserLocale"))
        testSuite.addTest(\
            testSpecfile("testSpecfileReadingCompatibleWithOtherLocale"))
    return testSuite

def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    test()
