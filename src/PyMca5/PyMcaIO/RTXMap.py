#!/usr/bin/env python
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
import sys
import os
import numpy
import types
import logging

_logger = logging.getLogger(__name__)

#the file format is based on XML
import xml.etree.ElementTree as ElementTree
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaIO import ArtaxFileParser
from PyMca5.PyMcaIO import SpecFileStack
#SOURCE_TYPE = "EdfFileStack"
SOURCE_TYPE ="SpecFileStack"

myFloat = ArtaxFileParser.myFloat

class RTXMap(DataObject.DataObject):
    '''
    Class to read ARTAX .rtx files
    '''
    def __init__(self, filename):
        '''
        Parameters:
        -----------
        filename : str
            Name of the .rtx file.
        '''
        if not os.path.exists(filename):
            raise IOError("File %s does not exists"  % filename)

        if 0:
            # this works but it is very slow
            DataObject.DataObject.__init__(self)
            stack = SpecFileStack.SpecFileStack(filename)
            self.data = stack.data
            self.info = stack.info
            return

        sf = ArtaxFileParser.ArtaxFileParser(filename)
        # get some Artax map specific information
        tScanInfo = sf.artaxTScanInfo

        # the rest is specfile like
        nScans = sf.scanno()
        scan = sf[0]
        calib0 = scan.header("@CALIB")
        ctime = scan.header("@CTIME")
        positioners = None
        motorNames = sf.allmotors()
        # assuming dictionaries are ordered
        if len(motorNames):
            # test if last scan also contains motors
            # processed files contain an additional sum spectrum
            if len(sf[-1].allmotorpos()) == 0:
                _logger.info("Last scan does not contain motors. Ignoring it")
            nScans -= 1
            positioners = {}
            for mne in motorNames:
                positioners[mne] = numpy.zeros((nScans,),
                                               dtype=numpy.float32)
        if ctime:
            liveTime = numpy.zeros((nScans,), dtype=numpy.float32)
        spectrum = sf[0].mca(1)
        data = numpy.zeros((1, nScans, len(spectrum)),
                            dtype=numpy.float32)
        for i in range(nScans):
            scan = sf[i]
            if ctime:
                ctime = scan.header("@CTIME")[0]
                liveTime[i] = myFloat(ctime.split()[-2])
            if positioners:
                motorPos = scan.allmotorpos()
                for mneIdx in range(len(motorNames)):
                    mne = motorNames[mneIdx]
                    positioners[mne][i] = motorPos[mneIdx]
            data[0, i] = scan.mca(1)
        DataObject.DataObject.__init__(self)
        self.data = data
        if positioners:
            self.info["positioners"] = positioners
        if ctime:
            self.info["McaLiveTime"] = liveTime
        self.info["McaCalib"] = [myFloat(x) for x in calib0[0].split()[1:]]
        self.info["SourceName"] = os.path.abspath(filename)
        
        if tScanInfo.get("Mapping", False):
            _logger.info("Regular Artax Map")
        else:
            _logger.info("Non-regular Artax Map")

        # we are supposed to have a regular map
        # let's figure out the shape?
        # It seems the {AxisName}First and {AxisName}Last information is
        # not reliable to decide the scanned motors.
        axes = []
        if positioners:
            for axis in positioners:
                # Axis0, Axis1, Axis2 typically named x, y, z
                if numpy.all(numpy.isfinite(positioners[axis])):
                    axes.append(axis)
            
        if len(axes) in [0, 1]:
            # we do not need to figure out any regular shape
            return
        elif len(axes) == 2:
            # potentially variating X, Y and Z
            x = positioners[axes[0]]
            y = positioners[axes[1]]
            deltaX = x[-1] - x[0]
            deltaY = y[-1] - y[0]
            deltaZ = 0.0
        elif len(axes) == 3:
            # potentially variating X, Y and Z
            x = positioners[axes[0]]
            y = positioners[axes[1]]
            z = positioners[axes[2]]
            deltaX = x[-1] - x[0]
            deltaY = y[-1] - y[0]
            deltaZ = z[-1] - z[0]
        else:
            # wait for the case to appear
            return

        epsilon = 1.0e-8
        meshType = None
        if abs(deltaX) > epsilon and \
           abs(deltaY) > epsilon and \
           abs(deltaZ) > epsilon:
            # XYZ scan
            # do not try to figure out any shape
            _logger.info("XYZ scan")
            meshType = "XYZ"
        elif abs(deltaX) < epsilon:
            # Y and Z variating
            if abs(y[1] - y[0]) < epsilon:
                meshType = "ZY"
            else:
                meshType = "YZ"
        elif abs(deltaY) < epsilon:
            # X and Z variating
            if abs(x[1] - x[0]) < epsilon:
                meshType = "ZX"
            else:
                meshType = "XZ"
        elif abs(deltaZ) < epsilon:
            # X and Y variating
            if abs(x[1] - x[0]) < epsilon:
                meshType = "YX"
            else:
                meshType = "XY"
        else:
            _logger.info("Unknown scan type")

        if meshType in [None, "XYZ"]:
            # the only safe solution is a scatter plot
            return

        _logger.info("%s scan" % meshType)


        # the only safe solution is a scatter plot but attempt to
        # interpret as a regular map
        for axis in meshType:
            key=axis+"First"
            if not numpy.isfinite(tScanInfo[key]):
                meshType = None
                break

        if meshType == "XY":
            x = positioners[axes[0]]
            y = positioners[axes[1]]
        elif meshType == "YX":
            x = positioners[axes[1]]
            y = positioners[axes[0]]
        elif meshType == "XZ":
            x = positioners[axes[0]]
            y = positioners[axes[2]]
        elif meshType == "ZX":
            x = positioners[axes[2]]
            y = positioners[axes[0]]
        elif meshType == "YZ":
            x = positioners[axes[1]]
            y = positioners[axes[2]]
        elif meshType == "ZY":
            x = positioners[axes[2]]
            y = positioners[axes[1]]
        else:
            return

        if len(x) == 1 or len(y) == 1:
            return

        xFirst = x[0]
        xLast = x[-1]
        yFirst = y[0]
        yLast = y[-1]

        reasonableDeltaX = numpy.abs(x.max() - x.min()) / (1.0 + len(x))
        reasonableDeltaY = numpy.abs(y.max() - y.min()) / (1.0 + len(y))
        if numpy.abs(x[1] - x[0]) > reasonableDeltaX:
            x0 = x[0]
            i = 1
            while (i < len(x)) and (numpy.abs(x[i] - x[0]) > reasonableDeltaX):
                i += 1
            nColumns = i
        else:
            x0 = x[0]
            i = 0
            while (i < len(x)) and (numpy.abs(x[i] - x[0]) < reasonableDeltaX):
                i += 1
            nColumns = i
        # the scan can be in zig-zag
        # it is safer to rely on the scatter view
        if nScans % nColumns == 0:
            nRows = nScans // nColumns
            self.data = self.data.reshape(nRows, nColumns, -1)
            self.info["xScale"] = [xFirst, (xLast - xFirst) / nColumns]
            self.info["yScale"] = [yFirst, (yLast - yFirst) / nRows]

def isRTXMap(filename):
    try:
        if filename[-3:].lower() not in ["rtx", "spx"]:
            return False
        with open(filename, 'rb') as f:
            # expected to read an xml file
            someChar = f.read(20).decode()
        if "<" in someChar and "xml version" in someChar:
            return True
    except Exception:
        pass
    return False

def test(filename):
    print("isRTXMap?  = ", isRTXMap(filename))
    a = RTXMap(filename)
    print("info = ", a.info)
    print("Data shape = ", a.data.shape)

if __name__ == "__main__":
    test(sys.argv[1])
