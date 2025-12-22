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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy
from .fitting import SpecfitFuns

snip1d = SpecfitFuns.snip1d
snip2d = SpecfitFuns.snip2d


def getSpectrumBackground(spectrum, width, roi_min=None, roi_max=None, smoothing=1):
    if roi_min is None:
        roi_min = 0
    if roi_max is None:
        roi_max = len(spectrum)
    background = spectrum * 1
    background[roi_min:roi_max] = snip1d(spectrum[roi_min:roi_max], width, smoothing)
    return background

getSnip1DBackground = getSpectrumBackground

def subtractSnip1DBackgroundFromStack(stack, width, roi_min=None, roi_max=None,  smoothing=1):
    mcaIndex = -1
    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
        mcaIndex = stack.info.get('McaIndex', -1)
    else:
        data = stack
    if not isinstance(data, numpy.ndarray):
        raise TypeError("This Plugin only supports numpy arrays")

    if roi_min is None:
        roi_min = 0
    if roi_max is None:
        roi_max = data.shape[mcaIndex]

    oldShape = data.shape
    if mcaIndex in [-1, len(data.shape)-1]:
        data = data.reshape(-1, oldShape[-1])
        if roi_min > 0:
            data[:, 0:roi_min] = 0
        if roi_max < oldShape[-1]:
            data[:, roi_max:] = 0
        for i in range(data.shape[0]):
            data[i,roi_min:roi_max] -= snip1d(data[i,roi_min:roi_max],
                                              width, smoothing)
        data = data.reshape(oldShape)

    elif mcaIndex == 0:
        data = data.reshape(oldShape[0], -1)
        for i in range(data.shape[-1]):
            data[roi_min:roi_max, i] -= snip1d(data[roi_min:roi_max, i],
                                               width, smoothing)
        data = data.reshape(oldShape)
    else:
        raise ValueError("Invalid 1D index %d" % mcaIndex)
    return

def replaceStackWithSnip1DBackground(stack, width, roi_min=None, roi_max=None,  smoothing=1):
    mcaIndex = -1
    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
        mcaIndex = stack.info.get('McaIndex', -1)
    else:
        data = stack
    if not isinstance(data, numpy.ndarray):
        raise TypeError("This Plugin only supports numpy arrays")

    if roi_min is None:
        roi_min = 0
    if roi_max is None:
        roi_max = data.shape[mcaIndex]

    oldShape = data.shape
    if mcaIndex in [-1, len(data.shape)-1]:
        data = data.reshape(-1, oldShape[-1])
        if roi_min > 0:
            data[:, 0:roi_min] = 0
        if roi_max < oldShape[-1]:
            data[:, roi_max:] = 0
        for i in range(data.shape[0]):
            data[i,roi_min:roi_max] = snip1d(data[i,roi_min:roi_max],
                                              width, smoothing)
        data.shape = oldShape

    elif mcaIndex == 0:
        data = data.reshape(oldShape[0], -1)
        for i in range(data.shape[-1]):
            data[roi_min:roi_max, i] = snip1d(data[roi_min:roi_max, i],
                                               width, smoothing)
        data = data.reshape(oldShape)
    else:
        raise ValueError("Invalid 1D index %d" % mcaIndex)
    return


def getImageBackground(image, width, roi_min=None, roi_max=None, smoothing=1):
    if roi_min is None:
        roi_min = (0, 0)
    if roi_max is None:
        roi_max = image.shape
    background = image * 1
    background[roi_min[0]:roi_max[0],roi_min[1]:roi_max[1]]=\
             snip2d(image[roi_min[0]:roi_max[0],roi_min[1]:roi_max[1]],
                    width,
                    smoothing)
    return background

getSnip2DBackground = getImageBackground

def subtractSnip2DBackgroundFromStack(stack, width, roi_min=None, roi_max=None,  smoothing=1, index=None):
    """
    index is the dimension used to index the images
    """
    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
        if index is None:
            index = stack.info.get('McaIndex', 0)
    else:
        data = stack
    if index is None:
        index = 2
    if not isinstance(data, numpy.ndarray):
        raise TypeError("This Plugin only supports numpy arrays")

    if roi_min is None:
        roi_min = (0, 0)
    if roi_max is None:
        roi_max = tuple(data.shape[i] for i in range(3) if i != index)

    shape = data.shape
    if index == 0:
        if (roi_min[0] > 0) or (roi_min[1] > 0):
            data[:, 0:roi_min[0], 0:roi_min[1]] = 0
        if roi_max[0] < (shape[1]-1):
            if roi_max[1] < (shape[2]-1):
                data[:, roi_max[0]:, roi_max[1]:] = 0
            else:
                data[:, roi_max[0]:, :] = 0
        else:
            if roi_max[1] < (shape[2]-1):
                data[:, :, roi_max[1]:] = 0
        for i in range(shape[index]):
            data[i,roi_min[0]:roi_max[0],roi_min[1]:roi_max[1]] -=\
                snip2d(data[i,roi_min[0]:roi_max[0],roi_min[1]:roi_max[1]], width, smoothing)
        return
    if index == 1:
        if (roi_min[0] > 0) or (roi_min[1] > 0):
            data[0:roi_min[0], :, 0:roi_min[1]] = 0
        if roi_max[0] < (shape[0]-1):
            if roi_max[1] < (shape[2]-1):
                data[roi_max[0]:, :, roi_max[1]:] = 0
            else:
                data[roi_max[0]:, :, :] = 0
        else:
            if roi_max[1] < (shape[2]-1):
                data[:, :, roi_max[1]:] = 0
        for i in range(shape[index]):
            data[roi_min[0]:roi_max[0], i, roi_min[1]:roi_max[1]] -=\
                snip2d(data[roi_min[0]:roi_max[0], i, roi_min[1]:roi_max[1]], width, smoothing)
        return
    if index == 2:
        if (roi_min[0] > 0) or (roi_min[1] > 0):
            data[0:roi_min[0], 0:roi_min[1],:] = 0
        if roi_max[0] < (shape[0]-1):
            if roi_max[1] < (shape[1]-1):
                data[roi_max[0]:, roi_max[1]:, :] = 0
            else:
                data[roi_max[0]:, :, :] = 0
        else:
            if roi_max[1] < (shape[2]-1):
                data[:, roi_max[1]:, :] = 0
        for i in range(shape[index]):
            data[roi_min[0]:roi_max[0],roi_min[1]:roi_max[1], i] -=\
                snip2d(data[roi_min[0]:roi_max[0],roi_min[1]:roi_max[1], i], width, smoothing)
        return
