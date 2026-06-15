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
import os
import logging
import sys
import numpy
import mmap
import re
import time
from PyMca5.PyMcaIO import JcampReader
from PyMca5.PyMcaIO import SpecFileAbstractClass
from io import StringIO
_logger = logging.getLogger(__name__)


class JcampFileParser(SpecFileAbstractClass.SpecFileAbstractClass):
    def __init__(self, filename, single=False):
        # get the number of entries in the file
        self.__lastEntryData = -1
        t0 = time.time()
        if sys.maxsize > 2**32:
            self._useMMap = True
        else:
            self._useMMap = False
        _logger.debug("USING MMPA = %s", self._useMMap)
        if self._useMMap:
            # 64-bit supported
            f = open(filename, "rb")
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            a = [x.start() for x in re.finditer("##TITLE".encode("utf-8"), mm)]
            b = [x.end() for x in re.finditer("##END.*\n".encode("utf-8"), mm)]
            mm = None
            f.close()
            # we can have twice the TITLE before the first data block
            # we get rid of the second to have also the file header
            if len(a) > 1:
                if a[1] < b[0]:
                    del a[1]
            self._scanLimits = [(start, end) for start, end in zip(a, b)]
        else:
            # 32-bit
            self._scanLimits = []
            f = open(filename, "rb")
            entryStarted = False
            current = f.tell()
            line = f.readline()
            nLines = 0
            while len(line):
                if entryStarted:
                    if line.startswith("##END=".encode("utf-8")):
                        lineEnd = nLines
                        self._scanLimits.append((start, f.tell(), lineStart, lineEnd))
                        entryStarted = False
                        if single:
                            break
                elif line.startswith("##TITLE".encode("utf-8")):
                    start = current
                    lineStart = nLines
                    entryStarted = True
                nLines += 1
                current = f.tell()
                line = f.readline()
            f.close()
        _logger.debug("Elapsed CURRENT = %s",
                      time.time() - t0)
        self._filename = os.path.abspath(filename)
        _logger.debug("PARSING FIRST ")
        t0 = time.time()
        self._parseEntryData(0)
        elapsed = time.time() - t0
        _logger.debug("ELAPSED PER SCAN = %s", elapsed)
        _logger.debug("N SCANS = %s", self.scanno())
        _logger.debug("EXPECTED = %s", elapsed * self.scanno())

    def _parseEntryData(self, idx):
        if idx == self.__lastEntryData:
            # nothing to be done
            return
        if (idx < 0) or (idx >= len(self._scanLimits)):
            raise IndexError("Only %d entries in file. Requested %d" % (len(self._scanLimits), idx))
        start, end = self._scanLimits[idx][0:2]
        if self._useMMap:
            #get the relevant file section
            f = open(self._filename, "rb")
            scanBuffer = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)[start:end]
            f.close()
            # the Reader expects to work with strings and not with bytes
            scanBuffer = scanBuffer.decode("utf-8")
            fileBlock = True
        else:
            #get the relevant file section
            f = open(self._filename, "r")
            start, end = self._scanLimits[idx][0:2]
            f.seek(start)
            scanBuffer = StringIO(f.read(1 + end - start))
            f.close()
            fileBlock = False
        instance = JcampReader.JcampReader(scanBuffer, block=fileBlock)
        info = instance.info
        jcampDict = info
        x, y = instance.data
        title = jcampDict.get('TITLE', "Unknown scan")
        xLabel = jcampDict.get('XUNITS', 'channel')
        yLabel = jcampDict.get('YUNITS', 'counts')
        try:
            fileheader = instance._header
        except Exception:
            _logger.warning("JCampFileParser cannot access '_header' attribute")
            fileheader=None
        data = numpy.zeros((x.size, 2), numpy.float32)
        data[:, 0] = x
        data[:, 1] = y
        self.scandata = []
        scanheader = ["#S %d %s" % (2*idx + 1, title),
                      "#N 2",
                      "#L %s  %s" % (xLabel, yLabel)]
        scanData = JCAMPFileScan(data,
                                 scantype="SCAN",
                                 scanheader=scanheader,
                                 labels=[xLabel, yLabel],
                                 fileheader=fileheader)
        self.scandata.append(scanData)
        scanheader = ["#S %d %s" % (2*idx + 2, title)]
        if jcampDict['XYDATA'].upper() ==  '(X++(Y..Y))':
            # we can deal with the X axis via its calibration
            scanheader.append("#@CHANN %d  %d  %d  1" % (len(x), 0, len(x) - 1))
            scanheader.append("#@CALIB %f %f 0" % (x[0], x[1] - x[0]))
            scantype = "MCA"
        scanData = JCAMPFileScan(data, scantype="MCA",
                                                      scanheader=scanheader,
                                                      #labels=[xLabel, yLabel],
                                                      fileheader=fileheader)
        self.scandata.append(scanData)
        self.__lastEntryData = idx

    def __getitem__(self, item):
        if item < 0:
            item = self.scanno() - item
        idx = item // 2
        self._parseEntryData(idx)
        return self.scandata[item % 2]

    def list(self):
        return '1:%d' % self.scanno()

    def scanno(self):
        return len(self.scandata) * len(self._scanLimits)

class JCAMPFileScan(SpecFileAbstractClass.SpecFileAbstractScan):
    def __init__(self, data, scantype="SCAN",
                 scanheader=None, labels=None, fileheader=None):
        SpecFileAbstractClass.SpecFileAbstractScan.__init__(self, data,
                            scantype=scantype, scanheader=scanheader,
                            labels=labels)
        self._data = data
        self._fileHeader = fileheader

    def fileheader(self, key=''):
        return self._fileHeader

    def nbmca(self):
        if self.scantype == 'SCAN':
            return 0
        else:
            return 1

    def mca(self, number):
        if number not in [1]:
            raise ValueError("Specfile mca numberig starts at 1")
        return self._data[:, number]

def isJcampFile(filename):
    return JcampReader.isJcampFile(filename)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python JCAMPFileParser.py filename")
        sys.exit(0)
    print(" isJCAMPFile = ", isJcampFile(sys.argv[1]))
    sf = JcampFileParser(sys.argv[1])
    print("nscans = ", sf.scanno())
    print("list = ", sf.list())
    print("select = ", sf.select(sf.list()[0]))
