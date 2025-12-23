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
"""This plugin aligns all curves with the active curve, using the FFT.
"""
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy

try:
    from PyMca5.PyMcaCore import Plugin1DBase    
except ImportError:
    print("AlignmentScanPlugin import from somewhere else")
    from . import Plugin1DBase

from PyMca5.PyMcaMath.fitting import SpecfitFuns

class AlignmentScanPlugin(Plugin1DBase.Plugin1DBase):
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.__methodKeys = []
        self.methodDict = {}
        text = "FFT based alignment\n"
        info = text
        icon = None
        function = self.fftAlignment
        method = "FFT Alignment"
        self.methodDict[method] = [function,
                                   info,
                                   icon]
        self.__methodKeys.append(method)

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
        return None

    def applyMethod(self, name):
        """
        The plugin is asked to apply the method associated to name.
        """
        return self.methodDict[name][0]()

    def fftAlignment(self):
        curves = self.getMonotonicCurves()
        nCurves = len(curves)
        if nCurves < 2:
            raise ValueError("At least 2 curves needed")
            return

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
            activeCurveLegend = activeCurve[2]

        # apply between graph limits
        x0, y0 = activeCurve[0:2]
        xmin, xmax =self.getGraphXLimits()

        for curve in curves:
            xmax = float(min(xmax, curve[0][-1]))
            xmin = float(max(xmin, curve[0][0]))

        idx = numpy.nonzero((x0 >= xmin) & (x0 <= xmax))[0]
        x0 = numpy.take(x0, idx)
        y0 = numpy.take(y0, idx)

        #make sure values are regularly spaced
        xi = numpy.linspace(x0[0], x0[-1], len(idx)).reshape(-1, 1)
        yi = SpecfitFuns.interpol([x0], y0, xi, y0.min())
        x0 = xi * 1
        y0 = yi * 1

        y0 = numpy.ravel(y0)
        fft0 = numpy.fft.fft(y0)
        y0 = y0.reshape(-1, 1)
        x0 = x0.reshape(-1, 1)
        nChannels = x0.shape[0]

        # built a couple of temporary array of spectra for handy access
        shiftList = []
        curveList = []
        i = 0
        activeCurveIndex = 0
        for idx in range(nCurves):
            x, y, legend, info = curves[idx][0:4]
            if legend == activeCurveLegend:
                needInterpolation = False
                activeCurveIndex = idx
            elif x.size != x0.size:
                needInterpolation = True
            elif numpy.allclose(x, x0):
                # no need for interpolation
                needInterpolation = False
            else:
                needInterpolation = True

            if needInterpolation:
                # we have to interpolate
                x = numpy.ravel(x)
                y = numpy.ravel(y)
                xi = x0[:] * 1
                y = SpecfitFuns.interpol([x], y, xi, y0.min())
                x = xi

            y = numpy.ravel(y)
            i += 1

            # now calculate the shift
            ffty = numpy.fft.fft(y)

            if numpy.allclose(fft0, ffty):
                shiftList.append(0.0)
                x = numpy.ravel(x)
            else:
                shift = numpy.fft.ifft(fft0 * ffty.conjugate()).real
                shift2 = numpy.zeros(shift.shape, dtype=shift.dtype)
                m = shift2.size//2
                shift2[m:] = shift[:-m]
                shift2[:m] = shift[-m:]
                threshold = 0.80*shift2.max()
                #threshold = shift2.mean()
                idx = numpy.nonzero(shift2 > threshold)[0]
                #print("max indices = %d" % (m - idx))
                shift = (shift2[idx] * idx/shift2[idx].sum()).sum()
                #print("shift = ", shift - m, "in x units = ", (shift - m) * (x[1]-x[0]))

                # shift the curve
                shift = (shift - m) * (x[1]-x[0])
                x = numpy.ravel(x)
                y = numpy.fft.ifft(numpy.exp(-2.0*numpy.pi*numpy.sqrt(numpy.complex(-1))*\
                                numpy.fft.fftfreq(len(x), d=x[1]-x[0])*shift)*ffty)
                y = y.real
                y = numpy.ravel(y)
            curveList.append([x, y, legend + "SHIFT", False, False])
        curveList[-1][-2] = True
        curveList[-1][-1] = False
        x, y, legend, replot, replace = curveList[activeCurveIndex]
        self.addCurve(x, y, legend=legend, replot=True, replace=True)
        for i in range(len(curveList)):
            if i == activeCurveIndex:
                continue
            x, y, legend, replot, replace = curveList[i]
            self.addCurve(x,
                          y,
                          legend=legend,
                          info=None,
                          replot=replot,
                          replace=False)
        return

MENU_TEXT = "Alignment Plugin"
def getPlugin1DInstance(plotWindow, **kw):
    ob = AlignmentScanPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    import os
    try:
        from PyMca5.PyMcaGui import PyMcaQt as qt
        from PyMca5.PyMcaGui.plotting import PlotWindow
        app = qt.QApplication([])
        QT = True
        plot = PlotWindow.PlotWindow()
    except Exception:
        # test without graphical interface
        QT = False
        from PyMca5.PyMcaGraph import Plot
        plot = Plot.Plot()
    pluginDir = [os.path.dirname(__file__)]
    plot.getPlugins(method="getPlugin1DInstance",
                directoryList=pluginDir)
    i = numpy.arange(1000.)
    y1 = 10.0 + 5000.0 * numpy.exp(-0.01*(i-50)**2)
    y2 = 10.0 + 5000.0 * numpy.exp(-((i-55)/5.)**2)
    plot.addCurve(i, y1, "y1")
    plot.addCurve(i, y2, "y2")
    plugin = getPlugin1DInstance(plot)
    for method in plugin.getMethods():
        print(method, ":", plugin.getMethodToolTip(method))
    plugin.applyMethod(plugin.getMethods()[0])
    curves = plugin.getAllCurves()
    #for curve in curves:
    #    print(curve[2])
    print("LIMITS = ", plugin.getGraphYLimits())
    if QT:
        plot.show()
        app.exec()
