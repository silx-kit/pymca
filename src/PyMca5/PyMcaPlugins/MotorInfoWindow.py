#/*##########################################################################
# Copyright (C) 2004-2020 T. Rueter, European Synchrotron Radiation Facility
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
__author__ = "Tonn Rueter"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui import IconDict
from PyMca5.PyMcaGui.misc.TableWidget import TableWidget


_logger = logging.getLogger(__name__)


class MotorInfoComboBox(qt.QComboBox):
    loadColumnSignal = qt.pyqtSignal(object)

    def __init__(self, parent, mlist, nCol):
        qt.QComboBox.__init__(self,  parent)
        self.motorNamesList = [""] + mlist
        self.nColumn = nCol
        self.addItems([str(elem) for elem in self.motorNamesList])
        self.activated.connect(self.emitLoadColumnSignal)

    def emitLoadColumnSignal(self):
        ddict = {}
        ddict['column'] = self.nColumn
        ddict['motor'] = str(self.currentText())
        ddict['event'] = "activated"
        self.loadColumnSignal.emit(ddict)

    def currentMotor(self):
        return str(self.currentText())

    def updateMotorNamesList(self, newMotorNamesList):
        currentMotorName = self.currentMotor()
        self.clear()
        newMotorNamesList = [''] + newMotorNamesList
        self.motorNamesList = newMotorNamesList
        self.addItems([str(elem) for elem in self.motorNamesList])
        newIndex = self.findText(currentMotorName)
        if newIndex < 0:
            newIndex = 0
        self.setCurrentIndex(newIndex)


class MotorInfoHeader(qt.QHeaderView):
    xOffsetLeft = 5
    xOffsetRight = -5
    yOffset = 0

    def __init__(self, parent):
        qt.QHeaderView.__init__(self, qt.Qt.Horizontal, parent)
        self.boxes = []
        self.sectionResized.connect( self.handleSectionResized )
        if hasattr(self, "setClickable"):
            # Qt 4
            self.setClickable(True)
        else:
            # Qt 5
            self.setSectionsClickable(True)
        self.setDefaultSectionSize(120)
        self.setMinimumSectionSize(120)

    def showEvent(self, event):
        if len(self.boxes) == 0:
            self.boxes = [None] * self.count()
        for idx in range(1, self.count()):
            if self.boxes[idx] is None:
                newBox = MotorInfoComboBox(self, self.parent().motorNamesList, idx)
                newBox.loadColumnSignal.connect(self.parent().loadColumn)
                newBox.resize(self.sectionSize(idx) - 30, self.height())
                self.boxes[idx] = newBox
            self.boxes[idx].setGeometry(self.sectionViewportPosition(idx) + self.xOffsetLeft,
                                      self.yOffset,
                                      self.sectionSize(idx) + self.xOffsetRight,
                                      self.height())
            #if idx > 0:
            #    self.setTabOrder(self.boxes[idx-1], self.boxes[idx])
            self.boxes[idx].show()
        qt.QHeaderView.showEvent(self, event)

    def handleSectionResized(self, index):
        for idx in range(self.visualIndex(index), len(self.boxes)):
            if idx > 0:
                logical = self.logicalIndex(idx)
                self.boxes[idx].setGeometry(self.sectionViewportPosition(logical) + self.xOffsetLeft,
                                          self.yOffset,
                                          self.sectionSize(logical) + self.xOffsetRight,
                                          self.height())

    def deleteLastSection(self):
        self.boxes[-1].close()
        del( self.boxes[-1] )

    def addLastSection(self):
        idx = self.count()-1
        newBox = MotorInfoComboBox(self, self.parent().motorNamesList, idx)
        newBox.loadColumnSignal.connect(self.parent().loadColumn)
        newBox.setGeometry(self.sectionViewportPosition(idx) + self.xOffsetLeft,
                           self.yOffset,
                           self.sectionSize(idx) +  self.xOffsetRight,
                           self.height() )
        newBox.show()
        self.boxes += [newBox]

    def fixComboPositions(self):
        for idx in range(1, self.count()):
            self.boxes[idx].setGeometry(self.sectionViewportPosition(idx) + self.xOffsetLeft,
                                        self.yOffset,
                                        self.sectionSize(idx) +  self.xOffsetRight,
                                        self.height())


class MotorInfoTable(TableWidget):
    def __init__(self, parent, numRows, numColumns, legList, motList):
        TableWidget.__init__(self, parent)
        self.setRowCount(0)
        self.setColumnCount(numColumns)
        self.currentComboBox = 1
        self.legendsList = legList
        self.motorsList  = motList
        self.motorNamesList = self.getAllMotorNames()
        self.motorNamesList.sort()
        self.infoDict = dict( zip( self.legendsList, self.motorsList ) )
        self.header = MotorInfoHeader(self)
        self.setHorizontalHeader(self.header)
        self.setHorizontalHeaderItem(0, qt.QTableWidgetItem('Legend'))
        #self.setSortingEnabled(True)
        self.verticalHeader().hide()
        self.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.setShowGrid(False)
        for idx in range(len(self.legendsList)):
            curveLegend = self.legendsList[idx]
            self.insertRow(idx)
            self.setItem(idx, 0, curveLegend )
            for jdx in range(1, self.columnCount()):
                self.setItem(0, jdx, '')
        #self.sortByColumn(0, qt.Qt.AscendingOrder)

    def addColumn(self):
        currentColumn = self.columnCount()
        self.insertColumn(currentColumn)
        self.header.addLastSection()

    def delColumn(self):
        if self.columnCount() > 1:
            self.removeColumn(self.columnCount()-1)
            self.header.deleteLastSection()

    def fillRow(self, currentRow):
        legend = self.legendsList[currentRow]
        self.setItem(currentRow, 0, legend )

    def updateTable(self, legList, motList):
        _logger.debug("updateTable received lengths = %d %d", len(legList), len(motList))
        _logger.debug("updateTable received legList = %s", legList)
        _logger.debug("updateTable received motList = %s", motList)
        if legList is None:
            nItems = 0
        else:
            nItems = len(legList)
        if self.legendsList == legList and self.motorsList == motList:
            _logger.debug("Ignoring update, no changes")
        else:
            nRows = self.rowCount()
            if nRows != nItems:
                self.setRowCount(nItems)
            self.infoDict = dict(zip(legList, motList))
            self.legendsList = legList
            self.motorsList = motList
            motorNamesList = self.getAllMotorNames()
            motorNamesList.sort()
            for idx in range(0, self.columnCount()):
                cBox = self.header.boxes[idx]
                if cBox is not None:
                    cBox.updateMotorNamesList(motorNamesList)
            self.motorNamesList = motorNamesList
            for idx in range(len(legList)):
                self.fillRow(idx)
            for idx in range(0, self.columnCount()):
                cBox = self.header.boxes[idx]
                if cBox is not None:
                    cBox.emitLoadColumnSignal()

    def loadColumn(self, ddict):
        for key in ddict.keys():
            if str(key) == str("motor"):
                motorName = ddict[key]
            elif str(key) == str("column"):
                column = ddict[key]
        if len(motorName) > 0:
            for idx in range(self.rowCount()):
                legend = str( self.item(idx, 0).text() )
                curveInfo = self.infoDict.get(legend, None)
                if curveInfo is not None:
                    motorValue = curveInfo.get(motorName, '---')
                else:
                    motorValue = '---'
                self.setItem(idx, column, str(motorValue))
        else:
            for idx in range(0, self.rowCount()):
                self.setItem(idx, column, '')
        # self.resizeColumnToContents(column)

    def getAllMotorNames(self):
        nameSet = []
        for dic in self.motorsList:
            for key in dic.keys():
                if key not in nameSet:
                    nameSet.append(key)
        return nameSet

    def setItem(self, row, column, text=''):
        item = self.item(row, column)
        if item is None:
            item = qt.QTableWidgetItem(text)
            item.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)
            qt.QTableWidget.setItem(self, row, column, item)
        else:
            item.setText(text)

    def scrollContentsBy(self, dx, dy):
        qt.QTableWidget.scrollContentsBy(self, dx, dy )
        if (dx != 0):
            self.horizontalHeader().fixComboPositions()


class MotorInfoDialog(qt.QWidget):
    def __init__(self, parent, legends, motorValues):
        """
        legends         List contains Plotnames
        motorValues     List contains names and values of the motors
        """
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("Motor Info Plugin")
        if len(legends) != len(motorValues):
            _logger.warning('Consistency error: legends and motorValues do not have same length!')
        self.numCurves = len(legends)
        # Buttons
        self.buttonAddColumn = qt.QPushButton("Add", self)
        self.buttonDeleteColumn = qt.QPushButton("Del", self)
        self.buttonUpdate = qt.QPushButton(
                                qt.QIcon(qt.QPixmap(IconDict["reload"])), '', self)
        # Table
        self.table = MotorInfoTable(self, self.numCurves, 4, legends, motorValues)

        # Layout
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setSpacing(2)
        self.buttonLayout = qt.QHBoxLayout(None)
        self.buttonLayout .setSpacing(1)
        # Add widgets to layour
        self.mainLayout.addWidget(self.table, 0, 0)
        self.mainLayout.addLayout(self.buttonLayout, 1, 0)
        self.buttonLayout.addWidget(self.buttonUpdate)
        self.buttonLayout.addWidget(self.buttonAddColumn)
        self.buttonLayout.addWidget(self.buttonDeleteColumn)
        self.buttonLayout.addWidget(qt.HorizontalSpacer(self))
        self.resize(700, 400)
        # Create shortcuts
        self.updateShortCut = qt.QShortcut(qt.QKeySequence('F5'), self)
        self.addColShortCut = qt.QShortcut(qt.QKeySequence('Ctrl++'), self)
        self.delColShortCut = qt.QShortcut(qt.QKeySequence('Ctrl+-'), self)
        # Make connections
        self.buttonAddColumn.clicked.connect(self.table.addColumn)
        self.buttonDeleteColumn.clicked.connect(self.table.delColumn)
        self.addColShortCut.activated.connect(self.table.addColumn)
        self.delColShortCut.activated.connect(self.table.delColumn)

    def keyPressEvent(self, event):
        if (event.key() == qt.Qt.Key_Escape):
            self.close()


def main():
    import sys, random
    legends = ['Curve0', 'Curve1', 'Curve2', 'Curve3']
    motors = [{'Motor12': 0.5283546103038855, 'Motor11': 0.8692713996985609, 'Motor10': 0.2198364185388587,
               'Motor 8': 0.19806882661182112, 'Motor 9': 0.4844754557916431, 'Motor 4': 0.3502522172639875},
               {'Motor18': 0.4707468826876532, 'Motor17': 0.6958160702991127, 'Motor16': 0.8257808117546283,
               'Motor13': 0.09084289261899736, 'Motor12': 0.5190253643331453, 'Motor11': 0.21344565983311958},
               {'Motor12': 0.6504890336783156, 'Motor11': 0.44400576643956124, 'Motor10': 0.613870067851634,
               'Motor 8': 0.901968648110583, 'Motor 9': 0.3197687710845185, 'Motor 4': 0.5714322786278168},
               {'Motor13': 0.6491598094029021, 'Motor12': 0.2975843286841311, 'Motor11': 0.006312468992195397,
               'Motor 9': 0.014325738753558803, 'Motor 4': 0.8185362197656616, 'Motor 5': 0.6643614796103005}]
    app = qt.QApplication(sys.argv)
    w = MotorInfoDialog(None, legends, motors)
    w.show()
    app.exec()

if __name__ == '__main__':
    main()
