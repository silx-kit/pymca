#/*##########################################################################
# Copyright (C) 2004-2014 V.A. Sole, European Synchrotron Radiation Facility
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
from PyMca5.PyMcaGui import PyMcaQt as qt
DEBUG = 0

class RGBCorrelatorTable(qt.QTableWidget):
    sigRGBCorrelatorTableSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.elementList      = []
        self.rSelection   = []
        self.gSelection   = []
        self.bSelection = []
        labels = ['Element', 'R', 'G', 'B', 'Data Min', "Data Max"]
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[i])
            self.setHorizontalHeaderItem(i,item)
        rheight = self.horizontalHeader().sizeHint().height()
        self.setMinimumHeight(5*rheight)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)

    def build(self, elementlist):
        self.elementList = elementlist
        n = len(elementlist)
        self.setRowCount(n)
        if n > 0:
            rheight = self.horizontalHeader().sizeHint().height()
            for i in range(n):
                self.setRowHeight(i, rheight)
                self._addLine(i, elementlist[i])

        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)

    def _addLine(self, i, cntlabel):
        #the counter name
        item = self.item(i, 0)
        if item is None:
            item = qt.QTableWidgetItem(cntlabel,
                                       qt.QTableWidgetItem.Type)
            item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.setItem(i, 0, item)
        else:
            item.setText(cntlabel)
        #item is enabled and selectable
        item.setFlags(qt.Qt.ItemIsEnabled | qt.Qt.ItemIsSelectable)

        #the checkboxes
        for j in range(1, 4, 1):
            widget = self.cellWidget(i, j)
            if widget is None:
                widget = CheckBoxItem(self, i, j)
                self.setCellWidget(i, j, widget)
                widget.sigCheckBoxItemSignal.connect(self._mySlot)
            else:
                pass

    def _mySlot(self, ddict):
        row = ddict["row"]
        col = ddict["col"]
        if col == 1:
            if ddict["state"]:
                if row not in self.rSelection:
                    self.rSelection.append(row)
            else:
                if row in self.rSelection:
                    del self.rSelection[self.rSelection.index(row)]
            if len(self.rSelection) > 1:
                self.rSelection = self.rSelection[-1:]
        if col == 2:
            if ddict["state"]:
                if row not in self.gSelection:
                    self.gSelection.append(row)
            else:
                if row in self.gSelection:
                    del self.gSelection[self.gSelection.index(row)]
            if len(self.gSelection) > 1:
                self.gSelection = self.gSelection[-1:]
        if col == 3:
            if ddict["state"]:
                if row not in self.bSelection:
                    self.bSelection.append(row)
            else:
                if row in self.bSelection:
                    del self.bSelection[self.bSelection.index(row)]
            if len(self.bSelection) > 1:
                self.bSelection = self.bSelection[-1:]
        #I should check if there is a change ...
        self._update()

    def _emitSignal(self):
        ddict = self.getElementSelection()
        ddict['event'] = "updated"
        self.sigRGBCorrelatorTableSignal.emit(ddict)

    def _update(self):
        for i in range(self.rowCount()):
            j = 1
            widget = self.cellWidget(i, j)
            if i in self.rSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
            else:
                if widget.isChecked():
                    widget.setChecked(False)
            j = 2
            widget = self.cellWidget(i, j)
            if i in self.gSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
            else:
                if widget.isChecked():
                    widget.setChecked(False)
            j = 3
            widget = self.cellWidget(i, j)
            if i in self.bSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
            else:
                if widget.isChecked():
                    widget.setChecked(False)
        self._emitSignal()

    def getElementSelection(self):
        ddict = {}
        ddict['elementlist'] = self.elementList * 1
        n = len(self.elementList)
        if n == 0:
            self.rSelection = []
            self.gSelection = []
            self.bSelection = []
        if len(self.rSelection):
            if self.rSelection[0] >= n:
                self.rSelection = []
        if len(self.gSelection):
            if self.gSelection[0] >= n:
                self.gSelection = []
        if len(self.bSelection):
            if self.bSelection[0] >= n:
                self.bSelection = []
        ddict['r'] = self.rSelection * 1
        ddict['g'] = self.gSelection * 1
        ddict['b'] = self.bSelection * 1
        return ddict

    def setElementSelection(self, ddict):
        keys = ddict.keys()
        if 'elementlist' in keys: elementlist = ddict['elementlist']
        else: elementlist = self.elementList * 1

        if 'r' in keys: x = ddict['r']
        else: x = []

        if 'g' in keys: y = ddict['g']
        else: y = []

        if 'b' in keys: monitor = ddict['b']
        else: monitor = []

        self.rSelection = []
        for item in x:
            if item < len(elementlist):
                counter = elementlist[item]
                self.rSelection.append(item)

        self.gSelection = []
        for item in y:
            if item < len(elementlist):
                counter = elementlist[item]
                if counter in self.elementList:
                    self.gSelection.append(self.elementList.index(counter))
        self.bSelection = []
        for item in monitor:
            if item < len(elementlist):
                counter = elementlist[item]
                if counter in self.elementList:
                    self.bSelection.append(self.elementList.index(counter))
        self._update()


class CheckBoxItem(qt.QCheckBox):
    sigCheckBoxItemSignal = qt.pyqtSignal(object)
    def __init__(self, parent, row, col):
        qt.QCheckBox.__init__(self, parent)
        self.__row = row
        self.__col = col
        self.clicked[bool].connect(self._mySignal)

    def _mySignal(self, value):
        ddict = {}
        ddict["event"] = "clicked"
        ddict["state"] = value
        ddict["row"] = self.__row * 1
        ddict["col"] = self.__col * 1
        self.sigCheckBoxItemSignal.emit(ddict)

def main():
    app = qt.QApplication([])
    def slot(ddict):
        print("received dict = ", ddict)
    tab = RGBCorrelatorTable()
    tab.sigRGBCorrelatorTableSignal.connect(slot)

    tab.build(["Cnt1", "Cnt2", "Cnt3"])
    tab.setElementSelection({'r':[1], 'g':[4], 'elementlist':["dummy", "Ca K", "Fe K", "Pb M", "U l"]})
    tab.show()
    app.exec()

if __name__ == "__main__":
    main()

