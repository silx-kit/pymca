#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2026 European Synchrotron Radiation Facility
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
import os
import numpy
import logging
from . import QXTube
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaGui.plotting import PyMca_Icons as Icons
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
qt = QXTube.qt
QTable = qt.QTableWidget

QTVERSION = qt.qVersion()

_logger = logging.getLogger(__name__)


class EnergyTab(qt.QWidget):
    def __init__(self,parent=None, name="Energy Tab"):
        qt.QWidget.__init__(self, parent)
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        hbox = qt.QWidget(self)
        self.hbox = qt.QHBoxLayout(hbox)
        self.hbox.setContentsMargins(0, 0, 0, 0)
        self.hbox.setSpacing(0)
        self.tube = QXTube.QXTube(hbox)
        self.table  = EnergyTable(hbox)
        self.hbox.addWidget(self.tube)
        self.hbox.addWidget(self.table)
        self.tube.plot()
        self.tube.hide()
        self.outputFilter = None
        self.inputDir = None
        self.outputDir = None

        self.__calculating = 0
        self.tubeActionsBox = qt.QWidget(self)
        actionsLayout = qt.QHBoxLayout(self.tubeActionsBox)
        actionsLayout.setContentsMargins(0, 0, 0, 0)
        actionsLayout.setSpacing(0)
        #tube setup button
        self.tubeButton = qt.QPushButton(self.tubeActionsBox)
        self.tubeButton.setText("Open X-Ray Tube Setup")
        actionsLayout.addWidget(self.tubeButton, 1)
        #load new energy table
        self.tubeLoadButton = qt.QPushButton(self.tubeActionsBox)
        self.tubeLoadButton.setText("Load Table")
        actionsLayout.addWidget(self.tubeLoadButton, 0)
        #save seen energy table
        self.tubeSaveButton = qt.QPushButton(self.tubeActionsBox)
        self.tubeSaveButton.setText("Save Table")
        actionsLayout.addWidget(self.tubeSaveButton, 0)

        layout.addWidget(self.tubeActionsBox)
        layout.addWidget(hbox)
        self.tubeButton.clicked.connect(self.tubeButtonClicked)
        self.tubeLoadButton.clicked.connect(self.loadButtonClicked)
        self.tubeSaveButton.clicked.connect(self.saveButtonClicked)
        self.tube.sigQXTubeSignal.connect(self.__tubeUpdated)

    def tubeButtonClicked(self):
        if self.tube.isHidden():
            self.tube.show()
            self.tubeButton.setText("Close X-Ray Tube Setup")
            self.tubeLoadButton.hide()
            self.tubeSaveButton.hide()
        else:
            self.tube.hide()
            self.tubeLoadButton.show()
            self.tubeSaveButton.show()
            self.tubeButton.setText("Open X-Ray Tube Setup")

    def loadButtonClicked(self):
        if self.inputDir is None:
            if self.inputDir is not None:
                self.inputDir = self.outputDir
            else:
                self.inputDir = PyMcaDirs.inputDir
        wdir = self.inputDir
        if not os.path.exists(wdir):
            wdir = os.getcwd()
        filename = PyMcaFileDialogs.getFileList(self,
                            filetypelist=["Energy table files (*.csv)"],
                            mode="OPEN",
                            message="Choose energy table file",
                            currentdir=wdir,
                            single=True)
        if len(filename):
            filename = qt.safe_str(filename[0])
            if len(filename):
                try:
                    self.loadEnergyTableParameters(filename)
                    self.inputDir = os.path.dirname(filename)
                    PyMcaDirs.inputDir = self.inputDir
                except Exception:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Error loading energy table: %s" % (sys.exc_info()[1]))
                    msg.exec()

    def loadEnergyTableParameters(self, filename):
        if sys.platform == "win32" and (sys.version < "3.0.0"):
            ffile = open(filename, "rb")
        else:
            ffile = open(filename, "r")
        lines = ffile.read()
        ffile.close()
        lines = lines.replace("\r","\n")
        lines = lines.replace('\n\n',"\n")
        lines = lines.replace(";","  ")
        lines = lines.replace("\t","  ")
        lines = lines.replace('"',"")
        lines = lines.split("\n")
        if (len(lines) == 1) or\
           ((len(lines) == 2) and (len(lines[1])==0)):
            #clear table
            ddict={}
            ddict['energylist'] = [None]
            ddict['weightlist'] = [1.0]
            ddict['flaglist'] = [1]
            ddict['scatterlist'] = [1]
        else:
            ddict={}
            ddict['energylist'] = []
            ddict['weightlist'] = []
            ddict['flaglist'] = []
            ddict['scatterlist'] = []
            for i in range(1, len(lines)):
                line = lines[i]
                if not len(line):
                    continue
                ene, weight, useflag, scatterflag = map(float,
                                                        line.split("  "))
                if ene > 0:
                    ddict['energylist'].append(ene)
                else:
                    ddict['energylist'].append(None)
                ddict['weightlist'].append(weight)
                ddict['flaglist'].append(int(useflag))
                ddict['scatterlist'].append(int(scatterflag))
        energylist, weightlist, flaglist, scatterlist = self.table.getParameters()
        lold = len(energylist)
        lnew = len(ddict['energylist'])
        if lold > lnew:
            energylist = [None] * lold
            weightlist = [0.0]  * lold
            flaglist = [0] * lold
            scatterlist = [0] * lold
            energylist[0:lnew] = ddict['energylist'][0:lnew]
            weightlist[0:lnew] = ddict['weightlist'][0:lnew]
            flaglist[0:lnew] = ddict['flaglist'][0:lnew]
            scatterlist[0:lnew] = ddict['scatterlist'][0:lnew]
            self.table.setParameters(energylist,
                                     weightlist,
                                     flaglist,
                                     scatterlist)
        else:
            self.table.setParameters(ddict["energylist"],
                                 ddict["weightlist"],
                                 ddict["flaglist"],
                                 ddict["scatterlist"])

    def saveButtonClicked(self):
        energylist, weightlist, flaglist, scatterlist = self.table.getParameters()
        if self.outputDir is None:
            if self.inputDir is not None:
                self.outputDir = self.inputDir
            else:
                self.outputDir = PyMcaDirs.outputDir
        wdir = self.outputDir
        format_list = ['";"-separated CSV *.csv',
                       '","-separated CSV *.csv',
                       '"tab"-separated CSV *.csv']
        if self.outputFilter is None:
            self.outputFilter = format_list[0]
        outfile, filterused = PyMcaFileDialogs.getFileList(self,
                                        filetypelist=format_list,                                          
                                        mode="SAVE",
                                        message="Output File Selection",
                                        currentdir=wdir,
                                        currentfilter=self.outputFilter,
                                        getfilter=True,
                                        single=True)
        if len(outfile):
            outputFile = qt.safe_str(outfile[0])
        else:
            return
        self.outputFilter = qt.safe_str(filterused)
        filterused = self.outputFilter.split()
        try:
            self.outputDir  = os.path.dirname(outputFile)
            PyMcaDirs.outputDir = os.path.dirname(outputFile)
        except Exception:
            self.outputDir  = "."
        if not outputFile.endswith('.csv'):
            outputFile += '.csv'
        #always overwrite
        if os.path.exists(outputFile):
            os.remove(outputFile)
        try:
            if sys.version < "3.0.0":
                ffile=open(outputFile,'wb')
            else:
                ffile=open(outputFile,'w')
        except IOError:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Input Output Error: %s" % (sys.exc_info()[1]))
            msg.exec()
            return
        if "," in filterused[0]:
            csv = ","
        elif ";" in filterused[0]:
            csv = ";"
        else:
            csv = "\t"

        ffile.write('"energy"%s"weight"%s"flag"%s"scatter"\n' % (csv, csv, csv))
        #write the scatter lines in first instance
        alreadysaved = []
        for i in range(len(energylist)):
            if (energylist[i] is not None) and \
               (scatterlist[i] == 1):
                ffile.write("%f%s%f%s%d%s%d\n" % \
                   (energylist[i], csv,
                    weightlist[i], csv,
                    flaglist[i], csv,
                    scatterlist[i]))
                alreadysaved.append(i)

        for i in range(len(energylist)):
            if energylist[i] is not None:
                if i not in alreadysaved:
                    ffile.write("%f%s%f%s%d%s%d\n" % \
                       (energylist[i], csv,
                        weightlist[i], csv,
                        flaglist[i], csv,
                        scatterlist[i]))
        ffile.close()

    def __tubeUpdated(self, d):
        if    self.__calculating:return
        else: self.__calculating = 1
        self.table.setParameters(d["energylist"],
                                 d["weightlist"],
                                 d["flaglist"],
                                 d["scatterlist"])
        self.__calculating = 0
        self.tubeButtonClicked()

class EnergyTable(QTable):
    sigEnergyTableSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="Energy Table",
                     energylist=None, weightlist=None, flaglist=None,offset=None,scatterlist=None,scattercolor=None):
        QTable.__init__(self, parent)
        if energylist is  None:energylist=[]
        if weightlist is  None:weightlist  =[]
        if flaglist   is  None:flaglist  =[]
        if scatterlist   is  None:scatterlist  = []
        if scattercolor is None: 
            scattercolor = qt.QColor(255, 20, 147)
        if offset is None:offset = 0
        self.energyList  = energylist
        self.weightList  = weightlist
        self.flagList    = flaglist
        self.offset      = offset
        self.scatterList = scatterlist
        self._scatterColor = scattercolor
        try:
            self._textBackgroundColor = \
                qt.QApplication.instance().palette().color(qt.QPalette.Base)
        except Exception:
            _logger.warning("Cannot obtain text background color")
            self._textBackgroundColor = qt.QColor(255, 255, 255)

        self.verticalHeader().hide()
        self.dataColumns = 30
        _logger.debug("margin\n"
                      "frame shape\n"
                      "selection mode\n"
                      "focus style\n"
                      "all of them missing")
        self.setColumnCount(3 * self.dataColumns)

        labels = []
        for i in range(self.dataColumns):
            labels.append("Use")
            labels.append("Energy")
            labels.append("Weight")
        _logger.debug("margin to adjust")
        _logger.debug("focus style")
        self.setFrameShape(qt.QTableWidget.NoFrame)
        self.setSelectionMode(qt.QTableWidget.NoSelection)
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],qt.QTableWidgetItem.Type)
            self.setHorizontalHeaderItem(i,item)

        self.__rows = 20
        self.__build(self.dataColumns * 20)
        self.__disconnected = False
        for i in range(self.dataColumns):
            _logger.debug("column adjustment missing")
        self.cellChanged[int, int].connect(self.mySlot)
        if hasattr(self, "cellDoubleClicked"):
            self.cellDoubleClicked[int, int].connect(self._doubleClickSlot)

    def _itemSlot(self, *var):
        self.mySlot(self.currentRow(), self.currentColumn())

    def _doubleClickSlot(self, row, col):
        _logger.debug("cell %d %d double clicked" % (row, col))
        if col // self.dataColumns:
            _logger.debug("Not an Energy column")
            return
        item = self.cellWidget(row, col)
        if item is None:
            return
        oldcolor = item.color
        if oldcolor != self._scatterColor:
            item.setColor(self._scatterColor)
        else:
            item.setColor(self._textBackgroundColor)
        item.repaint(item.rect())
        self.cellChanged.emit(row, col)

    def __build(self,nrows=None):
        #self.setNumRows(int(nrows/2))
        if nrows is None: nrows = self.__rows *self.dataColumns
        self.setRowCount(int(nrows/self.dataColumns))
        rheight = self.horizontalHeader().sizeHint().height()
        for idx in range(self.rowCount()):
            self.setRowHeight(idx, rheight)

        coloffset = 0
        rowoffset = 0
        for idx in range(nrows):
            text = "Energy %3d" % (idx)
            if idx >= (nrows // self.dataColumns):
                rowoffset= (-int(idx/self.__rows))*(nrows //self.dataColumns)
                coloffset=  3*int(idx/self.__rows)
            r = idx + rowoffset
            color = self._textBackgroundColor
            if len(self.scatterList):
                if idx < len(self.scatterList):
                    if (self.scatterList[idx] is not None)and \
                       (self.scatterList[idx] != "None"):
                        if self.scatterList[idx]:
                            color = self._scatterColor
            elif idx == 0:
                color = self._scatterColor
            item = self.cellWidget(r, 0+coloffset)
            if item is None:
                item= ColorQTableItem(self, text, color)
                self.setCellWidget(r, 0+coloffset, item)
                item.stateChanged[int].connect(self._itemSlot)
                if hasattr(item, "setToolTip"):
                    item.setToolTip("Double click on empty space at the end to toggle inclusion as scatter peak (different color)")
            else:
                item.setText(text)
            oldcolor = item.color
            if color != oldcolor:
                item.setColor(color)
                item.repaint(item.rect())
            if idx < len(self.energyList):
                item.setChecked(self.flagList[idx])
                if (self.energyList[idx] is not None) and \
                   (self.energyList[idx] != "None"):
                    self.setText(r, 1+coloffset,
                                 "%f" % self.energyList[idx])
                else:
                    self.setText(r, 1+coloffset,"")
            else:
                item.setChecked(False)
                self.setText(r, 1+coloffset,"")
            if idx < len(self.weightList):
                self.setText(r, 2+coloffset,"%.8g" % self.weightList[idx])
            else:
                self.setText(r, 2+coloffset,"")

    def setParameters(self, energylist, weightlist, flaglist, scatterlist=None):
        if isinstance(energylist, numpy.ndarray):
            self.energyList = energylist.tolist()
        elif type(energylist) != type([]):
            self.energyList = [energylist]
        else:
            self.energyList = energylist

        if isinstance(weightlist, numpy.ndarray):
            self.weightList = weightlist.tolist()
        elif type(weightlist) != type([]):
            self.energyList = [weightlist]
        else:
            self.weightList = weightlist

        if isinstance(flaglist, numpy.ndarray):
            self.flagList = flaglist.tolist()
        elif type(flaglist) != type([]):
            self.flagList = [flaglist]
        else:
            self.flagList = flaglist


        if scatterlist is None:
            scatterlist = numpy.zeros(len(self.energyList),
                                      dtype=numpy.int32).tolist()
            scatterlist[0] = 1
        if isinstance(scatterlist, numpy.ndarray):
            self.scatterList=scatterlist.tolist()
        elif type(scatterlist) != type([]):
            self.scatterList=[scatterlist]
        else:
            self.scatterList =scatterlist
        self.__fillTable()

    def getParameters(self):
        nrows = self.rowCount() * self.dataColumns
        coloffset   = 0
        rowoffset   = 0
        energyList  = []
        weightList  = []
        flagList    = []
        scatterList = []
        for idx in range(nrows):
            if idx >= (nrows//self.dataColumns):
                rowoffset= (-int(idx/self.__rows)) * (nrows//self.dataColumns)
                coloffset=  3 * int(idx/self.__rows)
            r = idx + rowoffset
            item = self.cellWidget(r,0+coloffset)
            if item is None:
                #this should never happen
                continue
            else:
                energyflag = int(item.isChecked())
            if item.color != self._scatterColor:
                scatterflag = 0
            else:
                scatterflag = 1
            text = str(self.text(r,1+coloffset))
            text=text.replace(" ","")
            if len(text):
                try:
                    energy = float(text)
                except Exception:
                    energyflag = 0
                    energy = None
            else:
                energyflag = 0
                energy = None
            text = str(self.text(r,2+coloffset))
            text=text.replace(" ","")
            if len(text):
                try:
                    energyweight = float(text)
                except Exception:
                    energyflag  = 0
                    energyweight= 0.0
            else:
                energyflag = 0
                energyweight = 0.0
            energyList.append(energy)
            weightList.append(energyweight)
            flagList.append(int(energyflag))
            scatterList.append(scatterflag)
        return energyList, weightList, flagList, scatterList

    def __fillTable(self):
        self.__disconnected = True
        try:
            self.__build(max(self.__rows*self.dataColumns,len(self.energyList)))
            for i in range(self.dataColumns):
                _logger.debug("column adjustment missing")
        except Exception:
            self.__disconnected = False
            raise
        self.__disconnected = False
        ddict = self._getDict()
        if ddict != {}:
            ddict['event'] = "TableFilled"
            ddict['row']   = 0
            ddict['col']   = 0
            self.sigEnergyTableSignal.emit(ddict)

    def mySlot(self,row,col):
        if self.__disconnected:return
        _logger.debug("Value changed row = %d col = %d", row, col)
        _logger.debug("Text = %s", self.text(row, col))
        if (col % 3) != 0:
            try:
                s = str(self.text(row, col))
                s=s.replace(" ","")
                if len(s):
                    float(s)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Float")
                msg.exec()
                return
        ddict = self._getDict()
        if ddict != {}:
            ddict['event'] = "ValueChanged"
            ddict['row']   = row
            ddict['col']   = col
            self.sigEnergyTableSignal.emit(ddict)

    def text(self, row, col):
        if (col % 3) != 0:
            item = self.item(row , col)
            if item is not None:
                return item.text()
            else:
                return ''

    def setText(self, row, col, text):
        #ncol = self.columnCount()
        if (col % 3) != 0:
            item = self.item(row, col)
            if item is None:
                item = qt.QTableWidgetItem(text,
                                           qt.QTableWidgetItem.Type)
                self.setItem(row, col, item)
            else:
                item.setText(text)
        else:
            _logger.debug("checkbox can be called?")
            pass

    def _getDict(self):
        ddict ={}
        n = self.rowCount()
        ddict['energy'] = []
        ddict['rate']   = []
        ddict['flag']   = []
        ddict['scatterflag']   = []
        for i in range(n * self.dataColumns):
                if i >= (n*self.__rows/self.dataColumns):
                    rowoffset= (-int(i/self.__rows))*(self.__rows)
                    r = i + rowoffset
                    coffset=  3*int(i/self.__rows)
                else:
                    r = i
                    coffset= 0
                try:
                    s = str(self.text(r, 1+coffset))
                    s=s.replace(" ","")
                    if len(s):
                        ene=float(s)
                        selfitem = self.cellWidget(r, 0+coffset)
                        if selfitem.isChecked():
                            flag = 1
                        else:
                            flag = 0
                        if selfitem.color == self._scatterColor:
                            scatterflag = 1
                        else:
                            scatterflag = 0
                        s = str(self.text(r, 2+coffset))
                        s=s.replace(" ","")
                        if len(s):
                            rate = float(s)
                            ddict['flag'].append(flag)
                            ddict['energy'].append(ene)
                            ddict['rate'].append(rate)
                            ddict['scatterflag'].append(scatterflag)
                except Exception:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("EnergyTable: Error on energy %d" % i)
                    msg.exec()
                    return {}
        return ddict

class ColorQTableItem(qt.QCheckBox):
         def __init__(self, table, text, color=None, bold=0):
            qt.QCheckBox.__init__(self, table)
            try:
                _palette = qt.QApplication.instance().palette()
                self._textColor = _palette.color(qt.QPalette.WindowText)
                self._backgroundColor = _palette.color(qt.QPalette.Base)
            except Exception:
                self._textColor = qt.QColor(qt.Qt.black)                
                self._backgroundColor = qt.QColor(255, 255, 255)
            self._selectedTextColor = qt.QColor(qt.Qt.black)
            self._selectedBackgroundColor = qt.QColor(255, 20, 147)

            if color is None:
                color = self._backgroundColor
            self.setColor(color)
            self.bold  = bold
            self.setText(text)
            #this is one critical line
            self.setAutoFillBackground(1)

         def setColor(self, color):
             self.color = color
             if color == self._backgroundColor:
                 self.setStyleSheet("color: %s; background-color: %s" % \
                     (self._textColor.name(), self._backgroundColor.name()))
             else:
                 self.setStyleSheet("color: %s; background-color: %s" % \
                     (self._selectedTextColor.name(),  self._selectedBackgroundColor.name()))

         def paintEvent(self, painter):
            #this is the other (self.palette() is not appropriate)
            palette = qt.QPalette()
            role = self.backgroundRole()
            palette.setColor(role, self.color)
            self.setPalette(palette)
            return qt.QCheckBox.paintEvent(self, painter)

def main(args):
    app=qt.QApplication(args)
    #tab = AttenuatorsTableWidget(None)
    def dummy(ddict):
        print("dict =",ddict)
    tab = EnergyTable(None)
    energy = numpy.arange(100.).astype(numpy.float64)+ 1.5
    weight = numpy.ones(len(energy), numpy.float64)
    flag  = numpy.zeros(len(energy), dtype=numpy.int32).tolist()
    scatterlist = numpy.zeros(len(energy)).astype(numpy.int8)
    scatterlist[0:10] = 1
    tab.setParameters(energy, weight, flag, scatterlist)
    tab.sigEnergyTableSignal.connect(dummy)
    tab.show()
    app.exec()

if __name__=="__main__":
    main(sys.argv)
