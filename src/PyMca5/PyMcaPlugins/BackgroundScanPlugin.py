#/*##########################################################################
# Copyright (C) 2004-2019 V.A. Sole, European Synchrotron Radiation Facility
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
"""
This plugin provides 3 methods:

  - subtract a SNIP1D background from the active curve
  - apply a Savitsky-Golay filter on the active curve
  - smooth and replace current curve by its SNIP1D background (deglitch)


"""
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy

from PyMca5 import Plugin1DBase
from PyMca5.PyMcaGui import SGWindow
from PyMca5.PyMcaGui import SNIPWindow
from PyMca5.PyMcaGui import PyMca_Icons

class BackgroundScanPlugin(Plugin1DBase.Plugin1DBase):
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        SGtext  = "Replace active curve by a\n"
        SGtext += "Savitsky-Golay treated one."
        SNIP1Dtext  = "Replace active curve by a\n"
        SNIP1Dtext += "SNIP1D treated one."
        self.methodDict = {}
        function = self.replaceActiveCurveWithSavitzkyGolayFiltering
        info = SGtext
        icon = PyMca_Icons.substract
        self.methodDict["Savitzky-Golay Filtering"] =[function,
                                                      info,
                                                      icon]
        function = self.subtract1DSnipBackgroundFromActiveCurve
        info = SNIP1Dtext
        self.methodDict["Subtract SNIP 1D Background"] =[function,
                                                      info,
                                                      icon]
        function = self.deglitchActiveCurveWith1DSnipBackground
        info  = "Smooth and replace current curve\n"
        info += "by its SNIP1D background."
        self.methodDict["Deglitch with SNIP 1D Background"] =[function,
                                                              info,
                                                              PyMca_Icons.smooth]
        self.__methodKeys = ["Subtract SNIP 1D Background",
                             "Savitzky-Golay Filtering",
                             "Deglitch with SNIP 1D Background"]
        self.subtract1DSnipParameters = None
        self.deglitch1DSnipParameters = None

    #Methods to be implemented by the plugin
    def getMethods(self, plottype=None):
        """
        A list with the NAMES  associated to the callable methods
        that are applicable to the specified plot.

        Plot type can be "SCAN", "MCA", None, ...
        """
        return self.__methodKeys

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

    def replaceActiveCurveWithSavitzkyGolayFiltering(self):
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            return
        x, spectrum, legend, info = activeCurve[:4]
        snipWindow = SGWindow.SGDialog(None,
                                           spectrum, x=x)
        snipWindow.graph.setGraphXLabel(info['xlabel'])
        snipWindow.graph.setGraphYLabel(info['ylabel'])
        #snipWindow.setModal(True)
        snipWindow.show()
        ret = snipWindow.exec()
        if ret:
            ydata = snipWindow.parametersWidget.background
            xdata = snipWindow.parametersWidget.xValues
            operations = info.get("operations", [])
            operations.append("SG Filtered")
            info['operations'] = operations
            self.addCurve(xdata, ydata, legend=legend, info=info, replot=True)

    def subtract1DSnipBackgroundFromActiveCurve(self, smooth=False):
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            return
        x, spectrum, legend, info = activeCurve[:4]
        snipWindow = SNIPWindow.SNIPDialog(None,
                                           spectrum, x=x, smooth=False)
        if self.subtract1DSnipParameters is not None:
            snipWindow.setParameters(self.subtract1DSnipParameters)
        snipWindow.graph.setGraphXLabel(info['xlabel'])
        snipWindow.graph.setGraphYLabel(info['ylabel'])
        snipWindow.show()
        ret = snipWindow.exec()
        if ret:
            ydata = snipWindow.parametersWidget.spectrum -\
                    snipWindow.parametersWidget.background
            xdata = snipWindow.parametersWidget.xValues
            operations = info.get("operations", [])
            operations.append("SNIP Background Removal")
            info['operations'] = operations
            # we cannot aford to change the name of the curve in order to properly
            # handle the calibration in an MCA window
            if "McaCalib" not in info:
                self.removeCurve(legend, replot=False)
                legend = legend + " Net"
            self.addCurve(xdata, ydata, legend=legend, info=info, replot=True)
            self.subtract1DSnipParameters = snipWindow.getParameters()

    def deglitchActiveCurveWith1DSnipBackground(self):
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            return
        x, spectrum, legend, info = activeCurve[:4]
        snipWindow = SNIPWindow.SNIPDialog(None,
                                           spectrum, x=x, smooth=True)
        if self.deglitch1DSnipParameters is not None:
            snipWindow.setParameters(self.deglitch1DSnipParameters)
        snipWindow.graph.setGraphXLabel(info['xlabel'])
        snipWindow.graph.setGraphYLabel(info['ylabel'])
        snipWindow.show()
        ret = snipWindow.exec()
        if ret:
            ydata = snipWindow.parametersWidget.background
            xdata = snipWindow.parametersWidget.xValues
            operations = info.get("operations", [])
            operations.append("SNIP Deglith")
            info['operations'] = operations
            self.addCurve(xdata, ydata, legend=legend, info=info, replot=True)
            self.deglitch1DSnipParameters = snipWindow.getParameters()

MENU_TEXT = "Background subtraction tools"
def getPlugin1DInstance(plotWindow, **kw):
    ob = BackgroundScanPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    from PyMca5.PyMcaGui import PyMcaQt as qt
    app = qt.QApplication([])
    from PyMca5.PyMcaGraph import Plot
    x = numpy.arange(100.)
    y = x * x
    plot = Plot.Plot()
    plot.addCurve(x, y, "dummy")
    plot.addCurve(x+100, -x*x)
    plugin = getPlugin1DInstance(plot)
    for method in plugin.getMethods():
        print(method, ":", plugin.getMethodToolTip(method))
    plugin.applyMethod(plugin.getMethods()[0])
    curves = plugin.getAllCurves()
    for curve in curves:
        print(curve[2])
    print("LIMITS = ", plugin.getGraphYLimits())
    #app = qt.QApplication()
