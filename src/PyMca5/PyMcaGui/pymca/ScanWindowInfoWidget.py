#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2024 European Synchrotron Radiation Facility
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


import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt
import logging

_logger = logging.getLogger(__name__)

QTVERSION = qt.qVersion()

"""
This module implements an info widget containing :
    - source name, scan name
    - h,k,l infos
    - peak, peak position
    - fwhm, center of fwhm
    - center of mass
"""


DEBUG = 0
STATISTICS = 1


class SpecArithmetic(object):
    """
    This class tries to mimic SPEC operations.
    Correct peak positions and fwhm information
    have to be made via a fit.
    """

    def search_peak(self, xdata, ydata):
        """
        Search a peak and its position in arrays xdata ad ydata.
        Return three integer:
          - peak position
          - peak value
          - index of peak position in array xdata
            This result may accelerate the fwhm search.
        """
        ydata = numpy.asarray(ydata)
        ymax = ydata[numpy.isfinite(ydata)].max()
        idx = self.__give_index(ymax, ydata)
        return xdata[idx], ymax, idx

    def search_com(self, xdata,ydata):
        """
        Return the center of mass in arrays xdata and ydata
        """
        num = numpy.sum(xdata * ydata)
        denom = numpy.sum(ydata)
        if abs(denom) > 0:
            result = num / denom
        else:
            result = 0

        return result

    def search_fwhm(self, xdata, ydata, peak=None, index=None):
        """
        Search a fwhm and its center in arrays xdata and ydatas.
        If no fwhm is found, (0,0) is returned.
        peak and index which are coming from search_peak result, may
        accelerate calculation
        """
        if peak is None or index is None:
            x, mypeak, index_peak = self.search_peak(xdata, ydata)
        else:
            mypeak = peak
            index_peak = index

        hm = mypeak / 2
        idx = index_peak

        try:
            while ydata[idx] >= hm:
                idx -= 1
            x0 = float(xdata[idx])
            x1 = float(xdata[idx + 1])
            y0 = float(ydata[idx])
            y1 = float(ydata[idx + 1])

            lhmx = (hm * (x1 - x0) - (y0 * x1) + (y1 * x0)) / (y1 - y0)
        except ZeroDivisionError:
            lhmx = 0
        except IndexError:
            lhmx = xdata[0]

        idx = index_peak
        try:
            while ydata[idx] >= hm:
                idx += 1

            x0 = float(xdata[idx - 1])
            x1 = float(xdata[idx])
            y0 = float(ydata[idx - 1])
            y1 = float(ydata[idx])

            uhmx = (hm * (x1 - x0) - (y0 * x1) + (y1 * x0)) / (y1 - y0)
        except ZeroDivisionError:
            uhmx = 0
        except IndexError:
            uhmx = xdata[-1]

        fwhm = uhmx - lhmx
        cfwhm = (uhmx + lhmx) / 2
        return fwhm, cfwhm


    def __give_index(self, elem,array):
         """
         Return the index of elem in array
         """
         mylist = array.tolist()
         return mylist.index(elem)

class HKL(qt.QWidget):
    def __init__(self, parent=None, h="", k="", l=""):
        qt.QWidget.__init__(self, parent)
        layout = qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        hlabel = qt.QLabel(self)
        hlabel.setText('H:')
        self.h = qt.QLineEdit(self)
        self.h.setReadOnly(True)
        fmetrics = self.h.fontMetrics()
        fmtext = '##.####'
        if hasattr(fmetrics, "maxWidth"):
            width = fmetrics.maxWidth()*len(fmtext)
        else:
            #deprecated
            _logger.info("Using deprecated method")
            width = fmetrics.width(fmtext)
        self.h.setFixedWidth(width)

        klabel = qt.QLabel(self)
        klabel.setText('K:')
        self.k = qt.QLineEdit(self)
        self.k.setReadOnly(True)
        self.k.setFixedWidth(width)

        llabel = qt.QLabel(self)
        llabel.setText('L:')
        self.l = qt.QLineEdit(self)
        self.l.setReadOnly(True)
        self.l.setFixedWidth(width)

        self.setHKL(h, k, l)

        layout.addWidget(hlabel)
        layout.addWidget(self.h)
        layout.addWidget(klabel)
        layout.addWidget(self.k)
        layout.addWidget(llabel)
        layout.addWidget(self.l)

    def setHKL(self, h="", k="", l=""):
        dformat = "%.4f"
        if isinstance(h, str):
            self.h.setText(h)
        else:
            self.h.setText(dformat % h)
        if isinstance(k, str):
            self.k.setText(k)
        else:
            self.k.setText(dformat % k)
        if isinstance(l, str):
            self.l.setText(l)
        else:
            self.l.setText(dformat % l)


class GraphInfoWidget(qt.QWidget):
    """Widget displaying statistics about curve data:
    peak info (x position, y value, fwhm, center of fwhm), max y value,
    min y value, delta y, mean y, center of mass of y values, standard
    deviation of y.

    This information is extracted directly from the curve data."""
    def __init__(self, parent):
        qt.QWidget.__init__(self, parent)
        layout = qt.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # peak
        peak = qt.QLabel(self)
        peak.setText("Peak:  ")
        self.peak = qt.QLineEdit(self)
        self.peak.setReadOnly(True)
        hboxPeak = qt.QWidget(self)
        hboxPeak.l = qt.QHBoxLayout(hboxPeak)
        hboxPeak.l.setContentsMargins(0, 0, 0, 0)
        hboxPeak.l.setSpacing(0)
        peakAt = qt.QLabel(hboxPeak)
        peakAt.setText(" at:")
        self.peakAt = qt.QLineEdit(hboxPeak)
        self.peak.setReadOnly(True)
        hboxPeak.l.addWidget(peakAt)
        hboxPeak.l.addWidget(self.peakAt)

        # fwhm
        fwhm = qt.QLabel(self)
        fwhm.setText("Fwhm: ")
        self.fwhm = qt.QLineEdit(self)
        self.fwhm.setReadOnly(True)
        hboxFwhm = qt.QWidget(self)
        hboxFwhm.l = qt.QHBoxLayout(hboxFwhm)
        hboxFwhm.l.setContentsMargins(0, 0, 0, 0)
        hboxFwhm.l.setSpacing(0)
        fwhmAt = qt.QLabel(hboxFwhm)
        fwhmAt.setText(" at:")
        self.fwhmAt = qt.QLineEdit(hboxFwhm)
        self.fwhm.setReadOnly(True)
        hboxFwhm.l.addWidget(fwhmAt)
        hboxFwhm.l.addWidget(self.fwhmAt)

        # statistics
        # COM
        com = qt.QLabel(self)
        com.setText("COM:")
        self.com = qt.QLineEdit(self)
        self.com.setReadOnly(True)

        # mean
        mean = qt.QLabel(self)
        mean.setText("Mean:")
        self.mean = qt.QLineEdit(self)
        self.mean.setReadOnly(True)

        # STD
        std = qt.QLabel(self)
        std.setText("STD:")
        self.std = qt.QLineEdit(self)
        self.std.setReadOnly(True)

        # Max
        maximum = qt.QLabel(self)
        maximum.setText("Max:")
        self.maximum = qt.QLineEdit(self)
        self.maximum.setReadOnly(True)

        # Min
        minimum = qt.QLabel(self)
        minimum.setText("Min:")
        self.minimum = qt.QLineEdit(self)
        self.minimum.setReadOnly(True)

        # STD
        delta = qt.QLabel(self)
        delta.setText("Delta:")
        self.delta = qt.QLineEdit(self)
        self.delta.setReadOnly(True)

        layout.addWidget(peak,      0, 0)
        layout.addWidget(self.peak, 0, 1)
        layout.addWidget(hboxPeak,  0, 2)
        layout.addWidget(com,       0, 3)
        layout.addWidget(self.com,  0, 4)
        layout.addWidget(mean,      0, 5)
        layout.addWidget(self.mean, 0, 6)
        layout.addWidget(std,       0, 7)
        layout.addWidget(self.std,  0, 8)

        layout.addWidget(fwhm,          1, 0)
        layout.addWidget(self.fwhm,     1, 1)
        layout.addWidget(hboxFwhm,      1, 2)
        layout.addWidget(maximum,       1, 3)
        layout.addWidget(self.maximum,  1, 4)
        layout.addWidget(minimum,       1, 5)
        layout.addWidget(self.minimum,  1, 6)
        layout.addWidget(delta,         1, 7)
        layout.addWidget(self.delta,    1, 8)
        self.specArithmetic = SpecArithmetic()

    def updateFromDataObject(self, dataObject):
        ydata = numpy.ravel(dataObject.y[0])
        ylen = len(ydata)
        if ylen:
            if dataObject.x is None:
                xdata = numpy.arange(ylen).astype(numpy.float64)
            elif not len(dataObject.x):
                xdata = numpy.arange(ylen).astype(numpy.float64)
            else:
                xdata = numpy.ravel(dataObject.x[0])
        else:
            xdata = None
        self.updateFromXY(xdata, ydata)


    def updateFromXY(self, xdata, ydata):
        if len(ydata):
            peakpos, peak, myidx = self.specArithmetic.search_peak(xdata, ydata)
            com = self.specArithmetic.search_com(xdata, ydata)
            fwhm, cfwhm = self.specArithmetic.search_fwhm(xdata, ydata,
                                                          peak=peak, index=myidx)
            ymax = max(ydata)
            ymin = min(ydata)
            ymean = sum(ydata) / len(ydata)
            if len(ydata) > 1:
                ystd = numpy.sqrt(sum((ydata - ymean) * (ydata - ymean)) / len(ydata))
            else:
                ystd = 0
            delta = ymax - ymin
            fformat = "%.7g"
            peakpos = fformat % peakpos
            peak = fformat % peak
            # myidx = "%d" % myidx
            com = fformat % com
            fwhm = fformat % fwhm
            cfwhm = fformat % cfwhm
            ymean = fformat % ymean
            ystd = fformat % ystd
            ymax = fformat % ymax
            ymin = fformat % ymin
            delta = fformat % delta
        else:
            peakpos = "----"
            peak = "----"
            # myidx = "----"
            com = "----"
            fwhm = "----"
            cfwhm = "----"
            ymean = "----"
            ystd = "----"
            ymax = "----"
            ymin = "----"
            delta = "----"
        self.peak.setText(peak)
        self.peakAt.setText(peakpos)
        self.fwhm.setText(fwhm)
        self.fwhmAt.setText(cfwhm)
        self.com.setText(com)
        self.mean.setText(ymean)
        self.std.setText(ystd)
        self.minimum.setText(ymin)
        self.maximum.setText(ymax)
        self.delta.setText(delta)

    def getInfo(self):
        ddict={}
        ddict['peak']   = self.peak.text()
        ddict['peakat'] = self.peakAt.text()
        ddict['fwhm']   = self.fwhm.text()
        ddict['fwhmat'] = self.fwhmAt.text()
        ddict['com']    = self.com.text()
        ddict['mean']   = self.mean.text()
        ddict['std']    = self.std.text()
        ddict['min']    = self.minimum.text()
        ddict['max']    = self.maximum.text()
        ddict['delta']  = self.delta.text()
        return ddict


class ScanInfoWidget(qt.QWidget):
    """Widget displaying curve metadata:
    data source, first scan header line, H, K, L

    This information is extracted from the curve info dict."""
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        layout = qt.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # scan info
        hBox = qt.QWidget(self)
        hBoxLayout = qt.QHBoxLayout(hBox)
        hBoxLayout.setContentsMargins(0, 0, 0, 0)
        hBoxLayout.setSpacing(0)
        sourceLabel = qt.QLabel(hBox)
        sourceLabel.setText('Source:')
        self.sourceLabel = qt.QLineEdit(hBox)
        self.sourceLabel.setReadOnly(True)
        hBoxLayout.addWidget(sourceLabel)
        hBoxLayout.addWidget(self.sourceLabel)

        scanLabel = qt.QLabel(self)
        scanLabel.setText('Scan:   ')
        self.scanLabel = qt.QLineEdit(self)
        self.scanLabel.setReadOnly(True)

        self.hkl = HKL(self)
        layout.addWidget(hBox, 0, 0, 1, 7)
        # layout.addWidget(self.sourceLabel, 0, 1)#, 1, 9)
        layout.addWidget(scanLabel,        1, 0)
        layout.addWidget(self.scanLabel,   1, 1)
        layout.addWidget(self.hkl,         1, 4, 1, 3)

    def updateFromDataObject(self, dataObject):
        info = dataObject.info
        return self.updateFromInfoDict(info)

    def updateFromInfoDict(self, info):
        source = info.get('SourceName', None)
        if source is None:
            self.sourceLabel.setText("")
        else:
            if isinstance(source, str):
                self.sourceLabel.setText(source)
            else:
                self.sourceLabel.setText(source[0])
        scan = info.get('Header', None)
        if scan is None:
            scan = ""
            if "envdict" in info:
                scan = info["envdict"].get('title', "")
            self.scanLabel.setText(scan)
        else:
            self.scanLabel.setText(scan[0])
        hkl = info.get('hkl', None)
        if hkl is None:
            self.hkl.setHKL("----", "----", "----")
        else:
            self.hkl.setHKL(*hkl)

    def getInfo(self):
        ddict = {}
        ddict['source'] = self.sourceLabel.text()
        ddict['scan'] = self.scanLabel.text()
        ddict['hkl'] = ["%s" % self.hkl.h.text(),
                        "%s" % self.hkl.k.text(),
                        "%s" % self.hkl.l.text()]
        return ddict

class ScanWindowInfoWidget(qt.QWidget):
    def __init__(self, parent = None):
        qt.QWidget.__init__(self, parent)
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.scanInfo = ScanInfoWidget(self)
        self.graphInfo = GraphInfoWidget(self)

        layout.addWidget(self.scanInfo)
        layout.addWidget(self.graphInfo)

    def updateFromDataObject(self, dataObject):
        self.scanInfo.updateFromDataObject(dataObject)
        self.graphInfo.updateFromDataObject(dataObject)

    def updateFromXYInfo(self, xdata, ydata, info):
        self.scanInfo.updateFromInfoDict(info)
        self.graphInfo.updateFromXY(xdata, ydata)

    def getInfo(self):
        ddict = {}
        ddict['scan']  = self.scanInfo.getInfo()
        ddict['graph'] = self.graphInfo.getInfo()
        return ddict


def test():
    app = qt.QApplication([])
    w = ScanWindowInfoWidget()
    app.lastWindowClosed.connect(app.quit)
    w.show()
    app.exec()


if __name__ == '__main__':
        test()
