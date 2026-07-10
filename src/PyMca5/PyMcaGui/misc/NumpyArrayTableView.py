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
from PyMca5.PyMcaGui import PyMcaQt as qt
def MyQVariant(x=None):
    return x
from . import NumpyArrayTableModel
import sys

class HorizontalHeader(qt.QAbstractItemModel):
    def __init__(self, parent=None):
        qt.QAbstractItemModel.__init__(self, parent)

    def columnCount(self, modelIndex):
        return self.parent().columnCount()

    def headerData(self, section, orientation, role=qt.Qt.DisplayRole):
        if role == qt.Qt.DisplayRole:
            return MyQVariant("%d" % section)
        return MyQVariant()

class VerticalHeader(qt.QAbstractItemModel):
    def __init__(self, parent=None):
        qt.QAbstractItemModel.__init__(self, parent)

    def rowCount(self, modelIndex):
        return self.parent().rowCount()

    def headerData(self, section, orientation, role=qt.Qt.DisplayRole):
        if role == qt.Qt.DisplayRole:
            return MyQVariant("%d" % section)
        return MyQVariant()

class NumpyArrayTableView(qt.QTableView):
    def __init__(self, parent=None):
        qt.QTableView.__init__(self, parent)
        self._model = NumpyArrayTableModel.NumpyArrayTableModel(self)
        self.setModel(self._model)
        self._horizontalHeaderModel = HorizontalHeader(self._model)
        self._verticalHeaderModel = VerticalHeader(self._model)
        self.horizontalHeader().setModel(self._horizontalHeaderModel)
        self.verticalHeader().setModel(self._verticalHeaderModel)

    def setArrayData(self, data):
        t = "%s" % data.dtype
        if '|' in t:
            fmt = "%s"
        else:
            fmt = "%g"
        self._model.setFormat(fmt)
        self._model.setArrayData(data)
        #some linux distributions need this call
        self.setModel(self._model)
        if sys.platform not in ['win32']:
            self._horizontalHeaderModel = HorizontalHeader(self._model)
            self._verticalHeaderModel = VerticalHeader(self._model)
        self.horizontalHeader().setModel(self._horizontalHeaderModel)
        self.verticalHeader().setModel(self._verticalHeaderModel)

    def setCurrentArrayIndex(self, index):
        return self._model.setCurrentArrayIndex(index)

if __name__ == "__main__":
    import numpy
    a = qt.QApplication([])
    d = numpy.random.normal(0,1, (5, 1000,1000))
    for i in range(5):
        d[i, :, :] += i
    w = NumpyArrayTableView()
    w.setArrayData(d)
    w.show()
    a.exec()
