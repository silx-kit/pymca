#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str

QTVERSION = qt.qVersion()

QTable = qt.QTableWidget

_logger = logging.getLogger(__name__)


class McaTable(QTable):
    sigMcaTableSignal = qt.pyqtSignal(object)
    def __init__(self, *args,**kw):
        QTable.__init__(self, *args)
        self.setRowCount(1)
        self.setColumnCount(1)
        self.labels=['Parameter','Estimation','Fit Value','Sigma',
                     'Restrains','Min/Parame','Max/Factor/Delta/']
        self.code_options=["FREE","POSITIVE","QUOTED",
                 "FIXED","FACTOR","DELTA","SUM","IGNORE","ADD","SHOW"]

        i=0
        if 'labels' in kw:
            self.labels=[]
            for label in kw['labels']:
                self.labels.append(label)
        else:
            self.labels=['Position','Fit Area','MCA Area','Sigma','Fwhm','Chisq',
                         'Region','XBegin','XEnd']

        self.setColumnCount(len(self.labels))
        for label in self.labels:
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(self.labels[i],
                                           qt.QTableWidgetItem.Type)
                self.setHorizontalHeaderItem(i,item)
            item.setText(self.labels[i])
            self.resizeColumnToContents(i)
            i=i+1

        self.regionlist=[]
        self.regiondict={}
        if _logger.getEffectiveLevel() == logging.DEBUG:
            _logger.debug("MCATABLE click on vertical header items?")
            self.verticalHeader().sectionClicked[int].connect(self.__myslot)
        self.cellClicked[int, int].connect(self.__myslot)
        self.itemSelectionChanged[()].connect(self.__myslot)


    def fillfrommca(self,mcaresult,diag=1):
        line0=0
        region=0
        alreadyforced = 0
        for result in mcaresult:
            region=region+1
            if result['chisq'] is not None:
                chisq=QString("%6.2f" % (result['chisq']))
            else:
                chisq=QString("Fit Error")
            if 1:
                xbegin=QString("%6g" % (result['xbegin']))
                xend=QString("%6g" % (result['xend']))
                fitlabel,fitpars, fitsigmas = self.__getfitpar(result)
                item = self.horizontalHeaderItem(1)
                item.setText("Fit "+fitlabel)
                i = 0
                for (pos,area,sigma,fwhm) in result['mca_areas']:
                    line0=line0+1
                    nlines=self.rowCount()
                    if (line0 > nlines):
                        self.setRowCount(line0)
                    line=line0-1
                    #pos=QString(str(pos))
                    #area=QString(str(area))
                    #sigma=QString(str(sigma))
                    #fwhm=QString(str(fwhm))
                    tregion=QString(str(region))
                    pos=QString("%6g" % (pos))
                    fitpar = QString("%6g" % (fitpars[i]))
                    if fitlabel == 'Area':
                        sigma = max(sigma,fitsigmas[i])
                    areastr=QString("%6g" % (area))
                    sigmastr=QString("%6.3g" % (sigma))
                    fwhm=QString("%6g" % (fwhm))
                    tregion=QString("%6g" % (region))
                    fields=[pos,fitpar,areastr,sigmastr,fwhm,chisq,tregion,xbegin,xend]
                    col=0
                    recolor = 0
                    if fitlabel == 'Area':
                        if diag:
                            if abs(fitpars[i]-area) > (3.0 * sigma):
                                try:
                                    _hl = qt.QApplication.instance().palette().color(qt.QPalette.Highlight)
                                    color = qt.QColor(_hl.red(), _hl.green(), _hl.blue(), 100)
                                except Exception:
                                    color = qt.QColor(255,182,193)
                                recolor = 1
                    for field in fields:
                        key = self.item(line, col)
                        if key is None:
                            key = qt.QTableWidgetItem(field)
                            self.setItem(line, col, key)
                        else:
                            item.setText(field)
                        if recolor:
                            #function introduced in Qt 4.2.0
                            item.setBackground(qt.QBrush(color))
                        item.setFlags(qt.Qt.ItemIsSelectable|qt.Qt.ItemIsEnabled)
                        col=col+1
                    if recolor:
                        if not alreadyforced:
                            alreadyforced = 1
                            self.scrollToItem(self.item(line, 0))
                    i += 1

        i = 0
        for label in self.labels:
            self.resizeColumnToContents(i)
            i=i+1
        ndict = {}
        ndict['event'] = 'McaTableFilled'
        self.sigMcaTableSignal.emit(ndict)


    def __getfitpar(self,result):
        if  result['fitconfig']['fittheory'].find("Area") != -1:
            fitlabel='Area'
        elif result['fitconfig']['fittheory'].find("Hypermet") != -1:
            fitlabel='Area'
        else:
            fitlabel='Height'
        values = []
        sigmavalues = []
        for param in result['paramlist']:
            if param['name'].find('ST_Area')!= -1:
                # value and sigmavalue known via fitlabel
                values[-1]      = value * (1.0 + param['fitresult'])
                #just an approximation
                sigmavalues[-1] = sigmavalue * (1.0 + param['fitresult'])
            elif param['name'].find('LT_Area')!= -1:
                pass
            elif param['name'].find(fitlabel)!= -1:
                value      = param['fitresult']
                sigmavalue = param['sigma']
                values.append(value)
                sigmavalues.append(sigmavalue)
        return fitlabel, values, sigmavalues


    def __myslot(self, *var):
        ddict={}
        if len(var) == 0:
            #selection changed event
            #get the current selection
            ddict['event']       = 'McaTableClicked'
            row = self.currentRow()
        else:
            #Header click
            ddict['event']       = 'McaTableRowHeaderClicked'
            row = var[0]
        ccol = self.currentColumn()
        ddict['row'  ]       = row
        ddict['col']         = ccol
        ddict['labelslist']  = self.labels
        if row >= 0:
            col = 0
            for label in self.labels:
                text = str(self.item(row, col).text())
                try:
                    ddict[label] = float(text)
                except Exception:
                    ddict[label] = text
                col +=1
        self.sigMcaTableSignal.emit(ddict)
