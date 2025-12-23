# /*##########################################################################
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
import os
import sys
import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt

if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaGui.plotting import ScatterPlotCorrelatorWidget
from PyMca5.PyMcaGui.pymca import ScanWindow
from PyMca5.PyMcaGui.pymca import ImageListStatsWidget
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaIO import ArraySave


class StackPluginResultsWindow(MaskImageWidget.MaskImageWidget):
    def __init__(self, *var, **kw):
        ddict = {}
        ddict["usetab"] = kw.get("usetab", True)
        ddict["aspect"] = kw.get("aspect", True)
        ddict["profileselection"] = kw.get("profileselection", True)
        ddict.update(kw)
        ddict["standalonesave"] = False
        MaskImageWidget.MaskImageWidget.__init__(self, *var, **ddict)
        self.slider = qt.QSlider(self)
        self.slider.setOrientation(qt.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        if ddict["usetab"]:
            # The 1D graph
            self.spectrumGraph = ScanWindow.ScanWindow(self)
            self.spectrumGraph.enableOwnSave(False)
            self.spectrumGraph.sigIconSignal.connect(self._spectrumGraphIconSlot)
            self.spectrumGraph.saveMenu = qt.QMenu()
            self.spectrumGraph.saveMenu.addAction(
                QString("Save From Current"), self.saveCurrentSpectrum
            )
            self.spectrumGraph.saveMenu.addAction(
                QString("Save From All"), self.saveAllSpectra
            )
            self.mainTab.addTab(self.spectrumGraph, "VECTORS")

        self.mainLayout.addWidget(self.slider)
        self.slider.valueChanged[int].connect(self._showImage)

        self.imageList = None
        self.imageNames = None
        self.spectrumList = None
        self.spectrumNames = None
        self.spectrumGraphTitles = None
        standalonesave = kw.get("standalonesave", True)
        if standalonesave:
            self.graphWidget.saveToolButton.clicked.connect(self._saveToolButtonSignal)
            self._saveMenu = qt.QMenu()
            self._saveMenu.addAction(QString("Image Data"), self.saveImageList)
            self._saveMenu.addAction(
                QString("Standard Graphics"), self.graphWidget._saveIconSignal
            )
            self._saveMenu.addAction(QString("Matplotlib"), self._saveMatplotlibImage)
        self.multiplyIcon = qt.QIcon(qt.QPixmap(IconDict["swapsign"]))
        infotext = "Multiply image by -1"
        self.multiplyButton = self.graphWidget._addToolButton(
            self.multiplyIcon,
            self._multiplyIconChecked,
            infotext,
            toggle=False,
            position=12,
        )

        # The density plot widget
        self.__scatterPlotWidgetDataToUpdate = True
        self.scatterPlotWidget = (
            ScatterPlotCorrelatorWidget.ScatterPlotCorrelatorWidget(
                None,
                labels=["Legend", "X", "Y"],
                types=["Text", "RadioButton", "RadioButton"],
                maxNRois=1,
            )
        )
        self.__scatterPlotWidgetDataToUpdate = True
        self.__maskToScatterConnected = True
        self.sigMaskImageWidgetSignal.connect(self._internalSlot)
        self.scatterPlotWidget.sigMaskScatterWidgetSignal.connect(self._internalSlot)

        # add the command to show it to the menu
        self.additionalSelectionMenu().addAction(
            QString("Show scatter plot"), self.showScatterPlot
        )

        # The stats widget
        self.statsWidget = None

    def sizeHint(self):
        return qt.QSize(400, 400)

    def _multiplyIconChecked(self):
        if self.imageList is None:
            return
        index = self.slider.value()
        self.imageList[index] *= -1
        if self.spectrumList is not None:
            self.spectrumList[index] *= -1

        self._showImage(index)
        # scatter plot related
        self.__scatterPlotWidgetDataToUpdate = True
        self._updateScatterPlotWidget()

    def _showImage(self, index):
        if len(self.imageList):
            self.showImage(index, moveslider=False)
        if self.spectrumList is not None:
            legend = self.spectrumNames[index]
            x = self.xValues[index]
            y = self.spectrumList[index]
            self.spectrumGraph.addCurve(x, y, legend, replace=True, replot=False)
            if self.spectrumGraphTitles is not None:
                self.spectrumGraph.setGraphTitle(self.spectrumGraphTitles[index])
            self.spectrumGraph.replot()

    def buildAndConnectImageButtonBox(self, replace=True, multiple=False):
        super(StackPluginResultsWindow, self).buildAndConnectImageButtonBox(
            replace=replace, multiple=multiple
        )

    def showImage(self, index=0, moveslider=True):
        if self.imageList is None:
            return
        if len(self.imageList) == 0:
            return
        # first the title to update any related selection curve legend
        self.graphWidget.graph.setGraphTitle(self.imageNames[index])
        self.setImageData(self.imageList[index])
        if moveslider:
            self.slider.setValue(index)

    def setStackPluginResults(
        self,
        images,
        spectra=None,
        image_names=None,
        spectra_names=None,
        xvalues=None,
        spectra_titles=None,
    ):
        self.spectrumList = spectra
        if type(images) == type([]):
            self.imageList = images
            if image_names is None:
                self.imageNames = []
                for i in range(nimages):
                    self.imageNames.append("Image %02d" % i)
            else:
                self.imageNames = image_names
        elif len(images.shape) == 3:
            nimages = images.shape[0]
            self.imageList = [0] * nimages
            for i in range(nimages):
                self.imageList[i] = images[i, :]
                if 0:
                    # leave the data as they originally come
                    if self.imageList[i].max() < 0:
                        self.imageList[i] *= -1
                        if self.spectrumList is not None:
                            self.spectrumList[i] *= -1
            if image_names is None:
                self.imageNames = []
                for i in range(nimages):
                    self.imageNames.append("Image %02d" % i)
            else:
                self.imageNames = image_names

        if self.imageList is not None:
            self.slider.setMaximum(len(self.imageList) - 1)
            self.showImage(0)
        else:
            self.slider.setMaximum(0)

        if self.spectrumList is not None:
            if spectra_names is None:
                self.spectrumNames = []
                for i in range(nimages):
                    self.spectrumNames.append("Spectrum %02d" % i)
            else:
                self.spectrumNames = spectra_names
            if xvalues is None:
                self.xValues = []
                for i in range(nimages):
                    self.xValues.append(numpy.arange(len(self.spectrumList[0])))
            else:
                self.xValues = xvalues
            self.spectrumGraphTitles = spectra_titles
            legend = self.spectrumNames[0]
            x = self.xValues[0]
            y = self.spectrumList[0]
            self.spectrumGraph.addCurve(x, y, legend, replace=True)
            if self.spectrumGraphTitles is not None:
                self.spectrumGraph.setGraphTitle(self.spectrumGraphTitles[0])

        self.slider.setValue(0)
        # scatter plot related
        self.__scatterPlotWidgetDataToUpdate = True
        self._updateScatterPlotWidget()

        # stats widget
        if self.statsWidget is not None:
            self.statsWidget.setSelectionMask(self.getSelectionMask())
            self.statsWidget.setImageList(self.imageList, image_names=self.imageNames)

    def _updateScatterPlotWidget(self):
        w = self.scatterPlotWidget
        if self.__scatterPlotWidgetDataToUpdate:
            for i in range(len(self.imageNames)):
                w.addSelectableItem(self.imageList[i], self.imageNames[i])
            self.__scatterPlotWidgetDataToUpdate = False
        w.setPolygonSelectionMode()
        w.setSelectionMask(self.getSelectionMask())

    def _internalSlot(self, ddict):
        if ddict["id"] == id(self):
            # signal generated by this instance
            # only the the scatter plot to be updated unless hidden
            if self.scatterPlotWidget.isHidden():
                return
            if ddict["event"] in [
                "selectionMaskChanged",
                "resetSelection",
                "invertSelection",
            ]:
                mask = self.getSelectionMask()
                if mask is None:
                    mask = numpy.zeros(self.imageList[0].shape, numpy.uint8)
                self.scatterPlotWidget.setSelectionMask(mask)
                if self.statsWidget:
                    self.statsWidget.setSelectionMask(mask)

        elif ddict["id"] == id(self.scatterPlotWidget):
            # signal generated by the scatter plot
            if ddict["event"] in [
                "selectionMaskChanged",
                "resetSelection",
                "invertSelection",
            ]:
                mask = self.scatterPlotWidget.getSelectionMask()
                super(StackPluginResultsWindow, self).setSelectionMask(mask, plot=True)
                ddict["id"] = id(self)
                try:
                    self.__maskToScatterConnected = False
                    self.sigMaskImageWidgetSignal.emit(ddict)
                finally:
                    self.__maskToScatterConnected = True

    def setSelectionMask(self, *var, **kw):
        super(StackPluginResultsWindow, self).setSelectionMask(*var, **kw)
        if not self.scatterPlotWidget.isHidden():
            self._updateScatterPlotWidget()
        if self.statsWidget is not None:
            self.statsWidget.setSelectionMask(self.getSelectionMask())

    def showScatterPlot(self):
        if self.scatterPlotWidget.isHidden():
            # it needs update
            self._updateScatterPlotWidget()
        self.scatterPlotWidget.show()

    def saveImageList(self, filename=None, imagelist=None, labels=None):
        if self.imageList is None:
            return
        labels = []
        for i in range(len(self.imageList)):
            labels.append(self.imageNames[i].replace(" ", "_"))
        return MaskImageWidget.MaskImageWidget.saveImageList(
            self, imagelist=self.imageList, labels=labels
        )

    def _spectrumGraphIconSlot(self, ddict):
        if ddict["event"] == "iconClicked" and ddict["key"] == "save":
            self.spectrumGraph.saveMenu.exec(qt.QCursor.pos())

    def saveCurrentSpectrum(self):
        return self.spectrumGraph._QSimpleOperation("save")

    def saveAllSpectra(self):
        fltrs = [
            "Raw ASCII *.txt",
            '","-separated CSV *.csv',
            '";"-separated CSV *.csv',
            '"tab"-separated CSV *.csv',
            "OMNIC CSV *.csv",
        ]
        message = "Enter file name to be used as root"
        fileList, fileFilter = PyMcaFileDialogs.getFileList(
            parent=self,
            filetypelist=fltrs,
            message=message,
            currentdir=None,
            mode="SAVE",
            getfilter=True,
            single=True,
            currentfilter=None,
            native=None,
        )
        if not len(fileList):
            return

        fileroot = fileList[0]
        dirname = os.path.dirname(fileroot)
        root, ext = os.path.splitext(os.path.basename(fileroot))
        if ext not in [".txt", ".csv"]:
            root = root + ext
            ext = ""

        # get appropriate extensions and separators
        filterused = fileFilter.split()
        if filterused[0].startswith("Raw"):
            csv = False
            ext = "txt"
            csvseparator = "  "
        elif filterused[0].startswith("OMNIC"):
            # extension is csv but saved as ASCII
            csv = False
            ext = "csv"
            csvseparator = ","
        else:
            csv = True
            ext = "csv"
            if "," in filterused[0]:
                csvseparator = ","
            elif ";" in filterused[0]:
                csvseparator = ";"
            elif "OMNIC" in filterused[0]:
                csvseparator = ","
            else:
                csvseparator = "\t"

        nSpectra = len(self.spectrumList)
        n = int(numpy.log10(nSpectra)) + 1
        fmt = "_%" + "0%dd" % n + ".%s"
        for index in range(nSpectra):
            legend = self.spectrumNames[index]
            x = self.xValues[index]
            y = self.spectrumList[index]
            filename = os.path.join(dirname, root + fmt % (index, ext))
            ArraySave.saveXY(
                x, y, filename, ylabel=legend, csv=csv, csvseparator=csvseparator
            )

    def setImageList(self, imagelist):
        self.imageList = imagelist
        self.spectrumList = None
        if imagelist is not None:
            self.slider.setMaximum(len(self.imageList) - 1)
            self.showImage(0)

    def _addAllImageClicked(self):
        ddict = {}
        ddict["event"] = "addAllClicked"
        ddict["images"] = self.imageList
        ddict["titles"] = self.imageNames
        ddict["id"] = id(self)
        self.emitMaskImageSignal(ddict)

    def showStatsWidget(self):
        if self.statsWidget is None:
            self.statsWidget = ImageListStatsWidget.ImageListStatsWidget(self)
            self.layout().addWidget(self.statsWidget)

        self.statsWidget.setSelectionMask(self.getSelectionMask())
        self.statsWidget.setImageList(self.imageList, image_names=self.imageNames)
        self.statsWidget.show()


def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)

    container = StackPluginResultsWindow()
    data = numpy.arange(20000)
    data = data.reshape(2, 100, 100)
    data[1, 0:100, 0:50] = 100
    container.setStackPluginResults(
        data,
        spectra=[numpy.arange(100.0), numpy.arange(100.0) + 10],
        image_names=["I1", "I2"],
        spectra_names=["V1", "V2"],
    )
    container.show()
    container.showStatsWidget()

    def theSlot(ddict):
        print(ddict["event"])

    container.sigMaskImageWidgetSignal.connect(theSlot)
    app.exec()


if __name__ == "__main__":
    import numpy

    test()
