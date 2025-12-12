#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
import sys
import os
import time
import subprocess
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
if sys.platform.startswith("darwin"):
    import threading
    QThread = threading.Thread
else:
    QThread = qt.QThread

QTVERSION = qt.qVersion()
try:
    import h5py
    from PyMca5.PyMcaCore import NexusDataSource
    from PyMca5.PyMcaGui.io.hdf5 import QNexusWidget
    from PyMca5.PyMcaGui.io.hdf5 import HDF5Selection
    HDF5SUPPORT = True
except ImportError:
    HDF5SUPPORT = False
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaPhysics.xrf import LegacyMcaAdvancedFitBatch as McaAdvancedFitBatch
from PyMca5.PyMcaGui.physics.xrf import QtMcaAdvancedFitReport
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaCore import EdfFileLayer
from PyMca5.PyMcaCore import SpecFileLayer
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.pymca import McaCustomEvent
from PyMca5.PyMcaGui.pymca import EdfFileSimpleViewer
from PyMca5.PyMcaCore import HtmlIndex
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaCore import LegacyPyMcaBatchBuildOutput as PyMcaBatchBuildOutput

ROIWIDTH = 100.
_logger = logging.getLogger(__name__)


class McaBatchGUI(qt.QWidget):
    def __init__(self,parent=None,name="PyMca batch fitting",fl=None,
                filelist=None,config=None,outputdir=None, actions=0,
                showresult=True):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self._layout = qt.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._edfSimpleViewer = None
        self._timer = None
        self._processList = []
        self._selection = None
        self.__build(actions)
        if filelist is None:
            filelist = []
        self.inputDir = None
        self.inputFilter = None
        self.outputDir  = None
        if outputdir is not None:
            if os.path.exists(outputdir):
                self.outputDir = outputdir
            else:
                qt.QMessageBox.information(self, "INFO",
                    "Directory %s does not exist\nUsing %s"% (outputdir, self.outputDir))

        self.configFile = None
        self.setFileList(filelist)
        self.setConfigFile(config)
        self.setOutputDir(self.outputDir)
        self._showResult = showresult

    def __build(self,actions):
        self.__grid= qt.QWidget(self)
        self._layout.addWidget(self.__grid)
        #self.__grid.setGeometry(qt.QRect(30,30,288,156))
        if QTVERSION < '4.0.0':
            grid       = qt.QGridLayout(self.__grid,3,3,11,6)
            grid.setColStretch(0,0)
            grid.setColStretch(1,1)
            grid.setColStretch(2,0)
        else:
            grid       = qt.QGridLayout(self.__grid)
            grid.setContentsMargins(11, 11, 11, 11)
            grid.setSpacing(6)
        #input list
        listrow  = 0
        listlabel   = qt.QLabel(self.__grid)
        listlabel.setText("Input File list:")
        self.__listView   = qt.QTextEdit(self.__grid)
        self.__listView.setMaximumHeight(30*listlabel.sizeHint().height())
        self.__listButton = qt.QPushButton(self.__grid)
        self.__listButton.setText('Browse')
        self.__listButton.clicked.connect(self.browseList)
        grid.addWidget(listlabel,        listrow, 0, qt.Qt.AlignTop|qt.Qt.AlignLeft)
        grid.addWidget(self.__listView,  listrow, 1)
        grid.addWidget(self.__listButton,listrow, 2, qt.Qt.AlignTop|qt.Qt.AlignRight)

        if HDF5SUPPORT:
            self._hdf5Widget = HDF5Selection.HDF5Selection(self)
            grid.addWidget(self._hdf5Widget, listrow+1, 0, 1, 3)
            row_offset = 1
            self._hdf5Widget.hide()
        else:
            row_offset = 0
        #config file
        configrow = 1 + row_offset
        configlabel = qt.QLabel(self.__grid)
        configlabel.setText("Fit Configuration File:")
        if QTVERSION < '4.0.0':
            configlabel.setAlignment(qt.QLabel.WordBreak | qt.QLabel.AlignVCenter)
        self.__configLine = qt.QLineEdit(self.__grid)
        self.__configLine.setReadOnly(True)
        self.__configButton = qt.QPushButton(self.__grid)
        self.__configButton.setText('Browse')
        self.__configButton.clicked.connect(self.browseConfig)
        grid.addWidget(configlabel,         configrow, 0, qt.Qt.AlignLeft)
        grid.addWidget(self.__configLine,   configrow, 1)
        grid.addWidget(self.__configButton, configrow, 2, qt.Qt.AlignLeft)


        #output dir
        outrow    = 2 + row_offset
        outlabel   = qt.QLabel(self.__grid)
        outlabel.setText("Output dir:")
        if QTVERSION < '4.0.0':
            outlabel.setAlignment(qt.QLabel.WordBreak | qt.QLabel.AlignVCenter)
        self.__outLine = qt.QLineEdit(self.__grid)
        self.__outLine.setReadOnly(True)
        #self.__outLine.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed))
        self.__outButton = qt.QPushButton(self.__grid)
        self.__outButton.setText('Browse')
        self.__outButton.clicked.connect(self.browseOutputDir)
        grid.addWidget(outlabel,         outrow, 0, qt.Qt.AlignLeft)
        grid.addWidget(self.__outLine,   outrow, 1)
        grid.addWidget(self.__outButton, outrow, 2, qt.Qt.AlignLeft)


        box  = qt.QWidget(self)
        box.l = qt.QHBoxLayout(box)
        box.l.setContentsMargins(11, 11, 11, 11)
        box.l.setSpacing(0)
        vbox1 = qt.QWidget(box)
        vbox1.l = qt.QVBoxLayout(vbox1)
        vbox1.l.setContentsMargins(0, 0, 0, 0)
        vbox1.l.setSpacing(0)
        box.l.addWidget(vbox1)
        vbox2 = qt.QWidget(box)
        vbox2.l = qt.QVBoxLayout(vbox2)
        vbox2.l.setContentsMargins(0, 0, 0, 0)
        vbox2.l.setSpacing(0)

        box.l.addWidget(vbox2)
        vbox3 = qt.QWidget(box)
        vbox3.l = qt.QVBoxLayout(vbox3)
        vbox3.l.setContentsMargins(0, 0, 0, 0)
        vbox3.l.setSpacing(0)

        box.l.addWidget(vbox3)
        self.__fitBox = qt.QCheckBox(vbox1)
        self.__fitBox.setText('Generate .fit Files')
        palette = self.__fitBox.palette()
        #if QTVERSION < '4.0.0':
        #    palette.setDisabled(palette.active())
        #else:
        #    print("palette set disabled")
        self.__fitBox.setChecked(False)
        self.__fitBox.setEnabled(True)
        vbox1.l.addWidget(self.__fitBox)

        self.__imgBox = qt.QCheckBox(vbox2)
        self.__imgBox.setText('Generate Peak Images')
        palette = self.__imgBox.palette()
        if QTVERSION < '4.0.0':
            palette.setDisabled(palette.active())
        else:
            _logger.debug("palette set disabled")
        self.__imgBox.setChecked(True)
        self.__imgBox.setEnabled(False)
        vbox2.l.addWidget(self.__imgBox)
        """
        self.__specBox = qt.QCheckBox(box)
        self.__specBox.setText('Generate Peak Specfile')
        palette = self.__specBox.palette()
        palette.setDisabled(palette.active())
        self.__specBox.setChecked(False)
        self.__specBox.setEnabled(False)
        """
        self.__htmlBox = qt.QCheckBox(vbox3)
        self.__htmlBox.setText('Generate Report (SLOW!)')
        #palette = self.__htmlBox.palette()
        #palette.setDisabled(palette.active())
        self.__htmlBox.setChecked(False)
        self.__htmlBox.setEnabled(True)
        vbox3.l.addWidget(self.__htmlBox)

        #report options
        #reportBox = qt.QHBox(self)
        self.__tableBox = qt.QCheckBox(vbox1)
        self.__tableBox.setText('Table in Report')
        palette = self.__tableBox.palette()
        #if QTVERSION < '4.0.0':
        #    palette.setDisabled(palette.active())
        #else:
        #    print("palette set disabled")
        self.__tableBox.setChecked(True)
        self.__tableBox.setEnabled(False)
        vbox1.l.addWidget(self.__tableBox)

        self.__extendedTable = qt.QCheckBox(vbox2)
        self.__extendedTable.setText('Extended Table')
        self.__extendedTable.setChecked(True)
        self.__extendedTable.setEnabled(False)
        vbox2.l.addWidget(self.__extendedTable)

        self.__concentrationsBox = qt.QCheckBox(vbox3)
        self.__concentrationsBox.setText('Concentrations')
        self.__concentrationsBox.setChecked(False)
        self.__concentrationsBox.setEnabled(True)
        #self.__concentrationsBox.setEnabled(False)
        vbox3.l.addWidget(self.__concentrationsBox)
        self._layout.addWidget(box)

        # other stuff
        bigbox   = qt.QWidget(self)
        bigbox.l = qt.QHBoxLayout(bigbox)
        bigbox.l.setContentsMargins(0, 0, 0, 0)
        bigbox.l.setSpacing(0)

        vBox = qt.QWidget(bigbox)
        vBox.l = qt.QVBoxLayout(vBox)
        vBox.l.setContentsMargins(0, 0, 0, 0)
        vBox.l.setSpacing(2)
        bigbox.l.addWidget(vBox)

        if 0:
            #These options are obsolete now
            self.__overwrite = qt.QCheckBox(vBox)
            self.__overwrite.setText('Overwrite Fit Files')
            self.__overwrite.setChecked(True)
            vBox.l.addWidget(self.__overwrite)

            self.__useExisting = qt.QCheckBox(vBox)
            self.__useExisting.setText('Use Existing Fit Files')
            self.__useExisting.setChecked(False)
            vBox.l.addWidget(self.__useExisting)

            self.__overwrite.clicked.connect(self.__clickSignal0)
            self.__useExisting.clicked.connect(self.__clickSignal1)
        self.__concentrationsBox.clicked.connect(self.__clickSignal2)
        self.__htmlBox.clicked.connect(self.__clickSignal3)

        boxStep0   = qt.QWidget(bigbox)
        boxStep0.l = qt.QVBoxLayout(boxStep0)
        boxStep  = qt.QWidget(boxStep0)
        boxStep.l= qt.QHBoxLayout(boxStep)
        boxStep.l.setContentsMargins(0, 0, 0, 0)
        boxStep.l.setSpacing(0)
        boxStep0.l.addWidget(boxStep)
        bigbox.l.addWidget(boxStep0)

        if 0:
            self.__boxFStep   = qt.QWidget(boxStep)
            boxFStep = self.__boxFStep
            boxFStep.l = qt.QHBoxLayout(boxFStep)
            boxFStep.l.setContentsMargins(0, 0, 0, 0)
            boxFStep.l.setSpacing(0)
            boxStep.l.addWidget(boxFStep)
            label= qt.QLabel(boxFStep)
            label.setText("File Step:")
            self.__fileSpin = qt.QSpinBox(boxFStep)
            if QTVERSION < '4.0.0':
                self.__fileSpin.setMinValue(1)
                self.__fileSpin.setMaxValue(10)
            else:
                self.__fileSpin.setMinimum(1)
                self.__fileSpin.setMaximum(10)
            self.__fileSpin.setValue(1)
            boxFStep.l.addWidget(label)
            boxFStep.l.addWidget(self.__fileSpin)


            self.__boxMStep   = qt.QWidget(boxStep0)
            boxMStep = self.__boxMStep
            boxMStep.l = qt.QHBoxLayout(boxMStep)
            boxMStep.l.setContentsMargins(0, 0, 0, 0)
            boxMStep.l.setSpacing(0)
            boxStep0.l.addWidget(boxMStep)

            label= qt.QLabel(boxMStep)
            label.setText("MCA Step:")
            self.__mcaSpin = qt.QSpinBox(boxMStep)
            if QTVERSION < '4.0.0':
                self.__mcaSpin.setMinValue(1)
                self.__mcaSpin.setMaxValue(10)
            else:
                self.__mcaSpin.setMinimum(1)
                self.__mcaSpin.setMaximum(10)
            self.__mcaSpin.setValue(1)

            boxMStep.l.addWidget(label)
            boxMStep.l.addWidget(self.__mcaSpin)



        #box2 = qt.QHBox(self)
        self.__roiBox = qt.QCheckBox(vBox)
        self.__roiBox.setText('ROI Fitting Mode')
        vBox.l.addWidget(self.__roiBox)
        #box3 = qt.QHBox(box2)
        self.__box3 = qt.QWidget(boxStep0)
        box3 = self.__box3
        box3.l = qt.QHBoxLayout(box3)
        box3.l.setContentsMargins(0, 0, 0, 0)
        box3.l.setSpacing(0)
        boxStep0.l.addWidget(box3)


        label= qt.QLabel(box3)
        label.setText("ROI Width (eV):")
        self.__roiSpin = qt.QSpinBox(box3)
        if QTVERSION < '4.0.0':
            self.__roiSpin.setMinValue(10)
            self.__roiSpin.setMaxValue(1000)
        else:
            self.__roiSpin.setMinimum(10)
            self.__roiSpin.setMaximum(1000)
        self.__roiSpin.setValue(int(ROIWIDTH))
        box3.l.addWidget(label)
        box3.l.addWidget(self.__roiSpin)


        #BATCH SPLITTING
        self.__splitBox = qt.QCheckBox(vBox)
        self.__splitBox.setText('EXPERIMENTAL: Use several processes')
        vBox.l.addWidget(self.__splitBox)
        #box3 = qt.QHBox(box2)
        self.__box4 = qt.QWidget(boxStep0)
        box4 = self.__box4
        box4.l = qt.QHBoxLayout(box4)
        box4.l.setContentsMargins(0, 0, 0, 0)
        box4.l.setSpacing(0)
        boxStep0.l.addWidget(box4)

        label= qt.QLabel(box4)
        label.setText("Number of processes:")
        self.__splitSpin = qt.QSpinBox(box4)
        if QTVERSION < '4.0.0':
            self.__splitSpin.setMinValue(1)
            self.__splitSpin.setMaxValue(1000)
        else:
            self.__splitSpin.setMinimum(1)
            self.__splitSpin.setMaximum(1000)
        self.__splitSpin.setValue(2)
        box4.l.addWidget(label)
        box4.l.addWidget(self.__splitSpin)

        self._layout.addWidget(bigbox)

        if actions: self.__buildActions()


    def __clickSignal0(self):
        if self.__overwrite.isChecked():
            self.__useExisting.setChecked(0)
        else:
            self.__useExisting.setChecked(1)

    def __clickSignal1(self):
        if self.__useExisting.isChecked():
            self.__overwrite.setChecked(0)
        else:
            self.__overwrite.setChecked(1)

    def __clickSignal2(self):
        #self.__tableBox.setEnabled(True)
        pass

    def __clickSignal3(self):
        if self.__htmlBox.isChecked():
            self.__tableBox.setEnabled(True)
            #self.__concentrationsBox.setEnabled(True)
            self.__fitBox.setChecked(True)
            self.__fitBox.setEnabled(False)
        else:
            self.__tableBox.setEnabled(False)
            #self.__concentrationsBox.setEnabled(False)
            self.__fitBox.setChecked(False)
            self.__fitBox.setEnabled(True)


    def __buildActions(self):
        box = qt.QWidget(self)
        box.l = qt.QHBoxLayout(box)
        box.l.addWidget(qt.HorizontalSpacer(box))
        self.__dismissButton = qt.QPushButton(box)
        box.l.addWidget(self.__dismissButton)
        box.l.addWidget(qt.HorizontalSpacer(box))
        self.__dismissButton.setText("Close")
        self.__startButton   = qt.QPushButton(box)
        box.l.addWidget(self.__startButton)
        box.l.addWidget(qt.HorizontalSpacer(box))
        self.__startButton.setText("Start")
        self.__dismissButton.clicked.connect(self.close)
        self.__startButton.clicked.connect(self.start)
        self._layout.addWidget(box)

    def close(self):
        if self._edfSimpleViewer is not None:
            self._edfSimpleViewer.close()
            self._edfSimpleViewer = None
        qt.QWidget.close(self)

    def setFileList(self,filelist=None):
        if filelist is None:filelist = []
        if True or self.__goodFileList(filelist):
            text = ""
            oldtype = None
            #do not sort the file list
            #respect user choice
            #filelist.sort()
            for file in filelist:
                filetype = self.__getFileType(file)
                if filetype is None:return
                if oldtype  is None: oldtype = filetype
                if oldtype != filetype:
                    qt.QMessageBox.critical(self, "ERROR",
                        "Type %s does not match type %s on\n%s"% (filetype,oldtype,file))
                    return
                text += "%s\n" % file

            if len(filelist):
                if HDF5SUPPORT:
                    if not h5py.is_hdf5(filelist[0]):
                        self._hdf5Widget.hide()
                        self._selection=None
                    else:
                        dialog = qt.QDialog(self)
                        dialog.setWindowTitle('Select your data set')
                        dialog.mainLayout = qt.QVBoxLayout(dialog)
                        dialog.mainLayout.setContentsMargins(0, 0, 0, 0)
                        dialog.mainLayout.setSpacing(0)
                        datasource = NexusDataSource.NexusDataSource(filelist[0])
                        nexusWidget = QNexusWidget.QNexusWidget(dialog,
                                                                buttons=True)
                        nexusWidget.buttons.hide()
                        nexusWidget.setDataSource(datasource)
                        button = qt.QPushButton(dialog)
                        button.setText("Done")
                        button.setAutoDefault(True)
                        button.clicked.connect(dialog.accept)
                        dialog.mainLayout.addWidget(nexusWidget)
                        dialog.mainLayout.addWidget(button)
                        ret = dialog.exec()
                        cntSelection = nexusWidget.cntTable.getCounterSelection()
                        cntlist = cntSelection['cntlist']
                        if not len(cntlist):
                            text = "No dataset selection"
                            self.showMessage(text)
                            self.__listView.clear()
                            return
                        if not len(cntSelection['y']):
                            text = "No dataset selected as y"
                            self.showMessage(text)
                            self.__listView.clear()
                            return
                        datasource = None
                        selection = {}
                        selection['x'] = []
                        selection['y'] = []
                        selection['m'] = []
                        for key in ['x', 'y', 'm']:
                            if len(cntSelection[key]):
                                for idx in cntSelection[key]:
                                    selection[key].append(cntlist[idx])
                        self._selection = selection
                        self._hdf5Widget.setSelection(selection)
                        #they are not used yet
                        #self._hdf5Widget.selectionWidgetsDict['x'].hide()
                        #self._hdf5Widget.selectionWidgetsDict['m'].hide()
                        if self._hdf5Widget.isHidden():
                            self._hdf5Widget.show()
                elif filelist[0][-3:].lower() in ['.h5', 'nxs', 'hdf', 'hdf5']:
                            text = "Warning, this looks as an HDF5 file "
                            text += "but you do not have HDF5 support."
                            self.showMessage(text)
            self.fileList = filelist
            if len(self.fileList):
                self.inputDir = os.path.dirname(self.fileList[0])
                PyMcaDirs.inputDir = os.path.dirname(self.fileList[0])
            if QTVERSION < '4.0.0':
                self.__listView.setText(text)
            else:
                self.__listView.clear()
                self.__listView.insertPlainText(text)

    def showMessage(self, text):
        msg = qt.QMessageBox(self)
        msg.setWindowTitle("PyMcaBatch Message")
        msg.setIcon(qt.QMessageBox.Information)
        msg.setText(text)
        msg.exec()

    def setConfigFile(self,configfile=None):
        if configfile is None:return
        if self.__goodConfigFile(configfile):
            self.configFile = configfile
            if type(configfile) == type([]):
                #do not sort file list
                #self.configFile.sort()
                self.__configLine.setText(self.configFile[0])
                self.lastInputDir = os.path.dirname(self.configFile[0])
            else:
                self.__configLine.setText(configfile)
                self.lastInputDir = os.path.dirname(self.configFile)

    def setOutputDir(self,outputdir=None):
        if outputdir is None:
            return
        if self.__goodOutputDir(outputdir):
            self.outputDir = outputdir
            PyMcaDirs.outputDir = outputdir
            self.__outLine.setText(outputdir)
        else:
            qt.QMessageBox.critical(self, "ERROR",
                "Cannot use output directory:\n%s"% (outputdir))

    def __goodFileList(self,filelist):
        if not len(filelist):
            return True
        for ffile in filelist:
            if not os.path.exists(ffile):
                qt.QMessageBox.critical(self, "ERROR",
                                    'File %s\ndoes not exist' % ffile)
                self.raise_()
                return False
        return True

    def __goodConfigFile(self,configfile0):
        if type(configfile0) != type([]):
            configfileList = [configfile0]
        else:
            configfileList = configfile0
        for configfile in configfileList:
            if not os.path.exists(configfile):
                qt.QMessageBox.critical(self,
                             "ERROR",'File %s\ndoes not exist' % configfile)
                self.raise_()
                return False
            elif len(configfile.split()) > 1:
                if sys.platform != 'win32':
                    qt.QMessageBox.critical(self,
                                 "ERROR",'Configuration File:\n %s\ncontains spaces in the path' % configfile)
                    self.raise_()
                    return False
        return True

    def __goodOutputDir(self,outputdir):
        if not os.path.isdir(outputdir):
            return False
        elif len(outputdir.split()) > 1:
            if sys.platform != 'win32':
                qt.QMessageBox.critical(self,
                    "ERROR",
                    'Output Directory:\n %s\ncontains spaces in the path' % outputdir)
                self.raise_()
                return False
        return True

    def __getFileType(self,inputfile):
        try:
            ffile = None
            try:
                ffile   = EdfFileLayer.EdfFileLayer(fastedf=0)
                ffile.SetSource(inputfile)
                fileinfo = ffile.GetSourceInfo()
                if fileinfo['KeyList'] == []:ffile=None
                return "EdfFile"
            except Exception:
                pass
            if (ffile is None):
                ffile   = SpecFileLayer.SpecFileLayer()
                ffile.SetSource(inputfile)
            del ffile
            return "Specfile"
        except Exception:
            qt.QMessageBox.critical(self,
                                    sys.exc_info()[0],
                                    'I do not know what to do with file\n %s' % ffile)
            self.raise_()
            return None

    def browseList(self):
        self.inputDir = PyMcaDirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        wfilter = self.inputFilter
        filetypes = ""
        if HDF5SUPPORT:
            filetypes += "HDF5 (*.nxs *.h5 *.hdf *.hdf5)\n"
        filetypes += "McaFiles (*.mca)\nEdfFiles (*.edf)\n"
        filetypes += "SpecFiles (*.spec)\nSpecFiles (*.dat)\nAll files (*)"
        filetypelist = filetypes.split("\n")
        filelist, filefilter = PyMcaFileDialogs.getFileList(self,
                                                filetypelist=filetypelist,
                                                message="Open a set of files",
                                                currentdir=wdir,
                                                mode="OPEN",
                                                getfilter=True,
                                                single=False,
                                                currentfilter=wfilter)

        if len(filelist):
            self.setFileList(filelist)
            self.inputFilter = filefilter
        self.raise_()

    def browseConfig(self):
        self.inputDir = PyMcaDirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        filetypelist = ["Config Files (*.cfg)", "All files (*)"]
        fileList, filefilter = PyMcaFileDialogs.getFileList(self,
                                                filetypelist=filetypelist,
                                                message="Open a new fit config file",
                                                currentdir=wdir,
                                                mode="OPEN",
                                                getfilter=True,
                                                single=False,
                                                currentfilter=None)

        if len(fileList) == 1:
            self.setConfigFile(fileList[0])
        elif len(fileList):
            self.setConfigFile(fileList)
        self.raise_()

    def browseOutputDir(self):
        self.outputDir = PyMcaDirs.outputDir
        if not os.path.exists(self.outputDir):
            self.outputDir =  os.getcwd()
        wdir = self.outputDir
        outdir =PyMcaFileDialogs.getExistingDirectory(self,
                                    message="Output Directory Selection",
                                    mode="SAVE",
                                    currentdir=wdir)
        if len(outdir):
            self.setOutputDir(outdir)
        self.raise_()

    def start(self):
        if not len(self.fileList):
            qt.QMessageBox.critical(self, "ERROR",'Empty file list')
            self.raise_()
            return

        if self.__splitBox.isChecked():
            if sys.platform == 'darwin':
                if ".app" in os.path.dirname(__file__):
                    text  = 'Multiple processes only supported on MacOS X when built from source\n'
                    text += 'and not when running the frozen binary.'
                    qt.QMessageBox.critical(self, "ERROR",text)
                    self.raise_()
                    return
            if len(self.fileList) == 1:
                if int(qt.safe_str(self.__splitSpin.text())) > 1:
                    allowSingleFileSplitProcesses = False
                    if HDF5SUPPORT:
                        if h5py.is_hdf5(self.fileList[0]):
                            _logger.info("Allowing single HDF5 file process split")
                            _logger.info("In the past it was problematic")
                            allowSingleFileSplitProcesses = True
                    if not allowSingleFileSplitProcesses:
                        text = "Multiple processes can only be used with multiple input files."
                        qt.QMessageBox.critical(self, "ERROR",text)
                        self.raise_()
                        return

        if (self.configFile is None) or (not self.__goodConfigFile(self.configFile)):
            qt.QMessageBox.critical(self, "ERROR",'Invalid fit configuration file')
            self.raise_()
            return
        if type(self.configFile) == type([]):
            if len(self.configFile) != len(self.fileList):
                qt.QMessageBox.critical(self, "ERROR",
      'Number of config files should be either one or equal to number of files')
                self.raise_()
                return
        if (self.outputDir is None) or (not self.__goodOutputDir(self.outputDir)):
            qt.QMessageBox.critical(self, "ERROR",'Invalid output directory')
            self.raise_()
            return
        name = "LegacyBatch from %s to %s " % (os.path.basename(self.fileList[ 0]),
                                          os.path.basename(self.fileList[-1]))
        roifit  = self.__roiBox.isChecked()
        html    = self.__htmlBox.isChecked()
        #if html:
        concentrations = self.__concentrationsBox.isChecked()
        #else:
        #    concentrations = 0
        if self.__tableBox.isChecked():
            if self.__extendedTable.isChecked():
                table = 2
            else:
                table = 1
        else:   table =0

        #htmlindex = qt.safe_str(self.__htmlIndex.text())
        htmlindex = "index.html"
        if html:
            if  len(htmlindex)<5:
                htmlindex+=".html"
            if  len(htmlindex) == 5:
                htmlindex = "index.html"
            if htmlindex[-5:] != "html":
                htmlindex+=".html"
        roiwidth = float(qt.safe_str(self.__roiSpin.text()))
        if 0:
            overwrite= self.__overwrite.isChecked()
            filestep = int(qt.safe_str(self.__fileSpin.text()))
            mcastep  = int(qt.safe_str(self.__mcaSpin.text()))
        else:
            overwrite= 1
            filestep = 1
            mcastep = 1
            if len(self.fileList) == 1:
                if self.__splitBox.isChecked():
                    nbatches = int(qt.safe_str(self.__splitSpin.text()))
                    mcastep = nbatches

        fitfiles = self.__fitBox.isChecked()
        selection = self._selection
        if selection is None:
            selectionFlag = False
        else:
            selectionFlag = True

        if self._edfSimpleViewer is not None:
            self._edfSimpleViewer.close()
            self._edfSimpleViewer = None
        if roifit:
            window =  McaBatchWindow(name="ROI"+name,actions=1, outputdir=self.outputDir,
                                     html=html, htmlindex=htmlindex, table = 0,
                                     showresult=self._showResult)
            b = McaBatch(window,self.configFile,self.fileList,self.outputDir,roifit=roifit,
                         roiwidth=roiwidth,overwrite=overwrite,filestep=1,mcastep=1,
                         concentrations=0, fitfiles=fitfiles, selection=selection)
            def cleanup():
                b.pleasePause = 0
                b.pleaseBreak = 1
                if hasattr(b, "wait"):
                    b.wait()
                qApp = qt.QApplication.instance()
                qApp.processEvents()
                qApp = None

            def pause():
                if b.pleasePause:
                    b.pleasePause=0
                    window.pauseButton.setText("Pause")
                else:
                    b.pleasePause=1
                    window.pauseButton.setText("Continue")
            window.pauseButton.clicked.connect(pause)
            window.abortButton.clicked.connect(window.close)
            window.abortButton.clicked.connect(cleanup)
            #qApp = qt.QApplication.instance()
            #qApp.aboutToQuit[()].connect(cleanup)
            self.__window = window
            self.__b      = b
            window.show()
            b.start()
        elif (sys.platform == 'darwin') and\
             ((".app" in os.path.dirname(__file__)) or (not self.__splitBox.isChecked())):
            #almost identical to batch
            window =  McaBatchWindow(name="ROI"+name,actions=1,outputdir=self.outputDir,
                                     html=html,htmlindex=htmlindex, table = table,
                                     showresult=self._showResult)
            b = McaBatch(window,self.configFile,self.fileList,self.outputDir,roifit=roifit,
                         roiwidth=roiwidth,overwrite=overwrite,filestep=filestep,
                         mcastep=mcastep, concentrations=concentrations, fitfiles=fitfiles,
                         selection=selection)
            def cleanup():
                b.pleasePause = 0
                b.pleaseBreak = 1
                if hasattr(b, "wait"):
                    b.wait()
                qApp = qt.QApplication.instance()
                qApp.processEvents()

            def pause():
                if b.pleasePause:
                    b.pleasePause=0
                    window.pauseButton.setText("Pause")
                else:
                    b.pleasePause=1
                    window.pauseButton.setText("Continue")
            window.pauseButton.clicked.connect(pause)
            window.abortButton.clicked.connect(window.close)
            window.abortButton.clicked.connect(cleanup)
            #qApp = qt.QApplication.instance()
            #qApp.aboutToQuit[()].connect(cleanup)
            window._rootname = "%s"% b._rootname
            self.__window = window
            self.__b      = b
            window.show()
            b.start()
        elif sys.platform == 'win32':
            try:
                dirname = os.path.dirname(__file__)
                frozen = False
                if not os.path.exists(os.path.join(dirname, "LegacyPyMcaBatch.py")):
                    # script usage case
                    dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
            except Exception:
                # __file__ is not defined
                dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
                frozen = True
            if os.path.basename(sys.executable) in ["PyMcaMain.exe",
                                                    "LegacyPyMcaBatch.exe"]:
                frozen = True
                dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
            listfile = os.path.join(self.outputDir, "tmpfile")
            self.genListFile(listfile, config=False)
            if frozen:
                # we are at level PyMca5\PyMcaGui\pymca
                dirname  = os.path.dirname(dirname)
                # level PyMcaGui
                dirname  = os.path.dirname(dirname)
                # level PyMca5
                dirname  = os.path.dirname(dirname)
                # directory level with exe files
                myself   = os.path.join(dirname, "LegacyPyMcaBatch.exe")
                viewer   = os.path.join(dirname, "EdfFileSimpleViewer.exe")
                rgb    = os.path.join(dirname, "PyMcaPostBatch.exe")
                if not os.path.exists(viewer):
                    viewer = None
                if not os.path.exists(rgb):
                    rgb = None
            else:
                myself = os.path.join(dirname, "LegacyPyMcaBatch.py")
                viewer = os.path.join(dirname, "EdfFileSimpleViewer.py")
                rgb    = os.path.join(dirname, "PyMcaPostBatch.py")
                if not os.path.exists(viewer):
                    viewer = None
                else:
                    viewer = '%s "%s"' % (sys.executable, viewer)
                if not os.path.exists(rgb):
                    rgb    = None
                else:
                    rgb = '%s "%s"' % (sys.executable, rgb)
            self._rgb = rgb
            if type(self.configFile) == type([]):
                cfglistfile = os.path.join(self.outputDir, "tmpfile.cfg")
                self.genListFile(cfglistfile, config=True)
                dirname  = os.path.dirname(dirname)
                if frozen:
                    cmd = '"%s" --cfglistfile="%s" --outdir="%s" --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile="%s" --concentrations=%d --table=%d --fitfiles=%d --selection=%d --showresult=%d --exitonend=%d' %\
                                                                  (myself,
                                                                    cfglistfile,
                                                                    self.outputDir, overwrite,
                                                                    filestep, mcastep,
                                                                    html,htmlindex,
                                                                    listfile,concentrations,
                                                                    table, fitfiles, selectionFlag,
                                                                    self._showResult, 1)
                else:
                    cmd = '%s "%s" --cfglistfile="%s" --outdir="%s" --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile="%s" --concentrations=%d --table=%d --fitfiles=%d --selection=%d --showresult=%d --exitonend=%d' %\
                                                                  (sys.executable,myself,
                                                                    cfglistfile,
                                                                    self.outputDir, overwrite,
                                                                    filestep, mcastep,
                                                                    html,htmlindex,
                                                                    listfile,concentrations,
                                                                    table, fitfiles, selectionFlag,
                                                                    self._showResult, 1)
            else:
                if not frozen:
                    cmd = '%s "%s" --cfg="%s" --outdir="%s" --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile="%s" --concentrations=%d --table=%d --fitfiles=%d --selection=%d --showresult=%d --exitonend=%d' % \
                                                                  (sys.executable, myself,
                                                                    self.configFile,
                                                                    self.outputDir, overwrite,
                                                                    filestep, mcastep,
                                                                    html,htmlindex,
                                                                    listfile,concentrations,
                                                                    table, fitfiles, selectionFlag,
                                                                    self._showResult, 1)
                else:
                    cmd = '"%s" --cfg="%s" --outdir="%s" --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile="%s" --concentrations=%d --table=%d --fitfiles=%d --selection=%d --showresult=%d --exitonend=%d' % \
                                                                  (myself,
                                                                    self.configFile,
                                                                    self.outputDir, overwrite,
                                                                    filestep, mcastep,
                                                                    html,htmlindex,
                                                                    listfile,concentrations,
                                                                    table, fitfiles, selectionFlag,
                                                                    self._showResult, 1)
            self.hide()
            qApp = qt.QApplication.instance()
            qApp.processEvents()
            _logger.debug("cmd = %s", cmd)
            if self.__splitBox.isChecked():
                nbatches = int(qt.safe_str(self.__splitSpin.text()))
                if len(self.fileList) > 1:
                    filechunk = int(len(self.fileList)/nbatches)
                    processList = []
                    for i in range(nbatches):
                        beginoffset = filechunk * i
                        endoffset   = len(self.fileList) - filechunk * (i+1)
                        if (i+1) == nbatches:endoffset = 0
                        cmd1        = cmd + " --filebeginoffset=%d --fileendoffset=%d --chunk=%d" % \
                                              (beginoffset, endoffset, i)
                        try:
                            processList.append(subprocess.Popen(cmd1,
                                                            cwd=os.getcwd()))
                        except UnicodeEncodeError:
                            processList.append(\
                                subprocess.Popen(cmd1.encode(sys.getfilesystemencoding()),
                                                 cwd=os.getcwd()))

                        _logger.debug("cmd = %s", cmd1)
                else:
                    #f = open("CMD", 'wb')
                    processList = []
                    for i in range(nbatches):
                        #the mcastep has been dealt with above
                        cmd1        = cmd + " --mcaoffset=%d --chunk=%d" % (i, i)
                        processList.append(subprocess.Popen(cmd1, cwd=os.getcwd()))
                        _logger.debug("CMD = %s", cmd1)
                        #f.write(cmd1+"\n")
                    #f.close()
                self._processList = processList
                if self._timer is None:
                    self._timer = qt.QTimer(self)
                    self._timer.timeout[()].connect(self._pollProcessList)
                if not self._timer.isActive():
                    self._timer.start(1000)
                else:
                    _logger.info("timer was already active")
                return
            else:
                try:
                    subprocess.call(cmd)
                except UnicodeEncodeError:
                    try:
                        subprocess.call(cmd.encode(sys.getfilesystemencoding()))
                    except Exception:
                        # be ready for any weird error like missing that encoding
                        try:
                            subprocess.call(cmd.encode('utf-8'))
                        except UnicodeEncodeError:
                            subprocess.call(cmd.encode('latin-1'))
            self.show()
        else:
            listfile = os.path.join(self.outputDir, "tmpfile")
            self.genListFile(listfile, config=False)
            try:
                dirname = os.path.dirname(__file__)
                frozen = False
                if not os.path.exists(os.path.join(dirname, "LegacyPyMcaBatch.py")):
                    # script usage case
                    dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
            except Exception:
                # __file__ is not defined
                dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
                frozen = True
            if not frozen:
                if os.path.basename(sys.executable) in ["PyMcaMain.exe",
                                                        "LegacyPyMcaBatch.exe",
                                                        "PyMcaMain",
                                                        "LegacyPyMcaBatch"]:
                    frozen = True
                    dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
            if frozen:
                # we are at level PyMca5\PyMcaGui\pymca
                dirname  = os.path.dirname(dirname)
                # level PyMcaGui
                dirname  = os.path.dirname(dirname)
                # level PyMca5
                dirname  = os.path.dirname(dirname)
                # directory level with exe files
                myself   = os.path.join(dirname, "LegacyPyMcaBatch")
                viewer   = os.path.join(dirname, "EdfFileSimpleViewer")
                rgb    = os.path.join(dirname, "PyMcaPostBatch")
                if not os.path.exists(viewer):
                    viewer = None
                if not os.path.exists(rgb):
                    rgb = None
            else:
                myself = os.path.join(dirname, "LegacyPyMcaBatch.py")
                if not os.path.exists(os.path.join(dirname, myself)):
                    dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
                    if not os.path.exists(os.path.join(dirname, myself)):
                        text  = 'Cannot locate LegacyPyMcaBatch.py file.\n'
                        qt.QMessageBox.critical(self, "ERROR",text)
                        self.raise_()
                        return
                myself  = sys.executable+" "+ os.path.join(dirname, myself)
                viewer = os.path.join(dirname, "EdfFileSimpleViewer.py")
                rgb    = os.path.join(dirname, "PyMcaPostBatch.py")
                if not os.path.exists(viewer):
                    viewer = None
                else:
                    viewer = '%s "%s"' % (sys.executable, viewer)
                if not os.path.exists(rgb):
                    rgb    = None
                else:
                    rgb = '%s "%s"' % (sys.executable, rgb)

            self._rgb = rgb
            if type(self.configFile) == type([]):
                cfglistfile = os.path.join(self.outputDir, "tmpfile.cfg")
                self.genListFile(cfglistfile, config=True)
                cmd = "%s --cfglistfile=%s --outdir=%s --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile=%s  --concentrations=%d --table=%d --fitfiles=%d --selection=%d  --showresult=%d --exitonend=%d &" % \
                                                    (myself,
                                                    cfglistfile,
                                                    self.outputDir, overwrite,
                                                    filestep, mcastep, html, htmlindex, listfile,
                                                    concentrations, table, fitfiles,
                                                    selectionFlag, self._showResult, 1)
            else:
                cmd = "%s --cfg=%s --outdir=%s --overwrite=%d --filestep=%d --mcastep=%d --html=%d --htmlindex=%s --listfile=%s  --concentrations=%d --table=%d --fitfiles=%d  --selection=%d  --showresult=%d --exitonend=%d &" % \
                                                   (myself, self.configFile,
                                                    self.outputDir, overwrite,
                                                    filestep, mcastep, html, htmlindex, listfile,
                                                    concentrations, table, fitfiles,
                                                    selectionFlag, self._showResult, 1)
            _logger.debug("cmd = %s", cmd)
            if self.__splitBox.isChecked():
                qApp = qt.QApplication.instance()
                qApp.processEvents()
                nbatches = int(qt.safe_str(self.__splitSpin.text()))
                filechunk = int(len(self.fileList)/nbatches)
                processList = []
                for i in range(nbatches):
                    beginoffset = filechunk * i
                    endoffset   = len(self.fileList) - filechunk * (i+1)
                    if (i+1) == nbatches:endoffset = 0
                    cmd1 = cmd.replace("&", "") + \
                           " --filebeginoffset=%d --fileendoffset=%d --chunk=%d" % \
                            (beginoffset, endoffset, i)
                    # unfortunately I have to set shell = True
                    # otherways I get a file not found error in the
                    # child process
                    processList.append(\
                        subprocess.Popen(cmd1,
                                         cwd=os.getcwd(),
                                         shell=True,
                                         close_fds=True))
                self._processList = processList
                self.hide()
                self._pollProcessList()
                if self._timer is None:
                    self._timer = qt.QTimer(self)
                    self._timer.timeout[()].connect( \
                                       self._pollProcessList)
                if not self._timer.isActive():
                    self._timer.start(1000)
                else:
                    _logger.info("timer was already active")
                return
            else:
                os.system(cmd)
                _logger.info(" COMMAND = %s", cmd)
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Information)
                text = "Your batch has been started as an independent process."
                msg.setText(text)
                # REMARK: non-blocking for unit testing
                #msg.exec()
                msg.show()

    def genListFile(self, listfile, config=None):
        if os.path.exists(listfile):
            try:
                os.remove(listfile)
            except Exception:
                _logger.error("Cannot delete file %s", listfile)
                raise
        if config is None:
            lst = self.fileList
        elif config:
            lst = self.configFile
        else:
            lst = self.fileList

        if lst == self.fileList:
            if self._selection is not None:
                ddict = ConfigDict.ConfigDict()
                ddict['PyMcaBatch'] = {}
                ddict['PyMcaBatch']['filelist'] = lst
                ddict['PyMcaBatch']['selection'] = self._selection
                ddict.write(listfile)
                return
        fd=open(listfile, 'wb')
        for filename in lst:
            # only the file system encoding makes sense here
            fd.write(('%s\n' % filename).encode(sys.getfilesystemencoding()))
        fd.close()

    def _pollProcessList(self):
        processList = self._processList
        rgb         = self._rgb
        if QTVERSION < '4.0.0':rgb = None
        n = 0
        for process in processList:
            if process.poll() is None:
                n += 1
        if n > 0: return
        self._timer.stop()
        self.show()
        self.raise_()

        work = PyMcaBatchBuildOutput.PyMcaBatchBuildOutput(os.path.join(self.outputDir, "IMAGES"))
        if _logger.getEffectiveLevel() == logging.DEBUG:
            a, b, c = work.buildOutput(delete=False)
        else:
            a, b, c = work.buildOutput(delete=True)
        if self._showResult:
            if len(a):
                if self._edfSimpleViewer is None:
                    self._edfSimpleViewer = EdfFileSimpleViewer.EdfFileSimpleViewer()
                self._edfSimpleViewer.setFileList(a)
                self._edfSimpleViewer.show()
            if rgb is not None:
                if len(b):
                    if sys.platform == "win32":
                        try:
                            subprocess.Popen('%s "%s"' % (rgb, b[0]),
                                            cwd = os.getcwd())
                        except UnicodeEncodeError:
                            subprocess.Popen(('%s "%s"' % (rgb, b[0])).encode(sys.getfilesystemencoding()),
                                            cwd = os.getcwd())
                    else:
                        os.system("%s %s &" % (rgb, b[0]))
        work = PyMcaBatchBuildOutput.PyMcaBatchBuildOutput(self.outputDir)
        if _logger.getEffectiveLevel() == logging.DEBUG:
            work.buildOutput(delete=False)
        else:
            work.buildOutput(delete=True)

class McaBatch(McaAdvancedFitBatch.McaAdvancedFitBatch, QThread):
    def __init__(self, parent, configfile, filelist=None, outputdir = None,
                     roifit = None, roiwidth=None, overwrite=1,
                     filestep=1, mcastep=1, concentrations=0,
                     fitfiles=0, filebeginoffset=0, fileendoffset=0,
                     mcaoffset=0, chunk=None,
                     selection=None, lock=None):
        McaAdvancedFitBatch.McaAdvancedFitBatch.__init__(self, configfile,
                                                         filelist=filelist, outputdir=outputdir,
                                                         roifit=roifit, roiwidth=roiwidth,
                                                         overwrite=overwrite, filestep=filestep,
                                                         mcastep=mcastep,
                                                         concentrations=concentrations,
                                                         fitfiles=fitfiles,
                                                         filebeginoffset = filebeginoffset,
                                                         fileendoffset = fileendoffset,
                                                         mcaoffset  = mcaoffset,
                                                         chunk=chunk,
                                                         selection=selection,
                                                         lock=lock)
        QThread.__init__(self)
        self.parent = parent
        self.pleasePause = 0

    def run(self):
        self.processList()

    def onNewFile(self, ffile, filelist):
        self.__lastOnNewFile = ffile
        ddict = {'file':ffile,
                 'filelist':filelist,
                 'filestep':self.fileStep,
                 'filebeginoffset':self.fileBeginOffset,
                 'fileendoffset':self.fileEndOffset,
                 'event':'onNewFile'}

        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))

        if self.pleasePause:self.__pauseMethod()

    def onImage(self, key, keylist):
        ddict = {'key':key, 'keylist':keylist, 'event':'onImage'}
        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))

    def onMca(self, mca, nmca, filename=None, key=None, info=None):
        _logger.debug("onMca key = %s", key)
        ddict = {'mca':mca,
                 'nmca':nmca,
                 'mcastep':self.mcaStep,
                 'filename':filename,
                 'key':key,
                 'info':info,
                 'outputdir':self._outputdir,
                 'useExistingFiles':self.useExistingFiles,
                 'roifit':self.roiFit,
                 'event':'onMca'}

        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))

        if self.pleasePause:self.__pauseMethod()

    def onEnd(self):
        _logger.debug("onEnd")

        ddict = {'event':'onEnd',
                 'filestep':self.fileStep,
                 'mcastep':self.mcaStep,
                 'chunk':self.chunk,
                 'savedimages':self.savedImages}

        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))

        if self.pleasePause:
            self.__pauseMethod()

    def __pauseMethod(self):
        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchPaused'}))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchPaused'}))

        while(self.pleasePause):
            time.sleep(1)

        if QTVERSION < '4.0.0':
            self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchResumed'}))
        else:
            qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchResumed'}))


class McaBatchWindow(qt.QWidget):
    def __init__(self,parent=None, name="BatchWindow", fl=0, actions = 0, outputdir=None, html=0,
                    htmlindex = None, table=2, chunk=None, exitonend=False, showresult=True):
        if QTVERSION < '4.0.0':
            qt.QWidget.__init__(self, parent, name, fl)
            self.setCaption(name)
        else:
            qt.QWidget.__init__(self, parent)
            self.setWindowTitle(name)
        self.chunk = chunk
        self.exitonend = exitonend
        self._showResult = showresult
        self.l = qt.QVBoxLayout(self)
        #self.l.setAutoAdd(1)
        self.bars =qt.QWidget(self)
        self.l.addWidget(self.bars)
        if QTVERSION < '4.0.0':
            self.barsLayout = qt.QGridLayout(self.bars,2,3)
        else:
            self.barsLayout = qt.QGridLayout(self.bars)
            self.barsLayout.setContentsMargins(2, 2, 2, 2)
            self.barsLayout.setSpacing(3)
        self.progressBar   = qt.QProgressBar(self.bars)
        self.progressLabel = qt.QLabel(self.bars)
        self.progressLabel.setText('File Progress:')
        self.imageBar   = qt.QProgressBar(self.bars)
        self.imageLabel = qt.QLabel(self.bars)
        self.imageLabel.setText('Image in File:')
        self.mcaBar   = qt.QProgressBar(self.bars)
        self.mcaLabel = qt.QLabel(self.bars)
        self.mcaLabel.setText('MCA in Image:')

        self.barsLayout.addWidget(self.progressLabel,0,0)
        self.barsLayout.addWidget(self.progressBar,0,1)
        self.barsLayout.addWidget(self.imageLabel,1,0)
        self.barsLayout.addWidget(self.imageBar,1,1)
        self.barsLayout.addWidget(self.mcaLabel,2,0)
        self.barsLayout.addWidget(self.mcaBar,2,1)
        self.status      = qt.QLabel(self)
        self.status.setText(" ")
        self.timeLeft      = qt.QLabel(self)
        self.l.addWidget(self.status)
        self.l.addWidget(self.timeLeft)

        self.timeLeft.setText("Estimated time left = ???? min")
        self.time0 = None
        self.html  = html
        if htmlindex is None:htmlindex="index.html"
        self.htmlindex = htmlindex
        self.outputdir = outputdir
        self.table = table
        self.__ended         = False
        self.__writingReport = False

        if actions: self.addButtons()
        self.show()
        self.raise_()


    def addButtons(self):
        self.actions = 1
        self.buttonsBox = qt.QWidget(self)
        l = qt.QHBoxLayout(self.buttonsBox)
        l.addWidget(qt.HorizontalSpacer(self.buttonsBox))
        self.pauseButton = qt.QPushButton(self.buttonsBox)
        l.addWidget(self.pauseButton)
        l.addWidget(qt.HorizontalSpacer(self.buttonsBox))
        self.pauseButton.setText("Pause")
        self.abortButton   = qt.QPushButton(self.buttonsBox)
        l.addWidget(self.abortButton)
        l.addWidget(qt.HorizontalSpacer(self.buttonsBox))
        self.abortButton.setText("Abort")
        self.l.addWidget(self.buttonsBox)
        self.update()

    def customEvent(self,event):
        if   event.dict['event'] == 'onNewFile':self.onNewFile(event.dict['file'],
                                                               event.dict['filelist'],
                                                               event.dict['filestep'],
                                                               event.dict['filebeginoffset'],
                                                               event.dict['fileendoffset'])
        elif event.dict['event'] == 'onImage':  self.onImage  (event.dict['key'],
                                                               event.dict['keylist'])
        elif event.dict['event'] == 'onMca':    self.onMca    (event.dict)
                                                               #event.dict['mca'],
                                                               #event.dict['nmca'],
                                                               #event.dict['mcastep'],
                                                               #event.dict['filename'],
                                                               #event.dict['key'])
        elif event.dict['event'] == 'onEnd':    self.onEnd(event.dict)

        elif event.dict['event'] == 'batchPaused': self.onPause()

        elif event.dict['event'] == 'batchResumed':self.onResume()

        elif event.dict['event'] == 'reportWritten':self.onReportWritten()

        else:
            _logger.warning("Unhandled event %s", event)


    def onNewFile(self, file, filelist, filestep, filebeginoffset =0, fileendoffset = 0):
        _logger.debug("onNewFile: %s", file)
        indexlist = list(range(0,len(filelist),filestep))
        index  = indexlist.index(filelist.index(file)) - filebeginoffset
        #print index + filebeginoffset
        if index == 0:
            self.report= None
            if self.html:
                self.htmlindex = os.path.join(self.outputdir, 'HTML')
                htmlindex = os.path.join(os.path.basename(file)+"_HTMLDIR",
                            "index.html")
                self.htmlindex = os.path.join(self.htmlindex,htmlindex)
                if os.path.exists(self.htmlindex):
                    try:
                        os.remove(self.htmlindex)
                    except Exception:
                        _logger.warning("cannot delete file %s", self.htmlindex)
        nfiles = len(indexlist)-filebeginoffset-fileendoffset
        self.status.setText("Processing file %s" % file)
        e = time.time()
        if QTVERSION < '4.0.0':
            self.progressBar.setTotalSteps(nfiles)
            self.progressBar.setProgress(index)
        else:
            self.progressBar.setMaximum(nfiles)
            self.progressBar.setValue(index)
        if self.time0 is not None:
            t = (e - self.time0) * (nfiles - index)
            self.time0 =e
            if t < 120:
                self.timeLeft.setText("Estimated time left = %d sec" % (t))
            else:
                self.timeLeft.setText("Estimated time left = %d min" % (int(t / 60.)))
        else:
            self.time0 = e
        if sys.platform == 'darwin':
            qApp = qt.QApplication.instance()
            qApp.processEvents()

    def onImage(self, key, keylist):
        _logger.debug("onImage %s",  key)
        i = keylist.index(key) + 1
        n = len(keylist)
        if QTVERSION < '4.0.0':
            self.imageBar.setTotalSteps(n)
            self.imageBar.setProgress(i)
            self.mcaBar.setTotalSteps(1)
            self.mcaBar.setProgress(0)
        else:
            self.imageBar.setMaximum(n)
            self.imageBar.setValue(i)
            self.mcaBar.setMaximum(1)
            self.mcaBar.setValue(0)


    #def onMca(self, mca, nmca, mcastep):
    def onMca(self, ddict):
        _logger.debug("onMca %s", ddict['mca'])
        mca  = ddict['mca']
        nmca = ddict['nmca']
        mcastep  = ddict['mcastep']
        filename = ddict['filename']
        key = ddict['key']
        info = ddict['info']
        outputdir = ddict['outputdir']
        useExistingFiles = ddict['useExistingFiles']
        self.roiFit = ddict['roifit']
        if self.html:
            try:
                if not self.roiFit:
                    if mca == 0:
                        self.__htmlReport(filename, key, outputdir,
                                          useExistingFiles, info, firstmca = True)
                    else:
                        self.__htmlReport(filename, key, outputdir,
                                          useExistingFiles, info, firstmca = False)
            except Exception:
                _logger.warning("ERROR on REPORT %s", sys.exc_info())
                _logger.warning("%s", sys.exc_info()[1])
                _logger.warning("filename = %s key =%s ", (filename, key))
                _logger.warning("If your batch is stopped, please report this")
                _logger.warning("error sending the above mentioned file and the")
                _logger.warning("associated fit configuration file.")
        if QTVERSION < '4.0.0':
            self.mcaBar.setTotalSteps(nmca)
            self.mcaBar.setProgress(mca)
        else:
            self.mcaBar.setMaximum(nmca)
            self.mcaBar.setValue(mca)
        if sys.platform == 'darwin':
            qApp = qt.QApplication.instance()
            qApp.processEvents()

    def __htmlReport(self, filename, key, outputdir, useExistingFiles, info=None, firstmca = True):
        """
        file=self.file
        fileinfo = file.GetSourceInfo()
        nimages = nscans = len(fileinfo['KeyList'])

        filename = os.path.basename(info['SourceName'])
        """
        fitdir = os.path.join(outputdir,"HTML")
        if not os.path.exists(fitdir):
            try:
                os.mkdir(fitdir)
            except Exception:
                _logger.warning("I could not create directory %s", fitdir)
                return
        fitdir = os.path.join(fitdir, filename+"_HTMLDIR")
        if not os.path.exists(fitdir):
            try:
                os.mkdir(fitdir)
            except Exception:
                _logger.warning("I could not create directory %s", fitdir)
                return
        localindex = os.path.join(fitdir, "index.html")
        if not os.path.isdir(fitdir):
            _logger.warning("%s does not seem to be a valid directory", fitdir)
        else:
            outfile = filename + "_" + key + ".html"
            outfile = os.path.join(fitdir,  outfile)
        useExistingResult = useExistingFiles
        if os.path.exists(outfile):
            if not useExistingFiles:
                try:
                    os.remove(outfile)
                except Exception:
                    _logger.warning("cannot delete file %s", outfile)
                useExistingResult = 0
        else:
            useExistingResult = 0
        outdir = fitdir
        fitdir = os.path.join(outputdir,"FIT")
        fitdir = os.path.join(fitdir,filename+"_FITDIR")
        fitfile= os.path.join(fitdir,  filename +"_"+key+".fit")
        if not os.path.exists(fitfile):
            _logger.warning("fit file %s does not exists!", fitfile)
            return
        if self.report is None:
            #first file
            self.forcereport = 0
            self._concentrationsFile = os.path.join(outputdir,
                                self._rootname + "_concentrations.txt")
            if os.path.exists(self._concentrationsFile):
                """
                #code removed, concentrations in McaAdvancedFitBatch.py
                try:
                    os.remove(self._concentrationsFile)
                except Exception:
                    pass
                """
                pass
            else:
                #this is to generate the concentrations file
                #from an already existing set of fitfiles
                self.forcereport = 1
        if self.forcereport or (not useExistingResult):
            self.report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(fitfile = fitfile,
                        outfile = outfile, table = self.table)
            self.__writingReport = True
            a=self.report.writeReport()
            """
            #The code below has been moved to McaAdvancedFitBatch.py
            if len(self.report._concentrationsTextASCII) > 1:
                text  = ""
                text += "SOURCE: "+ filename +"\n"
                text += "KEY: "+key+"\n"
                text += self.report._concentrationsTextASCII + "\n"
                f=open(self._concentrationsFile,"a")
                f.write(text)
                f.close()
            """
            self.__writingReport = False
            #qt.QApplication.postEvent(self, McaCustomEvent.McaCustomEvent({'event':'reportWritten'}))
            self.onReportWritten()

    def onEnd(self,dict):
        self.__ended = True
        if QTVERSION < '4.0.0':
            n = self.progressBar.progress()
            self.progressBar.setProgress(n+dict['filestep'])
            n = self.mcaBar.progress()
            self.mcaBar.setProgress(n+dict['mcastep'])
        else:
            n = self.progressBar.value()
            self.progressBar.setValue(n+dict['filestep'])
            n = self.mcaBar.value()
            self.mcaBar.setValue(n+dict['mcastep'])
        self.status.setText  ("Batch Finished")
        self.timeLeft.setText("Estimated time left = 0 sec")
        if self.actions:
            self.pauseButton.hide()
            self.abortButton.setText("OK")
        if self.chunk is None:
            if 'savedimages' in dict and self._showResult:
                self.plotImages(dict['savedimages'])
        if self.html:
            if not self.__writingReport:
                directory = os.path.join(self.outputdir,"HTML")
                a = HtmlIndex.HtmlIndex(directory)
                a.buildRecursiveIndex()
        if dict['chunk'] is not None:
            if 0:
                #this was giving troubles using HDF5 files as input
                sys.exit(0)
            else:
                #this seems to work properly
                self.close()
        if self.actions:
            if hasattr(self.abortButton, "animateClick"):
                if self.abortButton.text() == "OK":
                    # click for 100 milliseconds
                    _logger.debug("onEnd automatically clicking button")
                    self.abortButton.animateClick()
        if self.exitonend:
            _logger.debug("onEnd close and not quit")
            self.close()
        _logger.debug("onEnd returning")

    def onReportWritten(self):
        if self.__ended:
            directory = os.path.join(self.outputdir,"HTML")
            a = HtmlIndex.HtmlIndex(directory)
            a.buildRecursiveIndex()

    def onPause(self):
        pass

    def onResume(self):
        pass


    def plotImages(self,imagelist):
        if (sys.platform == 'win32') or (sys.platform == 'darwin'):
            self.__viewer = EdfFileSimpleViewer.EdfFileSimpleViewer()
            self.__viewer.setFileList(imagelist)
            self.__viewer.show()
        else:
            filelist = " "
            for ffile in imagelist:
                filelist+=" %s" % ffile
            try:
                dirname = os.path.dirname(__file__)
                frozen = False
            except Exception:
                frozen = True
                dirname = os.path.dirname(EdfFileSimpleViewer.__file__)
            if not frozen:
                if sys.executable in ["PyMcaMain", "PyMcaMain.exe",
                                      "LegacyPyMcaBatch", "LegacyPyMcaBatch.exe"]:
                    frozen = True
            _logger.debug("final dirname = %s", dirname)
            if frozen:
                # we are at level PyMca5\PyMcaGui\pymca
                dirname  = os.path.dirname(dirname)
                # level PyMcaGui
                dirname  = os.path.dirname(dirname)
                # level PyMca5
                dirname  = os.path.dirname(dirname)
                # directory level with exe files
                myself   = os.path.join(dirname, "EdfFileSimpleViewer")
            else:
                myself  = sys.executable+" "+os.path.join(dirname, "EdfFileSimpleViewer.py")
            cmd = "%s %s &" % (myself, filelist)
            _logger.debug("cmd = %s", cmd)
            os.system(cmd)

def main():
    sys.excepthook = qt.exceptionHandler
    import getopt
    from PyMca5.PyMcaCore.LoggingLevel import getLoggingLevel
    options     = 'f'
    longoptions = ['cfg=','outdir=','roifit=','roi=','roiwidth=',
                   'overwrite=', 'filestep=', 'mcastep=', 'html=','htmlindex=',
                   'listfile=','cfglistfile=', 'concentrations=', 'table=', 'fitfiles=',
                   'filebeginoffset=','fileendoffset=','mcaoffset=', 'chunk=',
                   'nativefiledialogs=','selection=', 'exitonend=',
                   'logging=', 'debug=', 'showresult=']
    filelist = None
    outdir   = None
    cfg      = None
    listfile = None
    cfglistfile = None
    selection = False
    roifit   = 0
    roiwidth = ROIWIDTH
    overwrite= 1
    filestep = 1
    html = 0
    htmlindex= None
    mcastep  = 1
    table    = 2
    fitfiles = 1
    concentrations = 0
    filebeginoffset = 0
    fileendoffset = 0
    mcaoffset = 0
    chunk = None
    exitonend = False
    showresult = True
    opts, args = getopt.getopt(
                    sys.argv[1:],
                    options,
                    longoptions)
    for opt,arg in opts:
        if opt in ('--cfg'):
            cfg = arg
        elif opt in ('--outdir'):
            outdir = arg
        elif opt in ('--roi','--roifit'):
            roifit   = int(arg)
        elif opt in ('--roiwidth'):
            roiwidth = float(arg)
        elif opt in ('--overwrite'):
            overwrite= int(arg)
        elif opt in ('--filestep'):
            filestep = int(arg)
        elif opt in ('--mcastep'):
            mcastep  = int(arg)
        elif opt in ('--html'):
            html  = int(arg)
        elif opt in ('--htmlindex'):
            htmlindex  = arg
        elif opt in ('--listfile'):
            listfile  = arg
        elif opt in ('--cfglistfile'):
            cfglistfile  = arg
        elif opt in ('--concentrations'):
            concentrations  = int(arg)
        elif opt in ('--table'):
            table  = int(arg)
        elif opt in ('--fitfiles'):
            fitfiles  = int(arg)
        elif opt in ('--filebeginoffset'):
            filebeginoffset = int(arg)
        elif opt in ('--fileendoffset'):
            fileendoffset   = int(arg)
        elif opt in ('--mcaoffset'):
            mcaoffset  = int(arg)
        elif opt in ('--chunk'):
            chunk  = int(arg)
        elif opt in ('--selection'):
            selection  = int(arg)
            if selection:
                selection = True
            else:
                selection = False
        elif opt in ('--nativefiledialogs'):
            if int(arg):
                PyMcaDirs.nativeFileDialogs = True
            else:
                PyMcaDirs.nativeFileDialogs = False
        elif opt in ('--exitonend'):
            exitonend = int(arg)
        elif opt in ('--showresult'):
            showresult = int(arg)

    logging.basicConfig(level=getLoggingLevel(opts))

    if listfile is None:
        filelist=[]
        for item in args:
            filelist.append(item)
        selection = None
    else:
        if selection:
            tmpDict = ConfigDict.ConfigDict()
            tmpDict.read(listfile)
            tmpDict = tmpDict['PyMcaBatch']
            filelist = tmpDict['filelist']
            if type(filelist) == type(""):
                filelist = [filelist]
            selection = tmpDict['selection']
        else:
            fd = open(listfile, 'rb')
            filelist = fd.readlines()
            fd.close()
            for i in range(len(filelist)):
                filelist[i]=filelist[i].decode(sys.getfilesystemencoding()).replace('\n','')
            selection = None
    if cfglistfile is not None:
        fd = open(cfglistfile, 'rb')
        cfg = fd.readlines()
        fd.close()
        for i in range(len(cfg)):
            cfg[i]=cfg[i].decode(sys.getfilesystemencoding()).replace('\n','')
    app=qt.QApplication(sys.argv)
    winpalette = qt.QPalette(qt.QColor(230,240,249),qt.QColor(238,234,238))
    app.setPalette(winpalette)
    if len(filelist) == 0:
        app.lastWindowClosed.connect(app.quit)
        w = McaBatchGUI(actions=1)
        w.show()
        w.raise_()
        app.exec()
    else:
        app.lastWindowClosed.connect(app.quit)
        text = "LegacyBatch from %s to %s" % (os.path.basename(filelist[0]), os.path.basename(filelist[-1]))
        window =  McaBatchWindow(name=text,actions=1,
                                outputdir=outdir,html=html, htmlindex=htmlindex, table=table,
                                chunk=chunk, exitonend=exitonend, showresult=showresult)

        if html:fitfiles=1
        try:
            b = McaBatch(window,cfg,filelist,outdir,roifit=roifit,roiwidth=roiwidth,
                     overwrite = overwrite, filestep=filestep, mcastep=mcastep,
                      concentrations=concentrations, fitfiles=fitfiles,
                      filebeginoffset=filebeginoffset,fileendoffset=fileendoffset,
                      mcaoffset=mcaoffset, chunk=chunk, selection=selection)
        except Exception:
            if exitonend:
                _logger.warning("Error: ", sys.exc_info()[1])
                _logger.warning("Quitting as requested")
                qt.QApplication.instance().quit()
            else:
                msg = qt.QMessageBox()
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("%s" % sys.exc_info()[1])
                msg.exec()
                return


        def cleanup():
            b.pleasePause = 0
            b.pleaseBreak = 1
            if hasattr(b, "wait"):
                b.wait()
            qApp = qt.QApplication.instance()
            qApp.processEvents()

        def pause():
            if b.pleasePause:
                b.pleasePause=0
                window.pauseButton.setText("Pause")
            else:
                b.pleasePause=1
                window.pauseButton.setText("Continue")
        window.pauseButton.clicked.connect(pause)
        window.abortButton.clicked.connect(window.close)
        app.aboutToQuit[()].connect(cleanup)
        window._rootname = "%s"% b._rootname
        window.show()
        b.start()
        app.exec()
    app = None

if __name__ == "__main__":
    main()


# LegacyPyMcaBatch.py --cfg=/mntdirect/_bliss/users/sole/COTTE/WithLead.cfg --outdir=/tmp/   /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0007.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0008.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0009.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0010.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0011.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0012.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0013.edf &
# LegacyPyMcaBatch.exe --cfg=E:/COTTE/WithLead.cfg --outdir=C:/tmp/   E:/COTTE/ch09/ch09__mca_0003_0000_0007.edf E:/COTTE/ch09/ch09__mca_0003_0000_0008.edf
