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
__author__ = "V. Armando Sole - ESRF"
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
_logger = logging.getLogger(__name__)

try:
    from PyMca5.PyMcaGui.misc.TableWidget import TableWidget
    QTable = TableWidget
except Exception:
    _logger.warning("Cannot import clipboard enabled table")
    QTable = qt.QTableWidget

class McaTable(QTable):
    sigMcaTableSignal = qt.pyqtSignal(object)
    sigClosed = qt.pyqtSignal(object)
    def __init__(self, *args,**kw):
        QTable.__init__(self, *args)
        if 'labels' in kw:
            self.labels=[]
            for label in kw['labels']:
                self.labels.append(label)
        else:
            #self.labels=['Element','Group','Energy','Ratio','Fit Area','MCA Area','Sigma','Fwhm','Chisq']
            self.labels=['Element','Group','Fit Area','Sigma','Energy','Ratio','FWHM','Chi square']
        self.setColumnCount(len(self.labels))

        for i in range(len(self.labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(self.labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(self.labels[i])
            self.setHorizontalHeaderItem(i,item)

        self.regionlist=[]
        self.regiondict={}
        verticalHeader = self.verticalHeader() 
        if hasattr(verticalHeader, "setSectionsClickable"):
            self.verticalHeader().setSectionsClickable(True)
        else:
            self.verticalHeader().setClickable(True)
        self.verticalHeader().sectionClicked.connect(self.__myslot)

        self.itemSelectionChanged.connect(self.__myslot)
        #self.connect(self,qt.SIGNAL("selectionChanged()"),self.__myslot)
        #self.setSelectionMode(qttable.QTable.SingleRow)


    def fillfrommca(self,result,diag=1):
        line=0
        #calculate the number of rows
        nrows = 0
        for group in result['groups']:
            nrows += 1
            for peak in result[group]['peaks']:
                nrows += 1
            for peak0 in result[group]['escapepeaks']:
                peak  = peak0+"esc"
                if result[group][peak]['ratio'] > 0.0:
                    nrows += 1
        self.setRowCount(nrows)
        for group in result['groups']:
            ele,group0 = group.split()
            fitarea    = QString("%.4e" % (result[group]['fitarea']))
            sigmaarea  = QString("%.2e" % (result[group]['sigmaarea']))
            fields = [ele,group0,fitarea,sigmaarea]
            col = 0
            color = qt.QApplication.instance().palette().color(qt.QPalette.Base)
            nlines = self.rowCount()
            if (line+1) > nlines:
                self.setRowCount(line+1)
            for i in range(len(self.labels)):
                if i < len(fields):
                    item = self.item(line, col)
                    text = fields[i]
                    if item is None:
                        item = qt.QTableWidgetItem(text,
                                                   qt.QTableWidgetItem.Type)
                        self.setItem(line, col, item)
                    else:
                        item.setText(text)
                        if hasattr(item, "setBackground"):
                            item.setBackground(color)
                        else:
                            item.setBackgroundColor(color)
                        item.setFlags(qt.Qt.ItemIsSelectable|
                                      qt.Qt.ItemIsEnabled)
                else:
                    item = self.item(line, col)
                    if item is not None:
                        item.setText("")
                    #self.setItem(line, col, item)
                col=col+1
            line += 1
            color = qt.QApplication.instance().palette().color(qt.QPalette.AlternateBase)
            for peak in result[group]['peaks']:
                name  = peak
                energy = QString("%.3f" % (result[group][peak]['energy']))
                ratio  = QString("%.5f" % (result[group][peak]['ratio']))
                area   = QString("%.4e" % (result[group][peak]['fitarea']))
                sigma  = QString("%.2e" % (result[group][peak]['sigmaarea']))
                fwhm   = QString("%.3f" % (result[group][peak]['fwhm']))
                chisq  = QString("%.2f" % (result[group][peak]['chisq']))
                if (line+1) > nlines:
                    self.setRowCount(line+1)
                fields = [name,area,sigma,energy,ratio,fwhm,chisq]
                col = 1
                for field in fields:
                    item = self.item(line, col)
                    text = field
                    if item is None:
                        item = qt.QTableWidgetItem(text,
                                                   qt.QTableWidgetItem.Type)
                        self.setItem(line, col, item)
                    else:
                        item.setText(text)
                    if hasattr(item, "setBackground"):
                        item.setBackground(color)
                    else:
                        item.setBackgroundColor(color)
                    item.setFlags(qt.Qt.ItemIsSelectable|
                                  qt.Qt.ItemIsEnabled)
                    col=col+1
                line+=1
            for peak0 in result[group]['escapepeaks']:
                peak  = peak0+"esc"
                if result[group][peak]['ratio'] > 0.0:
                    energy = QString("%.3f" % (result[group][peak]['energy']))
                    ratio  = QString("%.5f" % (result[group][peak]['ratio']))
                    area   = QString("%.4e" % (result[group][peak]['fitarea']))
                    sigma  = QString("%.2e" % (result[group][peak]['sigmaarea']))
                    fwhm   = QString("%.3f" % (result[group][peak]['fwhm']))
                    chisq  = QString("%.2f" % (result[group][peak]['chisq']))
                    if (line+1) > nlines:
                        self.setRowCount(line+1)
                    fields = [peak,area,sigma,energy,ratio,fwhm,chisq]
                    col = 1
                    for field in fields:
                        item = self.item(line, col)
                        if item is None:
                            item = qt.QTableWidgetItem(field,
                                                       qt.QTableWidgetItem.Type)
                            self.setItem(line, col, item)
                        else:
                            item.setText(field)
                        if hasattr(item, "setBackground"):
                            item.setBackground(color)
                        else:
                            item.setBackgroundColor(color)
                        item.setFlags(qt.Qt.ItemIsSelectable|
                                      qt.Qt.ItemIsEnabled)
                        col=col+1
                    line+=1
        for i in range(self.columnCount()):
            if i>-1:
                self.resizeColumnToContents(i)

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
            if param['name'].find('ST_Area') != -1:
                # value and sigmavalue defined via fitlabel
                values[-1]      = value * (1.0 + param['fitresult'])
                #just an approximation
                sigmavalues[-1] = sigmavalue * (1.0 + param['fitresult'])
            elif param['name'].find('LT_Area')!= -1:
                pass
            elif param['name'].find(fitlabel) != -1:
                value      = param['fitresult']
                sigmavalue = param['sigma']
                values.append(value)
                sigmavalues.append(sigmavalue)
        return fitlabel, values, sigmavalues


    def __myslot(self,*var):
        ddict={}
        if len(var) == 0:
            #selection changed event
            #get the current selection
            ddict['event'] = 'McaTableClicked'
            row = self.currentRow()
        else:
            #Header click
            ddict['event'] = 'McaTableRowHeaderClicked'
            row = var[0]
        ccol = self.currentColumn()
        ddict['row'  ]       = row
        ddict['col']         = ccol
        ddict['labelslist']  = self.labels
        if row >= 0:
            col = 0
            for label in self.labels:
                item = self.item(row, col)
                if item is not None:
                    text = item.text()
                    try:
                        ddict[label] = float(str(text))
                    except Exception:
                        ddict[label] = str(text)
                col +=1
        self.sigMcaTableSignal.emit(ddict)

    def gettext(self):
        lemon= ("#%x%x%x" % (255,250,205)).upper()
        if QTVERSION < '4.0.0':
            hb = self.horizontalHeader().paletteBackgroundColor()
            hcolor = ("#%x%x%x" % (hb.red(),hb.green(),hb.blue())).upper()
        else:
            _logger.debug("color background to implement")
            hcolor = ("#%x%x%x" % (230,240,249)).upper()
        text = ""
        text += ("<nobr>")
        text += ("<table>")
        text += ("<tr>")
        ncols = self.columnCount()
        for l in range(ncols):
            text+=('<td align="left" bgcolor="%s"><b>' % hcolor)
            text+=(str(self.horizontalHeaderItem(l).text()))
            text+=("</b></td>")
        text+=("</tr>")
        #text+=( str(QString("</br>"))
        nrows = self.rowCount()
        for r in range(nrows):
            text+=("<tr>")
            moretext = ""
            item = self.item(r, 0)
            if item is not None:
                moretext = str(item.text())
            if len(moretext):
                color = "white"
                b="<b>"
            else:
                b=""
                color = lemon
            for c in range(ncols):
                moretext = ""
                item = self.item(r, c)
                if item is not None:
                    moretext = str(item.text())
                if len(moretext):
                    finalcolor = color
                else:
                    finalcolor = "white"
                if c<2:
                    text+=('<td align="left" bgcolor="%s">%s' % (finalcolor,b))
                else:
                    text+=('<td align="right" bgcolor="%s">%s' % (finalcolor,b))
                text+= moretext
                if len(b):
                    text+=("</td>")
                else:
                    text+=("</b></td>")
            moretext = ""
            item = self.item(r, 0)
            if item is not None:
                moretext = str(item.text())
            if len(moretext):
                text+=("</b>")
            text+=("</tr>")
            #text+=( str(QString("<br>"))
            text+=("\n")
        text+=("</table>")
        text+=("</nobr>")
        return text

    def closeEvent(self, event):
        QTable.closeEvent(self, event)
        ddict={}
        ddict['event']= 'closed'
        self.sigClosed.emit(ddict)
