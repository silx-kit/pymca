#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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

import copy
import logging

from . import EnergyTable
from PyMca5.PyMcaPhysics import Elements
from .QPeriodicTable import QPeriodicTable
from PyMca5.PyMcaGui import PyMcaQt as qt


_logger = logging.getLogger(__name__)

QTVERSION = qt.qVersion()
ElementList = Elements.ElementList
__revision__ = "$Revision: 1.12 $"


class PeakButton(qt.QPushButton):
    sigPeakClicked = qt.pyqtSignal(str)
    def __init__(self, parent, peak):
        qt.QPushButton.__init__(self, parent)
        #, peak)
        self.peak= peak

        font= self.font()
        font.setBold(1)
        self.setText(peak)
        self.setFlat(1)
        if QTVERSION < '4.0.0':
            self.setToggleButton(0)
        self.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding))

        self.selected= 0
        self.brush= qt.QBrush(qt.QColor(qt.Qt.yellow))

        self.clicked.connect(self.clickedSlot)

    def toggle(self):
        self.selected= not self.selected
        self.update()

    def setSelected(self, b):
        self.selected= b
        if b:
            role = self.backgroundRole()
            palette = self.palette()
            palette.setBrush( role,self.brush)
            self.setPalette(palette)
        else:
            role = self.backgroundRole()
            palette = self.palette()
            palette.setBrush( role, qt.QBrush())
            self.setPalette(palette)
        self.update()

    def isSelected(self):
        return self.selected

    def clickedSlot(self):
        self.toggle()
        self.sigPeakClicked.emit(self.peak)

    def paintEvent(self, pEvent):
        p = qt.QPainter(self)
        wr= self.rect()
        pr= qt.QRect(wr.left()+1, wr.top()+1, wr.width()-2, wr.height()-2)
        if self.selected:
            p.fillRect(pr, self.brush)
        p.setPen(qt.QApplication.instance().palette().color(qt.QPalette.WindowText))
        if hasattr(p, "drawRoundRect"):
            p.drawRoundRect(pr)
        else:
            p.drawRoundedRect(pr, 1., 1., qt.Qt.RelativeSize)
        p.end()
        qt.QPushButton.paintEvent(self, pEvent)

    def drawButton(self, p):
        wr= self.rect()
        pr= qt.QRect(wr.left()+1, wr.top()+1, wr.width()-2, wr.height()-2)
        if self.selected:
                p.fillRect(pr, self.brush)
        qt.QPushButton.drawButtonLabel(self, p)
        p.setPen(qt.QApplication.instance().palette().color(qt.QPalette.WindowText))
        p.drawRoundRect(pr)

class PeakButtonList(qt.QWidget):
    # emitted object is a list
    sigSelectionChanged = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="PeakButtonList",
                 peaklist=['K','Ka','Kb','L','L1','L2','L3','M', 'M1', 'M2', 'M3', 'M4', 'M5'],
                 fl=0):
        qt.QWidget.__init__(self,parent)
        self.peaklist = peaklist

        if QTVERSION < '4.0.0':
            layout= qt.QHBoxLayout(self, 0, 5)
        else:
            layout= qt.QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            #, 0, 5)

        layout.addStretch(2)

        self.buttondict={}
        for key in peaklist:
            self.buttondict[key] = PeakButton(self, key)
            layout.addWidget(self.buttondict[key])
            self.buttondict[key].sigPeakClicked.connect(self.__selection)

        layout.addStretch(1)

        #Reset
        self.resetBut = qt.QPushButton(self)
        self.resetBut.setText("Reset")
        layout.addWidget(self.resetBut)
        self.resetBut.clicked.connect(self.__resetBut)

        layout.addStretch(2)

    def __resetBut(self):
        for key in self.peaklist:
            self.buttondict[key].setSelected(0)
        self.sigSelectionChanged.emit([])

    def __selection(self, peak):
        selection= []
        for key in self.peaklist:
            if self.buttondict[key].isSelected():
                selection.append(key)
        self.sigSelectionChanged.emit(selection)


    def setSelection(self, selection=[]):
        for key in self.peaklist:
            if key in selection:
                self.buttondict[key].setSelected(1)
            else:
                self.buttondict[key].setSelected(0)

    def setDisabled(self,selection=[]):
        for key in self.peaklist:
            if key in selection:
                self.buttondict[key].setEnabled(0)
            else:
                self.buttondict[key].setEnabled(1)


class FitPeakSelect(qt.QWidget):
    sigFitPeakSelect = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="FitPeakSelect", peakdict = {}, energyTable=None):
        qt.QWidget.__init__(self,parent)

        layout=qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(20)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        l1=MyQLabel(hbox, bold=True, color=qt.QApplication.instance().palette().color(qt.QPalette.WindowText))
        hboxLayout.addWidget(l1)

        self.energyValue = None
        if energyTable is not None:
            text = '<b><nobr>Excitation Energy (keV)</nobr></b>'
            l1.setFixedWidth(l1.fontMetrics().maxWidth()*len("##"+text+"####"))
            l1.setText(text)
            self.energyTable = energyTable
            add = 0
            self.energy = MyQLabel(hbox)
            hboxLayout.addWidget(self.energy)
            self.energy.setFixedWidth(self.energy.fontMetrics().maxWidth()*len('########.###'))
            self.energy.setAlignment(qt.Qt.AlignLeft)
            #self.energy.setForegroundColor(qt.Qt.red)
        else:
            l1.setText('<b><nobr>Excitation Energy (keV)</nobr></b>')
            self.energyTable = EnergyTable.EnergyTable(self)
            add = 1
            self.energy = qt.QLineEdit(hbox)
            hboxLayout.addWidget(self.energy)
            self.energy.setFixedWidth(self.energy.fontMetrics().maxWidth()*len('########.###'))
            self.energyButton = qt.QPushButton(hbox)
            hboxLayout.addWidget(self.energyButton)
            self.energyButton.setText("Update")
            self.energyButton.clicked.connect(self._energyClicked)

        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        layout.addSpacing(20)
        layout.addWidget(hbox)

        self.table = QPeriodicTable(self)
        line= qt.QFrame(self)
        line.setFrameShape(qt.QFrame.HLine)
        line.setFrameShadow(qt.QFrame.Sunken)

        self.peaks = PeakButtonList(self)
        self.peaks.setDisabled(['K','Ka','Kb','L','L1','L2','L3','M', 'M1', 'M2', 'M3', 'M4', 'M5'])

        self.energyTable.sigEnergyTableSignal.connect(self._energyTableAction)
        self.table.sigElementClicked.connect(self.elementClicked)
        self.peaks.sigSelectionChanged.connect(self.peakSelectionChanged)

        #Reset All
        self.resetAllButton = qt.QPushButton(self.peaks)
        palette = qt.QPalette(self.resetAllButton.palette())
        role = self.resetAllButton.foregroundRole()
        palette.setColor(role, qt.Qt.red)
        self.resetAllButton.setPalette(palette)
        self.resetAllButton.setText("Reset All")
        self.peaks.layout().addWidget(self.resetAllButton)

        self.resetAllButton.clicked.connect(self.__resetAll)

        layout.addWidget(self.table)
        layout.addWidget(line)
        layout.addWidget(self.peaks)
        if add:layout.addWidget(self.energyTable)
        layout.addStretch(1)

        self.current= None
        self.setSelection(peakdict)

    def __resetAll(self):
        msg=qt.QMessageBox.warning( self, "Clear selection",
                      "Do you want to reset the selection for all elements?",
                      qt.QMessageBox.Yes,qt.QMessageBox.No)
        if msg == qt.QMessageBox.No:
            return

        self.peakdict = {}
        self.table.setSelection(list(self.peakdict.keys()))
        self.peaks.setSelection([])
        self.peakSelectionChanged([])

    def __getZ(self,element):
        return ElementList.index(element) + 1

    def setSelection(self,peakdict):
        self.peakdict = {}
        self.peakdict.update(peakdict)
        for key in list(self.peakdict.keys()):
                if type(self.peakdict[key])!= type([]):
                        self.peakdict[key]= [ self.peakdict[key] ]
        self.table.setSelection(list(self.peakdict.keys()))

    def getSelection(self):
        ddict={}
        for key in list(self.peakdict.keys()):
                if len(self.peakdict[key]):
                        ddict[key]= self.peakdict[key]
        return ddict

    def peakSelectionChanged(self,selection):
        if self.current is None: return
        if type(selection) != type([]):
            selection=selection.list
        self.peakdict[self.current] = selection
        if len(self.peakdict[self.current]):
            self.table.setElementSelected(self.current,1)
        else:
            self.table.setElementSelected(self.current,0)
        sel= self.getSelection()
        sel['current'] = self.current
        self.sigFitPeakSelect.emit((sel))

    def elementClicked(self,symbol):
        if QTVERSION > '4.0.0':symbol = str(symbol)
        if not (symbol in self.peakdict):
            self.peakdict[symbol] = []
        self.current = symbol
        if len(self.peakdict[self.current]):
            self.table.setElementSelected(self.current,1)
        else:
            self.table.setElementSelected(self.current,0)
        for ele in list(self.peakdict.keys()):
            if ele != symbol:
                if not len(self.peakdict[ele]):
                    del self.peakdict[ele]
        sel= self.getSelection()
        sel['current'] = self.current
        self.setPeaksDisabled(symbol)
        self.sigFitPeakSelect.emit((sel))
        self.peaks.setSelection(self.peakdict[symbol])

    def setPeaksDisabled(self,symbol):
        z = self.__getZ(symbol)
        if (z > 47) and (Elements.getomegam5('Cd') > 0.0):
            #we have data available to support that
            disabled = []
        elif z > 66:
            #self.peaks.setDisabled(['Ka','Kb'])
            #disabled = ['Ka','Kb']
            disabled = []
        elif z > 17:
            #self.peaks.setDisabled(['Ka','Kb','M'])
            #disabled = ['Ka','Kb','M']
            disabled = ['M', 'M1', 'M2', 'M3', 'M4', 'M5']
        elif z > 2:
            #self.peaks.setDisabled(['Ka','Kb','L','L1','L2','L3','M'])
            #disabled = ['Ka','Kb','L','L1','L2','L3','M']
            disabled = ['L','L1','L2','L3','M', 'M1', 'M2', 'M3', 'M4', 'M5']
        else:
            #self.peaks.setDisabled(['K','Ka','Kb','L','L1','L2','L3','M'])
            #disabled = ['Ka','Kb','L','L1','L2','L3','M']
            disabled = ['Ka', 'Kb','L','L1','L2','L3','M', 'M1', 'M2', 'M3', 'M4', 'M5']

        ele = symbol
        if self.energyValue is not None:
            for peak in ['K', 'Ka', 'Kb', 'L','L1','L2','L3','M', 'M1', 'M2', 'M3', 'M4', 'M5']:
                if peak not in disabled:
                    if peak == 'L':
                        if Elements.Element[ele]['binding']['L3'] > self.energyValue:
                            disabled.append(peak)
                    elif peak == 'M':
                        if Elements.Element[ele]['binding']['M5'] > self.energyValue:
                            disabled.append(peak)
                    elif peak == 'Ka':
                        if Elements.Element[ele]['binding']['K'] > self.energyValue:
                            disabled.append(peak)
                    elif peak == 'Kb':
                        if Elements.Element[ele]['binding']['K'] > self.energyValue:
                            disabled.append(peak)
                    elif Elements.Element[ele]['binding'][peak] > self.energyValue:
                            disabled.append(peak)
                    else:
                        pass
        self.peaks.setDisabled(disabled)

    def setEnergy(self, energy):
        if (energy is None) or (energy == []):
            self.energyValue = energy
            self.energy.setText("None")
        elif energy == "None":
            self.energyValue = None
            self.energy.setText("None")
        elif type(energy) == type([]):
            self.energyValue = max(energy)
        else:
            self.energyValue = energy
            self.energy.setText("%.4f" % energy)
        self._energyClicked()

    def _energyTableAction(self, ddict):
        _logger.debug("_energyTableAction called, ddict = %s" % ddict)
        elist, wlist, flist, slist= self.energyTable.getParameters()
        maxenergy = 0.0
        for i in range(len(flist)):
            if flist[i]:
                if elist[i] is not None:
                    if wlist[i] > 0.0:
                        if elist[i] > maxenergy:
                            maxenergy = elist[i]
        if maxenergy == 0.0:maxenergy = None
        self.setEnergy(maxenergy)

    def _energyClicked(self):
        string = str(self.energy.text())
        string.replace(" ","")
        if (string != "None") and len(string):
            try:
                value = float(string)
                self.energyValue = value
                if False:
                    self.energyButton.setFocus()
            except Exception:
                msg=qt.QMessageBox(self.energy)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Float")
                msg.exec_loop()
                self.energy.setFocus()
        else:
            self.energyValue = None
            if False:
                self.energyButton.setFocus()
        self.__updateSelection()

    def __updateSelection(self):
        if self.energyValue is not None:
            for ele in list(self.peakdict.keys()):
                for peak in self.peakdict[ele]:
                    if   peak in self.peakdict[ele]:
                        index = self.peakdict[ele].index(peak)
                    if   peak == 'L':
                        if Elements.Element[ele]['binding']['L3'] > self.energyValue:
                            del self.peakdict[ele][index]
                    elif peak == 'M':
                        if Elements.Element[ele]['binding']['M5'] > self.energyValue:
                            del self.peakdict[ele][index]
                    elif peak == "Ka":
                        if Elements.Element[ele]['binding']['K'] > self.energyValue:
                            del self.peakdict[ele][index]
                    elif peak == "Kb":
                        if Elements.Element[ele]['binding']['K'] > self.energyValue:
                            del self.peakdict[ele][index]
                    elif Elements.Element[ele]['binding'][peak] > self.energyValue:
                        del self.peakdict[ele][index]
                    else:
                        pass
                if ele == self.current:
                    self.peaks.setSelection(self.peakdict[ele])
                    self.peakSelectionChanged(self.peakdict[ele])
                    self.elementClicked(ele)
                if not len(self.peakdict[ele]): del self.peakdict[ele]
        dict = copy.deepcopy(self.peakdict)
        self.setSelection(dict)


class MyQLineEdit(qt.QLineEdit):
    def __init__(self,parent=None,name=None):
        qt.QLineEdit.__init__(self,parent,name)

    def focusInEvent(self,event):
        self.setPaletteBackgroundColor(qt.QApplication.instance().palette().color(qt.QPalette.Highlight))

    def focusOutEvent(self,event):
        self.setPaletteBackgroundColor(qt.QApplication.instance().palette().color(qt.QPalette.Base))

class MyQLabel(qt.QLabel):
    def __init__(self, parent=None, bold=True, color=None):
        qt.QLabel.__init__(self,parent)
        if color is None:
            color = qt.QApplication.instance().palette().color(qt.QPalette.WindowText)
        palette = self.palette()
        role = self.foregroundRole()
        palette.setColor(role,color)
        self.setPalette(palette)
        self.font().setBold(bold)


    if QTVERSION < '4.0.0':
        def drawContents(self, painter):
            painter.font().setBold(self.bold)
            pal =self.palette()
            pal.setColor(qt.QColorGroup.Foreground,self.color)
            self.setPalette(pal)
            qt.QLabel.drawContents(self,painter)
            painter.font().setBold(0)

if __name__ == "__main__":
    import sys
    def change(ddict):
        print("New selection:",)
        print(ddict)
    a = qt.QApplication([])
    a.lastWindowClosed.connect(a.quit)

    w = qt.QTabWidget()

    f = FitPeakSelect()
    w.addTab(f, "QPeriodicTable")
    f.sigFitPeakSelect.connect(change)
    w.show()
    a.exec()
    a = None
