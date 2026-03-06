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
from . import ClassMcaTheory
from PyMca5.PyMcaCore import SpecFileLayer
from PyMca5.PyMcaCore import EdfFileLayer
from PyMca5.PyMcaIO import EdfFile
from PyMca5.PyMcaIO import LuciaMap
from PyMca5.PyMcaIO import AifiraMap
from PyMca5.PyMcaIO import EDFStack
from PyMca5.PyMcaIO import LispixMap
from PyMca5.PyMcaIO import NumpyStack
try:
    import h5py
    from PyMca5.PyMcaIO import HDF5Stack1D
    HDF5SUPPORT = True
except ImportError:
    HDF5SUPPORT = False
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaMisc import CliUtils
from . import ConcentrationsTool


class McaAdvancedFitBatch(object):
    def __init__(self,initdict,filelist=None,outputdir=None,
                    roifit=None,roiwidth=None,
                    overwrite=1, filestep=1, mcastep=1,
                    concentrations=0, fitfiles=1, fitimages=1,
                    filebeginoffset = 0, fileendoffset=0,
                    mcaoffset=0, chunk = None,
                    selection=None, lock=None, nosave=None, quiet=False):
        #for the time being the concentrations are bound to the .fit files
        #that is not necessary, but it will be correctly implemented in
        #future releases
        self._lock = lock
        if nosave:
            self._nosave = True
        else:
            self._nosave = False
        self.fitFiles = fitfiles
        self._concentrations = concentrations
        if type(initdict) == type([]):
            self.mcafit = ClassMcaTheory.McaTheory(initdict[mcaoffset])
            self.__configList = initdict
            self.__currentConfig = mcaoffset
        else:
            self.__configList = [initdict]
            self.__currentConfig = 0
            self.mcafit = ClassMcaTheory.McaTheory(initdict)
        self.__concentrationsKeys = []
        if self._concentrations:
            self._tool = ConcentrationsTool.ConcentrationsTool()
            self._toolConversion = ConcentrationsTool.ConcentrationsConversion()
        self.setFileList(filelist)
        self.setOutputDir(outputdir)
        if fitimages:
            self.fitImages=  1
            self.__ncols  =  None
        else:
            self.fitImages = False
            self.__ncols = None
        self.fileStep = filestep
        self.mcaStep  = mcastep
        self.useExistingFiles = not overwrite
        self.savedImages=[]
        if roifit   is None:roifit   = False
        if roiwidth is None:roiwidth = 100.
        self.pleaseBreak = 0
        self.roiFit   = roifit
        self.roiWidth = roiwidth
        self.fileBeginOffset = filebeginoffset
        self.fileEndOffset   = fileendoffset
        self.mcaOffset = mcaoffset
        self.chunk     = chunk
        self.selection = selection
        self.quiet = quiet


    def setFileList(self,filelist=None):
        self._rootname = ""
        if filelist is None:
            filelist = []
        if type(filelist) not in [type([]), type((2,))]:
            filelist = [filelist]
        self._filelist=filelist
        if len(filelist):
            if type(filelist[0]) is not numpy.ndarray:
                self._rootname = self.getRootName(filelist)

    def getRootName(self,filelist=None):
        if filelist is None:filelist = self._filelist
        first = os.path.basename(filelist[ 0])
        last  = os.path.basename(filelist[-1])
        if first == last:return os.path.splitext(first)[0]
        name1,ext1 = os.path.splitext(first)
        name2,ext2 = os.path.splitext(last )
        i0=0
        for i in range(len(name1)):
            if i >= len(name2):
                break
            elif name1[i] == name2[i]:
                pass
            else:
                break
        i0 = i
        for i in range(i0,len(name1)):
            if i >= len(name2):
                break
            elif name1[i] != name2[i]:
                pass
            else:
                break
        i1 = i
        if i1 > 0:
            delta=1
            while (i1-delta):
                if (last[(i1-delta)] in ['0', '1', '2',
                                        '3', '4', '5',
                                        '6', '7', '8',
                                        '9']):
                    delta = delta + 1
                else:
                    if delta > 1: delta = delta -1
                    break
            rootname = name1[0:]+"_to_"+last[(i1-delta):]
        else:
            rootname = name1[0:]+"_to_"+last[0:]
        return rootname

    def setOutputDir(self,outputdir=None):
        if outputdir is None:outputdir=os.getcwd()
        self._outputdir = outputdir

    def processList(self):
        self.counter =  0
        self.__row   = self.fileBeginOffset - 1
        self.__stack = None
        for i in range(0+self.fileBeginOffset,
                       len(self._filelist)-self.fileEndOffset,
                       self.fileStep):
            if not self.roiFit:
                if len(self.__configList) > 1:
                    if i != 0:
                        self.mcafit = ClassMcaTheory.McaTheory(self.__configList[i])
                        self.__currentConfig = i
            self.mcafit.enableOptimizedLinearFit()
            
            inputfile   = self._filelist[i]
            self.__row += 1 #should be plus fileStep?
            self.onNewFile(inputfile, self._filelist)
            self.filehandle = self.getFileHandle(inputfile)
            if self.pleaseBreak: break
            if self.__stack is None:
                self.__stack = False
                if hasattr(self.filehandle, "info"):
                    if "SourceType" in self.filehandle.info:
                        if self.filehandle.info["SourceType"] in\
                           ["EdfFileStack", "HDF5Stack1D"]:
                            self.__stack = True
            if self.__stack:
                self.__processStack()
                if self._HDF5:
                    # The complete stack has been analyzed
                    break
            else:
                self.__processOneFile()
            # Needed for cleanup
            self.filehandle = None

        if self.counter:
            if not self.roiFit:
                if self.fitFiles:
                    self.listfile.write(']\n')
                    self.listfile.close()
            if (self.__ncols is not None) and (not self._nosave):
                if self.__ncols:self.saveImage()
        self.onEnd()

    def getFileHandle(self,inputfile):
        
        try:
            self._HDF5 = False
            if type(inputfile) == numpy.ndarray:
                try:
                    a = NumpyStack.NumpyStack(inputfile)
                    return a
                except Exception as e:
#                     print e
                    raise
        
            if HDF5SUPPORT:
                if h5py.is_hdf5(inputfile):
                    self._HDF5 = True
                    # if (len(self._filelist) == 1) && (self.mcaStep > 1)
                    # it should attempt to avoid loading  many times
                    # the stack into memory in case of multiple processes
                    return HDF5Stack1D.HDF5Stack1D(self._filelist,
                                                   self.selection)

            ffile = self.__tryEdf(inputfile)
            if ffile is None:
                ffile = self.__tryLucia(inputfile)
            if ffile is None:
                if inputfile[-3:] == "DAT":
                    ffile = self.__tryAifira(inputfile)
            if ffile is None:
                if LispixMap.isLispixMapFile(inputfile):
                    ffile = LispixMap.LispixMap(inputfile, native=False)
            if (ffile is None):
                del ffile
                ffile   = SpecFileLayer.SpecFileLayer()
                ffile.SetSource(inputfile)
            return ffile
        except Exception:
            raise IOError("I do not know what to do with file %s" % inputfile)

    @property
    def filehandle(self):
        return self._filehandle
    
    @filehandle.setter
    def filehandle(self, value):
        try:
            del self._filehandle.Source
        except AttributeError:
            pass
        self._filehandle = value

    def onNewFile(self,ffile, filelist):
        if not self.quiet:
            self.__log(ffile)

    def onImage(self,image,imagelist):
        pass

    def onMca(self,mca,nmca, filename=None, key=None, info=None):
        pass


    def onEnd(self):
        pass

    def __log(self,text):
        print(text)

    def __tryEdf(self,inputfile):
        try:
            ffile   = EdfFileLayer.EdfFileLayer(fastedf=0)
            ffile.SetSource(inputfile)
            fileinfo = ffile.GetSourceInfo()
            if fileinfo['KeyList'] == []:
                ffile=None
            elif len(self._filelist) == 1:
                #Is it a Diamond stack?
                if len(fileinfo['KeyList']) > 1:
                    info, data = ffile.LoadSource(fileinfo['KeyList'][0])
                    shape = data.shape
                    if len(shape) == 2:
                        if min(shape) == 1:
                            #It is a Diamond Stack
                            ffile=EDFStack.EDFStack(inputfile)
            return ffile
        except Exception:
            return None

    def __tryLucia(self, inputfile):
        f = open(inputfile)
        line = f.readline()
        f.close()
        ffile = None
        if line.startswith('#\tDate:'):
            ffile = LuciaMap.LuciaMap(inputfile)
        return ffile

    def __tryAifira(self, inputfile):
        if sys.platform == "win32":
            f = open(inputfile,"rb")
        else:
            f = open(inputfile,"r")
        line = f.read(3)
        f.close()
        if '#' in line:
            #specfile
            return None
        ffile = None
        try:
            ffile = AifiraMap.AifiraMap(inputfile)
        except Exception:
            ffile = None
        return ffile

    def __processStack(self):
        stack = self.filehandle
        info = stack.info
        data = stack.data
        xStack = None
        if hasattr(stack, "x"):
            if stack.x not in [None, []]:
                if type(stack.x) == type([]):
                    xStack = stack.x[0]
                else:
                    print("THIS SHOULD NOT BE USED")
                    xStack = stack.x
        nimages = stack.info['Dim_1']
        self.__nrows = nimages
        numberofmca = stack.info['Dim_2']
        keylist = ["1.1"] * nimages
        for i in range(nimages):
            keylist[i] = "1.%04d" % i

        for i in range(nimages):
            if self.pleaseBreak: break
            self.onImage(keylist[i], keylist)
            self.__ncols = numberofmca
            colsToIter = range(0+self.mcaOffset,
                                     numberofmca,
                                     self.mcaStep)
            self.__row = i
            self.__col = -1
            try:
                cache_data = data[i, :, :]
            except Exception:
                print("Error reading dataset row %d" % i)
                print(sys.exc_info())
                print("Batch resumed")
                continue
            for mca in colsToIter:
                if self.pleaseBreak: break
                self.__col = mca
                mcadata = cache_data[mca, :]
                y0  = numpy.array(mcadata)
                if xStack is None:
                    if 'MCA start ch' in info:
                        xmin = float(info['MCA start ch'])
                    else:
                        xmin = 0.0
                    x = numpy.arange(len(y0))*1.0 + xmin
                else:
                    x = xStack
                #key = "%s.%s.%02d.%02d" % (scan,order,row,col)
                key = "%s.%04d" % (keylist[i], mca)
                #I only process the first file of the stack?
                filename = os.path.basename(info['SourceName'][0])
                infoDict = {}
                infoDict['SourceName'] = info['SourceName']
                infoDict['Key']        = key
                if "McaLiveTime" in info:
                    infoDict["McaLiveTime"] = \
                            info["McaLiveTime"][i * numberofmca + mca]
                self.__processOneMca(x, y0, filename, key, info=infoDict)
                self.onMca(mca, numberofmca, filename=filename,
                                            key=key,
                                            info=infoDict)

    def __processOneFile(self):
        ffile=self.filehandle
        fileinfo = ffile.GetSourceInfo()
        if 1:
            i = 0
            for scankey in  fileinfo['KeyList']:
                if self.pleaseBreak: break
                self.onImage(scankey, fileinfo['KeyList'])
                scan,order = scankey.split(".")
                info,data  = ffile.LoadSource(scankey)
                if info['SourceType'] == "EdfFile":
                    nrows = int(info['Dim_1'])
                    ncols = int(info['Dim_2'])
                    numberofmca  = ncols
                    self.__ncols = len(range(0+self.mcaOffset,numberofmca,self.mcaStep))
                    self.__col  = -1
                    for mca_index in range(self.__ncols):
                        mca = 0 + self.mcaOffset + mca_index * self.mcaStep
                        if self.pleaseBreak: break
                        self.__col += 1
                        mcadata = data[mca,:]
                        if 'MCA start ch' in info:
                            xmin = float(info['MCA start ch'])
                        else:
                            xmin = 0.0
                        key = "%s.%s.%04d" % (scan,order,mca)
                        y0  = numpy.array(mcadata)
                        x = numpy.arange(len(y0))*1.0 + xmin
                        filename = os.path.basename(info['SourceName'])
                        infoDict = {}
                        infoDict['SourceName'] = info['SourceName']
                        infoDict['Key']        = key
                        infoDict['McaLiveTime'] = info.get('McaLiveTime', None)
                        self.__processOneMca(x,y0,filename,key,info=infoDict)
                        self.onMca(mca, numberofmca, filename=filename,
                                                    key=key,
                                                    info=infoDict)
                else:
                    if info['NbMca'] > 0:
                        self.fitImages = True
                        numberofmca = info['NbMca'] * 1
                        self.__ncols = len(range(0+self.mcaOffset,
                                             numberofmca,self.mcaStep))
                        numberOfMcaToTakeFromScan = self.__ncols * 1
                        self.__col   = -1
                        scan_key = "%s.%s" % (scan,order)
                        scan_obj= ffile.Source.select(scan_key)
                        #I assume always same number of detectors and
                        #same offset for each detector otherways I would
                        #slow down everything to deal with not very common
                        #situations
                        #if self.__row == 0:
                        if self.counter == 0:
                            self.__chann0List = numpy.zeros(info['NbMcaDet'])
                            chan0list = scan_obj.header('@CHANN')
                            if len(chan0list):
                                for i in range(info['NbMcaDet']):
                                    self.__chann0List[i] = int(chan0list[i].split()[2])
                            # The calculation of self.__ncols is wrong if there are
                            # several scans containing MCAs. One needs to multiply by
                            # the number of scans assuming all of them contain MCAs.
                            # We have to assume the same structure in all files.
                            # Only in the case of "pseudo" two scan files where only
                            # the second scan contains MCAs we do not multiply.
                            if (len(fileinfo['KeyList']) == 2) and (fileinfo['KeyList'].index(scan_key) == 1):
                                # leave self.__ncols untouched
                                self.__ncolsModified = False
                            else:
                                # multiply by the number of scans
                                self.__ncols *= len(fileinfo['KeyList'])
                                self.__ncolsModified = True

                        #import time
                        for mca_index in range(numberOfMcaToTakeFromScan):
                            i = 0 + self.mcaOffset + mca_index * self.mcaStep
                            #e0 = time.time()
                            if self.pleaseBreak: break
                            if self.__ncolsModified:
                                self.__col = i + \
                                      fileinfo['KeyList'].index(scan_key) * \
                                      numberofmca
                            else:
                                self.__col += 1
                            point = int(i/info['NbMcaDet']) + 1
                            mca   = (i % info['NbMcaDet'])  + 1
                            key = "%s.%s.%05d.%d" % (scan,order,point,mca)
                            autotime = self.mcafit.config["concentrations"].get(\
                                        "useautotime", False)
                            if autotime:
                                #slow info reading methods needed to access time
                                mcainfo,mcadata = ffile.LoadSource(key)
                                info['McaLiveTime'] = mcainfo.get('McaLiveTime',
                                                              None)
                            else:
                                mcadata = scan_obj.mca(i+1)
                            y0  = numpy.array(mcadata)
                            x = numpy.arange(len(y0))*1.0 + \
                                self.__chann0List[mca-1]
                            filename = os.path.basename(info['SourceName'])

                            infoDict = {}
                            infoDict['SourceName'] = info['SourceName']
                            infoDict['Key']        = key
                            infoDict['McaLiveTime'] = info.get('McaLiveTime',
                                                               None)
                            self.__processOneMca(x,y0,filename,key,info=infoDict)
                            self.onMca(i, info['NbMca'],filename=filename,
                                                    key=key,
                                                    info=infoDict)
                            #print "remaining = ",(time.time()-e0) * (info['NbMca'] - i)

    def __getFitFile(self, filename, key):
        fitdir = self.os_path_join(self._outputdir,"FIT")
        fitdir = self.os_path_join(fitdir,filename+"_FITDIR")
        outfile = filename +"_"+key+".fit"
        outfile = self.os_path_join(fitdir,  outfile)
        return outfile

    def os_path_join(self, a, b):
        try:
            outfile=os.path.join(a, b)
        except UnicodeDecodeError:
            toBeDone = True
            if sys.platform == 'win32':
                try:
                    outfile=os.path.join(a.decode('mbcs'),
                                         b.decode('mbcs'))
                    toBeDone = False
                except UnicodeDecodeError:
                    pass
            if toBeDone:
                try:
                    outfile = os.path.join(a.decode('utf-8'),
                                           a.decode('utf-8'))
                except UnicodeDecodeError:
                    outfile = os.path.join(a.decode('latin-1'),
                                           a.decode('latin-1'))
        return outfile

    def __processOneMca(self,x,y,filename,key,info=None):
        self._concentrationsAsAscii = ""
        if not self.roiFit:
            result = None
            concentrationsdone = 0
            concentrations = None
            outfile=self.os_path_join(self._outputdir, filename)
            fitfile = self.__getFitFile(filename,key)
            if self.chunk is not None:
                con_extension = "_%06d_partial_concentrations.txt" % self.chunk
            else:
                con_extension = "_concentrations.txt"
            self._concentrationsFile = self.os_path_join(self._outputdir,
                                    self._rootname+ con_extension)
            #                        self._rootname+"_concentrationsNEW.txt")
            if self.counter == 0:
                if os.path.exists(self._concentrationsFile):
                    try:
                        os.remove(self._concentrationsFile)
                    except Exception:
                        print("I could not delete existing concentrations file %s" %\
                              self._concentrationsFile)
            #print "self._concentrationsFile", self._concentrationsFile
            if self.useExistingFiles and os.path.exists(fitfile):
                useExistingResult = 1
                try:
                    dict = ConfigDict.ConfigDict()
                    dict.read(fitfile)
                    result = dict['result']
                    if 'concentrations' in dict:
                        concentrationsdone = 1
                except Exception:
                    print("Error trying to use result file %s" % fitfile)
                    print("Please, consider deleting it.")
                    print(sys.exc_info())
                    return
            else:
                useExistingResult = 0
                try:
                    # Make sure the fit limits are taken from the configuration
                    self.mcafit.config['fit']['use_limit'] = 1
                    self.mcafit.setData(x,y, time=info.get("McaLiveTime", None))
                except Exception:
                    print("Error entering data of file with output = %s\n%s" %\
                          (filename, sys.exc_info()[1]))
                    # make sure the configuration is restored
                    if self.mcafit.config['fit'].get("strategyflag", False):
                        config = self.__configList[self.__currentConfig]
                        print("Restoring fitconfiguration")
                        self.mcafit = ClassMcaTheory.McaTheory(config)
                        self.mcafit.enableOptimizedLinearFit()
                    return
                try:
                    self.mcafit.estimate()
                    if self.fitFiles:
                        fitresult, result = self.mcafit.startfit(digest=1)
                    elif self._concentrations and (self.mcafit._fluoRates is None):
                        fitresult, result = self.mcafit.startfit(digest=1)
                    elif self._concentrations:
                        fitresult = self.mcafit.startfit(digest=0)
                        try:
                            fitresult0 = {}
                            fitresult0['fitresult'] = fitresult
                            fitresult0['result'] = self.mcafit.imagingDigestResult()
                            fitresult0['result']['config'] = self.mcafit.config
                            conf = self.mcafit.configure()
                            tconf = self._tool.configure()
                            if 'concentrations' in conf:
                                tconf.update(conf['concentrations'])
                            else:
                                #what to do?
                                pass
                            concentrations = self._tool.processFitResult(config=tconf,
                                            fitresult=fitresult0,
                                            elementsfrommatrix=False,
                                            fluorates = self.mcafit._fluoRates)
                        except Exception:
                            print("error in concentrations")
                            print(sys.exc_info()[0:-1])
                        concentrationsdone = True
                    else:
                        #just images
                        fitresult = self.mcafit.startfit(digest=0)
                except Exception:
                    print("Error fitting file with output = %s: %s)" %\
                          (filename, sys.exc_info()[1]))
                    if self.mcafit.config['fit'].get("strategyflag", False):
                        config = self.__configList[self.__currentConfig]
                        print("Restoring fitconfiguration")
                        self.mcafit = ClassMcaTheory.McaTheory(config)
                        self.mcafit.enableOptimizedLinearFit()
                    return
            if self._concentrations:
                if concentrationsdone == 0:
                    if not ('concentrations' in result):
                        if useExistingResult:
                            fitresult0={}
                            fitresult0['result'] = result
                            conf = result['config']
                        else:
                            fitresult0={}
                            if result is None:
                                result = self.mcafit.digestresult()
                            fitresult0['result']    = result
                            fitresult0['fitresult'] = fitresult
                            conf = self.mcafit.configure()
                        tconf = self._tool.configure()
                        if 'concentrations' in conf:
                            tconf.update(conf['concentrations'])
                        else:
                            pass
                            #print "Concentrations not calculated"
                            #print "Is your fit configuration file correct?"
                            #return
                        try:
                            concentrations = self._tool.processFitResult(config=tconf,
                                            fitresult=fitresult0,
                                            elementsfrommatrix=False)
                        except Exception:
                            print("error in concentrations")
                            print(sys.exc_info()[0:-1])
                            #return
                self._concentrationsAsAscii=self._toolConversion.getConcentrationsAsAscii(concentrations)
                if len(self._concentrationsAsAscii) > 1:
                    text  = ""
                    text += "SOURCE: "+ filename +"\n"
                    text += "KEY: "+key+"\n"
                    text += self._concentrationsAsAscii + "\n"
                    f=open(self._concentrationsFile,"a")
                    f.write(text)
                    f.close()

            #output options
            # .FIT files
            if self.fitFiles:
                fitdir = self.os_path_join(self._outputdir,"FIT")
                if not os.path.exists(fitdir):
                    try:
                        os.mkdir(fitdir)
                    except Exception:
                        print("I could not create directory %s" % fitdir)
                        return
                fitdir = self.os_path_join(fitdir,filename+"_FITDIR")
                if not os.path.exists(fitdir):
                    try:
                        os.mkdir(fitdir)
                    except Exception:
                        print("I could not create directory %s" % fitdir)
                        return
                if not os.path.isdir(fitdir):
                    print("%s does not seem to be a valid directory" % fitdir)
                else:
                    outfile = filename +"_"+key+".fit"
                    outfile = self.os_path_join(fitdir,  outfile)
                if not useExistingResult:
                    result = self.mcafit.digestresult(outfile=outfile,
                                                      info=info)
                if concentrations is not None:
                    try:
                        f=ConfigDict.ConfigDict()
                        f.read(outfile)
                        f['concentrations'] = concentrations
                        try:
                            os.remove(outfile)
                        except Exception:
                            print("error deleting fit file")
                        f.write(outfile)
                    except Exception:
                        print("Error writing concentrations to fit file")
                        print(sys.exc_info())

                #python like output list
                if not self.counter:
                    name = os.path.splitext(self._rootname)[0]+"_fitfilelist.py"
                    name = self.os_path_join(self._outputdir,name)
                    try:
                        os.remove(name)
                    except Exception:
                        pass
                    self.listfile=open(name,"w+")
                    self.listfile.write("fitfilelist = [")
                    self.listfile.write('\n'+outfile)
                else:
                    self.listfile.write(',\n'+outfile)
            else:
                if not useExistingResult:
                    if 0:
                        #this is very slow and not needed just for imaging
                        if result is None:
                            result = self.mcafit.digestresult()
                    else:
                        if result is None:
                            result = self.mcafit.imagingDigestResult()

            #IMAGES
            if self.fitImages:
                #this only works with EDF
                if self.__ncols is not None:
                    if not self.counter:
                        if not self._nosave:
                            imgdir = self.os_path_join(self._outputdir,"IMAGES")
                            if not os.path.exists(imgdir):
                                try:
                                    os.mkdir(imgdir)
                                except Exception:
                                    print("I could not create directory %s" %\
                                          imgdir)
                                    return
                            elif not os.path.isdir(imgdir):
                                print("%s does not seem to be a valid directory" %\
                                      imgdir)
                            self.imgDir = imgdir

                        self.__peaks  = []
                        self.__images = {}
                        self.__sigmas = {}
                        if not self.__stack:
                            self.__nrows   = len(range(0, len(self._filelist), self.fileStep))
                        for group in result['groups']:
                            self.__peaks.append(group)
                            self.__images[group]= numpy.zeros((self.__nrows,
                                                               self.__ncols),
                                                               numpy.float64)
                            self.__sigmas[group]= numpy.zeros((self.__nrows,
                                                               self.__ncols),
                                                               numpy.float64)
                        self.__images['chisq']  = numpy.zeros((self.__nrows,
                                                               self.__ncols),
                                                               numpy.float64) - 1.
                        if self._concentrations:
                            layerlist = concentrations['layerlist']
                            if 'mmolar' in concentrations:
                                self.__conLabel = " mM"
                                self.__conKey   = "mmolar"
                            else:
                                self.__conLabel = " mass fraction"
                                self.__conKey   = "mass fraction"
                            for group in concentrations['groups']:
                                key = group+self.__conLabel
                                self.__concentrationsKeys.append(key)
                                self.__images[key] = numpy.zeros((self.__nrows,
                                                                  self.__ncols),
                                                                  numpy.float64)
                                if len(layerlist) > 1:
                                    for layer in layerlist:
                                        key = group+" "+layer
                                        self.__concentrationsKeys.append(key)
                                        self.__images[key] = numpy.zeros((self.__nrows,
                                                                    self.__ncols),
                                                                    numpy.float64)
                for peak in self.__peaks:
                    try:
                        self.__images[peak][self.__row, self.__col] = result[peak]['fitarea']
                        self.__sigmas[peak][self.__row, self.__col] = result[peak]['sigmaarea']
                    except Exception:
                        pass
                if self._concentrations:
                    layerlist = concentrations['layerlist']
                    for group in concentrations['groups']:
                        self.__images[group+self.__conLabel][self.__row, self.__col] = \
                                              concentrations[self.__conKey][group]
                        if len(layerlist) > 1:
                            for layer in layerlist:
                                self.__images[group+" "+layer] [self.__row, self.__col] = \
                                              concentrations[layer][self.__conKey][group]
                try:
                    self.__images['chisq'][self.__row, self.__col] = result['chisq']
                except Exception:
                    print("Error on chisq row %d col %d" %\
                          (self.__row, self.__col))
                    print("File = %s\n" % filename)
                    pass

        else:
                dict=self.mcafit.roifit(x,y,width=self.roiWidth)
                #this only works with EDF
                if self.__ncols is not None:
                    if not self.counter:
                        if not self._nosave:
                            imgdir = self.os_path_join(self._outputdir,"IMAGES")
                            if not os.path.exists(imgdir):
                                try:
                                    os.mkdir(imgdir)
                                except Exception:
                                    print("I could not create directory %s" %\
                                          imgdir)
                                    return
                            elif not os.path.isdir(imgdir):
                                print("%s does not seem to be a valid directory" %\
                                      imgdir)
                            self.imgDir = imgdir
                        self.__ROIpeaks  = []
                        self._ROIimages = {}
                        if not self.__stack:
                            self.__nrows   = len(self._filelist)
                        for group in dict.keys():
                            self.__ROIpeaks.append(group)
                            self._ROIimages[group]={}
                            for roi in dict[group].keys():
                                self._ROIimages[group][roi]=numpy.zeros((self.__nrows,
                                                                   self.__ncols),
                                                                   numpy.float64)
                if not hasattr(self, "_ROIimages"):
                    print("ROI fitting only supported on EDF")
                for group in self.__ROIpeaks:
                    for roi in self._ROIimages[group].keys():
                        try:
                            self._ROIimages[group][roi][self.__row, self.__col] = dict[group][roi]
                        except Exception:
                            print("error on (row,col) = %d,%d" %\
                                  (self.__row, self.__col))
                            print("File = %s" % filename)
                            pass

        #update counter
        self.counter += 1

    def saveImage(self,ffile=None):
        self.savedImages=[]
        if ffile is None:
            ffile = os.path.splitext(self._rootname)[0]
            ffile = self.os_path_join(self.imgDir,ffile)
        if not self.roiFit:
            if (self.fileStep > 1) or (self.mcaStep > 1):
                # REMARK: makes merging difficult and not necessary anyway
                trailing = ""
                #trailing = "_filestep_%02d_mcastep_%02d" % ( self.fileStep,
                #                                             self.mcaStep )
            else:
                trailing = ""
            
            #speclabel = "#L row  column"
            speclabel = "row  column"
            if self.chunk is None:
                suffix = ".edf"
            else:
                suffix = "_%06d_partial.edf" % self.chunk

            iterationList = self.__peaks * 1
            iterationList += ['chisq']
            if self._concentrations:
                iterationList += self.__concentrationsKeys
            for peak in iterationList:
                if peak in self.__peaks:
                    a,b = peak.split()
                    speclabel +="  %s" % (a+"-"+b)
                    speclabel +="  s(%s)" % (a+"-"+b)
                    edfname = ffile +"_"+a+"_"+b+trailing+suffix
                elif peak in self.__concentrationsKeys:
                    speclabel +="  %s" % peak.replace(" ","-")
                    edfname = ffile +"_"+peak.replace(" ","_")+trailing+suffix
                elif peak == 'chisq':
                    speclabel +="  %s" % (peak)
                    edfname = ffile +"_"+peak+trailing+suffix
                else:
                    print("Unhandled peak name: %s. Not saved." % peak)
                    continue
                dirname = os.path.dirname(edfname)
                if not os.path.exists(dirname):
                    try:
                        os.mkdir(dirname)
                    except Exception:
                        print("I could not create directory %s" % dirname)
                Append = 0
                if os.path.exists(edfname):
                    try:
                        os.remove(edfname)
                    except Exception:
                        print("I cannot delete output file")
                        print("trying to append image to the end")
                        Append = 1
                edfout   = EdfFile.EdfFile(edfname, access='ab')
                edfout.WriteImage ({'Title':peak} , self.__images[peak], Append=Append)
                edfout = None
                self.savedImages.append(edfname)
            #save specfile format
            if self.chunk is None:
                specname = ffile+trailing+".dat"
            else:
                specname = ffile+trailing+"_%06d_partial.dat" % self.chunk
            if os.path.exists(specname):
                try:
                    os.remove(specname)
                except Exception:
                    pass
            specfile=open(specname,'w+')
            #specfile.write('\n')
            #specfile.write('#S 1  %s\n' % (file+trailing))
            #specfile.write('#N %d\n' % (len(self.__peaks)+2))
            specfile.write('%s\n' % speclabel)
            specline=""
            imageRows = self.__images['chisq'].shape[0]
            imageColumns = self.__images['chisq'].shape[1]
            for row in range(imageRows):
                for col in range(imageColumns):
                    specline += "%d" % row
                    specline += "  %d" % col
                    for peak in self.__peaks:
                        #write area
                        specline +="  %g" % self.__images[peak][row][col]
                        #write sigma area
                        specline +="  %g" % self.__sigmas[peak][row][col]
                    #write global chisq
                    specline +="  %g" % self.__images['chisq'][row][col]
                    if self._concentrations:
                        for peak in self.__concentrationsKeys:
                            specline +="  %g" % self.__images[peak][row][col]
                    specline += "\n"
                    specfile.write("%s" % specline)
                    specline =""
            specfile.write("\n")
            specfile.close()
        else:
            for group in self.__ROIpeaks:
                i = 0
                grouptext = group.replace(" ","_")
                for roi in self._ROIimages[group].keys():
                    #roitext = roi.replace(" ","-")
                    if (self.fileStep > 1) or (self.mcaStep > 1):
                        edfname = ffile+"_"+grouptext+("_%04deVROI_filestep_%02d_mcastep_%02d.edf" % (self.roiWidth,
                                                                    self.fileStep, self.mcaStep ))
                    else:
                        edfname = ffile+"_"+grouptext+("_%04deVROI.edf" % self.roiWidth)
                    dirname = os.path.dirname(edfname)
                    if not os.path.exists(dirname):
                        try:
                            os.mkdir(dirname)
                        except Exception:
                            print("I could not create directory %s" % dirname)
                    edfout  = EdfFile.EdfFile(edfname)
                    edfout.WriteImage ({'Title':group+" "+roi} , self._ROIimages[group][roi],
                                         Append=i)
                    if i==0:
                        self.savedImages.append(edfname)
                        i=1


def main(args):
    if not args.filelist:
        print("No input files provided.")
        return 0

    # Create batch object and process
    b = McaAdvancedFitBatch(
        args.cfg,
        args.filelist,
        args.outdir,
        args.roi,
        args.roiwidth
    )
    b.processList()


def build_parser():
    parser = CliUtils.create_parser(description="Batch MCA advanced fit (simple)")

    parser.add_argument("--cfg", "--pkm", dest="cfg", required=True, type=str, help="Configuration file")
    parser.add_argument("--outdir", default=None, type=str, help="Output directory")
    parser.add_argument("--roi", "--roifit", default=0, type=int, help="ROI fit")
    parser.add_argument("--roiwidth", default=250.0, type=float, help="ROI width")

    # Positional argument: list of input files
    parser.add_argument("filelist", nargs="*", help="Input files")

    return parser


if __name__ == "__main__":
    exit_code = CliUtils.cli_main(main, build_parser())
    sys.exit(exit_code)
