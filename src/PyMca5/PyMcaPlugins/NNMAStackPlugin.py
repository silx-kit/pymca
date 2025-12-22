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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
"""

A Stack plugin is a module that will be automatically added to the PyMca
stack windows in order to perform user defined operations on the data stack.

These plugins will be compatible with any stack window that provides the
functions:
    #data related
    getStackDataObject
    getStackData
    getStackInfo
    setStack

    #images related
    addImage
    removeImage
    replaceImage

    #mask related
    setSelectionMask
    getSelectionMask

    #displayed curves
    getActiveCurve
    getGraphXLimits
    getGraphYLimits

    #information method
    stackUpdated
    selectionMaskUpdated
"""
import numpy
import logging
from PyMca5 import StackPluginBase
from PyMca5.PyMcaGui.misc import CalculationThread

from PyMca5.PyMcaGui.math.NNMAWindow import NNMAParametersDialog
from PyMca5.PyMcaGui import StackPluginResultsWindow
from PyMca5.PyMcaGui import PyMca_Icons

qt = StackPluginResultsWindow.qt
_logger = logging.getLogger(__name__)


class NNMAStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {'Calculate': [self.calculate,
                                         "Perform NNMA",
                                         None],
                           'Show': [self._showWidget,
                                    "Show last results",
                                    PyMca_Icons.brushselect]}
        self.__methodKeys = ['Calculate', 'Show']
        self.configurationWidget = None
        self.widget = None
        self.thread = None

    def stackUpdated(self):
        _logger.debug("NNMAStackPlugin.stackUpdated() called")
        self.configurationWidget = None
        self.widget = None

    def selectionMaskUpdated(self):
        if self.widget is None:
            return
        if self.widget.isHidden():
            return
        mask = self.getStackSelectionMask()
        self.widget.setSelectionMask(mask)

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
        stack = self.getStackDataObject()
        mcaIndex = stack.info.get('McaIndex')
        shape = stack.data.shape
        stack = None
        if mcaIndex not in [0, -1, len(shape) - 1]:
            raise IndexError("NNMA only support stacks of images or spectra")
            return
        if self.configurationWidget is None:
            self.configurationWidget = NNMAParametersDialog(None, regions=True)
            self._status = qt.QLabel(self.configurationWidget)
            self._status.setAlignment(qt.Qt.AlignHCenter)
            font = qt.QFont(self._status.font())
            font.setBold(True)
            self._status.setFont(font)
            self._status.setText("Ready")
            self.configurationWidget.layout().addWidget(self._status)
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            #I could get some defaults from the stack itslef
            raise ValueError("Please select an active curve")
            return
        x, spectrum, legend, info = activeCurve
        spectrumLength = int(max(spectrum.shape))
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
        self.configurationWidget.raise_()
        ret = self.configurationWidget.exec()
        if ret:
            self._executeFunctionAndParameters()

    def _getFunctionAndParameters(self):
        """
        Get the function, vars and kw for the calculation thread
        """
        _logger.debug("NNMAStackPlugin actualCalculation")
        nnmaParameters = self.configurationWidget.getParameters()
        self._status.setText("Calculation going on")
        self.configurationWidget.setEnabled(False)
        #self.configurationWidget.close()
        #At some point I should make sure I get directly the
        #function and the parameters from the configuration widget
        function = nnmaParameters['function']
        ddict = {}
        ddict.update(nnmaParameters['kw'])
        ddict['ncomponents'] = nnmaParameters['npc']
        ddict['binning'] = nnmaParameters['binning']
        ddict['spectral_mask'] = nnmaParameters['spectral_mask']
        #ddict['kmeans'] = False
        if not self.isStackFinite():
            # one has to check for NaNs in the used region(s)
            # for the time being only in the global image
            # spatial_mask = numpy.isfinite(image_data)
            spatial_mask = numpy.isfinite(self.getStackOriginalImage())
            ddict['mask'] = spatial_mask
        del nnmaParameters
        return function, None, ddict

    def _executeFunctionAndParameters(self):
        _logger.debug("_executeFunctionAndParameters")
        self.widget = None
        self.configurationWidget.show()
        function, dummy, ddict = self._getFunctionAndParameters()
        _logger.info("NNMA function %s" % function.__name__)
        _logger.info("NNMA parameters %s" % ddict)

        stack = self.getStackDataObject()
        if isinstance(stack, numpy.ndarray):
            if stack.data.dtype not in [numpy.float64, numpy.float32]:
                _logger.warning("WARNING: Non floating point data")
                text = "Calculation going on."
                text += " WARNING: Non floating point data."
                self._status.setText(text)

        oldShape = stack.data.shape
        mcaIndex = stack.info.get('McaIndex')
        if mcaIndex == 0:
            # image stack. We need a copy
            _logger.info("NNMAStackPlugin converting to stack of spectra")
            data = numpy.zeros(oldShape[1:] + oldShape[0:1], dtype=numpy.float32)
            data = data.reshape(-1, oldShape[0])
            for i in range(oldShape[0]):
                tmpData = stack.data[i]
                tmpData = numpy.ravel(tmpData)
                data[:, i] = tmpData
            data = data.reshape(*(oldShape[1:] + oldShape[0:1]))
        else:
            data = stack
        try:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                result = function(inputStack, **ddict)
                self.threadFinished(result)
            else:
                thread = CalculationThread.CalculationThread(\
                                calculation_method=function,
                                calculation_vars=data,
                                calculation_kw=ddict,
                                expand_vars=False,
                                expand_kw=True)
                thread.start()
                message = "Please wait. NNMA Calculation going on."
                _logger.debug("NNMAStackPlugin waitingMessageDialog")
                CalculationThread.waitingMessageDialog(thread,
                                    message=message,
                                    parent=self.configurationWidget,
                                    modal=True,
                                    update_callback=None,
                                    frameless=False)
                _logger.debug("NNMAStackPlugin waitingMessageDialog passed")
                result = thread.getResult()
                self.threadFinished(result)
        except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Calculation error")
                msg.setText("Error on NNMA calculation")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
        finally:
            if mcaIndex == 0:
                data = None
            else:
                if stack.data.shape != oldShape:
                    stack.data = stack.data.reshape(*oldShape)

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

        images, eigenValues, eigenVectors = result
        imageNames = None
        vectorNames = None
        nimages = images.shape[0]
        imageNames = []
        vectorNames = []
        vectorTitles = []
        for i in range(nimages):
            imageNames.append("NNMA Image %02d" % i)
            vectorNames.append("NNMA Component %02d" % i)
            vectorTitles.append("%g %% explained intensity" %\
                                               eigenValues[i])
        _logger.debug("NNMAStackPlugin threadFinished. Create widget")
        self.widget = StackPluginResultsWindow.StackPluginResultsWindow(\
                                        usetab=True)
        _logger.debug("NNMAStackPlugin threadFinished. Widget created")
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
                                          spectra_names=vectorNames,
                                          spectra_titles=vectorTitles)
        self._showWidget()

    def _showWidget(self):
        if self.widget is None:
            return
        #Show
        self.widget.show()
        self.widget.raise_()

        #update
        self.selectionMaskUpdated()

MENU_TEXT = "PyMca NNMA"


def getStackPluginInstance(stackWindow, **kw):
    ob = NNMAStackPlugin(stackWindow)
    return ob
