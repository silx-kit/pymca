#/*##########################################################################
# Copyright (C) 2018 V.A. Sole, European Synchrotron Radiation Facility
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
import posixpath
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
safe_str = qt.safe_str

_logger = logging.getLogger(__name__)


class McaSelectionType(qt.QWidget):
    sigMcaSelectionTypeSignal = qt.pyqtSignal(object)
    
    def __init__(self, parent=None,row=0, column=0):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self._row = row
        self._column = column
        self._selection = qt.QCheckBox(self)
        self._selectionType = qt.QComboBox(self)
        self._optionsList = ["sum", "avg"]
        for option in self._optionsList:
            self._selectionType.addItem(option[0].upper() + option[1:])
        self._selectionType.setCurrentIndex(self._optionsList.index("avg"))
        self.mainLayout.addWidget(self._selection)
        self.mainLayout.addWidget(self._selectionType)
        self._selection.clicked.connect(self._mySignal)
        self._selectionType.activated[int].connect(self._preSignal)

    def setChecked(self, value):
        if value:
            self._selection.setChecked(True)
        else:
            self._selection.setChecked(False)

    def isChecked(self):
        return self._selection.isChecked()

    def currentText(self):
        return self._selectionType.currentText()

    def setCurrentText(self, text):
        text = text.lower()
        if text in ["average", "avg"]:
            text = "avg"
        if text in self._optionsList:
            idx = self._optionsList.index(text)
            if self._selectionType.currentIndex() != idx:
                self._selectionType.setCurrentIndex(idx)
        else:
            raise ValueError("Received option %s not among supported options")

    def _preSignal(self, value):
        if self.isChecked():
            # no need to emit anything because it was not selected
            self._mySignal(value)

    def _mySignal(self, value=None):
        ddict = {}
        ddict["event"] = "clicked"
        ddict["state"] = self._selection.isChecked()
        if value is None:
            idx = self._selectionType.currentIndex()
        else:
            idx = value
        ddict["type"] = self._optionsList[idx]
        ddict["row"] = self._row * 1
        ddict["column"] = self._column * 1
        self.sigMcaSelectionTypeSignal.emit(ddict)

class HDF5McaTable(qt.QTableWidget):
    sigHDF5McaTableSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.aliasList = []
        self.mcaList = []
        self.mcaSelection = []
        self.mcaSelectionType = []
        labels = ['Dataset', 'Selection', 'Alias']
        self._aliasColumn = labels.index('Alias')
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[i])
            self.setHorizontalHeaderItem(i,item)
        self.cellChanged[int, int].connect(self._aliasSlot)

    def build(self, cntlist, aliaslist=None):
        self.__building = True
        if aliaslist is None:
            aliaslist = []
            for item in cntlist:
                aliaslist.append(posixpath.basename(item))
        if len(cntlist) != len(aliaslist):
            raise ValueError("Alias list and counter list must have same length")
        self.mcaList = cntlist
        self.aliasList = aliaslist
        n = len(cntlist)
        self.setRowCount(n)
        if n > 0:
            self.setRowCount(n)
            rheight = self.horizontalHeader().sizeHint().height()
            # check if we need the complete description
            useFullPath = []
            for i in range(n):
                iName = posixpath.basename(cntlist[i])
                for j in range(i+1, n):
                    if posixpath.basename(cntlist[j]) == iName:
                        if i not in useFullPath:
                            useFullPath.append(i)
                        if j not in useFullPath:
                            useFullPath.append(j)
            for i in range(n):
                self.setRowHeight(i, rheight)
                if i in useFullPath:
                    self.__addLine(i, cntlist[i])
                else:
                    self.__addLine(i, posixpath.basename(cntlist[i]))
                for j in range(1, 2):
                    widget = self.cellWidget(i, j)
                    widget.setEnabled(True)
        else:
            self.setRowCount(0)

        self.resizeColumnToContents(1)
        #self.resizeColumnToContents(2)
        self.__building = False

    def __addLine(self, i, cntlabel):
        #the counter name
        j = 0
        item = self.item(i, 0)
        if item is None:
            item = qt.QTableWidgetItem(cntlabel,
                                       qt.QTableWidgetItem.Type)
            item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.setItem(i, 0, item)
        else:
            item.setText(cntlabel)

        #item is just enabled (not selectable)
        item.setFlags(qt.Qt.ItemIsEnabled)

        # the selection type
        j += 1
        widget = self.cellWidget(i, j)
        if widget is None:
            widget = McaSelectionType(self, i, j)
            self.setCellWidget(i, j, widget)
            widget.sigMcaSelectionTypeSignal.connect(self._mySlot)
        else:
            pass

        #the alias
        j += 1
        item = self.item(i, j)
        alias = self.aliasList[i]
        if item is None:
            item = qt.QTableWidgetItem(alias,
                                       qt.QTableWidgetItem.Type)
            item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.setItem(i, j, item)
        else:
            item.setText(alias)

    def _aliasSlot(self, row, col):
        if self.__building:
            return
        if col != self._aliasColumn:
            return
        item = self.item(row, col)
        self.aliasList[row] = safe_str(item.text())
        self._update(row, col)

    def _mySlot(self, ddict):
        _logger.debug("HDF5McaTable._mySlot %s", ddict)
        row = ddict["row"]
        col = ddict["column"]
        if col == 1:
            if ddict["state"]:
                if row not in self.mcaSelection:
                    self.mcaSelection.append(row)
                    self.mcaSelectionType.append(ddict["type"])
                else:
                    idx = self.mcaSelection.index(row)
                    self.mcaSelectionType[idx] = ddict["type"]
            else:
                if row in self.mcaSelection:
                    idx = self.mcaSelection.index(row)
                    del self.mcaSelection[idx]
                    del self.mcaSelectionType[idx]
        self._update(row, col)

    def _update(self, row=None, column=None):
        for i in range(self.rowCount()):
            j = 1
            widget = self.cellWidget(i, j)
            assert len(self.mcaSelection) == len(self.mcaSelectionType)
            if i in self.mcaSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
                    widget.setCurrentText(self.mcaSelectionType[i])
            else:
                if widget.isChecked():
                    widget.setChecked(False)            
        ddict = {}
        ddict["event"] = "updated"
        ddict["row"] = row
        ddict["column"] = column
        if row is not None and column is not None:
            self.sigHDF5McaTableSignal.emit(ddict)

    def getMcaSelection(self):
        ddict = {}
        ddict['mcalist'] = self.mcaList * 1
        ddict['aliaslist'] = self.aliasList * 1
        ddict['selectionindex'] = self.mcaSelection * 1
        ddict['selectiontype'] = self.mcaSelectionType * 1
        return ddict

    def setMcaSelection(self, ddict):
        keys = ddict.keys()
        if 'mcalist' in keys:
            mcalist = ddict['mcalist']
        else:
            mcalist = self.mcaList * 1

        # no selection based on aliaslist or counterlist (yet?)
        if 0:
            if 'aliaslist' in keys:
                aliaslist = ddict['aliaslist']
            elif len(self.aliasList) == len(cntlist):
                aliaslist = self.aliasList * 1
            else:
                aliaslist = self.mcaList * 1

        if 'selectionindex' in keys:
            selection = ddict['selectionindex']
        else:
            selection = []

        if 'selectiontype' in keys:
            selectionType = ddict['selectiontye']
        else:
            selectionType = []

        assert len(selection) == len(selectionType)

        self.mcaSelection = []
        self.mcaSelectionType = []
        for i in range(len(selection)):
            idx = selection[idx]
            if idx < len(mcalist):
                self.mcaSelection.append(selection[i])
                self.mcaSelectionType.append(selectionType[i])
        self._update()

def main():
    app = qt.QApplication([])
    tab = HDF5McaTable()
    tab.build(["Cnt1", "Cnt2", "Cnt3"])    
    #tab.setCounterSelection({'x':[1, 2], 'y':[4],
    #                    'cntlist':["dummy", "Cnt0", "Cnt1", "Cnt2", "Cnt3"]})
    tab.show()
    def slot(ddict):
        print("Received = ", ddict)
    tab.sigHDF5McaTableSignal.connect(slot)
    app.exec_()

if __name__ == "__main__":
    main()

