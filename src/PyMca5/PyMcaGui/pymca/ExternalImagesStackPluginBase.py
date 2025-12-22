#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2022 European Synchrotron Radiation Facility
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
__author__ = "Wout De Nolf"
__contact__ = "wout.de_nolf@esrf.eu"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import logging
from PyMca5 import StackPluginBase
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaIO import EDFStack
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
try:
    import h5py
except ImportError:
    HAS_H5PY = False
else:
    HAS_H5PY = True
    from PyMca5.PyMcaGui.io.hdf5 import HDF5Widget
    from PyMca5.PyMcaIO import NexusUtils

_logger = logging.getLogger(__name__)


class ExternalImagesStackPluginBase(StackPluginBase.StackPluginBase):

    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)

    def _loadImageFiles(self):
        fileTypeList = ['HDF5 Files (*.h5 *.nxs *.hdf *.hdf5)',
                        "PNG Files (*png)",
                        "JPEG Files (*jpg *jpeg)",
                        "IMAGE Files (*)",
                        "DAT Files (*dat)",
                        "CSV Files (*csv)",
                        "EDF Files (*edf)",
                        "EDF Files (*ccd)",
                        "EDF Files (*)"]
        filenamelist, filefilter = PyMcaFileDialogs.getFileList(parent=None,
                                    filetypelist=fileTypeList,
                                    message="Open image file",
                                    getfilter=True,
                                    single=False,
                                    currentfilter=None)
        if not filenamelist:
            return
        filefilter = filefilter.split()[0].lower()
        extension = qt.safe_str(os.path.splitext(filenamelist[0])[1]).lower()
        if (filefilter in ["edf"]) or \
           (extension in [".edf", ".tif"]):
            imagenames, imagelist = self._readImageListEdf(filenamelist)
            if imagenames:
                try:
                    self._createStackPluginWindowEdf(imagenames, imagelist)
                except AttributeError:
                    self._createStackPluginWindow(imagenames, imagelist)
        elif (filefilter in ["hdf5"]) or \
           (extension in [".h5", ".nxs", ".hdf", ".hdf5"]):
            imagenames, imagelist = self._readImageListHdf5(filenamelist)
            if imagenames:
                try:
                    self._createStackPluginWindowHdf5(imagenames, imagelist)
                except AttributeError:
                    self._createStackPluginWindow(imagenames, imagelist)
        elif extension in [".csv", ".dat"]:
            imagenames, imagelist = self._readImageListSpec(filenamelist)
            if imagenames:
                try:
                    self._createStackPluginWindowSpec(imagenames, imagelist)
                except AttributeError:
                    self._createStackPluginWindow(imagenames, imagelist)
        else:
            imagenames, imagelist = self._readImageListQImageReadable(filenamelist)
            if imagenames:
                try:
                    self._createStackPluginWindowQImage(imagenames, imagelist)
                except AttributeError:
                    self._createStackPluginWindow(imagenames, imagelist)

    def _createStackPluginWindow(self, imagenames, imagelist):
        raise NotImplemented(\
            "_createStackPluginWindow(self, imagenames, imagelist)")

    @property
    def _dialogParent(self):
        raise NotImplemented("_dialogParent(self) not implemented")

    @property
    def _requiredShape(self):
        mask = self.getStackSelectionMask()
        if mask is None:
            r, n = self.getStackROIImagesAndNames()
            return r[0].shape
        else:
            return mask.shape

    def _readImageListEdf(self, filenamelist):
        imagelist = []
        imagenames = []
        shape = tuple(sorted(self._requiredShape))
        for filename in filenamelist:
            edf = EDFStack.EdfFileDataSource.EdfFileDataSource(filename)
            keylist = edf.getSourceInfo()['KeyList']
            if len(keylist) < 1:
                self._criticalError("Cannot read image from file %s" % filename)
                return None, None
            for key in keylist:
                dataObject = edf.getDataObject(key)
                data = dataObject.data
                if tuple(sorted(data.shape)) != shape:
                    continue
                imagename = dataObject.info.get('Title', "")
                if imagename != "":
                    imagename += " "
                imagename += os.path.basename(filename)+" "+key
                imagelist.append(data)
                imagenames.append(imagename)
        if not imagenames:
            self._criticalError('No valid data provided')
        return imagenames, imagelist

    def _readImageListHdf5(self, filenamelist):
        if h5py is None:
            self._criticalError("Cannot read HDF5 files (h5py is missing)")
            return None, None
        imagelist = []
        imagenames = []
        shape = tuple(sorted(self._requiredShape))
        def match(dset):
            return tuple(sorted(dset.shape)) == shape
        for uri in filenamelist:
            tmp = uri.split('::')
            if len(tmp) == 1:
                tmp = uri, None
            filename, h5path = tmp
            # URI exists?
            if h5path:
                with HDF5Widget.h5open(filename) as hdf5File:
                    if h5path not in hdf5File:
                        h5path = None
            # Prompt for missing HDF5 path
            if not h5path:
                tmp = HDF5Widget.getUri(parent=self._dialogParent,
                                        filename=filename,
                                        message='Select Group or Dataset')
                if not tmp:
                    return None, None
                tmp = tmp.split('::')
                if len(tmp) == 2:
                    h5path = tmp[1]
            if not h5path:
                return None, None
            # Add datasets from HDF5 path
            with HDF5Widget.h5open(filename) as hdf5File:
                # If `h5path` is an instance of NXdata, only the signals
                # (including auxilary signals) are considered for `match`.
                datasets = NexusUtils.selectDatasets(hdf5File[h5path], match=match)
                if not datasets:
                    self._criticalError("No (valid) datasets were found in '%s::%s'" % (filename, h5path))
                    return None, None
                elif len({dset.size for dset in datasets}) > 1:
                    self._criticalError("'%s::%s' contains datasets with different sizes. Select datasets separately." % (filename, h5path))
                    return None, None
                else:
                    for dset in datasets:
                        imagename = '/'.join(dset.name.split('/')[-2:])
                        imagelist.append(dset[()])
                        imagenames.append(imagename)
        if not imagenames:
            self._criticalError('No valid data provided')
        return imagenames, imagelist

    def _readImageListSpec(self, filenamelist):
        # what to do if more than one file selected ?
        from PyMca5.PyMca import specfilewrapper as Specfile
        sf = Specfile.Specfile(filenamelist[0])
        scan = sf[0]
        labels = scan.alllabels()
        data = scan.data()
        scan = None
        sf = None
        if "column" in labels:
            offset = labels.index("column")
            ncols = int(data[offset].max() + 1)
            offset += 1
        else:
            raise IOError("Only images exported as csv supported")
        imagelist = []
        imagenames = []
        for i in range(offset, len(labels)):
            if labels[i].startswith("s("):
                continue
            tmpData = data[i]
            tmpData = tmpData.reshape(-1, ncols)
            imagelist.append(tmpData)
            imagenames.append(labels[i])
        if not imagenames:
            self._criticalError('No valid data provided')
        return imagenames, imagelist

    def _readImageListQImageReadable(self, filenamelist):
        imagelist = []
        imagenames = []
        for filename in filenamelist:
            image = qt.QImage(filename)
            if image.isNull():
                self._criticalError("Cannot read file %s as an image" % filename)
                return None, None
            imagelist.append(image)
            imagenames.append(os.path.basename(filename))
        if not imagenames:
            self._criticalError('No valid data provided')
        return imagenames, imagelist

    def _criticalError(self, text):
        msg = qt.QMessageBox(self._dialogParent)
        msg.setIcon(qt.QMessageBox.Critical)
        msg.setText(text)
        msg.exec()
