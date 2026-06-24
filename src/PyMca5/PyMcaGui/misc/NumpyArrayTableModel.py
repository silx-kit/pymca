#/*##########################################################################
# Copyright (C) 2004-2024 European Synchrotron Radiation Facility
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
import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt
def MyQVariant(x=None):
    return x

class NumpyArrayTableModel(qt.QAbstractTableModel):
    def __init__(self, parent=None, narray=None, fmt="%g", perspective=0):
        qt.QAbstractTableModel.__init__(self, parent)
        if narray is None:
            narray = numpy.array([])
        self._array  = narray
        self._bgcolors = None
        self._fgcolors = None
        self._hLabels = None
        self._vLabels = None

        self._format = fmt
        self._index  = []
        self.assignDataFunction(perspective)

    def rowCount(self, parent=None):
        return self._rowCount(parent)

    def columnCount(self, parent=None):
        return self._columnCount(parent)

    def data(self, index, role=qt.Qt.DisplayRole):
        if not index.isValid():
            return MyQVariant()
        row = index.row()
        col = index.column()
        selection = tuple(self._index + [row, col])
        if role == qt.Qt.BackgroundRole and self._bgcolors is not None:
            r, g, b = self._bgcolors[selection][0:3]
            if self._bgcolors.shape[-1] == 3:
                return qt.QColor(r, g, b)
            if self._bgcolors.shape[-1] == 4:
                a = self._bgcolors[selection][3]
                return qt.QColor(r, g, b, a)
        elif role == qt.Qt.ForegroundRole:
            if self._fgcolors is not None:
                r, g, b = self._fgcolors[selection][0:3]
                if self._fgcolors.shape[-1] == 3:
                    return qt.QColor(r, g, b)
                if self._fgcolors.shape[-1] == 4:
                    a = self._fgcolors[selection][3]
                    return qt.QColor(r, g, b, a)

            # no fg color given, use black or white
            # based on luminosity threshold
            elif self._bgcolors is not None:
                r, g, b = self._bgcolors[selection][0:3]
                lum = 0.21 * r + 0.72 * g + 0.07 * b
                if lum < 128:
                    return qt.QColor(qt.Qt.white)
                else:
                    return qt.QColor(qt.Qt.black)
        else:
            return self._data(index, role)

    def _rowCount1D(self, parent=None):
        return 1

    def _columnCount1D(self, parent=None):
        return self._array.shape[0]

    def _data1D(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                # row = 0
                col = index.column()
                return MyQVariant(self._format % self._array[col])

        return MyQVariant()

    def _rowCount2D(self, parent=None):
        return self._array.shape[0]

    def _columnCount2D(self, parent=None):
        return self._array.shape[1]

    def _data2D(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                row = index.row()
                col = index.column()
                return MyQVariant(self._format % self._array[row, col])
        return MyQVariant()

    def _rowCountND(self, parent=None):
        return self._array.shape[-2]

    def _columnCountND(self, parent=None):
        return self._array.shape[-1]

    def _dataND(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                row = index.row()
                col = index.column()
                actualSelection = tuple(self._index + [row, col])
                return MyQVariant(self._format % self._array[actualSelection])
        return MyQVariant()

    def _rowCount3DIndex0(self, parent=None):
        return self._array.shape[1]

    def _columnCount3DIndex0(self, parent=None):
        return self._array.shape[2]

    def _rowCount3DIndex1(self, parent=None):
        return self._array.shape[0]

    def _columnCount3DIndex1(self, parent=None):
        return self._array.shape[2]

    def _rowCount3DIndex2(self, parent=None):
        return self._array.shape[0]

    def _columnCount3DIndex2(self, parent=None):
        return self._array.shape[1]

    def _data3DIndex0(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                row = index.row()
                col = index.column()
                return MyQVariant(self._format % self._array[self._index,
                                                                  row,
                                                                  col])
        return MyQVariant()

    def _data3DIndex1(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                row = index.row()
                col = index.column()
                return MyQVariant(self._format % self._array[row,
                                                                  self._index,
                                                                  col])
        return MyQVariant()

    def _data3DIndex2(self, index, role=qt.Qt.DisplayRole):
        if index.isValid():
            if role == qt.Qt.DisplayRole:
                row = index.row()
                col = index.column()
                return MyQVariant(self._format % self._array[row,
                                                                  col,
                                                                  self._index])
        return MyQVariant()

    def setArrayData(self, data, perspective=0):
        """
        setStackData(self, data, perspective=0)
        data is a 3D array
        perspective is the array dimension acting as index of images
        """
        if qt.qVersion() > "4.6":
            self.beginResetModel()
        else:
            self.reset()
        self._array = data
        self._bgcolors = None
        self._fgcolors = None
        self._hLabels = None
        self._vLabels = None
        self.assignDataFunction(perspective)
        if len(data.shape) > 3:
            self._index = []
            for i in range(len(data.shape) - 2):
                self._index.append(0)
        elif len(data.shape) == 3:
            self._index = [0]
        else:
            self._index = []
        if qt.qVersion() > "4.6":
            self.endResetModel()

    def setArrayColors(self, bgcolors=None, fgcolors=None):
        """Set the colors for all table cells by passing an array
        of RGB or RGBA values (integers between 0 and 255).

        The shape of the colors array must be consistent with the data shape.

        If the data array is n-dimensional, the colors array must be
        (n+1)-dimensional, with the first n-dimensions identical to the data
        array dimensions, and the last dimension length-3 (RGB) or
        length-4 (RGBA).

        :param bgcolors: RGB or RGBA colors array, defining the background color
            for each cell in the table.
        :param fgcolors: RGB or RGBA colors array, defining the foreground color
            (text color) for each cell in the table.
        """
        # array must be RGB or RGBA
        valid_shapes = (self._array.shape + (3,), self._array.shape + (4,))
        errmsg = "Inconsistent shape for color array, should be %s or %s" % valid_shapes

        if bgcolors is not None:
            bgcolors = numpy.asarray(bgcolors)
            assert bgcolors.shape in valid_shapes, errmsg

        self._bgcolors = bgcolors

        if fgcolors is not None:
            fgcolors = numpy.asarray(fgcolors)
            assert fgcolors.shape in valid_shapes, errmsg

        self._fgcolors = fgcolors

    def assignDataFunction(self, dimension):
        shape = self._array.shape
        if len(shape) == 2:
            self._rowCount = self._rowCount2D
            self._columnCount = self._columnCount2D
            self._data = self._data2D
        elif len(shape) == 1:
            self._rowCount = self._rowCount1D
            self._columnCount = self._columnCount1D
            self._data = self._data1D
        elif len(shape) > 3:
            # only C order array of images supported
            self._rowCount = self._rowCountND
            self._columnCount = self._columnCountND
            self._data = self._dataND
        else:
            if dimension == 1:
                self._rowCount = self._rowCount3DIndex1
                self._columnCount = self._columnCount3DIndex1
                self._data = self._data3DIndex1
            elif dimension == 2:
                self._rowCount = self._rowCount3DIndex2
                self._columnCount = self._columnCount3DIndex2
                self._data = self._data3DIndex1
            else:
                self._rowCount = self._rowCount3DIndex0
                self._columnCount = self._columnCount3DIndex0
                self._data = self._data3DIndex0
            self._dimension = dimension

    def setCurrentArrayIndex(self, index):
        shape = self._array.shape
        if len(shape) < 3:
            # index is ignored
            self._index = []
            return
        if len(shape) == 3:
            shape = self._array.shape[self._dimension]
            if hasattr(index, "__len__"):
                index = index[0]
            if (index < 0) or (index >= shape):
                raise ValueError("Index must be an integer lower than %d" % shape)
            self._index = [index]
        else:
            # Only N-dimensional arrays of images supported
            print("NOT SUPPORTED YET")
            return
            __THOUGHTS__ = """
                for i in range(len(index)):
                    idx = index[i]
                    if (idx < 0) or (idx >= shape[i]):
                        raise ValueError("Index %d must be positive integer lower than %d" % \
                                        (idx, shape[i]))
                self._index = index
                """

    def setFormat(self, fmt):
        self._format = fmt

    def headerData(self, section, orientation, role=qt.Qt.DisplayRole):
        if self._hLabels and orientation == qt.Qt.Horizontal and role == qt.Qt.DisplayRole:
            if section < len(self._hLabels):
                return "%s" % self._hLabels[section]
        if self._vLabels and orientation == qt.Qt.Vertical and role == qt.Qt.DisplayRole:
            if section < len(self._vLabels):
                return "%s" % self._vLabels[section]
        return super().headerData(section, orientation, role)

    def setHorizontalHeaderLabels(self, labels):
        self._hLabels = labels

    def setVerticalHeaderLabels(self, labels):
        self._vLabels = labels

if __name__ == "__main__":
    a = qt.QApplication([])
    try:
        from .TableWidget import TableView
    except Exception:
        print("Cannot use PyMca Table")
        TableView = qt.QTableView
    w = TableView()
    d = numpy.random.normal(0,1, (5, 1000,1000))
    for i in range(5):
        d[i, :, :] += i
    #m = NumpyArrayTableModel(fmt="%.5f")
    #m = NumpyArrayTableModel(None, numpy.arange(100.), fmt="%.5f")
    #m = NumpyArrayTableModel(None, numpy.ones((100,20)), fmt="%.5f")
    m = NumpyArrayTableModel(None, d, fmt = "%.5f")
    m.setVerticalHeaderLabels(["Row %d" % i for i in range(d.shape[1])])
    m.setHorizontalHeaderLabels(["Column %d" % i for i in range(d.shape[2])])
    w.setModel(m)
    m.setCurrentArrayIndex(4)
    #m.setArrayData(numpy.ones((100,)))
    from PyMca5.PyMcaGraph import Colormap
    bg = Colormap.applyColormap(d, colormap="temperature",norm="linear")
    m.setArrayColors(bg[0])
    w.show()
    a.exec()
