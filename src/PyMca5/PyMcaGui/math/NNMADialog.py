#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import numpy
import time
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.misc import CalculationThread
from . import NNMAWindow
NNMA = True


_logger = logging.getLogger(__name__)


class NNMADialog(qt.QDialog):
    def __init__(self, parent=None, rgbwidget=None, selection=False):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("NNMA calculation dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.calculateButton = qt.QPushButton(self)
        self.calculateButton.setAutoDefault(False)
        self.calculateButton.setText("Perform NNMA")
        self.showLastButton = qt.QPushButton(self)
        self.showLastButton.setAutoDefault(False)
        self.showLastButton.setText("Last Results")
        self.mainLayout.addWidget(self.calculateButton)
        self.mainLayout.addWidget(self.showLastButton)
        self._data = None

        self.nnmaWindow = NNMAWindow.NNMAWindow(parent = None,
                                            rgbwidget=rgbwidget,
                                            #selection=True,
                                            selection=selection,
                                            colormap=True,
                                            #imageicons=True,
                                            imageicons=selection,
                                            standalonesave=True)
        self.nnmaWindow.setDefaultColormap(0, logflag=False)
        self.nnmaParametersDialog = None
        self.nnmaWindow.hide()

        #connections
        self.calculateButton.clicked.connect(self._calculateSlot)
        self.showLastButton.clicked.connect(self._showLastSlot)

    def sizeHint(self):
        return qt.QSize(int(4*qt.QDialog.sizeHint(self).width()),
                        qt.QDialog.sizeHint(self).height())

    def _calculateSlot(self):
        if self._data is None:
            msg = qt.QMessageBox(self)
            msg.setWindowTitle("No data")
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("No data to perform calculation")
            msg.exec()
            return

        if self.nnmaParametersDialog is None:
            self.nnmaParametersDialog = NNMAWindow.NNMAParametersDialog(self)
            self.nnmaParametersDialog.nPC.setMaximum(self._spectrumLength)
            self.nnmaParametersDialog.nPC.setValue(min(10, self._spectrumLength))
            ddict = {'options':self._binningOptions, 'binning': 1, 'method': 0}
            self.nnmaParametersDialog.setParameters(ddict)
        ret = self.nnmaParametersDialog.exec()
        if ret:
            t0 = time.time()
            nnmaParameters = self.nnmaParametersDialog.getParameters()
            self.nnmaParametersDialog.close()
            function = nnmaParameters['function']
            binning = nnmaParameters['binning']
            npc = nnmaParameters['npc']
            kw = nnmaParameters['kw']
            data = self._data
            old_shape = self._data.shape
            if _logger.getEffectiveLevel() == logging.DEBUG:
                images, eigenvalues, eigenvectors = function(data,
                                                             npc,
                                                             binning=binning,
                                                             **kw)
            else:
                try:
                    threadResult = self._submitThread(function,
                                                         data,
                                                         npc,
                                                         binning=binning,
                                                         **kw)
                    if type(threadResult) == type((1,)):
                        if len(threadResult):
                            if hasattr(threadResult[0], "startswith"):
                                if threadResult[0].startswith("Exception"):
                                    raise Exception(threadResult[1],
                                                threadResult[2])
                    images, eigenvalues, eigenvectors = threadResult
                except Exception:
                    if isinstance(data, numpy.ndarray):
                        self._data = self._data.reshape(*old_shape)
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("%s" % sys.exc_info()[1])
                    msg.exec()
                    return
            if isinstance(self._data, numpy.ndarray):
                self._data = self._data.reshape(old_shape)
            _logger.debug("NNMA Elapsed = %s", time.time() - t0)
            self.nnmaWindow.setPCAData(images,
                                       eigenvalues,
                                       eigenvectors)
            self.nnmaWindow.show()
            self.nnmaWindow.raise_()


    def _showLastSlot(self):
        self.nnmaWindow.show()
        self.nnmaWindow.raise_()

    def setData(self, data=None, spectrumindex=-1):
        if type(data) == type([]):
            #assume is an image list
            if data[0].dtype not in [numpy.float32, numpy.float64]:
                dtype = numpy.float64
            else:
                dtype = data[0].dtype
            self._spectrumLength = len(data)
            self._shape = data[0].shape
            n = 1
            for shape in self._shape:
                n *= shape
            self._binningOptions = [1]
            if len(self._shape) == 1:
                self._data = numpy.zeros((self._shape[0],
                                          self._spectrumLength), dtype)
                for i in range(self._spectrumLength):
                    self._data[:, i] = data[i][:]
            elif len(self._shape) == 2:
                self._data = numpy.zeros((self._shape[0],
                                          self._shape[1],
                                          self._spectrumLength), dtype)
                for i in range(self._spectrumLength):
                    self._data[:, :, i] = data[i][:,:]
        else:
            self._shape = data.shape
            self._data = data
            self._spectrumLength = self._shape[spectrumindex]
            self._binningOptions=[1]
            for number in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19]:
                if (self._spectrumLength % number) == 0:
                    self._binningOptions.append(number)
        if self.nnmaParametersDialog is not None:
            self.nnmaParametersDialog.nPC.setMaximum(self._spectrumLength)
            self.nnmaParametersDialog.nPC.setValue(min(10, self._spectrumLength))

    def _submitThread(self, function, *var, **kw):
        message = "Please Wait: NNMA Going On"
        thread = CalculationThread.CalculationThread(
                                      calculation_method=function,
                                      calculation_vars = var,
                                      calculation_kw = kw,
                                      expand_vars=True,
                                      expand_kw=True)
        thread.start()
        CalculationThread.waitingMessageDialog(thread,
                                              message=message,
                                              parent=self,
                                              modal=True,
                                              update_callback=None,
                                              frameless=True)
        threadResult = thread.getResult()
        self.raise_()        
        return threadResult

if __name__ == "__main__":
    import os
    from PyMca5.PyMcaIO import EdfFile
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    d = NNMADialog()
    imageList = []
    for t in ["mix1.edf", "mix2.edf", "mix3.edf"]:
        fname = os.path.join(os.path.dirname(__file__), "tests", t)
        if not os.path.exists(fname):
            break
        edf = EdfFile.EdfFile(fname)
        data = edf.GetData(0)
        edf = None
        imageList.append(data)
    if len(imageList):
        d.setData(imageList)
    d.show()
    app.exec()
