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
__author__ = "E. Papillon - ESRF Software Group"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os, os.path
import numpy
from PyMca5.PyMcaIO import EdfFile

XiaStatIndex= {
    "det": 0,
    "evt": 1,
    "icr": 2,
    "ocr": 3,
    "lt" : 4,
    "dt" : 5
}
XiaStatNb= len(XiaStatIndex.keys())
XiaStatLabels= ["xdet", "xevt", "xicr", "xocr", "xlt", "xdt"]

def cmp(first, second):
    if first < second:
        result = -1
    elif second < first:
        result = 1
    else:
        result = 0
    return result

def checkEdfForRead(filename):
    if not os.path.isfile(filename):
        raise XiaEdfError("Cannot find file <%s>"%filename)
    else:
        try:
            if os.path.getsize(filename)==0:
                raise XiaEdfError("File <%s> has a null size "%filename)
        except Exception:
            raise XiaEdfError("Cannot open file <%s>"%filename)

def openEdf(filename, read=0, write=0, force=0):
    if read:
        checkEdfForRead(filename)
    if write:
        checkEdfForWrite(filename, force)

    try:
        edf= EdfFile.EdfFile(filename)
    except Exception:
        raise XiaEdfError("Cannot open EDF file <%s>"%filename)
    return edf

def checkEdfForWrite(filename, force=0):
    if os.path.isfile(filename):
        if not force:
            raise XiaEdfError("<%s> already exist. Abort saving."%filename)
        else:
            os.remove(filename)
            if os.path.isfile(filename):
                raise XiaEdfError("Cannot remove <%s>. Abort saving."%filename)

class XiaEdfError(Exception):
    def __init__(self, message):
        self.msg= message

    def __str__(self):
        return "XiaEdf ERROR: %s"%self.msg

class XiaEdfCountFile:
    def __init__(self, filename):
        self.filename= filename

        self.edf= openEdf(filename, read=1)
        self.reset()

    def reset(self):
        self.data= None
        self.header= None
        try:
            self.__readStat()
        except Exception:
            raise XiaEdfError("Cannot parse header in <%s>" % self.filename)

    def __readStat(self):
        self.header= self.edf.GetHeader(0)

        self.nbDet= int(self.header.get("xnb", 0))
        if not self.nbDet:
            self.detList= []
            self.statArray= None
            return self.nbDet

        self.detList= range(self.nbDet)
        det= self.header.get("xdet", None)
        if det is not None:
            dets= det.split()
            if len(dets)==self.nbDet:
                self.detList= list(map(int, dets))

        self.statArray = numpy.zeros(XiaStatNb*self.nbDet, numpy.int64)
        idx= 0
        for det in self.detList:
            self.statArray[idx+XiaStatIndex["det"]]= int(self.header.get("xdet%02d"%det, det))
            self.statArray[idx+XiaStatIndex["evt"]]= int(self.header.get("xevt%02d"%det, 0))
            self.statArray[idx+XiaStatIndex["icr"]]= int(self.header.get("xicr%02d"%det, 1))
            self.statArray[idx+XiaStatIndex["ocr"]]= int(self.header.get("xocr%02d"%det, 1))
            self.statArray[idx+XiaStatIndex["lt"]]= int(self.header.get("xlt%02d"%det, 1))
            self.statArray[idx+XiaStatIndex["dt"]]= int(self.header.get("xdt%02d"%det, 0))
            idx += 6

    def __getData(self):
        self.__readData()
        return self.data

    def __readData(self):
        if self.data is None:
            try:
                self.data= self.edf.GetData(0)
            except Exception:
                raise XiaEdfError("Cannot read data in <%s>"%self.filename)

    def getDetList(self):
        return self.detList

    def getData(self, detector=-1):
        # --- WARNING: first index is channels
        data= self.__getData()
        if detector==-1:
            return data[1:]
        else:
            if detector not in self.detList:
                return None
            idx= self.detList.index(detector)
            return data[idx+1]

    def getStat(self, detector=-1):
        if detector==-1:
            return self.statArray
        else:
            if detector not in self.detList:
                return None
            idx= self.detList.index(detector)
            return self.statArray[(idx*XiaStatNb):((idx+1)*XiaStatNb)]

    def correct(self, deadtime=1, livetime=0):
        message= []
        corrflag= int(self.header.get("xcorr", 0))
        if livetime and corrflag&2:
            raise XiaEdfError("<%s> seems already livetime corrected"%self.filename)

        if deadtime and corrflag&1:
            raise XiaEdfError("<%s> seems already deadtime corrected"%self.filename)

        self.__readData()
        self.data= self.data.astype(numpy.float64)

        if livetime:
            lvt= numpy.zeros((self.nbDet,1), numpy.float64)
            derr= []
            for idx in range(len(self.detList)):
                lvt[idx]= self.statArray[idx*XiaStatNb + XiaStatIndex["lt"]] / 1000.0
                if lvt[idx]==0.:
                    lvt[idx]= 1.
                    derr.append("#%02d"%self.detList[idx])
            if len(derr):
                message.append("Null livetime on det %s"% " ".join(derr))

            self.data[1:,:]= self.data[1:,:] / lvt
            self.header["xcorr"]= corrflag|2

        if deadtime:
            rate= numpy.zeros((self.nbDet,1), numpy.float64)
            for idx in range(len(self.detList)):
                derr= []
                try:
                    rate[idx]= float(self.statArray[idx*XiaStatNb + XiaStatIndex["icr"]]) / \
                            float(self.statArray[idx*XiaStatNb + XiaStatIndex["ocr"]])
                except Exception:
                    rate[idx]= 1.
                    derr.append("#%02d"%idx)
            if len(derr):
                message.append("Null OCR on det %s" % " ".join(derr))

            self.data[1:,:]= self.data[1:,:] * rate
            self.header["xcorr"]= corrflag|1

        return message

    def sum(self, sums=[], deadtime=0, livetime=0, average=0):
        message= []
        if not len(sums):
            return message

        self.__readData()

        if deadtime or livetime:
            message+= self.correct(deadtime, livetime)
        else:
            self.data= self.data.astype(numpy.float64)

        sumdata= numpy.zeros((len(sums), self.data.shape[1]), numpy.float64)

        for idx in range(len(sums)):
            if not len(sums[idx]):
                sumdata[idx,:] = numpy.sum(self.data[1:,], 0)
                xdet= self.detList
            else:
                mask= numpy.zeros((self.nbDet+1,1), numpy.int64)
                xdet= []
                for det in sums[idx]:
                    if det in self.detList:
                        detidx= self.detList.index(det)
                        mask[detidx+1]= 1
                        xdet.append(det)
                sumdata[idx,:]= numpy.sum(self.data*mask, 0)

            self.header["xcorr%d"%idx] = self.header.get("xcorr", 0)
            self.header["xdet%d"%idx] = " ".join([str(det) for det in xdet])

        if average:
            self.data= sumdata / len(xdet)
        else:
            self.data= sumdata

        for key in self.header.keys():
            if key[0]=='x':
                try:
                    det= int(key[-2:])
                    del self.header[key]
                except Exception:
                    pass

        dataflag= int(self.header.get("xdata", 0))
        self.header["xdata"]= dataflag | (1<<2)
        self.header["xnb"]= len(sums)

        return message

    def save(self, filename, force=0):
        edf= openEdf(filename, write=1, force=force)
        self.__readData()
        edf.WriteImage(self.header, self.data)

class XiaEdfScanFile:
    def __init__(self, statfile, detfiles):
        self.statfile= statfile
        self.detfiles= detfiles

        self.detector= None
        self.data= None
        self.header= None

        checkEdfForRead(self.statfile)
        for file in self.detfiles:
            checkEdfForRead(file)

        try:
            self.__readStat()
        except Exception:
            raise XiaEdfError("Cannot parse header in <%s>"%self.statfile)

    def __readStat(self):
        edf= openEdf(self.statfile)
        header= edf.GetHeader(0)

        self.nbDet= int(header.get("xnb", 0))
        if not self.nbDet:
            self.detList= []
            self.statArray= None
            return self.nbDet

        self.detList= range(self.nbDet)
        det= header.get("xdet", None)
        if det is not None:
            dets= det.split()
            if len(dets)==self.nbDet:
                self.detList= list(map(int, dets))

        self.statArray= edf.GetData(0)

        return self.nbDet

    def __readData(self, detector):
        if detector!=self.detector:
            self.detector= None
            self.data= None
            self.header= None

            if detector in self.detList:
                idx= self.detList.index(detector)
                if idx < len(self.detfiles):
                    file= self.detfiles[idx]
                    edf= openEdf(self.detfiles[idx])
                    header= edf.GetHeader(0)
                    xdet= int(header.get("xdet", -1))
                    if xdet==-1 or xdet==detector:
                        self.data= edf.GetData(0)
                        self.header= header
                        self.detector= xdet

                if self.data is None:
                    for file in self.detfiles:
                        edf= openEdf(file)
                        header= edf.GetHeader(0)
                        xdet= int(header.get("xdet", -1))
                        if xdet==detector:
                            self.data= edf.GetData(0)
                            self.header= header
                            self.detector= xdet
                            break

            if self.data is None:
                raise XiaEdfError("Cannot read data on det #%02d"%detector)

    def getDetList(self):
        return self.detList

    def getData(self, detector):
        self.__readData(detector)
        return self.data

    def getStat(self, detector=-1):
        if detector==-1:
            return self.statArray
        else:
            if detector not in self.detList:
                return None
            idx= self.detList.index(detector)
            return self.statArray[:,(idx*XiaStatNb):((idx+1)*XiaStatNb)]

    def correct(self, detector, deadtime=1, livetime=0):
        message= []
        if detector!=self.detector:
            self.__readData(detector)

        corrflag= int(self.header.get("xcorr", 0))
        if livetime and corrflag&2:
            raise XiaEdfError("det #%02d seems already livetime corrected"%detector)

        if deadtime and corrflag&1:
            raise XiaEdfError("det #%02d seems already deadtime corrected"%detector)

        self.data= self.data.astype(numpy.float64)
        idx= self.detList.index(detector)
        pts= self.statArray.shape[0]

        if livetime:
            lvt= numpy.zeros((pts, 1), numpy.float64)
            lvt[:,0]= self.statArray[:,((XiaStatNb*idx)+XiaStatIndex["lt"])] / 1000.0

            perr= self.__checkNullLivetime(lvt, pts)
            if len(perr):
                message.append("Null livetime on det #%02d points %s"%(detector, self.__pointRange(perr)))

            self.data= self.data / lvt
            self.header["xcorr"]= corrflag|2

        if deadtime:
            rate= numpy.zeros((self.statArray.shape[0], 1), numpy.float64)
            count= numpy.zeros((self.statArray.shape[0], 2), numpy.float64)

            count[:,0]= self.statArray[:, (XiaStatNb*idx)+XiaStatIndex["ocr"]]
            count[:,1]= self.statArray[:, (XiaStatNb*idx)+XiaStatIndex["icr"]]

            perr= self.__checkNullCount(count, pts)
            if len(perr):
                message.append("Null ICR|OCR on det #%02d points %s"%(detector, self.__pointRange(perr)))

            perr= []
            for ipt in range(pts):
                if count[ipt,0]>0 and count[ipt,1]>0:
                    rate[ipt,0]= count[ipt,1]/count[ipt,0]
                else:
                    rate[ipt,0]= 1.
                    perr.append(ipt)

            if len(perr):
                message.append("No DeadTime correction perfomed on det #%02d points %s"%(detector, self.__pointRange(perr)))

            self.data= self.data * rate
            self.header["xcorr"]= corrflag|1

        return message

    def __checkNullCount(self, count, pts):
        perr= []
        check= numpy.sum(numpy.greater(count,0.), 1)
        for ipt in range(pts):
            if check[ipt]!=2:
                perr.append(ipt)
                if (ipt!=0 and check[ipt-1]==2) and (ipt!=pts-1 and check[ipt+1]==2):
                    count[ipt,:]= (count[ipt-1,:]+count[ipt+1,:])/2.
                elif (ipt!=0 and check[ipt-1]==2):
                    count[ipt,:]= count[ipt-1,:]
                elif (ipt!=pts-1 and check[ipt+1]==2):
                    count[ipt,:]= count[ipt+1,:]
                else:
                    count[ipt,:]= -1
        return perr

    def __checkNullLivetime(self, lvt, pts):
        perr= []
        check= numpy.greater(lvt, 0.)
        for ipt in range(pts):
            if check[ipt]==0:
                perr.append(ipt)
                if (ipt!=0 and check[ipt-1]==1) and (ipt!=pts-1 and check[ipt+1]==1):
                     lvt[ipt,0]= (lvt[ipt+1]+lvt[ipt-1])/2.
                elif (ipt!=0 and check[ipt-1]==1):
                     lvt[ipt,0]= lvt[ipt-1,0]
                elif (ipt!=pts-1 and check[ipt+1]==1):
                     lvt[ipt,0]= lvt[ipt+1,0]
                else:
                     lvt[ipt,0]= 1.
        return perr

    def __pointRange(self, ptlist):
        nb= len(ptlist)
        ptdiff= []
        for idx in range(nb-1):
            ptdiff.append(((ptlist[idx+1]-ptlist[idx])==1))
        ptdiff.append(0)

        ptrange= []
        curr= None
        for idx in range(nb):
            if ptdiff[idx]:
                if curr is None:
                    curr= ptlist[idx]
            else:
                if curr is None:
                    ptrange.append(str(ptlist[idx]))
                else:
                    ptrange.append("%d-%d"%(curr,ptlist[idx]))
                curr= None

        return "["+ ",".join(ptrange)+"]"

    def sum(self, detectors=[], deadtime=0, livetime=0, average=0):
        message= []
        if not len(detectors):
            sumdet= self.detList
        else:
            sumdet= [ det for det in detectors if det in self.detList ]

        sumdata= None
        for det in sumdet:
            if deadtime or livetime:
                message+= self.correct(det, deadtime, livetime)
            else:
                self.__readData(det)
                self.data= self.data.astype(numpy.float64)

            if sumdata is None:
                sumdata= self.data * 1.0
            else:
                sumdata= sumdata + self.data

        if average:
            self.data= sumdata / len(sumdet)
        else:
            self.data= sumdata

        dataflag= int(self.header.get("xdata", 0))
        self.header["xdata"]= dataflag | (1<<2)
        self.header["xnb"]= 1
        self.header["xdet"]= " ".join([str(det) for det in sumdet])

        return message

    def save(self, filename, force=0):
        if self.data is None:
            raise XiaEdfError("Cannot save. No data loaded.")
        edf= openEdf(filename, write=1, force=force)
        edf.WriteImage(self.header, self.data)

class XiaFilename:
    def __init__(self, filename=None):
        self.__reset()

        if filename is not None:
            self.__parseFilename(filename)

    def setType(self, type, det=None):
        self.type= type
        self.det= det

    def getType(self):
        return self.type

    def isValid(self):
        return self.type is not None

    def isCount(self):
        return (self.type=="ct" or (self.type=="sum" and self.det==-1))

    def isScan(self):
        return (self.type=="det" or self.type=="st" or (self.type=="sum" and self.det>0))

    def isSum(self):
        return (self.type=="sum")

    def isStat(self):
        return (self.type=="st")

    def findStatFile(self):
        xf= XiaFilename(self.get())
        xf.setType("st")
        if os.path.isfile(xf.get()):
            return xf
        else:
            return None

    def isGroupedWith(self, other):
        if (self.isScan() and other.isScan()) or (self.isCount() and other.isCount()):
            file1= "%s/%s"%(self.dir is None and "." or self.dir, self.prefix is None and "" or self.prefix)
            file2= "%s/%s"%(other.dir is None and "." or other.dir, other.prefix is None and "" or other.prefix)
            res= cmp(file1, file2)
            if res!=0: return 0

            res= cmp(self.index, other.index)
            if res!=0: return 0

            file1= "%s.%s"%(self.suffix is None and "" or self.suffix, self.ext is None and "" or self.ext)
            file2= "%s.%s"%(other.suffix is None and "" or other.suffix, other.ext is None and "" or other.ext)
            res= cmp(file1, file2)
            if res!=0: return 0

            return 1
        else:
            return 0

    def setDirectory(self, dirname):
        if dirname is None:
            self.dir= "."
        else:
            self.dir= dirname

    def appendPrefix(self, name):
        if self.prefix is None:
            self.prefix= name
        elif name is not None:
            self.prefix= "%s_%s"%(self.prefix, name)

    def getDetector(self):
        if self.type!="det":
            return None
        else:
            return self.det

    def set(self, filename):
        self.__reset()
        if filename is not None:
            self.__parseFilename(filename)

    def get(self):
        self.__createFilename()
        return self.file

    def __reset(self):
        self.file= None         # --- full filename
        self.dir = None         # --- directory
        self.type= None         # --- file type = "ct", "st", "det"
        self.index= []          # --- file indexes
        self.suffix= None       # --- suffix
        self.det= None          # --- if type=="det", detector number

    def __parseFilename(self, filename):
        self.file= os.path.basename(filename)
        self.dir= os.path.dirname(filename)
        if not len(self.dir):
            self.dir= "."

        fileext= os.path.splitext(self.file)
        if len(fileext[1]):
            self.ext= fileext[1][1:]

        filelist= fileext[0].split("_")

        xiaidx= 0
        for xiaidx in range(len(filelist)):
            if filelist[xiaidx][0:3]=="xia":
                break
            xiaidx += 1

        if xiaidx==len(filelist):
            self.type= None
            self.prefix= fileext[0]
        else:
            self.prefix= "_".join(filelist[0:xiaidx])
            try:
                self.index= list(map(int, filelist[xiaidx+1:]))
            except Exception:
                self.suffix= "_".join(filelist[xiaidx+1:])

            type= filelist[xiaidx][3:]
            if type=="ct" or type=="st":
                self.type= type
            elif type[0]=='S':
                self.type= "sum"
                if type[1]=='N':
                    self.det= -1
                else:
                    try:
                        self.det= int(type[1])
                    except Exception:
                        self.type= None
            else:
                try:
                    self.type= "det"
                    self.det= int(type)
                except Exception:
                    self.type= None

    def __createFilename(self):
        if self.prefix is None or self.type is None:
            self.file= None
        else:
            self.file= "%s/%s"%(self.dir, self.prefix)
            xia= None
            if self.type=="ct":
                xia= "xiact"
            elif self.type=="st":
                xia= "xiast"
            elif self.type=="sum":
                if self.det==-1:
                    xia= "xiaSN"
                else:
                    xia= "xiaS%01d"%self.det
            elif self.type=="det":
                xia= "xia%02d"%self.det
            elif self.type is not None:
                xia= "xia%s"%self.type

            if xia is not None:
                self.file= "%s_%s"%(self.file, xia)

            for idx in self.index:
                self.file= "%s_%04d"%(self.file, idx)

            if self.suffix is not None:
                self.file= "%s_%s"%(self.file, self.suffix)

            if self.ext is not None:
                self.file= "%s.%s"%(self.file, self.ext)

    def __cmp__(self, other):
        # this was only working under python2
        file1= "%s/%s"%(self.dir is None and "." or self.dir, self.prefix is None and "" or self.prefix)
        file2= "%s/%s"%(other.dir is None and "." or other.dir, other.prefix is None and "" or other.prefix)
        res= cmp(file1, file2)
        if res!=0:
            return res

        res= cmp(self.ext, other.ext)
        if res!=0:
            return res

        res= cmp(self.index, other.index)
        if res!=0:
            return res

        res= cmp(self.type, other.type)
        if res!=0:
            return res

        if self.type=="det" or self.type=="sum":
            res= cmp(self.det, other.det)
            if res!=0:
                return res

        file1= "%s.%s"%(self.suffix is None and "" or self.suffix, self.ext is None and "" or self.ext)
        file2= "%s.%s"%(other.suffix is None and "" or other.suffix, other.ext is None and "" or other.ext)
        return cmp(file1, file2)

    def __lt__(self, other):
        # this is needed under python3
        file1= "%s/%s"%(self.dir is None and "." or self.dir, self.prefix is None and "" or self.prefix)
        file2= "%s/%s"%(other.dir is None and "." or other.dir, other.prefix is None and "" or other.prefix)
        return file1 < file2

def testScan():
    x= XiaEdfScanFile("data/test_xiast_0000_0000_0000.edf",
        ["data/test_xia00_0000_0000_0000.edf",
        "data/test_xia01_0000_0000_0000.edf",
        "data/test_xia02_0000_0000_0000.edf",
        "data/test_xia03_0000_0000_0000.edf",
        "data/test_xia04_0000_0000_0000.edf",
        "data/test_xia05_0000_0000_0000.edf",
        "data/test_xia06_0000_0000_0000.edf",
        "data/test_xia07_0000_0000_0000.edf",
        "data/test_xia08_0000_0000_0000.edf",
        "data/test_xia09_0000_0000_0000.edf",
        "data/test_xia10_0000_0000_0000.edf",
        "data/test_xia11_0000_0000_0000.edf",
        ])

    x.sum([1,10])
    print(x.header)
    x.save("test_sum.edf")
    #for det in [1, 2, 3, 4, 5, 6]:
    #    x.correct(det, livetime=1)
    #    x.save(det, "scan_corr_xia%02d.edf"%det)

def testAcq(infile, outfile=None):
        print("Reading ", infile)
        x= XiaEdfCountFile(infile)
        #print "DeadTime Correction ..."
        #x.correct()
        x.sum([1,10])
        if outfile is not None:
            print(x.header)
            print("Saving %s" % outfile)
            x.save(outfile)

if __name__=="__main__":
    import sys

    testScan()
    sys.exit(0)
