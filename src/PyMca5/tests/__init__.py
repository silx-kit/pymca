#/*##########################################################################
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
__author__ = "V. Armando Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os

from PyMca5.tests.ConfigDictTest import test as testConfigDict
from PyMca5.tests.DataTest import test as testDataTest
from PyMca5.tests.EdfFileTest import test as testEdfFile
from PyMca5.tests.ROIBatchTest import test as testROIBatch
from PyMca5.tests.ElementsTest import test as testElements
from PyMca5.tests.GefitTest import test as testGefit
from PyMca5.tests.PCAToolsTest import test as testPCATools
from PyMca5.tests.SpecfileTest import test as testSpecfile
from PyMca5.tests.specfilewrapperTest import test as testSpecfilewrapper
from PyMca5.tests.XrfTest import test as testXrf
from PyMca5.tests.McaStackViewTest import test as testMcaStackView
from PyMca5.tests.NexusUtilsTest import test as testNexusUtils
from PyMca5.tests.StackInfoTest import test as testStackInfo
from PyMca5.tests.FastXRFLinearFitTest import test as testFastXRFLinearFit
from PyMca5.tests.ImportTest import test as testImport

def testAll():
    from PyMca5.tests.TestAll import main as testAll
    return testAll()
