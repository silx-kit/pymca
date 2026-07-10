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
__author__ = "V. Armando Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import time
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5 import PyMcaDirs as xrfmc_dirs
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.misc import SubprocessLogWidget
from PyMca5.PyMcaPhysics.xrf.XRFMC import XRFMCHelper

QTVERSION = qt.qVersion()

class VerticalSpacer(qt.QWidget):
    def __init__(self, *args):
        qt.QWidget.__init__(self, *args)

        self.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,
                           qt.QSizePolicy.Expanding))

class HorizontalSpacer(qt.QWidget):
    def __init__(self, *args):
        qt.QWidget.__init__(self, *args)

        self.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Expanding,
                           qt.QSizePolicy.Fixed))

class GetFileList(qt.QGroupBox):
    sigFileListUpdated = qt.pyqtSignal(object)

    def __init__(self, parent=None, title='File Input', nfiles=1):
        qt.QGroupBox.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.__maxNFiles = nfiles
        self.fileList = []
        self.setTitle(title)
        self.build()

    def build(self, text=""):
        self._label = qt.QLabel(self)
        self._label.setText(text)
        self.__listView = qt.QTextEdit(self)
        n = int(min(self.__maxNFiles, 10))
        self.__listButton = qt.QPushButton(self)
        self.__listButton.setText('Browse')
        self.__listView.setMaximumHeight(n*self.__listButton.sizeHint().height())
        self.__listButton.clicked.connect(self.__browseList)
        grid = self.mainLayout
        grid.addWidget(self._label, 0, 0, qt.Qt.AlignTop|qt.Qt.AlignLeft)
        grid.addWidget(self.__listView, 0, 1)
        grid.addWidget(self.__listButton, 0, 2, qt.Qt.AlignTop|qt.Qt.AlignRight)

    def __browseList(self, dummy=True):
        return self._browseList()

    def _browseList(self, filetypes=["All Files (*)"]):
        self.inputDir = xrfmc_dirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        filelist = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=filetypes,
                                                message="Open a set of files",
                                                currentdir=wdir,
                                                mode="OPEN",
                                                getfilter=False,
                                                single=False,
                                                currentfilter=None,
                                                native=False)
        if not len(filelist):
            return
        if self.__maxNFiles == 1:
            filelist = [filelist[0]]
        self.setFileList(filelist)

    def setFileList(self,filelist=None):
        if filelist is None:
            filelist = []
        text = ""
        self.fileList = filelist

        if len(self.fileList):
            self.fileList.sort()
            for i in range(len(self.fileList)):
                ffile = self.fileList[i]
                if i == 0:
                    text += "%s" % ffile
                else:
                    text += "\n%s" % ffile
            if len(self.fileList):
                self.inputDir = os.path.dirname(qt.safe_str(self.fileList[0]))
                xrfmc_dirs.inputDir = os.path.dirname(qt.safe_str(self.fileList[0]))
        self.__listView.clear()
        self.__listView.insertPlainText(text)
        ddict = {}
        ddict['event'] = 'fileListUpdated'
        ddict['filelist'] = self.fileList * 1
        self.sigFileListUpdated.emit(ddict)

    def getFileList(self):
        if not len(self.fileList):
            return []
        return self.fileList * 1

class PyMcaFitFileList(GetFileList):
    def __init__(self, parent=None):
        GetFileList.__init__(self, parent, title='PyMca Configuration or Fit Result File')
        self.build("")

    def _browseList(self, filetypes=["PyMca .cfg Files (*.cfg)", "PyMca .fit Files (*.fit)"]):
        GetFileList._browseList(self, filetypes)

class XRFMCProgramFile(GetFileList):
    def __init__(self, parent=None):
        GetFileList.__init__(self, parent, title='XMIMSIM-PyMca Program Location')
        self.build("")
        if XRFMCHelper.XMIMSIM_PYMCA is not None:
            self.setFileList([XRFMCHelper.XMIMSIM_PYMCA])

    def _browseList(self, filetypes=["All Files (*)"]):
        self.inputDir = xrfmc_dirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        if sys.platform == "darwin":
            message = "Select XMI-MSIM application bundle"
            filelist = PyMcaFileDialogs.getExistingDirectory(parent=self,
                                                             message=message,
                                                             mode="OPEN",
                                                             currentdir=wdir)
            if len(filelist):
                xmimsim = os.path.join(filelist,
                                       "Contents",
                                       "Resources",
                                       "xmimsim-pymca")
                filelist = [xmimsim]
            print(" FILELIST = ", filelist)
        else:
            message = "Select xmimsim-pymca executable"
            filelist = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=filetypes,
                                                message=message,
                                                mode="OPEN",
                                                currentdir=wdir)
        if len(filelist):
            self.setFileList(filelist)

    def setFileList(self, fileList):
        oldInputDir = xrfmc_dirs.inputDir
        oldOutputDir = xrfmc_dirs.outputDir
        if os.path.exists(fileList[0]):
            GetFileList.setFileList(self, fileList)
        if oldInputDir is not None:
            if os.path.exists(oldInputDir):
                xrfmc_dirs.inputDir = oldInputDir
        if oldOutputDir is not None:
            if os.path.exists(oldOutputDir):
                xrfmc_dirs.outputDir = oldOutputDir

class XRFMCIniFile(GetFileList):
    def __init__(self, parent=None):
        GetFileList.__init__(self, parent, title='XMIMSIM-PyMca Configuration File')
        self.build("")

    def _browseList(self, filetypes  = "XMIMSIM-PyMca .ini File (*.ini)\nXMIMSIM-PyMca .fit File (*.fit)"):
        GetFileList._browseList(self, filetypes)

class XRFMCOutputDir(GetFileList):
    def __init__(self, parent=None):
        GetFileList.__init__(self, parent, title='XMIMSIM-PyMca Output Directory')
        self.build("")

    def _browseList(self, filetypes=["All Files (*)"]):
        self.outputDir = xrfmc_dirs.outputDir
        if not os.path.exists(self.outputDir):
            self.outputDir =  os.getcwd()
        wdir = self.outputDir
        message = "Please select the output directory"
        filelist = PyMcaFileDialogs.getExistingDirectory(parent=self,
                                                         message=message,
                                                         mode="SAVE",
                                                         currentdir=wdir)
        if len(filelist):
            filelist = [str(filelist)]
            self.setFileList(filelist)


class XRFMCParameters(qt.QGroupBox):
    def __init__(self, parent=None, title='XMIMSIM-PyMca Configuration'):
        qt.QGroupBox.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.setTitle(title)
        # I should read a default configuration file
        # for the time being I define it here
        self.__configuration = {}
        self.__configuration['xrfmc'] ={}
        self.__configuration['xrfmc']['setup'] = {}
        current = self.__configuration['xrfmc']['setup']
        current['p_polarisation'] = 0.995
        current['source_sample_distance'] = 100.0
        current['slit_distance'] = 100.0
        current['slit_width_x']  = 0.005
        current['slit_width_y']  = 0.005
        current['source_size_x']  = 0.0005
        current['source_size_y']  = 0.0001
        current['source_diverg_x']  = 0.0001
        current['source_diverg_y']  = 0.0001
        current['nmax_interaction'] = 4
        current['layer'] = 1
        # these are assumed by the Monte Carlo code
        current['collimator_height']  = 0.0
        current['collimator_diameter']  = 0.0
        self.build()
        self.__update()

    def build(self):
        self.__text = ["Photon beam polarisation degree:",
                "Source horizontal size FWHM (cm):",
                "Source vertical   size FWHM (cm):",
                "Source horizontal divergence (rad):",
                "Source vertical   divergence (rad):",
                "Distance beam source to slits  (cm):",
                "Distance beam source to sample (cm):",
                "Slit width  (cm):",
                "Slit height (cm):",
                # "Detector acceptance angle (rad):",
                "Maximum number of sample interactions: ",
                "Sample layer to be adjusted:"]
        i = 0
        for t in self.__text:
            label = qt.QLabel(self)
            label.setText(t)
            self.mainLayout.addWidget(label, i, 0)
            i += 1

        self.__widgetList = []

        #polarisation
        i = 0
        self.polarisationSB = qt.QDoubleSpinBox(self)
        self.polarisationSB.setRange(0.0, 1.0)
        self.polarisationSB.setDecimals(5)
        self.__widgetList.append(self.polarisationSB)
        self.mainLayout.addWidget(self.polarisationSB, i, 1)
        i += 1

        #source horizontal size
        self.sourceHSize = qt.QDoubleSpinBox(self)
        self.sourceHSize.setRange(0.0, 1.0)
        self.sourceHSize.setDecimals(5)
        self.__widgetList.append(self.sourceHSize)
        self.mainLayout.addWidget(self.sourceHSize, i, 1)
        i += 1

        #source vertical size
        self.sourceVSize = qt.QDoubleSpinBox(self)
        self.sourceVSize.setRange(0.0, 1.0)
        self.sourceVSize.setDecimals(5)
        self.__widgetList.append(self.sourceVSize)
        self.mainLayout.addWidget(self.sourceVSize, i, 1)
        i += 1

        # Source horizontal divergence
        self.sourceHDivergence = qt.QDoubleSpinBox(self)
        self.sourceHDivergence.setDecimals(5)
        self.sourceHDivergence.setRange(0.0, 3.1415926)
        self.__widgetList.append(self.sourceHDivergence)
        self.mainLayout.addWidget(self.sourceHDivergence, i, 1)
        i += 1

        # Source vertical divergence
        self.sourceVDivergence = qt.QDoubleSpinBox(self)
        self.sourceVDivergence.setDecimals(5)
        self.sourceVDivergence.setRange(0.0, 3.14159)
        self.__widgetList.append(self.sourceVDivergence)
        self.mainLayout.addWidget(self.sourceVDivergence, i, 1)
        i += 1

        # Distance source sample
        self.sourceSampleDistance = qt.QDoubleSpinBox(self)
        self.sourceSampleDistance.setDecimals(5)
        self.sourceSampleDistance.setRange(0.0001, 100000.0)
        self.__widgetList.append(self.sourceSampleDistance)
        self.mainLayout.addWidget(self.sourceSampleDistance, i, 1)
        i += 1

        # Distance source slits
        self.sourceSlitsDistance = qt.QDoubleSpinBox(self)
        self.sourceSlitsDistance.setDecimals(5)
        self.sourceSlitsDistance.setRange(0.0001, 100000.0)
        self.__widgetList.append(self.sourceSlitsDistance)
        self.mainLayout.addWidget(self.sourceSlitsDistance, i, 1)
        i += 1

        # Slit H size
        self.slitsHWidth = qt.QDoubleSpinBox(self)
        self.slitsHWidth.setDecimals(5)
        self.slitsHWidth.setRange(0.0001, 100.0)
        self.__widgetList.append(self.slitsHWidth)
        self.mainLayout.addWidget(self.slitsHWidth, i, 1)
        i += 1

        # Slit V size
        self.slitsVWidth = qt.QDoubleSpinBox(self)
        self.slitsVWidth.setDecimals(5)
        self.slitsVWidth.setRange(0.0001, 100.0)
        self.__widgetList.append(self.slitsVWidth)
        self.mainLayout.addWidget(self.slitsVWidth, i, 1)
        i += 1

        # Maximum number of interactions
        self.maxInteractions = qt.QSpinBox(self)
        self.maxInteractions.setMinimum(1)
        self.__widgetList.append(self.maxInteractions)
        self.mainLayout.addWidget(self.maxInteractions, i, 1)
        i += 1

        # Layer to be adjusted
        self.fitLayer = qt.QSpinBox(self)
        self.fitLayer.setMinimum(0)
        self.fitLayer.setValue(0)
        self.__widgetList.append(self.fitLayer)
        self.mainLayout.addWidget(self.fitLayer, i, 1)
        i += 1

    def setParameters(self, ddict0):
        if 'xrfmc' in ddict0:
            ddict = ddict0['xrfmc']['setup']
        else:
            ddict= ddict0
        current = self.__configuration['xrfmc']['setup']

        keyList = current.keys()
        for key in keyList:
            value = ddict.get(key, current[key])
            current[key] = value
        self.__update()
        return

    def __update(self):
        current = self.__configuration['xrfmc']['setup']
        key = 'p_polarisation'
        self.polarisationSB.setValue(current[key])
        key = 'source_diverg_x'
        self.sourceHDivergence.setValue(current[key])
        key = 'source_diverg_y'
        self.sourceVDivergence.setValue(current[key])
        key = 'source_sample_distance'
        self.sourceSampleDistance.setValue(current[key])
        key = 'slit_distance'
        self.sourceSlitsDistance.setValue(current[key])
        key = 'slit_width_x'
        self.slitsHWidth.setValue(current[key])
        key = 'slit_width_y'
        self.slitsVWidth.setValue(current[key])
        key = 'source_size_x'
        self.sourceHSize.setValue(current[key])
        key = 'source_size_y'
        self.sourceVSize.setValue(current[key])
        key = 'nmax_interaction'
        self.maxInteractions.setValue(current[key])
        key = 'layer'
        self.fitLayer.setValue(current[key] - 1)

    def getParameters(self):
        current = self.__configuration['xrfmc']['setup']
        key = 'p_polarisation'
        current[key] = self.polarisationSB.value()
        key = 'source_diverg_x'
        current[key] = self.sourceHDivergence.value()
        key = 'source_diverg_y'
        current[key] = self.sourceVDivergence.value()
        key = 'source_sample_distance'
        current[key] = self.sourceSampleDistance.value()
        key = 'slit_distance'
        current[key] = self.sourceSlitsDistance.value()
        key = 'slit_width_x'
        current[key] = self.slitsHWidth.value()
        key = 'slit_width_y'
        current[key] = self.slitsVWidth.value()
        key = 'source_size_x'
        current[key] = self.sourceHSize.value()
        key = 'source_size_y'
        current[key] = self.sourceVSize.value()
        key = 'nmax_interaction'
        current[key] = self.maxInteractions.value()
        key = 'layer'
        current[key] = self.fitLayer.value() + 1
        return self.__configuration

    def getLabelsAndValues(self):
        labels = self.__text
        i = 0
        values = []
        for w in self.__widgetList:
            values.append(w.value())
            i += 1
        return labels, values

class XRFMCSimulationControl(qt.QGroupBox):
    def __init__(self, parent=None, fit=False):
        qt.QGroupBox.__init__(self, parent)
        self.setTitle("Simulation Control")
        self._fit = fit
        self.build()

    def build(self):
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)

        i = 0

        if self._fit:
            label = qt.QLabel(self)
            label.setText("Select simulation or fit mode:")
            self._simulationMode = qt.QComboBox(self)
            self._simulationMode.setEditable(False)
            self._simulationMode.addItem("Simulation")
            self._simulationMode.addItem("Fit")

            self.mainLayout.addWidget(label, i, 0)
            self.mainLayout.addWidget(self._simulationMode, i, 1)
            i += 1

        label = qt.QLabel(self)
        label.setText("Number of histories:")
        self.__nHistories = qt.QSpinBox(self)
        self.__nHistories.setMinimum(1000)
        self.__nHistories.setMaximum(10000000)
        self.__nHistories.setValue(100000)
        self.__nHistories.setSingleStep(50000)

        self.mainLayout.addWidget(label, i, 0)
        self.mainLayout.addWidget(self.__nHistories, i, 1)
        i += 1

    def getParameters(self):
        ddict = {}
        ddict['histories'] = self.__nHistories.value()
        return ddict

    def setParameters(self, ddict0):
        if 'xrfmc' in ddict0:
            ddict = ddict0['xrfmc']['setup']
        else:
            ddict= ddict0

        if 'histories' in ddict:
            self.__nHistories.setValue(int(ddict['histories']))

    def getSimulationMode(self):
        current = self._simulationMode.currentIndex()
        if current:
            mode = "Fit"
        else:
            mode = "Simulation"
        return mode

    def setSimulationMode(self, mode=""):
        current = 0
        if hasattr(mode, "lower"):
            if mode.lower() == "fit":
                current = 1
        self._simulationMode.setCurrentIndex(current)

class XRFMCTabWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("XRFMC Tab Widget")
        self.build()

    def build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        self.programWidget = XRFMCProgramFile(self)
        self.parametersWidget = XRFMCParameters(self)
        self.simulationWidget = XRFMCSimulationControl(self, fit=False)
        self.mainLayout.addWidget(self.programWidget)
        self.mainLayout.addWidget(self.parametersWidget)
        self.mainLayout.addWidget(self.simulationWidget)
        self.mainLayout.addWidget(VerticalSpacer(self))

    def getParameters(self):
        ddict = self.parametersWidget.getParameters()
        program = self.programWidget.getFileList()
        control = self.simulationWidget.getParameters()
        ddict['xrfmc']['setup']['histories'] = control['histories']
        if len(program) > 0:
            ddict['xrfmc']['program'] = program[0]
        else:
            ddict['xrfmc']['program'] = None
        return ddict

    def setParameters(self, ddict):
        self.parametersWidget.setParameters(ddict)
        if ddict['xrfmc']['program'] not in ["None", None, ""]:
            self.programWidget.setFileList([ddict['xrfmc']['program']])
        self.simulationWidget.setParameters(ddict)

class XRFMCActions(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.startButton = qt.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setAutoDefault(False)
        self.dismissButton = qt.QPushButton(self)
        self.dismissButton.setText("Dismiss")
        self.dismissButton.setAutoDefault(False)
        self.mainLayout.addWidget(self.startButton)
        self.mainLayout.addWidget(HorizontalSpacer(self))
        self.mainLayout.addWidget(self.dismissButton)

class XRFMCPyMca(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("XMIMSIM-PyMca")
        self.fitConfiguration  = None
        self.logWidget = None
        #self._loggedProcess = None
        self.build()
        self.buildConnections()

    def build(self):
        self.mainLayout = qt.QGridLayout(self)
        self.programWidget = XRFMCProgramFile(self)
        self.fitFileWidget = PyMcaFitFileList(self)
        #self.iniFileWidget = XRFMCIniFile(self)
        self.outputDirWidget = XRFMCOutputDir(self)
        self.parametersWidget = XRFMCParameters(self)
        self.simulationWidget = XRFMCSimulationControl(self, fit=True)
        self.actions = XRFMCActions(self)
        self.logWidget = SubprocessLogWidget.SubprocessLogWidget()
        self.logWidget.setMinimumWidth(400)

        i = 0
        self.mainLayout.addWidget(self.programWidget, i, 0)
        i += 1
        self.mainLayout.addWidget(self.fitFileWidget, i, 0)
        i += 1
        #self.mainLayout.addWidget(self.iniFileWidget, i, 0)
        #i += 1
        self.mainLayout.addWidget(self.outputDirWidget, i, 0)
        i += 1
        self.mainLayout.addWidget(self.parametersWidget, i, 0)
        i += 1
        self.mainLayout.addWidget(self.simulationWidget, i, 0)
        i += 1
        self.mainLayout.addWidget(self.actions, i, 0)
        i += 1
        self.mainLayout.addWidget(VerticalSpacer(self), i,0)
        i += 1
        self.mainLayout.addWidget(self.logWidget, 0, 1, i, 1)
        i += 1


    def buildConnections(self):
        self.fitFileWidget.sigFileListUpdated.connect(self.fitFileChanged)

        self.actions.startButton.clicked.connect(self.start)
        self.actions.dismissButton.clicked.connect(self.close)
        self.logWidget.sigSubprocessLogWidgetSignal.connect(\
                     self.subprocessSlot)

    def closeEvent(self, event):
        if self._closeDialog():
            event.accept()
        else:
            event.ignore()

    def _closeDialog(self):
        if self.logWidget is None:
            close = True
        elif self.logWidget.isSubprocessRunning():
            msg = qt.QMessageBox(self)
            msg.setWindowTitle("Simulation going on")
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("Do you want to stop on-going simulation?")
            msg.setStandardButtons(qt.QMessageBox.Yes|qt.QMessageBox.No)
            answer=msg.exec()
            if answer == qt.QMessageBox.Yes:
                self.logWidget.stop()
                close = True
            else:
                print("NOT KILLING")
                close = False
        else:
            close = True
        return close

    def errorMessage(self, text, title='ERROR'):
        qt.QMessageBox.critical(self, title,
            text)

    def fitFileChanged(self, ddict):
        #for the time being only one ...
        fitfile= ddict['filelist'][0]
        self.fitConfiguration = ConfigDict.ConfigDict()
        self.fitConfiguration.read(fitfile)
        if 'result' in self.fitConfiguration:
            matrix = self.fitConfiguration['result']\
                     ['config']['attenuators'].get('Matrix', None)
        else:
            matrix = self.fitConfiguration\
                     ['attenuators'].get('Matrix', None)

        if matrix is None:
            text = 'Undefined sample matrix in file %s' % fitfile
            title = "Invalid Matrix"
            self.errorMessage(text, title)
            return
        if matrix[0] != 1:
            text = 'Undefined sample matrix in file %s' % fitfile
            title = "Matrix not considered in fit"
            self.errorMessage(text, title)
            return
        if matrix[1] == '-':
            text = 'Invalid sample Composition "%s"' % matrix[1]
            title = "Invalid Sample"
            self.errorMessage(text, title)
            return

        if 'xrfmc' in self.fitConfiguration:
            if 'setup' in self.fitConfiguration['xrfmc']:
                self.parametersWidget.setParameters(self.fitConfiguration)

        if matrix[1] != "MULTILAYER":
            self.parametersWidget.setParameters({'layer':1})
            self.parametersWidget.fitLayer.setMaximum(0)

    def configurationFileChanged(self, ddict):
        configFile= ddict['filelist'][0]
        configuration = ConfigDict.ConfigDict()
        configuration.read(configFile)
        if not ('setup' in configuration['xrfmc']):
            title = "Invalid file"
            text = "Invalid configuration file."
            self.errorMessage(text, title)
        else:
            self.parametersWidget.setParameters(configuration['xrfmc']['setup'])

    def errorMessage(self, text, title=None):
        msg = qt.QMessageBox(self)
        if title is not None:
            msg.setWindowTitle(title)
        msg.setIcon(qt.QMessageBox.Critical)
        msg.setText(text)
        msg.exec()

    def start(self):
        try:
            self._start()
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Plugin error")
            msg.setText("An error has occured while executing the plugin:")
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _start(self):
        """
        """
        if self.logWidget is not None:
            if self.logWidget.isSubprocessRunning():
                text = "A simulation is already started\n"
                self.errorMessage(text)
                return
        pymcaFitFile = self.fitFileWidget.getFileList()
        if len(pymcaFitFile) < 1:
            text = "PyMca .fit or .cfg file is mandatory\n"
            self.errorMessage(text)
            return
        pymcaFitFile = pymcaFitFile[0]

        program = self.programWidget.getFileList()
        if len(program) < 1:
            text = "Simulation program file is mandatory\n"
            self.errorMessage(text)
            return
        program = program[0]

        #This one would only be needed for backup purposes
        #self.iniFileWidget.getFileList()

        #The output directory
        outputDir = self.outputDirWidget.getFileList()
        if len(outputDir) < 1:
            text = "Output directory is mandatory\n"
            self.errorMessage(text)
            return

        #the actual parameters to be used
        ddict = self.parametersWidget.getParameters()

        #the output directory
        ddict['xrfmc']['setup']['output_dir'] = outputDir[0]
        self.__outputDir = outputDir[0]

        #the simulation parameters
        simPar = self.simulationWidget.getParameters()
        ddict['xrfmc']['setup']['histories'] = simPar['histories']

        #write a file containing both, PyMca and XRFMC configuration in output dir
        if pymcaFitFile.lower().endswith(".cfg"):
            # not a fit result but a configuration file
            # but this does not work
            newFile=ConfigDict.ConfigDict()
            newFile.read(pymcaFitFile)
            __THOUGHTS__ = """
                # perform a dummy fit till xmimsim-pymca is upgraded
                import numpy
                from PyMca import ClassMcaTheory
                newFile['fit']['linearfitflag']=1
                newFile['fit']['stripflag']=0
                newFile['fit']['stripiterations']=0
                xmin = newFile['fit']['xmin']
                xmax = newFile['fit']['xmax']
                #xdata = numpy.arange(xmin, xmax + 1) * 1.0
                xdata = numpy.arange(0, xmax + 1) * 1.0
                ydata = 0.0 + 0.1 * xdata
                mcaFit = ClassMcaTheory.McaTheory()
                mcaFit.configure(newFile)
                mcaFit.setData(x=xdata, y=ydata, xmin=xmin, xmax=xmax)
                mcaFit.estimate()
                fitresult,result = mcaFit.startfit(digest=1)
                newFile = None
                nfile=ConfigDict.ConfigDict()
                nfile['result'] = result
                #nfile.write("tmpFitFileFromConfig.fit")
                """
            nfile = ConfigDict.ConfigDict()
            nfile.read(pymcaFitFile)
            nfile.update(ddict)
            newFile = os.path.join(outputDir[0],\
                                   os.path.basename(pymcaFitFile[:-4] + ".fit"))
        else:
            nfile = ConfigDict.ConfigDict()
            nfile.read(pymcaFitFile)
            nfile.update(ddict)
            newFile = os.path.join(outputDir[0],\
                                   os.path.basename(pymcaFitFile))
        if os.path.exists(newFile):
            os.remove(newFile)
        nfile.write(newFile)
        nfile = None

        fileNamesDict = XRFMCHelper.getOutputFileNames(newFile,
                                                       outputDir=outputDir[0])
        if newFile != fileNamesDict['fit']:
            raise ValueError("Inconsistent internal behaviour!")

        scriptName = fileNamesDict['script']
        scriptFile = XRFMCHelper.getScriptFile(program, name=scriptName)
        csvName = fileNamesDict['csv']
        speName = fileNamesDict['spe']
        xmsoName = fileNamesDict['xmso']

        # basic parameters
        args = [scriptFile,
               #"--enable-single-run",
               "--verbose",
               "--spe-file=%s" % speName,
               "--csv-file=%s" % csvName,
               #"--enable-roi-normalization",
               #"--disable-roi-normalization", #default
               #"--enable-pile-up"
               #"--disable-pile-up" #default
               #"--enable-poisson",
               #"--disable-poisson", #default no noise
               #"--set-threads=2", #overwrite default maximum
               newFile,
               xmsoName]

        self.__fileNamesDict = fileNamesDict

        # additionalParameters
        if self.simulationWidget.getSimulationMode().lower() == "fit":
            simulationParameters = []
        else:
            simulationParameters = ["--enable-single-run",
                                    "--set-threads=2"]
        i = 0
        for parameter in simulationParameters:
            i += 1
            args.insert(1, parameter)

        # show the command on the log widget
        text = "%s" % scriptFile
        for arg in args[1:]:
            text += " %s" % arg
        self.logWidget.clear()
        self.logWidget.append(text)
        self.logWidget.start(args=args)

    def subprocessSlot(self, ddict):
        if ddict['event'] == "ProcessStarted":
            # we do not need a direct handle to the process
            #self._loggedProcess = ddict['subprocess']
            return
        if ddict['event'] == "ProcessFinished":
            returnCode = ddict['code']
            msg = qt.QMessageBox(self)
            msg.setWindowTitle("Simulation finished")
            if returnCode == 0:
                msg.setIcon(qt.QMessageBox.Information)
                text = "Simulation finished, output written to the directory:\n"
                text += "%s" % self.__outputDir
            else:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                text = "Simulation finished with error code %d\n" % (returnCode)
                for line in ddict['message']:
                    text += line
            msg.setText(text)
            msg.exec()
        xmsoName = self.__fileNamesDict['xmso']

if __name__ == "__main__":
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    w = XRFMCPyMca()
    w.show()
    app.exec()

