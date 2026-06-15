# -*- coding: utf-8 -*-
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
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaPhysics.xrf import Elements
from PyMca5.PyMcaGui.physics.xrf import MatrixImage
from PyMca5.PyMcaGui.physics.xrf import MaterialEditor
from PyMca5.PyMcaIO import ConfigDict

qstring = str

_logger = logging.getLogger(__name__)


class SampleConfiguration(qt.QWidget):
    def __init__(self, parent=None,orientation="vertical"):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.setContentsMargins(0, 0, 0, 0)
        # material
        materialLabel = qt.QLabel(self)
        materialLabel.setText("Enter material name or formula")
        self.materialWidget = qt.QComboBox(self)
        self.materialWidget.setEditable(True)
        i = 0
        for key in Elements.Material.keys():
            self.materialWidget.insertItem(i + 1, qstring(key))
            i += 1
        self.materialWidget.setEditText("Fe")
        self.editorButton = qt.QPushButton(self)
        self.editorButton.setText("Show/Hide Editor")
        self.editorButton.setAutoDefault(False)
        self.mainLayout.addWidget(materialLabel, 0, 0, 1, 3)
        self.mainLayout.addWidget(self.materialWidget, 0, 2)
        self.mainLayout.addWidget(self.editorButton, 0, 3)
        self.materialEditor = MaterialEditor.MaterialEditor(self)
        offset = 1
        self.mainLayout.addWidget(self.materialEditor, offset, 0, 5, 4)
        offset += 5
        #element
        elementLabel = qt.QLabel(self)
        elementLabel.setText("Element")
        elementWidget = qt.QComboBox(self)
        for i, symbol in enumerate(Elements.ElementList[2:]):
            elementWidget.insertItem(i + 1,
                                         qstring(symbol + "(%d)" % (i+3)))
        edgeLabel = qt.QLabel(self)
        edgeLabel.setText("Edge")
        edgeWidget = qt.QComboBox(self)
        self.edgeWidget = edgeWidget
        self.elementWidget = elementWidget
        energyLabel = qt.QLabel(self)
        energyLabel.setText("Energy (eV)")
        self.energyWidget = qt.QLineEdit(self)
        self.energyWidget._validator = qt.CLocaleQDoubleValidator(self.energyWidget)
        self.energyWidget.setValidator(self.energyWidget._validator)
        if orientation.lower().startswith("v"):
            self.mainLayout.addWidget(elementLabel, 0, 0)
            self.mainLayout.addWidget(elementWidget, 0, 1)
            self.mainLayout.addWidget(edgeLabel, 1, 0)
            self.mainLayout.addWidget(edgeWidget, 1, 1)
            self.mainLayout.addWidget(energyLabel, 2, 0)
            self.mainLayout.addWidget(self.energyWidget, 2, 1)
            #self.mainLayout.addWidget(qt.HorizontalSpacer(self), 3, 2)
        else:
            self.mainLayout.addWidget(elementLabel, offset + 0, 0)
            self.mainLayout.addWidget(elementWidget, offset + 1, 0)
            self.mainLayout.addWidget(edgeLabel, offset + 0, 1)
            self.mainLayout.addWidget(edgeWidget, offset + 1, 1)
            self.mainLayout.addWidget(energyLabel, offset + 0, 2, 1, 2)
            self.mainLayout.addWidget(self.energyWidget, offset + 1, 2, 1, 2)
            #self.mainLayout.addWidget(qt.HorizontalSpacer(self), 0, 3)
        self.editorButton.clicked.connect(self.toggleEditor)
        self.toggleEditor()
        self._lastMaterial = "Fe"
        self.materialSignal("Fe")
        #self.elementWidget.setCurrentIndex(23)
        #self.elementSignal(23)
        #self.edgeWidget.setCurrentIndex(0)
        #self.edgeSignal(0)
        self.materialWidget.activated[qstring].connect(self.materialSignal)
        self.elementWidget.activated[qstring].connect(self.elementSignal)
        self.edgeWidget.activated["int"].connect(self.edgeSignal)
        self.energyWidget.editingFinished.connect(self.energySignal)

    def materialSignal(self, txt):
        txt = str(txt)
        if Elements.isValidFormula(txt):
            _logger.debug("validFormula")
            elementDict = Elements.getMaterialMassFractions([txt], [1.0])
        elif Elements.isValidMaterial(txt):
            _logger.debug("ValidMaterial")
            elementDict = Elements.getMaterialMassFractions([txt], [1.0])
        else:
            _logger.debug("Material to be defined")
            msg=qt.QMessageBox.information(self,
                                    "Invalid Material %s" % txt,
                                    "The material %s is not a valid Formula " \
                                    "nor a valid Material.\n" \
                "Please use the material editor to define materials" % txt)
            self.materialWidget.setEditText(self._lastMaterial)
            if self.materialEditor.isHidden():
                self.materialEditor.show()
            return
        # We have to update the possible elements
        elements = list(elementDict.keys())
        self.updateElementsWidget(elements)

    def updateElementsWidget(self, elementsList):
        z = []
        iMaxZ = 0
        for i, ele in enumerate(elementsList):
            tmpZ = Elements.ElementList.index(elementsList[i]) + 1
            z.append(tmpZ)
            if tmpZ > z[iMaxZ]:
                iMaxZ = i
        currentElement = str(self.elementWidget.currentText()).split("(")[0]
        self.elementWidget.clear()
        for i, ele in enumerate(elementsList):
            if z[i] > 2:
                self.elementWidget.insertItem(i,
                                         qstring(ele + "(%d)" % (z[i])))
        if currentElement in elementsList:
            #selection does not need to be changed
            _logger.debug("Element widget up to date")
        else:
            #selection needs to be changed
            _logger.debug("Setting the highest Z as default")
            self.elementSignal(qstring(elementsList[iMaxZ]))


    def toggleEditor(self):
        if self.materialEditor.isHidden():
            self.materialEditor.show()
        else:
            self.materialEditor.hide()

    def elementSignal(self, txt):
        element = str(txt)
        if "(" in txt:
            element = element.split("(")[0]
        options = []
        shellList = ["K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5", "N1"]
        for shell in shellList:
            if Elements.Element[element]["binding"][shell] > 0.0:
                options.append(shell)
        currentShell = str(self.edgeWidget.currentText())
        self.edgeWidget.clear()
        i = 0
        for shell in options[:-1]:
            self.edgeWidget.insertItem(i, qstring(shell))
            i += 1
        if currentShell in options:
            idx = options.index(currentShell)
        else:
            idx = 0
        self.edgeWidget.setCurrentIndex(idx)
        self.edgeSignal(idx)

    def edgeSignal(self, idx):
        shellList = ["K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5"]
        shell = shellList[idx]
        element = str(self.elementWidget.currentText()).split("(")[0]
        energy = Elements.Element[element]["binding"][shell] * 1000.
        self.energyWidget.setText("%.2f" % energy)

    def energySignal(self):
        try:
            energy = float(self.energyWidget.text())
        except Exception:
            energy = 0.0
        if energy <= 0.0:
            self.edgeSignal(self.edgeWidget.currentIndex())

    def setParameters(self, ddict=None):
        if ddict is None:
            ddict = {}
        key = "material"
        if key in ddict:
            material = ddict['material']
            if Elements.isValidMaterial(material):
                self.materialWidget.setEditText(material)
                self.materialSignal(material)
            else:
                raise ValueError("Invalid Material %s" % material)
        key = "element"
        if key in ddict:
            ele = ddict[key]
            for i in range(self.elementWidget.count()):
                if str(self.elementWidget.itemText(i)).split("(")[0] == ele:
                    self.elementWidget.setCurrentIndex(i)
                    self.elementSignal(ele)
        key = "edge"
        if key in ddict:
            shellList = ["K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5"]
            idx = shellList.index(ddict[key])
        else:
            idx = 0
        self.edgeWidget.setCurrentIndex(idx)
        self.edgeSignal(idx)
        key = "energy"
        if key in ddict:
            energy = ddict[key]
            self.energyWidget.setText("%.2f" % energy)

    def getParameters(self):
        ddict = {}
        ddict["material"] = str(self.materialWidget.currentText())
        ddict["element"] = str(self.elementWidget.currentText()).split("(")[0]
        ddict["edge"] = str(self.edgeWidget.currentText())
        ddict["energy"] = float(self.energyWidget.text())
        return ddict

class GeometryConfiguration(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.setContentsMargins(0, 0, 0, 0)
        self.imageLabel = qt.QLabel(self)
        self.imageLabel.setPixmap(qt.QPixmap(MatrixImage.image_medium))
        self.angleWidgets = []
        self.mainLayout.addWidget(self.imageLabel, 0, 0, 2, 2)
        i = 0
        for item in ["Alpha In", "Alpha Out"]:
            label = qt.QLabel(self)
            label.setText(item +"(deg) :")
            lineEdit = qt.QLineEdit(self)
            validator = qt.CLocaleQDoubleValidator(lineEdit)
            lineEdit.setValidator(validator)
            lineEdit._v = validator
            lineEdit.setText("45.0")
            self.angleWidgets.append(lineEdit)
            self.mainLayout.addWidget(label, i, 3)
            self.mainLayout.addWidget(lineEdit, i, 4)
            i += 1

    def getParameters(self):
        ddict = {}
        ddict['angles'] = [float(self.angleWidgets[0].text()),
                           float(self.angleWidgets[1].text())]
        return ddict

    def setParameters(self, ddict):
        if 'angles' in ddict:
            self.angleWidgets[0].setText("%.2f" % ddict['angles'][0])
            self.angleWidgets[1].setText("%.2f" % ddict['angles'][1])

class XASSelfattenuationWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.setContentsMargins(0, 0, 0, 0)
        self.element = SampleConfiguration(self, orientation="horizontal")
        self.geometry = GeometryConfiguration(self)
        self.mainLayout.addWidget(self.element)
        self.mainLayout.addWidget(self.geometry)
        self.mainLayout.addWidget(qt.VerticalSpacer(self))

    def setParameters(self, ddict):
        if "XAS" in ddict:
            self.element.setParameters(ddict['XAS'])
            self.geometry.setParameters(ddict['XAS'])
        else:
            self.element.setParameters(ddict)
            self.geometry.setParameters(ddict)

    def getParameters(self):
        ddict = {}
        ddict['XAS'] = self.element.getParameters()
        ddict['XAS'].update(self.geometry.getParameters())
        return ddict

class XASSelfattenuationDialog(qt.QDialog):
    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("XAS self-attenuation dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.setContentsMargins(0, 0, 0, 0)
        self.configurationWidget = XASSelfattenuationWidget(self)
        self.actionsBox = qt.QWidget(self)
        self.actionsBox.mainLayout = qt.QHBoxLayout(self.actionsBox)
        self.actionsBox.setContentsMargins(0, 0, 0, 0)
        self.loadButton = qt.QPushButton(self.actionsBox)
        self.loadButton.setText("Load")
        self.loadButton.setAutoDefault(False)
        self.saveButton = qt.QPushButton(self.actionsBox)
        self.saveButton.setText("Save")
        self.saveButton.setAutoDefault(False)
        self.cancelButton = qt.QPushButton(self.actionsBox)
        self.cancelButton.setText("Cancel")
        self.cancelButton.setAutoDefault(False)
        self.okButton = qt.QPushButton(self.actionsBox)
        self.okButton.setText("OK")
        self.okButton.setAutoDefault(False)
        self.actionsBox.mainLayout.addWidget(self.loadButton)
        self.actionsBox.mainLayout.addWidget(self.saveButton)
        self.actionsBox.mainLayout.addWidget(self.cancelButton)
        self.actionsBox.mainLayout.addWidget(self.okButton)
        self.mainLayout.addWidget(self.configurationWidget)
        self.mainLayout.addWidget(self.actionsBox)
        self.mainLayout.addWidget(qt.VerticalSpacer(self))

        self.loadButton.clicked.connect(self.loadSignal)
        self.saveButton.clicked.connect(self.saveSignal)
        self.cancelButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)

    def loadSignal(self):
        fileList = PyMcaFileDialogs.getFileList(self,
                                                filetypelist=['cfg file (*.cfg)'],
                                                mode="OPEN",
                                                single=True,
                                                getfilter=False)
        if len(fileList):
            self.loadConfiguration(fileList[0])

    def saveSignal(self):
        fileList = PyMcaFileDialogs.getFileList(self,
                                                filetypelist=['cfg file (*.cfg)'],
                                                mode="SAVE",
                                                single=True,
                                                getfilter=False)
        if len(fileList):
            self.saveConfiguration(fileList[0])

    def reject(self):
        return qt.QDialog.reject(self)

    def accept(self):
        return qt.QDialog.accept(self)

    def getConfiguration(self):
        return self.configurationWidget.getParameters()

    def setConfiguration(self, ddict):
        self.configurationWidget.setParameters(ddict)

    def loadConfiguration(self, filename):
        d = ConfigDict.ConfigDict()
        d.read(filename)
        self.setConfiguration(d['XAS'])

    def saveConfiguration(self, filename):
        d = ConfigDict.ConfigDict()
        d['XAS'] = {}
        ddict = self.getConfiguration()
        if 'XAS' in ddict:
            d['XAS'].update(ddict['XAS'])
        else:
            d['XAS'].update(ddict)
        d.write(filename)

if __name__ == "__main__":
    app = qt.QApplication([])
    w = XASSelfattenuationDialog()
    w.setConfiguration({"material":"Goethite"})
    ret = w.exec()
    if ret:
        cfg = w.getConfiguration()
        print(cfg)
        cfg['material'] = "Fe"
        w.setConfiguration(cfg)
        ret = w.exec()
        if ret:
            cfg = w.getConfiguration()
            print(cfg)
