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
import os
import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import ExternalImagesWindow
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
import pyopencl
import silx.opencl
from silx.image import sift

DEBUG = 0

if DEBUG:
    print("SIFT coming from %s" % os.path.abspath(sift.__file__))

__doc__ = """The SIFT algorithm belongs to the University of British Columbia. It is
protected by patent US6711293. If you are in a country where this patent
applies (like the USA), please check if you are allowed to use it. The
University of British Columbia does not require a license for its use for
non-commercial research applications.

This SIFT implementation uses the code developed by Jerome Kieffer and
Pierre Paleo. The project is hosted at:

https://github.com/silx-kit/silx/tree/master/silx/opencl/sift

This algorithm should provide better results than FFT based algorithms
provided the images to be aligned provide enough registration points
(or common "features").

You can restrict the region of the images to be used by drawing a mask.

If you do not find any device listed under OpenCL devices that could mean
you do not have any OpenCL driver installed in your system.

Windows users can at least install the CPU OpenCL drivers from AMD.
You can easily find them searching the internet for AMD Accelerated Parallel
Processing SDK.

Mac users should have OpenCL provided with their operating system.

Linux users probably need to install PyMca as provided by their distribution.
Please note that introduces an additional dependency of PyMca on PyOpenCL.

sift_pyocl license follows:

Copyright (C) 2013-2017  European Synchrotron Radiation Facility, Grenoble, France

 Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""

class ParametersWidget(qt.QWidget):
    parametersWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, ndim=2):
        qt.QWidget.__init__(self, parent)
        self._nDimensions = 2
        self._shape = 3000, 3000
        self._settingShape = False
        self._build()
        devices = self.getOpenCLDevices()
        if len(devices):
            self.deviceSelector.clear()
            for device in devices:
                self.deviceSelector.addItem("(%d, %d) %s" % (device[0], device[1], device[2]))

    def _build(self):
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        #self.aboutSiftButton = qt.QPushButton(self)
        #self.aboutSiftButton.setText("Please read prior to use!")
        #self.aboutSiftButton.clicked.connect(self._showInfo)
        # info
        self._infoDocument = qt.QTextEdit()
        self._infoDocument.setReadOnly(True)
        self._infoDocument.setMaximumHeight(150)
        self._infoDocument.setText(__doc__)
        #self._infoDocument.hide()
        label = qt.QLabel(self)
        label.setText("OpenCL Device:")
        self.deviceSelector = qt.QComboBox(self)
        self.deviceSelector.addItem("(-1, -1) No OpenCL device found")
        #self.mainLayout.addWidget(self.aboutSiftButton, 0, 0, 1, 2)
        self.mainLayout.addWidget(self._infoDocument, 0, 0, 2, 2)
        self.mainLayout.addWidget(label, 2, 0)
        self.mainLayout.addWidget(self.deviceSelector, 2, 1)

    def emitParametersWidgetSignal(self, event="ParametersChanged"):
        ddict = self.getParameters()
        ddict['event'] = "ParametersChanged"
        self.parametersWidgetSignal.emit(ddict)

    def _showInfo(self):
        if self._infoDocument.isHidden():
            self._infoDocument.show()
        else:
            self._infoDocument.hide()

    def getOpenCLDevices(self):
        devices = []
        if silx.opencl.ocl is not None:
            for platformid, platform in enumerate(silx.opencl.ocl.platforms):
                for deviceid, dev in enumerate(platform.devices):
                    devices.append((platformid, deviceid, dev.name))
        return devices

    def getParameters(self):
        txt = str(self.deviceSelector.currentText()).split(")")[0]
        txt = txt[1:].split(",")
        device = (int(txt[0]), int(txt[1]))
        return {'opencl_device':device}

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


class SIFTAlignmentWindow(qt.QWidget):
    def __init__(self, parent=None, stack=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("SIFT Alignment")
        self._build()

    def _build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        self.parametersWidget = ParametersWidget(self)
        self.outputFileWidget = OutputFile(self)
        self.imageBrowser = ExternalImagesWindow.ExternalImagesWindow(self,
                                                    crop=False,
                                                    selection=True,
                                                    imageicons=True)
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
        #shape = self.imageBrowser.getImageData().shape
        #self.parametersWidget.setShape(shape)
        #ddict = self.parametersWidget.getParameters()
        #self.mySlot(ddict)

    def getParameters(self):
        parameters = self.parametersWidget.getParameters()
        parameters['reference_image'] = self.imageBrowser.getImageData()
        parameters.update(self.outputFileWidget.getParameters())
        parameters['reference_index'] = self.imageBrowser.getCurrentIndex()
        parameters['mask'] = self.imageBrowser.getSelectionMask()
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

class SIFTAlignmentDialog(qt.QDialog):
    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("SIFT Alignment Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.parametersWidget = SIFTAlignmentWindow(self)
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
        self.setSelectionMask = self.parametersWidget.imageBrowser.setSelectionMask
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
    w = SIFTAlignmentDialog()
    w.setStack(stackData, index=0)
    ret = w.exec()
    if ret:
        print(w.getParameters())
