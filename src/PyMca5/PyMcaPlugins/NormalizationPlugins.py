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
"""This plugin provides methods to normalize all curves.

Following normalization methods are available:

 - Normalize to maximum y / max(y)
 - Subtract offset and normalize to new maximum (y-min(y))/(max(y)-min(y))
 - Subtract offset and normalize to integrated area (y-min(y))/trapz(max(y)-min(y),x)
 - Subtract offset and normalize to counts (y-min(y))/sum(max(y)-min(y))
 - Divide all curves by active curve
 - Take the negative of the log of the previous division
"""

__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
try:
    from PyMca5 import Plugin1DBase
except ImportError:
    from . import Plugin1DBase
import numpy
from PyMca5.PyMcaGui import PyMca_Icons

try:
    from PyMca5.PyMcaMath.fitting import SpecfitFuns
    HAS_SPECFIT = True
except ImportError:
    HAS_SPECFIT = False

class NormalizationPlugins(Plugin1DBase.Plugin1DBase):
    '''Normalization methods to simplify curve comparison'''
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.methodDict = {'y/max(y)':[self.toMaximum,
                        "Normalize to maximum",
                                       None],
                '(y-min(y))/(max(y)-min(y))':[self.offsetAndMaximum,
                       "Subtract offset and normalize to new maximum",
                                       None],
                '(y-min(y))/trapz(max(y)-min(y),x)':[self.offsetAndArea,
                       "Subtract offset and normalize to integrated area",
                                       None],
                '(y-min(y))/sum(max(y)-min(y))':[self.offsetAndCounts,
                       "Subtract offset and normalize to counts",
                                       None]}
        self._plotType = None

        if HAS_SPECFIT:
            self.methodDict['y/yactive'] = [self.divideByActiveCurve,
                       "Divide all curves by active curve",
                                       None]
            self.methodDict['-log(y/yactive)'] = [self.minusLogDivideByActiveCurve,
               "Take the negative log of the division of each curve by active curve",
                                       None]

    #Methods to be implemented by the plugin
    def getMethods(self, plottype=None):
        """
        A list with the NAMES  associated to the callable methods
        that are applicable to the specified plot.

        Plot type can be "SCAN", "MCA", None, ...
        """
        self._plotType = plottype
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

    def toMaximum(self):
        curves = self.getAllCurves()
        nCurves = len(curves)
        if not nCurves:
            return
        xmin, xmax = self.getGraphXLimits()
        i = 0
        for curve in curves:
            x, y, legend, info = curve[0:4]
            i1 = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
            yMax = numpy.take(y, i1).max()
            try:
                y = y/yMax
            except Exception:
                continue
            if i == 0:
                replace = (self._plotType != "MCA")
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=replot,
                          replace=replace)
        self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=True,
                          replace=False)

    def offsetAndMaximum(self):
        curves = self.getAllCurves()
        nCurves = len(curves)
        if not nCurves:
            return
        xmin, xmax = self.getGraphXLimits()
        i = 0
        for curve in curves:
            x, y, legend, info = curve[0:4]
            i1 = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
            x = numpy.take(x, i1)
            y = numpy.take(y, i1)
            try:
                ymin = numpy.nanmin(y)
                y = y - ymin
                ymax = numpy.nanmax(y)
                if ymax != 0:
                    y = y / ymax
            except Exception:
                print(sys.exc_info())
                continue
            if i == 0:
                replace = (self._plotType != "MCA")
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=replot,
                          replace=replace)
        self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=True,
                          replace=False)

    def offsetAndCounts(self):
        curves = self.getAllCurves()
        nCurves = len(curves)
        if not nCurves:
            return
        xmin, xmax = self.getGraphXLimits()
        i = 0
        for curve in curves:
            x, y, legend, info = curve[0:4]
            i1 = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
            x = numpy.take(x, i1)
            y = numpy.take(y, i1)
            try:
                ymin = numpy.nanmin(y)
                y = y - ymin
                ysum = numpy.nansum(y)
                y = y / ysum
            except Exception:
                print(sys.exc_info())
                continue
            if i == 0:
                replace = (self._plotType != "MCA")
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=replot,
                          replace=replace)
        self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=True,
                          replace=False)

    def offsetAndArea(self):
        curves = self.getAllCurves()
        nCurves = len(curves)
        if not nCurves:
            return
        xmin, xmax = self.getGraphXLimits()
        i = 0
        for curve in curves:
            x, y, legend, info = curve[0:4]
            i1 = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
            x = numpy.take(x, i1)
            y = numpy.take(y, i1)
            try:
                ymin = numpy.nanmin(y)
                y = y - ymin
                y = y / numpy.trapz(y, x)
            except Exception:
                print(sys.exc_info())
                continue
            if i == 0:
                replace = (self._plotType != "MCA")
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=replot,
                          replace=replace)
        self.addCurve(x, y,
                          legend=legend,
                          info=info,
                          replot=True,
                          replace=False)

    def minusLogDivideByActiveCurve(self):
        return self.divideByActiveCurve(minusLog=True)

    def divideByActiveCurve(self, minusLog=False):
        #all curves
        curves = self.getAllCurves()
        nCurves = len(curves)
        if nCurves < 2:
            raise ValueError("At least two curves needed")
            return

        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            raise ValueError("Please select an active curve")
            return

        x, y, legend0, info = activeCurve
        xmin, xmax = self.getGraphXLimits()
        y = y.astype(numpy.float64)

        #get the nonzero values
        idx = numpy.nonzero(abs(y) != 0.0)[0]
        if not len(idx):
            raise ValueError("All divisor values are zero!")
        x0 = numpy.take(x, idx)
        y0 = numpy.take(y, idx)

        #sort the values
        idx = numpy.argsort(x0, kind='mergesort')
        x0 = numpy.take(x0, idx)
        y0 = numpy.take(y0, idx)

        i = 0
        for curve in curves:
            x, y, legend, info = curve[0:4]
            if legend == legend0:
                continue
            #take the portion ox x between limits
            idx = numpy.nonzero((x>=xmin) & (x<=xmax))[0]
            if not len(idx):
                #no overlap
                continue
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)

            idx = numpy.nonzero((x0 >= numpy.nanmin(x)) & (x0 <= numpy.nanmax(x)))[0]
            if not len(idx):
                #no overlap
                continue
            xi = numpy.take(x0, idx)
            yi = numpy.take(y0, idx)

            #perform interpolation
            xi = xi.reshape(-1, 1)
            yw = SpecfitFuns.interpol([x], y, xi, yi.min())
            y = yw / yi
            if minusLog:
                y = -numpy.log(y)
                legend = "-log(%s/%s)" % (legend, legend0)
            else:
                legend = "%s/%s" % (legend, legend0)
            if i == 0:
                replace = (self._plotType != "MCA")
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            # this line is absolutely necessary!
            xi = xi.reshape(y.shape)
            self.addCurve(xi, y,
                          legend=legend,
                          info=info,
                          replot=replot,
                          replace=replace)
            lastCurve = [xi, y, legend]
        self.addCurve(lastCurve[0],
                      lastCurve[1],
                      legend=lastCurve[2],
                      info=info,
                      replot=True,
                      replace=False)

MENU_TEXT = "Normalization"
def getPlugin1DInstance(plotWindow, **kw):
    ob = NormalizationPlugins(plotWindow)
    return ob

if __name__ == "__main__":
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
