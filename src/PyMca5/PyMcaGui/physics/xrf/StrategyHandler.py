#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2022 European Synchrotron Radiation Facility
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
import copy
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaPhysics import Elements
from PyMca5.PyMcaGui.plotting import PyMca_Icons
from PyMca5.PyMcaIO import ConfigDict
from .MaterialEditor import MaterialComboBox

IconDict = PyMca_Icons.IconDict
QTVERSION = qt.qVersion()
_logger = logging.getLogger(__name__)


def _getPeakList(fitConfiguration):
    elementsList = []
    for element in fitConfiguration['peaks']:
        if len(element) > 1:
            ele = element[0:1].upper() + element[1:2].lower()
        else:
            ele = element.upper()
        if type(fitConfiguration['peaks'][element]) == type([]):
            for peak in fitConfiguration['peaks'][element]:
                elementsList.append(ele + " " + peak)
        else:
            for peak in [fitConfiguration['peaks'][element]]:
                elementsList.append(ele + " " + peak)
    elementsList.sort()
    return elementsList

def _getMatrixDescription(fitConfiguration):
    useMatrix = False
    detector = None
    for attenuator in list(fitConfiguration['attenuators'].keys()):
        if not fitConfiguration['attenuators'][attenuator][0]:
            # set to be ignored
            continue
        if attenuator.upper() == "MATRIX":
            if fitConfiguration['attenuators'][attenuator][0]:
                useMatrix = True
                matrix = fitConfiguration['attenuators'][attenuator][1:4]
                alphaIn= fitConfiguration['attenuators'][attenuator][4]
                alphaOut= fitConfiguration['attenuators'][attenuator][5]
            else:
                useMatrix = False
            break
    if not useMatrix:
        raise ValueError("Sample matrix has to be specified!")

    if matrix[0].upper() == "MULTILAYER":
        multilayerSample = {}
        layerKeys = list(fitConfiguration['multilayer'].keys())
        if len(layerKeys):
            layerKeys.sort()
        for layer in layerKeys:
            if fitConfiguration['multilayer'][layer][0]:
                multilayerSample[layer] = \
                                fitConfiguration['multilayer'][layer][1:]
    else:
        multilayerSample = {"Auto":matrix}
    return multilayerSample

class StrategyHandlerWidget(qt.QWidget):
    sigStrategyHandlerSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="Single Layer Matrix Iteration Strategy"):
        qt.QWidget.__init__(self, parent)
        self._fitConfiguration = None
        self.setWindowTitle(name)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self._descriptionButton = qt.QPushButton(self)
        self._descriptionButton.setText("Hide algorithm description")
        self._descriptionButton.setAutoDefault(False)
        self._descriptionButton.clicked.connect(self.toggleDescription)
        self._descriptionWidget = qt.QTextEdit(self)
        self._description = qt.QTextDocument()
        self.mainLayout.addWidget(self._descriptionButton)
        self.mainLayout.addWidget(self._descriptionWidget)
        self.build()

    def toggleDescription(self):
        if self._descriptionButton.text().startswith("Hide"):
            self._descriptionWidget.hide()
            self._descriptionButton.setText("Show algorithm description")
        else:
            self._descriptionWidget.show()
            self._descriptionButton.setText("Hide algorithm description")

    def setDescription(self, txt):
        self._description.setPlainText(txt)
        self._descriptionWidget.setDocument(self._description)

    def build(self):
        self.strategy = {}
        self.strategy["SingleLayerStrategy"] = SingleLayerStrategyWidget(self)
        currentStrategy = self.strategy["SingleLayerStrategy"]
        self.setDescription(currentStrategy.getDescription())
        self.mainLayout.addWidget(currentStrategy)

    def setFitConfiguration(self, fitConfiguration):
        self._fitConfiguration = copy.deepcopy(fitConfiguration)
        strategy = self._fitConfiguration["fit"].get("strategy", "SingleLayerStrategy")
        self.strategy[strategy].setFitConfiguration(self._fitConfiguration)

    def getParameters(self):
        if self._fitConfiguration is None:
            return {}
        strategy = self._fitConfiguration["fit"].get("strategy", "SingleLayerStrategy")
        return {strategy:self.strategy[strategy].getParameters()}

    def setParameters(self, ddict):
        # this is used to use the current fit configuration but with other strategy configuration
        # from other file
        if self._fitConfiguration is None:
            return
        strategy = self._fitConfiguration["fit"].get("strategy", "SingleLayerStrategy")
        if strategy in ddict:
            return self.strategy[strategy].setParameters(ddict[strategy])

class SingleLayerStrategyWidget(qt.QWidget):
    def __init__(self, parent=None, name="Single Layer Matrix Iteration Strategy"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.build()

    def getDescription(self):
        txt =  "WARNING: Not recommended for use with internal standard if the "
        txt += "internal standard is present in the refining layer. You will "
        txt += "get better results working in fundamental parameters mode.\n"
        txt += "This matrix iteration procedure is implemented as follows:\n"
        txt += "The concentration of the elements selected to be updated, will "
        txt += "be incorporated in the matrix in the specified form.\n"
        txt += "If the sum of the mass fractions of those elements is above 1 "
        txt += "the program will normalize as usual.\n"
        txt += "If the sum of the mass fractions is below 1, the same procedure "
        txt += "will be applied unless the user has chosen a completing material.\n"
        txt += "Limitations of the algorithm:\n"
        txt += "- The incorporated elements cannot be on different layers.\n"
        txt += "- One element cannot be selected more than once.\n"
        txt += "Recommendations:\n"
        txt += "- In order to avoid unnecessarily slow setups, "
        txt += "activate this option and any secondary or tertiary excitation "
        txt += "calculation once you are ready for quantification."
        return txt

    def build(self):
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        label = qt.QLabel("Number of matrix iterations to perfom:")
        self._nIterations = qt.QSpinBox(self)
        self._nIterations.setMinimum(1)
        self._nIterations.setMaximum(100)
        self._nIterations.setValue(3)
        self.mainLayout.addWidget(label, 0, 0)
        self.mainLayout.addWidget(qt.HorizontalSpacer(self), 1, 0)
        self.mainLayout.addWidget(self._nIterations, 0, 2)

        label = qt.QLabel("Layer in wich the algorithm is to be applied:")
        self._layerOptions = qt.QComboBox(self)
        self._layerOptions.addItem("Auto")
        self.mainLayout.addWidget(label, 1, 0)
        #self.mainLayout.addWidget(qt.HorizontalSpacer(self), 1, 0)
        self.mainLayout.addWidget(self._layerOptions, 1, 2)

        label = qt.QLabel("Completing material to be used:")
        materialList = list(Elements.Material.keys())
        materialList.sort()
        a = ["-"]
        for key in materialList:
            a.append(key)
        self._materialOptions = MyQComboBox(self, options=a)
        self._materialOptions.addItem("-")
        self.mainLayout.addWidget(label, 2, 0)
        self.mainLayout.addWidget(self._materialOptions, 2, 2)
        self._table = IterationTable(self)
        self.mainLayout.addWidget(self._table, 3, 0, 5, 5)

        self.mainLayout.addWidget(qt.VerticalSpacer(self), 10, 0)

    def setFitConfiguration(self, fitConfiguration):
        # obtain the peak families fitted
        _peakList = _getPeakList(fitConfiguration)
        if not len(_peakList):
            raise ValueError("No peaks to fit!!!!")

        matrixDescription = _getMatrixDescription(fitConfiguration)
        layerList = list(matrixDescription.keys())
        layerList.sort()

        materialList = list(Elements.Material.keys())
        materialList.sort()
        a = ["-"]
        for key in materialList:
            a.append(key)

        # Material options
        self._materialOptions.setOptions(a)
        self._table.setMaterialOptions(a)

        # If only one layer, all the elements are selectable
        layerPeaks = {}
        if len(layerList) == 1:
            layerPeaks[layerList[0]] = _peakList
        else:
            inAllLayers = []
            toDeleteFromAllLayers = []
            toForgetAbout = []
            for layer in layerList:
                layerPeaks[layer] = []
            for peak in _peakList:
                element = peak.split()[0]
                layersPresent = []
                for layer in layerList:
                    material = matrixDescription[layer][0]
                    if element in Elements.getMaterialMassFractions(\
                                                                [material],
                                                                [1.0]).keys():
                        layersPresent.append(layer)
                if len(layersPresent) == 1:
                    layerPeaks[layersPresent[0]].append(peak)
        oldOption  = qt.safe_str(self._layerOptions.currentText())
        self._layerOptions.clear()
        for item in layerList:
            self._layerOptions.addItem(item)
        self._layerList = layerList

        if oldOption not in layerList:
            oldOption = layerList[0]

        self._layerOptions.setCurrentIndex(layerList.index(oldOption))
        self._layerList = layerList
        self._layerPeaks = layerPeaks
        self._table.setLayerPeakFamilies(layerPeaks[oldOption])
        strategy = fitConfiguration["fit"].get("strategy", "SingleLayerStrategy")
        if strategy in fitConfiguration:
            self.setParameters(fitConfiguration["SingleLayerStrategy"])

    def getParameters(self):
        ddict = self._table.getParameters()
        ddict["layer"] = str(self._layerOptions.currentText())
        ddict["iterations"] = self._nIterations.value()
        ddict["completer"] = str(self._materialOptions.currentText())
        return ddict

    def setParameters(self, ddict):
        layer = ddict.get("layer", "Auto")
        if layer not in self._layerList:
            if layer.upper() != "AUTO":
                raise ValueError("Layer %s not among fitted layers" % layer)
            else:
                layerList = self._layerList + ["Auto"]
                self._layerOptions.clear()
                for item in layerList:
                    self._layerOptions.addItem(item)
                self._layerList = layerList

        nIterations = ddict.get("iterations", 3)
        self._nIterations.setValue(nIterations)

        layerList = self._layerList
        layerPeaks = self._layerPeaks

        self._layerOptions.setCurrentIndex(layerList.index(layer))
        if layer in layerPeaks:
            self._table.setLayerPeakFamilies(layerPeaks[layer])

        completer = ddict.get("completer", "-")
        self._materialOptions.setCurrentText(completer)

        flags     = ddict["flags"]
        families  = ddict["peaks"]
        materials = ddict["materials"]

        nItem = 0
        for i in range(len(flags)):
            doIt = 0
            if (flags[i] in [1, True, "1", "True"]) and (layer in layerPeaks):
                flag = 1
                if families[i] in layerPeaks[layer]:
                    if materials[i] in ["-"]:
                        doIt = 1
                    else:
                        element = families[i].split()[0]
                        if element in Elements.getMaterialMassFractions( \
                                                [materials[i]], [1.0]):
                            doIt = 1
                    if doIt:
                        self._table.setData(nItem, flag, families[i], materials[i])
                    else:
                        self._table.setData(nItem, flag, families[i], element)
            else:
                self._table.setData(nItem, 0, "-", "-")
            nItem += 1

class IterationTable(qt.QTableWidget):
    sigValueChanged = qt.pyqtSignal(int, int)
    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.verticalHeader().hide()
        nMaxEntries = 15
        nRows = 5
        nColumns = 3 * (nMaxEntries // nRows)
        self.setRowCount(nRows)
        self.setColumnCount(nColumns)
        labels = ["Use", "Peak Family", "Material Form"] * (nColumns // 3)
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            self.setHorizontalHeaderItem(i,item)
        self.build()
        for i in range(0, nColumns, 3):
            self.resizeColumnToContents(i)
        self.cellChanged[int, int].connect(self.mySlot)

    def setData(self, idx, use, peak, material="-"):
        row = idx % self.rowCount()
        c = 3 * (idx // self.rowCount())
        item = self.cellWidget(row, 0 + c)
        if use:
            item.setChecked(True)
        else:
            item.setChecked(False)
        item = self.cellWidget(row, 1 + c)
        n = item.findText(peak)
        item.setCurrentIndex(n)
        ddict = {}
        ddict['row'] = row
        ddict['col'] = 1 + c
        ddict['text'] = peak
        self.__updateMaterialOptions(ddict)
        item = self.cellWidget(row, 2 + c)
        item.setEditText(material)

    def mySlot(self,row,col):
        _logger.debug("Value changed row = %d col = %d" % (row, col))
        if col != 0:
            _logger.debug("Text = %s" % self.cellWidget(row, col).currentText())

    def _checkBoxSlot(self, ddict):
        # check we do not have duplicates
        row = ddict['row']
        col = ddict['col']
        target = str(self.cellWidget(row, 1 + col).currentText()).split()[0]
        nRows = self.rowCount()
        nColumns = self.columnCount() 
        for idx in range((nRows*nColumns) // 3):
            r = idx % nRows
            c = 3 * (idx // self.rowCount())
            if r == row:
                if c  == col:
                    continue
            item = self.cellWidget(r, 0 + c)
            if item.isChecked():
                element = str(self.cellWidget(r, 1 + c).currentText()).split()[0]
                if target == element:
                    # reset the just changed one
                    self.cellWidget(row, col).setChecked(False)
                    self.cellWidget(row, col + 1).setCurrentIndex(0)
                    self.cellWidget(row, col + 2).setCurrentText("-")
                    return
        self.setCurrentCell(row, col)
        self.sigValueChanged.emit(row, col)

    def build(self):
        materialList = list(Elements.Material.keys())
        materialList.sort()
        a = ["-"]
        for key in materialList:
            a.append(key)
        nRows = self.rowCount()
        nColumns = self.columnCount()
        for idx in range((nRows*nColumns) // 3):
            row = idx % nRows
            c = 3 * (idx // nRows)
            item = self.cellWidget(row, 0 + c)
            if item is None:
                item = MyCheckBox(self, row, 0 + c)
                self.setCellWidget(row, 0 + c, item)
                item.sigMyCheckBoxSignal.connect(self._checkBoxSlot)

            item = self.cellWidget(row, 1 + c)
            if item is None:
                item = SimpleComboBox(self, row=row, col=1 + c)
                self.setCellWidget(row, 1 + c, item)
                item.sigSimpleComboBoxSignal.connect(self._peakFamilySlot)

            item = self.cellWidget(row, 2 + c)
            if item is None:
                item = MyQComboBox(self, options=a, row=row, col=2 + c)
                item.setEditable(True)
                self.setCellWidget(row, 2 + c, item)
                item.sigMaterialComboBoxSignal.connect(self._comboSlot)

    def setMaterialOptions(self, options):
        nRows = self.rowCount()
        nColumns = self.columnCount()
        nItems = (nRows * nColumns) // 3
        for idx in range(nItems):
            row = idx % nRows
            c = 3 * (idx // nRows)
            item = self.cellWidget(row, 2 + c)
            item.setOptions(options)

    def setLayerPeakFamilies(self, layerPeaks):
        nRows = self.rowCount()
        nColumns = self.columnCount()
        nItems = (nRows * nColumns) // 3
        for idx in range(nItems):
            row = idx % nRows
            c = 3 * (idx // nRows)
            item = self.cellWidget(row, 1 + c)
            item.setOptions(["-"] + layerPeaks)
            # reset material form
            item = self.cellWidget(row, 2 + c)
            item.setCurrentIndex(0)

    def __updateMaterialOptions(self, ddict):
        row = ddict['row']
        col = ddict['col']
        text = ddict['text']
        element = text.split()[0]
        materialItem = self.cellWidget(row, col + 1)
        associatedMaterial = str(materialItem.currentText())

        goodCandidates = [element]
        for i in range(materialItem.count()):
            material = str(materialItem.itemText(i))
            if material not in ["-", element]:
                if element in Elements.getMaterialMassFractions([material],
                                                                    [1.0]):
                    goodCandidates.append(material)
        materialItem.clear()
        materialItem.setOptions(goodCandidates)
        if associatedMaterial in goodCandidates:
            materialItem.setCurrentIndex(goodCandidates.index(associatedMaterial))
        else:
            materialItem.setCurrentIndex(0)

    def _peakFamilySlot(self, ddict):
        _logger.debug("_peakFamilySlot %s" % ddict)
        # check we do not have duplicates
        target = ddict["text"].split()[0]
        row = ddict['row']
        col = ddict['col']
        for idx in range(10):
            r = idx % 5
            c = 3 * (idx // self.rowCount())
            if r == row:
                if (c + 1) == col:
                    continue
            item = self.cellWidget(r, 0 + c)
            if item.isChecked():
                element = str(self.cellWidget(r, 1 + c).currentText()).split()[0]
                if target == element:
                    # reset the just changed one
                    self.cellWidget(row, col - 1).setChecked(False)
                    return

        self.__updateMaterialOptions(ddict)
        self.setCurrentCell(row, col)
        self.sigValueChanged.emit(row, col)

    def _comboSlot(self, ddict):
        _logger.debug("_comboSlot %s" % ddict)
        row = ddict['row']
        col = ddict['col']
        text = ddict['text']
        self.setCurrentCell(row, col)
        self.sigValueChanged.emit(row, col)

    def getParameters(self):
        ddict = {}
        ddict["flags"] = []
        ddict["peaks"] = []
        ddict["materials"] = []
        nRows = self.rowCount()
        nColumns = self.columnCount()
        for idx in range((nRows * nColumns) // 3):
            row = idx % nRows
            c = 3 * (idx // nRows)
            item = self.cellWidget(row, 0 + c)
            if item.isChecked():
                peak = str(self.cellWidget(row, 1 + c).currentText())
                if peak in ["-"]:
                    continue
                    #raise ValueError("Invalid peak family in row %d" % row)
                ddict["flags"].append(1)
                ddict["peaks"].append(peak)
                ddict["materials"].append(self.cellWidget(row, 2 + c).currentText())
            else:
                ddict["flags"].append(0)
                ddict["peaks"].append(self.cellWidget(row, 1 + c).currentText())
                ddict["materials"].append(self.cellWidget(row, 2 + c).currentText())
        return ddict

class SimpleComboBox(qt.QComboBox):
    sigSimpleComboBoxSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None,row=None, col=None):
        if row is None: row = 0
        if col is None: col = 0
        self.row = row
        self.col = col
        qt.QComboBox.__init__(self,parent)
        self.setEditable(False)
        self.setDuplicatesEnabled(False)
        if hasattr(self, "textActivated"):
            self.textActivated[str].connect(self._mySignal)
        else:
            self.activated[str].connect(self._mySignal)

    def setOptions(self, options):
        self.clear()
        for item in options:
            self.addItem(item)

    def _mySignal(self, txt):
        ddict = {}
        ddict["event"] = "activated"
        ddict["row"] = self.row
        ddict["col"] = self.col
        ddict["text"] = self.currentText()
        self.sigSimpleComboBoxSignal.emit(ddict)

class MyQComboBox(MaterialComboBox):
    def _mySignal(self, qstring0):
        qstring = qstring0
        (result, index) = self.ownValidator.validate(qstring, 0)
        if result != self.ownValidator.Valid:
            qstring = self.ownValidator.fixup(qstring)
            (result, index) = self.ownValidator.validate(qstring,0)
        if result != self.ownValidator.Valid:
            text = str(qstring)
            if text.upper() not in ["-", "None"]:
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
        self.lastText = text
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

class MyCheckBox(qt.QCheckBox):
    sigMyCheckBoxSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, row=0, col=0):
        qt.QCheckBox.__init__(self, parent)
        self._row = row
        self._col = col
        self.stateChanged[int].connect(self._emitSignal)

    def _emitSignal(self, *var):
        ddict = {}
        ddict["row"] = self._row
        ddict["col"] = self._col
        self.sigMyCheckBoxSignal.emit(ddict)

class StrategyHandlerDialog(qt.QDialog):
    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("Fit Strategy Configuration Window")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.handlerWidget = StrategyHandlerWidget(self)

        # mimic behavior
        self.setFitConfiguration = self.handlerWidget.setFitConfiguration
        self.getParameters = self.handlerWidget.getParameters
        self.setParameters = self.handlerWidget.setParameters

        # the actions
        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(2)
        self.loadButton = qt.QPushButton(hbox)
        self.loadButton.setText("Load")
        self.loadButton.setAutoDefault(False)
        self.loadButton.setToolTip("Read the strategy parameters from other fit configuration file")
        self.okButton = qt.QPushButton(hbox)
        self.okButton.setText("OK")
        self.okButton.setAutoDefault(False)
        self.dismissButton = qt.QPushButton(hbox)
        self.dismissButton.setText("Cancel")
        self.dismissButton.setAutoDefault(False)
        hboxLayout.addWidget(self.loadButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.okButton)
        hboxLayout.addWidget(self.dismissButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))

        # layout
        self.mainLayout.addWidget(self.handlerWidget)
        self.mainLayout.addWidget(hbox)

        # connect
        self.loadButton.clicked.connect(self.load)
        self.dismissButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)

    def sizeHint(self):
        return qt.QSize(int(1.5*qt.QDialog.sizeHint(self).width()),
                        qt.QDialog.sizeHint(self).height())

    def load(self):
        fileList = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=["Fit files (*.cfg)"],
                                                message="Select a fit configuration file",
                                                mode="OPEN",
                                                getfilter=False,
                                                single=True)
        if len(fileList):
            d = ConfigDict.ConfigDict()
            d.read(fileList[0])
            self.setParameters(d)

def main(fileName=None):
    app  = qt.QApplication(sys.argv)
    w = StrategyHandlerDialog()
    if fileName is not None:
        d = ConfigDict.ConfigDict()
        d.read(fileName)
        d["fit"]["strategy"] = "SingleLayerStrategy"
        d["SingleLayerStrategy"] = {}
        d["SingleLayerStrategy"]["iterations"] = 4
        d["SingleLayerStrategy"]["flags"] = 1, 1, 0, 1
        d["SingleLayerStrategy"]["peaks"] = "Cr K", "Fe K", "Mn K",  "Fe Ka"
        d["SingleLayerStrategy"]["materials"] = "-", "Goethite", "-", "Goethite"
        d["SingleLayerStrategy"]["completer"] = "Mo"
        w.setFitConfiguration(d)
    if w.exec() == qt.QDialog.Accepted:
        print(w.getParameters())


if __name__ == "__main__":
    sys.excepthook = qt.exceptionHandler
    if len(sys.argv) < 2:
        print("Usage: python StrategyHandler FitConfigurationFile")
        main()
    else:
        fileName = sys.argv[1]
        print(main(fileName))
