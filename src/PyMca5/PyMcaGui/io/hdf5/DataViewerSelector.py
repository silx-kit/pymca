#/*##########################################################################
# Copyright (C) 2022 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import logging
_logger = logging.getLogger(__name__)

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io.hdf5.Hdf5NodeView import Hdf5NodeViewer
from silx.gui.data import DataViews
from silx.gui.data.DataViewer import DataViewer

class SelectorFromDataViewer(Hdf5NodeViewer):
    
    sigSliceSelectorSignal = qt.pyqtSignal(object)
    
    def __init__(self, parent=None):
        Hdf5NodeViewer.__init__(self, parent)
        self.__data = None
        self._buildActions()
        self.viewWidget.displayedViewChanged.connect(self._viewChanged)
        self.viewWidget.dataChanged.connect(self._dataChanged)

    def _buildActions(self):
        self.buttonBox = qt.QWidget(self)
        buttonBox = self.buttonBox
        self.buttonBoxLayout = qt.QHBoxLayout(buttonBox)

        self.addButton = qt.QPushButton(buttonBox)
        self.addButton.setText("ADD")
        self.removeButton = qt.QPushButton(buttonBox)
        self.removeButton.setText("REMOVE")
        self.replaceButton = qt.QPushButton(buttonBox)
        self.replaceButton.setText("REPLACE")

        self.buttonBoxLayout.addWidget(self.addButton)
        self.buttonBoxLayout.addWidget(self.removeButton)
        self.buttonBoxLayout.addWidget(self.replaceButton)

        self.layout().addWidget(buttonBox)

        self.addButton.clicked.connect(self._addClickedSlot)
        self.removeButton.clicked.connect(self._removeClicked)
        self.replaceButton.clicked.connect(self._replaceClicked)

    def _addClickedSlot(self):
        self._addClicked()

    def _addClicked(self):
        _logger.debug("_addClicked()")
        self._emitSignal(action="ADD")

    def _removeClicked(self):
        _logger.debug("_removeClicked()")
        self._emitSignal(action="REMOVE")

    def _replaceClicked(self):
        _logger.debug("_replaceClicked()")
        self._emitSignal(action="REPLACE")

    def getSelection(self):
        widget = self.viewWidget.displayedView().getWidget()
        if hasattr(widget, "getGraphTitle"):
            selection = widget.getGraphTitle()
        else:
            selection = widget.currentWidget().getGraphTitle()
        selection = selection[selection.index("["):selection.index("]")+1]
        return selection

    def _emitSignal(self, action="ADD"):
        ddict = {}
        ddict["action"] = action
        ddict["slice"] = self.getSelection()
        # shape = self.__data.shape
        # ddict["index"] = sel
        self.sigSliceSelectorSignal.emit(ddict)

    def setData(self, data, mode=None):
        if mode is None:
            interpretation = "spectrum"
            if hasattr(data, "attrs"):
                if "interpretation" in data.attrs:
                    interpretation = data.attrs["interpretation"]
            mode = interpretation
        
        self.viewWidget.setData(data)
        self.__data = data
        if mode.lower() in ["image"]: 
            self.viewWidget.setDisplayMode(DataViews.IMAGE_MODE)
        else:
            self.viewWidget.setDisplayMode(DataViews.PLOT1D_MODE)
        
    def _viewChanged(self, something):
        _logger.debug("_viewChanged called", something)
        if self.__data:
            pass

    def _dataChanged(self):
        _logger.debug("_dataChanged called")

if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = r"D:\DATA\DAPHNIA\Daphnia_float32.h5"
    if not os.path.exists(fname):
        print("Usage:")
        print("python DataViewerSelector.py [hdf5_file]")
        sys.exit()
    app = qt.QApplication([])
    w = SelectorFromDataViewer()
    def mySlot(ddict):
        print(ddict)
    w.sigSliceSelectorSignal.connect(mySlot)
    import h5py
    h5 = h5py.File(fname, "r")
    data = h5["/data/data"]
    w.setData(data)
    w.show()
    app.exec()
