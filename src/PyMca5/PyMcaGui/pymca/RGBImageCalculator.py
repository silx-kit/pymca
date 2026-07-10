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
import traceback
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaGui.plotting import ColormapDialog
from PyMca5 import spslut
try:
    from PyMca5.PyMcaMath.mva import KMeansModule
    KMEANS = KMeansModule.KMEANS
except Exception:
    KMEANS = False
from . import QPyMcaMatplotlibSave
MATPLOTLIB = True

convertToRowAndColumn = MaskImageWidget.convertToRowAndColumn
qt = MaskImageWidget.qt
IconDict = MaskImageWidget.IconDict
QTVERSION   = qt.qVersion()
COLORMAPLIST = [spslut.GREYSCALE, spslut.REVERSEGREY, spslut.TEMP,
                spslut.RED, spslut.GREEN, spslut.BLUE, spslut.MANY]


_logger = logging.getLogger(__name__)


class RGBImageCalculator(qt.QWidget):
    sigAddImageClicked = qt.pyqtSignal(object)
    sigRemoveImageClicked = qt.pyqtSignal(object)
    sigReplaceImageClicked = qt.pyqtSignal(object)

    def __init__(self, parent=None, math=True, replace=False,
                 scanwindow=None, selection=False, usesilx=False):
        qt.QWidget.__init__(self, parent)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.setWindowTitle("PyMca - RGB Image Calculator")

        self._useSilx = usesilx
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.imageList   = None
        self.imageDict   = None
        self._imageData = None
        self._xScale = None
        self._yScale = None
        self.__imagePixmap   = None
        self.__imageColormap = None
        self.__imageColormapDialog = None
        self.setDefaultColormap(2, logflag=False)
        self._y1AxisInverted = False
        self._matplotlibSaveImage = None
        self._build(math=math, replace=replace, scanwindow=scanwindow,
                    selection=selection)

    def _buildMath(self):
        self.mathBox = qt.QWidget(self)
        self.mathBox.mainLayout = qt.QHBoxLayout(self.mathBox)

        self.mathLabel = qt.QLabel(self.mathBox)
        self.mathLabel.setText("New image = ")

        self.mathExpression = qt.QLineEdit(self.mathBox)
        text  = ""
        text += "Enter a mathematical expression in which your images\n"
        text += "have to be identified by a number between curly brackets.\n"
        text += "In order to normalize image 1 by image 2:  {1}/{2}\n"
        text += "The numbers go from 1 to the number of rows in the table.\n"
        text += "If you can suggest useful correlation functions please,\n"
        text += "do not hesitate to contact us in order to implement them."

        self.mathExpression.setToolTip(text)

        self.mathAction = qt.QToolButton(self.mathBox)
        self.mathAction.setText("CALCULATE")

        self.mathBox.mainLayout.addWidget(self.mathLabel)
        self.mathBox.mainLayout.addWidget(self.mathExpression)
        self.mathBox.mainLayout.addWidget(self.mathAction)
        self.mainLayout.addWidget(self.mathBox)
        self.mathAction.clicked.connect(self._calculateClicked)

    def _buildKMeansMath(self):
        self.mathBox = qt.QWidget(self)
        self.mathBox.mainLayout = qt.QHBoxLayout(self.mathBox)

        self.mathLabel = qt.QLabel(self.mathBox)
        self.mathLabel.setText("Please select number of clusters = ")

        self.mathExpression = qt.QSpinBox(self.mathBox)
        text  = ""
        text += "Enter the number of desired clusters.\n"
        text += "It cannot be greater than the number of selected images."
        self.mathExpression.setMinimum(2)
        self.mathExpression.setMaximum(100)
        self.mathExpression.setValue(4)
        self.mathExpression.setToolTip(text)

        self.mathAction = qt.QToolButton(self.mathBox)
        self.mathAction.setText("CALCULATE")

        self.mathBox.mainLayout.addWidget(self.mathLabel)
        self.mathBox.mainLayout.addWidget(self.mathExpression)
        self.mathBox.mainLayout.addWidget(self.mathAction)
        self.mainLayout.addWidget(self.mathBox)
        self.mathAction.clicked.connect(self._calculateKMeansClicked)

    def _build(self, math=True, replace=False, scanwindow=False, selection=False):
        if math:
            if math == "kmeans":
                self._buildKMeansMath()
            else:
                self._buildMath()
        if selection:
            imageicons=True
        else:
            imageicons=False

        self.graphWidget = None
        if self._useSilx or self._useSilx is None:
            try:
                from PyMca5.PyMcaGui.plotting import SilxMaskImageWidget
                self.graphWidget = SilxMaskImageWidget.SilxMaskImageWidget()
                self.graphWidget.setAlphaSliderVisible(False)
                self.graphWidget.setBackgroundActionVisible(False)
                self.graphWidget.setMedianFilterWidgetVisible(False)
                self.graphWidget.setProfileToolbarVisible(True)
                self.graphWidget.setProfileToolbarVisible(True)
                self.graphWidget.setButtonBoxWidgetVisible(False)
                self.graphWidget.group.removeAction(\
                                self.graphWidget.getMaskAction())
                self.graphWidget.slider.hide()
                self.graphWidget.graph = self.graphWidget.plot
                if not hasattr(self.graphWidget, "setXLabel"):
                    self.graphWidget.setXLabel = \
                        self.graphWidget.plot.setGraphXLabel
                    self.graphWidget.setYLabel = \
                        self.graphWidget.plot.setGraphYLabel
                self._useSilx = True
            except Exception:
                if self._useSilx:
                    raise
                else:
                    _logger.debug("Defaulting to not using silx")
                    self._useSilx = False
                    self.graphWidget = None
        if self.graphWidget is None:
            self._useSilx = False
            self.graphWidget = MaskImageWidget.MaskImageWidget(self,
                                                           colormap=True,
                                                           standalonesave=True,
                                                           imageicons=imageicons,
                                                           profileselection=True,
                                                           selection=selection,
                                                           scanwindow=scanwindow,
                                                           aspect=True)

        self.nameBox = qt.QWidget(self)
        self.nameBox.mainLayout = qt.QHBoxLayout(self.nameBox)

        self.nameLabel = qt.QLabel(self.nameBox)

        self.nameLabel.setText("Image Name = ")
        #self.nameLabel.setText(qt.QString(qt.QChar(0x3A3)))

        self.name = qt.QLineEdit(self.nameBox)
        self.nameBox.mainLayout.addWidget(self.nameLabel)
        self.nameBox.mainLayout.addWidget(self.name)

        # The IMAGE selection
        #self.imageButtonBox = qt.QWidget(self)
        self.imageButtonBox = self.nameBox
        buttonBox = self.imageButtonBox
        #self.imageButtonBoxLayout = qt.QHBoxLayout(buttonBox)
        self.imageButtonBoxLayout = self.nameBox.mainLayout
        self.imageButtonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.imageButtonBoxLayout.setSpacing(0)
        self.addImageButton = qt.QPushButton(buttonBox)
        icon = qt.QIcon(qt.QPixmap(IconDict["rgb16"]))
        self.addImageButton.setIcon(icon)
        self.addImageButton.setText("ADD IMAGE")
        self.removeImageButton = qt.QPushButton(buttonBox)
        self.removeImageButton.setIcon(icon)
        self.removeImageButton.setText("REMOVE IMAGE")
        self.imageButtonBoxLayout.addWidget(self.addImageButton)
        self.imageButtonBoxLayout.addWidget(self.removeImageButton)
        if replace:
            self.replaceImageButton = qt.QPushButton(buttonBox)
            self.replaceImageButton.setIcon(icon)
            self.replaceImageButton.setText("REPLACE IMAGE")
            self.imageButtonBoxLayout.addWidget(self.replaceImageButton)

        #self.mainLayout.addWidget(self.nameBox)
        self.mainLayout.addWidget(self.graphWidget)
        self.mainLayout.addWidget(buttonBox)
        self.addImageButton.clicked.connect(self._addImageClicked)
        self.removeImageButton.clicked.connect(self._removeImageClicked)
        if replace:
            self.replaceImageButton.clicked.connect( \
                self._replaceImageClicked)

        #it consumes too much CPU, therefore only on click
        #self.graphWidget.graph.canvas().setMouseTracking(1)
        if self._useSilx:
            self.graphWidget.showInfo()
            self.graphWidget.plot.sigPlotSignal.connect(\
                                self._graphSignal)
        else:
            self.graphWidget.graphWidget.showInfo()
            self.graphWidget.graphWidget.graph.sigPlotSignal.connect(\
                                self._graphSignal)

    def plotImage(self, update=True):
        self.graphWidget.setImageData(self._imageData,
                                      xScale=self._xScale,
                                      yScale=self._yScale)
        return self.graphWidget.plotImage(update=update)

    def _calculateClicked(self):
        _logger.debug("Calculate clicked")
        text = "%s" % self.mathExpression.text()
        if not len(text):
            qt.QMessageBox.critical(self, "Calculation Error",
                                    "Empty expression")
            return 1

        expression = text * 1
        name       = text * 1
        i = 1
        for label in self.imageList:
            item = "{%d}" % i
            replacingChain ="self.imageDict[self.imageList[%d]]['image']" % (i-1)
            expression = expression.replace(item, replacingChain)
            tmpLabel = label
            name = name.replace(item, tmpLabel)
            i = i + 1
        try:
            self._imageData = 1 * eval(expression)
        except Exception:
            error = sys.exc_info()
            text = "Failed to evaluate expression:\n"
            text += "%s\n" % expression
            text += "%s" % error[1]
            qt.QMessageBox.critical(self,"%s" % error[0], text)
            return 1
        self.setName("(%s)" % name)
        self.plotImage()

    def _calculateKMeansClicked(self):
        _logger.debug("Calculate k-means clicked")
        k = self.mathExpression.value()
        name       = "k-means(%d)" % k

        # get dimensions
        keys = list(self.imageDict.keys())
        key = keys[0]
        image = self.imageDict[key]['image']
        shape = image.shape
        nSamples = image.size
        # build a stack (expected a small amount of images)
        data = numpy.zeros((nSamples, len(keys)),
                            dtype=numpy.float64)
        i = 0
        for key in self.imageDict:
            data[:, i] = self.imageDict[key]['image'].ravel()
            i += 1

        try:
            self._imageData = KMeansModule.label(data, k,
                                                 normalize=True).reshape(shape)
        except Exception:
            self._imageData = None
            text = "Failed to evaluate k-means(%d)\n" % k
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Save error")
            msg.setText(text)
            msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return 1
        self.setName("(%s)" % name)
        self.plotImage()

    def setName(self, name):
        self.name.setText(name)
        self.graphWidget.graph.setGraphTitle("%s" % name)

    def _addImageClicked(self):
        _logger.debug("Add image clicked")
        if self._imageData is None:
            return
        if len(self._imageData) == 0:
            return
        text = "%s" % self.name.text()
        if not len(text):
            qt.QMessageBox.critical(self, "Name Error",
                                    "Please give a name to the image")
            return 1
        ddict = {}
        ddict['label'] = text
        ddict['image']  = self._imageData
        self.sigAddImageClicked.emit(ddict)

    def _removeImageClicked(self):
        _logger.debug("remove image clicked")
        text = "%s" % self.name.text()
        if not len(text):
            qt.QMessageBox.critical(self, "Name Error",
                                    "Please enter the image name")
            return 1
        self.sigRemoveImageClicked.emit(text)

    def _replaceImageClicked(self):
        _logger.debug("replace image clicked")
        text = "%s" % self.name.text()
        if not len(text):
            qt.QMessageBox.critical(self, "Name Error",
                                    "Please enter the image name")
            return 1
        ddict = {}
        ddict['label'] = text
        ddict['image']  = self._imageData
        self.sigReplaceImageClicked.emit(ddict)


    def setDefaultColormap(self, colormapindex, logflag=False):
        self.__defaultColormap = COLORMAPLIST[min(colormapindex, len(COLORMAPLIST)-1)]
        if logflag:
            self.__defaultColormapType = spslut.LOG
        else:
            self.__defaultColormapType = spslut.LINEAR

    def _graphSignal(self, ddict):
        if ddict['event'] in ["mouseMoved", "MouseAt"]:
            if self._imageData is None:
                self.graphWidget.setInfoText("    X = ???? Y = ???? Z =????")
                return
            r, c = convertToRowAndColumn(ddict['x'], ddict['y'],
                                                        self._imageData.shape,
                                                        xScale=self._xScale,
                                                        yScale=self._yScale,
                                                        safe=True)
            z = self._imageData[r, c]
            if hasattr(self.graphWidget, "setInfoText"):
                self.graphWidget.setInfoText("    X = %.4g Y = %.4g Z = %.7g" %\
                                               (ddict['x'], ddict['y'], z))
            else:
                self.graphWidget.graphWidget.setInfoText("    X = %.2f Y = %.2f Z = %.7g" %\
                                               (ddict['x'], ddict['y'], z))

    def closeEvent(self, event):
        if self.__imageColormapDialog is not None:
            self.__imageColormapDialog.close()
        if self._matplotlibSaveImage is not None:
            self._matplotlibSaveImage.close()
        qt.QWidget.closeEvent(self, event)

def test():
    app = qt.QApplication(sys.argv)
    w = RGBImageCalculator()

    array1 = numpy.arange(10000)
    array2 = numpy.transpose(array1)
    array3 = array1 * 1
    array1 = array1.reshape(100,100)
    array2 = array2.reshape(100,100)
    array3 = array3.reshape(100,100)
    imageList = ["array1", "array2","array3"]
    imageDict = {"array1":{'image':array1},
                 "array2":{'image':array2},
                 "array3":{'image':array3}}
    w.imageList = imageList
    w.imageDict = imageDict
    w.show()
    app.exec()

if __name__ == "__main__":
    test()
