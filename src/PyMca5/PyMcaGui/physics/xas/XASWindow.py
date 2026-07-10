#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2022 European Synchrotron Radiation Facility
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
import os
import sys
import numpy
import traceback
import copy
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.plotting import PlotWindow
from PyMca5.PyMcaGui.physics.xas import XASParameters

from PyMca5.PyMcaPhysics.xas import XASClass
import logging

_logger = logging.getLogger(__name__)

class XASDialog(qt.QDialog):
    def __init__(self, parent=None, analyzer=None, backend=None):
        super(XASDialog, self).__init__(parent)
        self.setWindowTitle("XAS Window")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        # the main window
        self.xasWindow = XASWindow(self, analyzer=analyzer, backend=backend)
        self.setSpectrum = self.xasWindow.setSpectrum
        self.setConfiguration = self.xasWindow.setConfiguration
        self.getConfiguration = self.xasWindow.getConfiguration

        # the actions
        actionContainer = qt.QWidget(self)
        actionContainer.mainLayout = qt.QHBoxLayout(actionContainer)
        actionContainer.mainLayout.setContentsMargins(0, 0, 0, 0)
        actionContainer.mainLayout.setSpacing(2)
        self.acceptButton = qt.QPushButton(actionContainer)
        self.acceptButton.setText("Accept Seen Configuration")
        self.acceptButton.setAutoDefault(False)
        self.acceptButton.clicked.connect(self.accept)
        self.cancelButton = qt.QPushButton(actionContainer)
        self.cancelButton.setText("Reject Seen Configuration")
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.clicked.connect(self.reject)
        actionContainer.mainLayout.addWidget(self.acceptButton)
        actionContainer.mainLayout.addWidget(self.cancelButton)

        # arrange things
        #self.actionContainer = actionContainer
        self.mainLayout.addWidget(self.xasWindow)
        self.mainLayout.addWidget(actionContainer)

class XASWindow(qt.QMainWindow):
    def __init__(self, parent=None, analyzer=None, color="blue", backend=None):
        super(XASWindow, self).__init__(parent)
        self.setWindowTitle("XAS Window")
        if parent is not None:
            # behave as a widget
            self.setWindowFlags(qt.Qt.Widget)
        if analyzer is None:
            analyzer = XASClass.XASClass()
        self.mdiArea = XASMdiArea(self, analyzer=analyzer, backend=backend)
        self.setCentralWidget(self.mdiArea)
        self.parametersDockWidget = qt.QDockWidget(self)
        self.parametersDockWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.parametersWidget = XASParameters.XASParameters(color=color)
        self.parametersDockWidget.setWidget(self.parametersWidget)
        self.addDockWidget(qt.Qt.RightDockWidgetArea, self.parametersDockWidget)

        # connect
        self.parametersWidget.sigXASParametersSignal.connect(self._parametersSlot)
        self.mdiArea.sigXASMdiAreaSignal.connect(self._update)

    def setSpectrum(self, energy, mu):
        self.mdiArea.setSpectrum(energy, mu)
        self.parametersWidget.setSpectrum(energy, mu)

    def setConfiguration(self, ddict):
        self.mdiArea.setConfiguration(ddict)
        self.parametersWidget.setParameters(ddict)

    def getConfiguration(self, ddict):
        return self.mdiArea.getConfiguration()

    def setParameters(self, ddict):
        self.parametersWidget.setParameters(ddict)

    def getParameters(self):
        return self.parametersWidget.getParameters()

    def _parametersSlot(self, ddict):
        _logger.debug("XASWindow.parametersSlot: %s", ddict)
        analyzer = self.mdiArea.analyzer
        if "XASParameters" in ddict:
            ddict = ddict["XASParameters"]
        analyzer.setConfiguration(ddict)
        _logger.debug("ANALYZER CONFIGURATION FINAL")
        _logger.debug(analyzer.getConfiguration())
        self.update()

    def update(self, ddict=None):
        if ddict is None:
            # The emitted signal will reach self._update
            ddict = self.mdiArea.update()
        else:
            self._update(ddict)

    def _update(self, ddict):
        jump = ddict["Jump"]
        e0 = ddict["Edge"]
        maximumKRange = XASClass.e2k(ddict["NormalizedEnergy"][-1] - e0)
        self.parametersWidget.setJump(jump)
        self.parametersWidget.setMaximumK(maximumKRange)

    def setTitleColor(self, color):
        self.parametersWidget.setTitleColor(color)

class XASMdiArea(qt.QMdiArea):
    sigXASMdiAreaSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, analyzer=None, backend=None):
        super(XASMdiArea, self).__init__(parent)
        if analyzer is None:
            analyzer = XASClass.XASClass()
        self.analyzer = analyzer
        #self.setActivationOrder(qt.QMdiArea.CreationOrder)
        self._windowDict = {}
        self._windowList = ["Spectrum", "Post-edge", "Signal", "FT"]
        self._windowList.reverse()
        for title in self._windowList:
            plot = PlotWindow.PlotWindow(self,
                                         #control=True,
                                         position=True,
                                         backend=backend)
            plot.setWindowTitle(title)
            self.addSubWindow(plot)
            self._windowDict[title] = plot
            plot.setDataMargins(0, 0, 0.025, 0.025)
        self._windowList.reverse()
        self.setActivationOrder(qt.QMdiArea.StackingOrder)
        self.tileSubWindows()
        #self.cascadeSubWindows()
        #for window in self.subWindowList():
        #    print(" window = ", window.windowTitle())

    def getConfiguration(self):
        return self.analyzer.getConfiguration()

    def setConfiguration(self, ddict):
        # TODO: try except message
        return self.analyzer.setConfiguration(ddict)

    def setSpectrum(self, energy, mu):
        for key in self._windowDict:
            self._windowDict[key].clearCurves()
        # try to detect if we are working in eV or in keV
        if energy [0] < 200:
            if abs(energy[-1] - energy[0]) < 10:
                energy = energy * 1000.
        self._windowDict["Spectrum"].addCurve(energy,
                                              mu,
                                              legend="Spectrum",
                                              xlabel="Energy (eV)",
                                              ylabel="Absorption (a.u.)")
        return self.analyzer.setSpectrum(energy, mu)

    def update(self, ddict=None):
        if ddict is None:
            ddict = self.analyzer.processSpectrum()
        idx = (ddict["NormalizedEnergy"] >= ddict["NormalizedPlotMin"]) & \
                  (ddict["NormalizedEnergy"] <= ddict["NormalizedPlotMax"])
        plot = self._windowDict["Spectrum"]
        e0 = ddict["Edge"]
        plot.addCurve(ddict["Energy"] - e0, ddict["Mu"], legend="Spectrum",
                      xlabel="Energy (eV)", ylabel="Absorption (a.u.)",
                      replot=False, replace=True)
        plot.addCurve(ddict["NormalizedEnergy"][idx]  - e0,
                      ddict["NormalizedMu"][idx],
                      legend="Normalized",
                      xlabel="Energy (eV)",
                      ylabel="Absorption (a.u.)",
                      yaxis="right",
                      replot=False)
        plot.addCurve(ddict["NormalizedEnergy"] - e0,
               ddict["NormalizedSignal"], legend="Post", replot=False)
        plot.addCurve(ddict["NormalizedEnergy"] - e0,
               ddict["NormalizedBackground"], legend="Pre",replot=False)
        plot.resetZoom()
        #idxK = ddict["EXAFSKValues"] >= 0
        idx = (ddict["EXAFSKValues"] >= ddict["KMin"]) & \
              (ddict["EXAFSKValues"] <= ddict["KMax"])
        plot = self._windowDict["Post-edge"]
        plot.addCurve(ddict["EXAFSKValues"][idx],
                      ddict["EXAFSSignal"][idx],
                      legend="EXAFSSignal",
                      xlabel="K",
                      ylabel="Normalized Units",
                      replace=True,
                      replot=False)
        plot.addCurve(ddict["EXAFSKValues"][idx],
                      ddict["PostEdgeB"][idx],
                      legend="PostEdge",
                      xlabel="K",
                      ylabel="Normalized Units",
                      color="blue",
                      replot=False)
        plot.addCurve(ddict["KnotsX"],
                      ddict["KnotsY"],
                      legend="Knots",
                      replot=False,
                      linestyle="",
                      symbol="o",
                      color="orange")
        plot.resetZoom()
        plot = self._windowDict["Signal"]
        if ddict["KWeight"]:
            if ddict["KWeight"] == 1:
                ylabel = "EXAFS Signal * k"
            else:
                ylabel = "EXAFS Signal * k^%d" % ddict["KWeight"]
        else:
            ylabel = "EXAFS Signal"
        plot.addCurve(ddict["EXAFSKValues"][idx],
                      ddict["EXAFSNormalized"][idx],
                      legend="Normalized EXAFS",
                      xlabel="K",
                      ylabel=ylabel,
                      replace=True,
                      replot=False)
        plot.addCurve(ddict["FT"]["K"],
                      ddict["FT"]["WindowWeight"],
                      legend="FT Window",
                      xlabel="K",
                      ylabel="Weight",
                      yaxis="right",
                      color="red",
                      replace=False,
                      replot=False)
        plot.resetZoom()
        plot = self._windowDict["FT"]
        plot.addCurve(ddict["FT"]["FTRadius"],
                      ddict["FT"]["FTIntensity"],
                      legend="FT Intensity",
                      xlabel="R (Angstrom)",
                      ylabel="Arbitrary Units",
                      replace=True,
                      replot=False)
        """
        plot.addCurve(ddict["FT"]["FTRadius"],
                      ddict["FT"]["FTReal"],
                      legend="FT Real",
                      xlabel="R (Angstrom)",
                      ylabel="Arbitrary Units",
                      color="green",
                      replace=False,
                      replot=False)
        """
        plot.addCurve(ddict["FT"]["FTRadius"],
                      ddict["FT"]["FTImaginary"],
                      legend="FT Imaginary",
                      xlabel="R (Angstrom)",
                      ylabel="Arbitrary Units",
                      color="red",
                      replace=False,
                      replot=False)
        plot.resetZoom()
        self.sigXASMdiAreaSignal.emit(ddict)

if __name__ == "__main__":
    _logger.setLevel(logging.DEBUG)
    app = qt.QApplication([])
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR
    if len(sys.argv) > 1:
        fileName = sys.argv[1]
    else:
        fileName = os.path.join(PYMCA_DATA_DIR, "EXAFS_Ge.dat")
    data = specfile.Specfile(fileName)[0].data()[-2:, :]
    energy = data[0, :]
    mu = data[1, :]
    from PyMca5.PyMca import XASClass
    ownAnalyzer = XASClass.XASClass()
    configuration = ownAnalyzer.getConfiguration()
    w = XASDialog()
    w.setSpectrum(energy, mu)
    w.setConfiguration(configuration)
    print("SENT CONFIGURATION", configuration["Normalization"])
    if w.exec():
        print("PARAMETERS = ", w.getConfiguration())
    else:
        print("PARAMETERS = ", configuration)
