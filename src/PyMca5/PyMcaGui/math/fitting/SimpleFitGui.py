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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaMath.fitting import SimpleFitModule
from . import SimpleFitConfigurationGui
from PyMca5.PyMcaMath.fitting import SimpleFitUserEstimatedFunctions
from . import Parameters
from PyMca5.PyMcaGui.plotting import PlotWindow
from PyMca5.PyMcaGui.io import PyMcaFileDialogs

_logger = logging.getLogger(__name__)


class TopWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)
        font = qt.QFont(self.font())
        font.setBold(True)

        #Function handling
        self.functionLabel = qt.QLabel(self)
        self.functionLabel.setFont(font)
        self.functionLabel.setText("Function:")
        self.addFunctionButton = qt.QPushButton(self)
        self.addFunctionButton.setText("ADD")

        #fit function
        self.fitFunctionLabel = qt.QLabel(self)
        self.fitFunctionLabel.setFont(font)
        self.fitFunctionLabel.setText("Fit:")
        self.fitFunctionCombo = qt.QComboBox(self)
        self.fitFunctionCombo.addItem(qt.safe_str("None"))
        self.fitFunctionCombo.setSizeAdjustPolicy(qt.QComboBox.AdjustToContents)
        self.fitFunctionCombo.setMinimumWidth(100)

        #background function
        self.backgroundLabel = qt.QLabel(self)
        self.backgroundLabel.setFont(font)
        self.backgroundLabel.setText("Background:")
        self.backgroundCombo  = qt.QComboBox(self)
        self.backgroundCombo.addItem(qt.safe_str("None"))
        self.backgroundCombo.setSizeAdjustPolicy(qt.QComboBox.AdjustToContents)
        self.backgroundCombo.setMinimumWidth(100)

        #arrange everything
        self.mainLayout.addWidget(self.functionLabel,     0, 0)
        self.mainLayout.addWidget(self.addFunctionButton,    0, 1)
        self.mainLayout.addWidget(qt.HorizontalSpacer(self), 0, 2)
        self.mainLayout.addWidget(self.fitFunctionLabel,  0, 3)
        self.mainLayout.addWidget(self.fitFunctionCombo,  0, 4)
        self.mainLayout.addWidget(qt.HorizontalSpacer(self), 0, 5)
        self.mainLayout.addWidget(self.backgroundLabel,   0, 6)
        self.mainLayout.addWidget(self.backgroundCombo,   0, 7)

        self.configureButton = qt.QPushButton(self)
        self.configureButton.setText("CONFIGURE")
        self.mainLayout.addWidget(self.configureButton,   0, 8)

    def setFunctions(self, functionList):
        currentFunction = qt.safe_str(self.fitFunctionCombo.currentText())
        currentBackground = qt.safe_str(self.backgroundCombo.currentText())
        self.fitFunctionCombo.clear()
        self.backgroundCombo.clear()
        self.fitFunctionCombo.addItem('None')
        self.backgroundCombo.addItem('None')
        for key in functionList:
            self.fitFunctionCombo.addItem(qt.safe_str(key))
            self.backgroundCombo.addItem(qt.safe_str(key))

        #restore previous values
        idx = self.fitFunctionCombo.findText(currentFunction)
        self.fitFunctionCombo.setCurrentIndex(idx)
        idx = self.backgroundCombo.findText(currentBackground)
        self.backgroundCombo.setCurrentIndex(idx)

class StatusWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)

        self.statusLabel = qt.QLabel(self)
        self.statusLabel.setText(qt.safe_str("Status:"))
        self.statusLine = qt.QLineEdit(self)
        self.statusLine.setText(qt.safe_str("Ready"))
        self.statusLine.setReadOnly(1)

        self.chi2Label = qt.QLabel(self)
        self.chi2Label.setText(qt.safe_str("Reduced Chi Square:"))

        self.chi2Line = qt.QLineEdit(self)
        self.chi2Line.setText(qt.safe_str(""))
        self.chi2Line.setReadOnly(1)

        self.mainLayout.addWidget(self.statusLabel)
        self.mainLayout.addWidget(self.statusLine)
        self.mainLayout.addWidget(self.chi2Label)
        self.mainLayout.addWidget(self.chi2Line)

class SimpleFitGui(qt.QWidget):
    sigSimpleFitSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, fit=None, graph=None, actions=True):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("SimpleFitGui")
        if fit is None:
            self.fitModule = SimpleFitModule.SimpleFit()
            self.fitModule.importFunctions(SimpleFitUserEstimatedFunctions)
            self.fitModule.loadUserFunctions()
        else:
            self.fitModule = fit
        if graph is None:
            self.__useTab = True
            self.graph = PlotWindow.PlotWindow(newplot=False,
                                               plugins=False,
                                               fit=False,
                                               control=True,
                                               position=True)
        else:
            self.__useTab = False
            self.graph = graph
        self._configurationDialog = None
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)
        self.topWidget  = TopWidget(self)
        config = self.fitModule.getConfiguration()
        self.topWidget.setFunctions(config['fit']['functions'])
        config = None

        if self.__useTab:
            self.mainTab = qt.QTabWidget(self)
            self.mainLayout.addWidget(self.mainTab)
            self.parametersTable = Parameters.Parameters()
            self.mainTab.addTab(self.graph, 'GRAPH')
            self.mainTab.addTab(self.parametersTable, 'FIT')
        else:
            self.parametersTable = Parameters.Parameters(self)

        self.statusWidget  = StatusWidget(self)

        self.mainLayout.addWidget(self.topWidget)
        if self.__useTab:
            self.mainLayout.addWidget(self.mainTab)
        else:
            self.mainLayout.addWidget(self.parametersTable)
        self.mainLayout.addWidget(self.statusWidget)

        if actions:
            #build the actions widget
            self.fitActions = qt.QWidget(self)
            self.fitActions.mainLayout = qt.QHBoxLayout(self.fitActions)
            self.fitActions.mainLayout.setContentsMargins(2, 2, 2, 2)
            self.fitActions.mainLayout.setSpacing(2)
            self.fitActions.estimateButton = qt.QPushButton(self.fitActions)
            self.fitActions.estimateButton.setText("Estimate")
            self.fitActions.startFitButton = qt.QPushButton(self.fitActions)
            self.fitActions.startFitButton.setText("Start Fit")
            self.fitActions.dismissButton = qt.QPushButton(self.fitActions)
            self.fitActions.dismissButton.setText("Dismiss")
            self.fitActions.mainLayout.addWidget(self.fitActions.estimateButton)
            self.fitActions.mainLayout.addWidget(self.fitActions.startFitButton)
            self.fitActions.mainLayout.addWidget(self.fitActions.dismissButton)
            self.mainLayout.addWidget(self.fitActions)

        #connect top widget
        self.topWidget.addFunctionButton.clicked.connect(\
                    self.importFunctionsSlot)

        self.topWidget.fitFunctionCombo.currentIndexChanged[int].connect(\
                     self.fitFunctionComboSlot)

        self.topWidget.backgroundCombo.currentIndexChanged[int].connect(\
                     self.backgroundComboSlot)

        self.topWidget.configureButton.clicked.connect(\
                    self.configureButtonSlot)

        if actions:
            #connect actions
            self.fitActions.estimateButton.clicked.connect(self.estimate)
            self.fitActions.startFitButton.clicked.connect(self.startFit)
            self.fitActions.dismissButton.clicked.connect(self.dismiss)

    def importFunctionsSlot(self):
        return self.importFunctions()

    def importFunctions(self, functionsfile=None):
        if functionsfile is None:
            filetypelist = ['Python files (*.py)', 'All Files (*)']
            fileList = PyMcaFileDialogs.getFileList(self,
                                        filetypelist=filetypelist,
                                        message="Select input functions file",
                                        currentdir=None,
                                        mode="OPEN",
                                        getfilter=None,
                                        single=True,
                                        currentfilter=filetypelist[0],
                                        native=None)
            if len(fileList):
                functionsfile= qt.safe_str(fileList[0])
            else:
                functionsfile = ""
            if not len(functionsfile):
                return

        try:
            self.fitModule.importFunctions(functionsfile)
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            msg = qt.QMessageBox()
            msg.setWindowTitle("SimpleFitGui error")
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText("Function not imported %s" % \
                                           str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

        config = self.fitModule.getConfiguration()
        self.topWidget.setFunctions(config['fit']['functions'])

    def fitFunctionComboSlot(self, idx):
        if idx <= 0:
            fname = "None"
        else:
            fname = qt.safe_str(self.topWidget.fitFunctionCombo.itemText(idx))
        self.fitModule.setFitFunction(fname)

    def backgroundComboSlot(self, idx):
        if idx <= 0:
            fname = "None"
        else:
            fname = qt.safe_str(self.topWidget.backgroundCombo.itemText(idx))
        self.setBackgroundFunction(fname)

    def configureButtonSlot(self):
        if self._configurationDialog is None:
            self._configurationDialog =\
                SimpleFitConfigurationGui.SimpleFitConfigurationGui()
        self._configurationDialog.setSimpleFitInstance(self.fitModule)
        if not self._configurationDialog.exec():
            _logger.debug("NOT UPDATING CONFIGURATION")
            oldConfig = self.fitModule.getConfiguration()
            self._configurationDialog.setConfiguration(oldConfig)
            return
        newConfig = self._configurationDialog.getConfiguration()
        self.topWidget.setFunctions(newConfig['fit']['functions'])
        self.fitModule.setConfiguration(newConfig)
        newConfig = self.fitModule.getConfiguration()
        #self.topWidget.setFunctions(newConfig['fit']['functions'])
        fname = self.fitModule.getFitFunction()
        if fname in [None, "None", "NONE"]:
            idx = 0
        else:
            idx = newConfig['fit']['functions'].index(fname) + 1
        self.topWidget.fitFunctionCombo.setCurrentIndex(idx)
        fname = self.fitModule.getBackgroundFunction()
        if fname in [None, "None", "NONE"]:
            idx = 0
        else:
            idx = newConfig['fit']['functions'].index(fname) + 1
        idx = self.topWidget.backgroundCombo.findText(fname)
        self.topWidget.backgroundCombo.setCurrentIndex(idx)
        _logger.debug("TABLE TO BE CLEANED")
        #self.estimate()

    def setFitFunction(self, fname):
        current = self.fitModule.getFitFunction()
        if current != fname:
            self.fitModule.setFitFunction(fname)
            idx = self.topWidget.fitFunctionCombo.findText(fname)
            self.topWidget.fitFunctionCombo.setCurrentIndex(idx)

    def setBackgroundFunction(self, fname):
        current = self.fitModule.getBackgroundFunction()
        if current != fname:
            self.fitModule.setBackgroundFunction(fname)
            idx = self.topWidget.backgroundCombo.findText(fname)
            self.topWidget.backgroundCombo.setCurrentIndex(idx)

    def setData(self, *var, **kw):
        returnValue = self.fitModule.setData(*var, **kw)
        if self.__useTab:
            if hasattr(self.graph, "addCurve"):
                self.graph.addCurve(self.fitModule._x,
                                    self.fitModule._y,
                                    legend='Data',
                                    replace=True)
            elif hasattr(self.graph, "newCurve"):
                self.graph.clearCurves()
                self.graph.newCurve('Data',
                                    self.fitModule._x,
                                    self.fitModule._y)
            self.graph.replot()
        return returnValue

    def estimate(self):
        self.setStatus("Estimate started")
        self.statusWidget.chi2Line.setText("")
        try:
            x = self.fitModule._x
            y = self.fitModule._y
            self.graph.clear()
            self.graph.addCurve(x, y, 'Data')
            self.fitModule.estimate()
            self.setStatus()
            self.parametersTable.fillTableFromFit(self.fitModule.paramlist)
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            text = "%s:%s" % (sys.exc_info()[0], sys.exc_info()[1])
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText(text)
            msg.exec()
            self.setStatus("Ready (after estimate error)")

    def setStatus(self, text=None):
        if text is None:
            text = "%s" % self.fitModule.getStatus()

        self.statusWidget.statusLine.setText(text)

    def startFit(self):
        #get parameters from table
        self.fitModule.paramlist = self.parametersTable.fillFitFromTable()
        try:
            values,chisq,sigma,niter,lastdeltachi = self.fitModule.startFit()
            self.setStatus()
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            text = "%s:%s" % (sys.exc_info()[0], sys.exc_info()[1])
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText(text)
            msg.exec()
            self.setStatus("Ready (after fit error)")
            return

        self.parametersTable.fillTableFromFit(self.fitModule.paramlist)
        self.statusWidget.chi2Line.setText("%f" % chisq)
        ddict = {}
        ddict['event'] = "FitFinished"
        ddict['x']    = self.fitModule._x
        ddict['y']    = self.fitModule._y
        ddict['yfit'] = self.evaluateDefinedFunction()
        self.sigSimpleFitSignal.emit(ddict)
        self.updateGraph()

    def updateGraph(self):
        #this is to be overwritten and for test purposes
        if self.graph is None:
            return
        ddict = self.fitModule.evaluateContributions()
        ddict['event'] = "FitFinished"
        ddict['x']    = self.fitModule._x
        ddict['y']    = self.fitModule._y
        #ddict['yfit'] = self.evaluateDefinedFunction()
        #ddict['background'] = self.fitModule._evaluateBackground()
        self.graph.clear()
        self.graph.addCurve(ddict['x'], ddict['y'], 'Data', replot=False)
        self.graph.addCurve(ddict['x'], ddict['yfit'], 'Fit', replot=False)
        self.graph.addCurve(ddict['x'], ddict['background'], 'Background',
                                                replot=True)
        contributions = ddict['contributions']
        if len(contributions) > 1:
            background = ddict['background']
            i = 0
            for contribution in contributions:
                i += 1
                if i == len(contributions):
                    replot = True
                else:
                    replot = False
                self.graph.addCurve(ddict['x'], background + contribution,
                                    legend='Contribution %d' % i,
                                    replot=replot)
        self.graph.show()

    def dismiss(self):
        self.close()

    def evaluateDefinedFunction(self, x=None):
        return self.fitModule.evaluateDefinedFunction(x)

    def evaluateContributions(self, x=None):
        return self.fitModule.evaluateContributions(x)


def test():
    import numpy
    #import DefaultFitFunctions as SpecfitFunctions
    from PyMca5.PyMca import SpecfitFunctions
    a=SpecfitFunctions.SpecfitFunctions()
    x = numpy.arange(1000).astype(numpy.float64)
    p1 = numpy.array([1500,100.,50.0])
    p2 = numpy.array([1500,700.,50.0])
    y = a.gauss(p1, x)
    y = y + a.gauss(p2,x) + x * 5.
    fit=None
    w = SimpleFitGui(fit=fit)
    w.setData(x, y, xmin=x[0], xmax=x[-1])
    w.show()
    from PyMca5.PyMca import SimpleFitUserEstimatedFunctions
    fname = SimpleFitUserEstimatedFunctions.__file__
    w.importFunctions(fname)
    w.setFitFunction('User Estimated Gaussians')
    return w

if __name__=="__main__":
    _logger.setLevel(logging.DEBUG)
    app = qt.QApplication([])
    w = test()
    app.exec()
