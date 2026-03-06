#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019 European Synchrotron Radiation Facility
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
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
from PyMca5.PyMcaIO.OutputBuffer import OutputBuffer as OutputBufferBase


class OutputBuffer(OutputBufferBase):

    def __init__(self, saveResiduals=False, saveFit=False, saveData=False,
                 diagnostics=False, saveFOM=False, **kwargs):
        super(OutputBuffer, self).__init__(**kwargs)
        self.fileProcessDefault = 'xrf_fit'
        self._defaultgroups = 'molarconcentrations', 'massfractions', 'parameters'
        self._defaultorder = 'molarconcentrations', 'massfractions', 'parameters', 'uncertainties'
        self._optionalimage = 'chisq',

        self.saveResiduals = saveResiduals
        self.saveFit = saveFit
        self.saveData = saveData
        self.saveFOM = saveFOM
        if not self.diagnostics:
            # None of the above diagnostics
            # are enabled specifically
            self.diagnostics = diagnostics
        self.labelFormat('uncertainties', 's')
        self.labelFormat('massfractions', 'w')
        self.labelFormat('molarconcentrations', 'mM')

    @property
    def saveFOM(self):
        # For all non-hdf5 formats: FOM needs to be in
        # self._optionalimage to be saved
        return self._saveFOM

    @saveFOM.setter
    def saveFOM(self, value):
        self._checkBufferContext()
        self._saveFOM = value

    @property
    def saveData(self):
        return self._saveData and self.h5

    @saveData.setter
    def saveData(self, value):
        self._checkBufferContext()
        self._saveData = value

    @property
    def saveFit(self):
        return self._saveFit and self.h5

    @saveFit.setter
    def saveFit(self, value):
        self._checkBufferContext()
        self._saveFit = value

    @property
    def saveResiduals(self):
        return self._saveResiduals and self.h5

    @saveResiduals.setter
    def saveResiduals(self, value):
        self._checkBufferContext()
        self._saveResiduals = value

    @property
    def saveDataDiagnostics(self):
        return self.saveResiduals or self.saveFit or self.saveData

    @property
    def diagnostics(self):
        return self.saveDataDiagnostics or self.saveFOM

    @diagnostics.setter
    def diagnostics(self, value):
        self.saveResiduals = value
        self.saveFit = value
        self.saveData = value
        self.saveFOM = value
