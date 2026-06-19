#/*##########################################################################
# Copyright (C) 2004-2026 European Synchrotron Radiation Facility
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
"""
It is a wraper of a silx :class:`ScatterView` 
"""

import logging
import numpy

from PyMca5.PyMcaGui import PyMcaQt as qt

from silx.gui.plot.ScatterView import ScatterView
from silx.gui.plot import items as silx_items
from silx.gui.colors import Colormap

_logger = logging.getLogger(__name__)


class AxesPositionersSelector(qt.QWidget):
    sigSelectionChanged = qt.pyqtSignal(object, object)

    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        hlayout = qt.QHBoxLayout()
        self.setLayout(hlayout)
        self._initializing = True
        xlabel = qt.QLabel("X:", parent=parent)
        self.xPositioner = qt.QComboBox(parent)
        self.xPositioner.currentIndexChanged.connect(self._emitSelectionChanged)

        ylabel = qt.QLabel("Y:", parent=parent)
        self.yPositioner = qt.QComboBox(parent)
        self.yPositioner.currentIndexChanged.connect(self._emitSelectionChanged)
        self._initializing = False

        hlayout.addWidget(xlabel)
        hlayout.addWidget(self.xPositioner)
        hlayout.addWidget(ylabel)
        hlayout.addWidget(self.yPositioner)

        self._nPoints = None
        """If set to an integer, only motors with this number of data points
        can be added."""

        self._initComboBoxes()

    def _initComboBoxes(self):
        self.xPositioner.clear()
        self.xPositioner.insertItem(0, "None")
        self.yPositioner.clear()
        self.yPositioner.insertItem(0, "None")

    def _emitSelectionChanged(self, idx):
        if not self._initializing:
            self.sigSelectionChanged.emit(*self.getSelectedPositioners())

    def setNumPoints(self, n):
        self._nPoints = n

    def unsetNumPoints(self):
        self._nPoints = None

    def fillPositioners(self, positioners):
        """

        :param dict positioners: Dictionary of positioners
            The key is the motor name, the value are the motor's position data
        """
        currentX, currentY = self.getSelectedPositioners()

        self._initializing = True
        self._initComboBoxes()
        i = 0
        for motorName, motorValues in positioners.items():
            if not numpy.isscalar(motorValues) and self._nPoints is not None and self._nPoints != motorValues.size:
                # checks consistency of number of data points (but accepts scalars)
                continue
            else:
                i += 1
                self.xPositioner.insertItem(i, motorName)
                self.yPositioner.insertItem(i, motorName)

        if currentX in positioners and currentY in positioners:
            self.xPositioner.setCurrentIndex(self.xPositioner.findText(currentX))
            self.yPositioner.setCurrentIndex(self.yPositioner.findText(currentY))
        self._initializing = False
    def getSelectedPositioners(self):
        """

        :return: 2-tuple of selected positioner names (or None)
        """
        selected = [None, None]
        if self.xPositioner.currentText() != "None":
            selected[0] = self.xPositioner.currentText()
        if self.yPositioner.currentText() != "None":
            selected[1] = self.yPositioner.currentText()
        return selected


class MaskScatterViewWidget(qt.QWidget):
    """
    Plain QWidget (not a QMainWindow)
    to work in a layout and in a plugin
    """
    def __init__(self, parent=None, backend="mpl"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("Mask Scatter View")
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._scatterView = ScatterView(parent=self, backend=backend)
        self._scatterView.setColormap(Colormap("temperature"))
        self._scatterView.getScatterItem().setSymbol("s")

        self._axesSelector = AxesPositionersSelector(parent=self)
        self._axesSelector.sigSelectionChanged.connect(self._setAxesData)

        layout.addWidget(self._scatterView, 1)
        layout.addWidget(self._axesSelector, 0)

        self._positioners = {}
        self._xdata = None
        self._ydata = None
        self._stackImage = None

    def getMaskToolsWidget(self):
        return self._scatterView.getMaskToolsWidget()
    
    def resetZoom(self):
        return self._scatterView.resetZoom()
    
    def fillPositioners(self, positioners):
        self._positioners = positioners
        self._axesSelector.fillPositioners(positioners)

    def setNumPoints(self, n):
        self._axesSelector.setNumPoints(n)

    def _setAxesData(self, xPositioner, yPositioner):
        """

        :param str xPositioner: motor name, or None
        :param str yPositioner: motor name, or None
        :return:
        """
        if xPositioner not in [None, ""]:
            assert xPositioner in self._positioners
            self._xdata = self._positioners[xPositioner]
        else:
            self._xdata = None
        if yPositioner not in [None, ""]:
            assert yPositioner in self._positioners
            self._ydata = self._positioners[yPositioner]
        else:
            self._ydata = None
        if self._stackImage is not None:
            self.setData()
            if not self._scatterView.getMaskToolsWidget().isVisible():
                # synchronization inactive, force mask redrawing
                mask = self._scatterView.getMaskToolsWidget().getSelectionMask()
                if mask is not None:
                    self._scatterView.getMaskToolsWidget().setSelectionMask(mask)

            self._scatterView.resetZoom()

    def setData(self, stackImage=None):
        first_time = self._stackImage is None
        if first_time:
            assert stackImage is not None

        if stackImage is None:
            # use previous data
            stackImage = self._stackImage
        else:
            # update stored data
            self._stackImage = stackImage
        nrows, ncols = stackImage.shape

        # flatten image
        stackValues = stackImage.reshape((-1,))

        # get regular grid coordinates as a 1D array
        if self._xdata is None or self._ydata is None:
            defaultX, defaultY = numpy.meshgrid(numpy.arange(ncols),
                                                numpy.arange(nrows))
            defaultX = defaultX.reshape(*stackValues.shape)
            defaultY = defaultY.reshape(*stackValues.shape)

        xdata = self._xdata if self._xdata is not None else defaultX
        ydata = self._ydata if self._ydata is not None else defaultY

        if numpy.isscalar(xdata):
            xdata = xdata * numpy.ones_like(stackValues)
            _logger.debug("converting scalar to constant 1D array for x")
        elif len(xdata.shape) > 1:
            _logger.debug("flattening %s array", str(xdata.shape))
            xdata = xdata.reshape((-1,))

        if numpy.isscalar(ydata):
            ydata = ydata * numpy.ones_like(stackValues)
            _logger.debug("converting scalar to constant 1D array for y")
        elif len(ydata.shape) > 1:
            _logger.debug("flattening %s array", str(ydata.shape))
            ydata = ydata.reshape((-1,))

        self._scatterView.setData(xdata, ydata, stackValues,
                                  copy=False)
        if first_time:
            self._scatterView.resetZoom()

    def _maskDockWidget(self):
        widget = self._scatterView.getMaskToolsWidget()
        while widget is not None and not isinstance(widget, qt.QDockWidget):
            widget = widget.parentWidget()
        return widget

    def setMaskToolsVisible(self, visible=True):
        dock = self._maskDockWidget()
        if dock is not None:
            dock.setVisible(visible)

    def setSelectionReadOnly(self):
        '''
        To disable the mask selection for original stack in ROI tool
        '''
        dock = self._maskDockWidget()
        if dock is not None:
            dock.setVisible(False)
            dock.toggleViewAction().setVisible(False)

    def setVisualizationMode(self, mode):
        """
        Allow to set visualization mode like IRREGULAR_GRID
        """
        self._scatterView.getScatterItem().setVisualization(mode)

    def addControlToolBar(self, title="Controls"):
        """
        To be able to add extra menus to the toolbar
        """
        toolbar = qt.QToolBar(title, self._scatterView)
        self._scatterView.addToolBar(qt.Qt.TopToolBarArea, toolbar)
        return toolbar

    def getScatterView(self):
        return self._scatterView

    def setSelectedPositioners(self, xName, yName):
        """

        :param str xName: motor name to use as X axis (or None)
        :param str yName: motor name to use as Y axis (or None)
        """
        if xName is not None:
            self._axesSelector.xPositioner.setCurrentText(xName)
            if xName in self._positioners:
                self._xdata = self._positioners[xName]
        if yName is not None:
            self._axesSelector.yPositioner.setCurrentText(yName)
            if yName in self._positioners:
                self._ydata = self._positioners[yName]



