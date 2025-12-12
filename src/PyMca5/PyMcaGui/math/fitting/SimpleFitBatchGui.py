#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import IconDict
from PyMca5 import PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
PyMcaDirs.nativeFileDialogs = False
QTVERSION = qt.qVersion()
HDF5SUPPORT = True
from PyMca5.PyMcaGui.pymca import QDataSource

class SimpleFitBatchParameters(qt.QWidget):
    def __init__(self, parent=None, file_browser=True):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("PyMca Simple Fit Batch GUI")
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)
        self._inputDir   = None
        self._outputDir  = None
        self._lastInputFileFilter = None
        self._fileList   = []
        self._build(file_browser)

    def _build(self, file_browser):
        row = 0
        if file_browser:
            self._listLabel   = qt.QLabel(self)
            self._listLabel.setText("Input File list:")
            self._listView   = qt.QTextEdit(self)
            self._listView.setMaximumHeight(30*self._listLabel.sizeHint().height())
            self._listButton = qt.QPushButton(self)
            self._listButton.setText('Browse')
            self._listButton.setAutoDefault(False)
            self._listButton.clicked.connect(self.browseList)
            self.mainLayout.addWidget(self._listLabel,  0, 0, qt.Qt.AlignTop|qt.Qt.AlignLeft)
            self.mainLayout.addWidget(self._listView,   0, 1)
            self.mainLayout.addWidget(self._listButton, 0, 2, qt.Qt.AlignTop|qt.Qt.AlignRight)
            row += 1

        #options
        labels = ['Fit Configuration File:', 'Output Directory:']
        row0 = 0
        for label in labels:
            l = qt.QLabel(self)
            l.setText(label)
            line = qt.QLineEdit(self)
            b = qt.QPushButton(self)
            b.setText('Browse')
            self.mainLayout.addWidget(l,    row+row0, 0)
            self.mainLayout.addWidget(line, row+row0, 1)
            self.mainLayout.addWidget(b,    row+row0, 2)
            if row0 == 0:
                self._fitConfigurationLine = line
                self._fitConfigurationButton = b
            else:
                self._outputDirectoryLine = line
                self._outputDirectoryButton = b
            row0 += 1
        row += row0

        self._outputDirectoryButton.clicked.connect( \
                    self.browseOutputDirectory)
        self._fitConfigurationButton.clicked.connect( \
                    self.browseFitConfiguration)

    def browseList(self):
        if self._inputDir is None:
            self._inputDir = PyMcaDirs.inputDir
        elif os.path.exists(self._inputDir):
            PyMcaDirs.inputDir = self._inputDir
        filetypes = []
        if HDF5SUPPORT:
            filetypes.append("HDF5 Files(*.nxs *.h5 *.hdf *.hdf5)")
        filetypes  += ["Mca Files (*.mca)",
                      "Edf Files (*.edf)"]
        filetypes.append("SPEC Files (*.spec)")
        filetypes.append("SPEC Files (*.dat)")
        filetypes.append("All files (*)")
        message = "Open a set of files"
        mode = "OPEN"
        getfilter = True
        currentfilter = self._lastInputFileFilter
        fileList, fileFilter  = PyMcaFileDialogs.getFileList(self,
                                                 filetypelist=filetypes,
                                                 message=message,
                                                 mode=mode,
                                                 getfilter=getfilter,
                                                 single=False,
                                                 currentfilter=currentfilter)
        if not len(fileList):
            return
        else:
            self._lastInputFileFilter = fileFilter
        self._inputDir = os.path.dirname(fileList[0])
        if (QTVERSION < '4.2.0') or (not len(self._fileList)):
            self.setFileList(fileList)
            self.raise_()
            return
        msg = qt.QMessageBox()
        msg.setWindowTitle("Append or replace")
        msg.setIcon(qt.QMessageBox.Information)
        msg.setText("Do you want to delete current file list?")
        msg.setStandardButtons(qt.QMessageBox.Yes|qt.QMessageBox.No)
        answer=msg.exec()
        if answer == qt.QMessageBox.Yes:
            append = False
        else:
            append = True
        self.setFileList(fileList, append=append)
        self.raise_()

    def browseFitConfiguration(self):
        if self._inputDir is None:
            self._inputDir = PyMcaDirs.inputDir
        elif os.path.exists(self._inputDir):
            PyMcaDirs.inputDir = self._inputDir
        filetypes  = ["Configuration Files (*.cfg)"]
        if self._inputDir is None:
            self._inputDir = PyMcaDirs.inputDir
        elif os.path.exists(self._inputDir):
            PyMcaDirs.inputDir = self._inputDir
        message = "Select a Simple Fit Configuration File"
        mode = "OPEN"
        getfilter = False
        currentfilter = None #self._lastInputFileFilter
        fileList = PyMcaFileDialogs.getFileList(self,
                                                 filetypelist=filetypes,
                                                 message=message,
                                                 mode=mode,
                                                 getfilter=getfilter,
                                                 single=True,
                                                 currentfilter=currentfilter)
        if not len(fileList):
            return
        self._inputDir = os.path.dirname(fileList[0])
        self.setFitConfigurationFile(fileList[0])
        self.raise_()

    def browseOutputDirectory(self):
        if self._outputDir is None:
            self._outputDir = PyMcaDirs.outputDir
        elif os.path.exists(self._outputDir):
            PyMcaDirs.inputDir = self._outputDir
        message = "Select a Simple Fit Configuration File"
        mode = "OPEN"
        fileList = PyMcaFileDialogs.getExistingDirectory(self,
                                                 message=message,
                                                 mode=mode)
        if not len(fileList):
            return
        if type(fileList) != type([]):
            fileList = [fileList]
        self._outputDir = os.path.dirname(fileList[0])
        self.setOutputDirectory(fileList[0])
        self.raise_()

    def setFileList(self, filelist, append=False):
        if filelist is None:
            filelist = []
        if not append:
            self._fileList = []
        self._listView.clear()
        text = ""
        for ffile in self._fileList:
            text += ffile + "\n"
        for ffile in filelist:
            if ffile not in self._fileList:
                self._fileList.append(ffile)
                text += ffile + "\n"
        self._listView.insertPlainText(text)
        sourceType = QDataSource.getSourceType(self._fileList[0])
        dataSourceClass  = QDataSource.source_types[sourceType]
        dataSourceWidget = QDataSource.source_widgets[sourceType]
        self._dataSource = dataSourceClass(self._fileList[0])
        self._dataWidget = dataSourceWidget()
        self._dataWidget.setDataSource(self._dataSource)
        self._dataWidget.sigAddSelection.connect(self.printSelection)
        self._dataWidget.show()

    def setFitConfigurationFile(self, fname):
        self._fitConfigurationLine.setText(fname)

    def setOutputDirectory(self, fname):
        self._outputDirectoryLine.setText(fname)

    def printSelection(self, ddict):
        print("Received = ", ddict)

    def getParameters(self):
        ddict = {}
        ddict['selection'] = {}
        ddict['selection']['x'] = None
        ddict['selection']['y'] = None
        ddict['selection']['m'] = None
        ddict['filelist'] = self._fileList
        ddict['outputdir'] = str(self._outputDirectoryLine.text())
        ddict['fitconfiguration'] = str(self._fitConfigurationLine.text())
        return ddict

class SimpleFitBatchGui(qt.QWidget):
    def __init__(self, parent=None, stack=False, actions=True):
        qt.QWidget.__init__(self, parent)
        if stack in [None, False]:
            file_browser = False
        else:
            file_browser = True
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.setSpacing(2)

        self.parametersWidget = SimpleFitBatchParameters(self)
        self.getParameters = self.parametersWidget.getParameters
        self.mainLayout.addWidget(self.parametersWidget)
        if actions:
            self.actionsBox = qt.QWidget(self)
            self.actionsBox.mainLayout = qt.QHBoxLayout(self.actionsBox)
            self.actionsBox.mainLayout.setContentsMargins(2, 2, 2, 2)
            self.actionsBox.mainLayout.setSpacing(2)
            self.closeButton = qt.QPushButton(self.actionsBox)
            self.closeButton.setText("Close")
            self.startButton = qt.QPushButton(self.actionsBox)
            self.startButton.setText("Start")
            self.actionsBox.mainLayout.addWidget(qt.HorizontalSpacer(self.actionsBox))
            self.actionsBox.mainLayout.addWidget(self.closeButton)
            self.actionsBox.mainLayout.addWidget(qt.HorizontalSpacer(self.actionsBox))
            self.actionsBox.mainLayout.addWidget(self.startButton)
            self.actionsBox.mainLayout.addWidget(qt.HorizontalSpacer(self.actionsBox))
            self.mainLayout.addWidget(self.actionsBox)
            self.closeButton.clicked.connect(self.close)

if __name__ == "__main__":
    app = qt.QApplication([])
    w = SimpleFitBatchGui()
    w.show()
    app.exec()
