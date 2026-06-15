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
import os
import sys
import numpy
import re
import logging
from PyMca5.PyMcaIO import specfile
from PyMca5.PyMcaIO import Fit2DChiFileParser
from PyMca5.PyMcaIO import APSMEDFileParser
from PyMca5.PyMcaIO import SRSFileParser
from PyMca5.PyMcaIO import BAXSCSVFileParser
from PyMca5.PyMcaIO import OlympusCSVFileParser
from PyMca5.PyMcaIO import ThermoEMSFileParser
from PyMca5.PyMcaIO import JcampFileParser
from PyMca5.PyMcaIO import BlissSpecFile

_logger = logging.getLogger(__name__)

try:
    from PyMca5.PyMcaIO import ArtaxFileParser
    SPX = True
except Exception:
    _logger.info("specfilewrapper cannot import ArtaxFileParser")
    SPX = False


def safe_str(bytesObject):
    try:
        return str(bytesObject, 'utf-8')
    except UnicodeDecodeError:
        try:
            return str(bytesObject, 'latin-1')
        except Exception:
            try:
                return str(bytesObject, 'utf-16')
            except Exception:
                return str(bytesObject)

def Specfile(filename):
    if BlissSpecFile.isBlissSpecFile(filename):
        return BlissSpecFile.BlissSpecFile(filename)
    f = open(filename, 'r', errors="ignore")
    line0  = f.readline()
    if filename.upper().endswith('DTA'):
        #TwinMic single column file
        line = line0 * 1
        line = line.replace('\r','')
        line = line.replace('\n','')
        line = line.replace('\t',' ')
        s = line.split(' ')
        if len(s) == 2:
            if len(s[-1]) == 0:
                try:
                    float(s[0])
                    f.close()
                    output = specfilewrapper(filename, dta=True)
                    return output
                except Exception:
                    #try to read in other way
                    pass

    # this piece of code checks if we deal with a SPEC file
    # Prior to any data, all lines have to be either empty or starting
    # by the hash character.
    line = line0
    while(len(line)):
        if len(line) > 1:
            if line[0:2] == '#S':
                if ('#SIGNALTYPE' in line) or \
                   ('#SPECTRUM' in line):
                    line = ""
                break
            elif line[0] not in ['#', ' ', '\r']:
                line = ""
                break
        try:
            line = f.readline()
        except Exception:
            line = ""
            break
    f.close()
    # end of specfile identification
    amptek = False
    qxas   = False
    if len(line):
        #it is a Specfile
        _logger.debug("This looks as a specfile")
        output=specfile.Specfile(filename)
    elif SPX and ArtaxFileParser.isArtaxFile(filename):
        _logger.debug("This looks as an Artax file")
        output = ArtaxFileParser.ArtaxFileParser(filename)
    else:
        _logger.debug("this does not look as a specfile")
        if len(line0) > 7:
            if line0.startswith('$SPEC_ID') or\
               line0.startswith('$DATE_MEA') or\
               line0.startswith('$MEAS_TIM') or\
               line0.startswith('$Core_ID') or\
               line0.startswith('$Section_ID'):
                qxas = True
        if (not qxas) and line0.startswith('<<'):
                amptek = True
        if (not qxas) and (not amptek) and Fit2DChiFileParser.isFit2DChiFile(filename):
            return Fit2DChiFileParser.Fit2DChiFileParser(filename)
        if (not qxas) and (not amptek) and APSMEDFileParser.isAPSMEDFile(filename):
            return APSMEDFileParser.APSMEDFileParser(filename)
        if (not qxas) and (not amptek) and SRSFileParser.isSRSFile(filename):
            _logger.debug("SRSFileParser")
            return SRSFileParser.SRSFileParser(filename)
        if (not qxas) and (not amptek) and BAXSCSVFileParser.isBAXSCSVFile(filename):
            _logger.debug("BAXSCSVFileParser")
            return BAXSCSVFileParser.BAXSCSVFileParser(filename)
        if (not qxas) and (not amptek) and \
           OlympusCSVFileParser.isOlympusCSVFile(filename):
            _logger.debug("OlympusCSVFileParser")
            return OlympusCSVFileParser.OlympusCSVFileParser(filename)
        if (not qxas) and (not amptek) and \
           ThermoEMSFileParser.isThermoEMSFile(filename):
            _logger.debug("ThermoEMSFileParser")
            return ThermoEMSFileParser.ThermoEMSFileParser(filename)
        if (not qxas) and (not amptek) and \
           JcampFileParser.isJcampFile(filename):
            _logger.debug("JcampFileParser")
            return JcampFileParser.JcampFileParser(filename)
        output = specfilewrapper(filename, amptek=amptek, qxas=qxas)
    return output

class specfilewrapper(object):
    def __init__(self, filename, amptek=None, qxas=None, dta=None):
        if amptek is None:
            amptek = False
        if qxas is None:
            qxas = False
        if dta is None:
            dta = False
        self.amptek = amptek
        self.qxas = qxas
        self.dta = dta
        self.ketek = None
        self.header = []
        if self.dta:
            #TwinMic .dta files with only one spectrum
            self.data = numpy.fromfile(filename,
                                       dtype=numpy.float32,
                                       sep='\t\r\n')
            self.header = ['#S1 %s' % os.path.basename(filename)]
            self.data = self.data.reshape(-1, 1)
            self.scandata=[myscandata(self.data,'MCA','1.1',
                                      scanheader=self.header)]
            return
        if self.qxas:
            f = open(filename)
        else:
            f = BufferedFile(filename)
        line = f.readline()
        outdata = []
        ncol0 = -1
        nlines= 0
        if amptek:
            while bytes("<<DATA>>", 'utf-8') not in line:
                self.header.append(safe_str(line.replace(bytes("\n", 'utf-8'),
                                                bytes("", 'utf-8'))))
                line = f.readline()
        elif qxas:
            line.replace("\n","")
            line.replace("\x00","")
            self._qxasHeader = {}
            self._qxasHeader['S'] = '#S1 '+ " Unlabelled Spectrum"
            while 1:
                self.header.append(line)
                if line.startswith('$SPEC_ID:'):
                    line = f.readline().replace("\n","")
                    line.replace("\x00","")
                    self.header.append(line)
                    self._qxasHeader['S'] = '#S1 '+ line
                if line.startswith('$DATE_MEA'):
                    line = f.readline().replace("\n","")
                    self.header.append(line)
                    self._qxasHeader['D'] = line
                if line.startswith('$MEAS_TIM'):
                    line = f.readline().replace("\n","")
                    self.header.append(line)
                    tmpList = [float(i) for i in line.split()]
                    if len(tmpList) == 1:
                        preset = tmpList[0]
                        elapsed = preset
                    else:
                        preset, elapsed = tmpList[0:2]
                    self._qxasHeader['@CTIME'] = ['#@CTIME %f %f %f' % (preset, preset, elapsed)]
                if line.startswith('$MCA_CAL'):
                    try:
                       line = f.readline().replace("\n","")
                       self.header.append(line)
                       if line.startswith('$'):
                           continue
                       line = f.readline().replace("\n","")
                       self.header.append(line)
                       if line.startswith('$'):
                           continue
                       coefficients = [float(i) for i in line.split()]
                       if len(coefficients) == 2:
                           coefficients.append(0.0)
                       self._qxasHeader['@CALIB']=  ['#@CALIB %f  %f  %f' %\
                                            (coefficients[0], coefficients[1], coefficients[2])]
                    except Exception:
                        pass
                if line.startswith('$DATA:'):
                    line = f.readline().replace("\n","")
                    self.header.append(line)
                    start, stop = [int(i) for i in line.split()]
                    self._qxasHeader['@CHANN'] = ['#@CHANN  %d  %d  %d  1' % (stop-start+1, start, stop)]
                    break
                line = f.readline().replace("\n","")
        if qxas:
            outdata = []
            line = f.readline().replace("\n","")
            while len(line):
                if line[0] == "$":
                    break
                outdata += [float(x) for x in line.split()]
                line = f.readline().replace("\n","")
            nlines = len(outdata)
            f.close()
            self.data = numpy.resize(numpy.array(outdata).astype(numpy.float64),(nlines,1))
        else:
            tmpBytes = bytes(" ",'utf-8')
            line = line.replace(bytes(",",'utf-8'), tmpBytes)
            line = line.replace(bytes(";",'utf-8'), tmpBytes)
            line = line.replace(bytes("\t",'utf-8'), tmpBytes)
            tmpBytes = bytes("\n",'utf-8')
            line = line.replace(bytes("\r","utf-8"), tmpBytes)
            line = line.replace(bytes('"',"utf-8"), bytes("", "utf-8"))
            line = line.replace(bytes('\n\n',"utf-8"), tmpBytes)
            while(len(line)):
                values = line.split()
                if len(values):
                    try:
                        reals = [float(x) for x in values]
                        ncols = len(reals)
                        if ncol0 < 0:ncol0 = ncols
                        if ncols == ncol0:
                            outdata.append(reals)
                            nlines += 1
                    except Exception:
                        if len(line) > 1:
                            self.header.append(safe_str(line.replace(\
                                                bytes("\n",'utf-8'),\
                                                bytes("", 'utf-8'))))
                else:
                    if len(line) > 1:
                        self.header.append(safe_str(line.replace(bytes("\n",'utf-8'),
                                                        bytes("", 'utf-8'))))
                line = f.readline()
                tmpBytes = bytes(" ",'utf-8')
                line = line.replace(bytes(",",'utf-8'), tmpBytes)
                line = line.replace(bytes(";",'utf-8'), tmpBytes)
                line = line.replace(bytes("\t",'utf-8'), tmpBytes)
                tmpBytes = bytes("\n",'utf-8')
                line = line.replace(bytes("\r","utf-8"), tmpBytes)
                line = line.replace(bytes('"',"utf-8"), bytes("", "utf-8"))
                line = line.replace(bytes('\n\n',"utf-8"), tmpBytes)
            f.close()
            self.data = numpy.resize(numpy.array(outdata).astype(numpy.float64),(nlines,ncol0))
        if self.amptek:
            self.scandata=[myscandata(self.data,'MCA','1.1',
                                      scanheader=self.header)]
        elif self.qxas:
            self.scandata=[myscandata(self.data,'MCA','1.1',
                                      scanheader=self.header,
                                      qxas=self._qxasHeader)]
        else:
            labels = None
            if len(self.header) == 1:
                if len(self.header[0]) > 0:
                    labels = self.header[0].split("  ")
                    if len(labels) != ncol0:
                        labels = None
            # check if it is a KETEK AXAS-D file
            ketek_keys = ["File Version = ",
                          "Livetime = ", "Live Time: = ",
                          "Realtime = ", "Real Time: = ",
                          "Input Count Rate = ", "ICR: = ",
                          "Output Count Rate = ", "OCR: = ",
                          "= KETEK"]
            ketek_counter = 0
            icr = None
            ocr = None
            live_time = None
            live_time = None
            real_time = None
            for line in self.header:
                for key in ketek_keys:
                    if key in line:
                        keylower = line.lower()
                        if keylower.startswith("livetime =") or keylower.startswith("live time: = "):
                            tokens = line.split(" = ")[-1].split()
                            if tokens[-1] == "s":
                                if "." in tokens[0]:
                                    live_time = float(tokens[0])
                                else:
                                    live_time = float(tokens[0] + "." + tokens[1])
                        elif keylower.startswith("realtime =") or keylower.startswith("real time: = "):
                            tokens = line.split(" = ")[-1].split()
                            if tokens[-1] == "s":
                                if "." in tokens[0]:
                                    real_time = float(tokens[0]) 
                                else:
                                    real_time = float(tokens[0] + "." + tokens[1])
                        elif keylower.startswith("input count rate = ") or keylower.startswith("icr: = "):
                            tokens = line.split(" = ")[-1].split()
                            if "." in tokens[0]:
                                icr = float(tokens[0]) 
                            else:
                                icr = float(tokens[0] + "." + tokens[1])
                        elif keylower.startswith("output count rate = ") or keylower.startswith("ocr: = "):
                            tokens = line.split(" = ")[-1].split()
                            if "." in tokens[0]:
                                ocr = float(tokens[0]) 
                            else:
                                ocr = float(tokens[0] + "." + tokens[1])                            
                        ketek_counter += 1
                        break
            if ketek_counter >= 4:
                self.ketek = 1
                if real_time and live_time:
                    self._ketekHeader = {}
                    self._ketekHeader['S'] = '#S1 '+ " Unlabelled Spectrum"
                    if ocr and icr:
                        live_time = real_time * ocr / icr
                        _logger.info("Taking live time =  real_time * ocr / icr")
                    else:
                        _logger.warning("Taking live time from file")
                    self._ketekHeader['@CTIME'] = ['#@CTIME %f %f %f' % (real_time,
                                                                         live_time,
                                                                         real_time)]
                else:
                    self._ketekHeader = None
                self.scandata=[myscandata(self.data,'MCA','1.1',
                                      fileheader=self.header,
                                      qxas=self._ketekHeader)]
            else:
                self.scandata=[myscandata(self.data,'SCAN','1.1',
                                      labels=labels,
                                      fileheader=self.header),
                               myscandata(self.data,'MCA','2.1',
                                      fileheader=self.header)]

    def list(self):
        if self.amptek or self.qxas or self.dta or self.ketek:
            return "1:1"
        else:
            return "1:2"

    def __getitem__(self,item):
        return self.scandata[item]

    def __len__(self):
        return self.scanno()

    def select(self,i):
        n = i.split(".")
        return self.__getitem__(int(n[0]) - 1)

    def scanno(self):
        if self.amptek or self.qxas or self.dta or self.ketek:
            return 1
        else:
            return 2

class myscandata(object):
    def __init__(self, data, scantype=None, identification=None,
                 scanheader=None, qxas=None, labels=None, fileheader=None):
        if identification is None:
            identification='1.1'
        if scantype is None:
            scantype='SCAN'
        self.qxas = qxas
        self.scanheader = scanheader
        if fileheader is None:
            fileheader = []
        self._fileheader = fileheader
        #print shape(data)
        (rows, cols) = numpy.shape(data)
        if scantype == 'SCAN':
            self.__data = numpy.zeros((rows, cols +1 ), numpy.float64)
            self.__data[:,0] = numpy.arange(rows) * 1.0
            self.__data[:,1:] = data * 1
            self.__cols = cols + 1
            self.labels = ['Point']
            if labels is None:
                for i in range(cols):
                    self.labels.append('Column %d'  % i)
            else:
                for label in labels:
                    self.labels.append('%s' % label)
        else:
            self.__data = data
            self.__cols = cols
            self.labels = []
        self.scantype = scantype
        self.rows = rows
        if scanheader is None:
            labels = '#L '
            for label in self.labels:
                labels += '  '+label
            if self.scantype == 'SCAN':
                self.scanheader = ['#S1 Unknown command',
                              '#N %d' % len(self.labels),
                              labels]
            else:
                self.scanheader = ['#S1 Unknown command']

        n = identification.split(".")
        self.__number = int(n[0])
        self.__order  = int(n[1])

    def alllabels(self):
        if self.scantype == 'SCAN':
            return self.labels
        else:
            return []

    def allmotorpos(self):
        return []

    def cols(self):
        return self.__cols

    def command(self):
        _logger.debug("command called")
        if self.qxas is not None:
            if 'S' in self.qxas:
                text = self.qxas['S']
        elif self.scanheader is not None:
            if len(self.scanheader):
                text = self.scanheader[0]
        return text

    def data(self):
        return numpy.transpose(self.__data)

    def datacol(self, col):
        # it is awful that starts at one ...
        if col <= 0:
            raise ValueError("Specfile column numberig starts at 1")
        return self.__data[:, col - 1]

    def dataline(self, line):
        # it is awful that starts at one ...
        if line <= 0:
            raise ValueError("Specfile line numberig starts at 1")
        return self.__data[line - 1,:]


    def date(self):
        text = 'sometime'
        if self.qxas is not None:
            if 'D' in self.qxas:
                return self.qxas['D']
        elif self.scanheader is not None:
            for line in self.scanheader:
                if 'START_TIME' in line:
                    text = "%s" % line
                    break
        return text

    def fileheader(self, key=''):
        # key is there for compatibility
        _logger.debug("file header called")
        return self._fileheader

    def header(self, key):
        if self.qxas is not None:
            if key in self.qxas:
                return self.qxas[key]
            elif key == "" or key == " ":
                return self.scanheader
        if key == 'S':
            return self.scanheader[0]
        elif key == 'N':
            return self.scanheader[-2]
        elif key == 'L':
            return self.scanheader[-1]
        elif key == '@CALIB':
            output = []
            if self.scanheader is None:
                return output
            if self.scanheader[0][0:2] == '<<':
                #amptek
                try:
                    amptekCalibrationLines = []
                    amptekInCalibrationLines = False
                    for line in self.scanheader:
                        if '<<CALIBRATION>>' in line:
                            amptekInCalibrationLines = True
                            continue
                        if line.startswith('<<'):
                            amptekInCalibrationLines = False
                            continue
                        if amptekInCalibrationLines and\
                           ('LABEL' not in line):
                            amptekCalibrationLines.append(line)
                    n = len(amptekCalibrationLines)
                    if n == 0 :
                        return output
                    if n == 1:
                        #one point calibration
                        x0,y0 = 0.0, 0.0
                        values = amptekCalibrationLines[0].split()
                        x1,y1 = map(float,values)
                        gain = (y1-y0)/(x1-x0)
                        zero = y0 - gain * x0
                    elif n == 2:
                        #two point calibration
                        values = amptekCalibrationLines[0].split()
                        x0,y0 = map(float,values)
                        values = amptekCalibrationLines[1].split()
                        x1,y1 = map(float,values)
                        gain = (y1-y0)/(x1-x0)
                        zero = y0 - gain * x0
                    else:
                        x = numpy.zeros((n,), numpy.float64)
                        y = numpy.zeros((n,), numpy.float64)
                        for i in range(n):
                            values = amptekCalibrationLines[i].split()
                            x[i], y[i] = map(float,values)
                        Sxy = numpy.dot(x, y.T)
                        Sxx = numpy.dot(x, x.T)
                        Sx  = x.sum()
                        Sy  = y.sum()
                        d = n * Sxx - Sx * Sx
                        zero = (Sxx * Sy - Sx * Sxy)/d
                        gain = (n * Sxy - Sx * Sy)/d
                    output = ['#@CALIB  %g  %g  0' % (zero, gain)]
                except Exception:
                    pass
            return output
        elif key == "" or key == " ":
            return self.scanheader
        else:
            return []

    def order(self):
        return self.__order

    def number(self):
        return self.__number

    def lines(self):
        if self.scantype == 'SCAN':
            return self.rows
        else:
            return 0

    def nbmca(self):
        if self.scantype == 'SCAN':
            return 0
        else:
            return self.__cols

    def mca(self,number):
        if number <= 0:
            raise ValueError("Specfile mca numberig starts at 1")
        return self.__data[:,number-1]

class BufferedFile(object):
    def __init__(self, filename):
        f = open(filename, 'rb')
        self.__buffer = f.read()
        f.close()
        tmp = bytes("\n", 'utf-8')
        self.__buffer=self.__buffer.replace(bytes("\r", 'utf-8'), tmp)
        self.__buffer=self.__buffer.replace(bytes("\n\n", 'utf-8'), tmp)
        self.__buffer = self.__buffer.split(tmp)
        self.__currentLine = 0

    def readline(self):
        if self.__currentLine >= len(self.__buffer):
            return bytes("", 'utf-8')
        line = self.__buffer[self.__currentLine] + bytes("\n", 'utf-8')
        self.__currentLine += 1
        return line

    def close(self):
        self.__currentLine = 0
        return

if __name__ == "__main__":
    filename = sys.argv[1]
    print(filename)
    sf=Specfile(filename)
    sf.list()
    print(sf[0].alllabels())
    print(dir(sf[0]))
