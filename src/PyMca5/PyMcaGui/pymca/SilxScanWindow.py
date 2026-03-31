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
"""This module defines a :class:`ScanWindow` inheriting a *silx*
:class:`PlotWindow` with additional tools and actions.
The main addition is a :class:`PluginsToolButton` button added to the toolbar,
to open a menu with plugins."""

import os
import copy
import logging
import numpy
import sys
import time
import traceback

from silx.gui.plot import PlotWindow
from silx.gui.plot.PrintPreviewToolButton import SingletonPrintPreviewToolButton

import PyMca5
from PyMca5 import PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.pymca import ScanWindowInfoWidget
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.PluginsToolButton import PluginsToolButton
from PyMca5.PyMcaGui.math import SimpleActions
from PyMca5.PyMcaGui.pymca import ScanFit
from PyMca5.PyMcaGui.pymca.ScanFitToolButton import ScanFitToolButton
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave1D
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict, change_icons

if hasattr(qt, 'QString'):
    QString = qt.QString
else:
    QString = qt.safe_str

PLUGINS_DIR = None

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


_logger = logging.getLogger(__name__)
# _logger.setLevel(logging.DEBUG)

class ScanWindowPrintPreviewButton(SingletonPrintPreviewToolButton):
    """This class allows to add title and comment if the plot has the methods
    getPrintPreviewTitle and getPrintPreviewCommentAndPosition."""
    def _safeGetPlot(self):
        if hasattr(self, "getPlot"):
            plot = self.getPlot()
        elif hasattr(self, "plot"):
            plot = self.plot()
        elif hasattr(self, "_plot"):
            plot = self._plot
        else:
            plot = None
        return plot

    def getTitle(self):
        title = None
        plot = self._safeGetPlot()
        if plot is not None:
            if hasattr(plot, "getPrintPreviewTitle"):
                title = plot.getPrintPreviewTitle()
        return title

    def getCommentAndPosition(self):
        comment, position = None, None
        plot = self._safeGetPlot()
        if plot is not None:
            if hasattr(self._plot, "getPrintPreviewCommentAndPosition"):
                comment, position = plot.getPrintPreviewCommentAndPosition()
        return comment, position

class BaseScanWindow(PlotWindow):
    """:class:`PlotWindow` augmented with plugins, fitting actions,
    a widget for displaying scan metadata and simple curve processing actions.
    """
    def __init__(self, parent=None, name="Scan Window", fit=True, backend=None,
                 plugins=True, control=True, position=True, roi=True,
                 specfit=None, info=False, save=True):
        super(BaseScanWindow, self).__init__(parent,
                                             backend=backend,
                                             roi=roi,
                                             control=control,
                                             position=position,
                                             save=save,
                                             mask=False,
                                             colormap=False,
                                             aspectRatio=False,
                                             yInverted=False,
                                             copy=True,
                                             print_=False)
        self.setDataMargins(0, 0, 0.025, 0.025)

        self.setPanWithArrowKeys(True)
        self._plotType = "SCAN"     # needed by legacy plugins

        self.setWindowTitle(name)

        # No context menu by default, execute zoomBack on right click
        plotArea = self.getWidgetHandle()
        plotArea.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        plotArea.customContextMenuRequested.connect(self._zoomBack)

        # Toolbar:
        # hide interactive toolbar (zoom and pan mode buttons)
        self.getInteractiveModeToolBar().setVisible(False)

        # additional buttons
        self._mathToolBar = qt.QToolBar(self)

        self.addToolBar(self._mathToolBar)

        self.fitToolButton = None
        self.scanFit = None
        if fit:
            self.scanFit = ScanFit.ScanFit(specfit=specfit)
            self.fitToolButton = ScanFitToolButton(self)
            self.toolBar().insertWidget(self.getMaskAction(),  # before MaskAction (hidden)
                                        self.fitToolButton)

        self.avgAction = SimpleActions.AverageAction(plot=self)
        self.derivativeAction = SimpleActions.DerivativeAction(plot=self)
        self.smoothAction = SimpleActions.SmoothAction(plot=self)
        self.swapSignAction = SimpleActions.SwapSignAction(plot=self)
        self.yMinToZero = SimpleActions.YMinToZeroAction(plot=self)
        self.subtractAction = SimpleActions.SubtractAction(plot=self)

        self._mathToolBar.addAction(self.avgAction)
        self._mathToolBar.addAction(self.derivativeAction)
        self._mathToolBar.addAction(self.smoothAction)
        self._mathToolBar.addAction(self.swapSignAction)
        self._mathToolBar.addAction(self.yMinToZero)
        self._mathToolBar.addAction(self.subtractAction)

        self.pluginsToolButton = None
        """Plugins tool button, used to load and call plugins.
        It inherits the PluginLoader API:

            - getPlugins
            - getPluginDirectoryList
            - setPluginDirectoryList

        It can be None, if plugins are disabled when initializing
        the ScanWindow.
        """

        if plugins:
            self.pluginsToolButton = PluginsToolButton(plot=self)

            if PLUGINS_DIR is not None:
                if isinstance(PLUGINS_DIR, list):
                    pluginDir = PLUGINS_DIR
                else:
                    pluginDir = [PLUGINS_DIR]
                self.pluginsToolButton.getPlugins(
                        method="getPlugin1DInstance",
                        directoryList=pluginDir)
            self.pluginsAction = self._mathToolBar.addWidget(self.pluginsToolButton)

        self._printPreviewToolBar = qt.QToolBar(self)
        self._printPreviewToolBar.setMovable(False)
        self._printPreviewToolBar.setFloatable(False)
        self.addToolBar(self._printPreviewToolBar)
        self._printPreviewToolBar.addWidget(qt.HorizontalSpacer(self._printPreviewToolBar))
        self.printPreview = ScanWindowPrintPreviewButton(parent=self._printPreviewToolBar,
                                                         plot=self)
        self.printPreviewAction = self._printPreviewToolBar.addWidget(self.printPreview)

        self.scanWindowInfoWidget = None
        self.infoDockWidget = None
        if info:
            self.scanWindowInfoWidget = ScanWindowInfoWidget.\
                                            ScanWindowInfoWidget()
            self.infoDockWidget = qt.QDockWidget(self)
            self.infoDockWidget.layout().setContentsMargins(0, 0, 0, 0)
            self.infoDockWidget.setWidget(self.scanWindowInfoWidget)
            self.infoDockWidget.setWindowTitle("Scan Info")
            self.addDockWidget(qt.Qt.BottomDockWidgetArea,
                               self.infoDockWidget)

            self.sigActiveCurveChanged.connect(self.__updateInfoWidget)

        self.sigActiveCurveChanged.connect(self._updateGraphTitle)
        self.matplotlibDialog = None

        saveAction = self.getOutputToolBar().getSaveAction()
        for ext in ["png", "eps", "svg"]:
            name_filter = 'Customized graphics (*.%s)' % ext
            # if silx-kit/silx#2013 is merged, the following line can be removed for silx 0.9
            saveAction.setFileFilter(dataKind='curve',  # single curve case
                                     nameFilter=name_filter,
                                     func=self._graphicsSave)
            saveAction.setFileFilter(dataKind='curves',
                                     nameFilter=name_filter,
                                     func=self._graphicsSave)

        change_icons(self)

    def _customControlButtonMenu(self):
        """Display Options button sub-menu. Overloaded to add
        _toggleInfoAction"""
        # overloaded from PlotWindow to add "Show/Hide Info"
        controlMenu = self.controlButton.menu()
        controlMenu.clear()
        controlMenu.addAction(self.getLegendsDockWidget().toggleViewAction())

        if self.infoDockWidget is not None:
            controlMenu.addAction(self.infoDockWidget.toggleViewAction())
        controlMenu.addAction(self.getRoiAction())
        controlMenu.addAction(self.getMaskAction())
        controlMenu.addAction(self.getConsoleAction())

        controlMenu.addSeparator()
        controlMenu.addAction(self.getCrosshairAction())
        controlMenu.addAction(self.getPanWithArrowKeysAction())

    def __updateInfoWidget(self, previous_legend, legend):
        """Called on active curve changed, to update the info widget"""
        x, y, legend, info, params = self.getCurve(legend)
        self.scanWindowInfoWidget.updateFromXYInfo(x, y, info)

    def _updateGraphTitle(self, previous_legend, legend):
        """Called on active curve changed, to update the graph title"""
        if legend is None and previous_legend is not None:
            self.setGraphTitle()
        elif legend is not None:
            self.setGraphTitle(legend)

    def setWindowType(self, wtype=None):
        if wtype not in [None, "SCAN", "MCA"]:
            raise AttributeError("Unsupported window type %s." % wtype)
        self._plotType = wtype

    def _zoomBack(self, pos):
        self.getLimitsHistory().pop()

    def _graphicsSave(self, plot, filename, nameFilter=""):
        # note: the method's signature must conform to
        #       saveAction.setFileFilter requirements
        x, y, legend, info = plot.getActiveCurve()[:4]
        curveList = plot.getAllCurves()
        size = (6, 3)  # in inches
        legends = len(curveList) > 1
        if self.matplotlibDialog is None:
            self.matplotlibDialog = QPyMcaMatplotlibSave1D.\
                                    QPyMcaMatplotlibSaveDialog(size=size,
                                                        logx=plot.isXAxisLogarithmic(),
                                                        logy=plot.isYAxisLogarithmic(),
                                                        legends=legends,
                                                        bw=False)

        mtplt = self.matplotlibDialog.plot

        mtplt.setParameters({'logy': plot.isXAxisLogarithmic(),
                             'logx': plot.isYAxisLogarithmic(),
                             'legends': legends,
                             'bw': False})
        xmin, xmax = plot.getGraphXLimits()
        ymin, ymax = plot.getGraphYLimits()
        mtplt.setLimits(xmin, xmax, ymin, ymax)

        legend0 = legend
        dataCounter = 1
        alias = "%c" % (96 + dataCounter)
        mtplt.addDataToPlot(x, y, legend=legend0, alias=alias)
        for curve in curveList:
            x, y, legend, info = curve[0:4]
            if legend == legend0:
                continue
            dataCounter += 1
            alias = "%c" % (96 + dataCounter)
            mtplt.addDataToPlot(x, y, legend=legend, alias=alias)

        self.matplotlibDialog.setXLabel(plot.getGraphXLabel())
        self.matplotlibDialog.setYLabel(plot.getGraphYLabel())

        if legends:
            mtplt.plotLegends()
        ret = self.matplotlibDialog.exec()
        if ret == qt.QDialog.Accepted:
            mtplt.saveFile(filename)
        return

    def getPrintPreviewTitle(self):
        return None

    def getPrintPreviewCommentAndPosition(self):
        return None, None

    def printHtml(self, text):
        printer = qt.QPrinter()
        printDialog = qt.QPrintDialog(printer, self)
        if printDialog.exec():
            document = qt.QTextDocument()
            document.setHtml(text)
            document.print_(printer)

    def array2SpecMca(self, data):
        """ Write a python array into a Spec array.
            Return the string containing the Spec array
        """
        tmpstr = "@A "
        length = len(data)
        for idx in range(0, length, 16):
            if idx+15 < length:
                for i in range(0, 16):
                    tmpstr += "%.8g " % data[idx+i]
                if idx+16 != length:
                    tmpstr += "\\"
            else:
                for i in range(idx, length):
                    tmpstr += "%.8g " % data[i]
            tmpstr += "\n"
        return tmpstr


class ScanWindow(BaseScanWindow):
    """ScanWindow, adding dataObject management to BaseScanWindow
    """

    def __init__(self, parent=None, name="Scan Window", fit=True, backend=None,
                 plugins=True, control=True, position=True, roi=True,
                 specfit=None, info=False, save=None):
        if save is None:
            _logger.info("__init__ save option unset using custom save")
            save = False
        BaseScanWindow.__init__(self,
                                parent, name, fit, backend,
                                plugins, control, position, roi,
                                specfit, info, save)

        self.dataObjectsDict = {}
        self.outputDir = None
        self.outputFilter = None

        # custom save
        self.customSaveIcon = qt.QIcon(qt.QPixmap(IconDict["filesave"]))
        self.customSaveButton = qt.QToolButton(self)
        self.customSaveButton.setIcon(self.customSaveIcon)
        self.customSaveButton.setToolTip('Save as')
        self.customSaveButton.clicked.connect(self._saveIconSignal)
        self.getOutputToolBar().addWidget(self.customSaveButton)

        self.sigContentChanged.connect(self._handleContentChanged)

    @property
    def dataObjectsList(self):
        return self.getAllCurves(just_legend=True)

    @property
    def _curveList(self):
        return self.getAllCurves(just_legend=True)

    def _handleContentChanged(self, action, kind, legend):
        if action == 'remove' and kind == "curve":
            self.removeCurves([legend])

    def setDispatcher(self, w):
        w.sigAddSelection.connect(self._addSelection)
        w.sigRemoveSelection.connect(self._removeSelection)
        w.sigReplaceSelection.connect(self._replaceSelection)

    def _addSelection(self, selectionlist, resetzoom=True, replot=None):
        """Add curves to plot and data objects to :attr:`dataObjectsDict`
        """
        _logger.debug("_addSelection(self, selectionlist) " +
                      str(selectionlist))
        if replot is not None:
            _logger.warning(
                    'deprecated replot argument, use resetzoom instead')
            resetzoom = replot and resetzoom

        sellist = selectionlist if isinstance(selectionlist, list) else \
            [selectionlist]

        if len(self.getAllCurves(just_legend=True)):
            activeCurve = self.getActiveCurve(just_legend=True)
        else:
            activeCurve = None
        nSelection = len(sellist)
        for selectionIndex in range(nSelection):
            sel = sellist[selectionIndex]
            key = sel['Key']
            legend = sel['legend']  # expected form sourcename + scan key
            if "scanselection" not in sel or not sel["scanselection"] or \
                            sel['scanselection'] == "MCA":
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
                # mesh plot
                continue
            else:
                if numpy.isscalar(dataObject.x[0]):
                    dataObject.x[0] = numpy.array([dataObject.x[0]])
                xdata = dataObject.x[0]

            if sel.get('SourceType') == "SPS":
                ycounter = -1
                if 'selection' not in dataObject.info:
                    dataObject.info['selection'] = copy.deepcopy(sel['selection'])
                for ydata in dataObject.y:
                    xlabel = None
                    ylabel = None
                    ycounter += 1
                    # normalize ydata with monitor
                    if dataObject.m is not None and len(dataObject.m[0]) > 0:
                        if len(dataObject.m[0]) != len(ydata):
                            raise ValueError("Monitor data length different than counter data")
                        index = numpy.nonzero(dataObject.m[0])[0]
                        if not len(index):
                            continue
                        xdata = numpy.take(xdata, index)
                        ydata = numpy.take(ydata, index)
                        mdata = numpy.take(dataObject.m[0], index)
                        # A priori the graph only knows about plots
                        ydata = ydata / mdata
                    ylegend = 'y%d' % ycounter
                    if isinstance(dataObject.info['selection'], dict):
                        if 'x' in dataObject.info['selection']:
                            # proper scan selection
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
                                  xlabel=xlabel, ylabel=ylabel, resetzoom=False)
                    if self.scanWindowInfoWidget is not None:
                        if not self.infoDockWidget.isHidden():
                            activeLegend = self.getActiveCurve(just_legend=True)
                            if activeLegend == newLegend:
                                self.scanWindowInfoWidget.updateFromXYInfo( \
                                            xdata, ydata, dataObject.info)
            else:
                # we have to loop for all y values
                ycounter = -1
                for ydata in dataObject.y:
                    ylen = len(ydata)
                    if ylen == 1 and len(xdata) > 1:
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
                        # Combine all monitors: divide by each one
                        combinedMdata = numpy.ones(len(ydata)).astype(numpy.float64)
                        for imon in range(len(dataObject.m)):
                            monArray = dataObject.m[imon]
                            if len(monArray) == len(ydata):
                                combinedMdata = combinedMdata * monArray
                            elif len(monArray) == 1:
                                combinedMdata = combinedMdata * monArray[0]
                            else:
                                raise ValueError("Monitor data length different than counter data")
                        index = numpy.nonzero(combinedMdata)[0]
                        if not len(index):
                            continue
                        xdata = numpy.take(xdata, index)
                        ydata = numpy.take(ydata, index)
                        mdata = numpy.take(combinedMdata, index)
                        # A priori the graph only knows about plots
                        ydata = ydata / mdata
                    else:
                        raise ValueError("Monitor data length different than counter data")

                    newDataObject.x = [xdata]
                    newDataObject.y = [ydata]
                    newDataObject.m = [mdata]
                    newDataObject.info['selection'] = copy.deepcopy(sel['selection'])
                    ylegend = 'y%d' % ycounter
                    xlabel = None
                    ylabel = None
                    if isinstance(sel['selection'], dict) and 'x' in sel['selection']:
                        # proper scan selection
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
                    self.dataObjectsDict[newDataObject.info['legend']] = newDataObject
                    self.addCurve(xdata, ydata, legend=newDataObject.info['legend'],
                                  info=newDataObject.info,
                                  symbol=symbol,
                                  yaxis=yaxis,
                                  xlabel=xlabel,
                                  ylabel=ylabel,
                                  resetzoom=False)
        try:
            if activeCurve is None and self._curveList:
                self.setActiveCurve(self._curveList[0])
        finally:
            if resetzoom:
                self.resetZoom()

    def _removeSelection(self, selectionlist):
        _logger.debug("_removeSelection(self, selectionlist) " +
                      str(selectionlist))

        sellist = selectionlist if isinstance(selectionlist, list) else \
            [selectionlist]

        removelist = []
        for sel in sellist:
            key = sel['Key']
            if "scanselection" not in sel or not sel["scanselection"]:
                continue
            if sel['scanselection'] == "MCA":
                continue
            if len(key.split(".")) > 2:
                continue

            legend = sel['legend']  # expected form sourcename + scan key
            if isinstance(sel['selection'], dict) and 'y' in sel['selection']:
                for lName in ['cntlist', 'LabelNames']:
                    if lName in sel['selection']:
                        for index in sel['selection']['y']:
                            removelist.append(legend + " " +
                                              sel['selection'][lName][index])

        if len(removelist):
            self.removeCurves(removelist)

    def _replaceSelection(self, selectionlist):
        """Delete existing curves and data objects, then add new selection.
        """
        _logger.debug("_replaceSelection(self, selectionlist) " +
                      str(selectionlist))

        sellist = selectionlist if isinstance(selectionlist, list) else \
            [selectionlist]

        doit = False
        for sel in sellist:
            if "scanselection" not in sel or not sel["scanselection"]:
                continue
            if sel['scanselection'] == "MCA":
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
        self.dataObjectsDict = {}
        self._addSelection(selectionlist, resetzoom=True)

    def removeCurves(self, removeList):
        for legend in removeList:
            self.removeCurve(legend)
            if legend in self.dataObjectsDict:
                del self.dataObjectsDict[legend]

    def addCurve(self, x, y, legend=None, info=None, replace=False,
                 resetzoom=True, color=None, symbol=None,
                 linestyle=None, xlabel=None, ylabel=None, yaxis=None,
                 xerror=None, yerror=None, **kw):
        """Add a curve. If a curve with the same legend already exists,
        the unspecified parameters (color, symbol, linestyle, yaxis) are
        assumed to be identical to the parameters of the existing curve."""
        if "replot" in kw:
            _logger.warning("addCurve deprecated replot argument, "
                            "use resetzoom instead")
            resetzoom = kw["replot"] and resetzoom
        if legend in self._curveList:
            if info is None:
                info = {}
            oldStuff = self.getCurve(legend)
            if oldStuff is not None:
                oldX, oldY, oldLegend, oldInfo, oldParams = oldStuff
            else:
                oldInfo = {}
            if color is None:
                color = info.get("plot_color",
                                 oldInfo.get("plot_color", None))
            if symbol is None:
                symbol = info.get("plot_symbol",
                                  oldInfo.get("plot_symbol", None))
            if linestyle is None:
                linestyle = info.get("plot_linestyle",
                                     oldInfo.get("plot_linestyle", None))
            if yaxis is None:
                yaxis = info.get("plot_yaxis",
                                 oldInfo.get("plot_yaxis", None))
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
            super(ScanWindow, self).addCurve(
                    x, y, legend=legend, info=info,
                    replace=replace, color=color, symbol=symbol,
                    linestyle=linestyle, xlabel=xlabel, ylabel=ylabel,
                    yaxis=yaxis, xerror=xerror, yerror=yerror,
                    resetzoom=resetzoom, **kw)
        else:
            # create the data object
            self.newCurve(
                    x, y, legend=legend, info=info,
                    replace=replace, color=color, symbol=symbol,
                    linestyle=linestyle, xlabel=xlabel, ylabel=ylabel,
                    yaxis=yaxis, xerror=xerror, yerror=yerror,
                    resetzoom=resetzoom, **kw)

    def newCurve(self, x, y, legend=None, info=None, replace=False,
                 resetzoom=True, color=None, symbol=None,
                 linestyle=None, xlabel=None, ylabel=None, yaxis=None,
                 xerror=None, yerror=None, **kw):
        """
        Create and add a data object to :attr:`dataObjectsDict`
        """
        if "replot" in kw:
            _logger.warning("addCurve deprecated replot argument, "
                            "use resetzoom instead")
            resetzoom = kw["replot"] and resetzoom
        if legend is None:
            legend = "Unnamed curve 1.1"
        if xlabel is None:
            xlabel = "X"
        if ylabel is None:
            ylabel = "Y"
        if info is None:
            info = {}
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

        sel = {'SourceType': "Operation",
               'SourceName': legend,
               'Key': "",
               'legend': legend,
               'dataobject': newDataObject,
               'scanselection': True,
               'selection': {'x': [0], 'y': [1], 'm': [],
                             'cntlist': [xlabel, ylabel]},
               'selectiontype': "1D"}
        sel_list = [sel]
        if replace:
            self._replaceSelection(sel_list)
        else:
            self._addSelection(sel_list, resetzoom=resetzoom)

    def getPrintPreviewTitle(self):
        title = None
        try:
            if len(self.getGraphTitle()):
                # there is already a title
                # no need to add a second one
                return title
        except Exception:
            _logger.warning('Problem accessing ScanWindow plot title')
        if self.scanWindowInfoWidget is not None:
            if not self.infoDockWidget.isHidden():
                info = self.scanWindowInfoWidget.getInfo()
                title = info['scan'].get('source', None)
        return title

    def getPrintPreviewCommentAndPosition(self):
        comment = None
        position = None
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
            if self.scanFit is not None:
                if not self.scanFit.isHidden():
                    if comment is None:
                        comment = ""
                    comment += "\n"
                    comment += self.scanFit.getText()
        return comment, "LEFT"

    def _saveIconSignal(self):
        legend = self.getActiveCurve(just_legend=True)
        if legend is None:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Please Select an active curve")
            msg.setWindowTitle('%s window' % self._plotType)
            msg.exec()
            return
        output = self._getOutputFileNameAndFilter()
        if output is None:
            return
        outputFile, outputFilter = output
        try:
            self.saveOperation(outputFile, outputFilter)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Save error")
            msg.setInformativeText("Saving Error: %s" %
                                   (sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def saveOperation(self, outputFile, outputFilter):
        filterused = outputFilter.split()
        filetype = filterused[1]
        extension = filterused[-1]
        specFile = outputFile
        if os.path.exists(specFile):
            os.remove(specFile)

        # WIDGET format
        fformat = specFile[-3:].upper()
        if filterused[0].upper().startswith("WIDGET"):
            if hasattr(qt.QPixmap, "grabWidget"):
                pixmap = qt.QPixmap.grabWidget(self.getWidgetHandle())
            else:
                pixmap = self.getWidgetHandle().grab()
            if not pixmap.save(specFile, fformat):
                qt.QMessageBox.critical(
                        self,
                        "Save Error",
                        "%s" % "I could not save the file\nwith the desired format")
            return

        # GRAPHICS format
        if fformat in ['EPS', 'PNG', 'SVG']:
            try:
                self._graphicsSave(plot=self, filename=specFile)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Save error")
                msg.setInformativeText("Graphics Saving Error: %s" %
                                       (sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
            return

        # TEXT based formats

        # This was giving problems on legends with a leading b
        # legend = legend.strip('<b>')
        # legend = legend.strip('<\b>')
        x, y, legend, info = self.getActiveCurve()[:4]
        xlabel = info.get("xlabel", "X")
        ylabel = info.get("ylabel", "Y")

        try:
            systemline = os.linesep
            os.linesep = '\n'
            if sys.version < "3.0":
                ffile = open(specFile, 'wb')
            else:
                ffile = open(specFile, 'w', newline='')
            if filetype in ['Scan', 'MultiScan']:
                ffile.write("#F %s\n" % specFile)
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
                    for curve in curveList:
                        x, y, key, info = curve[:4]
                        if key == legend:
                            continue
                        xlabel = info.get("xlabel", "X")
                        ylabel = info.get("ylabel", "Y")
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
                ffile.write("#F %s\n" % specFile)
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

    def _getOutputFileNameAndFilter(self, format_list=None):
        """
        returns outputfile, file type and filter used
        """
        # get outputfile
        self.outputDir = PyMcaDirs.outputDir
        if self.outputDir is None:
            self.outputDir = os.getcwd()
            wdir = os.getcwd()
        elif os.path.exists(self.outputDir):
            wdir = self.outputDir
        else:
            self.outputDir = os.getcwd()
            wdir = self.outputDir
        if format_list is None:
            format_list = ['Specfile MCA  *.mca',
                           'Specfile Scan *.dat']
            if self._plotType != "MCA":
                format_list += ['Specfile MultiScan *.dat']
            format_list += ['Raw ASCII *.txt',
                            '","-separated CSV *.csv',
                            '";"-separated CSV *.csv',
                            '"tab"-separated CSV *.csv',
                            'OMNIC CSV *.csv',
                            'Widget PNG *.png',
                            'Widget JPG *.jpg',
                            'Graphics PNG *.png',
                            'Graphics EPS *.eps',
                            'Graphics SVG *.svg']
        if self.outputFilter is None:
            self.outputFilter = format_list[0]
        fileList, fileFilter = PyMcaFileDialogs.getFileList(
                                     self,
                                     filetypelist=format_list,
                                     message="Output File Selection",
                                     currentdir=wdir,
                                     single=True,
                                     mode="SAVE",
                                     getfilter=True,
                                     currentfilter=self.outputFilter)
        if not len(fileList):
            return
        self.outputFilter = fileFilter
        filterused = self.outputFilter.split()
        filetype = filterused[1]
        extension = filterused[2]
        outdir = qt.safe_str(fileList[0])
        try:
            self.outputDir = os.path.dirname(outdir)
            PyMcaDirs.outputDir = os.path.dirname(outdir)
        except Exception:
            self.outputDir = "."
        try:
            outputFile = os.path.basename(outdir)
        except Exception:
            outputFile = outdir
        if len(outputFile) < 5:
            outputFile = outputFile + extension[-4:]
        elif outputFile[-4:] != extension[-4:]:
            outputFile = outputFile + extension[-4:]
        return os.path.join(self.outputDir, outputFile), fileFilter

def test():
    import numpy
    app = qt.QApplication([])
    w = ScanWindow(info=True)
    x = numpy.arange(1000.)
    y1 = 10 * x + 10000. * numpy.exp(-0.5*(x-500)*(x-500)/400)
    y2 = y1 + 5000. * numpy.exp(-0.5*(x-700)*(x-700)/200)
    y3 = y1 + 7000. * numpy.exp(-0.5*(x-200)*(x-200)/1000)
    w.addCurve(x, y1, legend="dummy1",
               info={"SourceName": "Synthetic data 1 (linear+gaussian)",
                     "hkl": [1.1, 1.2, 1.3],
                     "Header": ["#S 1 toto"]})
    w.addCurve(x, y2, legend="dummy2",
               info={"SourceName": "Synthetic data 2",
                     "hkl": [2.1, 2.2, 2.3],
                     "Header": ["#S 2"]})
    w.addCurve(x, y3, legend="dummy3",
               info={"SourceName": "Synthetic data 3",
                     "hkl": ["3.1", 3.2, 3.3],
                     "Header": ["#S 3"]})
    w.resetZoom()
    app.lastWindowClosed.connect(app.quit)
    w.show()
    app.exec()


if __name__ == "__main__":
    test()
