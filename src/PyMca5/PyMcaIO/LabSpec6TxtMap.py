#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2022 European Synchrotron Radiation Facility
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
import re
import struct
import numpy
import copy
import logging
from PyMca5 import DataObject


_logger = logging.getLogger(__name__)

SOURCE_TYPE = "EdfFileStack"


class LabSpec6TxtMap(DataObject.DataObject):
    '''
    Class to read LabSpec6 .map files exported as txt

    It reads the spectra into a DataObject instance.
    This class  info member contains all the parsed information.
    This class data member contains the map itself as a 3D array.
    This class x member contains the abscisa of the spectra
    This class info["positioners"] contains the acquisition coordinates
    '''

    def __init__(self, filename):
        '''
        Parameters:
        -----------
        filename : str
            Name of the .map file.
            It is expected to work with OMNIC versions 7.x and 8.x
        '''
        DataObject.DataObject.__init__(self)
        fid = open(filename, 'r')
        data = fid.readlines()
        fid.close()
        fid = None

        headerInfo, x, spectra, positioners = self._parseContents(data)

        self.sourceName = [filename]
        self.data = spectra
        self.x = [x]
        self.info["positioners"] = {}
        if positioners.shape[1] > 0:
            self.info["positioners"]["X"] = numpy.array(positioners[:, 0],
                                                        copy=True).reshape(-1)
        if positioners.shape[1] > 1:
            self.info["positioners"]["Y"] = numpy.array(positioners[:, 1],
                                                        copy=True).reshape(-1)
        if positioners.shape[1] > 2:
            self.info["positioners"]["Z"] = numpy.array(positioners[:, 2],
                                                        copy=True).reshape(-1)

        nSpectra = self.data.shape[0]
        nRows = 1
        nColumns = 1
        if nSpectra > 1:
            if self.info["positioners"]["X"][0] == \
                self.info["positioners"]["X"][1]:
                for i in range(nSpectra - 1):
                    if self.info["positioners"]["X"][i] == \
                        self.info["positioners"]["X"][i+1]:
                        nRows += 1
                    else:
                        break
                nColumns = nSpectra // nRows
            else:
                for i in range(1, nSpectra):
                    if self.info["positioners"]["X"][i] != \
                        self.info["positioners"]["X"][0]:
                        nColumns += 1
                nRows = nSpectra // nColumns
        _logger.debug("DIMENSIONS X = %f Y=%d",
                      nSpectra * 1.0 / nRows, nRows)
        self.data = self.data.reshape(nRows, nColumns, -1)

        #arrange as an EDF Stack
        if positioners.shape[1] == 2 and (nSpectra > 1):
            xPositions = positioners[:, 0]
            yPositions = positioners[:, 1]
            deltaX = (xPositions[-1] - xPositions[0]) / (nRows - 1)
            deltaY = (yPositions[-1] - yPositions[0]) / (nColumns - 1)
        else:
            deltaX = None
            deltaY = None
            _logger.warning("Cannot calculate scales")

        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]

        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        self.info["Size"] = nSpectra
        self.info["NumberOfFiles"] = 1
        self.info["FileIndex"] = 0
        self.info["Channel0"] = 0.0
        self.info["McaCalib"] = [0.0, 1.0, 0.0]
        self.info['HeaderInfo'] = headerInfo
        if deltaX and deltaY:
            if (abs(deltaX) > 0.0) and (abs(deltaY) > 0.0):
                self.info["xScale"] = [xPositions[0], deltaX] 
                self.info["yScale"] = [yPositions[0], deltaY]

    def _parseContents(self, data):
        '''
        Parameters:
        -----------
        data : The contents of the .txt map file

        Returns:
        --------
        A dictionary with acquisition information
        '''

        # --- header ---
        i = 0
        info = {}
        for line in data:
            if line.startswith("#"):
                tokens = line[1:].split("=")
                info[tokens[0]] = tokens[1].replace("\t","").replace("\n","")
                i += 1
            else:
                break

        # --- Spectrum X values ---
        # two possibilities
        # exp = re.compile(r'(-?[0-9]+\.?[0-9]*)')
        # [float(token) for tokein in exp.findall(string)]
        # or
        # [float(token) for token in re.split('\t|\n| ', string) if len(token)]        

        exp = re.compile(r'(-?[0-9]+\.?[0-9]*)')
        x = [float(token) for token in exp.findall(data[i])]
        i += 1


        # spectra and positions
        n_channels = len(x)
        n_points = len(data[i:])

        #print("Number of channels %s", n_channels)
        #print("Number of spectra %s", n_points)

        x = numpy.array(x, dtype=numpy.float32)

        values = [float(token) for token in re.split('\t|\n| ', data[i]) if len(token)]
        n_positioners = len(values) - n_channels

        spectra = numpy.zeros((n_points, n_channels), numpy.float32)
        positioners = numpy.zeros((n_points, n_positioners), numpy.float32)


        for j in range(n_points):
            line = data[j+i]
            values = [float(token) for token in exp.findall(line)]
            positioners[j, :] = values[:n_positioners]
            spectra[j, :] = values[n_positioners:]
        return info, x, spectra, positioners

if __name__ == "__main__":
    filename = None
    _logger.setLevel(logging.DEBUG)
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    elif os.path.exists("map.txt"):
        filename = "map.txt"
    if filename is not None:
        w = LabSpec6TxtMap(filename)
        print(type(w))
        print(type(w.data[0:10]))
        print(w.data[0:10])
        print("shape = ", w.data.shape)
        print(type(w.info))
        print("INFO = ", w.info['HeaderInfo'])
        print("Positioners = ", w.info['positioners'])
    else:
        print("Please supply input filename")
