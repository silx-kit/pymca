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
from PyMca5.PyMcaIO import SpecFileAbstractClass

_logger = logging.getLogger(__name__)


class BufferedFile(object):
    def __init__(self, filename):
        f = open(filename, 'r')
        self.__buffer = f.read()
        f.close()
        self.__buffer = self.__buffer.replace("\r", "\n")
        self.__buffer = self.__buffer.replace("\n\n", "\n")
        self.__buffer = self.__buffer.split("\n")
        self.__currentLine = 0

    def readline(self):
        if self.__currentLine >= len(self.__buffer):
            return ""
        line = self.__buffer[self.__currentLine]
        self.__currentLine += 1
        return line

    def close(self):
        self.__buffer = [""]
        self.__currentLine = 0
        return

class BAXSCSVFileParser(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise IOError("File %s does not exists"  % filename)

        _fileObject = BufferedFile(filename)

        #Only one measurement per file
        header = []
        ddict = {}
        line = _fileObject.readline()
        if not (line.startswith("Bruker AXS") or \
               (("KTI" in line) and ("Spectrum" in line))):
            raise IOError("This does look as a Bruker AXS Handheld CSV file")
        _logger.info(line)
        if line.endswith("Simple CSV"):
            _logger.info("Simple CSV")
            version = "Simple CSV"
            while not line.startswith("1,") and len(line):
                header.append(line)
                line = _fileObject.readline()
            line = "1,0"
        elif line.endswith("Complete CSV"):
            _logger.info("Complete CSV")
            version = "Complete CSV"
            while not line.startswith("Spectrum:") and len(line):
                header.append(line)
                line = _fileObject.readline()
            line = _fileObject.readline()
        else:
            _logger.info("AXS Version < 5")
            version = None
            while not line.startswith("Channel#") and len(line):
                header.append(line)
                line = _fileObject.readline()
            header.append(line)
            line = _fileObject.readline()
        _logger.info("First data line = <%s>" % line) 
        line = line.replace('"',"")
        splitLine = line.split(",")
        data = []
        while(len(splitLine)):
            if len(splitLine[0]):
                try:
                    data.append([float(x) for x in splitLine if len(x) > 0])
                except ValueError:
                    break
            else:
                break
            line = _fileObject.readline()
            line = line.replace('"',"")
            splitLine = line.split(",")
        _fileObject.close()
        dataColumnNames = [x for x in header[-1].split(",") if len(x) > 0]
        data = numpy.array(data, dtype=numpy.float64)
        #print(header)
        #print(data)
        labels=[]
        #create an abstract scan object
        self._scan = [BAXSCSVScan(data,
                              scantype='MCA',
                              scanheader=header,
                              #labels=labels,
                              #motor_values=self.motorValues,
                              point=False,
                              version=version)]

    def __getitem__(self, item):
        return self._scan[item]

    def scanno(self):
        """
        Gives back the number of scans in the file
        """
        return len(self._scan)

    def list(self):
        return "1:1"

    def select(self, key):
        """
        key is of the from s.o
        scan number, scan order
        """
        n = key.split(".")
        return self.__getitem__(int(n[0])-1)

    def allmotors(self):
        _logger.debug("BAXCSVFileParser allmotors called")
        return []

class BAXSCSVScan(SpecFileAbstractClass.SpecFileAbstractScan):
    def __init__(self, data, scantype='MCA',
                 identification="1.1", scanheader=None, labels=None,
                 motor_values=None, point=False, version=None):
        SpecFileAbstractClass.SpecFileAbstractScan.__init__(self,
                    data, scantype=scantype, identification=identification,
                    scanheader=scanheader, labels=labels, point=point)
        self._data = data
        self._version = version

    def nbmca(self):
        return 1

    def mca(self, number):
        # it gives the last column (some files have three columns)
        # corresponding to channels, counts and (probably) corrected counts
        # this seems to be confirmed by the fact the Live Time is 0.0 in those
        # files
        if number <= 0:
            raise IndexError("Mca numbering starts at 1")
        elif number > self.nbmca():
            raise IndexError("Only %d MCA's" % number)
        return self._data[:, -1]

    def header(self, key):
        if key == "@CALIB":
            gain = 1.0
            offset = 0.0
            for item in self.scanheader:
                if item.startswith("eV per channel,") or \
                   item.startswith("eVPerChannel,"):
                    gain = 0.001 * float(item.split(",")[1])
                elif item.startswith("StartingKeV,"):
                    offset = float(item.split(",")[1])
            return ["#@CALIB %f %f %f" % (offset, gain, 0.0)] 
        elif key == "@CTIME":
            preset = -1
            live = -1
            duration = -1
            for item in self.scanheader:
                if item.startswith("Duration Time,") or\
                   item.startswith("TotalElapsedTimeInSeconds"):
                    duration = float(item.split(",")[1])
                elif item.startswith("Live Time,") or \
                     item.startswith("LiveTimeInSeconds"):
                    live = float(item.split(",")[1])
            if self._version not in ["Simple CSV", "Complete CSV"]:
                if self._data.shape[1] == 3:
                    # counts are already corrected
                    live = duration
            if (preset > 0) and (duration > 0) and (live > 0):
                return ["#@CTIME %f %f %f" % (preset, live, duration)]
            elif (duration > 0) and (live > 0):
                return ["#@CTIME %f %f %f" % (duration, live, duration)]
            elif (live > 0):
                return ["#@CTIME %f %f %f" % (live, live, live)]
            elif (duration > 0):
                return ["#@CTIME %f %f %f" % (duration, duration, duration)]
            else:
                return []
        else:
            return super(BAXSCSVScan, self).header(key)

def isBAXSCSVFile(filename):
    f = open(filename, 'r')
    try:
        line = f.readline()
        f.close()
    except Exception:
        f.close()
        return False
    try:
        if filename.lower().endswith(".csv"):
            if line.startswith("Bruker AXS") or \
               (("KTI" in line) and ("Spectrum" in line)):
                return True
    except Exception:
        pass
    return False

def test(filename):
    if isBAXSCSVFile(filename):
        print("Bruker AXS File")
        sf=BAXSCSVFileParser(filename)
    else:
        print("Not a Bruker AXS File")
    print(sf[0].header('S'))
    print(sf[0].header('D'))
    print(sf[0].header('@CALIB'))
    print(sf[0].header('@CTIME'))
    print(sf[0].alllabels())
    #print(sf[0].allmotorsvalues())
    print(sf[0].nbmca())
    print(sf[0].mca(1))

if __name__ == "__main__":
    test(sys.argv[1])
