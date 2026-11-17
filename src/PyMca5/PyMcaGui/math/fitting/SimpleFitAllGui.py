#/*##########################################################################
# Copyright (C) 2023 European Synchrotron Radiation Facility
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
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"


import logging
import os
import sys
import traceback
import time

from .SimpleFitGui import SimpleFitGui
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaMath.fitting import SimpleFitAll
from PyMca5.PyMcaMath.fitting import SimpleFitModule
from PyMca5.PyMcaMath.fitting import SpecfitFunctions

from PyMca5.PyMcaGui.math.fitting import SpecfitConfigGui

from PyMca5.PyMcaGui.misc import CalculationThread


_logger = logging.getLogger(__name__)


class OutputParameters(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)
        self.outputDirLabel = qt.QLabel(self)
        self.outputDirLabel.setText("Output directory")
        self.outputDirLine = qt.QLineEdit(self)
        self.outputDirLine.setReadOnly(True)
        self.outputDirButton = qt.QPushButton(self)
        self.outputDirButton.setText("Browse")
        self.outputDirButton.clicked.connect(self.browseDirectory)

        self.outputFileLabel = qt.QLabel(self)
        self.outputFileLabel.setText("Output file root")
        self.outputFileLine = qt.QLineEdit(self)

        self.outputDir = PyMcaDirs.outputDir
        self.outputFile = "SimpleFitAllOutput.h5"
        self.setOutputDirectory(self.outputDir)
        self.setOutputFileName(self.outputFile)

        self.mainLayout.addWidget(self.outputDirLabel, 0, 0)
        self.mainLayout.addWidget(self.outputDirLine, 0, 1)
        self.mainLayout.addWidget(self.outputDirButton, 0, 2)
        self.mainLayout.addWidget(self.outputFileLabel, 1, 0)
        self.mainLayout.addWidget(self.outputFileLine, 1, 1)

    def getOutputDirectory(self):
        return str(self.outputDirLine.text())

    def getOutputFileName(self):
        return str(self.outputFileLine.text())

    def setOutputDirectory(self, txt):
        if os.path.exists(txt):
            self.outputDirLine.setText(txt)
            self.outputDir = txt
            PyMcaDirs.outputDir = txt
        else:
            raise IOError("Directory does not exists")

    def setOutputFileName(self, txt):
        if len(txt):
            self.outputFileLine.setText(txt)
            self.outputFile = txt

    def browseDirectory(self):
        wdir = self.outputDir
        outputDir = qt.QFileDialog.getExistingDirectory(
                self, "Please select output directory", wdir)
        if len(outputDir):
            self.setOutputDirectory(str(outputDir))


class SimpleFitAllGui(SimpleFitGui):

    def __init__(self, parent=None, fit=None, graph=None, actions=True):
        if fit is None:
            fit = SimpleFitModule.SimpleFit()
            # inject config widget by patching the module
            w = SpecfitConfigGui.SpecfitConfigGui
            SpecfitFunctions.WIDGET = [w for _t in SpecfitFunctions.THEORY]
            fit.importFunctions(SpecfitFunctions)
            fit.loadUserFunctions()
        SimpleFitGui.__init__(self, parent, fit, graph, actions)

        self.fitAllInstance = SimpleFitAll.SimpleFitAll(fit=self.fitModule)

        self.fitActions.dismissButton.hide()
        self.outputParameters = OutputParameters(self)
        self.startFitAllButton = qt.QPushButton(self)
        self.startFitAllButton.setText("Fit all")
        self.startFitAllButton.clicked.connect(self.startFitAll)
        self.progressBar = qt.QProgressBar(self)
        self.mainLayout.addWidget(self.outputParameters)
        self.mainLayout.addWidget(self.startFitAllButton)
        self.mainLayout.addWidget(self.progressBar)

        # progress handling
        self._total = 100
        self._index = 0
        self.fitAllInstance.setProgressCallback(self.progressUpdate)

        self.curves_x = None
        self.curves_y = None
        self.legends = None
        self.xlabels = None
        self.ylabels = None

        # store active curve
        self._activeData = None

    def setSpectrum(self, x, y, sigma=None, xmin=None, xmax=None):
        """Set the main active curve to be plotted, for
        estimation purposes."""
        self._activeData = x, y, sigma, xmin, xmax
        SimpleFitGui.setData(self, x, y, sigma, xmin, xmax)

    def setSpectra(self, curves_x, curves_y, legends=None,
                   xlabels=None, ylabels=None):
        """Set all curves to be fitted.

        :param curves_x: list of 1D arrays of X curve values
        :param curves_y: list of 1D arrays of Y curve values.
        :param legends: list of curve legends
        """
        self.curves_x = curves_x
        self.curves_y = curves_y
        self.legends = legends
        self.xlabels = xlabels
        self.ylabels = ylabels

    def startFitAll(self):
        xmin = self.fitModule._fitConfiguration['fit']['xmin']
        xmax = self.fitModule._fitConfiguration['fit']['xmax']
        self.fitAllInstance.setOutputDirectory(
                self.outputParameters.getOutputDirectory())
        self.fitAllInstance.setOutputFileName(
                self.outputParameters.getOutputFileName())
        self.fitAllInstance.setData(self.curves_x, self.curves_y,
                                    sigma=None, xmin=xmin, xmax=xmax,
                                    legends=self.legends,
                                    xlabels=self.xlabels,
                                    ylabels=self.ylabels)

        fileName = self.outputParameters.getOutputFileName()
        if os.path.exists(fileName):
            msg = qt.QMessageBox()
            msg.setWindowTitle("Output file(s) exists")
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("Do you want to delete current output files?")
            msg.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.Cancel)
            answer = msg.exec()
            if answer == qt.QMessageBox.Yes:
                try:
                    if os.path.exists(fileName):
                        os.remove(fileName)
                except Exception:
                    qt.QMessageBox.critical(
                        self, "Delete Error",
                        "ERROR while deleting file:\n%s" % fileName,
                        qt.QMessageBox.Ok,
                        qt.QMessageBox.NoButton,
                        qt.QMessageBox.NoButton)
                    return
            else:
                return
        try:
            self._startWork()
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Fitting All Error")
            msg.setText("Error has occurred while processing the data")
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
        finally:
            self.progressBar.hide()
            self.setEnabled(True)
        if self._activeData is not None:
            self.setSpectrum(*self._activeData)

    def _startWork(self):
        self.setEnabled(False)
        self.progressBar.show()
        thread = CalculationThread.CalculationThread(
                parent=self, calculation_method=self.processAll)
        thread.start()
        self._total = 100
        self._index = 0
        while thread.isRunning():
            time.sleep(2)
            qApp = qt.QApplication.instance()
            qApp.processEvents()
            self.progressBar.setMaximum(self._total)
            self.progressBar.setValue(self._index)
        self.progressBar.hide()
        self.setEnabled(True)
        if thread.result is not None:
            if len(thread.result):
                tb = thread.result[-1]
                traceback.print_tb(tb)
                raise RuntimeError(*thread.result[1:])

    def processAll(self):
        # fill estimation from table, in case it has been updated manually
        self.fitModule.paramlist = self.parametersTable.fillFitFromTable()
        self.fitAllInstance.processAll()

    def progressUpdate(self, idx, total):
        self._index = int(idx)
        self._total = int(total)
        if idx % 10 == 0:
            _logger.info("Fitted %d of %d", idx, total)
