#!/usr/bin/env python
#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2014 European Synchrotron Radiation Facility
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
"""
This class just puts in evidence the Specfile methods called from
PyMca.
It can be used to wrap other formats as specile
"""
import os
import numpy
import logging


_logger = logging.getLogger(__name__)


class SpecFileAbstractClass(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            return None
        self.motorNames = []

    def list(self):
        """
        If there is only one scan returns 1:1
        with two scans returns 1:2
        """
        _logger.debug("list method called")
        return "1:1"

    def __getitem__(self, item):
        """
        Returns the scan data
        """
        _logger.debug("__getitem__ called")
        return self.scandata[item]

    def select(self, key):
        """
        key is of the from s.o
        scan number, scan order
        """
        n = key.split(".")
        return self.__getitem__(int(n[0])-1)

    def scanno(self):
        """
        Gives back the number of scans in the file
        """
        return 0

    def allmotors(self):
        return self.motorNames

class SpecFileAbstractScan(object):
    def __init__(self, data, scantype=None, identification=None, scanheader=None, labels=None,point=True):
        if identification is None:identification='1.1'
        if scantype is None:scantype='SCAN'
        self.scanheader = scanheader
        if hasattr(data, "shape"):
            if len(data.shape) == 1:
                data = data.reshape(-1, 1)
        self.__point = point
        if scantype == 'SCAN':
            (rows, cols) = data.shape
            if self.__point:
                self.__data = numpy.zeros((rows, cols +1 ), numpy.float32)
                self.__data[:,0] = numpy.arange(rows) * 1.0
                self.__data[:,1:] = data * 1
                self.__cols = cols + 1
                self.labels = ['Point']
            else:
                self.__data = numpy.zeros((rows, cols), numpy.float32)
                self.__data[:,0:] = data * 1
                self.__cols = cols
                self.labels = []
        else:
            self.__data = data
            if isinstance(self.__data, numpy.ndarray):
                (rows, cols) = data.shape
            else:
                #we have a list of MCAs
                rows = 0
                cols = len(data)
            self.__cols = cols
            self.labels = []
        self.scantype = scantype
        self.rows = rows
        if labels is None:
            for i in range(cols):
                self.labels.append('Column %d'  % i)
        else:
            for label in labels:
                self.labels.append('%s' % label)
        n = identification.split(".")
        self.__number = int(n[0])
        self.__order  = int(n[1])

    def alllabels(self):
        """
        These are the labels associated to the counters
        """
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
        text = ""
        if self.scanheader is not None:
            if len(self.scanheader):
                text = self.scanheader[0]
        return text

    def data(self):
        return numpy.transpose(self.__data)

    def datacol(self,col):
        return self.__data[:,col]

    def dataline(self,line):
        return self.__data[line,:]


    def date(self):
        text = 'sometime'
        return text

    def fileheader(self):
        _logger.debug("file header called")
        labels = '#L '
        for label in self.labels:
            labels += '  '+label
        if self.scanheader is None:
            if self.scantype == 'SCAN':
                return ['#S 1  Unknown command','#N %d' % self.cols(),labels]
            else:
                return ['#S 1  Unknown command']
        else:
            _logger.debug("returning %s", self.scanheader)
            return self.scanheader

    def header(self,key):
        if   key == 'S': return self.fileheader()[0]
        elif key == 'N':return self.fileheader()[-2]
        elif key == 'L':return self.fileheader()[-1]
        elif key == '@CALIB':
            output = []
            if self.scanheader is None: return output
            for line in self.scanheader:
                if line.startswith(key) or\
                   line.startswith('#'+key):
                    output.append(line)
            return output
        elif key == '@CTIME':
            # expected to send Preset Time, Live Time, Real (Elapsed) Time
            output = []
            if self.scanheader is None: return output
            for line in self.scanheader:
                if line.startswith(key) or\
                   line.startswith('#'+key):
                    output.append(line)
            return output
        elif key == "" or key == " ":
            return self.fileheader()
        elif self.scanheader is None:
            return []
        else:
            output = []
            for line in self.scanheader:
                if line.startswith("#"+key) or\
                   line.startswith(key):
                    output.append(line)
            return output

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
            raise IndexError("Mca numbering starts at 1")
        elif number > self.nbmca():
            raise IndexError("Only %d MCAs in file" % self.nbmca())
        if hasattr(self.__data, "shape"):
            return self.__data[:,number-1]
        else:
            return self.__data[number-1]

def test():
    pass

if __name__ == "__main__":
    test()

