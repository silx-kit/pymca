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
"""This module defines a :class:`ScanWindow` inheriting a 
:class:`PlotWindow` with additional tools and actions."""
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
import numpy
import time
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, 'QString'):
    QString = qt.QString
else:
    QString = qt.safe_str
if __name__ == "__main__":
    app = qt.QApplication([])

from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.plotting import PlotWindow
from . import ScanFit
from PyMca5.PyMcaMath import SimpleMath
from PyMca5.PyMcaCore import DataObject
import copy
from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaGui.pymca import ScanWindowInfoWidget
#implement the plugins interface
from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave1D
MATPLOTLIB = True
#force understanding of utf-8 encoding
#otherways it cannot generate svg output
try:
    import encodings.utf_8
except Exception:
    #not a big problem
    pass

PLUGINS_DIR = None
try:
    import PyMca5
    if os.path.exists(os.path.join(os.path.dirname(PyMca5.__file__), "PyMcaPlugins")):
        from PyMca5 import PyMcaPlugins
        PLUGINS_DIR = os.path.dirname(PyMcaPlugins.__file__)
    else:
        directory = os.path.dirname(__file__)
        while True:
            if os.path.exists(os.path.join(directory, "PyMcaPlugins")):
                PLUGINS_DIR = os.path.join(directory, "PyMcaPlugins")
                break
            directory = os.path.dirname(directory)
            if len(directory) < 5:
                break
    userPluginsDirectory = PyMca5.getDefaultUserPluginsDirectory()
    if userPluginsDirectory is not None:
        if PLUGINS_DIR is None:
            PLUGINS_DIR = userPluginsDirectory
        else:
            PLUGINS_DIR = [PLUGINS_DIR, userPluginsDirectory]
except Exception:
    pass

_logger = logging.getLogger(__name__)

class ScanWindow(PlotWindow.PlotWindow):
    def __init__(self, parent=None, name="Scan Window", specfit=None, backend=None,
                 plugins=True, newplot=True, roi=True, fit=True,
                 control=True, position=True, info=False, **kw):

        super(ScanWindow, self).__init__(parent,
                                         newplot=newplot,
                                         plugins=plugins,
                                         backend=backend,
                                         roi=roi,
                                         fit=fit,
                                         control=control,
                                         position=position,
                                         **kw)
        self.setDataMargins(0, 0, 0.025, 0.025)
        #self._togglePointsSignal()
        self.setPanWithArrowKeys(True)
        self.setWindowType("SCAN")
        # this two objects are the same
        self.dataObjectsList = self._curveList
        # but this is tricky
        self.dataObjectsDict = {}

        self.setWindowTitle(name)
        self.matplotlibDialog = None

        if PLUGINS_DIR is not None:
            if type(PLUGINS_DIR) == type([]):
                pluginDir = PLUGINS_DIR
            else:
                pluginDir = [PLUGINS_DIR]
            self.getPlugins(method="getPlugin1DInstance",
                            directoryList=pluginDir)

        if info:
            self.scanWindowInfoWidget = ScanWindowInfoWidget.\
                                            ScanWindowInfoWidget()
            self.infoDockWidget = qt.QDockWidget(self)
            self.infoDockWidget.layout().setContentsMargins(0, 0, 0, 0)
            self.infoDockWidget.setWidget(self.scanWindowInfoWidget)
            self.infoDockWidget.setWindowTitle(self.windowTitle()+(" Info"))
            self.addDockWidget(qt.Qt.BottomDockWidgetArea,
                                   self.infoDockWidget)
            controlMenu = qt.QMenu()
            controlMenu.addAction(QString("Show/Hide Legends"),
                                       self.toggleLegendWidget)
            controlMenu.addAction(QString("Show/Hide Info"),
                                       self._toggleInfoWidget)
            controlMenu.addAction(QString("Toggle Crosshair"),
                                       self.toggleCrosshairCursor)
            controlMenu.addAction(QString("Toggle Arrow Keys Panning"),
                                       self.toggleArrowKeysPanning)
            self.setControlMenu(controlMenu)
        else:
            self.scanWindowInfoWidget = None
        #self.fig = None
        if fit:
            self.scanFit = ScanFit.ScanFit(specfit=specfit)
        self.printPreview = PyMcaPrintPreview.PyMcaPrintPreview(modal = 0)
        self.simpleMath = SimpleMath.SimpleMath()
        self.outputDir = None
        self.outputFilter = None

        #signals
        if hasattr(self, "derivateToolButton"):
            # create the derivatives menu
            self.derivateToolButton.setPopupMode(qt.QToolButton.DelayedPopup)
            self.derivateOptionSelected = None
            self.derivateMenu = qt.QMenu()
            for item in self.simpleMath.derivateOptions:
                self.derivateMenu.addAction(item)

            self.derivateToolButton.setMenu(self.derivateMenu)
            tip = "Take Derivative of active curve"
            tip += ".\nLong press to configure"
            self.derivateToolButton.setToolTip(tip)
            self.derivateToolButton.triggered.connect(self._derivateTriggered)

        # this one was made in the base class
        #self.setCallback(self.graphCallback)
        if fit:
            from PyMca5.PyMcaGui.math.fitting import SimpleFitGui
            self.customFit = SimpleFitGui.SimpleFitGui()
            self.scanFit.sigScanFitSignal.connect(self._scanFitSignalReceived)
            self.customFit.sigSimpleFitSignal.connect( \
                            self._customFitSignalReceived)

            self.fitButtonMenu = qt.QMenu()
            self.fitButtonMenu.addAction(QString("Simple Fit"),
                                   self._simpleFitSignal)
            self.fitButtonMenu.addAction(QString("Customized Fit") ,
                                   self._customFitSignal)

    def _derivateTriggered(self, action):
        text = action.text()
        tip = "Take %s derivative of active curve" % text
        tip += ".\nLong press to configure"
        self.derivateToolButton.setToolTip(tip)
        self.derivateOptionSelected = text
        self._deriveIconSignal()

    def _toggleInfoWidget(self):
        if self.infoDockWidget.isHidden():
            self.infoDockWidget.show()
            legend = self.getActiveCurve(just_legend=True)
            if legend is not None:
                ddict ={}
                ddict['event'] = "curveClicked"
                ddict['label'] = legend
                ddict['legend'] = legend
                self.graphCallback(ddict)
        else:
            self.infoDockWidget.hide()

    def _buildLegendWidget(self):
        if self.legendWidget is None:
            super(ScanWindow, self)._buildLegendWidget()
            if hasattr(self, "infoDockWidget") and \
               hasattr(self, "roiDockWidget"):
                self.tabifyDockWidget(self.infoDockWidget,
                                      self.roiDockWidget,
                                      self.legendDockWidget)
            elif hasattr(self, "infoDockWidget"):
                self.tabifyDockWidget(self.infoDockWidget,
                                      self.legendDockWidget)

    def _toggleROI(self, position=None):
        super(ScanWindow, self)._toggleROI(position=position)
        if hasattr(self, "infoDockWidget"):
            self.tabifyDockWidget(self.infoDockWidget,
                                  self.roiDockWidget)

    def setDispatcher(self, w):
        w.sigAddSelection.connect(self._addSelection)
        w.sigRemoveSelection.connect(self._removeSelection)
        w.sigReplaceSelection.connect(self._replaceSelection)

    def _addSelection(self, selectionlist, replot=True):
        """Add curves to plot and data objects to :attr:`dataObjectsDict`
        """
        _logger.debug("_addSelection(self, selectionlist) " +
                      str(selectionlist))
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]

        if len(self._curveList):
            activeCurve = self.getActiveCurve(just_legend=True)
        else:
            activeCurve = None
        nSelection = len(sellist)
        for selectionIndex in range(nSelection):
            sel = sellist[selectionIndex]
            if selectionIndex == (nSelection - 1):
                actualReplot = replot
            else:
                actualReplot = False
            source = sel['SourceName']
            key    = sel['Key']
            legend = sel['legend'] #expected form sourcename + scan key
            if not ("scanselection" in sel): continue
            if sel['scanselection'] == "MCA":
                continue
            if not sel["scanselection"]:
                continue
            if len(key.split(".")) > 2:
                continue
            dataObject = sel['dataobject']
            # only one-dimensional selections considered
            if dataObject.info["selectiontype"] != "1D":
                continue

            # there must be something to plot
            if not hasattr(dataObject, 'y'):
                continue

            if len(dataObject.y) == 0:
                # nothing to be plot
                continue
            else:
                for i in range(len(dataObject.y)):
                    if numpy.isscalar(dataObject.y[i]):
                        dataObject.y[i] = numpy.array([dataObject.y[i]])
            if not hasattr(dataObject, 'x'):
                ylen = len(dataObject.y[0])
                if ylen:
                    xdata = numpy.arange(ylen).astype(numpy.float64)
                else:
                    #nothing to be plot
                    continue
            if getattr(dataObject, 'x', None) is None:
                ylen = len(dataObject.y[0])
                if not ylen:
                    # nothing to be plot
                    continue
                xdata = numpy.arange(ylen).astype(numpy.float64)
            elif len(dataObject.x) > 1:
                _logger.debug("Mesh plots. Ignoring")
                continue
            else:
                if numpy.isscalar(dataObject.x[0]):
                    dataObject.x[0] = numpy.array([dataObject.x[0]])    
                xdata = dataObject.x[0]
            sps_source = False
            if 'SourceType' in sel:
                if sel['SourceType'] == 'SPS':
                    sps_source = True

            if sps_source:
                ycounter = -1
                if 'selection' not in dataObject.info:
                    dataObject.info['selection'] = copy.deepcopy(sel['selection'])
                for ydata in dataObject.y:
                    xlabel = None
                    ylabel = None
                    ycounter += 1
                    if dataObject.m is None:
                        mdata = [numpy.ones(len(ydata)).astype(numpy.float64)]
                    elif len(dataObject.m[0]) > 0:
                        if len(dataObject.m[0]) == len(ydata):
                            index = numpy.nonzero(dataObject.m[0])[0]
                            if not len(index):
                                continue
                            xdata = numpy.take(xdata, index)
                            ydata = numpy.take(ydata, index)
                            mdata = numpy.take(dataObject.m[0], index)
                            #A priori the graph only knows about plots
                            ydata = ydata/mdata
                        else:
                            raise ValueError("Monitor data length different than counter data")
                    else:
                        mdata = [numpy.ones(len(ydata)).astype(numpy.float64)]
                    ylegend = 'y%d' % ycounter
                    if dataObject.info['selection'] is not None:
                        if type(dataObject.info['selection']) == type({}):
                            if 'x' in dataObject.info['selection']:
                                #proper scan selection
                                ilabel = dataObject.info['selection']['y'][ycounter]
                                ylegend = dataObject.info['LabelNames'][ilabel]
                                ylabel = ylegend
                                if sel['selection']['x'] is not None:
                                    if len(dataObject.info['selection']['x']):
                                        xlabel = dataObject.info['LabelNames'] \
                                                    [dataObject.info['selection']['x'][0]]
                    dataObject.info["xlabel"] = xlabel
                    dataObject.info["ylabel"] = ylabel
                    newLegend = legend + " " + ylegend
                    self.dataObjectsDict[newLegend] = dataObject
                    self.addCurve(xdata, ydata, legend=newLegend, info=dataObject.info,
                                                    xlabel=xlabel, ylabel=ylabel, replot=False)
                    #              replot=actualReplot)
                    if self.scanWindowInfoWidget is not None:
                        if not self.infoDockWidget.isHidden():
                            activeLegend = self.getActiveCurve(just_legend=True)
                            if activeLegend is not None:
                                if activeLegend == newLegend:
                                    self.scanWindowInfoWidget.updateFromDataObject\
                                                                (dataObject)
                            else:
                                dummyDataObject = DataObject.DataObject()
                                dummyDataObject.y=[numpy.array([])]
                                dummyDataObject.x=[numpy.array([])]
                                self.scanWindowInfoWidget.updateFromDataObject(dummyDataObject)
            else:
                # we have to loop for all y values
                ycounter = -1
                for ydata in dataObject.y:
                    ylen = len(ydata)
                    if ylen == 1:
                        if len(xdata) > 1:
                            ydata = ydata[0] * numpy.ones(len(xdata)).astype(numpy.float64)
                    elif len(xdata) == 1:
                        xdata = xdata[0] * numpy.ones(ylen).astype(numpy.float64)
                    ycounter += 1
                    newDataObject = DataObject.DataObject()
                    newDataObject.info = copy.deepcopy(dataObject.info)

                    if dataObject.m is not None:
                        for imon in range(len(dataObject.m)):
                            if numpy.isscalar(dataObject.m[imon]):
                                dataObject.m[imon] = \
                                             numpy.array([dataObject.m[imon]])
                    if dataObject.m is None:
                        mdata = numpy.ones(len(ydata)).astype(numpy.float64)
                    elif len(dataObject.m[0]) > 0:
                        if len(dataObject.m[0]) == len(ydata):
                            index = numpy.nonzero(dataObject.m[0])[0]
                            if not len(index):
                                continue
                            xdata = numpy.take(xdata, index)
                            ydata = numpy.take(ydata, index)
                            mdata = numpy.take(dataObject.m[0], index)
                            #A priori the graph only knows about plots
                            ydata = ydata/mdata
                        elif len(dataObject.m[0]) == 1:
                            mdata = numpy.ones(len(ydata)).astype(numpy.float64)
                            mdata *= dataObject.m[0][0]
                            index = numpy.nonzero(dataObject.m[0])[0]
                            if not len(index):
                                continue
                            xdata = numpy.take(xdata, index)
                            ydata = numpy.take(ydata, index)
                            mdata = numpy.take(dataObject.m[0], index)
                            #A priori the graph only knows about plots
                            ydata = ydata/mdata
                        else:
                            raise ValueError("Monitor data length different than counter data")
                    else:
                        mdata = numpy.ones(len(ydata)).astype(numpy.float64)
                    newDataObject.x = [xdata]
                    newDataObject.y = [ydata]
                    newDataObject.m = [mdata]
                    newDataObject.info['selection'] = copy.deepcopy(sel['selection'])
                    ylegend = 'y%d' % ycounter
                    xlabel = None
                    ylabel = None
                    if sel['selection'] is not None:
                        if type(sel['selection']) == type({}):
                            if 'x' in sel['selection']:
                                #proper scan selection
                                newDataObject.info['selection']['x'] = sel['selection']['x']
                                newDataObject.info['selection']['y'] = [sel['selection']['y'][ycounter]]
                                newDataObject.info['selection']['m'] = sel['selection']['m']
                                ilabel = newDataObject.info['selection']['y'][0]
                                ylegend = newDataObject.info['LabelNames'][ilabel]
                                ylabel = ylegend
                                if len(newDataObject.info['selection']['x']):
                                    ilabel = newDataObject.info['selection']['x'][0]
                                    xlabel = newDataObject.info['LabelNames'][ilabel]
                                else:
                                    xlabel = "Point number"
                    if ('operations' in dataObject.info) and len(dataObject.y) == 1:
                        newDataObject.info['legend'] = legend
                        symbol = 'x'
                    else:
                        symbol = None
                        newDataObject.info['legend'] = legend + " " + ylegend
                        newDataObject.info['selectionlegend'] = legend
                    yaxis = None
                    if "plot_yaxis" in dataObject.info:
                        yaxis = dataObject.info["plot_yaxis"]
                    elif 'operations' in dataObject.info:
                        if dataObject.info['operations'][-1] == 'derivate':
                            yaxis = 'right'
                    # do not keep unnecessary references
                    self.dataObjectsDict[newDataObject.info['legend']] = newDataObject
                    self.addCurve(xdata, ydata, legend=newDataObject.info['legend'],
                                    info=newDataObject.info,
                                    symbol=symbol,
                                    yaxis=yaxis,
                                    xlabel=xlabel,
                                    ylabel=ylabel,
                                    replot=False)
        self.dataObjectsList = self._curveList
        try:
            if activeCurve is None:
                if len(self._curveList) > 0:
                    activeCurve = self._curveList[0]
                ddict = {}
                ddict['event'] = "curveClicked"
                ddict['label'] = activeCurve
                self.graphCallback(ddict)
        finally:
            if replot:
                #self.replot()
                self.resetZoom()
        self.updateLegends()

    def _removeSelection(self, selectionlist):
        _logger.debug("_removeSelection(self, selectionlist)",selectionlist)
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]

        removelist = []
        for sel in sellist:
            source = sel['SourceName']
            key = sel['Key']
            if not ("scanselection" in sel):
                continue
            if sel['scanselection'] == "MCA":
                continue
            if not sel["scanselection"]:
                continue
            if len(key.split(".")) > 2:
                continue

            legend = sel['legend'] # expected form sourcename + scan key
            if type(sel['selection']) == type({}):
                if 'y' in sel['selection']:
                    for lName in ['cntlist', 'LabelNames']:
                        if lName in sel['selection']:
                            for index in sel['selection']['y']:
                                removelist.append(legend +" "+\
                                                  sel['selection'][lName][index])

        if len(removelist):
            self.removeCurves(removelist)

    def removeCurves(self, removeList, replot=True):
        for legend in removeList:
            if legend == removeList[-1]:
                self.removeCurve(legend, replot=replot)
            else:
                self.removeCurve(legend, replot=False)
            if legend in self.dataObjectsDict:
                del self.dataObjectsDict[legend]
        self.dataObjectsList = self._curveList

    def _replaceSelection(self, selectionlist):
        """Delete existing curves and data objects, then add new selection.
        """
        _logger.debug("_replaceSelection(self, selectionlist) %s" % selectionlist)
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]

        doit = False
        for sel in sellist:
            if not ("scanselection" in sel):
                continue
            if sel['scanselection'] == "MCA":
                continue
            if not sel["scanselection"]:
                continue
            if len(sel["Key"].split(".")) > 2:
                continue
            dataObject = sel['dataobject']
            if dataObject.info["selectiontype"] == "1D":
                if hasattr(dataObject, 'y'):
                    doit = True
                    break
        if not doit:
            return
        self.clearCurves()
        self.dataObjectsDict={}
        self.dataObjectsList=self._curveList
        self._addSelection(selectionlist, replot=True)

    def _handleMarkerEvent(self, ddict):
        if ddict['event'] == 'markerMoved':
            label = ddict['label']
            if label.startswith('ROI'):
                return self._handleROIMarkerEvent(ddict)
            else:
                _logger.debug("Unhandled marker %s" % label)
                return

    def graphCallback(self, ddict):
        _logger.debug("graphCallback: %s", ddict)
        if ddict['event'] in ['markerMoved', 'markerSelected']:
            self._handleMarkerEvent(ddict)
        elif ddict['event'] in ["mouseMoved", "MouseAt"]:
            if self._toggleCounter > 0:
                activeCurve = self.getActiveCurve()
                if activeCurve in [None, []]:
                    self._handleMouseMovedEvent(ddict)
                else:
                    x, y, legend, info = activeCurve[0:4]
                    # calculate the maximum distance
                    xMin, xMax = self.getGraphXLimits()
                    maxXDistance = abs(xMax - xMin)
                    yMin, yMax = self.getGraphYLimits()
                    maxYDistance = abs(yMax - yMin)
                    if (maxXDistance > 0.0) and (maxYDistance > 0.0):
                        closestIndex = (pow((x - ddict['x'])/maxXDistance, 2) + \
                                        pow((y - ddict['y'])/maxYDistance, 2))
                    else:
                        closestIndex = (pow(x - ddict['x'], 2) + \
                                    pow(y - ddict['y'], 2))
                    curs_xText = '%.7g' % ddict['x']
                    curs_yText = '%.7g' % ddict['y']
                    xText = '----'
                    yText = '----'
                    if len(closestIndex):
                        closestIndex = closestIndex.argmin()
                        xCurve = x[closestIndex]
                        if abs(xCurve - ddict['x']) < (0.05 * maxXDistance):
                            yCurve = y[closestIndex]
                            if abs(yCurve - ddict['y']) < (0.05 * maxYDistance):
                                xText = '%.7g' % xCurve
                                yText = '%.7g' % yCurve
                    # showing ToolTip with coordinates of a cursor and nearest point
                    # colors are hardcoded due to matplotlib colormap
                    # current point coordinates are red to match crosshair red color
                    if xMin <ddict['x']< xMax and yMin <ddict['y']< yMax and self.getGraphCursor():
                        xy_tip = ('<span style="color: red;">X:%s <br>'
                                  'Y:%s</span> <br>'
                                  'X:%s <br>'
                                  'Y:%s '
                                  % (curs_xText, curs_yText, xText, yText))
                        qt.QToolTip.showText(self.cursor().pos(), xy_tip)
                    if xText == '----':
                        if self.getGraphCursor():
                            self._xPos.setStyleSheet("color: rgb(255, 0, 0);")
                            self._yPos.setStyleSheet("color: rgb(255, 0, 0);")
                            xText = curs_xText
                            yText = curs_yText
                        else:
                            self._xPos.setStyleSheet("color: rgb(0, 0, 0);")
                            self._yPos.setStyleSheet("color: rgb(0, 0, 0);")
                    else:
                        self._xPos.setStyleSheet("color: rgb(0, 0, 0);")
                        self._yPos.setStyleSheet("color: rgb(0, 0, 0);")
                    self._xPos.setText(xText)
                    self._yPos.setText(yText)
            else:
                self._xPos.setStyleSheet("color: rgb(0, 0, 0);")
                self._yPos.setStyleSheet("color: rgb(0, 0, 0);")
                self._handleMouseMovedEvent(ddict)
        elif ddict['event'] in ["curveClicked", "legendClicked"]:
            legend = ddict["label"]
            if legend is None:
                if len(self.dataObjectsList):
                    legend = self.dataObjectsList[0]
                else:
                    return
            if legend not in self.dataObjectsList:
                _logger.debug("unknown legend %s" % legend)
                return

            #force the current x label to the appropriate value
            dataObject = self.dataObjectsDict[legend]
            if 'selection' in dataObject.info:
                ilabel = dataObject.info['selection']['y'][0]
                ylabel = dataObject.info['LabelNames'][ilabel]
                if len(dataObject.info['selection']['x']):
                    ilabel = dataObject.info['selection']['x'][0]
                    xlabel = dataObject.info['LabelNames'][ilabel]
                else:
                    xlabel = "Point Number"
                if len(dataObject.info['selection']['m']):
                    ilabel = dataObject.info['selection']['m'][0]
                    ylabel += "/" + dataObject.info['LabelNames'][ilabel]
            else:
                xlabel = dataObject.info.get('xlabel', None)
                ylabel = dataObject.info.get('ylabel', None)
            if xlabel is not None:
                self.setGraphXLabel(xlabel)
            if ylabel is not None:
                self.setGraphYLabel(ylabel)
            self.setGraphTitle(legend)
            self.setActiveCurve(legend)
            #self.setGraphTitle(legend)
            if self.scanWindowInfoWidget is not None:
                if not self.infoDockWidget.isHidden():
                    self.scanWindowInfoWidget.updateFromDataObject\
                                                            (dataObject)
        elif ddict['event'] == "removeCurveEvent":
            legend = ddict['legend']
            self.removeCurves([legend])
        elif ddict['event'] == "renameCurveEvent":
            legend = ddict['legend']
            newlegend = ddict['newlegend']
            if legend in self.dataObjectsDict:
                self.dataObjectsDict[newlegend]= copy.deepcopy(self.dataObjectsDict[legend])
                self.dataObjectsDict[newlegend].info['legend'] = newlegend
                self.dataObjectsList.append(newlegend)
                self.removeCurves([legend], replot=False)
                self.newCurve(self.dataObjectsDict[newlegend].x[0],
                              self.dataObjectsDict[newlegend].y[0],
                              legend=self.dataObjectsDict[newlegend].info['legend'])

        #make sure the plot signal is forwarded because we have overwritten
        #its handling
        self.sigPlotSignal.emit(ddict)


    def _customFitSignalReceived(self, ddict):
        if ddict['event'] == "FitFinished":
            newDataObject = self.__customFitDataObject

            xplot = ddict['x']
            yplot = ddict['yfit']
            newDataObject.x = [xplot]
            newDataObject.y = [yplot]
            newDataObject.m = [numpy.ones(len(yplot)).astype(numpy.float64)]

            #here I should check the log or linear status
            self.dataObjectsDict[newDataObject.info['legend']] = newDataObject
            self.addCurve(xplot,
                          yplot,
                          legend=newDataObject.info['legend'])

    def _scanFitSignalReceived(self, ddict):
        _logger.debug("_scanFitSignalReceived", ddict)
        if ddict['event'] == "EstimateFinished":
            return
        if ddict['event'] == "FitFinished":
            newDataObject = self.__fitDataObject

            xplot = self.scanFit.specfit.xdata * 1.0
            yplot = self.scanFit.specfit.gendata(parameters=ddict['data'])
            newDataObject.x = [xplot]
            newDataObject.y = [yplot]
            newDataObject.m = [numpy.ones(len(yplot)).astype(numpy.float64)]

            self.dataObjectsDict[newDataObject.info['legend']] = newDataObject
            self.addCurve(x=xplot, y=yplot, legend=newDataObject.info['legend'])

    def _fitIconSignal(self):
        _logger.debug("_fitIconSignal")
        self.fitButtonMenu.exec(self.cursor().pos())

    def _simpleFitSignal(self):
        _logger.debug("_simpleFitSignal")
        self._QSimpleOperation("fit")

    def _customFitSignal(self):
        _logger.debug("_customFitSignal")
        self._QSimpleOperation("custom_fit")

    def _saveIconSignal(self):
        _logger.debug("_saveIconSignal")
        if self._ownSave:
            self._QSimpleOperation("save")
        else:
            self.emitIconSignal("save")

    def _averageIconSignal(self):
        _logger.debug("_averageIconSignal")
        self._QSimpleOperation("average")

    def _smoothIconSignal(self):
        _logger.debug("_smoothIconSignal")
        self._QSimpleOperation("smooth")

    def _getOutputFileName(self):
        #get outputfile
        self.outputDir = PyMcaDirs.outputDir
        if self.outputDir is None:
            self.outputDir = os.getcwd()
            wdir = os.getcwd()
        elif os.path.exists(self.outputDir):
            wdir = self.outputDir
        else:
            self.outputDir = os.getcwd()
            wdir = self.outputDir

        filterlist = ['Specfile MCA  *.mca',
                      'Specfile Scan *.dat',
                      'Specfile MultiScan *.dat',
                      'Raw ASCII *.txt',
                      '","-separated CSV *.csv',
                      '";"-separated CSV *.csv',
                      '"tab"-separated CSV *.csv',
                      'OMNIC CSV *.csv',
                      'Widget PNG *.png',
                      'Widget JPG *.jpg',
                      'Graphics PNG *.png',
                      'Graphics EPS *.eps',
                      'Graphics SVG *.svg']
        fileList, fileFilter = PyMcaFileDialogs.getFileList(self,
                                     filetypelist=filterlist,
                                     message="Output File Selection",
                                     currentdir=wdir,
                                     single=True,
                                     mode="SAVE",
                                     getfilter=True,
                                     currentfilter=self.outputFilter)
        if not len(fileList):
            return
        filterused = fileFilter.split()
        filetype = filterused[1]
        extension = filterused[2]
        outdir = qt.safe_str(fileList[0])
        try:
            self.outputDir  = os.path.dirname(outdir)
            PyMcaDirs.outputDir = os.path.dirname(outdir)
        except Exception:
            print("setting output directory to default")
            self.outputDir  = os.getcwd()
        try:
            outputFile = os.path.basename(outdir)
        except Exception:
            outputFile = outdir
        if len(outputFile) < 5:
            outputFile = outputFile + extension[-4:]
        elif outputFile[-4:] != extension[-4:]:
            outputFile = outputFile + extension[-4:]
        return os.path.join(self.outputDir, outputFile), filetype, filterused

    def _QSimpleOperation(self, operation):
        try:
            self._simpleOperation(operation)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _saveOperation(self, fileName, fileType, fileFilter):
        filterused = fileFilter
        filetype = fileType
        filename = fileName
        if os.path.exists(filename):
            os.remove(filename)
        if filterused[0].upper() == "WIDGET":
            fformat = filename[-3:].upper()
            if hasattr(qt.QPixmap, "grabWidget"):
                pixmap = qt.QPixmap.grabWidget(self)
            else:
                pixmap = self.grab()
            if not pixmap.save(filename, fformat):
                qt.QMessageBox.critical(self,
                                    "Save Error",
                                    "%s" % sys.exc_info()[1])
            return
        try:
            if filename[-3:].upper() in ['EPS', 'PNG', 'SVG']:
                self.graphicsSave(filename)
                return
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Graphics Saving Error: %s" % (sys.exc_info()[1]))
            msg.exec()
            return
        systemline = os.linesep
        os.linesep = '\n'
        try:
            if sys.version < "3.0":
                ffile=open(filename, "wb")
            else:
                ffile=open(filename, "w", newline='')
        except IOError:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Input Output Error: %s" % (sys.exc_info()[1]))
            msg.exec()
            return
        x, y, legend, info = self.getActiveCurve()
        xlabel = info.get("xlabel", "X")
        ylabel = info.get("ylabel", "Y")
        if 0:
            if "selection" in info:
                if type(info['selection']) == type({}):
                    if 'x' in info['selection']:
                        #proper scan selection
                        ilabel = info['selection']['y'][0]
                        ylegend = info['LabelNames'][ilabel]
                        ylabel = ylegend
                        if info['selection']['x'] is not None:
                            if len(info['selection']['x']):
                                xlabel = info['LabelNames'] [info['selection']['x'][0]]
                            else:
                                xlabel = "Point number"
        try:
            if filetype in ['Scan', 'MultiScan']:
                ffile.write("#F %s\n" % filename)
                savingDate = "#D %s\n"%(time.ctime(time.time()))
                ffile.write(savingDate)
                ffile.write("\n")
                ffile.write("#S 1 %s\n" % legend)
                ffile.write(savingDate)
                ffile.write("#N 2\n")
                ffile.write("#L %s  %s\n" % (xlabel, ylabel) )
                for i in range(len(y)):
                    ffile.write("%.7g  %.7g\n" % (x[i], y[i]))
                ffile.write("\n")
                if filetype == 'MultiScan':
                    scan_n  = 1
                    curveList = self.getAllCurves()
                    for x, y, key, info in curveList:
                        if key == legend:
                            continue
                        xlabel = info.get("xlabel", "X")
                        ylabel = info.get("ylabel", "Y")
                        if 0:
                            if "selection" in info:
                                if type(info['selection']) == type({}):
                                    if 'x' in info['selection']:
                                        #proper scan selection
                                        ilabel = info['selection']['y'][0]
                                        ylegend = info['LabelNames'][ilabel]
                                        ylabel = ylegend
                                        if info['selection']['x'] is not None:
                                            if len(info['selection']['x']):
                                                xlabel = info['LabelNames'] [info['selection']['x'][0]]
                                            else:
                                                xlabel = "Point number"
                        scan_n += 1
                        ffile.write("#S %d %s\n" % (scan_n, key))
                        ffile.write(savingDate)
                        ffile.write("#N 2\n")
                        ffile.write("#L %s  %s\n" % (xlabel, ylabel) )
                        for i in range(len(y)):
                            ffile.write("%.7g  %.7g\n" % (x[i], y[i]))
                        ffile.write("\n")
            elif filetype == 'ASCII':
                for i in range(len(y)):
                    ffile.write("%.7g  %.7g\n" % (x[i], y[i]))
            elif filetype == 'CSV':
                if "," in filterused[0]:
                    csvseparator = ","
                elif ";" in filterused[0]:
                    csvseparator = ";"
                elif "OMNIC" in filterused[0]:
                    csvseparator = ","
                else:
                    csvseparator = "\t"
                if "OMNIC" not in filterused[0]:
                    ffile.write('"%s"%s"%s"\n' % (xlabel,csvseparator,ylabel))
                for i in range(len(y)):
                    ffile.write("%.7E%s%.7E\n" % (x[i], csvseparator,y[i]))
            else:
                ffile.write("#F %s\n" % filename)
                ffile.write("#D %s\n"%(time.ctime(time.time())))
                ffile.write("\n")
                ffile.write("#S 1 %s\n" % legend)
                ffile.write("#D %s\n"%(time.ctime(time.time())))
                ffile.write("#@MCA %16C\n")
                ffile.write("#@CHANN %d %d %d 1\n" %  (len(y), x[0], x[-1]))
                ffile.write("#@CALIB %.7g %.7g %.7g\n" % (0, 1, 0))
                ffile.write(self.array2SpecMca(y))
                ffile.write("\n")
            ffile.close()
            os.linesep = systemline
        except:
            os.linesep = systemline
            raise
        return


    def _simpleOperation(self, operation):
        if operation == 'subtract':
            self._subtractOperation()
            return
        if operation == "save":
            #getOutputFileName
            filename = self._getOutputFileName()
            if filename is None:
                return
            self._saveOperation(filename[0], filename[1], filename[2])
            return
        if operation != "average":
            #get active curve
            legend = self.getActiveCurveLegend()
            if legend is None:return

            found = False
            for key in self.dataObjectsList:
                if key == legend:
                    found = True
                    break

            if found:
                dataObject = self.dataObjectsDict[legend]
            else:
                print("I should not be here")
                print("active curve =",legend)
                print("but legend list = ",self.dataObjectsList)
                return
            y = dataObject.y[0]
            if dataObject.x is not None:
                x = dataObject.x[0]
            else:
                x = numpy.arange(len(y)).astype(numpy.float64)
            ilabel = dataObject.info['selection']['y'][0]
            ylabel = dataObject.info['LabelNames'][ilabel]
            if len(dataObject.info['selection']['x']):
                ilabel = dataObject.info['selection']['x'][0]
                xlabel = dataObject.info['LabelNames'][ilabel]
            else:
                xlabel = "Point Number"
        else:
            x = []
            y = []
            legend = ""
            i = 0
            ndata = 0
            for key in self._curveList:
                _logger.debug("key -> ", key)
                if key in self.dataObjectsDict:
                    x.append(self.dataObjectsDict[key].x[0]) #only the first X
                    if len(self.dataObjectsDict[key].y) == 1:
                        y.append(self.dataObjectsDict[key].y[0])
                    else:
                        sel_legend = self.dataObjectsDict[key].info['legend']
                        ilabel = 0
                        #I have to get the proper y associated to the legend
                        if sel_legend in key:
                            if key.index(sel_legend) == 0:
                                label = key[len(sel_legend):]
                                while (label.startswith(' ')):
                                    label = label[1:]
                                    if not len(label):
                                        break
                                if label in self.dataObjectsDict[key].info['LabelNames']:
                                    ilabel = self.dataObjectsDict[key].info['LabelNames'].index(label)
                                _logger.debug("LABEL = ", label)
                                _logger.debug("ilabel = ", ilabel)
                        y.append(self.dataObjectsDict[key].y[ilabel])
                    if i == 0:
                        legend = key
                        firstcurve = key
                        i += 1
                    else:
                        legend += " + " + key
                        lastcurve = key
                    ndata += 1
            if ndata == 0: return #nothing to average
            dataObject = self.dataObjectsDict[firstcurve]

        #create the output data object
        newDataObject = DataObject.DataObject()
        newDataObject.data = None
        newDataObject.info = copy.deepcopy(dataObject.info)
        if 'selectionlegend' in newDataObject.info:
            del newDataObject.info['selectionlegend']
        if not ('operations' in newDataObject.info):
            newDataObject.info['operations'] = []
        newDataObject.info['operations'].append(operation)

        sel = {}
        sel['SourceType'] = "Operation"
        #get new x and new y
        if operation == "derivate":
            #xmin and xmax
            xlimits=self.getGraphXLimits()
            xplot, yplot = self.simpleMath.derivate(x, y, xlimits=xlimits,
                                                    option=self.derivateOptionSelected)
            ilabel = dataObject.info['selection']['y'][0]
            ylabel = dataObject.info['LabelNames'][ilabel]
            newDataObject.info['LabelNames'][ilabel] = ylabel+"'"
            newDataObject.info['plot_yaxis'] = "right"
            sel['SourceName'] = legend
            sel['Key']    = "'"
            sel['legend'] = legend + sel['Key']
            outputlegend  = legend + sel['Key']
        elif operation == "average":
            xplot, yplot = self.simpleMath.average(x, y)
            if len(legend) < 80:
                sel['SourceName'] = legend
                sel['Key']    = ""
                sel['legend'] = "(%s)/%d" % (legend, ndata)
                outputlegend  = "(%s)/%d" % (legend, ndata)
            else:
                sel['SourceName'] = legend
                legend = "Average of %d from %s to %s" % (ndata, firstcurve, lastcurve)
                sel['Key']    = ""
                sel['legend'] = legend
                outputlegend  = legend
        elif operation == "swapsign":
            xplot =  x * 1
            yplot = -y
            sel['SourceName'] = legend
            sel['Key']    = ""
            sel['legend'] = "-(%s)" % legend
            outputlegend  = "-(%s)" % legend
        elif operation == "smooth":
            xplot =  x * 1
            yplot = self.simpleMath.smooth(y)
            sel['SourceName'] = legend
            sel['Key']    = ""
            sel['legend'] = "%s Smooth" % legend
            outputlegend  = "%s Smooth" % legend
            if 'operations' in dataObject.info:
                if len(dataObject.info['operations']):
                    if dataObject.info['operations'][-1] == "smooth":
                        sel['legend'] = legend
                        outputlegend  = legend
        elif operation == "forceymintozero":
            xplot =  x * 1
            yplot =  y - min(y)
            sel['SourceName'] = legend
            sel['Key']    = ""
            sel['legend'] = "(%s) - ymin" % legend
            outputlegend  = "(%s) - ymin" % legend
        elif operation == "fit":
            #remove a existing fit if present
            xmin,xmax=self.getGraphXLimits()
            outputlegend = legend + " Fit"
            for key in self._curveList:
                if key == outputlegend:
                    self.removeCurves([outputlegend], replot=False)
                    break
            self.scanFit.setData(x = x,
                                 y = y,
                                 xmin = xmin,
                                 xmax = xmax,
                                 legend = legend)
            if self.scanFit.isHidden():
                self.scanFit.show()
            self.scanFit.raise_()
        elif operation == "custom_fit":
            #remove a existing fit if present
            xmin, xmax=self.getGraphXLimits()
            outputlegend = legend + "Custom Fit"
            keyList = list(self._curveList)
            for key in keyList:
                if key == outputlegend:
                    self.removeCurves([outputlegend], replot=False)
                    break
            self.customFit.setData(x = x,
                                   y = y,
                                   xmin = xmin,
                                   xmax = xmax,
                                   legend = legend)
            if self.customFit.isHidden():
                self.customFit.show()
            self.customFit.raise_()
        else:
            raise ValueError("Unknown operation %s" % operation)
        if operation not in ["fit", "custom_fit"]:
            newDataObject.x = [xplot]
            newDataObject.y = [yplot]
            newDataObject.m = [numpy.ones(len(yplot)).astype(numpy.float64)]

        #and add it to the plot
        if True and (operation not in ['fit', 'custom_fit']):
            sel['dataobject'] = newDataObject
            sel['scanselection'] = True
            sel['selection'] = copy.deepcopy(dataObject.info['selection'])
            sel['selectiontype'] = "1D"
            if operation == 'average':
                self._replaceSelection([sel])
            elif operation != 'fit':
                self._addSelection([sel])
            else:
                self.__fitDataObject = newDataObject
                return
        else:
            newDataObject.info['legend'] = outputlegend
            if operation == 'fit':
                self.__fitDataObject = newDataObject
                return
            if operation == 'custom_fit':
                self.__customFitDataObject = newDataObject
                return

            self.dataObjectsDict[newDataObject.info['legend']] = newDataObject
            #here I should check the log or linear status
            self.addCurve(x=xplot, y=yplot, legend=newDataObject.info['legend'], replot=False)
        self.replot()

    def graphicsSave(self, filename):
        #use the plugin interface
        x, y, legend, info = self.getActiveCurve()[:4]
        curveList = self.getAllCurves()
        size = (6, 3) #in inches
        bw = False
        if len(curveList) > 1:
            legends = True
        else:
            legends = False
        if self.matplotlibDialog is None:
            self.matplotlibDialog = QPyMcaMatplotlibSave1D.\
                                    QPyMcaMatplotlibSaveDialog(size=size,
                                                        logx=self._logX,
                                                        logy=self._logY,
                                                        legends=legends,
                                                        bw = bw)
        mtplt = self.matplotlibDialog.plot
        mtplt.setParameters({'logy':self._logY,
                             'logx':self._logX,
                             'legends':legends,
                             'bw':bw})
        xmin, xmax = self.getGraphXLimits()
        ymin, ymax = self.getGraphYLimits()
        mtplt.setLimits(xmin, xmax, ymin, ymax)

        legend0 = legend
        xdata = x
        ydata = y
        dataCounter = 1
        alias = "%c" % (96+dataCounter)
        mtplt.addDataToPlot( xdata, ydata, legend=legend0, alias=alias )
        for curve in curveList:
            xdata, ydata, legend, info = curve[0:4]
            if legend == legend0:
                continue
            dataCounter += 1
            alias = "%c" % (96+dataCounter)
            mtplt.addDataToPlot( xdata, ydata, legend=legend, alias=alias )

        if sys.version < '3.0':
            self.matplotlibDialog.setXLabel(qt.safe_str(self.getGraphXLabel()))
            self.matplotlibDialog.setYLabel(qt.safe_str(self.getGraphYLabel()))
        else:
            self.matplotlibDialog.setXLabel(self.getGraphXLabel())
            self.matplotlibDialog.setYLabel(self.getGraphYLabel())

        if legends:
            mtplt.plotLegends()
        ret = self.matplotlibDialog.exec()
        if ret == qt.QDialog.Accepted:
            mtplt.saveFile(filename)
        return

    def getActiveCurveLegend(self):
        return super(ScanWindow,self).getActiveCurve(just_legend=True)

    def _deriveIconSignal(self):
        _logger.debug("_deriveIconSignal")
        self._QSimpleOperation('derivate')

    def _swapSignIconSignal(self):
        _logger.debug("_swapSignIconSignal")
        self._QSimpleOperation('swapsign')

    def _yMinToZeroIconSignal(self):
        _logger.debug("_yMinToZeroIconSignal")
        self._QSimpleOperation('forceymintozero')

    def _subtractIconSignal(self):
        _logger.debug("_subtractIconSignal")
        self._QSimpleOperation('subtract')

    def _subtractOperation(self):
        #identical to twice the average with the negative active curve
        #get active curve
        legend = self.getActiveCurveLegend()
        if legend is None:
            return

        found = False
        for key in self.dataObjectsList:
            if key == legend:
                found = True
                break

        if found:
            dataObject = self.dataObjectsDict[legend]
        else:
            print("I should not be here")
            print("active curve =",legend)
            print("but legend list = ",self.dataObjectsList)
            return
        x = dataObject.x[0]
        y = dataObject.y[0]
        ilabel = dataObject.info['selection']['y'][0]
        ylabel = dataObject.info['LabelNames'][ilabel]
        if len(dataObject.info['selection']['x']):
            ilabel = dataObject.info['selection']['x'][0]
            xlabel = dataObject.info['LabelNames'][ilabel]
        else:
            xlabel = "Point Number"

        xActive = x
        yActive = y
        yActiveLegend = legend
        yActiveLabel  = ylabel
        xActiveLabel  = xlabel

        operation = "subtract"
        sel_list = []
        i = 0
        ndata = 0
        keyList = list(self._curveList)
        for key in keyList:
            legend = ""
            x = [xActive]
            y = [-yActive]
            _logger.debug("key -> ", key)
            if key in self.dataObjectsDict:
                x.append(self.dataObjectsDict[key].x[0]) #only the first X
                if len(self.dataObjectsDict[key].y) == 1:
                    y.append(self.dataObjectsDict[key].y[0])
                    ilabel = self.dataObjectsDict[key].info['selection']['y'][0]
                else:
                    sel_legend = self.dataObjectsDict[key].info['legend']
                    ilabel = self.dataObjectsDict[key].info['selection']['y'][0]
                    #I have to get the proper y associated to the legend
                    if sel_legend in key:
                        if key.index(sel_legend) == 0:
                            label = key[len(sel_legend):]
                            while (label.startswith(' ')):
                                label = label[1:]
                                if not len(label):
                                    break
                            if label in self.dataObjectsDict[key].info['LabelNames']:
                                ilabel = self.dataObjectsDict[key].info['LabelNames'].index(label)
                            _logger.debug("LABEL = ", label)
                            _logger.debug("ilabel = ", ilabel)
                    y.append(self.dataObjectsDict[key].y[ilabel])
                outputlegend = "(%s - %s)" %  (key, yActiveLegend)
                ndata += 1
                xplot, yplot = self.simpleMath.average(x, y)
                yplot *= 2
                #create the output data object
                newDataObject = DataObject.DataObject()
                newDataObject.data = None
                newDataObject.info.update(self.dataObjectsDict[key].info)
                if not ('operations' in newDataObject.info):
                    newDataObject.info['operations'] = []
                newDataObject.info['operations'].append(operation)
                newDataObject.info['LabelNames'][ilabel] = "(%s - %s)" %  \
                                        (newDataObject.info['LabelNames'][ilabel], yActiveLabel)
                newDataObject.x = [xplot]
                newDataObject.y = [yplot]
                newDataObject.m = None
                sel = {}
                sel['SourceType'] = "Operation"
                sel['SourceName'] = key
                sel['Key']    = ""
                sel['legend'] = outputlegend
                sel['dataobject'] = newDataObject
                sel['scanselection'] = True
                sel['selection'] = copy.deepcopy(dataObject.info['selection'])
                #sel['selection']['y'] = [ilabel]
                sel['selectiontype'] = "1D"
                sel_list.append(sel)
        if True:
            #The legend menu was not working with the next line
            #but if works if I add the list
            self._replaceSelection(sel_list)
        else:
            oldlist = list(self.dataObjectsDict)
            self._addSelection(sel_list)
            self.removeCurves(oldlist)

    #The plugins interface
    def getGraphYLimits(self):
        #if the active curve is mapped to second axis
        #I should give the second axis limits
        return super(ScanWindow, self).getGraphYLimits()

    #end of plugins interface
    def addCurve(self, x, y, legend=None, info=None, replace=False, replot=True,
                 color=None, symbol=None, linestyle=None,
                 xlabel=None, ylabel=None, yaxis=None,
                 xerror=None, yerror=None, **kw):
        if legend in self._curveList:
            if info is None:
                info = {}
            oldStuff = self.getCurve(legend)
            if len(oldStuff):
                oldX, oldY, oldLegend, oldInfo = oldStuff
            else:
                oldInfo = {}
            if color is None:
                color = info.get("plot_color", oldInfo.get("plot_color", None))
            if symbol is None:
                symbol = info.get("plot_symbol",oldInfo.get("plot_symbol", None))
            if linestyle is None:
                linestyle = info.get("plot_linestyle",oldInfo.get("plot_linestyle", None))
            if yaxis is None:
                yaxis = info.get("plot_yaxis",oldInfo.get("plot_yaxis", None))
        else:
            if info is None:
                info = {}
            if color is None:
                color = info.get("plot_color", None)
            if symbol is None:
                symbol = info.get("plot_symbol", None)
            if linestyle is None:
                linestyle = info.get("plot_linestyle", None)
            if yaxis is None:
                yaxis = info.get("plot_yaxis", None)
        if legend in self.dataObjectsDict:
            # the info is changing
            super(ScanWindow, self).addCurve(x, y, legend=legend, info=info,
                                replace=replace, replot=replot, color=color, symbol=symbol,
                                linestyle=linestyle, xlabel=xlabel, ylabel=ylabel, yaxis=yaxis,
                                xerror=xerror, yerror=yerror, **kw)
        else:
            # create the data object
            self.newCurve(x, y, legend=legend, info=info,
                                replace=replace, replot=replot, color=color, symbol=symbol,
                                linestyle=linestyle, xlabel=xlabel, ylabel=ylabel, yaxis=yaxis,
                                xerror=xerror, yerror=yerror, **kw)

    def newCurve(self, x, y, legend=None, info=None, replace=False, replot=True,
                 color=None, symbol=None, linestyle=None,
                 xlabel=None, ylabel=None, yaxis=None,
                 xerror=None, yerror=None, **kw):
        if legend is None:
            legend = "Unnamed curve 1.1"
        if xlabel is None:
            xlabel = "X"
        if ylabel is None:
            ylabel = "Y"
        if info is None:
            info = {}
            # this is awfull but I have no other way to pass the plot information ...
        if color is not None:
            info["plot_color"] = color
        if symbol is not None:
            info["plot_symbol"] = symbol
        if linestyle is not None:
            info["plot_linestyle"] = linestyle
        if yaxis is not None:
            info["plot_yaxis"] = yaxis

        newDataObject = DataObject.DataObject()
        newDataObject.x = [x]
        newDataObject.y = [y]
        newDataObject.m = None
        newDataObject.info = copy.deepcopy(info)
        newDataObject.info['legend'] = legend
        newDataObject.info['SourceName'] = legend
        newDataObject.info['Key'] = ""
        newDataObject.info['selectiontype'] = "1D"
        newDataObject.info['LabelNames'] = [xlabel, ylabel]
        newDataObject.info['selection'] = {'x': [0], 'y': [1]}
        sel_list = []
        sel = {}
        sel['SourceType'] = "Operation"
        sel['SourceName'] = legend
        sel['Key']    = ""
        sel['legend'] = legend
        sel['dataobject'] = newDataObject
        sel['scanselection'] = True
        sel['selection'] = {'x':[0], 'y':[1], 'm':[], 'cntlist':[xlabel, ylabel]}
        #sel['selection']['y'] = [ilabel]
        sel['selectiontype'] = "1D"
        sel_list.append(sel)
        if replace:
            self._replaceSelection(sel_list)
        else:
            self._addSelection(sel_list, replot=replot)

    def printGraph(self):
        if self.printPreview.printer is None:
            # setup needed
            self.printPreview.setup()
        self._printer = self.printPreview.printer
        if self._printer is None:
            # printer was not selected
            return
        #self._printer = None
        if PlotWindow.PlotWidget.SVG:
            svg = True
            self._svgRenderer = self.getSvgRenderer()
        else:
            svg = False
            if hasattr(self, "getWidgetHandle"):
                widget = self.getWidgetHandle()
            else:
                widget = self.centralWidget()
            if hasattr(widget, "grab"):
                pixmap = widget.grab()
            else:
                pixmap = qt.QPixmap.grabWidget(widget)

        title = None
        comment = None
        if self.scanWindowInfoWidget is not None:
            if not self.infoDockWidget.isHidden():
                info = self.scanWindowInfoWidget.getInfo()
                title = info['scan'].get('source', None)
                comment = info['scan'].get('scan', None)+"\n"
                h, k, l = info['scan'].get('hkl')
                if h != "----":
                    comment += "H = %s  K = %s  L = %s\n" % (h, k, l)
                peak   = info['graph']['peak']
                peakAt = info['graph']['peakat']
                fwhm   = info['graph']['fwhm']
                fwhmAt = info['graph']['fwhmat']
                com    = info['graph']['com']
                mean   = info['graph']['mean']
                std    = info['graph']['std']
                minimum = info['graph']['min']
                maximum = info['graph']['max']
                delta   = info['graph']['delta']
                xLabel = self.getGraphXLabel()
                comment += "Peak %s at %s = %s\n" % (peak, xLabel, peakAt)
                comment += "FWHM %s at %s = %s\n" % (fwhm, xLabel, fwhmAt)
                comment += "COM = %s  Mean = %s  STD = %s\n" % (com, mean, std)
                comment += "Min = %s  Max = %s  Delta = %s\n" % (minimum,
                                                                maximum,
                                                                delta)

        if hasattr(self, "scanFit"):
            if not self.scanFit.isHidden():
                if comment is None:
                    comment = ""
                comment += "\n"
                comment += self.scanFit.getText()

        if svg:
            self.printPreview.addSvgItem(self._svgRenderer,
                                    title=None,
                                    comment=comment,
                                    commentPosition="LEFT")
        else:
            self.printPreview.addPixmap(pixmap,
                                    title=None,
                                    comment=comment,
                                    commentPosition="LEFT")
        if self.printPreview.isHidden():
            self.printPreview.show()
        self.printPreview.raise_()

    def getSvgRenderer(self, printer=None):
        if printer is None:
            if self.printPreview.printer is None:
                # setup needed
                self.printPreview.setup()
            self._printer = self.printPreview.printer
            printer = self._printer
        if printer is None:
            # printer was not selected
            # return a renderer without adjusting the viewbox
            if sys.version < '3.0':
                import cStringIO as StringIO
                imgData = StringIO.StringIO()
            else:
                from io import StringIO
                imgData = StringIO()
            self.saveGraph(imgData, fileFormat='svg')
            imgData.flush()
            imgData.seek(0)
            svgData = imgData.read()
            imgData = None
            svgRenderer = qt.QSvgRenderer()
            svgRenderer._svgRawData = svgData
            svgRenderer._svgRendererData = qt.QXmlStreamReader(svgData)
            if not svgRenderer.load(svgRenderer._svgRendererData):
                raise RuntimeError("Cannot interpret svg data")
            return svgRenderer

        # we have what is to be printed
        if sys.version < '3.0':
            import cStringIO as StringIO
            imgData = StringIO.StringIO()
        else:
            from io import StringIO
            imgData = StringIO()
        self.saveGraph(imgData, fileFormat='svg')
        imgData.flush()
        imgData.seek(0)
        svgData = imgData.read()
        imgData = None
        svgRenderer = qt.QSvgRenderer()

        #svgRenderer = PlotWindow.PlotWindow.getSvgRenderer(self)

        # we have to specify the bounding box
        config = self.getPrintConfiguration()
        width = config['width']
        height = config['height']
        xOffset = config['xOffset']
        yOffset = config['yOffset']
        units = config['units']
        keepAspectRatio = config['keepAspectRatio']


        dpix    = printer.logicalDpiX()
        dpiy    = printer.logicalDpiY()

        # get the available space
        availableWidth = printer.width()
        availableHeight = printer.height()

        # convert the offsets to dpi
        if units.lower() in ['inch', 'inches']:
            xOffset = xOffset * dpix
            yOffset = yOffset * dpiy
            if width is not None:
                width = width * dpix
            if height is not None:
                height = height * dpiy
        elif units.lower() in ['cm', 'centimeters']:
            xOffset = (xOffset/2.54) * dpix
            yOffset = (yOffset/2.54) * dpiy
            if width is not None:
                width = (width/2.54) * dpix
            if height is not None:
                height = (height/2.54) * dpiy
        else:
            # page units
            xOffset = availableWidth * xOffset
            yOffset = availableHeight * yOffset
            if width is not None:
                width = availableWidth * width
            if height is not None:
                height = availableHeight * height

        availableWidth -= xOffset
        availableHeight -= yOffset

        if width is not None:
            if (availableWidth + 0.1) < width:
                txt = "Available width  %f is less than requested width %f" % \
                              (availableWidth, width)
                raise ValueError(txt)
            availableWidth = width
        if height is not None:
            if (availableHeight + 0.1) < height:
                txt = "Available height  %f is less than requested height %f" % \
                              (availableHeight, height)
                raise ValueError(txt)
            availableHeight = height

        if keepAspectRatio:
            #get the aspect ratio
            widget = self.getWidgetHandle()
            if widget is None:
                # does this make sense?
                graphWidth = availableWidth
                graphHeight = availableHeight
            else:
                graphWidth = float(widget.width())
                graphHeight = float(widget.height())

            graphRatio = graphHeight / graphWidth
            # that ratio has to be respected

            bodyWidth = availableWidth
            bodyHeight = availableWidth * graphRatio

            if bodyHeight > availableHeight:
                bodyHeight = availableHeight
                bodyWidth = bodyHeight / graphRatio
        else:
            bodyWidth = availableWidth
            bodyHeight = availableHeight

        body = qt.QRectF(xOffset,
                         yOffset,
                         bodyWidth,
                         bodyHeight)
        # this does not work if I set the svgData before
        svgRenderer.setViewBox(body)
        svgRenderer._viewBox = body
        if not sys.version.startswith("2"):
            svgData = svgData.encode(encoding="utf-8",
                                     errors="replace")
        svgRenderer._svgRawData = svgData
        svgRenderer._svgRendererData = qt.QXmlStreamReader(svgData)

        if not svgRenderer.load(svgRenderer._svgRendererData):
            raise RuntimeError("Cannot interpret svg data")
        return svgRenderer

def test():
    w = ScanWindow()
    x = numpy.arange(1000.)
    y =  10 * x + 10000. * numpy.exp(-0.5*(x-500)*(x-500)/400)
    w.addCurve(x, y, legend="dummy", replot=True, replace=True)
    w.resetZoom()
    app.lastWindowClosed.connect(app.quit)
    w.show()
    app.exec()


if __name__ == "__main__":
    test()
    app = None
