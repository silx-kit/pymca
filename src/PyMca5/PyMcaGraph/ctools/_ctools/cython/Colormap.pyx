#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2015 European Synchrotron Radiation Facility
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
cimport cython
cimport numpy as np
import numpy as np


from Colormap cimport colormapFillPixmap, initFastLog10
from Colormap cimport fastLog10 as _fastLog10

from MinMax cimport getMinMax

# Init fastLog10 look-up table
initFastLog10()

# Convert numpy dtype array-protocol string to bit field to pass to C function
# 4th bit for type: 1: floating point, 0: integer
# 3rd bit for signedness (int only): 1: unsigned, 0: signed
# 1st and 2nd bits for size: 00: 8 bits, 01: 16 bits, 10: 32 bits, 11: 64 bits.
_NUMPY_TO_TYPE_DESC = {
    'f8': 0b1011,
    'f4': 0b1010,
    'i1': 0b0000,
    'u1': 0b0100,
    'i2': 0b0001,
    'u2': 0b0101,
    'i4': 0b0010,
    'u4': 0b0110,
    'i8': 0b0011,
    'u8': 0b0111,
}

@cython.boundscheck(False)
@cython.wraparound(False)
def dataToRGBAColormap(data,
                       np.ndarray[np.uint8_t, ndim=2, mode="c"] colormap,
                       startValue=None, endValue=None,
                       bint isLog10Mapping=False,
                       nanColor=None):
    """Compute a pixmap by applying a colormap to data.

    :param numpy.ndarray data: Array of data value to convert to pixmap.
    :param numpy.ndarray colormap: palette to use as colormap as an array of
                                   RGBA color.
    :param startValue: The value to map to the first color of the colormap.
    :param endValue: The value to map to the last color of the colormap.
    :param bool isLog10Mapping: The mapping: False for linear, True for log10.
    :param nanColor: RGBA color to use for NaNs.
                     If None, the first color of the colormap.
    :type nanColor: None (the default) or a container that can be converted
                    to a numpy.ndarray containing 4 elements in [0, 255].
    :returns: The corresponding pixmap of RGBA pixels as an array of 4 uint8
              with same dimensions as data and used min and max.
    :rtype: A tuple : (pixmap , (usedMin, usedMax)).
    """
    #Convert float16 to float32
    if data.dtype.str[1:] == 'f2':
        data = np.asarray(data, dtype=np.float32)

    cdef np.ndarray c_data = np.ascontiguousarray(data)
    cdef void * c_dataPtr = c_data.data  # &c_data[0] needs dim
    cdef unsigned long c_dataSize = c_data.size
    cdef unsigned int c_dataItemSize = c_data.itemsize

    cdef unsigned char[:, :] c_colormap = colormap
    cdef unsigned int c_colormapLength = len(colormap)

    cdef unsigned char * c_nanColorPtr
    cdef np.ndarray c_nanColor
    if nanColor is None:
        c_nanColorPtr = NULL
    else:
        c_nanColor = np.asarray(nanColor, dtype=np.uint8, order='C')
        c_nanColorPtr = <unsigned char *> c_nanColor.data

    pixmap = np.empty((data.size, 4), dtype=np.uint8)
    cdef unsigned char[:, :] c_pixmap = pixmap

    cdef unsigned int c_type = _NUMPY_TO_TYPE_DESC[data.dtype.str[1:]]

    cdef double c_start, c_startExtra, c_end
    if startValue is None or endValue is None:
        if isLog10Mapping:
            with nogil:
                getMinMax(c_dataPtr, c_type, c_dataSize,
                          &c_startExtra, &c_start, &c_end)
        else:
            with nogil:
                getMinMax(c_dataPtr, c_type, c_dataSize,
                          &c_start, NULL, &c_end)

        if startValue is not None:
            c_start = startValue
        if endValue is not None:
            c_end = endValue
    else:
        c_start = startValue
        c_end = endValue

    with nogil:
        colormapFillPixmap(c_dataPtr,
                           c_type,
                           c_dataSize,
                           c_start,
                           c_end,
                           isLog10Mapping,
                           &c_colormap[0, 0],
                           c_colormapLength,
                           c_nanColorPtr,
                           &c_pixmap[0, 0])

    pixmap = pixmap.reshape(data.shape + (4,))
    return pixmap, (c_start, c_end)

def fastLog10(double value):
    return _fastLog10(value)
