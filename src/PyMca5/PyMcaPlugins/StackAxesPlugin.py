#/*##########################################################################
# Copyright (C) 2004-2019 V.A. Sole, European Synchrotron Radiation Facility
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
"""This plugin can be used to replace the stack's X data with data from
a text file, or with the MCA curve's X or Y data.

When loading from a file, the data should be in a format that can be
loaded using `numpy.loadtxt
<https://docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.loadtxt.html>`_,
i.e. must be a CSV file without a header line and with a single column.
"""

__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
import logging
from PyMca5 import StackPluginBase
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui import PyMca_Icons

_logger = logging.getLogger(__name__)


class StackAxesPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        text = "Replace current 1D axis by list of numbers found in ASCII file"
        self.methodDict = {}
        function = self.replace1DAxisWithASCII
        info = text
        icon = None
        self.methodDict["1D axis from ASCII file"] = [function, info, icon]
        self.__methodKeys = ["1D axis from ASCII file"]

        function = self.replace1DAxisWithActiveCurveXValues
        text = "Replace current 1D axis by X values in current MCA curve"
        info = text
        icon = None
        self.methodDict["1D axis from MCA curve X values"] = [function, info, icon]
        self.__methodKeys.append("1D axis from MCA curve X values")

        function = self.replace1DAxisWithActiveCurveYValues
        text = "Replace current 1D axis by Y values in current MCA curve"
        info = text
        icon = None
        self.methodDict["1D axis from MCA curve Y values"] = [function, info, icon]
        self.__methodKeys.append("1D axis from MCA curve Y values")

    #Methods implemented by the plugin
    def getMethods(self):
        return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    def replace1DAxisWithASCII(self):
        stack = self.getStackDataObject()
        mcaIndex = stack.info.get('McaIndex', -1)
        nPoints = stack.data.shape[mcaIndex]
        fileList = PyMcaFileDialogs.getFileList(None,
                                           filetypelist=["ASCII files (*)"],
                                           message="Select ASCII file",
                                           mode="OPEN",
                                           getfilter=False,
                                           single=True)
        if not len(fileList):
            return

        filename = fileList[0]
        data = numpy.loadtxt(filename)
        data = numpy.ravel(data)
        if data.size != nPoints:
            raise ValueError("Number of read values not equal to %d" % nPoints)
        else:
            stack.x = [data]
            self.setStack(stack, mcaindex=mcaIndex)

    def replace1DAxisWithActiveCurveYValues(self):
        stack = self.getStackDataObject()
        mcaIndex = stack.info.get('McaIndex', -1)
        nPoints = stack.data.shape[mcaIndex]
        curve = self.getActiveCurve()
        data = curve[1]
        data = numpy.ravel(data)
        if data.size != nPoints:
            raise ValueError("Number of read values not equal to %d" % nPoints)
        else:
            stack.x = [data]
            self.setStack(stack, mcaindex=mcaIndex)

    def replace1DAxisWithActiveCurveXValues(self):
        stack = self.getStackDataObject()
        mcaIndex = stack.info.get('McaIndex', -1)
        nPoints = stack.data.shape[mcaIndex]
        curve = self.getActiveCurve()
        data = curve[0]
        data = numpy.ravel(data)
        if data.size != nPoints:
            raise ValueError("Number of read values not equal to %d" % nPoints)
        else:
            stack.x = [data]
            self.setStack(stack, mcaindex=mcaIndex)

MENU_TEXT = "Stack Axes Options"
def getStackPluginInstance(stackWindow, **kw):
    ob = StackAxesPlugin(stackWindow)
    return ob
