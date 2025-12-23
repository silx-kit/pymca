#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
__doc__ = """
    Common tools to deal with common graphics operations on images.
    """
import sys
import os
import numpy

from PyMca5 import spslut
COLORMAP_LIST = [spslut.GREYSCALE, spslut.REVERSEGREY, spslut.TEMP,
                 spslut.RED, spslut.GREEN, spslut.BLUE, spslut.MANY]

DEFAULT_COLORMAP_INDEX = 2
DEFAULT_COLORMAP_LOG_FLAG = False

def convertToRowAndColumn(x, y, shape, xScale=None, yScale=None, safe=True):
    """
    Convert from plot coordinates to image row and column.
    """
    if xScale is None:
        c = x
    else:
        if x < xScale[0]:
            x = xScale[0]
        c = (x - xScale[0]) / xScale[1]
    if yScale is None:
        r = y
    else:
        if y < yScale[0]:
            y = yScale[0]
        r = ( y - yScale[0]) / yScale[1]

    if safe:
        c = min(int(c), shape[1] - 1)
        r = min(int(r), shape[0] - 1)
    else:
        c = int(c)
        r = int(r)
    return r, c

def getPixmapFromData(ndarray, colormap=None, mask=None, colors=None):
    """
    Calculate a colormap and apply a mask (given as a set of unsigned ints) to
    it.

    :param ndarray:  Data values
    :type ndarray: Numpy array
    :param colormap: None or a list of seven parameters:

                0. Colormap index. Positive integer
                1. Autoscale flag
                2. Minimum value to be mapped
                3. Maximum value to be mapped
                4. Minimum data value
                5. Maximum data value
                6. Flag to indicate mode (0 - linear, 1 - logarithmic)

    :type colormap: list or None (default)
    :param mask: Numpy array of indices to indicating mask levels
    :type mask: Numpy nd array of indices or None (default)
    :param colors: List containing the colors associated to the mask levels
    :type colors: Numpy array of dimensions (N mask levels, 4) or None (default)
    :returns: Numpy uint8 array of shape equal data.shape + [4]
    """
    oldShape = list(ndarray.shape)

    # deal with numpy masked arrays
    if hasattr(ndarray, 'mask'):
        data = ndarray.data[:]
    else:
        data = ndarray[:]

    if len(oldShape) == 1:
        data = data.reshape(-1, 1)
    elif len(oldShape) != 2:
        raise TypeError("Input array must be of dimension 2 got %d" % \
                                len(oldShape))

    # deal with non finite data
    finiteData = numpy.isfinite(data)
    goodData = finiteData.min()

    if goodData:
        minData = data.min()
        maxData = data.max()
    else:
        tmpData = data[finiteData]
        if tmpData.size > 0:
            minData = tmpData.min()
            maxData = tmpData.max()
        else:
            minData = None
            maxData = None
        tmpData = None

    # apply colormap
    if colormap is None:
        colormapName = COLORMAP_LIST[min(DEFAULT_COLORMAP_INDEX,
                                    len(COLORMAP_LIST) - 1)]
        if DEFAULT_COLORMAP_LOG_FLAG:
            colormapScaling = spslut.log
        else:
            colormapScaling = spslut.LINEAR
        if minData is None:
            (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormapScaling, 3.0),
                            "RGBX",
                            colormapName,
                            1,
                            (0, 1),
                            (0, 255), 1)
        else:
            (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormapScaling,3.0),
                            "RGBX",
                            colormapName,
                            0,
                            (minData,maxData),
                            (0, 255), 1)
    else:
        if len(colormap) < 7:
            print("Missing colormap log flag assuming linear")
            colormap.append(spslut.LINEAR)
        if goodData:
            (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormap[6],3.0),
                            "RGBX",
                            COLORMAP_LIST[int(str(colormap[0]))],
                            colormap[1],
                            (colormap[2],colormap[3]),
                            (0, 255), 1)
        elif colormap[1]:
            #autoscale
            if minData is None:
                colormapName = COLORMAP_LIST[min(DEFAULT_COLORMAP_INDEX,
                                            len(COLORMAP_LIST) - 1)]
                colormapScaling = DEFAULT_COLORMAP_LOG_FLAG
                (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormapScaling, 3.0),
                            "RGBX",
                            colormapName,
                            1,
                            (0, 1),
                            (0, 255), 1)
            else:
                (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormap[6],3.0),
                            "RGBX",
                            COLORMAP_LIST[int(str(colormap[0]))],
                            0,
                            (minData, maxData),
                            (0,255), 1)
        else:
            (pixmap, size, minmax)= spslut.transform(\
                            data,
                            (1,0),
                            (colormap[6],3.0),
                            "RGBX",
                            COLORMAP_LIST[int(str(colormap[0]))],
                            colormap[1],
                            (colormap[2],colormap[3]),
                            (0,255), 1)

    # make sure alpha is set
    pixmap = pixmap.reshape(-1, 4)
    pixmap[:, 3] = 255
    pixmap = pixmap.reshape(list(data.shape) + [4])
    if not goodData:
        pixmap[finiteData < 1] = 255
    if mask is not None:
        return applyMaskToImage(pixmap, mask, colors=colors, copy=False)
    return pixmap


def applyMaskToImage(pixmap, mask=None, colors=None, copy=True):
    """
    Calculate the resulting pixmap after applying a mask. Each value of the
    mask indicates the color index to be used.

    :param pixmap: Numpy array of RGBA values.
    :type pixmap: Numpy ndarray.
    :param mask: Numpy array of positive indices. Usually of type uint8.
    :type mask: Numpy ndarray.
    :param colors: Array of dimension (n_colors, 4) containing the RGBA colors.
    :type colors: Numpy ndarray of uint8 values.
    :param copy: Flag to indicate if a copy of th einput pixmap is to be made.
    :type copy: Boolean, default True.
    :returns: The resulting pixmap.
    """
    if copy:
        pixmap = pixmap.copy()
    if mask is None:
        return pixmap

    maxValue = mask.max()
    startIndex = mask.min()
    if colors is None:
        if maxValue == 1:
            startIndex = 1
            colors = numpy.zeros((2, 4), dtype=numpy.uint8)
            colors[1, 3] = 255
        else:
            raise ValueError("Different mask levels require color list input")
    oldShape = pixmap.shape
    pixmap = pixmap.reshape(-1, 4)
    maskView = mask[:]
    maskView = numpy.ravel(maskView)
    blendFactor = 0.8
    for i in range(startIndex, maxValue + 1):
        idx = (maskView==i)
        pixmap[idx, :] = pixmap[idx, :] * blendFactor + \
                         colors[i] * (1.0 - blendFactor)
    pixmap = pixmap.reshape(*oldShape)
    return pixmap

if __name__ == "__main__":
    from PyMca5.PyMcaGui import PyMcaQt as qt
    from PyMca5.PyMcaGui.plotting import PlotWidget
    app = qt.QApplication([])
    w = PlotWidget.PlotWidget()
    data = numpy.arange(10000.).reshape(100, 100)
    mask = numpy.zeros(data.shape, dtype=numpy.uint8)
    mask[25:75, 25:75] = 1
    image = getPixmapFromData(data, mask=mask)
    w.addImage(image, mask=mask)
    w.show()
    app.exec()
