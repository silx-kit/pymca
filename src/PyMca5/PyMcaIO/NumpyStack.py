#/*##########################################################################
#
# Copyright (c) 2016 Diamond Light Source
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
__author__ = "Aaron Parsons"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "Diamond Light Source"
__doc__ = """
Convenience class to make an in-memory array look as if it would have
been read from a set of EDF files.
The purpose of using this class instead of using StackBase is to simplify the
use of McaAdvancedFitBatch with in-memory arrays.
"""

from PyMca5.PyMcaCore import DataObject

SOURCE_TYPE = "EdfFileStack"

class NumpyStack(DataObject.DataObject):
    def __init__(self, inputArray):
        DataObject.DataObject.__init__(self)
        # we need this to be 3D with shape (y, x, spectrum)
        # take a view in order to avoid modification of input data
        y = inputArray[:]
        if y.ndim == 1:
            y = y.reshape(1, 1, -1)
        elif y.ndim == 2:
            oldShape = y.shape
            y = y.reshape(1, oldShape[0], oldShape[1])
        self.info['McaCalib'] = [0.0, 1.0, 0.0]
        self.info["McaIndex"] = 2
        self.info['Channel0'] = 0
        self.info['Dim_1'] = y.shape[0]
        self.info['Dim_2'] = y.shape[1]
        self.info['Dim_3'] = y.shape[2]
        self.info['SourceName'] = SOURCE_TYPE
        self.info['SourceType'] = SOURCE_TYPE
        self.data = y
