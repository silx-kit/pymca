#/*##########################################################################
# Copyright (C) 2004-2014 V.A. Sole, European Synchrotron Radiation Facility
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
This plugin offers 4 methods for rearranging spectra within the stack data
cube:

  - Reverse Odd Rows
  - Reverse Even Rows
  - Reverse Odd Columns
  - Reverse Even Columns

"""

__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
import logging
from PyMca5 import StackPluginBase

_logger = logging.getLogger(__name__)


class ReverseStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {}
        text  = "Replace current stack by one\n"
        text += "with odd rows reversed."
        function = self.reverseOddRows
        info = text
        icon = None
        self.methodDict["Reverse Odd Rows"] = [function,
                                               info,
                                               icon]
        text  = "Replace current stack by one\n"
        text += "with even rows reversed."
        function = self.reverseEvenRows
        info = text
        icon = None
        self.methodDict["Reverse Even Rows"] = [function,
                                                info,
                                                icon]
        text  = "Replace current stack by one\n"
        text += "with odd columns reversed."
        function = self.reverseOddColumns
        info = text
        icon = None
        self.methodDict["Reverse Odd Columns"] = [function,
                                                  info,
                                                  icon]
        text  = "Replace current stack by one\n"
        text += "with odd columns reversed."
        function = self.reverseEvenColumns
        info = text
        icon = None
        self.methodDict["Reverse Even Columns"] = [function,
                                                   info,
                                                   icon]

        self.__methodKeys = ["Reverse Odd Rows",
                             "Reverse Even Rows",
                             "Reverse Odd Columns",
                             "Reverse Even Columns"]

    #Methods implemented by the plugin
    def getMethods(self):
        return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    def reverseOddRows(self):
        self.reverseRows(offset=1)
        self.reversePositioners(offset=1, direction="rows")

    def reverseEvenRows(self):
        self.reverseRows(offset=0)
        self.reversePositioners(offset=0, direction="rows")

    def reverseOddColumns(self):
        self.reverseColumns(offset=1)
        self.reversePositioners(offset=1, direction="columns")

    def reverseEvenColumns(self):
        self.reverseColumns(offset=0)
        self.reversePositioners(offset=0, direction="columns")

    def reverseRows(self, offset=1):
        stack = self.getStackDataObject()
        if not isinstance(stack.data, numpy.ndarray):
            text = "This method does not work with dynamically loaded stacks"
            raise TypeError(text)
        mcaIndex = stack.info.get('McaIndex', -1)
        if mcaIndex in [-1, 2]:
            ndata = stack.data.shape[1]
            limit = 0.5 * ndata
            for i in range(offset, stack.data.shape[0], 2):
                j = 0
                while j < limit:
                    tmp = stack.data[i, j, :] * 1
                    stack.data[i, j, :] = stack.data[i,(ndata-j-1),:] * 1
                    stack.data[i,(ndata-j-1),:] = tmp
                    j += 1
        elif mcaIndex == 0:
            ndata = stack.data.shape[2]
            limit = 0.5 * ndata
            for i in range(offset, stack.data.shape[1], 2):
                j = 0
                while j < limit:
                    tmp = stack.data[:, i, j] * 1
                    stack.data[:, i, j] = stack.data[:, i,(ndata-j-1)] * 1
                    stack.data[:, i,(ndata-j-1)] = tmp
                    j += 1
        else:
            raise ValueError("Invalid 1D index %d" % mcaIndex)
        self.setStack(stack)

    def reverseColumns(self, offset=1):
        stack = self.getStackDataObject()
        if not isinstance(stack.data, numpy.ndarray):
            text = "This method does not work with dynamically loaded stacks"
            raise TypeError(text)
        mcaIndex = stack.info.get('McaIndex', -1)
        if mcaIndex in [-1, 2]:
            ndata = stack.data.shape[0]
            limit = 0.5 * ndata
            for i in range(offset, stack.data.shape[1], 2):
                j = 0
                while j < limit:
                    tmp = stack.data[j, i, :] * 1
                    stack.data[j, i, :] = stack.data[(ndata-j-1), i,:] * 1
                    stack.data[(ndata-j-1), i,:] = tmp
                    j += 1
        elif mcaIndex == 0:
            ndata = stack.data.shape[1]
            limit = 0.5 * ndata
            for i in range(offset, stack.data.shape[2], 2):
                j = 0
                while j < limit:
                    tmp = stack.data[:, j, i] * 1
                    stack.data[:, j, i] = stack.data[:,(ndata-j-1), i] * 1
                    stack.data[:, (ndata-j-1), i] = tmp
                    j += 1
        else:
            raise ValueError("Invalid 1D index %d" % mcaIndex)
        self.setStack(stack)

    def reversePositioners(self, offset=1, direction="rows"):
        """Re-arrange positioners data to preserve the match between
        a pixel of the stack image and the corresponding values when
        reversing half the rows or half the columns.

        :param int offset: 1 to reverse odd rows orcolumns,
            0 to reverse even ones.
        :param str direction: "rows" or "columns"
        """
        assert direction in ["rows", "columns"]
        stackImageShape = self.getStackOriginalImage().shape
        positioners = self.getStackInfo().get("positioners", None)
        if positioners is None:
            return

        newPositioners = {}

        for motorName, motorValues in positioners.items():
            if numpy.isscalar(motorValues) or (hasattr(motorValues, "ndim") and
                                               motorValues.ndim == 0):
                # scalar
                newPositioners[motorName] = motorValues
            else:
                # non-scalar positioners are always stored as arrays in info
                originalShape = motorValues.shape
                motorValues2d = numpy.array(motorValues, copy=True)
                motorValues2d = motorValues2d.reshape(stackImageShape)

                if direction == "rows":
                    motorValues2d[offset::2] = numpy.fliplr(motorValues2d[offset::2])
                elif direction == "columns":
                    motorValues2d[:, offset::2] = numpy.flipud(motorValues2d[:, offset::2])

                newPositioners[motorName] = motorValues2d.reshape(originalShape)

        self._stackWindow.setPositioners(newPositioners)


MENU_TEXT = "Stack Row or Column Reversing"
def getStackPluginInstance(stackWindow, **kw):
    ob = ReverseStackPlugin(stackWindow)
    return ob
