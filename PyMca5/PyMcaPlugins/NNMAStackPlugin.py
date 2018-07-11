#/*##########################################################################
# Copyright (C) 2004-2015 V.A. Sole, European Synchrotron Radiation Facility
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
from PyMca5.PyMcaGui import CalculationThread

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
        if mcaIndex not in [-1, len(shape) - 1]:
            raise IndexError("NNMA does not support stacks of images yet")
            return
        if self.configurationWidget is None:
            self.configurationWidget = NNMAParametersDialog(None)
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
        ddict = {'options': binningOptions,
                 'binning': 1,
                 'method': 0}
        self.configurationWidget.setParameters(ddict)
        y = spectrum
        self.configurationWidget.setSpectrum(x, y)
        self.configurationWidget.show()
        self.configurationWidget.raise_()
        ret = self.configurationWidget.exec_()
        if ret:
            self._executeFunctionAndParameters()

    def _executeFunctionAndParameters(self):
        _logger.debug("NNMAStackPlugin _executeFunctionAndParameters")
        self.widget = None
        self.thread = CalculationThread.CalculationThread(\
                            calculation_method=self.actualCalculation)
        self.thread.finished.connect(self.threadFinished)
        self.configurationWidget.show()
        message = "Please wait. NNMA Calculation going on."
        _logger.debug("NNMAStackPlugin starting thread")
        self.thread.start()
        _logger.debug("NNMAStackPlugin waitingMessageDialog")
        CalculationThread.waitingMessageDialog(self.thread,
                                message=message,
                                parent=self.configurationWidget)
        _logger.debug("NNMAStackPlugin waitingMessageDialog passed")

    def actualCalculation(self):
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
        #ddict['kmeans'] = False
        del nnmaParameters
        stack = self.getStackDataObject()
        if isinstance(stack, numpy.ndarray):
            if stack.data.dtype not in [numpy.float, numpy.float32]:
                _logger.warning("WARNING: Non floating point data")
                text = "Calculation going on."
                text += " WARNING: Non floating point data."
                self._status.setText(text)

        oldShape = stack.data.shape
        result = function(stack, **ddict)
        if stack.data.shape != oldShape:
            stack.data.shape = oldShape
        return result

    def threadFinished(self):
        _logger.debug("NNMAStackPlugin threadFinished")
        result = self.thread.result
        self.thread = None
        if type(result) == type((1,)):
            #if we receive a tuple there was an error
            if len(result):
                if type(result[0]) == type("Exception"):
                    if result[0] == "Exception":
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
