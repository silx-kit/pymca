#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2019 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import numpy
import struct
import time
import logging
from PyMca5 import DataObject
from PyMca5.PyMcaIO import PyMcaIOHelper


_logger = logging.getLogger(__name__)

SOURCE_TYPE = "EdfFileStack"

class SupaVisioMap(DataObject.DataObject):
    def __init__(self, filename):
        DataObject.DataObject.__init__(self)

        fileSize = os.path.getsize(filename)
        fid = open(filename, 'rb')
        data=fid.read()
        fid.close()
        self.sourceName = [filename]
        e0 = time.time()

        values = struct.unpack("%dH" % (len(data)/2), data)
        data = numpy.array(values, numpy.uint16)
        #print values
        nrows = values[1]
        ncols = values[2]
        self.nSpectra = nrows * ncols
        data = data.reshape(int(len(data)/3), 3)
        self.nChannels = data[:,2].max() + 1

        #fill the header
        self.header =[]
        self.nRows = nrows

        #arrange as an EDF Stack
        self.info = {}
        self.__nFiles = (self.nSpectra)/self.nRows
        self.__nImagesPerFile = 1

        e0 = time.time()
        self.data = PyMcaIOHelper.fillSupaVisio(data).astype(numpy.float64);
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i+1,)
            self.info[key] = shape[i]

        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        self.info["Size"]       = self.__nFiles * self.__nImagesPerFile
        self.info["NumberOfFiles"] = self.__nFiles * 1
        self.info["FileIndex"] = 0
        self.info["McaCalib"] = [0.0, 1.0, 0.0]
        self.info["Channel0"] = 0.0

if __name__ == "__main__":
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    elif os.path.exists(r".\PIGE\010826.pige"):
        filename = r".\PIGE\010826.pige"
    if filename is not None:
        _logger.setLevel(logging.DEBUG)
        w = SupaVisioMap(filename)
    else:
        print("Please supply input filename")
