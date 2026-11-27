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
import numpy
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.io import PyMcaFileDialogs

DEBUG = 0

class StackXASBatchWindow(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("StackXASBatchWindow")
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        # configuration file
        configLabel = qt.QLabel(self)
        configLabel.setText("XAS Configuration File:")
        self._configLine = qt.QLineEdit(self)
        self._configLine.setReadOnly(True)

        self._configButton = qt.QPushButton(self)
        self._configButton.setText("Browse")
        self._configButton.setAutoDefault(False)
        self._configButton.clicked.connect(self.browseConfigurationFile)

        # output directory
        outLabel   = qt.QLabel(self)
        outLabel.setText("Output dir:")
        self._outLine = qt.QLineEdit(self)
        self._outLine.setReadOnly(True)

        self._outButton = qt.QPushButton(self)
        self._outButton.setText('Browse')
        self._outButton.setAutoDefault(False)
        self._outButton.clicked.connect(self.browseOutputDir)

        # output file name
        fileLabel   = qt.QLabel(self)
        fileLabel.setText("Output file root:")
        self._fileLine = qt.QLineEdit(self)
        self._fileLine.setReadOnly(False)
        self._fileLine.setText("XAS_Result")


        boxLabel   = qt.QLabel(self)
        boxLabel.setText("Options:")

        self._boxContainer = qt.QWidget(self) 
        self._boxContainerLayout = qt.QHBoxLayout(self._boxContainer)
        self._boxContainerLayout.setContentsMargins(0, 0, 0, 0)
        self._boxContainerLayout.setSpacing(0)
        # Mask
        self._maskBox = qt.QCheckBox(self._boxContainer)
        self._maskBox.setText("Use selection mask")
        self._maskBox.setChecked(True)
        self._maskBox.setEnabled(False)
        text  = "If pixels are currently selected, only the spectra\n"
        text += "associated to those pixels will be analyzed"
        self._maskBox.setToolTip(text)

        self._boxContainerLayout.addWidget(self._maskBox)
        
        self.mainLayout.addWidget(configLabel, 0, 0)
        self.mainLayout.addWidget(self._configLine, 0, 1)
        self.mainLayout.addWidget(self._configButton, 0, 2)
        self.mainLayout.addWidget(outLabel, 1, 0)
        self.mainLayout.addWidget(self._outLine, 1, 1)
        self.mainLayout.addWidget(self._outButton, 1, 2)
        self.mainLayout.addWidget(fileLabel, 2, 0)
        self.mainLayout.addWidget(self._fileLine, 2, 1)
        self.mainLayout.addWidget(boxLabel, 3, 0)
        self.mainLayout.addWidget(self._boxContainer, 3, 1, 1, 1)

    def sizeHint(self):
        return qt.QSize(int(1.8 * qt.QWidget.sizeHint(self).width()),
                        qt.QWidget.sizeHint(self).height())

    def browseConfigurationFile(self):
        f = PyMcaFileDialogs.getFileList(parent=self,
                                     filetypelist=["Configuration files (*.ini)",
                                                   "Configuration files (*.cfg)"],
                                     message="Open a XAS configuration file",
                                     mode="OPEN",
                                     single=True)
        if len(f):
            self._configLine.setText(f[0])

    def browseOutputDir(self):
        f = PyMcaFileDialogs.getExistingDirectory(parent=self,
                                     message="Please select output directory",
                                     mode="OPEN")
        if len(f):
            self._outLine.setText(f)

    def getParameters(self):
        ddict = {}
        ddict['configuration'] = str(self._configLine.text())
        ddict['output_dir'] = str(self._outLine.text())
        ddict['file_root'] = str(self._fileLine.text())
        if self._maskBox.isChecked():
            ddict['mask'] = 1
        else:
            ddict['mask'] = 0
        return ddict

class StackXASBatchDialog(qt.QDialog):
    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("Stack XAS Batch Dialog")
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.parametersWidget = StackXASBatchWindow(self)

        self.rejectButton= qt.QPushButton(self)
        self.rejectButton.setAutoDefault(False)
        self.rejectButton.setText("Cancel")

        self.acceptButton= qt.QPushButton(self)
        self.acceptButton.setAutoDefault(False)
        self.acceptButton.setText("OK")

        self.rejectButton.clicked.connect(self.reject)
        self.acceptButton.clicked.connect(self.accept)

        self.mainLayout.addWidget(self.parametersWidget, 0, 0, 5, 4)
        self.mainLayout.addWidget(self.rejectButton, 6, 1)
        self.mainLayout.addWidget(self.acceptButton, 6, 2)

    def getParameters(self):
        return self.parametersWidget.getParameters()

if __name__ == "__main__":
    app = qt.QApplication([])
    w = StackXASBatchDialog()
    ret = w.exec()
    if ret:
        print(w.getParameters())
    #app.exec()
