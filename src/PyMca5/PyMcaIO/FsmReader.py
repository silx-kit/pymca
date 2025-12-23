#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2023 European Synchrotron Radiation Facility
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
import struct
import numpy

__doc__ = """
Reads IR maps from Perkin Elmer files.

The files are structured in a set of blocks.

The most relevant ones are:

5100 - Data
5101 - Coordinates

"""


def _parse5100(fid):
    # 5100
    blockNameLength = struct.unpack('<H', fid.read(2))[0]
    #print("blockNameLength = ", blockNameLength)
    blockName = fid.read(blockNameLength)
    if hasattr(blockName, "decode"):
        blockName = blockName.decode("utf-8")
    #print("blockName = ", blockName)
    fmt = '<ddd'
    size = struct.calcsize(fmt)
    xDelta, yDelta, zDelta = struct.unpack(fmt, fid.read(size))
    fmt = '<dd'
    size = struct.calcsize(fmt)
    zStart, zEnd = struct.unpack(fmt, fid.read(size))
    dataMin, dataMax = struct.unpack(fmt, fid.read(size))
    fmt = '<ddd'
    size = struct.calcsize(fmt)
    x0, y0, z0 = struct.unpack(fmt, fid.read(size))
    fmt = '<iii'
    size = struct.calcsize(fmt)
    xLen, yLen, zLen = struct.unpack(fmt, fid.read(size))

    # get the labels
    for i in range(4):
        length = struct.unpack('<h', fid.read(2))[0]
        text = fid.read(length)
        if hasattr(text, "decode"):
            text = text.decode("utf-8")
        if i == 0:
            xLabel = text
        elif i == 1:
            yLabel = text
        elif i == 3:
            zLabel = text
        else:
            wLabel = text
        #print("text%d = %s" % (i,text))
    return {"xStart": x0,
            "yStart": y0,
            "zStart": z0,
            "xDelta": xDelta,
            "yDelta": yDelta,
            "zDelta": zDelta,
            "xLength": xLen,
            "yLength": yLen,
            "zLength": zLen,
            "labels": (xLabel, yLabel, zLabel, wLabel),
            "xLabel": xLabel,
            "yLabel": yLabel,
            "zLabel": zLabel,
            "dataMin": dataMin,
            "dataMax": dataMax}

def parseFile(filename):
    fid = open(filename, mode='rb')
    # should we read the whole file into memory?
    signature = fid.read(4)
    if signature not in ["PEPE", b"PEPE"]:
        raise IOError("This does not look like a PE Fsm file")
    comment = fid.read(40)
    if hasattr(comment, "decode"):
        comment = comment.decode("utf-8")
    if hasattr(comment, "strip"):
        comment = comment.strip("\0")
    # read 6 bytes indicating block ID and block size
    blockHeader = fid.read(6)
    idx = 0
    while len(blockHeader) == 6:
        blockId, blockSize = struct.unpack('<Hi', blockHeader)
        if blockId == 5100:
            info = _parse5100(fid)
            nRows = info["yLength"]
            nColumns = info["xLength"]
            data = None 
        elif blockId == 5105:
            blockContent = fid.read(blockSize)
            # data are stored as 32 bit floats
            if data is None:
                tmpData = numpy.frombuffer(blockContent,
                                           dtype=numpy.float32)
                nChannels = tmpData.shape[0]
                data = numpy.zeros((nRows * nColumns, nChannels),
                                dtype=numpy.float32)
                data[idx] = tmpData
            else:
                data[idx] = numpy.frombuffer(blockContent,
                                             dtype=numpy.float32)
            idx += 1 
        else:
            blockContent = fid.read(blockSize)
            if len(blockContent) < blockSize:
                raise IOError("Cannot read block %d" % blockId)
        blockHeader = fid.read(6)
    info["Title"] = comment
    data = data.reshape(nRows, nColumns, nChannels)
    return info, data

def isFsmFile(filename):
    isSupported = False
    try:
        if not hasattr(filename, "seek"):
            fid = open(filename, mode='rb')
            owner = True
        else:
            fid =filename
            current = fid.tell()
            fid.seek(0)
        signature = fid.read(4)
        if signature in ["PEPE", b"PEPE"]:
            isSupported = True
    except Exception:
        isSupported = False
    if owner:
        fid.close()
    else:
        fid.seek(current)
    return isSupported

if __name__ == "__main__":
    import sys
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    print("is PE fms File?", isFsmFile(filename))
    info, data = parseFile(filename)
    print(info)
