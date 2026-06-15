#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2026 European Synchrotron Radiation Facility
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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import os
import time
import subprocess
import signal
import atexit
import logging
import traceback

from glob import glob
try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

from PyMca5.PyMcaGui import PyMcaQt as qt
if sys.platform.startswith("darwin"):
    import threading
    QThread =  threading.Thread
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
from PyMca5.PyMcaPhysics.xrf import McaAdvancedFitBatch
from PyMca5.PyMcaGui.physics.xrf import QtMcaAdvancedFitReport
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.io import ConfigurationFileDialogs
from PyMca5.PyMcaCore import EdfFileLayer
from PyMca5.PyMcaCore import SpecFileLayer
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.pymca import McaCustomEvent
from PyMca5.PyMcaGui.pymca import EdfFileSimpleViewer
from PyMca5.PyMcaCore import HtmlIndex
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaCore import PyMcaBatchBuildOutput
from PyMca5.PyMcaMisc import CliUtils


ROIWIDTH = 100.
_logger = logging.getLogger(__name__)


def moduleRunCmd(modulePath):
    modulePath = os.path.abspath(modulePath)
    if not os.path.exists(modulePath):
        return ''
    sysExecutable = sys.executable
    bootstrap = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'bootstrap.py')
    bootstrap = os.path.abspath(bootstrap)
    if (os.path.isfile(bootstrap)):
        modulePath, ext = os.path.splitext(modulePath)
        parts = [p for p in modulePath.split(os.path.sep) if p][::-1]
        parts = parts[:parts.index('PyMca5')+1][::-1]
        module = '.'.join(parts)
        cmd = '"{}" "{}" -m {}'.format(sysExecutable, bootstrap, module)
    else:
        cmd = '"{}" "{}"'.format(sysExecutable, modulePath)
    _logger.info("Issued command = <%s>" % cmd)
    return cmd


def ranAsBootstrap():
    bootstrap = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'bootstrap.py')
    bootstrap = os.path.abspath(bootstrap)
    return os.path.isfile(bootstrap)


class Option(object):
    """
    Command option wrapper used by `Command`
    which converts to a string "--option=..." 
    """

    def __init__(self, name, value=None, convert=None, format=None):
        self.value = value
        if not format:
            format = "{}"
        if convert is None:
            convert = lambda x: x
        self._name = " --{}".format(name)
        self._format = format
        self._convert = convert

    @property
    def cmdvalue(self):
        if self._convert is None:
            return self.value
        else:
            return self._convert(self.value)

    def __str__(self):
        value = self.cmdvalue
        if value is None:
            return self._name
        else:
            return self._name + "=" + self._format.format(value)


class Command(MutableMapping):
    """
    Class that wraps "cmd --option1=... --option2=..."
    while allowing for adding/removing/modifying options
    and conversion to a string for execution
    """

    def __init__(self, cmd=''):
        self._options = {}
        self.setCommand(cmd)

    def setCommand(self, name, fmt=None):
        if not fmt:
            fmt = "{}"
        self._cmd = name, fmt

    def addOption(self, attr, name=None, **kwargs):
        if not name:
            name = attr
        self._options[attr] = Option(name, **kwargs)

    def removeOption(self, attr):
        self._options.pop(attr)

    def __str__(self):
        name, fmt = self._cmd
        if not name:
            name = "<missing command>"
        cmd = fmt.format(name)
        options = map(str, self._options.values())
        cmd += ''.join(list(options))
        return cmd
    
    def getOptions(self, *attrs):
        return {attr: getattr(self, attr) for attr in attrs}

    def getAllOptionsBut(self, *attrs):
        attrs = [attr for attr in self._options if attr not in attrs]
        return self.getOptions(*attrs)

    def getAllOptions(self):
        attrs = list(self._options.keys())
        return self.getOptions(*attrs)

    def __getattr__(self, attr):
        if attr in self._options:
            return self._options[attr].value
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            super(Command, self).__setattr__(attr, value)
        else:
            if attr in self._options:
                option = self._options[attr]
                option.value = value
            else:
                self.addOption(attr, value=value)

    def __getitem__(self, attr):
        return self._options[attr].value
            
    def __setitem__(self, attr, value):
        self.addOption(attr, value=value)

    def __delitem__(self, key):
        del self._options[key]
        
    def __iter__(self):
        return iter(self._options)

    def __len__(self):
        return len(self._options)


def toolInfo():
    """
    :returns 2-tuple: rootdir(str): directory of executables or GUI launch scripts
                        frozen(bool): run as frozen executable
    """
    if getattr(sys, "frozen", False):
        # frozen
        rootdir = os.path.dirname(sys.executable)
        return rootdir, True
    try:
        rootdir = os.path.dirname(__file__)
        if sys.platform == 'darwin':
            # TODO: is this necessary?
            frozen = '.app' in rootdir
        else:
            frozen = False
        if not os.path.exists(os.path.join(rootdir, "PyMcaBatch.py")):
            # script usage case
            rootdir = os.path.dirname(EdfFileSimpleViewer.__file__)
    except Exception:
        # __file__ is not defined
        frozen = True
        rootdir = os.path.dirname(EdfFileSimpleViewer.__file__)
    if not frozen:
        lst = ["PyMcaMain.exe", "PyMcaBatch.exe"]
        if sys.platform != 'win32':
            lst += ["PyMcaMain", "PyMcaBatch"]
        if os.path.basename(sys.executable) in lst:
            frozen = True
            rootdir = os.path.dirname(EdfFileSimpleViewer.__file__)
    if frozen:
        # we are at level PyMca5\PyMcaGui\pymca
        rootdir = os.path.dirname(rootdir)
        # level PyMcaGui
        rootdir = os.path.dirname(rootdir)
        # level PyMca5
        rootdir = os.path.dirname(rootdir)
        # rootdir is the directory level with executables
        # the above is not true with cx_Freeze because there is an additional
        # /lib directory
    return rootdir, frozen


def toolPath(toolname):
    """
    :params str toolname: e.g. PyMcaBatch
    :returns str: e.g. /users/denolf/.local/bin/pymca
    """
    rootdir, frozen = toolInfo()
    if frozen:
        if sys.platform == 'win32':
            toolname += '.exe'
        tool = os.path.join(rootdir, toolname)
        if os.path.exists(tool):
            tool = '"{}"'.format(tool)
        else:
            tool = ''
    else:
        tool = os.path.join(rootdir, toolname+".py")
        if os.path.exists(tool):
            tool = moduleRunCmd(tool)
        else:
            tool = ''
    return tool


def noProcesses():
    _, forzen = toolInfo()
    forzenDarwin = sys.platform == 'not_any_longer_needed_with_py_installer_on_darwin' and forzen
    return forzenDarwin


def launchThread(thread, window):
    """Launch thread with control window
    """
    def cleanup():
        window.close()
        thread.pleasePause = 0
        thread.pleaseBreak = 1
        if hasattr(thread, "quit"):
            thread.quit()
            thread.wait()
        app = qt.QApplication.instance()
        app.processEvents()
    def pause():
        if thread.pleasePause:
            thread.pleasePause=0
            window.pauseButton.setText("Pause")
        else:
            thread.pleasePause=1
            window.pauseButton.setText("Continue")
    window.pauseButton.clicked.connect(pause)
    window.abortButton.clicked.connect(cleanup)
    qt.QApplication.instance().aboutToQuit[()].connect(cleanup)
    window.show()
    thread.start()


def addToSignal(onSignal, signalNumber):
    """
    Add function to signal `signalNumber` handler

    :param callable onSignal: signature `(int, int)`
    :param int signalNumber:
    """
    oldfunc = signal.getsignal(signalNumber)
    def newfunc(_signalNumber, frame):
        onSignal(_signalNumber, frame)
        if oldfunc:
            oldfunc(_signalNumber, frame)
    try:
        signal.signal(signalNumber, newfunc)
    except RuntimeError:
        pass


def addToSignals(onSignal, signals=None, onexit=True):
    """
    Add function to signal handlers

    :param callable onSignal: signature `(int, int)`
    :param list(int) signals: all signals by default
    :param bool onexit: execute on python exit
    """
    for signalName in dir(signal):
        if not signalName.startswith('SIG'):
            continue
        signalNumber = getattr(signal, signalName, None)
        if signals:
            if signalNumber not in signals:
                continue
        try:
            signal.getsignal(signalNumber)
        except (ValueError, TypeError):
            pass
        else:
            addToSignal(onSignal, signalNumber)
    if onexit:
        atexit.register(onSignal, signal.SIGTERM, 0)


def launchProcess(cmd, blocking=False, independent=False):
    """
    Run `cmd` in one process

    :param Command or str cmd:
    :param bool blocking: wait for finish or not
    :param bool independent: implies non-blocking
    :returns: process handle when `not blocking and not independent`
              None when `blocking or independent`
    """
    cmd = str(cmd)
    # Old way of launching an independent process:
    #if sys.platform == 'win32':
    #    os.system("START /B {}".format(cmd))
    #else:
    #    os.system("{} &".format(cmd))

    # Launch arguments:
    kwargs = {}
    kwargs['cwd'] = os.getcwd()
    kwargs['env'] = {k:str(v) for k,v in os.environ.items()}
    kwargs['close_fds'] = True
    kwargs['shell'] = True

    def afterLaunch(proc):
        return proc
    if blocking:
        _logger.info("BLOCKING PROCESS = %s", cmd)
        def afterLaunch(proc):
            """Wait for process to finish
            """
            proc.wait()
            return proc
    elif independent:
        _logger.info("INDEPENDENT PROCESS = %s", cmd)
        # REMARK: Not needed when shell=True
        #if sys.platform == 'win32':
        #    kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE
    else:
        _logger.info("DEPENDENT PROCESS = %s", cmd)
        # TODO: make child process dependent on parent
        #       by forwarding interrupts and termination
        #def afterLaunch(proc):
        #    """Make dependent
        #    """
        #    def passSignal(signalNumber, frame):
        #        os.kill(proc.pid, signalNumber)
        #    addToSignals(passSignal)
        #    return proc

    # Launch with encoding error handling:
    encodings = None, sys.getfilesystemencoding(), 'utf-8', 'latin-1'
    for encoding in encodings:
        try:
            if encoding:
                lcmd = cmd.encode(encoding)
            else:
                lcmd = cmd
            return afterLaunch(subprocess.Popen(lcmd, **kwargs))
        except UnicodeEncodeError:
            if encoding == encodings[-1]:
                raise


def subCommands(cmd, nFiles, nBatches, func, chunks=True):
    """
    Each batch handles a slice of the 2D XRF map.
    Two slicing strategies are supported:

    ..code: python

        if chunks:
            for mcaoffset in range(nBatchesPerFile):
                for filebeginoffset, fileendoffset in ...:
                    image[filebeginoffset:fileendoffset:1, mcaoffset:None:nBatchesPerFile] 
        else:
            for mcaoffset in range(nBatchesPerFile):
                for filebeginoffset in range(nChunks):
                    image[filebeginoffset:None:nFilesPerChunk, mcaoffset:None:nBatchesPerFile] 
    
    :param Command cmd:
    :param num nFiles: number of files to be process
    :param num nBatches: number sub processes
    :param callable func: signature `(Command)`
    :param chunks: 
    """
    cmd.addOption('filebeginoffset', value=0)
    cmd.addOption('fileendoffset', value=0)
    cmd.addOption('filestep', value=1)
    cmd.addOption('mcaoffset', value=0)
    cmd.addOption('mcastep', value=1)
    cmd.addOption('chunk', value=0)

    nFilesPerChunk = min((nFiles + nBatches - 1)//nBatches, nFiles)
    nChunks = (nFiles + nFilesPerChunk - 1)//nFilesPerChunk
    nBatchesPerFile = max(nBatches//nChunks, 1)
    if chunks:
        cmd.mcastep = nBatchesPerFile
        cmd.filestep = 1
        for i in range(nBatchesPerFile):
            cmd.mcaoffset = i
            for j in range(nChunks):
                filebeginoffset = j * nFilesPerChunk
                fileend = min(filebeginoffset + nFilesPerChunk, nFiles)
                if filebeginoffset >= fileend:
                    break
                cmd.filebeginoffset = filebeginoffset
                cmd.fileendoffset = nFiles - fileend
                cmd.chunk = i*nChunks + j
                func(cmd)
    else:
        cmd.mcastep = nBatchesPerFile
        cmd.filestep = nChunks
        cmd.fileendoffset = 0
        for i in range(nBatchesPerFile):
            cmd.mcaoffset = i
            for j in range(nChunks):
                cmd.filebeginoffset = j
                cmd.chunk = i*nChunks + j
                func(cmd)


class McaBatchGUI(qt.QWidget):
    """
    Main batch fitting widget
    """

    def __init__(self,parent=None,name="PyMca batch fitting",fl=None,
                 filelist=None,config=None,outputdir=None, actions=0,
                 selection=None, showresult=True, **guikwargs):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self._layout = qt.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._edfSimpleViewer = None
        self._showResult = showresult
        self._timer = None
        self._processList = []
        self._selection = None
        self.__build(actions, **guikwargs)
        if filelist is None:
            filelist = []
        self.inputDir = None
        self.inputFilter = None
        self.outputDir = None
        if outputdir is not None:
            if os.path.exists(outputdir):
                self.outputDir = outputdir
            else:
                qt.QMessageBox.information(self, "INFO",
                    "Directory %s does not exist\nUsing %s"% (outputdir, self.outputDir))

        self.configFile = None
        self.fileList = []
        self.setFileList(filelist, selection=selection)
        self.setConfigFile(config)
        self.setOutputDir(self.outputDir)

    def __build(self, actions, roifit=0, roiwidth=ROIWIDTH, overwrite=1,
                concentrations=0, fitfiles=0, diagnostics=0, multipage=0,
                tif=0, edf=1, csv=0, h5=1, dat=1, nproc=1,
                table=2, html=0):
        self.__grid= qt.QWidget(self)
        self._layout.addWidget(self.__grid)
        #self.__grid.setGeometry(qt.QRect(30,30,288,156))
        grid = qt.QGridLayout(self.__grid)
        grid.setContentsMargins(11, 11, 11, 11)
        grid.setSpacing(6)
        #input list
        listrow = 0
        listlabel = qt.QLabel(self.__grid)
        listlabel.setText("Input File list:")
        self.__listView = qt.QTextEdit(self.__grid)
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
        self.__configLine = qt.QLineEdit(self.__grid)
        self.__configLine.setReadOnly(True)
        self.__configButton = qt.QPushButton(self.__grid)
        self.__configButton.setText('Browse')
        self.__configButton.clicked.connect(self.browseConfig)
        grid.addWidget(configlabel,         configrow, 0, qt.Qt.AlignLeft)
        grid.addWidget(self.__configLine,   configrow, 1)
        grid.addWidget(self.__configButton, configrow, 2, qt.Qt.AlignLeft)


        #output dir
        outrow = 2 + row_offset
        outlabel = qt.QLabel(self.__grid)
        outlabel.setText("Output dir:")
        self.__outLine = qt.QLineEdit(self.__grid)
        self.__outLine.setReadOnly(True)
        #self.__outLine.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed))
        self.__outButton = qt.QPushButton(self.__grid)
        self.__outButton.setText('Browse')
        self.__outButton.clicked.connect(self.browseOutputDir)
        grid.addWidget(outlabel,         outrow, 0, qt.Qt.AlignLeft)
        grid.addWidget(self.__outLine,   outrow, 1)
        grid.addWidget(self.__outButton, outrow, 2, qt.Qt.AlignLeft)

        box1 = qt.QWidget(self)
        box1.l = qt.QHBoxLayout(box1)
        box1.l.setContentsMargins(11, 11, 11, 11)
        box1.l.setSpacing(0)
        
        vbox1 = qt.QWidget(box1)
        vbox1.l = qt.QVBoxLayout(vbox1)
        vbox1.l.setContentsMargins(0, 0, 0, 0)
        vbox1.l.setSpacing(0)
        box1.l.addWidget(vbox1)

        vbox2 = qt.QWidget(box1)
        vbox2.l = qt.QVBoxLayout(vbox2)
        vbox2.l.setContentsMargins(0, 0, 0, 0)
        vbox2.l.setSpacing(0)
        box1.l.addWidget(vbox2)

        vbox3 = qt.QWidget(box1)
        vbox3.l = qt.QVBoxLayout(vbox3)
        vbox3.l.setContentsMargins(0, 0, 0, 0)
        vbox3.l.setSpacing(0)
        box1.l.addWidget(vbox3)

        self.__fitBox = qt.QCheckBox(vbox1)
        self.__fitBox.setText('Generate .fit Files')
        palette = self.__fitBox.palette()
        # print("palette set disabled")
        self.__fitBox.setChecked(fitfiles)
        self.__fitBox.setEnabled(True)
        vbox1.l.addWidget(self.__fitBox)

        self.__imgBox = qt.QCheckBox(vbox2)
        self.__imgBox.setText('Generate Peak Images')
        palette = self.__imgBox.palette()
        _logger.debug("palette set disabled")
        self.__imgBox.setChecked(True)
        self.__imgBox.setEnabled(False)
        vbox2.l.addWidget(self.__imgBox)
        """
        self.__specBox = qt.QCheckBox(box1)
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
        self.__htmlBox.setChecked(html)
        self.__htmlBox.setEnabled(True)
        vbox3.l.addWidget(self.__htmlBox)

        #report options
        #reportBox = qt.QHBox(self)
        self.__tableBox = qt.QCheckBox(vbox1)
        self.__tableBox.setText('Table in Report')
        palette = self.__tableBox.palette()
        # print("palette set disabled")
        self.__tableBox.setChecked(bool(table))
        self.__tableBox.setEnabled(False)
        vbox1.l.addWidget(self.__tableBox)

        self.__extendedTable = qt.QCheckBox(vbox2)
        self.__extendedTable.setText('Extended Table')
        self.__extendedTable.setChecked(table>1)
        self.__extendedTable.setEnabled(False)
        vbox2.l.addWidget(self.__extendedTable)

        # overwrite output
        self._overwriteBox = qt.QCheckBox(vbox3)
        self._overwriteBox.setText("Overwrite")
        self._overwriteBox.setChecked(overwrite)
        self._overwriteBox.setEnabled(True)
        vbox3.l.addWidget(self._overwriteBox)

        # concentrations
        self.__concentrationsBox = qt.QCheckBox(vbox3)
        self.__concentrationsBox.setText('Concentrations')
        self.__concentrationsBox.setChecked(concentrations)
        self.__concentrationsBox.setEnabled(True)
        vbox3.l.addWidget(self.__concentrationsBox)

        # diagnostics
        self.__diagnosticsBox = qt.QCheckBox(vbox3)
        self.__diagnosticsBox.setText("Diagnostics")
        self.__diagnosticsBox.setChecked(diagnostics and HDF5SUPPORT)
        self.__diagnosticsBox.setEnabled(HDF5SUPPORT)
        vbox3.l.addWidget(self.__diagnosticsBox)

        # generate hdf5 file
        self._h5Box = qt.QCheckBox(vbox1)
        self._h5Box.setText("HDF5")
        self._h5Box.setChecked(h5 and HDF5SUPPORT)
        self._h5Box.setEnabled(HDF5SUPPORT)
        vbox1.l.addWidget(self._h5Box)

        # generate edf file
        self._edfBox = qt.QCheckBox(vbox2)
        self._edfBox.setText("EDF")
        self._edfBox.setChecked(edf)
        self._edfBox.setEnabled(True)
        vbox2.l.addWidget(self._edfBox)

        # generate csv file
        self._csvBox = qt.QCheckBox(vbox1)
        self._csvBox.setText("CSV")
        self._csvBox.setChecked(csv)
        self._csvBox.setEnabled(True)
        vbox1.l.addWidget(self._csvBox)

        # generate tiff files
        self._tiffBox = qt.QCheckBox(vbox2)
        self._tiffBox.setText("TIFF")
        self._tiffBox.setChecked(tif)
        self._tiffBox.setEnabled(True)
        vbox2.l.addWidget(self._tiffBox)

        # generate dat file
        self._datBox = qt.QCheckBox(vbox1)
        self._datBox.setText("DAT")
        self._datBox.setChecked(dat)
        self._datBox.setEnabled(True)
        vbox1.l.addWidget(self._datBox)

        # multipage edf/tif
        self._multipageBox = qt.QCheckBox(vbox2)
        self._multipageBox.setText("Multipage")
        self._multipageBox.setChecked(multipage)
        self._multipageBox.setEnabled(True)
        vbox2.l.addWidget(self._multipageBox)

        self._edfBox.stateChanged.connect(self.__stateMultiPage)
        self._tiffBox.stateChanged.connect(self.__stateMultiPage)
        self.__stateMultiPage()

        self._layout.addWidget(box1)

        # other stuff
        bigbox = qt.QWidget(self)
        bigbox.l = qt.QHBoxLayout(bigbox)
        bigbox.l.setContentsMargins(0, 0, 0, 0)
        bigbox.l.setSpacing(0)

        vBox = qt.QWidget(bigbox)
        vBox.l = qt.QVBoxLayout(vBox)
        vBox.l.setContentsMargins(0, 0, 0, 0)
        vBox.l.setSpacing(2)
        bigbox.l.addWidget(vBox)

        self.__concentrationsBox.clicked.connect(self.__clickSignal2)
        self.__htmlBox.clicked.connect(self.__clickSignal3)

        boxStep0 = qt.QWidget(bigbox)
        boxStep0.l = qt.QVBoxLayout(boxStep0)
        boxStep = qt.QWidget(boxStep0)
        boxStep.l= qt.QHBoxLayout(boxStep)
        boxStep.l.setContentsMargins(0, 0, 0, 0)
        boxStep.l.setSpacing(0)
        boxStep0.l.addWidget(boxStep)
        bigbox.l.addWidget(boxStep0)


        #box2 = qt.QHBox(self)
        self.__roiBox = qt.QCheckBox(vBox)
        self.__roiBox.setText('ROI Fitting Mode')
        self.__roiBox.setChecked(roifit)
        self.__roiBox.setEnabled(True)
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
        self.__roiSpin.setMinimum(10)
        self.__roiSpin.setMaximum(1000)
        self.__roiSpin.setValue(int(roiwidth))
        box3.l.addWidget(label)
        box3.l.addWidget(self.__roiSpin)

        #BATCH SPLITTING
        self.__splitBox = qt.QCheckBox(vBox)
        self.__splitBox.setText('Use several processes')
        self.__splitBox.setChecked(nproc > 1)
        self.__splitBox.setEnabled(True)
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
        self.__splitSpin.setMinimum(0)
        self.__splitSpin.setMaximum(1000)
        self.__splitSpin.setValue(max(nproc, 0))
        # nproc == 0: run fit in single thread
        # nproc != 0: run fit in one or more processes
        box4.l.addWidget(label)
        box4.l.addWidget(self.__splitSpin)

        self._layout.addWidget(bigbox)
        if actions:
            self.__buildActions()

    def __stateMultiPage(self, state=None):
        self._multipageBox.setEnabled(self._edfBox.isChecked() or self._tiffBox.isChecked())

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
        self.__startButton = qt.QPushButton(box)
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

    def setFileList(self, filelist=None, selection=None):
        self._selection = selection
        if filelist is None:
            filelist = []

        # Check file existence
        if not self.__goodFileList(filelist) and False:
            return

        # Check file types
        text = ""
        oldtype = None
        #do not sort the file list
        #respect user choice
        #filelist.sort()
        for file in filelist:
            filetype = self.__getFileType(file)
            if filetype is None:
                return
            if oldtype is None:
                oldtype = filetype
            if oldtype != filetype:
                qt.QMessageBox.critical(self, "ERROR",
                    "Type %s does not match type %s on\n%s"% (filetype,oldtype,file))
                return
            text += "%s\n" % file

        # HDF5 selection
        if len(filelist):
            if HDF5SUPPORT:
                if h5py.is_hdf5(filelist[0]):
                    if selection is None:
                        selection = self._hdf5Selection(filelist[0])
                    if selection:
                        self._selection = selection
                        self._hdf5Widget.setSelection(selection)
                        #they are not used yet
                        #self._hdf5Widget.selectionWidgetsDict['x'].hide()
                        #self._hdf5Widget.selectionWidgetsDict['m'].hide()
                    if self._hdf5Widget.isHidden():
                        self._hdf5Widget.show()
                else:
                    self._selection = None
                    self._hdf5Widget.hide()
            elif filelist[0][-3:].lower() in ['.h5', 'nxs', 'hdf', 'hdf5']:
                        text = "Warning, this looks as an HDF5 file "
                        text += "but you do not have HDF5 support."
                        self.showMessage(text)
            else:
                self._selection = None
                self._hdf5Widget.hide()

        # Accept new file list
        self.fileList = filelist
        if len(self.fileList):
            self.inputDir = os.path.dirname(self.fileList[0])
            PyMcaDirs.inputDir = os.path.dirname(self.fileList[0])
        self.__listView.clear()
        self.__listView.insertPlainText(text)

    def _hdf5Selection(self, filename):
        selection = {}
        dialog = qt.QDialog(self)
        dialog.setWindowTitle('Select your data set')
        dialog.mainLayout = qt.QVBoxLayout(dialog)
        dialog.mainLayout.setContentsMargins(0, 0, 0, 0)
        dialog.mainLayout.setSpacing(0)
        datasource = NexusDataSource.NexusDataSource(filename)
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
            return selection
        if not len(cntSelection['y']):
            text = "No dataset selected as y"
            self.showMessage(text)
            self.__listView.clear()
            return selection
        entryList = nexusWidget.getSelectedEntries()
        datasource = None
        selection['entry'] = []
        selection['x'] = []
        selection['y'] = []
        selection['m'] = []
        for key in ['x', 'y', 'm']:
            if len(cntSelection[key]):
                for idx in cntSelection[key]:
                    selection[key].append(cntlist[idx])
        for item in entryList:
            selection['entry'].append(item[0])
        return selection

    def showMessage(self, text):
        msg = qt.QMessageBox(self)
        msg.setWindowTitle("PyMcaBatch Message")
        msg.setIcon(qt.QMessageBox.Information)
        msg.setText(text)
        msg.exec()

    def setConfigFile(self,configfile=None):
        if configfile is None:
            return
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
            if not os.path.exists(configfile.split('::')[0]):
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
        if len(self.fileList) == 1:
            if HDF5SUPPORT:
                try:
                    if h5py.is_hdf5(self.fileList[0]):
                        if os.path.dirname(os.path.abspath(self.fileList[0])) == \
                           os.path.abspath(outputdir):
                            msg = "Please specify a different output directory.\n"
                            msg += "Risk of overwritting input file."
                            qt.QMessageBox.critical(self,"ERROR", msg)
                            self.raise_()
                            return False
                except Exception:
                    _logger.warning("Cannot verify suitability of output directory")
        return True

    def __getFileType(self,inputfile):
        try:
            ffile = None
            try:
                ffile = EdfFileLayer.EdfFileLayer(fastedf=0)
                ffile.SetSource(inputfile)
                fileinfo = ffile.GetSourceInfo()
                if fileinfo['KeyList'] == []:ffile=None
                return "EdfFile"
            except Exception:
                pass
            if (ffile is None):
                ffile = SpecFileLayer.SpecFileLayer()
                ffile.SetSource(inputfile)
            del ffile
            return "Specfile"
        except Exception:
            qt.QMessageBox.critical(self,
                                    sys.exc_info()[0],
                                    'I do not know what to do with file\n %s' % inputfile)
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
        filetypes += "McaFiles (*.mca)\nEdfFiles (*.edf)\nCSV (*.csv *.CSV)\n"
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

        if filelist:
            self.setFileList(filelist)
            self.inputFilter = filefilter
        self.raise_()

    def browseConfig(self):
        self.inputDir = PyMcaDirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        fileList = ConfigurationFileDialogs.getFitConfigurationFilePath(self,
                                                currentdir=wdir,
                                                mode="OPEN",
                                                single=True,
                                                currentfilter="Fit configuration files (*.cfg)")

        if fileList:
            self.setConfigFile(fileList[0])
        self.raise_()

    def browseOutputDir(self):
        self.outputDir = PyMcaDirs.outputDir
        if not os.path.exists(self.outputDir):
            self.outputDir =  os.getcwd()
        wdir = self.outputDir
        outdir = PyMcaFileDialogs.getExistingDirectory(self,
                                    message="Output Directory Selection",
                                    mode="SAVE",
                                    currentdir=wdir)
        if outdir:
            self.setOutputDir(outdir)
        self.raise_()

    @property
    def _runAsMultiProcess(self):
        return self._nProcesses > 1

    @property
    def _runAsSingleProcess(self):
        return self._nProcesses == 1

    @property
    def _runAsSingleThread(self):
        return self._nProcesses == 0

    @property
    def _nProcesses(self):
        roifit = self.__roiBox.isChecked()
        if roifit or noProcesses():
            # single thread
            return 0
        n = int(qt.safe_str(self.__splitSpin.text()))
        if not self.__splitBox.isChecked():
            # single thread or single process
            n = min(n, 1)
        return n

    def start(self, blocking=False):
        """
        :param bool blocking: blocking call in case of single process
        """
        if not len(self.fileList):
            qt.QMessageBox.critical(self, "ERROR",'Empty file list')
            self.raise_()
            return

        # Raise exception in case multi processing is not allowed
        # REMARK: not longer needed because
        #       - silently ignore multi processing on frozen MacOS X
        #       - multi processing on single file always allowed
        #if self._runAsMultiProcess:
        #    if sys.platform == 'darwin':
        #        if ".app" in os.path.dirname(__file__):
        #            text = 'Multiple processes only supported on MacOS X when built from source\n'
        #            text += 'and not when running the frozen binary.'
        #            qt.QMessageBox.critical(self, "ERROR",text)
        #            self.raise_()
        #            return
        #    if len(self.fileList) == 1:
        #        if int(qt.safe_str(self.__splitSpin.text())) > 1:
        #            allowSingleFileSplitProcesses = True
        #            if HDF5SUPPORT:
        #                if h5py.is_hdf5(self.fileList[0]):
        #                    _logger.info("Allowing single HDF5 file process split")
        #                    _logger.info("In the past it was problematic")
        #                    allowSingleFileSplitProcesses = True
        #            if not allowSingleFileSplitProcesses:
        #                text = "Multiple processes can only be used with multiple input files."
        #                qt.QMessageBox.critical(self, "ERROR",text)
        #                self.raise_()
        #                return

        # Verify config file
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

        # Verify output
        if (self.outputDir is None) or (not self.__goodOutputDir(self.outputDir)):
            qt.QMessageBox.critical(self, "ERROR",'Invalid output directory')
            self.raise_()
            return

        # Command options
        cmd = Command()
        cmd.addOption('outdir', value=self.outputDir, format='"{}"')
        cmd.addOption('roifit', value=self.__roiBox.isChecked(), format="{:d}")
        cmd.addOption('html', value=self.__htmlBox.isChecked(), format="{:d}")
        cmd.addOption('concentrations', value=self.__concentrationsBox.isChecked(), format="{:d}")
        cmd.addOption('diagnostics', value=self.__diagnosticsBox.isChecked(), format="{:d}")
        cmd.addOption('tif', value=self._tiffBox.isChecked(), format="{:d}")
        cmd.addOption('csv', value=self._csvBox.isChecked(), format="{:d}")
        cmd.addOption('dat', value=self._datBox.isChecked(), format="{:d}")
        cmd.addOption('edf', value=self._edfBox.isChecked(), format="{:d}")
        cmd.addOption('h5', value=self._h5Box.isChecked(), format="{:d}")
        cmd.addOption('overwrite', value=self._overwriteBox.isChecked(), format="{:d}")
        cmd.addOption('multipage', value=self._multipageBox.isChecked(), format="{:d}")

        if self.__tableBox.isChecked():
            if self.__extendedTable.isChecked():
                table = 2
            else:
                table = 1
        else:
            table = 0
        cmd.addOption('table', value=table, format="{:d}")

        #htmlindex = qt.safe_str(self.__htmlIndex.text())
        htmlindex = "index.html"
        if cmd.html:
            if  len(htmlindex)<5:
                htmlindex+=".html"
            if  len(htmlindex) == 5:
                htmlindex = "index.html"
            if htmlindex[-5:] != "html":
                htmlindex+=".html"
        cmd.addOption('htmlindex', value=htmlindex)

        #filestep = int(qt.safe_str(self.__fileSpin.text()))
        #mcastep = int(qt.safe_str(self.__mcaSpin.text()))
        cmd.addOption('filestep', value=1)
        cmd.addOption('mcastep', value=1)
        cmd.addOption('fitfiles', value=self.__fitBox.isChecked(), format="{:d}")
        cmd.addOption('selection', value=self._selection, format="{:d}", convert=bool)

        if cmd.roifit:
            cmd.addOption('roiwidth', value=float(qt.safe_str(self.__roiSpin.text())))
            cmd.table = 0
            cmd.concentrations = 0
            cmd.filestep = 1
            cmd.mcastep = 1

        if self._edfSimpleViewer is not None:
            self._edfSimpleViewer.close()
            self._edfSimpleViewer = None

        # Launch `cmd` in thread or process(es)
        wname = "Batch from %s to %s " % (os.path.basename(self.fileList[ 0]),
                                          os.path.basename(self.fileList[-1]))
        if self._runAsSingleThread:
            self._runInThreadMain(cmd, wname)
        else:
            self._runInProcessMain(cmd, blocking=blocking)

    def _runInThreadMain(self, cmd, wname):
        """
        Run `cmd` in a single thread

        :param Command cmd:
        :param str wname:
        """
        kwargs = cmd.getOptions('outdir', 'html', 'htmlindex', 'table')
        kwargs['outputdir'] = kwargs.pop('outdir')
        window = McaBatchWindow(name=wname, actions=1,
                                showresult=self._showResult,
                                **kwargs)
        kwargs = cmd.getAllOptionsBut('html', 'htmlindex', 'table')
        kwargs['outputdir'] = kwargs.pop('outdir')
        thread = McaBatch(window, self.configFile, filelist=self.fileList, **kwargs)
        window._rootname = "%s"% thread._rootname
        launchThread(thread, window)
        self.__window = window
        self.__thread = thread
    
    def _runInProcessMain(self, cmd, blocking=False):
        """
        Run `cmd` in one of more processes

        :param Command cmd:
        :param bool blocking: blocking call in case of single process
        """
        cmd.addOption('debug', value=_logger.getEffectiveLevel() == logging.DEBUG, format="{:d}")
        cmd.addOption('exitonend', value=1, format="{:d}")
        cmd.addOption('showresult', value=0, format="{:d}")

        # Prepare tools (executables or python scripts) for processing/viewing
        if not self._processToolsInit(cmd):
            return

        # Create file with files to be processed
        listfile = os.path.join(self.outputDir, "tmpfile")
        cmd.addOption("listfile", value=listfile, format='"{}"')
        self.genListFile(listfile, config=False)

        # Create file with config files to be used
        if isinstance(self.configFile, list):
            cfglistfile = os.path.join(self.outputDir, "tmpfile.cfg")
            self.genListFile(cfglistfile, config=True)
            if sys.platform.startswith("win"):
                cmd.addOption("cfglistfile", value='"%s"' % cfglistfile)
            else:
                cmd.addOption("cfglistfile", value=cfglistfile)
        else:
            if sys.platform.startswith("win"):
                cmd.addOption("cfg", value='"%s"' % self.configFile)
            else:
                cmd.addOption("cfg", value=self.configFile)

        # Launch process(es)
        monitored = self._runAsMultiProcess or not blocking
        if monitored:
            # Dependent (monitored) processes
            # REMARK: _pollProcessList will
            #   - show the result
            #   - show the PyMcaBatch window
            cmd.showresult = 0
            self.hide()
            qApp = qt.QApplication.instance()
            qApp.processEvents()
            self._runInProcessMonitored(cmd)
        else:
            # Blocking or independent (unmonitored) process
            # REMARK: currently a non-blocking is always monitored (see above)
            cmd.showresult = self._showResult
            if blocking:
                self.hide()
                qApp = qt.QApplication.instance()
                qApp.processEvents()
            self._runInProcess(cmd, blocking=blocking)
            if blocking:
                self.show()

    def _processToolsInit(self, cmd):
        """
        Initialize tools for processings and inspecting results

        :param Command cmd:
        """
        myself = toolPath('PyMcaBatch')
        if not myself:
            text = 'Cannot locate PyMcaBatch.\n'
            qt.QMessageBox.critical(self, "ERROR",text)
            self.raise_()
            return False
        cmd.setCommand(myself)
        self._datviewer_path = toolPath('PyMcaPostBatch')
        self._edfviewer_path = toolPath('EdfFileSimpleViewer')
        return True

    def _runInProcessMonitored(self, cmd):
        """
        Run `cmd` in one or more processes and start polling for finish

        :param Command cmd:
        """
        processList = []
        nFiles = len(self.fileList)
        nBatches = self._nProcesses
        if nBatches > 1:
            def launch(cmd):
                self._runInProcess(cmd, blocking=False,
                                   processList=processList)
            subCommands(cmd, nFiles, nBatches, launch)
        else:
            self._runInProcess(cmd, blocking=False,
                               processList=processList)
        self._processList = processList
        self._pollProcessList()
        if self._timer is None:
            self._timer = qt.QTimer(self)
            self._timer.timeout[()].connect(self._pollProcessList)
        if not self._timer.isActive():
            self._timer.start(1000)
        else:
            _logger.info("timer was already active")

    def _runInProcess(self, cmd, blocking=False, processList=None):
        """
        Run `cmd` in one process

        :param Command cmd:
        :param bool blocking: wait for finish or not
        :param processList: implies non-blocking when a list
        """
        if processList is not None:
            p = launchProcess(cmd, blocking=False)
            processList.append(p)
        elif blocking:
            launchProcess(cmd, blocking=True)
        else:
            launchProcess(cmd, independent=True)
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            text = "Your fit has been started as an independent process."
            msg.setText(text)
            # REMARK: needs to be non-blocking for unit testing
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
        n = 0
        for process in processList:
            if process.poll() is None:
                n += 1
        if n > 0:
            return
        self._timer.stop()
        self.show()
        self.raise_()
        edfoutlist, datoutlist = self._mergeProcessResults()
        if not edfoutlist and not datoutlist:
            edfoutlist, datoutlist = self._fetchProcessResults()
        if self._showResult:
            try:
                self._showProcessResults(edfoutlist, datoutlist)
            except Exception:
                _logger.error("Failed plotting result (probably interrupted by the user)")

    def _mergeProcessResults(self):
        _logger.info('Merging multi-process results...')
        work = PyMcaBatchBuildOutput.PyMcaBatchBuildOutput(inputdir=self.outputDir)
        delete = _logger.getEffectiveLevel() != logging.DEBUG
        basename = McaAdvancedFitBatch.getRootName(self.fileList)
        edfoutlist, datoutlist, h5outlist = work.buildOutput(basename=basename, delete=delete)
        #inputdir = os.path.join(self.outputDir, basename)
        inputdir = os.path.join(self.outputDir, 'IMAGES')
        edfoutlist2, datoutlist2, h5outlist2 = work.buildOutput(basename=basename, inputdir=inputdir, delete=delete)
        edfoutlist += edfoutlist2
        datoutlist += datoutlist2
        _logger.info('Finished merging multi-process results.')
        return edfoutlist, datoutlist

    def _fetchProcessResults(self):
        basename = McaAdvancedFitBatch.getRootName(self.fileList)
        #inputdir = os.path.join(self.outputDir, basename)
        inputdir = os.path.join(self.outputDir, 'IMAGES')
        edfoutlist = glob(os.path.join(inputdir, basename+'*.edf'))
        datoutlist = glob(os.path.join(inputdir, basename+'*.dat'))
        return edfoutlist, datoutlist

    def _showProcessResults(self, edfoutlist, datoutlist):
        # Load in EDF viewer (this process)
        #if edfoutlist:
        #    if self._edfSimpleViewer is None:
        #        self._edfSimpleViewer = EdfFileSimpleViewer.EdfFileSimpleViewer()
        #    # REMARK: this call takes a long time to finish and blocks everything:
        #    self._edfSimpleViewer.setFileList(edfoutlist)
        #    self._edfSimpleViewer.show()

        # Load in EDF viewer (independent process)
        if edfoutlist and self._edfviewer_path:
            edfoutlist = ' '.join('"%s"' % filename for filename in edfoutlist)
            cmd = '%s %s' % (self._edfviewer_path, edfoutlist)
            launchProcess(cmd, independent=True)

        # Load in RGB correlator (independent process)
        if datoutlist and self._datviewer_path:
            cmd = '%s "%s"' % (self._datviewer_path, datoutlist[0])
            launchProcess(cmd, independent=True)

class McaBatch(McaAdvancedFitBatch.McaAdvancedFitBatch, QThread):
    """
    Batch fitting thread
    """

    def __init__(self, parent, configfile, **kwargs):
        McaAdvancedFitBatch.McaAdvancedFitBatch.__init__(self, configfile, **kwargs)
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
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        if self.pleasePause:
            self.__pauseMethod()

    def onImage(self, key, keylist):
        ddict = {'key':key, 'keylist':keylist, 'event':'onImage'}
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))

    def onMca(self, imca, nmca, filename=None, key=None, info=None):
        _logger.debug("onMca key = %s", key)
        ddict = {'mca':imca,
                 'nmca':nmca,
                 'mcastep':self.mcaStep,
                 'filename':filename,
                 'key':key,
                 'info':info,
                 'outputdir':self.outputdir,
                 'useExistingFiles':self.useExistingFiles,
                 'roifit':self.roiFit,
                 'event':'onMca'}
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        if self.pleasePause:
            self.__pauseMethod()

    def onEnd(self):
        _logger.debug("onEnd")
        savedimages = []
        if self.outbuffer is not None:
            savedimages = self.outbuffer.filenames('.edf')
            savedimages = [fname for fname in savedimages if os.path.isfile(fname)]
        ddict = {'event':'onEnd',
                 'filestep':self.fileStep,
                 'mcastep':self.mcaStep,
                 'chunk':self.chunk,
                 'savedimages':savedimages}
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent(ddict))
        if self.pleasePause:
            self.__pauseMethod()

    def __pauseMethod(self):
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchPaused'}))
        while(self.pleasePause):
            time.sleep(1)
        qt.QApplication.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchResumed'}))


class McaBatchWindow(qt.QWidget):
    """
    Widget to control batch fitting threads
    """

    def __init__(self,parent=None, name="BatchWindow", fl=0, actions = 0, outputdir=None, html=0,
                    htmlindex = None, table=2, chunk=None, exitonend=False, showresult=True):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.chunk = chunk
        self.exitonend = exitonend
        self._showResult = showresult
        self.l = qt.QVBoxLayout(self)
        #self.l.setAutoAdd(1)
        self.bars =qt.QWidget(self)
        self.l.addWidget(self.bars)
        self.barsLayout = qt.QGridLayout(self.bars)
        self.barsLayout.setContentsMargins(2, 2, 2, 2)
        self.barsLayout.setSpacing(3)
        self.progressBar = qt.QProgressBar(self.bars)
        self.progressLabel = qt.QLabel(self.bars)
        self.progressLabel.setText('File Progress:')
        self.imageBar = qt.QProgressBar(self.bars)
        self.imageLabel = qt.QLabel(self.bars)
        self.imageLabel.setText('Image in File:')
        self.mcaBar = qt.QProgressBar(self.bars)
        self.mcaLabel = qt.QLabel(self.bars)
        self.mcaLabel.setText('MCA in Image:')

        self.barsLayout.addWidget(self.progressLabel,0,0)
        self.barsLayout.addWidget(self.progressBar,0,1)
        self.barsLayout.addWidget(self.imageLabel,1,0)
        self.barsLayout.addWidget(self.imageBar,1,1)
        self.barsLayout.addWidget(self.mcaLabel,2,0)
        self.barsLayout.addWidget(self.mcaBar,2,1)
        self.status = qt.QLabel(self)
        self.status.setText(" ")
        self.timeLeft = qt.QLabel(self)
        self.l.addWidget(self.status)
        self.l.addWidget(self.timeLeft)

        self.timeLeft.setText("Estimated time left = ???? min")
        self.time0 = None
        self.html = html
        if htmlindex is None:htmlindex="index.html"
        self.htmlindex = htmlindex
        self.outputdir = outputdir
        self.table = table
        self.__ended = False
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
        self.abortButton = qt.QPushButton(self.buttonsBox)
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
        indexlist = list(range(filebeginoffset, len(filelist)-fileendoffset, filestep))
        index = indexlist.index(filelist.index(file))
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
        nfiles = len(indexlist)
        self.status.setText("Processing file %s" % file)
        e = time.time()
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
        self.imageBar.setMaximum(n)
        self.imageBar.setValue(i)
        self.mcaBar.setMaximum(1)
        self.mcaBar.setValue(0)

    #def onMca(self, mca, nmca, mcastep):
    def onMca(self, ddict):
        _logger.debug("onMca %s", ddict['mca'])
        mca = ddict['mca']
        nmca = ddict['nmca']
        mcastep = ddict['mcastep']
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
                try:
                    _logger.warning("%s", ''.join(traceback.format_tb(sys.exc_info()[2])))
                except Exception:
                    pass
                _logger.warning("filename = %s key =%s " , filename, key)
                _logger.warning("If your batch is stopped, please report this")
                _logger.warning("error sending the above mentioned file and the")
                _logger.warning("associated fit configuration file.")
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
                os.makedirs(fitdir)
            except Exception:
                _logger.warning("I could not create directory %s", fitdir)
                return
        fitdir = os.path.join(fitdir, filename+"_HTMLDIR")
        if not os.path.exists(fitdir):
            try:
                os.makedirs(fitdir)
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
                text = ""
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

    def onEnd(self, dict):
        _logger.debug("Batch finished")
        self.__ended = True
        n = self.progressBar.value()
        self.progressBar.setValue(n + dict['filestep'])
        n = self.mcaBar.value()
        self.mcaBar.setValue(n + dict['mcastep'])
        self.status.setText  ("Batch Finished")
        self.timeLeft.setText("Estimated time left = 0 sec")
        if self.actions:
            self.pauseButton.hide()
            self.abortButton.setText("OK")
        if self.chunk is None:
            savedimages = dict.get('savedimages', None)
            if savedimages and self._showResult:
                self.plotImages(savedimages)
        if self.html:
            if not self.__writingReport:
                directory = os.path.join(self.outputdir,"HTML")
                a = HtmlIndex.HtmlIndex(directory)
                a.buildRecursiveIndex()
        if dict['chunk'] is not None:
            #this seems to work properly
            _logger.debug("onEnd Closing after processing a chunk")
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
        if noProcesses():
            if self.exitonend:
                # Do not start because we exit anyway
                return
            self.__viewer = EdfFileSimpleViewer.EdfFileSimpleViewer()
            # REMARK: this call takes a long time to finish:
            self.__viewer.setFileList(imagelist)
            self.__viewer.show()
        else:
            edfviewer_path = toolPath('EdfFileSimpleViewer')
            if edfviewer_path:
                filelist = ' '.join('"%s"' % filename for filename in imagelist)
                cmd = '%s %s' % (edfviewer_path, filelist)
                launchProcess(cmd, independent=True)


def main(args):
    if args.cli_test and not args.listfile:
        print("No input files provided.")
        return 0

    # Prepare file list
    if args.listfile is None:
        filelist = args.files or []
        selection = None
    else:
        if args.selection:
            tmpDict = ConfigDict.ConfigDict()
            tmpDict.read(args.listfile)
            tmpDict = tmpDict['PyMcaBatch']
            filelist = tmpDict['filelist']
            if isinstance(filelist, str):
                filelist = [filelist]
            selection = tmpDict['selection']
        else:
            with open(args.listfile, 'rb') as fd:
                filelist = [line.decode(sys.getfilesystemencoding()).strip() for line in fd.readlines()]
            selection = None

    # Prepare configurations
    cfg = args.cfg
    if args.cfglistfile is not None:
        with open(args.cfglistfile, 'rb') as fd:
            cfg = [line.decode(sys.getfilesystemencoding()).strip() for line in fd.readlines()]

    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    if args.html:
        fitfiles = 1
    else:
        fitfiles = args.fitfiles

    if not filelist or args.gui:
        # Launch GUI
        w = McaBatchGUI(
            actions=1,
            filelist=filelist,
            config=cfg,
            outputdir=args.outdir,
            roifit=args.roifit,
            roiwidth=args.roiwidth,
            overwrite=args.overwrite,
            concentrations=args.concentrations,
            fitfiles=fitfiles,
            diagnostics=args.diagnostics,
            multipage=args.multipage,
            tif=args.tif,
            edf=args.edf,
            csv=args.csv,
            h5=args.h5,
            dat=args.dat,
            nproc=args.nproc,
            table=args.table,
            html=args.html
        )
        w.show()
        w.raise_()
    else:
        # Launch processing thread
        text = f"Batch from {os.path.basename(filelist[0])} to {os.path.basename(filelist[-1])}"
        window = McaBatchWindow(
            name=text,
            actions=1,
            outputdir=args.outdir,
            html=args.html,
            htmlindex=args.htmlindex,
            table=args.table,
            chunk=args.chunk,
            exitonend=args.exitonend,
            showresult=args.showresult
        )
        try:
            thread = McaBatch(
                window,
                cfg,
                filelist=filelist,
                outputdir=args.outdir,
                roifit=args.roifit,
                roiwidth=args.roiwidth,
                overwrite=args.overwrite,
                filestep=args.filestep,
                mcastep=args.mcastep,
                concentrations=args.concentrations,
                fitfiles=fitfiles,
                filebeginoffset=args.filebeginoffset,
                fileendoffset=args.fileendoffset,
                mcaoffset=args.mcaoffset,
                chunk=args.chunk,
                selection=selection,
                diagnostics=args.diagnostics,
                multipage=args.multipage,
                tif=args.tif,
                edf=args.edf,
                csv=args.csv,
                h5=args.h5,
                dat=args.dat
            )
        except Exception as ex:
            thread = None
            if args.exitonend:
                _logger.warning("Error: %s", ex)
                _logger.warning("Quitting as requested")
                qt.QApplication.instance().quit()
            else:
                msg = qt.QMessageBox()
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText(str(ex))
                msg.exec()
                return

        if thread is not None:
            window._rootname = f"{thread._rootname}"
            launchThread(thread, window)

    # Auto-close Qt application for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="PyMca Batch Processing GUI", add_qt_options=True)

    parser.add_argument("--cfg", type=str, help="Configuration file")
    parser.add_argument("--cfglistfile", type=str, help="Configuration list file")
    parser.add_argument("--outdir", type=str, help="Output directory")
    parser.add_argument("--listfile", type=str, help="List of input files")
    parser.add_argument("--roifit", "--roi", type=int, default=0)
    parser.add_argument("--roiwidth", type=float, default=ROIWIDTH)
    parser.add_argument("--overwrite", type=int, default=1)
    parser.add_argument("--filestep", type=int, default=1)
    parser.add_argument("--mcastep", type=int, default=1)
    parser.add_argument("--html", type=int, default=0)
    parser.add_argument("--htmlindex", type=str, default=None)
    parser.add_argument("--concentrations", type=int, default=0)
    parser.add_argument("--table", type=int, default=2)
    parser.add_argument("--fitfiles", type=int, default=0)
    parser.add_argument("--filebeginoffset", type=int, default=0)
    parser.add_argument("--fileendoffset", type=int, default=0)
    parser.add_argument("--mcaoffset", type=int, default=0)
    parser.add_argument("--chunk", type=int, default=None)
    parser.add_argument("--selection", type=int, default=0)
    parser.add_argument("--exitonend", type=int, default=0)
    parser.add_argument("--showresult", type=int, default=1)

    # Perhaps this flag was originally intended to be equivalent to --fitfiles=1
    parser.add_argument("-f", action="store_true", help="UNUSED")

    parser.add_argument("--gui", type=int, default=0)
    parser.add_argument("--diagnostics", type=int, default=0)
    parser.add_argument("--tif", type=int, default=0)
    parser.add_argument("--edf", type=int, default=1)
    parser.add_argument("--csv", type=int, default=0)
    parser.add_argument("--h5", type=int, default=1)
    parser.add_argument("--dat", type=int, default=1)
    parser.add_argument("--multipage", type=int, default=0)
    parser.add_argument("--nproc", type=int, default=1)

    parser.add_argument("files", nargs="*", help="Files to process if --listfile is not provided")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)

    # PyMcaBatch.py --cfg=/mntdirect/_bliss/users/sole/COTTE/WithLead.cfg --outdir=/tmp/   /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0007.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0008.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0009.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0010.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0011.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0012.edf /mntdirect/_bliss/users/sole/COTTE/ch09/ch09__mca_0003_0000_0013.edf &
    # PyMcaBatch.exe --cfg=E:/COTTE/WithLead.cfg --outdir=C:/tmp/   E:/COTTE/ch09/ch09__mca_0003_0000_0007.edf E:/COTTE/ch09/ch09__mca_0003_0000_0008.edf
