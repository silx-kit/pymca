# /*#########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2020 European Synchrotron Radiation Facility
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
# ###########################################################################*/
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Functions to extract a profile curve of a region of interest in an image.
"""

# import ######################################################################

import numpy
import logging
from PyMca5.PyMcaMath.fitting import SpecfitFuns

_logger = logging.getLogger(__name__)


# utils #######################################################################

def _clamp(value, min_, max_):
    if value < min_:
        return min_
    elif value > max_:
        return max_
    else:
        return value


# coordinate conversion #######################################################

def plotToImage(x, y, origin=(0, 0), scale=(1, 1), shape=None):
    """Convert a position from plot to image coordinates.

    If shape is not None, return the position clipped to the image bounds.

    :param float x: X coordinate in plot.
    :param float y: Y coordinate in plot.
    :param origin: Origin of the image in the plot.
    :type origin: 2-tuple of float: (ox, oy).
    :param scale: Scale of the image in the plot.
    :type scale: 2-tuple of float: (sx, sy).
    :param shape: Shape of the image or None to disable clipping.
    :type shape: 2-tuple of int: (height, width) or None.
    :return: Position in the image.
    :rtype: 2-tuple of int: (row, col).
    """
    col = int((x - origin[0]) / float(scale[0]))
    row = int((y - origin[1]) / float(scale[1]))

    if shape is not None:
        col = _clamp(col, 0, shape[1] - 1)
        row = _clamp(row, 0, shape[0] - 1)
    return row, col


def imageToPlot(row, col, origin=(0., 0.), scale=(1., 1.)):
    """Convert a position from image to plot coordinates.

    :param row: Row coordinate(s) in image.
    :type row: int or numpy.ndarray
    :param col: Column coordinate(s) in image.
    :type col: int or numpy.ndarray
    :param origin: Origin of the image in the plot.
    :type origin: 2-tuple of float: (ox, oy).
    :param scale: Scale of the image in the plot.
    :type scale: 2-tuple of float: (sx, sy).
    :return: Position in the image.
    :rtype: 2-tuple of float or numpy.ndarray: (x, y).
    """
    x = origin[0] + col * scale[0]
    y = origin[1] + row * scale[1]
    return x, y


# profiles ####################################################################

def getAlignedROIProfileCurve(image, roiCenter, roiWidth, roiRange, axis):
    """Sums of a rectangular region of interest (ROI) along a given axis.

    Returned values and all parameters are in image coordinates.
    This function might change the ROI so it remains within the image.
    Thus, the bounds of the effective ROI and the effective roiRange are
    returned along with the profile.

    :param image: 2D data.
                  Warning: The sum is performed with the dtype of the provided
                  array!
    :type image: numpy.ndarray with 2 dimensions.
    :param int roiCenter: Center of the ROI in image coordinates along
                          the given axis.
    :param int roiWidth: Width of the ROI in image pixels along
                         the given axis.
    :param roiRange: [Start, End] positions of the ROI from which to take the
                     ROI in image coordinates along the other dimension.
                     Both start and end are included in the ROI if they are
                     in the image.
                     This range is clipped to the image.
    :type roiRange: 2-tuple of int.
    :param int axis: The axis along which to take the profile of the ROI.
                     0: Sum rows along columns.
                     1: Sum columns along rows.
    :return: The profile and the effective ROI as a dict with the keys:

             - 'profileCoordsRange': The range of profile coordinates
                                     along the selected axis (2-tuple of int).
             - 'profileValues': The sums of the ROI along the selected axis.
             - 'roiPolygonCols': The column coordinates of the polygon of the
                                 effective ROI.
             - 'roiPolygonRows': The row coordinates of the polygon of the
                                 effective ROI.
    :rtype: dict
    """
    assert axis in (0, 1)

    if axis == 1:
        # Transpose image to use same code for both dimensions.
        image = image.transpose()

    dim0Size, dim1Size = image.shape

    roiCenter = int(roiCenter)
    roiWidth = int(roiWidth)

    # Keep range within image
    startRange = _clamp(int(roiRange[0]), 0, dim1Size - 1)
    endRange = _clamp(int(roiRange[1]), 0, dim1Size - 1)
    stepRange = 1 if startRange <= endRange else -1
    rangeSlice = slice(startRange, endRange + stepRange, stepRange)

    # Get ROI extent in the dimension to sum
    start = int(roiCenter + 0.5 - 0.5 * roiWidth)
    end = int(roiCenter + 0.5 + 0.5 * roiWidth)

    # Keep ROI within image and keep its width if possible
    if start < 0:
        start, end = 0, min(roiWidth, dim0Size)
    elif end > dim0Size:
        start, end = max(dim0Size - roiWidth, 0), dim0Size

    if roiWidth <= 1:
        profileValues = image[start, rangeSlice]
        end = start + 1
    else:
        profileValues = image[start:end, rangeSlice].sum(axis=0)

    # Get the ROI polygon
    roiPolygonCols = numpy.array(
        (startRange, endRange + stepRange, endRange + stepRange, startRange),
        dtype=numpy.float64)
    roiPolygonRows = numpy.array((start, start, end, end),
                                 dtype=numpy.float64)

    if axis == 1:  # Image was transposed
        roiPolygonCols, roiPolygonRows = roiPolygonRows, roiPolygonCols

    return {'profileValues': profileValues,
            'profileCoordsRange': (startRange, endRange),
            'roiPolygonRows': roiPolygonRows,
            'roiPolygonCols': roiPolygonCols}


def _getROILineProfileCurve(image, roiStart, roiEnd, roiWidth,
                            lineProjectionMode):
    """Returns the profile values and the polygon in the given ROI.

    Works in image coordinates.

    See :func:`getAlignedROIProfileCurve`.
    """
    row0, col0 = roiStart
    row1, col1 = roiEnd

    deltaRow = abs(row1 - row0)
    deltaCol = abs(col1 - col0)

    if (lineProjectionMode == 'X' or
            (lineProjectionMode == 'D' and deltaCol >= deltaRow)):
        nPoints = deltaCol + 1
        coordsRange = col0, col1
    else:  # 'Y' or ('D' and deltaCol < deltaRow)
        nPoints = deltaRow + 1
        coordsRange = row0, row1

    nPoints = int(nPoints)

    if nPoints == 1:  # all points are the same
        _logger.debug("START AND END POINT ARE THE SAME!!")
        return None

    # the coordinates of the reference points
    x0 = numpy.arange(image.shape[0], dtype=numpy.float64)
    y0 = numpy.arange(image.shape[1], dtype=numpy.float64)

    if roiWidth < 1:
        x = numpy.zeros((nPoints, 2), numpy.float64)
        x[:, 0] = numpy.linspace(row0, row1, nPoints)
        x[:, 1] = numpy.linspace(col0, col1, nPoints)
        # perform the interpolation
        ydata = SpecfitFuns.interpol((x0, y0), image, x)

        roiPolygonCols = numpy.array((col0, col1), dtype=numpy.float64)
        roiPolygonRows = numpy.array((row0, row1), dtype=numpy.float64)

    else:
        # find m and b in the line y = mx + b
        m = (row1 - row0) / float((col1 - col0))
        # Not used: b = row0 - m * col0
        alpha = numpy.arctan(m)
        # imagine the following sequence
        # - change origin to the first point
        # - clock-wise rotation to bring the line on the x axis of a new system
        #   so that the points (col0, row0) and (col1, row1)
        #   become (x0, 0) (x1, 0).
        # - counter clock-wise rotation to get the points (x0, -0.5 width),
        #   (x0, 0.5 width), (x1, 0.5 * width) and (x1, -0.5 * width) back to
        #   the original system.
        # - restore the origin to (0, 0)
        # - if those extremes are inside the image the selection is acceptable
        cosalpha = numpy.cos(alpha)
        sinalpha = numpy.sin(alpha)
        newCol0 = 0.0
        newCol1 = (col1 - col0) * cosalpha + (row1 - row0) * sinalpha
        newRow0 = 0.0
        newRow1 = - (col1 - col0) * sinalpha + (row1 - row0) * cosalpha

        _logger.debug("new X0 Y0 = %f, %f  ", newCol0, newRow0)
        _logger.debug("new X1 Y1 = %f, %f  ", newCol1, newRow1)

        tmpX = numpy.linspace(newCol0, newCol1,
                              nPoints).astype(numpy.float64)
        rotMatrix = numpy.zeros((2, 2), dtype=numpy.float64)
        rotMatrix[0, 0] = cosalpha
        rotMatrix[0, 1] = - sinalpha
        rotMatrix[1, 0] = sinalpha
        rotMatrix[1, 1] = cosalpha
        if _logger.getEffectiveLevel() == logging.DEBUG:
            # test if I recover the original points
            testX = numpy.zeros((2, 1), numpy.float64)
            colRow = numpy.dot(rotMatrix, testX)
            _logger.debug("Recovered X0 = %f", colRow[0, 0] + col0)
            _logger.debug("Recovered Y0 = %f", colRow[1, 0] + row0)
            _logger.debug("It should be = %f, %f", col0, row0)
            testX[0, 0] = newCol1
            testX[1, 0] = newRow1
            colRow = numpy.dot(rotMatrix, testX)
            _logger.debug("Recovered X1 = %f", colRow[0, 0] + col0)
            _logger.debug("Recovered Y1 = %f", colRow[1, 0] + row0)
            _logger.debug("It should be = %f, %f", col1, row1)

        # find the drawing limits
        testX = numpy.zeros((2, 4), numpy.float64)
        testX[0, 0] = newCol0
        testX[0, 1] = newCol0
        testX[0, 2] = newCol1
        testX[0, 3] = newCol1
        testX[1, 0] = newRow0 - 0.5 * roiWidth
        testX[1, 1] = newRow0 + 0.5 * roiWidth
        testX[1, 2] = newRow1 + 0.5 * roiWidth
        testX[1, 3] = newRow1 - 0.5 * roiWidth
        colRow = numpy.dot(rotMatrix, testX)
        colLimits0 = colRow[0, :] + col0
        rowLimits0 = colRow[1, :] + row0

        for a in rowLimits0:
            if (a >= image.shape[0]) or (a < 0):
                _logger.debug("outside row limits %s", a)
                return None
        for a in colLimits0:
            if (a >= image.shape[1]) or (a < 0):
                _logger.debug("outside column limits %s", a)
                return None

        r0 = rowLimits0[0]
        r1 = rowLimits0[1]

        if r0 > r1:
            _logger.debug("r0 > r1 %s %s", r0, r1)
            raise ValueError("r0 > r1")

        x = numpy.zeros((2, nPoints), numpy.float64)

        # oversampling solves noise introduction issues
        oversampling = roiWidth + 1
        oversampling = min(oversampling, 21)
        ncontributors = int(roiWidth * oversampling)
        iterValues = numpy.linspace(-0.5 * roiWidth, 0.5 * roiWidth,
                                    ncontributors)
        tmpMatrix = numpy.zeros((nPoints * len(iterValues), 2),
                                dtype=numpy.float64)
        x[0, :] = tmpX
        offset = 0
        for i in iterValues:
            x[1, :] = i
            colRow = numpy.dot(rotMatrix, x)
            colRow[0, :] += col0
            colRow[1, :] += row0
            # it is much faster to make one call to the interpolating
            # routine than making many calls
            tmpMatrix[offset:(offset + nPoints), 0] = colRow[1, :]
            tmpMatrix[offset:(offset + nPoints), 1] = colRow[0, :]
            offset += nPoints
        ydata = SpecfitFuns.interpol((x0, y0), image, tmpMatrix)
        ydata = ydata.reshape(len(iterValues), nPoints)
        ydata = ydata.sum(axis=0)
        # deal with the oversampling
        ydata /= oversampling

        roiPolygonCols, roiPolygonRows = colLimits0, rowLimits0

    return {'profileValues': ydata,
            'profileCoordsRange': coordsRange,
            'roiPolygonCols': roiPolygonCols,
            'roiPolygonRows': roiPolygonRows}


def getProfileCurve(image, roiStart, roiEnd, roiWidth=1,
                    origin=(0., 0.), scale=(1., 1.),
                    lineProjectionMode='D'):
    """Sums a region of interest (ROI) of an image along a given line.

    Returned values and all parameters except roiWidth are in plot coordinates.
    This function might change the ROI so it remains within the image.
    Thus, the polygon of the effective ROI is returned along with the
    profile.
    The profile is always returned with increasing coordinates on the
    projection axis, so roiStart and roiEnd are flipped if roiStart > roiEnd.

    :param image: 2D data.
    :type image: numpy.ndarray with 2 dimensions.
    :param roiStart: Start point (x0, y0) of the ROI line in plot coordinates.
                     Start point is included in ROI.
    :type roiStart: 2-tuple of float.
    :param roiEnd: End point (x1, y1) of the ROI line in plot coordinates.
                   End point is included in ROI.
    :type roiEnd: 2-tuple of float.
    :param int roiWidth: Width of the ROI line in image pixels and NOT in
                         plot coordinates.
    :param origin: (ox, oy) coordinates of the origin of the image
                   in plot coordinates.
    :type origin: 2-tuple of float.
    :param scale: (sx, sy) scale of the image in plot coordinates.
    :type scale: 2-tuple of float.
    :param str lineProjectionMode: The axis on which to do the profile, in:

                                   - 'D': Use the axis with the longest
                                     projection of the ROI line in pixels.
                                     The profile coordinates are distance
                                     along the profile line.
                                   - 'X': Use the X axis.
                                     The profile coordinates are in X axis
                                     coordinates.
                                   - 'Y': Use the Y axis.
                                     The profile coordinates are in Y axis
                                     coordinates.

                                   This changes the sampling over the
                                   ROI line and the returned coordinates of
                                   the profile curve.

    :return: None if cannot compute a profile curve, or
             the profile and the effective ROI as a dict with the keys:

             - 'profileCoords': The profile coordinates along the selected
                                axis if lineProjectionMode is in ('X', 'Y'),
                                or the distance in plot coordinates along
                                the line if lineProjectionMode is 'D'.
             - 'profileValues': The sums of the ROI along the line.
             - 'roiPolygonCols': The column coordinates of the polygon of the
                                 effective ROI.
             - 'roiPolygonRows': The row coordinates of the polygon of the
                                 effective ROI.
             - 'roiPolygonX': The x coordinates of the polygon of the
                              effective ROI in plot coordinates.
             - 'roiPolygonY': The y coordinates of the polygon of the
                              effective ROI in plot coordinates.
    :rtype: dict
    """
    assert lineProjectionMode in ('D', 'X', 'Y')

    if image is None:
        return None

    row0, col0 = plotToImage(roiStart[0], roiStart[1],
                             origin, scale, image.shape)
    row1, col1 = plotToImage(roiEnd[0], roiEnd[1],
                             origin, scale, image.shape)

    # Makes sure coords are increasing along the projection axis
    if (lineProjectionMode == 'X' or
            (lineProjectionMode == 'D' and
                abs(col1 - col0) >= abs(row1 - row0))):
        if col1 < col0:
            # Invert end points to have increasing coords on X axis
            row0, col0, row1, col1 = row1, col1, row0, col0

    else:  # i.e., 'Y' or ('D' and abs(col1 - col0) < abs(row1 - row0))
        if row1 < row0:
            # Invert end points to have increasing coords on Y axis
            row0, col0, row1, col1 = row1, col1, row0, col0

    if col0 == col1:  # Vertical line
        if lineProjectionMode not in ('D', 'Y'):
            return None  # Nothing to profile over 'X'

        result = getAlignedROIProfileCurve(image,
                                           roiCenter=col0,
                                           roiRange=(row0, row1),
                                           roiWidth=roiWidth,
                                           axis=1)

    elif row0 == row1:  # Horizontal line
        if lineProjectionMode not in ('D', 'X'):
            return None  # Nothing to profile over 'Y'

        result = getAlignedROIProfileCurve(image,
                                           roiCenter=row0,
                                           roiRange=(col0, col1),
                                           roiWidth=roiWidth,
                                           axis=0)

    else:
        result = _getROILineProfileCurve(image,
                                         (row0, col0), (row1, col1),
                                         roiWidth, lineProjectionMode)

    if result is None:
        return None

    values = result['profileValues']

    # Generates profile coordinates
    if lineProjectionMode == 'D':
        # Profile coordinates are distances along the ROI line in plot unit

        # get the abscisa in distance units
        colRange = float(scale[0] * abs(col1 - col0))
        rowRange = float(scale[1] * abs(row1 - row0))
        deltaDistance = numpy.sqrt(
            colRange * colRange + rowRange * rowRange) / (len(values) - 1.0)

        coords = deltaDistance * numpy.arange(len(values), dtype=numpy.float64)

    else:
        # Profile coordinates are returned in plot coords

        # Build coords in image frame
        start, end = result['profileCoordsRange']
        step = 1 if start <= end else -1  # In case profile is inverted
        coords = numpy.arange(start, end + step, step, dtype=numpy.float64)

        # Convert coords from image to plot
        if lineProjectionMode == 'X':
            if origin[0] != 0. or scale[0] != 1.:
                coords = origin[0] + coords * scale[0]

        elif lineProjectionMode == 'Y':
            if origin[1] != 0. or scale[1] != 1.:
                coords = origin[1] + coords * scale[1]

    roiPolygonX, roiPolygonY = imageToPlot(result['roiPolygonRows'],
                                           result['roiPolygonCols'],
                                           origin, scale)

    return {'profileValues': values,
            'profileCoords': coords,
            'startPoint': imageToPlot(row0, col0, origin, scale),
            'endPoint': imageToPlot(row1, col1, origin, scale),
            'roiPolygonCols': result['roiPolygonCols'],
            'roiPolygonRows': result['roiPolygonRows'],
            'roiPolygonX': roiPolygonX,
            'roiPolygonY': roiPolygonY}
