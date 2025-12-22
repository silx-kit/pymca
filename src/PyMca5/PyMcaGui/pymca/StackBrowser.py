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
import logging
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaGui.misc import FrameBrowser
from PyMca5.PyMcaCore import DataObject
qt = MaskImageWidget.qt
IconDict = MaskImageWidget.IconDict

_logger = logging.getLogger(__name__)


class StackBrowser(MaskImageWidget.MaskImageWidget):
    def __init__(self, *var, **kw):
        ddict = {}
        ddict['usetab'] = kw.get("usetab", False)
        ddict['aspect'] = kw.get("aspect", True)
        ddict.update(kw)
        ddict['standalonesave'] = True
        MaskImageWidget.MaskImageWidget.__init__(self, *var, **ddict)
        self.setWindowTitle("Stack Browser")
        self.dataObjectsList = []
        self.dataObjectsDict = {}

        self.nameBox = qt.QWidget(self)
        self.nameBox.mainLayout = qt.QHBoxLayout(self.nameBox)

        self.nameLabel = qt.QLabel(self.nameBox)
        self.nameLabel.setText("Image Name = ")
        self.name = qt.QLineEdit(self.nameBox)
        self.nameBox.mainLayout.addWidget(self.nameLabel)
        self.nameBox.mainLayout.addWidget(self.name)

        self.roiWidthLabel = qt.QLabel(self.nameBox)
        self.roiWidthLabel.setText("Width = ")
        self.roiWidthSpin = qt.QSpinBox(self.nameBox)
        self.roiWidthSpin.setMinimum(1)
        self.roiWidthSpin.setMaximum(9999)
        self.roiWidthSpin.setValue(1)
        self.roiWidthSpin.setSingleStep(2)
        self.nameBox.mainLayout.addWidget(self.roiWidthLabel)
        self.nameBox.mainLayout.addWidget(self.roiWidthSpin)

        self.slider = FrameBrowser.HorizontalSliderWithBrowser(self)
        self.slider.setRange(0, 0)

        self.mainLayout.addWidget(self.nameBox)
        self.mainLayout.addWidget(self.slider)
        self.roiWidthSpin.valueChanged[int].connect(self._roiWidthSlot)
        self.slider.valueChanged[int].connect(self._showImageSliderSlot)
        self.name.editingFinished[()].connect(self._nameSlot)

        self.backgroundIcon = qt.QIcon(qt.QPixmap(IconDict["subtract"]))
        infotext  = 'Toggle background image subtraction from current image\n'
        infotext += 'No action if no background image available.'
        self.backgroundIcon = qt.QIcon(qt.QPixmap(IconDict["subtract"]))
        self.backgroundButton = self.graphWidget._addToolButton(\
                                    self.backgroundIcon,
                                    self.subtractBackground,
                                    infotext,
                                    toggle = True,
                                    state = False,
                                    position = 6)

        self._backgroundSubtraction = False
        self.slider.hide()
        self.buildAndConnectImageButtonBox(replace=True)

    def setBackgroundImage(self, image=None):
        self._backgroundImage = image
        if self._backgroundSubtraction:
            self.subtractBackground()

    def setStackDataObject(self, stack, index=None, stack_name=None):
        if hasattr(stack, "info") and hasattr(stack, "data"):
            dataObject = stack
        else:
            dataObject = DataObject.DataObject()
            dataObject.info = {}
            dataObject.data = stack
        if dataObject.data is None:
            return
        if stack_name is None:
            legend = dataObject.info.get('SourceName', "Stack")
        else:
            legend = stack_name
        if index is None:
            mcaIndex = dataObject.info.get('McaIndex', 0)
        else:
            mcaIndex = index
        shape = dataObject.data.shape
        self.dataObjectsList = [legend]
        self.dataObjectsDict = {legend:dataObject}
        self._browsingIndex = mcaIndex
        if mcaIndex == 0:
            if len(shape) == 2:
                self._nImages = 1
                self.setImageData(dataObject.data)
                self.slider.hide()
                self.name.setText(legend)
            else:
                self._nImages = 1
                for dimension in dataObject.data.shape[:-2]:
                    self._nImages *= dimension
                #This is a problem for dynamic data
                #dataObject.data.shape = self._nImages, shape[-2], shape[-1]
                data = self._getImageDataFromSingleIndex(0)
                self.setImageData(data)
                self.slider.setRange(0, self._nImages - 1)
                self.slider.setValue(0)
                self.slider.show()
                self.name.setText(legend+" 0")
        elif mcaIndex in [len(shape)-1, -1]:
            mcaIndex = -1
            self._browsingIndex = mcaIndex
            if len(shape) == 2:
                self._nImages = 1
                self.setImageData(dataObject.data)
                self.slider.hide()
                self.name.setText(legend)
            else:
                self._nImages = 1
                for dimension in dataObject.data.shape[2:]:
                    self._nImages *= dimension
                #This is a problem for dynamic data
                #dataObject.data.shape = self._nImages, shape[-2], shape[-1]
                data = self._getImageDataFromSingleIndex(0)
                self.setImageData(data)
                self.slider.setRange(0, self._nImages - 1)
                self.slider.setValue(0)
                self.slider.show()
                self.name.setText(legend+" 0")
        else:
            raise ValueError("Unsupported 1D index %d"  % mcaIndex)
        if self._nImages > 1:
            self.showImage(0)
        else:
            self.plotImage()

    def subtractBackground(self):
        if self.backgroundButton.isChecked():
            self._backgroundSubtraction = True
        else:
            self._backgroundSubtraction = False
        index = self.slider.value()
        self._showImageSliderSlot(index)

    def _roiWidthSlot(self, width):
        index = self.slider.value()
        self._showImageSliderSlot(index)

    def _getImageDataFromSingleIndex(self, index, width=None, background=None):
        if width is None:
            width = int(0.5*(self.roiWidthSpin.value() - 1))
        if width < 1:
            width = 0
        if background is None:
            background = self._backgroundSubtraction
        if not len(self.dataObjectsList):
            _logger.debug("nothing to show")
            return
        legend = self.dataObjectsList[0]
        if type(legend) == type([]):
            legend = legend[index]
        dataObject = self.dataObjectsDict[legend]
        shape = dataObject.data.shape
        if len(shape) == 2:
            if index > 0:
                raise IndexError("Only one image in stack")
            return dataObject.data
        if self._browsingIndex == 0:
            if len(shape) == 3:
                if width < 1:
                    data = dataObject.data[index:index+1,:,:]
                    data = data.reshape(*data.shape[1:])
                else:
                    i0 = index - width
                    i1 = index + width + 1
                    i0 = max(i0, 0)
                    i1 = min(i1, shape[0])
                    if background:
                        data = dataObject.data[i0:i1,:,:]
                        backgroundData = 0.5*(i1-i0)*\
                                     (data[0, :, :]+data[-1, :,:])
                        data = data.sum(axis=0) - backgroundData
                    else:
                        data = dataObject.data[i0:i1,:,:].sum(axis=0)
                    data /= float(i1-i0)
                return data
            #I have to deduce the appropriate indices from the given index
            #always assuming C order
            acquisitionShape =  dataObject.data.shape[:-2]
            if len(shape) == 4:
                if width < 1:
                    j = index % acquisitionShape[-1]
                    i = int(index/(acquisitionShape[-1]*acquisitionShape[-2]))
                    return dataObject.data[i, j]
                else:
                    npoints = (acquisitionShape[-1]*acquisitionShape[-2])
                    i0 = max(index - width, 0)
                    i1 = min(index + width + 1, npoints)
                    for tmpIndex in range(i0, i1):
                        j = tmpIndex % acquisitionShape[-1]
                        i = int(index/npoints)
                        if tmpIndex == i0:
                            data = dataObject.data[i, j]
                            backgroundData = data * 1
                        elif tmpIndex == (i1-1):
                            tmpData = dataObject.data[i, j]
                            backgroundData = 0.5*(i1-i0)*\
                                     (background+tmpData)
                            data += tmpData
                        else:
                            data += dataObject.data[i, j]
                    if background:
                        data -= backgroundData
                    data /= float(i1-i0)
                    return data
        elif self._browsingIndex == -1:
            if len(shape) == 3:
                if width < 1:
                    data = dataObject.data[:,:,index:index+1]
                    data = data.reshape(data.shape[0], data.shape[1])
                else:
                    i0 = index - width
                    i1 = index + width + 1
                    i0 = max(i0, 0)
                    i1 = min(i1, shape[-1])
                    if background:
                        data = dataObject.data[:,:,i0:i1]
                        backgroundData = 0.5*(i1-i0)*\
                                     (data[:, :,  0]+data[:,:,-1])
                        data = data.sum(axis=-1) - backgroundData
                    else:
                        data = dataObject.data[:,:,i0:i1].sum(axis=-1)
                    data /= float(i1-i0)
                return data
        raise IndexError("Unhandled dimension")

    def _showImageSliderSlot(self, index):
        self.showImage(index, moveslider=False)

    def _nameSlot(self):
        txt = str(self.name.text())
        if len(txt):
            self.graphWidget.graph.setGraphTitle(txt)
        else:
            self.name.setText(self.graphWidget.graph.getTitle())

    def _buildTitle(self, legend, index):
        width = int(0.5*(self.roiWidthSpin.value() - 1))
        if width < 1:
            title = "%s %d" % (legend, index)
        else:
            title = "%s average %d to %d" % (legend, index - width, index + width)
        if self._backgroundSubtraction:
            title += " Net"
        return title

    def showImage(self, index=0, moveslider=True):
        if not len(self.dataObjectsList):
            return
        legend = self.dataObjectsList[0]
        dataObject = self.dataObjectsDict[legend]
        data = self._getImageDataFromSingleIndex(index)
        txt = self._buildTitle(legend, index)
        self.graphWidget.graph.setGraphTitle(txt)
        self.name.setText(txt)
        if self._backgroundSubtraction and (self._backgroundImage is not None):
            self.setImageData(data - self._backgroundImage)
        else:
            self.setImageData(data, clearmask=False)
        if moveslider:
            self.slider.setValue(index)
        self.updateProfileSelectionWindow()

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
    w = StackBrowser()
    w.setStackDataObject(stackData, index=0)
    w.show()
    app.exec()
