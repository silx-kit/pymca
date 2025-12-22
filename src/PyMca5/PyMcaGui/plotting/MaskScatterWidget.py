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
___doc__ = """
    This module implements a scatter plot with selection capabilities.

    It is structured in three superposed layers:

    - First (deepest) layer containing the original points as they came.
    - Second layer containing the scatter plot density map.
    - Final layer containing the selected points with the selected colors.

"""
import numpy
import logging
from PyMca5.PyMcaGraph.ctools import pnpoly
_logger = logging.getLogger(__name__)

from . import PlotWindow
from . import MaskImageWidget
from . import MaskImageTools
qt = PlotWindow.qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str
IconDict = PlotWindow.IconDict

class MaskScatterWidget(PlotWindow.PlotWindow):
    sigMaskScatterWidgetSignal = qt.pyqtSignal(object)
    DEFAULT_COLORMAP_INDEX = 2
    DEFAULT_COLORMAP_LOG_FLAG = True

    def __init__(self, parent=None, backend=None, plugins=False, newplot=False,
                 control=False, position=False, maxNRois=1, grid=False,
                 logx=False, logy=False, togglePoints=False, normal=True,
                 polygon=True, colormap=True, aspect=True,
                 imageIcons=True, bins=None, **kw):
        super(MaskScatterWidget, self).__init__(parent=parent,
                                                backend=backend,
                                                plugins=plugins,
                                                newplot=newplot,
                                                control=control,
                                                position=position,
                                                grid=grid,
                                                logx=logx,
                                                logy=logy,
                                                togglePoints=togglePoints,
                                                normal=normal,
                                                aspect=aspect,
                                                colormap=colormap,
                                                imageIcons=imageIcons,
                                                polygon=polygon,
                                                **kw)
        self._buildAdditionalSelectionMenuDict()
        self._selectionCurve = None
        self._selectionMask = None
        self._selectionColors = numpy.zeros((len(self.colorList), 4), numpy.uint8)
        self._alphaLevel = None
        for i in range(len(self.colorList)):
            self._selectionColors[i, 0] = int(self.colorList[i][-2:], 16)
            self._selectionColors[i, 1] = int(self.colorList[i][3:-2], 16)
            self._selectionColors[i, 2] = int(self.colorList[i][1:3], 16)
            self._selectionColors[i, 3] = 0xff
        self._maxNRois = maxNRois
        self._nRoi = 1
        self._zoomMode = True
        self._eraseMode = False
        self._brushMode = False
        self._brushWidth = 5
        self._brushMenu = None
        self._bins = bins
        self._densityPlotWidget = None
        self._pixmap = None
        self.setPlotViewMode("scatter", bins=bins)
        self.setDrawModeEnabled(False)

    def setPlotViewMode(self, mode="scatter", bins=None):
        if mode.lower() != "density":
            self._activateScatterPlotView()
        else:
            self._activateDensityPlotView(bins)

    def _activateScatterPlotView(self):
        self._plotViewMode = "scatter"
        for key in ["colormap", "brushSelection", "brush"]:
            self.setToolBarActionVisible(key, False)
        if hasattr(self, "eraseSelectionToolButton"):
            self.eraseSelectionToolButton.setToolTip("Set erase mode if checked")
            self.eraseSelectionToolButton.setCheckable(True)
            if self._eraseMode:
                self.eraseSelectionToolButton.setChecked(True)
            else:
                self.eraseSelectionToolButton.setChecked(False)
        if hasattr(self, "polygonSelectionToolButton"):
            self.polygonSelectionToolButton.setCheckable(True)
        if hasattr(self, "rectSelectionToolButton"):
            self.rectSelectionToolButton.setCheckable(True)
        if hasattr(self, "brushSelectionToolButton"):
            if self.brushSelectionToolButton.isChecked():
                self.brushSelectionToolButton.setChecked(False)
                self._brushMode = False
                self.setZoomModeEnabled(True)
        self.clearImages()
        self._updatePlot()

    def _activateDensityPlotView(self, bins=None):
        self._plotViewMode = "density"
        for key in ["colormap", "brushSelection", "brush", "rectangle"]:
            self.setToolBarActionVisible(key, True)
        if hasattr(self, "eraseSelectionToolButton"):
            self.eraseSelectionToolButton.setCheckable(True)
        if hasattr(self, "brushSelectionToolButton"):
            self.brushSelectionToolButton.setCheckable(True)
        if hasattr(self, "polygonSelectionToolButton"):
            self.polygonSelectionToolButton.setCheckable(True)
        if hasattr(self, "rectSelectionToolButton"):
            self.rectSelectionToolButton.setCheckable(True)

        if _logger.getEffectiveLevel() == logging.DEBUG:
            if self._densityPlotWidget is None:
                self._densityPlotWidget = MaskImageWidget.MaskImageWidget(
                                imageicons=True,
                                selection=True,
                                profileselection=True,
                                aspect=True,
                                polygon=True)
                self._densityPlotWidget.sigMaskImageWidgetSignal.connect(self._densityPlotSlot)
            self._updateDensityPlot(bins)
            # only show it in debug mode
            self._densityPlotWidget.show()
        curve = self.getCurve(self._selectionCurve)
        if curve is None:
            return
        x, y, legend, info = curve[0:4]
        self.setSelectionCurveData(x, y, legend=legend, info=info)

    def getDensityData(self, bins=None):
        curve = self.getCurve(self._selectionCurve)
        if curve is None:
            return
        x, y, legend, info = curve[0:4]
        if bins is not None:
            if type(bins) == type(1):
                bins = (bins, bins)
            elif len(bins) == 0:
                bins = (bins[0], bins[0])
            else:
                bins = bins[0:2]
        elif self._bins is None:
            bins = [int(x.size / 10), int(y.size/10)]
            if bins[0] > 100:
                bins[0] = 100
            elif bins[0] < 2:
                bins[0] = 2
            if bins[1] > 100:
                bins[1] = 100
            elif bins[1] < 2:
                bins[1] = 2
        else:
            bins = self._bins
        idx = numpy.where(numpy.isfinite(x) & numpy.isfinite(y))
        x0 = x[idx].min()
        y0 = y[idx].min()
        image = numpy.histogram2d(y[idx], x[idx],
                                  bins=bins,
                                  #range=(binsY, binsX),
                                  density=False)
        self._binsX = image[2]
        self._binsY = image[1]
        self._bins = bins
        #print("shape", image[0].shape, "image max  min ", image[0].max(), image[0].min())
        #print("deltaxmin and max", (self._binsX[1:] - self._binsX[:-1]).min(),
        #      (self._binsX[1:] - self._binsX[:-1]).max())
        deltaX = (self._binsX[1:] - self._binsX[:-1]).mean()
        deltaY = (self._binsY[1:] - self._binsY[:-1]).mean()
        self._xScale = (x0, deltaX)
        self._yScale = (y0, deltaY)
        return image[0]

    def _updateDensityPlot(self, bins=None):
        _logger.debug("_updateDensityPlot called")
        if self._densityPlotWidget is None:
            return
        curve = self.getCurve(self._selectionCurve)
        if curve is None:
            return
        x, y, legend, info = curve[0:4]
        if bins is not None:
            if type(bins) == type(1):
                bins = (bins, bins)
            elif len(bins) == 0:
                bins = (bins[0], bins[0])
            else:
                bins = bins[0:2]
        elif self._bins is None:
            bins = [int(x.size/ 10), int(y.size/10)]
            if bins[0] > 100:
                bins[0] = 100
            elif bins[0] < 2:
                bins[0] = 2
            if bins[1] > 100:
                bins[1] = 100
            elif bins[1] < 2:
                bins[1] = 2
        else:
            bins = self._bins
        idx = numpy.where(numpy.isfinite(x) & numpy.isfinite(y))
        x0 = x[idx].min()
        y0 = y[idx].min()
        deltaX = (x[idx].max() - x0) / float(bins[0] - 1)
        deltaY = (y[idx].max() - y0) / float(bins[1] - 1)
        self.xScale = (x0, deltaX)
        self.yScale = (y0, deltaY)
        binsX = numpy.arange(bins[0]) * deltaX
        binsY = numpy.arange(bins[1]) * deltaY
        image = numpy.histogram2d(y[idx], x[idx], bins=(binsY, binsX), density=False)
        self._binsX = image[2]
        self._binsY = image[1]
        self._bins = bins
        if _logger.getEffectiveLevel() == logging.DEBUG:
            # this does not work properly
            # update mask levels
            if self._selectionMask is not None:
                weights = self._selectionMask[:]
                weights = weights.reshape(*x.shape)
                if self._maxNRois > 1:
                    _logger.debug("BAD PATH")
                    # this does not work properly yet
                    weightsSum = weights.sum(dtype=numpy.float64)
                    volume = (binsY[1] - binsY[0]) * (binsX[1] - binsX[0])
                    mask = numpy.round(numpy.histogram2d(y[idx], x[idx],
                                       bins=(binsY, binsX),
                                       weights=weights,
                                       density=True)[0] * weightsSum * volume).astype(numpy.uint8)
                else:
                    #print("GOOD PATH")
                    mask = numpy.histogram2d(y[idx], x[idx],
                                             bins=(binsY, binsX),
                                             weights=weights,
                                             density=False)[0]
                    mask[mask > 0] = 1
                #print(mask.min(), mask.max())
                self._densityPlotWidget.setSelectionMask(mask, plot=False)
        self._densityPlotWidget.graphWidget.graph.setGraphXLabel(self.getGraphXLabel())
        self._densityPlotWidget.graphWidget.graph.setGraphYLabel(self.getGraphYLabel())
        self._densityPlotWidget.setImageData(image[0],
                                             clearmask=False,
                                             xScale=self.xScale,
                                             yScale=self.yScale)

        # do not overlay plot (yet)
        pixmap = self._densityPlotWidget.getPixmap() * 1
        #pixmap[:, :, 3] = 128
        #self.addImage(pixmap,
        #              legend=legend+" density",
        #              xScale=(x0, deltaX), yScale=(y0, deltaY), z=10)
        self._pixmap = pixmap
        self._imageData = image[0]
        #raise NotImplemented("Density plot view not implemented yet")

    def setSelectionCurveData(self, x, y, legend=None, info=None,
                 replot=True, replace=True, linestyle=" ", color=None,
                 symbol=None, selectable=None, **kw):
        self.enableActiveCurveHandling(False)
        if legend is None:
            legend = "MaskScatterWidget"
        if symbol is None:
            if x.size < 1000:
                # circle
                symbol = "o"
            elif x.size < 1.0e5:
                # dot
                symbol = "."
            else:
                # pixel
                symbol = ","
        #if selectable is None:
        #    if symbol == ",":
        #        selectable = False
        #    else:
        #        selectable = True

        # the basic curve is drawn
        self.addCurve(x=x, y=y, legend=legend, info=info,
                      replace=replace, replot=False, linestyle=linestyle,
                      color=color, symbol=symbol, selectable=selectable,z=0,
                      **kw)
        self._selectionCurve = legend

        # if view mode, draw the image
        if self._plotViewMode == "density":
            # get the binned data
            imageData = self.getDensityData()
            # get the associated pixmap
            if self.colormapDialog is None:
                self._initColormapDialog(imageData)
            cmap = self.colormapDialog.getColormap()
            pixmap=MaskImageTools.getPixmapFromData(imageData,
                                                    colormap=cmap)
            self.addImage(imageData, legend=legend + "density",
                          xScale=self._xScale,
                          yScale=self._yScale,
                          z=0,
                          pixmap=pixmap,
                          replot=False)
            self._imageData = imageData
            self._pixmap = pixmap

        # draw the mask as a set of curves
        hasMaskedData = False
        if self._selectionMask is not None:
            if self._selectionMask.max():
                hasMaskedData = True

        if hasMaskedData or (replace==False):
            self._updatePlot(replot=False)

        # update the plot if it was requested
        if replot:
            self.replot()

        if 0 :#or self._plotViewMode == "density":
            # get the binned data
            imageData = self.getDensityData()
            # get the associated pixmap
            pixmap=MaskImageTools.getPixmapFromData(imageData)
            if 0:
                self.addImage(imageData, legend=legend + "density",
                          xScale=self._xScale,
                          yScale=self._yScale,
                          z=0,
                          pixmap=pixmap,
                          replot=True)
            if _logger.getEffectiveLevel() == logging.DEBUG:
                if self._densityPlotWidget is None:
                    self._densityPlotWidget = MaskImageWidget.MaskImageWidget(
                                    imageicons=True,
                                    selection=True,
                                    profileselection=True,
                                    aspect=True,
                                    polygon=True)
                self._updateDensityPlot()
                _logger.debug("CLOSE = %s", numpy.allclose(imageData, self._imageData))
                _logger.debug("CLOSE PIXMAP = %s", numpy.allclose(pixmap, self._pixmap))
            self._imageData = imageData
            self._pixmap = pixmap
        #self._updatePlot()

    def setSelectionMask(self, mask=None, plot=True):
        if self._selectionCurve is not None:
            selectionCurve = self.getCurve(self._selectionCurve)
        else:
            selectionCurve = None
        if selectionCurve in [[], None]:
            self._selectionCurve = None
            self._selectionMask = mask
        else:
            x, y = selectionCurve[0:2]
            x = numpy.asarray(x)
            if hasattr(mask, "size"):
                if mask.size == x.size:
                    if self._selectionMask is None:
                        self._selectionMask = mask
                    elif self._selectionMask.size == mask.size:
                        # keep shape because we may refer to images
                        tmpView = self._selectionMask[:]
                        tmpView = numpy.ravel(tmpView)
                        tmpMask = mask[:]
                        tmpMask = numpy.ravel(tmpMask)
                        tmpView[:] = tmpMask[:]
                    else:
                        self._selectionMask = mask
                else:
                    raise ValueError("Mask size = %d while data size = %d" % (mask.size, x.size))
        if plot:
            self._updatePlot()

    def getSelectionMask(self):
        if self._selectionMask is None:
            if self._selectionCurve is not None:
                x, y, legend, info = self.getCurve(self._selectionCurve)
                self._selectionMask = numpy.zeros(x.shape, numpy.uint8)
        return self._selectionMask

    def _updatePlot(self, replot=True, replace=True):
        if self._selectionCurve is None:
            return
        x0, y0, legend, info = self.getCurve(self._selectionCurve)[0:4]
        # make sure we work with views
        x = x0[:]
        y = y0[:]
        x = numpy.ravel(x)
        y = numpy.ravel(y)
        if 0:
            colors = numpy.zeros((y.size, 4), dtype=numpy.uint8)
            colors[:, 3] = 255
            if self._selectionMask is not None:
                tmpMask = self._selectionMask[:]
                tmpMask = numpy.ravel(tmpMask)
                for i in range(0, self._maxNRois + 1):
                    colors[tmpMask == i, :] = self._selectionColors[i]
                self.setSelectionCurveData(x, y, legend=legend, info=info,
                                           #color=colors,
                                           color="k",
                                           linestyle=" ",
                                           replot=replot, replace=replace)
        else:
            if self._selectionMask is None:
                for i in range(1, self._maxNRois + 1):
                    self.removeCurve(legend=legend + " %02d" % i, replot=False)
            else:
                tmpMask = self._selectionMask[:]
                tmpMask = numpy.ravel(tmpMask)
                if self._plotViewMode == "density":
                    useAlpha = True
                    if self._alphaLevel is None:
                        self._initializeAlpha()
                else:
                    useAlpha = False
                for i in range(1, self._maxNRois + 1):
                    xMask = x[tmpMask == i]
                    yMask = y[tmpMask == i]
                    if xMask.size < 1:
                        self.removeCurve(legend=legend + " %02d" % i,
                                         replot=False)
                        continue
                    color = self._selectionColors[i].copy()
                    if useAlpha:
                        if len(color) == 4:
                            if type(color[3]) in [numpy.uint8,
                                                  numpy.int32,
                                                  numpy.int64]:
                                color[3] = self._alphaLevel
                    # a copy of the input info is needed in order not
                    # to set the main curve to that color
                    self.addCurve(xMask, yMask, legend=legend + " %02d" % i,
                                  info=info.copy(), color=color, linestyle=" ",
                                  selectable=False,
                                  z=1,
                                  replot=False, replace=False)
                if replot:
                    self.replot()
                    #self.resetZoom()

    def setActiveRoiNumber(self, intValue):
        if (intValue < 0) or (intValue > self._maxNRois):
            raise ValueError("Value %d outside the interval [0, %d]" % (intValue, self._maxNRois))
        self._nRoi = intValue


    def _eraseSelectionIconSignal(self):
        if self.eraseSelectionToolButton.isChecked():
            self._eraseMode = True
        else:
            self._eraseMode = False

    def _polygonIconSignal(self):
        if self.polygonSelectionToolButton.isChecked():
            self.setPolygonSelectionMode()
        else:
            self.setZoomModeEnabled(True)

    def _rectSelectionIconSignal(self):
        _logger.debug("_rectSelectionIconSignal")
        if self.rectSelectionToolButton.isChecked():
            self.setRectangularSelectionMode()
        else:
            self.setZoomModeEnabled(True)

    def setZoomModeEnabled(self, flag, color=None):
        if color is None:
            if hasattr(self, "colormapDialog"):
                if self.colormapDialog is None:
                    color = "#00FFFF"
                else:
                    cmap = self.colormapDialog.getColormap()
                    if cmap[0] < 2:
                        color = "#00FFFF"
                    else:
                        color = "black"
        super(MaskScatterWidget, self).setZoomModeEnabled(flag, color=color)
        if flag:
            if hasattr(self,"polygonSelectionToolButton"):
                self.polygonSelectionToolButton.setChecked(False)
            if hasattr(self,"brushSelectionToolButton"):
                self.brushSelectionToolButton.setChecked(False)

    def _handlePolygonMask(self, points):
        _logger.debug("_handlePolygonMask called")
        if self._eraseMode:
            value = 0
        else:
            value = self._nRoi
        x, y, legend, info = self.getCurve(self._selectionCurve)[0:4]
        x = numpy.ravel(x)
        y = numpy.ravel(y)
        currentMask = self.getSelectionMask()
        if currentMask is None:
            currentMask = numpy.zeros(y.shape, dtype=numpy.uint8)
            if value == 0:
                return
        Z = numpy.zeros((y.size, 2), numpy.float64)
        Z[:, 0] = x
        Z[:, 1] = y
        mask = pnpoly(points, Z, 1)
        mask = mask.reshape(*currentMask.shape)
        currentMask[mask > 0] = value
        self.setSelectionMask(currentMask, plot=True)
        self._emitMaskChangedSignal()

    def graphCallback(self, ddict):
        _logger.debug("MaskScatterWidget graphCallback %s", ddict)
        if ddict["event"] == "drawingFinished":
            if ddict["parameters"]["shape"].lower() == "rectangle":
                points = numpy.zeros((5,2), dtype=ddict["points"].dtype)
                points[0] = ddict["points"][0]
                points[1, 0] = ddict["points"][0, 0]
                points[1, 1] = ddict["points"][1, 1]
                points[2] = ddict["points"][1]
                points[3, 0] = ddict["points"][1, 0]
                points[3, 1] = ddict["points"][0, 1]
                points[4] = ddict["points"][0]
                self._handlePolygonMask(points)
            else:
                self._handlePolygonMask(ddict["points"])
        elif ddict['event'] in ["mouseMoved", "MouseAt", "mouseClicked"]:
            if (self._plotViewMode == "density") and \
               (self._imageData is not None):
                shape = self._imageData.shape
                row, column = MaskImageTools.convertToRowAndColumn( \
                                                      ddict['x'],
                                                      ddict['y'],
                                                      shape,
                                                      xScale=self._xScale,
                                                      yScale=self._yScale,
                                                      safe=True)

                halfWidth = 0.5 * self._brushWidth   #in (row, column) units
                halfHeight = 0.5 * self._brushWidth  #in (row, column) units

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
                elif (rowMax - rowMin) > self._brushWidth:
                    # python 3 implements banker's rounding
                    # test case ddict['x'] = 23.3 gives:
                    # i1 = 22 and i2 = 24 in python 3
                    # i1 = 23 and i2 = 24 in python 2
                    rowMin = rowMax - self._brushWidth

                if columnMin == columnMax:
                    columnMax = columnMin + 1
                elif (columnMax - columnMin) > self._brushWidth:
                    # python 3 implements banker's rounding
                    # test case ddict['x'] = 23.3 gives:
                    # i1 = 22 and i2 = 24 in python 3
                    # i1 = 23 and i2 = 24 in python 2
                    columnMin = columnMax - self._brushWidth

                #To show array coordinates:
                #x = self._xScale[0] + columnMin * self._xScale[1]
                #y = self._yScale[0] + rowMin * self._yScale[1]
                #self.setMouseText("%g, %g, %g" % (x, y, self.__imageData[rowMin, columnMin]))
                #To show row and column:
                #self.setMouseText("%g, %g, %g" % (row, column, self.__imageData[rowMin, columnMin]))
                #To show mouse coordinates:
                #self.setMouseText("%g, %g, %g" % (ddict['x'], ddict['y'], self.__imageData[rowMin, columnMin]))
                if self._xScale is not None and self._yScale is not None:
                    x = self._xScale[0] + column * self._xScale[1]
                    y = self._yScale[0] + row * self._yScale[1]
                else:
                    x = column
                    y = row
                self.setMouseText("%g, %g, %g" % (x, y, self._imageData[row, column]))

            if self._brushMode:
                if self.isZoomModeEnabled():
                    return
                if ddict['button'] != "left":
                    return
                selectionMask = numpy.zeros(self._imageData.shape,
                                            numpy.uint8)
                if self._eraseMode:
                    selectionMask[rowMin:rowMax, columnMin:columnMax] = 1
                else:
                    selectionMask[rowMin:rowMax, columnMin:columnMax] = \
                                                                self._nRoi
                self._setSelectionMaskFromDensityMask(selectionMask,
                                                      update=True)
        #if emitsignal:
        #    #should this be made by the parent?
        #    self.plotImage(update = False)
        #
        #    #inform the other widgets
        #    self._emitMaskChangedSignal()
        # the base implementation handles ROIs, mouse position and activeCurve
        super(MaskScatterWidget, self).graphCallback(ddict)

    def _brushIconSignal(self):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            _logger.debug("brushIconSignal")
        if self._brushMenu is None:
            self._brushMenu = qt.QMenu()
            self._brushMenu.addAction(QString(" 1 Image Pixel Width"),
                                       self._setBrush1)
            self._brushMenu.addAction(QString(" 2 Image Pixel Width"),
                                       self._setBrush2)
            self._brushMenu.addAction(QString(" 3 Image Pixel Width"),
                                       self._setBrush3)
            self._brushMenu.addAction(QString(" 5 Image Pixel Width"),
                                       self._setBrush4)
            self._brushMenu.addAction(QString("10 Image Pixel Width"),
                                       self._setBrush5)
            self._brushMenu.addAction(QString("20 Image Pixel Width"),
                                       self._setBrush6)
        self._brushMenu.exec(self.cursor().pos())

    def _brushSelectionIconSignal(self):
        _logger.debug("_setBrushSelectionMode")
        if hasattr(self, "polygonSelectionToolButton"):
            self.polygonSelectionToolButton.setChecked(False)
            self.setDrawModeEnabled(False)
        if self.brushSelectionToolButton.isChecked():
            self._brushMode = True
            self.setZoomModeEnabled(False)
        else:
            self._brushMode = False
            self.setZoomModeEnabled(True)

    def _setBrush1(self):
        self._brushWidth = 1

    def _setBrush2(self):
        self._brushWidth = 2

    def _setBrush3(self):
        self._brushWidth = 3

    def _setBrush4(self):
        self._brushWidth = 5

    def _setBrush5(self):
        self._brushWidth = 10

    def _setBrush6(self):
        self._brushWidth = 20

    def setRectangularSelectionMode(self):
        """
        Resets zoom mode and enters selection mode with the current active ROI index
        """
        self._zoomMode = False
        self._brushMode = False
        color = self._selectionColors[self._nRoi]
        # make sure the selection is made with a non transparent color
        if len(color) == 4:
            if type(color[-1]) in [numpy.uint8, numpy.int8]:
                color = color.copy()
                color[-1] = 255
        self.setDrawModeEnabled(True,
                                shape="rectangle",
                                label="mask",
                                color=color)
        self.setZoomModeEnabled(False)
        if hasattr(self, "brushSelectionToolButton"):
            self.brushSelectionToolButton.setChecked(False)
        if hasattr(self,"polygonSelectionToolButton"):
            self.polygonSelectionToolButton.setChecked(False)
        if hasattr(self,"rectSelectionToolButton"):
            self.rectSelectionToolButton.setChecked(True)

    def setPolygonSelectionMode(self):
        """
        Resets zoom mode and enters selection mode with the current active ROI index
        """
        self._zoomMode = False
        self._brushMode = False
        color = self._selectionColors[self._nRoi]
        # make sure the selection is made with a non transparent color
        if len(color) == 4:
            if type(color[-1]) in [numpy.uint8, numpy.int8]:
                color = color.copy()
                color[-1] = 255
        self.setDrawModeEnabled(True, shape="polygon", label="mask",
                                color=color)
        self.setZoomModeEnabled(False)
        if hasattr(self, "brushSelectionToolButton"):
            self.brushSelectionToolButton.setChecked(False)
        if hasattr(self,"rectSelectionToolButton"):
            self.rectSelectionToolButton.setChecked(False)
        if hasattr(self,"polygonSelectionToolButton"):
            self.polygonSelectionToolButton.setChecked(True)

    def setEraseSelectionMode(self, erase=True):
        if erase:
            self._eraseMode = True
        else:
            self._eraseMode = False
        if hasattr(self, "eraseSelectionToolButton"):
            self.eraseSelectionToolButton.setCheckable(True)
            if erase:
                self.eraseSelectionToolButton.setChecked(True)
            else:
                self.eraseSelectionToolButton.setChecked(False)

    def _emitMaskChangedSignal(self):
        #inform the other widgets
        ddict = {}
        ddict['event'] = "selectionMaskChanged"
        ddict['current'] = self._selectionMask * 1
        ddict['id'] = id(self)
        self.emitMaskScatterWidgetSignal(ddict)

    def emitMaskScatterWidgetSignal(self, ddict):
        self.sigMaskScatterWidgetSignal.emit(ddict)

    def _imageIconSignal(self):
        self.__resetSelection()

    def _buildAdditionalSelectionMenuDict(self):
        self._additionalSelectionMenu = {}
        #scatter view menu
        menu = qt.QMenu()
        menu.addAction(QString("Density plot view"), self.__setDensityPlotView)
        menu.addAction(QString("Reset Selection"), self.__resetSelection)
        menu.addAction(QString("Invert Selection"), self._invertSelection)
        self._additionalSelectionMenu["scatter"] = menu

        # density view menu
        menu = qt.QMenu()
        menu.addAction(QString("Scatter plot view"), self.__setScatterPlotView)
        menu.addAction(QString("Reset Selection"), self.__resetSelection)
        menu.addAction(QString("Invert Selection"), self._invertSelection)
        menu.addAction(QString("I >= Colormap Max"), self._selectMax)
        menu.addAction(QString("Colormap Min < I < Colormap Max"),
                                                self._selectMiddle)
        menu.addAction(QString("I <= Colormap Min"), self._selectMin)
        menu.addAction(QString("Increase mask alpha"), self._increaseMaskAlpha)
        menu.addAction(QString("Decrease mask alpha"), self._decreaseMaskAlpha)
        self._additionalSelectionMenu["density"] = menu

    def __setScatterPlotView(self):
        self.setPlotViewMode(mode="scatter")

    def __setDensityPlotView(self):
        self.setPlotViewMode(mode="density")

    def _additionalIconSignal(self):
        if self._plotViewMode == "density": # and imageData is not none ...
            self._additionalSelectionMenu["density"].exec(self.cursor().pos())
        else:
            self._additionalSelectionMenu["scatter"].exec(self.cursor().pos())

    def __resetSelection(self):
        # Needed because receiving directly in _resetSelection it was passing
        # False as argument
        self._resetSelection(True)

    def _resetSelection(self, owncall=True):
        _logger.debug("_resetSelection")

        if self._selectionMask is None:
            _logger.info("Selection mask is None, doing nothing")
            return
        else:
            self._selectionMask[:] = 0

        self._updatePlot()

        #inform the others
        if owncall:
            ddict = {}
            ddict['event'] = "resetSelection"
            ddict['id'] = id(self)
            self.emitMaskScatterWidgetSignal(ddict)

    def _invertSelection(self):
        if self._selectionMask is None:
            return
        mask = numpy.ones(self._selectionMask.shape, numpy.uint8)
        mask[self._selectionMask > 0] = 0
        self.setSelectionMask(mask, plot=True)
        self._emitMaskChangedSignal()

    def _getSelectionMinMax(self):
        if self.colormap is None:
            goodData = self._imageData[numpy.isfinite(self._imageData)]
            maxValue = goodData.max()
            minValue = goodData.min()
        else:
            minValue = self.colormap[2]
            maxValue = self.colormap[3]
        return minValue, maxValue

    def _selectMax(self):
        if (self._plotViewMode != "density") or \
           (self._imageData is None):
            return

        selectionMask = numpy.zeros(self._imageData.shape, numpy.uint8)
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self._imageData, copy=True)
        tmpData[True - numpy.isfinite(self._imageData)] = minValue
        selectionMask[tmpData >= maxValue] = self._nRoi
        self._setSelectionMaskFromDensityMask(selectionMask)
        self._emitMaskChangedSignal()

    def _selectMiddle(self):
        if (self._plotViewMode != "density") or \
           (self._imageData is None):
            return
        selectionMask = numpy.zeros(self._imageData.shape, numpy.uint8)
        selectionMask[:] = self._nRoi
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self._imageData, copy=True)
        tmpData[True - numpy.isfinite(self._imageData)] = minValue
        selectionMask[tmpData >= maxValue] = 0
        selectionMask[tmpData <= minValue] = 0
        self._setSelectionMaskFromDensityMask(selectionMask)
        self._emitMaskChangedSignal()

    def _selectMin(self):
        if (self._plotViewMode != "density") or \
           (self._imageData is None):
            return
        selectionMask = numpy.zeros(self._imageData.shape, numpy.uint8)
        minValue, maxValue = self._getSelectionMinMax()
        tmpData = numpy.array(self._imageData, copy=True)
        tmpData[True - numpy.isfinite(self._imageData)] = maxValue
        selectionMask[tmpData <= minValue] = self._nRoi
        self._setSelectionMaskFromDensityMask(selectionMask)
        self._emitMaskChangedSignal()

    def _setSelectionMaskFromDensityMask(self, densityPlotMask, update=None):
        _logger.debug("_setSelectionMaskFromDensityMask called")
        curve = self.getCurve(self._selectionCurve)
        if curve is None:
            return
        x, y, legend, info = curve[0:4]
        bins = self._bins
        x0 = x.min()
        y0 = y.min()
        deltaX = (x.max() - x0)/float(bins[0])
        deltaY = (y.max() - y0)/float(bins[1])
        columns = numpy.digitize(x, self._binsX, right=True)
        columns[columns>=densityPlotMask.shape[1]] = \
                                                   densityPlotMask.shape[1] - 1
        rows = numpy.digitize(y, self._binsY, right=True)
        rows[rows>=densityPlotMask.shape[0]] = densityPlotMask.shape[0] - 1
        values = densityPlotMask[rows, columns]
        values = numpy.ravel(values)

        if self._selectionMask is None:
            view = numpy.zeros(x.size, dtype=numpy.uint8)
            view[:] = values[:]
        elif update:
            view = self._selectionMask.copy()
            if self._eraseMode:
                view[values > 0] = 0
            else:
                view[values > 0] = values[values > 0]
        else:
            view = numpy.zeros(self._selectionMask.size,
                               dtype=self._selectionMask.dtype)
            view[:] = values[:]
        if self._selectionMask is not None:
            view = view.reshape(*self._selectionMask.shape)
        self.setSelectionMask(view, plot=True)

    def _densityPlotSlot(self, ddict):
        _logger.debug("_densityPlotSlot called")
        if ddict["event"] == "resetSelection":
            self.__resetSelection()
            return
        if ddict["event"] not in ["selectionMaskChanged"]:
            return
        densityPlotMask = ddict["current"]
        curve = self.getCurve(self._selectionCurve)
        if curve is None:
            return
        x, y, legend, info = curve[0:4]
        bins = self._bins
        x0 = x.min()
        y0 = y.min()
        deltaX = (x.max() - x0)/float(bins[0])
        deltaY = (y.max() - y0)/float(bins[1])
        if _logger.getEffectiveLevel() == logging.DEBUG:
            if self._selectionMask is None:
                view = numpy.zeros(x.size, dtype=numpy.uint8)
            else:
                view = numpy.zeros(self._selectionMask.size, dtype=self._selectionMask.dtype)
            # this works even on unordered data
            for i in range(x.size):
                row = int((y[i] - y0) /deltaY)
                column = int((x[i] - x0) /deltaX)
                try:
                    value = densityPlotMask[row, column]
                except Exception:
                    if row >= densityPlotMask.shape[0]:
                        row = densityPlotMask.shape[0] - 1
                    if column >= densityPlotMask.shape[1]:
                        column = densityPlotMask.shape[1] - 1
                    value = densityPlotMask[row, column]
                if value:
                    view[i] = value
            if self._selectionMask is not None:
                view = view.reshape(*self._selectionMask.shape)
            self.setSelectionMask(view)

        if self._selectionMask is None:
            view2 = numpy.zeros(x.size, dtype=numpy.uint8)
        else:
            view2 = numpy.zeros(self._selectionMask.size, dtype=self._selectionMask.dtype)
        columns = numpy.digitize(x, self._binsX, right=True)
        columns[columns>=densityPlotMask.shape[1]] = densityPlotMask.shape[1] - 1
        rows = numpy.digitize(y, self._binsY, right=True)
        rows[rows>=densityPlotMask.shape[0]] = densityPlotMask.shape[0] - 1
        values = densityPlotMask[rows, columns]
        values = numpy.ravel(values)
        view2[:] = values[:]
        if self._selectionMask is not None:
            view2 = view2.reshape(*self._selectionMask.shape)
        if _logger.getEffectiveLevel() == logging.DEBUG:
            if not numpy.allclose(view, view2):
                a = view[:]
                b = view2[:]
                a = numpy.ravel(a)
                b = numpy.ravel(b)
                c = 0
                for i in range(a.size):
                    if a[i] != b[i]:
                        _logger.debug("%d a = %s, b = %s, (x, y) = (%s, %s)",
                                      i, a[i], b[i], x[i], y[i])
                        c += 1
                        if c > 10:
                            break
            else:
                _logger.debug("OK!!!")
        self.setSelectionMask(view2)

    def _initializeAlpha(self):
        self._alphaLevel = 128

    def _increaseMaskAlpha(self):
        if self._alphaLevel is None:
            self._initializeAlpha()
        self._alphaLevel *= 4
        if self._alphaLevel > 255:
            self._alphaLevel = 255
        self._alphaLevel
        self._updatePlot()

    def _decreaseMaskAlpha(self):
        if self._alphaLevel is None:
            self._initializeAlpha()
        self._alphaLevel /= 4
        if self._alphaLevel < 2:
            self._alphaLevel = 2
        self._updatePlot()

if __name__ == "__main__":
    backend = "matplotlib"
    #backend = "opengl"
    app = qt.QApplication([])
    def receivingSlot(ddict):
        print("Received: ", ddict)
    x = numpy.arange(100.)
    y = x * 1
    y[50] = numpy.nan
    w = MaskScatterWidget(maxNRois=10, bins=(100,100), backend=backend)
    w.setSelectionCurveData(x, y, color="k", selectable=False)
    import numpy.random
    w.setSelectionMask(numpy.random.permutation(100) % 10)
    w.setPolygonSelectionMode()
    w.sigMaskScatterWidgetSignal.connect(receivingSlot)
    w.show()
    app.exec()

