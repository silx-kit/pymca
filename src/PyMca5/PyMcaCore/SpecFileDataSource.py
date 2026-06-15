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
import time
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaIO import specfilewrapper as specfile

_logger = logging.getLogger(__name__)


SOURCE_TYPE = "SpecFile"

# Scan types
# ----------
SF_EMPTY       = 0        # empty scan
SF_SCAN        = 1        # non-empty scan
SF_MESH        = 2        # mesh scan
SF_MCA         = 4        # single mca
SF_NMCA        = 8        # multi mca (more than 1 mca per acq)
SF_UMCA        = 16       # mca number does not match pts number


class SpecFileDataSource(object):
    Error= "SpecFileDataError"

    def __init__(self, nameInput):
        if type(nameInput) == type([]):
            nameList = nameInput
        else:
            nameList = [nameInput]
        if len(nameList) > 1:
            #who knows if one day will make selections thru several files...
            raise TypeError("Constructor needs string as first argument")
        testTypes = [type("")]

        for name in nameList:
            if type(name) not in testTypes:
                raise TypeError("Constructor needs string as first argument")
        self.sourceName   = nameInput
        self.sourceType   = SOURCE_TYPE
        self.__sourceNameList = nameList
        self.__source_info_cached = None

        self.refresh()

    def refresh(self):
        self._sourceObjectList = []
        self.__fileHeaderList = []
        #for name in self.__sourceNameList:
        #    if not os.path.exists(name):
        #        raise ValueError("File %s does not exists" % name)
        for name in self.__sourceNameList:
            self._sourceObjectList.append(specfile.Specfile(name))
            self.__fileHeaderList.append(False)
        self.__lastKeyInfo = {}

    def getSourceInfo(self):
        """
        Returns information about the specfile object created by
        the constructor to give application possibility to know about
        it before loading.
        Returns a dictionary with the key "KeyList" (list of all available keys
        in this source). Each element in "KeyList" has the form 'n1.n2' where
        n1 is the scan number and n2 the order number in file starting at 1.
        """
        return self.__getSourceInfo()

    def __getSourceInfo(self):
        scanlist=self.__getScanList()
        source_info={}
        source_info["Size"]       = len(scanlist)
        source_info["KeyList"]    = scanlist
        source_info["SourceType"] = SOURCE_TYPE

        HAS_CACHED_INFO = False
        if self.__source_info_cached:
            if self.__source_info_cached["SourceName"] == self.__sourceNameList[0]:
                HAS_CACHED_INFO = True

        num_mca = []
        num_pts = []
        commands = []
        sf_type = []
        for i in scanlist:
            CACHE_INDEX = None
            if HAS_CACHED_INFO:
                if i in self.__source_info_cached["KeyList"]:
                    if i != self.__source_info_cached["KeyList"][-1]:
                        # information in cache and it was not the last scan
                        # at that time. We can use the cached information
                        self.__fileHeaderList[0] = self.__source_info_cached["FileHeader"]
                        CACHE_INDEX = self.__source_info_cached["KeyList"].index(i)
            if CACHE_INDEX is not None: # it can be 0 and still use the cache
                num_mca.append(self.__source_info_cached["NumMca"][CACHE_INDEX])
                num_pts.append(self.__source_info_cached["NumPts"][CACHE_INDEX])
                commands.append(self.__source_info_cached["Commands"][CACHE_INDEX])
                continue

            sel=self._sourceObjectList[0].select(i)
            if self.__fileHeaderList[0] == False:
                try:
                    self.__fileHeaderList[0] = sel.fileheader('')
                except Exception:
                    _logger.debug("getSourceInfo %s", sys.exc_info()[1])
                    self.__fileHeaderList[0] = None
            try:
                n = sel.nbmca()
            except Exception:
                n = 0
            num_mca.append(n)

            try:
                n = sel.lines()
            except Exception:
                n= 0
            num_pts.append(n)

            try:
                n = sel.command()
            except Exception:
                n= ""
            commands.append(n)
        source_info["SourceName"] = self.__sourceNameList[0]
        source_info["FileHeader"] = self.__fileHeaderList[0]
        source_info["NumMca"] = num_mca
        source_info["NumPts"] = num_pts
        source_info["Commands"] = commands
        source_info["ScanType"] = list(map(self.__getScanType, num_pts, num_mca, commands))
        self.__source_info_cached = source_info
        return source_info

    def __getScanList(self):
        aux= self._sourceObjectList[0].list().split(",")
        newlistcount=[]
        newlist=[]
        for i in aux:
            if not (":" in i):
                start_index=end_index=int(i)
            else:
                s= i.split(":")
                start_index=int(s[0])
                end_index=int(s[1])
            for j in range(start_index,end_index+1):
                newlist.append(j)
                newlistcount.append(newlist.count(j))
        for i in range(len(newlist)):
            newlist[i]="%d.%d" % (newlist[i],newlistcount[i])
        return newlist

    def __getScanType(self, num_pts, num_mca, command):
        stype= SF_EMPTY
        if num_pts>0:
                if command is None:
                    stype= SF_SCAN
                elif "mesh" in command:
                    stype= SF_MESH
                else:
                    stype= SF_SCAN
                if num_mca%num_pts:
                    stype+= SF_UMCA
                elif num_mca==num_pts:
                    stype+= SF_MCA
                elif num_mca>0:
                    stype+= SF_NMCA
        else:
                if num_mca==1:
                    stype= SF_MCA
                elif num_mca>1:
                    stype= SF_NMCA
        return stype


    def getKeyInfo (self, key):
        """
        If key given returns information of a perticular key.
        """
        fileName = self.__sourceNameList[0]
        key_type= self.__getKeyType(key)
        if key_type=="scan":
            scan_key= key
        elif key_type=="mca":
            (scan_key, mca_no)=self.__getMcaPars(key)
        key_info = self.__getScanInfo(scan_key)
        if os.path.exists(fileName):
            self.__lastKeyInfo[key] = os.path.getmtime(fileName)
        else:
            self.__lastKeyInfo[key] = key_info["Lines"] + \
                                      key_info["NbMca"]
        return key_info

    def __getKeyType (self,key):
        count= key.count('.')
        if (count==1):
            return "scan"
        elif (count==2) or (count==3):
            return "mca"
        else:
            raise KeyError("SpecFileDataSource: Invalid key")

    def __getScanInfo(self, scankey):
        index = 0
        sourceObject = self._sourceObjectList[index]
        scandata= sourceObject.select(scankey)

        info={}
        info["SourceType"] = SOURCE_TYPE
        #doubts about if refer to the list or to the individual file
        info["SourceName"] = self.sourceName
        info["Key"]        = scankey
        info['FileName']   = self.__sourceNameList[index]
        if self.__fileHeaderList[index] == False:
            try:
                self.__fileHeaderList[index] = scandata.fileheader('')
            except Exception:
                _logger.debug("getScanInfo %s", sys.exc_info()[1])
                self.__fileHeaderList[index] = None
        info["FileHeader"] = self.__fileHeaderList[index]
        try: info["Number"] = scandata.number()
        except Exception: info["Number"] = None
        try: info["Order"] = scandata.order()
        except Exception: info["Order"] = None
        try: info["Cols"] = scandata.cols()
        except Exception: info["Cols"] = 0
        try: info["Lines"] = scandata.lines()
        except Exception: info["Lines"] = 0
        try: info["Date"] = scandata.date()
        except Exception: info["Date"] = None
        if hasattr(scandata, "allmotors"):
            try:
                info["MotorNames"] = scandata.allmotors()
            except Exception:
                info["MotorNames"] = None
        else:
            try:
                info["MotorNames"] = sourceObject.allmotors()
            except Exception:
                info["MotorNames"] = None
        try: info["MotorValues"] = scandata.allmotorpos()
        except Exception: info["MotorValues"] = None
        try: info["LabelNames"] = scandata.alllabels()
        except Exception: info["LabelNames"] = []
        try: info["Command"] = scandata.command()
        except Exception: info["Command"] = None
        try: info["Header"] = scandata.header("")
        except Exception: info["Header"] = None
        try: info["NbMca"] = scandata.nbmca()
        except Exception: info["NbMca"] = 0
        try: info["hkl"] =  scandata.hkl()
        except Exception: info["hkl"] =  None
        if info["NbMca"]:
            if info["Lines"] > 0 and info["NbMca"] % info["Lines"] == 0:
                info["NbMcaDet"]= info["NbMca"] // info["Lines"]
            else:
                info["NbMcaDet"]= info["NbMca"]
        info["ScanType"]= self.__getScanType(info["Lines"], info["NbMca"], info["Command"])
        return info


    def __getMcaInfo(self, mcano, scandata, info=None):
        if info is None: info = {}
        mcainfo= {}
        if "NbMcaDet" in info:
            det= info["NbMcaDet"]
            if info["Lines"]>0:
                mcainfo["McaPoint"]= int(mcano/info["NbMcaDet"])+(mcano%info["NbMcaDet"]>0)
                mcainfo["McaDet"]= mcano-((mcainfo["McaPoint"]-1)*info["NbMcaDet"])
                try: mcainfo["LabelValues"]= scandata.dataline(mcainfo["McaPoint"])
                except Exception: mcainfo["LabelValues"]= None
            else:
                mcainfo["McaPoint"]= 0
                mcainfo["McaDet"]= mcano
                mcainfo["LabelValues"]= None
        calib= scandata.header("@CALIB")
        mcainfo["McaCalib"]=[0.0,1.0,0.0]
        if len(calib):
            if len(calib) == info["NbMcaDet"]:
                calib = [calib[mcainfo["McaDet"]-1]]
            else:
                _logger.debug("Number of calibrations does not match number of MCAs")
                if len(calib) == 1:
                    pass
                else:
                    raise ValueError("Number of calibrations does not match number of MCAs")
            ctxt= calib[0].split()
            if len(ctxt)==4:
                cval= [ float(ctxt[1]), float(ctxt[2]), float(ctxt[3]) ]
                mcainfo["McaCalib"]= cval
        ctime= scandata.header("@CTIME")
        if len(ctime):
            if len(ctime) == info["NbMcaDet"]:
                ctime = [ctime[mcainfo["McaDet"]-1]]
            else:
                _logger.debug("Number of counting times does not match number of MCAs")
                if len(ctime) == 1:
                    pass
                else:
                    raise ValueError("Number of counting times does not match number of MCAs")
            ctxt= ctime[0].split()
            if len(ctxt)==4:
                try:
                    mcainfo["McaPresetTime"]= float(ctxt[1])
                    mcainfo["McaLiveTime"]= float(ctxt[2])
                    mcainfo["McaRealTime"]= float(ctxt[3])
                except Exception:
                    pass

        chann = scandata.header("@CHANN")
        if len(chann):
            if len(chann) == info["NbMcaDet"]:
                chann = [chann[mcainfo["McaDet"] - 1]]
            else:
                _logger.debug("Number of @CHANN information does not match number of MCAs")
                if len(chann) == 1:
                    pass
                else:
                    raise ValueError("Number of @CHANN information does not match number of MCAs")
            ctxt= chann[0].split()
            if len(ctxt)==5:
                mcainfo['Channel0'] = float(ctxt[2])
            else:
                mcainfo['Channel0'] = 0.0
        else:
            mcainfo['Channel0'] = 0.0
        return mcainfo


    def __getMcaPars(self,key):
        index = 0
        nums= key.split('.')
        size = len(nums)
        sel_key = nums[0] + "." + nums[1]
        if size==3:
            mca_no=int(nums[2])
        elif size==4:
            sel=self._sourceObjectList[index].select(sel_key)
            try: lines = sel.lines()
            except Exception: lines=0
            if nums[3]==0: mca_no=int(nums[2])
            else:          mca_no=((int(nums[3])-1)*lines)+int(nums[2])
        else:
            raise KeyError("SpecFileData: Invalid key")
        return (sel_key,mca_no)

    def getDataObject(self,key,selection=None):
        """
        Parameters:
        * key: key to be read from source. It is a string
              using the following formats:

            "s.o": loads all counter values (s=scan number, o=order)
              - if ScanType==SCAN: in a 2D array (mot*cnts)
              - if ScanType==MESH: in a 3D array (mot1*mot2*cnts)
              - if ScanType==MCA: single MCA in 1D array (0:channels)

            "s.o.n": loads a single MCA in a 1D array (0:channels)
              - if ScanType==NMCA: n is the MCA number from 1 to N
              - if ScanType==SCAN+MCA: n is the scan point number (from 1)
              - if ScanType==MESH+MCA: n is the scan point number (from 1)

            "s.o.p.n": loads a single MCA in a 1D array (0:channels)
              - if ScanType==SCAN+NMCA:
                      p is the point number in the scan
                      n is the MCA device number
              - if ScanType==MESH+MCA:
                      p is first motor index
                      n is second motor index

            "s.o.MCA": loads all MCA in an array
              - if ScanType==SCAN+MCA: 2D array (pts*mca)
              - if ScanType==NMCA: 2D array (mca_det*mca)
              - if ScanType==MESH+MCA: 3D array (pts_mot1*pts_mot2*mca)
              - if ScanType==SCAN+NMCA: 3D array (pts_mot1*mca_det*mca)
              - if ScanType==MESH+NMCA:
                      creates N data page, one for each MCA device,
                      with a 3D array (pts_mot1*pts_mot2*mca)
        """
        key_type= self.__getKeyType(key)
        if key_type=="scan":
            scan_key= key
        elif key_type=="mca":
            (scan_key, mca_no)=self.__getMcaPars(key)
        if self.__source_info_cached is None:
            sourceinfo = self.getSourceInfo()
            sourcekeys = sourceinfo['KeyList']
        else:
            sourceinfo = self.__source_info_cached
            sourcekeys = sourceinfo['KeyList']
            if scan_key not in sourcekeys:
                sourceinfo = self.getSourceInfo()
                sourcekeys = sourceinfo['KeyList']
        if scan_key not in sourcekeys:
            raise KeyError("Key %s not in source keys" % key)

        mca3D = False
        _logger.debug("SELECTION = %s", selection)
        _logger.debug("key_type = %s", key_type)
        if key_type == "scan":
            if selection  is not None:
                if 'mcalist' in selection:
                    mca3D = True

        if (key_type=="scan") and (not mca3D):
            output = self._getScanData(key, raw = True)
            output.x = None
            output.y = None
            output.m = None
            output.info['selection'] = selection
            if selection is None:
                output.info['selectiontype'] = "2D"
                return output
            elif type(selection) != type({}):
                #I only understand index selections
                raise TypeError("Only selections of type {x:[],y:[],m:[]} understood")
            else:
                if 'x' in selection:
                    indexlist = []
                    for labelindex in selection['x']:
                        if labelindex != 0:
                            if 'cntlist' in selection:
                                label = selection['cntlist'][labelindex]
                            else:
                                label = output.info['LabelNames'][labelindex]
                        else:
                            label = output.info['LabelNames'][labelindex]
                        if label not in output.info['LabelNames']:
                            raise ValueError("Label %s not in scan labels" % label)
                        index = output.info['LabelNames'].index(label)
                        if output.x is None:
                            output.x = []
                        output.x.append(output.data[:, index])
                        indexlist.append(index)
                    output.info['selection']['x'] = indexlist
                if 'y' in selection:
                    indexlist = []
                    for labelindex in selection['y']:
                        if 'cntlist' in selection:
                            label = selection['cntlist'][labelindex]
                        else:
                            label = output.info['LabelNames'][labelindex]
                        if label not in output.info['LabelNames']:
                            raise ValueError("Label %s not in scan labels" % label)
                        index = output.info['LabelNames'].index(label)
                        if output.y is None:
                            output.y = []
                        output.y.append(output.data[:, index])
                        indexlist.append(index)
                    output.info['selection']['y'] = indexlist
                if 'm' in selection:
                    indexlist = []
                    for labelindex in selection['m']:
                        if 'cntlist' in selection:
                            label = selection['cntlist'][labelindex]
                        else:
                            label = output.info['LabelNames'][labelindex]
                        if label not in output.info['LabelNames']:
                            raise ValueError("Label %s not in scan labels" % label)
                        index = output.info['LabelNames'].index(label)
                        if output.m is None:
                            output.m = []
                        output.m.append(output.data[:, index])
                        indexlist.append(index)
                    output.info['selection']['m'] = indexlist
                output.info['selection']['cntlist'] = output.info['LabelNames']
                output.info['selectiontype'] = "1D"
                if output.x is not None:
                    output.info['selectiontype'] = "%dD" % len(output.x)
                output.data = None
        elif key_type=="mca":
            output = self._getMcaData(key)
            selectiontype = "1D"
            if selection  is not None:
                selectiontype = selection.get('selectiontype', "1D")
            output.info['selectiontype'] = selectiontype
            if output.info['selectiontype'] not in ['2D', '3D', 'STACK']:
                ch0 =  int(output.info['Channel0'])
                output.x = [numpy.arange(ch0, ch0 + len(output.data)).astype(numpy.float64)]
                output.y = [output.data[:].astype(numpy.float64)]
                output.m = None
                output.data = None
            else:
                output.x    = None
                output.y    = None
                output.m    = None
                output.data = None
                npoints = output.info['NbMca'] // output.info['NbMcaDet']
                index = 0
                scan_obj = self._sourceObjectList[index].select(scan_key)
                SPECFILE = True
                if isinstance(self._sourceObjectList[index], specfile.specfilewrapper):
                    SPECFILE = False
                for i in range(npoints):
                    if SPECFILE:
                        wmca_no= mca_no + output.info['NbMcaDet'] * i
                        mcaData= scan_obj.mca(wmca_no)
                    else:
                        mca_key = '%s.%d' % (scan_key, mca_no)
                        mcaData = self._getMcaData(mca_key).data
                    if i == 0:
                        nChannels = mcaData.shape[0]
                        output.data = numpy.zeros((npoints, nChannels), numpy.float32)
                    output.data[i,:] = mcaData
                #I have all the MCA data ready for image plot
                if selectiontype == 'STACK':
                    output.data = output.data.reshape(1, npoints, -1)
                    shape = output.data.shape
                    for i in range(len(shape)):
                        key = 'Dim_%d' % (i+1,)
                        output.info[key] = shape[i]
                    output.info["SourceType"] = "SpecFileStack"
                    output.info["SourceName"] = self.sourceName
                    output.info["Size"]       = shape[0] * shape[1]
                    output.info["NumberOfFiles"] = 1
                    output.info["FileIndex"] = 1
        elif (key_type=="scan") and mca3D:
            output = self._getScanData(key, raw = True)
            output.x = None
            output.y = None
            output.m = None
            #get the number of counters in the scan
            if 'cntlist' in selection:
                ncounters = len(selection['cntlist'])
            else:
                ncounters = output.info['LabelNames']

            # For the time being assume only one mca can be selected
            detectorNumber = selection['y'][0] - ncounters

            #read the first mca data of the first point
            mca_key = '%s.%d.%d' % (key, 1+detectorNumber, 1)
            mcaData = self._getMcaData(mca_key)
            ch0 = int(mcaData.info['Channel0'])
            calib = mcaData.info['McaCalib']
            nChannels = float(mcaData.data.shape[0])
            channels = numpy.arange(nChannels) + ch0

            #apply the calibration
            channels = calib[0] + calib[1] * channels +\
                       calib[2] * channels * channels

            ones =numpy.ones(nChannels)
            #get the different x components
            xselection = selection.get('x', [])
            if len(xselection) != 2:
                raise ValueError("You have to select two X axes")
            indexlist = []
            for labelindex in xselection:
                if labelindex != 0:
                    if 'cntlist' in selection:
                        label = selection['cntlist'][labelindex]
                    else:
                        label = output.info['LabelNames'][labelindex]
                else:
                    label = output.info['LabelNames'][labelindex]
                if label not in output.info['LabelNames']:
                    raise ValueError("Label %s not in scan labels" % label)
                index = output.info['LabelNames'].index(label)
                if output.x is None:
                    output.x = []
                output.x.append(output.data[:, index])
                indexlist.append(index)
            npoints = output.x[0].shape[0]
            output.info['selection'] = selection
            output.info['selection']['x'] = indexlist
            for i in range(len(output.x)):
                output.x[i] = numpy.outer(output.x[i], ones).flatten()
            tmp = numpy.outer(channels, numpy.ones(float(npoints))).flatten()
            output.x.append(tmp)
            output.y = [numpy.zeros(nChannels * npoints,numpy.float64)]
            for i in range(npoints):
                mca_key = '%s.%d.%d' % (key, 1+detectorNumber, 1)
                mcaData = self._getMcaData(mca_key)
                output.y[0][(i*nChannels):((i+1)*nChannels)] = mcaData.data[:]
            if 'm' in selection:
                indexlist = []
                for labelindex in selection['m']:
                    if 'cntlist' in selection:
                        label = selection['cntlist'][labelindex]
                    else:
                        label = output.info['LabelNames'][labelindex]
                    if label not in output.info['LabelNames']:
                        raise ValueError("Label %s not in scan labels" % label)
                    index = output.info['LabelNames'].index(label)
                    if output.m is None:
                            output.m = []
                    output.m.append(output.data[:, index])
                    indexlist.append(index)
                output.info['selection']['m'] = indexlist
                if output.m is not None:
                    output.m[0] = numpy.outer(output.m[0], ones).flatten()
            output.info['selection']['cntlist'] = output.info['LabelNames']
            output.info['selectiontype'] = "3D"
            output.info['LabelNames'] = selection['cntlist'] + selection['mcalist']

            output.data = None
        return output

    def _getScanData(self, scan_key, raw=False):
        index = 0
        scan_obj = self._sourceObjectList[index].select(scan_key)
        scan_info= self.__getScanInfo(scan_key)
        scan_info["Key"]      = scan_key
        scan_info["FileInfo"] = self.__getFileInfo()
        scan_type = scan_info["ScanType"]
        scan_data = None

        if scan_type&SF_SCAN:
            try:
                scan_data= numpy.transpose(scan_obj.data()).copy()
            except Exception:
                raise IOError("SF_SCAN read failed")
        elif scan_type&SF_MESH:
            try:
                if raw:
                    try:
                        scan_data= numpy.transpose(scan_obj.data()).copy()
                    except Exception:
                        raise IOError("SF_MESH read failed")
                else:
                    scan_array = scan_obj.data()
                    (mot1,mot2,cnts) = self.__getMeshSize(scan_array)
                    scan_data = numpy.zeros((mot1,mot2,cnts), numpy.float64)
                    for idx in range(mot2):
                        scan_data[:,idx,:] = numpy.transpose(scan_array[:,idx*mot1:(idx+1)*mot1]).copy()
                    scan_data = numpy.transpose(scan_data).copy()
            except Exception:
                raise IOError("SF_MESH read failed")
        elif scan_type&SF_MCA:
            try:
                scan_data = scan_obj.mca(1)
            except Exception:
                raise IOError("SF_MCA read failed")
        elif scan_type&SF_NMCA:
            try:
                scan_data = scan_obj.mca(1)
            except Exception:
                raise IOError("SF_NMCA read failed")

        if scan_data is not None:
            #create data object
            dataObject = DataObject.DataObject()
            #data.info = self.__getKeyInfo(key)
            dataObject.info = scan_info
            dataObject.data = scan_data
            return dataObject
        else:
            raise TypeError("getData unknown type")

    def _getMcaData(self, key):
        index = 0
        key_split= key.split(".")
        scan_key= key_split[0]+"."+key_split[1]
        scan_info = {}
        scan_info["Key"]= key
        scan_info["FileInfo"] = self.__getFileInfo()
        scan_obj = self._sourceObjectList[index].select(scan_key)
        scan_info.update(self.__getScanInfo(scan_key))
        scan_type= scan_info["ScanType"]
        scan_data= None
        mca_range= []        # for each dim., (name, length, values or None)

        if len(key_split)==3:
            if scan_type&SF_NMCA or scan_type&SF_MCA:
                try:
                    mca_no= int(key_split[2])
                    scan_data= scan_obj.mca(mca_no)
                except Exception:
                    raise IOError("Single MCA read failed")
            if scan_data is not None:
                scan_info.update(self.__getMcaInfo(mca_no, scan_obj, scan_info))
                dataObject = DataObject.DataObject()
                dataObject.info = scan_info
                dataObject.data = scan_data
                return dataObject

        elif len(key_split) == 4:
            if scan_type == SF_SCAN + SF_NMCA:
                try:
                    mca_no = (int(key_split[2])-1) * scan_info["NbMcaDet"] + \
                             int(key_split[3])
                    scan_data = scan_obj.mca(mca_no)
                except Exception:
                    raise IOError("SF_SCAN+SF_NMCA read failed")
            elif scan_type == SF_MESH + SF_MCA:
                try:
                    #scan_array= scan_obj.data()
                    #(mot1,mot2,cnts)= self.__getMeshSize(scan_array)
                    #mca_no= 1 + int(key_split[2]) + int(key_split[3])*mot1
                    mca_no = (int(key_split[2])-1) * scan_info["NbMcaDet"] + \
                              int(key_split[3])
                    _logger.debug("try to read mca number = %s", mca_no)
                    _logger.debug("total number of mca = %s", scan_info["NbMca"])
                    scan_data = scan_obj.mca(mca_no)
                except Exception:
                    raise IOError("SF_MESH+SF_MCA read failed")
            elif scan_type & SF_NMCA or scan_type & SF_MCA:
                try:
                    mca_no = (int(key_split[2])-1) * scan_info["NbMcaDet"] + \
                             int(key_split[3])
                    scan_data = scan_obj.mca(mca_no)
                except Exception:
                    raise IOError("SF_MCA or SF_NMCA read failed")
            else:
                raise TypeError("Unknown scan type!!!!!!!!!!!!!!!!")
            if scan_data is not None:
                scan_info.update(self.__getMcaInfo(mca_no, scan_obj, scan_info))
                dataObject = DataObject.DataObject()
                dataObject.info = scan_info
                dataObject.data = scan_data
                return dataObject

    def __getFileInfo(self):
        index = 0
        source = self._sourceObjectList[index]
        file_info={}
        try: file_info["Title"] = source.title()
        except Exception: file_info["Title"] = None
        try: file_info["User"] = source.user()
        except Exception: file_info["User"] = None
        try: file_info["Date"] = source.date()
        except Exception: file_info["Date"] = None
        try: file_info["Epoch"] = source.epoch()
        except Exception: file_info["Epoch"] = None
        try: file_info["ScanNo"] = source.scanno()
        except Exception: file_info["ScanNo"] = None
        return file_info

    def __getMeshSize(self, scan_array):
        """ Given the scandata array, return the size tuple of the mesh
        """
        mot2_array = scan_array[1]
        mot2_max = mot2_array.shape[0]
        mot1_idx = 1
        while mot1_idx < mot2_max and mot2_array[mot1_idx] == mot2_array[0]:
            mot1_idx+=1
        mot2_idx = scan_array.shape[1] // mot1_idx
        cnts_idx = scan_array.shape[0]
        return (mot1_idx, mot2_idx, cnts_idx)

    def __getScanMotorRange(self, info, obj):
        name = info["LabelNames"][0]
        values = obj.datacol(1)
        length = values.shape[0]
        return (name, values, length)

    def __getMeshMotorRange(self, info, obj):
        return ()

    def isUpdated(self, sourceName, key):
        #sourceName is redundant because only the first file is retained.
        index = 0
        if not os.path.exists(self.__sourceNameList[index]):
            if _logger.getEffectiveLevel() == logging.DEBUG:
                t0 = time.time()
            # bliss case
            if self.__source_info_cached is None:
                return False
            sourcekeys = self.__source_info_cached['KeyList']
            if key not in sourcekeys:
                return False
            if key != sourcekeys[-1]:
                # not the last key and only last scan is supposed to change
                return False
            # check the source might have changed respect to what is
            # available for this module
            key_info = self.__getScanInfo(key)
            npoints = key_info['Lines']
            nmca = key_info["NbMca"]
            if (npoints > self.__source_info_cached["NumPts"][-1]) or \
               (nmca > self.__source_info_cached["NumMca"][-1]):
                return True
            # the problem that remains is if there are new scans taken after the last
            # one was finished. That is supposed to be handled by the isUpdated method if present
            if hasattr(self._sourceObjectList[0], "isUpdated"):
                if self._sourceObjectList[0].isUpdated():
                    return True
            if _logger.getEffectiveLevel() == logging.DEBUG:
                _logger.debug("Update check took %s seconds", time.time() - t0)
            return False

        lastmodified = os.path.getmtime(self.__sourceNameList[index])
        if key not in self.__lastKeyInfo.keys():
            #nothing has been read???
            self.__lastKeyInfo[key] = lastmodified
            return False
        if lastmodified != self.__lastKeyInfo[key]:
            # do not update the __lastKeyInfo because until
            # refresh is not called data will not be updated
            return True
        else:
            return False

source_types = { SOURCE_TYPE: SpecFileDataSource}

def DataSource(name="", source_type=SOURCE_TYPE):
  try:
     sourceClass = source_types[source_type]
  except KeyError:
     #ERROR invalid source type
     raise TypeError("Invalid Source Type, source type should be one of %s" % source_types.keys())

  return sourceClass(name)


if __name__ == "__main__":
    if len(sys.argv) not in [2,3,4]:
        print("Usage: %s <filename> [<key_to_load>]")
        sys.exit()

    filename= sys.argv[1]
    sf = SpecFileDataSource(filename)
    sf = DataSource(filename)
    if len(sys.argv)==2:
        import time
        for i in range(2):
            t0 = time.time()
            info = sf.getSourceInfo()
            print("getSourceInfo %d elapsed = " % i, time.time() - t0)
            print("Filename        :", sf.sourceName)
            print("Number of scans :", info["Size"])

            print("S# - command - pts - mca - type")
            for (s,c,p,m,t) in zip(info["KeyList"],info["Commands"],info["NumPts"],info["NumMca"],info["ScanType"]):
                    print(s,"-",c,"-",p,"-",m,"-",t)
            print("KeyList = ",info["KeyList"])

    if len(sys.argv)==3:
        t0 = time.time()
        dataObject = sf.getDataObject(sys.argv[2])
        t0 = time.time() - t0
        info= dataObject.info
        data= dataObject.data

        print("Filename   :", info['SourceName'])
        print("Loaded key :", info["Key"])
        print("Header     :")
        for i,v in info.items():
                print("-", i, ":", v)
        print("Data Shape :", data.shape)
        print("read time = ",t0)

    if len(sys.argv)==4:
        t0 = time.time()
        label = sys.argv[3]
        dataObject = sf.getDataObject(sys.argv[2], selection={'x':[label],
                                                        'y':[label],
                                                        'm':[label]})
        t0 = time.time() - t0
        info= dataObject.info
        #print dataObject.x
        print(dataObject.y)
        #print dataObject.x

