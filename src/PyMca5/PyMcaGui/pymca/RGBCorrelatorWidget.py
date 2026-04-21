# /*##########################################################################
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import os
import numpy
import traceback
import logging
import warnings
import re
from typing import Optional

from PyMca5.PyMcaGui.pymca import RGBImageCalculator
from PyMca5 import spslut
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaIO import ArraySave
from PyMca5 import PyMcaDirs
from PyMca5.PyMcaCore import EdfFileDataSource
from PyMca5.PyMcaGui.pymca import StackPluginResultsWindow
from PyMca5.PyMcaGui.pymca import ExternalImagesWindow
from PyMca5.PyMcaIO import TiffIO
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.plotting import ScatterPlotCorrelatorWidget
from PyMca5.PyMcaGui.plotting import RGBCorrelatorGraph
from PyMca5.PyMcaMisc import CliUtils

from . import RGBCorrelatorSlider
from . import RGBCorrelatorTable

DataReader = EdfFileDataSource.EdfFileDataSource
USE_STRING = False

from PyMca5.PyMcaGui import PyMcaQt as qt

if hasattr(qt, "QString"):
    QString = qt.QString
    QStringList = qt.QStringList
else:
    QString = str
    QStringList = list

QTVERSION = qt.qVersion()
try:
    from PyMca5.PyMcaGui.math import NNMADialog

    NNMA = NNMADialog.NNMA
    from PyMca5.PyMcaGui.math import PCADialog

    PCA = PCADialog.PCA
except Exception:
    NNMA = False
    PCA = False

KMEANS = RGBImageCalculator.KMEANS

try:
    import tomogui.gui.utils.icons
    from tomogui.gui.ProjectWidget import ProjectWindow as TomoguiProjWindow
    from PyMca5.PyMcaGui.pymca.TomographyRecons import TomoReconsDialog

    TOMOGUI_FLAG = True
except Exception:
    TOMOGUI_FLAG = False

# Use QDataSource for complete test but requires too many imports
# TODO: then why have all format tests in the same module?
# def isHdf5(filename):
#    import QDataSource
#    sourceType = QDataSource.getSourceType(filename).upper()
#    return sourceType.startswith("HDF5")
try:
    import h5py
except ImportError:
    h5py = None

    def isHdf5(filename):
        return os.path.splitext(filename)[-1].lower() in (
            ".h5",
            ".nxs",
            ".hdf",
            ".hdf5",
        )

else:

    def isHdf5(filename):
        return h5py.is_hdf5(filename)

    from PyMca5.PyMcaGui.io.hdf5 import HDF5Widget
    from PyMca5.PyMcaIO import NexusUtils


def isEdf(filename):
    # Complete Test but requires too many imports
    # TODO: then why have have all format tests in the same module?
    # import QDataSource
    # sourceType = QDataSource.getSourceType(filename).upper()
    # return sourceType.startswith("EDFFILE")
    with open(filename, "rb") as f:
        twoBytes = f.read(2)
    if sys.version < "3.0":
        twoChar = twoBytes
    else:
        try:
            twoChar = twoBytes.decode("utf-8")
        except Exception:
            twoChar = "__dummy__"
    filename = filename.lower()
    return (
        twoChar in ["II", "MM", "\n{"]
        or twoChar[0] in ["{"]
        or filename.endswith("cbf")
        or (filename.endswith("spe") and twoChar[0] not in ["$"])
    )


def isTif(filename):
    return os.path.splitext(filename)[-1].lower() in (".tif", ".tiff")


def isQImageReadable(filename):
    return os.path.splitext(filename)[-1].lower() in (
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
    )


def makeQimageBW(qimage):
    height = qimage.height()
    width = qimage.width()
    if qimage.format() == qt.QImage.Format_Indexed8:
        pixmap0 = numpy.frombuffer(
            qimage.bits().asstring(width * height), dtype=numpy.uint8
        )
        pixmap = numpy.zeros((height * width, 4), numpy.uint8)
        pixmap[:, 0] = pixmap0[:]
        pixmap[:, 1] = pixmap0[:]
        pixmap[:, 2] = pixmap0[:]
        pixmap[:, 3] = 255
        pixmap = pixmap.reshape(height, width, 4)
    else:
        image = qimage.convertToFormat(qt.QImage.Format_ARGB32)
        pixmap0 = numpy.frombuffer(
            image.bits().asstring(width * height * 4), dtype=numpy.uint8
        )
        pixmap = numpy.array(pixmap0, copy=True)
    pixmap = pixmap.reshape(height, width, -1)
    return pixmap[:, :, 0] * 0.114 + pixmap[:, :, 1] * 0.587 + pixmap[:, :, 2] * 0.299


_logger = logging.getLogger(__name__)


class RGBCorrelatorWidget(qt.QWidget):
    sigRGBCorrelatorWidgetSignal = qt.pyqtSignal(object)
    sigMaskImageWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, bgrx=False, replace=False, image_shape=None):
        qt.QWidget.__init__(self, parent)
        self.replaceOption = replace
        self.setWindowTitle("RGBCorrelatorWidget")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(4)
        self.labelWidget = qt.QWidget(self)
        self.labelWidget.mainLayout = qt.QGridLayout(self.labelWidget)
        self.labelWidget.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.labelWidget.mainLayout.setSpacing(0)
        alignment = qt.Qt.AlignVCenter | qt.Qt.AlignCenter
        self.toolBar = qt.QWidget(self)
        # hbox = qt.QWidget(self.labelWidget)
        hbox = self.toolBar
        hbox.mainLayout = qt.QHBoxLayout(hbox)
        hbox.mainLayout.setContentsMargins(0, 0, 0, 0)
        hbox.mainLayout.setSpacing(0)

        self.loadButton = qt.QToolButton(hbox)
        self.loadButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["fileopen"])))
        self.loadButton.setToolTip("Load new images of the same size")
        self.saveButton = qt.QToolButton(hbox)
        self.saveButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["filesave"])))
        self.saveButton.setToolTip("Save image data to file")
        self._saveFilter = None
        self.removeButton = qt.QToolButton(hbox)
        self.removeButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["remove"])))
        self.removeButton.setToolTip("Remove the selected images")
        self.toggleSlidersButton = qt.QToolButton(hbox)
        self._slidersOffIcon = qt.QIcon(qt.QPixmap(IconDict["slidersoff"]))
        self._slidersOnIcon = qt.QIcon(qt.QPixmap(IconDict["sliderson"]))
        self.toggleSlidersButton.setIcon(self._slidersOffIcon)
        self.toggleSlidersButton.setToolTip("Toggle sliders show On/Off")
        self.statisticsDialog = None
        self.calculationDialog = None
        self.calculationButton = qt.QToolButton(hbox)
        self.calculationButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["sigma"])))
        self.calculationButton.setToolTip("Operate with the images")
        self.profileImageListWidget = None
        self.profileButton = qt.QToolButton(hbox)
        self.profileButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["diagonal"])))
        self.profileButton.setToolTip("Show selected images profile")
        self.currentNanColor = 'black'
        self.nanColorButton = qt.QToolButton(hbox)
        self.nanColorButton.setAutoFillBackground(True)
        self.nanColorButton.setText('nan')
        self.nanColorButton.setToolTip("Toggle black/white color for 'nan' pixels")
        self.toggleNanColor(initial=True)
        self.nanColorButton.setFixedHeight(self.loadButton.sizeHint().height())

        if TOMOGUI_FLAG:
            self.tomographyButton = qt.QToolButton(hbox)
            tomoguiIcon = tomogui.gui.utils.icons.getQIcon("tomogui")
            self.tomographyButton.setIcon(tomoguiIcon)
            self.tomographyButton.setToolTip("Run tomography reconstruction")
            self.tomographyButton.clicked.connect(self._showTomoReconsDialog)

        label1 = MyQLabel(self.labelWidget, color=qt.QApplication.instance().palette().color(qt.QPalette.Text))
        label1.setAlignment(alignment)
        label1.setText("Image Size")
        # Should be red even in Dark mode
        self.__sizeLabel = MyQLabel(self.labelWidget, bold=True, color=qt.Qt.red)
        self.__sizeLabel.setAlignment(alignment)
        self.__sizeLabel.setText("No image set")

        # self.__rowLineEdit = qt.QLineEdit(self.labelWidget)
        # self.__columnLineEdit = qt.QLineEdit(self.labelWidget)
        self.__imageResizeButton = qt.QPushButton(self.labelWidget)
        self.__imageResizeButton.setText("Reshape")

        hbox.mainLayout.addWidget(self.loadButton)
        hbox.mainLayout.addWidget(self.saveButton)
        hbox.mainLayout.addWidget(self.removeButton)
        hbox.mainLayout.addWidget(self.toggleSlidersButton)
        hbox.mainLayout.addWidget(self.calculationButton)
        hbox.mainLayout.addWidget(self.profileButton)
        hbox.mainLayout.addWidget(self.nanColorButton)
        if TOMOGUI_FLAG:
            hbox.mainLayout.addWidget(self.tomographyButton)
        hbox.mainLayout.addWidget(qt.HorizontalSpacer(self.toolBar))

        # hbox.mainLayout.addWidget(label1)
        self.labelWidget.mainLayout.addWidget(label1, 0, 0)
        self.labelWidget.mainLayout.addWidget(self.__sizeLabel, 0, 1)

        # self.labelWidget.mainLayout.addWidget(self.__rowLineEdit, 1, 0)
        # self.labelWidget.mainLayout.addWidget(self.__columnLineEdit, 1, 1)
        self.labelWidget.mainLayout.addWidget(self.__imageResizeButton, 0, 2)

        self.colormapType = 0
        self.buttonGroup = qt.QButtonGroup()
        g1 = qt.QPushButton(self.labelWidget)
        g1.setText("Linear")
        g2 = qt.QPushButton(self.labelWidget)
        g2.setText("Logarithmic")
        g3 = qt.QPushButton(self.labelWidget)
        g3.setText("Gamma")
        g1.setCheckable(True)
        g2.setCheckable(True)
        g3.setCheckable(True)
        self.buttonGroup.addButton(g1, 0)
        self.buttonGroup.addButton(g2, 1)
        self.buttonGroup.addButton(g3, 2)
        self.buttonGroup.setExclusive(True)
        self.buttonGroup.button(self.colormapType).setChecked(True)
        self.labelWidget.mainLayout.addWidget(g1, 1, 0)
        self.labelWidget.mainLayout.addWidget(g2, 1, 1)
        self.labelWidget.mainLayout.addWidget(g3, 1, 2)

        self.buttonGroup.setExclusive(True)

        self.sliderWidget = RGBCorrelatorSlider.RGBCorrelatorSlider(
            self, autoscalelimits=[5.0, 80.0]
        )
        self.tableWidget = RGBCorrelatorTable.RGBCorrelatorTable(self)

        self.mainLayout.addWidget(self.toolBar)
        self.mainLayout.addWidget(self.labelWidget)
        self.mainLayout.addWidget(self.sliderWidget)
        self.mainLayout.addWidget(self.tableWidget)

        if bgrx:
            self.bgrx = "BGRX"
        else:
            self.bgrx = "RGBX"
        self._imageList = []
        self._imageDict = {}
        if image_shape:
            self.__imageLength = numpy.prod(image_shape, dtype=int)
            self.__imageShape = tuple(image_shape)
        else:
            self.__imageLength = None
            self.__imageShape = None
        self.__imageLengthOriginal = self.__imageLength
        self.__imageShapeOriginal = self.__imageShape
        self.__prePadLength = None
        self.__redLabel = None
        self.__greenLabel = None
        self.__blueLabel = None
        self.__redImageData = None
        self.__greenImageData = None
        self.__blueImageData = None
        self.__redMin = 0.0
        self.__redMax = 100.0
        self.__greenMin = 0.0
        self.__greenMax = 100.0
        self.__blueMin = 0.0
        self.__blueMax = 0.0
        self.__redImage = None
        self.__greenImage = None
        self.__blueImage = None
        self.outputDir = None

        self.loadButton.clicked.connect(self._addFileList)
        self.saveButton.clicked.connect(self.saveButtonClicked)
        self._saveButtonMenu = qt.QMenu()
        self._saveButtonMenu.addAction(QString("Save all"), self.saveImageList)
        self._saveButtonMenu.addAction(
            QString("Save selected"), self.saveSelectedImages
        )

        self.removeButton.clicked.connect(self.removeButtonClicked)

        self.toggleSlidersButton.clicked.connect(self.toggleSliders)

        self.calculationButton.clicked.connect(self._showCalculationDialog)

        self.profileButton.clicked.connect(self.profileSelectedImages)

        self.nanColorButton.clicked.connect(self.toggleNanColor)

        self._calculationMenu = None
        self.scatterPlotWidget = None
        self.pcaDialog = None
        self.nnmaDialog = None
        self.kMeansDialog = None
        self._tomoguiWindow = None
        self._lastMask = None

        self.__imageResizeButton.clicked.connect(self._imageResizeSlot)
        self.sliderWidget.sigRGBCorrelatorSliderSignal.connect(self._sliderSlot)

        self.tableWidget.sigRGBCorrelatorTableSignal.connect(self._tableSlot)

        if hasattr(self.buttonGroup, "idClicked"):
            self.buttonGroup.idClicked[int].connect(self._colormapTypeChange)
        else:
            # deprecated
            _logger.debug("Using deprecated signal")
            self.buttonGroup.buttonClicked[int].connect(self._colormapTypeChange)

    def toggleNanColor(self, initial=False):
        self.currentNanColor = 'white' if self.currentNanColor == 'black' else 'black'

        bg = qt.QColor(self.currentNanColor)
        text = qt.QColor(qt.Qt.red) if self.currentNanColor == 'black' else qt.QColor(qt.Qt.black)

        palette = qt.QPalette(self.nanColorButton.palette())
        palette.setColor(qt.QPalette.Button, bg)
        palette.setColor(qt.QPalette.ButtonText, text)
        palette.setColor(qt.QPalette.Window, bg)
        palette.setColor(qt.QPalette.Text, text)
        self.nanColorButton.setPalette(palette)
        if not initial:
            if self.__imageLength is not None:
                self.update()

    def _showCalculationDialog(self):
        if (not NNMA) and (not PCA) and (not KMEANS):
            return self.showCalculationDialog()
        if self._calculationMenu is None:
            self._calculationMenu = qt.QMenu()
            self._calculationMenu.addAction(
                QString("Image Statistics"), self.showStatisticsDialog
            )
            self._calculationMenu.addAction(
                QString("Image Calculator"), self.showCalculationDialog
            )
            self._calculationMenu.addAction(
                QString("Scatter Plot"), self.showScatterPlotDialog
            )
            if PCA:
                if PCADialog.MDP:
                    self._calculationMenu.addAction(
                        QString("PCA/ICA Analysis"), self.showPCADialog
                    )
                else:
                    self._calculationMenu.addAction(
                        QString("PCA Analysis"), self.showPCADialog
                    )
            if NNMA:
                self._calculationMenu.addAction(
                    QString("NNMA Analysis"), self.showNNMADialog
                )
            if KMEANS:
                self._calculationMenu.addAction(
                    QString("K-Means Clustering"), self.showKMeansDialog
                )
        self._calculationMenu.exec(self.cursor().pos())

    def _showTomoReconsDialog(self):
        def getSinograms(ids):
            datas = []
            for id in ids:
                assert "image" in self._imageDict[id]
                datas.append(self._imageDict[id]["image"])
            return datas

        assert TOMOGUI_FLAG is True
        diag = TomoReconsDialog(entries=self._imageList)
        if diag.exec():
            if self._tomoguiWindow is None:
                self._tomoguiWindow = TomoguiProjWindow()

            self._tomoguiWindow.clean()
            reconsType = diag.getReconstructionType()
            sinoIDs = diag.getSinogramsToRecons()
            self._tomoguiWindow.setSinoToRecons(
                reconsType=reconsType, sinograms=getSinograms(sinoIDs), names=sinoIDs
            )
            if diag.hasIt() is True:
                it = self._imageDict[diag.getIt()]["image"]
                self._tomoguiWindow.setIt(it=it, name=diag.getIt())
            if diag.hasI0() is True:
                i0 = self._imageDict[diag.getI0()]["image"]
                self._tomoguiWindow.setI0(i0=i0, name=diag.getI0())
            # by default do not reconstruct log
            self._tomoguiWindow.setLogRecons(False)
            self._tomoguiWindow.show()

    def toggleSliders(self):
        if self.sliderWidget.isHidden():
            self.sliderWidget.show()
            self.toggleSlidersButton.setIcon(self._slidersOffIcon)
        else:
            self.sliderWidget.hide()
            self.toggleSlidersButton.setIcon(self._slidersOnIcon)

    def _sliderSlot(self, ddict):
        _logger.debug("RGBCorrelatorWidget._sliderSlot()")
        if self.__imageLength is None:
            return
        tableDict = self.tableWidget.getElementSelection()
        if ddict["event"] == "redChanged":
            self.__redMin = ddict["min"]
            self.__redMax = ddict["max"]
            if len(tableDict["r"]):
                self.__recolor(["r"])
        elif ddict["event"] == "greenChanged":
            self.__greenMin = ddict["min"]
            self.__greenMax = ddict["max"]
            if len(tableDict["g"]):
                self.__recolor(["g"])
        elif ddict["event"] == "blueChanged":
            self.__blueMin = ddict["min"]
            self.__blueMax = ddict["max"]
            if len(tableDict["b"]):
                self.__recolor(["b"])
        elif ddict["event"] == "allChanged":
            self.__redMin = ddict["red"][0]
            self.__redMax = ddict["red"][1]
            self.__greenMin = ddict["green"][0]
            self.__greenMax = ddict["green"][1]
            self.__blueMin = ddict["blue"][0]
            self.__blueMax = ddict["blue"][1]
            if not len(tableDict["r"]):
                if not len(tableDict["g"]):
                    if not len(tableDict["b"]):
                        return
            self.__recolor(["r", "g", "b"])

    def _tableSlot(self, ddict):
        _logger.debug("RGBCorrelatorWidget._tableSlot()")
        if self.__imageLength is None:
            return
        if ddict["r"] == []:
            ddict["r"] = None
        if ddict["g"] == []:
            ddict["g"] = None
        if ddict["b"] == []:
            ddict["b"] = None

        if ddict["r"] is None:
            self.__redImageData = numpy.zeros(self.__imageShape).astype(numpy.float64)
            self.__redLabel = None
        else:
            self.__redLabel = ddict["elementlist"][ddict["r"][0]]
            self.__redImageData = self._imageDict[self.__redLabel]["image"]

        if ddict["g"] is None:
            self.__greenImageData = numpy.zeros(self.__imageShape).astype(numpy.float64)
            self.__greenLabel = None
        else:
            self.__greenLabel = ddict["elementlist"][ddict["g"][0]]
            self.__greenImageData = self._imageDict[self.__greenLabel]["image"]

        if ddict["b"] is None:
            self.__blueImageData = numpy.zeros(self.__imageShape).astype(numpy.float64)
            self.__blueLabel = None
        else:
            self.__blueLabel = ddict["elementlist"][ddict["b"][0]]
            self.__blueImageData = self._imageDict[self.__blueLabel]["image"]
        self.__recolor(["r", "g", "b"])

    def __recolor(self, color=None):
        if color is None:
            colorlist = ["r", "g", "b"]
        elif type(color) == type(""):
            colorlist = [color]
        else:
            colorlist = color * 1
        ddict = {}
        ddict["event"] = "updated"

        # whitening the nan pixels
        if (
                (
            bool(numpy.isnan(self.__redImageData).any())
            or bool(numpy.isnan(self.__greenImageData).any())
            or bool(numpy.isnan(self.__blueImageData).any())
                )
            and self.currentNanColor == 'white'
        ):
            colorlist = ["r", "g", "b"]
            # if any element of R or G or B map is nan it will become white
            nan_indices = numpy.where(
                numpy.isnan(self.__redImageData) |
                numpy.isnan(self.__greenImageData) |
                numpy.isnan(self.__blueImageData)
            )
            redImageData = numpy.copy(self.__redImageData)
            greenImageData = numpy.copy(self.__greenImageData)
            blueImageData = numpy.copy(self.__blueImageData)
            redImageData[nan_indices[0], nan_indices[1]] = (
                max(numpy.nanmax(self.__redImageData), 1) + 255
            )
            greenImageData[nan_indices[0], nan_indices[1]] = (
                max(numpy.nanmax(self.__greenImageData), 1) + 255
            )
            blueImageData[nan_indices[0], nan_indices[1]] = (
                max(numpy.nanmax(self.__blueImageData), 1) + 255
            )
        else:
            redImageData = self.__redImageData
            greenImageData = self.__greenImageData
            blueImageData = self.__blueImageData

        if "r" in colorlist:
            # get slider
            label = self.__redLabel
            if label is None:
                valmin = 0.0
                valmax = 1.0
            else:
                valmin = self._imageDict[label]["min"]
                valmax = self._imageDict[label]["max"]
                delta = 0.01 * (valmax - valmin)
                valmin = valmin + delta * self.__redMin
                valmax = valmin + delta * self.__redMax
            if USE_STRING:
                red, size, minmax = self.getColorImage(
                    redImageData, spslut.RED, valmin, valmax, 0
                )
                self.__redImage = numpy.array(red).astype(numpy.uint8)
                ddict["red"] = red
            else:
                red, size, minmax = self.getColorImage(
                    redImageData, spslut.RED, valmin, valmax, 1
                )
                self.__redImage = red
                ddict["red"] = red.tobytes()
            ddict["size"] = size

        if "g" in colorlist:
            # get slider
            label = self.__greenLabel
            if label is None:
                valmin = 0.0
                valmax = 1.0
            else:
                valmin = self._imageDict[label]["min"]
                valmax = self._imageDict[label]["max"]
                delta = 0.01 * (valmax - valmin)
                valmin = valmin + delta * self.__greenMin
                valmax = valmin + delta * self.__greenMax
            if USE_STRING:
                green, size, minmax = self.getColorImage(
                    greenImageData, spslut.GREEN, valmin, valmax
                )
                self.__greenImage = numpy.array(green).astype(numpy.uint8)
                ddict["green"] = green
            else:
                green, size, minmax = self.getColorImage(
                    greenImageData, spslut.GREEN, valmin, valmax, 1
                )
                self.__greenImage = green
                ddict["green"] = green.tobytes()
            ddict["size"] = size

        if "b" in colorlist:
            # get slider
            label = self.__blueLabel
            if label is None:
                valmin = 0.0
                valmax = 1.0
            else:
                valmin = self._imageDict[label]["min"]
                valmax = self._imageDict[label]["max"]
                # if valmax == valmin:valmax = valmin + 1
                delta = 0.01 * (valmax - valmin)
                valmin = valmin + delta * self.__blueMin
                valmax = valmin + delta * self.__blueMax
            if USE_STRING:
                blue, size, minmax = self.getColorImage(
                    blueImageData, spslut.BLUE, valmin, valmax
                )
                self.__blueImage = numpy.array(blue).astype(numpy.uint8)
                ddict["blue"] = blue
            else:
                blue, size, minmax = self.getColorImage(
                    blueImageData, spslut.BLUE, valmin, valmax, 1
                )
                self.__blueImage = blue
                ddict["blue"] = blue.tobytes()
            ddict["size"] = size

        image = self.__redImage + self.__greenImage + self.__blueImage
        ddict["image"] = image
        self.sigRGBCorrelatorWidgetSignal.emit(ddict)

    def _colormapTypeChange(self, val):
        self.colormapType = val
        self.__recolor()

    def getColorImage(self, image, colormap, datamin=None, datamax=None, arrayflag=0):
        COLORMAPLIST = [
            spslut.GREYSCALE,
            spslut.REVERSEGREY,
            spslut.TEMP,
            spslut.RED,
            spslut.GREEN,
            spslut.BLUE,
            spslut.MANY,
        ]
        if colormap not in COLORMAPLIST:
            raise ValueError("Unknown color scheme %s" % colormap)

        if (datamin is None) or (datamax is None):
            # spslut already calculates min and max
            # tmp = numpy.ravel(image)
            (image_buffer, size, minmax) = spslut.transform(
                image,
                (1, 0),
                (self.colormapType, 3.0),
                self.bgrx,
                colormap,
                1,
                (0, 1),
                (0, 255),
                arrayflag,
            )
            # (min(tmp),max(tmp)))
        else:
            (image_buffer, size, minmax) = spslut.transform(
                image,
                (1, 0),
                (self.colormapType, 3.0),
                self.bgrx,
                colormap,
                0,
                (datamin, datamax),
                (0, 255),
                arrayflag,
            )

        return image_buffer, size, minmax

    def addImage(self, image0, label=None):
        image = numpy.array(image0).astype(numpy.float64)
        if label is None:
            label = "Unnamed 00"
            i = 0
            while label in self._imageList:
                i += 1
                label = "Unnamed %02d" % i
        if not len(image):
            return
        firstTime = False
        if self.__imageLength is None:
            if not len(image.shape):
                return
            self.__imageLength = 1
            for value in image.shape:
                self.__imageLength *= value
            if len(image.shape) == 1:
                image = numpy.resize(image, (image.shape[0], 1))
            self.__imageShape = image.shape
            self._updateSizeLabel()
            firstTime = True

        if image.shape != self.__imageShape:
            length = 1
            for value in image.shape:
                length *= value
            if length == self.__imageLength:
                image = numpy.resize(
                    image, (self.__imageShape[0], self.__imageShape[1])
                )
            elif self.__prePadLength is not None and length == self.__prePadLength:
                flat = image.ravel()
                padded = numpy.full(self.__imageLength, numpy.nan, dtype=numpy.float64)
                padded[:length] = flat
                image = padded.reshape(self.__imageShape)
            else:
                raise ValueError(
                    "Image cannot be reshaped to %d x %d"
                    % (self.__imageShape[0], self.__imageShape[1])
                )

        if label not in self._imageList:
            self._imageList.append(label)
        self._imageDict[label] = {}
        self._imageDict[label]["image"] = image
        tmp = numpy.ravel(image)
        self._imageDict[label]["min"] = numpy.nanmin(tmp)
        self._imageDict[label]["max"] = numpy.nanmax(tmp)

        self.tableWidget.build(self._imageList)
        i = 0
        for label in self._imageList:
            mintext = "%g" % self._imageDict[label]["min"]
            maxtext = "%g" % self._imageDict[label]["max"]
            item = self.tableWidget.item(i, 4)
            if item is None:
                item = qt.QTableWidgetItem(mintext, qt.QTableWidgetItem.Type)
                item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
                item.setFlags(qt.Qt.ItemIsEnabled)
                self.tableWidget.setItem(i, 4, item)
            else:
                item.setText(mintext)
            item = self.tableWidget.item(i, 5)
            if item is None:
                item = qt.QTableWidgetItem(maxtext, qt.QTableWidgetItem.Type)
                item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
                item.setFlags(qt.Qt.ItemIsEnabled)
                self.tableWidget.setItem(i, 5, item)
            else:
                item.setText(maxtext)
            i += 1
        if firstTime:
            self.tableWidget.setElementSelection({"r": [0]})
            # , 'g':[0],'b':[0]})
            self.sliderWidget.autoScaleFromAToB()
            # self.__recolor()
            # self.tableWidget._update()
        if self.calculationDialog is not None:
            self.calculationDialog.imageList = self._imageList
            self.calculationDialog.imageDict = self._imageDict

    def removeButtonClicked(self):
        itemList = self.tableWidget.selectedItems()
        labelList = []
        nImages = len(self._imageList)
        for item in itemList:
            row = item.row()
            if row < nImages:
                labelList.append(self._imageList[row])

        for label in labelList:
            self.removeImage(label)

        # if all images removed then it is possible to choose different size.
        if len(self._imageList) == 0:
            self.__imageShape = None
            self.__imageLength = None
            self._updateSizeLabel()

    def removeImage(self, label):
        if label not in self._imageList:
            return
        self._imageDict[label] = {}
        del self._imageDict[label]
        del self._imageList[self._imageList.index(label)]
        if self.__redLabel == label:
            self.__redLabel = None
        if self.__greenLabel == label:
            self.__greenLabel = None
        if self.__blueLabel == label:
            self.__blueLabel = None
        self.tableWidget.build(self._imageList)
        self.tableWidget._update()
        if self.calculationDialog is not None:
            self.calculationDialog.imageList = self._imageList
            self.calculationDialog.imageDict = self._imageDict

    def removeImageSlot(self, ddict):
        if type(ddict) == type({}):
            self.removeImage(ddict["label"])
        else:
            self.removeImage(ddict)

    def replaceImageSlot(self, ddict):
        self.reset()
        self.addImageSlot(ddict)

    def _imageResizeSlot(self):
        dialog = ImageShapeDialog(self, shape=self.__imageShape)
        dialog.setModal(True)
        ret = dialog.exec()
        if ret:
            shape = dialog.getImageShape()
            pad_with_nan = dialog.isIncompleteScan()
            dialog.close()
            del dialog
            try:
                if (shape[0] * shape[1]) <= 0:
                    self.reset()
                else:
                    self.setImageShape(shape, pad_with_nan=pad_with_nan)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error reshaping: %s" % sys.exc_info()[1])
                msg.exec()

    def setImageShape(self, shape, pad_with_nan=False):
        length = numpy.prod(shape, dtype=int)
        if self.__imageLength is None:
            self.__imageLength = length
        elif length != self.__imageLength:
            if pad_with_nan and length > self.__imageLength:
                self._padImagesWithNaN(length)
            else:
                raise ValueError(
                    "New length %d different of old length %d"
                    % (length, self.__imageLength)
                )
        self.__imageShape = shape
        self._updateSizeLabel()
        for key in self._imageDict.keys():
            self._imageDict[key]["image"] = self._imageDict[key]["image"].reshape(*shape)
        self.tableWidget._update()

    def _padImagesWithNaN(self, new_length):
        old_length = self.__imageLength
        for key in self._imageDict.keys():
            flat = self._imageDict[key]["image"].ravel()
            padded = numpy.full(new_length, numpy.nan, dtype=numpy.float64)
            padded[:old_length] = flat
            self._imageDict[key]["image"] = padded
        self.__prePadLength = old_length
        self.__imageLength = new_length

    def transposeImages(self):
        if self.__imageLength is None:
            return
        shape = [self.__imageShape[0], self.__imageShape[1]]
        shape.reverse()
        length = 1
        for value in shape:
            length *= value
        if length != self.__imageLength:
            raise ValueError(
                "New length %d different of old length %d"
                % (length, self.__imageLength)
            )
        self.__imageShape = (shape[0], shape[1])
        self._updateSizeLabel()
        for key in self._imageDict.keys():
            self._imageDict[key]["image"] = self._imageDict[key]["image"].T
        self.tableWidget._update()

    def _updateSizeLabel(self):
        if self.__imageLength is None:
            self.__sizeLabel.setText("No image set")
            return
        text = ""
        n = len(self.__imageShape)
        for i in range(n):
            value = self.__imageShape[i]
            if i == (n - 1):
                text += " %d" % value
            else:
                text += " %d x" % value
        self.__sizeLabel.setText(text)

    def reset(self):
        # ask the possible graph client to delete the image
        self._tableSlot({"r": [], "g": [], "b": []})
        self._imageList = []
        self._imageDict = {}
        self.__imageLength = self.__imageLengthOriginal
        self.__imageShape = self.__imageShapeOriginal
        self.__prePadLength = None
        self.__redLabel = None
        self.__greenLabel = None
        self.__blueLabel = None
        self.__redImageData = None
        self.__greenImageData = None
        self.__blueImageData = None
        self.__redMin = 0.0
        self.__redMax = 100.0
        self.__greenMin = 0.0
        self.__greenMax = 100.0
        self.__blueMin = 0.0
        self.__blueMax = 0.0
        self.__redImage = None
        self.__greenImage = None
        self.__blueImage = None
        self._updateSizeLabel()
        self.tableWidget.setRowCount(0)

    def update(self):
        self.__recolor()

    def getOutputFileNameAndFilter(self):
        initdir = PyMcaDirs.outputDir
        if self.outputDir is not None:
            if os.path.exists(self.outputDir):
                initdir = self.outputDir
        formatlist = [
            "HDF5 Files *.h5 *.nxs *.hdf *.hdf5",
            "ASCII Files *.dat",
            "EDF Files *.edf",
            "EDF(Float32) Files *.edf",
            "Single TIFF(Float32 Mono) Files *.tif",
            "Single TIFF(Mono) Files *.tif",
            "Several TIFF(Float32 Mono) Files *.tif",
            "Several TIFF(Mono) Files *.tif",
            "CSV(, separated) Files *.csv",
            "CSV(; separated) Files *.csv",
            "CSV(tab separated) Files *.csv",
        ]
        if self._saveFilter is None:
            self._saveFilter = formatlist[0]
        filelist, filterused = PyMcaFileDialogs.getFileList(
            parent=self,
            filetypelist=formatlist,
            message="Get output filename",
            currentdir=initdir,
            mode="SAVE",
            getfilter=True,
            single=True,
            currentfilter=self._saveFilter,
            native=False,
        )
        self._saveFilter = "%s" % filterused
        if len(filelist):
            return filelist[0], filterused
        else:
            return "", filterused
        return filelist

    def getOutputFileName(self):
        initdir = PyMcaDirs.outputDir
        if self.outputDir is not None:
            if os.path.exists(self.outputDir):
                initdir = self.outputDir

        formatlist = [
            "HDF5 Files *.h5 *.nxs *.hdf *.hdf5",
            "ASCII Files *.dat",
            "EDF Files *.edf",
            "EDF(Float32) Files *.edf",
            "TIFF(Float32 Mono) Files *.tif",
            "TIFF(Mono) Files *.tif",
            "CSV(, separated) Files *.csv",
            "CSV(; separated) Files *.csv",
            "CSV(tab separated) Files *.csv",
        ]
        if self._saveFilter in [None, ""]:
            self._saveFilter = formatlist[0]

        filename, self._saveFilter = PyMcaFileDialogs.getFileList(
            self,
            filetypelist=formatlist,
            message="Provide output file",
            currentdir=initdir,
            mode="SAVE",
            getfilter=True,
            single=False,
            currentfilter=self._saveFilter,
            native=None,
        )
        if not len(filename):
            return ""

        filename = filename[0]
        if len(filename):
            self.outputDir = os.path.dirname(filename)
            filterused = "." + self._saveFilter[-3:]
            PyMcaDirs.outputDir = os.path.dirname(filename)
            if len(filename) < 4:
                filename = filename + filterused
            elif filename[-4:] != filterused:
                if filterused in [".tif"] and filename[-4:] == "tiff":
                    # do not append .tif to the file name
                    pass
                else:
                    filename = filename + filterused
        return filename

    def getInputFileName(self, getfilter=False):
        initdir = PyMcaDirs.inputDir
        filedialog = qt.QFileDialog(self)
        filedialog.setFileMode(qt.QFileDialog.FileMode.ExistingFiles)
        filedialog.setAcceptMode(qt.QFileDialog.AcceptMode.AcceptOpen)
        filedialog.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict["gioconda16"])))
        formatlist = [
            "HDF5 Files *.h5 *.nxs *.hdf *.hdf5",
            "ASCII Files *dat",
            "EDF Files *edf",
            "EDF Files *ccd",
            "CSV Files *csv",
            "TIFF Files *tiff *tif",
            "TextImage Files *txt",
            "All Files *",
        ]
        strlist = QStringList()
        for f in formatlist:
            strlist.append(f)
        if hasattr(filedialog, "setFilters"):
            filedialog.setFilters(strlist)
        else:
            filedialog.setNameFilters(strlist)
        filedialog.setDirectory(initdir)
        ret = filedialog.exec()
        if not ret:
            if getfilter:
                return [""], None
            else:
                return [""]
        filename = filedialog.selectedFiles()
        filterused = None
        if len(filename):
            filename = ["%s" % fname for fname in filename]
            self.outputDir = os.path.dirname(filename[0])
            PyMcaDirs.inputDir = os.path.dirname(filename[0])
            if getfilter:
                if hasattr(filedialog, "selectedFilter"):
                    filterused = "%s" % filedialog.selectedFilter()
                else:
                    filterused = "%s" % filedialog.selectedNameFilter()
        else:
            filename = [""]
        if getfilter:
            return filename, filterused
        else:
            return filename

    def _addFileList(self):
        self.addFileList()

    def addFileList(self, filelist=None, filterused=None, ignoreStDev=True):
        if filelist is None:
            filelist, filterused = self.getInputFileName(getfilter=True)
        if not filelist:
            return
        if filterused is None:
            filterused = ""
        try:
            for uri in filelist:
                self._addSingleFile(uri, filterused=filterused, ignoreStDev=ignoreStDev)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error adding file: %s" % sys.exc_info()[1])
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise

    def addBatchDatFile(self, filename, ignoreStDev=True):
        warnings.warn("Use addFileList instead", DeprecationWarning)
        self.addFileList([filename], ignoreStDev=ignoreStDev)

    def _addSingleFile(self, uri, filterused=None, ignoreStDev=True):
        if not uri:
            return
        filename = uri.split("::")[0]
        self.outputDir = os.path.dirname(filename)
        if not os.path.isfile(filename):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("%s does not exist" % filename)
            msg.exec()
            return
        if filterused is None:
            filterused = ""
        if isTif(filename):
            try:
                self._addTifFile(filename, ignoreStDev=ignoreStDev)
            except Exception:
                _logger.debug("Built-in tif support unsuccessful")
                self._addQImageReadable(filename, ignoreStDev=ignoreStDev)
        elif isQImageReadable(filename):
            self._addQImageReadable(filename, ignoreStDev=ignoreStDev)
        elif isEdf(filename):
            self._addEdfFile(filename, ignoreStDev=ignoreStDev)
        elif isHdf5(filename.split("::")[0]):
            self._addHf5File(uri, ignoreStDev=ignoreStDev)
        elif filterused.upper().startswith("TEXTIMAGE"):
            self._addTxtFile(filename, ignoreStDev=ignoreStDev)
        else:
            extension = os.path.splitext(filename)[-1].lower()
            csv = extension == ".csv"
            self._addBatchDatFile(filename, csv=csv, ignoreStDev=ignoreStDev)

    def _ignoreStDevFile(self, filename):
        return bool(re.search(r"_s[A-Z][a-z_]", filename))

    def _ignoreStDevLabel(self, label):
        return bool(re.match(r"s\([A-Z][a-z_]", label))

    def _addEdfFile(self, filename, ignoreStDev=True):
        source = DataReader(filename)
        for key in source.getSourceInfo()["KeyList"]:
            dataObject = source.getDataObject(key)
            label = dataObject.info.get("Title", key)
            if ignoreStDev and self._ignoreStDevLabel(label):
                continue
            self.addImage(dataObject.data, os.path.basename(filename) + " " + label)

    def _addHf5File(self, uri: str, ignoreStDev: bool = True) -> bool:
        # Check dependencies
        if not self._checkDependencies(uri):
            return False
        # Read uri
        tmp = uri.split("::")
        if len(tmp) == 1:
            tmp = uri, None
        filename, h5path = tmp
        # Search for paths in selected items
        h5path = self._validateOrSelectH5Path(filename, h5path, ignoreStDev)
        if not h5path:
            return False
        return self._loadAndAddDatasets(filename, h5path)

    def _checkDependencies(self, uri: str) -> bool:
        if h5py is None:
            qt.QMessageBox.critical(
                self,
                "Missing dependency",
                f"Cannot read file {uri} (h5py is missing)."
            )
            return False
        return True

    def _validateOrSelectH5Path(self, filename: str, h5path: Optional[str], ignoreStDev: bool = True):

        if h5path:
            with HDF5Widget.h5open(filename) as hdf5_file:
                if h5path not in hdf5_file:
                    h5path = None

        if h5path:
            return h5path

        selected_uris = HDF5Widget.getUris(
            parent=self,
            filename=filename,
            message="Select Group or Dataset"
        )
        if not selected_uris:
            return None

        # Process each selected URI recursively
        for selected_uri in selected_uris:
            if not self._addHf5File(selected_uri, ignoreStDev=ignoreStDev):
                return None
        return None

    def _loadAndAddDatasets(self, filename: str, h5path: str, ignoreStDev: bool = True) -> bool:
        with HDF5Widget.h5open(filename) as hdf5_file:
            def matches_expected_shape(dset) -> bool:
                if self.__imageLength:
                    return dset.size == self.__imageLength
                return dset.ndim in (1, 2)
            datasets = NexusUtils.selectDatasets(
                hdf5_file[h5path],
                match=matches_expected_shape
            )
            if not datasets:
                qt.QMessageBox.critical(
                    self,
                    "No valid datasets",
                    f"No valid or consistent datasets were found in '{filename}::{h5path}'."
                )
                return self._addHf5File(filename, ignoreStDev=ignoreStDev)
            for dset in datasets:
                label = "/".join(dset.name.split("/")[-2:])
                self.addImage(dset[()], label)
        return True

    def _addQImageReadable(self, filename, ignoreStDev=True):
        if ignoreStDev and self._ignoreStDevFile(filename):
            return
        qimage = qt.QImage(filename)
        if qimage.isNull():
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Cannot read file %s as an image" % filename)
            msg.exec()
        else:
            # add as black and white
            self.addImage(makeQimageBW(qimage), os.path.basename(filename))

    def _addTifFile(self, filename, ignoreStDev=True):
        tif = TiffIO.TiffIO(filename, mode="rb")
        nImages = tif.getNumberOfImages()
        for nImage in range(nImages):
            info = tif.getInfo(nImage)["info"]
            imgData = tif.getImage(nImage)
            title = os.path.basename(filename)
            label = info.get("Title", "1.%d" % (nImage))
            if ignoreStDev and self._ignoreStDevLabel(label):
                continue
            title = os.path.basename(filename) + " " + label
            if len(imgData.shape) == 3:
                # color image
                colorIndex = 0
                for component in ["R", "G", "B"]:
                    self.addImage(
                        imgData[:, :, colorIndex].astype(numpy.float64),
                        title + "_" + component,
                    )
                    colorIndex += 1
                data = (
                    imgData[:, :, 0] * 0.114
                    + imgData[:, :, 1] * 0.587
                    + imgData[:, :, 2] * 0.299
                )
                self.addImage(data, title)
            else:
                self.addImage(imgData, title)

    def _addTxtFile(self, filename, ignoreStDev=True):
        if ignoreStDev and self._ignoreStDevFile(filename):
            return
        data = numpy.loadtxt(filename)
        self.addImage(data, os.path.basename(filename))

    def _addBatchDatFile(self, filename, csv=False, ignoreStDev=True):
        self.outputDir = os.path.dirname(filename)
        if sys.platform == "win32":
            f = open(filename, "rb")
        else:
            f = open(filename, "r")
        lines = f.read()
        f.close()
        if (sys.version_info > (3, 0)) and hasattr(lines, "decode"):
            lines = lines.decode()
        lines = lines.replace("\r", "\n")
        lines = lines.replace("\n\n", "\n")
        lines = lines.replace(",", "  ")
        lines = lines.replace("\t", "  ")
        lines = lines.replace(";", "  ")
        lines = lines.replace('"', "")
        lines = lines.split("\n")
        labels = lines[0].replace("\n", "").split("  ")
        i = 1
        while not len(lines[-i].replace("\n", "")):
            i += 1
        nlabels = len(labels)
        nrows = len(lines) - i
        if ignoreStDev and len(labels) > 4:
            iterationList = []
            for i in range(2, len(labels)):
                if not self._ignoreStDevLabel(labels[i]):
                    iterationList.append(i)
        else:
            iterationList = range(2, nlabels)
        totalArray = numpy.zeros((nrows, nlabels), numpy.float64)
        for i in range(nrows):
            totalArray[i, :] = [float(x) for x in lines[i + 1].split()]
        nrows = int(max(totalArray[:, 0]) + 1)
        ncols = int(max(totalArray[:, 1]) + 1)
        singleArray = numpy.zeros((nrows * ncols, 1), numpy.float64)
        for i in iterationList:
            singleArray[:, 0] = totalArray[:, i] * 1
            self.addImage(numpy.resize(singleArray, (nrows, ncols)), labels[i])

    def saveButtonClicked(self):
        self._saveButtonMenu.exec(self.cursor().pos())

    def saveSelectedImages(self):
        itemList = self.tableWidget.selectedItems()
        saveList = []
        imageList = []
        nImages = len(self._imageList)
        for item in itemList:
            row = item.row()
            if row >= nImages:
                errorText = "Requested to save non existing \nimage number %d." % row
                qt.QMessageBox.critical(self, "ValueError", errorText)
                return
            saveList.append(row)
        saveList.sort()
        for index in saveList:
            imageList.append(self._imageList[index])
        self.saveImageList(imagelist=imageList)

    def saveImageList(self, filename=None, imagelist=None):
        if imagelist is None:
            imageList = self._imageList
        else:
            imageList = imagelist
        if not len(imageList):
            qt.QMessageBox.information(
                self, "No Data", "Image list is empty.\nNothing to be saved"
            )
            return
        if filename is None:
            filename, filterused = self.getOutputFileNameAndFilter()
            if not len(filename):
                return
        else:
            filterused = None

        datalist = []
        labels = []
        for label in imageList:
            datalist.append(self._imageDict[label]["image"])
            # prevent problems when reading back the saved data
            labels.append(label.replace(" ", "_").replace(",", "_").replace(";", "_"))

        fileRoot = os.path.splitext(filename)[0]
        fileExtension = os.path.splitext(filename)[-1].lower()
        if fileExtension in [".edf"]:
            if "Float32" in self._saveFilter:
                dtype = numpy.float32
                ArraySave.save2DArrayListAsEDF(datalist, filename, labels, dtype)
            else:
                ArraySave.save2DArrayListAsEDF(datalist, filename, labels)
        elif fileExtension in [".tif", ".tiff"]:
            if "Float32" in self._saveFilter:
                dtype = numpy.float32
            else:
                dtype = None
            severalFiles = False
            if len(datalist) > 1:
                if filterused is not None:
                    if filterused.lower().startswith("several"):
                        severalFiles = True
                elif self._saveFilter.lower().startswith("several"):
                    severalFiles = True
            if severalFiles:
                for idx in range(len(labels)):
                    fname = fileRoot + labels[idx] + fileExtension
                    ArraySave.save2DArrayListAsMonochromaticTiff(
                        [datalist[idx]], fname, labels=[labels[idx]], dtype=dtype
                    )
            else:
                ArraySave.save2DArrayListAsMonochromaticTiff(
                    datalist, filename, labels=labels, dtype=dtype
                )
        elif fileExtension in [".csv"]:
            if "," in self._saveFilter:
                csvseparator = ","
            elif ";" in self._saveFilter:
                csvseparator = ";"
            else:
                csvseparator = "\t"
            ArraySave.save2DArrayListAsASCII(
                datalist, filename, labels, csv=True, csvseparator=csvseparator
            )
        else:
            ArraySave.save2DArrayListAsASCII(datalist, filename, labels, csv=False)

    def showStatisticsDialog(self):
        if self.statisticsDialog is None:
            self.statisticsDialog = StackPluginResultsWindow.StackPluginResultsWindow(
                usetab=False
            )
            self.statisticsDialog.setWindowTitle("Image Statistics")
            self.statisticsDialog.sigMaskImageWidgetSignal.connect(self.maskImageSlot)
            self.statisticsDialog.showStatsWidget()

        itemList = self.tableWidget.selectedItems()
        if len(itemList) < 1:
            images = [self._imageDict[x]["image"] for x in self._imageList]
            self.statisticsDialog.setStackPluginResults(
                images, image_names=self._imageList
            )
        else:
            rowList = []
            imageList = []
            imageNames = []
            for item in itemList:
                row = item.row()
                rowList.append(row)

            for index in rowList:
                name = self._imageList[index]
                imageList.append(self._imageDict[name]["image"])
                imageNames.append(name)
            self.statisticsDialog.setStackPluginResults(
                imageList, image_names=imageNames
            )

        self.statisticsDialog.setSelectionMask(self.getSelectionMask())
        self.statisticsDialog.showStatsWidget()
        if self.statisticsDialog.isHidden():
            self.statisticsDialog.show()
        self.statisticsDialog.raise_()

    def showCalculationDialog(self):
        if self.calculationDialog is None:
            selection = True
            self.calculationDialog = RGBImageCalculator.RGBImageCalculator(
                replace=self.replaceOption, selection=selection
            )
            self.calculationDialog.sigAddImageClicked.connect(self.addImageSlot)
            self.calculationDialog.sigRemoveImageClicked.connect(self.removeImage)
            if self.replaceOption:
                self.calculationDialog.sigReplaceImageClicked.connect(
                    self.replaceImageSlot
                )
            if selection:
                self.calculationDialog.graphWidget.sigMaskImageWidgetSignal.connect(
                    self.maskImageSlot
                )
                self.calculationDialog.graphWidget.setSelectionMask(
                    self.getSelectionMask()
                )
        self.calculationDialog.imageList = self._imageList
        self.calculationDialog.imageDict = self._imageDict
        if self.calculationDialog.isHidden():
            self.calculationDialog.graphWidget.setSelectionMask(self.getSelectionMask())
            self.calculationDialog.show()
        self.calculationDialog.raise_()

    def showKMeansDialog(self):
        itemList = self.tableWidget.selectedItems()
        if len(itemList) < 1:
            errorText = "Please select at least one image"
            qt.QMessageBox.critical(self, "ValueError", errorText)
            return
        if self.kMeansDialog is None:
            selection = True
            self.kMeansDialog = RGBImageCalculator.RGBImageCalculator(
                math="kmeans", replace=self.replaceOption, selection=selection
            )
            self.kMeansDialog.sigAddImageClicked.connect(self.addImageSlot)
            self.kMeansDialog.sigRemoveImageClicked.connect(self.removeImage)
            if self.replaceOption:
                self.kMeansDialog.sigReplaceImageClicked.connect(self.replaceImageSlot)
            if selection:
                self.kMeansDialog.graphWidget.sigMaskImageWidgetSignal.connect(
                    self.maskImageSlot
                )
                self.kMeansDialog.graphWidget.setSelectionMask(self.getSelectionMask())

        # TODO: just pass a list or an array of images instead of a dict
        nImages = len(self._imageList)
        dataDict = {}
        for item in itemList:
            row = item.row()
            if row >= nImages:
                errorText = (
                    "Requested to work with non existing \nimage number %d." % row
                )
                qt.QMessageBox.critical(self, "ValueError", errorText)
                return
            label = self._imageList[row]
            dataDict[label] = {"image": self._imageDict[label]["image"]}
        self.kMeansDialog.graphWidget.setImageData(None, clearmask=False)
        self.kMeansDialog.imageDict = dataDict
        if self.kMeansDialog.isHidden():
            self.kMeansDialog.graphWidget.setSelectionMask(self.getSelectionMask())
            self.kMeansDialog.show()
        self.kMeansDialog.raise_()

    def showScatterPlotDialog(self):
        if self.scatterPlotWidget is None:
            self.scatterPlotWidget = (
                ScatterPlotCorrelatorWidget.ScatterPlotCorrelatorWidget(
                    labels=("Legend", "X", "Y"),
                    types=("Text", "RadioButton", "RadioButton"),
                )
            )
            self.scatterPlotWidget.sigMaskScatterWidgetSignal.connect(
                self.maskImageSlot
            )
        # I should check if the list is to be updated instead of systematically
        # send it
        initialize = True
        for label in self._imageList:
            item = self._imageDict[label]["image"]
            if initialize:
                self.scatterPlotWidget.setSelectableItemList([item], labels=[label])
                initialize = False
            else:
                self.scatterPlotWidget.addSelectableItem(item, label=label)
        self.scatterPlotWidget.setSelectionMask(self.getSelectionMask())
        self.scatterPlotWidget.show()
        self.scatterPlotWidget.raise_()

    def getSelectedDataList(self):
        itemList = self.tableWidget.selectedItems()
        nImages = len(self._imageList)
        datalist = []
        for item in itemList:
            row = item.row()
            if row >= nImages:
                errorText = (
                    "Requested to work with non existing \nimage number %d." % row
                )
                qt.QMessageBox.critical(self, "ValueError", errorText)
                return
            label = self._imageList[row]
            datalist.append(self._imageDict[label]["image"])
        return datalist

    def showPCADialog(self):
        if self.pcaDialog is None:
            selection = True
            self.pcaDialog = PCADialog.PCADialog(rgbwidget=self, selection=selection)
            self.pcaDialog.pcaWindow.buildAndConnectImageButtonBox(self.replaceOption)
            self.pcaDialog.pcaWindow.sigMaskImageWidgetSignal.connect(
                self.maskImageSlot
            )

        datalist = self.getSelectedDataList()
        if len(datalist) < 2:
            errorText = "Please select at least two images"
            qt.QMessageBox.critical(self, "ValueError", errorText)
            return

        self.pcaDialog.setData(datalist)
        self.pcaDialog.pcaWindow.setSelectionMask(self.getSelectionMask())
        self.pcaDialog.show()
        self.pcaDialog.raise_()

    def showNNMADialog(self):
        if self.nnmaDialog is None:
            selection = True
            self.nnmaDialog = NNMADialog.NNMADialog(rgbwidget=self, selection=selection)
            self.nnmaDialog.nnmaWindow.buildAndConnectImageButtonBox(self.replaceOption)
            self.nnmaDialog.nnmaWindow.sigMaskImageWidgetSignal.connect(
                self.maskImageSlot
            )

        datalist = self.getSelectedDataList()
        if len(datalist) < 2:
            errorText = "Please select at least two images"
            qt.QMessageBox.critical(self, "ValueError", errorText)
            return

        self.nnmaDialog.setData(datalist)
        self.nnmaDialog.nnmaWindow.setSelectionMask(self.getSelectionMask())
        self.nnmaDialog.show()
        self.nnmaDialog.raise_()

    def maskImageSlot(self, ddict):
        if ddict["event"] == "addImageClicked":
            ddict["label"] = ddict["title"]
            self.addImageSlot(ddict)
            return
        if ddict["event"] == "replaceImageClicked":
            ddict["label"] = ddict["title"]
            self.replaceImageSlot(ddict)
            return
        if ddict["event"] == "removeImageClicked":
            ddict["label"] = ddict["title"]
            self.removeImageSlot(ddict)
            return
        if ddict["event"] in [
            "selectionMaskChanged",
            "resetSelection",
            "invertSelection",
        ]:
            mask = ddict.get("current", None)
            self.setSelectionMask(mask, instance_id=ddict["id"])
            self.sigMaskImageWidgetSignal.emit(ddict)
            return

    def setSelectionMask(self, mask, instance_id=None):
        self._lastMask = mask
        widgetList = []
        if self.statisticsDialog:
            widgetList.append(self.statisticsDialog)
        if self.calculationDialog:
            widgetList.append(self.calculationDialog.graphWidget)
        if self.kMeansDialog:
            widgetList.append(self.kMeansDialog.graphWidget)
        if self.pcaDialog:
            widgetList.append(self.pcaDialog.pcaWindow)
        if self.nnmaDialog:
            widgetList.append(self.nnmaDialog.nnmaWindow)
        if self.scatterPlotWidget:
            widgetList.append(self.scatterPlotWidget)
        for widget in widgetList:
            if id(widget) != instance_id:
                widget.setSelectionMask(mask)

    def getSelectionMask(self):
        return self._lastMask

    def addImageSlot(self, ddict):
        self.addImage(ddict["image"], ddict["label"])

    def closeEvent(self, event):
        if self.calculationDialog is not None:
            self.calculationDialog.close()
        if self.profileImageListWidget is not None:
            self.profileImageListWidget.close()
        qt.QWidget.closeEvent(self, event)

    """
    #This was for debugging
    #left out in order to skip PIL from the list of
    #packages when building binaries.
    def tiffExport(self, filename = "test.tif"):
        import Image
        Image.preinit()
        image = self.__redImage + self.__greenImage + self.__blueImage
        width  = self.__imageShape[0]
        height = self.__imageShape[1]
        pilImage = Image.fromstring("RGBX",(width,height),image)
        if os.path.exists(filename):
            os.remove(filename)
        pilImage.save(filename)
    """

    def profileSelectedImages(self):
        itemList = self.tableWidget.selectedItems()
        if len(itemList) < 1:
            errorText = "Please select at least one row in the table"
            qt.QMessageBox.critical(self, "ValueError", errorText)
            return
        profileList = []
        imageList = []
        imageNames = []

        for item in itemList:
            row = item.row()
            profileList.append(row)

        for index in profileList:
            name = self._imageList[index]
            imageList.append(self._imageDict[name]["image"])
            imageNames.append(name)
        self.profileImageList(imagelist=imageList, imagenames=imageNames)

    def profileImageList(self, imagelist=None, imagenames=None):
        if imagelist in [None, []]:
            return
        if self.profileImageListWidget is None:
            self.profileImageListWidget = ExternalImagesWindow.ExternalImagesWindow(
                None,
                crop=False,
                imageicons=False,
                profileselection=True,
                depthselection=True,
            )
        self.profileImageListWidget.setImageList(
            imagelist=imagelist, imagenames=imagenames
        )
        self.profileImageListWidget.show()


class ImageShapeDialog(qt.QDialog):
    def __init__(self, parent=None, shape=None):
        qt.QDialog.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        label1 = MyQLabel(self, bold=False, color=qt.QApplication.instance().palette().color(qt.QPalette.Text))
        label1.setText("Number of rows    = ")
        self.rows = qt.QLineEdit(self)
        self._size = None
        self.columns = qt.QLineEdit(self)
        if shape is not None:
            self.rows.setText("%g" % shape[0])
            self.columns.setText("%g" % shape[1])
            self._size = shape[0] * shape[1]
            self._shape = shape
            self.setWindowTitle("Reshape %d x %d image" % (shape[0], shape[1]))
        label2 = MyQLabel(self, bold=False, color=qt.QApplication.instance().palette().color(qt.QPalette.Text))
        label2.setText("Number of columns = ")
        self.incompleteScanCheckBox = qt.QCheckBox("Incomplete scan (pad with NaN)", self)
        self.incompleteScanCheckBox.setToolTip(
            "Explicit values for both rows and columns.\n"
            "Missing pixels will be filled with NaN."
        )
        self.cancelButton = qt.QPushButton(self)
        self.cancelButton.setText("Dismiss")
        self.okButton = qt.QPushButton(self)
        self.okButton.setText("Accept")

        self.cancelButton.setAutoDefault(False)
        self.okButton.setAutoDefault(False)
        self.rows.editingFinished[()].connect(self._rowsChanged)
        self.columns.editingFinished[()].connect(self._columnsChanged)

        self.mainLayout.addWidget(label1, 0, 0)
        self.mainLayout.addWidget(self.rows, 0, 1)
        self.mainLayout.addWidget(label2, 1, 0)
        self.mainLayout.addWidget(self.columns, 1, 1)
        self.mainLayout.addWidget(self.incompleteScanCheckBox, 2, 0, 1, 2)
        self.mainLayout.addWidget(self.cancelButton, 3, 0)
        self.mainLayout.addWidget(self.okButton, 3, 1)
        self.cancelButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)

    def isIncompleteScan(self):
        return self.incompleteScanCheckBox.isChecked()

    def _rowsChanged(self):
        if not self._size:
            return
        if self.incompleteScanCheckBox.isChecked():
            return
        nrows, ncolumns = self.getImageShape()
        size = nrows * ncolumns
        if size and size != self._size:
            self.columns.setText("%g" % (self._size / float(nrows)))

    def _columnsChanged(self):
        if not self._size:
            return
        if self.incompleteScanCheckBox.isChecked():
            return
        nrows, ncolumns = self.getImageShape()
        size = nrows * ncolumns
        if size and size != self._size:
            self.rows.setText("%g" % (self._size / float(ncolumns)))

    def getImageShape(self):
        text = "%s" % self.rows.text()
        if len(text):
            nrows = int(float(text))
        else:
            nrows = 0
        text = "%s" % self.columns.text()
        if len(text):
            ncolumns = int(float(text))
        else:
            ncolumns = 0
        return nrows, ncolumns

    def accept(self):
        if self._size is None:
            return qt.QDialog.accept(self)
        nrows, ncolumns = self.getImageShape()
        try:
            product = nrows * ncolumns
            if product == self._size:
                return qt.QDialog.accept(self)
            elif self.incompleteScanCheckBox.isChecked():
                if product >= self._size and product > 0:
                    return qt.QDialog.accept(self)
                else:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText(
                        "Shape %d x %d = %d is smaller than data size %d.\n\n"
                        "An incomplete scan can only be padded "
                        "with NaN to fill missing pixels.\n"
                        "It cannot be cropped.\n\n"
                        "If the data was already padded in a "
                        "previous load, please reload the file "
                        "and enter the correct shape."
                        % (nrows, ncolumns, product, self._size)
                    )
                    msg.exec()
            else:
                self.rows.setText("%g" % self._shape[0])
                self.columns.setText("%g" % self._shape[1])
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid shape %d x %d" % (nrows, ncolumns))
                msg.exec()
        except Exception:
            self.rows.setText("%g" % self._shape[0])
            self.columns.setText("%g" % self._shape[1])
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error reshaping: %s" % sys.exc_info()[1])
            msg.exec()


class MyQLabel(qt.QLabel):
    def __init__(self, parent=None, name=None, fl=0, bold=True, color=None):
        qt.QLabel.__init__(self, parent)
        if color is None:
            color = qt.QApplication.instance().palette().color(qt.QPalette.Text)
        if qt.qVersion() < "4.0.0":
            self.color = color
            self.bold = bold
        else:
            palette = qt.QPalette(self.palette())
            role = self.foregroundRole()
            palette.setColor(role, color)
            self.setPalette(palette)
            self.font().setBold(bold)

    if qt.qVersion() < "4.0.0":

        def drawContents(self, painter):
            painter.font().setBold(self.bold)
            pal = self.palette()
            pal.setColor(qt.QColorGroup.Foreground, self.color)
            self.setPalette(pal)
            qt.QLabel.drawContents(self, painter)
            painter.font().setBold(0)


def main(args):
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    container = qt.QSplitter()

    w = RGBCorrelatorWidget(container)
    graph = RGBCorrelatorGraph.RGBCorrelatorGraph(container)

    def slot(ddict):
        if "image" in ddict:
            image_buffer = ddict["image"]
            size = ddict["size"]
            image_buffer = image_buffer.reshape(size[1], size[0], 4)
            graph.graph.addImage(image_buffer)
            graph.graph.replot()

    w.sigRGBCorrelatorWidgetSignal.connect(slot)

    filelist = args.files

    if filelist:
        try:
            import DataSource
            DataReader = DataSource.DataSource
        except Exception:
            from PyMca5.PyMcaCore import EdfFileDataSource
            DataReader = EdfFileDataSource.EdfFileDataSource

        for fname in filelist:
            source = DataReader(fname)
            for key in source.getSourceInfo()["KeyList"]:
                dataObject = source.getDataObject(key)
                w.addImage(dataObject.data, os.path.basename(fname) + " " + key)
    else:
        array1 = numpy.arange(10000)
        array2 = numpy.resize(numpy.arange(10000), (100, 100))
        array2 = numpy.transpose(array2)
        array3 = array1 * 1

        w.addImage(array1)
        w.addImage(array2)
        w.addImage(array3)
        w.setImageShape([100, 100])

    # containerLayout.addWidget(w)
    # containerLayout.addWidget(graph)
    container.show()

    # Auto-close Qt application for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="RGB Correlator Viewer", add_qt_options=True)

    parser.add_argument("files", nargs="*", help="Input files")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
