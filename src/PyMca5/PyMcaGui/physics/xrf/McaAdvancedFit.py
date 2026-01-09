#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import numpy
import time
import copy
import logging
import tempfile
import shutil
import traceback

from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str

QTVERSION = qt.qVersion()

from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave1D
MATPLOTLIB = True
#force understanding of utf-8 encoding
#otherways it cannot generate svg output
try:
    import encodings.utf_8
except Exception:
    #not a big problem
    pass

from PyMca5.PyMcaPhysics.xrf import ClassMcaTheory
FISX = ClassMcaTheory.FISX
if FISX:
    FisxHelper = ClassMcaTheory.FisxHelper
from PyMca5.PyMcaGui.physics.xrf import FitParam
from PyMca5.PyMcaGui.physics.xrf import McaAdvancedTable
from PyMca5.PyMcaGui.physics.xrf import QtMcaAdvancedFitReport
from PyMca5.PyMcaGui.physics.xrf import ConcentrationsWidget
from PyMca5.PyMcaPhysics.xrf import ConcentrationsTool
from PyMca5.PyMcaGui.plotting import PlotWindow
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.physics.xrf import McaCalWidget
from PyMca5.PyMcaGui.physics.xrf import PeakIdentifier
from PyMca5.PyMcaGui.misc import SubprocessLogWidget
from PyMca5.PyMcaGui.physics.xrf import ElementsInfo
Elements = ElementsInfo.Elements
#import McaROIWidget
from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaGui.misc import CalculationThread
from PyMca5.PyMcaGui.io import PyMcaFileDialogs

_logger = logging.getLogger(__name__)

_logger.debug("############################################\n"
              "#    McaAdvancedFit is in DEBUG mode       #\n"
              "############################################")
XRFMC_FLAG = False
try:
    from PyMca5.PyMcaPhysics.xrf.XRFMC import XRFMCHelper
    XRFMC_FLAG = True
except ImportError:
    _logger.warning("Cannot import XRFMCHelper module")
    if _logger.getEffectiveLevel() == logging.DEBUG:
        raise
USE_BOLD_FONT = True

class McaAdvancedFit(qt.QWidget):
    """
    This class inherits QWidget.

    It provides all the functionality required to perform an interactive fit
    and to generate a configuration file.

    It is the simplest way to embed PyMca's fitting functionality into other
    PyQt application.

    It can be used from the interactive prompt of ipython provided ipython is
    started with the -q4thread flag.

    **Usage**

    >>> from PyMca5 import McaAdvancedFit
    >>> w = McaAdvancedFit.McaAdvancedFit()
    >>> w.setData(x=x, y=y) # x is your channel array and y the counts array
    >>> w.show()

    """
    sigMcaAdvancedFitSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, name="PyMca - McaAdvancedFit",fl=0,
                 sections=None, top=True, margin=11, spacing=6):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.lastInputDir = None
        self.configDialog = None
        self.matplotlibDialog = None
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(margin, margin, margin, margin)
        self.mainLayout.setSpacing(0)
        if sections is None:
            sections=["TABLE"]
        self.headerLabel = qt.QLabel(self)
        self.mainLayout.addWidget(self.headerLabel)

        self.headerLabel.setAlignment(qt.Qt.AlignHCenter)
        font = self.font()
        font.setBold(USE_BOLD_FONT)
        self.headerLabel.setFont(font)
        self.setHeader('Fit of XXXXXXXXXX from Channel XXXXX to XXXX')
        self.top = Top(self)
        self.mainLayout.addWidget(self.top)
        self.sthread = None
        self.elementsInfo = None
        self.identifier   = None
        self.logWidget = None
        if False and len(sections) == 1:
            w = self
            self.mcatable  = McaAdvancedTable.McaTable(w)
            self.concentrationsWidget = None
        else:
            self.mainTab = qt.QTabWidget(self)
            self.mainLayout.addWidget(self.mainTab)
            #graph
            self.tabGraph  = qt.QWidget()
            tabGraphLayout = qt.QVBoxLayout(self.tabGraph)
            tabGraphLayout.setContentsMargins(margin, margin, margin, margin)
            tabGraphLayout.setSpacing(spacing)
            #self.graphToolbar  = qt.QHBox(self.tabGraph)
            self.graphWindow = McaGraphWindow(self.tabGraph)
            tabGraphLayout.addWidget(self.graphWindow)
            self.graph = self.graphWindow
            self.graph.setGraphXLabel('Channel')
            self.graph.setGraphYLabel('Counts')
            self.mainTab.addTab(self.tabGraph, "GRAPH")
            self.graphWindow.sigPlotSignal.connect(self._mcaGraphSignalSlot)
            #table
            self.tabMca  = qt.QWidget()
            tabMcaLayout = qt.QVBoxLayout(self.tabMca)
            tabMcaLayout.setContentsMargins(margin, margin, margin, margin)
            tabMcaLayout.setSpacing(spacing)
            w = self.tabMca
            line = Line(w, info="TABLE")
            tabMcaLayout.addWidget(line)

            line.setToolTip("DoubleClick toggles floating window mode")

            self.mcatable  = McaAdvancedTable.McaTable(w)
            tabMcaLayout.addWidget(self.mcatable)
            self.mainTab.addTab(w,"TABLE")
            line.sigLineDoubleClickEvent.connect(self._tabReparent)
            self.mcatable.sigClosed.connect(self._mcatableClose)

            #concentrations
            self.tabConcentrations  = qt.QWidget()
            tabConcentrationsLayout = qt.QVBoxLayout(self.tabConcentrations)
            tabConcentrationsLayout.setContentsMargins(margin,
                                                       margin,
                                                       margin,
                                                       margin)
            tabConcentrationsLayout.setSpacing(0)
            line2 = Line(self.tabConcentrations, info="CONCENTRATIONS")
            self.concentrationsWidget = ConcentrationsWidget.Concentrations(self.tabConcentrations)
            tabConcentrationsLayout.addWidget(line2)
            tabConcentrationsLayout.addWidget(self.concentrationsWidget)

            self.mainTab.addTab(self.tabConcentrations,"CONCENTRATIONS")
            line2.setToolTip("DoubleClick toggles floating window mode")
            self.concentrationsWidget.sigConcentrationsSignal.connect( \
                        self.__configureFromConcentrations)
            line2.sigLineDoubleClickEvent.connect(self._tabReparent)
            self.concentrationsWidget.sigClosed.connect( \
                            self._concentrationsWidgetClose)

            #diagnostics
            self.tabDiagnostics  = qt.QWidget()
            tabDiagnosticsLayout = qt.QVBoxLayout(self.tabDiagnostics)
            tabDiagnosticsLayout.setContentsMargins(margin, margin, margin, margin)
            tabDiagnosticsLayout.setSpacing(spacing)
            w = self.tabDiagnostics
            self.diagnosticsWidget = qt.QTextEdit(w)
            self.diagnosticsWidget.setReadOnly(1)

            tabDiagnosticsLayout.addWidget(self.diagnosticsWidget)
            self.mainTab.addTab(w, "DIAGNOSTICS")
            self.mainTab.currentChanged[int].connect(self._tabChanged)

        self._energyAxis = False
        self.__printmenu = qt.QMenu()
        self.__printmenu.addAction(QString("Calibrate"),     self._calibrate)
        self.__printmenu.addAction(QString("Identify Peaks"),self.__peakIdentifier)
        self.__printmenu.addAction(QString("Elements Info"), self.__elementsInfo)
        self.outdir      = None
        self.configDir   = None
        self.__lastreport= None
        self.browser     = None
        self.info        = {}
        self.__fitdone   = 0
        self._concentrationsDict = None
        self._concentrationsInfo = None
        self._xrfmcMatrixSpectra = None
        #self.graph.hide()
        #self.guiconfig = FitParam.Fitparam()
        """
        self.specfitGUI.guiconfig.MCACheckBox.setEnabled(0)
        palette = self.specfitGUI.guiconfig.MCACheckBox.palette()
        palette.setDisabled(palette.active())
        """
        ##############
        hbox=qt.QWidget(self)
        self.bottom = hbox
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(4)
        if not top:
            self.configureButton = qt.QPushButton(hbox)
            self.configureButton.setText("Configure")
            self.toolsButton = qt.QPushButton(hbox)
            self.toolsButton.setText("Tools")
            hboxLayout.addWidget(self.configureButton)
            hboxLayout.addWidget(self.toolsButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        self.fitButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.fitButton)
        #font = self.fitButton.font()
        #font.setBold(True)
        #self.fitButton.setFont(font)
        self.fitButton.setText("Fit Again!")
        self.printButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.printButton)
        self.printButton.setText("Print")
        self.htmlReportButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.htmlReportButton)
        self.htmlReportButton.setText("HTML Report")
        self.matrixSpectrumButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.matrixSpectrumButton)
        self.matrixSpectrumButton.setText("Matrix Spectrum")
        self.matrixXRFMCSpectrumButton = qt.QPushButton(hbox)
        self.matrixXRFMCSpectrumButton.setText("MC Matrix Spectrum")
        hboxLayout.addWidget(self.matrixXRFMCSpectrumButton)
        self.matrixXRFMCSpectrumButton.hide()
        self.peaksSpectrumButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.peaksSpectrumButton)
        self.peaksSpectrumButton.setText("Peaks Spectrum")
        self.matrixSpectrumButton.setCheckable(1)
        self.peaksSpectrumButton.setCheckable(1)

        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        self.dismissButton = qt.QPushButton(hbox)
        hboxLayout.addWidget(self.dismissButton)
        self.dismissButton.setText("Dismiss")
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))

        self.mainLayout.addWidget(hbox)
        self.printButton.setToolTip('Print Active Tab')
        self.htmlReportButton.setToolTip('Generate Browser Compatible Output\nin Chosen Directory')
        self.matrixSpectrumButton.setToolTip('Toggle Matrix Spectrum Calculation On/Off')
        self.matrixXRFMCSpectrumButton.setToolTip('Calculate Matrix Spectrum Using Monte Carlo')
        self.peaksSpectrumButton.setToolTip('Toggle Individual Peaks Spectrum Calculation On/Off')

        self.mcafit = ClassMcaTheory.McaTheory()

        self.fitButton.clicked.connect(self.fit)
        self.printButton.clicked.connect(self.printActiveTab)
        self.htmlReportButton.clicked.connect(self.htmlReport)
        self.matrixSpectrumButton.clicked.connect(self.__toggleMatrixSpectrum)
        if self.matrixXRFMCSpectrumButton is not None:
            self.matrixXRFMCSpectrumButton.clicked.connect(self.xrfmcSpectrum)
        self.peaksSpectrumButton.clicked.connect(self.__togglePeaksSpectrum)
        self.dismissButton.clicked.connect(self.dismiss)
        self.top.configureButton.clicked.connect(self.__configure)
        self.top.printButton.clicked.connect(self.__printps)
        if top:
            self.top.sigTopSignal.connect(self.__updatefromtop)
        else:
            self.top.hide()
            self.configureButton.clicked.connect(self.__configure)
            self.toolsButton.clicked.connect(self.__printps)
        self._updateTop()

    def __mainTabPatch(self, index):
        return self.mainTabLabels[index]

    def _fitdone(self):
        if self.__fitdone:
            return True
        else:
            return False

    def refreshWidgets(self):
        """
        This method just forces the graphical widgets to get updated.
        It should be called if somehow you have modified the fit and/
        or concentrations parameters by other means than the graphical
        interface.
        """
        self.__configure(justupdate=True)

    def configure(self, ddict=None):
        """
        This methods configures the fitting parameters and updates the
        graphical interface.

        It returns the current configuration.
        """
        if ddict is None:
            return self.mcafit.configure(ddict)

        #configure and get the new configuration
        newConfig = self.mcafit.configure(ddict)

        #refresh the interface
        self.refreshWidgets()

        #return the current configuration
        return newConfig

    def __configure(self, justupdate=False):
        config = {}
        config.update(self.mcafit.config)
        #config['fit']['use_limit'] = 1
        if not justupdate:
            if self.configDialog is None:
                if self.__fitdone:
                    dialog = FitParam.FitParamDialog(modal=1,
                                                     fl=0,
                                                     initdir=self.configDir,
                                                     fitresult=self.dict['result'])
                else:
                    dialog = FitParam.FitParamDialog(modal=1,
                                                     fl=0,
                                                     initdir=self.configDir,
                                                     fitresult=None)
                dialog.fitparam.peakTable.sigFitPeakSelect.connect( \
                             self.__elementclicked)
                self.configDialog = dialog
            else:
                dialog = self.configDialog
                if self.__fitdone:
                    dialog.setFitResult(self.dict['result'])
                else:
                    dialog.setFitResult(None)
            if self.__fitdone:
                # a direct fit without loading the file can lead to errors
                lastTime = self.mcafit.getLastTime()
                self.info["time"] = lastTime

            dialog.setParameters(self.mcafit.getStartingConfiguration())
            dialog.setData(self.mcafit.xdata * 1.0,
                           self.mcafit.ydata * 1.0,
                           info=copy.deepcopy(self.info))

            #dialog.fitparam.regionCheck.setDisabled(True)
            #dialog.fitparam.minSpin.setDisabled(True)
            #dialog.fitparam.maxSpin.setDisabled(True)
            ret = dialog.exec()
            if dialog.initDir is not None:
                self.configDir = 1 * dialog.initDir
            else:
                self.configDir = None
            if ret != qt.QDialog.Accepted:
                dialog.close()
                #del dialog
                return
            try:
                #this may crash in qt 2.3.0
                npar = dialog.getParameters()
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error occured getting parameters:")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
            config.update(npar)
            dialog.close()
            #del dialog

        self.graph.clearMarkers()
        self.graph.replot()
        self.__fitdone = False
        self._concentrationsDict = None
        self._concentrationsInfo = None
        self._xrfmcMatrixSpectra = None
        if self.concentrationsWidget is not None:
            self.concentrationsWidget.concentrationsTable.setRowCount(0)
        if self.mcatable is not None:
            self.mcatable.setRowCount(0)
        self.diagnosticsWidget.clear()


        #make sure newly or redefined materials are added to the
        #materials in the fit configuration
        for material in Elements.Material.keys():
            self.mcafit.config['materials'][material] =copy.deepcopy(Elements.Material[material])

        hideButton = True
        if 'xrfmc' in config:
            programFile = config['xrfmc'].get('program', None)
            if programFile is not None:
                if os.path.exists(programFile):
                    if os.path.isfile(config['xrfmc']['program']):
                        hideButton = False
        if hideButton:
            self.matrixXRFMCSpectrumButton.hide()
        else:
            self.matrixXRFMCSpectrumButton.show()

        if _logger.getEffectiveLevel() == logging.DEBUG:
            self.mcafit.configure(config)
        else:
            try:
                thread = CalculationThread.CalculationThread( \
                                      calculation_method = self.mcafit.configure,
                                      calculation_vars = config,
                                      expand_vars=False,
                                      expand_kw=False)
                thread.start()
                CalculationThread.waitingMessageDialog(thread,
                                    message = "Configuring, please wait",
                                    parent=self,
                                    modal=True,
                                    update_callback=None,
                                    frameless=True)
                threadResult = thread.getResult()
                if type(threadResult) == type((1,)):
                    if len(threadResult):
                        if threadResult[0] == "Exception":
                            raise Exception(threadResult[1], threadResult[2])
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Configuration error")
                msg.setText("Error configuring fit:")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return

        #update graph
        delcurves = []
        curveList = self.graph.getAllCurves(just_legend=True)
        for key in curveList:
            if key not in ["Data"]:
                delcurves.append(key)
        for key in delcurves:
            self.graph.removeCurve(key)

        if not justupdate:
            self.plot()


        self._updateTop()
        if self.concentrationsWidget is not None:
            try:
                app = qt.QApplication.instance()
                app.processEvents()
                self.concentrationsWidget.setParameters(config['concentrations'], signal=False)
            except Exception:
                if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "CONCENTRATIONS":
                    self.mainTab.setCurrentIndex(0)

    def __configureFromConcentrations(self,ddict):
        _logger.debug("McaAdvancedFit.__configureFromConcentrations %s", ddict)
        config = self.concentrationsWidget.getParameters()
        self.mcafit.config['concentrations'].update(config)
        if ddict['event'] == 'updated':
            if 'concentrations' in ddict:
                self._concentrationsDict = ddict['concentrations']
                self._concentrationsInfo = None
                self._xrfmcMatrixSpectra = None

    def __elementclicked(self,ddict):
        ddict['event'] = 'McaAdvancedFitElementClicked'
        self.__showElementMarker(ddict)
        self.__anasignal(ddict)

    def __showElementMarker(self, dict):
        self.graph.clearMarkers()
        ele = dict['current']
        items = []
        if not (ele in dict):
            self.graph.replot()
            return
        for rays in dict[ele]:
            for transition in Elements.Element[ele][rays +" xrays"]:
                items.append([transition,
                              Elements.Element[ele][transition]['energy'],
                              Elements.Element[ele][transition]['rate']])

        config = self.mcafit.configure()
        xdata  = self.mcafit.xdata * 1.0
        xmin = xdata[0]
        xmax = xdata[-1]
        ymin,ymax = self.graph.getGraphYLimits()
        calib = [config['detector'] ['zero'], config['detector'] ['gain']]
        for transition,energy,rate in items:
            marker = ""
            x = (energy - calib[0])/calib[1]
            if (x < xmin) or (x > xmax):continue
            if not self._energyAxis:
                if abs(calib[1]) > 0.0000001:
                    marker=self.graph.insertXMarker(x,
                                                    legend=transition,
                                                    text=transition,
                                                    color='orange',
                                                    replot=False)
            else:
                marker=self.graph.insertXMarker(energy,
                                                legend=transition,
                                                text=transition,
                                                color='orange',
                                                replot=False)
        self.graph.replot()

    def _updateTop(self):
        config = {}
        if 0:
            config.update(self.mcafit.config['fit'])
        else:
            config['stripflag']    = self.mcafit.config['fit'].get('stripflag',0)
            config['fitfunction'] = self.mcafit.config['fit'].get('fitfunction',0)
            config['hypermetflag'] = self.mcafit.config['fit'].get('hypermetflag',1)
            config['sumflag']      = self.mcafit.config['fit'].get('sumflag',0)
            config['escapeflag']   = self.mcafit.config['fit'].get('escapeflag',0)
            config['continuum']    = self.mcafit.config['fit'].get('continuum',0)
        self.top.setParameters(config)

    def __updatefromtop(self,ndict):
        config = self.mcafit.configure()
        for key in ndict.keys():
            if key not in ['stripflag', 'hypermetflag',
                           'sumflag', 'escapeflag',
                           'fitfunction', 'continuum']:
                _logger.debug("UNKNOWN key %s", key)
            config['fit'][key] = ndict[key]
        self.__fitdone = False
        #erase table
        if self.mcatable is not None:
            self.mcatable.setRowCount(0)
        #erase concentrations
        if self.concentrationsWidget is not None:
            self.concentrationsWidget.concentrationsTable.setRowCount(0)
        #erase diagnostics
        self.diagnosticsWidget.clear()
        #update graph
        curveList = self.graph.getAllCurves(just_legend=True)
        delcurves = []
        for key in curveList:
            if key not in ["Data"]:
                delcurves.append(key)
        for key in delcurves:
            self.graph.removeCurve(key)
        self.plot()

        if _logger.getEffectiveLevel() == logging.DEBUG:
            self.mcafit.configure(config)
        else:
            try:
                thread = CalculationThread.CalculationThread( \
                                      calculation_method = self.mcafit.configure,
                                      calculation_vars = config,
                                      expand_vars=False,
                                      expand_kw=False)
                thread.start()
                CalculationThread.waitingMessageDialog(thread,
                                    message = "Configuring, please wait",
                                    parent=self,
                                    modal=True,
                                    update_callback=None)
                threadResult = thread.getResult()
                if type(threadResult) == type((1,)):
                    if len(threadResult):
                        if threadResult[0] == "Exception":
                            raise Exception(threadResult[1], threadResult[2])
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Configuration error")
                msg.setText("Error configuring fit:")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return

    def _tabChanged(self, value):
        _logger.debug("_tabChanged(self, value) called")
        if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "CONCENTRATIONS":
            self.printButton.setEnabled(False)
            w = self.concentrationsWidget
            if w.parent() is None:
                if w.isHidden():
                    w.show()
                w.raise_()
                self.printButton.setEnabled(True)
                #do not calculate again. It should be already updated
                return
            try:
                self.concentrations()
                self.printButton.setEnabled(True)
            except Exception:
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                #print "try to set"
                self.printButton.setEnabled(False)
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Concentrations error: %s" % sys.exc_info()[1])
                msg.exec()
                self.mainTab.setCurrentIndex(0)
        elif str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "TABLE":
            self.printButton.setEnabled(True)
            w = self.mcatable
            if w.parent() is None:
                if w.isHidden():
                    w.show()
                w.raise_()
        elif str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "DIAGNOSTICS":
            self.printButton.setEnabled(False)
            self.diagnostics()
        else:
            self.printButton.setEnabled(True)

    def _concentrationsWidgetClose(self, ddict):
        ddict['info'] = "CONCENTRATIONS"
        self._tabReparent(ddict)

    def _mcatableClose(self, ddict):
        ddict['info'] = "TABLE"
        self._tabReparent(ddict)

    def _tabReparent(self, ddict):
        if ddict['info'] == "CONCENTRATIONS":
            w = self.concentrationsWidget
            parent = self.tabConcentrations
        elif ddict['info'] == "TABLE":
            w = self.mcatable
            parent = self.tabMca
        if w.parent() is not None:
            parent.layout().removeWidget(w)
            w.setParent(None)
            w.show()
        else:
            w.setParent(parent)
            parent.layout().addWidget(w)

    def _calibrate(self):
        config = self.mcafit.configure()
        x = self.mcafit.xdata0[:]
        y = self.mcafit.ydata0[:]
        legend = "Calibration for " + qt.safe_str(self.headerLabel.text())
        ndict={}
        ndict[legend] = {'A':config['detector']['zero'],
               'B':config['detector']['gain'],
               'C': 0.0}
        caldialog = McaCalWidget.McaCalWidget(legend=legend,
                                                     x=x,
                                                     y=y,
                                                     modal=1,
                                                     caldict=ndict,
                                                     fl=0)
        caldialog.calpar.orderbox.setEnabled(0)
        caldialog.calpar.CText.setEnabled(0)
        caldialog.calpar.savebox.setEnabled(0)
        ret = caldialog.exec()
        if ret == qt.QDialog.Accepted:
            ddict = caldialog.getDict()
            config['detector']['zero'] = ddict[legend]['A']
            config['detector']['gain'] = ddict[legend]['B']
            #self.mcafit.configure(config)
            self.mcafit.config['detector']['zero'] = 1. * ddict[legend]['A']
            self.mcafit.config['detector']['gain'] = 1. * ddict[legend]['B']
            self.__fitdone = 0
            self.plot()
        del caldialog

    def __elementsInfo(self):
        if self.elementsInfo is None:
            self.elementsInfo = ElementsInfo.ElementsInfo(None, "Elements Info")
        if self.elementsInfo.isHidden():
           self.elementsInfo.show()
        self.elementsInfo.raise_()

    def __peakIdentifier(self, energy = None):
        if energy is None:
            energy = 5.9
        if self.identifier is None:
            self.identifier=PeakIdentifier.PeakIdentifier(energy=energy,
                                                          threshold=0.040,
                                                          useviewer=1)
            self.identifier.mySlot()
        self.identifier.setEnergy(energy)
        if self.identifier.isHidden():
            self.identifier.show()
        self.identifier.raise_()

    def printActiveTab(self):
        txt = str(self.mainTab.tabText(self.mainTab.currentIndex())).upper()
        if txt == "GRAPH":
            self.graphWindow.printGraph()
        elif txt == "TABLE":
            self.printps(True)
        elif txt == "CONCENTRATIONS":
            self.printConcentrations(True)
        elif txt == "DIAGNOSTICS":
            pass
        else:
            pass

    def diagnostics(self):
        self.diagnosticsWidget.clear()
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Sorry. You need to perform a fit first.\n"
            msg.setText(text)
            msg.exec()
            if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "DIAGNOSTICS":
                self.mainTab.setCurrentIndex(0)
            return
        fitresult = self.dict
        x = fitresult['result']['xdata']
        energy = fitresult['result']['energy']
        y = fitresult['result']['ydata']
        yfit = fitresult['result']['yfit']
        param = fitresult['result']['fittedpar']
        i    = fitresult['result']['parameters'].index('Noise')
        noise= param[i] * param[i]
        i    = fitresult['result']['parameters'].index('Fano')
        fano = param[i] * 2.3548*2.3548*0.00385
        meanfwhm = numpy.sqrt(noise + 0.5 * (energy[0] + energy[-1]) * fano)
        i = fitresult['result']['parameters'].index('Gain')
        gain = fitresult['result']['fittedpar'][i]
        meanfwhm = int(meanfwhm/gain) + 1
        missed =  self.mcafit.detectMissingPeaks(y, yfit, meanfwhm)
        hcolor = 'white'
        finalcolor = 'white'
        text=""
        if len(missed):
            text+="<br><b><font color=blue size=4>Possibly Missing or Underestimated Peaks</font></b>"
            text+="<nobr><table><tr>"
            text+='<td align="right" bgcolor="%s"><b>' % hcolor
            text+='Channel'
            text+="</b></td>"
            text+='<td align="right" bgcolor="%s"><b>' % hcolor
            text+='Energy'
            text+="</b></td>"
            text+="</tr>"
            for peak in missed:
                text+="<tr>"
                text+='<td align="right" bgcolor="%s">' % finalcolor
                text+="<b><font size=3>%d </font></b>"  % x[int(peak)]
                text+="</td>"
                text+='<td align="right" bgcolor="%s">' % finalcolor
                text+="<b><font size=3>%.3f </font></b>"  % energy[int(peak)]
                text+="</td>"
            text+="</tr>"
            text+="<tr>"
            text+="</table>"
        missed =  self.mcafit.detectMissingPeaks(yfit, y, meanfwhm)
        if len(missed):
            text+="<br><b><font color=blue size=4>Possibly Overestimated Peaks</font></b>"
            text+="<nobr><table><tr>"
            text+='<td align="right" bgcolor="%s"><b>' % hcolor
            text+='Channel'
            text+="</b></td>"
            text+='<td align="right" bgcolor="%s"><b>' % hcolor
            text+='Energy'
            text+="</b></td>"
            text+="</tr>"
            for peak in missed:
                text+="<tr>"
                text+='<td align="right" bgcolor="%s">' % finalcolor
                text+="<b><font size=3>%d </font></b>"  % x[int(peak)]
                text+="</td>"
                text+='<td align="right" bgcolor="%s">' % finalcolor
                text+="<b><font size=3>%.3f </font></b>"  % energy[int(peak)]
                text+="</td>"
            text+="</tr>"
            text+="<tr>"
            text+="</table>"

        # check for secondary effects
        useMatrix = False
        for attenuator in fitresult['result']['config']['attenuators']:
            if attenuator.upper() == "MATRIX":
                if fitresult['result']['config']['attenuators'][attenuator][0]:
                    useMatrix = True
                    break
        if useMatrix and FISX and \
           (not fitresult['result']['config']['concentrations']['usemultilayersecondary']):
            doIt = False
            corrections = None
            if 'fisx' in fitresult['result']['config']:
                corrections = fitresult['result']['config']['fisx'].get('corrections',
                                                                        None)
            if corrections is None:
                # calculate the corrections
                corrections = FisxHelper.getFisxCorrectionFactorsFromFitConfiguration( \
                                        fitresult['result']['config'],
                                        elementsFromMatrix=False)
                # to put it into config is misleading because it was not made at
                # configuration time.
                if 'fisx' not in fitresult['result']['config']:
                    fitresult['result']['config']['fisx'] = {}
                    fitresult['result']['config']['fisx']['secondary'] = 2
                fitresult['result']['config']['fisx']['corrections'] = corrections
            tertiary = False
            bodyText = ""
            for element in corrections:
                for family in corrections[element]:
                    correction = corrections[element][family]['correction_factor']
                    if correction[-1] > 1.02:
                        doIt = True
                        bodyText += "<tr>"
                        bodyText += '<td align="right" bgcolor="%s">' % finalcolor
                        bodyText += "<b><font size=3>%s&nbsp;&nbsp;</font></b>"  % \
                                              (element + " " + family)
                        bodyText += "</td>"
                        bodyText += '<td align="right" bgcolor="%s">' % finalcolor
                        bodyText += "<b><font size=3>"
                        bodyText += "%.3f</font></b>"  % correction[1]
                        bodyText += "&nbsp;&nbsp;&nbsp;"
                        if len(corrections[element][family]['correction_factor']) > 2:
                            tertiary = True
                            bodyText+= "</td>"
                            bodyText += '<td align="right" bgcolor="%s">' % finalcolor
                            bodyText += "<b><font size=3>"
                            bodyText+= "%.3f </font></b>"  % correction[2]
                            bodyText += "&nbsp;&nbsp;&nbsp;"
                        bodyText+= "</td>"
                        bodyText+= "</tr>"
            if doIt:
                bodyText += "<tr>"
                bodyText += "</table>"
                warningText  = "<br><b><font color=blue size=4>"
                warningText += "Neglected higher order excitation correction</font></b>"
                warningText += "<nobr><table>"
                warningText += "<tr>"
                warningText += '<td align="right" bgcolor="%s"><b>' % hcolor
                warningText += 'Peak Family'
                warningText += "</b></td>"
                warningText += '<td align="right" bgcolor="%s"><b>' % hcolor
                warningText += ('&nbsp;' * 10)
                warningText += '2nd Order'
                warningText += "</b></td>"
                if tertiary:
                    warningText += '<td align="right" bgcolor="%s"><b>' % hcolor
                    warningText += ('&nbsp;' * 10)
                    warningText += '3rd Order'
                    warningText += "</b></td>"
                warningText += "</tr>"
                text += (warningText + bodyText)
        self.diagnosticsWidget.insertHtml(text)

    def concentrations(self):
        self._concentrationsDict = None
        self._concentrationsInfo = None
        self._xrfmcMatrixSpectra = None
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Sorry, You need to perform a fit first.\n"
            msg.setText(text)
            msg.exec()
            if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == "CONCENTRATIONS":
                self.mainTab.setCurrentIndex(0)
            return
        fitresult = self.dict
        if False:
            #from the fit, it misses any update from concentrations
            config = fitresult['result']['config']
        else:
            #from current, it should be up to date
            config = self.mcafit.configure()
        #tool = ConcentrationsWidget.Concentrations(fl=qt.Qt.WDestructiveClose)
        if self.concentrationsWidget is None:
           self.concentrationsWidget = ConcentrationsWidget.Concentrations()
           self.concentrationsWidget.sigConcentrationsSignal.connect( \
                        self.__configureFromConcentrations)
        self.concentrationsWidget.setTimeFactor(self.mcafit.getLastTime(), signal=False)
        tool = self.concentrationsWidget
        #this forces update
        tool.getParameters()
        ddict = {}
        ddict.update(config['concentrations'])
        tool.setParameters(ddict, signal=False)
        try:
            ddict, info = tool.processFitResult(config=ddict, fitresult=fitresult,
                                                elementsfrommatrix=False,
                                                fluorates=self.mcafit._fluoRates,
                                                addinfo=True)
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error processing fit result: %s" % (sys.exc_info()[1]))
            msg.exec()
            if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == 'CONCENTRATIONS':
                self.mainTab.setCurrentIndex(0)
            return
        self._concentrationsDict = ddict
        self._concentrationsInfo = info
        tool.show()
        tool.setFocus()
        tool.raise_()

    def __toggleMatrixSpectrum(self):
        if self.matrixSpectrumButton.isChecked():
            self.matrixSpectrum()
            self.plot()
        else:
            if "Matrix" in self.graph.getAllCurves(just_legend=True):
                self.graph.removeCurve("Matrix", replot=False)
                self.plot()

    def __togglePeaksSpectrum(self):
        if self.peaksSpectrumButton.isChecked():
            self.peaksSpectrum()
        else:
            self.__clearPeaksSpectrum()
        self.plot()

    def __clearPeaksSpectrum(self):
        delcurves = []
        for key in self.graph.getAllCurves(just_legend=True):
            if key not in ["Data", "Fit", "Continuum", "Pile-up", "Matrix"]:
                if key.startswith('MC Matrix'):
                    if self._xrfmcMatrixSpectra in [None, []]:
                        delcurves.append(key)
                else:
                    delcurves.append(key)
        for key in delcurves:
            self.graph.removeCurve(key, replot=False)


    def matrixSpectrum(self):
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Sorry, for the time being you need to perform a fit first\n"
            text+= "in order to calculate the spectrum derived from the matrix.\n"
            text+= "Background and detector parameters are taken from last fit"
            msg.setText(text)
            msg.exec()
            return
        #fitresult = self.dict['result']
        fitresult = self.dict
        config = self.mcafit.configure()
        self._concentrationsInfo = None
        tool   = ConcentrationsTool.ConcentrationsTool()
        #this forces update
        tool.configure()
        ddict = {}
        ddict.update(config['concentrations'])
        tool.configure(ddict)
        if _logger.getEffectiveLevel() == logging.DEBUG:
            ddict, info = tool.processFitResult(fitresult=fitresult,
                                                elementsfrommatrix=True,
                                                addinfo=True)
        else:
            try:
                thread = CalculationThread.CalculationThread(
                                      calculation_method=tool.processFitResult,
                                      calculation_kw={'fitresult': fitresult,
                                                      'elementsfrommatrix': True,
                                                      'addinfo': True},
                                      expand_vars=True,
                                      expand_kw=True)
                thread.start()
                CalculationThread.waitingMessageDialog(thread,
                                    message = "Calculating Matrix Spectrum",
                                    parent=self,
                                    modal=True,
                                    update_callback=None)
                threadResult = thread.getResult()
                if type(threadResult) == type((1,)):
                    if len(threadResult):
                        if threadResult[0] == "Exception":
                            raise Exception(threadResult[1], threadResult[2])
                ddict, info = threadResult
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error: %s" % (sys.exc_info()[1]))
                msg.exec()
                return

        self._concentrationsInfo = info
        groupsList = fitresult['result']['groups']

        if type(groupsList) != type([]):
            groupsList = [groupsList]
        corrections = None
        if fitresult['result']['config']['concentrations']['usemultilayersecondary']:
            if 'fisx' in fitresult:
                corrections = fitresult['fisx'].get('corrections', None)
            if corrections is None:
                # try to see if they were in the configuration
                # in principle this would be the most appropriate place to be
                # unless matrix/configuration has been somehow updated.
                if 'fisx' in fitresult['result']['config']:
                    corrections = fitresult['result']['config']['fisx'].get('corrections',
                                                                            None)
            if corrections is None:
                # calculate the corrections
                # in principle I should never get here
                corrections = FisxHelper.getFisxCorrectionFactorsFromFitConfiguration( \
                                        fitresult['result']['config'])
        areas = []
        for group in groupsList:
            item = group.split()
            element = item[0]
            if len(element) >2:
                areas.append(0.0)
            else:
                area = ddict['area'][group]
                if corrections is not None:
                    if element in corrections:
                        area *= corrections[element][item[1]]['counts'][-1] / \
                            corrections[element][item[1]]['counts'][0]
                areas.append(area)
        nglobal    = len(fitresult['result']['parameters']) - len(groupsList)
        parameters = []
        for i in range(len(fitresult['result']['parameters'])):
            if i < nglobal:
                parameters.append(fitresult['result']['fittedpar'][i])
            else:
                parameters.append(areas[i-nglobal])

        xmatrix = fitresult['result']['xdata']
        ymatrix = self.mcafit.mcatheory(parameters,xmatrix)
        ymatrix = ymatrix.reshape(len(ymatrix), 1)
        ddict=copy.deepcopy(self.dict)
        ddict['event'] = "McaAdvancedFitMatrixFinished"
        if self.mcafit.STRIP:
            ddict['result']['ymatrix']  = ymatrix + self.mcafit.zz
        else:
            ddict['result']['ymatrix']  = ymatrix
        ddict['result']['ymatrix'].shape  = (len(ddict['result']['ymatrix']),)
        ddict['result']['continuum'].shape  = (len(ddict['result']['ymatrix']),)
        if self.matrixSpectrumButton.isChecked():
            self.dict['result']['ymatrix']= ddict['result']['ymatrix'] * 1.0
        """
        if self.graph is not None:
            if self._logY:
                logfilter = 1
            else:
                logfilter = 0
            if self._energyAxis:
                xdata = dict['result']['energy'][:]
            else:
                xdata = dict['result']['xdata'][:]
            self.graph.newCurve("Matrix",xdata,dict['result']['ymatrix'],logfilter=logfilter)
        """
        try:
            self.__anasignal(ddict)
        except Exception:
            _logger.warning("Error generating matrix output. ")
            _logger.warning("Try to perform your fit again.  ")
            _logger.warning("%s" % sys.exc_info())
            _logger.warning("If error persists, please report this error.")
            _logger.warning("ymatrix shape = %s" % ddict['result']['ymatrix'].shape)
            _logger.warning("xmatrix shape = %s" % xmatrix.shape)
            _logger.warning("continuum shape = %s" % ddict['result']['continuum'].shape)
            _logger.warning("zz      shape = %s" % self.mcafit.zz.shape)

    def fisxSpectrum(self):
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Sorry, current implementation requires you to perform a fit first\n"
            msg.setText(text)
            msg.exec()
            return
        self._xrfmcMatrixSpectra = None
        fitresult = self.dict
        self._fisxMatrixSpectra = None
        if self._concentrationsInfo is None:
            # concentrations have to be calculated too
            self.concentrations()

        # force fisx to work on fundamental parameters mode
        fitConfiguration = copy.deepcopy(self.dict['result']["config"])
        fitConfiguration['concentrations']['usematrix'] = 0
        fitConfiguration['concentrations']['flux'] = self._concentrationsInfo['Flux']
        fitConfiguration['concentrations']['time'] = self._concentrationsInfo['Time']


        # calculate expected fluorescence signal from elements present in the sample
        correctionFactors = FisxHelper.getFisxCorrectionFactorsFromFitConfiguration( \
                                                            fitConfiguration,
                                                            elementsFromMatrix=True)
        groupsList = fitresult['result']['groups']
        if type(groupsList) != type([]):
            groupsList = [groupsList]

        areas0 = []
        areas1 = []
        for group in groupsList:
            item = group.split()
            element = item[0]
            if element not in correctionFactors:
                areas0.append(0.0)
                areas1.append(0.0)
            else:
                if len(element) >2:
                    areas0.append(0.0)
                    areas1.append(0.0)
                else:
                    # transitions = item[1] + " xrays"
                    areas0.append(correctionFactors[element][item[1]]['counts'][0] * \
                                 self._concentrationsInfo['Flux'] * self._concentrationsInfo['Time'] * \
                                 self._concentrationsInfo['SolidAngle'])
                    areas1.append(correctionFactors[element][item[1]]['counts'][1] * \
                                 self._concentrationsInfo['Flux'] * self._concentrationsInfo['Time'] * \
                                 self._concentrationsInfo['SolidAngle'])

        # primary
        nglobal    = len(fitresult['result']['parameters']) - len(groupsList)
        parameters = []
        for i in range(len(fitresult['result']['parameters'])):
            if i < nglobal:
                parameters.append(fitresult['result']['fittedpar'][i])
            else:
                parameters.append(areas0[i-nglobal])
        xmatrix = fitresult['result']['xdata']
        ymatrix0 = self.mcafit.mcatheory(parameters, xmatrix)
        ymatrix0 = ymatrix0.reshape(len(ymatrix0), 1)

        #secondary
        nglobal    = len(fitresult['result']['parameters']) - len(groupsList)
        parameters = []
        for i in range(len(fitresult['result']['parameters'])):
            if i < nglobal:
                parameters.append(fitresult['result']['fittedpar'][i])
            else:
                parameters.append(areas1[i-nglobal])
        ymatrix1 = self.mcafit.mcatheory(parameters, xmatrix)
        ymatrix1 = ymatrix1.reshape(len(ymatrix1), 1)

        zeroindex = fitresult['result']['parameters'].index('Zero')
        gainindex = fitresult['result']['parameters'].index('Gain')
        zero = fitresult['result']['fittedpar'][zeroindex]
        gain = fitresult['result']['fittedpar'][gainindex]

        if self.mcafit.STRIP:
            ymatrix0  += self.mcafit.zz
            ymatrix1  += self.mcafit.zz

        # channels, energy, single, multiple
        self._xrfmcMatrixSpectra = [xmatrix, xmatrix * gain + zero, ymatrix0, ymatrix1]

        #self.logWidget.hide()
        self.plot()
        ddict=copy.deepcopy(self.dict)
        ddict['event'] = "McaAdvancedFitXRFMCMatrixFinished"

    def xrfmcSpectrum(self):
        #print "SKIPPING"
        #return self.fisxSpectrum()
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Sorry, current implementation requires you to perform a fit first\n"
            msg.setText(text)
            msg.exec()
            return
        fitresult = self.dict
        self._xrfmcMatrixSpectra = None
        if self._concentrationsInfo is None:
            # concentrations have to be calculated too
            self.concentrations()

        # force the Monte Carlo to work on fundamental parameters mode
        ddict = copy.deepcopy(self.dict)
        ddict['result']['config']['concentrations']['usematrix'] = 0
        ddict['result']['config']['concentrations']['flux'] = self._concentrationsInfo['Flux']
        ddict['result']['config']['concentrations']['time'] = self._concentrationsInfo['Time']

        if hasattr(self, "__tmpMatrixSpectrumDir"):
            if self.__tmpMatrixSpectrumDir is not None:
                self.removeDirectory(self.__tmpMatrixSpectrumDir)

        self.__tmpMatrixSpectrumDir = tempfile.mkdtemp(prefix="pymcaTmp")
        nfile = ConfigDict.ConfigDict()
        nfile.update(ddict)
        #the Monte Carlo expects this at top level
        nfile['xrfmc'] = ddict['result']['config']['xrfmc']
        newFile = os.path.join(self.__tmpMatrixSpectrumDir, "pymcaTmpFitFile.fit")
        if os.path.exists(newFile):
            # this should never happen
            os.remove(newFile)
        nfile.write(newFile)
        nfile = None
        fileNamesDict = XRFMCHelper.getOutputFileNames(newFile,
                                                       outputDir=self.__tmpMatrixSpectrumDir)
        if newFile != fileNamesDict['fit']:
            self.removeDirectory(self.__tmpMatrixSpectrumDir)
            raise ValueError("Inconsistent internal behaviour!")

        self._xrfmcFileNamesDict = fileNamesDict
        xrfmcProgram = ddict['result']['config']['xrfmc']['program']

        scriptName = fileNamesDict['script']
        scriptFile = XRFMCHelper.getScriptFile(xrfmcProgram, name=scriptName)
        csvName = fileNamesDict['csv']
        speName = fileNamesDict['spe']
        xmsoName = fileNamesDict['xmso']
        # basic parameters
        args = [scriptFile,
               "--verbose",
               "--spe-file=%s" % speName,
               "--csv-file=%s" % csvName,
               #"--enable-roi-normalization",
               #"--disable-roi-normalization", #default
               #"--enable-pile-up"
               #"--disable-pile-up" #default
               #"--enable-poisson",
               #"--disable-poisson", #default no noise
               #"--set-threads=2", #overwrite default maximum
               newFile,
               xmsoName]

        # additionalParameters
        simulationParameters = ["--enable-single-run"]
        #simulationParameters = ["--enable-single-run",
        #                        "--set-threads=2"]
        i = 0
        for parameter in simulationParameters:
            i += 1
            args.insert(1, parameter)

        # show the command on the log widget
        text = "%s" % scriptFile
        for arg in args[1:]:
            text += " %s" % arg
        if self.logWidget is None:
            self.logWidget = SubprocessLogWidget.SubprocessLogWidget()
            self.logWidget.setMinimumWidth(400)
            self.logWidget.sigSubprocessLogWidgetSignal.connect(\
                self._xrfmcSubprocessSlot)
        self.logWidget.clear()
        self.logWidget.show()
        self.logWidget.raise_()
        self.logWidget.append(text)
        self.logWidget.start(args=args)

    def removeDirectory(self, dirName):
        if os.path.exists(dirName):
            if os.path.isdir(dirName):
                shutil.rmtree(dirName)

    def _xrfmcSubprocessSlot(self, ddict):
        if ddict['event'] == "ProcessFinished":
            returnCode = ddict['code']
            msg = qt.QMessageBox(self)
            msg.setWindowTitle("Simulation finished")
            if returnCode != 0:
                msg = qt.QMessageBox(self)
                msg.setWindowTitle("Simulation Error")
                msg.setIcon(qt.QMessageBox.Critical)
                text = "Simulation finished with error code %d\n" % (returnCode)
                for line in ddict['message']:
                    text += line
                msg.setText(text)
                msg.exec()
                return

            xmsoFile = self._xrfmcFileNamesDict['xmso']
            corrections = XRFMCHelper.getXMSOFileFluorescenceInformation(xmsoFile)
            self.dict['result']['config']['xrfmc']['corrections'] = corrections
            elementsList = list(corrections.keys())
            elementsList.sort()
            for element in elementsList:
                for key in ['K', 'Ka', 'Kb', 'L', 'L1', 'L2', 'L3', 'M']:
                    if corrections[element][key]['total'] > 0.0:
                        value = corrections[element][key]['correction_factor'][-1]
                        if value != 1.0:
                            text = "%s %s xrays multiple excitation factor = %.4f" % \
                                   (element, key, value)
                            self.logWidget.append(text)

            from PyMca5.PyMcaIO import specfilewrapper as specfile
            sf = specfile.Specfile(self._xrfmcFileNamesDict['csv'])
            nScans = len(sf)
            scan = sf[nScans - 1]
            nMca = scan.nbmca()
            # specfile starts numbering at one
            # and the first mca corresponds to the energy
            self._xrfmcMatrixSpectra = []
            for i in range(1, nMca + 1):
                self._xrfmcMatrixSpectra.append(scan.mca(i))
            scan = None
            sf = None
            self.removeDirectory(self.__tmpMatrixSpectrumDir)
            #self.logWidget.hide()
            self.plot()
            ddict=copy.deepcopy(self.dict)
            ddict['event'] = "McaAdvancedFitXRFMCMatrixFinished"
            if 0:
                # this for later
                try:
                    self.__anasignal(ddict)
                except Exception:
                    _logger.warning("Error generating Monte Carlo matrix output. ")
                    _logger.warning(sys.exc_info())

    def peaksSpectrum(self):
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "You need to perform a fit first\n"
            msg.setText(text)
            msg.exec()
            return
        #fitresult = self.dict['result']
        fitresult = self.dict
        # force update
        self.mcafit.configure()
        groupsList = fitresult['result']['groups']
        if type(groupsList) != type([]):
            groupsList = [groupsList]

        nglobal    = len(fitresult['result']['parameters']) - len(groupsList)
        ddict=copy.deepcopy(self.dict)
        ddict['event'] = "McaAdvancedFitPeaksFinished"
        newparameters = fitresult['result']['fittedpar'] * 1
        for i in range(nglobal,len(fitresult['result']['parameters'])):
            newparameters[i] = 0.0
        for i in range(nglobal,len(fitresult['result']['parameters'])):
            group = fitresult['result']['parameters'][i]
            parameters    = newparameters * 1
            parameters[i] = fitresult['result']['fittedpar'][i]
            xmatrix = fitresult['result']['xdata']
            ymatrix = self.mcafit.mcatheory(parameters,xmatrix)
            ymatrix = ymatrix.reshape(len(ymatrix), 1)
            label = 'y'+group
            if self.mcafit.STRIP:
                ddict['result'][label]  = ymatrix + self.mcafit.zz
            else:
                ddict['result'][label]  = ymatrix
            ddict['result'][label] = numpy.ravel(ddict['result'][label])
            if self.peaksSpectrumButton.isChecked():
                self.dict['result'][label]= ddict['result'][label] * 1.0
        try:
            self.__anasignal(ddict)
        except Exception:
            _logger.warning("Error generating peaks output. ")
            _logger.warning("Try to perform your fit again.  ")
            _logger.warning("%s" % sys.exc_info())
            _logger.warning("If error persists, please report this error.")
            _logger.warning("ymatrix shape = %s" % ddict['result']['ymatrix'].shape)
            _logger.warning("xmatrix shape = %s" % xmatrix.shape)
            _logger.warning("continuum shape = %s" % ddict['result']['continuum'].shape)
            _logger.warning("zz      shape = %s" % self.mcafit.zz.shape)

    def __printps(self):
        self.__printmenu.exec(self.cursor().pos())

    def htmlReport(self,index=None):
        if not self.__fitdone:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("You should perform a fit \nfirst,\n shouldn't you?")
            msg.exec()
            return
        oldoutdir = self.outdir
        if self.outdir is None:
            cwd = PyMcaDirs.outputDir
            self.outdir =PyMcaFileDialogs.getExistingDirectory(self,
                                    message="Output Directory Selection",
                                    mode="SAVE",
                                    currentdir=cwd)
            if len(self.outdir):
                if self.outdir[-1]=="/":
                    self.outdir=self.outdir[:-1]
        try:
            self.__htmlReport()
        except IOError:
            self.outdir = None
            if oldoutdir is not None:
                if os.path.exists(oldoutdir):
                    self.outdir = oldoutdir
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("IO error")
            msg.setText("Input Output Error: %s" % (sys.exc_info()[1]))
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def __htmlReport(self,outfile=None):
        report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(fitfile=None,
                    outfile=outfile, outdir=self.outdir,
                    sourcename=self.info['sourcename'],
                    selection=self.info['legend'],
                    fitresult=self.dict,
                    concentrations=self._concentrationsDict,
                    plotdict={'logy': self.graph.isYAxisLogarithmic()})
        if 0:
            #this forces to open and read the file
            self.__lastreport = report.writeReport()
        else:
            text = report.getText()
            self.__lastreport = report.writeReport(text=text)
        if self.browser is None:
            self.browser= qt.QWidget()
            self.browser.setWindowTitle(QString(self.__lastreport))
            self.browser.layout = qt.QVBoxLayout(self.browser)
            self.browser.layout.setContentsMargins(0, 0, 0, 0)
            self.browser.layout.setSpacing(0)
            self.__printmenu.addSeparator()
            self.__printmenu.addAction(QString("Last Report"),self.showLastReport)

            self.browsertext = qt.QTextBrowser(self.browser)
            self.browsertext.setReadOnly(1)
            screenWidth = qt.QDesktopWidget().width()
            if screenWidth > 0:
                self.browsertext.setMinimumWidth(min(self.width(), int(0.5 * screenWidth)))
            else:
                self.browsertext.setMinimumWidth(self.width())
            screenHeight = qt.QDesktopWidget().height()
            if screenHeight > 0:
                self.browsertext.setMinimumHeight(min(self.height(), int(0.5 * screenHeight)))
            else:
                self.browsertext.setMinimumHeight(self.height())

            self.browser.layout.addWidget(self.browsertext)
        else:
            self.browser.setWindowTitle(QString(self.__lastreport))

        dirname = os.path.dirname(self.__lastreport)
        # basename = os.path.basename(self.__lastreport)
        #self.browsertext.setMimeSourceFactory(qt.QMimeFactory.defaultFactory())
        #self.browsertext.mimeSourceFactory().addFilePath(QString(dirname))
        self.browsertext.setSearchPaths([QString(dirname)])
        #self.browsertext.setSource(qt.QUrl(QString(basename)))
        self.browsertext.clear()
        if QTVERSION < '4.2.0':
            self.browsertext.insertHtml(text)
        else:
            self.browsertext.setText(text)
        self.browsertext.show()
        self.showLastReport()

    def showLastReport(self):
        if self.browser is not None:
            self.browser.show()
            self.browser.raise_()

    def printConcentrations(self, doit=0):
        text = "<CENTER>"+self.concentrationsWidget.concentrationsTable.getHtmlText()+"</CENTER>"
        if (__name__ == "__main__") or (doit):
            self.__print(text)
        else:
            ddict={}
            ddict['event'] = "McaAdvancedFitPrint"
            ddict['text' ] = text
            self.sigMcaAdvancedFitSignal.emit(ddict)

    def printps(self, doit=0):
        h = self.__htmlheader()
        text = "<CENTER>"+self.mcatable.gettext()+"</CENTER>"
        #text = self.mcatable.gettext()
        if (__name__ == "__main__") or (doit):
            self.__print(h+text)
            #print h+text
        else:
            ddict={}
            ddict['event'] = "McaAdvancedFitPrint"
            ddict['text' ] = h+text
            self.sigMcaAdvancedFitSignal.emit(ddict)

    def __htmlheader(self):
        header = "%s" % qt.safe_str(self.headerLabel.text())
        if header[0] == "<":
            header = header[3:-3]
        if self.mcafit.config['fit']['sumflag']:
            sumflag = "Y"
        else:
            sumflag = "N"

        if self.mcafit.config['fit']['escapeflag']:
            escapeflag =  "Y"
        else:
            escapeflag = "N"

        if self.mcafit.config['fit']['stripflag']:
            stripflag = "Y"
        else:
            stripflag = "N"
        #bkg = self.mcafit.config['fit']['continuum']
        #theory = "Hypermet"
        bkg    = "%s" % qt.safe_str(self.top.BkgComBox.currentText())
        theory = "%s" % qt.safe_str(self.top.FunComBox.currentText())
        hypermetflag=self.mcafit.config['fit']['hypermetflag']
        # g_term  = hypermetflag & 1
        st_term   = (hypermetflag >>1) & 1
        lt_term   = (hypermetflag >>2) & 1
        step_term = (hypermetflag >>3) & 1
        if st_term:
            st_term = "Y"
        else:
            st_term = "N"
        if st_term:
            lt_term = "Y"
        else:
            lt_term = "N"
        if step_term:
            step_term = "Y"
        else:
            step_term = "N"


        h=""
        h+="    <CENTER>"
        h+="<B>%s</B>" % header
        h+="    </CENTER>"
        h+="    <SPACER TYPE=BLOCK HEIGHT=10>"
        #h+="<BR></BR>"
        h+="    <CENTER>"
        h+="<TABLE>"
        h+="<TR>"
        h+="    <TD ALIGN=LEFT><B>Function</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD NOWRAP ALIGN=LEFT>%s</TD>" % theory
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=15></TD>"

        h+="    <TD ALIGN=LEFT><B>ShortTail</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD>%s</TD>" % st_term
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=5></B></TD>"

        h+="    <TD ALIGN=LEFT><B>LongTail</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD>%s</TD>" % lt_term
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=5></B></TD>"

        h+="    <TD ALIGN=LEFT><B>StepTail</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD>%s</TD>" % step_term
        h+="</TR>"

        h+="<TR>"
        #h+="    <TD ALIGN=LEFT><B>Background</B></TH>"
        h+="    <TD ALIGN=LEFT><B>Backg.</B></TH>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD NOWRAP ALIGN=LEFT>%s</TD>" % bkg
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=15></B></TD>"

        h+="    <TD ALIGN=LEFT><B>Escape</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD>%s</TD>" % escapeflag
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=5></B></TD>"

        h+="    <TD ALIGN=LEFT><B>Pile-up</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%s</TD>" % sumflag
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=5></B></TD>"

        h+="    <TD ALIGN=LEFT><B>Strip</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD>%s</TD>" % stripflag

        h+="</TR>"
        h+="</TABLE>"
        h+="</CENTER>"
        return h

    # pyflakes http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=666503
    def __print(self, text):
        _logger.info("__print not working yet")
        return
        printer = qt.QPrinter()
        printDialog = qt.QPrintDialog(printer, self)
        if printDialog.exec():
            if 0:
                #this was crashing in Qt 4.2.2
                #with the PyQt snapshot of 20061203
                editor = qt.QTextEdit()
                cursor = editor.textCursor()
                cursor.movePosition(qt.QTextCursor.Start)
                editor.insertHtml(text)
                document = editor.document()
            else:
                document = qt.QTextDocument()
                document.setHtml(text)
            document.print_(printer)

    def setdata(self, *var, **kw):
        _logger.debug("McaAdvancedFit.setdata deprecated, use setData instead.")
        return self.setData(*var, **kw)

    def setData(self,*var,**kw):
        """
        The simplest way to use it is to pass at least the y keyword containing
        the channel counts. The other items are not mandatory.

        :keywords:
            x
                channels
            y
                counts in each channel
            sigmay
                uncertainties to be applied if different than sqrt(y)
            xmin
                minimum channel/x value of the fit. It will be ignored if use_limits is True
            xmax
                maximum channel/x value of the fit. It will be ignored if use_limits is True
            calibration
                list of the form [a, b, c] containing the mca calibration
            time
                float containing the time or monitor factor to be used in
                the concentrations if requested.
        """

        self.__fitdone = 0
        self.info ={}
        key = 'legend'
        if key in kw:
            self.info[key] = kw[key]
        else:
            self.info[key] = 'Unknown Origin'
        key = 'xlabel'
        if key in kw:
            self.info[key] = kw[key]
        else:
            self.info[key] = 'X'

        # PyMca McaWindow is systematically sending the zoomed region xmin and xmax
        # To make sure the limits configuration settings respect the selected GUI behavior
        # xmin and xmax they need to be set or overwritten here if required
        for key in ['xmin', 'xmax']:
            if self.mcafit.config['fit']['use_limit']:
                kw[key] = self.mcafit.config['fit'][key]
                _logger.info("%s limit overwritten by fit configuration" % key)

        key = 'xmin'
        if key in kw:
            self.info[key] = "%.3f" % kw[key]
        else:
            self.info[key] = "????"
        key = 'xmax'
        if key in kw:
            self.info[key] = "%.3f" % kw[key]
        else:
            self.info[key] = "????"
        key = 'sourcename'
        if key in kw:
            self.info[key] = "%s" % kw[key]
        else:
            self.info[key] = "Unknown Source"
        key = 'time'
        if key in kw:
            self.info[key] = kw[key]
        else:
            self.info[key] = None

        # TODO: These two variables do not seem to be used anywhere.
        # Is there a reason to keep a reference? 
        self.__var = var
        self.__kw  = kw

        try:
            self.mcafit.setData(*var,**kw)
        except ValueError:
            if self.info["time"] is None:
                if "concentrations" in self.mcafit.config:
                    if self.mcafit.config["concentrations"].get("useautotime", False):
                        if not self.mcafit.config["concentrations"]["usematrix"]:
                            msg = qt.QMessageBox(self)
                            msg.setIcon(qt.QMessageBox.Information)
                            txt = "No time information associated to spectrum but requested in configuration.\n"
                            txt += "Please correct the acquisition time in your configuration."
                            msg.setText(txt)
                            msg.exec()
                            self.mcafit.config["concentrations"] ["useautotime"] = 0
                            kw["time"] = None
                            self.mcafit.setData(*var, **kw)
                    else:
                        raise
                else:
                    raise
            else:
                raise

        self.info["calibration"] = kw.get('calibration', None)
        if 'calibration' in kw:
            if kw['calibration'] is not None:
                # The condition below gave troubles because it was using the
                # current calibration even if the x data where actual energies.
                # if (kw['calibration'] != [0.0,1.0,0.0]):
                if not self.mcafit.config['detector'].get('ignoreinputcalibration', False):
                    self.mcafit.config['detector']['zero']=kw['calibration'][0] * 1
                    self.mcafit.config['detector']['gain']=kw['calibration'][1] * 1

        if self.configDialog is not None:
            self.configDialog.setData(self.mcafit.xdata * 1.0,
                           self.mcafit.ydata * 1.0,
                           info=copy.deepcopy(self.info))

        if self.concentrationsWidget is not None:
            if self.mcafit.config["concentrations"].get("useautotime", False):
                self.concentrationsWidget.setTimeFactor(self.info["time"],
                                                    signal=False)

        self.setHeader(text="Fit of %s from %s %s to %s" % (self.info['legend'],
                                                            self.info['xlabel'],
                                                            self.info['xmin'],
                                                            self.info['xmax']))
        self._updateTop()
        self.plot()

    def setheader(self, *var, **kw):
        _logger.debug("McaAdvancedFit.setheader deprecated, use setHeader instead.")
        return self.setHeader( *var, **kw)

    def setHeader(self,*var,**kw):
        if len(var):
            text = var[0]
        elif 'text' in kw:
            text = kw['text']
        elif 'header' in kw:
            text = kw['header']
        else:
            text = ""
        self.headerLabel.setText("%s" % text)

    def fit(self):
        """
        Function called to start the fit process.

        Interactive use

        It returns a dictionary containing the fit results or None in case of
        unsuccessfull fit.

        Embedded use

        In case of successfull fit emits a signal of the form:

        self.sigMcaAdvancedFitSignal.emit(ddict)

        where ddict['event'] = 'McaAdvancedFitFinished'
        """
        self.__fitdone = 0
        self.mcatable.setRowCount(0)
        if self.concentrationsWidget is not None:
            self.concentrationsWidget.concentrationsTable.setRowCount(0)
        self.diagnosticsWidget.clear()
        fitconfig = {}
        fitconfig.update(self.mcafit.configure())
        if fitconfig['peaks'] == {}:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("No peaks defined.\nPlease configure peaks")
            msg.exec()
            return
        if _logger.getEffectiveLevel() == logging.DEBUG:
            _logger.debug("calling estimate")
            self.mcafit.estimate()
            _logger.debug("calling startfit")
            fitresult, result = self.mcafit.startfit(digest=1)
            _logger.debug("filling table")
            self.mcatable.fillfrommca(result)
            _logger.debug("finished")
        else:
            try:
                self.mcafit.estimate()
                thread = CalculationThread.CalculationThread( \
                                      calculation_method = self.mcafit.startfit,
                                      calculation_kw = {'digest':1},
                                      expand_vars=True,
                                      expand_kw=True)
                thread.start()
                CalculationThread.waitingMessageDialog(thread,
                                    message = "Calculating Fit",
                                    parent=self,
                                    modal=True,
                                    update_callback=None,
                                    frameless=True)
                threadResult = thread.getResult()
                if type(threadResult) == type((1,)):
                    if len(threadResult):
                        if threadResult[0] == "Exception":
                            raise Exception(threadResult[1], threadResult[2])
                fitresult = threadResult[0]
                result    = threadResult[1]
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Fit error")
                msg.setText("Error on fit:")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
            try:
                #self.mcatable.fillfrommca(self.mcafit.result)
                self.mcatable.fillfrommca(result)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error filling Table: %s" % (sys.exc_info()[1]))
                msg.exec()
                return

        ddict={}
        ddict['event']     = "McaAdvancedFitFinished"
        ddict['fitresult'] = fitresult
        ddict['result']    = result
        #I should make a copy but ...
        self.dict = {}
        self.dict['info'] = {}
        self.dict['info'] = self.info.copy()
        self.dict['result'] = ddict['result']
        self.__fitdone      = 1
        # add the matrix spectrum
        if self.matrixSpectrumButton.isChecked():
            self.matrixSpectrum()
        else:
            if "Matrix" in self.graph.getAllCurves(just_legend=True):
                self.graph.removeCurve("Matrix")

        # clear the Monte Carlo spectra (if any)
        self._xrfmcMatrixSpectra = None

        # add the peaks spectrum
        if self.peaksSpectrumButton.isChecked():
            self.peaksSpectrum()
        else:
            self.__clearPeaksSpectrum()
        self.plot()

        if self.concentrationsWidget is not None:
            if (str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == 'CONCENTRATIONS') or \
                (self.concentrationsWidget.parent() is None):
                if not self.concentrationsWidget.isHidden():
                    try:
                        self.concentrations()
                    except Exception:
                        if _logger.getEffectiveLevel() == logging.DEBUG:
                            raise
                        msg = qt.QMessageBox(self)
                        msg.setIcon(qt.QMessageBox.Critical)
                        msg.setText("Concentrations Error: %s" % (sys.exc_info()[1]))
                        msg.exec()
                        return
        if str(self.mainTab.tabText(self.mainTab.currentIndex())).upper() == 'DIAGNOSTICS':
            try:
                self.diagnostics()
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Diagnostics Error: %s" % (sys.exc_info()[1]))
                msg.exec()
                return

        return self.__anasignal(ddict)

    def __anasignal(self, ddict):
        if type(ddict) != type({}):
            return
        if 'event' in ddict:
            ddict['info'] = {}
            ddict['info'].update(self.info)
            self.sigMcaAdvancedFitSignal.emit(ddict)
            #Simplify interactive usage of the module
            return ddict

    def dismiss(self):
        self.close()

    def closeEvent(self, event):
        if self.identifier is not None:
            self.identifier.close()
        qt.QWidget.closeEvent(self, event)

    def _mcaGraphSignalSlot(self, ddict):
        if ddict['event'] == "FitClicked":
            self.fit()
        elif ddict['event'] == "EnergyClicked":
            self.toggleEnergyAxis()
        elif ddict['event'] == "SaveClicked":
            self._saveGraph()
        elif ddict['event'].lower() in ["mouseclicked", "curveclicked"]:
            if ddict['button'] == 'left':
                if self._energyAxis:
                    self.__peakIdentifier(ddict['x'])
        else:
            pass
        return

    def toggleEnergyAxis(self, dict=None):
        if self._energyAxis:
            self._energyAxis = False
            self.graph.setGraphXLabel('Channel')
        else:
            self._energyAxis = True
            self.graph.setGraphXLabel('Energy')
        self.plot()

    def plot(self, ddict=None):
        if self.graph.isYAxisLogarithmic():
            logfilter = 1
        else:
            logfilter = 0
        formerActiveCurveLegend = self.graph.getActiveCurve(just_legend=True)
        self.graph.clearCurves(replot=False)
        config = self.mcafit.configure()
        if ddict is None:
            if not self.__fitdone:
                #just the data
                xdata  = self.mcafit.xdata * 1.0
                if self._energyAxis:
                    xdata = config['detector'] ['zero'] + config['detector'] ['gain'] * xdata
                if self.mcafit.STRIP:
                    ydata  = self.mcafit.ydata + self.mcafit.zz
                else:
                    ydata  = self.mcafit.ydata * 1.0
                xdata = numpy.ravel(xdata)
                ydata = numpy.ravel(ydata)
                self.graph.addCurve(xdata, ydata, legend="Data", replot=True, replace=True)
                self.graph.updateLegends()
                return
            else:
                ddict = self.dict
        if self._energyAxis:
            xdata = ddict['result']['energy'][:]
        else:
            xdata = ddict['result']['xdata'][:]
        self.graph.addCurve(xdata, ddict['result']['ydata'], legend="Data",
                            replot=False)
        self.graph.addCurve(xdata, ddict['result']['yfit'], legend="Fit",
                            replot=False)
        self.graph.addCurve(xdata, ddict['result']['continuum'],
                            legend="Continuum",
                            replot=False)

        curveList = self.graph.getAllCurves(just_legend=True)

        if config['fit']['sumflag']:
            self.graph.addCurve(xdata, ddict['result']['pileup'] + \
                                       ddict['result']['continuum'],
                                       legend="Pile-up", replot=False)
        elif "Pile-up" in curveList:
            self.graph.removeCurve("Pile-up", replot=False)

        if self.matrixSpectrumButton.isChecked():
            if 'ymatrix' in ddict['result']:
                self.graph.addCurve(xdata,
                                    ddict['result']['ymatrix'],
                                    legend="Matrix")
            else:
                self.graph.removeCurve("Matrix")
        else:
            self.graph.removeCurve("Matrix")

        if self._xrfmcMatrixSpectra is not None:
            if len(self._xrfmcMatrixSpectra):
                if self._energyAxis:
                    mcxdata = self._xrfmcMatrixSpectra[1]
                else:
                    mcxdata = self._xrfmcMatrixSpectra[0]
                mcydata0 = self._xrfmcMatrixSpectra[2]
                mcydatan = self._xrfmcMatrixSpectra[-1]
                self.graph.addCurve(mcxdata,
                                    mcydata0,
                                    legend='MC Matrix 1',
                                    replot=False)
                self.graph.addCurve(mcxdata,
                                    mcydatan,
                                    legend='MC Matrix %d' % (len(self._xrfmcMatrixSpectra) - 2),
                                    replot=False)

        if self.peaksSpectrumButton.isChecked():
            keep = ['Data','Fit','Continuum','Matrix','Pile-up']
            for group in ddict['result']['groups']:
                keep += [group]
            for key in curveList:
                if key not in keep:
                    if key.startswith('MC Matrix'):
                        if self._xrfmcMatrixSpectra in [None, []]:
                            self.graph.removeCurve(key)
                    else:
                        self.graph.removeCurve(key)
            for group in ddict['result']['groups']:
                label = 'y' + group
                if label in ddict['result']:
                    self.graph.addCurve(xdata,
                                        ddict['result'][label],
                                        legend=group,
                                        replot=False)
                else:
                    if group in curveList:
                        self.graph.removeCurve(group, replot=False)
        else:
            self.__clearPeaksSpectrum()

        curveList = self.graph.getAllCurves(just_legend=True)
        if formerActiveCurveLegend in curveList:
            currentActiveCurveLegend = self.graph.getActiveCurve(just_legend=True)
            if currentActiveCurveLegend != formerActiveCurveLegend:
                self.graph.setActiveCurve(formerActiveCurveLegend, replot=False)

        self.graph.replot()
        self.graph.updateLegends()

    def _saveGraph(self, dict=None):
        curves = self.graph.getAllCurves()
        if not len(curves):
            return
        if not self.__fitdone:
            if False:
                # just save the data ?
                # just save data plus strip background if any?
                # for the time being just force to have the fit
                pass
            else:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                text = "Sorry, You need to perform a fit first.\n"
                msg.setText(text)
                msg.exec()
                return
        if dict is None:
            #everything
            fitresult = self.dict
        else:
            fitresult = dict
        xdata     = fitresult['result']['xdata']
        # energy    = fitresult['result']['energy']
        # ydata     = fitresult['result']['ydata']
        # yfit      = fitresult['result']['yfit']
        # continuum = fitresult['result']['continuum']
        # pileup    = fitresult['result']['pileup']
        # savelist  = ['xdata', 'energy','ydata','yfit','continuum','pileup']
        # parNames  = fitresult['result']['parameters']
        # parFit    = fitresult['result']['fittedpar']
        # parSigma  = fitresult['result']['sigmapar']

        #still to add the MC matrix spectrum
        # The Monte Carlo generated spectra
        # I assume the calibration is the same
        MCLabels, MCSpectra = self._getXRFMCLabelsAndSpectra(limits=\
                                                    (fitresult['result']['xdata'][0],
                                                     fitresult['result']['xdata'][-1]))
        if MCLabels is not None:
            if MCSpectra[2].size != fitresult['result']['xdata'].size:
                _logger.warning("Monte Carlo Spectra not saved: Wrong spectrum length.")
                MCLabels = None
                MCSpectra = None

        if self.lastInputDir is None:
            self.lastInputDir = PyMcaDirs.outputDir
        format_list = ['Specfile MCA  *.mca',
                       'Specfile Scan *.dat',
                       'Raw ASCII  *.txt',
                       '";"-separated CSV *.csv',
                       '","-separated CSV *.csv',
                       '"tab"-separated CSV *.csv',
                       'Graphics PNG *.png',
                       'Graphics EPS *.eps',
                       'Graphics SVG *.svg']
        if not self.peaksSpectrumButton.isChecked():
            format_list.append('B/WGraphics PNG *.png')
            format_list.append('B/WGraphics EPS *.eps')
            format_list.append('B/WGraphics SVG *.svg')
        wdir = self.lastInputDir
        outputFile, filterused = PyMcaFileDialogs.getFileList(self,
                                        filetypelist=format_list,
                                        message="Output File Selection",
                                        currentdir=wdir,
                                        mode="SAVE",
                                        getfilter=True,
                                        single=True,
                                        currentfilter=None)
        if outputFile:
            outputFile = outputFile[0]
            filterused = filterused.split()
            filedescription = filterused[0]
            filetype  = filterused[1]
            extension = filterused[2]
            try:
                outputDir  = os.path.dirname(outputFile)
                self.lastInputDir   = outputDir
                PyMcaDirs.outputDir = outputDir
            except Exception:
                outputDir  = "."
            #self.outdir = outputDir
        else:
            return

        #always overwrite for the time being
        if len(outputFile) < len(extension[1:]):
            outputFile += extension[1:]
        elif outputFile[-4:] != extension[1:]:
            outputFile += extension[1:]
        specFile = os.path.join(outputDir, outputFile)
        try:
            os.remove(specFile)
        except Exception:
            pass
        systemline = os.linesep
        os.linesep = '\n'
        try:
            if filetype in ['EPS', 'PNG', 'SVG']:
                size = (7, 3.5) #in inches
                logy = self.graph.isYAxisLogarithmic()
                if filedescription == "B/WGraphics":
                    bw = True
                else:
                    bw = False
                if self.peaksSpectrumButton.isChecked():
                    legends = True
                elif 'ymatrix' in fitresult['result'].keys():
                    legends = False
                else:
                    legends = False
                if self.matplotlibDialog is None:
                    self.matplotlibDialog = QPyMcaMatplotlibSave1D.\
                                            QPyMcaMatplotlibSaveDialog(size=size,
                                                                logy=logy,
                                                                legends=legends,
                                                                bw = bw)
                mtplt = self.matplotlibDialog.plot
                mtplt.setParameters({'logy':logy,
                                     'legends':legends,
                                     'bw':bw})
                """
                    mtplt = PyMcaMatplotlibSave.PyMcaMatplotlibSave(size=size,
                                                                logy=logy,
                                                                legends=legends,
                                                                bw = bw)
                    self.matplotlibDialog = None
                """
                if self._energyAxis:
                    x = fitresult['result']['energy']
                else:
                    x = fitresult['result']['xdata']
                xmin, xmax = self.graph.getGraphXLimits()
                ymin, ymax = self.graph.getGraphYLimits()
                mtplt.setLimits(xmin, xmax, ymin, ymax)
                index = numpy.nonzero((xmin <= x) & (x <= xmax))[0]
                x = numpy.take(x, index)
                if bw:
                    mtplt.addDataToPlot( x,
                            numpy.take(fitresult['result']['ydata'],index),
                            legend='data',
                            color='k',linestyle=':', linewidth=1.5, markersize=3)
                else:
                    mtplt.addDataToPlot( x,
                            numpy.take(fitresult['result']['ydata'],index),
                            legend='data',
                            linewidth=1)

                mtplt.addDataToPlot( x,
                            numpy.take(fitresult['result']['yfit'],index),
                            legend='fit',
                            linewidth=1.5)
                if not self.peaksSpectrumButton.isChecked():
                    mtplt.addDataToPlot( x,
                                numpy.take(fitresult['result']['continuum'],index),
                                legend='bck', linewidth=1.5)
                if self.top.sumbox.isChecked():
                    mtplt.addDataToPlot( x,
                            numpy.take(fitresult['result']['pileup']+\
                                         fitresult['result']['continuum'],index),
                                         legend="pile up",
                                         linewidth=1.5)
                if 'ymatrix' in fitresult['result'].keys():
                    mtplt.addDataToPlot( x,
                            numpy.take(fitresult['result']['ymatrix'],index),
                            legend='matrix',
                            linewidth=1.5)
                if self._xrfmcMatrixSpectra is not None:
                    if len(self._xrfmcMatrixSpectra):
                        if self._energyAxis:
                            mcxdata = self._xrfmcMatrixSpectra[1]
                        else:
                            mcxdata = self._xrfmcMatrixSpectra[0]
                        mcindex = numpy.nonzero((xmin <= mcxdata) & (mcxdata <= xmax))[0]
                        mcxdatax = numpy.take(mcxdata, mcindex)
                        mcydata0 = numpy.take(self._xrfmcMatrixSpectra[2], mcindex)
                        mcydatan = numpy.take(self._xrfmcMatrixSpectra[-1], mcindex)
                        mtplt.addDataToPlot(mcxdatax,
                                            mcydata0,
                                            legend='MC Matrix 1',
                                            linewidth=1.5)
                        mtplt.addDataToPlot(mcxdatax,
                                            mcydatan,
                                            legend='MC Matrix %d' % (len(self._xrfmcMatrixSpectra) - 2),
                                            linewidth=1.5)
                if self.peaksSpectrumButton.isChecked():
                    for group in fitresult['result']['groups']:
                        label = 'y'+group
                        if label in fitresult['result'].keys():
                            mtplt.addDataToPlot( x,
                                numpy.take(fitresult['result'][label],index),
                                            legend=group,
                                            linewidth=1.5)
                if self._energyAxis:
                    mtplt.setXLabel('Energy (keV)')
                else:
                    mtplt.setXLabel('Channel')
                mtplt.setYLabel('Counts')
                mtplt.plotLegends()
                if self.matplotlibDialog is not None:
                    ret = self.matplotlibDialog.exec()
                    if ret == qt.QDialog.Accepted:
                        mtplt.saveFile(specFile)
                else:
                    mtplt.saveFile(specFile)
                return
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText("Matplotlib or Input Output Error: %s" \
                                   % (sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return
        try:
            if sys.version < "3.0":
                file = open(specFile, 'wb')
            else:
                file = open(specFile, 'w', newline='')
        except IOError:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText("Input Output Error: %s" % \
                                   (sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return
        try:
            if filetype == 'ASCII':
                keys = fitresult['result'].keys()
                for i in range(len(fitresult['result']['ydata'])):
                    file.write("%.7g  %.7g   %.7g  %.7g  %.7g  %.7g" % (fitresult['result']['xdata'][i],
                                       fitresult['result']['energy'][i],
                                       fitresult['result']['ydata'][i],
                                       fitresult['result']['yfit'][i],
                                       fitresult['result']['continuum'][i],
                                       fitresult['result']['pileup'][i]))
                    if 'ymatrix' in fitresult['result'].keys():
                        file.write("  %.7g" %  fitresult['result']['ymatrix'][i])

                    if MCLabels is not None:
                        for nInteractions in range(2, len(MCLabels)):
                            file.write("  %.7g" %  MCSpectra[nInteractions][i])

                    for group in fitresult['result']['groups']:
                        label = 'y'+group
                        if label in keys:
                            file.write("  %.7g" %  fitresult['result'][label][i])
                    file.write("\n")
                file.close()
                return
            if filetype == 'CSV':
                if "," in filterused[0]:
                    csv = ","
                elif ";" in filterused[0]:
                    csv = ";"
                else:
                    csv = "\t"
                keys = fitresult['result'].keys()

                headerLine = '"channel"%s"Energy"%s"counts"%s"fit"%s"continuum"%s"pileup"' % (csv, csv, csv, csv, csv)
                if 'ymatrix' in keys:
                    headerLine += '%s"ymatrix"' % csv

                if MCLabels is not None:
                    for nLabel in range(2, len(MCLabels)):
                        headerLine += csv+ ('"%s"' % MCLabels[nLabel])

                for group in fitresult['result']['groups']:
                    label = 'y'+group
                    if label in keys:
                        headerLine += csv+ ('"%s"' % group)
                file.write(headerLine)
                file.write('\n')
                for i in range(len(fitresult['result']['ydata'])):
                    file.write("%.7g%s%.7g%s%.7g%s%.7g%s%.7g%s%.7g" % (fitresult['result']['xdata'][i],
                                       csv,
                                       fitresult['result']['energy'][i],
                                       csv,
                                       fitresult['result']['ydata'][i],
                                       csv,
                                       fitresult['result']['yfit'][i],
                                       csv,
                                       fitresult['result']['continuum'][i],
                                       csv,
                                       fitresult['result']['pileup'][i]))
                    if 'ymatrix' in fitresult['result'].keys():
                        file.write("%s%.7g" %  (csv,fitresult['result']['ymatrix'][i]))

                    if MCLabels is not None:
                        for nInteractions in range(2, len(MCLabels)):
                            file.write("%s%.7g" %  (csv,MCSpectra[nInteractions][i]))

                    for group in fitresult['result']['groups']:
                        label = 'y'+group
                        if label in keys:
                            file.write("%s%.7g" %  (csv,fitresult['result'][label][i]))
                    file.write("\n")
                file.close()
                return
            #header is almost common to specfile and mca
            file.write("#F %s\n" % specFile)
            file.write("#D %s\n"%(time.ctime(time.time())))
            file.write("\n")
            legend = str(self.headerLabel.text()).strip('<b>')
            legend.strip('<\b>')
            file.write("#S 1 %s\n" % legend)
            file.write("#D %s\n"%(time.ctime(time.time())))
            i = 0
            for parameter in fitresult['result']['parameters']:
                file.write("#U%d %s %.7g +/- %.3g\n" % (i, parameter,
                                                     fitresult['result']['fittedpar'][i],
                                                     fitresult['result']['sigmapar'][i]))
                i+=1
            if filetype == 'Scan':
                keys = fitresult['result'].keys()
                labelline= "#L channel  Energy  counts  fit  continuum  pileup"
                if 'ymatrix' in keys:
                    nlabels = 7
                    labelline += "ymatrix"
                else:
                    nlabels = 6

                if MCLabels is not None:
                    for nLabel in range(2, len(MCLabels)):
                        nlabels += 1
                        labelline += '  '+ MCLabels[nLabel]

                for group in fitresult['result']['groups']:
                    label = 'y'+group
                    if label in keys:
                        nlabels += 1
                        labelline += '  '+group
                file.write("#N %d\n" % nlabels)
                file.write(labelline)
                file.write("\n")
                for i in range(len(fitresult['result']['ydata'])):
                    file.write("%.7g  %.7g  %.7g  %.7g  %.7g  %.7g" % (fitresult['result']['xdata'][i],
                                       fitresult['result']['energy'][i],
                                       fitresult['result']['ydata'][i],
                                       fitresult['result']['yfit'][i],
                                       fitresult['result']['continuum'][i],
                                       fitresult['result']['pileup'][i]))
                    if 'ymatrix' in keys:
                        file.write("  %.7g" % fitresult['result']['ymatrix'][i])
                    if MCLabels is not None:
                        for nInteractions in range(2, len(MCLabels)):
                            file.write("  %.7g" %  MCSpectra[nInteractions][i])
                    for group in fitresult['result']['groups']:
                        label = 'y'+group
                        if label in keys:
                            file.write("  %.7g" %  fitresult['result'][label][i])
                    file.write("\n")
            else:
                file.write("#@MCA %16C\n")
                file.write("#@CHANN %d %d %d 1\n" %  (len(fitresult['result']['ydata']),
                                                        fitresult['result']['xdata'][0],
                                                        fitresult['result']['xdata'][-1]))
                zeroindex = fitresult['result']['parameters'].index('Zero')
                gainindex = fitresult['result']['parameters'].index('Gain')
                file.write("#@CALIB %.7g %.7g 0.0\n" % (fitresult['result']['fittedpar'][zeroindex],
                                                        fitresult['result']['fittedpar'][gainindex]))
                file.write(self.array2SpecMca(fitresult['result']['ydata']))
                file.write(self.array2SpecMca(fitresult['result']['yfit']))
                file.write(self.array2SpecMca(fitresult['result']['continuum']))
                file.write(self.array2SpecMca(fitresult['result']['pileup']))
                keys = fitresult['result'].keys()
                if 'ymatrix' in keys:
                    file.write(self.array2SpecMca(fitresult['result']['ymatrix']))
                # The Monte Carlo generated spectra
                # I assume the calibration is the same
                if MCLabels is not None:
                    for i in range(2, len(MCLabels)):
                        file.write(self.array2SpecMca(MCSpectra[i]))
                for group in fitresult['result']['groups']:
                    label = 'y'+group
                    if label in keys:
                        file.write(self.array2SpecMca(fitresult['result'][label]))
            file.write("\n")
            file.close()
        except Exception:
            os.linesep = systemline
            raise
        return

    def _getXRFMCLabelsAndSpectra(self, limits=None):
        labels = None
        spectra = None
        if self._xrfmcMatrixSpectra is not None:
            if len(self._xrfmcMatrixSpectra):
                labels = []
                spectra = []
                labels.append("channels")
                data = self._xrfmcMatrixSpectra[0]
                if limits:
                    idx = numpy.nonzero((data >= limits[0]) & \
                                        (data <= limits[1]))[0]
                    data = data[idx]
                spectra.append(data)
                labels.append("energy")
                data = self._xrfmcMatrixSpectra[1]
                if limits:
                    data = data[idx]
                spectra.append(data)
                for i in range(2, len(self._xrfmcMatrixSpectra)):
                    labels.append("MC Matrix %d" % (i - 1))
                    data = self._xrfmcMatrixSpectra[i]
                    if limits:
                        data = data[idx]
                    spectra.append(data)
        return labels, spectra

    def array2SpecMca(self, data):
        """ Write a python array into a Spec array.
            Return the string containing the Spec array
        """
        tmpstr = "@A"
        length = len(data)
        for idx in range(0, length, 16):
            if idx+15 < length:
                for i in range(0,16):
                    tmpstr += " %.4f" % data[idx+i]
                if idx+16 != length:
                    tmpstr += "\\"
            else:
                for i in range(idx, length):
                    tmpstr += " %.4f" % data[i]
            tmpstr += "\n"
        return tmpstr


class Top(qt.QWidget):
    sigTopSignal = qt.pyqtSignal(object)
    def __init__(self,parent = None,name = None,fl = 0):
        qt.QWidget.__init__(self,parent)
        self.mainLayout= qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.build()

    def build(self):
        self.__w=qt.QWidget(self)
        w = self.__w
        self.mainLayout.addWidget(w)
        wlayout = qt.QGridLayout(w)
        wlayout.setSpacing(5)
        #function
        FunLabel = qt.QLabel(w)
        FunLabel.setText(str("Function"))
        if QTVERSION < '4.0.0':
            self.FunComBox = qt.QComboBox(0,w,"FunComBox")
            self.FunComBox.insertStrList(["Mca Hypermet"])
            self.FunComBox.insertStrList(["Mca Pseudo-Voigt"])
        else:
            self.FunComBox = qt.QComboBox(w)
            self.FunComBox.insertItem(0, "Mca Hypermet")
            self.FunComBox.insertItem(1, "Mca Pseudo-Voigt")
        wlayout.addWidget(FunLabel,0,0)
        wlayout.addWidget(self.FunComBox,0,1)
        #background
        BkgLabel = qt.QLabel(w)
        BkgLabel.setText(str("Background"))
        if QTVERSION < '4.0.0':
            self.BkgComBox = qt.QComboBox(0,w,"BkgComBox")
            self.BkgComBox.insertStrList(['No Background',
                                          'Constant',
                                          'Linear',
                                          'Parabolic',
                                          'Linear Polynomial',
                                          'Exp. Polynomial'])
        else:
            self.BkgComBox = qt.QComboBox(w)
            options = ['No Background',
                       'Constant',
                       'Linear',
                       'Parabolic',
                       'Linear Polynomial',
                       'Exp. Polynomial']
            for item in options:
                self.BkgComBox.insertItem(options.index(item), item)

        self.FunComBox.activated[int].connect(self.mysignal)

        self.BkgComBox.activated[int].connect(self.mysignal)
        wlayout.addWidget(BkgLabel,1,0)
        wlayout.addWidget(self.BkgComBox,1,1)
        dummy = qt.QWidget(self)
        dummy.setMinimumSize(20,0)
        self.mainLayout.addWidget(dummy)
        self.mainLayout.addWidget(qt.HorizontalSpacer(self))

        #the checkboxes
        if 0:
             w1 = qt.QVBox(self)
             self.WeightCheckBox = qt.QCheckBox(w1)
             self.WeightCheckBox.setText(str("Weight"))
             self.McaModeCheckBox = qt.QCheckBox(w1)
             self.McaModeCheckBox.setText(str("Mca Mode"))

        # Flags
        f       = qt.QWidget(self)
        self.mainLayout.addWidget(f)
        f.layout= qt.QGridLayout(f)
        f.layout.setSpacing(5)
        flagsoffset = -1
        coffset     = 0
        #hyplabel = qt.QLabel(f)
        #hyplabel.setText(str("<b>%s</b>" % 'FLAGS'))
        self.stbox = qt.QCheckBox(f)
        self.stbox.setText('Short Tail')
        self.ltbox = qt.QCheckBox(f)
        self.ltbox.setText('Long Tail')
        self.stepbox = qt.QCheckBox(f)
        self.stepbox.setText('Step Tail')
        self.escapebox = qt.QCheckBox(f)
        self.escapebox.setText('Escape')
        self.sumbox = qt.QCheckBox(f)
        self.sumbox.setText('Pile-up')
        self.stripbox = qt.QCheckBox(f)
        self.stripbox.setText('Strip Back.')
        #checkbox connections
        self.stbox.clicked.connect(self.mysignal)
        self.ltbox.clicked.connect(self.mysignal)
        self.stepbox.clicked.connect(self.mysignal)
        self.escapebox.clicked.connect(self.mysignal)
        self.sumbox.clicked.connect(self.mysignal)
        self.stripbox.clicked.connect(self.mysignal)
        #f.layout.addWidget(hyplabel,flagsoffset,coffset +1)
        f.layout.addWidget(self.stbox,flagsoffset+1,coffset +0)
        f.layout.addWidget(self.ltbox,flagsoffset+1,coffset +1)
        f.layout.addWidget(self.stepbox,flagsoffset+1,coffset +2)
        f.layout.addWidget(self.escapebox,flagsoffset+2,coffset +0)
        f.layout.addWidget(self.sumbox,flagsoffset+2,coffset +1)
        f.layout.addWidget(self.stripbox,flagsoffset+2,coffset +2)
        self.mainLayout.addWidget(qt.HorizontalSpacer(self))

        #buttons
        g = qt.QWidget(self)
        self.mainLayout.addWidget(g)
        glayout = qt.QGridLayout(g)
        glayout.setSpacing(5)
        self.configureButton = qt.QPushButton(g)
        self.configureButton.setText(str("Configure"))
        self.printButton = qt.QPushButton(g)
        self.printButton.setText(str("Tools"))
        glayout.addWidget(self.configureButton,0,0)
        glayout.addWidget(self.printButton,1,0)

    def setParameters(self,ddict=None):
        if ddict == None: ddict = {}
        hypermetflag = ddict.get('hypermetflag', 1)
        if not ('fitfunction' in ddict):
            if hypermetflag:
                ddict['fitfunction'] = 0
            else:
                ddict['fitfunction'] = 1

        self.FunComBox.setCurrentIndex(ddict['fitfunction'])

        if 'hypermetflag' in ddict:
            hypermetflag = ddict['hypermetflag']
            if ddict['fitfunction'] == 0:
                # g_term  = hypermetflag & 1
                st_term   = (hypermetflag >>1) & 1
                lt_term   = (hypermetflag >>2) & 1
                step_term = (hypermetflag >>3) & 1
                self.stbox.setEnabled(1)
                self.ltbox.setEnabled(1)
                self.stepbox.setEnabled(1)
                if st_term:
                    self.stbox.setChecked(1)
                else:
                    self.stbox.setChecked(0)
                if lt_term:
                    self.ltbox.setChecked(1)
                else:
                    self.ltbox.setChecked(0)
                if step_term:
                    self.stepbox.setChecked(1)
                else:
                    self.stepbox.setChecked(0)
            else:
                self.stbox.setEnabled(0)
                self.ltbox.setEnabled(0)
                self.stepbox.setEnabled(0)

        key = 'sumflag'
        if key in ddict:
            if ddict[key] == 1:
                self.sumbox.setChecked(1)
            else:
                self.sumbox.setChecked(0)

        key = 'stripflag'
        if key in ddict:
            if ddict[key] == 1:
                self.stripbox.setChecked(1)
            else:
                self.stripbox.setChecked(0)

        key = 'escapeflag'
        if key in ddict:
            if ddict[key] == 1:
                self.escapebox.setChecked(1)
            else:
                self.escapebox.setChecked(0)

        key = 'continuum'
        if key in ddict:
            if QTVERSION < '4.0.0':
                self.BkgComBox.setCurrentItem(ddict[key])
            else:
                self.BkgComBox.setCurrentIndex(ddict[key])

    def getParameters(self):
        ddict={}
        index = self.FunComBox.currentIndex()
        ddict['fitfunction'] = index
        ddict['hypermetflag'] = 1
        if index == 0:
            self.stbox.setEnabled(1)
            self.ltbox.setEnabled(1)
            self.stepbox.setEnabled(1)
        else:
            ddict['hypermetflag'] = 0
            self.stbox.setEnabled(0)
            self.ltbox.setEnabled(0)
            self.stepbox.setEnabled(0)

        if self.stbox.isChecked():
            ddict['hypermetflag'] += 2
        if self.ltbox.isChecked():
            ddict['hypermetflag'] += 4

        if self.stepbox.isChecked():
            ddict['hypermetflag'] += 8

        if self.sumbox.isChecked():
            ddict['sumflag'] = 1
        else:
            ddict['sumflag'] = 0

        if self.stripbox.isChecked():
            ddict['stripflag'] = 1
        else:
            ddict['stripflag'] = 0

        if self.escapebox.isChecked():
            ddict['escapeflag'] = 1
        else:
            ddict['escapeflag'] = 0
        if QTVERSION < '4.0.0':
            ddict['continuum'] = self.BkgComBox.currentItem()
        else:
            ddict['continuum'] = self.BkgComBox.currentIndex()
        return ddict

    def mysignal(self, *var):
        ddict = self.getParameters()
        self.sigTopSignal.emit(ddict)


class Line(qt.QFrame):
    sigLineDoubleClickEvent = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="Line", fl=0, info=None):
        qt.QFrame.__init__(self, parent)
        self.info = info
        self.setFrameShape(qt.QFrame.HLine)
        self.setFrameShadow(qt.QFrame.Sunken)
        self.setFrameShape(qt.QFrame.HLine)


    def mouseDoubleClickEvent(self, event):
        _logger.debug("Double Click Event")
        ddict={}
        ddict['event']="DoubleClick"
        ddict['data'] = event
        ddict['info'] = self.info
        self.sigLineDoubleClickEvent.emit(ddict)

class McaGraphWindow(PlotWindow.PlotWindow):
    def __init__(self, parent=None, backend=None, plugins=False,
                 newplot=False, position=True, control=True, plot1d=True,
                 **kw):
        super(McaGraphWindow, self).__init__(parent, backend=backend,
                                       plugins=plugins,
                                       newplot=newplot,
                                       energy=True,
                                       roi=True,
                                       logx=False,
                                       fit=True,
                                       position=position,
                                       control=control,
                                       plot1d=plot1d,
                                       **kw)
        self.setDataMargins(0, 0, 0.025, 0.025)
        self.setPanWithArrowKeys(True)
        self.printPreview = PyMcaPrintPreview.PyMcaPrintPreview(modal = 0)
        self.setGraphYLabel("Counts")
        if self.energyButton.isChecked():
            self.setGraphXLabel("Energy")
        else:
            self.setGraphXLabel("Channel")

    def printGraph(self):
        widget = self.getWidgetHandle()
        if hasattr(qt.QPixmap, "grabWidget"):
            pixmap = qt.QPixmap.grabWidget(widget)
        else:
            pixmap = widget.grab()
        self.printPreview.addPixmap(pixmap)
        if self.printPreview.isHidden():
            self.printPreview.show()
        self.printPreview.raise_()

    def _energyIconSignal(self):
        legend = self.getActiveCurve(just_legend=True)
        ddict={}
        ddict['event']  = 'EnergyClicked'
        ddict['active'] = legend
        self.sigPlotSignal.emit(ddict)

    def _fitIconSignal(self):
        legend = self.getActiveCurve(just_legend=True)
        ddict={}
        ddict['event']  = 'FitClicked'
        ddict['active'] = legend
        self.sigPlotSignal.emit(ddict)

    def _saveIconSignal(self):
        legend = self.getActiveCurve(just_legend=True)
        ddict={}
        ddict['event']  = 'SaveClicked'
        ddict['active'] = legend
        self.sigPlotSignal.emit(ddict)

    def setActiveCurve(self, legend, replot=True):
        super(McaGraphWindow, self).setActiveCurve(legend, replot=False)
        self.setGraphYLabel("Counts")
        if self.energyButton.isChecked():
            self.setGraphXLabel("Energy")
        else:
            self.setGraphXLabel("Channel")
        if replot:
            self.replot()

def test(ffile='03novs060sum.mca', cfg=None):
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    sf=specfile.Specfile(ffile)
    scan=sf[-1]
    nMca = scan.nbmca()
    mcadata=scan.mca(nMca)
    y0= numpy.array(mcadata)
    x = numpy.arange(len(y0))*1.0
    demo = McaAdvancedFit()
    #This illustrates how to change the configuration
    #oldConfig = demo.configure()
    #oldConfig['fit']['xmin'] = 123
    #demo.configure(oldConfig)
    if cfg is not None:
        d = ConfigDict.ConfigDict()
        d.read(cfg)
        demo.configure(d)
        d = None
    xmin = demo.mcafit.config['fit']['xmin']
    xmax = demo.mcafit.config['fit']['xmax']
    demo.setData(x,y0,xmin=xmin,xmax=xmax,sourcename=ffile)
    demo.show()
    app.exec()


def main():
    app = qt.QApplication([])
    form = McaAdvancedFit(top=False)
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) >1:
        ffile = sys.argv[1]
    else:
        ffile = '03novs060sum.mca'
    if len(sys.argv) > 2:
        cfg = sys.argv[2]
    else:
        cfg = None
    if os.path.exists(ffile):
        test(ffile, cfg)
    else:
        main()
