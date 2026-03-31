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
"""

"""
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaPhysics.xas import XASNormalization

from PyMca5.PyMcaCore import Plugin1DBase
try:
    from PyMca5.PyMcaPhysics.xas import XASClass
    from PyMca5.PyMcaGui.physics.xas import XASWindow
except ImportError:
    print("XASPlugin problem")


class XASPlugin(Plugin1DBase.Plugin1DBase):
    '''Normalization, EXAFS signal extraction and FT of XAS data''' 
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.methodDict = {}

        text = "Configure normalization parameters."
        function = self.configure
        info = text
        icon = None
        self.methodDict["Configure"] =[function,
                                       info,
                                       icon]

        text = "Replace all curves by normalized ones."
        function = self.getNormalization
        info = text
        icon = None
        self.methodDict["Normalize"] =[function,
                                       info,
                                       icon]

        text = "Replace all curves by their EXAFS FTs."
        function = self.getFT
        info = text
        icon = None
        self.methodDict["FT"] =[function,
                                       info,
                                       icon]

        text = "Replace all curves by their EXAFS Signal."
        function = self.getSignal0
        info = text
        icon = None
        self.methodDict["EXAFS"] =[function,
                                   info,
                                   icon]

        text = "Replace all curves by their EXAFS Signal."
        function = self.getSignal1
        info = text
        icon = None
        self.methodDict["EXAFS * k"] =[function,
                                   info,
                                   icon]

        text = "Replace all curves by their EXAFS Signal."
        function = self.getSignal2
        info = text
        icon = None
        self.methodDict["EXAFS * k^2"] =[function,
                                         info,
                                         icon]

        text = "Replace all curves by their EXAFS Signal."
        function = self.getSignal3
        info = text
        icon = None
        self.methodDict["EXAFS * k^3"] =[function,
                                         info,
                                         icon]

        self.analyzer = XASClass.XASClass()
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

    def configure(self):
        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            raise ValueError("Please select an active curve")
            return
        x, y, legend0, info = activeCurve
        xmin, xmax = self.getGraphXLimits()
        idx = (x >= xmin) & (x <= xmax)
        x = x[idx]
        y = y[idx]
        if self.widget is None:
            self._createWidget()
        self.widget.setSpectrum(x, y)
        oldConfiguration = self.analyzer.getConfiguration()
        self.widget.setConfiguration(oldConfiguration)
        ret = self.widget.exec()
        if ret:
            # it should be already configured
            pass
        else:
            self.analyzer.setConfiguration(oldConfiguration)

    def _createWidget(self):
        parent = None
        self.widget = XASWindow.XASDialog(parent,
                                          analyzer=self.analyzer)

    def processAllCurves(self):
        # for the time being we do not calculate just
        # what is asked but everything
        results = []
        curves = self.getMonotonicCurves()
        for curve in curves:
            x, y, legend, info = curve[0:4]
            self.analyzer.setSpectrum(x, y)
            ddict = self.analyzer.processSpectrum()
            results.append([ddict, legend, info])
        return results

    def getNormalization(self):
        xlabel="Energy (eV)"
        ylabel="Absorption (a.u.)"
        results = self.processAllCurves()
        n = len(results)
        i = 0
        for result in results:
            ddict, legend, info = result
            idx = (ddict["NormalizedEnergy"] >= ddict["NormalizedPlotMin"]) & \
                  (ddict["NormalizedEnergy"] <= ddict["NormalizedPlotMax"])
            x = ddict["NormalizedEnergy"][idx]
            y = ddict["NormalizedMu"][idx]
            if i == 0:
                replace = True
            else:
                replace = False
            i += 1
            if i == n:
                replot = True
            else:
                replot = False
            self.addCurve(x, y, legend, info,
                          xlabel=xlabel,
                          ylabel=ylabel,
                          replot=replot, replace=replace)

    def getFT(self):
        xlabel="R (Angstrom)"
        ylabel="Intensity (a.u.)"
        results = self.processAllCurves()
        n = len(results)
        i = 0
        for result in results:
            ddict, legend, info = result
            x = ddict["FT"]["FTRadius"]
            y = ddict["FT"]["FTIntensity"]
            if i == 0:
                replace = True
            else:
                replace = False
            i += 1
            if i == n:
                replot = True
            else:
                replot = False
            self.addCurve(x, y, legend, info,
                          xlabel=xlabel,
                          ylabel=ylabel,
                          replot=replot, replace=replace)

    def getSignal(self, weight=0):
        xlabel="K"
        weight = int(weight)
        if weight == 0:
            ylabel = "Signal"
        elif weight == 1:
            ylabel = "Signal * k"
        else:
            ylabel = "Signal * k^%d" % int(weight)
        results = self.processAllCurves()
        n = len(results)
        i = 0
        for result in results:
            ddict, legend, info = result
            idx = (ddict["EXAFSKValues"] >= ddict["KMin"]) & \
                  (ddict["EXAFSKValues"] <= ddict["KMax"])
            x = ddict["EXAFSKValues"][idx]
            if ddict["KWeight"] != weight:
                y =  ddict["EXAFSNormalized"][idx] * (pow(x, weight-ddict["KWeight"]))
            else:
                y = ddict["EXAFSNormalized"][idx]
            if i == 0:
                replace = True
            else:
                replace = False
            i += 1
            if i == n:
                replot = True
            else:
                replot = False
            self.addCurve(x, y, legend, info,
                          xlabel=xlabel,
                          ylabel=ylabel,
                          replot=replot, replace=replace)

    def getSignal0(self):
        self.getSignal(0)

    def getSignal1(self):
        self.getSignal(1)

    def getSignal2(self):
        self.getSignal(2)

    def getSignal3(self):
        self.getSignal(3)

    def XASNormalize(self):
        #all curves
        curves = self.getAllCurves()
        nCurves = len(curves)
        if nCurves < 1:
            raise ValueError("At least one curve needed")
            return

        #get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            raise ValueError("Please select an active curve")
            return

        x, y, legend0, info = activeCurve

        #sort the values
        idx = numpy.argsort(x, kind='mergesort')
        x0 = numpy.take(x, idx)
        y0 = numpy.take(y, idx)
        xmin, xmax = self.getGraphXLimits()

        # get calculation parameters
        if self.widget is None:
            self._createWidget()

        parameters = self.parameters
        if parameters['auto_edge']:
            edge = None
        else:
            edge = parameters['edge_energy']
        energy = x
        pre_edge_regions = parameters['pre_edge']['regions']
        post_edge_regions = parameters['post_edge']['regions']
        algorithm ='polynomial'
        algorithm_parameters = {}
        algorithm_parameters['pre_edge_order'] = parameters['pre_edge']\
                                                         ['polynomial']
        algorithm_parameters['post_edge_order'] = parameters['post_edge']\
                                                         ['polynomial']
        i = 0
        lastCurve = None
        for curve in curves:
            x, y, legend, info = curve[0:4]
            #take the portion ox x between limits
            idx = numpy.nonzero((x>=xmin) & (x<=xmax))[0]
            if not len(idx):
                #no overlap
                continue
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)

            idx = numpy.nonzero((x0>=x.min()) & (x0<=x.max()))[0]
            if not len(idx):
                #no overlap
                continue
            xi = numpy.take(x0, idx)
            yi = numpy.take(y0, idx)

            #perform interpolation
            xi = xi.reshape(-1, 1)
            yw = SpecfitFuns.interpol([x], y, xi, yi.min())

            # try: ... except: here?
            yw = numpy.ravel(yw)
            xi = numpy.ravel(xi)
            x, y = XASNormalization.XASNormalization(yw,
                                energy=xi,
                                edge=edge,
                                pre_edge_regions=pre_edge_regions,
                                post_edge_regions=post_edge_regions,
                                algorithm=algorithm,
                                algorithm_parameters=algorithm_parameters)[0:2]
            #
            if i == 0:
                replace = True
                replot = True
                i = 1
            else:
                replot = False
                replace = False
            newLegend = " ".join(legend.split(" ")[:-1])
            if not newLegend.startswith('Norm.'):
                newLegend = "Norm. " + newLegend
            self.addCurve(x, y,
                          legend=newLegend,
                          info=info,
                          replot=replot,
                          replace=replace)
            lastCurve = [x, y, newLegend]
        self.addCurve(lastCurve[0],
                      lastCurve[1],
                      legend=lastCurve[2],
                      info=info,
                      replot=True,
                      replace=False)

MENU_TEXT = "XAS"
def getPlugin1DInstance(plotWindow, **kw):
    ob = XASPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    import sys
    import os
    from PyMca5.PyMcaGui import PyMcaQt as qt
    from PyMca5.PyMcaGui import PlotWindow
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR
    if len(sys.argv) > 1:
        fileName = sys.argv[1]
    else:
        fileName = os.path.join(PYMCA_DATA_DIR, "EXAFS_Ge.dat")
    data = specfile.Specfile(fileName)[0].data()[-2:, :]
    energy = data[0, :]
    mu = data[1, :]
    app = qt.QApplication([])
    plot = PlotWindow.PlotWindow()
    plot.setPluginDirectoryList([os.path.dirname(__file__)])
    plot.getPlugins()
    plot.addCurve(energy, mu, os.path.basename(fileName))
    plot.show()
    plugin = getPlugin1DInstance(plot)
    for method in plugin.getMethods():
        print(method, ":", plugin.getMethodToolTip(method))
    #plugin.applyMethod(plugin.getMethods()[1])    
    app.exec()

