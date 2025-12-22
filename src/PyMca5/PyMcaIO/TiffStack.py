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
import sys
import os
import numpy
from PyMca5 import DataObject
from PyMca5.PyMcaIO import TiffIO
if sys.version > '2.9':
    long = int

SOURCE_TYPE = "TiffStack"

class TiffArray(object):
    def __init__(self, filelist, shape, dtype, imagestack=True):
        self.__fileList    = filelist
        self.__shape       = shape
        self.__dtype       = dtype
        self.__imageStack  = imagestack
        if imagestack:
            self.__nImagesPerFile = int(shape[0]/len(filelist))
        else:
            self.__nImagesPerFile = int(shape[-1]/len(filelist))
        self.__oldFileNumber = -1

    def __getitem__(self, args0):
        standardSlice = True
        indices = []
        outputShape = []
        scalarArgs = []
        args = []
        if not hasattr(args0, "__len__"):
            args0 = [args0]
        for i in range(len(self.__shape)):
            if i < len(args0):
                args.append(args0[i])
            else:
                args.append(slice(None, None, None))
        for i in range(len(args)):
            if isinstance(args[i], slice):
                start = args[i].start
                stop  = args[i].stop
                step  = args[i].step
                if start is None:
                    start = 0
                if stop is None:
                    stop = self.__shape[i]
                if step is None:
                    step = 1
                if step < 1:
                    raise ValueError("Step must be >= 1 (got %d)" % step)
                if start is None:
                    start = 0
                if start < 0:
                    start = self.__shape[i]-start
                if stop < 0:
                    stop = self.__shape[i]-stop
                if stop == start:
                    raise ValueError("Zero-length selections are not allowed")
                indices.append(list(range(start, stop, step)))
            elif type(args[i]) == type([]):
                if len(args[i]):
                    indices.append([int(x) for x in args[i]])
                else:
                    standardSlice = False
            elif type(args[i]) in [type(1), type(long(1))]:
                start = args[i]
                if start < 0:
                    start = self.__shape[i] - start
                stop = start + 1
                step = 1
                start = args[i]
                args[i] = slice(start, stop, step)
                indices.append(list(range(start, stop, step)))
                scalarArgs.append(i)
            else:
                standardSlice = False

        if not standardSlice:
            print("args = ", args)
            raise NotImplemented("__getitem__(self, args) only works on slices")

        if len(indices) < 3:
            print("input args = ", args0)
            print("working args = ", args)
            print("indices = ", indices)
            raise NotImplemented("__getitem__(self, args) only works on slices")
        outputShape = [len(indices[0]), len(indices[1]), len(indices[2])]
        outputArray = numpy.zeros(outputShape, dtype=self.__dtype)
        # nbFiles = len(self.__fileList)
        nImagesPerFile = self.__nImagesPerFile

        if self.__imageStack:
            i = 0
            rowMin = min(indices[1])
            rowMax = max(indices[1])
            for imageIndex in indices[0]:
                fileNumber = int(imageIndex/nImagesPerFile)
                if fileNumber != self.__oldFileNumber:
                    self.__tmpInstance = TiffIO.TiffIO(self.__fileList[fileNumber],
                                                       mode='rb+')
                    self.__oldFileNumber = fileNumber
                imageNumber = imageIndex % nImagesPerFile
                imageData = self.__tmpInstance.getData(imageNumber,
                                                       rowMin=rowMin,
                                                       rowMax=rowMax)
                try:
                    outputArray[i,:,:] = imageData[args[1],args[2]]
                except Exception:
                    print("outputArray[i,:,:].shape =",outputArray[i,:,:].shape)
                    print("imageData[args[1],args[2]].shape = " , imageData[args[1],args[2]].shape)
                    print("input args = ", args0)
                    print("working args = ", args)
                    print("indices = ", indices)
                    print("scalarArgs = ", scalarArgs)
                    raise
                i += 1
        else:
            i = 0
            rowMin = min(indices[0])
            rowMax = max(indices[0])
            for imageIndex in indices[-1]:
                fileNumber = int(imageIndex/nImagesPerFile)
                if fileNumber != self.__oldFileNumber:
                    self.__tmpInstance = TiffIO.TiffIO(self.__fileList[fileNumber],
                                                       mode='rb+')
                    self.__oldFileNumber = fileNumber
                imageNumber = imageIndex % nImagesPerFile
                imageData = self.__tmpInstance.getData(imageNumber,
                                                       rowMin=rowMin,
                                                       rowMax=rowMax)
                outputArray[:,:, i] = imageData[args[0],args[1]]
                i += 1
        if len(scalarArgs):
            finalShape = []
            for i in range(len(outputShape)):
                if i in scalarArgs:
                    continue
                finalShape.append(outputShape[i])
            outputArray = outputArray.reshape(finalShape)
        return outputArray

    def getShape(self):
        return self.__shape
    shape = property(getShape)

    def getDtype(self):
        return self.__dtype
    dtype = property(getDtype)

    def getSize(self):
        s = 1
        for item in self.__shape:
            s *= item
        return s
    size = property(getSize)

class TiffStack(DataObject.DataObject):
    def __init__(self, filelist=None, imagestack=None, dtype=None):
        DataObject.DataObject.__init__(self)
        self.sourceType = SOURCE_TYPE
        if imagestack is None:
            self.__imageStack = True
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

    def loadFileList(self, filelist, dynamic=False, fileindex=0):
        if type(filelist) != type([]):
            filelist = [filelist]

        #retain the file list
        self.sourceName = filelist

        #the number of files
        nbFiles=len(filelist)

        #the intance to access the first file
        fileInstance = TiffIO.TiffIO(filelist[0])

        #the number of images per file
        nImagesPerFile = fileInstance.getNumberOfImages()

        #get the dimensions from the image itself
        tmpImage = fileInstance.getImage(0)
        if self.__dtype is None:
            self.__dtype = tmpImage.dtype

        nRows, nCols = tmpImage.shape

        #stack shape
        if self.__imageStack:
            shape = (nbFiles * nImagesPerFile, nRows, nCols)
        else:
            shape = (nRows, nCols, nbFiles * nImagesPerFile)

        #we can create the stack
        if not dynamic:
            try:
                data = numpy.zeros(shape,
                                   self.__dtype)
            except (MemoryError, ValueError):
                dynamic = True
        if not dynamic:
            imageIndex = 0
            self.onBegin(nbFiles * nImagesPerFile)
            for i in range(nbFiles):
                tmpInstance =TiffIO.TiffIO(filelist[i])
                for j in range(nImagesPerFile):
                    tmpImage = tmpInstance.getImage(j)
                    if self.__imageStack:
                        data[imageIndex,:,:] = tmpImage
                    else:
                        data[:,:,imageIndex] = tmpImage
                    imageIndex += 1
                    self.incrProgressBar = imageIndex
                    self.onProgress(imageIndex)
            self.onEnd()

        if dynamic:
            data = TiffArray(filelist,
                             shape,
                             self.__dtype,
                             imagestack=self.__imageStack)
        self.info = {}
        self.data = data
        shape = self.data.shape
        for i in range(len(shape)):
            key = 'Dim_%d' % (i+1,)
            self.info[key] = shape[i]

        if self.__imageStack:
            self.info["McaIndex"] = 0
            self.info["FileIndex"] = 1
        else:
            self.info["McaIndex"] = 2
            self.info["FileIndex"] = 0

        self.info["SourceType"] = SOURCE_TYPE
        self.info["SourceName"] = self.sourceName

    def loadIndexedStack(self,filename,begin=None,end=None, skip = None, fileindex=0):
        #if begin is None: begin = 0
        if type(filename) == type([]):
            filename = filename[0]
        if not os.path.exists(filename):
            raise IOError("File %s does not exists" % filename)
        name = os.path.basename(filename)
        n = len(name)
        i = 1
        numbers = ['0', '1', '2', '3', '4', '5',
                   '6', '7', '8','9']
        while (i <= n):
            c = name[n-i:n-i+1]
            if c in numbers:
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
                prefix = name[0:n-i+1]
            prefix = os.path.join(os.path.dirname(filename),prefix)
            if not os.path.exists(prefix + number + suffix):
                print("Internal error in TIFFStack")
                print("file should exist: %s " % (prefix + number + suffix))
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

    def onBegin(self, n):
        pass

    def onProgress(self, n):
        pass

    def onEnd(self):
        pass

def test():
    from PyMca5 import StackBase
    testFileName = "TiffTest.tif"
    nrows = 2000
    ncols = 2000
    #create a dummy stack with 100 images
    nImages = 100
    imagestack = True
    a = numpy.ones((nrows, ncols), numpy.float32)
    if not os.path.exists(testFileName):
        print("Creating test filename %s"  % testFileName)
        tif = TiffIO.TiffIO(testFileName, mode = 'wb+')

        for i in range(nImages):
            data = (a * i).astype(numpy.float32)
            if i == 1:
                tif = TiffIO.TiffIO(testFileName, mode = 'rb+')
            tif.writeImage(data,
                           info={'Title':'Image %d of %d' % (i+1, nImages)})
        tif = None

    stackData = TiffStack(imagestack=imagestack)
    stackData.loadFileList([testFileName], dynamic=True)

    if 0:
        stack = StackBase.StackBase()
        stack.setStack(stackData)
        print("This should be 0 = %f" %  stack.calculateROIImages(0, 0)['ROI'].sum())
        print("This should be %f = %f" %\
              (a.sum(),stack.calculateROIImages(1, 2)['ROI'].sum()))
        if imagestack:
            print("%f should be = %f" %\
                  (stackData.data[0:10,:,:].sum(),
                   stack.calculateROIImages(0, 10)['ROI'].sum()))
            print("Test small ROI 10 should be = %f" %\
                  stackData.data[10:11,[10],11].sum())
            print("Test small ROI 40 should be = %f" %\
                  stackData.data[10:11,[10,12,14,16],11].sum())
        else:
            print("%f should be = %f" %\
                  (stackData.data[:,:, 0:10].sum(),
                   stack.calculateROIImages(0, 10)['ROI'].sum()))
            print("Test small ROI %f" %\
                  stackData.data[10:11,[29],:].sum())
    else:
        from PyMca5.PyMca import PyMcaQt as qt
        from PyMca5.PyMca import QStackWidget
        app = qt.QApplication([])
        w = QStackWidget.QStackWidget()
        print("Setting stack")
        w.setStack(stackData)
        w.show()
        app.exec()

if __name__ == "__main__":
    test()

