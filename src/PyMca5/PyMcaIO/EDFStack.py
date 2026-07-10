#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaIO import EdfFile
from PyMca5.PyMcaCore import EdfFileDataSource
from PyMca5.PyMcaMisc import PhysicalMemory
import numpy
import sys
import os
import logging

# Offer automatic conversion to HDF5 in case of lacking
# memory to hold the Stack.
HDF5 = False
try:
    import h5py
    HDF5 = True
except Exception:
    pass


SOURCE_TYPE = "EdfFileStack"
_logger = logging.getLogger(__name__)


X_AXIS=0
Y_AXIS=1
Z_AXIS=2

class EDFStack(DataObject.DataObject):
    def __init__(self, filelist = None, imagestack=None, dtype=None):
        DataObject.DataObject.__init__(self)
        self.incrProgressBar=0
        self.__keyList = []
        if imagestack is None:
            self.__imageStack = False
        else:
            self.__imageStack = imagestack
        self.__dtype = dtype
        if filelist is not None:
            if type(filelist) != type([]):
                filelist = [filelist]
            if len(filelist) == 1:
                self.loadIndexedStack(filelist)
            else:
                self.loadFileList(filelist)

    def loadFileList(self, filelist, fileindex=0):
        if type(filelist) == type(''):filelist = [filelist]
        self.__keyList = []
        self.sourceName = filelist
        self.__indexedStack = True
        self.sourceType = SOURCE_TYPE
        self.info = {}
        self.nbFiles=len(filelist)
        fileSampling = 1
        mcaSampling = 1

        #read first edf file
        #get information
        tempEdf=EdfFileDataSource.EdfFileDataSource(filelist[0])
        keylist = tempEdf.getSourceInfo()['KeyList']
        nImages = len(keylist)
        dataObject = tempEdf.getDataObject(keylist[0])
        self.info.update(dataObject.info)
        if len(dataObject.data.shape) == 3:
            #this is already a stack
            self.data = dataObject.data
            self.__nFiles         = 1
            self.__nImagesPerFile = nImages
            shape = self.data.shape
            for i in range(len(shape)):
                key = 'Dim_%d' % (i+1,)
                self.info[key] = shape[i]
            self.info["SourceType"] = SOURCE_TYPE
            self.info["SourceName"] = filelist[0]
            self.info["Size"]       = 1
            self.info["NumberOfFiles"] = 1
            self.info["FileIndex"] = fileindex
            return
        arrRet = dataObject.data
        if self.__dtype is None:
            self.__dtype = arrRet.dtype

        self.onBegin(self.nbFiles)
        singleImageShape = arrRet.shape
        actualImageStack = False
        if (fileindex == 2) or (self.__imageStack):
            self.__imageStack = True
            if len(singleImageShape) == 1:
                #single line
                #be ready for specfile stack?
                self.onEnd()
                raise IOError("Not implemented yet")
            else:
                if nImages > 1:
                    #this is not the common case
                    #should I try to convert it to a standard one
                    #using a 3D matrix or keep as 4D matrix?
                    if self.nbFiles > 1:
                        raise IOError(\
                            "Multiple files with multiple images implemented yet")
                    self.data = numpy.zeros((arrRet.shape[0],
                                               arrRet.shape[1],
                                               nImages * self.nbFiles),
                                               self.__dtype)
                    self.incrProgressBar=0
                    for tempEdfFileName in filelist:
                        tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                        for i in range(nImages):
                            pieceOfStack=tempEdf.GetData(i)
                            self.data[:,:,
                                      nImages*self.incrProgressBar+i] = \
                                                      pieceOfStack[:,:]
                        self.incrProgressBar += 1
                else:
                    #this is the common case
                    try:
                        # calculate needed megabytes
                        if self.__dtype == numpy.float64:
                            bytefactor = 8
                        else:
                            bytefactor = 4
                        needed_ = self.nbFiles * \
                                   arrRet.shape[0] *\
                                   arrRet.shape[1] * bytefactor
                        physicalMemory = PhysicalMemory.getPhysicalMemoryOrNone()
                        if physicalMemory is not None:
                            # spare 5% or memory
                            if physicalMemory < (1.05 * needed_):
                                raise MemoryError("Not enough physical memory available")
                        if self.__imageStack:
                            self.data = numpy.zeros((self.nbFiles,
                                                     arrRet.shape[0],
                                                     arrRet.shape[1]),
                                                     self.__dtype)
                            self.incrProgressBar=0
                            for tempEdfFileName in filelist:
                                tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                pieceOfStack=tempEdf.GetData(0)
                                self.data[self.incrProgressBar] = pieceOfStack
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                            actualImageStack = True
                        else:
                            self.data = numpy.zeros((arrRet.shape[0],
                                                     arrRet.shape[1],
                                                     self.nbFiles),
                                                     self.__dtype)
                            self.incrProgressBar=0
                            for tempEdfFileName in filelist:
                                tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                pieceOfStack=tempEdf.GetData(0)
                                self.data[:,:, self.incrProgressBar] = pieceOfStack
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                    except (MemoryError, ValueError):
                        hdf5done = False
                        if HDF5 and (('PyMcaQt' in sys.modules) or\
                           ('PyMca.PyMcaQt' in sys.modules)):
                            from PyMca5 import PyMcaQt as qt
                            from PyMca5 import ArraySave
                            msg=qt.QMessageBox.information( None,
                              "Memory error\n",
                              "Do you want to convert your data to HDF5?\n",
                              qt.QMessageBox.Yes,qt.QMessageBox.No)
                            if msg != qt.QMessageBox.No:
                                hdf5file = qt.QFileDialog.getSaveFileName(None,
                                            "Please select output file name",
                                            os.path.dirname(filelist[0]),
                                            "HDF5 files *.h5")
                                if not len(hdf5file):
                                    raise IOError("Invalid output file")
                                hdf5file = qt.safe_str(hdf5file)
                                if not hdf5file.endswith(".h5"):
                                    hdf5file += ".h5"
                                hdf, self.data =  ArraySave.getHDF5FileInstanceAndBuffer(hdf5file,
                                              (self.nbFiles,
                                               arrRet.shape[0],
                                               arrRet.shape[1]))
                                self.incrProgressBar=0
                                for tempEdfFileName in filelist:
                                    tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                    pieceOfStack=tempEdf.GetData(0)
                                    self.data[self.incrProgressBar,:,:] = pieceOfStack[:,:]
                                    hdf.flush()
                                    self.incrProgressBar += 1
                                    self.onProgress(self.incrProgressBar)
                                hdf5done = True
                        if not hdf5done:
                            for i in range(3):
                                print("\7")
                            samplingStep = None
                            i = 2
                            while samplingStep is None:
                                _logger.warning("**************************************************")
                                _logger.warning(" Memory error!, attempting %dx%d sampling reduction ", i,i)
                                _logger.warning("**************************************************")
                                s1, s2 = arrRet[::i, ::i].shape
                                try:
                                    self.data = numpy.zeros((s1, s2,
                                                         self.nbFiles),
                                                         self.__dtype)
                                    samplingStep = i
                                except Exception:
                                    i += 1
                            self.incrProgressBar=0
                            for tempEdfFileName in filelist:
                                tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                pieceOfStack=tempEdf.GetData(0)
                                self.data[:,:, self.incrProgressBar] = pieceOfStack[
                                                            ::samplingStep,::samplingStep]
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                self.onEnd()
        else:
            self.__imageStack = False
            if len(singleImageShape) == 1:
                #single line
                #be ready for specfile stack?
                raise IOError("Not implemented yet")
            else:
                if nImages > 1:
                    #this is not the common case
                    #should I try to convert it to a standard one
                    #using a 3D matrix or kepp as 4D matrix?
                    if self.nbFiles > 1:
                        if (arrRet.shape[0] > 1) and\
                           (arrRet.shape[1] > 1):
                                raise IOError(\
                                    "Multiple files with multiple images not implemented yet")
                        elif arrRet.shape[0] == 1:
                            self.data = numpy.zeros((self.nbFiles,
                                               arrRet.shape[0] * nImages,
                                               arrRet.shape[1]),
                                               self.__dtype)
                            self.incrProgressBar=0
                            for tempEdfFileName in filelist:
                                tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                for i in range(nImages):
                                    pieceOfStack=tempEdf.GetData(i)
                                    self.data[self.incrProgressBar, i,:] = \
                                                              pieceOfStack[:,:]
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                        elif arrRet.shape[1] == 1:
                            self.data = numpy.zeros((self.nbFiles,
                                               arrRet.shape[1] * nImages,
                                               arrRet.shape[0]),
                                               self.__dtype)
                            self.incrProgressBar=0
                            for tempEdfFileName in filelist:
                                tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                                for i in range(nImages):
                                    pieceOfStack=tempEdf.GetData(i)
                                    self.data[self.incrProgressBar, i,:] = \
                                                            pieceOfStack[:,:]
                                self.incrProgressBar += 1
                                self.onProgress(self.incrProgressBar)
                    else:
                        self.data = numpy.zeros((nImages * self.nbFiles,
                                               arrRet.shape[0],
                                               arrRet.shape[1]),
                                               self.__dtype)
                        self.incrProgressBar=0
                        for tempEdfFileName in filelist:
                            tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                            for i in range(nImages):
                                pieceOfStack=tempEdf.GetData(i)
                                self.data[nImages*self.incrProgressBar+i,
                                          :,:] = pieceOfStack[:,:]
                            self.incrProgressBar += 1
                            self.onProgress(self.incrProgressBar)
                    self.onEnd()
                else:
                    if fileindex == 1:
                        try:
                            self.data = numpy.zeros((arrRet.shape[0],
                                                    self.nbFiles,
                                                   arrRet.shape[1]),
                                                   self.__dtype)
                        except Exception:
                            try:
                                self.data = numpy.zeros((arrRet.shape[0],
                                                    self.nbFiles,
                                                   arrRet.shape[1]),
                                                   numpy.float32)
                            except Exception:
                                self.data = numpy.zeros((arrRet.shape[0],
                                                    self.nbFiles,
                                                   arrRet.shape[1]),
                                                   numpy.int16)
                    else:
                        try:
                            # calculate needed megabytes
                            if self.__dtype == numpy.float64:
                                bytefactor = 8
                            else:
                                bytefactor = 4
                            needed_ = self.nbFiles * \
                                       arrRet.shape[0] *\
                                       arrRet.shape[1] * 4
                            physicalMemory = PhysicalMemory.getPhysicalMemoryOrNone()
                            if physicalMemory is not None:
                                # spare 5% of memory
                                if physicalMemory < (1.05 * needed_):
                                    raise MemoryError("Not enough physical memory available")
                            self.data = numpy.zeros((self.nbFiles,
                                                   arrRet.shape[0],
                                                   arrRet.shape[1]),
                                                   self.__dtype)
                        except Exception:
                            text = "Memory Error: Attempt subsampling or convert to HDF5"
                            if 'PyMca5.PyMcaGui.PyMcaQt' in sys.modules:
                                from PyMca5.PyMcaGui import PyMcaQt as qt
                                msg=qt.QMessageBox.information( None,
                                  "Memory error\n",
                                  "Do you want to subsample your data?\n",
                                qt.QMessageBox.Yes,qt.QMessageBox.No)
                                if msg == qt.QMessageBox.No:
                                    raise MemoryError(text)
                            self.data = None
                            self.__dtype = numpy.float32
                            nTry = 0
                            while self.data is None:
                                try:
                                    self.data = numpy.zeros((len(numpy.arange(self.nbFiles)[::fileSampling]),
                                                       len(numpy.arange(arrRet.shape[0])[::mcaSampling]),
                                                       arrRet.shape[1]),
                                                       self.__dtype)
                                    _logger.warning("Subsampling data by %d x %d " % (fileSampling, mcaSampling))
                                    _logger.warning("Data shape %d x %d x %d " % (self.data.shape[0],
                                                                                  self.data.shape[1],
                                                                                  self.data.shape[2]))
                                except Exception:
                                    if 10 * fileSampling < self.nbFiles:
                                        fileSampling += 1
                                    if 10 * mcaSampling < arrRet.shape[0]:
                                        mcaSampling += 1
                                    nTry += 1
                                    if nTry > 100:
                                        raise MemoryError("Memory Error and I could not subsample")
                    filelist = filelist[::fileSampling]
                    self.sourceName = self.sourceName[::fileSampling]
                    self.nbFiles = len(filelist)
                    self.incrProgressBar=0
                    if fileindex == 1:
                        for tempEdfFileName in filelist:
                            tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                            pieceOfStack=tempEdf.GetData(0)
                            self.data[:,self.incrProgressBar,:] = pieceOfStack[:,:]
                            self.incrProgressBar += 1
                            self.onProgress(self.incrProgressBar * fileSampling)
                    else:
                        # test for ID24 map
                        ID24 = False
                        if "_sample_" in filelist[0]:
                            bckFile = filelist[0].replace("_sample_", "_samplebk_")
                            if os.path.exists(bckFile):
                                bckData = EdfFile.EdfFile(bckFile).GetData(0)
                            else:
                                bckData = 0
                            i0StartFile = filelist[0].replace("_sample_", "_I0start_")
                            if os.path.exists(i0StartFile):
                                ID24 = True
                                id24idx = 0
                                i0Start = EdfFile.EdfFile(i0StartFile, 'rb').GetData(0).astype(numpy.float64)
                                i0Start -= bckData
                                i0EndFile = filelist[0].replace("_sample_", "_I0end_")
                                i0Slope = 0.0
                                if os.path.exists(i0EndFile):
                                    i0End = EdfFile.EdfFile(i0EndFile, 'rb').GetData(0) - bckData
                                    i0Slope = (i0End-i0Start)/len(filelist)
                            positionersFile = filelist[0].replace("_sample_", "_positioners_")
                            if os.path.exists(positionersFile):
                                positionersEdf = EdfFile.EdfFile(positionersFile, 'rb')
                                self.info["positioners"] = {}
                                for i in range(positionersEdf.GetNumImages()):
                                    motorName = positionersEdf.GetHeader(i).get("Title", "Motor_%02d" % i)
                                    motorValue = positionersEdf.GetData(i)
                                    self.info["positioners"][motorName] = motorValue
                        for tempEdfFileName in filelist:
                            tempEdf=EdfFile.EdfFile(tempEdfFileName, 'rb')
                            if ID24:
                                pieceOfStack=-numpy.log((tempEdf.GetData(0) - bckData)/(i0Start[0,:] + id24idx * i0Slope))
                                pieceOfStack[numpy.isfinite(pieceOfStack) == False] = 1
                                id24idx += 1
                            else:
                                pieceOfStack=tempEdf.GetData(0)
                            try:
                                self.data[self.incrProgressBar, :,:] = pieceOfStack[::mcaSampling,:]
                            except Exception:
                                if pieceOfStack.shape[1] != arrRet.shape[1]:
                                    _logger.warning(" ERROR on file %s", tempEdfFileName)
                                    _logger.warning(" DIM 1 error Assuming missing data were at the end!!!")
                                if pieceOfStack.shape[0] != arrRet.shape[0]:
                                    _logger.warning(" ERROR on file %s", tempEdfFileName)
                                    _logger.warning(" DIM 0 error Assuming missing data were at the end!!!")
                                self.data[self.incrProgressBar,
                                          :pieceOfStack.shape[0],
                                          :pieceOfStack.shape[1]] = pieceOfStack[:, :]
                            self.incrProgressBar += 1
                            self.onProgress(self.incrProgressBar * fileSampling)
                    self.onEnd()
        self.__nFiles = self.incrProgressBar
        self.__nImagesPerFile = nImages
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i+1,)
            self.info[key] = shape[i]
        if not isinstance(self.data, numpy.ndarray):
            hdf.flush()
            self.info["SourceType"] = "HDF5Stack1D"
            if self.__imageStack:
                self.info["McaIndex"] = 0
                self.info["FileIndex"] = 1
            else:
                self.info["McaIndex"] = 2
                self.info["FileIndex"] = 0
            self.info["SourceName"] = [hdf5file]
            self.info["NumberOfFiles"] = 1
            self.info["Size"]       = 1
        elif actualImageStack:
            self.info["SourceType"] = SOURCE_TYPE
            self.info["McaIndex"] = 0
            self.info["FileIndex"] = 1
            self.info["SourceName"] = self.sourceName
            self.info["NumberOfFiles"] = self.__nFiles * 1
            self.info["Size"] = self.__nFiles * self.__nImagesPerFile
        else:
            self.info["SourceType"] = SOURCE_TYPE
            self.info["FileIndex"] = fileindex
            self.info["SourceName"] = self.sourceName
            self.info["NumberOfFiles"] = self.__nFiles * 1
            self.info["Size"] = self.__nFiles * self.__nImagesPerFile

        # try to use positioners to compute the scales (ID24 specific)
        xPositionerName = None
        yPositionerName = None
        if "positioners" in self.info and len(self.info["positioners"]) == 2:
            for k, v in self.info["positioners"].items():
                if isinstance(v, numpy.ndarray) and v.ndim == 2:
                    deltaDim1 = v[:, 1:] - v[:, :-1]
                    deltaDim0 = v[1:, :] - v[:-1, :]
                    if numpy.any(deltaDim1) and not numpy.any(deltaDim0):
                        # positioner varying only along dim1
                        xPositionerName = k
                        # should we check that all delta values are equal?
                        deltaX = numpy.mean(deltaDim1)
                        originX = v[0, 0]
                    elif numpy.any(deltaDim0) and not numpy.any(deltaDim1):
                        # positioner varying only along dim0
                        yPositionerName = k
                        deltaY = numpy.mean(deltaDim0)
                        originY = v[0, 0]
            if xPositionerName is not None and yPositionerName is not None:
                self.info["xScale"] = (originX, deltaX)
                self.info["yScale"] = (originY, deltaY)

    def onBegin(self, n):
        pass

    def onProgress(self, n):
        pass

    def onEnd(self):
        pass

    def loadIndexedStack(self,filename,begin=None,end=None, skip = None, fileindex=0):
        #if begin is None: begin = 0
        if type(filename) == type([]):
            filename = filename[0]
        if not os.path.exists(filename):
            raise IOError("File %s does not exists" % filename)
        name = os.path.basename(filename)
        n = len(name)
        i = 1
        while (i <= n):
            c = name[n-i:n-i+1]
            if c in ['0', '1', '2',
                                '3', '4', '5',
                                '6', '7', '8',
                                '9']:
                break
            i += 1
        suffix = name[n-i+1:]
        if len(name) == len(suffix):
            #just one file, one should use standard widget
            #and not this one.
            self.loadFileList(filename, fileindex=fileindex)
        else:
            nchain = []
            while (i<=n):
                c = name[n-i:n-i+1]
                if c not in ['0', '1', '2',
                                    '3', '4', '5',
                                    '6', '7', '8',
                                    '9']:
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
                prefix = name[0:n-i+1]
            prefix = os.path.join(os.path.dirname(filename),prefix)
            if not os.path.exists(prefix + number + suffix):
                _logger.error("Internal error in EDFStack "
                              "file should exist: %s ",
                              prefix + number + suffix)
                return
            i = 0
            if begin is None:
                begin = 0
                testname = prefix+fformat % begin+suffix
                while not os.path.exists(prefix+fformat % begin+suffix):
                    begin += 1
                    testname = prefix+fformat % begin+suffix
                    if len(testname) > len(filename):break
                i = begin
            else:
                i = begin
            if not os.path.exists(prefix+fformat % i+suffix):
                raise ValueError("Invalid start index file = %s" % \
                      (prefix+fformat % i+suffix))
            f = prefix+fformat % i+suffix
            filelist = []
            while os.path.exists(f):
                filelist.append(f)
                i += 1
                if end is not None:
                    if i > end:
                        break
                f = prefix+fformat % i+suffix
            self.loadFileList(filelist, fileindex=fileindex)

    def getSourceInfo(self):
        sourceInfo = {}
        sourceInfo["SourceType"]=SOURCE_TYPE
        if self.__keyList == []:
            for i in range(1, self.__nFiles + 1):
                for j in range(1, self.__nImages + 1):
                    self.__keyList.append("%d.%d" % (i,j))
        sourceInfo["KeyList"]= self.__keyList

    def getKeyInfo(self, key):
        _logger.info("Not implemented")
        return {}

    def isIndexedStack(self):
        return self.__indexedStack

    def getZSelectionArray(self,z=0):
        return (self.data[:,:,z]).astype(numpy.float64)

    def getXYSelectionArray(self,coord=(0,0)):
        x,y=coord
        return (self.data[y,x,:]).astype(numpy.float64)

if __name__ == "__main__":
    import time
    t0= time.time()
    stack = EDFStack()
    #stack.loadIndexedStack("Z:\COTTE\ch09\ch09__mca_0005_0000_0070.edf")
    stack.loadIndexedStack(r".\COTTE\ch09\ch09__mca_0005_0000_0070.edf")
    shape = stack.data.shape
    print("elapsed = %f" % (time.time() - t0))
    #guess the MCA
    imax = 0
    for i in range(len(shape)):
        if shape[i] > shape[imax]:
            imax = i

    print("selections ")
    print("getZSelectionArray  shape = ", stack.getZSelectionArray().shape)
    print("getXYSelectionArray shape = ", stack.getXYSelectionArray().shape)

