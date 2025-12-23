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

import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons

IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaGui.pymca import ScanWindow
from PyMca5.PyMcaMath.mva import PCAModule
from PyMca5.PyMcaGui.plotting import ScatterPlotCorrelatorWidget

if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str

MDP = PCAModule.MDP
MATPLOTLIB = MaskImageWidget.MATPLOTLIB
QTVERSION = MaskImageWidget.QTVERSION
import logging

_logger = logging.getLogger(__name__)


class PCAParametersDialog(qt.QDialog):
    def __init__(
        self, parent=None, options=[1, 2, 3, 4, 5, 10], regions=False, index=-1
    ):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("PCA Configuration Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(11, 11, 11, 11)
        self.mainLayout.setSpacing(0)

        self.methodOptions = qt.QGroupBox(self)
        self.methodOptions.setTitle("PCA Method to use")
        self.methods = [
            "Covariance",
            "Correlation",
            "Expectation Max.",
            "Cov. Multiple Arrays",
            "Corr. Multiple Arrays",
        ]
        self._multipleIndex = [3, 4]
        self.functions = [
            PCAModule.numpyCovariancePCA,
            PCAModule.numpyCorrelationPCA,
            PCAModule.expectationMaximizationPCA,
            PCAModule.multipleArrayCovariancePCA,
            PCAModule.multipleArrayCorrelationPCA,
        ]
        self.methodOptions.mainLayout = qt.QGridLayout(self.methodOptions)
        self.methodOptions.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.methodOptions.mainLayout.setSpacing(2)
        if MDP and (index != 0):
            # self.methods.append("MDP (PCA + ICA)")
            self.methods.append("MDP (SVD float32)")
            self.methods.append("MDP (SVD float64)")
            self.methods.append("MDP ICA (float32)")
            self.methods.append("MDP ICA (float64)")
            self.functions.append(PCAModule.mdpPCASVDFloat32)
            self.functions.append(PCAModule.mdpPCASVDFloat64)
            self.functions.append(PCAModule.mdpICAFloat32)
            self.functions.append(PCAModule.mdpICAFloat64)
        self.buttonGroup = qt.QButtonGroup(self.methodOptions)
        i = 0
        for item in self.methods:
            rButton = qt.QRadioButton(self.methodOptions)
            row = int(i / 5)
            col = i % 5
            self.methodOptions.mainLayout.addWidget(rButton, row, col)
            # self.l.setAlignment(rButton, qt.Qt.AlignHCenter)
            if i == 1:
                rButton.setChecked(True)
            rButton.setText(item)
            self.buttonGroup.addButton(rButton)
            self.buttonGroup.setId(rButton, i)
            i += 1

        if hasattr(self.buttonGroup, "idClicked"):
            self.buttonGroup.idClicked[int].connect(self._slot)
        else:
            # deprecated
            _logger.debug("PCAWindow. Using deprecated signal")
            self.buttonGroup.buttonClicked[int].connect(self._slot)

        self.mainLayout.addWidget(self.methodOptions)

        # built in speed options
        self.speedOptions = qt.QGroupBox(self)
        self.speedOptions.setTitle("Speed Options")
        self.speedOptions.mainLayout = qt.QGridLayout(self.speedOptions)
        self.speedOptions.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.speedOptions.mainLayout.setSpacing(2)
        labelPC = qt.QLabel(self)
        labelPC.setText("Number of PC:")
        self.nPC = qt.QSpinBox(self.speedOptions)
        self.nPC.setMinimum(0)
        self.nPC.setValue(10)
        self.nPC.setMaximum(40)

        self.binningLabel = qt.QLabel(self.speedOptions)
        self.binningLabel.setText("Spectral Binning:")
        self.binningCombo = qt.QComboBox(self.speedOptions)
        for option in options:
            self.binningCombo.addItem("%d" % option)
        self.speedOptions.mainLayout.addWidget(labelPC, 0, 0)
        self.speedOptions.mainLayout.addWidget(self.nPC, 0, 1)
        # self.speedOptions.mainLayout.addWidget(qt.HorizontalSpacer(self), 0, 2)
        self.speedOptions.mainLayout.addWidget(self.binningLabel, 1, 0)
        self.speedOptions.mainLayout.addWidget(self.binningCombo, 1, 1)
        self.binningCombo.activated[int].connect(self._updatePlotFromBinningCombo)
        if regions:
            self.__regions = True
            self.__addRegionsWidget()
        else:
            self.__regions = False
            # the optional plot
            self.graph = None

        # the OK button
        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(0)
        self.okButton = qt.QPushButton(hbox)
        self.okButton.setText("Accept")
        self.okButton.setAutoDefault(False)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.okButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        self.mainLayout.addWidget(self.speedOptions)
        if regions:
            self.mainLayout.addWidget(self.regionsWidget)
        self.mainLayout.addWidget(hbox)
        if self.graph is not None:
            self.mainLayout.addWidget(self.graph)

        self.okButton.clicked.connect(self.accept)

    def __addRegionsWidget(self):
        # Region handling
        self.regionsWidget = RegionsWidget(self)
        self.regionsWidget.setEnabled(True)
        self.regionsWidget.sigRegionsWidgetSignal.connect(self.regionsWidgetSlot)
        # the plot
        self.graph = ScanWindow.ScanWindow(self)
        self.graph.setEnabled(False)
        self.graph.sigPlotSignal.connect(self._graphSlot)
        if not self.__regions:
            # I am adding after instantiation
            self.mainLayout.insertWidget(2, self.regionsWidget)
            self.mainLayout.addWidget(self.graph)
        self.__regions = True

    def regionsWidgetSlot(self, ddict):
        if ddict["nRegions"] > 0:
            fromValue = ddict["from"]
            toValue = ddict["to"]
            self.graph.setEnabled(True)
            self.graph.clearMarkers()
            self.graph.insertXMarker(
                fromValue, "From", text="From", color="blue", draggable=True
            )
            self.graph.insertXMarker(
                toValue, "To", text="To", color="blue", draggable=True
            )
            self.graph.replot()
        else:
            self.graph.clearMarkers()
            self.graph.setEnabled(False)

    def _graphSlot(self, ddict):
        if ddict["event"] == "markerMoved":
            marker = ddict["label"]
            value = ddict["x"]
            signal = False
            if marker == "From":
                self.regionsWidget.fromLine.setText("%f" % value)
            elif marker == "To":
                self.regionsWidget.toLine.setText("%f" % value)
            else:
                signal = True
            self.regionsWidget._editingSlot(signal=signal)

    def _slot(self, index):
        button = self.buttonGroup.button(index)
        button.setChecked(True)
        self.binningLabel.setText("Spectral Binning:")
        if index not in self._multipleIndex:
            self.binningCombo.setEnabled(True)
        else:
            self.binningCombo.setEnabled(False)
        if self.__regions:
            if index not in self._multipleIndex:
                self.regionsWidget.setEnabled(True)
                self.graph.setEnabled(True)
            else:
                self.regionsWidget.setEnabled(False)
                self.graph.setEnabled(False)
        return

    def setSpectrum(self, x, y, legend=None, info=None):
        if self.graph is None:
            self.__addRegionsWidget()
        if legend is None:
            legend = "Current Active Spectrum"
        if info is None:
            info = {}
        if not isinstance(x, numpy.ndarray):
            x = numpy.array(x)
            y = numpy.array(y)

        self._x = x
        self._y = y
        self.regionsWidget.setLimits(x.min(), x.max())
        self._legend = legend
        self._info = info
        self.updatePlot()

    def getSpectrum(self, binned=False):
        if binned:
            return self._binnedX, self._binnedY, self._legend, self._info
        else:
            return self._x, self._y, self._legend, self._info

    # value unused, but received with the Qt signal
    def _updatePlotFromBinningCombo(self, value):
        if self.graph is None:
            return
        self.updatePlot()

    def updatePlot(self):
        binning = int(self.binningCombo.currentText())
        x = self._x * 1.0
        y = self._y * 1.0
        x = x.reshape(1, -1)
        y = y.reshape(1, -1)
        r, c = x.shape
        x = x.reshape(r, int(c / binning), binning)
        y = y.reshape(r, int(c / binning), binning)
        x = x.sum(axis=-1, dtype=numpy.float32) / binning
        y = y.sum(axis=-1, dtype=numpy.float32)
        x = numpy.ravel(x)
        y = numpy.ravel(y)
        self._binnedX = x
        self._binnedY = y
        self.graph.addCurve(x, y, legend=self._legend, replace=True)

    def setParameters(self, ddict):
        if "options" in ddict:
            self.binningCombo.clear()
            for option in ddict["options"]:
                self.binningCombo.addItem("%d" % option)
        if "binning" in ddict:
            option = "%d" % ddict["binning"]
            for i in range(self.binningCombo.count()):
                if str(self.binningCombo.itemText(i)) == option:
                    self.binningCombo.setCurrentIndex(i)
        if "npc" in ddict:
            self.nPC.setValue(ddict["npc"])
        if "method" in ddict:
            self.buttonGroup.buttons()[ddict["method"]].setChecked(True)
            if ddict["method"] not in self._multipleIndex:
                self.binningCombo.setEnabled(True)
            else:
                self.binningCombo.setEnabled(False)
        if "regions" in ddict:
            self.regionsWidget.setRegions(regions)
        return

    def getParameters(self):
        ddict = {}
        ddict["binning"] = int(self.binningCombo.currentText())
        ddict["npc"] = self.nPC.value()
        i = self.buttonGroup.checkedId()
        ddict["method"] = i
        ddict["methodlabel"] = self.methods[i]
        ddict["function"] = self.functions[i]
        mask = None
        if self.__regions:
            regions = self.regionsWidget.getRegions()
            if not len(regions):
                mask = None
            else:
                mask = numpy.zeros(self._binnedX.shape, dtype=numpy.uint8)
                for region in regions:
                    mask[
                        (self._binnedX >= region[0]) * (self._binnedX <= region[1])
                    ] = 1
            ddict["regions"] = regions
            # try to simplify life to the caller but can be hard if
            # spectral_binning has been applied because of the ambiguity
            # about if the spectral_mask is to be applied before or after
            # binning. The use of the 'regions' should be less prone to errors
            ddict["spectral_mask"] = mask
        else:
            ddict["regions"] = []
            ddict["spectral_mask"] = mask
        return ddict


class RegionsWidget(qt.QGroupBox):
    sigRegionsWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, nregions=10, limits=[0.0, 1000.0]):
        qt.QGroupBox.__init__(self, parent)
        self.setTitle("Spectral Regions")
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        if nregions % 2:
            nregions += 1
        self.nRegions = nregions
        self.regionList = []
        self.__limits = [limits[0], limits[1]]
        # Nice hint -> What about:
        # self.regionList.extend([[limits[0], limits[1]] * self.nRegions)
        # instead of this loop with the useless i?
        for i in range(self.nRegions):
            self.regionList.append([limits[0], limits[1]])
        self.nRegionsLabel = qt.QLabel(self)
        self.nRegionsLabel.setText("Number of Regions:")
        self.nRegionsSpinBox = qt.QSpinBox(self)
        self.nRegionsSpinBox.setMinimum(0)
        self.nRegionsSpinBox.setValue(0)
        self.nRegionsSpinBox.setMaximum(self.nRegions)
        self.mainLayout.addWidget(self.nRegionsLabel, 0, 0)
        self.mainLayout.addWidget(self.nRegionsSpinBox, 0, 1)
        self.nRegionsSpinBox.valueChanged[int].connect(self._regionsChanged)

        self.currentRegionLabel = qt.QLabel(self)
        self.currentRegionLabel.setText("Current Region:")
        self.currentRegionSpinBox = qt.QSpinBox(self)
        self.currentRegionSpinBox.setMinimum(1)
        self.currentRegionSpinBox.setValue(1)
        self.currentRegionSpinBox.setMaximum(1)
        self.mainLayout.addWidget(self.currentRegionLabel, 0, 2)
        self.mainLayout.addWidget(self.currentRegionSpinBox, 0, 3)
        self.currentRegionSpinBox.valueChanged[int].connect(self._currentRegionChanged)

        label = qt.QLabel(self)
        label.setText("From:")
        self.fromLine = qt.QLineEdit(self)
        self.fromLine.setText("%f" % limits[0])
        self.fromLine._v = qt.CLocaleQDoubleValidator(self.fromLine)
        self.fromLine.setValidator(self.fromLine._v)
        self.mainLayout.addWidget(label, 0, 4)
        self.mainLayout.addWidget(self.fromLine, 0, 5)
        self.fromLine.editingFinished[()].connect(self._editingSlot)

        label = qt.QLabel(self)
        label.setText("To:")
        self.toLine = qt.QLineEdit(self)
        self.toLine.setText("%f" % limits[1])
        self.toLine._v = qt.CLocaleQDoubleValidator(self.toLine)
        self.toLine.setValidator(self.toLine._v)
        self.mainLayout.addWidget(label, 0, 6)
        self.mainLayout.addWidget(self.toLine, 0, 7)
        self.toLine.editingFinished[()].connect(self._editingSlot)
        self._regionsChanged(0)

    def setLimits(self, xmin, xmax):
        for i in range(len(self.regionList)):
            self.regionList[i][0] = max(self.regionList[i][0], xmin)
            self.regionList[i][1] = min(self.regionList[i][1], xmax)
        self.__limits = [xmin, xmax]
        current = self.currentRegionSpinBox.value()
        self._currentRegionChanged(current)

    def _regionsChanged(self, value):
        if value == 0:
            self.toLine.setDisabled(True)
            self.fromLine.setDisabled(True)
            self.currentRegionSpinBox.setDisabled(True)
        else:
            current = self.currentRegionSpinBox.value()
            self.currentRegionSpinBox.setMaximum(value)
            self.toLine.setDisabled(False)
            self.fromLine.setDisabled(False)
            self.currentRegionSpinBox.setDisabled(False)
            if current > value:
                self.currentRegionSpinBox.setValue(value)
        self._currentRegionChanged(value)

    def _currentRegionChanged(self, value):
        if value > 0:
            fromValue, toValue = self.regionList[value - 1]
            self.fromLine.setText("%f" % fromValue)
            self.toLine.setText("%f" % toValue)
        self.mySignal()

    def _editingSlot(self, signal=True):
        current = self.currentRegionSpinBox.value() - 1
        self.regionList[current][0] = float(str(self.fromLine.text()))
        self.regionList[current][1] = float(str(self.toLine.text()))
        if self.regionList[current][0] < self.__limits[0]:
            self.regionList[current][0] = self.__limits[0]
        if self.regionList[current][1] > self.__limits[1]:
            self.regionList[current][1] = self.__limits[1]
        if signal:
            self.mySignal()

    def mySignal(self):
        current = self.currentRegionSpinBox.value() - 1
        ddict = {}
        ddict["event"] = "regionChanged"
        ddict["nRegions"] = self.nRegionsSpinBox.value()
        ddict["current"] = current
        if current >= 0:
            ddict["from"] = self.regionList[current][0]
            ddict["to"] = self.regionList[current][1]
        self.sigRegionsWidgetSignal.emit(ddict)

    def getRegions(self):
        nRegions = self.nRegionsSpinBox.value()
        regions = []
        if nRegions > 0:
            for i in range(nRegions):
                regions.append(self.regionList[i])
        return regions

    def setRegions(self, regionList=None):
        """
        :param regionList: List of couple of "from" and to "values"
        :type param: List
        """
        if regionList is None:
            regionList = []
        nRegions = len(regionList)
        # the number of regions is small so, we can afford to loop
        # instead of a direct copy
        self.regionList = []
        for i in range(nRegions):
            fromValue, toValue = regionList[i]
            self.regionList.append([fromValue, toValue])
        self.currentRegionSpinBox.setValue(nRegions)
        if nRegions > 0:
            self._editingSlot(signal=False)
        self._regionsChanged(self, nRegions)


class PCAWindow(MaskImageWidget.MaskImageWidget):
    def __init__(self, *var, **kw):
        ddict = {}
        ddict["usetab"] = True
        ddict.update(kw)
        ddict["standalonesave"] = False
        MaskImageWidget.MaskImageWidget.__init__(self, *var, **ddict)
        self.slider = qt.QSlider(self)
        self.slider.setOrientation(qt.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)

        # The 1D graph
        self.vectorGraph = ScanWindow.ScanWindow(self)
        self.mainTab.addTab(self.vectorGraph, "VECTORS")

        self.mainLayout.addWidget(self.slider)
        self.slider.valueChanged[int].connect(self._showImage)

        self.imageList = None
        self.imageNames = None
        self.eigenValues = None
        self.eigenVectors = None
        self.vectorNames = None
        self.vectorGraphTitles = None
        standalonesave = kw.get("standalonesave", True)
        if standalonesave:
            self.graphWidget.saveToolButton.clicked.connect(self._saveToolButtonSignal)
            self._saveMenu = qt.QMenu()
            self._saveMenu.addAction(QString("Image Data"), self.saveImageList)
            self._saveMenu.addAction(
                QString("Standard Graphics"), self.graphWidget._saveIconSignal
            )
            if MATPLOTLIB:
                self._saveMenu.addAction(
                    QString("Matplotlib"), self._saveMatplotlibImage
                )
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
        if hasattr(self, "_additionalSelectionMenu"):
            self.additionalSelectionMenu().addAction(
                QString("Show scatter plot"), self.showScatterPlot
            )

    def sizeHint(self):
        return qt.QSize(400, 400)

    def _multiplyIconChecked(self):
        if self.imageList is None:
            return
        index = self.slider.value()
        self.imageList[index] *= -1
        if self.eigenVectors is not None:
            self.eigenVectors[index] *= -1

        self._showImage(index)
        self.__scatterPlotWidgetDataToUpdate = True
        self._updateScatterPlotWidget()

    def _showImage(self, index):
        if self.eigenVectors is not None:
            legend = self.vectorNames[index]
            y = self.eigenVectors[index]
            if self.vectorGraphTitles is not None:
                self.vectorGraph.setGraphTitle(self.vectorGraphTitles[index])
            self.vectorGraph.addCurve(range(len(y)), y, legend, replace=True)
        if len(self.imageList):
            self.showImage(index, moveslider=False)

    def showImage(self, index=0, moveslider=True):
        if self.imageList is None:
            return
        if len(self.imageList) == 0:
            return
        self.graphWidget.graph.setGraphTitle(self.imageNames[index])
        self.setImageData(self.imageList[index])
        if moveslider:
            self.slider.setValue(index)

    def setPCAData(
        self,
        images,
        eigenvalues=None,
        eigenvectors=None,
        imagenames=None,
        vectornames=None,
    ):
        self.eigenValues = eigenvalues
        self.eigenVectors = eigenvectors
        if type(images) == type([]):
            self.imageList = images
        elif len(images.shape) == 3:
            nimages = images.shape[0]
            self.imageList = [0] * nimages
            for i in range(nimages):
                self.imageList[i] = images[i, :]
                if self.imageList[i].max() < 0:
                    self.imageList[i] *= -1
                    if self.eigenVectors is not None:
                        self.eigenVectors[i] *= -1
            if imagenames is None:
                self.imageNames = []
                for i in range(nimages):
                    self.imageNames.append("Eigenimage %02d" % i)
            else:
                self.imageNames = imagenames

        if self.imageList is not None:
            self.slider.setMaximum(len(self.imageList) - 1)
            self.showImage(0)
        else:
            self.slider.setMaximum(0)

        if self.eigenVectors is not None:
            if vectornames is None:
                self.vectorNames = []
                for i in range(nimages):
                    self.vectorNames.append("Component %02d" % i)
            else:
                self.vectorNames = vectornames
            legend = self.vectorNames[0]
            y = self.eigenVectors[0]
            self.vectorGraph.newCurve(range(len(y)), y, legend, replace=True)

        self.slider.setValue(0)
        self.__scatterPlotWidgetDataToUpdate = True
        self._updateScatterPlotWidget()

    def _updateScatterPlotWidget(self):
        w = self.scatterPlotWidget
        if self.__scatterPlotWidgetDataToUpdate:
            if self.imageNames:
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
        elif ddict["id"] == id(self.scatterPlotWidget):
            # signal generated by the scatter plot
            if ddict["event"] in [
                "selectionMaskChanged",
                "resetSelection",
                "invertSelection",
            ]:
                mask = self.scatterPlotWidget.getSelectionMask()
                super(PCAWindow, self).setSelectionMask(mask, plot=True)
                ddict["id"] = id(self)
                try:
                    self.__maskToScatterConnected = False
                    self.sigMaskImageWidgetSignal.emit(ddict)
                finally:
                    self.__maskToScatterConnected = True

    def setSelectionMask(self, *var, **kw):
        super(PCAWindow, self).setSelectionMask(*var, **kw)
        if not self.scatterPlotWidget.isHidden():
            self._updateScatterPlotWidget()

    def saveImageList(self, filename=None, imagelist=None, labels=None):
        if self.imageList is None:
            return
        labels = []
        for i in range(len(self.imageList)):
            labels.append(self.imageNames[i].replace(" ", "_"))
        return MaskImageWidget.MaskImageWidget.saveImageList(
            self, imagelist=self.imageList, labels=labels
        )

    def setImageList(self, imagelist):
        self.imageList = imagelist
        self.eigenValues = None
        self.eigenVectors = None
        if imagelist is not None:
            self.slider.setMaximum(len(self.imageList) - 1)
            self.showImage(0)

    def showScatterPlot(self):
        if self.scatterPlotWidget.isHidden():
            # it needs update
            self._updateScatterPlotWidget()
        self.scatterPlotWidget.show()
        # make sure it is visible
        self.scatterPlotWidget.raise_()


def test2():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    dialog = PCAParametersDialog()
    dialog.setParameters(
        {"options": [1, 3, 5, 7, 9], "method": 1, "npc": 8, "binning": 3}
    )
    dialog.setModal(True)
    ret = dialog.exec()
    if ret:
        dialog.close()
        print(dialog.getParameters())


def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    container = PCAWindow()
    data = numpy.arange(20000)
    data = data.reshape(2, 100, 100)
    data[1, 0:100, 0:50] = 100
    container.setPCAData(
        data,
        eigenvectors=[numpy.arange(100.0), numpy.arange(100.0) + 10],
        imagenames=["I1", "I2"],
        vectornames=["V1", "V2"],
    )
    container.show()

    def theSlot(ddict):
        print(ddict["event"])

    container.sigMaskImageWidgetSignal.connect(theSlot)
    app.exec()


if __name__ == "__main__":
    test()
