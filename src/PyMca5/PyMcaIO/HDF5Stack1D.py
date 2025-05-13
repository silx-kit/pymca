#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import posixpath
import numpy
import h5py
import logging
_logger = logging.getLogger(__name__)

from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaMisc import PhysicalMemory
from PyMca5.PyMcaCore import NexusDataSource
from PyMca5.PyMcaCore import NexusTools

SOURCE_TYPE = "HDF5Stack1D"

class HDF5Stack1D(DataObject.DataObject):
    def __init__(self, filelist, selection,
                       scanlist=None,
                       dtype=None):
        DataObject.DataObject.__init__(self)

        #the data type of the generated stack
        self.__dtype0 = dtype
        self.__dtype  = dtype

        if filelist is not None:
            if selection is not None:
                self.loadFileList(filelist, selection, scanlist)

    def loadFileList(self, filelist, selection, scanlist=None):
        """
        loadFileList(self, filelist, y, scanlist=None, monitor=None, x=None)
        filelist is the list of file names belonging to the stack
        selection is a dictionary with the keys x, y, m.
        x        is the path to the x data (the channels) in the spectrum,
                 without the first level "directory". It is unused (for now).
        y        is the path to the 1D data (the counts) in the spectrum,
                 without the first level "directory"
        m        is the path to the normalizing data (I0 or whatever)
                 without the first level "directory".
        scanlist is the list of first level "directories" containing the 1D data
                 Example: The actual path has the form:
                 /whatever1/whatever2/counts
                 That means scanlist = ["/whatever1"]
                 and selection['y'] = "/whatever2/counts"
        """
        _logger.info("filelist = %s", filelist)
        _logger.info("selection = %s", selection)
        _logger.info("scanlist = %s", scanlist)

        if scanlist is not None:
            if type(scanlist) not in (type([]), type(())):
                scanlist = [scanlist]

        # all the files in the same source
        hdfStack = NexusDataSource.NexusDataSource(filelist)

        # if there is more than one file, it is assumed all the files have
        # the same structure.
        tmpHdf = hdfStack._sourceObjectList[0]
        entryNames = []
        for key in tmpHdf["/"].keys():
            try:
                if isinstance(tmpHdf["/"+key], h5py.Group):
                    entryNames.append(key)
            except KeyError:
                _logger.info("Broken link with key? <%s>" % key)

        # built the selection in terms of HDF terms
        # for the time being
        xSelectionList = selection.get('x', None)
        if not xSelectionList:
            xSelectionList = None
        if xSelectionList is not None:
            if type(xSelectionList) != type([]):
                xSelectionList = [xSelectionList]
            if len(xSelectionList):
                xSelection = xSelectionList[0]
            else:
                xSelection = None
        else:
            xSelection = None
        # only one y is taken
        ySelection = selection['y']
        if type(ySelection) == type([]):
            ySelectionList = list(ySelection)
            ySelection = ySelection[0]
        else:
            ySelectionList = [ySelection]

        # monitor selection
        mSelection = selection.get('m', None)
        if mSelection:
            if type(mSelection) != type([]):
                mSelection = [mSelection]
        else:
            mSelection = None
        if type(mSelection) == type([]):
            if len(mSelection):
                mSelection = mSelection[0]
            else:
                mSelection = None
        else:
            mSelection = None

        USE_JUST_KEYS = False
        # deal with the pathological case where the scanlist corresponds
        # to a selected top level dataset
        if len(entryNames) == 0:
            if scanlist is not None:
                if (ySelection in scanlist) or \
                   (xSelection in scanlist) or \
                   (mSelection in scanlist):
                    scanlist = None
                    USE_JUST_KEYS = True
            else:
                USE_JUST_KEYS = True
        elif len(entryNames) == 1:
            # deal with the SOLEIL case of one entry but with different name
            # in different files
            USE_JUST_KEYS = True
        elif scanlist in [None, []]:
            USE_JUST_KEYS = True
        if USE_JUST_KEYS:
            # if the scanlist is None, it is assumed we are interested on all
            # the scans containing the selection, not that all the scans
            # contain the selection.
            scanlist = []
            if 0:
                JUST_KEYS = False
                #expect same entry names in the files
                #Unfortunately this does not work for SOLEIL
                for entry in entryNames:
                    path = "/" + entry + ySelection
                    dirname = posixpath.dirname(path)
                    base = posixpath.basename(path)
                    try:
                        file_entry = tmpHdf[dirname]
                        if base in file_entry.keys():
                            scanlist.append(entry)
                    except Exception:
                        pass
            else:
                JUST_KEYS = True
                #expect same structure in the files even if the
                #names are different (SOLEIL ...)
                if len(entryNames):
                    i = 0
                    for entry in entryNames:
                        i += 1
                        path = "/" + entry + ySelection
                        dirname = posixpath.dirname(path)
                        base = posixpath.basename(path)
                        try:
                            file_entry = tmpHdf[dirname]
                            if hasattr(file_entry, "keys"):
                                if base in file_entry.keys():
                                    # this is the case of a selection inside a group
                                    scanlist.append("1.%d" % i)
                        except KeyError:
                            _logger.warning("%s not in file, ignoring.", dirname)
                    if not len(scanlist):
                        if not ySelection.startswith("/"):
                            path = "/" + ySelection
                        else:
                            path = ySelection
                        dirname = posixpath.dirname(path)
                        base = posixpath.basename(path)
                        try:
                            if dirname in tmpHdf["/"]:
                                # this is the case of a dataset at top plevel
                                # or having given the complete path
                                if base in tmpHdf[dirname]:
                                    JUST_KEYS = False
                                    scanlist.append("")
                            elif base in file_entry.keys():
                                JUST_KEYS = False
                                scanlist.append("")
                        except Exception:
                            #it will crash later on
                            pass
                else:
                    JUST_KEYS = False
                    scanlist.append("")
        else:
            try:
                # the ESRF uses "1.1" notation for the scans so this is ambiguous because
                # one does not know if the selection is based on scan name or scan order
                if scanlist[0] in entryNames:
                    # assumed the selection is based on scan name
                    JUST_KEYS = False
                else:
                    number, order = [int(x) for x in scanlist[0].split(".")]
                    JUST_KEYS = True
            except Exception:
                JUST_KEYS = False
            if not JUST_KEYS:
                for scan in scanlist:
                    if scan.startswith("/"):
                        t = scan[1:]
                    else:
                        t = scan
                    if t not in entryNames:
                        raise ValueError("Entry %s not in file" % scan)

        nFiles = len(filelist)
        nScans = len(scanlist)
        if JUST_KEYS:
            if not nScans:
                raise IOError("No entry contains the required data")

        _logger.debug("Retained number of files = %d", nFiles)
        _logger.debug("Retained number of scans = %d", nScans)

        # Now is to decide the number of mca ...
        # I assume all the scans contain the same number of mca
        if JUST_KEYS:
            path = "/" + entryNames[int(scanlist[0].split(".")[-1])-1] + ySelection
            if mSelection is not None:
                mpath = "/" + entryNames[int(scanlist[0].split(".")[-1])-1] + mSelection
            if xSelectionList is not None:
                xpathList = []
                for xSelection in xSelectionList:
                    xpath = "/" + entryNames[int(scanlist[0].split(".")[-1])-1] + xSelection
                    xpathList.append(xpath)
        else:
            path = scanlist[0] +  ySelection
            if mSelection is not None:
                mpath = scanlist[0] + mSelection
            if xSelectionList is not None:
                xpathList = []
                for xSelection in xSelectionList:
                    xpath = scanlist[0] + xSelection
                    xpathList.append(xpath)

        yDataset = tmpHdf[path]
        if (self.__dtype is None) or (mSelection is not None):
            self.__dtype = yDataset.dtype
            if self.__dtype in [numpy.int16, numpy.uint16]:
                self.__dtype = numpy.float32
            elif self.__dtype in [numpy.int32, numpy.uint32]:
                if mSelection:
                    self.__dtype = numpy.float32
                else:
                    self.__dtype = numpy.float64
            elif self.__dtype not in [numpy.float16, numpy.float32,
                                      numpy.float64]:
                # Some datasets form CLS (origin APS?) arrive as data format
                # equal to ">u2" and are not triggered as integer types
                _logger.debug("Not basic dataset type %s", self.__dtype)
                if ("%s" % self.__dtype).endswith("2"):
                    self.__dtype = numpy.float32
                else:
                    if mSelection:
                        self.__dtype = numpy.float32
                    else:
                        self.__dtype = numpy.float64

        # figure out the shape of the stack
        shape = yDataset.shape
        mcaIndex = selection.get('index', len(shape)-1)
        if mcaIndex == -1:
            mcaIndex = len(shape) - 1
        _logger.debug("mcaIndex = %d", mcaIndex)
        considerAsImages = False
        dim0, dim1, mcaDim = self.getDimensions(nFiles, nScans, shape,
                                                index=mcaIndex)
        _logger.debug("Returned dimensions = %d, %d, %d" % (dim0, dim1, mcaDim))
        try:
            if self.__dtype in [numpy.float32, numpy.int32]:
                bytefactor = 4
            elif self.__dtype in [numpy.int16, numpy.uint16]:
                bytefactor = 2
            elif self.__dtype in [numpy.int8, numpy.uint8]:
                bytefactor = 1
            else:
                bytefactor = 8

            neededMegaBytes = nFiles * dim0 * dim1 * (mcaDim * bytefactor/(1024*1024.))
            _logger.info("Using %d bytes per item" % bytefactor)
            _logger.info("Needed %d Megabytes" % neededMegaBytes)
            physicalMemory = None
            if hasattr(PhysicalMemory, "getAvailablePhysicalMemoryOrNone"):
                physicalMemory = PhysicalMemory.getAvailablePhysicalMemoryOrNone()
            if not physicalMemory:
                physicalMemory = PhysicalMemory.getPhysicalMemoryOrNone()
            else:
                _logger.info("Available physical memory %.1f GBytes" % \
                             (physicalMemory/(1024*1024*1024.)))
            if physicalMemory is None:
                # 6 Gigabytes of available memory
                # should be a good compromise in 2018
                physicalMemory = 6000
                _logger.info("Assumed physical memory %.1f MBytes" % physicalMemory)
            else:
                physicalMemory /= (1024*1024.)
            _logger.info("Using physical memory %.1f GBytes" % (physicalMemory/1024))
            if (neededMegaBytes > (0.95*physicalMemory))\
               and (nFiles == 1) and (len(shape) == 3):
                if self.__dtype0 is None:
                    if (bytefactor == 8) and (neededMegaBytes < (2*physicalMemory)):
                        # try reading as float32
                        print("Forcing the use of float32 data")
                        self.__dtype = numpy.float32
                    else:
                        raise MemoryError("Force dynamic loading")
                else:
                    raise MemoryError("Force dynamic loading")
            if (mcaIndex == 0) and ( nFiles == 1) and (nScans == 1) \
                and (len(yDataset.shape) > 1):
                #keep the original arrangement but in memory
                self.data = numpy.zeros(yDataset.shape, self.__dtype)
                considerAsImages = True
            else:
                # force arrangement as spectra
                self.data = numpy.zeros((dim0, dim1, mcaDim), self.__dtype)
            DONE = False
        except (MemoryError, ValueError):
            # some versions report ValueError instead of MemoryError
            if (nFiles == 1) and (len(shape) == 3):
                _logger.warning("Attempting dynamic loading")
                if mSelection is not None:
                    _logger.warning("Ignoring monitor")
                self.data = yDataset
                if mSelection is not None:
                    mdtype = tmpHdf[mpath].dtype
                    if mdtype not in [numpy.float64, numpy.float32]:
                        mdtype = numpy.float64
                    mDataset = numpy.asarray(tmpHdf[mpath], dtype=mdtype)
                    self.monitor = [mDataset]
                if xSelectionList is not None:
                    if len(xpathList) == 1:
                        xpath = xpathList[0]
                        xDataset = tmpHdf[xpath][()]
                        xDatasetList = [xDataset]
                        self.x = [xDataset]
                if h5py.version.version < '2.0':
                    #prevent automatic closing keeping a reference
                    #to the open file
                    self._fileReference = hdfStack
                DONE = True
            else:
                # what to do if the number of dimensions is only 2?
                raise

        # get the positioners information associated to the path
        positioners = {}
        try:
            positionersGroup = NexusTools.getPositionersGroup(tmpHdf, path)
            for motorName, motorValues in positionersGroup.items():
                positioners[motorName] = motorValues[()]
        except Exception:
            positionersGroup = None
            positioners = {}

        # get the mca information associated to the path
        mcaObjectPaths = NexusTools.getMcaObjectPaths(tmpHdf, path)
        _time = None
        _calibration = None
        _channels = None
        if considerAsImages:
            self._pathHasRelevantInfo = False
        else:
            numberOfRelevantInfoKeys = 0
            for objectPath in mcaObjectPaths:
                if objectPath not in ["counts", "target"]:
                    numberOfRelevantInfoKeys += 1
            if numberOfRelevantInfoKeys: # not just "counts" or "target"
                self._pathHasRelevantInfo = True
                if "live_time" in mcaObjectPaths:
                    if DONE:
                        # hopefully it will fit into memory
                        if mcaObjectPaths["live_time"] in tmpHdf:
                            _time = tmpHdf[mcaObjectPaths["live_time"]][()]
                        elif "::" in mcaObjectPaths["live_time"]:
                            tmpFileName, tmpDatasetPath = \
                                        mcaObjectPaths["live_time"].split("::")
                            with h5py.File(tmpFileName, "r") as tmpH5:
                                _time = tmpH5[tmpDatasetPath][()]
                        else:
                            del mcaObjectPaths["live_time"]
                    else:
                        # we have to have as many live times as MCA spectra
                        _time = numpy.zeros( \
                                    (self.data.shape[0] * self.data.shape[1]),
                                    dtype=numpy.float64)
                elif "elapsed_time" in mcaObjectPaths:
                    if DONE:
                        # hopefully it will fit into memory
                        if mcaObjectPaths["elapsed_time"] in tmpHdf:
                            _time = \
                                tmpHdf[mcaObjectPaths["elapsed_time"]][()]
                        elif "::" in mcaObjectPaths["elapsed_time"]:
                            tmpFileName, tmpDatasetPath = \
                                    mcaObjectPaths["elapsed_time"].split("::")
                            with h5py.File(tmpFileName, "r") as tmpH5:
                                _time = tmpH5[tmpDatasetPath][()]
                        else:
                            del mcaObjectPaths["elapsed_time"]
                    else:
                        # we have to have as many elpased times as MCA spectra
                        _time = numpy.zeros((self.data.shape[0] * self.data.shape[1]),
                                                numpy.float32)
                if "calibration" in mcaObjectPaths:
                    if mcaObjectPaths["calibration"] in tmpHdf:
                        _calibration = \
                                tmpHdf[mcaObjectPaths["calibration"]][()]
                    elif "::" in mcaObjectPaths["calibration"]:
                        tmpFileName, tmpDatasetPath = \
                                    mcaObjectPaths["calibration"].split("::")
                        with h5py.File(tmpFileName, "r") as tmpH5:
                            _calibration = tmpH5[tmpDatasetPath][()]
                    else:
                        del mcaObjectPaths["calibration"]
                if "channels" in mcaObjectPaths:
                    if mcaObjectPaths["channels"] in tmpHdf:
                        _channels = \
                                tmpHdf[mcaObjectPaths["channels"]][()]
                    elif "::" in mcaObjectPaths["channels"]:
                        tmpFileName, tmpDatasetPath = \
                                    mcaObjectPaths["channels"].split("::")
                        with h5py.File(tmpFileName, "r") as tmpH5:
                            _channels = tmpH5[tmpDatasetPath][()]
                    else:
                        del mcaObjectPaths["channels"]
            else:
                self._pathHasRelevantInfo = False

        if (not DONE) and (not considerAsImages):
            _logger.info("Data in memory as spectra")
            self.info["McaIndex"] = 2
            n = 0

            if dim0 == 1:
                self.onBegin(dim1)
            else:
                self.onBegin(dim0)
            self.incrProgressBar=0
            for hdf in hdfStack._sourceObjectList:
                entryNames = list(hdf["/"].keys())
                goodEntryNames = []
                for entry in entryNames:
                    tmpPath = "/" + entry
                    try:
                        if hasattr(hdf[tmpPath], "keys"):
                            goodEntryNames.append(entry)
                    except KeyError:
                        _logger.info("Broken link with key? <%s>" % tmpPath)

                for scan in scanlist:
                    IN_MEMORY = None
                    nStart = n
                    for ySelection in ySelectionList:
                        n = nStart
                        if JUST_KEYS:
                            entryName = goodEntryNames[int(scan.split(".")[-1])-1]
                            path = entryName + ySelection
                            if mSelection is not None:
                                mpath = entryName + mSelection
                                mdtype = hdf[mpath].dtype
                                if mdtype not in [numpy.float64, numpy.float32]:
                                    mdtype = numpy.float64
                                mDataset = numpy.asarray(hdf[mpath], dtype=mdtype)
                            if xSelectionList is not None:
                                xDatasetList = []
                                for xSelection in xSelectionList:
                                    xpath = entryName + xSelection
                                    xDataset = hdf[xpath][()]
                                    xDatasetList.append(xDataset)
                        else:
                            path = scan + ySelection
                            if mSelection is not None:
                                mpath = scan + mSelection
                                mdtype = hdf[mpath].dtype
                                if mdtype not in [numpy.float64, numpy.float32]:
                                    mdtype = numpy.float64
                                mDataset = numpy.asarray(hdf[mpath], dtype=mdtype)
                            if xSelectionList is not None:
                                xDatasetList = []
                                for xSelection in xSelectionList:
                                    xpath = scan + xSelection
                                    xDataset = hdf[xpath][()]
                                    xDatasetList.append(xDataset)
                        try:
                            yDataset = hdf[path]
                            tmpShape = yDataset.shape
                            totalBytes = numpy.ones((1,), yDataset.dtype).itemsize
                            for nItems in tmpShape:
                                totalBytes *= nItems
                            # should one be conservative or just try?
                            if (totalBytes/(1024.*1024.)) > (0.4 * physicalMemory):
                                _logger.info("Force dynamic loading of spectra")
                                #read from disk
                                IN_MEMORY = False
                            else:
                                #read the data into memory
                                _logger.info("Attempt to load whole map into memory")
                                yDataset = hdf[path][()]
                                IN_MEMORY = True
                        except (MemoryError, ValueError):
                            _logger.info("Dynamic loading of spectra")
                            yDataset = hdf[path]
                            IN_MEMORY = False
                        nMcaInYDataset = 1
                        for dim in yDataset.shape:
                            nMcaInYDataset *= dim
                        nMcaInYDataset = int(nMcaInYDataset/mcaDim)
                        timeData = None
                        if _time is not None:
                            if "live_time" in mcaObjectPaths:
                                # it is assumed that all have the same structure!!!
                                timePath = NexusTools.getMcaObjectPaths(hdf, path)["live_time"]
                            elif "elapsed_time" in mcaObjectPaths:
                                timePath = NexusTools.getMcaObjectPaths(hdf,
                                                                        path)["elapsed_time"]
                            if timePath in hdf:
                                timeData = hdf[timePath][()]
                            elif "::" in timePath:
                                externalFile, externalPath = timePath.split("::")
                                with h5py.File(externalFile, "r") as timeHdf:
                                    timeData = timeHdf[externalPath][()]
                        if mcaIndex != 0:
                            if IN_MEMORY:
                                yDataset.shape = -1, mcaDim
                            if mSelection is not None:
                                case = -1
                                nMonitorData = 1
                                for v in mDataset.shape:
                                    nMonitorData *= v
                                if nMonitorData == nMcaInYDataset:
                                    mDataset.shape = nMcaInYDataset
                                    case = 0
                                elif nMonitorData == (nMcaInYDataset * mcaDim):
                                    case = 1
                                    mDataset.shape = nMcaInYDataset, mcaDim
                                if case == -1:
                                    raise ValueError(\
                                        "I do not know how to handle this monitor data")
                            if timeData is not None:
                                case = -1
                                nTimeData = 1
                                for v in timeData.shape:
                                    nTimeData *= v
                                if nTimeData == nMcaInYDataset:
                                    timeData.shape = nMcaInYDataset
                                    case = 0
                                    _time[nStart: nStart + nMcaInYDataset] += timeData
                                if case == -1:
                                    _logger.warning("I do not know how to handle this time data")
                                    _logger.warning("Ignoring time information")
                                    _time= None
                            if (len(yDataset.shape) == 3) and\
                               (dim1 == yDataset.shape[1]):
                                mca = 0
                                deltaI = int(yDataset.shape[1]/dim1)
                                for ii in range(yDataset.shape[0]):
                                    i = int(n/dim1)
                                    yData = yDataset[ii:(ii+1)]
                                    yData.shape = -1, mcaDim
                                    if mSelection is not None:
                                        if case == 0:
                                            mData = numpy.outer(mDataset[mca:(mca+dim1)],
                                                                numpy.ones((mcaDim)))
                                            self.data[i, :, :] += yData / mData
                                        elif case == 1:
                                            mData = mDataset[mca:(mca+dim1), :]
                                            mData.shape = -1, mcaDim
                                            self.data[i, :, :]  += yData / mData
                                    else:
                                        self.data[i:(i+deltaI), :] += yData
                                    n += yDataset.shape[1]
                                    mca += dim1
                            else:
                                for mca in range(nMcaInYDataset):
                                    i = int(n/dim1)
                                    j = n % dim1
                                    if len(yDataset.shape) == 3:
                                        ii = int(mca/yDataset.shape[1])
                                        jj = mca % yDataset.shape[1]
                                        yData = yDataset[ii, jj]
                                    elif len(yDataset.shape) == 2:
                                        yData = yDataset[mca,:]
                                    elif len(yDataset.shape) == 1:
                                        yData = yDataset
                                    if mSelection is not None:
                                        if case == 0:
                                            self.data[i, j, :] += yData / mDataset[mca]
                                        elif case == 1:
                                            self.data[i, j, :] += yData / mDataset[mca, :]
                                    else:
                                        self.data[i, j, :] += yData
                                    n += 1
                        else:
                            if mSelection is not None:
                                case = -1
                                nMonitorData = 1
                                for v in mDataset.shape:
                                    nMonitorData *= v
                                if nMonitorData == yDataset.shape[0]:
                                    case = 3
                                    mDataset.shape = yDataset.shape[0]
                                elif nMonitorData == nMcaInYDataset:
                                    mDataset.shape = nMcaInYDataset
                                    case = 0
                                #elif nMonitorData == (yDataset.shape[1] * yDataset.shape[2]):
                                #    case = 1
                                #    mDataset.shape = yDataset.shape[1], yDataset.shape[2]
                                if case == -1:
                                    raise ValueError(\
                                        "I do not know how to handle this monitor data")
                            if IN_MEMORY:
                                yDataset.shape = mcaDim, -1
                            if len(yDataset.shape) != 3:
                                for mca in range(nMcaInYDataset):
                                    i = int(n/dim1)
                                    j = n % dim1
                                    if len(yDataset.shape) == 3:
                                        ii = int(mca/yDataset.shape[2])
                                        jj = mca % yDataset.shape[2]
                                        yData = yDataset[:, ii, jj]
                                    elif len(yDataset.shape) == 2:
                                        yData = yDataset[:, mca]
                                    elif len(yDataset.shape) == 1:
                                        yData = yDataset[:]
                                    if mSelection is not None:
                                        if case == 0:
                                            self.data[i, j, :] += yData / mDataset[mca]
                                        elif case == 1:
                                            self.data[i, j, :] += yData / mDataset[:, mca]
                                        elif case == 3:
                                            self.data[i, j, :] += yData / mDataset
                                    else:
                                        self.data[i, j, :] += yData
                                    n += 1
                            else:
                                #stack of images to be read as MCA
                                for nImage in range(yDataset.shape[0]):
                                    tmp = yDataset[nImage:(nImage+1)]
                                    if len(tmp.shape) == 3:
                                        i = int(n/dim1)
                                        j = n % dim1
                                        if 0:
                                            #this loop is extremely SLOW!!!(and useless)
                                            for ii in range(tmp.shape[1]):
                                                for jj in range(tmp.shape[2]):
                                                    self.data[i+ii, j+jj, nImage] += tmp[0, ii, jj]
                                        else:
                                            self.data[i:i+tmp.shape[1],
                                                      j:j+tmp.shape[2], nImage] += tmp[0]
                                if mSelection is not None:
                                    for mca in range(yDataset.shape[0]):
                                        i = int(n/dim1)
                                        j = n % dim1
                                        yData = self.data[i, j, :]
                                        if case == 0:
                                            self.data[i, j, :] += yData / mDataset[mca]
                                        elif case == 1:
                                            self.data[i, j, :]  += yData / mDataset[:, mca]
                                        n += 1
                                else:
                                    n += tmp.shape[1] * tmp.shape[2]
                        yDataset = None
                        if dim0 == 1:
                            self.onProgress(j)
                if dim0 != 1:
                    self.onProgress(i)
            self.onEnd()
        elif not DONE:
            # data into memory but as images
            self.info["McaIndex"] = mcaIndex
            for hdf in hdfStack._sourceObjectList:
                entryNames = list(hdf["/"].keys())
                for scan in scanlist:
                    for ySelection in ySelectionList:
                        if JUST_KEYS:
                            entryName = entryNames[int(scan.split(".")[-1])-1]
                            path = entryName + ySelection
                            if mSelection is not None:
                                mpath = entryName + mSelection
                                mDataset.shape
                            if xSelectionList is not None:
                                xDatasetList = []
                                for xSelection in xSelectionList:
                                    xpath = entryName + xSelection
                                    xDataset = hdf[xpath][()]
                                    xDatasetList.append(xDataset)
                        else:
                            path = scan + ySelection
                            if mSelection is not None:
                                mpath = scan + mSelection
                                mdtype = hdf[mpath].dtype
                                if mdtype not in [numpy.float64, numpy.float32]:
                                    mdtype = numpy.float64
                                mDataset = numpy.asarray(hdf[mpath], dtype=mdtype)
                            if xSelectionList is not None:
                                xDatasetList = []
                                for xSelection in xSelectionList:
                                    xpath = scan + xSelection
                                    xDataset = hdf[xpath][()]
                                    xDatasetList.append(xDataset)
                        try:
                            yDataset = hdf[path][()]
                            IN_MEMORY = True
                        except (MemoryError, ValueError):
                            _logger.info("Dynamic loading of images")
                            yDataset = hdf[path]
                            IN_MEMORY = False                     
                        if mSelection is not None:
                            nMonitorData = mDataset.size
                            case = -1
                            yDatasetShape = yDataset.shape
                            if nMonitorData == yDatasetShape[0]:
                                #as many monitor data as images
                                mDataset.shape = yDatasetShape[0]
                                case = 0
                            elif nMonitorData == (yDatasetShape[1] * yDatasetShape[2]):
                                #as many monitorData as pixels
                                case = 1
                                mDataset.shape = yDatasetShape[1], yDatasetShape[2]
                            if case == -1:
                                raise ValueError(\
                                    "I do not know how to handle this monitor data")
                            if case == 0:
                                for i in range(yDatasetShape[0]):
                                    self.data[i] += yDataset[i][()] / mDataset[i]
                            elif case == 1:
                                for i in range(yDataset.shape[0]):
                                    self.data[i] += yDataset[i] / mDataset
                        else:
                            if IN_MEMORY:
                                self.data += yDataset
                            else:
                                for i in range(yDataset.shape[0]):
                                    self.data[i:i+1] += yDataset[i:i+1]
        else:
            self.info["McaIndex"] = mcaIndex
            if _time:
                nRequiredValues = 1
                for i in range(len(self.data.shape)):
                    if i != mcaIndex:
                        nRequiredValues *= self.data.shape[i]
                if _time.size != nRequiredValues:
                    _logger.warning("I do not know how to interpret the time information")
                    _logger.warning("Ignoring time information")
                    _time = None
                else:
                    _time.shape = -1

        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = filelist
        self.info["Size"]       = 1
        self.info["NumberOfFiles"] = 1
        if mcaIndex == 0:
            self.info["FileIndex"] = 1
        else:
            self.info["FileIndex"] = 0
        if _calibration is not None:
            self.info['McaCalib'] = _calibration
        else:
            self.info['McaCalib'] = [ 0.0, 1.0, 0.0]
        shape = self.data.shape
        nSpectra = 1
        for i in range(len(shape)):
            key = 'Dim_%d' % (i+1,)
            self.info[key] = shape[i]
            if i != self.info['McaIndex']:
                nSpectra *= shape[i]
        self.info['Channel0'] = 0

        # try to get scales
        scaleList = []
        if xSelectionList is not None:
            if len(xDatasetList) == 1:
                xDataset = xDatasetList[0]
                if xDataset.size == shape[self.info['McaIndex']]:
                    # assuming providing channels
                    self.x = [xDataset.reshape(-1)]
                else:
                    _logger.warning("Ignoring channels selection %s" % xSelectionList)
            elif len(xDatasetList) == len(self.data.shape):
                # assuming providing spatial coordinates and channels
                goodScale = 0
                for i in range(len(self.data.shape)):
                    dataset = xDatasetList[i]
                    datasize = self.data.shape[i]
                    if dataset.size == datasize:
                        goodScale += 1
                    else:
                        _logger.warning("Dimensions do not match %d != %d"  % \
                                        (dataset.size, datasize))
                if goodScale == len(self.data.shape):
                    scaleList = []
                    for i in range(len(self.data.shape)):
                        dataset = xDatasetList[i].reshape(-1)
                        datasize = self.data.shape[i]
                        if i == mcaIndex:
                            self.x = [dataset]
                        else:
                            origin = dataset[0]
                            if dataset.size > 1:
                                delta = numpy.mean(dataset[1:] - dataset[:-1],
                                                   dtype=numpy.float32)
                            else:
                                delta = 1.0
                            scaleList.append([origin, delta])
                    if goodScale == 3:
                        xScale = scaleList[1]
                        yScale = scaleList[0]
                    else:
                        _logger.warning("Spatial dimensions ignored")
                else:
                    _logger.warning("Ignoring dimension selections %s" % xSelectionList)
            elif len(xDatasetList) == (len(self.data.shape) - 1):
                scaleList = []
                for i in range(len(self.data.shape)):
                    if i == mcaIndex:
                        continue
                    dataset = xDatasetList[i].reshape(-1)
                    datasize = self.data.shape[i]
                    if dataset.size == datasize:
                        origin = dataset[0]
                        if dataset.size > 1:
                            delta = numpy.mean(dataset[1:] - dataset[:-1],
                                               dtype=numpy.float32)
                        else:
                            delta = 1.0
                        scaleList.append([origin, delta])
                    else:
                        _logger.warning("Dimensions do not match %d != %d"  % \
                                        (dataset.size, datasize))

                if len(scaleList) == 2:
                    xScale = scaleList[1]
                    yScale = scaleList[0]
                else:
                    _logger.warning("Ignoring dimension selections %s" % xSelectionList)
            else:
                _logger.warning("Ignoring axes selection %s" % xSelectionList)
        elif _channels is not None:
            _channels.shape = -1
            self.x = [_channels]
        if _time is not None:
            self.info["McaLiveTime"] = _time
        if positionersGroup:
            self.info["positioners"] = positioners
        if (len(scaleList) == 0) and (nFiles == 1) and (nScans == 1) \
           and (len(self.data.shape) == 3):
            # try to figure out the scales from the data layout
            originalDir = posixpath.dirname(mcaObjectPaths["counts"])
            targetDir = posixpath.dirname(mcaObjectPaths["target"])
            for countsDir in [originalDir,
                              posixpath.join(originalDir, "map"),
                              targetDir,
                              posixpath.join(targetDir, "map")]:
                dims = []
                for i in range(3):
                    dimPath = posixpath.join(countsDir, "dim%d" % i)
                    if dimPath in tmpHdf:
                        item = tmpHdf[dimPath]
                    elif "::" in tmpHdf:
                        tmpFileName, tmpDatasetPath = dimPath.split("::")
                        with h5py.File(tmpFileName, "r") as tmpH5:
                            item = tmpH5[tmpDatasetPath][()]
                    else:
                        continue
                    if hasattr(item, "shape") and hasattr(item, "size"):
                        if item.size == self.data.shape[i]:
                            dims.append(item[()].reshape(-1))
                if len(dims) == len(self.data.shape):
                    break
            if len(dims) == len(self.data.shape):
                scaleList = []
                for i in range(len(self.data.shape)):
                    if i == mcaIndex:
                        continue
                    dataset = dims[i]
                    origin = dataset[0]
                    if dataset.size > 1:
                        delta = numpy.mean(dataset[1:] - dataset[:-1],
                                               dtype=numpy.float32)
                    else:
                        delta = 1.0
                    scaleList.append([origin, delta])

                if len(scaleList) == 2:
                    xScale = scaleList[1]
                    yScale = scaleList[0]

        if len(self.data.shape) == 3:
            if len(scaleList) == 2:
                self.info["xScale"] = xScale
                self.info["yScale"] = yScale

    def getDimensions(self, nFiles, nScans, shape, index=None):
        #somebody may want to overwrite this
        """
        Returns the shape of the final stack as (Dim0, Dim1, Nchannels)
        """
        if index is None:
            index = -1
        if index == -1:
            index = len(shape) - 1
        _logger.debug("INDEX = %d", index)
        #figure out the shape of the stack
        if len(shape) == 0:
            #a scalar?
            raise ValueError("Selection corresponds to a scalar")
        elif len(shape) == 1:
            #nchannels
            nMca = 1
        elif len(shape) == 2:
            if index == 0:
                #npoints x nchannels
                nMca = shape[1]
            else:
                #npoints x nchannels
                nMca = shape[0]
        elif len(shape) == 3:
            if index in [2, -1]:
                #dim1 x dim2 x nchannels
                nMca = shape[0] * shape[1]
            elif index == 0:
                nMca = shape[1] * shape[2]
            else:
                raise IndexError("Only first and last dimensions handled")
        else:
            nMca = 1
            for i in range(len(shape)):
                if i == index:
                    continue
                nMca *= shape[i]

        mcaDim = shape[index]
        _logger.debug("nMca = %d", nMca)
        _logger.debug("mcaDim = %s", mcaDim)

        # HDF allows to work directly from the files without loading
        # them into memory.
        if (nScans == 1) and (nFiles > 1):
            if nMca == 1:
                #specfile like case
                dim0 = nFiles
                dim1 = nMca * nScans # nScans is 1
            else:
                #ESRF EDF like case
                dim0 = nFiles
                dim1 = nMca * nScans # nScans is 1
        elif (nScans == 1) and (nFiles == 1):
            if nMca == 1:
                #specfile like single mca
                dim0 = nFiles # it is 1
                dim1 = nMca * nScans # nScans is 1
            elif len(shape) == 2:
                dim0 = nFiles # it is 1
                dim1 = nMca * nScans # nScans is 1
            elif len(shape) == 3:
                if index == 0:
                    dim0 = shape[1]
                    dim1 = shape[2]
                else:
                    dim0 = shape[0]
                    dim1 = shape[1]
            else:
                #specfile like multiple mca
                dim0 = nFiles # it is 1
                dim1 = nMca * nScans  # nScans is 1
        elif (nScans > 1)  and (nFiles == 1):
            if nMca == 1:
                #specfile like case
                dim0 = nFiles
                dim1 = nMca * nScans
            elif nMca > 1:
                if len(shape) == 1:
                    #specfile like case
                    dim0 = nFiles
                    dim1 = nMca * nScans
                elif len(shape) == 2:
                    dim0 = nScans
                    dim1 = nMca     #shape[0]
                elif len(shape) == 3:
                    if (shape[0] == 1) or (shape[1] == 1):
                        dim0 = nScans
                        dim1 = nMca
                    else:
                        #The user will have to decide the shape
                        dim0 = 1
                        dim1 = nScans * nMca
                else:
                    #The user will have to decide the shape
                    dim0 = 1
                    dim1 = nScans * nMca
        elif (nScans > 1) and (nFiles > 1):
            dim0 = nFiles
            dim1 = nMca * nScans
        else:
            #I should not reach this point
            raise ValueError("Unhandled case")

        return dim0, dim1, shape[index]

    def onBegin(self, n):
        pass

    def onProgress(self, n):
        pass

    def onEnd(self):
        pass
