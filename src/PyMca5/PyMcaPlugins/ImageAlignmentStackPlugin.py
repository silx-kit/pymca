#/*##########################################################################
# Copyright (C) 2004-2024 European Synchrotron Radiation Facility
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
"""
This plugin provides two methods to align stack images, one based on a FFT
algorithm and the other one based on the SIFT algorithm (on GPU).

The result of the alignment computation may be applied directly to the data,
or saved to a file.

This plugin also allows to apply the results from a file.
"""
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import os
import numpy
import logging
from PyMca5 import StackPluginBase
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui import FFTAlignmentWindow
from PyMca5.PyMcaMath import ImageRegistration
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaGui.misc import CalculationThread
from PyMca5.PyMcaIO import ArraySave
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaIO import specfilewrapper
from PyMca5.PyMcaGui import HDF5Widget

_logger = logging.getLogger(__name__)

try:
    from PyMca5.PyMcaGui.math import SIFTAlignmentWindow
    sift = SIFTAlignmentWindow.sift
    ocl = SIFTAlignmentWindow.silx.opencl.ocl
    SIFT = True
except Exception:
    _logger.info("SIFTAlignmentWindow not successful")
    SIFT = False

try:
    import h5py
    HDF5 = True
except Exception:
    HDF5 = False


class ImageAlignmentStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {'FFT Alignment':[self._fftAlignment,
                                            "Align using FFT",
                                            None]}
        self.__methodKeys = ['FFT Alignment']
        if SIFT:
            key = 'SIFT Alignment'
            self.methodDict[key] = [self._siftAlignment,
                                    "Align using SIFT Algorithm",
                                    None]
            self.__methodKeys.append(key)
        key = 'From File Alignment'
        self.methodDict[key] = [self._shiftFromFile,
                                "Align using shifts from file",
                                None]
        self.__methodKeys.append(key)
        self.widget = None

    def stackUpdated(self):
        self.widget = None

    #Methods implemented by the plugin
    def getMethods(self):
        return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    def _fftAlignment(self):
        stack = self.getStackDataObject()
        if stack is None:
            return
        mcaIndex = stack.info.get('McaIndex')
        if not (mcaIndex in [0, -1, 2]):
            raise IndexError("1D index must be 0, 2, or -1")

        if self.widget is None:
            self.widget = FFTAlignmentWindow.FFTAlignmentDialog()
        self.widget.setStack(stack)
        ret = self.widget.exec()
        if ret:
            ddict = self.widget.getParameters()
            self.widget.setDummyStack()
            offsets = [ddict['Dim 0']['offset'], ddict['Dim 1']['offset']]
            widths = [ddict['Dim 0']['width'], ddict['Dim 1']['width']]
            if mcaIndex == 0:
                reference = stack.data[ddict['reference_index']]
            else:
                reference = ddict['reference_image']
            crop = False
            if ddict['file_use']:
                filename = ddict['file_name']
            else:
                filename = None
            if filename is not None:
                self.__hdf5 = self.initializeHDF5File(filename)

            if _logger.getEffectiveLevel() == logging.DEBUG:
                shifts = self.calculateShiftsFFT(stack,
                                                 reference,
                                                 offsets=offsets,
                                                 widths=widths,
                                                 crop=crop)
                result = self.shiftStack(stack,
                                         shifts,
                                         crop=crop,
                                         filename=filename)
            else:
                result = self.__calculateShiftsFFT(stack,
                                                   reference,
                                                   offsets=offsets,
                                                   widths=widths,
                                                   crop=crop)
                # result[0] contains the string "Exception" in case
                # of error. However, direct comparison will raise an
                # error
                if isinstance(result[0], str):
                    if result[0] == 'Exception':
                        # exception occurred
                        raise Exception(result[1], result[2], result[3])
                else:
                    shifts = result
                result = self.__shiftStack(stack,
                                           shifts,
                                           crop=crop,
                                           filename=filename)
                if result is not None:
                    # exception occurred
                    raise Exception(result[1], result[2], result[3])
            if filename is not None:
                hdf = self.__hdf5
                alignmentGroup = hdf['/entry_000/Alignment']
                outputShifts = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                     shape=(stack.data.shape[mcaIndex], 2),
                                                     name="shifts",
                                                     dtype=numpy.float32)
                outputShifts[:,:] = shifts
                attributes={'interpretation':'image'}
                referenceFrame = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                     shape=reference.shape,
                                                     name="reference_frame",
                                                     dtype=numpy.float32,
                                                     attributes=attributes)
                referenceFrame[:,:] = reference[:,:]
                maskFrame = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                   shape=reference.shape,
                                                   name="reference_mask",
                                                   dtype=numpy.uint8,
                                                   attributes=attributes)

                maskData = numpy.zeros(reference.shape, dtype=numpy.uint8)
                maskData[offsets[0]:offsets[0] + widths[0], offsets[1] : offsets[1] + widths[1]] = 1
                maskFrame[:,:] = maskData[:,:]
                # fill the axes information
                dataGroup = hdf['/entry_000/Data']
                try:
                    activeCurve = self.getActiveCurve()
                    if activeCurve is None:
                        activeCurve = self.getAllCurves()[0]
                    x, y, legend, info = activeCurve
                    dataGroup[info['xlabel']] = numpy.array(x, dtype=numpy.float32)
                    dataGroup[info['xlabel']].attrs['axis'] = numpy.int32(1)
                    axesAttribute = '%s:dim_1:dim_2' % info['xlabel']
                except Exception:
                    if _logger.getEffectiveLevel() == logging.DEBUG:
                        raise
                    dataGroup['dim_0'] = numpy.arange(stack.data.shape[mcaIndex]).astype(numpy.float32)
                    dataGroup['dim_0'].attrs['axis'] = numpy.int32(1)
                    axesAttribute = 'dim_0:dim_1:dim_2'
                dataGroup['dim_1'] = numpy.arange(reference.shape[0]).astype(numpy.float32)
                dataGroup['dim_1'].attrs['axis'] = numpy.int32(2)
                dataGroup['dim_2'] = numpy.arange(reference.shape[1]).astype(numpy.float32)
                dataGroup['dim_2'].attrs['axis'] = numpy.int32(3)
                dim2 = numpy.arange(reference.shape[1]).astype(numpy.float32)
                dataGroup['data'].attrs['axes'] = axesAttribute
                self.finishHDF5File(hdf)
            else:
                self.setStack(stack)

    def __calculateShiftsFFT(self, *var, **kw):
        self._progress = 0.0
        thread = CalculationThread.CalculationThread(\
                calculation_method=self.calculateShiftsFFT,
                calculation_vars=var,
                calculation_kw=kw)
        thread.start()
        CalculationThread.waitingMessageDialog(thread,
                                               message="Please wait. Calculation going on.",
                                               parent=self.widget,
                                               modal=True,
                                               update_callback=self._waitingCallback)
        return thread.result

    def __shiftStack(self, *var, **kw):
        self._progress = 0.0
        thread = CalculationThread.CalculationThread(\
                calculation_method=self.shiftStack,
                calculation_vars=var,
                calculation_kw=kw)
        thread.start()
        CalculationThread.waitingMessageDialog(thread,
                                               message="Please wait. Calculation going on.",
                                               parent=self.widget,
                                               modal=True,
                                               update_callback=self._waitingCallback)
        return thread.result


    def __calculateShiftsSIFT(self, *var, **kw):
        self._progress = 0.0
        thread = CalculationThread.CalculationThread(\
                calculation_method=self.calculateShiftsSIFT,
                calculation_vars=var,
                calculation_kw=kw)
        thread.start()
        CalculationThread.waitingMessageDialog(thread,
                                               message="Please wait. Calculation going on.",
                                               parent=self.widget,
                                               modal=True,
                                               update_callback=self._waitingCallback)
        return thread.result

    def _waitingCallback(self):
        ddict = {}
        ddict['message'] = "Calculation Progress = %d %%" % self._progress
        return ddict

    def _siftAlignment(self):
        if not SIFT:
            try:
                import pyopencl
            except Exception:
                raise ImportError("PyOpenCL does not seem to be installed on your system")
        if ocl is None:
            raise ImportError("PyOpenCL does not seem to be installed on your system")
        stack = self.getStackDataObject()
        if stack is None:
            return
        mcaIndex = stack.info.get('McaIndex')
        if not (mcaIndex in [0, 2, -1]):
            raise IndexError("Unsupported 1D index %d" % mcaIndex)
        widget = SIFTAlignmentWindow.SIFTAlignmentDialog()
        widget.setStack(stack)
        mask = self.getStackSelectionMask()
        widget.setSelectionMask(mask)
        ret = widget.exec()
        if ret:
            ddict = widget.getParameters()
            widget.setDummyStack()
            reference = ddict['reference_image']
            mask = ddict['mask']
            if ddict['file_use']:
                filename = ddict['file_name']
            else:
                filename = None
            if filename is not None:
                self.__hdf5 = self.initializeHDF5File(filename)
            crop = False
            device = ddict['opencl_device']
            if _logger.getEffectiveLevel() == logging.DEBUG:
                result = self.calculateShiftsSIFT(stack, reference, mask=mask, device=device,
                                                  crop=crop, filename=filename)
            else:
                result = self.__calculateShiftsSIFT(stack, reference, mask=mask, device=device,
                                                    crop=crop, filename=filename)
                if result is not None:
                    if len(result):
                        if isinstance(result[0], str):
                            if result[0] == 'Exception':
                                # exception occurred
                                raise Exception(result[1], result[2], result[3])
            if filename is None:
                self.setStack(stack)

    def calculateShiftsSIFT(self, stack, reference, mask=None, device=None, crop=None,
                            sigma=None,
                            filename=None):
        mask = self.getStackSelectionMask()
        if mask is not None:
            if mask.sum() == 0:
                mask = None
        if device is None:
            siftInstance = sift.LinearAlign(reference.astype(numpy.float32),
                                            devicetype="cpu",
                                            init_sigma=sigma)
        else:
            siftInstance = sift.LinearAlign(reference.astype(numpy.float32),
                                            deviceid=device,
                                            init_sigma=sigma)
        data = stack.data
        mcaIndex = stack.info['McaIndex']
        if not (mcaIndex in [0, 2, -1]):
             raise IndexError("Unsupported 1D index %d" % mcaIndex)
        total = float(data.shape[mcaIndex])
        if filename is not None:
            hdf = self.__hdf5
            dataGroup = hdf['/entry_000/Data']
            attributes = {}
            attributes['interpretation'] = "image"
            attributes['signal'] = numpy.int32(1)
            outputStack = self.getHDF5BufferIntoGroup(dataGroup,
                                                      shape=(data.shape[mcaIndex],
                                                            reference.shape[0],
                                                            reference.shape[1]),
                                                      name="data",
                                                      dtype=numpy.float32,
                                                      attributes=attributes)
        shifts = numpy.zeros((data.shape[mcaIndex], 2), dtype=numpy.float32)
        if mcaIndex == 0:
            for i in range(data.shape[mcaIndex]):
                _logger.debug("SIFT Shifting image %d", i)
                result = siftInstance.align(data[i].astype(numpy.float32), shift_only=True, return_all=True)
                _logger.debug("Index = %d shift = %.4f, %.4f",
                              i, result['offset'][0], result['offset'][1])
                if filename is None:
                    stack.data[i] = result['result']
                else:
                    outputStack[i] = result['result']
                shifts[i, 0] = result['offset'][0]
                shifts[i, 1] = result['offset'][1]
                self._progress = (100 * i) / total
        else:
            image2 = numpy.zeros(reference.shape, dtype=numpy.float32)
            for i in range(data.shape[mcaIndex]):
                _logger.debug("SIFT Shifting image %d", i)
                image2[:, :] = data[:, :, i]
                result = siftInstance.align(image2, shift_only=True, return_all=True)
                _logger.debug("Index = %d shift = %.4f, %.4f",
                              i, result['offset'][0], result['offset'][1])
                if filename is None:
                    stack.data[:, :, i] = result['result']
                else:
                    outputStack[i] = result['result']
                shifts[i, 0] = result['offset'][0]
                shifts[i, 1] = result['offset'][1]
                self._progress = (100 * i) / total
        if filename is not None:
            hdf = self.__hdf5
            alignmentGroup = hdf['/entry_000/Alignment']
            outputShifts = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                 shape=(stack.data.shape[mcaIndex], 2),
                                                 name="shifts",
                                                 dtype=numpy.float32)
            outputShifts[:,:] = shifts
            attributes={'interpretation':'image'}
            referenceFrame = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                 shape=reference.shape,
                                                 name="reference_frame",
                                                 dtype=numpy.float32,
                                                 attributes=attributes)
            referenceFrame[:,:] = reference[:,:]
            maskFrame = self.getHDF5BufferIntoGroup(alignmentGroup,
                                               shape=reference.shape,
                                               name="reference_mask",
                                               dtype=numpy.uint8,
                                               attributes=attributes)

            if mask is None:
                maskData = numpy.ones(reference.shape, dtype=numpy.uint8)
            else:
                maskData = mask
            maskFrame[:,:] = maskData[:,:]
            # fill the axes information
            dataGroup = hdf['/entry_000/Data']
            try:
                activeCurve = self.getActiveCurve()
                if activeCurve is None:
                    activeCurve = self.getAllCurves()[0]
                x, y, legend, info = activeCurve
                dataGroup[info['xlabel']] = numpy.array(x, dtype=numpy.float32)
                dataGroup[info['xlabel']].attrs['axis'] = numpy.int32(1)
                axesAttribute = '%s:dim_1:dim_2' % info['xlabel']
            except Exception:
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                dataGroup['dim_0'] = numpy.arange(stack.data.shape[mcaIndex]).astype(numpy.float32)
                dataGroup['dim_0'].attrs['axis'] = numpy.int32(1)
                axesAttribute = 'dim_0:dim_1:dim_2'
            dataGroup['dim_1'] = numpy.arange(reference.shape[0]).astype(numpy.float32)
            dataGroup['dim_1'].attrs['axis'] = numpy.int32(2)
            dataGroup['dim_2'] = numpy.arange(reference.shape[1]).astype(numpy.float32)
            dataGroup['dim_2'].attrs['axis'] = numpy.int32(3)
            dim2 = numpy.arange(reference.shape[1]).astype(numpy.float32)
            dataGroup['data'].attrs['axes'] = axesAttribute
            self.finishHDF5File(hdf)

    def calculateShiftsFFT(self, stack, reference, offsets=None, widths=None, crop=False):
        _logger.debug("Offsets = %s", offsets)
        _logger.debug("Widths = %s", widths)
        data = stack.data
        if offsets is None:
            offsets = [0.0, 0.0]
        if widths is None:
            widths = [reference.shape[0], reference.shape[1]]
        fft2Function = numpy.fft.fft2
        DTYPE = numpy.float32
        image2 = numpy.zeros((widths[0], widths[1]), dtype=DTYPE)
        shape = image2.shape

        USE_APODIZATION_WINDOW = False
        apo = [10, 10]
        if USE_APODIZATION_WINDOW:
            # use apodization window
            window = numpy.outer(SpecfitFuns.slit([0.5, shape[0] * 0.5, shape[0] - 4 * apo[0], apo[0]],
                                          numpy.arange(float(shape[0]))),
                                 SpecfitFuns.slit([0.5, shape[1] * 0.5, shape[1] - 4 * apo[1], apo[1]],
                                          numpy.arange(float(shape[1])))).astype(DTYPE)
        else:
            window = numpy.zeros((shape[0], shape[1]), dtype=DTYPE)
            window[apo[0]:shape[0] - apo[0], apo[1]:shape[1] - apo[1]] = 1
        image2[:,:] = window * reference[offsets[0]:offsets[0]+widths[0],
                                         offsets[1]:offsets[1]+widths[1]]
        image2fft2 = fft2Function(image2)
        mcaIndex = stack.info.get('McaIndex')
        shifts = numpy.zeros((data.shape[mcaIndex], 2), numpy.float64)
        image1 = numpy.zeros(image2.shape, dtype=DTYPE)
        total = float(data.shape[mcaIndex])
        if mcaIndex == 0:
            for i in range(data.shape[mcaIndex]):
                image1[:,:] = window * data[i][offsets[0]:offsets[0]+widths[0],
                                               offsets[1]:offsets[1]+widths[1]]

                image1fft2 = fft2Function(image1)
                shifts[i] = ImageRegistration.measure_offset_from_ffts(image2fft2,
                                                                       image1fft2)
                _logger.debug("Index = %d shift = %.4f, %.4f",
                              i, shifts[i][0], shifts[i][1])
                self._progress = (100 * i) / total
        elif mcaIndex in [2, -1]:
            for i in range(data.shape[mcaIndex]):
                image1[:,:] = window * data[:,:,i][offsets[0]:offsets[0]+widths[0],
                                               offsets[1]:offsets[1]+widths[1]]

                image1fft2 = fft2Function(image1)
                shifts[i] = ImageRegistration.measure_offset_from_ffts(image2fft2,
                                                                       image1fft2)
                _logger.debug("Index = %d shift = %.4f, %.4f",
                              i, shifts[i][0], shifts[i][1])
                self._progress = (100 * i) / total
        else:
            raise IndexError("Only stacks of images or spectra supported. 1D index should be 0 or 2")
        return shifts

    def _shiftFromFile(self):
        stack = self.getStackDataObject()
        if stack is None:
            return
        data = stack.data
        mcaIndex = stack.info.get('McaIndex')
        if not (mcaIndex in [0, -1, 2]):
            raise IndexError("1D index must be 0, 2, or -1")
        filefilter = ['HDF5 Files (*.h5 *.nxs *.hdf *.hdf5)', 'CSV 2-column (*.csv)', 'ASCII 2-column (*)']
        filename, ffilter = PyMcaFileDialogs.\
                    getFileList(parent=None,
                        filetypelist=filefilter,
                        message='Load',
                        mode='OPEN',
                        single=True,
                        getfilter=True,
                        currentfilter=filefilter[0])
        if len(filename):
            _logger.debug("file name = %s file filter = %s", filename, ffilter)
        else:
            _logger.debug("nothing selected")
            return
        filename = filename[0]
        if ffilter.startswith('HDF5'):
            # browse
            self.__hdf5Dialog = qt.QDialog()
            self.__hdf5Dialog.setWindowTitle('Select your data set by a double click')
            self.__hdf5Dialog.mainLayout = qt.QVBoxLayout(self.__hdf5Dialog)
            self.__hdf5Dialog.mainLayout.setContentsMargins(0, 0, 0, 0)
            self.__hdf5Dialog.mainLayout.setSpacing(0)
            fileModel = HDF5Widget.FileModel()
            fileView = HDF5Widget.HDF5Widget(fileModel)
            with h5py.File(filename, "r") as hdfFile:
                fileModel.appendPhynxFile(hdfFile, weakreference=True)
                self.__shiftsDataset = None
                fileView.sigHDF5WidgetSignal.connect(self._hdf5WidgetSlot)
                self.__hdf5Dialog.mainLayout.addWidget(fileView)
                self.__hdf5Dialog.resize(400, 200)
                ret = self.__hdf5Dialog.exec()
                if not ret:
                    return
                shifts = hdfFile[self.__shitfsDataset].value
        else:
            sf = specfilewrapper.Specfile(filename)
            nScans = len(sf)
            targetScan = None
            for scan in sf:
                if scan.lines() ==  data.shape[stack.info['McaIndex']]:
                    targetScan = scan
                    break
            if targetScan is None:
                scan = None
                sf = None
                raise IOError("Number of read lines does not match stack shape")
            shifts = targetScan.data()
            targetScan = None
            scan = None
            sf = None
            if shifts.shape[0] == 3 and\
               shifts.shape[1] == data.shape[stack.info['McaIndex']]:
                # one column was added (point number)
                shifts = shifts[1:].T

        filename = None
        if not isinstance(data, numpy.ndarray):
            filefilter = ['HDF5 Files (*.h5)']
            filename = PyMcaFileDialogs.\
                        getFileList(parent=None,
                        filetypelist=filefilter,
                        message='Select output file',
                        mode='SAVE',
                        single=True,
                        getfilter=False,
                        currentfilter=filefilter[0])
            if len(filename):
                filename = filename[0]
                _logger.debug("file name = %s", filename)
            else:
                raise IOError("No output file selected")
        if filename is not None:
            self.__hdf5 = self.initializeHDF5File(filename)
        crop = False
        if _logger.getEffectiveLevel() == logging.DEBUG:
            result = self.shiftStack(stack,
                                     shifts,
                                     crop=crop,
                                     filename=filename)
        else:
            result = self.__shiftStack(stack,
                                       shifts,
                                       crop=crop,
                                       filename=filename)
            if result is not None:
                # exception occurred
                raise Exception(result[1], result[2], result[3])

        if filename is not None:
            hdf = self.__hdf5
            alignmentGroup = hdf['/entry_000/Alignment']
            outputShifts = self.getHDF5BufferIntoGroup(alignmentGroup,
                                                 shape=(stack.data.shape[mcaIndex], 2),
                                                 name="shifts",
                                                 dtype=numpy.float32)
            outputShifts[:,:] = shifts
            attributes={'interpretation':'image'}
            # fill the axes information
            dataGroup = hdf['/entry_000/Data']
            if mcaIndex == 0:
                reference_shape = data[0].shape
            else:
                reference_shape = data.shape[0], data.shape[1]
            try:
                activeCurve = self.getActiveCurve()
                if activeCurve is None:
                    activeCurve = self.getAllCurves()[0]
                x, y, legend, info = activeCurve
                dataGroup[info['xlabel']] = numpy.array(x, dtype=numpy.float32)
                dataGroup[info['xlabel']].attrs['axis'] = numpy.int32(1)
                axesAttribute = '%s:dim_1:dim_2' % info['xlabel']
            except Exception:
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                dataGroup['dim_0'] = numpy.arange(stack.data.shape[mcaIndex]).astype(numpy.float32)
                dataGroup['dim_0'].attrs['axis'] = numpy.int32(1)
                axesAttribute = 'dim_0:dim_1:dim_2'
            dataGroup['dim_1'] = numpy.arange(reference_shape[0]).astype(numpy.float32)
            dataGroup['dim_1'].attrs['axis'] = numpy.int32(2)
            dataGroup['dim_2'] = numpy.arange(reference_shape[1]).astype(numpy.float32)
            dataGroup['dim_2'].attrs['axis'] = numpy.int32(3)
            dim2 = numpy.arange(reference_shape[1]).astype(numpy.float32)
            dataGroup['data'].attrs['axes'] = axesAttribute
            self.finishHDF5File(hdf)
        else:
            self.setStack(stack)

    def _hdf5WidgetSlot(self, ddict):
        if ddict['event'] == "itemDoubleClicked":
            if ddict['type'].lower() in ['dataset']:
                self.__shitfsDataset = ddict['name']
                self.__hdf5Dialog.accept()

    def shiftStack(self, stack, shifts, crop=False, filename=None):
        """
        """
        data = stack.data
        mcaIndex = stack.info['McaIndex']
        if mcaIndex not in [0, 2, -1]:
             raise IndexError("Only stacks of images or spectra supported. 1D index should be 0 or 2")
        if mcaIndex == 0:
            shape = data[mcaIndex].shape
        else:
            shape = data.shape[0], data.shape[1]
        d0_start, d0_end, d1_start, d1_end = \
                  ImageRegistration.get_crop_indices(shape,
                                                     shifts[:, 0],
                                                     shifts[:, 1])
        window = numpy.zeros(shape, numpy.float32)
        window[d0_start:d0_end, d1_start:d1_end] = 1.0
        self._progress = 0.0
        total = float(data.shape[mcaIndex])
        if filename is not None:
            hdf = self.__hdf5
            dataGroup = hdf['/entry_000/Data']
            attributes = {}
            attributes['interpretation'] = "image"
            attributes['signal'] = numpy.int32(1)
            outputStack = self.getHDF5BufferIntoGroup(dataGroup,
                                                      shape=(data.shape[mcaIndex],
                                                            shape[0],
                                                            shape[1]),
                                                      name="data",
                                                      dtype=numpy.float32,
                                                      attributes=attributes)
        for i in range(data.shape[mcaIndex]):
            #tmpImage = ImageRegistration.shiftFFT(data[i], shifts[i])
            if mcaIndex == 0:
                tmpImage = ImageRegistration.shiftBilinear(data[i], shifts[i])
                #tmpImage = ImageRegistration.shiftImage(data[i], -shifts[i], method="fft")
                if filename is None:
                    stack.data[i] = tmpImage * window
                else:
                    outputStack[i] = tmpImage * window
            else:
                tmpImage = ImageRegistration.shiftBilinear(data[:,:,i], shifts[i])
                if filename is None:
                    stack.data[:, :, i] = tmpImage * window
                else:
                    outputStack[i] = tmpImage * window
            _logger.debug("Index %d bilinear shifted", i)
            self._progress = (100 * i) / total

    def initializeHDF5File(self, fname):
        #for the time being overwriting
        if os.path.exists(fname):
            os.remove(fname)
        hdf = h5py.File(fname, 'w')
        entryName = "entry_000"
        nxEntry = hdf.require_group(entryName)
        if 'NX_class' not in nxEntry.attrs:
            nxEntry.attrs['NX_class'] = 'NXentry'.encode('utf-8')
        nxEntry['title'] = numpy.bytes_("PyMca saved 3D Array".encode('utf-8'))
        nxEntry['start_time'] = numpy.bytes_(ArraySave.getDate().encode('utf-8'))

        alignmentGroup = nxEntry.require_group('Alignment')
        dataGroup = nxEntry.require_group('Data')
        dataGroup.attrs['NX_class'] = 'NXdata'.encode('utf-8')
        return hdf

    def finishHDF5File(self, hdf):
        #add final date
        toplevelEntry = hdf["entry_000"]
        toplevelEntry['end_time'] = numpy.bytes_(ArraySave.getDate().encode('utf-8'))
        hdf.flush()
        hdf.close()

    def getHDF5BufferIntoGroup(self, h5Group, shape,
                               name="data", dtype=numpy.float32,
                               attributes=None,
                               compression=None,
                               shuffle=False,
                               chunks=None,
                               chunk_cache=None):
        dataset = h5Group.require_dataset(name,
                                          shape=shape,
                                          dtype=dtype,
                                          chunks=chunks,
                                          shuffle=shuffle,
                                          compression=compression)
        if attributes is None:
            attributes = {}
        for attribute in attributes:
            dataset.attrs[attribute] = attributes[attribute]
        return dataset

MENU_TEXT = "Image Alignment Tool"
def getStackPluginInstance(stackWindow, **kw):
    ob = ImageAlignmentStackPlugin(stackWindow)
    return ob
