#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2014 European Synchrotron Radiation Facility
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
import numpy
from PyMca5 import DataObject
from PyMca5.PyMcaIO import specfilewrapper as specfile

SOURCE_TYPE = "SpecFileStack"


class OpusDPTMap(DataObject.DataObject):
    def __init__(self, filename):
        DataObject.DataObject.__init__(self)
        sf = specfile.Specfile(filename)
        scan = sf[1]
        data = scan.data()
        nMca, nchannels = data.shape
        nMca = nMca - 1
        xValues = data[0, :] * 1
        xValues = numpy.ravel(xValues)
        if 0:
            self.data = numpy.zeros((nMca, nchannels), numpy.float32)
            self.data[:, :] = data[1:, :]
            self.data = self.data.reshape(1, nMca, nchannels)
        else:
            self.data = data[1:, :]
            self.data = self.data.reshape(1, nMca, nchannels)
        data = None

        #perform a least squares adjustment to a line
        x = numpy.arange(nchannels).astype(numpy.float32)
        Sxy = numpy.dot(x, xValues.T)
        Sxx = numpy.dot(x, x.T)
        Sx  = x.sum()
        Sy  = xValues.sum()
        d = nchannels * Sxx - Sx * Sx
        zero = (Sxx * Sy - Sx * Sxy) / d
        gain = (nchannels * Sxy - Sx * Sy) / d

        #and fill the requested information to be identified as a stack
        self.info['SourceName'] = [filename]
        self.info["SourceType"] = "SpecFileStack"
        self.info["Size"]       = 1, nMca, nchannels
        self.info["NumberOfFiles"] = 1
        self.info["FileIndex"] = 0
        self.info["McaCalib"] = [zero, gain, 0.0]
        self.info["Channel0"] = 0.0


def main():
    import sys
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    if filename is not None:
        OpusDPTMap(filename)
    else:
        print("Please supply input filename")

if __name__ == "__main__":
    main()
