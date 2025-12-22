#!/usr/bin/env python
#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
from __future__ import with_statement
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
This module reads Renishaw Raman MAP measurements exported as .txt file.

The native .wxd file has to be converted to .txt using Renishaw tools.

The output ASCII file has no headers. It contains several columns, their meaning
being different according to the type of data. Some possibilities:

columns

wavelength value
z wavelength value
time wavelength value
y x wavelength value

Of all the previous possibilities, this module only supports the last one.

"""
import os
import sys
import re
import numpy
from PyMca5.PyMcaCore import DataObject

SOURCE_TYPE = "EdfFileStack"

class RenishawMap(DataObject.DataObject):
    def __init__(self, filename, infofile=None):
        DataObject.DataObject.__init__(self)

        # allocate buffers greater than any spected number of channels
        x = numpy.zeros((10000,), numpy.float32)
        y = numpy.zeros((10000,), numpy.float32)
        wl = numpy.zeros((10000,), numpy.float32)
        data = numpy.zeros((10000,), numpy.float32)
        #import time
        #t0 = time.time()
        with open(filename, 'r') as f:
            nChannels = 0
            for line in f:
                # read the first line
                if "X" in line.upper() and \
                   "Y" in line.upper() and \
                   "WAVE" in line.upper() and \
                   "INTENSITY" in line.upper():
                    continue
                y[nChannels], x[nChannels], wl[nChannels], data[nChannels] = \
                              [float(value) for value in line.split("\t")]
                if nChannels == 0:
                    firstChannel = wl[0]
                elif wl[nChannels] == firstChannel:
                    break
                nChannels += 1
            if y[0] == y[nChannels]:
                firstChangesFirst = False
            else:
                firstChangesFirst = True
            nLines = nChannels + 1 + sum([1 for l in f])
        #print("ELAPSED 0 = ", time.time() - t0)
        if nLines % nChannels:
            raise IOError("Not a regular Renishaw map or a not a complete file")
        nSpectra = int(nLines / nChannels)
        #print("N Channels = %d" % nChannels)
        #print("N Lines = %d" % nLines)
        #print("N Spectra = %f" % (nLines/nChannels))

        rows = numpy.zeros((nSpectra,), numpy.float32)
        columns = numpy.zeros((nSpectra,), numpy.float32)
        wl = numpy.array(wl[:nChannels], dtype=numpy.float32)
        data = numpy.zeros((nSpectra, nChannels), numpy.float32)
        nRows = 0
        nColumns = 0
        #t0 = time.time()
        myFloat = numpy.float32
        actualRows = []
        actualColumns = []
        indices = [None] * nSpectra
        with open(filename, 'r') as f:
            for i in range(nSpectra):
                for j in range(nChannels):
                    line = f.readline()
                    if "X" in line.upper() and \
                       "Y" in line.upper() and \
                       "WAVE" in line.upper() and \
                       "INTENSITY" in line.upper():
                        line = f.readline()
                if firstChangesFirst:
                    column, row, dummy1, dummy2 = \
                            [float(value) for value in line.split("\t")]
                else:
                    row, column, dummy1, dummy2 = \
                            [float(value) for value in line.split("\t")]
                #positions.append((row, column, i))
                if row not in actualRows:
                    actualRows.append(row)
                if column not in actualColumns:
                    actualColumns.append(column)
                indices[i] = (actualRows.index(row), actualColumns.index(column))
        nRows = len(actualRows)
        nColumns = len(actualColumns)
        #positions.sort()
        data = data.reshape(nRows, nColumns, nChannels)
        with open(filename, 'r') as f:
            for i in range(nSpectra):
                row, column = indices[i]
                for j in range(nChannels):
                    line = f.readline()
                    if "X" in line.upper() and \
                       "Y" in line.upper() and \
                       "WAVE" in line.upper() and \
                       "INTENSITY" in line.upper():
                        line = f.readline()
                    d1, d2, d3, data[row, column, j] = \
                              [myFloat(value) for value in line.split("\t")]
        #print "nRows = ", nRows
        #print "nColumns= ", nColumns
        #print columns[::nColumns]
        #print rows[::nRows]
        #print "product = ", nRows * nColumns
        #print("ELAPSED tinal = ", time.time() - t0)

        # arrange as EDF stack
        self.sourceName = filename
        self.data = data
        self.info = {}
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]
        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        self.info["Size"]       = 1
        self.info["NumberOfFiles"] = 1
        self.info["FileIndex"] = 0
        self.info["McaIndex"] = 2
        self.info["McaCalib"] = [0.0, 1.0, 0.0]
        self.info["Channel0"] = 0.0
        self.x = [wl]

def isRenishawMapFile(filename):
    try:
        if filename.endswith(".txt"):
            with open(filename, 'r') as f:
                line = f.readline().upper()
                if "X" in line and \
                   "Y" in line and \
                   "WAVE" in line and \
                   "INTENSITY" in line:
                    line = f.readline()
                line = line.split("\t")
            y, x, wl, data = [float(item) for item in line]
            return True
    except Exception:
        # it is not a Renishaw map file
        pass
    return False

if __name__ == "__main__":
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    print("is Renishaw File?", isRenishawMapFile(filename))
    instance = RenishawMap(filename)
    print(instance.info)
    print(instance.data.size)
