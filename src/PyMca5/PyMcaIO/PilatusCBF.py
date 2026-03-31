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
"""
Authors: Jerome Kieffer, ESRF
         email:jerome.kieffer@esrf.fr

Cif Binary Files images are 2D images written by the Pilatus detector and others.
They use a modified (simplified) byte-offset algorithm.
"""

__author__    = "Jerome Kieffer"
__contact__   = "sole@esrf.fr"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__license__   = "MIT"

import sys
import os
import numpy as np
import logging
import io
_fileClass = io.IOBase

_logger = logging.getLogger(__name__)


DATA_TYPES = { "signed 8-bit integer"   : np.int8,
               "signed 16-bit integer"  : np.int16,
               "signed 32-bit integer"  : np.int32
                }

MINIMUM_KEYS = ["X-Binary-Size-Fastest-Dimension",
                'ByteOrder',
                'Data type',
                'X dimension',
                'Y dimension',
                'Number of readouts']

DEFAULT_VALUES = {
                  "Data type": "signed 32-bit integer",
                  "X-Binary-Size-Fastest-Dimension": 2463,
                  "X-Binary-Element-Byte-Order": "LITTLE_ENDIAN"
                  }


class PilatusCBF(object):
    def __init__(self, filename):
        if isinstance(filename, _fileClass):
            fd = filename
        else:
            # make sure we read bytes
            fd = open(filename, 'rb')
        self.cif = CIF()
        self.__data = np.array([])
        self.__info = {}
        #read the file
        if isinstance(filename, _fileClass):
            self.read(filename.name)
        else:
            self.read(filename)

    def getData(self, *var, **kw):
        return self.__data

    def getInfo(self, *var, **kw):
        return self.__info

    def _readheader(self, inStream):
        """
        Read in a header in some CBF format from a string representing the binary stuff
        @param inStream: the binary image (without any CIF decorators)
        @type inStream: python string.
        """
        if sys.platform < '3.0' or\
           isinstance(inStream, str):
            sep = "\r\n"
            iSepPos = inStream.find(sep)
            if iSepPos < 0 or iSepPos > 80:
                sep = "\n" #switch back to unix representation
            lines = inStream.split(sep)
            for oneLine in lines[1:]:
                if len(oneLine) < 10:
                    break
                try:
                    key, val = oneLine.split(':' , 1)
                except ValueError:
                    key, val = oneLine.split('=' , 1)
                key = key.strip()
                self.__header[key] = val.strip(" \"\n\r\t")
        else:
            sep = "\r\n".encode('utf-8')
            iSepPos = inStream.find(sep)
            if iSepPos < 0 or iSepPos > 80:
                sep = "\n".encode('utf-8') #switch back to unix representation
            lines = inStream.split(sep)
            for oneLine in lines[1:]:
                if len(oneLine) < 10:
                    break
                try:
                    key, val = oneLine.split(':'.encode('utf-8') , 1)
                except ValueError:
                    key, val = oneLine.split('='.encode('utf-8') , 1)
                key = key.strip()
                self.__header[key.decode('utf-8')] = val.decode('utf-8').\
                                                         strip(" \"\n\r\t")
        missing = []
        for item in MINIMUM_KEYS:
            if item not in self.__header.keys():
                missing.append(item)
        if len(missing) > 0:
            _logger.debug("CBF file misses the keys %s", " ".join(missing))

    def _readbinary_byte_offset(self, inStream):
        """
        Read in a binary part of an x-CBF_BYTE_OFFSET compressed image

        @param inStream: the binary image (without any CIF decorators)
        @type inStream: python string.
        @return: a linear numpy array without shape and dtype set
        @rtype: numpy array
        """

        def analyse(stream):
            """
            Analyze a stream of char with any length of exception (2,4, or 8 bytes integers)

            @return list of NParrays
            """
            listnpa = []
            if sys.version < '3.0' or\
               isinstance(stream, str):
                key16 = "\x80"
                key32 = "\x00\x80"
                key64 = "\x00\x00\x00\x80"
            else:
                # I avoid the b"..." syntax to try to keep python 2.5 compatibility
                # encoding with utf-8 does not work
                key16 = "\x80".encode('latin-1')
                key32 = "\x00\x80".encode('latin-1')
                key64 = "\x00\x040\x00\x80".encode('latin-1')
#            idx = 0
            shift = 1
#            position = 0
            while True:
#                lns = len(stream)
                idx = stream.find(key16)
                if idx == -1:
                    listnpa.append(np.array(np.frombuffer(stream, dtype="int8")))
                    break
                listnpa.append(np.array(np.frombuffer(stream[:idx], dtype="int8")))
#                position += listnpa[-1].size

                if stream[idx + 1:idx + 3] == key32:
                    if stream[idx + 3:idx + 7] == key64:
                        listnpa.append(np.array(np.frombuffer(stream[idx + 7:idx + 15],
                                                              dtype="int64")))
#                        position += 1
#                        print "loop64 x=%4i y=%4i in idx %4i lns %4i value=%s" % ((position % 2463), (position // 2463), idx, lns, listnpa[-1])
                        shift = 15
                    else: #32 bit int
                        listnpa.append(np.array(np.frombuffer(stream[idx + 3:idx + 7],
                                                              dtype="int32")))
#                        position += 1
#                        print "loop32 x=%4i y=%4i in idx %4i lns %4i value=%s" % ((position % 2463), (position // 2463), idx, lns, listnpa[-1])
                        shift = 7
                else: #int16
                    listnpa.append(np.array(np.frombuffer(stream[idx + 1:idx + 3],
                                                          dtype="int16")))
#                    position += 1
#                    print "loop16 x=%4i y=%4i in idx %4i lns %4i value=%s" % ((position % 2463), (position // 2463), idx, lns, listnpa[-1])
                    shift = 3
                stream = stream[idx + shift:]
            return  listnpa

        if sys.version < '3.0' or\
            isinstance(inStream, str):
            starter = "\x0c\x1a\x04\xd5"
        else:
            # I avoid the b"..." syntax to try to keep python 2.5 compatibility
            # encoding with utf-8 does not work
            starter = "\x0c\x1a\x04\xd5".encode('latin-1')
        startPos = inStream.find(starter) + 4
        data = inStream[ startPos: startPos + int(self.__header["X-Binary-Size"])]
        myData = np.hstack(analyse(data)).cumsum()

        assert len(myData) == self.dim1 * self.dim2
        return myData

    def read(self, fname):
        self.__header = {}
        self.cif.loadCIF(fname, _bKeepComment=True)
        # backport contents of the CIF data to the headers
        for key in self.cif:
            if key != "_array_data.data":
                if isinstance(self.cif[key], str):
                    self.__header[key] = self.cif[key].strip(" \"\n\r\t")
                else:
                    self.__header[key] = self.cif[key].decode('utf-8').\
                                         strip(" \"\n\r\t")
        if not "_array_data.data" in self.cif:
            raise IOError("CBF file %s is corrupt, cannot find data block with '_array_data.data' key" % fname)

        self._readheader(self.cif["_array_data.data"])
        # Compute image size
        try:
            self.dim1 = int(self.__header['X-Binary-Size-Fastest-Dimension'])
            self.dim2 = int(self.__header['X-Binary-Size-Second-Dimension'])
        except Exception:
            raise Exception(IOError, "CBF file %s is corrupt, no dimensions in it" % fname)
        try:
            bytecode = DATA_TYPES[self.__header['X-Binary-Element-Type']]
            self.bpp = len(np.array(0, bytecode).tobytes())
        except KeyError:
            bytecode = np.int32
            self.bpp = 32
            _logger.warning("Defaulting type to int32")

        if self.__header["conversions"] == "x-CBF_BYTE_OFFSET":
            self.__data = self._readbinary_byte_offset(self.cif["_array_data.data"]).astype(bytecode).reshape((self.dim2, self.dim1))
        else:
            raise Exception(IOError, "Compression scheme not yet supported, please contact FABIO development team")
        self.__info = self.__header

class CIF(dict):
    """
    This is the CIF class, it represents the CIF dictionary as a a python dictionary thus inherits from the dict built in class.
    """
    if sys.version < '3.0':
        EOL = ["\r", "\n", "\r\n", "\n\r"]
        BLANK = [" ", "\t"] + EOL
        START_COMMENT = ["\"", "\'"]
        BINARY_MARKER = "--CIF-BINARY-FORMAT-SECTION--"
    else:
        EOL = ["\r", "\n", "\r\n", "\n\r",
               "\r".encode('utf-8'),
               "\n".encode('utf-8'),
               "\r\n".encode('utf-8'),
               "\n\r".encode('utf-8')]
        BLANK = [" ", "\t", " ".encode('utf-8'), "\t".encode('utf-8')] + EOL
        START_COMMENT = ["\"", "\'", "\"".encode('utf-8'), "\'".encode('utf-8')]
        bBINARY_MARKER = "--CIF-BINARY-FORMAT-SECTION--".encode('utf-8')

    def __init__(self, _strFilename=None):
        """
        Constructor of the class.

        @param _strFilename: the name of the file to open
        @type  _strFilename: string
        """
        dict.__init__(self)
        if _strFilename is not None: #load the file)
            self.loadCIF(_strFilename)

    def readCIF(self, _strFilename):
        """
        Just call loadCIF:
        Load the CIF file and sets the CIF dictionary into the object

        @param _strFilename: the name of the file to open
        @type  _strFilename: string
        """
        self.loadCIF(_strFilename)

    def loadCIF(self, _strFilename, _bKeepComment=False):
        """Load the CIF file and returns the CIF dictionary into the object
        @param _strFilename: the name of the file to open
        @type  _strFilename: string
        @param _strFilename: the name of the file to open
        @type  _strFilename: string
        @return the
        """
        if not os.path.isfile(_strFilename):
            _logger.error("I cannot find the file %s", _strFilename)
            raise IOError("I cannot find the file %s" % _strFilename)
        if _bKeepComment:
            self._parseCIF(open(_strFilename, "rb").read())
        else:
            self._parseCIF(CIF._readCIF(_strFilename))

    @staticmethod
    def isAscii(_strIn):
        """
        Check if all characters in a string are ascii,

        @param _strIn: input string
        @type _strIn: python string
        @return: boolean
        @rtype: boolean
        """
        bIsAcii = True
        for i in _strIn:
            if ord(i) > 127:
                bIsAcii = False
                break
        return bIsAcii

    @staticmethod
    def _readCIF(_strFilename):
        """
        -Check if the filename containing the CIF data exists
        -read the cif file
        -removes the comments

        @param _strFilename: the name of the CIF file
        @type _strFilename: string
        @return: a string containing the raw data
        @rtype: string
        """
        if not os.path.isfile(_strFilename):
            _logger.error("I cannot find the file %s", _strFilename)
            raise IOError("I cannot find the file %s" % _strFilename)
        lLinesRead = open(_strFilename, "r").readlines()
        sText = ""
        for sLine in lLinesRead:
            iPos = sLine.find("#")
            if iPos >= 0:
                if CIF.isAscii(sLine):
                    sText += sLine[:iPos] + "\n"

                if iPos > 80:
                    _logger.warning("Warning, this line is too long and could cause problems in PreQuest\n"
                                    "%s", sLine)
            else :
                sText += sLine
                if len(sLine.strip()) > 80 :
                    _logger.warning("Warning, this line is too long and could cause problems in PreQuest\n"
                                    "%s", sLine)
        return sText


    def _parseCIF(self, sText):
        """
        -Parses the text of a CIF file
        -Cut it in fields
        -Find all the loops and process
        -Find all the keys and values

        @param sText: the content of the CIF-file
        @type sText: string
        @return: Nothing, the data are incorporated at the CIF object dictionary
        @rtype: dictionary
        """
        loopidx = []
        looplen = []
        loop = []
        #first of all : separate the cif file in fields
        lFields = CIF._splitCIF(sText.strip())
        #Then : look for loops
        for i in range(len(lFields)):
            if lFields[i].lower() in ["loop_", "loop_".encode('utf-8')]:
                loopidx.append(i)
        if len(loopidx) > 0:
            for i in loopidx:
                loopone, length, keys = CIF._analyseOneLoop(lFields, i)
                loop.append([keys, loopone])
                looplen.append(length)


            for i in range(len(loopidx) - 1, -1, -1):
                f1 = lFields[:loopidx[i]] + lFields[loopidx[i] + looplen[i]:]
                lFields = f1

            self["loop_"] = loop

        for i in range(len(lFields) - 1):
            if len(lFields[i + 1]) == 0 :
                lFields[i + 1] = "?"
            if lFields[i][0:1] in ["_", "_".encode('utf-8')] and \
               lFields[i + 1][0:1] not in ["_", "_".encode('utf-8')]:
                if sys.version < '3.0' or\
                   isinstance(lFields[i], str):
                    self[lFields[i]] = lFields[i + 1]
                else:
                    self[lFields[i].decode('utf-8')] = lFields[i + 1]

    @staticmethod
    def _splitCIF(sText):
        """
        Separate the text in fields as defined in the CIF

        @param sText: the content of the CIF-file
        @type sText: string
        @return: list of all the fields of the CIF
        @rtype: list
        """
        lFields = []
        while True:
            if len(sText) == 0:
                break
            elif sText[0:1] in ["'", "'".encode('utf-8')]:
                toTest = sText[0:1]
                idx = 0
                bFinished = False
                while not  bFinished:
                    idx += 1 + sText[idx + 1:].find(sText[0])
    ##########debuging    in case we arrive at the end of the text
                    if idx >= len(sText) - 1:
                        lFields.append(sText[1:-1].strip())
                        sText = ""
                        bFinished = True
                        break

                    if sText[idx + 1:idx + 2] in CIF.BLANK:
                        lFields.append(sText[1:idx].strip())
                        sText1 = sText[idx + 1:]
                        sText = sText1.strip()
                        bFinished = True

            elif sText[0:1] in ['"', '"'.encode('utf-8')]:
                toTest = sText[0:1]
                idx = 0
                bFinished = False
                while not  bFinished:
                    idx += 1 + sText[idx + 1:].find(toTest)
    ##########debuging    in case we arrive at the end of the text
                    if idx >= len(sText) - 1:
    #                    print sText,idx,len(sText)
                        lFields.append(sText[1:-1].strip())
#                        print lFields[-1]
                        sText = ""
                        bFinished = True
                        break

                    if sText[idx + 1:idx + 2] in CIF.BLANK:
                        lFields.append(sText[1:idx].strip())
                        #print lFields[-1]
                        sText1 = sText[idx + 1:]
                        sText = sText1.strip()
                        bFinished = True
            elif sText[0:1] in [';', ';'.encode('utf-8')]:
                toTest = sText[0:1]
                if isinstance(sText, str):
                    CIF_BINARY_MARKER = CIF.BINARY_MARKER
                else:
                    CIF_BINARY_MARKER = CIF.bBINARY_MARKER
                if sText[1:].strip().find(CIF_BINARY_MARKER) == 0:
                    idx = sText[32:].find(CIF_BINARY_MARKER)
                    if idx == -1:
                        idx = 0
                    else:
                        idx += 32 + len(CIF_BINARY_MARKER)
                else:
                    idx = 0
                bFinished = False
                while not  bFinished:
                    idx += 1 + sText[idx + 1:].find(toTest)
                    if sText[idx - 1:idx] in CIF.EOL:
                        lFields.append(sText[1:idx - 1].strip())
                        sText1 = sText[idx + 1:]
                        sText = sText1.strip()
                        bFinished = True
            else:
                f = sText.split(None, 1)[0]
                lFields.append(f)
                #print lFields[-1]
                sText1 = sText[len(f):].strip()
                sText = sText1
        return lFields

    @staticmethod
    def _analyseOneLoop(lFields, iStart):
        """Processes one loop in the data extraction of the CIF file
        @param lFields: list of all the words contained in the cif file
        @type lFields: list
        @param iStart: the starting index corresponding to the "loop_" key
        @type iStart: integer
        @return: the list of loop dictionaries, the length of the data extracted from the lFields and the list of all the keys of the loop.
        @rtype: tuple
        """
    #    in earch loop we first search the length of the loop
    #    print lFields
#        curloop = {}
        loop = []
        keys = []
        i = iStart + 1
        bFinished = False
        while not bFinished:
            if lFields[i][0] == "_":
                keys.append(lFields[i])#.lower())
                i += 1
            else:
                bFinished = True
        data = []
        while True:
            if i >= len(lFields):
                break
            elif len(lFields[i]) == 0:
                break
            elif lFields[i][0] == "_":
                break
            elif lFields[i] in ["loop_", "stop_", "global_", "data_", "save_"]:
                break
            else:
                data.append(lFields[i])
                i += 1
        #print len(keys), len(data)
        k = 0

        if len(data) < len(keys):
            element = {}
            for j in keys:
                if k < len(data):
                    element[j] = data[k]
                else :
                    element[j] = "?"
                k += 1
            #print element
            loop.append(element)

        else:
            #print data
            #print keys
            for i in range(len(data) / len(keys)):
                element = {}
                for j in keys:
                    element[j] = data[k]
                    k += 1
    #            print element
                loop.append(element)
    #    print loop
        return loop, 1 + len(keys) + len(data), keys






#############################################################################################
########     everything needed to  write a cif file #########################################
#############################################################################################

    def saveCIF(self, _strFilename="test.cif"):
        """Transforms the CIF object in string then write it into the given file
        @param _strFilename: the of the file to be written
        @type param: string
        """
#TODO We should definitly handle exception here
        try:
            fFile = open(_strFilename, "w")
        except IOError:
            _logger.error("Error during the opening of file for write : %s", _strFilename)
            return
        fFile.write(self._cif2str(_strFilename))
        try:
            fFile.close()
        except IOError:
            _logger.error("Error during the closing of file for write : %s", _strFilename)
            raise





    def _cif2str(self, _strFilename):
        """converts a cif dictionary to a string according to the CIF syntax
        @param _strFilename: the name of the filename to be apppended in the header of the CIF file
        @type _strFilename: string
        @return : a sting that corresponds to the content of the CIF-file.
        @rtype: string
        """
        sCifText = ""
        for i in __version__:
            sCifText += "# " + i + "\n"
        if self.exists("_chemical_name_common"):
            t = self["_chemical_name_common"].split()[0]
        else:
            t = os.path.splitext(os.path.split(_strFilename.strip())[1])[0]
        sCifText += "data_%s\n" % t
        #first of all get all the keys :
        lKeys = self.keys()
        lKeys.sort()
        for sKey in lKeys:
            if sKey == "loop_":
                continue
            sValue = str(self[sKey])
            if sValue.find("\n") > -1: #should add value  between ;;
                sLine = "%s \n;\n %s \n;\n" % (sKey, sValue)
            elif len(sValue.split()) > 1: #should add value between ''
                sLine = "%s        '%s' \n" % (sKey, sValue)
                if len(sLine) > 80:
                    sLine = "%s\n '%s' \n" % (sKey, sValue)
            else:
                sLine = "%s        %s \n" % (sKey, sValue)
                if len(sLine) > 80:
                    sLine = "%s\n %s \n" % (sKey, sValue)
            sCifText += sLine
        if "loop_" in self:
            for loop in self["loop_"]:
                sCifText += "loop_ \n"
                lKeys = loop[0]
                llData = loop[1]
                for sKey in lKeys:
                    sCifText += " %s \n" % sKey
                for lData in llData:
                    sLine = ""
                    for key in lKeys:
                        sRawValue = lData[key]
                        if sRawValue.find("\n") > -1: #should add value  between ;;
                            sLine += "\n; %s \n;\n" % (sRawValue)
                            sCifText += sLine
                            sLine = ""
                        else:
                            if len(sRawValue.split()) > 1: #should add value between ''
                                value = "'%s'" % (sRawValue)
                            else:
                                value = sRawValue
                            if len(sLine) + len(value) > 78:
                                sCifText += sLine + " \n"
                                sLine = " " + value
                            else:
                                sLine += " " + value
                    sCifText += sLine + " \n"
                sCifText += "\n"
        #print sCifText
        return sCifText

    def exists(self, sKey):
        """
        Check if the key exists in the CIF and is non empty.
        @param sKey: CIF key
        @type sKey: string
        @param cif: CIF dictionary
        @return: True if the key exists in the CIF dictionary and is non empty
        @rtype: boolean
        """
        bExists = False
        if sKey in self:
            if len(self[sKey]) >= 1:
                if self[sKey][0] not in ["?", "."]:
                    bExists = True
        return bExists

    def existsInLoop(self, sKey):
        """
        Check if the key exists in the CIF dictionary.
        @param sKey: CIF key
        @type sKey: string
        @param cif: CIF dictionary
        @return: True if the key exists in the CIF dictionary and is non empty
        @rtype: boolean
        """
        if not self.exists("loop_"):
            return False
        bExists = False
        if not bExists:
            for i in self["loop_"]:
                for j in i[0]:
                    if j == sKey:
                        bExists = True
        return bExists

    def loadCHIPLOT(self, _strFilename):
        """Load the powder diffraction CHIPLOT file and returns the pd_CIF dictionary in the object
        @param _strFilename: the name of the file to open
        @type  _strFilename: string
        @return: the CIF object corresponding to the powder diffraction
        @rtype: dictionary
        """
        if not os.path.isfile(_strFilename):
            _logger.error("I cannot find the file %s", _strFilename)
            raise IOError("I cannot find the file %s" % _strFilename)
        lInFile = open(_strFilename, "r").readlines()
        self["_audit_creation_method"] = 'From 2-D detector using FIT2D and CIFfile'
        self["_pd_meas_scan_method"] = "fixed"
        self["_pd_spec_description"] = lInFile[0].strip()
        try:
            iLenData = int(lInFile[3])
        except ValueError:
            iLenData = None
        lOneLoop = []
        try:
            f2ThetaMin = float(lInFile[4].split()[0])
            last = ""
            for sLine in lInFile[-20:]:
                if sLine.strip() != "":
                    last = sLine.strip()
            f2ThetaMax = float(last.split()[0])
            limitsOK = True

        except (ValueError, IndexError):
            limitsOK = False
            f2ThetaMin = 180.0
            f2ThetaMax = 0
#        print "limitsOK:", limitsOK
        for sLine in lInFile[4:]:
            sCleaned = sLine.split("#")[0].strip()
            data = sCleaned.split()
            if len(data) == 2 :
                if not limitsOK:
                    f2Theta = float(data[0])
                    if f2Theta < f2ThetaMin :
                        f2ThetaMin = f2Theta
                    if f2Theta > f2ThetaMax :
                        f2ThetaMax = f2Theta
                lOneLoop.append({ "_pd_meas_intensity_total": data[1] })
        if not iLenData:
            iLenData = len(lOneLoop)
        assert (iLenData == len(lOneLoop))
        self[ "_pd_meas_2theta_range_inc" ] = "%.4f" % ((f2ThetaMax - f2ThetaMin) / (iLenData - 1))
        if self[ "_pd_meas_2theta_range_inc" ] < 0:
            self[ "_pd_meas_2theta_range_inc" ] = abs (self[ "_pd_meas_2theta_range_inc" ])
            tmp = f2ThetaMax
            f2ThetaMax = f2ThetaMin
            f2ThetaMin = tmp
        self[ "_pd_meas_2theta_range_max" ] = "%.4f" % f2ThetaMax
        self[ "_pd_meas_2theta_range_min" ] = "%.4f" % f2ThetaMin
        self[ "_pd_meas_number_of_points" ] = str(iLenData)
        self["loop_"] = [ [ ["_pd_meas_intensity_total" ], lOneLoop ] ]


    @staticmethod
    def LoopHasKey(loop, key):
        "Returns True if the key (string) existe in the array called loop"""
        try:
            loop.index(key)
            return True
        except ValueError:
            return False

if __name__ == "__main__":
    from PyMca5 import EdfFile
    #fd = open('Cu_ZnO_20289.mccd', 'rb')
    filename = sys.argv[1]
    cbf = PilatusCBF(filename)
    print(cbf.getInfo())
    edfFile = filename+".edf"
    if os.path.exists(edfFile):
        os.remove(edfFile)
    edf = EdfFile.EdfFile(edfFile)
    edf.WriteImage(cbf.getInfo(), cbf.getData())
    edf = None
