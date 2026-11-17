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
"""This module implements a plot toolbar with buttons to draw and erase masks.
"""

__author__ = "P. Knobel"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy

from PyMca5.PyMcaGui import PyMcaQt as qt
from .PyMca_Icons import IconDict

from silx.gui import colors



_COLORDICT = colors.COLORDICT
# these are color RGBA strings '#0000ff'
_COLORLIST = [_COLORDICT['black'],
              _COLORDICT['blue'],
              _COLORDICT['red'],
              _COLORDICT['green'],
              _COLORDICT['pink'],
              _COLORDICT['yellow'],
              _COLORDICT['brown'],
              _COLORDICT['cyan'],
              _COLORDICT['magenta'],
              _COLORDICT['orange'],
              _COLORDICT['violet'],
              #_COLORDICT['bluegreen'],
              _COLORDICT['grey'],
              _COLORDICT['darkBlue'],
              _COLORDICT['darkRed'],
              _COLORDICT['darkGreen'],
              _COLORDICT['darkCyan'],
              _COLORDICT['darkMagenta'],
              _COLORDICT['darkYellow'],
              _COLORDICT['darkBrown']]


class MaskToolBar(qt.QToolBar):
    """Toolbar with buttons controlling the mask drawing and erasing
    interactions on a :class:`MaskScatterWidget`, to select or deselect
    data."""
    # sigIconSignal = qt.pyqtSignal(object)
    colorList = _COLORLIST

    def __init__(self, parent=None, plot=None, title="Mask tools",
                 imageIcons=True, polygon=True):
        super(MaskToolBar, self).__init__(title, parent)
        assert plot is not None
        assert imageIcons or polygon,\
            "It makes no sense to build an empty mask toolbar"
        self.plot = plot
        self._brushMenu = None

        self.polygonIcon = qt.QIcon(qt.QPixmap(IconDict["polygon"]))
        self.imageIcon = qt.QIcon(qt.QPixmap(IconDict["image"]))
        self.eraseSelectionIcon = qt.QIcon(qt.QPixmap(IconDict["eraseselect"]))
        self.rectSelectionIcon = qt.QIcon(qt.QPixmap(IconDict["boxselect"]))
        self.brushSelectionIcon = qt.QIcon(qt.QPixmap(IconDict["brushselect"]))
        self.brushIcon = qt.QIcon(qt.QPixmap(IconDict["brush"]))
        self.additionalIcon = qt.QIcon(qt.QPixmap(IconDict["additionalselect"]))

        self.polygonSelectionToolButton = qt.QToolButton(self)
        self.imageToolButton = qt.QToolButton(self)
        self.eraseSelectionToolButton = qt.QToolButton(self)
        self.rectSelectionToolButton = qt.QToolButton(self)
        self.brushSelectionToolButton = qt.QToolButton(self)
        self.brushToolButton = qt.QToolButton(self)
        self.additionalSelectionToolButton = qt.QToolButton(self)

        self.polygonSelectionToolButton.setIcon(self.polygonIcon)
        self.imageToolButton.setIcon(self.imageIcon)
        self.eraseSelectionToolButton.setIcon(self.eraseSelectionIcon)
        self.rectSelectionToolButton.setIcon(self.rectSelectionIcon)
        self.brushSelectionToolButton.setIcon(self.brushSelectionIcon)
        self.brushToolButton.setIcon(self.brushIcon)
        self.additionalSelectionToolButton.setIcon(self.additionalIcon)

        self.polygonSelectionToolButton.setToolTip('Polygon selection\n'
                                                   'Click first point to finish')
        self.imageToolButton.setToolTip('Reset')
        self.eraseSelectionToolButton.setToolTip('Erase Selection')
        self.rectSelectionToolButton.setToolTip('Rectangular Selection')
        self.brushSelectionToolButton.setToolTip('Brush Selection')
        self.brushToolButton.setToolTip('Brush Size')
        self.additionalSelectionToolButton.setToolTip('Additional Selections Menu')

        self.eraseSelectionToolButton.setCheckable(True)
        self.polygonSelectionToolButton.setCheckable(True)
        self.rectSelectionToolButton.setCheckable(True)
        self.brushSelectionToolButton.setCheckable(True)

        self.imageAction = self.addWidget(self.imageToolButton)
        self.eraseSelectionAction = self.addWidget(self.eraseSelectionToolButton)
        self.rectSelectionAction = self.addWidget(self.rectSelectionToolButton)
        self.brushSelectionAction = self.addWidget(self.brushSelectionToolButton)
        self.brushAction = self.addWidget(self.brushToolButton)
        self.polygonSelectionAction = self.addWidget(self.polygonSelectionToolButton)
        self.additionalSelectionAction = self.addWidget(self.additionalSelectionToolButton)

        self.imageToolButton.clicked.connect(self._imageIconSignal)
        self.eraseSelectionToolButton.clicked.connect(self._eraseSelectionIconSignal)
        self.rectSelectionToolButton.clicked.connect(self._rectSelectionIconSignal)
        self.brushSelectionToolButton.clicked.connect(self._brushSelectionIconSignal)
        self.brushToolButton.clicked.connect(self._brushIconSignal)
        self.polygonSelectionToolButton.clicked.connect(self._polygonIconSignal)
        self.additionalSelectionToolButton.clicked.connect(self._additionalIconSignal)

        if not imageIcons:
            self.imageAction.setVisible(False)
            self.eraseSelectionAction.setVisible(False)
            self.rectSelectionAction.setVisible(False)
            self.brushSelectionAction.setVisible(False)
            self.brushAction.setVisible(False)
            self.polygonSelectionAction.setVisible(False)
            self.additionalSelectionAction.setVisible(False)

        if not polygon:
            self.polygonSelectionAction.setVisible(False)

        self._buildAdditionalSelectionMenuDict()

        # selection colors as a RBGA (uint8) array
        self._selectionColors = numpy.zeros((len(self.colorList), 4), numpy.uint8)
        for i in range(len(self.colorList)):
            self._selectionColors[i, 0] = eval("0x" + self.colorList[i][-2:])
            self._selectionColors[i, 1] = eval("0x" + self.colorList[i][3:-2])
            self._selectionColors[i, 2] = eval("0x" + self.colorList[i][1:3])
            self._selectionColors[i, 3] = 0xff

        self.plot.sigInteractiveModeChanged.connect(self._interactiveModeChanged)

    def activateScatterPlotView(self):
        self.brushSelectionAction.setVisible(False)
        self.brushAction.setVisible(False)
        self.eraseSelectionAction.setToolTip("Set erase mode if checked")

        self.eraseSelectionToolButton.setChecked(self.plot._eraseMode)
        self.brushSelectionToolButton.setChecked(False)

    def activateDensityPlotView(self):
        self.brushSelectionAction.setVisible(True)
        self.brushAction.setVisible(True)
        self.rectSelectionAction.setVisible(True)

    def _imageIconSignal(self, checked=False):
        self.plot._resetSelection(owncall=True)

    def _eraseSelectionIconSignal(self, checked=False):
        self.plot._eraseMode = checked

    def _getSelectionColor(self):
        """Return a selection color as hex "#RRGGBBAA" string"""
        rgba_color_array = self._selectionColors[self.plot._nRoi]
        # make sure the selection is made with a non transparent color
        if len(rgba_color_array) == 4:
            rgba_color_array = rgba_color_array.copy()
            rgba_color_array[-1] = 255

        # convert to string
        s = "#"
        for channel_uint8_value in rgba_color_array:
            s += "{:02x}".format(channel_uint8_value)
        return s

    def _polygonIconSignal(self, checked=False):
        if checked:
            self.plot.setInteractiveMode("draw", shape="polygon",
                                         label="mask",
                                         color=self._getSelectionColor())
            self.plot._zoomMode = False
            self.plot._brushMode = False

            self.brushSelectionToolButton.setChecked(False)
            self.rectSelectionToolButton.setChecked(False)
            self.polygonSelectionToolButton.setChecked(True)
        else:
            self.plot.setInteractiveMode("select")
            self._uncheckAllSelectionButtons()

    def setPolygonSelectionMode(self):
        """
        Resets zoom mode and enters selection mode with the current active ROI index
        """
        self.polygonSelectionToolButton.setChecked(True)
        self.polygonSelectionAction.trigger()    # calls _polygonIconSignal

    def _rectSelectionIconSignal(self, checked=False):
        if checked:
            self.plot._zoomMode = False
            self.plot._brushMode = False
            self.brushSelectionToolButton.setChecked(False)
            self.polygonSelectionToolButton.setChecked(False)
            self.rectSelectionToolButton.setChecked(True)

            self.plot.setInteractiveMode("draw",
                                         shape="rectangle",
                                         label="mask",
                                         color=self._getSelectionColor())
        else:
            self.plot.setInteractiveMode("select")
            self._uncheckAllSelectionButtons()

    def _brushSelectionIconSignal(self, checked=False):
        self.polygonSelectionToolButton.setChecked(False)
        self.rectSelectionToolButton.setChecked(False)
        if checked:
            self.plot._brushMode = True
            self.plot.setInteractiveMode('select')
        else:
            self._brushMode = False

    def _brushIconSignal(self, checked=False):
        if self._brushMenu is None:
            self._brushMenu = qt.QMenu()
            self._brushMenu.addAction(" 1 Image Pixel Width",
                                      self._setBrush1)
            self._brushMenu.addAction(" 2 Image Pixel Width",
                                      self._setBrush2)
            self._brushMenu.addAction(" 3 Image Pixel Width",
                                      self._setBrush3)
            self._brushMenu.addAction(" 5 Image Pixel Width",
                                      self._setBrush4)
            self._brushMenu.addAction("10 Image Pixel Width",
                                      self._setBrush5)
            self._brushMenu.addAction("20 Image Pixel Width",
                                      self._setBrush6)
        self._brushMenu.exec(self.cursor().pos())

    def _setBrush1(self):
        self.plot._brushWidth = 1

    def _setBrush2(self):
        self.plot._brushWidth = 2

    def _setBrush3(self):
        self.plot._brushWidth = 3

    def _setBrush4(self):
        self.plot._brushWidth = 5

    def _setBrush5(self):
        self.plot._brushWidth = 10

    def _setBrush6(self):
        self.plot._brushWidth = 20

    def _buildAdditionalSelectionMenuDict(self):
        self._additionalSelectionMenu = {}
        #scatter view menu
        menu = qt.QMenu()
        menu.addAction("Density plot view", self.__setDensityPlotView)
        menu.addAction("Reset Selection", self.__resetSelection)
        menu.addAction("Invert Selection", self.plot._invertSelection)
        self._additionalSelectionMenu["scatter"] = menu

        # density view menu
        menu = qt.QMenu()
        menu.addAction("Scatter plot view", self.__setScatterPlotView)
        menu.addAction("Reset Selection", self.__resetSelection)
        menu.addAction("Invert Selection", self.plot._invertSelection)
        menu.addAction("I >= Colormap Max", self.plot._selectMax)
        menu.addAction("Colormap Min < I < Colormap Max",
                               self.plot._selectMiddle)
        menu.addAction("I <= Colormap Min", self.plot._selectMin)
        menu.addAction("Increase mask alpha", self.plot._increaseMaskAlpha)
        menu.addAction("Decrease mask alpha", self.plot._decreaseMaskAlpha)

        self._additionalSelectionMenu["density"] = menu

    def __setScatterPlotView(self):
        self.plot.setPlotViewMode(mode="scatter")

    def __setDensityPlotView(self):
        self.plot.setPlotViewMode(mode="density")

    def __resetSelection(self):
        self.plot._resetSelection(owncall=True)

    def _additionalIconSignal(self, checked=False):
        if self.plot._plotViewMode == "density":   # and imageData is not none ...
            self._additionalSelectionMenu["density"].exec(self.cursor().pos())
        else:
            self._additionalSelectionMenu["scatter"].exec(self.cursor().pos())

    def _uncheckAllSelectionButtons(self):
        self.brushSelectionToolButton.setChecked(False)
        self.polygonSelectionToolButton.setChecked(False)
        self.brushSelectionToolButton.setChecked(False)

    def _interactiveModeChanged(self, source):
        if self.plot.getInteractiveMode()['mode'] != "draw":
            self._uncheckAllSelectionButtons()

    # def emitIconSignal(self, key, event="iconClicked"):
    #     ddict = {"key": key,
    #              "event": event}
    #     self.sigIconSignal.emit(ddict)


