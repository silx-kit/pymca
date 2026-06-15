#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
import sys
import os
import numpy
import logging
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaIO import specfilewrapper as specfile
from PyMca5.PyMcaCore import SpecFileDataSource

HDF5 = False
try:
    import h5py
    HDF5 = True
except Exception:
    pass
SOURCE_TYPE = "SpecFileStack"
_logger = logging.getLogger(__name__)


X_AXIS = 0
Y_AXIS = 1
Z_AXIS = 2


class SpecFileStack(DataObject.DataObject):
    def __init__(self, filelist=None):
        DataObject.DataObject.__init__(self)
        self.incrProgressBar = 0
        self.__keyList = []
        if filelist is not None:
            if type(filelist) != type([]):
                filelist = [filelist]
            if len(filelist) == 1:
                self.loadIndexedStack(filelist)
            else:
                self.loadFileList(filelist)

    def loadFileList(self, filelist, fileindex=0, shape=None):
        if type(filelist) == type(''):
            filelist = [filelist]
        self.__keyList = []
        self.sourceName = filelist
        self.__indexedStack = True
        self.sourceType = SOURCE_TYPE
        self.info = {}
        self.nbFiles = len(filelist)

        # read first file
        # get information
        tempInstance = SpecFileDataSource.SpecFileDataSource(filelist[0])
        keylist = tempInstance.getSourceInfo()['KeyList']
        nscans = len(keylist)        # that is the number of scans
        nmca = 0
        numberofdetectors = 0
        for key in keylist:
            info = tempInstance.getKeyInfo(key)
            numberofmca = info['NbMca']
            if numberofmca > 0:
                numberofdetectors = info['NbMcaDet']
            scantype = info["ScanType"]
            if numberofmca:
                nmca += numberofmca
        if numberofdetectors == 0:
            raise ValueError("No MCA found in file %s" % filelist[0])

        if (nscans > 1) and ((nmca // numberofdetectors) == nscans):
            SLOW_METHOD = True
        else:
            SLOW_METHOD = False
        # get last mca of first point
        key = "%s.1.%s" % (keylist[-1], numberofmca)
        dataObject = tempInstance._getMcaData(key)
        self.info.update(dataObject.info)
        arrRet = dataObject.data
        self.onBegin(self.nbFiles * nmca // numberofdetectors)

        self.incrProgressBar = 0
        if info['NbMcaDet'] > 1:
            # Should I generate a map for each mca and not just for the last one as I am doing?
            iterlist = range(info['NbMcaDet'], info['NbMca'] + 1, info['NbMcaDet'])
        else:
            iterlist = [1]
        if SLOW_METHOD and shape is None:
            self.data = numpy.zeros((self.nbFiles,
                                     nmca // numberofdetectors,
                                     arrRet.shape[0]),
                                     arrRet.dtype.char)
            nTimes = self.nbFiles * (nmca // numberofdetectors)
            filecounter = 0
            for key in ["McaLiveTime", "McaElapsedTime"]:
                if key in dataObject.info:
                    self.info[key] = numpy.zeros((nTimes,), numpy.float32)

            # positioners
            key = "MotorNames"
            positioners = None
            if key in dataObject.info:
                positioners = {}
                for mne in dataObject.info[key]:
                    positioners[mne] = numpy.zeros((nTimes,), numpy.float32)

            nTimes = -1
            for tempFileName in filelist:
                tempInstance = SpecFileDataSource.SpecFileDataSource(tempFileName)
                mca_number = -1
                for keyindex in keylist:
                    info = tempInstance.getKeyInfo(keyindex)
                    numberofmca = info['NbMca']
                    if numberofmca <= 0:
                        continue
                    # the positioners are for all the mca in the scan

                    # only the last mca is read
                    key = "%s.1.%s" % (keyindex, numberofmca)
                    dataObject = tempInstance._getMcaData(key)
                    arrRet = dataObject.data
                    mca_number += 1
                    nTimes += 1
                    for i in iterlist:
                        # mcadata = scan_obj.mca(i)
                        self.data[filecounter,
                                  mca_number,
                                  :] = arrRet[:]
                        self.incrProgressBar += 1
                        for timeKey in ["McaElapsedTime", "McaLiveTime"]:
                            if timeKey in dataObject.info:
                                self.info[timeKey][nTimes] = \
                                    dataObject.info[timeKey]

                        if positioners and  "MotorNames" in dataObject.info:
                            for mne in positioners:
                                if mne in dataObject.info["MotorNames"]:
                                    mneIdx = \
                                           dataObject.info["MotorNames"].index(mne)
                                    positioners[mne][nTimes] = \
                                             dataObject.info["MotorValues"][mneIdx]
                        self.onProgress(self.incrProgressBar)
                filecounter += 1
            if positioners:
                self.info["positioners"] = positioners
        elif shape is None and (self.nbFiles == 1) and (iterlist == [1]):
            # it can only be here if there is one file
            # it can only be here if there is only one scan
            # it can only be here if there is only one detector
            self.data = numpy.zeros((1,
                                     numberofmca,
                                     arrRet.shape[0]),
                                     arrRet.dtype.char)
            # when reading fast we do not read the time information
            # therefore we have to remove it from the info
            self._cleanupTimeInfo()
            for tempFileName in filelist:
                tempInstance = specfile.Specfile(tempFileName)
                # it can only be here if there is one scan per file
                # prevent problems if the scan number is different
                # scan = tempInstance.select(keylist[-1])
                scan = tempInstance[-1]
                iterationList = range(scan.nbmca())
                for i in iterationList:
                    # mcadata = scan_obj.mca(i)
                    self.data[0,
                              i,
                              :] = scan.mca(i + 1)[:]
                    self.incrProgressBar += 1
                    self.onProgress(self.incrProgressBar)
                filecounter = 1
        elif shape is None:
            # it can only be here if there is one scan per file
            # when reading fast we do not read the time information
            # therefore we have to remove it from the info
            self._cleanupTimeInfo()
            try:
                self.data = numpy.zeros((self.nbFiles,
                                         numberofmca // numberofdetectors,
                                         arrRet.shape[0]),
                                         arrRet.dtype.char)
                filecounter = 0
                for tempFileName in filelist:
                    tempInstance = specfile.Specfile(tempFileName)
                    # it can only be here if there is one scan per file
                    # prevent problems if the scan number is different
                    # scan = tempInstance.select(keylist[-1])
                    scan = tempInstance[-1]
                    for i in iterlist:
                        # mcadata = scan_obj.mca(i)
                        self.data[filecounter,
                                  0,
                                  :] = scan.mca(i)[:]
                        self.incrProgressBar += 1
                        self.onProgress(self.incrProgressBar)
                    filecounter += 1
            except MemoryError:
                qtflag = False
                if 'PyMca5.PyMcaGui.PyMcaQt' in sys.modules:
                    qtflag = True
                hdf5done = False
                if HDF5 and qtflag:
                    from PyMca5.PyMcaGui import PyMcaQt as qt
                    from PyMca5.PyMcaIO import ArraySave
                    msg = qt.QMessageBox.information( \
                             None,
                             "Memory error\n",
                             "Do you want to convert your data to HDF5?\n",
                             qt.QMessageBox.Yes,qt.QMessageBox.No)
                    if msg != qt.QMessageBox.No:
                        hdf5file = qt.QFileDialog.getSaveFileName( \
                                      None,
                                      "Please select output file name",
                                      os.path.dirname(filelist[0]),
                                      "HDF5 files *.h5")
                        if not len(hdf5file):
                            raise IOError("Invalid output file")
                        hdf5file = qt.safe_str(hdf5file)
                        if not hdf5file.endswith(".h5"):
                            hdf5file += ".h5"

                        # get the final shape
                        from PyMca5.RGBCorrelatorWidget import ImageShapeDialog
                        stackImageShape = self.nbFiles,\
                                     int(numberofmca/numberofdetectors)
                        dialog = ImageShapeDialog(None, shape = stackImageShape)
                        dialog.setModal(True)
                        ret = dialog.exec()
                        if ret:
                            stackImageShape = dialog.getImageShape()
                            dialog.close()
                            del dialog
                        hdf, self.data = ArraySave.getHDF5FileInstanceAndBuffer( \
                                       hdf5file,
                                       (stackImageShape[0],
                                        stackImageShape[1],
                                        arrRet.shape[0]),
                                       compression=None,
                                       interpretation="spectrum")
                        nRow = 0
                        nCol = 0
                        for tempFileName in filelist:
                            tempInstance = specfile.Specfile(tempFileName)
                            # it can only be here if there is one scan per file
                            # prevent problems if the scan number is different
                            # scan = tempInstance.select(keylist[-1])
                            scan = tempInstance[-1]
                            nRow = int(self.incrProgressBar / stackImageShape[1])
                            nCol = self.incrProgressBar % stackImageShape[1]
                            for i in iterlist:
                                # mcadata = scan_obj.mca(i)
                                self.data[nRow,
                                          nCol,
                                          :] = scan.mca(i)[:]
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                        hdf5done = True
                        hdf.flush()
                    self.onEnd()
                    self.info["SourceType"] = "HDF5Stack1D"
                    self.info["McaIndex"] = 2
                    self.info["FileIndex"] = 0
                    self.info["SourceName"] = [hdf5file]
                    self.info["NumberOfFiles"] = 1
                    self.info["Size"] = 1
                    return
                else:
                    raise
        else:
            # time information not read
            self._cleanupTimeInfo()
            sampling_order = 1
            s0 = shape[0]
            s1 = shape[1]
            MEMORY_ERROR = False
            try:
                self.data = numpy.zeros((shape[0],
                                         shape[1],
                                         arrRet.shape[0]),
                                         arrRet.dtype.char)
            except MemoryError:
                try:
                    self.data = numpy.zeros((shape[0],
                                             shape[1],
                                             arrRet.shape[0]),
                                             numpy.float32)
                except MemoryError:
                    MEMORY_ERROR = True
            while MEMORY_ERROR:
                try:
                    for i in range(5):
                        print("\7")
                    sampling_order += 1
                    _logger.warning("**************************************************")
                    _logger.warning(" Memory error!, attempting %dx%d sub-sampling ",
                                    sampling_order, sampling_order)
                    _logger.warning("**************************************************")
                    s0 = int(shape[0] / sampling_order)
                    s1 = int(shape[1] / sampling_order)
                    #if shape[0] % sampling_order:
                    #    s0 = s0 + 1
                    #if shape[1] % sampling_order:
                    #    s1 = s1 + 1
                    self.data = numpy.zeros((s0, s1,
                                             arrRet.shape[0]),
                                             numpy.float32)
                    MEMORY_ERROR = False
                except MemoryError:
                    pass
            filecounter = 0
            for j in range(s0):
                filecounter = (j * sampling_order) * shape[1]
                for k in range(s1):
                    tempFileName = filelist[filecounter]
                    tempInstance = specfile.Specfile(tempFileName)
                    if tempInstance is None:
                        if not os.path.exists(tempFileName):
                            _logger.error("File %s does not exists", tempFileName)
                            raise IOError(
                                "File %s does not exists" % tempFileName)
                    scan = tempInstance.select(keylist[-1])
                    for i in iterlist:
                        # sum the present mcas
                        self.data[j,
                                  k,
                                  :] += scan.mca(i)[:]
                        self.incrProgressBar += 1
                        self.onProgress(self.incrProgressBar)
                    filecounter += sampling_order
            self.nbFiles = s0 * s1
        self.onEnd()

        """
        # Scan types
        # ----------
        #SF_EMPTY       = 0        # empty scan
        #SF_SCAN        = 1        # non-empty scan
        #SF_MESH        = 2        # mesh scan
        #SF_MCA         = 4        # single mca
        #SF_NMCA        = 8        # multi mca (more than 1 mca per acq)

        case = None
        if scantype == (SpecFileDataSource.SF_MESH + \
                        SpecFileDataSource.SF_MCA):
            # SINGLE MESH + SINGLE MCA
            # nfiles  = 1
            # nscans  = 1
            # nmca    = 1
            # there is a danger if it can be considered an indexed file ...
            pass

        elif scantype == (SpecFileDataSource.SF_MESH + \
                        SpecFileDataSource.SF_NMCA):
            # SINGLE MESH + MULTIPLE MCA
            # nfiles  = 1
            # nscans  = 1
            # nmca    > 1
            # there is a danger if it can be considered an indexed file ...
            #for the time being I take last mca
            pass

        elif scantype == (SpecFileDataSource.SF_SCAN+ \
                          SpecFileDataSource.SF_MCA):
            #Assumed scans containing always 1 detector
            pass

        elif scantype == (SpecFileDataSource.SF_MCA):
            #Assumed scans containing always 1 detector
            pass

        elif scantype == (SpecFileDataSource.SF_SCAN+ \
                          SpecFileDataSource.SF_NMCA):
            #Assumed scans containing the same number of detectors
            #for the time being I take last mca
            pass

        elif scantype == (SpecFileDataSource.SF_NMCA):
            #Assumed scans containing the same number of detectors
            #for the time being I take last mca
            pass

        else:
            raise ValueError, "Unhandled scan type = %s" % scantype

        """

        self.__nFiles = self.nbFiles
        self.__nImagesPerFile = 1
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i + 1,)
            self.info[key] = shape[i]
        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName
        self.info["Size"] = self.__nFiles * self.__nImagesPerFile
        self.info["NumberOfFiles"] = self.__nFiles * 1
        self.info["FileIndex"] = fileindex

    def _cleanupTimeInfo(self):
        for timeKey in ["McaElapsedTime", "McaLiveTime"]:
            if timeKey in self.info:
                del self.info[timeKey]

    def onBegin(self, n):
        pass

    def onProgress(self, n):
        pass

    def onEnd(self):
        pass

    def loadIndexedStack(self,filename, begin=None, end=None,
                         skip = None, fileindex=0):
        #if begin is None: begin = 0
        if type(filename) == type([]):
            filename = filename[0]
        if not os.path.exists(filename):
            raise IOError("File %s does not exists" % filename)
        name = os.path.basename(filename)
        n = len(name)
        i = 1
        numbers = ['0', '1', '2', '3', '4', '5',
                   '6', '7', '8', '9']
        while (i <= n):
            c = name[n - i:n - i + 1]
            if c in numbers:
                break
            i += 1
        suffix = name[n - i + 1:]
        if len(name) == len(suffix):
            # just one file, one should use standard widget
            # and not this one.
            self.loadFileList(filename, fileindex=fileindex)
        else:
            nchain = []
            while (i <= n):
                c = name[n - i:n - i + 1]
                if c not in numbers:
                    break
                else:
                    nchain.append(c)
                i += 1
            number = ""
            nchain.reverse()
            for c in nchain:
                number += c
            fformat = "%" + "0%dd" % len(number)
            if (len(number) + len(suffix)) == len(name):
                prefix = ""
            else:
                prefix = name[0:n - i + 1]
            prefix = os.path.join(os.path.dirname(filename), prefix)
            if not os.path.exists(prefix + number + suffix):
                _logger.warning("Internal error in EDFStack")
                _logger.warning("file should exist: %s", prefix + number + suffix)
                return
            i = 0
            if begin is None:
                begin = 0
                testname = prefix + fformat % begin + suffix
                while not os.path.exists(prefix + fformat % begin + suffix):
                    begin += 1
                    testname = prefix + fformat % begin + suffix
                    if len(testname) > len(filename):
                        break
                i = begin
            else:
                i = begin
            if not os.path.exists(prefix + fformat % i + suffix):
                raise ValueError("Invalid start index file = %s" % \
                                 (prefix + fformat % i + suffix))
            f = prefix + fformat % i + suffix
            filelist = []
            while os.path.exists(f):
                filelist.append(f)
                i += 1
                if end is not None:
                    if i > end:
                        break
                f = prefix + fformat % i + suffix
            self.loadFileList(filelist, fileindex=fileindex)

    def getSourceInfo(self):
        sourceInfo = {}
        sourceInfo["SourceType"] = SOURCE_TYPE
        if self.__keyList == []:
            for i in range(1, self.__nFiles + 1):
                for j in range(1, self.__nImages + 1):
                    self.__keyList.append("%d.%d" % (i, j))
        sourceInfo["KeyList"] = self.__keyList

    def getKeyInfo(self, key):
        _logger.info("Not implemented")
        return {}

    def isIndexedStack(self):
        return self.__indexedStack

    def getZSelectionArray(self, z=0):
        return (self.data[:, :, z]).astype(numpy.float64)

    def getXYSelectionArray(self, coord=(0, 0)):
        x, y = coord
        return (self.data[y, x, :]).astype(numpy.float64)

if __name__ == "__main__":
    stack = SpecFileStack()
    if len(sys.argv) > 1:
        stack.loadIndexedStack(sys.argv[1])
    else:
        print("Usage: python SpecFileStack.py indexed_file")
