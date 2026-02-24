#/*##########################################################################
# Copyright (C) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import posixpath
import logging
import re
from PyMca5.PyMcaGui import PyMcaQt as qt
safe_str = qt.safe_str

_logger = logging.getLogger(__name__)

class CntSelectionType(qt.QWidget):
    sigCntSelectionTypeSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, row=0, column=0, shape=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self._row = row
        self._column = column
        self._selector = False
        self._selection = qt.QCheckBox(self)
        self._selection.setText(" ")
        self._selectionType = qt.QComboBox(self)
        self._optionsList = ["full", "index"]
        if shape:
            if len(shape) > 2:
                self._optionsList += ["slice"]
        for option in self._optionsList:
            self._selectionType.addItem(option[0].upper() + option[1:])
        self._selectionType.setCurrentIndex(self._optionsList.index("full"))
        self.mainLayout.addWidget(self._selection)
        self.mainLayout.addWidget(self._selectionType)
        self._selection.clicked.connect(self._mySignal)
        self._selectionType.activated[int].connect(self._preSignal)
        self._sliceList = []

        self._index = qt.QSpinBox(self)
        if shape in [None, "None"]:
            shape = None
            maximum = 0
        elif len(shape) in [0, 1]:
            maximum = 0
        else:
            maximum = 1
            for dim in shape[:-1]:
                maximum *= dim
        self._index.setMinimum(0)
        if maximum:
            self._index.setMaximum(min(maximum,2**31)  - 1)
        else:
            self._index.setMaximum(0)
        self._index.setValue(0)
        self.mainLayout.addWidget(self._index)
        if self._selector:
            self._selectorButton = qt.QPushButton(self)
            self._selectorButton.setText("Browser")
            self.mainLayout.addWidget(self._selectorButton)
        self._index.hide()
        # textChanged or editingFinished ?
        self._index.valueChanged[int].connect(self._indexValueChangedSlot)
        if self._selector:
            self._selectorButton.hide()
            self._selectorButton.clicked.connect(self._selectorButtonClickedSlot)
        if shape and len(shape) > 2:
            self._sliceList = []
            for i in range(len(shape) - 1):
                spinbox = qt.QSpinBox(self)
                spinbox.setMinimum(0)
                if shape[i] > 0:
                    spinbox.setMaximum(shape[i] - 1)
                else:
                    spinbox.setMaximum(0)
                spinbox.setValue(0)
                self.mainLayout.addWidget(spinbox)
                spinbox.hide()
                spinbox.valueChanged[int].connect(self._sliceChangedSlot)
                self._sliceList.append(spinbox)
        if shape is None or len(shape) < 2:
            self._selectionType.hide()
        elif len(shape) == 2:
            if shape[0] == 1:
                self._selectionType.hide()

    def setChecked(self, value):
        if value:
            self._selection.setChecked(True)
        else:
            self._selection.setChecked(False)

    def isChecked(self):
        return self._selection.isChecked()

    def setText(self, text):
        self._selection.setText(text)

    def currentText(self):
        idx = self._selectionType.currentIndex()
        text = self._optionsList[idx]
        if text == "index":
            text += " %d" % self._index.value()
        if text == "slice":
            for i in range(len(self._sliceList)):
                if i == 0:
                    text += " [%d" % self._sliceList[0].value()
                else:
                    text += ", %d" % self._sliceList[1].value()
            text += ", :]"
        return text

    def currentIndex(self):
        if hasattr(self, "_index"):
            return self._index.value()
        else:
            return 0

    def setCurrentText(self, text):
        text = text.lower()
        if text in ["full", ""]:
            text = "full"
        elif text.startswith("index"):
            exp = re.compile(r'(-?[0-9]+\.?[0-9]*)')
            items = exp.findall(text)
            if len(items) not in [0, 1]:
                raise ValueError("Cannot retieve index from %s" % text)
            elif len(items) == 0:
                value = 0
            else:
                value = 1
            self._index.setValue(value)
        elif text.startswith("slice"):
            exp = re.compile(r'(-?[0-9]+\.?[0-9]*)')
            items = exp.findall(text)
            if len(items) != len(self._sliceList):
                raise IndexError("Received slice %s does not match length of %" % (text, len(self._sliceList)))
            for w in self._sliceList:
                w.setValue(int(items[0]))
        else:
            raise ValueError("Received option %s not among supported options" % text)

    def _indexTextChangedSlot(self, text):
        _logger.debug("Text changed %s" % text)
        self._mySignal()

    def _indexValueChangedSlot(self, value):
        _logger.debug("Value changed %s" % value)
        self._mySignal()

    def _sliceChangedSlot(self, value):
        _logger.debug("Value changed %s" % value)
        self._mySignal()

    def _selectorButtonClickedSlot(self):
        _logger.debug("selectorButtonClicked")
        self._mySignal(event="selector")

    def _preSignal(self, value):
        if self._optionsList[value] == "index":
            self._index.show()
            if self._selector:
                self._selectorButton.show()
        else:
            self._index.hide()
            if self._selector:
                self._selectorButton.hide()
        if self._optionsList[value] == "slice":
            for w in self._sliceList:
                w.show()
            if self._selector:
                self._selectorButton.show()
        else:
            for w in self._sliceList:
                w.hide()
            if self._selector:
                self._selectorButton.hide()
        self._mySignal()

    def _mySignal(self, value=None, event=None):
        if event is None:
            event = "clicked"
        ddict = {}
        ddict["event"] = event
        ddict["state"] = self._selection.isChecked()
        ddict["type"] = self.currentText()
        ddict["row"] = self._row * 1
        ddict["column"] = self._column * 1
        self.sigCntSelectionTypeSignal.emit(ddict)



class HDF5CounterTable(qt.QTableWidget):

    sigHDF5CounterTableSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.cntList      = []
        self.aliasList    = []
        self.shapeList    = []
        self.mcaList      = []
        self.xSelection   = []
        self.ySelection   = []
        self.yrightSelection = []
        self.monSelection = []
        self.xSelectionType   = []
        self.ySelectionType   = []
        self.yrightSelectionType = []
        self.monSelectionType = []
        self.__monitorMultipleMode = False
        self.__oldSelection = self.getCounterSelection()
        self.__is3DEnabled = False
        self.__is2DEnabled = False
        labels = ['Dataset', 'Axes', 'Signals', 'Signals R', 'Monitor', 'Alias']
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[i])
            self.setHorizontalHeaderItem(i,item)

        # Enable custom context menu on horizontal header for Monitor column
        self.horizontalHeader().setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._headerContextMenu)

        """
        #the cell is not the same as the check box
        #but I wonder about the checkboxes being destroyed
        """
        self.cellChanged[int, int].connect(self._aliasSlot)

    def build(self, cntlist, aliaslist=None, selection=None, shapelist=None):
        _logger.debug("build cntlist = %s aliaslist = %s shapelist = %s" % (cntlist, aliaslist, shapelist))
        self.__building = True
        if selection is None:
            if len(cntlist):
                if len(self.cntList):
                    self.__oldSelection = self.getCounterSelection()
        else:
            _logger.info("received selection %s", selection)
            self.__oldSelection = selection
        if aliaslist is None:
            aliaslist = []
            for item in cntlist:
                aliaslist.append(posixpath.basename(item))
        if len(cntlist) != len(aliaslist):
            raise ValueError("Alias list and counter list must have same length")
        self.cntList = cntlist
        self.aliasList = aliaslist
        self.shapeList = shapelist
        self.setRowCount(0)
        n = len(cntlist)
        if self.shapeList is None:
            self.shapeList = (None,) * n
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
                    self.__addLine(i, cntlist[i], shape=self.shapeList[i])
                else:
                    self.__addLine(i, posixpath.basename(cntlist[i]), shape=self.shapeList[i])
                for j in range(1, 5, 1):
                    widget = self.cellWidget(i, j)
                    widget.setEnabled(True)
        else:
            self.setRowCount(0)

        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)
        self.setCounterSelection(self.__oldSelection)
        self.__building = False

    def __addLine(self, i, cntlabel, shape=None):
        #the counter name
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

        #the checkboxes
        for j in range(1, 5, 1):
            widget = self.cellWidget(i, j)
            if widget is None:
                """
                widget = CheckBoxItem(self, i, j)
                self.setCellWidget(i, j, widget)
                widget.sigCheckBoxItemSignal.connect(self._mySlot)
                """
                widget = CntSelectionType(self, i, j, shape=shape)
                self.setCellWidget(i, j, widget)
                widget.sigCntSelectionTypeSignal.connect(self._mySlot)
            else:
                pass

        #the alias
        item = self.item(i, 5)
        alias = self.aliasList[i]
        if item is None:
            item = qt.QTableWidgetItem(alias,
                                       qt.QTableWidgetItem.Type)
            item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.setItem(i, 5, item)
        else:
            item.setText(alias)

    def _headerContextMenu(self, pos):
        """Show context menu on Monitor header for single/multiple choice."""
        logicalIndex = self.horizontalHeader().logicalIndexAt(pos)
        # Monitor column is now at index 4
        if logicalIndex != 4:
            return
        menu = qt.QMenu(self)
        singleAction = menu.addAction("Single choice")
        multipleAction = menu.addAction("Multiple choice")
        singleAction.setCheckable(True)
        multipleAction.setCheckable(True)
        singleAction.setChecked(not self.__monitorMultipleMode)
        multipleAction.setChecked(self.__monitorMultipleMode)
        action = menu.exec(self.horizontalHeader().mapToGlobal(pos))
        if action == singleAction:
            self.__monitorMultipleMode = False
            # If multiple monitors were selected, keep only the last one
            if len(self.monSelection) > 1:
                self.monSelection = self.monSelection[-1:]
                self.monSelectionType = self.monSelectionType[-1:]
                self._update()
        elif action == multipleAction:
            self.__monitorMultipleMode = True

    def set3DEnabled(self, value, emit=True):
        if value:
            self.__is3DEnabled = True
            self.__is2DEnabled = True
        else:
            self.__is3DEnabled = False
            if len(self.xSelection) > 1:
                self.xSelection = self.xSelection[-1:]
        self._update(emit=emit)

    def set2DEnabled(self, value, emit=True):
        if value:
            self.__is2DEnabled = True
            self.__is3DEnabled = False
            if len(self.xSelection) > 2:
                self.xSelection = self.xSelection[-2:]
        else:
            self.__is2DEnabled = False
            if len(self.xSelection) > 1:
                self.xSelection = self.xSelection[-1:]
        self._update(emit=emit)

    def _aliasSlot(self, row, col):
        if self.__building:
            return
        if col != 5:
            return
        item = self.item(row, 5)
        self.aliasList[row] = safe_str(item.text())

    def _mySlot(self, ddict):
        _logger.debug("HDF5CounterTable._mySlot %s", ddict)
        row = ddict["row"]
        col = ddict["column"]
        if col == 1:
            if ddict["state"]:
                if row not in self.xSelection:
                    self.xSelection.append(row)
                    self.xSelectionType.append(ddict["type"])
                else:
                    self.xSelectionType[self.xSelection.index(row)] = ddict["type"]
            else:
                if row in self.xSelection:
                    del self.xSelectionType[self.xSelection.index(row)]
                    del self.xSelection[self.xSelection.index(row)]
            if self.__is3DEnabled:
                if len(self.xSelection) > 3:
                    self.xSelection = self.xSelection[-3:]
                    self.xSelectionType = self.xSelectionType[-3:]
            elif self.__is2DEnabled:
                if len(self.xSelection) > 2:
                    self.xSelection = self.xSelection[-2:]
                    self.xSelectionType = self.xSelectionType[-2:]
            else:
                if len(self.xSelection) > 1:
                    self.xSelection = self.xSelection[-1:]
                    self.xSelectionType = self.xSelectionType[-1:]
        if col == 2:
            if ddict["state"]:
                # Mutual exclusivity: remove from Signals R if present
                if row in self.yrightSelection:
                    del self.yrightSelectionType[self.yrightSelection.index(row)]
                    del self.yrightSelection[self.yrightSelection.index(row)]
                if row not in self.ySelection:
                    self.ySelection.append(row)
                    self.ySelectionType.append(ddict["type"])
                else:
                    self.ySelectionType[self.ySelection.index(row)] = ddict["type"]
            else:
                if row in self.ySelection:
                    del self.ySelectionType[self.ySelection.index(row)]
                    del self.ySelection[self.ySelection.index(row)]
        if col == 3:
            # Signals R column - only for 1D data
            if ddict["state"]:
                # Check if the dataset is 1D
                shape = self.shapeList[row] if self.shapeList else None
                is1D = (shape is None) or (len(shape) <= 1) or \
                       (len(shape) == 2 and 1 in shape)
                if not is1D:
                    # Not 1D data - show warning and reject
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Warning)
                    msg.setText("Second Y-axis is not available for "
                                "not a 1D data")
                    msg.setWindowTitle("Signals R")
                    msg.exec()
                    # Uncheck the widget
                    widget = self.cellWidget(row, col)
                    if widget is not None:
                        widget.setChecked(False)
                    return
                # Mutual exclusivity: remove from Signals if present
                if row in self.ySelection:
                    del self.ySelectionType[self.ySelection.index(row)]
                    del self.ySelection[self.ySelection.index(row)]
                if row not in self.yrightSelection:
                    self.yrightSelection.append(row)
                    self.yrightSelectionType.append(ddict["type"])
                else:
                    self.yrightSelectionType[self.yrightSelection.index(row)] = ddict["type"]
            else:
                if row in self.yrightSelection:
                    del self.yrightSelectionType[self.yrightSelection.index(row)]
                    del self.yrightSelection[self.yrightSelection.index(row)]
        if col == 4:
            if ddict["state"]:
                if row not in self.monSelection:
                    self.monSelection.append(row)
                    self.monSelectionType.append(ddict["type"])
                else:
                    self.monSelectionType[self.monSelection.index(row)] = ddict["type"]
            else:
                if row in self.monSelection:
                    del self.monSelectionType[self.monSelection.index(row)]
                    del self.monSelection[self.monSelection.index(row)]
            if not self.__monitorMultipleMode:
                if len(self.monSelection) > 1:
                    self.monSelection = self.monSelection[-1:]
                    self.monSelectionType = self.monSelectionType[-1:]

        index = ddict.get("type", "")
        if index.lower().startswith("index") and ddict["column"] == 2 and ddict["state"]:
            # we have a selection based on a index
            referenceWidget = self.cellWidget(ddict['row'], ddict['column'])
            refIndex = index
            refValue = referenceWidget._index.value()
            refMin = referenceWidget._index.minimum()
            refMax = referenceWidget._index.maximum()
            # try to synchronize all other indices
            for i in range(len(self.xSelectionType)):
                if self.xSelectionType[i].lower().startswith("index"):
                    widget = self.cellWidget(self.xSelection[i], 1)
                    if widget._index.minimum() == refMin and widget._index.maximum() == refMax:
                        widget._index.setValue(refValue)
                        self.xSelectionType[i] = refIndex
            for i in range(len(self.ySelectionType)):
                if i == ddict["column"]:
                    continue
                if self.ySelectionType[i].lower().startswith("index"):
                    widget = self.cellWidget(self.ySelection[i], 2)
                    if widget._index.minimum() == refMin and widget._index.maximum() == refMax:
                        widget._index.setValue(refValue)
                        self.ySelectionType[i] = refIndex
            for i in range(len(self.yrightSelectionType)):
                if self.yrightSelectionType[i].lower().startswith("index"):
                    widget = self.cellWidget(self.yrightSelection[i], 3)
                    if widget._index.minimum() == refMin and widget._index.maximum() == refMax:
                        widget._index.setValue(refValue)
                        self.yrightSelectionType[i] = refIndex
            for i in range(len(self.monSelectionType)):
                if self.monSelectionType[i].lower().startswith("index"):
                    widget = self.cellWidget(self.monSelection[i], 4)
                    if widget._index.minimum() == refMin and widget._index.maximum() == refMax:
                        widget._index.setValue(refValue)
                        self.monSelectionType[i] = refIndex
        self._update()

    def _update(self, emit=True):
        _logger.debug("_update called with emit = %s" % emit)
        axisLabels = ['X', 'Y', 'Z']
        for i in range(self.rowCount()):
            j = 1
            widget = self.cellWidget(i, j)
            if i in self.xSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
                    widget.setCurrentText(self.xSelectionType[self.xSelection.index(i)])
                widget.setText(axisLabels[self.xSelection.index(i)])
            else:
                if widget.isChecked():
                    widget.setChecked(False)
                widget.setText("")
            j = 2
            widget = self.cellWidget(i, j)
            if i in self.ySelection:
                if not widget.isChecked():
                    widget.setChecked(True)
                    widget.setCurrentText(self.ySelectionType[self.ySelection.index(i)])
            else:
                if widget.isChecked():
                    widget.setChecked(False)
            j = 3
            widget = self.cellWidget(i, j)
            if i in self.yrightSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
                    widget.setCurrentText(self.yrightSelectionType[self.yrightSelection.index(i)])
            else:
                if widget.isChecked():
                    widget.setChecked(False)
            j = 4
            widget = self.cellWidget(i, j)
            if i in self.monSelection:
                if not widget.isChecked():
                    widget.setChecked(True)
                    widget.setCurrentText(self.monSelectionType[self.monSelection.index(i)])
            else:
                if widget.isChecked():
                    widget.setChecked(False)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)

        if emit:
            ddict = {}
            ddict["event"] = "updated"
            self.sigHDF5CounterTableSignal.emit(ddict)

    def getCounterSelection(self):
        ddict = {}
        ddict['cntlist'] = self.cntList * 1
        ddict['aliaslist'] = self.aliasList * 1
        ddict['shapelist'] = self.shapeList * 1
        ddict['x'] = self.xSelection * 1
        ddict['y'] = self.ySelection * 1
        ddict['yright'] = self.yrightSelection * 1
        ddict['m'] = self.monSelection * 1
        ddict['xselectiontype'] = self.xSelectionType * 1
        ddict['yselectiontype'] = self.ySelectionType * 1
        ddict['yrightselectiontype'] = self.yrightSelectionType * 1
        ddict['monselectiontype'] = self.monSelectionType * 1
        return ddict

    def setCounterSelection(self, ddict):
        _logger.debug("HDF5CounterTable.setCounterSelection %s", ddict)
        keys = ddict.keys()
        if 'cntlist' in keys:
            cntlist = ddict['cntlist']
        else:
            cntlist = self.cntList * 1

        # no selection based on aliaslist or counterlist (yet?)
        if 0:
            if 'aliaslist' in keys:
                aliaslist = ddict['aliaslist']
            elif len(self.aliasList) == len(cntlist):
                aliaslist = self.aliasList * 1
            else:
                aliaslist = self.cntList * 1

        if 'x' in keys:
            x = ddict['x']
        else:
            x = []

        if 'y' in keys:
            y = ddict['y']
        else:
            y = []

        if 'yright' in keys:
            yright = ddict['yright']
        else:
            yright = []

        if 'm' in keys:
            monitor = ddict['m']
        else:
            monitor = []

        if 'xselectiontype' in keys:
            xSelectionType = ddict['xselectiontype']
        else:
            xSelectionType = ['full'] * len(x)

        if 'yselectiontype' in keys:
            ySelectionType = ddict['yselectiontype']
        else:
            ySelectionType = ['full'] * len(y)

        if 'yrightselectiontype' in keys:
            yrightSelectionType = ddict['yrightselectiontype']
        else:
            yrightSelectionType = ['full'] * len(yright)

        if 'monselectiontype' in keys:
            monSelectionType = ddict['monselectiontype']
        else:
            monSelectionType = ['full'] * len(monitor)



        self.xSelection = []
        self.xSelectionType = []
        for i in range(len(x)):
            item = x[i]
            if item < len(cntlist):
                counter = cntlist[item]
                if counter in self.cntList:
                    # counter name based selection
                    self.xSelection.append(self.cntList.index(counter))
                    self.xSelectionType.append(xSelectionType[i])
                elif item < len(self.cntList):
                    # index based selection
                    self.xSelection.append(item)
                    self.xSelectionType.append(xSelectionType[i])

        self.ySelection = []
        self.ySelectionType = []
        for i in range(len(y)):
            item = y[i]
            if item < len(cntlist):
                counter = cntlist[item]
                if counter in self.cntList:
                    self.ySelection.append(self.cntList.index(counter))
                    self.ySelectionType.append(ySelectionType[i])

        self.yrightSelection = []
        self.yrightSelectionType = []
        for i in range(len(yright)):
            item = yright[i]
            if item < len(cntlist):
                counter = cntlist[item]
                if counter in self.cntList:
                    self.yrightSelection.append(self.cntList.index(counter))
                    self.yrightSelectionType.append(yrightSelectionType[i])

        self.monSelection = []
        self.monSelectionType = []
        for i in range(len(monitor)):
            item = monitor[i]
            if item < len(cntlist):
                counter = cntlist[item]
                if counter in self.cntList:
                    self.monSelection.append(self.cntList.index(counter))
                    self.monSelectionType.append(monSelectionType[i])
        self._update()

class CheckBoxItem(qt.QCheckBox):

    sigCheckBoxItemSignal = qt.pyqtSignal(object)

    def __init__(self, parent, row, col):
        qt.QCheckBox.__init__(self, parent)
        self.__row = row
        self.__col = col
        self.clicked[bool].connect(self._mySignal)

    def _mySignal(self, value=None):
        ddict = {}
        ddict["event"] = "clicked"
        if value is None:
            value = self.isChecked()
        ddict["state"] = value
        ddict["row"] = self.__row * 1
        ddict["column"] = self.__col * 1
        self.sigCheckBoxItemSignal.emit(ddict)

def main():
    app = qt.QApplication([])
    tab = HDF5CounterTable()
    tab.build(["Cnt1", "Cnt2", "Cnt3", "Cnt 4", "Cnt 5"], shapelist=[None, (10, 10), (10, 20), (10, 10), (20, 10)])
    tab.show()
    def slot(ddict):
        print("Received = ", ddict)
        print("Selection = ", tab.getCounterSelection())
    tab.sigHDF5CounterTableSignal.connect(slot)
    app.exec()

if __name__ == "__main__":
    main()
