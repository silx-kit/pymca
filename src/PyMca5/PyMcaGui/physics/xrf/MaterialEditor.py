#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF.
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
import os
import copy
import logging
import numpy
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaPhysics import Elements
from PyMca5.PyMcaGui.plotting import PlotWindow
ScanWindow = PlotWindow.PlotWindow


_logger = logging.getLogger(__name__)


class MaterialEditor(qt.QWidget):
    def __init__(self, parent=None, name="Material Editor",
                 comments=True, height= 7, graph=None, toolmode=False):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        if graph is None:
            self.graph = None
            self.graphDialog = None
        else:
            if isinstance(graph, qt.QDialog):
                self.graphDialog = graph
                self.graph = self.graphDialog.graph
            else:
                self.graphDialog = None
                self.graph = graph
        self.__toolMode = toolmode
        self.build(comments, height)

    def build(self,comments, height):
        a = []
        for key in Elements.Material.keys():
            a.append(key)
        a.sort()

        if self.__toolMode:
            layout = qt.QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            layout = qt.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.__hboxMaterialCombo   = qt.QWidget(self)
            hbox = self.__hboxMaterialCombo
            hboxlayout = qt.QHBoxLayout(hbox)
            hboxlayout.setContentsMargins(0, 0, 0, 0)
            hboxlayout.setSpacing(0)
            label = qt.QLabel(hbox)
            label.setText("Enter name of material to be defined:")
            self.matCombo = MaterialComboBox(hbox,options=a)
            hboxlayout.addWidget(label)
            hboxlayout.addWidget(self.matCombo)
            layout.addWidget(hbox)

            #self.matCombo.setEditable(True)
            self.matCombo.sigMaterialComboBoxSignal.connect( \
                         self._comboSlot)

        self.materialGUI = MaterialGUI(self, comments=comments,
                                       height=height, toolmode=self.__toolMode)
        self.materialGUI.sigMaterialTransmissionSignal.connect( \
                     self._transmissionSlot)
        self.materialGUI.sigMaterialMassAttenuationSignal.connect( \
                     self._massAttenuationSlot)
        if self.__toolMode:
            self.materialGUI.setCurrent(a[0])
            if (self.graph is None):
                self.graph = ScanWindow(self, newplot=False,
                                        fit=False,
                                        plugins=False,
                                        control=True,
                                        position=True)
                self.graph._togglePointsSignal()
                self.graph.enableOwnSave(True)
                self.graph.setDataMargins(0, 0, 0.025, 0.025)
            layout.addWidget(self.materialGUI)
            layout.addWidget(self.graph)
        else:
            self.materialGUI.setCurrent(a[0])
            layout.addWidget(self.materialGUI)

    def importFile(self, filename):
        if not os.path.exists(filename):
            qt.QMessageBox.critical(self, "ERROR opening file",
                                    "File %s not found" % filename)
            return 1
        Elements.Material.read(filename)
        error = 0
        for material in list(Elements.Material.keys()):
            keys = list(Elements.Material[material].keys())
            compoundList = []
            if "CompoundList" in  keys:
                compoundList = Elements.Material[material]["CompoundList"]
            if "CompoundFraction" in  keys:
                compoundFraction = Elements.Material[material]["CompoundFraction"]
            if  (compoundList == []) or (compoundFraction == []):
                #no message?
                error = 1
                del Elements.Material[material]
                continue
            #I should try to calculate the attenuation at one energy ...
            try:
                Elements.getMaterialMassAttenuationCoefficients(compoundList,
                                                                compoundFraction,
                                                                energy = 10.0)
            except Exception:
                #no message?
                error = 1
                del Elements.Material[material]
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                continue
        return error

    def _comboSlot(self, ddict):
        self.materialGUI.setCurrent(ddict['text'])

    def _addGraphDialogButton(self):
        self.graphDialog.okButton = qt.QPushButton(self.graphDialog)
        self.graphDialog.okButton.setText('OK')
        self.graphDialog.okButton.setAutoDefault(True)
        self.graphDialog.mainLayout.addWidget(self.graphDialog.okButton)
        self.graphDialog.okButton.clicked.connect( \
                                 self.graphDialog.accept)


    def _transmissionSlot(self, ddict):
        try:
            compoundList = ddict['CompoundList']
            fractionList = ddict['CompoundFraction']
            density = ddict['Density']
            thickness = ddict.get('Thickness', 0.1)
            energy = numpy.arange(1, 100, 0.1)
            data=Elements.getMaterialTransmission(compoundList, fractionList, energy,
                                             density=density, thickness=thickness, listoutput=False)
            addButton = False
            if self.graph is None:
                # probably dead code (ScanWindow not imported)
                self.graphDialog = qt.QDialog(self)
                self.graphDialog.mainLayout = qt.QVBoxLayout(self.graphDialog)
                self.graphDialog.mainLayout.setContentsMargins(0, 0, 0, 0)
                self.graphDialog.mainLayout.setSpacing(0)
                #self.graph = ScanWindow.ScanWindow(self.graphDialog)
                self.graph = ScanWindow(self.graphDialog)
                self.graphDialog.mainLayout.addWidget(self.graph)
                self.graph._togglePointsSignal()
                self.graph.graph.crossPicker.setEnabled(False)
                addButton = True
            if addButton:
                self._addGraphDialogButton()
            if self.__toolMode:
                legend = ddict['Comment']
            else:
                legend = str(self.matCombo.currentText()) +\
                         " with density = %f g/cm3" % density +\
                         " and thickness = %f cm" % thickness
            self.graph.addCurve(energy, data['transmission'],
                                legend=legend,
                                xlabel='Energy (keV)',
                                ylabel='Transmission',
                                replace=True)
            self.graph.setGraphTitle(ddict['Comment'])
            if self.graphDialog is not None:
                self.graphDialog.exec()
        except Exception:
            msg=qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _massAttenuationSlot(self, ddict):
        try:
            compoundList = ddict['CompoundList']
            fractionList = ddict['CompoundFraction']
            energy = numpy.arange(1, 100, 0.1)
            data=Elements.getMaterialMassAttenuationCoefficients(compoundList,
                                                                 fractionList,
                                                                 energy)
            addButton = False
            if self.graph is None:
                # probably dead code (ScanWindow.ScanWindow not imported)
                self.graphDialog = qt.QDialog(self)
                self.graphDialog.mainLayout = qt.QVBoxLayout(self.graphDialog)
                self.graphDialog.mainLayout.setContentsMargins(0, 0, 0, 0)
                self.graphDialog.mainLayout.setSpacing(0)
                #self.graph = ScanWindow.ScanWindow(self.graphDialog)
                self.graph = ScanWindow(self.graphDialog)
                self.graphDialog.mainLayout.addWidget(self.graph)
                self.graph._togglePointsSignal()
                self.graph.graph.crossPicker.setEnabled(False)
                addButton = True
            if addButton:
                self._addGraphDialogButton()
            self.graph.setGraphTitle(ddict['Comment'])
            legend = 'Coherent'
            self.graph.addCurve(energy, numpy.array(data[legend.lower()]),
                                legend=legend,
                                xlabel='Energy (keV)',
                                ylabel='Mass Att. (cm2/g)',
                                replace=True,
                                replot=False)
            for legend in ['Compton', 'Photo','Total']:
                self.graph.addCurve(energy, numpy.array(data[legend.lower()]),
                                    legend=legend,
                                    xlabel='Energy (keV)',
                                    ylabel='Mass Att. (cm2/g)',
                                    replace=False,
                                    replot=False)
            self.graph.setActiveCurve(legend+' '+'Mass Att. (cm2/g)')
            self.graph.setGraphTitle(ddict['Comment'])
            if self.graphDialog is not None:
                self.graphDialog.exec()
        except Exception:
            msg=qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def closeEvent(self, event):
        if self.graph is not None:
            self.graph.close()
        qt.QWidget.closeEvent(self, event)

    def show(self):
        if self.graph is not None:
            if self.graph.isHidden():
                self.graph.show()
        qt.QWidget.show(self)

class MaterialComboBox(qt.QComboBox):
    sigMaterialComboBoxSignal = qt.pyqtSignal(object)
    def __init__(self,parent=None,name = None,fl = 0,
                 options=['1','2','3'],row=None,col=None):
        if row is None: row = 0
        if col is None: col = 0
        self.row = row
        self.col = col
        qt.QComboBox.__init__(self,parent)
        self.setOptions(options)
        self.ownValidator = MaterialValidator(self)
        self.setDuplicatesEnabled(False)
        self.setEditable(True)
        self._line = self.lineEdit()
        self.lastText = "_U_N1iKeLyText"
        if hasattr(self, "textActivated"):
            self.textActivated[str].connect(self._mySignal)
        else:
            self.activated[str].connect(self._mySignal)
        self._line.editingFinished.connect(self._mySlot)

    def setCurrentText(self, qstring):
        qt.QComboBox.setEditText(self, qstring)

    def setOptions(self,options=['1','2','3']):
        self.clear()
        for item in options:
            self.addItem(item)

    def getCurrent(self):
        return   self.currentIndex(),str(self.currentText())

    def _mySignal(self, qstring0):
        qstring = qstring0
        text = str(qstring0)
        if text == '-':
            return
        (result, index) = self.ownValidator.validate(qstring,0)
        if result != self.ownValidator.Valid:
            qstring = self.ownValidator.fixup(qstring)
            (result, index) = self.ownValidator.validate(qstring,0)
        if result != self.ownValidator.Valid:
            text = str(qstring)
            if "%" in text:
                msg =  qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Material Name '%s'\n" % text + \
                            "It contains a % character.\n")
                msg.exec()
                msg = qt.QMessageBox.No
            elif text.endswith(" ") or text.startswith(" "):
                msg =  qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Material Name '%s'\n" % text + \
                            "It starts or ends with a space character.\n")
                msg.exec()
                msg = qt.QMessageBox.No
            else:
                try:
                    # this test is needed even if pyflakes complains
                    float(text)
                    msg =  qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Invalid Material Name %s\n" % text + \
                                "You cannot use a number as material name.\n" +\
                                "Hint: You can use _%s_" % text)
                    msg.exec()
                    msg = qt.QMessageBox.No
                except Exception:
                    msg=qt.QMessageBox.information( self, "Invalid Material %s" % str(qstring),
                                          "The material %s is not a valid Formula " \
                                          "nor a valid Material.\n" \
                                          "Do you want to define the material %s\n" % \
                                          (str(qstring), str(qstring)),
                                          qt.QMessageBox.Yes,qt.QMessageBox.No)
            if msg == qt.QMessageBox.No:
                self.setCurrentIndex(0)
                for i in range(self.count()):
                    selftext = self.itemText(i)
                    if selftext == qstring0:
                        self.removeItem(i)
                return
            else:
                qstring = qstring0
        text = str(qstring)

        if Elements.isValidFormula(text):
            msg =  qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Material Name %s\n" % text + \
                        "The material is a valid Formula.\n " \
                        "There is no need to define it.")
            msg.exec()
            self.setCurrentIndex(0)
            for i in range(self.count()):
                selftext = self.itemText(i)
                if selftext == qstring0:
                    self.removeItem(i)
                    break
            return
        self.setCurrentText(text)
        self.lastText = text
        ddict = {}
        ddict['event'] = 'activated'
        ddict['row']   = self.row
        ddict['col']   = self.col
        ddict['text']  = text
        if qstring0 != qstring:
            self.removeItem(self.count()-1)

        insert = True
        for i in range(self.count()):
            selftext = self.itemText(i)
            if qstring == selftext:
                insert = False
        if insert:
            self.insertItem(self.count(), qstring)

        self.sigMaterialComboBoxSignal.emit(ddict)

    def _mySlot(self):
        current = str(self.currentText())
        if current != self.lastText:
            self._mySignal(self.currentText())

class MaterialValidator(qt.QValidator):
    def __init__(self, *var):
        qt.QValidator.__init__(self, *var)
        if hasattr(self, "Acceptable"):
            self.Valid = self.Acceptable
        else:
            self.Valid = qt.QValidator.State.Acceptable
        if not hasattr(self, "Invalid"):
            self.Invalid = qt.QValidator.State.Invalid

    def fixup(self, qstring):
        if qstring is None:
            return None
        text = str(qstring)
        key  = Elements.getMaterialKey(text)
        if key is not None:
            return str(key)
        else:
            return qstring

    def validate(self, qstring, pos):
        text = str(qstring)
        if "%" in text:
            return (self.Invalid, pos)
        if text == '-':
            return (self.Valid, pos)
        try:
            # this test is needed even if pyflakes complains!
            float(text)
            return (self.Invalid, pos)
        except Exception:
            pass
        if text.endswith(' '):
            return (self.Invalid, pos)
        if Elements.isValidFormula(text):
            return (self.Valid, pos)
        elif Elements.isValidMaterial(text):
            return (self.Valid, pos)
        else:
            return (self.Invalid,pos)

class MaterialGUI(qt.QWidget):
    sigMaterialMassAttenuationSignal = qt.pyqtSignal(object)
    sigMaterialTransmissionSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="New Material",default=None,
                 comments=True, height=10, toolmode=False):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        if default is None:
            default = {}
        self._default = default
        self._setCurrentDefault()
        for key in default.keys():
            if key in self._current:
                self._current[key] = self._default[key]
        self.__lastRow    = None
        self.__lastColumn = None
        self.__fillingValues = True
        self.__toolMode = toolmode
        if toolmode:
            self.buildToolMode(comments,height)
        else:
            self.build(comments,height)

    def _setCurrentDefault(self):
        self._current = {'Comment':"New Material",
                         'CompoundList':[],
                         'CompoundFraction':[1.0],
                         'Density':1.0,
                         'Thickness':1.0}

    def build(self,comments="True",height=3):
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.__comments = comments
        commentsHBox   = qt.QWidget(self)
        layout.addWidget(commentsHBox)
        commentsHBoxLayout = qt.QHBoxLayout(commentsHBox)
        commentsHBoxLayout.setContentsMargins(0, 0, 0, 0)
        commentsHBoxLayout.setSpacing(0)

        tableContainer = qt.QWidget(commentsHBox)
        commentsHBoxLayout.addWidget(tableContainer)
        tableContainerLayout = qt.QVBoxLayout(tableContainer)
        tableContainerLayout.setContentsMargins(0, 0, 0, 0)
        tableContainerLayout.setSpacing(0)
        self.__hboxTableContainer = qt.QWidget(tableContainer)
        hbox = self.__hboxTableContainer
        tableContainerLayout.addWidget(hbox)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(0)
        numberLabel  = qt.QLabel(hbox)
        hboxLayout.addWidget(numberLabel)
        numberLabel.setText("Number  of  Compounds:")
        numberLabel.setAlignment(qt.Qt.AlignVCenter)
        self.__numberSpin  = qt.QSpinBox(hbox)
        hboxLayout.addWidget(self.__numberSpin)
        self.__numberSpin.setMinimum(1)
        self.__numberSpin.setMaximum(100)
        self.__numberSpin.setValue(1)
        self.__table = qt.QTableWidget(tableContainer)
        self.__table.setRowCount(1)
        self.__table.setColumnCount(2)
        tableContainerLayout.addWidget(self.__table)
        self.__table.setMinimumHeight((height)*self.__table.horizontalHeader().sizeHint().height())
        self.__table.setMaximumHeight((height)*self.__table.horizontalHeader().sizeHint().height())
        self.__table.setMinimumWidth(1*self.__table.sizeHint().width())
        self.__table.setMaximumWidth(1*self.__table.sizeHint().width())
        #self.__table.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,qt.QSizePolicy.Fixed))
        labels = ["Material", "Mass Fraction"]
        for i in range(len(labels)):
            item = self.__table.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],qt.QTableWidgetItem.Type)
            self.__table.setHorizontalHeaderItem(i,item)
        self.__table.setSelectionMode(qt.QTableWidget.NoSelection)
        if self.__comments:
            vbox = qt.QWidget(commentsHBox)
            commentsHBoxLayout.addWidget(vbox)
            vboxLayout = qt.QVBoxLayout(vbox)

            #default thickness and density
            self.__gridVBox = qt.QWidget(vbox)
            grid = self.__gridVBox
            vboxLayout.addWidget(grid)
            gridLayout = qt.QGridLayout(grid)
            gridLayout.setContentsMargins(11, 11, 11, 11)
            gridLayout.setSpacing(4)

            densityLabel  = qt.QLabel(grid)
            gridLayout.addWidget(densityLabel, 0, 0)
            densityLabel.setText("Default Density (g/cm3):")
            densityLabel.setAlignment(qt.Qt.AlignVCenter)
            self.__densityLine  = qt.QLineEdit(grid)
            validator = qt.CLocaleQDoubleValidator(self.__densityLine)
            self.__densityLine.setValidator(validator)

            self.__densityLine.setReadOnly(False)
            gridLayout.addWidget(self.__densityLine, 0, 1)

            thicknessLabel  = qt.QLabel(grid)
            gridLayout.addWidget(thicknessLabel, 1, 0)
            thicknessLabel.setText("Default  Thickness  (cm):")
            thicknessLabel.setAlignment(qt.Qt.AlignVCenter)
            self.__thicknessLine  = qt.QLineEdit(grid)
            validator = qt.CLocaleQDoubleValidator(self.__thicknessLine)
            self.__thicknessLine.setValidator(validator)

            gridLayout.addWidget(self.__thicknessLine, 1, 1)
            self.__thicknessLine.setReadOnly(False)
            self.__densityLine.editingFinished[()].connect( \
                         self.__densitySlot)
            self.__thicknessLine.editingFinished[()].connect( \
                     self.__thicknessSlot)

            self.__transmissionButton = qt.QPushButton(grid)
            self.__transmissionButton.setText('Material Transmission')
            gridLayout.addWidget(self.__transmissionButton, 2, 0)
            self.__massAttButton = qt.QPushButton(grid)
            self.__massAttButton.setText('Mass Att. Coefficients')
            gridLayout.addWidget(self.__massAttButton, 2, 1)
            self.__transmissionButton.setAutoDefault(False)
            self.__massAttButton.setAutoDefault(False)

            self.__transmissionButton.clicked.connect(
                         self.__transmissionSlot)
            self.__massAttButton.clicked.connect(
                         self.__massAttSlot)
            vboxLayout.addWidget(qt.VerticalSpacer(vbox))

        if self.__comments:
            #comment
            nameHBox       = qt.QWidget(self)
            nameHBoxLayout = qt.QHBoxLayout(nameHBox)
            nameLabel      = qt.QLabel(nameHBox)
            nameHBoxLayout.addWidget(nameLabel)
            nameLabel.setText("Material Name/Comment:")
            nameLabel.setAlignment(qt.Qt.AlignVCenter)
            nameHBoxLayout.addWidget(qt.HorizontalSpacer(nameHBox))
            self.__nameLine  = qt.QLineEdit(nameHBox)
            self.__nameLine.editingFinished[()].connect(self.__nameLineSlot)
            nameHBoxLayout.addWidget(self.__nameLine)
            self.__nameLine.setReadOnly(False)
            longtext="En un lugar de La Mancha, de cuyo nombre no quiero acordarme ..."
            self.__nameLine.setFixedWidth(self.__nameLine.fontMetrics().maxWidth()*len(longtext))
            layout.addWidget(nameHBox)

        self.__numberSpin.valueChanged[int].connect(self.__numberSpinChanged)
        self.__table.cellChanged[int,int].connect(self.__tableSlot)
        self.__table.cellEntered[int,int].connect(self.__tableSlot2)

    def buildToolMode(self, comments="True",height=3):
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.__comments = comments
        grid = qt.QWidget(self)
        gridLayout = qt.QGridLayout(grid)
        gridLayout.setContentsMargins(11, 11, 11, 11)
        gridLayout.setSpacing(4)
        numberLabel  = qt.QLabel(grid)
        numberLabel.setText("Number  of  Compounds:")
        numberLabel.setAlignment(qt.Qt.AlignVCenter)
        self.__numberSpin  = qt.QSpinBox(grid)
        self.__numberSpin.setMinimum(1)
        self.__numberSpin.setMaximum(30)
        self.__numberSpin.setValue(1)

        tableContainer = qt.QWidget(self)
        tableContainerLayout = qt.QVBoxLayout(tableContainer)
        tableContainerLayout.setContentsMargins(0, 0, 0, 0)
        tableContainerLayout.setSpacing(0)
        self.__tableContainer = tableContainer

        self.__table = qt.QTableWidget(tableContainer)
        self.__table.setRowCount(1)
        self.__table.setColumnCount(2)
        tableContainerLayout.addWidget(self.__table)
        self.__table.setMinimumHeight((height)*self.__table.horizontalHeader().sizeHint().height())
        self.__table.setMaximumHeight((height)*self.__table.horizontalHeader().sizeHint().height())
        self.__table.setMinimumWidth(1*self.__table.sizeHint().width())
        self.__table.setMaximumWidth(1*self.__table.sizeHint().width())
        labels = ["Material", "Mass Fraction"]
        for i in range(len(labels)):
            item = self.__table.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],qt.QTableWidgetItem.Type)
            self.__table.setHorizontalHeaderItem(i,item)
        self.__table.setSelectionMode(qt.QTableWidget.NoSelection)


        densityLabel  = qt.QLabel(grid)
        densityLabel.setText("Density (g/cm3):")
        densityLabel.setAlignment(qt.Qt.AlignVCenter)
        self.__densityLine  = qt.QLineEdit(grid)
        self.__densityLine.setText("1.0")
        validator = qt.CLocaleQDoubleValidator(self.__densityLine)
        self.__densityLine.setValidator(validator)
        self.__densityLine.setReadOnly(False)

        thicknessLabel  = qt.QLabel(grid)
        thicknessLabel.setText("Thickness  (cm):")
        thicknessLabel.setAlignment(qt.Qt.AlignVCenter)
        self.__thicknessLine  = qt.QLineEdit(grid)
        self.__thicknessLine.setText("0.1")
        validator = qt.CLocaleQDoubleValidator(self.__thicknessLine)
        self.__thicknessLine.setValidator(validator)
        self.__thicknessLine.setReadOnly(False)

        self.__transmissionButton = qt.QPushButton(grid)
        self.__transmissionButton.setText('Material Transmission')
        self.__massAttButton = qt.QPushButton(grid)
        self.__massAttButton.setText('Mass Att. Coefficients')
        self.__transmissionButton.setAutoDefault(False)
        self.__massAttButton.setAutoDefault(False)


        nameHBox       = qt.QWidget(grid)
        nameHBoxLayout = qt.QHBoxLayout(nameHBox)
        nameHBoxLayout.setContentsMargins(0, 0, 0, 0)
        nameHBoxLayout.setSpacing(0)
        nameLabel      = qt.QLabel(nameHBox)
        nameLabel.setText("Name:")
        nameLabel.setAlignment(qt.Qt.AlignVCenter)
        self.__nameLine  = qt.QLineEdit(nameHBox)
        self.__nameLine.setReadOnly(False)
        if self.__toolMode:
            toolTip  = "Type your material name and press the ENTER key.\n"
            toolTip += "Fitting materials cannot be defined or redefined here.\n"
            toolTip += "Use the material editor of the advanced fit for it.\n"
            self.__nameLine.setToolTip(toolTip)

        nameHBoxLayout.addWidget(nameLabel)
        nameHBoxLayout.addWidget(self.__nameLine)
        gridLayout.addWidget(nameHBox, 0, 0, 1, 2)
        gridLayout.addWidget(numberLabel, 1, 0)
        gridLayout.addWidget(self.__numberSpin, 1, 1)
        gridLayout.addWidget(self.__tableContainer, 2, 0, 1, 2)
        gridLayout.addWidget(densityLabel, 3, 0)
        gridLayout.addWidget(self.__densityLine, 3, 1)
        gridLayout.addWidget(thicknessLabel, 4, 0)
        gridLayout.addWidget(self.__thicknessLine, 4, 1)
        gridLayout.addWidget(self.__transmissionButton, 5, 0)
        gridLayout.addWidget(self.__massAttButton, 5, 1)
        layout.addWidget(grid)
        layout.addWidget(qt.VerticalSpacer(self))

        #build all the connections
        self.__nameLine.editingFinished[()].connect(self.__nameLineSlot)

        self.__numberSpin.valueChanged[int].connect(self.__numberSpinChanged)

        self.__table.cellChanged[int,int].connect(self.__tableSlot)
        self.__table.cellEntered[int,int].connect(self.__tableSlot2)

        self.__densityLine.editingFinished[()].connect( self.__densitySlot)

        self.__thicknessLine.editingFinished[()].connect(self.__thicknessSlot)

        self.__transmissionButton.clicked.connect(self.__transmissionSlot)

        self.__massAttButton.clicked.connect(self.__massAttSlot)

    def setCurrent(self, matkey0):
        _logger.debug("setCurrent(self, matkey0=%s)", matkey0)
        matkey = Elements.getMaterialKey(matkey0)
        if self._default == {}:
            firstTime = True
        else:
            firstTime = False
        if matkey is not None:
            if self.__toolMode:
                #make sure the material CANNOT be modified
                self._current = copy.deepcopy(Elements.Material[matkey])
                if self.__table.isEnabled():
                    self.__disableInput()
            else:
                self._current = Elements.Material[matkey]
        else:
            self._setCurrentDefault()
            if not self.__toolMode:
                Elements.Material[matkey0] = self._current
        self.__numberSpin.setFocus()
        try:
            self._fillValues()
            self._updateCurrent()
        finally:
            if self.__toolMode:
                self.__nameLine.setText("%s" % matkey)
            self.__fillingValues = False
        if firstTime:
            self.__table.resizeColumnToContents(0)

    def _fillValues(self):
        _logger.debug("fillValues(self)")
        self.__fillingValues = True
        if self.__comments:
            self.__nameLine.setText("%s" % self._current['Comment'])
            try:
                self.__densityLine.setText("%.5g" % self._current['Density'])
            except Exception:
                self.__densityLine.setText("")
            if 'Thickness' in self._current.keys():
                try:
                    self.__thicknessLine.setText("%.5g" % self._current['Thickness'])
                except Exception:
                    self.__thicknessLine.setText("")
        if type(self._current['CompoundList']) != type([]):
            self._current['CompoundList'] = [self._current['CompoundList']]
        if type(self._current['CompoundFraction']) != type([]):
            self._current['CompoundFraction'] = [self._current['CompoundFraction']]
        self.__numberSpin.setValue(max(len(self._current['CompoundList']),1))
        row = 0
        for compound in  self._current['CompoundList']:
            item = self.__table.item(row,0)
            if item is None:
                item = qt.QTableWidgetItem(compound,qt.QTableWidgetItem.Type)
                self.__table.setItem(row,0,item)
            else:
                item.setText(compound)
            item = self.__table.item(row,1)
            if item is None:
                item = qt.QTableWidgetItem("%.5g" % self._current['CompoundFraction'][row],
                                           qt.QTableWidgetItem.Type)
                self.__table.setItem(row,1,item)
            else:
                item.setText("%.5g" % self._current['CompoundFraction'][row])
            row += 1
        self.__fillingValues = False

    # http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=666503
    def _updateCurrent(self):
        _logger.debug("updateCurrent(self)")
        _logger.debug("self._current before = %s", self._current)

        self._current['CompoundList']     = []
        self._current['CompoundFraction'] = []
        for i in range(self.__table.rowCount()):
            item = self.__table.item(i, 0)
            if item is None:
                item = qt.QTableWidgetItem("",
                                           qt.QTableWidgetItem.Type)
            txt0 = str(item.text())
            item = self.__table.item(i, 1)
            if item is None:
                item = qt.QTableWidgetItem("",
                                           qt.QTableWidgetItem.Type)
            txt1 = str(item.text())
            if (len(txt0) > 0) and (len(txt1) > 0):
                self._current['CompoundList'].append(txt0)
                self._current['CompoundFraction'].append(float(txt1))
        self.__densitySlot(silent=True)
        self.__thicknessSlot(silent=True)
        _logger.debug("self._current after = %s", self._current)

    def __densitySlot(self, silent=False):
        try:
            qstring = self.__densityLine.text()
            text = str(qstring)
            if len(text):
                value = float(str(qstring))
                self._current['Density'] = value
        except Exception:
            if silent:
                return
            msg=qt.QMessageBox(self.__densityLine)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.__densityLine.setFocus()

    def __thicknessSlot(self, silent=False):
        try:
            qstring = self.__thicknessLine.text()
            text = str(qstring)
            if len(text):
                value = float(text)
                self._current['Thickness'] = value
        except Exception:
            if silent:
                return
            msg=qt.QMessageBox(self.__thicknessLine)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.__thicknessLine.setFocus()

    def __transmissionSlot(self):
        ddict = {}
        ddict.update(self._current)
        ddict['event'] = 'MaterialTransmission'
        self.sigMaterialTransmissionSignal.emit(ddict)


    def __massAttSlot(self):
        ddict = {}
        ddict.update(self._current)
        ddict['event'] = 'MaterialMassAttenuation'
        self.sigMaterialMassAttenuationSignal.emit(ddict)

    def __nameLineSlot(self):
        _logger.debug("__nameLineSlot(self)")
        qstring = self.__nameLine.text()
        text = str(qstring)
        if self.__toolMode:
            if len(text):
                matkey = Elements.getMaterialKey(text)
            if matkey is not None:
                self.setCurrent(matkey)
                #Disable everything
                self.__disableInput()
            elif text in Elements.ElementList:
                self.__disableInput()
                name = Elements.Element[text]['name']
                self._current['Comment'] = name[0].upper() + name[1:]
                self._current['CompoundList'] = [text+"1"]
                self._current['CompoundFraction'] = [1.0]
                self._current['Density'] = Elements.Element[text]['density']
                self._fillValues()
                self._updateCurrent()
                self.__nameLine.setText("%s" % text)
            else:
                self._current['Comment'] = text
                self.__numberSpin.setEnabled(True)
                self.__table.setEnabled(True)
                self.__densityLine.setEnabled(True)
                self.__thicknessLine.setEnabled(True)
        else:
            self._current['Comment'] = text

    def __disableInput(self):
        self.__numberSpin.setEnabled(False)
        self.__table.setEnabled(False)
        self.__densityLine.setEnabled(False)
        self.__thicknessLine.setEnabled(True)

    def __numberSpinChanged(self,value):
        #size = self.__table.size()
        self.__table.setRowCount(value)
        rheight = self.__table.horizontalHeader().sizeHint().height()
        nrows = self.__table.rowCount()
        for idx in range(nrows):
            self.__table.setRowHeight(idx, rheight)
        if len(self._current['CompoundList']) > value:
            self._current['CompoundList'] = self._current['CompoundList'][0:value]
        if len(self._current['CompoundFraction']) > value:
            self._current['CompoundFraction'] = self._current['CompoundFraction'][0:value]

    def __tableSlot(self,row, col):
        if self.__fillingValues:
            return
        item = self.__table.item(row, col)
        if item is not None:
            _logger.debug("table item is None")
            qstring = item.text()
        else:
            qstring = ""
        if col == 0:
            compound = str(qstring)
            if Elements.isValidFormula(compound):
                pass
            else:
                matkey  = Elements.getMaterialKey(compound)
                if matkey is not None:
                    item.setText(matkey)
                else:
                    msg=qt.QMessageBox(self.__table)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Invalid Formula %s" % compound)
                    msg.exec()
                    self.__table.setCurrentCell(row, col)
                    return
        else:
            try:
                float(str(qstring))
            except Exception:
                msg=qt.QMessageBox(self.__table)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Float")
                msg.exec()
                self.__table.setCurrentCell(row, col)
                return
        self._updateCurrent()

    def __tableSlot2(self,row, col):
        if self.__fillingValues:return
        if self.__lastRow is None:
            self.__lastRow = row

        if self.__lastColumn is None:
            self.__lastColumn = col

        item = self.__table.item(self.__lastRow,
                                self.__lastColumn)
        if item is None:
            item = qt.QTableWidgetItem("",qt.QTableWidgetItem.Type)
            self.__table.setItem(self.__lastRow,
                                 self.__lastColumn,
                                 item)
        qstring = item.text()

        if self.__lastColumn == 0:
            compound     = str(qstring)
            if Elements.isValidFormula(compound):
                pass
            else:
                matkey  = Elements.getMaterialKey(compound)
                if matkey is not None:
                    item = self.__table.item(self.__lastRow,
                                        self.__lastColumn)
                    if item is None:
                        item = qt.QTableWidgetItem(matkey,
                                        qt.QTableWidgetItem.Type)
                        self.__table.setItem(self.__lastRow,
                                         self.__lastColumn,
                                         item)
                    else:
                        item.setText(matkey)
                else:
                    msg=qt.QMessageBox(self.__table)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Invalid Formula %s" % compound)
                    msg.exec()
                    self.__table.setCurrentCell(self.__lastRow, self.__lastColumn)
                    return
        else:
            try:
                float(str(qstring))
            except Exception:
                msg=qt.QMessageBox(self.__table)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Float")
                msg.exec()
                self.__table.setCurrentCell(self.__lastRow, self.__lastColumn)
                return
        self._updateCurrent()

if __name__ == "__main__":
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    if len(sys.argv) > 1:
        demo = MaterialEditor(toolmode=True)
    else:
        demo = MaterialEditor(toolmode=False)
    demo.show()
    ret  = app.exec()
    app = None
