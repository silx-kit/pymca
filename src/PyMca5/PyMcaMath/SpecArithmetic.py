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
__doc__ = """
This module implements several mathematical functions:
    - peak search
    - center of mass search
    - fwhm search
WARNING : array are numpy.ndarray objects.
"""

import numpy

def search_peak(xdata, ydata):
     """
     Search a peak and its position in arrays xdata ad ydata.
     Return three integer:
       - peak position
       - peak value
       - index of peak position in array xdata
         This result may accelerate the fwhm search.
     """
     ymax   = max(ydata)
     idx    = __give_index(ymax,ydata)
     return xdata[idx],ymax,idx


def search_com(xdata,ydata):
    """
    Return the center of mass in arrays xdata and ydata
    """
    # make sure com is inside the region
    ydata = ydata - numpy.min(ydata)
    num    = numpy.sum(xdata*ydata)
    denom  = numpy.sum(ydata).astype(numpy.float64)
    try:
       result = num/denom
    except ZeroDivisionError:
       result = numpy.mean(xdata)
    return result


def search_fwhm(xdata,ydata,peak=None,index=None):
    """
    Search a fwhm and its center in arrays xdata and ydatas.
    If no fwhm is found, (0,0) is returned.
    peak and index which are coming from search_peak result, may
    accelerate calculation
    """
    if peak is None or index is None:
        x,mypeak,index_peak = search_peak(xdata,ydata)
    else:
        mypeak     = peak
        index_peak = index

    mymin = numpy.min(ydata)
    hm = (mypeak-mymin)/2 + mymin
    idx = index_peak

    lpeak = False
    upeak = False

    if numpy.any(ydata[0:idx] < hm):
        lpeak = True
    if numpy.any(ydata[idx:] < hm):
        upeak = True

    if lpeak and upeak:
        # it is a peak so we keep the data and half-max
        pass
    elif lpeak:
        # it is step-like data with a positive gradient 
        ydata = numpy.gradient(ydata)
        hm = (numpy.max(ydata)-numpy.min(ydata))/2+numpy.min(ydata)
    else:
        # it is step-like data with a negative gradient
        ydata = -1*numpy.gradient(ydata)
        hm = (numpy.max(ydata)-numpy.min(ydata))/2+numpy.min(ydata)

    index_peak = numpy.argmax(ydata)
    idx = index_peak
    try:
        while ydata[idx] >= hm:
           idx = idx-1
        x0 = xdata[idx]
        x1 = xdata[idx+1]
        y0 = ydata[idx]
        y1 = ydata[idx+1]

        lhmx = (hm*(x1-x0) - (y0*x1)+(y1*x0)) / (y1-y0)
    except ZeroDivisionError:
        lhmx = 0
    except IndexError:
        lhmx = xdata[0]

    idx = index_peak
    try:
        while ydata[idx] >= hm:
            idx = idx+1

        x0 = xdata[idx-1]
        x1 = xdata[idx]
        y0 = ydata[idx-1]
        y1 = ydata[idx]

        uhmx = (hm*(x1-x0) - (y0*x1)+(y1*x0)) / (y1-y0)
    except ZeroDivisionError:
        uhmx = 0
    except IndexError:
        uhmx = xdata[-1]

    FWHM  = uhmx - lhmx
    CFWHM = (uhmx+lhmx)/2
    return FWHM,CFWHM


def __give_index(elem,array):
     """
     Return the index of elem in array
     """
     mylist = array.tolist()
     return mylist.index(elem)


def test():
    pass

if __name__ == '__main__':
       test()
