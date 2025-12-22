#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.pymca import ExternalImagesWindow
from PyMca5.PyMcaGui.io import PyMcaFileDialogs

class ParametersWidget(qt.QWidget):
    parametersWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, ndim=2):
        qt.QWidget.__init__(self, parent)
        self._nDimensions = 2
        self._shape = 3000, 3000
        self._settingShape = False
        self._build()

    def _build(self):
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.widgetDict = {}
        for i in range(self._nDimensions):
            key = "Dim %d" % i
            self.widgetDict[key] = {}

            #offset
            offsetLabel = qt.QLabel(self)
            offsetLabel.setText("Dimension %d Offset :" % i)
            offset = qt.QSpinBox(self)
            offset.setMinimum(0)
            offset.setMaximum(100)
            offset.setValue(0)

            #width
            widthLabel = qt.QLabel(self)
            widthLabel.setText("Dimension %d width :" % i)
            width = qt.QComboBox(self)
            nMax = int(numpy.log10(self._shape[i])/numpy.log10(2))
            for j in range(1, nMax + 1):
                width.addItem("%d" % pow(2, j))
            self.widgetDict[key]['offset'] = offset
            self.widgetDict[key]['width'] = width
            self.mainLayout.addWidget(offsetLabel,  i, 0)
            self.mainLayout.addWidget(offset, i, 1)
            self.mainLayout.addWidget(widthLabel,  i, 2)
            self.mainLayout.addWidget(width, i, 3)
            width.setCurrentIndex(width.count() - 1)

        # connections
        for i in range(self._nDimensions):
            key = "Dim %d" % i
            offset = self.widgetDict[key]['offset']
            offset.valueChanged.connect(self._offsetValueChanged)
            width = self.widgetDict[key]['width']
            width.currentIndexChanged.connect(self._widthValueChanged)

    def _offsetValueChanged(self, value):
        if self._settingShape:
            return
        ddict = self.getParameters()
        for i in range(self._nDimensions):
            key = "Dim %d" % i
            offset = ddict[key]['offset']
            width = ddict[key]['width']
            if (offset + width) > self._shape[i]:
                offset = self._shape[i] - width
                if offset < 0:
                    print("This should not happen")
                    offset = 0
                self.widgetDict[key]['offset'].setValue(offset)
                return
            else:
                lastItem = 0
                for j in range(1, 11):
                    v = pow(2, j)
                    if v <= (self._shape[i] - offset):
                        lastItem = "%d" %  v
                    self.widgetDict[key]['width'].addItem(lastItem)
        self.emitParametersWidgetSignal()

    def _widthValueChanged(self, value):
        if self._settingShape:
            return
        ddict = self.getParameters()
        for i in range(self._nDimensions):
            key = "Dim %d" % i
            offset = ddict[key]['offset']
            width = ddict[key]['width']
            if (offset + width) > self._shape[i]:
                offset = self._shape[i] - width
                self.widgetDict[key]['offset'].setValue(offset)
                return
        self.emitParametersWidgetSignal()

    def setShape(self, shape):
        if len(shape) != self._nDimensions:
            raise ValueError("Shape length does not match number of dimensions")

        self._shape = shape
        self._settingShape = True

        for i in range(self._nDimensions):
            key = "Dim %d" % i
            # offset
            current = self.widgetDict[key]['offset'].value()
            self.widgetDict[key]['offset'].setMinimum(0)
            self.widgetDict[key]['offset'].setMaximum(shape[i] - 1)
            if current < shape[0]:
                self.widgetDict[key]['offset'].setValue(current)
            else:
                self.widgetDict[key]['offset'].setValue(0)

            # width
            current = str(self.widgetDict[key]['width'].currentText())
            self.widgetDict[key]['width'].clear()
            nMax = int(numpy.log10(self._shape[i])/numpy.log10(2))
            for j in range(1, nMax + 1):
                self.widgetDict[key]['width'].addItem("%d" % pow(2, j))
            self.widgetDict[key]['width'].setCurrentIndex(nMax - 1)

        self._settingShape = False

    def getParameters(self):
        ddict = {}
        for i in range(self._nDimensions):
            key = "Dim %d" % i
            ddict[key] = {}
            ddict[key]['offset'] = self.widgetDict[key]['offset'].value()
            width = str(self.widgetDict[key]['width'].currentText())
            ddict[key]['width'] = int(width)
        ddict['shape'] = self._shape * 1
        return ddict

    def emitParametersWidgetSignal(self, event="ParametersChanged"):
        ddict = self.getParameters()
        ddict['event'] = "ParametersChanged"
        self.parametersWidgetSignal.emit(ddict)

class OutputFile(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.checkBox = qt.QCheckBox(self)
        self.checkBox.setText("Use")
        self.fileName = qt.QLineEdit(self)
        self.fileName.setText("")
        self.fileName.setReadOnly(True)
        self.browse = qt.QPushButton(self)
        self.browse.setAutoDefault(False)
        self.browse.setText("Browse")
        self.browse.clicked.connect(self.browseFile)
        self.mainLayout.addWidget(self.checkBox)
        self.mainLayout.addWidget(self.fileName)
        self.mainLayout.addWidget(self.browse)

    def browseFile(self):
        filelist = PyMcaFileDialogs.getFileList(self,
                                filetypelist=['HDF5 files (*.h5)'],
                                message="Please enter output file",
                                mode="SAVE",
                                single=True)
        if len(filelist):
            name = filelist[0]
            if not name.endswith('.h5'):
                name = name + ".h5"
            self.fileName.setText(name)

    def getParameters(self):
        ddict = {}
        ddict['file_use'] = self.checkBox.isChecked()
        ddict['file_name'] = qt.safe_str(self.fileName.text())
        return ddict

    def setForcedFileOutput(self, flag=True):
        if flag:
            self.checkBox.setChecked(True)
            self.checkBox.setEnabled(False)
        else:
            self.checkBox.setChecked(False)
            self.checkBox.setEnabled(True)


class FFTAlignmentWindow(qt.QWidget):
    def __init__(self, parent=None, stack=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("FFT Alignment")
        self._build()

    def _build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        self.parametersWidget = ParametersWidget(self)
        self.outputFileWidget = OutputFile(self)
        self.imageBrowser = ExternalImagesWindow.ExternalImagesWindow(self,
                                                    crop=False,
                                                    selection=False,
                                                    imageicons=False)
        self.mainLayout.addWidget(self.parametersWidget)
        self.mainLayout.addWidget(self.outputFileWidget)
        self.mainLayout.addWidget(self.imageBrowser)
        self.parametersWidget.parametersWidgetSignal.connect(self.mySlot)

    def setStack(self, stack, index=None):
        if index is None:
            if hasattr(stack, "info"):
                index = stack.info.get('McaIndex')
            else:
                index = 0
        if hasattr(stack, "info") and hasattr(stack, "data"):
            data = stack.data
        else:
            data = stack
        if isinstance(data, numpy.ndarray):
            self.outputFileWidget.setForcedFileOutput(False)
        else:
            self.outputFileWidget.setForcedFileOutput(True)
        self.imageBrowser.setStack(data, index=index)
        shape = self.imageBrowser.getImageData().shape
        self.parametersWidget.setShape(shape)
        ddict = self.parametersWidget.getParameters()
        self.mySlot(ddict)

    def getParameters(self):
        parameters = self.parametersWidget.getParameters()
        parameters['reference_image'] = self.imageBrowser.getImageData()
        parameters.update(self.outputFileWidget.getParameters())
        parameters['reference_index'] = self.imageBrowser.getCurrentIndex()
        return parameters

    def mySlot(self, ddict):
        mask = self.imageBrowser.getSelectionMask()
        i0start = ddict['Dim 0']['offset']
        i0end = i0start + ddict['Dim 0']['width']
        i1start = ddict['Dim 1']['offset']
        i1end = i1start + ddict['Dim 1']['width']
        mask[:,:] = 0
        mask[i0start:i0end, i1start:i1end] = 1
        self.imageBrowser.setSelectionMask(mask)

class FFTAlignmentDialog(qt.QDialog):
    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("FFT Alignment Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.parametersWidget = FFTAlignmentWindow(self)
        self.mainLayout.addWidget(self.parametersWidget)
        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(0)
        self.okButton = qt.QPushButton(hbox)
        self.okButton.setText("OK")
        self.okButton.setAutoDefault(False)
        self.dismissButton = qt.QPushButton(hbox)
        self.dismissButton.setText("Cancel")
        self.dismissButton.setAutoDefault(False)
        hboxLayout.addWidget(self.okButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.dismissButton)
        self.mainLayout.addWidget(hbox)
        self.dismissButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)
        self.setStack = self.parametersWidget.setStack
        self.setDummyStack()

    def setDummyStack(self):
        dummyStack = numpy.arange(2 * 128 *256)
        dummyStack = dummyStack.reshape(2, 128, 256)
        self.setStack(dummyStack, index=0)

    def getParameters(self):
        return self.parametersWidget.getParameters()

    def accept(self):
        parameters = self.getParameters()
        if parameters['file_use']:
            if not len(parameters['file_name']):
                qt.QMessageBox.information(self,
                                           "Missing valid file name",
                        "Please provide a valid output file name")
                return
        shape = parameters['shape']
        for i in range(len(shape)):
            key = "Dim %d" % i
            offset = parameters[key]['offset']
            width = parameters[key]['width']
            if (offset + width) > shape[i]:
                qt.QMessageBox.information(self, "Check window",
                        "Inconsistent limits on dimension %d" % i)
                return
        return qt.QDialog.accept(self)

    def reject(self):
        self.setDummyStack()
        return qt.QDialog.reject(self)

    def closeEvent(self, ev):
        self.setDummyStack()
        return qt.QDialog.closeEvent(self, ev)

if __name__ == "__main__":
    #create a dummy stack
    nrows = 100
    ncols = 200
    nchannels = 1024
    a = numpy.ones((nrows, ncols), numpy.float64)
    stackData = numpy.zeros((nrows, ncols, nchannels), numpy.float64)
    for i in range(nchannels):
        stackData[:, :, i] = a * i

    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    w = FFTAlignmentDialog()
    w.setStack(stackData, index=0)
    w.exec()
