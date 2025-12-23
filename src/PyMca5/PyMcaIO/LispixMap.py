#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2022 European Synchrotron Radiation Facility
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
import struct
import numpy
import logging
from PyMca5 import DataObject

_logger = logging.getLogger(__name__)

SOURCE_TYPE = "EdfFileStack"

class LispixMap(DataObject.DataObject):
    '''
    Class to read Lispix files (Raw file described by a header file)

    It reads the spectra into a DataObject instance.
    This class info member contains all the parsed information.
    This class data member contains the map itself as a 3D array.
    '''
    
    def __init__(self, filename, native=False):
        '''
        Parameters:
        -----------
        filename : str
            Name of the input file.
        native : boolean (default False)
            If set to False, it will always return a stack of spectra.
            It set to True, it will return what it is specified in the original file.
        '''
        dataFile, headerFile = _getDataAndDescriptionFileName(filename)
        description = _parseHeaderFile(headerFile)

        columns = description.get("width", None)
        rows = description.get("height", None)
        if columns is None:
            raise IOError("Missing width field")
        if rows is None:
            raise IOError("Missing height field")
        offset = description["offset"]
        channels = description["depth"]        
        if description["data-type"] in ["float", "double"]:
            if description["data-length"] == 4:
                dtype = numpy.float32
                fmt = "f"
            elif description["data-length"] == 8:
                dtype = numpy.float64
                fmt = "d"
            else:
                raise ValueError("Out of standard float length %d" % description["data-length"])
        elif description["data-type"] == "signed":
            if description["data-length"] == 1:
                dtype = numpy.int8
                fmt = "b"
            elif description["data-length"] == 2:
                dtype = numpy.int16
                fmt = "h"
            elif description["data-length"] == 4:
                dtype = numpy.int32
                fmt = "l"                      
            elif description["data-length"] == 8:
                dtype = numpy.int64
                fmt = "q"
        elif description["data-type"] == "unsigned":
            if description["data-length"] == 1:
                dtype = numpy.uint8
                fmt = "B"
            elif description["data-length"] == 2:
                dtype = numpy.uint16
                fmt = "H"
            elif description["data-length"] == 4:
                dtype = numpy.uint32
                fmt = "L"
            elif description["data-length"] == 8:
                dtype = numpy.uint64
                fmt = "Q"
        else:
            raise IOError("Unknown data-type:  <%s>" % description["data-type"])

        if (description["record-by"] == "image") and (not native):
            # we have to convert to stack of spectra to make sure all PyMca
            # functionalities (particularly fitting) are available
            if dtype in [numpy.int8, numpy.uint8, numpy.int16, numpy.uint16]:
                # force stack of spectra with floating point values
                self.data = numpy.zeros((rows, columns, channels), dtype=numpy.float32)
            else:
                self.data = numpy.zeros((rows, columns, channels), dtype=dtype)
            try:
                f =open(dataFile, "rb")
                dataBuffer = f.read(offset)
                if description["byte-order"] in ["big-endian", "high-endian"]:
                    fmt = ">%d%s" % (rows * columns, fmt)
                else:
                    fmt = "<%d%s" % (rows * columns, fmt)
                nBytes = struct.calcsize(fmt)
                for i in range(channels):
                    tmpData = numpy.array(struct.unpack(fmt, f.read(nBytes)), dtype=self.data.dtype)
                    tmpData = tmpData.reshape(rows, columns)
                    self.data[:, :, i] = tmpData
            finally:
                f.close()
            mcaIndex = 2
        elif (offset == 0) and (dtype not in [numpy.int8, numpy.uint8, numpy.int16, numpy.uint16]):
            # direct, native readout using numpy
            self.data = numpy.fromfile(dataFile, dtype=dtype)
            native = True
        elif description["record-by"] == "image":
            if dtype in [numpy.int8, numpy.uint8, numpy.int16, numpy.uint16]:
                # force stack of spectra with floating point values
                self.data = numpy.zeros((channels, rows, columns), dtype=numpy.float32)
            else:
                self.data = numpy.zeros((channels, rows, columns), dtype=dtype)
            try:
                f =open(dataFile, "rb")
                dataBuffer = f.read(offset)
                if description["byte-order"] in ["big-endian", "high-endian"]:
                    fmt = ">%d%s" % (rows * columns, fmt)
                else:
                    fmt = "<%d%s" % (rows * columns, fmt)
                nBytes = struct.calcsize(fmt)
                for i in range(channels):
                    tmpData = numpy.array(struct.unpack(fmt, f.read(nBytes)), dtype=self.data.dtype)
                    tmpData = tmpData.reshape(rows, columns)
                    self.data[i] = tmpData
            finally:
                f.close()
            native = True
        elif description["record-by"] != "image":
            if dtype in [numpy.int8, numpy.uint8, numpy.int16, numpy.uint16]:
                # force stack of spectra with floating point values
                self.data = numpy.zeros((rows, columns, channels), dtype=numpy.float32)
            else:
                self.data = numpy.zeros((rows, columns, channels), dtype=dtype)
            try:
                f =open(dataFile, "rb")
                dataBuffer = f.read(offset)
                if description["byte-order"] in ["big-endian", "high-endian"]:
                    fmt = ">%d%s" % (columns * channels, fmt)
                else:
                    fmt = "<%d%s" % (columns * channels, fmt)
                nBytes = struct.calcsize(fmt)
                for i in range(rows):
                    tmpData = numpy.array(struct.unpack(fmt, f.read(nBytes)), dtype=self.data.dtype)
                    tmpData = tmpData.reshape(columns, channels)
                    self.data[i] = tmpData
            finally:
                f.close()
            native = True
        else:
            raise IOError("Unhandled reading case. I should not reach this point")

        if native:
            if description["record-by"] == "image":
                self.data = self.data.reshape(channels, rows, columns)
                mcaIndex = 0
            elif description["record-by"] == "vector":
                self.data = self.data.reshape(rows, columns, channels)
                mcaIndex = 2
            else:
                _logger.info("Assuming spectra")
                self.data = self.data.reshape(rows, columns, channels)
                mcaIndex = 2

        self.sourceName = filename
        self.info = {}
        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]
        self.info["NumberOfFiles"] = 1
        self.info["McaIndex"] = mcaIndex
        self.info["McaCalib"] = [0.0, 1.0, 0.0]
        self.info["Channel0"] = 0.0

def _getDataAndDescriptionFileName(filename):
    """
    Given a file name, returns the name of the associated raw data file
    and associated rpl description file.

    If the associated file is not existing, it returns None.
    """
    tmpFileName = filename.lower()
    if tmpFileName.endswith(".raw"):
        dataDile = filename 
        headerFile = filename[:-3] + "rpl"
    elif tmpFileName.endswith(".rpl"):
        headerFile = filename
    else:
        headerFile = "input file not .rpl"
        dataFile = "input file not .raw"
    if os.path.exists(headerFile):
        dataFile = headerFile[:-3] + "raw"
    else:
        headerFile = ".rpl file not found"
        dataFile = ".raw file not found"
    return dataFile, headerFile

def _parseHeaderFile(headerFile):
    """
    Given the input header file describing the data, returns a dictionary
    with the description of the binary data:

    key         value
    width         187                # pixels per row
    height        184                # rows
    depth        4096                # images or spectrum points
    offset          0                # bytes to skip
    data-length     2                # bytes per pixel
    data-type       unsigned         # possible values: signed, unsigned or float
    byte-order      little-endian    # big-endian, little-endian, or dont-care
    record-by       vector           # image, vector, or dont-care
    
    """
    f = open(headerFile, "r")
    data = f.readlines()
    f.close()
    numericKeyList = ["width",
                      "height",
                      "depth",
                      "offset",
                      "data-length"]
    asciiKeyList = ["data-type",
                    "byte-order",
                    "record-by"]
    otherKeys = []
    description = {}
    description["depth"] = 1
    description["offset"] = 0
    description["data-length"] = 1
    description["data-type"] = "unsigned"
    description["byte-order"] = "little-endian"
    for tmpLine in data:
        treated = False
        line = tmpLine.lower()
        for key in numericKeyList:
            if line.startswith(key):
                cleanLine = line.replace("\t", " ")
                cleanLine = cleanLine.replace("\n", "")
                cleanLine = cleanLine.replace("\r", "")
                content = cleanLine.split(key)[-1]
                content = int(content.strip(" "))
                description[key.lower()] = content
                treated = True
                break
        if not treated:
            for key in asciiKeyList:
                if line.startswith(key):
                    cleanLine = line.replace("\t", " ")
                    cleanLine = cleanLine.replace("\n", "")
                    cleanLine = cleanLine.replace("\r", "")
                    content = cleanLine.split(key)[-1]
                    content = content.strip(" ")
                    description[key.lower()] = content.lower()
                    treated = True
                    break
        if not treated:
            content = line.replace("\t", " ")
            if len(content.strip(" ")):
                _logger.debug("Ignored line: %s", line)
    return description


def isLispixMapFile(filename):
    dataFile, descriptionFile = _getDataAndDescriptionFileName(filename)
    if os.path.exists(descriptionFile) and os.path.exists(dataFile):
        return True
    return False

if __name__ == "__main__":
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    print("is Lispix File?", isLispixMapFile(filename))
    instance = LispixMap(filename)
    print(instance.info)
    print(instance.data.size)
