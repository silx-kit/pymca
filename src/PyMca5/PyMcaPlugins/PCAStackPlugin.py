#/*##########################################################################
# Copyright (C) 2004-2025 European Synchrotron Radiation Facility
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
This plugin opens a window allowing to configure and compute the principal
component analysis.
Each spectrum is considered an *observation*, and each channel is considered
a *variable*.

The user can configure following parameters:

  - PCA method (*Covariance, Expectation Max, Covariance Multiple Arrays*)
  - Number of Principal Components
  - Spectral Binning
  - Spectral Regions

After the configuration dialog is validated, the eigenimages and the
eigenvectors are computed and displayed in another window.

"""
# TODO: explain PCA methods and regions
# TODO: provide a practical use case for a PCA. Isolating elements?
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
import logging

from PyMca5 import StackPluginBase
from PyMca5.PyMcaMath.mva import KMeansModule
from PyMca5.PyMcaGui.misc import CalculationThread

from PyMca5.PyMcaGui.math.PCAWindow import PCAParametersDialog
from PyMca5.PyMcaGui import StackPluginResultsWindow
from PyMca5.PyMcaGui.pymca import RGBImageCalculator
from PyMca5.PyMcaGui import PyMca_Icons

qt = StackPluginResultsWindow.qt
_logger = logging.getLogger(__name__)


class PCAStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {'Calculate': [self.calculate, "Perform PCA", None],
                           'Show': [self._showWidget,
                                    "Show last results",
                                    PyMca_Icons.brushselect]}
        self.__methodKeys = ['Calculate', 'Show']
        if 0 and KMeansModule.KMEANS:
            self.methodDict['KMeans'] = [self._showKMeansWidget,
                                         "KMeans",
                                         None]
            self.__methodKeys.append('KMeans')
        self.configurationWidget = None
        self.widget = None
        self._kMeansWidget = None
        self.thread = None

    def stackUpdated(self):
        _logger.debug("PCAStackPlugin.stackUpdated() called")
        self.configurationWidget = None
        self.widget = None
        self._kMeansWidget = None

    def selectionMaskUpdated(self):
        if self.widget is None:
            return
        if self.widget.isHidden():
            if self._kMeansWidget is None:
                return
            elif self._kMeansWidget.isHidden():
                return
        mask = self.getStackSelectionMask()
        self.widget.setSelectionMask(mask)
        if self._kMeansWidget:
            self._kMeansWidget.graphWidget.setSelectionMask(mask)

    def mySlot(self, ddict):
        _logger.debug("mySlot %s %s", ddict['event'], ddict.keys())
        if ddict['event'] == "selectionMaskChanged":
            self.setStackSelectionMask(ddict['current'])
        elif ddict['event'] == "addImageClicked":
            self.addImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "addAllClicked":
            for i in range(len(ddict["images"])):
                self.addImage(ddict['images'][i], ddict['titles'][i])            
        elif ddict['event'] == "removeImageClicked":
            self.removeImage(ddict['title'])
        elif ddict['event'] == "replaceImageClicked":
            self.replaceImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "resetSelection":
            self.setStackSelectionMask(None)

    #Methods implemented by the plugin
    def getMethods(self):
        if self.widget is None:
            return [self.__methodKeys[0]]
        else:
            return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    #The specific part
    def calculate(self):
        if self.configurationWidget is None:
            stack = self.getStackDataObject()
            index = stack.info.get("McaIndex", -1)
            if index == len(stack.data.shape):
                index = -1
            stack = None
            self.configurationWidget = PCAParametersDialog(None,
                                                           regions=True,
                                                           index=index)
            self._status = qt.QLabel(self.configurationWidget)
            self._status.setAlignment(qt.Qt.AlignHCenter)
            font = qt.QFont(self._status.font())
            font.setBold(True)
            self._status.setFont(font)
            self._status.setText("Ready")
            self.configurationWidget.layout().addWidget(self._status)
        self.configurationWidget.setEnabled(True)
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            #I could get some defaults from the stack itslef
            raise ValueError("Please select an active curve")
            return
        x, spectrum, legend, info = activeCurve
        spectrumLength = max(spectrum.shape)
        oldValue = self.configurationWidget.nPC.value()
        self.configurationWidget.nPC.setMaximum(spectrumLength)
        self.configurationWidget.nPC.setValue(min(oldValue, spectrumLength))
        binningOptions = [1]
        for number in [2, 3, 4, 5, 7, 9, 10, 11, 13, 15, 17, 19]:
            if (spectrumLength % number) == 0:
                binningOptions.append(number)
        # TODO: Should inform the configuration widget about the possibility
        #       to encounter non-finite data?
        ddict = {'options': binningOptions,
                 'binning': 1,
                 'method': 0}
        self.configurationWidget.setParameters(ddict)
        y = spectrum
        self.configurationWidget.setSpectrum(x, y, legend=legend, info=info)
        self.configurationWidget.show()
        ret = self.configurationWidget.exec()
        if ret:
            self._kMeansWidget = None
            self._executeFunctionAndParameters()

    def _getFunctionAndParameters(self):
        """
        Get the function, vars and kw for the calculation thread
        """
        #obtain the parameters for the calculation
        pcaParameters = self.configurationWidget.getParameters()
        self._status.setText("Calculation going on")
        self.configurationWidget.setEnabled(False)
        #self.configurationWidget.close()
        self.__methodlabel = pcaParameters.get('methodlabel', "")
        function = pcaParameters['function']
        pcaParameters['ncomponents'] = pcaParameters['npc']
        # At some point I should make sure I get directly the
        # function and the parameters from the configuration widget
        del pcaParameters['npc']
        del pcaParameters['method']
        del pcaParameters['function']
        del pcaParameters['methodlabel']
        # binning = pcaParameters['binning']
        # mask = pcaParameters['mask']
        regions = pcaParameters['regions']
        spectral_mask = pcaParameters['spectral_mask']
        #print("regions = ", regions)
        #del pcaParameters['regions']
        #del pcaParameters['spectral_mask']
        #print("Regions and spectral mask not handled yet")
        if not self.isStackFinite():
            # one has to check for NaNs in the used region(s)
            # for the time being only in the global image
            # spatial_mask = numpy.isfinite(image_data)
            spatial_mask = numpy.isfinite(self.getStackOriginalImage())
            pcaParameters['mask'] = spatial_mask
        pcaParameters["legacy"] = False
        return function, None, pcaParameters

    def _executeFunctionAndParameters(self):
        _logger.debug("_executeFunctionAndParameters")
        self.widget = None
        self.configurationWidget.show()
        function, dummy, pcaParameters = self._getFunctionAndParameters()
        _logger.info("PCA function %s" % function.__name__)
        _logger.info("PCA parameters %s" % pcaParameters)
        if "Multiple" in self.__methodlabel:
            stackList = self.getStackDataObjectList()
            oldShapes = []
            for stack in stackList:
                oldShapes.append(stack.data.shape)
            inputStack = stackList
        else:
            stack = self.getStackDataObject()
            if isinstance(stack, numpy.ndarray):
                if stack.data.dtype not in [numpy.float64, numpy.float32]:
                    _logger.warning("WARNING: Non floating point data")
                    text = "Calculation going on."
                    text += " WARNING: Non floating point data."
                    self._status.setText(text)
            oldShape = stack.data.shape
            inputStack = stack

        try:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                result = function(inputStack, **pcaParameters)
                self.threadFinished(result)
            else:
                thread = CalculationThread.CalculationThread(\
                                calculation_method=function,
                                calculation_vars=inputStack,
                                calculation_kw=pcaParameters,
                                expand_vars=False,
                                expand_kw=True)
                thread.start()
                message = "Please wait. PCA Calculation going on."
                CalculationThread.waitingMessageDialog(thread,
                                    message=message,
                                    parent=self.configurationWidget,
                                    modal=True,
                                    update_callback=None,
                                    frameless=False)
                result = thread.getResult()
                self.threadFinished(result)
        except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Calculation error")
                msg.setText("Error on PCA calculation")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
        finally:
            if "Multiple" in self.__methodlabel:
                for i in range(len(stackList)):
                    stackList[i].data = stackList[i].data.reshape(oldShapes[i])
            else:
                if stack.data.shape != oldShape:
                    stack.data = stack.data.reshape(oldShape)

    def threadFinished(self, result):
        _logger.info("threadFinished")
        if type(result) == type((1,)):
            #if we receive a tuple there was an error
            if len(result):
                if isinstance(result[0], str) and result[0] == "Exception":
                    self._status.setText("Ready after calculation error")
                    self.configurationWidget.setEnabled(True)
                    raise Exception(result[1], result[2])
                    return
        self._status.setText("Ready")

        curve = self.configurationWidget.getSpectrum(binned=True)
        if curve not in [None, []]:
            xValues = curve[0]
        else:
            xValues = None
        self.configurationWidget.setEnabled(True)
        self.configurationWidget.close()
        if hasattr(result, "keys"):
            # new way
            images = result["scores"]
            eigenValues = result["eigenvalues"]
            eigenVectors = result["eigenvectors"]
            variance = result.get("variance", None)
            if variance is not None:
                explainedVariance = []
                for value in eigenValues:
                    explainedVariance.append(100 * (value/variance))
        else:
            variance = None
            images, eigenValues, eigenVectors = result
        methodlabel = self.__methodlabel
        imageNames = None
        vectorNames = None
        nimages = images.shape[0]
        imageNames = []
        vectorNames = []
        itmp = nimages
        if " ICA " in methodlabel:
            itmp = int(nimages / 2)
            for i in range(itmp):
                imageNames.append("ICAimage %02d" % i)
                vectorNames.append("ICAvector %02d" % i)
        if "Multiple" in methodlabel:
            xValues = None
        for i in range(itmp):
            imageNames.append("Eigenimage %02d" % i)
            vectorNames.append("Eigenvector %02d" % i)
            if variance is not None:
                vectorNames[-1] = "EV%02d Explained variance %.4f %%" % \
                                  (i, explainedVariance[i])

        self.widget = StackPluginResultsWindow.StackPluginResultsWindow(\
                                        usetab=True)
        self.widget.buildAndConnectImageButtonBox(replace=True,
                                                  multiple=True)
        qt = StackPluginResultsWindow.qt
        self.widget.sigMaskImageWidgetSignal.connect(self.mySlot)
        if xValues is not None:
            xValues = [xValues] * nimages
        self.widget.setStackPluginResults(images,
                                          spectra=eigenVectors,
                                          image_names=imageNames,
                                          xvalues=xValues,
                                          spectra_names=vectorNames)
        self._showWidget()

    def _showWidget(self):
        if self.widget is None:
            return
        #Show
        self.widget.show()
        self.widget.raise_()

        #update
        self.selectionMaskUpdated()

    def _showKMeansWidget(self):
        if self._kMeansWidget is None:
            self._kMeansWidget = RGBImageCalculator.RGBImageCalculator( \
                                    math="kmeans", selection=True)
            #self._kMeansWidget = MaskImageWidget.MaskImageWidget()
            #labels = KMeansModule.label(view, k=int(min(nImages, 4)))
            #labels.shape = nRows, nColumns
            self._kMeansWidget.graphWidget.sigMaskImageWidgetSignal.connect( \
                                            self.mySlot)
            # self._kMeansWidget.setImageData(labels)

        imageDict = {}
        for i in range(len(self.widget.imageList)):
            imageDict[self.widget.imageNames[i]] = \
                                        {"image":self.widget.imageList[i]}

        self._kMeansWidget.imageList = list(imageDict.keys())
        self._kMeansWidget.imageDict = imageDict

        #Show
        self._kMeansWidget.show()
        self._kMeansWidget.raise_()

        #update
        self.selectionMaskUpdated()

MENU_TEXT = "PyMca PCA"
def getStackPluginInstance(stackWindow, **kw):
    ob = PCAStackPlugin(stackWindow)
    return ob
