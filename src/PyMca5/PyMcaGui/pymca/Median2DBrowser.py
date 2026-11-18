#/*##########################################################################
# Copyright (C) 2004-2019 V.A. Sole, European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import numpy
import logging
_logger = logging.getLogger(__name__)

try:
    from PyMca5.PyMcaGui.pymca import StackBrowser
    from PyMca5.PyMcaMath.PyMcaSciPy.signal import median
except ImportError:
    _logger.warning("Median2DBrowser problem!")
    import traceback
    print(traceback.format_exc())


medfilt2d = median.medfilt2d
qt = StackBrowser.qt

class MedianParameters(qt.QWidget):
    def __init__(self, parent=None, use_conditional=False):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.label = qt.QLabel(self)
        self.label.setText("Median filter width: ")
        self.widthSpin = qt.QSpinBox(self)
        self.widthSpin.setMinimum(1)
        self.widthSpin.setMaximum(99)
        self.widthSpin.setValue(1)
        self.widthSpin.setSingleStep(2)
        if use_conditional:
            self.conditionalLabel = qt.QLabel(self)
            self.conditionalLabel.setText("Conditional:")
            self.conditionalSpin = qt.QSpinBox(self)
            self.conditionalSpin.setMinimum(0)
            self.conditionalSpin.setMaximum(1)
            self.conditionalSpin.setValue(0)
        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.widthSpin)
        if use_conditional:
            self.mainLayout.addWidget(self.conditionalLabel)
            self.mainLayout.addWidget(self.conditionalSpin)

class Median2DBrowser(StackBrowser.StackBrowser):
    def __init__(self, *var, **kw):
        StackBrowser.StackBrowser.__init__(self, *var, **kw)
        self.setWindowTitle("Image Browser with Median Filter")
        # all the images would be added without the median filter
        self.addAllImageButton.hide()
        self._medianParameters = {'use':True,
                                  'row_width':5,
                                  'column_width':5,
                                  'conditional':0}
        self._medianParametersWidget = MedianParameters(self,
                                                        use_conditional=1)
        self._medianParametersWidget.widthSpin.setValue(5)
        self.layout().addWidget(self._medianParametersWidget)
        self._medianParametersWidget.widthSpin.valueChanged[int].connect( \
                     self.setKernelWidth)
        self._medianParametersWidget.conditionalSpin.valueChanged[int].connect(\
                     self.setConditionalFlag)

    def setKernelWidth(self, value):
        kernelSize = numpy.asarray(value)
        if not (int(value) % 2):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Median filter error")
            msg.setText("One odd values accepted")
            msg.exec()
            return
        if len(kernelSize.shape) == 0:
            kernelSize = [kernelSize.item()] * 2
        self._medianParameters['row_width'] = kernelSize[0]
        self._medianParameters['column_width'] = kernelSize[1]
        self._medianParametersWidget.widthSpin.setValue(int(kernelSize[0]))
        current = self.slider.value()
        self.showImage(current, moveslider=False)

    def setConditionalFlag(self, value):
        self._medianParameters['conditional'] = int(value)
        self._medianParametersWidget.conditionalSpin.setValue(int(value))
        current = self.slider.value()
        self.showImage(current, moveslider=False)

    def _buildTitle(self, legend, index):
        a = self._medianParameters['row_width']
        b = self._medianParameters['column_width']
        title = StackBrowser.StackBrowser._buildTitle(self, legend, index)
        if max(a, b) > 1:
            if self._medianParameters['conditional'] == 0:
                return "Median Filter (%d,%d) of %s" % (a, b, title)
            else:
                return "Conditional Median Filter (%d,%d) of %s" % (a, b, title)
        else:
            return title

    def showImage(self, index=0, moveslider=True):
        if not len(self.dataObjectsList):
            return
        legend = self.dataObjectsList[0]
        dataObject = self.dataObjectsDict[legend]
        data = self._getImageDataFromSingleIndex(index)
        if self._backgroundSubtraction and (self._backgroundImage is not None):
            self.setImageData(data - self._backgroundImage)
        else:
            self.setImageData(data, clearmask=False)
        txt = self._buildTitle(legend, index)
        self.graphWidget.graph.setGraphTitle(txt)
        self.name.setText(txt)
        if moveslider:
            self.slider.setValue(index)

    def setImageData(self, data, **kw):
        if self._medianParameters['use']:
            if max(self._medianParameters['row_width'],
                   self._medianParameters['column_width']) > 1:
                conditional = self._medianParameters['conditional']
                data = medfilt2d(data,[self._medianParameters['row_width'],
                                 self._medianParameters['column_width']],
                                 conditional=conditional)
        # this method is in fact of MaskImageWidget
        StackBrowser.StackBrowser.setImageData(self, data, **kw)

if __name__ == "__main__":
    #create a dummy stack
    nrows = 100
    ncols = 200
    nchannels = 1024
    a = numpy.ones((nrows, ncols), numpy.float64)
    stackData = numpy.zeros((nrows, ncols, nchannels), numpy.float64)
    for i in range(nchannels):
        if i % 10:
            stackData[:, :, i] = a * i
        else:
            stackData[:, :, i] = 10 * a * i

    app = qt.QApplication([])
    app.lastWindowClosed[()].connect(app.quit)
    w = Median2DBrowser()
    w.setStackDataObject(stackData, index=0)
    w.show()
    app.exec()
