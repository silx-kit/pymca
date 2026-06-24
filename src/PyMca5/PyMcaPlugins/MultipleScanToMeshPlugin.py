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
__author__ = "Mauro Rovezzi & V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import numpy
import logging
_logger = logging.getLogger(__name__)

try:
    from matplotlib.mlab import griddata
    GRIDDATA = "matplotlib"
except ImportError:
    # matplotlib 3.x got rid of griddata
    try:
        from scipy.interpolate import griddata
        GRIDDATA = "scipy"
    except ImportError:
        GRIDDATA = None
        _logger.info("matplotlib.mlab.griddata not available")

from PyMca5 import Plugin1DBase
from PyMca5.PyMcaGui import MaskImageWidget
from PyMca5.PyMcaGui import PyMcaQt as qt

class MultipleScanToMeshPlugin(Plugin1DBase.Plugin1DBase):
    """
    This plugin attempts to create an image from multiple scans.

    It is aimed at dealing with:

    - ID26 RIXS Data
    - Meshes generated line by line.

    """
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.methodDict = {}
        self.methodDict['RIXS Etransfer'] = [self._energyTransfer,
                                             "Show RIXS E transfer image",
                                             None]
        self.methodDict['RIXS Eout'] = [self._energyAnalyzer,
                                        "Show RIXS E out image",
                                        None]
        self.methodDict['Mesh'] = [self._mesh,
                                   "Show mesh image",
                                   None]
        self._silx = None
        self._rixsWidget = None
        self._lastFixedMotorMne = None

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
        try:
            self.methodDict[name][0]()
        except Exception:
            _logger.error(sys.exc_info())
            raise

    def _mesh(self):
        return self._energyTransfer(mode="mesh")

    def _energyAnalyzer(self):
        return self._energyTransfer(mode="energyout")

    def _energyTransfer(self, mode="energytransfer"):
        allCurves = self.getAllCurves()

        nCurves = len(allCurves)
        if  nCurves < 2:
            msg = "RIXS scans are built combining several single scans"
            raise ValueError(msg)

        self._xLabel = self.getGraphXLabel()
        self._yLabel = self.getGraphYLabel()

        if self._xLabel not in \
           ["energy", "Energy", "Spec.Energy", "arr_hdh_ene", "Mono.Energy"]:
            if not self._xLabel.lower().startswith("energy"):
                msg = "X axis does not correspond to a supported RIXS scan"
                raise ValueError(msg)

        motorNames = allCurves[0][3]["MotorNames"]
        CHESS = False
        if self._xLabel == "Spec.Energy":
            # ID26
            fixedMotorMne = "Mono.Energy"
        elif (self._xLabel == "Energy") and ("xes_dn_ana" in motorNames):
            # CHESS
            fixedMotorMne = "xes_dn_ana"
            CHESS = True
            msg = "Please use CHESS provided plugin. Contact beamline staff"
            raise RuntimeError(msg)
        elif (self._xLabel == "energy") and ("xes_en" in motorNames):
            # BM20 case
            fixedMotorMne = "xes_en"
        elif "Spec.Energy" in motorNames:
            # ID26
            fixedMotorMne = "Spec.Energy"
        elif (self._xLabel == "energy_enc") and ("spenean0" in motorNames):
            # ID24-DCM
            fixedMotorMne = "spenean0"
        else:
            if self._lastFixedMotorMne is None:
                # TODO: Show a combobox to allow the selection of the "motor"
                pass
            if self._lastFixedMotorMne not in motorNames:
                self._lastFixedMotorMne = None
                msg = "Cannot automatically recognize motor mnemomnic to be used"
                raise ValueError(msg)
        fixedMotorIndex = allCurves[0][3]["MotorNames"].index(fixedMotorMne)

        #get the min and max values of the curves
        if fixedMotorMne != "Mono.Energy":
            xMin = allCurves[0][0][0] # ID26 data are already ordered
            xMax = allCurves[0][0][-1]

            minValues = numpy.zeros((nCurves,), numpy.float64)
            minValues[0] = xMin
            nData = len(allCurves[0][0])
            i = 0
            for curve in allCurves[1:]:
                i += 1
                tmpMin = curve[0][0]
                tmpMax = curve[0][-1]
                minValues[i] = tmpMin
                if tmpMin < xMin:
                    xMin = tmpMin
                if tmpMax > xMax:
                    xMax =tmpMax
                nData += len(curve[0])
        else:
            info = allCurves[0][3]
            xMin = info["MotorValues"][fixedMotorIndex]
            xMax = xMin
            nData = 0
            i = 0
            minValues = numpy.zeros((nCurves,), numpy.float64)
            for curve in allCurves:
                info = curve[3]
                tmpMin = info['MotorValues'][fixedMotorIndex]
                tmpMax = info['MotorValues'][fixedMotorIndex]
                minValues[i] = tmpMin
                if tmpMin < xMin:
                    xMin = tmpMin
                if tmpMax > xMax:
                    xMax =tmpMax
                nData += len(curve[0])
                i += 1

        #sort the curves
        orderIndex = minValues.argsort()

        #print "ORDER INDEX = ", orderIndex
        # express data in eV
        if (xMax - xMin) < 5.0 :
            # it seems data need to be multiplied
            factor = 1000.
        else:
            factor = 1.0

        motor2Values = numpy.zeros((nCurves,), numpy.float64)
        xData = numpy.zeros((nData,), numpy.float32)
        yData = numpy.zeros((nData,), numpy.float32)
        zData = numpy.zeros((nData,), numpy.float32)
        start = 0
        for i in range(nCurves):
            idx = orderIndex[i]
            curve = allCurves[idx]
            info = curve[3]
            nPoints = max(curve[0].shape)
            end = start + nPoints
            x = curve[0]
            z = curve[1]
            x = numpy.ravel(x)
            z = numpy.ravel(z)
            if fixedMotorMne == "Mono.Energy":
                xData[start:end] = info["MotorValues"][fixedMotorIndex] * factor
                yData[start:end] = x * factor
            elif CHESS:
                xData[start:end] = x * factor
                #yData[start:end] = info["MotorValues"][fixedMotorIndex]
                thetaDeg = 78.1119 + 0.5 * (info["MotorValues"][fixedMotorIndex] + 5.25)
                yData[start:end] = 12398.4 / (1.656446 * numpy.sin(numpy.pi*thetaDeg/180.))
            else:
                xData[start:end] = x * factor
                yData[start:end] = info["MotorValues"][fixedMotorIndex] * factor
            zData[start:end] = z
            start = end

        # construct the grid in steps of eStep eV
        eStep = 0.05
        n = int((xMax - xMin) * (factor / eStep))
        grid0 = numpy.linspace(xMin * factor, xMax * factor, n)
        grid1 = numpy.linspace(yData.min(), yData.max(), n)

        # create the meshgrid
        xx, yy = numpy.meshgrid(grid0, grid1)

        __THOUGHTS__ = """
            # get the interpolated values
            etData = xData - yData
            grid3 = numpy.linspace(etData.min(), etData.max(), n)
            xx, yy = numpy.meshgrid(grid0, grid3)
            try:
                zz = griddata(xData, etData, zData, xx, yy)
            except RuntimeError:
                zz = griddata(xData, etData, zData, xx, yy, interp='linear')

            # show them
            if self._rixsWidget is None:
                self._rixsWidget = MaskImageWidget.MaskImageWidget(\
                                            imageicons=False,
                                            selection=False,
                                            profileselection=True,
                                            scanwindow=self)
            shape = zz.shape
            xScale = (xx.min(), (xx.max() - xx.min())/float(zz.shape[1]))
            yScale = (yy.min(), (yy.max() - yy.min())/float(zz.shape[0]))
            self._rixsWidget.setImageData(zz,
                                          xScale=xScale,
                                          yScale=yScale)
            self._rixsWidget.setXLabel("Incident Energy (eV)")
            self._rixsWidget.setYLabel("Energy Transfer (eV)")
            self._rixsWidget.show()
            """
        
        if mode == "mesh":
            etData = yData
        else:
            etData = xData - yData
        grid3 = numpy.linspace(etData.min(), etData.max(), n)
        # create the meshgrid
        xx, yy = numpy.meshgrid(grid0, grid3)

        # get the interpolated values
        if GRIDDATA == "matplotlib":
            try:
                zz = griddata(xData, etData, zData, xx, yy)
            except Exception:
                # Natural neighbor interpolation not always possible
                zz = griddata(xData, etData, zData, xx, yy, interp='linear')
        elif GRIDDATA == "scipy":
            zz = griddata((xData, etData),
                          zData,
                          (xx, yy),
                          method='linear')
        else:
            raise RuntimeError("griddata function not available")

        if self._rixsWidget is None:
            try:
                from PyMca5.PyMcaGui.pymca import RGBImageCalculator
                self._rixsWidget = \
                        RGBImageCalculator.RGBImageCalculator( \
                            math=False,
                            usesilx=True)
                if not hasattr(self._rixsWidget, "setXLabel"):
                    self._rixsWidget.setXLabel = \
                        self._rixsWidget.graphWidget.plot.setGraphXLabel
                    self._rixsWidget.setYLabel = \
                        self._rixsWidget.graphWidget.plot.setGraphYLabel
                self._silx = True
            except Exception:
                _logger.info("Cannot use SilxMaskImageWidget")
                self._silx = False
                self._rixsWidget = MaskImageWidget.MaskImageWidget(\
                                            imageicons=False,
                                            selection=False,
                                            aspect=True,
                                            profileselection=True,
                                            scanwindow=self)
                self._rixsWidget.setLineProjectionMode('X')
        #actualMax = zData.max()
        #actualMin = zData.min()
        #zz = numpy.where(numpy.isfinite(zz), zz, actualMax)
        shape = zz.shape
        xScale = (xx.min(), (xx.max() - xx.min())/float(zz.shape[1]))
        if mode == "energyout":
            yScale = (yy.min() + yData.min(), (yy.max() - yy.min())/float(zz.shape[0]))
        else:
            yScale = (yy.min(), (yy.max() - yy.min())/float(zz.shape[0]))
        self._rixsWidget.setXLabel("Incident Energy (eV)")
        if mode == "mesh":
            self._rixsWidget.setYLabel("Emitted Energy (eV)")
        elif mode == "energyout":
            self._rixsWidget.setYLabel("Emitted Energy (eV)")
        else:
            self._rixsWidget.setYLabel("Energy Transfer (eV)")
        if self._silx:
            self._rixsWidget.graphWidget.setImageData(zz,
                                      xScale=xScale,
                                      yScale=yScale)
        else:
            self._rixsWidget.setImageData(zz,
                                      xScale=xScale,
                                      yScale=yScale)
        # self._rixsWidget.graph.replot()
        self._rixsWidget.show()
        self._rixsWidget.raise_()
        return

MENU_TEXT = "MultipleScanToMeshPlugin"
def getPlugin1DInstance(plotWindow, **kw):
    ob = MultipleScanToMeshPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    from PyMca5.PyMcaGraph import Plot
    app = qt.QApplication([])
    #w = ConfigurationWidget()
    #w.exec()
    #sys.exit(0)

    _logger.setLevel(logging.DEBUG)
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
