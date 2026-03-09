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
from PyMca5.PyMcaGui.math import PCAWindow
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaMath.mva import NNMAModule
import logging

_logger = logging.getLogger(__name__)


class NNMAParametersDialog(qt.QDialog):
    def __init__(self, parent=None, options=[1, 2, 3, 4, 5, 10], regions=False):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("NNMA Configuration Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(11, 11, 11, 11)
        self.mainLayout.setSpacing(0)

        self.infoButton = qt.QPushButton(self)
        self.infoButton.setAutoDefault(False)
        self.infoButton.setText("About NNMA")
        self.mainLayout.addWidget(self.infoButton)
        self.infoButton.clicked.connect(self._showInfo)

        #
        self.methodOptions = qt.QGroupBox(self)
        self.methodOptions.setTitle("NNMA Method to use")
        self.methods = [
            "RRI",
            "NNSC",
            "NMF",
            "SNMF",
            "NMFKL",
            "FNMAI",
            "ALS",
            "FastHALS",
            "GDCLS",
        ]
        self.methodOptions.mainLayout = qt.QGridLayout(self.methodOptions)
        self.methodOptions.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.methodOptions.mainLayout.setSpacing(2)
        self.buttonGroup = qt.QButtonGroup(self.methodOptions)
        i = 0
        for item in self.methods:
            rButton = qt.QRadioButton(self.methodOptions)
            self.methodOptions.mainLayout.addWidget(rButton, 0, i)
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
            _logger.debug("Using deprecated signal")
            self.buttonGroup.buttonClicked[int].connect(self._slot)

        self.mainLayout.addWidget(self.methodOptions)

        # NNMA configuration parameters
        self.nnmaConfiguration = qt.QGroupBox(self)
        self.nnmaConfiguration.setTitle("NNMA Configuration")
        self.nnmaConfiguration.mainLayout = qt.QGridLayout(self.nnmaConfiguration)
        self.nnmaConfiguration.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.nnmaConfiguration.mainLayout.setSpacing(2)
        label = qt.QLabel(self.nnmaConfiguration)
        label.setText("Tolerance (0<eps<1000:")
        self._tolerance = qt.QLineEdit(self.nnmaConfiguration)
        validator = qt.CLocaleQDoubleValidator(self._tolerance)
        self._tolerance.setValidator(validator)
        self._tolerance._validator = validator
        self._tolerance.setText("0.001")
        self.nnmaConfiguration.mainLayout.addWidget(label, 0, 0)
        self.nnmaConfiguration.mainLayout.addWidget(self._tolerance, 0, 1)
        label = qt.QLabel(self.nnmaConfiguration)
        label.setText("Maximum iterations:")
        self._maxIterations = qt.QSpinBox(self.nnmaConfiguration)
        self._maxIterations.setMinimum(1)
        self._maxIterations.setMaximum(1000)
        self._maxIterations.setValue(100)
        self.nnmaConfiguration.mainLayout.addWidget(label, 1, 0)
        self.nnmaConfiguration.mainLayout.addWidget(self._maxIterations, 1, 1)
        self.mainLayout.addWidget(self.nnmaConfiguration)

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
        self.binningCombo.setEnabled(True)
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
        self.okButton.setAutoDefault(False)
        self.okButton.setText("Accept")
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.okButton)
        self.dismissButton = qt.QPushButton(hbox)
        self.dismissButton.setAutoDefault(False)
        self.dismissButton.setText("Dismiss")
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.dismissButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        self.mainLayout.addWidget(self.speedOptions)
        if regions:
            self.mainLayout.addWidget(self.regionsWidget)
        self.mainLayout.addWidget(hbox)
        if self.graph is not None:
            self.mainLayout.addWidget(self.graph)

        self.okButton.clicked.connect(self.accept)
        self.dismissButton.clicked.connect(self.reject)

        self._infoDocument = qt.QTextEdit()
        self._infoDocument.setReadOnly(True)
        self._infoDocument.setText(NNMAModule.__doc__)
        self._infoDocument.hide()
        self.mainLayout.addWidget(self._infoDocument)

    def _showInfo(self):
        self._infoDocument.show()

    def __addRegionsWidget(self):
        # Region handling
        self.regionsWidget = PCAWindow.RegionsWidget(self)
        self.regionsWidget.setEnabled(True)
        self.regionsWidget.sigRegionsWidgetSignal.connect(self.regionsWidgetSlot)
        # the plot
        self.graph = PCAWindow.ScanWindow.ScanWindow(self)
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
        if 1 or index != 2:
            self.binningCombo.setEnabled(True)
        else:
            self.binningCombo.setEnabled(False)
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
        if self.graph:
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
        if "regions" in ddict:
            self.regionsWidget.setRegions(ddict["regions"])
        return

    def getParameters(self):
        ddict = {}
        i = self.buttonGroup.checkedId()
        ddict["methodlabel"] = self.methods[i]
        ddict["function"] = NNMAModule.nnma
        eps = float(self._tolerance.text())
        maxcount = self._maxIterations.value()
        ddict["binning"] = int(self.binningCombo.currentText())
        ddict["npc"] = self.nPC.value()
        ddict["kw"] = {"eps": eps, "maxcount": maxcount}
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


class NNMAWindow(PCAWindow.PCAWindow):
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
                    self.imageNames.append("NNMA Image %02d" % i)
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
                    self.vectorNames.append("NNMA Component %02d" % i)
            else:
                self.vectorNames = vectornames
            legend = self.vectorNames[0]
            y = self.eigenVectors[0]
            self.vectorGraph.newCurve(range(len(y)), y, legend, replace=True)
            if self.eigenValues is not None:
                self.vectorGraphTitles = []
                for i in range(nimages):
                    self.vectorGraphTitles.append(
                        "%g %% explained intensity" % self.eigenValues[i]
                    )
                self.vectorGraph.setGraphTitle(self.vectorGraphTitles[0])

        self.slider.setValue(0)


def test2():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    dialog = NNMAParametersDialog(regions=True)
    # dialog.setParameters({'options':[1,3,5,7,9],'method':1, 'npc':8,'binning':3})
    dialog.setModal(True)
    ret = dialog.exec()
    if ret:
        dialog.close()
        print(dialog.getParameters())
    # app.exec()


def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    container = NNMAWindow()
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
    import numpy

    test2()
