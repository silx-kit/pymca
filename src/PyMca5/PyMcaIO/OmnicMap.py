#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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


class OmnicMap(DataObject.DataObject):
    '''
    Class to read OMNIC .map files

    It reads the spectra into a DataObject instance.
    This class  info member contains all the parsed information.
    This class data member contains the map itself as a 3D array.
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
        fid = open(filename, 'rb')
        data = fid.read()
        fid.close()
        fid = None

        try:
            omnicInfo = self._getOmnicInfo(data)
        except Exception:
            omnicInfo = None
        self.sourceName = [filename]
        searchedChain = bytes("Spectrum ", 'utf-8')
        firstByte = data.index(searchedChain)
        s = data[firstByte:(firstByte + 100 - 16)]
        s = str(s)
        _logger.debug("firstByte = %d", firstByte)
        _logger.debug("s1 = %s ", s)
        exp = re.compile(r'(-?[0-9]+\.?[0-9]*)')
        tmpValues = exp.findall(s)
        spectrumIndex = int(tmpValues[0])
        self.nSpectra = int(tmpValues[1])
        if "X = " in s:
            xPosition = float(tmpValues[2])
            yPosition = float(tmpValues[3])
        else:
            # I have to calculate them from the scan
            xPosition, yPosition = self.getPositionFromIndexAndInfo(0, omnicInfo)
        _logger.debug("spectrumIndex, nSpectra, xPosition, yPosition = %d %d %f %f",
                      spectrumIndex, self.nSpectra, xPosition, yPosition)
        chain = bytes("Spectrum", 'utf-8')
        secondByte = data[(firstByte + 1):].index(chain)
        secondByte += firstByte + 1
        _logger.debug("secondByte = %s", secondByte)
        self.nChannels = int((secondByte - firstByte - 100) / 4)
        _logger.debug("nChannels = %d", self.nChannels)
        self.firstSpectrumOffset = firstByte - 16

        #fill the header
        self.header = []
        oldXPosition = xPosition
        oldYPosition = yPosition
        self.nRows = 0
        xPositions = numpy.zeros(self.nSpectra)
        yPositions = numpy.zeros(self.nSpectra)
        calculating = True
        for i in range(self.nSpectra):
            offset = int(firstByte + i * (100 + self.nChannels * 4))
            s = str(data[offset:(offset + 100 - 16)])
            tmpValues = exp.findall(s)
            spectrumIndex = int(tmpValues[0])
            if "X = " in s:
                xPosition = float(tmpValues[2])
                yPosition = float(tmpValues[3])
            else:
                #I have to calculate them from the scan
                xPosition, yPosition = self.getPositionFromIndexAndInfo(i,
                                                                    omnicInfo)
            xPositions[i] = xPosition
            yPositions[i] = yPosition
            if calculating:
                if (abs(yPosition - oldYPosition) > 1.0e-6) and\
                   (abs(xPosition - oldXPosition) < 1.0e-6):
                    calculating = False
                    continue
                self.nRows += 1

        _logger.debug("DIMENSIONS X = %f Y=%d",
                      self.nSpectra * 1.0 / self.nRows, self.nRows)

        #arrange as an EDF Stack
        self.info = {}
        self.__nFiles = int(self.nSpectra / self.nRows)
        try:
            deltaX = (xPositions[-1] - xPositions[0]) / (self.nRows - 1)
            deltaY = (yPositions[-1] - yPositions[0]) / (self.__nFiles - 1)
        except Exception:
            deltaX = None
            deltaY = None
            _logger.warning("Cannot calculate scales")
        self.data = numpy.zeros((self.__nFiles, self.nRows, self.nChannels),
                                 dtype=numpy.float32)

        self.__nImagesPerFile = 1
        offset = firstByte - 16 + 100  # starting position of the data
        delta = 100 + self.nChannels * 4
        fmt = "%df" % self.nChannels
        for i in range(self.__nFiles):
            for j in range(self.nRows):
                # this approach is inneficient when compared to a direct
                # data readout, but it allows to deal with nan at the source
                tmpData = numpy.zeros((self.nChannels,), dtype=numpy.float32)
                tmpData[:] = struct.unpack(fmt,\
                                data[offset:(offset + delta - 100)])
                finiteData = numpy.isfinite(tmpData)
                self.data[i, j, finiteData] = tmpData[finiteData]
                offset = int(offset + delta)
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]

        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        self.info["Size"] = self.__nFiles * self.__nImagesPerFile
        self.info["NumberOfFiles"] = self.__nFiles * 1
        self.info["FileIndex"] = 0
        self.info["Channel0"] = 0.0
        if omnicInfo is not None:
            self.info['McaCalib'] = [omnicInfo['First X value'] * 1.0,
                                     omnicInfo['Data spacing'] * 1.0,
                                     0.0]
        else:
            self.info["McaCalib"] = [0.0, 1.0, 0.0]
        self.info['OmnicInfo'] = omnicInfo
        if deltaX and deltaY:
            if (deltaX > 0.0) and (deltaY > 0.0):
                self.info["xScale"] = [oldXPosition, deltaX] 
                self.info["yScale"] = [oldYPosition, deltaY]
        self.info["positioners"] = {"X":xPositions, "Y":yPositions}

    def _getOmnicInfo(self, data):
        '''
        Parameters:
        -----------
        data : The contents of the .map file

        Returns:
        --------
        A dictionary with acquisition information
        '''
        #additional information
        fmt = "I"  # unsigned long in 32-bit
        offset = 372  # 93*4 unsigned integers
        infoBlockIndex = (struct.unpack(fmt, data[offset:(offset + 4)])[0] - 204) / 4.
        infoBlockIndex = int(infoBlockIndex)
        #infoblock is the position of the information block
        offset = infoBlockIndex * 4
        #read 13 unsigned integers
        nValues = 13
        fmt = "%dI" % nValues
        values = struct.unpack(fmt, data[offset:(offset + 4 * nValues)])
        ddict = {}
        ddict['Number of points'] = values[0]
        ddict['Number of scan points'] = values[6]
        ddict['Interferogram peak position'] = values[7]
        ddict['Number of sample scans'] = values[8]
        ddict['Number of FFT points'] = values[10]
        ddict['Number of background scans'] = values[12]
        offset = (infoBlockIndex + 3) * 4
        nFloats = 47
        fmt = "%df" % nFloats
        vFloats = struct.unpack(fmt, data[offset:(offset + 4 * nFloats)])
        lastX = vFloats[0]
        firstX = vFloats[1]
        ddict['First X value'] = firstX
        ddict['Last X value'] = lastX
        ddict['Identifier for start indices of spectra'] = vFloats[14]
        ddict['Laser frequency'] = vFloats[16]
        ddict['Data spacing'] = (lastX - firstX) / (ddict['Number of points'] - 1.0)
        ddict['Background gain'] = vFloats[10]
        for key in ddict.keys():
            _logger.debug("%s: %s", key, ddict[key])
        ddict.update(self.getMapInformation(data))
        return ddict

    def getMapInformation(self, data):
        '''
        Internal method to help finding spectra coordinates
        Parameters:
        -----------
            data : Contents of the .map file

        Returns:
        --------
            Dictionary with map gemoetrical acquisition parameters
        '''
        #look for the chain 'Position'
        chain = bytes('Position', 'utf-8')
        offset = data.index(chain)
        positions = [offset]
        while True:
            try:
                a = data[(offset + 1):].index(chain)
                offset = a + offset + 1
                positions.append(offset)
            except ValueError:
                break

        ddict = {}
        #map description position
        if (positions[1] - positions[0]) == 66:  # reverse engineered magic number :-)
            mapDescriptionOffset = positions[0] - 90
            mapDescription = struct.unpack('6f', data[mapDescriptionOffset:mapDescriptionOffset + 24])
            y0, y1, deltaY, x0, x1, deltaX = mapDescription
            ddict['First map location'] = [x0, y0]
            ddict['Last map location'] = [x1, y1]
            ddict['Mapping stage X step size'] = deltaX
            ddict['Mapping stage Y step size'] = deltaY
            ddict['Number of spectra'] = abs((1 + ((y1 - y0) / deltaY)) * (1 + ((x1 - x0) / deltaX)))
        for key in ddict.keys():
            _logger.debug("%s: %s", key, ddict[key])
        return ddict

    def getOmnicInfo(self):
        """
        Returns a dictionary with the parsed OMNIC information
        """
        return copy.deepcopy(self.info['OmnicInfo'])

    def getPositionFromIndexAndInfo(self, index, info=None):
        '''
        Internal method to obtain the position at which a spectrum
        was acquired
        Parameters:
        -----------
        index : int
            Index of spectrum
        info : Dictionary
            Information recovered with _getOmnicInfo
        Returns:
        --------
        x, y : floats
            Position at which  the spectrum was acquired.
        '''
        if info is None:
            return 0.0, 0.0
        ddict = info
        #first variation on X and then on Y
        try:
            x0, y0 = ddict['First map location']
        except KeyError:
            return 0.0, 0.0
        x1, y1 = ddict['Last map location']
        deltaX = ddict['Mapping stage X step size']
        deltaY = ddict['Mapping stage Y step size']
        nX = int(1.5 + ((x1 - x0) / deltaX))
        x = x0 + (index % nX) * deltaX
        y = y0 + int(index / nX) * deltaY
        return x, y

if __name__ == "__main__":
    filename = None
    if len(sys.argv) > 2:
        _logger.setLevel(logging.DEBUG)
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    elif os.path.exists("SambaPhg_IR.map"):
        filename = "SambaPhg_IR.map"
    if filename is not None:
        w = OmnicMap(filename)
        print(type(w))
        print(type(w.data[0:10]))
        print(w.data[0:10])
        print("shape = ", w.data.shape)
        print(type(w.info))
        print("INFO = ", w.info['OmnicInfo'])
    else:
        print("Please supply input filename")
