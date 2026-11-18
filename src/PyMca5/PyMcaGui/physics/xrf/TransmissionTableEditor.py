#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2020-2023 European Synchrotron Radiation Facility
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
import os
import copy
import logging
import numpy
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaIO import specfilewrapper as specfile
from PyMca5.PyMcaIO import ArraySave

_logger = logging.getLogger(__name__)

class TransmissionTableEditor(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        layout = qt.QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        # the flag to use it
        useBox = qt.QWidget(self)
        label = qt.QLabel(useBox)
        label.setText("Use")
        self.useCheckBox = qt.QCheckBox(useBox)
        self.useCheckBox.setChecked(False)
        self.useCheckBox.clicked.connect(self._useSlot)
        useBoxLayout = qt.QHBoxLayout(useBox)
        useBoxLayout.addWidget(label)
        useBoxLayout.addWidget(self.useCheckBox)
        layout.addWidget(useBox, 0, 0, 2, 1)

        self.lineEditDict = {}
        r = 0
        c = 1
        labels = ["Name", "Comment"]
        for idx in range(len(labels)):
            l = labels[idx]
            label = qt.QLabel(self)
            label.setText(l)
            line = qt.QLineEdit(self)
            line.editingFinished.connect(self._lineSlot)
            line.setText("")
            layout.addWidget(label, r, c)
            layout.addWidget(line, r, c + 1)
            self.lineEditDict[l.lower()] = line
            r += 1

        buttonsBox = qt.QWidget(self)
        buttonsBoxLayout = qt.QHBoxLayout(buttonsBox)
        self.buttonsDict = {}
        actions = ["Load", "Save", "Show"]
        slots = [self._loadSlot, self._saveSlot, self._showSlot]
        buttonsBoxLayout.addWidget(qt.HorizontalSpacer(buttonsBox))
        for i in range(len(slots)):
            l = actions[i]
            s = slots[i]
            b = qt.QPushButton(buttonsBox)
            b.setText(l)
            b.setAutoDefault(False)
            b.clicked.connect(s)
            buttonsBoxLayout.addWidget(b)
            self.buttonsDict[l.lower()] = b
        buttonsBoxLayout.addWidget(qt.HorizontalSpacer(buttonsBox))
        layout.addWidget(buttonsBox, 2, 0, 1, 3)
        self.inputDir = None
        self.outputDir = None
        self.outputFilter = None
        self.plotDialog = None
        ddict = {}
        ddict["use"] = 0
        ddict["name"] = ""
        ddict["comment"] = ""
        ddict["energy"] = [0.0, 0.001]
        ddict["transmission"] = [0.0, 1.0]
        self._transmissionTable = ddict
        self.update()
        self.setTransmissionTable(ddict)

    def _useSlot(self):
        if self.useCheckBox.isChecked():
            self._transmissionTable["use"] = 1
        else:
            self._transmissionTable["use"] = 0

    def _lineSlot(self):
        ddict = {}
        for key in ["name", "comment"]:
            txt = qt.safe_str(self.lineEditDict[key].text())
            ddict[key] = txt.strip()
        self.setTransmissionTable(ddict, updating=True)

    def _loadSlot(self):
        if self.inputDir is None:
            if self.inputDir is not None:
                self.inputDir = self.outputDir
            else:
                self.inputDir = PyMcaDirs.inputDir
        wdir = self.inputDir
        if not os.path.exists(wdir):
            wdir = os.getcwd()
        filename = PyMcaFileDialogs.getFileList(self,
                            filetypelist=["Transmission table files (*.csv)",
                                          "Transmission table files (*)"],
                            mode="OPEN",
                            message="Choose 2-column transmission table file",
                            currentdir=wdir,
                            single=True)
        if len(filename):
            filename = qt.safe_str(filename[0])
            if len(filename):
                try:
                    self.loadTransmissionTable(filename)
                    self.inputDir = os.path.dirname(filename)
                    PyMcaDirs.inputDir = self.inputDir
                except Exception:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Error transmission table: %s" % (sys.exc_info()[1]))
                    msg.exec()
                    return

    def loadTransmissionTable(self, filename):
        # read with our wrapper
        sf = specfile.Specfile(filename)
        scan = sf[0]
        data = scan.data()
        labels = scan.alllabels()
        scan = None
        sf = None

        nLabels = len(labels)
        if nLabels not in [2, 3]:
            txt = "Expected a two column file got %d columns" % nLabels
            raise IOError(txt)
        if nLabels == 3 and labels[0].lower().startswith("point"):
            energyIdx = 1
            transmissionIdx = 2
        else:
            energyIdx = 0
            transmissionIdx = 1

        # sort energies in ascending order
        energy = data[energyIdx, :]
        transmission = data[transmissionIdx, :]
        idx = numpy.argsort(energy)
        energy = numpy.take(energy, idx)
        transmission = numpy.take(transmission, idx)

        ddict = {}
        ddict["use"] = 1
        ddict["energy"] = energy
        ddict["transmission"] = transmission 
        ddict["name"] = os.path.basename(filename)
        ddict["comment"] = ""

        self.setTransmissionTable(ddict, updating=True)

    def _saveSlot(self):
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
        if "," in filterused[0]:
            csv = ","
        elif ";" in filterused[0]:
            csv = ";"
        else:
            csv = "\t"

        ddict = self.getTransmissionTable()
        x = ddict["energy"]
        y = ddict["transmission"]

        try:
            ArraySave.saveXY(x, y, outputFile,
                             xlabel="Energy", ylabel="Transmission",
                             csv=True, csvseparator=csv)
        except IOError:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Input Output Error: %s" % (sys.exc_info()[1]))
            msg.exec()
            return

    def _showSlot(self):
        self.showPlot()

    def setTransmissionTable(self, tableDict, updating=False):
        # make things case insensitive
        tableKeys = list(tableDict.keys())
        tableKeysLower = [x.lower() for x in tableKeys]
        if updating:
            # we are not expected to supply a complete dictionary
            ddict = self.getTransmissionTable()
        else:
            # a complete dictionary expected
            ddict = {}
            ddict["use"] = 0
            ddict["name"] = ""
            ddict["comment"] = ""
            ddict["energy"] = [0.0, 0.001]
            ddict["transmission"] = [0.0, 1.0]

        for key in ["name", "comment"]:
            if key in tableKeysLower:
                idx = tableKeysLower.index(key)
                txt = tableDict[tableKeys[idx]]
                if not len(txt):
                    txt = ""
                ddict[key] = txt.strip()

        for key in ["use"]:
            if key in tableKeysLower:
                idx = tableKeysLower.index(key)
                txt = tableDict[tableKeys[idx]]
                if txt in ["", "0", 0, "false", "False"]:
                    ddict[key] = 0
                else:
                    ddict[key] = 1

        for key in ["energy", "transmission"]:
            if key in tableKeysLower:
                idx = tableKeysLower.index(key)
                values = tableDict[tableKeys[idx]]
                ddict[key] = values

        for key in ["energy", "transmission"]:
            # make sure we have floats
            values = numpy.array(ddict[key], numpy.float64).reshape(-1)
            # convert to list to prevent issues when saving
            ddict[key] = values.tolist()

        try:
            self._validateDict(ddict)
            self._transmissionTable = ddict
        except Exception:
            msg=qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
        self.update()

    def _validateDict(self, ddict):
        for key in ["name", "comment"]:
            txt = ddict.get(key, "")
            for c in ["%"]:
                if c in txt:
                    raise ValueError("Invalid name '%s'\n" % txt + \
                            "It contains a <%s> character.\n" % c)
        txt = ddict.get("name", "")
        if txt.startswith(" ") or txt.endswith(" "):
            raise ValueError("Invalid name '%s'\n" % txt + \
                        "It starts or ends with a space.\n")

        if len(ddict["energy"]) != len(ddict["transmission"]):
            txt = "Energy and transmission vectors must have same length"
            raise ValueError(txt)
        return True

    def update(self):
        for key in ["name", "comment"]:
            self.lineEditDict[key].setText(self._transmissionTable[key])
        if self._transmissionTable["use"]:
            self.useCheckBox.setChecked(True)
        else:
            self.useCheckBox.setChecked(False)
        if self.plotDialog is not None:
            self.plot()

    def plot(self):
        if self.plotDialog is None:
            from PyMca5.PyMcaGui.plotting.PlotWindow import PlotWindow
            dialog = qt.QDialog(self)
            dialog.mainLayout = qt.QVBoxLayout(dialog)
            dialog.mainLayout.setContentsMargins(0, 0, 0, 0)
            dialog.mainLayout.setSpacing(0)
            dialog.plotWidget = PlotWindow(dialog,
                                           newplot=False,
                                           fit=False,
                                           plugins=False,
                                           control=True,
                                           position=True)
            dialog.plotWidget.setDefaultPlotLines(True)
            dialog.plotWidget.setDefaultPlotPoints(True)
            dialog.plotWidget.setDataMargins(0.05, 0.05, 0.05, 0.05)
            dialog.mainLayout.addWidget(dialog.plotWidget)
            self.plotDialog = dialog

        legend = self._transmissionTable["name"]
        if legend == "":
            legend = None
        x = self._transmissionTable["energy"]
        y = self._transmissionTable["transmission"]
        comment = self._transmissionTable["comment"]
        self.plotDialog.plotWidget.addCurve(x,
                                 y,
                                 legend=legend,
                                 xlabel="Energy (keV)",
                                 ylabel="Transmission",
                                 replot=True,
                                 replace=True)
        self.plotDialog.plotWidget.setGraphTitle(comment)

    def showPlot(self):
        self.plot()
        self.plotDialog.exec()

    def getTransmissionTable(self):
        return copy.deepcopy(self._transmissionTable)

if __name__ == "__main__":
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    demo = TransmissionTableEditor()
    if len(sys.argv) > 1:
        demo.loadTransmissionTable(sys.argv[1])
    demo.show()
    ret  = app.exec()
    app = None
