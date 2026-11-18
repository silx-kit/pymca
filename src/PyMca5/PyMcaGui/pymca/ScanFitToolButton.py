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
"""This module defines a QToolButton opening a fit menu when clicked:

    - :class:`ScanFitToolButton`

This button takes a plot object as constructor parameter.
"""


import silx.gui.icons

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.math.fitting import SimpleFitGui
from PyMca5.PyMcaGui.pymca import ScanFit




class ScanFitToolButton(qt.QToolButton):
    def __init__(self, plot, parent=None):
        """QAction offering a menu with two fit options: simple fit
        and custom fit.

        :param plot: :class:`ScanWindow` instance on which to operate
        :param parent: Parent QObject. If parent is an action group the action
            will be automatically inserted into the group.
        """
        qt.QToolButton.__init__(self, parent)
        self.setIcon(silx.gui.icons.getQIcon('math-fit'))
        self.setToolTip("Fit of Active Curve")
        self.clicked.connect(self._buttonClicked)

        self.plot = plot

        if not hasattr(self.plot, "scanFit"):
            self.scanFit = ScanFit.ScanFit()
        else:
            # ScanWindow can define a customized scanFit with custom fit functions
            self.scanFit = self.plot.scanFit
        self.scanFit.sigScanFitSignal.connect(
                self._scanFitSignalReceived)

        self.customFit = SimpleFitGui.SimpleFitGui()
        self.customFit.sigSimpleFitSignal.connect(
                self._customFitSignalReceived)

        self.fitButtonMenu = qt.QMenu()
        self.fitButtonMenu.addAction(
                "Simple Fit",
                self._scanFitSignal)
        self.fitButtonMenu.addAction(
                "Customized Fit",
                self._customFitSignal)

        self._scanFitLegend = None
        self._customFitLegend = None

    def _buttonClicked(self):
        """Display a menu to select simple fit or custom fit.

        Selecting simple fit calls :meth:`_scanFitSignal`.
        Selecting customized fit calls :meth:`_customFitSignal`.
        """
        self.fitButtonMenu.exec(self.plot.cursor().pos())

    def _getOneCurve(self):
        """Return active curve if any. Else return first curve, if any.
        Else return None
        :return: [x, y, legend, info, params] or None"""
        curve = self.plot.getActiveCurve()
        if curve is None:
            curves = self.plot.getAllCurves()
            if len(curves):
                curve = curves[0]
        return curve

    def _showFitWidget(self):
        """Initialize fit dialog widget and raise it.

        :attr:`_activeFitDialog` must be set to :attr:`scanFit` or
        :attr:`customFit` before this method is called.
        """
        curve = self._getOneCurve()
        if curve is None:
            return
        x, y, legend, info, params = curve

        xmin, xmax = self.plot.getGraphXLimits()

        fitLegend = legend + " Fit"
        if fitLegend in self.plot.getAllCurves(just_legend=True):
                self.plot.removeCurve(fitLegend)

        if self._activeFitDialog is self.scanFit:
            self._scanFitLegend = fitLegend
        elif self._activeFitDialog is self.customFit:
            self._customFitLegend = fitLegend

        self._activeFitDialog.setData(x=x,
                                      y=y,
                                      xmin=xmin,
                                      xmax=xmax,
                                      legend=legend)
        if self._activeFitDialog.isHidden():
            self._activeFitDialog.show()
        self._activeFitDialog.raise_()

    def _scanFitSignal(self):
        self._activeFitDialog = self.scanFit
        self._showFitWidget()

    def _customFitSignal(self):
        self._activeFitDialog = self.customFit
        self._showFitWidget()

    def _scanFitSignalReceived(self, ddict):
        if ddict['event'] == "FitFinished":
            xplot = self.scanFit.specfit.xdata * 1.0
            yplot = self.scanFit.specfit.gendata(parameters=ddict['data'])

            self.plot.addCurve(x=xplot, y=yplot, legend=self._scanFitLegend,
                               resetzoom=False)
        elif ddict['event'] == "ScanFitPrint":
            if hasattr(self.plot, "printHtml"):
                self.plot.printHtml(ddict['text'])

    def _customFitSignalReceived(self, ddict):
        if ddict['event'] == "FitFinished":
            xplot = ddict['x']
            yplot = ddict['yfit']

            self.plot.addCurve(xplot, yplot, legend=self._customFitLegend,
                               resetzoom=False)
