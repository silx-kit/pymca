#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2024 European Synchrotron Radiation Facility
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
import sys
import numpy
import logging
import time
import re
import itertools
if sys.version_info[0] < 3:
    string_types = basestring,
else:
    string_types = str,
from contextlib import contextmanager
from collections import defaultdict
try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping
from . import NexusUtils

_logger = logging.getLogger(__name__)

if NexusUtils.h5py is None:
    bufferTypes = list,  numpy.ndarray
else:
    bufferTypes = list,  numpy.ndarray, NexusUtils.h5py.Dataset


class OutputBuffer(MutableMapping):
    """
    Dictionary enriched with memory allocation and save options.

    Implicite saving with context:
        outbuffer = OutputBuffer(...)
        with outbuffer.saveContext():
            ...

    Explicite saving without context:
        outbuffer = OutputBuffer(...)
        ...
        outbuffer.save()
    """

    def __init__(self, outputDir=None, outputRoot=None, fileEntry=None,
                 fileProcess=None, suffix=None, h5=True,
                 tif=False, edf=False, csv=False, dat=False,
                 multipage=False, overwrite=False,
                 nosave=False, dtype=None):
        """
        Dictionary will be saved as:
         .h5 : outputDir/outputRoot+suffix.h5::/fileEntry/fileProcess
         .edf/.csv/.tif: outputDir/outputRoot/fileEntry+suffix.ext

        :param str outputDir: default: current working directory
        :param str outputRoot: default: "IMAGES"
        :param str fileEntry: default: "images"
        :param str fileProcess: default: "pymcaprocess"
        :param bool tif:
        :param bool edf:
        :param bool csv:
        :param bool dat:
        :param bool h5:
        :param bool multipage: all images in 1 file if the format allows it
        :param bool overwrite:
        :param str suffix: default: None
        :param bool nosave: prevent saving (everything will be in memory)
        :param dtype: force dtype on memory allocation
        """
        self._inBufferContext = False
        self._inSaveContext = False
        self._buffers = {}
        self._info = {}
        self._results = {}
        self._labels = {}
        self._nxprocess = None
        self._labelFormats = defaultdict(lambda: '')
        self._defaultgroups = ()
        self._defaultorder = ()
        self._optionalimage = ()
        self._configurationkey = 'configuration'
        self._forcedtype = dtype

        self.outputRootDefault = 'IMAGES'
        self.fileEntryDefault = 'images'
        self.fileProcessDefault = 'pymcaprocess'
        self.outputDir = outputDir
        self.outputRoot = outputRoot
        self.fileEntry = fileEntry
        self.fileProcess = fileProcess
        self.suffix = suffix

        self.tif = tif
        self.edf = edf
        self.csv = csv
        self.dat = dat
        self.h5 = h5
        self.multipage = multipage
        self.overwrite = overwrite
        self.nosave = nosave

    def __getitem__(self, key):
        try:
            return self._buffers[key]
        except KeyError:
            return self._info[key]

    def __setitem__(self, key, value):
        if isinstance(value, bufferTypes):
            self.allocateMemory(key, data=value)
        else:
            self._info[key] = value

    def __delitem__(self, key):
        try:
            del self._buffers[key]
        except KeyError:
            del self._info[key]

    def __iter__(self):
        return itertools.chain(iter(self._buffers), iter(self._info))

    def __len__(self):
        return len(self._buffers) + len(self._info)

    def __repr__(self):
        return "OutputBuffer(outputDir={}, outputRoot={}, fileEntry={}, suffix={})"\
                .format(repr(self.outputDir), repr(self.outputRoot),
                        repr(self.fileEntry), repr(self.suffix))

    def hasAllocatedMemory(self):
        return bool(self._buffers)

    def labelFormat(self, group, prefix):
        """For single-page edf/tif file names
        """
        self._labelFormats[group] = prefix

    @property
    def outputRoot(self):
        ret = self._outputRoot
        if ret:
            return ret
        else:
            return self.outputRootDefault

    @outputRoot.setter
    def outputRoot(self, value):
        self._checkBufferContext()
        self._outputRoot = value

    @property
    def fileEntry(self):
        ret = self._fileEntry
        if ret:
            return ret
        else:
            return self.fileEntryDefault

    @fileEntry.setter
    def fileEntry(self, value):
        self._checkBufferContext()
        self._fileEntry = value

    @property
    def fileProcess(self):
        ret = self._fileProcess
        if ret:
            return ret
        else:
            return self.fileProcessDefault

    @fileProcess.setter
    def fileProcess(self, value):
        self._checkBufferContext()
        self._fileProcess = value

    @property
    def extensions(self):
        lst = []
        if self.h5:
            lst.append('.h5')
        if self.dat:
            lst.append('.dat')
        if self.csv:
            lst.append('.csv')
        if self.tif:
            lst.append('.tif')
        if self.edf:
            lst.append('.edf')
        return lst

    @extensions.setter
    def extensions(self, lst):
        for ext in lst:
            if ext.startswith('.'):
                attr = ext[1:]
            else:
                attr = ext
            if hasattr(self, attr):
                setattr(self, attr, True)

    @property
    def edf(self):
        return self._edf

    @edf.setter
    def edf(self, value):
        self._checkBufferContext()
        self._edf = value

    @property
    def tif(self):
        return self._tif

    @tif.setter
    def tif(self, value):
        self._checkBufferContext()
        self._tif = value

    @property
    def csv(self):
        return self._csv

    @csv.setter
    def csv(self, value):
        self._checkBufferContext()
        self._csv = value

    @property
    def dat(self):
        return self._dat

    @dat.setter
    def dat(self, value):
        self._checkBufferContext()
        self._dat = value

    @property
    def cfg(self):
        return self.csv or self.dat or self.edf or self.tif

    @property
    def overwrite(self):
        return self._overwrite

    @overwrite.setter
    def overwrite(self, value):
        self._checkBufferContext()
        self._overwrite = bool(value)

    @property
    def nosave(self):
        return self._nosave

    @nosave.setter
    def nosave(self, value):
        self._checkBufferContext()
        self._nosave = bool(value)

    def _checkBufferContext(self):
        if self._inBufferContext:
            raise RuntimeError('Buffer is locked')

    @property
    def outputDirLegacy(self):
        #return os.path.join(self.outputDir, self.outputRoot)
        # REMARK: do this to be compatible with the legacy code
        return os.path.join(self.outputDir, 'IMAGES')

    def filename(self, ext, suffix=None):
        if not suffix:
            suffix = ""
        if self.suffix:
            suffix += self.suffix
        if ext == '.h5':
            return os.path.join(self.outputDir, self.outputRoot+suffix+ext)
        else:
            return os.path.join(self.outputDirLegacy, self.fileEntry+suffix+ext)

    def allocateMemory(self, label, group=None, memtype='ram', **kwargs):
        """
        :param str label:
        :param str group: group name of this dataset (in hdf5 this is the nxdata name)
        :param str memtype: ram or hdf5
        :param **kwargs: see _allocateRam or _allocateHdf5
        """
        memtype = memtype.lower()
        if self._forcedtype is not None:
            kwargs['dtype'] = self._forcedtype
        if not group:
            group = label
        allocH5 = memtype in ('hdf5', 'h5', 'nx', 'nexus')
        if allocH5:
            allocH5 = False
            if self.nosave:
                _logger.info('Allocate in memory instead of Hdf5 (saving is disabled)')
            elif not self.h5:
                _logger.info('Allocate in memory instead of Hdf5 (h5 format is disabled)')
            elif NexusUtils.h5py is None:
                _logger.info('Allocate in memory instead of Hdf5 (h5py not installed)')
            elif not self.outputDir:
                _logger.warning('Allocate in memory instead of Hdf5 (no output directory specified)')
            else:
                allocH5 = True
        if allocH5:
            buffer = self._allocateHdf5(label, group=group, **kwargs)
        else:
            buffer = self._allocateRam(label, group=group, **kwargs)
        return buffer

    def _allocateRam(self, label, group=None, fill_value=None, dataAttrs=None,
                     data=None, shape=None, dtype=None, labels=None,
                     groupAttrs=None, **unused):
        """
        :param str label:
        :param str group: group name of this dataset (in hdf5 this is the nxdata name)
        :param num fill_value: initial buffer item value
        :param dict dataAttrs: dataset attributes
        :param ndarray data: dataset or stack of datasets
        :param tuple shape: buffer shape
        :param dtype: buffer type
        :param list labels: for stack of datasets
        :param dict groupAttrs: nxdata attributes (e.g. axes)
        """
        if data is not None:
            buffer = numpy.asarray(data, dtype=dtype)
            if id(buffer) in set(map(id, self._buffers.values())):
                buffer = buffer.copy()
            if fill_value is not None:
                buffer[:] = fill_value
        elif fill_value is None:
            buffer = numpy.empty(shape, dtype=dtype)
        elif fill_value == 0:
            buffer = numpy.zeros(shape, dtype=dtype)
        else:
            buffer = numpy.full(shape, fill_value, dtype=dtype)
        self._buffers[label] = buffer

        # Prepare Hdf5 dataset arguments
        if labels:
            names = self._labelsToHdf5Strings(labels)
            for lbl, name, data in zip(labels, names, buffer):
                self._addResult(group, lbl, name, data, dataAttrs, groupAttrs)
        else:
            name = self._labelsToHdf5Strings([label])[0]
            self._addResult(group, label, name, buffer, dataAttrs, groupAttrs)
        return buffer

    def _allocateHdf5(self, label, group=None, fill_value=None, dataAttrs=None,
                      data=None, shape=None, dtype=None, labels=None,
                      groupAttrs=None, **createkwargs):
        """
        :param str or tuple label:
        :param str group: group name of this dataset (in hdf5 this is the nxdata name)
        :param num fill_value: initial buffer item value
        :param dict dataAttrs: dataset attributes
        :param ndarray data: dataset or stack of datasets
        :param tuple shape: buffer shape
        :param dtype: buffer type
        :param list labels: for stack of datasets
        :param dict groupAttrs: nxdata attributes (e.g. axes)
        :param **createkwargs: see h5py.Group.create_dataset
        """
        if data is None and shape is None:
            raise ValueError("Provide 'data' or 'shape'")
        if data is None and dtype is None:
            raise ValueError("Missing 'dtype' argument")

        # Create Nxdata group (if not already there)
        nxdata = self._getNXdataGroup(group)

        # Create datasets (attributes will be handled later)
        if labels:
            names = self._labelsToHdf5Strings(labels)
            buffer = []  # TODO: list of datasets cannot be indexed like a numpy array
            if data is None:
                signalshape = shape[1:]
                for lbl, name in zip(labels, names):
                    dset = nxdata.create_dataset(name, shape=signalshape,
                                                 dtype=dtype, **createkwargs)
                    if fill_value is not None:
                        dset[()] = fill_value
                    self._addResult(group, lbl, name, dset, dataAttrs, groupAttrs)
                    buffer.append(dset)
            else:
                for lbl, name, signaldata in zip(labels, names, data):
                    if dtype is not None:
                        signaldata = signaldata.astype(dtype)
                    dset = nxdata.create_dataset(name, data=signaldata,
                                                 **createkwargs)
                    if fill_value is not None:
                        dset[()] = fill_value
                    self._addResult(group, lbl, name, dset, dataAttrs, groupAttrs)
                    buffer.append(dset)
        else:
            name = self._labelsToHdf5Strings([label])[0]
            if data is None:
                buffer = nxdata.create_dataset(name, shape=shape,
                                               dtype=dtype, **createkwargs)
            else:
                if dtype is not None:
                    try:
                        data = data.astype(dtype)
                    except AttributeError:
                        data = data[()].astype(dtype)
                buffer = nxdata.create_dataset(name, data=data, **createkwargs)
            if fill_value is not None:
                buffer[()] = fill_value
            self._addResult(group, label, name, buffer, dataAttrs, groupAttrs)

        self.flush()
        self._buffers[label] = buffer
        return buffer

    def _getNXdataGroup(self, group):
        """
        Get h5py.Group (create when missing, verify class when present)
        :param str group:
        """
        parent = self._nxprocess['results']
        if group in parent:
            nxdata = parent[group]
            NexusUtils.raiseIsNotNxClass(nxdata, u'NXdata')
        else:
            nxdata = NexusUtils.nxData(parent, group)
        return nxdata

    def _addResult(self, group, label, h5name, buffer, dataAttrs, groupAttrs):
        # Prepare HDF5 output
        # group -> NXdata (h5py.group), label -> signal (h5py.dataset)
        info = self._results.get(group, None)
        if info is None:
            if groupAttrs:
                info = groupAttrs.copy()
            else:
                info = {}
            info['_signals'] = []
            info['default'] = info.get('default', False)
            info['errors'] = info.get('errors', None)
            info['axes'] = info.get('axes', None)
            info['axesused'] = info.get('axesused', None)
            self._results[group] = info
        if dataAttrs is None:
            attrs = {}
        else:
            attrs = dataAttrs.copy()
        attrs['chunks'] = attrs.get('chunks', True)
        if buffer.ndim == 2:
            interpretation = 'image'
        else:
            interpretation = 'spectrum'
        attrs['interpretation'] = attrs.get('interpretation', interpretation)
        info['_signals'].append((h5name, {'data': buffer}, attrs))

        # Groups labels
        labels = self._labels.get(group, None)
        if labels is None:
            self._labels[group] = labels = []
        labels.append(label)

        # Mark as default (unmark others)
        if info['default']:
            self.markDefault(group)

    def labels(self, group, labeltype=None):
        """
        :param str group:
        :param str labeltype: 'hdf5': dataset names used in h5
                              'filename': file names
                              'title': titles used in edf/dat/csv/tif
                              else: join with space-separator
        :returns list: strings or tuples
        """
        labels = self._labels.get(group, [])
        return self._labelsToStrings(group, labels, labeltype=labeltype)

    def _labelsToStrings(self, group, labels, labeltype=None):
        if not labels:
            return labels
        if labeltype == 'hdf5':
            return self._labelsToHdf5Strings(labels)
        elif labeltype == 'filename' or labeltype == 'title':
            prefix = self._labelFormats[group]
            return self._labelsToPathStrings(labels,
                                             prefix=prefix,
                                             filename=labeltype == 'filename')
        else:
            return labels

    @staticmethod
    def _labelsToPathStrings(labels, prefix='', separator='_', filename=False):
        """
        Used for EDF files names and CSV titles
        For example: ('Fe-K', 'Layer1') -> `s(Fe-K)_Layer1` (title)
                                        -> `s(Fe_K)_Layer1` (filename)

        :param list(tuple) labels:
        :param str prefix: for decoration (for example s(...), w(...), ...)
        :param str separator: to join the tuples (regular expression)
        :param bool filename: file name or title
        """
        if not labels:
            return []
        out = []
        def replbrackets(matchobj):
            return matchobj.group(1)+separator
        separators = {r'\-', ':', ';', '_'}
        separators -= {separator}
        separators = '[' + ''.join(separators) + ']+'
        for args in labels:
            if not isinstance(args, tuple):
                args = (args,)
            if prefix:
                args = ('{}({})'.format(prefix, args[0]), ) + args[1:]
            label = separator.join(args)
            # Replace spaces with separator
            label = re.sub(r'\s+', separator, label)
            if filename:
                # Replace separators
                label = re.sub(separators, separator, label)
                # Replace brackets with a trailing separator
                label = re.sub(r'\((.+)\)', replbrackets, label)
                label = re.sub(r'\[(.+)\]', replbrackets, label)
                label = re.sub(r'\{(.+)\}', replbrackets, label)
                # Remove non-alphanumeric characters (except . and separator)
                label = re.sub(r'[^0-9a-zA-Z\.'+separator+']+', '', label)
                # Remove trailing/leading separators
                label = re.sub('^'+separator+'+', '', label)
                label = re.sub(separator+'+$', '', label)
            # Remove repeated separators
            label = re.sub(separator+'+', separator, label)
            out.append(label)
        return out

    @staticmethod
    def _labelsToHdf5Strings(labels, separator='_', replace=(r'\s+',)):
        """
        Used for hdf5 dataset names
        For example: ('Fe-K', 'Layer1') -> `Fe-K_Layer1`

        :param list(tuple) labels:
        :param str separator: to join the tuples (regular expression)
        :param tuple(str) replace: to be replaced by the `separator` (regular expressions)
        """
        if not labels:
            return []
        out = []
        for args in labels:
            if not isinstance(args, tuple):
                args = (args,)
            for srepl in replace:
                args = tuple(re.sub(srepl, separator, s) for s in args)
            out.append(separator.join(args))
        return out

    def markDefault(self, group):
        for groupname, info in self._results.items():
            info['default'] = groupname == group

    @contextmanager
    def bufferContext(self, update=True):
        """
        Prepare output buffers (HDF5: create file, NXentry and NXprocess)

        :param bool update: True: update existing NXprocess
                            False: overwrite or raise an exception
        :raises RuntimeError: NXprocess exists and overwrite==False
        """
        if self._inBufferContext:
            yield
        else:
            self._inBufferContext = True
            _logger.debug('Enter buffering context of {}'.format(self))
            try:
                if self.h5:
                    if self._nxprocess is None and self.outputDir:
                        cleanup_funcs = []
                        try:
                            with self._h5Context(cleanup_funcs, update=update):
                                yield
                        except:
                            # clean-up and re-raise
                            for func in cleanup_funcs:
                                func()
                            raise
                    else:
                        yield
                else:
                    yield
            finally:
                self._inBufferContext = False
                _logger.debug('Exit buffering context of {}'.format(self))

    @contextmanager
    def _h5Context(self, cleanup_funcs, update=True):
        """
        Initialize NXprocess on enter and close/cleanup on exit
        """
        if self.nosave:
            yield
        else:
            fileName = self.filename('.h5')
            existed = [False]*3  # h5file, nxentry, nxprocess
            existed[0] = os.path.exists(fileName)
            with NexusUtils.nxRoot(fileName, mode='a') as f:
                # Open/overwrite NXprocess: h5file::/entry/process
                entryname = self.fileEntry
                existed[1] = entryname in f
                entry = NexusUtils.nxEntry(f, entryname)
                procname = self.fileProcess
                if procname in entry:
                    existed[2] = True
                    path = entry[procname].name
                    if update:
                        _logger.debug('edit {}'.format(path))
                    elif self.overwrite:
                        _logger.info('overwriting {}::{}'.format(fileName, path))
                        del entry[procname]
                        existed[2] = False
                    else:
                        raise RuntimeError('{}::{} already exists'.format(fileName, path))
                self._nxprocess = NexusUtils.nxProcess(entry, procname)
                try:
                    with self._h5DatasetContext(f):
                        yield
                except:
                    # clean-up and re-raise
                    if not existed[0]:
                        cleanup_funcs.append(lambda: os.remove(fileName))
                    elif not existed[1]:
                        del f[entryname]
                    elif not existed[2]:
                        del entry[procname]
                    raise
                finally:
                    self._nxprocess = None

    @contextmanager
    def _h5DatasetContext(self, f):
        """
        Swap strings for dataset objects on enter and back on exit
        """
        update = {}
        for k, v in self._buffers.items():
            if isinstance(v, string_types):
                update[k] = f[v]
        self._buffers.update(update)
        try:
            yield
        finally:
            update = {}
            for k, v in self._buffers.items():
                if isinstance(v, NexusUtils.h5py.Dataset):
                    update[k] = v.name
            self._buffers.update(update)

    @contextmanager
    def saveContext(self, update=False):
        """
        Same as `bufferContext` but with `save` when leaving the context.
        By default `update=False`: try overwriting (exception when not allowed)
        """
        alreadyIn = self._inSaveContext
        if not alreadyIn:
            self._inSaveContext = True
            _logger.debug('Enter saving context of {}'.format(self))
        with self.bufferContext(update=update):
            try:
                yield
            except:
                raise
            else:
                if not alreadyIn:
                    self.save()
            finally:
                if not alreadyIn:
                    self._inSaveContext = False
        _logger.debug('Exit saving context of {}'.format(self))

    @contextmanager
    def Context(self, save=True, update=False):
        """
        Either saveContext or bufferContext.
        By default `update=False`: try overwriting (exception when not allowed)
        """
        if save:
            with self.saveContext(update=update):
                yield
        else:
            with self.bufferContext(update=update):
                yield

    def flush(self):
        if self._nxprocess is not None:
            self._nxprocess.file.flush()

    def save(self):
        """
        Save result of XRF batch fitting. Preferrable use saveContext instead.
        HDF5 NXprocess will be updated, not overwritten.
        """
        _logger.debug('Saving {}'.format(self))
        if self.nosave:
            _logger.info('Fit results are not saved (saving is disabled)')
            return
        elif not (self.tif or self.edf or self.csv or self.dat or self.h5):
            _logger.warning('Fit results are not saved (all output formats disabled)')
            return
        elif not self.outputDir:
            _logger.warning('Fit results are not saved (no output directory specified)')
            return
        t0 = time.time()
        with self.bufferContext(update=True):
            if self.tif or self.edf or self.csv or self.dat:
                self._saveImages()
            if self.h5:
                self._saveH5()
        t = time.time() - t0
        _logger.debug("Saving results elapsed = %f", t)

    def _imageList(self, onlylabels=False):
        imageFileLabels = []
        if onlylabels:
            out = imageFileLabels
        else:
            imageTitleLabels = []
            imageList = []
            out = imageFileLabels, imageTitleLabels, imageList
        keys = list(self._buffers.keys())
        groups = []
        for key in self._defaultorder:
            if key in keys:
                groups.append(key)
                keys.pop(keys.index(key))
        groups += sorted(keys)
        for group in groups:
            names = self.labels(group, labeltype='filename')
            buffer = self._buffers[group]
            if len(names) == len(buffer):
                # Stack of datasets
                mnames = self.labels(group, labeltype='title')
                for name, mname, bufferi in zip(names, mnames, buffer):
                    imageFileLabels.append(name)
                    if not onlylabels:
                        imageTitleLabels.append(mname)
                        imageList.append(bufferi[()])
            else:
                # Single dataset
                if group.lower() in self._optionalimage:
                    name = self._labelsToStrings(group, [group], labeltype='filename')[0]
                    mname = self._labelsToStrings(group, [group], labeltype='title')[0]
                    imageFileLabels.append(name)
                    if not onlylabels:
                        imageTitleLabels.append(mname)
                        imageList.append(buffer[()])
        return out

    def filenames(self, ext):
        if self.multipage or ext == '.h5':
            return [self.filename(ext)]
        else:
            labels = self._imageList(onlylabels=True)
            return [self.filename(ext, suffix="_" + label) for label in labels]

    def _saveImages(self):
        from PyMca5.PyMcaIO import ArraySave

        # List of images in deterministic order
        imageFileLabels, imageTitleLabels, imageList = self._imageList()
        if not imageFileLabels:
            return

        NexusUtils.mkdir(self.outputDirLegacy)
        if self.edf:
            if self.multipage:
                fileName = self.filename('.edf')
                self._checkOverwrite(fileName)
                ArraySave.save2DArrayListAsEDF(imageList, fileName,
                                               labels=imageTitleLabels)
            else:
                for label, title, image in zip(imageFileLabels, imageTitleLabels, imageList):
                    fileName = self.filename('.edf', suffix="_" + label)
                    self._checkOverwrite(fileName)
                    ArraySave.save2DArrayListAsEDF([image],
                                                   fileName,
                                                   labels=[title])
        if self.tif:
            if self.multipage:
                fileName = self.filename('.tif')
                self._checkOverwrite(fileName)
                ArraySave.save2DArrayListAsMonochromaticTiff(imageList,
                                                             fileName,
                                                             labels=imageTitleLabels,
                                                             dtype=numpy.float32)
            else:
                for label, title, image in zip(imageFileLabels, imageTitleLabels, imageList):
                    fileName = self.filename('.tif', suffix="_" + label)
                    self._checkOverwrite(fileName)
                    ArraySave.save2DArrayListAsMonochromaticTiff([image],
                                                                 fileName,
                                                                 labels=[title],
                                                                 dtype=numpy.float32)
        if self.csv or self.dat:
            # only same shapes can be saved
            goodIndices = []
            for i in range(len(imageTitleLabels)):
                if imageList[i].shape == imageList[0].shape:
                    goodIndices.append(i)
                else:
                    txt = "Skip ASCII saving of badly shaped image {}".format(imageTitleLabels[i]) 
                    _logger.info(txt)
            if len(goodIndices) == len((imageTitleLabels)):
                goodImageList = imageList
                goodImageTitleLabels = imageTitleLabels
            else:
                goodImageList = []
                goodImageTitleLabels = []
                for i in goodIndices:
                    goodImageList.append(imageList[i])
                    goodImageTitleLabels.append(imageTitleLabels[i])

        if self.csv:
            fileName = self.filename('.csv')
            self._checkOverwrite(fileName)
            ArraySave.save2DArrayListAsASCII(goodImageList, fileName, csv=True,
                                             labels=goodImageTitleLabels)
        if self.dat:
            fileName = self.filename('.dat')
            self._checkOverwrite(fileName)
            ArraySave.save2DArrayListAsASCII(goodImageList, fileName, csv=False,
                                             labels=goodImageTitleLabels)

        if self.cfg and self._configurationkey in self:
            fileName = self.filename('.cfg')
            self._checkOverwrite(fileName)
            self[self._configurationkey].write(fileName)

    def _checkOverwrite(self, fileName):
        if os.path.exists(fileName):
            if self.overwrite:
                _logger.info('overwriting {}'.format(fileName))
            else:
                raise RuntimeError('{} already exists'.format(fileName))

    def _saveH5(self):
        nxprocess = self._nxprocess
        if nxprocess is None:
            return

        # Save fit configuration
        configdict = self.get(self._configurationkey, None)
        NexusUtils.nxProcessConfigurationInit(nxprocess, configdict=configdict)

        # Save allocated memory
        nxresults = nxprocess['results']
        adderrors = []
        markdefault = []
        for group, info in self._results.items():
            # Create group
            nxdata = self._getNXdataGroup(group)
            # Add signals
            NexusUtils.nxDataAddSignals(nxdata, info['_signals'])
            # Add axes
            axes = info.get('axes', None)
            axes_used = info.get('axesused', None)
            if axes:
                NexusUtils.nxDataAddAxes(nxdata, axes)
            if axes_used:
                axes = [(ax, None, None) for ax in axes_used]
                NexusUtils.nxDataAddAxes(nxdata, axes, append=False)
            # Add error links
            errors = info['errors']
            if errors:
                adderrors.append((nxdata, errors))
            # Default nxdata for visualization
            if info['default']:
                markdefault.append(nxdata)

        # Error links and default for visualization
        for nxdata, errors in adderrors:
            if errors in nxresults:
                NexusUtils.nxDataAddErrors(nxdata, nxresults[errors])
        if markdefault:
            NexusUtils.markDefault(markdefault[-1])
        else:
            for group in self._defaultgroups:
                if group in nxresults:
                    NexusUtils.markDefault(nxresults[group])
                    break
