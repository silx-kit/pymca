#/*##########################################################################
# Copyright (C) 2019-2023 European Synchrotron Radiation Facility
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
import numpy
from silx.gui import qt
from silx.gui.plot import ScatterView, items
from silx.gui.colors import Colormap

DEBUG = 0

DEFAULT_SCATTER_SYMBOL = "s"
DEFAULT_SCATTER_COLORMAP = "temperature"
DEFAULT_SCATTER_VISUALIZATION = items.Scatter.Visualization.POINTS

class ScatterViewUserDefault(ScatterView):
    _defaultColormap = None
    _defaultSymbol = None
    _defaultVisualization = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._defaultColormap is None:
            self._defaultColormap = Colormap(DEFAULT_SCATTER_COLORMAP)
        if self._defaultSymbol is None:
            self._defaultSymbol = DEFAULT_SCATTER_SYMBOL
        if self._defaultVisualization is None:
            self._defaultVisualization= DEFAULT_SCATTER_VISUALIZATION

        # Apply defaults
        self.setColormap(self._defaultColormap.copy())
        scatter = self.getScatterItem()
        scatter.setSymbol(self._defaultSymbol)
        scatter.setVisualization(self._defaultVisualization)

        # Connect to scatter item
        scatter.sigItemChanged.connect(self.__scatterItemChanged)

    def __scatterItemChanged(self, event):
        """Handle change of scatter item colormap and symbol"""
        if event is items.ItemChangedType.COLORMAP:
            ScatterViewUserDefault._defaultColormap = self.getScatterItem().getColormap().copy()
        elif event is items.ItemChangedType.SYMBOL:
            ScatterViewUserDefault._defaultSymbol = self.getScatterItem().getSymbol()
        elif event is items.ItemChangedType.VISUALIZATION_MODE:
            ScatterViewUserDefault._defaultVisualization = self.getScatterItem().getVisualization()
            
class SilxScatterWindow(qt.QWidget):
    def __init__(self, parent=None, backend="gl"):
        super(SilxScatterWindow, self).__init__(parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.plot = ScatterViewUserDefault(self, backend=backend)
        #self.plot = ScatterView(self, backend=backend)
        self.plot.getPlotWidget().setDataMargins(0.05, 0.05, 0.05, 0.05)
        self.mainLayout.addWidget(self.plot)
        self._plotEnabled = True
        self.dataObjectsList = []
        self.dataObjectsDict = {}
        self._xLabel = "X"
        self._yLabel = "Y"

    def _removeSelection(self, *var):
        if DEBUG:
            print("_removeSelection to be implemented")

    def _replaceSelection(self, *var):
        if DEBUG:
            print("_removeSelection to be implemented")

    def _addSelection(self, selectionlist):
        if DEBUG:
            print("_addSelection(self, selectionlist)",selectionlist)
        if type(selectionlist) == type([]):
            sellist = selectionlist
        else:
            sellist = [selectionlist]

        for sel in sellist:
            source = sel['SourceName']
            key    = sel['Key']
            legend = sel['legend'] #expected form sourcename + scan key
            dataObject = sel['dataobject']
            #only two-dimensional selections considered
            if dataObject.info.get("selectiontype", "1D") != "2D":
                continue
            if not hasattr(dataObject, "x"):
                raise TypeError("Not a scatter plot. No axes")
            elif len(dataObject.x) != 2:
                raise TypeError("Not a scatter plot. Invalid number of axes.")
            for i in range(len(dataObject.x)):
                if numpy.isscalar(dataObject.x[i]):
                    dataObject.x[i] = numpy.array([dataObject.x[i]])
            z = None
            if hasattr(dataObject, "y"):
                if dataObject.y not in [None, []]:
                    z = dataObject.y
            if z is None:
                if hasattr(dataObject, "data"):
                    if dataObject.data is not None:
                        z = [dataObject.data]
            if z is None:
                raise TypeError("Not a scatter plot. No signal.")
            elif not len(z):
                raise TypeError("Not a scatter plot. No signal.")
            for i in range(len(z)):
                if numpy.isscalar(z[i]):
                    z[i] = numpy.array([z[i]], dtype=numpy.float32)
            # we only deal with one signal, if there are more, they should be separated
            # in different selections
            x = numpy.ascontiguousarray(dataObject.x[0])[:]
            y = numpy.ascontiguousarray(dataObject.x[1])[:]
            data = numpy.ascontiguousarray(z[0], dtype=numpy.float32)[:]
            if (data.size == x.size) and (data.size == y.size):
                # standard scatter plot
                data = data.reshape(1, -1)
                nscatter = 1
            elif (x.size == y.size) and ((data.size % x.size) == 0):
                # we have n items, assuming they follow C order we can collapse them to
                # something that can be viewed. In this case (scatter) we can sum. The
                # only problem is that if we have a multidimensional monitor we have to
                # normalize first.
                oldDataShape = data.shape
                n = 1
                gotIt = False
                for i in range(len(oldDataShape)):
                    n *= oldDataShape[i]
                    if n == x.size:
                        gotIt = True
                        break
                if not gotIt:
                    raise ValueError("Unmatched dimensions following C order")
                data = data.reshape(x.size, *oldDataShape[i+1:])
                nscatter = data.shape[0]
            else:
                raise ValueError("Unmatched dimensions among axes and signals")

            # deal with the monitor
            if hasattr(dataObject, 'm'):
                if dataObject.m is not None:
                    for m in dataObject.m:
                        if numpy.isscalar(m):
                            data /= m
                        elif m.size == 1:
                            data /= m[0]
                        elif (m.size == data.shape[0]) and (m.size == data[0].shape):
                            # resolve an ambiguity, for instance, monitor has 10 values
                            # and the data to be normalized are 10 x 10
                            if len(m.shape) > 1:
                                # the monitor was multidimensional.
                                # that implies normalization "per pixel"
                                for i in range(data[0].shape):
                                    data[i] /= m.reshape(data[i].shape)
                            else:
                                # the monitor was unidimensional.
                                # that implies normalization "per acquisition point"
                                for i in range(m.size):
                                    data[i] /= m[i]
                        elif m.size == data.shape[0]:
                            for i in range(m.size):
                                data[i] /= m[i]
                        elif m.size == data[0].shape:
                            for i in range(data[0].shape):
                                data[i] /= m.reshape(data[i].shape)
                        elif m.size == data.size:
                            # potentially can take a lot of memory, numexpr?
                            tmpView = m[:]
                            tmpView = tmpView.reshape(*data.shape)
                            data /= tmpView
                        else:
                            raise ValueError("Incompatible monitor data")

            while len(data.shape) > 2:
                # collapse any additional dimension by summing
                data = data.sum(dtype=numpy.float32, axis=-1).astype(numpy.float32)
            dataObject.data = data
            x = numpy.ravel(x)
            y = numpy.ravel(y)
            dataObject.x = [x, y]
            if len(self.dataObjectsList):
                resetZoom = False
            else:
                resetZoom = True
            if legend not in self.dataObjectsList:
                self.dataObjectsList.append(legend)
            self.dataObjectsDict[legend] = dataObject
            try:
                self._xLabel, self._yLabel = self._getXYLabels(dataObject.info)
            except Exception:
                self._xLabel, self._yLabel = "X", "Y"

        if self._plotEnabled:
            self.showData(0)
            if resetZoom:
                self.plot.getPlotWidget().resetZoom()

    def _getXYLabels(self, info):
        xLabel = "X"
        yLabel = "Y"
        if ("LabelNames" in info) and ("selection") in info:
            xLabel = info["LabelNames"][info["selection"]["x"][0]]
            yLabel = info["LabelNames"][info["selection"]["x"][1]]
        return xLabel, yLabel

    def showData(self, index=0, moveslider=True):
        if DEBUG:
            print("showData called")
        legend = self.dataObjectsList[0]
        dataObject = self.dataObjectsDict[legend]
        shape = dataObject.data.shape
        x = dataObject.x[0]
        y = dataObject.x[1]
        #x.shape = -1
        #y.shape = -1
        values = dataObject.data[index]
        #values.shape = -1
        item = self.plot.getScatterItem()
        if item is None:
            # only one scatter there
            self.plot.getPlotWidget().remove(kind="scatter")
            self.plot.getPlotWidget().addScatter(x, y, values, info=dataObject.info)
        else:
            # by using the OO API symbol and colormap are kept
            item.setData(x, y, values)
            item.setInfo(dataObject.info)

        self.plot.getPlotWidget().setGraphXLabel(self._xLabel)
        self.plot.getPlotWidget().setGraphYLabel(self._yLabel)
        txt = "%s %d" % (legend, index)
        #self.setName(txt)
        #if moveslider:
        #    self.slider.setValue(index)

    def setPlotEnabled(self, value=True):
        self._plotEnabled = value
        if value:
            if len(self.dataObjectsList):
                self.showData()


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
        print("Test function called")

if __name__ == "__main__":
    from PyMca5 import DataObject
    import weakref
    import time
    import sys
    def buildDataObject(arrayData):
        dataObject = DataObject.DataObject()
        #dataObject.data = arrayData
        dataObject.y = [arrayData]
        x1, x0 = numpy.meshgrid(10 * numpy.arange(arrayData.shape[0]), numpy.arange(arrayData.shape[1]))
        dataObject.x = [x1, x0]
        dataObject.m = None
        dataObject.info['selectiontype'] = "2D"
        dataObject.info['Key'] = id(dataObject)
        return dataObject

    def buildSelection(dataObject, name = "image_data0"):
        key = dataObject.info['Key']
        def dataObjectDestroyed(ref, dataObjectKey=key):
            if DEBUG:
                print("dataObject distroyed key = %s" % key)
        dataObjectRef=weakref.proxy(dataObject, dataObjectDestroyed)
        selection = {}
        selection['SourceType'] = 'SPS'
        selection['SourceName'] = 'spec'
        selection['Key']        = name
        selection['legend']     = selection['SourceName'] + "  "+ name
        selection['imageselection'] = False
        selection['dataobject'] = dataObjectRef
        selection['selection'] = None
        return selection

    a = 1000
    b = 1000
    period = 1000
    x1 = numpy.arange(a * b).astype(numpy.float64)
    x1 = x1.reshape(a, b)
    x2 = numpy.transpose(x1)
    print("INPUT SHAPES = ", x1.shape, x2.shape)

    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    if len(sys.argv) > 1:
        PYMCA=True
    else:
        PYMCA = False

    if PYMCA:
        from PyMca5.PyMcaGui.pymca import PyMcaMain
        w = PyMcaMain.PyMcaMain()
        w.show()
    else:
        w = SilxScatterWindow()
        w.show()
    counter = 0
    def function(period = period):
        global counter
        flag = counter % 6
        if flag == 0:
            #add x1
            print("Adding X1", x1.shape, x2.shape)
            dataObject = buildDataObject(x1)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 1:
            #add x2
            print("Adding X2", x1.shape, x2.shape)
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X2')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 2:
            #add x1
            print("Changing X1", x1.shape, x2.shape)
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 1:
            #add x2
            print("Changing X2", x1.shape, x2.shape)
            dataObject = buildDataObject(x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherAddSelectionSlot(selection)
            else:
                w._addSelection(selection)
        elif flag == 4:
            #replace x1
            print("Replacing by new X1", x1.shape, x2.shape)
            dataObject = buildDataObject(x1-x2)
            selection = buildSelection(dataObject, 'X1')
            if PYMCA:
                w.dispatcherReplaceSelectionSlot(selection)
            else:
                w._replaceSelection(selection)
        else:
            #replace by x2
            print("Replacing by new X2", x1.shape, x2.shape)
            dataObject = buildDataObject(x2-x1)
            selection = buildSelection(dataObject, 'X2')
            if PYMCA:
                w.dispatcherReplaceSelectionSlot(selection)
            else:
                w._replaceSelection(selection)
        counter += 1

    loop = TimerLoop(function = function, period = period)
    ret = app.exec()
    sys.exit(ret)
