#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2017-2023 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import sys
import numpy
from PyMca5.PyMcaIO import JcampFileParser
from PyMca5.PyMcaCore import DataObject

SOURCE_TYPE = "EdfFileStack"

class JcampOpusStack(DataObject.DataObject):
    def __init__(self, filename):
        DataObject.DataObject.__init__(self)
        fileParser = JcampFileParser.JcampFileParser(filename, single=False)
        scan = fileParser[0]
        fileHeader = scan.fileheader()
        firstHeaderInfo = parseFileHeader(fileHeader)
        if scan.nbmca() == 0:
            scan = fileParser[1]
        nBlocks = firstHeaderInfo["BLOCKS"]
        nbmca = scan.nbmca()

        # take the last mca of the scan
        lastMca = scan.mca(nbmca)
        nChannels = lastMca.size
        calib = scan.header('@CALIB')[0]
        if len(calib):
            calib = [float(x) for x in calib.split()[1:]]
        else:
            calib = [0.0, 1.0, 0.0]
        chann = scan.header('@CHANN')[0]
        if len(chann):
            ctxt = chann.split()
            if len(ctxt) == 5:
                chann = float(ctxt[2])
            else:
                chann = 0.0
        else:
            chann = 0.0

        # assume all mca have the same size, calibration, ...
        data = numpy.zeros((1, nBlocks, nChannels), dtype=numpy.float32)
        nScans = fileParser.scanno()
        mcaIndex = 0
        for i in range(nScans):
            scan = fileParser[i]
            if scan.nbmca():
                mcaData = scan.mca(scan.nbmca())
                data[0, mcaIndex] = mcaData
                mcaIndex += 1

        # make use of the collected information
        # shape
        xShape = firstHeaderInfo.get("$MAP_POINTS_IN_X", None)
        yShape = firstHeaderInfo.get("$MAP_POINTS_IN_Y", None)
        if (xShape is not None) and (yShape is not None):
            if xShape * yShape == nBlocks:
                data = data.reshape(yShape, xShape, nChannels)
            else:
                print("PRODUCT DOES NOT MATCH NUMBER OF BLOCKS")

        #scales
        xScale = [0.0, 1.0]
        yScale = [0.0, 1.0]
        xScale[0] = firstHeaderInfo.get("$MAP_ORIGIN_X", 0.0)
        xScale[1] = firstHeaderInfo.get("$MAP_DELTA_X", 1.0)
        yScale[0] = firstHeaderInfo.get("$MAP_ORIGIN_Y", 0.0)
        yScale[1] = firstHeaderInfo.get("$MAP_DELTA_Y", 1.0)
        
        self.sourceName = filename
        self.info = {}
        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]
        self.info["NumberOfFiles"] = 1
        self.info["McaIndex"] = 2
        self.info["McaCalib"] = calib
        self.info["Channel0"] = chann
        self.info["xScale"] = xScale
        self.info["yScale"] = yScale
        self.data = data

def parseFileHeader(lines):
    ddict = {}
    for line in lines:
        key, content = line.split("=")
        key = key[2:]
        if key in ["BLOCKS", "$MAP_POINTS_IN_X", "$MAP_POINTS_IN_Y"]:
            ddict[key] = int(content)
        else:
            try:
                ddict[key] = float(content)
            except Exception:
                ddict[key] = content
    return ddict

def isJcampOpusStackFile(filename):
    if not JcampFileParser.isJcampFile(filename):
        return False
    # Parse the first scan
    jcamp = JcampFileParser.JcampFileParser(filename, single=True)
    scan = jcamp[0]
    header = parseFileHeader(scan.fileheader())
    if "BLOCKS" in header:
        if header["BLOCKS"] > 1:
            return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python JCAMPFileParser.py filename")
        sys.exit(0)
    actualOpus = isJcampOpusStackFile(sys.argv[1])
    print(" isJcampOpusStackFile = ", actualOpus)
    if actualOpus:
        stack = JcampOpusStack(sys.argv[1])
        print("info = ", stack.info)
    #print("list = ", sf.list())
    #print("select = ", sf.select(sf.list()[0]))
