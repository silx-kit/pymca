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
__author__ = "V. Armando Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()

qt.QLabel.AlignRight = qt.Qt.AlignRight
qt.QLabel.AlignCenter = qt.Qt.AlignCenter
qt.QLabel.AlignVCenter = qt.Qt.AlignVCenter

class Q3GridLayout(qt.QGridLayout):
    def addMultiCellWidget(self, w, r0, r1, c0, c1, *var):
        self.addWidget(w, r0, c0, 1 + r1 - r0, 1 + c1 - c0)

from PyMca5.PyMcaPhysics import Elements
from . import MaterialEditor
from . import MatrixEditor
from . import TransmissionTableGui
import re

_logger = logging.getLogger(__name__)


class MyQLabel(qt.QLabel):
    def __init__(self, parent=None, name=None, fl=0, bold=True,
                 color= qt.Qt.red):
        qt.QLabel.__init__(self, parent)
        palette = self.palette()
        role = self.foregroundRole()
        palette.setColor(role, color)
        self.setPalette(palette)
        self.font().setBold(bold)

class AttenuatorsTab(qt.QWidget):
    def __init__(self, parent=None, name="Attenuators Tab",
                 attenuators=None, graph=None):
        qt.QWidget.__init__(self, parent)
        layout = qt.QVBoxLayout(self)

        maxheight = qt.QDesktopWidget().height()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.table  = AttenuatorsTableWidget(self, name, attenuators,
                                             funnyfilters=True)
        layout.addWidget(self.table)
        self.mainTab = qt.QTabWidget(self)
        layout.addWidget(self.mainTab)
        rheight = self.table.horizontalHeader().sizeHint().height()
        if maxheight < 801:
            self.editor = MaterialEditor.MaterialEditor(height=5,
                                                        graph=graph)
            self.table.setMinimumHeight(7 * rheight)
            self.table.setMaximumHeight(13 * rheight)
        else:
            spacer = qt.VerticalSpacer(self)
            layout.addWidget(spacer)
            if rheight > 32:
                # when using big letters we run into troubles
                # for instance windowx 1920x1080 but with a 150% scale
                self.editor = MaterialEditor.MaterialEditor(height=5,
                                                            graph=graph)
                if rheight > 40:
                    self.table.setMinimumHeight(10*rheight)
                else:
                    self.table.setMinimumHeight(14*rheight)
            else:
                self.editor = MaterialEditor.MaterialEditor(graph=graph)
                self.table.setMinimumHeight(14*rheight)
            self.table.setMaximumHeight(14*rheight)
        self.userAttenuators = TransmissionTableGui.TransmissionTableGui()
        self.mainTab.addTab(self.editor, "Material Editor")
        self.mainTab.addTab(self.userAttenuators, "User Attenuators")

class MultilayerTab(qt.QWidget):
    def __init__(self,parent=None, name="Multilayer Tab", matrixlayers=None):
        if matrixlayers is None:
            matrixlayers=["Layer0", "Layer1", "Layer2", "Layer3",
                          "Layer4", "Layer5", "Layer6", "Layer7",
                          "Layer8", "Layer9"]
        qt.QWidget.__init__(self, parent)
        layout = qt.QVBoxLayout(self)

        self.matrixGeometry = MatrixEditor.MatrixEditor(self, "tabMatrix",
                                   table=False, orientation="horizontal",
                                   density=False, thickness=False,
                                   size="image2")
        layout.addWidget(self.matrixGeometry)

        text = "This matrix definition will only be "
        text += "considered if Matrix is selected and material is set to "
        text += "MULTILAYER in the ATTENUATORS tab.\n  "
        self.matrixInfo  = qt.QLabel(self)
        layout.addWidget(self.matrixInfo)
        self.matrixInfo.setText(text)
        self.matrixTable = AttenuatorsTableWidget(self, name,
                                                  attenuators=matrixlayers,
                                                  matrixmode=True)
        layout.addWidget(self.matrixTable)

class CompoundFittingTab(qt.QWidget):
    def __init__(self, parent=None, name="Compound Tab",
                    layerlist=None):
        qt.QWidget.__init__(self, parent)
        if layerlist is None:
            self.nlayers = 5
        else:
            self.nlayers = len(layerlist)
        layout = qt.QVBoxLayout(self)
        hbox = qt.QWidget(self)
        hboxlayout  = qt.QHBoxLayout(hbox)
        #hboxlayout.addWidget(qt.HorizontalSpacer(hbox))
        self._compoundFittingLabel = MyQLabel(hbox, color=qt.Qt.red)
        self._compoundFittingLabel.setText("Compound Fitting Mode is OFF")
        self._compoundFittingLabel.setAlignment(qt.QLabel.AlignCenter)
        hboxlayout.addWidget(self._compoundFittingLabel)
        #hboxlayout.addWidget(qt.HorizontalSpacer(hbox))
        layout.addWidget(hbox)

        grid = qt.QWidget(self)
        glt = Q3GridLayout(grid)
        glt.setContentsMargins(11, 11, 11, 11)
        glt.setSpacing(2)

        self._layerFlagWidgetList = []
        options = ["FREE", "FIXED", "IGNORED"]
        for i in range(self.nlayers):
            r = int(i / 5)
            c = 3 * (i % 5)
            label = qt.QLabel(grid)
            label.setText("Layer%d" % i)
            cbox = qt.QComboBox(grid)
            for item in options:
                cbox.addItem(item)
            if i == 0:
                cbox.setCurrentIndex(0)
            else:
                cbox.setCurrentIndex(1)
            glt.addWidget(label, r, c)
            glt.addWidget(cbox, r, c + 1)
            glt.addWidget(qt.QWidget(grid), r, c + 2)

        layout.addWidget(grid)
        self.mainTab = qt.QTabWidget(self)
        layout.addWidget(self.mainTab)
        self._editorList = []
        for i in range(self.nlayers):
            editor = CompoundFittingTab0(layerindex=i)
            self.mainTab.addTab(editor, "layer Editor")
            self._editorList.append(editor)


class CompoundFittingTab0(qt.QWidget):
    def __init__(self, parent=None, name="Compound Tab",
                    layerindex=None, compoundlist=None):
        if layerindex is None:
            layerindex = 0
        if compoundlist is None:
            compoundlist = []
            for i in range(10):
                compoundlist.append("Compound%d%d" % (layerindex, i))
        qt.QWidget.__init__(self, parent)
        layout = qt.QVBoxLayout(self)

        grid = qt.QWidget(self)
        gl = Q3GridLayout(grid)
        gl.setContentsMargins(11, 11, 11, 11)
        gl.setSpacing(2)

        # Layer name
        nameLabel = qt.QLabel(grid)
        nameLabel.setText("Name")

        self.nameLine = qt.QLineEdit(grid)
        self.nameLine.setText("Compound fitting layer %d" % layerindex)

        gl.addWidget(nameLabel, 0, 0)
        gl.addMultiCellWidget(self.nameLine, 0, 0, 1, 5)

        Line = qt.QFrame(grid)
        Line.setFrameShape(qt.QFrame.HLine)
        Line.setFrameShadow(qt.QFrame.Sunken)
        Line.setFrameShape(qt.QFrame.HLine)
        gl.addMultiCellWidget(Line, 1, 1, 0, 5)

        #labels
        fixedLabel = qt.QLabel(grid)
        fixedLabel_font = qt.QFont(fixedLabel.font())
        fixedLabel_font.setItalic(1)
        fixedLabel.setFont(fixedLabel_font)
        fixedLabel.setText(str("Fixed"))
        fixedLabel.setAlignment(qt.Qt.AlignVCenter)

        valueLabel = qt.QLabel(grid)
        valueLabel_font = qt.QFont(valueLabel.font())
        valueLabel_font.setItalic(1)
        valueLabel.setFont(valueLabel_font)
        valueLabel.setText(str("Value"))
        valueLabel.setAlignment(qt.QLabel.AlignCenter)


        errorLabel = qt.QLabel(grid)
        errorLabel_font = qt.QFont(errorLabel.font())
        errorLabel_font.setItalic(1)
        errorLabel.setFont(errorLabel_font)
        errorLabel.setText(str("Error"))
        errorLabel.setAlignment(qt.QLabel.AlignCenter)

        gl.addWidget(fixedLabel, 2, 2)
        gl.addWidget(valueLabel, 2, 3)
        gl.addWidget(errorLabel, 2, 5)

        #density
        densityLabel = qt.QLabel(grid)
        densityLabel.setText("Density")

        self.densityCheck = qt.QCheckBox(grid)
        self.densityCheck.setText(str(""))

        self.densityValue = qt.QLineEdit(grid)
        densitySepLabel = qt.QLabel(grid)
        densitySepLabel_font = qt.QFont(densitySepLabel.font())
        densitySepLabel_font.setBold(1)
        densitySepLabel.setFont(densitySepLabel_font)
        densitySepLabel.setText(str("+/-"))

        self.densityError = qt.QLineEdit(grid)

        gl.addWidget(densityLabel, 3, 0)
        gl.addWidget(qt.HorizontalSpacer(grid), 3, 1)
        gl.addWidget(self.densityCheck, 3, 2)
        gl.addWidget(self.densityValue, 3, 3)
        gl.addWidget(densitySepLabel, 3, 4)
        gl.addWidget(self.densityError, 3, 5)

        #thickness
        thicknessLabel = qt.QLabel(grid)
        thicknessLabel.setText("Thickness")

        self.thicknessCheck = qt.QCheckBox(grid)
        self.thicknessCheck.setText(str(""))

        self.thicknessValue = qt.QLineEdit(grid)
        thicknessSepLabel = qt.QLabel(grid)
        thicknessSepLabel_font = qt.QFont(thicknessSepLabel.font())
        thicknessSepLabel_font.setBold(1)
        thicknessSepLabel.setFont(thicknessSepLabel_font)
        thicknessSepLabel.setText(str("+/-"))

        self.thicknessError = qt.QLineEdit(grid)

        gl.addWidget(thicknessLabel, 4, 0)
        gl.addWidget(self.thicknessCheck, 4, 2)
        gl.addWidget(self.thicknessValue, 4, 3)
        gl.addWidget(thicknessSepLabel, 4, 4)
        gl.addWidget(self.thicknessError, 4, 5)

        Line = qt.QFrame(grid)
        Line.setFrameShape(qt.QFrame.HLine)
        Line.setFrameShadow(qt.QFrame.Sunken)
        Line.setFrameShape(qt.QFrame.HLine)
        gl.addMultiCellWidget(Line, 5, 5, 0, 5)

        layout.addWidget(grid)
        """
        self.matrixGeometry = MatrixEditor.MatrixEditor(self,"tabMatrix",
                                   table=False, orientation="horizontal",
                                   density=False, thickness=False,
                                   size="image2")
        layout.addWidget(self.matrixGeometry)

        text  ="This matrix definition will only be "
        text +="considered if Matrix is selected and material is set to "
        text +="MULTILAYER in the ATTENUATORS tab.\n  "
        self.matrixInfo  = qt.QLabel(self)
        layout.addWidget(self.matrixInfo)
        self.matrixInfo.setText(text)
        """
        self.matrixTable = AttenuatorsTableWidget(self, name,
                                                  attenuators=compoundlist,
                                                  matrixmode=False,
                                                  compoundmode=True,
                                                  layerindex=layerindex)
        layout.addWidget(self.matrixTable)

QTable = qt.QTableWidget


class AttenuatorsTableWidget(QTable):
    sigValueChanged = qt.pyqtSignal(int, int)
    def __init__(self, parent=None, name="Attenuators Table",
                 attenuators=None, matrixmode=None, compoundmode=None,
                 layerindex=0, funnyfilters=False):

        beamFilters0 = ["BeamFilter1", "BeamFilter2", "BeamFilter3"] # this needs to be synchronized with FitParam.py
        attenuators0 = ["Atmosphere", "Air", "Window", "Contact", "DeadLayer",
                       "Filter5", "Filter6", "Filter7"] + beamFilters0 +  ["Detector", "Matrix"]
        self.__attenuators0 = attenuators0
        self.__beamFilters0 = beamFilters0

        QTable.__init__(self, parent)
        self.setWindowTitle(name)

        if attenuators is None:
            attenuators = attenuators0
        if matrixmode is None:
            matrixmode = False
        if matrixmode:
            self.compoundMode = False
        elif compoundmode is None:
            self.compoundMode = False
        else:
            self.compoundMode = compoundmode
        if funnyfilters is None:
            funnyfilters = False
        self.funnyFiltersMode = funnyfilters
        if self.compoundMode:
            self.funnyFiltersMode = False
            labels = ["Compound", "Name", "Material", "Initial Amount"]
        else:
            if self.funnyFiltersMode:
                labels = ["Attenuator", "Name", "Material",
                          "Density (g/cm3)", "Thickness (cm)", "Funny Factor"]
            else:
                labels = ["Attenuator", "Name", "Material",
                          "Density (g/cm3)", "Thickness (cm)"]
        self.layerindex = layerindex
        self.matrixMode = matrixmode
        self.attenuators = attenuators
        self.verticalHeader().hide()
        _logger.debug("margin to adjust")
        _logger.debug("focus style")
        self.setFrameShape(qt.QTableWidget.NoFrame)
        self.setSelectionMode(qt.QTableWidget.NoSelection)
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[i])
            self.setHorizontalHeaderItem(i,item)
        if self.matrixMode:
            self.__build(len(attenuators))
        elif self.compoundMode:
            self.__build(len(attenuators))
        else:
            self.__build(len(attenuators0))
            #self.adjustColumn(0)
        if self.matrixMode:
            item = self.horizontalHeaderItem(0)
            item.setText('Layer')
            self.setHorizontalHeaderItem(0, item)
        if self.compoundMode:
            self.resizeColumnToContents(0)
            self.resizeColumnToContents(1)

        self.sigValueChanged[int,int].connect(self.mySlot)

    def __build(self, nfilters=13):
        n = 0
        if (not self.matrixMode) and (not self.compoundMode):
            n = len(self.__beamFilters0) + 2
            #self.setNumRows(nfilters+n)
            self.setRowCount(len(self.__attenuators0))
        else:
            self.setRowCount(nfilters)
        rheight = self.horizontalHeader().sizeHint().height()
        for idx in range(self.rowCount()):
            self.setRowHeight(idx, rheight)

        self.comboList = []
        matlist = list(Elements.Material.keys())
        matlist.sort()
        if self.matrixMode or self.compoundMode:
            if self.matrixMode:
                roottext = "Layer"
            else:
                roottext = "Compound%d" % self.layerindex
            a = []
            #a.append('')
            for key in matlist:
                a.append(key)
            for idx in range(self.rowCount()):
                item= qt.QCheckBox(self)
                self.setCellWidget(idx, 0, item)
                text = roottext+"%d" % idx
                item.setText(text)
                item = self.item(idx, 1)
                if item is None:
                    item = qt.QTableWidgetItem(text,
                                               qt.QTableWidgetItem.Type)
                    self.setItem(idx, 1, item)
                else:
                    item.setText(text)
                item.setFlags(qt.Qt.ItemIsSelectable|
                              qt.Qt.ItemIsEnabled)
                combo = MyQComboBox(self, options=a, row = idx, col = 2)
                combo.setEditable(True)
                self.setCellWidget(idx, 2, combo)
                combo.sigMaterialComboBoxSignal.connect(self._comboSlot)
            return
        selfnumRows = self.rowCount()

        for idx in range(selfnumRows - n):
            text = "Filter% 2d" % idx
            item = qt.QCheckBox(self)
            self.setCellWidget(idx, 0, item)
            item.setText(text)
            if idx < len(self.attenuators):
                text = self.attenuators[idx]

            item = self.item(idx, 1)
            if item is None:
                item = qt.QTableWidgetItem(text,
                                           qt.QTableWidgetItem.Type)
                self.setItem(idx, 1, item)
            else:
                item.setText(text)

            #a = qt.QStringList()
            a = []
            #a.append('')
            for key in matlist:
                a.append(key)
            combo = MyQComboBox(self, options=a, row=idx, col = 2)
            combo.setEditable(True)
            self.setCellWidget(idx, 2, combo)
            #self.setItem(idx,2,combo)
            combo.sigMaterialComboBoxSignal.connect(self._comboSlot)

        nBeamFilters = len(self.__beamFilters0)
        for i in range(nBeamFilters):
            #BeamFilter(i)
            item = qt.QCheckBox(self)
            idx = self.rowCount() - (n - i)
            self.setCellWidget(idx, 0, item)
            text = "BeamFilter%d" % i
            item.setText(text)

            item = self.item(idx,1)
            if item is None:
                item = qt.QTableWidgetItem(text,
                                           qt.QTableWidgetItem.Type)
                self.setItem(idx, 1, item)
            else:
                item.setText(text)
            item.setFlags(qt.Qt.ItemIsSelectable|
                          qt.Qt.ItemIsEnabled)

            text = "1.0"
            item = self.item(idx, 5)
            if item is None:
                item = qt.QTableWidgetItem(text,
                                           qt.QTableWidgetItem.Type)
                self.setItem(idx, 5, item)
            else:
                item.setText(text)
            item.setFlags(qt.Qt.ItemIsSelectable|
                          qt.Qt.ItemIsEnabled)

            combo = MyQComboBox(self, options=a, row=idx, col=2)
            combo.setEditable(True)
            self.setCellWidget(idx, 2, combo)
            combo.sigMaterialComboBoxSignal.connect(self._comboSlot)

        #Detector
        item = qt.QCheckBox(self)
        idx = self.rowCount() - 2
        self.setCellWidget(idx, 0, item)
        text = "Detector"
        item.setText(text)

        item = self.item(idx,1)
        if item is None:
            item = qt.QTableWidgetItem(text,
                                       qt.QTableWidgetItem.Type)
            self.setItem(idx, 1, item)
        else:
            item.setText(text)
        item.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)

        text = "1.0"
        item = self.item(idx, 5)
        if item is None:
            item = qt.QTableWidgetItem(text,
                                       qt.QTableWidgetItem.Type)
            self.setItem(idx, 5, item)
        else:
            item.setText(text)
        item.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)

        combo = MyQComboBox(self, options=a, row=idx, col=2)
        combo.setEditable(True)
        self.setCellWidget(idx, 2, combo)
        #Matrix
        item = qt.QCheckBox(self)
        idx = self.rowCount() - 1
        self.setCellWidget(idx, 0, item)
        text = "Matrix"
        item.setText(text)
        item = self.item(idx, 1)
        if item is None:
            item = qt.QTableWidgetItem(text,
                                       qt.QTableWidgetItem.Type)
            self.setItem(idx, 1, item)
        else:
            item.setText(text)
        item.setFlags(qt.Qt.ItemIsSelectable |qt.Qt.ItemIsEnabled)

        text = "1.0"
        item = self.item(idx, 5)
        if item is None:
            item = qt.QTableWidgetItem(text,
                                       qt.QTableWidgetItem.Type)
            self.setItem(idx, 5, item)
        else:
            item.setText(text)
        item.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)

        combo.sigMaterialComboBoxSignal.connect(self._comboSlot)

        #a = qt.QStringList()
        a = []
        #a.append('')
        for key in matlist:
            a.append(key)
        #combo = qttable.QComboTableItem(self,a)
        self.combo = MyQComboBox(self, options=a, row=idx, col=2)
        self.setCellWidget(idx, 2, self.combo)
        self.combo.sigMaterialComboBoxSignal.connect(self._comboSlot)

    def mySlot(self, row, col):
        _logger.debug("Value changed row = %d cole = &d", row, col)
        _logger.debug("Text = %s", self.text(row, col))

    def _comboSlot(self, ddict):
        _logger.debug("_comboSlot %s", ddict)
        row = ddict['row']
        col = ddict['col']
        text = ddict['text']
        self.setCurrentCell(row, col)
        self._checkDensityThickness(text, row)
        self.sigValueChanged.emit(row, col)

    def text(self, row, col):
        if col == 2:
            return self.cellWidget(row, col).currentText()
        else:
            if col not in [1, 3, 4, 5]:
                _logger.info("row, col = %d, %d", row, col)
                _logger.info("I should not be here")
            else:
                item = self.item(row, col)
                return item.text()

    def setText(self, row, col, text):
        if col == 0:
            self.cellWidget(row, 0).setText(text)
            return
        if col not in [1, 3, 4, 5]:
            _logger.warning("only compatible columns 1, 3 and 4")
            raise ValueError("method for column > 2")
        item = self.item(row, col)
        if item is None:
            item = qt.QTableWidgetItem(text,
                                       qt.QTableWidgetItem.Type)
            self.setItem(row, col, item)
        else:
            item.setText(text)

    def setCellWidget(self, row, col, w):
        QTable.setCellWidget(self, row, col, w)

    def _checkDensityThickness(self, text, row):
        try:
            currentDensity = float(str(self.text(row, 3)))
        except Exception:
            currentDensity = 0.0
        try:
            currentThickness = float(str(self.text(row, 4)))
        except Exception:
            currentThickness = 0.0
        defaultDensity = -1.0
        defaultThickness = -0.1
        #check if default density is there
        if Elements.isValidFormula(text):
            #check if single element
            if text in Elements.Element.keys():
                defaultDensity = Elements.Element[text]['density']
            else:
                elts = [ w for w in re.split('[0-9]', text) if w != '']
                nbs = [ int(w) for w in re.split('[a-zA-Z]', text) if w != '']
                if len(elts) == 1 and len(nbs) == 1:
                    defaultDensity = Elements.Element[elts[0]]['density']
        elif Elements.isValidMaterial(text):
            key = Elements.getMaterialKey(text)
            if key is not None:
                if 'Density' in Elements.Material[key]:
                    defaultDensity = Elements.Material[key]['Density']
                if 'Thickness' in Elements.Material[key]:
                    defaultThickness = Elements.Material[key]['Thickness']
        if defaultDensity >= 0.0:
            self.setText(row, 3, "%g" % defaultDensity)
        elif currentDensity <= 0:
            # should not be better to raise an exception if the
            # entered density or thickness were negative?
            self.setText(row, 3, "%g" % 1.0)
        if defaultThickness >= 0.0:
            self.setText(row, 4, "%g" % defaultThickness)
        elif currentThickness <= 0.0:
            # should not be better to raise an exception if the
            # entered density or thickness were negative?
            self.setText(row, 4, "%g" % 0.1)

class MyQComboBox(MaterialEditor.MaterialComboBox):
    def _mySignal(self, qstring0):
        qstring = qstring0
        (result, index) = self.ownValidator.validate(qstring, 0)
        if result != self.ownValidator.Valid:
            qstring = self.ownValidator.fixup(qstring)
            (result, index) = self.ownValidator.validate(qstring,0)
        if result != self.ownValidator.Valid:
            text = str(qstring)
            if text.upper() != "MULTILAYER":
                qt.QMessageBox.critical(self, "Invalid Material '%s'" % text,
                                        "The material '%s' is not a valid Formula " \
                                        "nor a valid Material.\n" \
                                        "Please define the material %s or correct the formula\n" % \
                                        (text, text))
                self.setCurrentIndex(0)
                for i in range(self.count()):
                    selftext = self.itemText(i)
                    if selftext == qstring0:
                        self.removeItem(i)
                        break
                return
        text = str(qstring)
        self.setCurrentText(text)
        ddict = {}
        ddict['event'] = 'activated'
        ddict['row'] = self.row
        ddict['col'] = self.col
        ddict['text'] = text
        if qstring0 != qstring:
            self.removeItem(self.count() - 1)
        insert = True
        for i in range(self.count()):
            selftext = self.itemText(i)
            if qstring == selftext:
                insert = False
        if insert:
            self.insertItem(-1, qstring)
        # signal defined in the superclass.
        self.sigMaterialComboBoxSignal.emit(ddict)

def main(args):
    app = qt.QApplication(args)
    #tab = AttenuatorsTableWidget(None)
    if len(args) < 2:
        tab = AttenuatorsTab(None)
    elif len(args) > 3:
        tab = CompoundFittingTab(None)
    else:
        tab = MultilayerTab(None)
    tab.show()
    app.exec()


if __name__=="__main__":
    main(sys.argv)

