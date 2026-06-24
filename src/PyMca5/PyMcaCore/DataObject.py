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
__author__ = "V. Armando Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy

class DataObject(object):
    '''
    Simple container of an array and associated information.
    Basically it has the members:
    info: A dictionary
    data: An array, usually 2D, 3D, ...

    In the past also incorporated selection methods.
    Now each different data source implements its selection methods.

    Plotting routines may add additional members

    x: A list containing arrays to be considered axes
    y: A list of data to be considered as signals
    m: A list containing the monitor data
    '''
    GETINFO_DEPRECATION_WARNING = True
    GETDATA_DEPRECATION_WARNING = True
    SELECT_DEPRECATION_WARNING = True

    def __init__(self):
        '''
        Default Constructor
        '''
        self.info = {}
        self.data = numpy.array([])

    def padIncompleteScan(self, imageShape, padPositioners=False, mcaIndex=-1):
        """
        Pad an incomplete/unfinished scan with NaN.
        Result array have channels as the last dimension.

        :param imageShape: desired shape after padding (without the channels)
        :param bool padPositioners: also pad the per-point positioners with NaN.
        """
        
        nChannels = self.data.shape[mcaIndex]
        imageShape = tuple(int(d) for d in imageShape)
        finalShape = imageShape + (nChannels,)
        nOld = numpy.prod(numpy.delete(self.data.shape, mcaIndex))
        numberOfSpectra = int(numpy.prod(imageShape))
        if numberOfSpectra <= nOld:
            return
        if self.data.dtype in (numpy.float16, numpy.float32):
            dtype = self.data.dtype
        else:
            dtype = numpy.float64
        padded = numpy.full((numberOfSpectra, nChannels), numpy.nan, dtype=dtype)
        reorderedData = numpy.moveaxis(self.data, mcaIndex, -1)
        padded[:nOld] = reorderedData.reshape(nOld, nChannels)
        self.data = padded.reshape(finalShape)
        for i in range(len(self.data.shape)):
            self.info["Dim_%d" % (i + 1)] = self.data.shape[i]
        self.info["McaIndex"] = len(self.data.shape) - 1

        # per-point metadata (e.g. McaLiveTime) must follow the data to stay
        # aligned, so it is always padded with zeros
        for key, value in self.info.items():
            if key == "positioners":
                continue
            if hasattr(value, "size"):
                arr = numpy.asarray(value)
                if arr.size == nOld:
                    paddedArr = numpy.zeros(numberOfSpectra, dtype=arr.dtype)
                    paddedArr[:nOld] = arr.ravel()
                    self.info[key] = paddedArr
        
        if padPositioners:
            if "positioners" in self.info and hasattr(self.info["positioners"], "items"):
                for motor_name, motor_values in self.info["positioners"].items():
                    if hasattr(motor_values, "size") and motor_values.size == nOld:
                        if motor_values.dtype in (numpy.float16, numpy.float32):
                            pos_dtype = motor_values.dtype
                        else:
                            pos_dtype = numpy.float64
                        paddedPos = numpy.full(numberOfSpectra, numpy.nan, dtype=pos_dtype)
                        paddedPos[:nOld] = numpy.asarray(motor_values).ravel()
                        self.info["positioners"][motor_name] = paddedPos


    # all the following  methods are here for compatibility purposes
    # they are obsolete and bound to disappear.

    def getInfo(self):
        """
        Deprecated method
        """
        if DataObject.GETINFO_DEPRECATION_WARNING:
            print("DEPRECATION WARNING: DataObject.getInfo()")
            DataObject.GETINFO_DEPRECATION_WARNING  = False
        return self.info

    def getData(self):
        """
        Deprecated method
        """
        if DataObject.GETDATA_DEPRECATION_WARNING:
            print("DEPRECATION WARNING: DataObject.getData()")
            DataObject.GETDATA_DEPRECATION_WARNING  = False
        return self.data

    def select(self, selection=None):
        """
        Deprecated method
        """
        if DataObject.SELECT_DEPRECATION_WARNING:
            print("DEPRECATION WARNING: DataObject.select(selection=None)")
            DataObject.SELECT_DEPRECATION_WARNING = False
        dataObject = DataObject()
        dataObject.info = self.info
        dataObject.info['selection'] = selection
        if selection is None:
            dataObject.data = self.data
            return dataObject
        if type(selection) == dict:
            #dataObject.data = self.data #should I set it to none???
            dataObject.data = None
            if 'rows' in selection:
                dataObject.x = None
                dataObject.y = None
                dataObject.m = None
                if 'x' in selection['rows']:
                    for rownumber in selection['rows']['x']:
                        if rownumber is None:
                            continue
                        if dataObject.x is None:
                            dataObject.x = []
                        dataObject.x.append(self.data[rownumber, :])

                if 'y' in selection['rows']:
                    for rownumber in selection['rows']['y']:
                        if rownumber is None:
                            continue
                        if dataObject.y is None:
                            dataObject.y = []
                        dataObject.y.append(self.data[rownumber, :])

                if 'm' in selection['rows']:
                    for rownumber in selection['rows']['m']:
                        if rownumber is None:
                            continue
                        if dataObject.m is None:
                            dataObject.m = []
                        dataObject.m.append(self.data[rownumber, :])
            elif ('cols' in selection) or ('columns' in selection):
                if 'cols' in selection:
                    key = 'cols'
                else:
                    key = 'columns'
                dataObject.x = None
                dataObject.y = None
                dataObject.m = None
                if 'x' in selection[key]:
                    for rownumber in selection[key]['x']:
                        if rownumber is None:
                            continue
                        if dataObject.x is None:
                            dataObject.x = []
                        dataObject.x.append(self.data[:, rownumber])

                if 'y' in selection[key]:
                    for rownumber in selection[key]['y']:
                        if rownumber is None:
                            continue
                        if dataObject.y is None:
                            dataObject.y = []
                        dataObject.y.append(self.data[:, rownumber])

                if 'm' in selection[key]:
                    for rownumber in selection[key]['m']:
                        if rownumber is None:
                            continue
                        if dataObject.m is None:
                            dataObject.m = []
                        dataObject.m.append(self.data[:, rownumber])
            if dataObject.x is None:
                if 'Channel0' in dataObject.info:
                    ch0 = int(dataObject.info['Channel0'])
                else:
                    ch0 = 0
                dataObject.x = [numpy.arange(ch0,
                             ch0 + len(dataObject.y[0])).astype(numpy.float64)]
            if not ("selectiontype" in dataObject.info):
                dataObject.info["selectiontype"] = "%dD" % len(dataObject.y)
            return dataObject
