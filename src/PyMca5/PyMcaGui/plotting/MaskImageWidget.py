#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import os
import numpy
import logging
from PyMca5.PyMcaGraph.ctools import pnpoly
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from . import RGBCorrelatorGraph
from . import ColormapDialog
qt = RGBCorrelatorGraph.qt

IconDict = RGBCorrelatorGraph.IconDict
convertToRowAndColumn = RGBCorrelatorGraph.convertToRowAndColumn
QTVERSION = qt.qVersion()
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str
MATPLOTLIB = False
try:
    from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave
    MATPLOTLIB = True
except ImportError:
    MATPLOTLIB = False
from PyMca5 import spslut
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaIO import ArraySave
from . import ProfileScanWidget
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaMisc import CliUtils

COLORMAPLIST = [spslut.GREYSCALE, spslut.REVERSEGREY, spslut.TEMP,
                spslut.RED, spslut.GREEN, spslut.BLUE, spslut.MANY]

OVERLAY_DRAW = True

DEFAULT_COLORMAP_INDEX = 2
DEFAULT_COLORMAP_LOG_FLAG = False
_logger = logging.getLogger(__name__)


USE_PICKER = False

class MaskImageWidget(qt.QWidget):
    sigMaskImageWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent = None, rgbwidget=None, backend=None, selection=True, colormap=False,
                 imageicons=True, standalonesave=True, usetab=False,
                 profileselection=False, scanwindow=None, aspect=False, polygon=None,
                 maxNRois=1):
        qt.QWidget.__init__(self, parent)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.setWindowTitle("PyMca - Image Selection Tool")
        if 0:
            screenHeight = qt.QDesktopWidget().height()
            if screenHeight > 0:
                self.setMaximumHeight(int(0.99*screenHeight))
                self.setMinimumHeight(int(0.5*screenHeight))
            screenWidth = qt.QDesktopWidget().width()
            if screenWidth > 0:
                self.setMaximumWidth(int(screenWidth)-5)
                self.setMinimumWidth(min(int(0.5*screenWidth),800))

        self._y1AxisInverted = False
        self.__selectionMask = None
        self._selectionColors = None
        self.__imageData = None
        self.__pixmap0 = None
        self.__pixmap = None
        self.__image = None
        self._xScale = None
        self._yScale = None

        self._backend = backend
        self.colormap = None
        self.colormapDialog = None
        self.setDefaultColormap(DEFAULT_COLORMAP_INDEX,
                                DEFAULT_COLORMAP_LOG_FLAG)
        self.rgbWidget = rgbwidget

        self.__imageIconsFlag = imageicons
        if polygon is None:
            polygon = imageicons
        self.__selectionFlag = selection
        self.__useTab = usetab
        self.mainTab = None

        self.__aspect = aspect
        self._maxNRois = maxNRois
        self._nRoi = 1
        self._build(standalonesave, profileselection=profileselection, polygon=polygon)
        self._profileSelectionWindow = None
        self._profileScanWindow = scanwindow

        self.__brushMenu  = None
        self.__brushMode  = False
        self.__eraseMode  = False
        self.__connected = True

        self.__setBrush2()

        self.outputDir   = None
        self._saveFilter = None

        self._buildConnections()
        self._matplotlibSaveImage = None

        # the last overlay legend used
        self.__lastOverlayLegend = None
        self.__lastOverlayWidth = None
        # the projection mode
        self.__lineProjectionMode = 'D'


    def _build(self, standalonesave, profileselection=False, polygon=False):
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        if self.__useTab:
            self.mainTab = qt.QTabWidget(self)
            #self.graphContainer =qt.QWidget()
            #self.graphContainer.mainLayout = qt.QVBoxLayout(self.graphContainer)
            #self.graphContainer.mainLayout.setContentsMargins(0, 0, 0, 0)
            #self.graphContainer.mainLayout.setSpacing(0)
            self.graphWidget = RGBCorrelatorGraph.RGBCorrelatorGraph(self,
                                                   backend=self._backend,
                                                   selection = self.__selectionFlag,
                                                   colormap=True,
                                                   imageicons=self.__imageIconsFlag,
                                                   standalonesave=False,
                                                   standalonezoom=False,
                                                   aspect=self.__aspect,
                                                   profileselection=profileselection,
                                                   polygon=polygon)
            self.mainTab.addTab(self.graphWidget, 'IMAGES')
        else:
            self.graphWidget = RGBCorrelatorGraph.RGBCorrelatorGraph(self,
                                               backend=self._backend,
                                               selection =self.__selectionFlag,
                                               colormap=True,
                                               imageicons=self.__imageIconsFlag,
                                               standalonesave=False,
                                               standalonezoom=False,
                                               profileselection=profileselection,
                                               aspect=self.__aspect,
                                               polygon=polygon)


        if self._maxNRois > 1:
            # multiple ROI control
            self._buildMultipleRois()
        else:
            self._roiTags=[1]

        #for easy compatibility with RGBCorrelatorGraph
        self.graph = self.graphWidget.graph
        if profileselection:
            self.graphWidget.sigProfileSignal.connect(self._profileSignalSlot)

        if standalonesave:
            self.buildStandaloneSaveMenu()

        self.graphWidget.zoomResetToolButton.clicked.connect(self._zoomResetSignal)
        self.graphWidget.graph.setDrawModeEnabled(False)
        self.graphWidget.graph.setZoomModeEnabled(True)
        if self.__selectionFlag:
            if self.__imageIconsFlag:
                self.setSelectionMode(False)
                self._toggleSelectionMode()
                self.graphWidget.graph.setDrawModeEnabled(True,
                                                          shape="rectangle",
                                                          label="mask")
            else:
                self.setSelectionMode(True)
                self._toggleSelectionMode()
        if self.__useTab:
            self.mainLayout.addWidget(self.mainTab)
        else:
            self.mainLayout.addWidget(self.graphWidget)

    def buildStandaloneSaveMenu(self):
        self.graphWidget.saveToolButton.clicked.connect(self._saveToolButtonSignal)
        self._saveMenu = qt.QMenu()
        self._saveMenu.addAction(QString("Image Data"),
                                 self.saveImageList)
        self._saveMenu.addAction(QString("Colormap Clipped Seen Image Data"),
                                 self.saveClippedSeenImageList)
        self._saveMenu.addAction(QString("Clipped and Subtracted Seen Image Data"),
                                 self.saveClippedAndSubtractedSeenImageList)

        self._saveMenu.addAction(QString("Standard Graphics"),
                                 self.graphWidget._saveIconSignal)
        if MATPLOTLIB:
            self._saveMenu.addAction(QString("Matplotlib") ,
                             self._saveMatplotlibImage)

    def _buildMultipleRois(self):
        """
        Multiple ROI control
        """
        mytoolbar = self.graphWidget.toolBar

        self._nRoiLabel = qt.QLabel(mytoolbar)
        self._nRoiLabel.setText("Roi:")
        mytoolbar.layout().addWidget(self._nRoiLabel )

        self._nRoiSelector = qt.QSpinBox(mytoolbar)
        self._nRoiSelector.setMinimum(1)
        self._nRoiSelector.setMaximum(self._maxNRois)
        mytoolbar.layout().addWidget(self._nRoiSelector)
        self._nRoiSelector.valueChanged[int].connect(self.setActiveRoiNumber)

        if 0:
            self._nRoiTagLabel = qt.QLabel(mytoolbar)
            self._nRoiTagLabel.setText("Tag:")
            mytoolbar.layout().addWidget(self._nRoiTagLabel)
            self._nRoiTag = qt.QSpinBox(mytoolbar)
            self._nRoiTag.setMinimum(1)
            self._nRoiTag.setMaximum(self._maxNRois)
            mytoolbar.layout().addWidget(self._nRoiTag)
            self._nRoiTag.valueChanged[int].connect(self.tagRoi)
        # initialize tags (ROI 1 , has tag 1, ROI 2 has tag 2, ...)
        self._roiTags = list(range(1, self._maxNRois + 1))

    def _buildConnections(self, widget = None):
        self.graphWidget.hFlipToolButton.clicked.connect(self._hFlipIconSignal)

        self.graphWidget.colormapToolButton.clicked.connect(self.selectColormap)

        if self.__selectionFlag:
            self.graphWidget.selectionToolButton.clicked.connect(self._toggleSelectionMode)
            text = "Toggle between Selection\nand Zoom modes"
            self.graphWidget.selectionToolButton.setToolTip(text)

        if self.__imageIconsFlag:
            self.graphWidget.imageToolButton.clicked.connect(\
                self.__resetSelection)

            self.graphWidget.eraseSelectionToolButton.clicked.connect(\
                self._setEraseSelectionMode)

            self.graphWidget.rectSelectionToolButton.clicked.connect(\
                self._setRectSelectionMode)

            self.graphWidget.brushSelectionToolButton.clicked.connect(\
                self._setBrushSelectionMode)

            self.graphWidget.brushToolButton.clicked.connect(self._setBrush)

            if hasattr(self.graphWidget, "polygonSelectionToolButton"):
                self.graphWidget.polygonSelectionToolButton.clicked.connect(\
                    self._setPolygonSelectionMode)

            self.graphWidget.additionalSelectionToolButton.clicked.connect(\
                self._additionalSelectionMenuDialog)
            self._additionalSelectionMenu = qt.QMenu()
            self._additionalSelectionMenu.addAction(QString("Reset Selection"),
                                                    self.__resetSelection)
            self._additionalSelectionMenu.addAction(QString("Invert Selection"),
                                                    self._invertSelection)
            self._additionalSelectionMenu.addAction(QString("I >= Colormap Max"),
                                                    self._selectMax)
            self._additionalSelectionMenu.addAction(QString("Colormap Min < I < Colormap Max"),
                                                    self._selectMiddle)
            self._additionalSelectionMenu.addAction(QString("I <= Colormap Min"),
                                                    self._selectMin)
        self.graphWidget.graph.sigPlotSignal.connect(self._graphSignal)


    def setSelectionColors(self, selectionColors):
        """
        selectionColors must be None or an array of shape (n, 4) of type numpy.uint8
        """
        if selectionColors is None:
            self._selectionColors = None
            return
        if selectionColors.shape[1] != 4:
            raise ValueError("Array of shape (maxNRois, 4) needed")
        if selectionColors.dtype != numpy.uint8:
            raise TypeError("Array of unsigned bytes needed")
        self._selectionColors = selectionColors

    def additionalSelectionMenu(self):
        return self._additionalSelectionMenu

    def updateProfileSelectionWindow(self):
        mode = self.graphWidget.getPickerSelectionMode()
        if self.__lastOverlayLegend is not None:
            if mode is None:
                # remove the overlay if present
                legend = self.__lastOverlayLegend
                self.graphWidget.graph.removeItem(legend)
            elif self.__lastOverlayWidth is not None:
                # create a fake signal
                ddict = {}
                ddict['event'] = "profileWidthChanged"
                ddict['pixelwidth'] = self.__lastOverlayWidth
                ddict['mode'] = mode
                self._profileSignalSlot(ddict)

    def _profileSignalSlot(self, ddict):
        _logger.debug("_profileSignalSLot, event = %s", ddict['event'])
        _logger.debug("Received ddict = %s", ddict)

        if ddict['event'] in [None, "NONE"]:
            #Nothing to be made
            return

        if ddict['event'] == "profileWidthChanged":
            if self.__lastOverlayLegend is not None:
                legend = self.__lastOverlayLegend
                #TODO: Find a better way to deal with this
                if legend in self.graphWidget.graph._itemDict:
                    info = self.graphWidget.graph._itemDict[legend]['info']
                    if info['mode'] == ddict['mode']:
                        newDict = {}
                        newDict['event'] = "updateProfile"
                        newDict['xdata'] = info['xdata'] * 1
                        newDict['ydata'] = info['ydata'] * 1
                        newDict['mode'] = info['mode'] * 1
                        newDict['pixelwidth'] = ddict['pixelwidth'] * 1
                        info = None
                        #self._updateProfileCurve(newDict)
                        self._profileSignalSlot(newDict)
            return

        if self._profileSelectionWindow is None:
            if self._profileScanWindow is None:
                #identical to the standard scan window
                self._profileSelectionWindow = ProfileScanWidget.ProfileScanWidget(actions=False)
            else:
                self._profileSelectionWindow = ProfileScanWidget.ProfileScanWidget(actions=True)
                self._profileSelectionWindow.sigAddClicked.connect( \
                             self._profileSelectionSlot)
                self._profileSelectionWindow.sigRemoveClicked.connect( \
                             self._profileSelectionSlot)
                self._profileSelectionWindow.sigReplaceClicked.connect(
                             self._profileSelectionSlot)
            self._interpolate = SpecfitFuns.interpol
            #if I do not return here and the user interacts with the graph while
            #the profileSelectionWindow is not shown, I get crashes under Qt 4.5.3 and MacOS X
            #when calling _getProfileCurve
            ############## TODO: show it here?
            self._profileSelectionWindow.show()
            return

        self._updateProfileCurve(ddict)

    def _updateProfileCurve(self, ddict):
        curve = self._getProfileCurve(ddict)
        if curve is None:
            return
        xdata, ydata, legend, info = curve
        replot=True
        replace=True
        idx = numpy.isfinite(ydata)
        xdata = xdata[idx]
        ydata = ydata[idx]
        self._profileSelectionWindow.addCurve(xdata, ydata,
                                              legend=legend,
                                              info=info,
                                              replot=replot,
                                              replace=replace)

    def getGraphTitle(self):
        try:
            title = self.graphWidget.graph.getGraphTitle()
            if sys.version < '3.0':
                title = qt.safe_str(title)
        except Exception:
            title = ""
        return title

    def setGraphTitle(self, title=""):
        self.graphWidget.graph.setGraphTitle(title)

    def setLineProjectionMode(self, mode):
        """
        Set the line projection mode.

        mode: 1 character string. Allowed options 'D', 'X' 'Y'
        D - Plot the intensity over the drawn line over as many intervals as pixels over the axis
            containing the longest projection in pixels.
        X - Plot the intensity over the drawn line over as many intervals as pixels over the X axis
        Y - Plot the intensity over the drawn line over as many intervals as pixels over the Y axis
        """
        m = mode.upper()
        if m not in ['D', 'X', 'Y']:
            raise ValueError("Invalid mode %s. It has to be 'D', 'X' or 'Y'")
        self.__lineProjectionMode = m

    def getLineProjectionMode(self):
        return self.__lineProjectionMode

    def _getProfileCurve(self, ddict, image=None, overlay=OVERLAY_DRAW):
        if image is None:
            imageData = self.__imageData
        else:
            imageData = image
        if imageData is None:
            return None

        title = self.getGraphTitle()

        self._profileSelectionWindow.setGraphTitle(title)
        if self._profileScanWindow is not None:
            self._profileSelectionWindow.label.setText(title)

        #showing the profileSelectionWindow now can make the program crash if the workaround mentioned above
        #is not implemented
        self._profileSelectionWindow.show()
        #self._profileSelectionWindow.raise_()

        if ddict['event'] == 'profileModeChanged':
            if self.__lastOverlayLegend:
                self.graphWidget.graph.removeItem(self.__lastOverlayLegend, replot=True)
            return

        #if I show the image here it does not crash, but it is not nice because
        #the user would get the profileSelectionWindow under his mouse
        #self._profileSelectionWindow.show()

        if ('row' in ddict) and ('column' in ddict):
            # probably arriving after width changed
            pass
        else:
            r0, c0 = convertToRowAndColumn(ddict['xdata'][0], ddict['ydata'][0],
                                                        self.__imageData.shape,
                                                        xScale=self._xScale,
                                                        yScale=self._yScale,
                                                        safe=True)
            r1, c1 = convertToRowAndColumn(ddict['xdata'][1], ddict['ydata'][1],
                                                        self.__imageData.shape,
                                                        xScale=self._xScale,
                                                        yScale=self._yScale,
                                                        safe=True)
            ddict['row'] = [r0, r1]
            ddict['column'] = [c0, c1]

        shape = imageData.shape
        width = ddict['pixelwidth'] - 1
        if ddict['mode'].upper() in ["HLINE", "HORIZONTAL"]:
            xLabel = self.getXLabel()
            deltaDistance = 1.0
            if width < 1:
                row = int(ddict['row'][0])
                if row < 0:
                    row = 0
                if row >= shape[0]:
                    row = shape[0] - 1
                ydata  = imageData[row, :]
                legend = "Row = %d"  % row
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([0.0, shape[1], shape[1], 0.0],
                                         [row, row, row+1, row+1],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            else:
                row0 = int(int(ddict['row'][0]) - 0.5 * width)
                if row0 < 0:
                    row0 = 0
                    row1 = row0 + width
                else:
                    row1 = int(int(ddict['row'][0]) + 0.5 * width)
                if row1 >= shape[0]:
                    row1 = shape[0] - 1
                    row0 = max(0, row1 - width)

                ydata = imageData[row0:row1+1, :].sum(axis=0)
                legend = "Row = %d to %d"  % (row0, row1)
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([0.0, 0.0, shape[1], shape[1]],
                                         [row0, row1+1, row1+1, row0],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            xdata  = numpy.arange(shape[1]).astype(numpy.float64)
            if self._xScale is not None:
                xdata = self._xScale[0] + xdata * self._xScale[1]
        elif ddict['mode'].upper() in ["VLINE", "VERTICAL"]:
            xLabel = self.getYLabel()
            deltaDistance = 1.0
            if width < 1:
                column = int(ddict['column'][0])
                if column < 0:
                    column = 0
                if column >= shape[1]:
                    column = shape[1] - 1
                ydata  = imageData[:, column]
                legend = "Column = %d"  % column
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([column, column, column+1, column+1],
                                         [0.0, shape[0], shape[0], 0.0],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            else:
                col0 = int(int(ddict['column'][0]) - 0.5 * width)
                if col0 < 0:
                    col0 = 0
                    col1 = col0 + width
                else:
                    col1 = int(int(ddict['column'][0]) + 0.5 * width)
                if col1 >= shape[1]:
                    col1 = shape[1] - 1
                    col0 = max(0, col1 - width)

                ydata = imageData[:, col0:col1+1].sum(axis=1)
                legend = "Col = %d to %d"  % (col0, col1)
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([col0, col0, col1+1, col1+1],
                                         [0, shape[0], shape[0], 0.],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            xdata  = numpy.arange(shape[0]).astype(numpy.float64)
            if self._yScale is not None:
                xdata = self._yScale[0] + xdata * self._yScale[1]
        elif ddict['mode'].upper() in ["LINE"]:
            if len(ddict['column']) == 1:
                #only one point given
                return
            #the coordinates of the reference points
            x0 = numpy.arange(float(shape[0]))
            y0 = numpy.arange(float(shape[1]))
            #get the interpolation points
            col0, col1 = [int(x) for x in ddict['column']]
            row0, row1 = [int(x) for x in ddict['row']]
            deltaCol = abs(col0 - col1)
            deltaRow = abs(row0 - row1)

            if self.__lineProjectionMode == 'X' or (
                    self.__lineProjectionMode == 'D' and deltaCol >= deltaRow):
                npoints = deltaCol + 1
                if col1 < col0:
                    # Invert start and end points
                    row0, col0, row1, col1 = row1, col1, row0, col0
            else:  #  mode == 'Y' or (mode == 'D' and deltaCol < deltaRow)
                npoints = deltaRow + 1
                if row1 < row0:
                    # Invert start and end points
                    row0, col0, row1, col1 = row1, col1, row0, col0

            if npoints == 1:
                #all points are the same
                _logger.debug("START AND END POINT ARE THE SAME!!")
                return

            # make sure we deal with integers
            npoints = int(npoints)

            if width < 0:  # width = pixelwidth - 1
                x = numpy.zeros((npoints, 2), numpy.float64)
                x[:, 0] = numpy.linspace(row0, row1, npoints)
                x[:, 1] = numpy.linspace(col0, col1, npoints)
                legend = "From (%.3f, %.3f) to (%.3f, %.3f)" % (col0, row0, col1, row1)
                #perform the interpolation
                ydata = self._interpolate((x0, y0), imageData, x)
                xdata = numpy.arange(float(npoints))

                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([col0, col1],
                                         [row0, row1],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            elif deltaCol == 0:
                #vertical line
                col0 = int(int(ddict['column'][0]) - 0.5 * width)
                if col0 < 0:
                    col0 = 0
                    col1 = col0 + width
                else:
                    col1 = int(int(ddict['column'][0]) + 0.5 * width)
                if col1 >= shape[1]:
                    col1 = shape[1] - 1
                    col0 = max(0, col1 - width)
                row0 = int(ddict['row'][0])
                row1 = int(ddict['row'][1])
                if row0 > row1:
                    tmp = row0
                    row0 = row1
                    row1 = tmp
                if row0 < 0:
                    row0 = 0
                if row1 >= shape[0]:
                    row1 = shape[0] - 1
                ydata = imageData[row0:row1+1, col0:col1+1].sum(axis=1)
                legend = "Col = %d to %d"  % (col0, col1)
                npoints = max(ydata.shape)
                xdata = numpy.arange(float(npoints))
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([col0, col0, col1+1, col1+1],
                                         [row0, row1+1, row1+1, row0],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            elif deltaRow == 0:
                #horizontal line
                row0 = int(int(ddict['row'][0]) - 0.5 * width)
                if row0 < 0:
                    row0 = 0
                    row1 = row0 + width
                else:
                    row1 = int(int(ddict['row'][0]) + 0.5 * width)
                if row1 >= shape[0]:
                    row1 = shape[0] - 1
                    row0 = max(0, row1 - width)
                col0 = int(ddict['column'][0])
                col1 = int(ddict['column'][1])
                if col0 > col1:
                    tmp = col0
                    col0 = col1
                    col1 = tmp
                if col0 < 0:
                    col0 = 0
                if col1 >= shape[1]:
                    col1 = shape[1] - 1
                ydata = imageData[row0:row1+1, col0:col1+1].sum(axis=0)
                legend = "Row = %d to %d"  % (row0, row1)
                npoints = max(ydata.shape)
                xdata = numpy.arange(float(npoints))
                if overlay:
                    #self.drawOverlayItem(x, y, legend=name, info=info, replot, replace)
                    self.drawOverlayItem([col0, col0, col1+1, col1+1],
                                         [row0, row1+1, row1+1, row0],
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            else:
                #restore original value of width
                width = ddict['pixelwidth']
                #find m and b in the line y = mx + b
                m = (row1 - row0) / float((col1 - col0))
                b = row0 - m * col0
                alpha = numpy.arctan(m)
                #imagine the following sequence
                # - change origin to the first point
                # - clock-wise rotation to bring the line on the x axis of a new system
                # so that the points (col0, row0) and (col1, row1) become (x0, 0) (x1, 0)
                # - counter clock-wise rotation to get the points (x0, -0.5 width),
                # (x0, 0.5 width), (x1, 0.5 * width) and (x1, -0.5 * width) back to the
                # original system.
                # - restore the origin to (0, 0)
                # - if those extremes are inside the image the selection is acceptable
                cosalpha = numpy.cos(alpha)
                sinalpha = numpy.sin(alpha)
                newCol0 = 0.0
                newCol1 = (col1-col0) * cosalpha + (row1-row0) * sinalpha
                newRow0 = 0.0
                newRow1 = -(col1-col0) * sinalpha + (row1-row0) * cosalpha

                _logger.debug("new X0 Y0 = %f, %f  ", newCol0, newRow0)
                _logger.debug("new X1 Y1 = %f, %f  ", newCol1, newRow1)

                tmpX   = numpy.linspace(newCol0, newCol1, npoints).astype(numpy.float64)
                rotMatrix = numpy.zeros((2,2), numpy.float64)
                rotMatrix[0,0] =   cosalpha
                rotMatrix[0,1] = - sinalpha
                rotMatrix[1,0] =   sinalpha
                rotMatrix[1,1] =   cosalpha
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    #test if I recover the original points
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

                #find the drawing limits
                testX = numpy.zeros((2, 4) , numpy.float64)
                testX[0,0] = newCol0
                testX[0,1] = newCol0
                testX[0,2] = newCol1
                testX[0,3] = newCol1
                testX[1,0] = newRow0 - 0.5 * width
                testX[1,1] = newRow0 + 0.5 * width
                testX[1,2] = newRow1 + 0.5 * width
                testX[1,3] = newRow1 - 0.5 * width
                colRow = numpy.dot(rotMatrix, testX)
                colLimits0 = colRow[0, :] + col0
                rowLimits0 = colRow[1, :] + row0

                for a in rowLimits0:
                    if (a >= shape[0]) or (a < 0):
                        _logger.debug("outside row limits %s" % a)
                        return
                for a in colLimits0:
                    if (a >= shape[1]) or (a < 0):
                        _logger.debug("outside column limits %s" % a)
                        return

                r0 = rowLimits0[0]
                r1 = rowLimits0[1]

                if r0 > r1:
                    _logger.debug("r0 > r1 %s %s" % (r0, r1))
                    raise ValueError("r0 > r1")

                x = numpy.zeros((2, npoints) , numpy.float64)
                tmpMatrix = numpy.zeros((npoints, 2) , numpy.float64)

                if 0:
                    #take only the central point
                    oversampling = 1
                    x[0, :] = tmpX
                    x[1, :] = 0.0
                    colRow = numpy.dot(rotMatrix, x)
                    colRow[0, :] += col0
                    colRow[1, :] += row0
                    tmpMatrix[:,0] = colRow[1,:]
                    tmpMatrix[:,1] = colRow[0,:]
                    ydataCentral = self._interpolate((x0, y0),\
                                    imageData, tmpMatrix)
                    #multiply by width too have the equivalent scale
                    ydata = ydataCentral
                else:
                    if True: #ddict['event'] == "PolygonSelected":
                        #oversampling solves noise introduction issues
                        oversampling = width + 1
                        oversampling = min(oversampling, 21)
                    else:
                        oversampling = 1
                    ncontributors = int(width * oversampling)
                    iterValues = numpy.linspace(-0.5*width, 0.5*width, ncontributors)
                    tmpMatrix = numpy.zeros((npoints*len(iterValues), 2) , numpy.float64)
                    x[0, :] = tmpX
                    offset = 0
                    for i in iterValues:
                        x[1, :] = i
                        colRow = numpy.dot(rotMatrix, x)
                        colRow[0, :] += col0
                        colRow[1, :] += row0
                        """
                        colLimits = [colRow[0, 0], colRow[0, -1]]
                        rowLimits = [colRow[1, 0], colRow[1, -1]]
                        for a in rowLimits:
                            if (a >= shape[0]) or (a < 0):
                                print("outside row limits",a)
                                return
                        for a in colLimits:
                            if (a >= shape[1]) or (a < 0):
                                print("outside column limits",a)
                                return
                        """
                        #it is much faster to make one call to the interpolating
                        #routine than making many calls
                        tmpMatrix[offset:(offset+npoints),0] = colRow[1,:]
                        tmpMatrix[offset:(offset+npoints),1] = colRow[0,:]
                        offset += npoints
                    ydata = self._interpolate((x0, y0),\
                                   imageData, tmpMatrix)
                    ydata = ydata.reshape(len(iterValues), npoints)
                    ydata = ydata.sum(axis=0)
                    #deal with the oversampling
                    ydata /= oversampling

                xdata = numpy.arange(float(npoints))
                legend = "y = %f (x-%.1f) + %f ; width=%d" % (m, col0, b, width)
                if overlay:
                    self.drawOverlayItem(colLimits0,
                                         rowLimits0,
                                         legend=ddict['mode'],
                                         info=ddict,
                                         replace=True,
                                         replot=True)
            if self.__lineProjectionMode == 'X':
                xLabel = self.getXLabel()
                xdata += col0
                if self._xScale is not None:
                    xdata = self._xScale[0] + xdata * self._xScale[1]
            elif self.__lineProjectionMode == 'Y':
                xLabel = self.getYLabel()
                xdata += row0
                if self._xScale is not None:
                    xdata = self._yScale[0] + xdata * self._yScale[1]
            else:
                xLabel = "Distance"
                if self._xScale is not None:
                    deltaCol *= self._xScale[1]
                    deltaRow *= self._yScale[1]
                #get the abscisa in distance units
                deltaDistance = numpy.sqrt(float(deltaCol) * deltaCol +
                                    float(deltaRow) * deltaRow)/(npoints-1.0)
                xdata *= deltaDistance
        else:
            _logger.debug("Mode %s not supported yet %s", ddict['mode'])
            return

        self.__lastOverlayWidth = ddict['pixelwidth']
        info = {}
        info['xlabel'] = xLabel
        info['ylabel'] = "Z"
        return xdata, ydata, legend, info

    def _profileSelectionSlot(self, ddict):
        _logger.debug("%s", ddict)
        # the curves as [[x0, y0, legend0, info0], ...]
        curveList = ddict['curves']
        label = ddict['label']
        n = len(curveList)
        if ddict['event'] == 'ADD':
            for i in range(n):
                x, y, legend, info = curveList[i]
                info['profilelabel'] = label
                if i == (n-1):
                    replot = True
                self._profileScanWindow.addCurve(x, y, legend=legend, info=info,
                                                 replot=replot, replace=False)
        elif ddict['event'] == 'REPLACE':
            for i in range(n):
                x, y, legend, info = curveList[i]
                info['profilelabel'] = label
                if i in [0, n-1]:
                    replace = True
                else:
                    replace = False
                if i == (n-1):
                    replot = True
                else:
                    replot = False
                self._profileScanWindow.addCurve(x, y, legend=legend, info=info,
                                                 replot=replot, replace=replace)
        elif ddict['event'] == 'REMOVE':
            curveList = self._profileScanWindow.getAllCurves()
            if curveList in [None, []]:
                return
            toDelete = []
            n = len(curveList)
            for i in range(n):
                x, y, legend, info = curveList[i]
                curveLabel = info.get('profilelabel', None)
                if curveLabel is not None:
                    if label == curveLabel:
                        toDelete.append(legend)
            n = len(toDelete)
            for i in range(n):
                legend = toDelete[i]
                if i == (n-1):
                    replot = True
                else:
                    replot = False
                self._profileScanWindow.removeCurve(legend, replot=replot)

    def drawOverlayItem(self, x, y, legend=None, info=None, replace=False, replot=True):
        #same call as the plot1D addCurve command
        if legend is None:
            legend="UnnamedOverlayItem"
        #the type of x can be list or array
        shape = self.__imageData.shape
        if self._xScale is None:
            xList = x
        else:
            xList = []
            for i in x:
                xList.append(self._xScale[0] + i * self._xScale[1])

        if self._yScale is None:
            yList = y
        else:
            yList = []
            for i in y:
                yList.append(self._yScale[0] + i * self._yScale[1])
        self.graphWidget.graph.addItem(xList, yList, legend=legend, info=info,
                                               replace=replace, replot=replot,
                                               shape="polygon", fill=True)
        self.__lastOverlayLegend = legend

    def _hFlipIconSignal(self):
        self._y1AxisInverted = self.graphWidget.graph.isYAxisInverted()
        if self._y1AxisInverted:
            self._y1AxisInverted = False
        else:
            self._y1AxisInverted = True
        #self.graphWidget.graph.zoomReset()
        self.graphWidget.graph.invertYAxis(self._y1AxisInverted)
        self._y1AxisInverted = self.graphWidget.graph.isYAxisInverted()
        self.graphWidget.graph.replot()

        #inform the other widgets
        ddict = {}
        ddict['event'] = "hFlipSignal"
        ddict['current'] = self._y1AxisInverted * 1
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def setY1AxisInverted(self, value):
        self._y1AxisInverted = value
        self.graphWidget.graph.invertYAxis(self._y1AxisInverted)

    def setXLabel(self, label="Column"):
        return self.graphWidget.setXLabel(label)

    def setYLabel(self, label="Row"):
        return self.graphWidget.setYLabel(label)

    def getXLabel(self):
        return self.graphWidget.getXLabel()

    def getYLabel(self):
        return self.graphWidget.getYLabel()

    def buildAndConnectImageButtonBox(self, replace=True, multiple=False):
        # The IMAGE selection
        self.imageButtonBox = qt.QWidget(self)
        buttonBox = self.imageButtonBox
        self.imageButtonBoxLayout = qt.QHBoxLayout(buttonBox)
        self.imageButtonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.imageButtonBoxLayout.setSpacing(0)
        self.addImageButton = qt.QPushButton(buttonBox)
        icon = qt.QIcon(qt.QPixmap(IconDict["rgb16"]))
        self.addImageButton.setIcon(icon)
        self.addImageButton.setText("ADD IMAGE")

        self.imageButtonBoxLayout.addWidget(self.addImageButton)
        if multiple:
            self.addAllImageButton = qt.QPushButton(buttonBox)
            self.addAllImageButton.setIcon(icon)
            self.addAllImageButton.setText("ADD ALL")
            self.imageButtonBoxLayout.addWidget(self.addAllImageButton)
            self.addAllImageButton.clicked.connect( \
                                self._addAllImageClicked)

        self.removeImageButton = qt.QPushButton(buttonBox)
        self.removeImageButton.setIcon(icon)
        self.removeImageButton.setText("REMOVE IMAGE")
        self.imageButtonBoxLayout.addWidget(self.removeImageButton)

        self.mainLayout.addWidget(buttonBox)

        self.addImageButton.clicked.connect(self._addImageClicked)
        self.removeImageButton.clicked.connect(self._removeImageClicked)
        if replace:
            self.replaceImageButton = qt.QPushButton(buttonBox)
            self.replaceImageButton.setIcon(icon)
            self.replaceImageButton.setText("REPLACE IMAGE")
            self.imageButtonBoxLayout.addWidget(self.replaceImageButton)
            self.replaceImageButton.clicked.connect( \
                                self._replaceImageClicked)

    def _setEraseSelectionMode(self):
        _logger.debug("_setEraseSelectionMode")
        self.__eraseMode = True
        self.__brushMode = True
        self.graphWidget.graph.setDrawModeEnabled(False)

    def _setRectSelectionMode(self):
        _logger.debug("_setRectSelectionMode")
        self.__eraseMode = False
        self.__brushMode = False
        self.graphWidget.graph.setDrawModeEnabled(True,
                                                  shape="rectangle",
                                                  label="mask")

    def _setPolygonSelectionMode(self):
        self.__eraseMode = False
        self.__brushMode = False
        self.graphWidget.graph.setDrawModeEnabled(True,
                                                  shape="polygon",
                                                  label="mask")

    def _setBrushSelectionMode(self):
        _logger.debug("_setBrushSelectionMode")
        self.__eraseMode = False
        self.__brushMode = True
        self.graphWidget.graph.setDrawModeEnabled(False)

    def _setBrush(self):
        _logger.debug("_setBrush")
        if self.__brushMenu is None:
            self.__brushMenu = qt.QMenu()
            self.__brushMenu.addAction(QString(" 1 Image Pixel Width"),
                                       self.__setBrush1)
            self.__brushMenu.addAction(QString(" 2 Image Pixel Width"),
                                       self.__setBrush2)
            self.__brushMenu.addAction(QString(" 3 Image Pixel Width"),
                                       self.__setBrush3)
            self.__brushMenu.addAction(QString(" 5 Image Pixel Width"),
                                       self.__setBrush4)
            self.__brushMenu.addAction(QString("10 Image Pixel Width"),
                                       self.__setBrush5)
            self.__brushMenu.addAction(QString("20 Image Pixel Width"),
                                       self.__setBrush6)
        self.__brushMenu.exec(self.cursor().pos())

    def __setBrush1(self):
        self.__brushWidth = 1

    def __setBrush2(self):
        self.__brushWidth = 2

    def __setBrush3(self):
        self.__brushWidth = 3

    def __setBrush4(self):
        self.__brushWidth = 5

    def __setBrush5(self):
        self.__brushWidth = 10

    def __setBrush6(self):
        self.__brushWidth = 20

    def _toggleSelectionMode(self):
        drawMode = self.graphWidget.graph.getDrawMode()
        if drawMode is None:
            # we are not drawing anything
            if self.graphWidget.graph.isZoomModeEnabled():
                # we have to pass to mask mode
                self.setSelectionMode(True)
            else:
                # we set zoom mode and show the line icons
                self.setSelectionMode(False)
        elif drawMode['label'] is not None:
            if drawMode['label'].startswith('mask'):
                #we set the zoom mode and show the line icons
                self.setSelectionMode(False)
            else:
                # we disable zoom and drawing and set mask mode
                self.setSelectionMode(True)
        elif drawMode['label'] in [None]:
            # we are not drawing anything
            if self.graphWidget.graph.isZoomModeEnabled():
                # we have to pass to mask mode
                self.setSelectionMode(True)
            else:
                # we set zoom mode and show the line icons
                self.setSelectionMode(False)

    def setSelectionMode(self, mode=None):
        #does it have sense to enable the selection without the image selection icons?
        #if not self.__imageIconsFlag:
        #    mode = False
        if mode:
            self.graphWidget.graph.setDrawModeEnabled(True,
                                                      'rectangle',
                                                      label='mask')
            self.__brushMode = False
            self.graphWidget.hideProfileSelectionIcons()
            self.graphWidget.selectionToolButton.setChecked(True)
            self.graphWidget.selectionToolButton.setDown(True)
            self.graphWidget.showImageIcons()
        else:
            self.graphWidget.showProfileSelectionIcons()
            self.graphWidget.graph.setZoomModeEnabled(True)
            self.graphWidget.selectionToolButton.setChecked(False)
            self.graphWidget.selectionToolButton.setDown(False)
            self.graphWidget.hideImageIcons()
        if self.__imageData is None:
            return

    def _additionalSelectionMenuDialog(self):
        if self.__imageData is None:
            return
        self._additionalSelectionMenu.exec(self.cursor().pos())

    def _getSelectionMinMax(self):
        if self.colormap is None:
            goodData = self.__imageData[numpy.isfinite(self.__imageData)]
            maxValue = goodData.max()
            minValue = goodData.min()
        else:
            minValue = self.colormap[2]
            maxValue = self.colormap[3]

        return minValue, maxValue

    def _selectMax(self):
        selectionMask = numpy.zeros(self.__imageData.shape,
                                             numpy.uint8)
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self.__imageData, copy=True)
        tmpData[~numpy.isfinite(self.__imageData)] = minValue
        selectionMask[tmpData >= maxValue] = 1
        self.setSelectionMask(selectionMask, plot=False)
        self.plotImage(update=False)
        self._emitMaskChangedSignal()

    def _selectMiddle(self):
        selectionMask = numpy.ones(self.__imageData.shape,
                                             numpy.uint8)
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self.__imageData, copy=True)
        tmpData[~numpy.isfinite(self.__imageData)] = maxValue
        selectionMask[tmpData >= maxValue] = 0
        selectionMask[tmpData <= minValue] = 0
        self.setSelectionMask(selectionMask, plot=False)
        self.plotImage(update=False)
        self._emitMaskChangedSignal()

    def _selectMin(self):
        selectionMask = numpy.zeros(self.__imageData.shape,
                                             numpy.uint8)
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self.__imageData, copy=True)
        tmpData[~numpy.isfinite(self.__imageData)] = maxValue
        selectionMask[tmpData <= minValue] = 1
        self.setSelectionMask(selectionMask, plot=False)
        self.plotImage(update=False)
        self._emitMaskChangedSignal()

    def _invertSelection(self):
        if self.__imageData is None:
            return
        mask = numpy.ones(self.__imageData.shape,
                                             numpy.uint8)
        if self.__selectionMask is not None:
            mask[self.__selectionMask > 0] = 0

        self.setSelectionMask(mask, plot=True)
        self._emitMaskChangedSignal()

    def __resetSelection(self):
        # Needed because receiving directly in _resetSelection it was passing
        # False as argument
        self._resetSelection(True)

    def _resetSelection(self, owncall=True):
        _logger.debug("_resetSelection")
        self.__selectionMask = None
        if self.__imageData is None:
            return
        #self.__selectionMask = numpy.zeros(self.__imageData.shape, numpy.uint8)
        self.plotImage(update = True)

        #inform the others
        if owncall:
            ddict = {}
            ddict['event'] = "resetSelection"
            ddict['id'] = id(self)
            self.emitMaskImageSignal(ddict)

    def setSelectionMask(self, mask, plot=True):
        if mask is not None:
            if self.__imageData is not None:
                # this operation will be made when retrieving the mask
                #mask *= numpy.isfinite(self.__imageData)
                if self.__imageData.size == mask.size:
                    view = mask[:]
                    view = view.reshape(*self.__imageData.shape)
                    mask = view
        self.__selectionMask = mask
        if plot:
            self.plotImage(update=False)

    def getSelectionMask(self):
        if self.__imageData is None:
            return None
        if self.__selectionMask is None:
             return numpy.zeros(self.__imageData.shape, numpy.uint8) *\
                    numpy.isfinite(self.__imageData)
        return self.__selectionMask *\
                    numpy.isfinite(self.__imageData)

    def setImageData(self, data, clearmask=False, xScale=None, yScale=None):
        self.__image = None
        self._xScale = xScale
        self._yScale = yScale
        if data is None:
            self.__imageData = data
            if not clearmask:
                self.__selectionMask = None
            self.plotImage(update=True)
            self.graphWidget._zoomReset(replot=True)
            return
        else:
            self.__imageData = data
        if clearmask:
            self.__selectionMask = None
        if self.__selectionMask is not None and self.__imageData is not None:
            if self.__selectionMask.size == self.__imageData.size:
                view = self.__selectionMask[:]
                view = view.reshape(*self.__imageData.shape)
                self.__selectionMask = view
            else:
                # reset selection mask
                self.__selectionMask = None
                _logger.info("Resetting incompatible mask")
        if self.colormapDialog is not None:
            goodData = self.__imageData[numpy.isfinite(self.__imageData)]
            minData = goodData.min()
            maxData = goodData.max()
            if self.colormapDialog.autoscale:
                self.colormapDialog.setDisplayedMinValue(minData)
                self.colormapDialog.setDisplayedMaxValue(maxData)
            self.colormapDialog.setDataMinMax(minData, maxData, update=True)
        else:
            self.plotImage(update = True)
            self.graphWidget._zoomReset(replot=True)

    def getImageData(self):
        return self.__imageData

    def getQImage(self):
        return self.__image

    def setQImage(self, qimage, width, height, clearmask=False, data=None):
        #This is just to get it different than None
        if (qimage.width() != width) or (qimage.height() != height):
            if 1 or (qimage.width() > width) or (qimage.height() > height):
                transformation = qt.Qt.SmoothTransformation
            else:
                transformation = qt.Qt.FastTransformation
            self.__image = qimage.scaled(qt.QSize(width, height),
                                     qt.Qt.IgnoreAspectRatio,
                                     transformation)
        else:
            self.__image = qimage

        if self.__image.format() == qt.QImage.Format_Indexed8:
            pixmap0 = numpy.frombuffer(qimage.bits().asstring(width * height),
                                       dtype=numpy.uint8)
            pixmap = numpy.zeros((height * width, 4), numpy.uint8)
            pixmap[:, 0] = pixmap0[:]
            pixmap[:, 1] = pixmap0[:]
            pixmap[:, 2] = pixmap0[:]
            pixmap[:, 3] = 255
            pixmap = pixmap.reshape(height, width, 4)
        else:
            self.__image = self.__image.convertToFormat(qt.QImage.Format_ARGB32)
            pixmap0 = numpy.frombuffer(self.__image.bits().asstring(width * height * 4),
                                       dtype=numpy.uint8)
            pixmap = numpy.array(pixmap0, copy=True)
            pixmap = pixmap.reshape(height, width, -1)
            # Qt uses BGRA, convert to RGBA
            tmpBuffer = numpy.array(pixmap[:, :, 0],
                                    copy=True, dtype=pixmap.dtype)
            pixmap[:, :, 0] = pixmap[:, :, 2]
            pixmap[:, :, 2] = tmpBuffer

        if data is None:
            self.__imageData = numpy.zeros((height, width), numpy.float64)
            self.__imageData = pixmap[:,:,0] * 0.299 +\
                               pixmap[:,:,1] * 0.587 +\
                               pixmap[:,:,2] * 0.114
        else:
            self.__imageData = data
            self.__imageData = self.__imageData.reshape(height, width)
        self._xScale = None
        self._yScale = None
        self.__pixmap0 = pixmap
        if clearmask:
            self.__selectionMask = None
        self.plotImage(update = True)
        self.graphWidget._zoomReset(replot=True)

    def plotImage(self, update=True):
        if self.__imageData is None:
            self.graphWidget.graph.clear()
            return

        if update:
            self.getPixmapFromData()
            self.__pixmap0 = self.__pixmap.copy()
        self.__applyMaskToImage()

        # replot=False as it triggers a zoom reset in Plot.py
        self.graphWidget.graph.addImage(self.__pixmap,
                                        "image",
                                        xScale=self._xScale,
                                        yScale=self._yScale,
                                        replot=False)
        self.graphWidget.graph.replot()
        self.updateProfileSelectionWindow()

    def getPixmapFromData(self):
        colormap = self.colormap
        if self.__image is not None:
            self.__pixmap = self.__pixmap0.copy()
            return

        if hasattr(self.__imageData, 'mask'):
            data = self.__imageData.data
        else:
            data = self.__imageData

        finiteData = numpy.isfinite(data)
        goodData = finiteData.min()

        if self.colormapDialog is not None:
            minData = self.colormapDialog.dataMin
            maxData = self.colormapDialog.dataMax
        else:
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
        if colormap is None:
            if minData is None:
                (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                1,
                                (0, 1),
                                (0, 255), 1)
            else:
                (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                0,
                                (minData,maxData),
                                (0, 255), 1)
        else:
            if len(colormap) < 7:
                colormap.append(spslut.LINEAR)
            if goodData:
                (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                colormap[1],
                                (colormap[2],colormap[3]),
                                (0,255), 1)
            elif colormap[1]:
                #autoscale
                if minData is None:
                    (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                1,
                                (0, 1),
                                (0, 255), 1)
                else:
                    (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                0,
                                (minData,maxData),
                                (0,255), 1)
            else:
                (self.__pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                colormap[1],
                                (colormap[2],colormap[3]),
                                (0,255), 1)

        self.__pixmap = self.__pixmap.reshape(data.shape[0], data.shape[1], 4)
        if not goodData:
            self.__pixmap[finiteData < 1] = 255
        return self.__pixmap

    def getPixmap(self, original=True):
        if original:
            if self.__pixmap0 is None:
                return self.__pixmap
            else:
                return self.__pixmap0
        else:
            # in this case also the mask may been applied
            return self.__pixmap

    def tagRoi(self, intValue):
        #get current ROI tag
        oldTag = self._roiTags[self._nRoi - 1]
        newTag = intValue
        if oldTag != newTag:
            self._roiTags[self._roiTags.index(intValue)] = oldTag
            self._roiTags[self._nRoi - 1] = newTag
            if self.__selectionMask is not None:
                mem0 = (self.__selectionMask ==  oldTag)
                mem1 = (self.__selectionMask ==  newTag)
                self.__selectionMask[mem0] = newTag
                self.__selectionMask[mem1] = oldTag
        self.plotImage(update=False)

    def setActiveRoiNumber(self, intValue):
        self._nRoi = intValue
        if 0:
            self.tagRoi(self._roiTags[intValue-1])
        else:
            self.plotImage(update=False)

    def __applyMaskToImageOLD(self):
        """
        Method kept for reference till the new one is fully tested
        """
        if self.__selectionMask is None:
            return
        #if not self.__selectionFlag:
        #    print("Return because of selection flag")
        #    return
        if self._maxNRois < 2:
            alteration = (1 - (0.2 * self.__selectionMask))
        else:
            alteration = (1 - (0.2 * (self.__selectionMask > 0))) - \
                         0.1 * (self.__selectionMask == self._nRoi)
        if self.colormap is None:
            if self.__image is not None:
                if self.__image.format() == qt.QImage.Format_ARGB32:
                    for i in range(4):
                        self.__pixmap[:,:,i]  = (self.__pixmap0[:,:,i] *\
                                alteration).astype(numpy.uint8)
                else:
                    self.__pixmap = self.__pixmap0.copy()
                    self.__pixmap[self.__selectionMask>0,0]    = 0x40
                    self.__pixmap[self.__selectionMask>0,2]    = 0x70
                    self.__pixmap[self.__selectionMask>0,3]    = 0x40
            else:
                if self.__defaultColormap > 1:
                    for i in range(3):
                        self.__pixmap[:,:,i]  = (self.__pixmap0[:,:,i] *\
                                alteration)
                    if 0:
                        #this is to recolor non finite points
                        tmpMask = numpy.isfinite(self.__imageData)
                        goodData = numpy.isfinite(self.__imageData).min()
                        if not goodData:
                            for i in range(3):
                                self.__pixmap[:,:,i] *= tmpMask
                else:
                    self.__pixmap = self.__pixmap0.copy()
                    self.__pixmap[self.__selectionMask>0,0]    = 0x40
                    self.__pixmap[self.__selectionMask>0,2]    = 0x70
                    self.__pixmap[self.__selectionMask>0,3]    = 0x40
                    if 0:
                        #this is to recolor non finite points
                        tmpMask = ~numpy.isfinite(self.__imageData)
                        badData = numpy.isfinite(self.__imageData).max()
                        if badData:
                            self.__pixmap[tmpMask,0]    = 0x00
                            self.__pixmap[tmpMask,1]    = 0xff
                            self.__pixmap[tmpMask,2]    = 0xff
                            self.__pixmap[tmpMask,3]    = 0xff
        elif int(str(self.colormap[0])) > 1:     #color
            tmp = 1 - 0.2 * self.__selectionMask
            for i in range(3):
                self.__pixmap[:,:,i]  = (self.__pixmap0[:,:,i] *\
                        tmp)
            if 0:
                tmpMask = numpy.isfinite(self.__imageData)
                goodData = numpy.isfinite(self.__imageData).min()
                if not goodData:
                    if not goodData:
                        for i in range(3):
                            self.__pixmap[:,:,i] *= tmpMask
        else:
            self.__pixmap = self.__pixmap0.copy()
            tmp  = 1 - self.__selectionMask
            self.__pixmap[:,:, 2] = (0x70 * self.__selectionMask) +\
                                  tmp * self.__pixmap0[:,:,2]
            self.__pixmap[:,:, 3] = (0x40 * self.__selectionMask) +\
                                  tmp * self.__pixmap0[:,:,3]
            if 0:
                tmpMask = ~numpy.isfinite(self.__imageData)
                badData = numpy.isfinite(self.__imageData).max()
                if badData:
                    self.__pixmap[tmpMask,0]    = 0x00
                    self.__pixmap[tmpMask,1]    = 0xff
                    self.__pixmap[tmpMask,2]    = 0xff
                    self.__pixmap[tmpMask,3]    = 0xff
        return

    def __applyMaskToImage(self):
        if self.__selectionMask is None:
            self.__selectionMask = numpy.zeros(self.__imageData.shape,
                                               numpy.uint8)
        #if not self.__selectionFlag:
        #    print("Return because of selection flag")
        #    return
        if self._selectionColors is not None:
            self.__pixmap = self.__pixmap0.copy()
            for i in range(1, self._maxNRois + 1):
                color = self._selectionColors[i - 1].copy()
                self.__pixmap[self.__selectionMask == i] = color
            return
        if self._maxNRois < 2:
            alteration = (1 - (0.3 * (self.__selectionMask > 0)))
        else:
            alteration = (1 - (0.2 * (self.__selectionMask > 0))) - \
                         0.1 * (self.__selectionMask == self._roiTags[self._nRoi - 1])
        if self.colormap is None:
            _logger.debug("Colormap is None")
            if self.__image is not None:
                if self.__image.format() == qt.QImage.Format_ARGB32:
                    _logger.debug("__applyMaskToImage CASE 1")
                    for i in range(4):
                        self.__pixmap[:,:,i]  = (self.__pixmap0[:,:,i] *\
                                alteration).astype(numpy.uint8)
                else:
                    _logger.debug("__applyMaskToImage CASE 2")
                    self.__pixmap = self.__pixmap0.copy()
                    tmp = self.__selectionMask > 0
                    self.__pixmap[tmp, 0] = 0x40
                    self.__pixmap[tmp, 2] = 0x70
                    self.__pixmap[tmp, 3] = 0x40
                    if self._maxNRois > 1:
                        roiTag = (self.__selectionMask == self._roiTags[self._nRoi - 1])
                        self.__pixmap[roiTag, 0] = 2*0x40
                        self.__pixmap[roiTag, 2] = 2*0x70
                        self.__pixmap[roiTag, 3] = 2*0x40
            else:
                if self.__defaultColormap > 1:
                    _logger.debug("__applyMaskToImage CASE 3")
                    self.__pixmap = self.__pixmap0.copy()
                    for i in range(3):
                        self.__pixmap[:,:,i]  = (self.__pixmap0[:,:,i] *\
                                                     alteration)
                    if 0:
                        #this is to recolor non finite points
                        tmpMask = numpy.isfinite(self.__imageData)
                        goodData = numpy.isfinite(self.__imageData).min()
                        if not goodData:
                            for i in range(3):
                                self.__pixmap[:,:,i] *= tmpMask
                else:
                    _logger.debug("__applyMaskToImage CASE 4")
                    self.__pixmap = self.__pixmap0.copy()
                    self.__pixmap[self.__selectionMask>0,0]    = 0x40
                    self.__pixmap[self.__selectionMask>0,2]    = 0x70
                    self.__pixmap[self.__selectionMask>0,3]    = 0x40
                    if self._maxNRois > 1:
                        self.__pixmap[self.__selectionMask==self._nRoi,0]    = 2*0x40
                        self.__pixmap[self.__selectionMask==self._nRoi,2]    = 2*0x70
                        self.__pixmap[self.__selectionMask==self._nRoi,3]    = 2*0x40

                    if 0:
                        #this is to recolor non finite points
                        tmpMask = ~numpy.isfinite(self.__imageData)
                        badData = numpy.isfinite(self.__imageData).max()
                        if badData:
                            self.__pixmap[tmpMask,0]    = 0x00
                            self.__pixmap[tmpMask,1]    = 0xff
                            self.__pixmap[tmpMask,2]    = 0xff
                            self.__pixmap[tmpMask,3]    = 0xff
        elif int(str(self.colormap[0])) > 1:     #color
            _logger.debug("__applyMaskToImage CASE 5")
            # default color should be black, pink or green
            if int(str(self.colormap[0])) == 2:
                # expected to be temp, use black
                color = [0x00, 0x00, 0x00, 0xff]
            elif int(str(self.colormap[0])) == 3:
                # expected to be red, use green
                color = [0x00, 0xff, 0x00, 0xff]
            elif int(str(self.colormap[0])) == 4:
                # expected to be green, use pink
                color = [0xff, 0x66, 0xff, 0xff]
            elif int(str(self.colormap[0])) == 5:
                # expected to be blue, use yellow
                color = [0xff, 0xff, 0x00, 0xff]
            else:
                color = [0x00, 0x00, 0x00, 0xff]

            for i in range(3):
                self.__pixmap[:,:,i] = (self.__pixmap0[:,:,i] * alteration) + \
                                       (1 - alteration) * color[i]
            if 0:
                tmpMask = numpy.isfinite(self.__imageData)
                goodData = numpy.isfinite(self.__imageData).min()
                if not goodData:
                    if not goodData:
                        for i in range(3):
                            self.__pixmap[:,:,i] *= tmpMask
        elif self._maxNRois > 1:
            _logger.debug("__applyMaskToImage CASE 6")
            tmp  = 1 - (self.__selectionMask>0)
            tmp2 = (self.__selectionMask == self._roiTags[self._nRoi - 1])
            self.__pixmap[:, :, 2] = (0x70 * (self.__selectionMask>0) + \
                                      0x70 * tmp2) +\
                                      tmp * self.__pixmap0[:,:,2]
            self.__pixmap[:,:, 3] = (0x40 * (self.__selectionMask>0)   + 0x40 * tmp2) +\
                                      tmp * self.__pixmap0[:,:,3]
        else:
            _logger.debug("__applyMaskToImage CASE 7")
            color = numpy.array([0xff, 0x66, 0xff, 0xff], dtype=numpy.uint8)
            for i in range(3):
                self.__pixmap[:,:,i] = (self.__pixmap0[:,:,i] * alteration) +\
                            (1 - alteration) * color[i]
            if 0:
                tmpMask = ~numpy.isfinite(self.__imageData)
                badData = numpy.isfinite(self.__imageData).max()
                if badData:
                    self.__pixmap[tmpMask,0]    = 0x00
                    self.__pixmap[tmpMask,1]    = 0xff
                    self.__pixmap[tmpMask,2]    = 0xff
                    self.__pixmap[tmpMask,3]    = 0xff
        return

    def selectColormap(self):
        if self.__imageData is None:
            return
        if self.colormapDialog is None:
            self.__initColormapDialog()
            if self.colormapDialog is None:
                return
        if self.colormapDialog.isHidden():
            self.colormapDialog.show()
        self.colormapDialog.raise_()
        self.colormapDialog.show()

    def __initColormapDialog(self):
        goodData = self.__imageData[numpy.isfinite(self.__imageData)]
        if goodData.size > 0:
            maxData = goodData.max()
            minData = goodData.min()
        else:
            qt.QMessageBox.critical(self,"No Data",
                "Image data does not contain any real value")
            return
        self.colormapDialog = ColormapDialog.ColormapDialog(self)
        self.colormapDialog.show()
        colormapIndex = self.__defaultColormap
        if colormapIndex == 1:
            colormapIndex = 0
        elif colormapIndex == 6:
            colormapIndex = 1
        self.colormapDialog.colormapIndex  = colormapIndex
        self.colormapDialog.colormapString = self.colormapDialog.colormapList[colormapIndex]
        self.colormapDialog.setDataMinMax(minData, maxData)
        self.colormapDialog.setAutoscale(1)
        self.colormapDialog.setColormap(self.colormapDialog.colormapIndex)
        self.colormapDialog.setColormapType(self.__defaultColormapType, update=False)
        self.colormap = (self.colormapDialog.colormapIndex,
                              self.colormapDialog.autoscale,
                              self.colormapDialog.minValue,
                              self.colormapDialog.maxValue,
                              minData, maxData)
        self.colormapDialog.setWindowTitle("Colormap Dialog")
        self.colormapDialog.sigColormapChanged.connect(self.updateColormap)
        self.colormapDialog._update()

    def updateColormap(self, *var):
        if len(var) == 1:
            var = var[0]
        if len(var) > 6:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5],
                             var[6]]
        elif len(var) > 5:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5]]
        else:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5]]
        self.plotImage(True)

    def _addImageClicked(self):
        ddict = {}
        ddict['event'] = "addImageClicked"
        ddict['image'] = self.__imageData
        ddict['title'] = self.getGraphTitle()
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def _addAllImageClicked(self):
        ddict = {}
        ddict['event'] = "addAllClicked"
        ddict['image'] = self.__imageData
        ddict['title'] = self.getGraphTitle()
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def _removeImageClicked(self):
        ddict = {}
        ddict['event'] = "removeImageClicked"
        ddict['title'] = self.getGraphTitle()
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def _replaceImageClicked(self):
        ddict = {}
        ddict['event'] = "replaceImageClicked"
        ddict['image'] = self.__imageData
        ddict['title'] = self.getGraphTitle()
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def _saveToolButtonSignal(self):
        self._saveMenu.exec(self.cursor().pos())

    def _saveMatplotlibImage(self):
        imageData = self.__imageData
        if self._matplotlibSaveImage is None:
            self._matplotlibSaveImage = QPyMcaMatplotlibSave.SaveImageSetup(None,
                                                            image=None)
        title = "Matplotlib " + self.getGraphTitle()
        self._matplotlibSaveImage.setWindowTitle(title)
        ddict = self._matplotlibSaveImage.getParameters()
        if self.colormap is not None:
            colormapType = ddict['linlogcolormap']
            try:
                colormapIndex, autoscale, vmin, vmax,\
                        dataMin, dataMax, colormapType = self.colormap
                if colormapType == spslut.LOG:
                    colormapType = 'logarithmic'
                else:
                    colormapType = 'linear'
            except Exception:
                colormapIndex, autoscale, vmin, vmax = self.colormap[0:4]
            ddict['linlogcolormap'] = colormapType
            if not autoscale:
                ddict['valuemin'] = vmin
                ddict['valuemax'] = vmax
            else:
                ddict['valuemin'] = 0
                ddict['valuemax'] = 0

        #this sets the actual dimensions
        if self._xScale is not None:
            ddict['xorigin'] = self._xScale[0]
            ddict['xpixelsize'] = self._xScale[1]

        if self._yScale is not None:
            ddict['yorigin'] = self._yScale[0]
            ddict['ypixelsize'] = self._yScale[1]
        ddict['xlabel'] = self.getXLabel()
        ddict['ylabel'] = self.getYLabel()
        limits = self.graphWidget.graph.getGraphXLimits()
        ddict['zoomxmin'] = limits[0]
        ddict['zoomxmax'] = limits[1]
        limits = self.graphWidget.graph.getGraphYLimits()
        ddict['zoomymin'] = limits[0]
        ddict['zoomymax'] = limits[1]

        self._matplotlibSaveImage.setParameters(ddict)
        self._matplotlibSaveImage.setImageData(imageData)
        self._matplotlibSaveImage.show()
        self._matplotlibSaveImage.raise_()

    def _otherWidgetGraphSignal(self, ddict):
        self._graphSignal(ddict, ownsignal = False)

    def _handlePolygonMask(self, ddict):
        if self._xScale is None:
            self._xScale = [0, 1]
        if self._yScale is None:
            self._yScale = [0, 1]

        # this is when we have __imageData
        if self.__imageData is not None:
            imageShape = self.__imageData.shape
        elif self.__pixmap0 is not None:
            imageShape = self.__pixmap0.shape[0:2]
        else:
            _logger.warning("Cannot handle polygon mask")
            return
        x = self._xScale[0] + self._xScale[1] * numpy.arange(imageShape[1])
        y = self._yScale[0] + self._yScale[1] * numpy.arange(imageShape[0])
        X, Y = numpy.meshgrid(x, y)
        X = numpy.ravel(X)
        Y = numpy.ravel(Y)
        Z = numpy.zeros((imageShape[1]*imageShape[0], 2))
        Z[:, 0] = X
        Z[:, 1] = Y
        X = None
        Y = None
        mask = pnpoly(ddict['points'][:-1], Z, 1)
        mask = mask.reshape(*imageShape)
        if self.__selectionMask is None:
            self.__selectionMask = mask
        else:
            self.__selectionMask[mask==1] = self._roiTags[self._nRoi - 1]
        self.plotImage(update = False)
        #inform the other widgets
        self._emitMaskChangedSignal()

    def _graphSignal(self, ddict, ownsignal = None):
        if ownsignal is None:
            ownsignal = True
        emitsignal = False
        if self.__imageData is None:
            if ddict['event'] == "drawingFinished":
                label = ddict['parameters']['label']
                shape = ddict['parameters']['shape']
                if shape == "polygon":
                    return self._handlePolygonMask(ddict)
            return
        if ddict['event'] == "drawingFinished":
            # TODO: when drawing a shape, set a legend to it in order
            # to identify it.
            # In the mean time, assume nobody else is triggering drawing
            # and therefore only rectangle is supported as selection
            label = ddict['parameters']['label']
            shape = ddict['parameters']['shape']
            if label is None:
                #not this module business
                return
            elif not label.startswith('mask'):
                # is it a profile selection
                return
            elif shape == "polygon":
                return self._handlePolygonMask(ddict)
            else:
                # rectangle
                pass

            j1, i1 = convertToRowAndColumn(ddict['x'], ddict['y'], self.__imageData.shape,
                                                  xScale=self._xScale,
                                                  yScale=self._yScale,
                                                  safe=True)
            w = ddict['width']
            h = ddict['height']

            j2, i2 = convertToRowAndColumn(ddict['x'] + w,
                                                  ddict['y'] + h,
                                                  self.__imageData.shape,
                                                  xScale=self._xScale,
                                                  yScale=self._yScale,
                                                  safe=True)
            if i1 == i2:
                i2 += 1
            elif (ddict['x'] + w) < self.__imageData.shape[1]:
                i2 += 1
            if j1 == j2:
                j2 += 1
            elif (ddict['y'] + h) < self.__imageData.shape[0]:
                j2 += 1
            if self.__selectionMask is None:
                self.__selectionMask = numpy.zeros(self.__imageData.shape,
                                 numpy.uint8)
            if self.__eraseMode:
                self.__selectionMask[j1:j2, i1:i2] = 0
            else:
                self.__selectionMask[j1:j2, i1:i2] = self._roiTags[self._nRoi - 1]
            emitsignal = True

        elif ddict['event'] in ["mouseMoved", "MouseAt", "mouseClicked"]:
            if ownsignal:
                pass
            if None in [ddict['x'], ddict['y']]:
                _logger.debug("Signal from outside region %s", ddict)
                return

            if self.graphWidget.infoWidget.isHidden() or self.__brushMode:
                row, column = convertToRowAndColumn(ddict['x'], ddict['y'], self.__imageData.shape,
                                                      xScale=self._xScale,
                                                      yScale=self._yScale,
                                                      safe=True)

                halfWidth = 0.5 * self.__brushWidth   #in (row, column) units
                halfHeight = 0.5 * self.__brushWidth  #in (row, column) units
                shape = self.__imageData.shape

                columnMin = max(column - halfWidth, 0)
                columnMax = min(column + halfWidth, shape[1])

                rowMin = max(row - halfHeight, 0)
                rowMax = min(row + halfHeight, shape[0])

                rowMin = min(int(round(rowMin)), shape[0] - 1)
                rowMax = min(int(round(rowMax)), shape[0])
                columnMin = min(int(round(columnMin)), shape[1] - 1)
                columnMax = min(int(round(columnMax)), shape[1])

                if rowMin == rowMax:
                    rowMax = rowMin + 1
                elif (rowMax - rowMin) > self.__brushWidth:
                    # python 3 implements banker's rounding
                    # test case ddict['x'] = 23.3 gives:
                    # i1 = 22 and i2 = 24 in python 3
                    # i1 = 23 and i2 = 24 in python 2
                    rowMin = rowMax - self.__brushWidth

                if columnMin == columnMax:
                    columnMax = columnMin + 1
                elif (columnMax - columnMin) > self.__brushWidth:
                    # python 3 implements banker's rounding
                    # test case ddict['x'] = 23.3 gives:
                    # i1 = 22 and i2 = 24 in python 3
                    # i1 = 23 and i2 = 24 in python 2
                    columnMin = columnMax - self.__brushWidth

                #To show array coordinates:
                #x = self._xScale[0] + columnMin * self._xScale[1]
                #y = self._yScale[0] + rowMin * self._yScale[1]
                #self.setMouseText("%g, %g, %g" % (x, y, self.__imageData[rowMin, columnMin]))
                #To show row and column:
                #self.setMouseText("%g, %g, %g" % (row, column, self.__imageData[rowMin, columnMin]))
                #To show mouse coordinates:
                #self.setMouseText("%g, %g, %g" % (ddict['x'], ddict['y'], self.__imageData[rowMin, columnMin]))
                if self._xScale is not None:
                    x = self._xScale[0] + column * self._xScale[1]
                    y = self._yScale[0] + row * self._yScale[1]
                else:
                    x = column
                    y = row
                self.setMouseText("%g, %g, %g" % (x, y, self.__imageData[row, column]))

            if self.__brushMode:
                if self.graphWidget.graph.isZoomModeEnabled():
                    return
                if ddict['button'] != "left":
                    return
                if self.__selectionMask is None:
                    self.__selectionMask = numpy.zeros(self.__imageData.shape,
                                     numpy.uint8)
                if self.__eraseMode:
                    self.__selectionMask[rowMin:rowMax, columnMin:columnMax] = 0
                else:
                    self.__selectionMask[rowMin:rowMax, columnMin:columnMax] = self._roiTags[self._nRoi - 1]
                emitsignal = True
        if emitsignal:
            #should this be made by the parent?
            self.plotImage(update = False)

            #inform the other widgets
            self._emitMaskChangedSignal()

    def _emitMaskChangedSignal(self):
        #inform the other widgets
        ddict = {}
        ddict['event'] = "selectionMaskChanged"
        ddict['current'] = self.__selectionMask * 1
        ddict['id'] = id(self)
        self.emitMaskImageSignal(ddict)

    def emitMaskImageSignal(self, ddict):
        #qt.QObject.emit(self,
        #            qt.SIGNAL('MaskImageWidgetSignal'),
        #            ddict)
        self.sigMaskImageWidgetSignal.emit(ddict)

    def _zoomResetSignal(self):
        _logger.debug("_zoomResetSignal")
        self.graphWidget._zoomReset(replot=False)
        self.plotImage(True)

    def getOutputFileName(self):
        initdir = PyMcaDirs.outputDir
        if self.outputDir is not None:
            if os.path.exists(self.outputDir):
                initdir = self.outputDir
        formatlist = ["TIFF Files *.tif",
                      "ASCII Files *.dat",
                      "EDF Files *.edf",
                      'CSV(, separated) Files *.csv',
                      'CSV(; separated) Files *.csv',
                      'CSV(tab separated) Files *.csv']
        if self._saveFilter in [None, ""]:
            self._saveFilter = formatlist[0]
        filelist, self._saveFilter = PyMcaFileDialogs.getFileList(parent=self,
                        filetypelist=formatlist,
                        message="Provide output file name", currentdir=initdir,
                        mode="SAVE",
                        getfilter=True,
                        single=False, currentfilter=None, native=None)
        if not len(filelist):
            return ""
        filename = filelist[0]
        if len(filename):
            self.outputDir = os.path.dirname(filename)
            filterused = "." + self._saveFilter[-3:]
            PyMcaDirs.outputDir = os.path.dirname(filename)
            if len(filename) < 4:
                filename = filename + filterused
            elif filename[-4:] != filterused :
                filename = filename + filterused
        return filename

    def saveImageList(self, filename=None, imagelist=None, labels=None):
        imageList = []
        if labels is None:
            labels = []
        if imagelist is None:
            if self.__imageData is not None:
                imageList.append(self.__imageData)
                label = self.getGraphTitle()
                label.replace(' ', '_')
                labels.append(label)
                if self.__selectionMask is not None:
                    if self.__selectionMask.max() > 0:
                        imageList.append(self.__selectionMask)
                        labels.append(label+"_Mask")
        else:
            imageList = imagelist
            if len(labels) == 0:
                for i in range(len(imagelist)):
                    labels.append("Image%02d" % i)

        if not len(imageList):
            qt.QMessageBox.information(self,"No Data",
                            "Image list is empty.\nNothing to be saved")
            return
        if filename is None:
            filename = self.getOutputFileName()
            if not len(filename):
                return

        if filename.lower().endswith(".edf"):
            ArraySave.save2DArrayListAsEDF(imageList, filename, labels)
        elif filename.lower().endswith(".tif"):
            ArraySave.save2DArrayListAsMonochromaticTiff(imageList,
                                                         filename,
                                                         labels)
        elif filename.lower().endswith(".csv"):
            if "," in self._saveFilter:
                csvseparator = ","
            elif ";" in self._saveFilter:
                csvseparator = ";"
            else:
                csvseparator = "\t"
            ArraySave.save2DArrayListAsASCII(imageList, filename, labels,
                                             csv=True,
                                             csvseparator=csvseparator)
        else:
            ArraySave.save2DArrayListAsASCII(imageList, filename, labels,
                                             csv=False)


    def saveClippedSeenImageList(self):
        return self.saveClippedAndSubtractedSeenImageList(subtract=False)


    def saveClippedAndSubtractedSeenImageList(self, subtract=True):
        imageData = self.__imageData
        if imageData is None:
            return
        vmin = None
        label = self.getGraphTitle()
        if not len(label):
            label = "Image01"
        if self.colormap is not None:
            colormapIndex, autoscale, vmin, vmax = self.colormap[0:4]
            if not autoscale:
                imageData = imageData.clip(vmin, vmax)
                label += ".clip(%f,%f)" % (vmin, vmax)
        if subtract:
            if vmin is None:
                vmin = imageData.min()
            imageData = imageData-vmin
            label += "-%f" % vmin
        imageList = [imageData]
        labelList = [label]
        if self.__selectionMask is not None:
            if self.__selectionMask.max() > 0:
                imageList.append(self.__selectionMask)
                labelList.append(label+"_Mask")
        self.saveImageList(filename=None,
                           imagelist=imageList,
                           labels=labelList)

    def setDefaultColormap(self, colormapindex, logflag=False):
        self.__defaultColormap = COLORMAPLIST[min(colormapindex, len(COLORMAPLIST)-1)]
        if logflag:
            self.__defaultColormapType = spslut.LOG
        else:
            self.__defaultColormapType = spslut.LINEAR

    def closeEvent(self, event):
        if self._profileSelectionWindow is not None:
            self._profileSelectionWindow.close()
        if self.colormapDialog is not None:
            self.colormapDialog.close()
        return qt.QWidget.closeEvent(self, event)

    def setInfoText(self, text):
        return self.graphWidget.setInfoText(text)

    def setMouseText(self, text=""):
        return self.graphWidget.setMouseText(text)

class MaskImageDialog(qt.QDialog):
    def __init__(self, parent=None, image=None, mask=None):
        super(MaskImageDialog, self).__init__(parent)
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.maskWidget = MaskImageWidget(self, aspect=True)
        buttonBox = qt.QWidget(self)
        buttonBoxLayout = qt.QHBoxLayout(buttonBox)
        buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        buttonBoxLayout.setSpacing(0)
        self.okButton = qt.QPushButton(buttonBox)
        self.okButton.setText("OK")
        self.okButton.setAutoDefault(False)
        self.cancelButton = qt.QPushButton(buttonBox)
        self.cancelButton.setText("Cancel")
        self.cancelButton.setAutoDefault(False)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        #buttonBoxLayout.addWidget(qt.HorizontalSpacer(self))
        buttonBoxLayout.addWidget(self.okButton)
        buttonBoxLayout.addWidget(self.cancelButton)
        #buttonBoxLayout.addWidget(qt.HorizontalSpacer(self))
        layout.addWidget(self.maskWidget)
        layout.addWidget(buttonBox)
        self.setImage = self.maskWidget.setImageData
        self.setMask = self.maskWidget.setSelectionMask
        self.getMask = self.maskWidget.getSelectionMask
        if image is not None:
            self.setImage(image)
        if mask is not None:
            self.setMask(mask)

def getImageMask(image, mask=None):
    """
    Functional interface to interactively define a mask
    """
    w = MaskImageDialog(image=image, mask=mask)
    ret = w.exec()
    if ret:
        mask = w.getMask()
    w = None
    del(w)
    return mask


def main(args):
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    if args.filename:
        container = MaskImageWidget(backend=args.backend,
                                    selection=True,
                                    aspect=True,
                                    imageicons=True,
                                    profileselection=True,
                                    maxNRois=2)

        if args.filename.endswith('edf') or\
           args.filename.endswith('cbf') or\
           args.filename.endswith('ccd') or\
           args.filename.endswith('spe') or\
           args.filename.endswith('tif') or\
           args.filename.endswith('tiff'):
            from PyMca5.PyMcaIO import EdfFile
            edf = EdfFile.EdfFile(sys.argv[1])
            data = edf.GetData(0)
            container.setImageData(data)

        else:

            image = qt.QImage(args.filename)
            #container.setQImage(image, image.width(),image.height())
            container.setQImage(image, 200, 200)

    else:
        container = MaskImageWidget(backend=args.backend,
                                    aspect=True,
                                    profileselection=True,
                                    maxNRois=2)
        # show how to use user specified colors for the mask
        # without using any blitting (for the time being)
        # in the future it could be made using the alpha channel
        if 0:
            colors = numpy.zeros((2, 4), dtype=numpy.uint8)
            colors[0,0] = 255
            colors[0,1] = 0
            colors[0,2] = 0
            colors[0,3] = 255
            colors[1,0] = 0
            colors[1,1] = 0
            colors[1,2] = 255
            colors[1,3] = 255
            container.setSelectionColors(colors)
        data = numpy.arange(400 * 400).astype(numpy.int32)
        data = data.reshape(200, 800)
        #data = numpy.eye(200)
        container.setImageData(data, xScale=(1000.0, 1.0), yScale=(1000., 1.))
        mask = (data*0).astype(numpy.uint8)
        n, m = data.shape
        mask[ n//4 : n//4 + n//8, m//4 : m//4 + m//8] = 1
        mask[ 3*n//4 : 3*n//4 + n//8, m//4 : m//4 + m//8] = 2
        container.setSelectionMask(mask, plot=True)
        #data.shape = 100, 400
        #container.setImageData(None)
        #container.setImageData(data)

    container.show()
    def theSlot(ddict):
        print(ddict['event'])

    container.sigMaskImageWidgetSignal.connect(theSlot)

    # Auto-close Qt for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    exit_code = app.exec()

    print(container.getSelectionMask())
    return exit_code


def build_parser():
    parser = CliUtils.create_parser(
        description="PyMca image mask authoring tool.", add_qt_options=True, add_backend_options=True
    )

    parser.add_argument('filename', default='', nargs='?',
                        help='Image filename to open')

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser())
    sys.exit(exit_code)
