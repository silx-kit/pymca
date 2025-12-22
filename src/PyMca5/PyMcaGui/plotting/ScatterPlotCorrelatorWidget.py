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
import sys
import os
import numpy
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.misc import SelectionTable
from PyMca5.PyMcaGui.plotting import MaskScatterWidget

class ScatterPlotCorrelatorWidget(MaskScatterWidget.MaskScatterWidget):
    def __init__(self, parent=None,
                       labels=("Legend", "X", "Y"),
                       types=("Text","RadioButton", "RadioButton"),
                       toolbar=False,
                       **kw):
        super(ScatterPlotCorrelatorWidget, self).__init__(None, **kw)
        self._splitter = qt.QSplitter(parent)
        self._splitter.setOrientation(qt.Qt.Horizontal)

        self.container = qt.QWidget(self._splitter)
        self.container.mainLayout = qt.QVBoxLayout(self.container)
        self.container.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.container.mainLayout.setSpacing(0)

        # add a toolbar on top of the table
        if toolbar:
            self.toolBar = qt.QToolBar(self.container)

        # the selection table
        self.table = SelectionTable.SelectionTable(self.container,
                                                   labels=labels,
                                                   types=types)
        if toolbar:
            self.container.mainLayout.addWidget(self.toolBar)
        self.container.mainLayout.addWidget(self.table)
        self._splitter.addWidget(self.container)
        self._splitter.addWidget(self)

        # internal variables
        self._itemList = []
        self._itemLabels = []

        # connect
        self.table.sigSelectionTableSignal.connect(self.selectionTableSlot)

    def show(self):
        if self._splitter.isHidden():
            self._splitter.show()
        else:
            super(ScatterPlotCorrelatorWidget, self).show()

    def setSelectableItemList(self, items, labels=None, copy=True):
        self._itemList = []
        self._itemLabels = []
        if labels is None:
            labels = [None] * len(items)
        for i in range(len(items)):
            self.addSelectableItem(items[i], label=labels[i], copy=copy)

    def addSelectableItem(self, item, label=None, copy=True):
        # we always keep a copy by default
        if copy:
            item = numpy.array(item, dtype=numpy.float32, copy=True)
        else:
            item = numpy.asarray(item, dtype=numpy.float32)
        if label is None:
            label = "Unnamed 00"
            i = 0
            while(label in self._itemLabels):
                i += 1
                label = "Unnamed %02d" % i

        if len(self._itemList):
            if item.size != self._itemList[0].size:
                raise IndexError("Invalid size")
        if label in self._itemLabels:
            self._itemList[self._itemLabels.index(label)] = item
        else:
            self._itemList.append(item)
            self._itemLabels.append(label)
            nItems = len(self._itemList)
            self.table.setRowCount(nItems)
            self.table.fillLine(nItems - 1, [label, "", ""])
            self.table.resizeColumnToContents(0)
            self.table.resizeColumnToContents(1)
            self.table.resizeColumnToContents(2)

        ddict = self.table.getSelection()
        index = self._itemLabels.index(label)
        xKey = qt.safe_str(self.table.horizontalHeaderItem(1).text()).lower()
        yKey = qt.safe_str(self.table.horizontalHeaderItem(2).text()).lower()
        if index in (ddict[xKey] + ddict[yKey]):
            self.selectionTableSlot(ddict)

    def selectionTableSlot(self, ddict):
        legendKey = qt.safe_str(self.table.horizontalHeaderItem(0).text()).lower()
        xKey = qt.safe_str(self.table.horizontalHeaderItem(1).text()).lower()
        yKey = qt.safe_str(self.table.horizontalHeaderItem(2).text()).lower()
        if len(ddict[xKey]):
            x0 = self._itemList[ddict[xKey][0]]
        else:
            return
        if len(ddict[yKey]):
            y0 = self._itemList[ddict[yKey][0]]
        else:
            return
        x = x0[:]
        x = numpy.ravel(x)
        y = y0[:]
        y = numpy.ravel(y)
        xLabel = self._itemLabels[ddict[xKey][0]]
        yLabel = self._itemLabels[ddict[yKey][0]]
        # active curve handling is disabled
        self.setGraphXLabel(xLabel)
        self.setGraphYLabel(yLabel)
        self.setSelectionCurveData(x, y, legend=None,
                                   color="k",
                                   symbol=".",
                                   replot=False,
                                   replace=True,
                                   xlabel=xLabel,
                                   ylabel=yLabel,
                                   selectable=False)
        self._updatePlot(replot=False, replace=True)
        #matplotlib needs a zoom reset to update the scales
        # that problem does not seem to be present with OpenGL
        self.resetZoom()

if __name__ == "__main__":
    if "opengl" in sys.argv:
        backend = "opengl"
    else:
        backend = None
    app = qt.QApplication([])
    w = ScatterPlotCorrelatorWidget(labels=["Legend",
                                            "X",
                                            "Y"],
                                    types=["Text",
                                           "RadioButton",
                                           "RadioButton"],
                                    maxNRois=1,
                                    backend=backend)
    w.show()
    # fill some data
    import numpy
    import numpy.random
    import time
    t0 = time.time()
    x = numpy.arange(1000000.)
    w.addSelectableItem(x, "range(%d)" % x.size)
    print("elapsed = ", time.time() - t0)
    w.addSelectableItem(x * x, "range(%d) ** 2"  % x.size)
    x = numpy.random.random(x.size)
    w.addSelectableItem(x, "random(%d)" % x.size)
    x = numpy.random.normal(500000., 1.0, 1000000)
    w.addSelectableItem(x, "Gauss 0")
    x = numpy.random.normal(500000., 1.0, 1000000)
    w.addSelectableItem(x, "Gauss 1")
    w.setPolygonSelectionMode()

    def theSlot(ddict):
        print(ddict['event'])

    w.sigMaskScatterWidgetSignal.connect(theSlot)

    app.exec()
