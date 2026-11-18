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
import sys
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QStringList"):
    QStringList = qt.QStringList
else:
    def QStringList():
        return []
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
from PyMca5.PyMcaPhysics import Elements

_logger = logging.getLogger(__name__)


QTable = qt.QTableWidget
class QComboTableItem(qt.QComboBox):
    sigCellChanged = qt.pyqtSignal(int,int)
    def __init__(self, parent=None, row = None, col = None):
        self._row = row
        self._col = col
        qt.QComboBox.__init__(self,parent)
        self.activated[int].connect(self._cellChanged)

    def _cellChanged(self, idx):
        _logger.debug("cell changed %s", idx)
        self.sigCellChanged.emit(self._row, self._col)

class QCheckBoxItem(qt.QCheckBox):
    sigCellChanged = qt.pyqtSignal(int, int)
    def __init__(self, parent=None, row = None, col = None):
        self._row = row
        self._col = col
        qt.QCheckBox.__init__(self,parent)
        self.clicked.connect(self._cellChanged)

    def _cellChanged(self):
        self.sigCellChanged.emit(self._row, self._col)


class PeakTableWidget(QTable):
    sigPeakTableWidgetSignal = qt.pyqtSignal(object)
    def __init__(self, *args,**kw):
        QTable.__init__(self, *args)
        self.setRowCount(0)
        self.labels=['Peak','Channel','Element','Line',
                     'Energy','Use','Calc. Energy']
        self.setColumnCount(len(self.labels))
        if 'labels' in kw:
            self.labels = kw['labels']
        for i in range(len(self.labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(self.labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(self.labels[i])
            self.setHorizontalHeaderItem(i,item)

        self.peaks={}
        self.peaklist=[]
        if 'peaklist' in kw:
            self.peaklist = kw['peaklist']
        self.build()
        self.cellChanged[int,int].connect(self.myslot)

        rheight = self.horizontalHeader().sizeHint().height()
        for idx in range(self.rowCount()):
            self.setRowHeight(idx, rheight)


    def build(self):
        line = 1
        oldlist=list(self.peaklist)
        self.peaklist=[]
        for peak in oldlist:
            self.newpeakline(peak,line)
            line=line+1
        self.resizeColumnToContents(0)
        #self.resizeColumnToContents(1)
        #self.resizeColumnToContents(2)
        self.resizeColumnToContents(5)

    def clearPeaks(self):
        self.peaks = {}
        self.peaklist = []
        self.setRowCount(0)

    def newpeakline(self,peak,line):
        #get current number of lines
        nlines=self.rowCount()
        #if the number of lines is smaller than line resize table
        if (line > nlines):
            self.setRowCount(line)
        linew=line-1
        self.peaks[peak]={ 'line':linew,
                           'fields':['number',
                                    'channel',
                                    'element',
                                    'elementline',
                                    'setenergy',
                                    'use',
                                    'calenergy'],
                          'number':     QString('1'),
                          'channel':    QString('0'),
                          'element':    QString('-'),
                          'elementline':QString('-'),
                          'setenergy':  QString('0'),
                          'use':        0,
                          'calenergy':  QString()}
        self.peaklist.append(peak)
        self.setReadWrite(peak,'setenergy')
        self.setReadWrite(peak,'channel')
        self.setReadOnly (peak,['number','line','calenergy'])
        col = self.peaks[peak]['fields'].index('element')
        self.peaks[peak]['element_item']=QPeriodicComboTableItem(self,
                                        row = linew, col= col)
        self.setCellWidget(linew,
                           col,
                           self.peaks[peak]['element_item'])
        self.peaks[peak]['element_item'].sigCellChanged[int,int].connect( \
                           self.myslot)
        a = QStringList()
        a.append('-')
        col = self.peaks[peak]['fields'].index('elementline')
        self.peaks[peak]['elementline_item']= QComboTableItem(self,
                                                              row = linew,
                                                              col = col)
        self.peaks[peak]['elementline_item'].addItems(a)
        self.setCellWidget(linew,
                           col,
                           self.peaks[peak]['elementline_item'])
        self.peaks[peak]['elementline_item'].sigCellChanged[int,int].connect( \
            self.myslot)

        col = self.peaks[peak]['fields'].index('use')
        self.peaks[peak]['use_item']    = QCheckBoxItem(self,
                                                        row = linew,
                                                        col = col)
        self.peaks[peak]['use_item'].setText("")
        self.setCellWidget(linew, col,
                 self.peaks[peak]['use_item'])
        self.peaks[peak]['use_item'].sigCellChanged[int,int].connect( \
                 self.myslot)

        self.peaks[peak]['use_item'].setChecked(self.peaks[peak]['use'])

    def myslot(self, row, col):
        _logger.debug("Passing by myslot %s",
                      self.peaks[self.peaklist[row]]['fields'][col])
        peak = self.peaklist[row]
        field = self.peaks[peak]['fields'][col]
        if (field == "element") or (field == "elementline"):
            key = field + "_item"
            newvalue = self.peaks[peak][key].currentText()
        elif field == "use":
            pass
        else:
            newvalue = self.item(row, col).text()
        if field == "element":
            if str(newvalue) == '-':
                #no element
                #set line to -
                options  = QStringList()
                options.append('-')
                self.peaks[peak]["elementline_item"].insertItems(0, options)
                self.peaks[peak]["elementline_item"].setCurrentIndex(0)
            else:
                #get the emission energies
                ele = str(newvalue).split()[0]
                options  = QStringList()
                energies = QStringList()
                options.append('-')
                energies.append('0.000')
                emax = 0.0
                for rays in Elements.Element[ele]['rays']:
                    for transition in Elements.Element[ele][rays]:
                        options.append("%s (%.5f)" % (transition,
                                    Elements.Element[ele][transition]['rate']))
                        energies.append("%.5f " % (Elements.Element[ele][transition]['energy']))
                        emax = max(emax,Elements.Element[ele][transition]['rate'])
                energies[0] = "%.5f " % emax
                #lineitem=qttable.QComboTableItem(self,options)
                self.peaks[peak]["elementline_item"].insertItems(0, options)
                self.peaks[peak]["elementline_item"].setCurrentIndex(0)
                #self.setItem(row,
                #             col+1,
                #             lineitem)
            self.peaks[peak][field] = newvalue
        if field == "elementline":
            if str(newvalue) == '-':
                #no element
                #set energy to rw
                self.setReadWrite(peak,'setenergy')
            else:
                #get the element energy
                #newvalue=QString(self.text(row,col-1))
                elevalue=self.peaks[peak]["element_item"].currentText()
                ele = str(elevalue).split()[0]
                energy = "0.0"
                for rays in Elements.Element[ele]['rays']:
                    for transition in Elements.Element[ele][rays]:
                        option = QString("%s (%.5f)" % (transition,
                                    Elements.Element[ele][transition]['rate']))
                        if option == newvalue:
                            energy = "%.5f " % (Elements.Element[ele][transition]['energy'])
                            break
                if energy == "0.0":
                    _logger.warning("Something is wrong")
                else:
                    self.configure(name=peak,setenergy=energy)
                self.setReadOnly(peak,'setenergy')
            self.peaks[peak][field] = newvalue
        if field == "setenergy":
            oldvalue = self.peaks[peak]["setenergy"]
            try:
                value = float(str(newvalue))
            except Exception:
                _logger.warning("%s newvalue = %s taking old value %s" % (field, newvalue, oldvalue))
                item = self.item(row, col)
                item.setText("%s" % oldvalue)
                value = float(str(oldvalue))
            self.peaks[peak][field] = value
            ddict={}
            ddict['event'] = 'use'
            self.sigPeakTableWidgetSignal.emit(ddict)

        if field == "channel":
            oldvalue = self.peaks[peak]["channel"]
            try:
                value = float(str(newvalue))
            except Exception:
                _logger.warning("%s newvalue = %s taking old value%s" % (field, newvalue, oldvalue))
                item = self.item(row, col)
                item.setText("%s" % oldvalue)
                value = float(str(oldvalue))
            self.peaks[peak][field] = value
            ddict={}
            ddict['event'] = 'use'
            self.sigPeakTableWidgetSignal.emit(ddict)

        if field == "use":
            if self.peaks[peak][field+"_item"].isChecked():
                self.peaks[peak][field] = 1
            else:
                self.peaks[peak][field] = 0
            ddict={}
            ddict['event'] = 'use'
            self.sigPeakTableWidgetSignal.emit(ddict)

    def setReadOnly(self, parameter, fields):
        _logger.debug("peak %s fields = %s asked to be read only" % (parameter, fields))
        self.setfield(parameter, fields,
                      qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)

    def setReadWrite(self, parameter, fields):
        _logger.debug("peak %s fields = %s asked to be read write" % (parameter, fields))
        self.setfield(parameter, fields,
                      qt.Qt.ItemIsEditable | qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)

    def setfield(self,peak,fields,EditType):
        _logger.debug("setfield. peak = %s fields = %s" % (peak, fields))
        if type(peak) == type (()) or \
           type(peak) == type ([]):
            peaklist=peak
        else:
            peaklist=[peak]
        if type(fields) == type (()) or \
           type(fields) == type ([]):
            fieldlist=fields
        else:
            fieldlist=[fields]
        for peak in peaklist:
            if peak in self.peaklist:
                try:
                    row=self.peaklist.index(peak)
                except ValueError:
                    row=-1
                if row >= 0:
                    for field in fieldlist:
                        if field in self.peaks[peak]['fields']:
                            col=self.peaks[peak]['fields'].index(field)
                            if (field != 'element') and (field != 'elementline'):
                                key=field+"_item"
                                item = self.item(row, col)
                                text = "%s" % self.peaks[peak][field]
                                if item is None:
                                    item = qt.QTableWidgetItem(text,
                                               qt.QTableWidgetItem.Type)
                                    self.setItem(row, col, item)
                                else:
                                    item.setText(str(text))
                                item.setFlags(EditType)


    def configure(self,*vars,**kw):
        _logger.debug("configure called with **kw = %s", kw)
        _logger.debug("configure called with *vars = %s", vars)
        name = None
        error=0
        if 'name' in kw:
            name=kw['name']
        elif 'number' in kw:
            name=kw['number']
        else:
            return 1

        keylist = []
        if "channel" in kw:
            keylist=["channel"]
        for key in kw.keys():
            if key != "setenergy":
                if key not in keylist:
                    keylist.append(key)
        if "setenergy"  in kw.keys():
            keylist.append("setenergy")

        if name in self.peaks:
            row=self.peaks[name]['line']
            for key in keylist:
              if key != 'name':
                if key in self.peaks[name]['fields']:
                    col=self.peaks[name]['fields'].index(key)
                    oldvalue=self.peaks[name][key]
                    if key == 'code':
                        newvalue = QString(str(kw[key]))
                    elif key == 'element':
                        newvalue = str(kw[key]).split()[0]
                        if newvalue == "-":
                            self.peaks[name][key+"_item"].setCurrentIndex(0)
                        else:
                            self.peaks[name][key+"_item"].setSelection(newvalue)
                        try:
                            self.myslot(row,col)
                        except Exception:
                            _logger.warning("Error setting element")
                    elif key == 'elementline':
                        try:
                            iv = self.peaks[name][key+"_item"].findText(QString(kw[key]))
                            self.peaks[name][key+"_item"].setCurrentIndex(iv)
                        except Exception:
                            _logger.warning("Error setting elementline")
                    elif key == 'use':
                        if kw[key]:
                            self.peaks[name][key] = 1
                        else:
                            self.peaks[name][key] = 0
                        self.peaks[name][key+"_item"].setChecked(self.peaks[name][key])
                    elif key == 'number':
                        if len(str(kw[key])):
                            newvalue=float(str(kw[key]))
                            newvalue= QString("%3d" % newvalue)
                            self.peaks[name][key]=newvalue
                        else:
                            self.peaks[name][key]=oldvalue
                        text = self.peaks[name][key]
                        item = self.item(row, col)
                        if item is None:
                            item = qt.QTableWidgetItem(text,
                                            qt.QTableWidgetItem.Type)
                            self.setItem(row, col, item)
                        else:
                            item.setText(text)
                    elif key == 'channel':
                        _logger.debug("setting channel in configure")
                        if len(str(kw[key])):
                            newvalue = float(str(kw[key]))
                            newvalue = QString("%.3f" % newvalue)
                            self.peaks[name][key]=newvalue
                        else:
                            self.peaks[name][key]=oldvalue
                        text = self.peaks[name][key]
                        item = self.item(row, col)
                        if item is None:
                            item = qt.QTableWidgetItem(text,
                                            qt.QTableWidgetItem.Type)
                            self.setItem(row, col, item)
                        else:
                            item.setText(text)
                    elif (key == 'setenergy') or (key == 'calenergy'):
                        if len(str(kw[key])):
                            newvalue=float(str(kw[key]))
                            newvalue= QString("%.4f" % newvalue)
                            self.peaks[name][key]=newvalue
                        else:
                            self.peaks[name][key]=oldvalue
                        text = self.peaks[name][key]
                        item = self.item(row, col)
                        if item is None:
                            item = qt.QTableWidgetItem(text,
                                            qt.QTableWidgetItem.Type)
                            self.setItem(row, col, item)
                        else:
                            item.setText(text)
                        #self.myslot(row,col)
                    else:
                        if len(str(kw[key])):
                            newvalue=float(str(kw[key]))
                            if key == 'sigma':
                                newvalue= "%6.3g" % newvalue
                            else:
                                newvalue= "%8g" % newvalue
                        else:
                            newvalue=""
                        newvalue=QString(newvalue)
        return error


    def validate(self,name,key,oldvalue,newvalue):
        if (key == 'setenergy') or (key == 'number') or (key == 'calcenergy'):
            try:
                float(str(newvalue))
            except Exception:
                return 0
        return 1

    def getdict(self, *var):
        _logger.warning("PeakTableWidget.getdict deprecated. Use getDict")
        return self.getDict(*var)

    def getDict(self,*var):
        ddict={}
        if len(var) == 0:
            #asked for the dict of dicts
            for peak in self.peaks.keys():
                ddict[peak] = {}
                ddict[peak]['number']      = float(str(self.peaks[peak]['number']))
                ddict[peak]['channel']     = float(str(self.peaks[peak]['channel']))
                ddict[peak]['element']     = str(self.peaks[peak]['element'])
                ddict[peak]['elementline'] = str(self.peaks[peak]['elementline'])
                ddict[peak]['setenergy']   = float(str(self.peaks[peak]['setenergy']))
                ddict[peak]['use']         = self.peaks[peak]['use']
                if len(str(self.peaks[peak]['calenergy'])):
                    ddict[peak]['calenergy']   = float(str(self.peaks[peak]['calenergy']))
                else:
                    ddict[peak]['calenergy']   = ""
        else:
            peak=var[0]
            if peak in self.peaks.keys():
                ddict['number']      = float(str(self.peaks[peak]['number']))
                ddict['channel']     = float(str(self.peaks[peak]['channel']))
                ddict['element']     = str(self.peaks[peak]['element'])
                ddict['elementline'] = str(self.peaks[peak]['elementline'])
                ddict['setenergy']   = float(str(self.peaks[peak]['setenergy']))
                ddict['use']         = self.peaks[peak]['use']
                if len(str(self.peaks[peak]['calenergy'])):
                    ddict['calenergy']   = float(str(self.peaks[peak]['calenergy']))
                else:
                    ddict['calenergy']   = ""
        return ddict

class QPeriodicComboTableItem(QComboTableItem):
    """ Periodic Table Combo List to be used in a QTable
        Init options:
            table (mandatory)= parent QTable
            addnone= 1 (default) add "-" in the list to provide possibility
                        to select no specific element.
                 0 only element list.
            detailed= 1 (default) display element symbol, Z and name
                  0 display only element symbol and Z
        Public methods:
            setSelection(eltsymbol):
                Set the element selected given its symbol
            getSelection():
                Return symbol of element selected

        Signals:
            sigValueChanged(int,int)
    """
    sigValueChanged = qt.pyqtSignal(int, int)
    def __init__(self, table=None, addnone=1, detailed=0, row=None, col=None):
        strlist = QStringList()
        self.addnone= (addnone==1)
        if self.addnone: strlist.append("-")
        for (symbol, Z, x, y, name, mass, density) in Elements.ElementsInfo:
            if detailed:    txt= "%2s (%d) - %s"%(symbol, Z, name)
            else:       txt= "%2s (%d)"%(symbol, Z)
            strlist.append(txt)
        if row is None:
            row = 0
        if col is None:
            col = 0
        self._row = row
        self._col = col
        qt.QComboBox.__init__(self)
        self.addItems(strlist)
        self.activated[int].connect(self._cellChanged)

    def _cellChanged(self, idx):
        self.sigCellChanged.emit(self._row, self._col)

    def setSelection(self, symbol=None):
        if symbol is None:
            if self.addnone:
                self.setCurrentIndex(0)
        else:
            idx= self.addnone+Elements.getz(symbol)-1
            self.setCurrentIndex(idx)

    def getSelection(self):
        idx = self.currentIndex()
        if self.addnone and not idx:
            return None
        else:
            return Elements.ElementList[idx - self.addnone]

def main(args):
    app=qt.QApplication(args)
    win=qt.QMainWindow()
    #tab = Parameters(labels=['Parameter','Estimation','Fit Value','Sigma',
    #                    'Restrains','Min/Parame','Max/Factor/Delta/'],
    #               paramlist=['Height','Position','FWHM'])
    tab = PeakTableWidget(labels= ['Peak','Channel','Element','Line','Set Energy','Use',
                            'Cal. Energy'],
                            peaklist=['1'])
    tab.showGrid()
    tab.configure(name='1',number=24,channel='1234',use=1,
                  setenergy=12.5,calenergy=24.0)
    tab.show()
    app.exec()

if __name__=="__main__":
    main(sys.argv)
