#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import time
import logging
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
from PyMca5.PyMcaIO import BrukerBCF
from PyMca5.PyMcaMisc import ProfilingUtils
from PyMca5.PyMcaMisc import CliUtils

try:
    import h5py
    from PyMca5.PyMcaIO import HDF5Stack1D
    HDF5SUPPORT = True
except ImportError:
    HDF5SUPPORT = False
from PyMca5.PyMcaIO import ConfigDict
from . import ConcentrationsTool
from .XRFBatchFitOutput import OutputBuffer


_logger = logging.getLogger(__name__)


def getRootName(filelist=None):
    if filelist is None:
        filelist = self._filelist
    first = os.path.basename(filelist[ 0])
    last = os.path.basename(filelist[-1])
    if first == last:
        return os.path.splitext(first)[0]
    name1, ext1 = os.path.splitext(first)
    name2, ext2 = os.path.splitext(last)
    i0 = 0
    for i in range(len(name1)):
        if i >= len(name2):
            break
        elif name1[i] == name2[i]:
            pass
        else:
            break
    i0 = i
    for i in range(i0, len(name1)):
        if i >= len(name2):
            break
        elif name1[i] != name2[i]:
            pass
        else:
            break
    i1 = i
    if i1 > 0:
        delta = 1
        while (i1-delta):
            if (last[i1-delta] in ['0', '1', '2',
                                    '3', '4', '5',
                                    '6', '7', '8',
                                    '9']):
                delta = delta + 1
            else:
                if delta > 1:
                    delta = delta - 1
                break
        rootname = name1[0:]+"_to_"+name2[(i1-delta):]
    else:
        rootname = name1[0:]+"_to_"+name2[0:]
    return rootname


class McaAdvancedFitBatch(object):
    """
    XRF or ROI fit of a list of files, representing XRF data from a 2D map.
    It is currently assumed that one file contains either the data from the
    entire map (one .h5 file) or the data from one row (multiple .edf files).
    """

    def __init__(self, initdict, filelist=None, outputdir=None,
                 roifit=False, roiwidth=100,
                 overwrite=1, filestep=1, mcastep=1,
                 fitfiles=0, fitimages=1,
                 concentrations=0, fitconcfile=1,
                 filebeginoffset=0, fileendoffset=0,
                 mcaoffset=0, chunk=None,
                 selection=None, lock=None, nosave=None,
                 quiet=False, outbuffer=None,
                 **outbufferkwargs):
        """
        Range of filelist indices to be processed:

        .. code:: python

            range(filebeginoffset, len(filelist)-fileendoffset, filestep)

        Range of column indices to be processed for each file:

        .. code:: python

            range(mcaoffset, nColumns, mcastep)

        """
        #for the time being the concentrations are bound to the .fit files
        #that is not necessary, but it will be correctly implemented in
        #future releases
        self._lock = lock

        self.setFileList(filelist)
        self.pleaseBreak = 0  # stop the processing of filelist
        self.roiFit = roifit
        self.roiWidth = roiwidth
        self.selection = selection
        self.quiet = quiet
        self.fitFiles = fitfiles
        self.fitConcFile = fitconcfile
        self._concentrations = concentrations

        # Assume each file in filelist = 1 row of XRF spectra
        # Files to be fitted: range(filebeginoffset, nFiles-fileEndOffset, filestep)
        # Columns to be fitted: range(mcaOffset, nColumns, mcaStep)
        self.fileBeginOffset = filebeginoffset
        self.fileEndOffset = fileendoffset
        self.fileStep = filestep
        self.mcaStep = mcastep
        self.mcaOffset = mcaoffset
        self.chunk = chunk

        if isinstance(initdict, list):
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

        self.outbuffer = outbuffer
        self.overwrite = overwrite
        self.nosave = nosave
        self.outputdir = outputdir
        self.outbufferkwargs = outbufferkwargs
        if fitimages:
            self._initOutputBuffer()

    @property
    def useExistingFiles(self):
        return not self.overwrite

    @property
    def nosave(self):
        return self._nosave

    @nosave.setter
    def nosave(self, value):
        self._nosave = bool(value)
        if self.outbuffer is not None:
            self.outbuffer.nosave = self._nosave

    @property
    def overwrite(self):
        return self._overwrite

    @overwrite.setter
    def overwrite(self, value):
        self._overwrite = bool(value)
        if self.outbuffer is not None:
            self.outbuffer.overwrite = self._overwrite

    def _initOutputBuffer(self):
        if self.outbuffer is None:
            self.outbuffer = OutputBuffer(outputDir=self.outputdir,
                                          outputRoot=self._rootname,
                                          fileEntry=self._rootname,
                                          overwrite=self.overwrite,
                                          nosave=self.nosave,
                                          suffix=self._outputSuffix(),
                                          **self.outbufferkwargs)
        # Always save figures-of-merit (HDF5: all, EDF/CSV: chisq only)
        self.outbuffer.saveFOM = True
        self.outbuffer['configuration'] = self.mcafit.getConfiguration()

    def _outputSuffix(self):
        suffix = ""
        if self.roiFit:
            suffix = "_%04deVROI" % self.roiWidth
        # REMARK: makes merging difficult and not necessary anyway
        #if (self.fileStep > 1) or (self.mcaStep > 1):
        #    suffix += "_filestep_%02d_mcastep_%02d" %\
        #                (self.fileStep, self.mcaStep)
        if self.chunk is not None:
            suffix += "_%06d_partial" % self.chunk
        return suffix

    def setFileList(self, filelist=None):
        self._rootname = ""
        if filelist is None:
            filelist = []
        if type(filelist) not in [type([]), type((2,))]:
            filelist = [filelist]
        self._filelist = filelist
        if len(filelist):
            if type(filelist[0]) is not numpy.ndarray:
                self._rootname = getRootName(filelist)

    @property
    def outputdir(self):
        return self._outputdir

    @outputdir.setter
    def outputdir(self, value):
        if value is None:
            value = os.getcwd()
        self._outputdir = value

    def processList(self):
        if self.outbuffer is None:
            self._processList()
        else:
            with self.outbuffer.saveContext():
                self._processList()
        self.onEnd()

    def _processList(self):
        # Initialize list processing variables
        self.counter = 0  # spectrum counter
        self.__ncols = 0
        self.__nrows = 0
        self.__stack = None
        self._fitlistfile = None

        # Loop over the files in filelist (1 file = 1 row in image)
        start = self.fileBeginOffset
        stop = len(self._filelist)-self.fileEndOffset
        for i in range(start, stop, self.fileStep):
            if not self.roiFit:
                if len(self.__configList) > 1:
                    if i != 0:
                        self.mcafit = ClassMcaTheory.McaTheory(self.__configList[i])
                        self.__currentConfig = i
                        # TODO: outbuffer does not support multiple configurations
                        #       Only the first one is saved.
            self.mcafit.enableOptimizedLinearFit()  # TODO: why????

            # Load file
            inputfile = self._filelist[i]
            self.__row = i
            self.onNewFile(inputfile, self._filelist)
            self.filehandle = self.getFileHandle(inputfile)
            if self.pleaseBreak:
                break
            if self.__stack is None:
                self.__stack = False
                if hasattr(self.filehandle, "info"):
                    if "SourceType" in self.filehandle.info:
                        if self.filehandle.info["SourceType"] in\
                        ["EdfFileStack", "HDF5Stack1D"]:
                            self.__stack = True

            # Fit spectra in current file
            if self.__stack:
                self.__processStack()
                if self._HDF5:
                    # The complete stack has been analyzed
                    # TODO: what if the user gave more than one HDF5 file?
                    break
                else:
                    _logger.warning("Multiple stacks may no work yet")
                    # TODO: I doubt this works for multiple non-HDF5 stacks
                    #       because __processStack restarts from __row = 0
            else:
                self.__processOneFile()

            # Needed for cleanup
            self.filehandle = None

        if self.counter:
            # Finish list of FIT files
            if not self.roiFit and self.fitFiles and \
                self._fitlistfile is not None:
                    self._fitlistfile.write(']\n')
                    self._fitlistfile.close()

    def getFileHandle(self, inputfile):
        try:
            self._HDF5 = False
            if type(inputfile) == numpy.ndarray:
                return NumpyStack.NumpyStack(inputfile)

            if HDF5SUPPORT:
                if h5py.is_hdf5(inputfile):
                    self._HDF5 = True
                    # if (len(self._filelist) == 1) && (self.mcaStep > 1)
                    # it should attempt to avoid loading  many times
                    # the stack into memory in case of multiple processes
                    if len(self._filelist) == 1:
                        scanlist = self.selection.get("entry", None)
                    else:
                        scanlist = None
                    return HDF5Stack1D.HDF5Stack1D(self._filelist,
                                                   self.selection,
                                                   scanlist=scanlist)

            ffile = self.__tryEdf(inputfile)
            if ffile is None:
                if BrukerBCF.HAS_BCF_SUPPORT:
                    if BrukerBCF.isBrukerBCFFile(inputfile):
                        ffile = BrukerBCF.BrukerBCF(inputfile)
            if ffile is None:
                ffile = self.__tryLucia(inputfile)
            if ffile is None:
                if inputfile[-3:] == "DAT":
                    ffile = self.__tryAifira(inputfile)
            if ffile is None:
                if LispixMap.isLispixMapFile(inputfile):
                    ffile = LispixMap.LispixMap(inputfile, native=False)
            if ffile is None:
                del ffile
                ffile = SpecFileLayer.SpecFileLayer()
                ffile.SetSource(inputfile)
            return ffile
        except Exception:
            _logger.critical("I do not know what to do with file %s" % inputfile)
            raise

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

    def onNewFile(self, ffile, filelist):
        if not self.quiet:
            self.__log(ffile)

    def onImage(self, image, imagelist):
        pass

    def onMca(self, imca, nmca, filename=None, key=None, info=None):
        pass

    def onEnd(self):
        pass

    def __log(self,text):
        _logger.info(text)

    def __tryEdf(self,inputfile):
        try:
            ffile = EdfFileLayer.EdfFileLayer(fastedf=0)
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
                            ffile = EDFStack.EDFStack(inputfile)
            return ffile
        except Exception:
            return None

    def __tryLucia(self, inputfile):
        f = open(inputfile, "rb")
        line = f.read(10)
        f.close()
        ffile = None
        if line.startswith(b'#\tDate:'):
            ffile = LuciaMap.LuciaMap(inputfile)
        return ffile

    def __tryAifira(self, inputfile):
        f = open(inputfile,"rb")
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
        """
        Fit spectra from one file, which corresponds to the spectra
        from the entire image.
        """
        stack = self.filehandle
        info = stack.info
        data = stack.data
        xStack = None
        if hasattr(stack, "x"):
            if stack.x not in [None, []]:
                if type(stack.x) == type([]):
                    xStack = stack.x[0]
                else:
                    _logger.warning("THIS SHOULD NOT BE USED")
                    xStack = stack.x
        nrows = stack.info['Dim_1']
        self.__nrows = nrows
        self.__ncols = stack.info['Dim_2']
        mcaIndices = list(range(self.mcaOffset, self.__ncols, self.mcaStep))
        nmcaToFit = len(mcaIndices)
        keylist = ["1.1"] * nrows
        for i in range(nrows):
            keylist[i] = "1.%04d" % i

        for i in range(nrows):
            if self.pleaseBreak:
                break
            self.onImage(keylist[i], keylist)
            self.__row = i
            try:
                cache_data = data[i, :, :]
            except Exception:
                _logger.error("Error reading dataset row %d" % i)
                _logger.error(str(sys.exc_info()))
                _logger.error("Batch resumed")
                continue
            for imca, mcaIndex in enumerate(mcaIndices):
                if self.pleaseBreak:
                    break
                self.__col = mcaIndex
                mcadata = cache_data[mcaIndex, :]
                y0 = numpy.array(mcadata)
                if xStack is None:
                    if 'MCA start ch' in info:
                        xmin = float(info['MCA start ch'])
                    else:
                        xmin = 0.0
                    x = numpy.arange(len(y0))*1.0 + xmin
                else:
                    x = xStack
                #key = "%s.%s.%02d.%02d" % (scan,order,row,col)
                key = "%s.%04d" % (keylist[i], mcaIndex)
                #I only process the first file of the stack?
                filename = os.path.basename(info['SourceName'][0])
                infoDict = {}
                infoDict['SourceName'] = info['SourceName']
                infoDict['Key'] = key
                if "McaLiveTime" in info:
                    infoDict["McaLiveTime"] = \
                            info["McaLiveTime"][i * self.__ncols + mcaIndex]
                self.__processOneMca(x, y0, filename, key, info=infoDict)
                self.onMca(imca, nmcaToFit, filename=filename,
                           key=key, info=infoDict)

    def __processOneFile(self):
        """
        Fit spectra from one file, which corresponds to the spectra
        from one image row.
        """
        ffile = self.filehandle
        fileinfo = ffile.GetSourceInfo()
        if self.counter == 0:
            self.__nMcaPerScan = None

        # In case of multiple scans:
        # assume they have the same number of spectra
        for scankey in fileinfo['KeyList']:
            if self.pleaseBreak:
                break
            self.onImage(scankey, fileinfo['KeyList'])
            scan, order = scankey.split(".")
            info, data = ffile.LoadSource(scankey)
            if info['SourceType'] == "EdfFile":
                # nMcaChan = info['Dim_1'])
                self.__ncols = int(info['Dim_2'])
                mcaIndices = list(range(self.mcaOffset, self.__ncols, self.mcaStep))
                nmcaToFit = len(mcaIndices)
                for imca, mcaIndex in enumerate(mcaIndices):
                    if self.pleaseBreak:
                        break
                    self.__col = mcaIndex
                    mcadata = data[mcaIndex, :]
                    if 'MCA start ch' in info:
                        xmin = float(info['MCA start ch'])
                    else:
                        xmin = 0.0
                    key = "%s.%s.%04d" % (scan, order, mcaIndex)
                    y0 = numpy.array(mcadata)
                    x = numpy.arange(len(y0))*1.0 + xmin
                    filename = os.path.basename(info['SourceName'])
                    infoDict = {}
                    infoDict['SourceName'] = info['SourceName']
                    infoDict['Key'] = key
                    infoDict['McaLiveTime'] = info.get('McaLiveTime', None)
                    self.__processOneMca(x, y0, filename, key, info=infoDict)
                    self.onMca(imca, nmcaToFit, filename=filename,
                               key=key, info=infoDict)
            else:
                if info['NbMca'] == 0:
                    continue
                scan_key = "%s.%s" % (scan, order)
                scan_obj = ffile.Source.select(scan_key)
                if self.__nMcaPerScan is None:
                    self.__nMcaPerScan = info['NbMca'] * 1
                    self.__chann0List = numpy.zeros(info['NbMcaDet'])
                    chan0list = scan_obj.header('@CHANN')
                    if len(chan0list):
                        for i in range(info['NbMcaDet']):
                            self.__chann0List[i] = int(chan0list[i].split()[2])
                    if (len(fileinfo['KeyList']) == 2) and (fileinfo['KeyList'].index(scan_key) == 1):
                        # "pseudo": two scans and only the second contains MCA's
                        self.__ncols = self.__nMcaPerScan
                    else:
                        self.__ncols = self.__nMcaPerScan*len(fileinfo['KeyList'])
                else:
                    # Skip scan when not enough spectra
                    # When more spectra than the first scan: skip the excess spectra
                    if (info['NbMca'] * 1) < self.__nMcaPerScan:
                        _logger.error('Skip scan {} (not enough MCA spectra)'
                                      .format(repr(scan_key)))
                        continue

                mcaIndices = list(range(self.mcaOffset, self.__nMcaPerScan, self.mcaStep))
                nmcaToFit = len(mcaIndices)
                multipleScans = self.__ncols > self.__nMcaPerScan
                for imca, mcaIndex in enumerate(mcaIndices):
                    if self.pleaseBreak:
                        break
                    self.__col = mcaIndex
                    if multipleScans:
                        self.__col += fileinfo['KeyList'].index(scan_key) * \
                                        self.__nMcaPerScan

                    point = int(mcaIndex/info['NbMcaDet']) + 1
                    mca = (mcaIndex % info['NbMcaDet']) + 1
                    key = "%s.%s.%05d.%d" % (scan, order, point, mca)
                    autotime = self.mcafit.config["concentrations"].get("useautotime", False)
                    if autotime:
                        # slow info reading methods needed to access time
                        mcainfo, mcadata = ffile.LoadSource(key)
                        info['McaLiveTime'] = mcainfo.get('McaLiveTime', None)
                    else:
                        mcadata = scan_obj.mca(mcaIndex+1)
                    y0 = numpy.array(mcadata)
                    x = numpy.arange(len(y0))*1.0 + self.__chann0List[mca-1]
                    filename = os.path.basename(info['SourceName'])

                    infoDict = {}
                    infoDict['SourceName'] = info['SourceName']
                    infoDict['Key'] = key
                    infoDict['McaLiveTime'] = info.get('McaLiveTime', None)
                    self.__processOneMca(x, y0, filename, key, info=infoDict)
                    self.onMca(imca, nmcaToFit, filename=filename,
                               key=key, info=infoDict)

    def __getFitFile(self, filename, key, createdirs=False):
        fitdir = self.os_path_join(self.outputdir, "FIT")
        if createdirs:
            if not os.path.exists(fitdir):
                try:
                    os.makedirs(fitdir)
                except Exception:
                    _logger.error("I could not create directory %s" % fitdir)
                    return
        fitdir = self.os_path_join(fitdir, filename+"_FITDIR")
        if createdirs:
            if not os.path.exists(fitdir):
                try:
                    os.makedirs(fitdir)
                except Exception:
                    _logger.error("I could not create directory %s" % fitdir)
                    return
            if not os.path.isdir(fitdir):
                _logger.error("%s does not seem to be a valid directory" % fitdir)
                return
        fitfilename = filename + "_" + key + ".fit"
        fitfilename = self.os_path_join(fitdir, fitfilename)
        return fitfilename

    def __getFitConcFile(self):
        if self.chunk is not None:
            con_extension = "_%06d_partial_concentrations.txt" % self.chunk
        else:
            con_extension = "_concentrations.txt"
        if not os.path.exists(self.outputdir):
            os.makedirs(self.outputdir)
        cfitfilename = self.os_path_join(self.outputdir,
                                self._rootname + con_extension)
        if self.counter == 0:
            if os.path.exists(cfitfilename):
                try:
                    os.remove(cfitfilename)
                except Exception:
                    _logger.error("I could not delete existing concentrations file %s" %\
                        cfitfilename)
        return cfitfilename

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
        if not self.__nrows:
            self.__nrows = len(self._filelist)
        bOutput = self.outbuffer is not None and \
                  self.__ncols and self.__nrows
        if self.roiFit:
            result = self.__roiOneMca(x,y)
            if bOutput and result is not None:
                if not self.outbuffer.hasAllocatedMemory():
                    self._allocateMemoryRoiFit(result)
                self._storeRoiFitResult(result)
        else:
            result, concentrations = self.__fitOneMca(x,y,filename,key,info=info)
            if bOutput and result is not None:
                result['ydata0'] = y
                if not self.outbuffer.hasAllocatedMemory():
                    if self._concentrations and (concentrations is None):
                        # if concentrations were requested but unsuccessful on the first MCA
                        # the memory allocation crashes the program
                        _logger.error("Cannot allocate memory due to error on concentrations")
                    else:
                        self._allocateMemoryFit(result, concentrations)
                        self._storeFitResult(result, concentrations)
                        _logger.info("Memory allocated")
                else:
                    self._storeFitResult(result, concentrations)
        self.counter += 1

    def __fitOneMca(self,x,y,filename,key,info=None):
        fitresult = None
        result = None
        concentrations = None
        concentrationsInFitFile = False

        # Fit MCA
        fitfile = self.__getFitFile(filename,key,createdirs=False)
        if os.path.exists(fitfile) and not self.overwrite:
            # Load MCA data when needed
            if self.outbuffer.saveDataDiagnostics:
                if not self._attemptMcaLoad(x, y, filename, info=info):
                    return result, concentrations
            # Load result from FIT file
            try:
                fitdict = ConfigDict.ConfigDict()
                fitdict.read(fitfile)
                concentrations = fitdict.get('concentrations', None)
                concentrationsInFitFile = bool(concentrations)
                result = fitdict['result']
            except Exception:
                _logger.error("Error trying to use result file %s" % fitfile)
                _logger.error("Please, consider deleting it.")
                _logger.error(str(sys.exc_info()))
                return result, concentrations
        else:
            # Load MCA data
            if not self._attemptMcaLoad(x, y, filename, info=info):
                return result, concentrations
            # Fit XRF spectrum
            fitresult, result, concentrations = self._fitMca(filename)

        # Extract/calculate + save concentrations
        if result:
            # TODO: 'concentrations' in result, when does this happens and should we pop it????
            concentrationsInResult = 'concentrations' not in result
        else:
            concentrationsInResult = False
        if self._concentrations and concentrationsInResult:
            result, concentrations = self._concentrationsFromResult(fitresult, result)
        if self.fitConcFile and concentrations is not None and not concentrationsInFitFile:
            self._updateConcFile(concentrations, filename, key)

        # Digest fit result when not already digested
        if self.fitFiles:
            # Create/update existing FIT file
            fitfile = self.__getFitFile(filename, key, createdirs=True)
            if fitresult:  # TODO: why not "and result is None"?
                result = self.mcafit.digestresult(outfile=fitfile,
                                                  info=info)
            if fitfile:
                if concentrations and not concentrationsInFitFile:
                    self._updateFitFile(concentrations, fitfile)
                self._updateFitFileList(fitfile)
        else:
            if fitresult and result is None:
                # Use imagingDigestResult instead of digestresult:
                # faster and digestresult is not needed just for imaging
                result = self.mcafit.imagingDigestResult()

        return result, concentrations

    def _attemptMcaLoad(self, x, y, filename, info=None):
        try:
            # Make sure the fit limits are taken from the configuration
            self.mcafit.config['fit']['use_limit'] = 1
            self.mcafit.setData(x, y, time=info.get("McaLiveTime", None))
        except Exception:
            self._restoreFitConfig(filename, 'entering data')
            return False
        return True

    def _restoreFitConfig(self, filename, task):
        _logger.error("Error %s of file with output = %s\n%s" %\
                    (task, filename, sys.exc_info()[1]))
        # Restore when a fit strategy like `matrix adjustment` is used
        if self.mcafit.config['fit'].get("strategyflag", False):
            config = self.__configList[self.__currentConfig]
            _logger.info("Restoring fitconfiguration")
            self.mcafit = ClassMcaTheory.McaTheory(config)
            self.mcafit.enableOptimizedLinearFit()  # TODO: why???

    def _fitMca(self, filename):
        result = None
        concentrations = None
        fitresult = None
        try:
            self.mcafit.estimate()
            # Avoid digest=1 when possible (slow but more detailed information)
            digest = self.fitFiles or\
                     (self._concentrations and (self.mcafit._fluoRates is None))
            if self.outbuffer is not None:
                # TODO: we need a full digest although only yfit and ydata
                # are needed, which are thrown away by Gefit.LeastSquaresFit
                digest |= self.outbuffer.saveDataDiagnostics
            if digest:
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
                    concentrations = None
                    _logger.error("error in concentrations")
                    _logger.error(str(sys.exc_info()[0:-1]))
                    self._restoreFitConfig(filename,
                                           'calculating concentrations')
            else:
                #just images
                fitresult = self.mcafit.startfit(digest=0)
        except Exception:
            self._restoreFitConfig(filename, 'fitting data')
        return fitresult, result, concentrations

    def _concentrationsFromResult(self, fitresult, result):
        if fitresult:
            fitresult0 = {}
            if result is None:
                result = self.mcafit.digestresult()
            fitresult0['result'] = result
            fitresult0['fitresult'] = fitresult
            conf = self.mcafit.configure()
        else:
            fitresult0 = {}
            fitresult0['result'] = result
            conf = result['config']
        tconf = self._tool.configure()
        if 'concentrations' in conf:
            tconf.update(conf['concentrations'])
        else:
            pass
            #_logger.error("Concentrations not calculated")
            #_logger.error("Is your fit configuration file correct?")
        try:
            concentrations = self._tool.processFitResult(config=tconf,
                            fitresult=fitresult0,
                            elementsfrommatrix=False)
        except Exception:
            _logger.error("error in concentrations")
            _logger.error(str(sys.exc_info()[0:-1]))
            concentrations = None
        return result, concentrations

    def _updateFitFile(self, concentrations, outfile):
        """Add concentrations to fit file
        """
        try:
            f = ConfigDict.ConfigDict()
            f.read(outfile)
            f['concentrations'] = concentrations
            try:
                os.remove(outfile)
            except Exception:
                _logger.error("error deleting fit file")
            f.write(outfile)
        except Exception:
            _logger.error("Error writing concentrations to fit file")
            _logger.error(str(sys.exc_info()))

    def _updateFitFileList(self, outfile):
        """Append FIT file to list of FIT files
        """
        if self.counter:
            self._fitlistfile.write(',\n'+outfile)
        else:
            name = self._rootname +"_fitfilelist.py"
            name = self.os_path_join(self.outputdir,name)
            try:
                os.remove(name)
            except Exception:
                pass
            self._fitlistfile = open(name,"w+")
            self._fitlistfile.write("fitfilelist = [")
            self._fitlistfile.write('\n'+outfile)

    def _updateConcFile(self, concentrations, filename, key):
        if not self.fitConcFile or concentrations is None:
            return
        concentrationsAsAscii = self._toolConversion.getConcentrationsAsAscii(concentrations)
        if len(concentrationsAsAscii) > 1:
            text = ""
            text += "SOURCE: "+ filename +"\n"
            text += "KEY: "+key+"\n"
            text += concentrationsAsAscii + "\n"
            f = open(self.__getFitConcFile(),"a")
            f.write(text)
        f.close()

    def __roiOneMca(self,x,y):
        return self.mcafit.roifit(x,y,width=self.roiWidth)

    def _allocateMemoryFit(self, result, concentrations):
        if self._concentrations:
            if 'mmolar' in concentrations:
                self.__conKey = "mmolar"
            else:
                self.__conKey = "mass fraction"

        outbuffer = self.outbuffer

        # Fit parameters and their uncertainties
        labels = result['groups']
        nFree = len(labels)
        imageShape = self.__nrows, self.__ncols
        paramShape = nFree, self.__nrows, self.__ncols
        dtypeResult = numpy.float32
        dataAttrs = {} #{'units':'counts'}
        paramAttrs = {'errors': 'uncertainties', 'default': not self._concentrations}
        outbuffer.allocateMemory('parameters',
                                 shape=paramShape,
                                 dtype=dtypeResult,
                                 fill_value=numpy.nan,
                                 labels=labels,
                                 dataAttrs=dataAttrs,
                                 groupAttrs=paramAttrs,
                                 memtype='ram')
        outbuffer.allocateMemory('uncertainties',
                                 shape=paramShape,
                                 dtype=dtypeResult,
                                 fill_value=numpy.nan,
                                 labels=labels,
                                 dataAttrs=dataAttrs,
                                 groupAttrs=None,
                                 memtype='ram')

        # Concentrations
        if self._concentrations:
            groupAttrs = {'default': True}
            if 'mmolar' in concentrations:
                concentration_key = 'molarconcentrations'
                dataAttrs = {} #{'units': 'mM'}
            else:
                concentration_key = 'massfractions'
                dataAttrs = {}
            self._concentration_key = concentration_key
            labels = concentrations['groups']
            layerlist = concentrations['layerlist']
            if len(layerlist) > 1:
                labels += [(group, layer)
                            for group in concentrations['groups']
                            for layer in layerlist]
            nConcFree = len(concentrations['groups'])
            paramShape = nConcFree, self.__nrows, self.__ncols
            outbuffer.allocateMemory(concentration_key,
                                     shape=paramShape,
                                     dtype=dtypeResult,
                                     fill_value=numpy.nan,
                                     labels=labels,
                                     dataAttrs=dataAttrs,
                                     groupAttrs=groupAttrs,
                                     memtype='ram')

        # Model ,residuals, chisq ,...
        if outbuffer.diagnostics:
            xdata0 = self.mcafit.xdata0.flatten().astype(numpy.float32) # x (channels or energy)
            xdata = self.mcafit.xdata.flatten().astype(numpy.float32)   # x (after fit limits)
            stackShape = self.__nrows, self.__ncols, len(xdata0)
            mcaIndex = 2
            iXMin, iXMax = int(max(numpy.where(xdata0 <= xdata[0])[0])), \
                           int(min(numpy.where(xdata0 >= xdata[-1])[0])) + 1
            self._mcaIdx = slice(iXMin, iXMax)
            nObs = iXMax-iXMin
            if outbuffer.saveFOM:
                outbuffer.allocateMemory('nFreeParameters',
                                         group='diagnostics',
                                         shape=imageShape,
                                         fill_value=nFree,
                                         dtype=numpy.int32,
                                         dataAttrs=None,
                                         groupAttrs=None,
                                         memtype='ram')
                outbuffer.allocateMemory('nObservations',
                                         group='diagnostics',
                                         shape=imageShape,
                                         fill_value=nObs,
                                         dtype=numpy.int32,
                                         dataAttrs=None,
                                         groupAttrs=None,
                                         memtype='ram')
                outbuffer.allocateMemory('chisq',
                                         group='diagnostics',
                                         shape=imageShape,
                                         fill_value=numpy.nan,
                                         dtype=dtypeResult,
                                         dataAttrs=None,
                                         groupAttrs=None,
                                         memtype='ram')
            dataAttrs = {} #{'units':'counts'}
            fitAttrs = {}
            if outbuffer.saveDataDiagnostics:
                # Generic axes
                dataAxesNames = ['dim{}'.format(i) for i in range(len(stackShape))]
                dataAxes = [(name, numpy.arange(n, dtype=dtypeResult), {})
                            for name, n in zip(dataAxesNames, stackShape)]
                if 'config' in result:
                    cfg = result['config']
                else:
                    cfg = self.mcafit.getConfiguration()
                mcacfg = cfg['detector']
                linear = cfg["fit"]["linearfitflag"]
                if linear or (mcacfg['fixedzero'] and mcacfg['fixedgain']):
                    #zero = result['fittedpar'][result['parameters'].index('Zero')]
                    #gain = result['fittedpar'][result['parameters'].index('Gain')]
                    zero = mcacfg['zero']
                    gain = mcacfg['gain']
                    xenergy = zero + gain * xdata0
                    dataAxesNames[mcaIndex] = 'energy'
                    dataAxes[mcaIndex] = 'energy', xenergy.astype(dtypeResult), {'units': 'keV'}
                    dataAxes.append(('channels', xdata0.astype(numpy.float32), {}))
                fitAttrs['axes'] = dataAxes
                fitAttrs['axesused'] = dataAxesNames
            if outbuffer.saveFit:
                fitmodel = outbuffer.allocateMemory('model',
                                                    group='fit',
                                                    shape=stackShape,
                                                    dtype=dtypeResult,
                                                    fill_value=numpy.nan,
                                                    chunks=True,
                                                    dataAttrs=dataAttrs,
                                                    groupAttrs=fitAttrs,
                                                    memtype='hdf5')
                #idx = [slice(None)]*fitmodel.ndim
                #idx[mcaIndex] = slice(0, iXMin)
                #fitmodel[tuple(idx)] = numpy.nan
                #idx[mcaIndex] = slice(iXMax, None)
                #fitmodel[tuple(idx)] = numpy.nan
            if outbuffer.saveData:
                outbuffer.allocateMemory('data',
                                         group='fit',
                                         shape=stackShape,
                                         dtype=dtypeResult,
                                         fill_value=numpy.nan,
                                         chunks=True,
                                         dataAttrs=dataAttrs,
                                         groupAttrs=fitAttrs,
                                         memtype='hdf5')
            if outbuffer.saveResiduals:
                outbuffer.allocateMemory('residuals',
                                         group='fit',
                                         shape=stackShape,
                                         dtype=dtypeResult,
                                         fill_value=numpy.nan,
                                         chunks=True,
                                         dataAttrs=dataAttrs,
                                         groupAttrs=fitAttrs,
                                         memtype='hdf5')

    def _storeFitResult(self, result, concentrations):
        outbuffer = self.outbuffer

        # Fit parameters and their uncertainties
        output = outbuffer['parameters']
        outputs = outbuffer['uncertainties']
        for i, group in enumerate(outbuffer.labels('parameters')):
            output[i, self.__row, self.__col] = result[group]['fitarea']
            outputs[i, self.__row, self.__col] = result[group]['sigmaarea']
        # Concentrations
        if self._concentrations:
            output = outbuffer[self._concentration_key]
            for i, label in enumerate(outbuffer.labels(self._concentration_key)):
                if isinstance(label, tuple):
                    group, layer = label
                    output[i, self.__row, self.__col] = concentrations[layer][self.__conKey][group]
                else:
                    output[i, self.__row, self.__col] = concentrations[self.__conKey][label]
        # Diagnostics: model, residuals, chisq ,...
        if outbuffer.diagnostics:
            if outbuffer.saveFOM:
                outbuffer['chisq'][self.__row, self.__col] = result['chisq']
            idx = self.__row, self.__col, self._mcaIdx
            idxall = self.__row, self.__col, slice(None)
            if outbuffer.saveFit:
                output = outbuffer['model']
                output[idx] = result['yfit']
            if outbuffer.saveData:
                output = outbuffer['data']
                output[idxall] = result['ydata0']
            if outbuffer.saveResiduals:
                output = outbuffer['residuals']
                output[idx] = result['yfit'] - result['ydata']

    def _allocateMemoryRoiFit(self, result):
        outbuffer = self.outbuffer

        # Fit parameters (ROIs)
        labels = [(group, roi.replace(' ROI', ''))
                  for group, rois in result.items()
                  for roi in rois]
        nFree = len(labels)
        paramShape = nFree, self.__nrows, self.__ncols
        dtypeResult = numpy.float32
        dataAttrs = {} #{'units':'counts'}
        groupAttrs = {'default': True}
        outbuffer.allocateMemory('roi',
                                 shape=paramShape,
                                 dtype=dtypeResult,
                                 labels=labels,
                                 dataAttrs=dataAttrs,
                                 groupAttrs=groupAttrs,
                                 memtype='ram')

    def _storeRoiFitResult(self, result):
        outbuffer = self.outbuffer
        output = outbuffer['roi']
        for i, label in enumerate(outbuffer.labels('roi')):
            group, roi = label
            output[i, self.__row, self.__col] = result[group][roi+' ROI']


def main(args):
    filelist = args.filelist
    if not filelist:
        _logger.warning("No input files provided.")
        return 0

    t0 = time.time()

    # Setup output buffer
    outbuffer = OutputBuffer(
        outputDir=args.outdir,
        outputRoot=args.outroot,
        fileEntry=args.outentry,
        fileProcess=args.outprocess,
        diagnostics=args.diagnostics,
        tif=args.tif,
        edf=args.edf,
        csv=args.csv,
        h5=args.h5,
        dat=args.dat,
        multipage=args.multipage,
        overwrite=1  # original code always sets overwrite=1
    )

    # Profiling context
    with ProfilingUtils.profile(memory=args.debug, time=args.debug):
        b = McaAdvancedFitBatch(
            args.cfg,
            filelist=filelist,
            fitfiles=False,
            outputdir=args.outdir,
            roifit=args.roi,
            roiwidth=args.roiwidth,
            concentrations=args.concentrations,
            outbuffer=outbuffer,
            overwrite=1
        )
        b.processList()
        print("Total Elapsed = %s " % (time.time() - t0))


def build_parser():
    parser = CliUtils.create_parser(description="Batch MCA advanced fit")

    parser.add_argument("--cfg", "--pkm", dest="cfg", required=True, type=str, help="Configuration file")
    parser.add_argument("--outdir", default=None, type=str, help="Output directory")
    parser.add_argument("--roi", "--roifit", default=0, type=int, help="ROI fit")
    parser.add_argument("--roiwidth", default=250.0, type=float, help="ROI width")
    parser.add_argument("--tif", "--tiff", default=0, type=int, help="Write TIFF files")
    parser.add_argument("--edf", default=1, type=int, help="Write EDF files")
    parser.add_argument("--csv", default=0, type=int, help="Write CSV files")
    parser.add_argument("--h5", default=1, type=int, help="Write HDF5 files")
    parser.add_argument("--dat", default=0, type=int, help="Write DAT files")
    parser.add_argument("--multipage", default=0, type=int, help="Multipage output")
    parser.add_argument("--diagnostics", default=0, type=int, help="Enable diagnostics")
    parser.add_argument("--concentrations", default=0, type=int, help="Compute concentrations")
    parser.add_argument("--outroot", default="", type=str, help="Output root name")
    parser.add_argument("--outentry", default="", type=str, help="File entry")
    parser.add_argument("--outprocess", default="", type=str, help="File process")

    # Positional arguments: list of input files
    parser.add_argument("filelist", nargs="*", help="Input files")

    return parser


if __name__ == "__main__":
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
