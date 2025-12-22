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
import sys
import numpy
import logging
from . import RGBImageCalculator
qt = RGBImageCalculator.qt
QTVERSION = qt.qVersion()
from . import RGBCorrelator
from PyMca5.PyMcaGui.misc import FrameBrowser
USE_BROWSER = True

_logger = logging.getLogger(__name__)


class PyMcaImageWindow(RGBImageCalculator.RGBImageCalculator):
    def __init__(self, parent = None,
                 name = "PyMca Image Window",
                 correlator = None,
                 scanwindow=None,
                 usesilx=False):
        RGBImageCalculator.RGBImageCalculator.__init__(self, parent,
                                                       math = False,
                                                       replace = True,
                                                       scanwindow=scanwindow,
                                                       usesilx=usesilx)
        self.setWindowTitle(name)
        self.correlator = correlator
        self.ownCorrelator = False
        #self.mathBox.hide()
        self.dataObjectsList = []
        self.dataObjectsDict = {}
        self._plotEnabled    = True
        self._externalWidget = None
        self.setDefaultColormap(2, logflag=True)
        if USE_BROWSER:
            self.slider = FrameBrowser.HorizontalSliderWithBrowser(self)
        else:
            self.slider = qt.QSlider(self)
            self.slider.setOrientation(qt.Qt.Horizontal)
        self.slider.setRange(0, 0)
        self._xLabel = "Column"
        self._yLabel = "Row"
        self.mainLayout.addWidget(self.slider)
        self.slider.valueChanged[int].connect(self._showImageSliderSlot)
        self.slider.hide()

    def _connectCorrelator(self):
        if self.correlator is None:
            self.ownCorrelator = True
            self.correlator = RGBCorrelator.RGBCorrelator()
        self.correlator.setWindowTitle("ImageWindow RGB Correlator")
        self.sigAddImageClicked.connect(self.correlator.addImageSlot)
        self.sigRemoveImageClicked.connect(self.correlator.removeImageSlot)
        self.sigReplaceImageClicked.connect( \
            self.correlator.replaceImageSlot)


    def _addImageClicked(self):
        if self.correlator is None:
            self._connectCorrelator()
        if self._imageData is None:
            return
        if len(self._imageData) == 0:
            return

        if not RGBImageCalculator.RGBImageCalculator._addImageClicked(self):
            #if self.ownCorrelator:
                if self.correlator.isHidden():
                    self.correlator.show()

    def setDispatcher(self, w):
        w.sigAddSelection.connect(self._addSelection)
        w.sigRemoveSelection.connect(self._removeSelection)
        w.sigReplaceSelection.connect(self._replaceSelection)

    def _addSelection(self, selectionlist):
        _logger.debug("_addSelection(self, selectionlist=%s)", selectionlist)
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]

        for sel in sellist:
            self._xScale = None
            self._yScale = None
            xLabel = "Column"
            yLabel = "Row"
            source = sel['SourceName']
            key    = sel['Key']
            legend = sel['legend'] #expected form sourcename + scan key
            #if not "scanselection" in sel: continue
            #if not sel["scanselection"]:continue
            #if len(key.split(".")) > 2: continue
            dataObject = sel['dataobject']

            #only two-dimensional selections considered
            if dataObject.info.get("selectiontype", "1D") != "2D":
                continue
            if dataObject.data is None:
                # This is the SCAN regular mesh case
                if hasattr(dataObject, "y"):
                    if dataObject.y is not None:
                        dataObject.data = dataObject.y[0]
                        data0 = dataObject.y[0]
                        if len(data0.shape) == 1:
                            #we have to figure out the shape ...
                            if hasattr(dataObject, "x"):
                                if len(dataObject.x) == 2:
                                    x0 = dataObject.x[0][:]
                                    x0.shape = -1
                                    x1 = dataObject.x[1][:]
                                    x1.shape = -1
                                    if abs(x0[1] - x0[0]) < 1.0e-6:
                                        nColumns = numpy.argmin(abs(x0-x0[0]) < 1.0e-6)
                                        nRows = x1.size / nColumns
                                        if nRows!= int(nRows):
                                            raise ValueError("2D Selection not understood")
                                        transpose = False
                                        self._yScale = x0[0], x0[nColumns] - x0[0]
                                        self._xScale = x1[0], x1[1] - x1[0]
                                    elif abs(x1[1] - x1[0]) < 1.0e-6:
                                        nRows = numpy.argmin(abs(x1-x1[0]) < 1.0e-6)
                                        nColumns = x0.size / nRows
                                        if nColumns != int(nColumns):
                                            raise ValueError("2D Selection not understood")
                                        transpose = True
                                        self._xScale = x0[0], x0[1] - x0[0]
                                        self._yScale = x1[0], x1[nRows] - x1[0]
                                    else:
                                        raise TypeError("2D Selection is not a regular mesh")
                                    dataObject.data = numpy.zeros((len(dataObject.y),
                                                                   int(nRows),
                                                                   int(nColumns)),
                                                                   data0.dtype)
                                    for yIndex in range(len(dataObject.y)):
                                        if transpose:
                                            tmpData = numpy.transpose(dataObject.y[yIndex])[:]
                                        else:
                                            tmpData = dataObject.y[yIndex][:]
                                        tmpData.shape = int(nRows), int(nColumns)
                                        dataObject.data[yIndex] = tmpData
                    else:
                        _logger.info("Nothing to plot")
            elif hasattr(dataObject, "x") and (dataObject.x is not None):
                if "selection"  in sel:
                    axesLabels = self._getAxesLabelsFromSelection(sel["selection"])
                else:
                    axesLabels = []
                shape = dataObject.data.shape
                if len(dataObject.x) == 2:
                    x0 = dataObject.x[0][:]
                    x0.shape = -1
                    x1 = dataObject.x[1][:]
                    x1.shape = -1
                    if abs(x0[1] - x0[0]) < 1.0e-6:
                        nColumns = numpy.argmin(abs(x0-x0[0]) < 1.0e-6)
                        nRows = x1.size / nColumns
                        if nRows!= int(nRows):
                            _logger.warning("%f != %d", nRows, int(nRows))
                            raise ValueError("2D Selection not understood")
                        transpose = False
                        nColumns = int(nColumns)
                        self._yScale = x0[0], x0[nColumns] - x0[0]
                        self._xScale = x1[0], x1[1] - x1[0]
                    elif abs(x1[1] - x1[0]) < 1.0e-6:
                        nRows = numpy.argmin(abs(x1-x1[0]) < 1.0e-6)
                        nColumns = x0.size / nRows
                        if nColumns != int(nColumns):
                            _logger.warning("%f != %d", nColumns, int(nColumns))
                            raise ValueError("2D Selection not understood")
                        transpose = True
                        nRows = int(nRows)
                        self._xScale = x0[0], x0[1] - x0[0]
                        self._yScale = x1[0], x1[nRows] - x1[0]
                    elif (len(x0) == shape[-2]) and (len(x1) == shape[-1]):
                        self._xScale = x1[0], x1[1] - x1[0]
                        self._yScale = x0[0], x0[1] - x0[0]
                        if len(axesLabels) == 2:
                            xLabel = axesLabels[1]
                            yLabel = axesLabels[0]
                    elif (len(x0) == shape[-1]) and (len(x1) == shape[-2]):
                        self._yScale = x1[0], x1[1] - x1[0]
                        self._xScale = x0[0], x0[1] - x0[0]
                        if len(axesLabels) == 2:
                            xLabel = axesLabels[0]
                            yLabel = axesLabels[1]
                    else:
                        raise TypeError("2D Selection is not a regular mesh")

            self._xLabel = xLabel
            self._yLabel = yLabel
            dataObject.info['xlabel'] = xLabel
            dataObject.info['ylabel'] = yLabel
            self.dataObjectsList = [legend]
            self.dataObjectsDict = {legend:dataObject}
            shape = dataObject.data.shape
            if len(shape) == 2:
                self._nImages = 1
                self._imageData = dataObject.data
                if hasattr(dataObject, 'm'):
                    if dataObject.m is not None:
                        for m in dataObject.m:
                            if hasattr(m, "size"):
                                if m.size == self._imageData.size:
                                    tmpView = m[:]
                                    tmpView.shape = shape
                                    self._imageData = self._imageData / tmpView.astype(numpy.float64)
                                else:
                                    #let numpy raise the appropriate error
                                    self._imageData = self._imageData / numpy.float(m)
                            else:
                                self._imageData = self._imageData / numpy.float(m)
                self.slider.hide()
                self.setName(legend)
            else:
                self._nImages = 1
                for dimension in dataObject.data.shape[:-2]:
                    self._nImages *= dimension
                #This is a problem for dynamic data
                #dataObject.data.shape = self._nImages, shape[-2], shape[-1]
                self._imageData = self._getImageDataFromSingleIndex(0)
                self.slider.setRange(0, self._nImages - 1)
                self.slider.setValue(0)
                self.slider.show()
                self.setName(legend+" 0")
            if self._plotEnabled:
                self.plotImage(True)

    def _getAxesLabelsFromSelection(self, selection):
        labels = []
        if "x" in selection:
            if "LabelNames" in selection:
                if selection["x"]:
                    for idx in selection["x"]:
                        labels.append(selection["LabelNames"][idx])
        return labels

    def _getImageDataFromSingleIndex(self, index):
        legend = self.dataObjectsList[0]
        dataObject = self.dataObjectsDict[legend]
        shape = dataObject.data.shape
        if len(shape) == 2:
            if index > 0:
                raise IndexError("Only one image in stack")
            data = dataObject.data
            if hasattr(dataObject, 'm'):
                if dataObject.m is not None:
                    #is a list
                    for m in dataObject.m:
                        data = data / numpy.float(m)
            return data
        if len(shape) == 3:
            data = dataObject.data[index:index+1,:,:]
            data.shape = data.shape[1:]
            if hasattr(dataObject, 'm'):
                if dataObject.m is not None:
                    for m in dataObject.m:
                        if hasattr(m, "size"):
                            if m.size == data.size:
                                tmpView = m[:]
                                tmpView.shape = data.shape
                                data = data / tmpView.astype(numpy.float64)
                            else:
                                data = data / numpy.float(m)
                        else:
                            data = data / numpy.float(m)
            return data

        #I have to deduce the appropriate indices from the given index
        #always assuming C order
        acquisitionShape =  dataObject.data.shape[:-2]
        if len(shape) == 4:
            j = index % acquisitionShape[-1]
            i = int(index/(acquisitionShape[-1]*acquisitionShape[-2]))
            data = dataObject.data[i, j]
            if hasattr(dataObject, 'm'):
                if dataObject.m is not None:
                    for m in dataObject.m:
                        if hasattr(m, "size"):
                            if m.size == data.size:
                                tmpView = m[:]
                                tmpView.shape = data.shape
                                data = data / tmpView.astype(numpy.float64)
                            else:
                                data = data / numpy.float(m)
                        else:
                            data = data / numpy.float(m)
            return data
        raise IndexError("Unhandled dimension")

    def setPlotEnabled(self, value=True):
        self._plotEnabled = value
        if value:
            if self._imageData is not None:
                self.plotImage(True)
            else:
                self.graphWidget.graph.clear()
                pass

    def _removeSelection(self, selectionlist):
        _logger.debug("_removeSelection(self, selectionlist=%s)", selectionlist)
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]
        for sel in sellist:
            legend = sel['legend']
            if legend in self.dataObjectsList:
                self.dataObjectsList = []
            if legend in self.dataObjectsDict.keys():
                self.dataObjectsDict = {}
                #For the time being I prefer to leave the last image plotted
                #self._imageData = 0 * self._imageData
                #self.plotImage(True)

    def _replaceSelection(self, selectionlist):
        _logger.debug("_replaceSelection(self, selectionlist=%s)",
                      selectionlist)
        current = self.slider.value()
        self._addSelection(selectionlist)
        if current < self._nImages:
            self.showImage(current, moveslider=False)
        else:
            self.showImage(0, moveslider=True)

    def closeEvent(self, event):
        if self.ownCorrelator:
            self.correlator.close()
        RGBImageCalculator.RGBImageCalculator.closeEvent(self, event)

    def _showImageSliderSlot(self, index):
        self.showImage(index, moveslider=False)

    def showImage(self, index=0, moveslider=True):
        legend = self.dataObjectsList[0]
        dataObject = self.dataObjectsDict[legend]
        self._imageData = self._getImageDataFromSingleIndex(index)
        self.plotImage(True)
        txt = "%s %d" % (legend, index)
        self.setName(txt)
        if "xlabel" in dataObject.info:
            self._xLabel = dataObject.info["xlabel"]
        else:
            self._xLabel = "Column"
        if "ylabel" in dataObject.info:
            self._yLabel = dataObject.info["ylabel"]
        else:
            self._yLabel = "Row"

        if moveslider:
            self.slider.setValue(index)

    def plotImage(self, update=True):
        self.graphWidget.graph.setGraphYLabel(self._yLabel)
        self.graphWidget.graph.setGraphXLabel(self._xLabel)
        self.graphWidget.setImageData(self._imageData,
                                      xScale=self._xScale,
                                      yScale=self._yScale)
        return self.graphWidget.plotImage(update=update)

class TimerLoop:
    def __init__(self, function = None, period = 1000):
        self.__timer = qt.QTimer()
        if function is None: function = self.test
        self._function = function
        self.__setThread(function, period)
        #self._function = function

    def __setThread(self, function, period):
        self.__timer = qt.QTimer()
        self.__timer.timeout[()].connect(function)
        self.__timer.start(period)

    def test(self):
        _logger.info("Test function called")

if __name__ == "__main__":
    from PyMca5 import DataObject
    import weakref
    import time
    def buildDataObject(arrayData):
        dataObject = DataObject.DataObject()
        dataObject.data = arrayData
        dataObject.info['selectiontype'] = "2D"
        dataObject.info['Key'] = id(dataObject)
        return dataObject

    def buildSelection(dataObject, name = "image_data0"):
        key = dataObject.info['Key']
        def dataObjectDestroyed(ref, dataObjectKey=key):
            _logger.debug("dataObject distroyed key = %s", key)
        dataObjectRef=weakref.proxy(dataObject, dataObjectDestroyed)
        selection = {}
        selection['SourceType'] = 'SPS'
        selection['SourceName'] = 'spec'
        selection['Key']        = name
        selection['legend']     = selection['SourceName'] + "  "+ name
        selection['imageselection'] = True
        selection['dataobject'] = dataObjectRef
        return selection

    a = 1000
    b = 1000
    period = 1000
    x1 = numpy.arange(a * b).astype(numpy.float64)
    x1 = x1.reshape(a, b)
    x2 = numpy.transpose(x1)

    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    if len(sys.argv) > 1:PYMCA=True
    else:PYMCA = False

    if PYMCA:
        from PyMca5.PyMcaGui.pymca import PyMcaMain
        w = PyMcaMain.PyMcaMain()
        w.show()
    else:
        w = PyMcaImageWindow(usesilx=None)
        w.show()
    counter = 0
    def function(period = period):
        global counter
        flag = counter % 6
        if flag == 0:
            #add x1
            print("Adding X1")
            dataObject = buildDataObject(x1)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 1:
            #add x2
            print("Adding X2")
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X2')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 2:
            #add x1
            print("Changing X1")
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 1:
            #add x2
            print("Changing X2")
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 4:
            #replace x1
            print("Replacing by new X1")
            dataObject = buildDataObject(x1-x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherReplaceSelectionSlot(selection)
            else:
                w._replaceSelection(selection)
        else:
            #replace by x2
            print("Replacing by new X2")
            dataObject = buildDataObject(x2-x1)
            selection = buildSelection(dataObject, 'X2')
            if PYMCA:
                w.dispatcherReplaceSelectionSlot(selection)
            else:
                w._replaceSelection(selection)
        counter += 1

    loop = TimerLoop(function = function, period = period)
    sys.exit(app.exec())
