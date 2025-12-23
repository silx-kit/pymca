# /*##########################################################################
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
# ###########################################################################*/
__author__ = "T. Vincent - ESRF"
__contact__ = "thomas.vincent@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """Convert data to a RGBA colormap."""


# import ######################################################################

import numpy as np
from . import ctools
from . import MatplotlibColormaps

# default colormaps ###########################################################

_CMAP_RED = np.zeros((256, 4), dtype=np.uint8)
_CMAP_RED[:, 0] = np.arange(256, dtype=np.uint8)
_CMAP_RED[:, 3] = 255

_CMAP_GREEN = np.zeros((256, 4), dtype=np.uint8)
_CMAP_GREEN[:, 1] = np.arange(256, dtype=np.uint8)
_CMAP_GREEN[:, 3] = 255

_CMAP_BLUE = np.zeros((256, 4), dtype=np.uint8)
_CMAP_BLUE[:, 2] = np.arange(256, dtype=np.uint8)
_CMAP_BLUE[:, 3] = 255

_CMAP_BLUE = np.zeros((256, 4), dtype=np.uint8)
_CMAP_BLUE[:, 2] = np.arange(256, dtype=np.uint8)
_CMAP_BLUE[:, 3] = 255

_CMAP_GRAY = np.indices((256, 4), dtype=np.uint8)[0]
_CMAP_GRAY[:, 3] = 255

_CMAP_REVERSED_GRAY = 255 - np.indices((256, 4), dtype=np.uint8)[0]
_CMAP_REVERSED_GRAY[:, 3] = 255

_INDICES = np.arange(256, dtype=np.uint8)
_CMAP_TEMPERATURE = np.asarray(np.dstack((
    np.interp(_INDICES, (128, 192), (0, 255)),
    np.interp(_INDICES, (0, 64, 192, 255), (0, 255, 255, 0)),
    np.interp(_INDICES, (64, 128), (255, 0)),
    np.array((255,) * 256)))[0], dtype=np.uint8, order='C')
"""
red: For index 128->192, red is 0->255
green: For index 0->64, green is 0->255 and for 192->255, green is 255->0
blue: For index 64->128, blue is 255->0
"""

COLORMAPS = {
    # Sequential
    'red': _CMAP_RED,
    'green': _CMAP_GREEN,
    'blue': _CMAP_BLUE,
    'gray': _CMAP_GRAY,
    'reversed gray': _CMAP_REVERSED_GRAY,
    # Rainbow
    'temperature': _CMAP_TEMPERATURE,
}
"""Dictionary of default colormaps."""

# Add matplotlib colormaps
for key in MatplotlibColormaps.cmaps:
    COLORMAPS[key] = MatplotlibColormaps.cmaps[key]

# colormap ####################################################################

def applyColormap(data, colormap='gray', norm='linear', bounds=None):
    """Convert data to a RGBA pixmap using a colormap.

    The returned pixmap has the same shape as data plus one dimension of 4.

    :param numpy.ndarray data: The data to convert to a pixmap.
                               Any dimension is supported.
    :param colormap: Either the name or the RGBA colors of the colormap to use.
    :type colormap: Either str or numpy.ndarray with shape=(N, 4)
                    and dtype=numpy.uint8.
    :param str norm: The normalization to use. Either 'linear' (the default)
                     or 'log' for log10 normalization.
    :param bounds: The start and end value used to apply the colormap
                   or None (the default) to use auto-scale.
                   As is, start value must be <= end value.
    :type bounds: tuple of two floats (startValue, endValue) or None.
    :returns: The RGBA pixmap and the used start and end value.
    :rtype: (numpy.ndarray with dtype=numpy.uint8, (float, float))
    """
    if not isinstance(colormap, np.ndarray):
        try:
            colormap = COLORMAPS[colormap]
        except KeyError:
            raise RuntimeError("Invalid colormap: %s" % colormap)

    isLog10 = norm.startswith('log')
    if bounds is None:
        start, end = None, None
    else:
        start, end = bounds
    return ctools.dataToRGBAColormap(data, colormap, start, end, isLog10, None)


# demo ########################################################################

if __name__ == "__main__":
    data = np.arange(1024 * 1024.)
    data = data.reshape(1024, -1)

    for colormap in COLORMAPS:
        pixmap, _ = applyColormap(data, colormap)

        filename = 'demoColormap_%s.ppm' % colormap
        print('Write generated RGB image to: %s' % filename)
        with open(filename, 'wb') as f:
            f.write(('P6\n%d %d\n255\n' % (pixmap.shape[1], pixmap.shape[0])).encode('utf-8'))
            f.write(pixmap[:, :, 0:3].tobytes())
