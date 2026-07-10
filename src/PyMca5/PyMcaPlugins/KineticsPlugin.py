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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy
try:
    from PyMca5 import Plugin1DBase
except ImportError:
    from . import Plugin1DBase

try:
    from PyMca5.PyMcaGui.math.fitting import RateLawWindow
except ImportError:
    print("KineticsPlugin problem")

class KineticsPlugin(Plugin1DBase.Plugin1DBase):
    '''Calculate Rate Laws plot and Arrhenius plot'''
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.methodDict = {}

        text = "Graphical calculation of Rate Laws"
        function = self.rateLaw
        info = text
        icon = None
        self.methodDict["Rate Law Plots"] =[function,
                                       info,
                                       icon]

        text = "Replace current (x, y) plot by (1/x, log(y)) plot"
        info = text
        icon = None
        function = self.arrhenius
        method = "Arrhenius Plot"
        self.methodDict[method] = [function,
                                   info,
                                   icon]

        self.widget = None

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

    def rateLaw(self):
        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            raise ValueError("Please select an active curve")
        x, y, legend0, info = activeCurve[:4]
        xmin, xmax = self.getGraphXLimits()
        idx = (x >= xmin) & (x <= xmax)
        x = x[idx]
        y = y[idx]
        if self.widget is None:
            parent = None
            self.widget = RateLawWindow.RateLawWindow(parent)
        self.widget.setSpectrum(x, y,
                                legend=legend0,
                                xlabel=info["xlabel"],
                                ylabel=info["ylabel"])
        self.widget.show()
        self.widget.raise_()

    def arrhenius(self):
        curves = self.getMonotonicCurves()
        nCurves = len(curves)
        if nCurves < 1:
            raise ValueError("At least one curve needed")

        # get legend of active curve
        try:
            activeCurveLegend = self.getActiveCurve()[2]
            if activeCurveLegend is None:
                activeCurveLegend = curves[0][2]
            for curve in curves:
                if curve[2] == activeCurveLegend:
                    activeCurve = curve
                    break
        except Exception:
            activeCurve = curves[0]
            activeCurveLegend = curves[0][2]

        # apply between graph limits
        xmin, xmax =self.getGraphXLimits()
        toPlot = []
        for curve in curves:
            x0, y0, legend, info = curve[:4]
            idx = numpy.nonzero((x0 >= xmin) & (x0 <= xmax) & (x0 != 0))[0]
            x = numpy.take(x0, idx)
            y = numpy.take(y0, idx)
            idx = numpy.nonzero(y > 0)[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)
            if not x.size:
                continue
            x = 1.0 / x
            y = numpy.log(y)
            toPlot.append((x, y, legend, info))

        for i in range(len(toPlot)):
            if i == 0:
                replace=True
            else:
                replace=False
            if i == (len(toPlot) - 1):
                replot = True
            else:
                replot=False
            x, y, legend, info = toPlot[i]            
            self.addCurve(x, y,
                         legend=legend,
                         info=info,
                         ylabel="log(%s)" % info["ylabel"],
                         xlabel="1/%s" % info["xlabel"],
                         replot=replot,
                         replace=replace)
        self.setActiveCurve(activeCurveLegend)

MENU_TEXT = "Kinetics Tools"
def getPlugin1DInstance(plotWindow, **kw):
    ob = KineticsPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    import os
    from PyMca5.PyMcaGui import PyMcaQt as qt
    from PyMca5.PyMcaGui import PlotWindow
    # first order, k = 4.820e-04
    x = [0, 600, 1200, 1800, 2400, 3000, 3600]
    y = [0.0365, 0.0274, 0.0206, 0.0157, 0.0117, 0.00860, 0.00640]
    order = "First"
    slope = "0.000482"
    print("Expected order: First")
    print("Expected slope: 0.000482")
    sigmay = None
    app = qt.QApplication([])
    plot = PlotWindow.PlotWindow()
    plot.setPluginDirectoryList([os.path.dirname(__file__)])
    plot.getPlugins()
    plot.addCurve(x, y, "Test Data")
    plot.show()
    plugin = getPlugin1DInstance(plot)
    for method in plugin.getMethods():
        print(method, ":", plugin.getMethodToolTip(method))
    #plugin.applyMethod(plugin.getMethods()[1])    
    app.exec()
