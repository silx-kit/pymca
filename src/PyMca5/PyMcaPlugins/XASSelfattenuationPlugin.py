#/*##########################################################################
# Copyright (C) 2004-2014 V.A. Sole, European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy
from PyMca5 import Plugin1DBase
from PyMca5.PyMcaPhysics.xas import XASSelfattenuationCorrection
from PyMca5.PyMcaGui.physics.xas import XASSelfattenuationWindow

class XASSelfattenuationPlugin(Plugin1DBase.Plugin1DBase):
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.methodDict = {}
        text = "Configure fluorescent XAS self-\n"
        text += "attenuation correction parameters.\n"
        text += "Input curves need to be normalized.\n"
        text += "For the time being thick sample is assumed."
        function = self.configure
        info = text
        icon = None
        self.methodDict["Configure"] =[function,
                                       info,
                                       icon]
        function = self.correctActive
        text = "Add corrected active curve."
        info = text
        icon = None
        self.methodDict["Correct Active"] =[function,
                                         info,
                                         icon]
        function = self.correctAll
        text = "Replace all curves by normalized ones."
        info = text
        icon = None
        self.methodDict["Correct All"] =[function,
                                         info,
                                         icon]
        self.widget = None
        self.instance = XASSelfattenuationCorrection.XASSelfattenuationCorrection()
        self.parameters = None
        self.configuration = None

    #Methods to be implemented by the plugin
    def getMethods(self, plottype=None):
        """
        A list with the NAMES  associated to the callable methods
        that are applicable to the specified plot.

        Plot type can be "SCAN", "MCA", None, ...
        """
        names = list(self.methodDict.keys())
        names.sort()
        return names

    def getMethodToolTip(self, name):
        """
        Returns the help associated to the particular method name or None.
        """
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        """
        Returns the pixmap associated to the particular method name or None.
        """
        return self.methodDict[name][2]

    def applyMethod(self, name):
        """
        The plugin is asked to apply the method associated to name.
        """
        self.methodDict[name][0]()
        return

    def configure(self):
        if self.widget is None:
            self.widget = XASSelfattenuationWindow.XASSelfattenuationDialog()
        ret = self.widget.exec()
        if ret:
            self.configuration = self.widget.getConfiguration()
            self.instance.setConfiguration(self.configuration)

    def correctActive(self):
        #check we have a configuration
        if self.configuration is None:
            raise RuntimeError("Please configure the plugin")

        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            raise ValueError("Please select an active curve")

        energy, spectrum, legend, info = activeCurve[0:4]
        spectrum = self.instance.correctNormalizedSpectrum(energy, spectrum)
        self.addCurve(energy, spectrum, legend="CORR"+legend, info=info, replace=False, replot=True)

    def correctAll(self):
        #check we have a configuration
        if self.configuration is None:
            raise RuntimeError("Please configure the plugin")

        curves = self.getAllCurves()
        nCurves = len(curves)
        if nCurves < 1:
            raise ValueError("At least one curve needed")

        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            activeCurve = curves[0]

        for i in range(nCurves):
            energy, spectrum, legend, info = curves[i][0:4]
            if i == 0:
                replace = True
            else:
                replace = False
            if i == nCurves - 1:
                replot = True
            else:
                replot = False
            spectrum = self.instance.correctNormalizedSpectrum(energy, spectrum)
            self.addCurve(energy, spectrum, legend="CORR"+legend, info=info,
                          replot=replot, replace=replace)

MENU_TEXT = "XAS Self-Attenuation Correction"
def getPlugin1DInstance(plotWindow, **kw):
    ob = XASSelfattenuationPlugin(plotWindow)
    return ob
