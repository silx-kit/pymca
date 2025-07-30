#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2025 European Synchrotron Radiation Facility
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
import os
import sys, getopt
import traceback
import logging
if sys.platform == 'win32':
    import ctypes
    from ctypes.wintypes import MAX_PATH

nativeFileDialogs = None
_logger = logging.getLogger(__name__)
backend=None
if __name__ == '__main__':
    options     = '-f'
    longoptions = ['spec=',
                   'shm=',
                   'debug=',
                   'qt=',
                   'backend=',
                   'nativefiledialogs=',
                   'PySide=',
                   'binding=',
                   'logging=']
    try:
        opts, args = getopt.getopt(
                     sys.argv[1:],
                     options,
                     longoptions)
    except getopt.error:
        print("%s" % sys.exc_info()[1])
        sys.exit(1)

    keywords={}
    debugreport = 0
    qtversion = None
    binding = None
    for opt, arg in opts:
        if  opt in ('--spec'):
            keywords['spec'] = arg
        elif opt in ('--shm'):
            keywords['shm']  = arg
        elif opt in ('--debug'):
            if arg.lower() not in ['0', 'false']:
                debugreport = 1
                _logger.setLevel(logging.DEBUG)
            # --debug is also parsed later for the global logging level
        elif opt in ('-f'):
            keywords['fresh'] = 1
        elif opt in ('--qt'):
            qtversion = arg
        elif opt in ('--backend'):
            backend = arg
        elif opt in ('--nativefiledialogs'):
            if int(arg):
                nativeFileDialogs = True
            else:
                nativeFileDialogs = False
        elif opt in ('--PySide'):
            print("Please use --binding=PySide6")
            import PySide6.QtCore
        elif opt in ('--binding'):
            binding = arg.lower()
            if binding == "pyqt5":
                import PyQt5.QtCore
            elif binding == "pyside2":
                import PySide2.QtCore
            elif binding == "pyside6":
                import PySide6.QtCore
            elif binding == "pyqt6":
                import PyQt6.QtCore
            else:
                raise ValueError("Unknown Qt binding <%s>" % binding)

    from PyMca5.PyMcaCore.LoggingLevel import getLoggingLevel
    logging.basicConfig(level=getLoggingLevel(opts))
    # We are going to read. Disable file locking.
    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    _logger.info("%s set to %s" % ("HDF5_USE_FILE_LOCKING",
                                    os.environ["HDF5_USE_FILE_LOCKING"]))
    if binding is None:
        if qtversion == '3':
            raise NotImplementedError("Qt3 is no longer supported")
        elif qtversion == '4':
            raise NotImplementedError("Qt4 is no longer supported")
        elif qtversion == '5':
            try:
                import PyQt5.QtCore
            except ImportError:
                import PySide2.QtCore
        elif qtversion == '6':
            import PySide6.QtCore
    try:
        # make sure hdf5plugins are imported
        import hdf5plugin
    except Exception:
        _logger.info("Failed to import hdf5plugin")

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
QTVERSION = qt.qVersion()

try:
    import silx
    # try to import silx prior to importing matplotlib to prevent
    # unnecessary warning
    import silx.gui.plot
except Exception:
    pass
from PyMca5.PyMcaGui.pymca import PyMcaMdi
IconDict = PyMcaMdi.IconDict
IconDict0 = PyMcaMdi.IconDict0
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str

try:
    from PyMca5.PyMcaGui.physics.xrf import XRFMCPyMca
    XRFMC_FLAG = True
except Exception:
    XRFMC_FLAG = False

try:
    from PyMca5.PyMcaGui.pymca import SumRulesTool
    SUMRULES_FLAG = True
except Exception:
    SUMRULES_FLAG = False

# prefer lazy import to avoid OpenCL related crashes on startup
TOMOGUI_FLAG = True

import PyMca5
from PyMca5 import PyMcaDataDir
__version__ = PyMca5.version()

if __name__ == "__main__":
    sys.excepthook = qt.exceptionHandler

    app = qt.QApplication(sys.argv)
    if sys.platform not in ["win32", "darwin"]:
        # some themes of Ubuntu 16.04 give black tool tips on black background
        app.setStyleSheet("QToolTip { color: #000000; background-color: #fff0cd; border: 1px solid black; }")

    mpath = PyMcaDataDir.PYMCA_DATA_DIR
    if mpath[-3:] == "exe":
        mpath = os.path.dirname(mpath)

    fname = os.path.join(mpath, 'PyMcaSplashImage.png')
    if not os.path.exists(fname):
       while len(mpath) > 3:
         fname = os.path.join(mpath, 'PyMcaSplashImage.png')
         if not os.path.exists(fname):
             mpath = os.path.dirname(mpath)
         else:
             break
    if os.path.exists(fname):
        pixmap = qt.QPixmap(QString(fname))
        splash  = qt.QSplashScreen(pixmap)
    else:
        splash = qt.QSplashScreen()
    splash.show()
    splash.raise_()
    from PyMca5.PyMcaGui.pymca import ChangeLog
    font = splash.font()
    font.setBold(1)
    splash.setFont(font)
    try:
        # there is a deprecation warning in Python 3.8 when
        # dealing with the alignement flags.
        alignment = int(qt.Qt.AlignLeft|qt.Qt.AlignBottom)
        splash.showMessage( 'PyMca %s' % __version__,
                alignment,
                qt.Qt.white)
    except Exception:
        # fall back to original implementation in case of troubles
        splash.showMessage( 'PyMca %s' % __version__,
                qt.Qt.AlignLeft|qt.Qt.AlignBottom,
                qt.Qt.white)
    if sys.platform == "darwin":
        qApp = qt.QApplication.instance()
        qApp.processEvents()

from PyMca5.PyMcaGraph.Plot import Plot
from PyMca5.PyMcaGui.pymca import ScanWindow
from PyMca5.PyMcaGui.pymca import McaWindow

from PyMca5.PyMcaGui.pymca import PyMcaImageWindow
from PyMca5.PyMcaGui.pymca import PyMcaHKLImageWindow

try:
    #This is to make sure it is properly frozen
    #and that Object3D is fully supported
    import OpenGL.GL
    OBJECT3D = False
    if ("PyQt4.QtOpenGL" in sys.modules) or \
       ("PySide.QtOpenGL") in sys.modules or \
       ("PySide6.QtOpenGL") in sys.modules or \
       ("PySide2.QtOpenGL") in sys.modules or \
       ("PyQt5.QtOpenGL") in sys.modules:
        OBJECT3D = True
except Exception:
    _logger.info("pyopengl not installed")
    OBJECT3D = False

# Silx OpenGL availability (former Object3D)
try:
    import PyMca5.PyMcaGui.pymca.SilxGLWindow
    isSilxGLAvailable = True
except ImportError:
    isSilxGLAvailable = False

if isSilxGLAvailable:
    SceneGLWindow = PyMca5.PyMcaGui.pymca.SilxGLWindow
else:
    SceneGLWindow = None

try:
    from PyMca5.PyMcaGui.pymca import SilxScatterWindow
except Exception:
    _logger.info("Cannot import SilxScatterWindow")

# check that OpenGL is actually supported (ESRF rnice problems)
OPENGL_DRIVERS_OK = True
if sys.platform.startswith("linux"):
    import subprocess
    if subprocess.call("which glxinfo > /dev/null", shell=True) == 0:
        if subprocess.call("glxinfo > /dev/null", shell=True):
            OPENGL_DRIVERS_OK = False
            isSilxGLAvailable = False
            OBJECT3D = False
            _logger.warning("OpenGL disabled. Errors using glxinfo command")

    if OPENGL_DRIVERS_OK and isSilxGLAvailable:
        # additional test (takes care of disabled forwarding)
        try:
            from silx.gui.utils.glutils import isOpenGLAvailable
            isSilxGLAvailable = isOpenGLAvailable(version=(2, 1), runtimeCheck=True)
            if not isSilxGLAvailable:
                _logger.info("OpenGL >= 2.1 not available")
                if not isOpenGLAvailable(version=(1, 4), runtimeCheck=True):
                    _logger.info("OpenGL >= 1.4 not available")
                    OPENGL_DRIVERS_OK = False
                    OBJECT3D = False
        except Exception:
            _logger.info("Cannot test OpenGL availability %s" % sys.exc_info()[1])

# PyMca 3D disabled in favor of silx
OBJECT3D = isSilxGLAvailable
_logger.info("SilxGL availability: %s", isSilxGLAvailable)

from PyMca5.PyMcaGui.pymca import QDispatcher
from PyMca5.PyMcaGui.physics.xrf import ElementsInfo
from PyMca5.PyMcaGui.physics.xrf import PeakIdentifier
from PyMca5.PyMcaGui.pymca import PyMcaBatch
###########import Fit2Spec
from PyMca5.PyMcaGui.pymca import Mca2Edf
try:
    from PyMca5.PyMcaGui.pymca import QStackWidget
    from PyMca5.PyMcaGui.pymca import StackSelector
    STACK = True
except Exception:
    STACK = False
from PyMca5.PyMcaGui.pymca import PyMcaPostBatch
from PyMca5.PyMcaGui.pymca import RGBCorrelator
from PyMca5.PyMcaGui.physics.xrf import MaterialEditor

from PyMca5.PyMcaIO import ConfigDict
from PyMca5 import PyMcaDirs

XIA_CORRECT = False
if QTVERSION > '4.3.0':
    try:
        from PyMca5.PyMcaCore import XiaCorrect
        XIA_CORRECT = True
    except Exception:
        pass

SOURCESLIST = QDispatcher.QDataSource.source_types.keys()

class PyMcaMain(PyMcaMdi.PyMcaMdi):
    def __init__(self, parent=None, name="PyMca", fl=None,**kw):
            if fl is None:
                fl = qt.Qt.WA_DeleteOnClose
            PyMcaMdi.PyMcaMdi.__init__(self, parent, name, fl)
            maxheight = qt.QDesktopWidget().height()
            if maxheight < 799 and maxheight > 0:
                self.setMinimumHeight(int(0.8*maxheight))
                self.setMaximumHeight(int(0.9*maxheight))
            self.setWindowTitle(name)
            self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
            self.changeLog = None

            self._widgetDict = {}
            self.initSourceBrowser()
            self.initSource()

            self.elementsInfo= None
            self.attenuationTool =  None
            self.identifier  = None
            self.__batch     = None
            self.__mca2Edf   = None
            self.__fit2Spec  = None
            self.__correlator  = None
            self.__imagingTool = None
            self._xrfmcTool = None
            self._sumRulesTool = None
            self.__reconsWidget = None
            self.openMenu = qt.QMenu()
            self.openMenu.addAction("PyMca Configuration", self.openSource)
            self.openMenu.addAction("Data Source",
                         self.sourceWidget.sourceSelector._openFileSlot)
            self.openMenu.addAction("Load Training Data",
                                        self.loadTrainingData)
            self.trainingDataMenu = None

            self.__useTabWidget = True

            if not self.__useTabWidget:
                self.mcaWindow = McaWindow.McaWidget(self.mdi)
                self.scanWindow = ScanWindow.ScanWindow(self.mdi)
                self.imageWindowDict = None
                self.connectDispatcher(self.mcaWindow, self.sourceWidget)
                self.connectDispatcher(self.scanWindow, self.sourceWidget)
                self.mdi.addWindow(self.mcaWindow)
                self.mdi.addWindow(self.scanWindow)
            else:
                if backend is not None:
                    Plot.defaultBackend = backend
                self.mainTabWidget = qt.QTabWidget(self.mdi)
                self.mainTabWidget.setWindowTitle("Main Window")
                self.mcaWindow = McaWindow.McaWindow(backend=backend)
                self.mcaWindow.showRoiWidget(qt.Qt.BottomDockWidgetArea)

                self.scanWindow = ScanWindow.ScanWindow(info=True,
                                                        backend=backend)
                self.scanWindow._togglePointsSignal()
                if OBJECT3D or isSilxGLAvailable:
                    self.glWindow = SceneGLWindow.SceneGLWindow()
                self.mainTabWidget.addTab(self.mcaWindow, "MCA")
                self.mainTabWidget.addTab(self.scanWindow, "SCAN")
                if OBJECT3D or isSilxGLAvailable:
                    self.mainTabWidget.addTab(self.glWindow, "OpenGL")
                if QTVERSION < '5.0.0':
                    self.mdi.addWindow(self.mainTabWidget)
                else:
                    self.mdi.addSubWindow(self.mainTabWidget)
                #print "Markus patch"
                #self.mainTabWidget.show()
                #print "end Markus patch"
                self.mainTabWidget.showMaximized()
                if False:
                    self.connectDispatcher(self.mcaWindow, self.sourceWidget)
                    self.connectDispatcher(self.scanWindow, self.sourceWidget)
                else:
                    self.imageWindowDict = {}
                    self.imageWindowCorrelator = None
                    self.sourceWidget.sigAddSelection.connect( \
                             self.dispatcherAddSelectionSlot)
                    self.sourceWidget.sigRemoveSelection.connect( \
                             self.dispatcherRemoveSelectionSlot)
                    self.sourceWidget.sigReplaceSelection.connect( \
                             self.dispatcherReplaceSelectionSlot)
                    self.mainTabWidget.currentChanged[int].connect( \
                        self.currentTabIndexChanged)

            self.sourceWidget.sigOtherSignals.connect( \
                         self.dispatcherOtherSignalsSlot)
            if 0:
                if 'shm' in kw:
                    if len(kw['shm']) >= 8:
                        if kw['shm'][0:8] in ['MCA_DATA', 'XIA_DATA']:
                            self.mcaWindow.showMaximized()
                            self.toggleSource()
                else:
                    self.mcaWindow.showMaximized()
            currentConfigDict = ConfigDict.ConfigDict()
            try:
                defaultFileName = PyMca5.getDefaultSettingsFile()
                self.configDir  = os.path.dirname(defaultFileName)
            except Exception:
                if not ('fresh' in kw):
                    raise
            if not ('fresh' in kw):
                if os.path.exists(defaultFileName):
                    currentConfigDict.read(defaultFileName)
                    self.setConfig(currentConfigDict)
            if ('spec' in kw) and ('shm' in kw):
                if len(kw['shm']) >= 8:
                    #if kw['shm'][0:8] in ['MCA_DATA', 'XIA_DATA']:
                    if kw['shm'][0:8] in ['MCA_DATA']:
                        #self.mcaWindow.showMaximized()
                        self.toggleSource()
                        self._startupSelection(source=kw['spec'],
                                                selection=kw['shm'])
                    else:
                        self._startupSelection(source=kw['spec'],
                                                selection=None)
                else:
                     self._startupSelection(source=kw['spec'],
                                                selection=None)

    def connectDispatcher(self, viewer, dispatcher=None):
        #I could connect sourceWidget to myself and then
        #pass the selections to the active window!!
        #That will be made in a next iteration I guess
        if dispatcher is None:
            dispatcher = self.sourceWidget
        dispatcher.sigAddSelection.connect(viewer._addSelection)
        dispatcher.sigRemoveSelection.connect(viewer._removeSelection)
        dispatcher.sigReplaceSelection.connect(viewer._replaceSelection)

    def currentTabIndexChanged(self, index):
        legend = "%s" % self.mainTabWidget.tabText(index)
        for key in self.imageWindowDict.keys():
            if key == legend:
                value = True
            else:
                value = False
            self.imageWindowDict[key].setPlotEnabled(value)

    def _is2DSelection(self, ddict):
        if 'imageselection' in ddict:
            if ddict['imageselection']:
                return True
        if 'selection' in ddict:
            if ddict['selection'] is None:
                return False
            if 'selectiontype' in ddict['selection']:
                if ddict['selection']['selectiontype'] == '2D':
                    return True
        return False

    def _isScatterSelection(self, ddict):
        if 'imageselection' in ddict:
            if ddict['imageselection']:
                return False
        if 'selection' in ddict:
            if ddict['selection'] is None:
                return False
            if "x" in ddict['selection']:
                if hasattr(ddict['selection']['x'], "__len__"):
                    if len(ddict['selection']['x']) != 2:
                        return False
                    size0 = ddict['dataobject'].x[0].size
                    size1 = ddict['dataobject'].x[1].size
                    if size0 != size1:
                        return False
                    if hasattr(ddict['dataobject'], "y"):
                        if ddict['dataobject'].y:
                            if ddict['dataobject'].y[0].size != size0 * size1:
                                return False
                    if "PyMca5.PyMcaGui.pymca.SilxScatterWindow" in sys.modules:
                        if silx.version_info > (0, 10, 2):
                            return True
        return False

    def _is3DSelection(self, ddict):
        if self._is2DSelection(ddict):
            return False

        if 'selection' in ddict:
            if ddict['selection'] is None:
                return False
            if 'selectiontype' in ddict['selection']:
                if ddict['selection']['selectiontype'] == '3D':
                    return True

            if 'x' in ddict['selection']:
                if hasattr(ddict['selection']['x'], "__len__"):
                    if len(ddict['selection']['x']) > 1:
                        return True
        return False

    def _isStackSelection(self, ddict):
        if self._is2DSelection(ddict):
            return False
        if self._is3DSelection(ddict):
            return False
        if 'selection' in ddict:
            if ddict['selection'] is None:
                return False
            if 'selectiontype' in ddict['selection']:
                if ddict['selection']['selectiontype'] == 'STACK':
                    return True
        return False


    def dispatcherAddSelectionSlot(self, ddict):
        if self.__useTabWidget:
            if self.mainTabWidget.isHidden():
                #make sure it is visible in case of being closed
                self.mainTabWidget.show()

        try:
            self._dispatcherAddSelectionSlot(ddict)
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error: %s" % sys.exc_info()[1])
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _dispatcherAddSelectionSlot(self, dictOrList):
        _logger.info("self._dispatcherAddSelectionSlot(ddict), ddict = %s",
                      dictOrList)
        if type(dictOrList) == type([]):
            ddict = dictOrList[0]
        else:
            ddict = dictOrList

        toadd = False
        if self._isScatterSelection(ddict):
            _logger.info("ScatterPlot selection")
            legend = ddict['legend']
            if legend not in self.imageWindowDict.keys():
                if OPENGL_DRIVERS_OK:
                    backend = "gl"
                else:
                    backend = "mpl"
                imageWindow = SilxScatterWindow.SilxScatterWindow(backend=backend)
                self.imageWindowDict[legend] = imageWindow
                self.imageWindowDict[legend].setPlotEnabled(True)
                if self.mainTabWidget.indexOf(self.imageWindowDict[legend]) < 0:
                    self.mainTabWidget.addTab(self.imageWindowDict[legend],
                                          legend)
                self.imageWindowDict[legend]._addSelection(ddict)
                self.mainTabWidget.setCurrentWidget(imageWindow)
                return
            if self.mainTabWidget.indexOf(self.imageWindowDict[legend]) < 0:
                self.mainTabWidget.addTab(self.imageWindowDict[legend],
                                          legend)
                #self.imageWindowDict[legend].setPlotEnabled(False)
                self.imageWindowDict[legend]._addSelection(ddict)
                self.mainTabWidget.setCurrentWidget(self.imageWindowDict\
                                                        [legend])
            else:
                self.imageWindowDict[legend]._addSelection(ddict)
            return
        elif self._is2DSelection(ddict):
            _logger.info("2D selection")
            if self.imageWindowCorrelator is None:
                self.imageWindowCorrelator = RGBCorrelator.RGBCorrelator()
                #toadd = True
            title  = "ImageWindow RGB Correlator"
            self.imageWindowCorrelator.setWindowTitle(title)
            legend = ddict['legend']
            if legend not in self.imageWindowDict.keys():
                hkl = False
                try:
                    motor_mne = ddict['dataobject'].info['motor_mne'].split()
                    if ('phi' in motor_mne) and ('chi' in motor_mne):
                        if ('mu'  in motor_mne) and ('gam' in motor_mne) :
                           if 'del' in motor_mne:
                               #SIXC
                               hkl = True
                        if ('tth' in motor_mne) and ('th' in motor_mne):
                            #FOURC
                            hkl = True
                except Exception:
                    pass
                if hkl:
                    imageWindow = PyMcaHKLImageWindow.PyMcaHKLImageWindow(
                            name=legend,
                            correlator=self.imageWindowCorrelator,
                            scanwindow=self.scanWindow)
                else:
                    imageWindow = PyMcaImageWindow.PyMcaImageWindow(
                            name=legend,
                            correlator=self.imageWindowCorrelator,
                            scanwindow=self.scanWindow,
                            usesilx=None)
                self.imageWindowDict[legend] = imageWindow

                imageWindow.sigAddImageClicked.connect( \
                     self.imageWindowCorrelator.addImageSlot)
                imageWindow.sigRemoveImageClicked.connect( \
                     self.imageWindowCorrelator.removeImageSlot)
                imageWindow.sigReplaceImageClicked.connect( \
                     self.imageWindowCorrelator.replaceImageSlot)
                self.mainTabWidget.addTab(imageWindow, legend)
                if toadd:
                    self.mainTabWidget.addTab(self.imageWindowCorrelator,
                        "RGB Correlator")
                self.imageWindowDict[legend].setPlotEnabled(False)
                self.imageWindowDict[legend]._addSelection(ddict)
                self.mainTabWidget.setCurrentWidget(imageWindow)
                #self.imageWindowDict[legend].setPlotEnabled(True)
                return
            if self.mainTabWidget.indexOf(self.imageWindowDict[legend]) < 0:
                self.mainTabWidget.addTab(self.imageWindowDict[legend],
                                          legend)
                self.imageWindowDict[legend].setPlotEnabled(False)
                self.imageWindowDict[legend]._addSelection(ddict)
                self.mainTabWidget.setCurrentWidget(self.imageWindowDict\
                                                        [legend])
            else:
                self.imageWindowDict[legend]._addSelection(ddict)
        elif self._isStackSelection(ddict):
            _logger.info("Stack selection")
            legend = ddict['legend']
            widget = QStackWidget.QStackWidget()
            widget.notifyCloseEventToWidget(self)
            widget.setStack(ddict['dataobject'])
            widget.setWindowTitle(legend)
            widget.show()
            self._widgetDict[id(widget)] = widget
        else:
            if OBJECT3D or isSilxGLAvailable:
                if ddict['dataobject'].info['selectiontype'] == "1D":
                    _logger.info("1D selection")
                    self.mcaWindow._addSelection(dictOrList)
                    self.scanWindow._addSelection(dictOrList)
                else:
                    _logger.info("3D selection")
                    self.mainTabWidget.setCurrentWidget(self.glWindow)
                    self.glWindow._addSelection(dictOrList)
            else:
                _logger.info("1D selection")
                self.mcaWindow._addSelection(dictOrList)
                self.scanWindow._addSelection(dictOrList)

    def dispatcherRemoveSelectionSlot(self, ddict):
        try:
            return self._dispatcherRemoveSelectionSlot(ddict)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            txt = "Error: %s" % sys.exc_info()[1]
            msg.setInformativeText(txt)
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _dispatcherRemoveSelectionSlot(self, dictOrList):
        _logger.debug("self.dispatcherRemoveSelectionSlot(ddict), ddict = %s", dictOrList)
        if type(dictOrList) == type([]):
            ddict = dictOrList[0]
        else:
            ddict = dictOrList
        if self._is2DSelection(ddict) or self._isScatterSelection(ddict):
            legend = ddict['legend']
            if legend in self.imageWindowDict.keys():
                index = self.mainTabWidget.indexOf(self.imageWindowDict[legend])
                if index >0:
                    self.imageWindowDict[legend].close()
                    self.imageWindowDict[legend].setParent(None)
                    self.mainTabWidget.removeTab(index)
                    self.imageWindowDict[legend]._removeSelection(ddict)
                    del self.imageWindowDict[legend]
        elif self._is3DSelection(ddict):
            self.glWindow._removeSelection(dictOrList)
        else:
            self.mcaWindow._removeSelection(dictOrList)
            self.scanWindow._removeSelection(dictOrList)

    def dispatcherReplaceSelectionSlot(self, ddict):
        try:
            return self._dispatcherReplaceSelectionSlot(ddict)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            txt = "Error: %s" % sys.exc_info()[1]
            msg.setInformativeText(txt)
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _dispatcherReplaceSelectionSlot(self, dictOrList):
        _logger.debug("self.dispatcherReplaceSelectionSlot(ddict), ddict = %s",
                      dictOrList)
        if type(dictOrList) == type([]):
            ddict = dictOrList[0]
        else:
            ddict = dictOrList
        if self._isScatterSelection(ddict) or self._is2DSelection(ddict):
            legend = ddict['legend']
            for key in list(self.imageWindowDict.keys()):
                index = self.mainTabWidget.indexOf(self.imageWindowDict[key])
                if key == legend:
                    continue
                if index >= 0:
                    self.imageWindowDict[key].close()
                    self.imageWindowDict[key].setParent(None)
                    self.mainTabWidget.removeTab(index)
                    self.imageWindowDict[key]._removeSelection(ddict)
                    del self.imageWindowDict[key]
            if legend in self.imageWindowDict.keys():
                self.imageWindowDict[legend].setPlotEnabled(False)
            self.dispatcherAddSelectionSlot(ddict)
            index = self.mainTabWidget.indexOf(self.imageWindowDict[legend])
            if index != self.mainTabWidget.currentIndex():
                self.mainTabWidget.setCurrentWidget(self.imageWindowDict[legend])
            if legend in self.imageWindowDict.keys():
                # force an update
                self.imageWindowDict[legend].setPlotEnabled(True)
                self.imageWindowDict[legend].setPlotEnabled(False)
        elif self._is3DSelection(ddict):
            self.glWindow._replaceSelection(dictOrList)
        else:
            self.mcaWindow._replaceSelection(dictOrList)
            self.scanWindow._replaceSelection(dictOrList)

    def dispatcherOtherSignalsSlot(self, dictOrList):
        _logger.debug("self.dispatcherOtherSignalsSlot(ddict), ddict = %s",
                      dictOrList)
        if type(dictOrList) == type([]):
            ddict = dictOrList[0]
        else:
            ddict = dictOrList
        if not self.__useTabWidget:
            return
        if ddict['event'] == "SelectionTypeChanged":
            if ddict['SelectionType'].upper() == "COUNTERS":
                self.mainTabWidget.setCurrentWidget(self.scanWindow)
                return
            for i in range(self.mainTabWidget.count()):
                if str(self.mainTabWidget.tabText(i)) == \
                                   ddict['SelectionType']:
                    self.mainTabWidget.setCurrentIndex(i)
            return
        if ddict['event'] == "SourceTypeChanged":
            pass
            return
        _logger.debug("Unhandled dict")

    def setConfig(self, configDict):
        if 'PyMca' in configDict:
            self.__configurePyMca(configDict['PyMca'])
        if 'ROI' in configDict:
            self.__configureRoi(configDict['ROI'])
        if 'Elements' in configDict:
            self.__configureElements(configDict['Elements'])
        if 'Fit' in configDict:
            self.__configureFit(configDict['Fit'])
        if 'ScanSimpleFit' in configDict:
            self.__configureScanSimpleFit(configDict['ScanSimpleFit'])
        if 'ScanCustomFit' in configDict:
            self.__configureScanCustomFit(configDict['ScanCustomFit'])

    def getConfig(self):
        d = {}
        d['PyMca']    = {}
        d['PyMca']['VERSION']   = __version__
        d['PyMca']['ConfigDir'] = self.configDir
        d['PyMca']['nativeFileDialogs'] = PyMcaDirs.nativeFileDialogs

        #geometry
        d['PyMca']['Geometry']  ={}
        r = self.geometry()
        d['PyMca']['Geometry']['MainWindow'] = [r.x(), r.y(), r.width(), r.height()]
        r = self.splitter.sizes()
        d['PyMca']['Geometry']['Splitter'] = r
        r = self.mcaWindow.geometry()
        d['PyMca']['Geometry']['McaWindow'] = [r.x(), r.y(), r.width(), r.height()]

        #sources
        d['PyMca']['Sources'] = {}
        d['PyMca']['Sources']['lastFileFilter'] = self.sourceWidget.sourceSelector.lastFileFilter
        for source in SOURCESLIST:
            d['PyMca'][source] = {}
            if (self.sourceWidget.sourceSelector.lastInputDir is not None) and \
               len(self.sourceWidget.sourceSelector.lastInputDir):
                d['PyMca'][source]['lastInputDir'] = self.sourceWidget.sourceSelector.lastInputDir
                try:
                    PyMcaDirs.inputDir = self.sourceWidget.sourceSelector.lastInputDir
                except ValueError:
                    pass
            else:
                d['PyMca'][source]['lastInputDir'] = "None"
            if source == "SpecFile":
                d['PyMca'][source]['SourceName'] = []
                for key in self.sourceWidget.sourceList:
                    if key.sourceType == source:
                        d['PyMca'][source]['SourceName'].append(key.sourceName)
            elif source == "EdfFile":
                d['PyMca'][source]['SourceName'] = []
                for key in self.sourceWidget.sourceList:
                    if key.sourceType == source:
                        d['PyMca'][source]['SourceName'].append(key.sourceName)
                    #if key == "EDF Stack":
                    #    d['PyMca'][source]['SourceName'].append(self.sourceWidget.selectorWidget[source]._edfstack)
                    #else:
                    #    d['PyMca'][source]['SourceName'].append(self.sourceWidget.selectorWidget[source].mapComboName[key])
            elif source == "HDF5":
                d['PyMca'][source]['SourceName'] = []
                for key in self.sourceWidget.sourceList:
                    if key.sourceType == source:
                        d['PyMca'][source]['SourceName'].append(key.sourceName)
            selectorWidget = self.sourceWidget.selectorWidget[source]
            if hasattr(selectorWidget,'setWidgetConfiguration'):
                d['PyMca'][source]['WidgetConfiguration'] = selectorWidget.getWidgetConfiguration()

            #d['PyMca'][source]['Selection'] = self.sourceWidget[source].getSelection()

        # McaWindow calibrations
        d["PyMca"]["McaWindow"] = {}
        d["PyMca"]["McaWindow"]["calibrations"] = self.mcaWindow.getCalibrations()

        #ROIs
        d['ROI'] = {}
        if self.mcaWindow.roiWidget is None:
            roilist = []
            roidict = {}
        else:
            roilist, roidict = self.mcaWindow.roiWidget.getROIListAndDict()
        d['ROI']['roilist'] = roilist
        d['ROI']['roidict'] = {}
        d['ROI']['roidict'].update(roidict)

        #fit related
        d['Elements'] = {}
        d['Elements']['Material'] = {}
        d['Elements']['Material'].update(ElementsInfo.Elements.Material)
        d['Fit'] = {}
        if self.mcaWindow.advancedfit.configDir is not None:
            d['Fit'] ['ConfigDir'] = self.mcaWindow.advancedfit.configDir * 1
        d['Fit'] ['Configuration'] = {}
        d['Fit'] ['Configuration'].update(self.mcaWindow.advancedfit.mcafit.configure())
        d['Fit'] ['Information'] = {}
        d['Fit'] ['Information'].update(self.mcaWindow.advancedfit.info)
        d['Fit'] ['LastFit'] = {}
        d['Fit'] ['LastFit']['hidden'] = self.mcaWindow.advancedfit.isHidden()
        d['Fit'] ['LastFit']['xdata0'] = self.mcaWindow.advancedfit.mcafit.xdata0
        d['Fit'] ['LastFit']['ydata0'] = self.mcaWindow.advancedfit.mcafit.ydata0
        d['Fit'] ['LastFit']['sigmay0']= self.mcaWindow.advancedfit.mcafit.sigmay0
        d['Fit'] ['LastFit']['fitdone']= self.mcaWindow.advancedfit._fitdone()
        #d['Fit'] ['LastFit']['fitdone']= 1
        #d['Fit'] ['LastFit']['xmin'] = self.mcaWindow.advancedfit.mcafit.sigma0
        #d['Fit'] ['LastFit']['xmax'] = self.mcaWindow.advancedfit.mcafit.sigma0

        #ScanFit related
        d['ScanSimpleFit'] = {}
        d['ScanSimpleFit']['Configuration'] = {}

        try:
            d['ScanSimpleFit']['Configuration'].update(
                self.scanWindow.scanFit.getConfiguration())
        except Exception:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            _logger.warning("Error getting ScanFit configuration")
        return d

    def saveConfig(self, config, filename = None):
        d = ConfigDict.ConfigDict()
        d.update(config)
        if filename is None:
            filename = PyMca5.getDefaultSettingsFile()
        d.write(filename)

    def __configurePyMca(self, ddict):
        savedVersion = ddict.get("VERSION", '4.7.2')
        if 'ConfigDir' in ddict:
            self.configDir = ddict['ConfigDir']

        if 'Geometry' in ddict:
            r = qt.QRect(*ddict['Geometry']['MainWindow'])
            self.setGeometry(r)
            key = 'Splitter'
            if key in ddict['Geometry'].keys():
                self.splitter.setSizes(ddict['Geometry'][key])
            key = 'McaWindow'
            if key in ddict['Geometry'].keys():
                r = qt.QRect(*ddict['Geometry']['McaWindow'])
                self.mcaWindow.setGeometry(r)
            if hasattr(self.mcaWindow, "graph"):
                # this was the way of working of 4.x.x versions
                key = 'McaGraph'
                if key in ddict['Geometry'].keys():
                    r = qt.QRect(*ddict['Geometry']['McaGraph'])
                    self.mcaWindow.graph.setGeometry(r)
            self.show()
            qApp = qt.QApplication.instance()
            qApp.processEvents()
            qApp.postEvent(self, qt.QResizeEvent(qt.QSize(ddict['Geometry']['MainWindow'][2]+1,
                                                          ddict['Geometry']['MainWindow'][3]+1),
                                                 qt.QSize(ddict['Geometry']['MainWindow'][2],
                                                          ddict['Geometry']['MainWindow'][3])))
            self.mcaWindow.showMaximized()

        native = ddict.get('nativeFileDialogs', True)
        if native in ["False", "0", 0]:
            native = False
        else:
            native = True
        PyMcaDirs.nativeFileDialogs = native

        if 'Sources' in ddict:
            if 'lastFileFilter' in ddict['Sources']:
                self.sourceWidget.sourceSelector.lastFileFilter = ddict['Sources']['lastFileFilter']
        for source in SOURCESLIST:
            if source in ddict:
                if 'lastInputDir' in ddict[source]:
                    if ddict[source] ['lastInputDir'] not in ["None", []]:
                        self.sourceWidget.sourceSelector.lastInputDir =  ddict[source] ['lastInputDir']
                        try:
                            PyMcaDirs.inputDir = ddict[source] ['lastInputDir']
                        except ValueError:
                            _logger.info("Cannot open directory <%s>" % ddict[source] ['lastInputDir'])
                            pass
                if 'SourceName' in ddict[source]:
                    if type(ddict[source]['SourceName']) != type([]):
                        ddict[source]['SourceName'] = [ddict[source]['SourceName'] * 1]
                    for SourceName0 in ddict[source]['SourceName']:
                        if type(SourceName0) == type([]):
                            SourceName = SourceName0[0]
                        else:
                            SourceName = SourceName0
                        if len(SourceName):
                            try:
                                if not os.path.exists(SourceName):
                                    continue
                                self.sourceWidget.sourceSelector.openFile(SourceName, justloaded =1)
                                continue
                                #This event is not needed
                                ndict = {}
                                ndict["event"] = "NewSourceSelected"
                                ndict["sourcelist"] = [SourceName]
                                self.sourceWidget._sourceSelectorSlot(ndict)
                                continue
                                if source == "EdfFile":
                                    self.sourceWidget.selectorWidget[source].openFile(SourceName, justloaded=1)
                                else:
                                    self.sourceWidget.selectorWidget[source].openFile(SourceName)
                            except Exception:
                                msg = qt.QMessageBox(self)
                                msg.setIcon(qt.QMessageBox.Critical)
                                txt = "Error: %s\n opening file %s" % (sys.exc_info()[1],SourceName )
                                msg.setInformativeText(txt)
                                msg.setDetailedText(traceback.format_exc())
                                msg.exec()

                if 'WidgetConfiguration' in ddict[source]:
                    selectorWidget = self.sourceWidget.selectorWidget[source]
                    if hasattr(selectorWidget,'setWidgetConfiguration'):
                        try:
                            selectorWidget.setWidgetConfiguration(ddict[source]['WidgetConfiguration'])
                        except Exception:
                            msg = qt.QMessageBox(self)
                            msg.setIcon(qt.QMessageBox.Critical)
                            txt = "Error: %s\n configuring %s widget" % (sys.exc_info()[1], source )
                            msg.setInformativeText(txt)
                            msg.setDetailedText(traceback.format_exc())
                            msg.exec()
        if "McaWindow" in ddict:
            self.mcaWindow.setCalibrations(ddict["McaWindow"]["calibrations"])

    def __configureRoi(self, ddict):
        if 'roidict' in ddict:
            if 'roilist' in ddict:
                roilist = ddict['roilist']
                if type(roilist) != type([]):
                    roilist=[roilist]
                roidict = ddict['roidict']
                if self.mcaWindow.roiWidget is None:
                    self.mcaWindow.showRoiWidget(qt.Qt.BottomDockWidgetArea)
                self.mcaWindow.roiWidget.fillFromROIDict(roilist=roilist,
                                                         roidict=roidict)

    def __configureElements(self, ddict):
        if 'Material' in ddict:
            ElementsInfo.Elements.Material.update(ddict['Material'])

    def __configureFit(self, d):
        if 'Configuration' in d:
            self.mcaWindow.advancedfit.configure(d['Configuration'])
            if not self.mcaWindow.advancedfit.isHidden():
                self.mcaWindow.advancedfit._updateTop()
        if 'ConfigDir' in d:
            self.mcaWindow.advancedfit.configDir = d['ConfigDir'] * 1
        if False and ('LastFit' in d):
            if (d['LastFit']['ydata0'] != None) and \
               (d['LastFit']['ydata0'] != 'None'):
                self.mcaWindow.advancedfit.setdata(x=d['LastFit']['xdata0'],
                                                   y=d['LastFit']['ydata0'],
                                              sigmay=d['LastFit']['sigmay0'],
                                              **d['Information'])
                if d['LastFit']['hidden'] == 'False':
                    self.mcaWindow.advancedfit.show()
                    self.mcaWindow.advancedfit.raise_()
                    if d['LastFit']['fitdone']:
                        try:
                            self.mcaWindow.advancedfit.fit()
                        except Exception:
                            pass
                else:
                    print("hidden")

    def __configureFit(self, d):
        if 'Configuration' in d:
            self.mcaWindow.advancedfit.mcafit.configure(d['Configuration'])
            if not self.mcaWindow.advancedfit.isHidden():
                self.mcaWindow.advancedfit._updateTop()
        if 'ConfigDir' in d:
            self.mcaWindow.advancedfit.configDir = d['ConfigDir'] * 1
        if False and ('LastFit' in d):
            if (d['LastFit']['ydata0'] != None) and \
               (d['LastFit']['ydata0'] != 'None'):
                self.mcaWindow.advancedfit.setdata(x=d['LastFit']['xdata0'],
                                                   y=d['LastFit']['ydata0'],
                                              sigmay=d['LastFit']['sigmay0'],
                                              **d['Information'])
                if d['LastFit']['hidden'] == 'False':
                    self.mcaWindow.advancedfit.show()
                    self.mcaWindow.advancedfit.raise_()
                    if d['LastFit']['fitdone']:
                        try:
                            self.mcaWindow.advancedfit.fit()
                        except Exception:
                            pass
                else:
                    _logger.info("hidden")

    def __configureScanCustomFit(self, ddict):
        pass

    def __configureScanSimpleFit(self, ddict):
        if 'Configuration' in ddict:
            self.scanWindow.scanFit.setConfiguration(ddict['Configuration'])

    def initMenuBar(self):
        if self.options["MenuFile"]:
            #build the actions
            #fileopen
            self.actionOpen = qt.QAction(self)
            self.actionOpen.setText(QString("&Open"))
            self.actionOpen.setIcon(self.Icons["fileopen"])
            self.actionOpen.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_O))
            self.actionOpen.triggered[bool].connect(self.onOpen)
            #filesaveas
            self.actionSaveAs = qt.QAction(self)
            self.actionSaveAs.setText(QString("&Save"))
            self.actionSaveAs.setIcon(self.Icons["filesave"])
            self.actionSaveAs.setShortcut(\
                qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_S))
            self.actionSaveAs.triggered[bool].connect(self.onSaveAs)

            #filesave
            self.actionSave = qt.QAction(self)
            self.actionSave.setText(QString("Save &Default Settings"))
            #self.actionSave.setIcon(self.Icons["filesave"])
            #self.actionSave.setShortcut(qt.Qt.CTRL|qt.Qt.Key_S)
            self.actionSave.triggered[bool].connect(self.onSave)

            #fileprint
            self.actionPrint = qt.QAction(self)
            self.actionPrint.setText(QString("&Print"))
            self.actionPrint.setIcon(self.Icons["fileprint"])
            self.actionPrint.setShortcut(\
                qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_P))
            self.actionPrint.triggered[bool].connect(self.onPrint)

            #filequit
            self.actionQuit = qt.QAction(self)
            self.actionQuit.setText(QString("&Quit"))
            #self.actionQuit.setIcon(self.Icons["fileprint"])
            self.actionQuit.setShortcut(\
                                       qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_Q))
            qApp = qt.QApplication.instance()
            self.actionQuit.triggered.connect(qApp.closeAllWindows)

            #self.menubar = qt.QMenuBar(self)
            self.menuFile= qt.QMenu(self.menuBar())
            self.menuFile.addAction(self.actionOpen)
            self.menuFile.addAction(self.actionSaveAs)
            self.menuFile.addAction(self.actionSave)
            self.menuFile.addSeparator()
            self.menuFile.addAction(self.actionPrint)
            self.menuFile.addSeparator()
            self.menuFile.addAction(self.actionQuit)
            self.menuBar().addMenu(self.menuFile)
            self.menuFile.setTitle("&File")
            self.onInitMenuBar(self.menuBar())

        if self.options["MenuTools"]:
            self.menuTools= qt.QMenu()
            #self.menuTools.setCheckable(1)
            self.menuTools.aboutToShow[()].connect(self.menuToolsAboutToShow)
            self.menuTools.setTitle("&Tools")
            self.menuBar().addMenu(self.menuTools)

        if self.options["MenuWindow"]:
            self.menuWindow= qt.QMenu()
            #self.menuWindow.setCheckable(1)
            self.menuWindow.aboutToShow[()].connect(self.menuWindowAboutToShow)
            self.menuWindow.setTitle("&Window")
            self.menuBar().addMenu(self.menuWindow)

        if self.options["MenuHelp"]:
            self.menuHelp= qt.QMenu(self)
            self.menuHelp.addAction("&Menu", self.onMenuHelp)
            self.menuHelp.addAction("&Data Display HOWTOs", self.onDisplayHowto)
            self.menuHelp.addAction("MCA &HOWTOs",self.onMcaHowto)
            self.menuHelp.addSeparator()
            self.menuHelp.addAction("&About", self.onAbout)
            self.menuHelp.addAction("Web Documentation", self.onWebDocumentation)
            self.menuHelp.addAction("Changes", self.onChanges)
            self.menuHelp.addAction("About &Qt",self.onAboutQt)
            self.menuBar().addSeparator()
            self.menuHelp.setTitle("&Help")
            self.menuBar().addMenu(self.menuHelp)
            self.menuBrowser    = None
            self.displayBrowser = None
            self.mcaBrowser     = None

    def initSourceBrowser(self):
        self.sourceFrame     = qt.QWidget(self.splitter)
        self.splitter.insertWidget(0, self.sourceFrame)
        self.sourceFrame.setWindowTitle("Source Selector")
        self.sourceFrame.setWindowIcon(self.windowIcon())
        #self.splitter.setResizeMode(self.sourceFrame,qt.QSplitter.KeepSize)
        self.sourceFrameLayout = qt.QVBoxLayout(self.sourceFrame)
        self.sourceFrameLayout.setContentsMargins(0, 0, 0, 0)
        self.sourceFrameLayout.setSpacing(0)
        #layout.setAutoAdd(1)

        sourceToolbar = qt.QWidget(self.sourceFrame)
        layout1       = qt.QHBoxLayout(sourceToolbar)
        #self.line1 = qt.QFrame(sourceToolbar,"line1")
        self.line1 = Line(sourceToolbar)
        self.line1.setFrameShape(qt.QFrame.HLine)
        self.line1.setFrameShadow(qt.QFrame.Sunken)
        self.line1.setFrameShape(qt.QFrame.HLine)
        layout1.addWidget(self.line1)
        #self.closelabel = qt.QLabel(sourceToolbar)
        self.closelabel = PixmapLabel(sourceToolbar)
        self.closelabel.setPixmap(qt.QPixmap(IconDict0['close']))
        layout1.addWidget(self.closelabel)
        self.closelabel.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        #self.sourceBrowserTab=qt.QTabWidget(self.sourceFrame)

        self.sourceFrameLayout.addWidget(sourceToolbar)

        #connections
        self.line1.sigLineDoubleClickEvent.connect(self.sourceReparent)
        self.closelabel.sigPixmapLabelMousePressEvent.connect(self.toggleSource)

        #tips
        self.line1.setToolTip("DoubleClick toggles floating window mode")
        self.closelabel.setToolTip("Hides Source Area")

    def sourceReparent(self,ddict = None):
        if self.sourceFrame.parent() is not None:
            self.sourceFrame.setParent(None)
            self.sourceFrame.move(self.cursor().pos())
            self.sourceFrame.show()
        else:
            try:
                self.splitter.insertWidget(0, self.sourceFrame)
            except Exception:
                self.sourceFrame.setParent(self.splitter)

    def initSource(self):
        self.sourceWidget = QDispatcher.QDispatcher(self.sourceFrame)
        self.sourceFrameLayout.addWidget(self.sourceWidget)

    def _startupSelection(self, source, selection):
        self.sourceWidget.sourceSelector.openSource(source)
        if selection is None:
            return

        if len(selection) >= 8:
            if selection[0:8] == "MCA_DATA":
                ddict= {}
                ddict['event'] = "addSelection"
                ddict['SourceName'] = source
                ddict['Key'] = selection
                ddict["selection"] = {'cols': {'y': [1], 'x': [0]}}
                ddict["legend"] = ddict['SourceName'] + ' %s.c.1' %selection
                ddict["SourceType"] =  'SPS'
                self.sourceWidget._addSelectionSlot([ddict])
                self.mcaWindow.controlWidget.calbox.setCurrentIndex(2)
                self.mcaWindow.calibration = self.mcaWindow.calboxoptions[2]
                self.mcaWindow.controlWidget._calboxactivated("Internal")
        else:
            return
        """
        elif selection == "XIA_DATA":
            ddict= {}
            ddict['event'] = "addSelection"
            ddict['SourceName'] = "armando5"
            ddict['Key'] = selection
            ddict["selection"] = {'rows': {'y': [1], 'x': [0]}}
            ddict["legend"] = ddict['SourceName'] + ' XIA_DATA.c.1'
            ddict["SourceType"] =  'SPS'
            self.sourceWidget._addSelectionSlot([ddict])
        """

    def menuToolsAboutToShow(self):
        _logger.debug("menu ToolsAboutToShow")
        self.menuTools.clear()
        if self.sourceFrame.isHidden():
            self.menuTools.addAction("Show Source",self.toggleSource)
        else:
            self.menuTools.addAction("Hide Source",self.toggleSource)
        self.menuTools.addAction("Elements   Info",self.__elementsInfo)
        self.menuTools.addAction("Material Transmission",self.__attTool)
        self.menuTools.addAction("Identify  Peaks",self.__peakIdentifier)
        self.menuTools.addAction("Batch   Fitting",self.__batchFitting)
        self.menuTools.addAction("Convert Mca to Edf",self.__mca2EdfConversion)
        #self.menuTools.addAction("Fit to Specfile",self.__fit2SpecConversion)
        self.menuTools.addAction("RGB Correlator",self.__rgbCorrelator)
        if STACK:
            self.menuTools.addAction("ROI Imaging",self.__roiImaging)
        if XIA_CORRECT:
            self.menuTools.addAction("XIA Correct",
                                     self.__xiaCorrect)
        if XRFMC_FLAG:
            self.menuTools.addAction("XMI-MSIM PyMca",
                                     self._xrfmcPyMca)
        if SUMRULES_FLAG:
            self.menuTools.addAction("Sum Rules Tool", self._sumRules)
        _logger.debug("Fit to Specfile missing")
        if TOMOGUI_FLAG:
            self.menuTools.addAction("Tomography reconstruction",
                                     self.__tomoRecons)

    def fontdialog(self):
        fontd = qt.QFontDialog.getFont(self)
        if fontd[1]:
            qApp = qt.QApplication.instance()
            qApp.setFont(fontd[0],1)


    def toggleSource(self,**kw):
        _logger.debug("toggleSource called")
        if self.sourceFrame.isHidden():
            self.sourceFrame.show()
            self.sourceFrame.raise_()
        else:
            self.sourceFrame.hide()

    def __elementsInfo(self):
        if self.elementsInfo is None:
            self.elementsInfo=ElementsInfo.ElementsInfo(None,"Elements Info")
        if self.elementsInfo.isHidden():
           self.elementsInfo.show()
        self.elementsInfo.raise_()

    def __attTool(self):
        if self.attenuationTool is None:
            self.attenuationTool = MaterialEditor.MaterialEditor(toolmode=True)
        if self.attenuationTool.isHidden():
            self.attenuationTool.show()
        self.attenuationTool.raise_()

    def __peakIdentifier(self):
        if self.identifier is None:
            self.identifier=PeakIdentifier.PeakIdentifier(energy=5.9,
                                useviewer=1)
            self.identifier.mySlot()
        if self.identifier.isHidden():
            self.identifier.show()
        self.identifier.raise_()

    def __batchFitting(self):
        if self.__batch is None:
            self.__batch = PyMcaBatch.McaBatchGUI(fl=0,actions=1)
        if self.__batch.isHidden():
            self.__batch.show()
        self.__batch.raise_()

    def __mca2EdfConversion(self):
        if self.__mca2Edf is None:
            self.__mca2Edf = Mca2Edf.Mca2EdfGUI(fl=0,actions=1)
        if self.__mca2Edf.isHidden():
            self.__mca2Edf.show()
        self.__mca2Edf.raise_()

    def __fit2SpecConversion(self):
        if self.__fit2Spec is None:
            self.__fit2Spec = Fit2Spec.Fit2SpecGUI(fl=0,actions=1)
        if self.__fit2Spec.isHidden():
            self.__fit2Spec.show()
        self.__fit2Spec.raise_()

    def __rgbCorrelator(self):
        if self.__correlator is None:
            self.__correlator = []
        fileTypeList = [
            "HDF5 Files *.h5 *.nxs *.hdf *.hdf5",
            "ASCII Files *dat",
            "EDF Files *edf",
            "EDF Files *ccd",
            "CSV Files *csv",
            "TIFF Files *tiff *tif",
            "TextImage Files *txt",
            "All Files *",
        ]
        message = "Open ONE Batch result .dat file or SEVERAL EDF files"
        filelist = self.__getStackOfFiles(fileTypeList, message)
        if filelist:
            filelist.sort()
            self.sourceWidget.sourceSelector.lastInputDir = os.path.dirname(filelist[0])
            PyMcaDirs.inputDir = os.path.dirname(filelist[0])
        self.__correlator.append(PyMcaPostBatch.PyMcaPostBatch())
        for correlator in self.__correlator:
            if correlator.isHidden():
                correlator.show()
            correlator.raise_()
        self.__correlator[-1].sigRGBCorrelatorSignal.connect( \
                self._deleteCorrelator)
        if filelist:
            correlator.addFileList(filelist)

    def __sumRules(self):
        if self.__correlator is None:
            self.__correlator = []

    def __tomoRecons(self):
        if self.__reconsWidget is None:
            try:
                from tomogui.gui.ProjectWidget \
                     import ProjectWindow as TomoguiProjectWindow
            except ImportError:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                txt = "This functionality requires tomogui, silx and FreeART"
                msg.setInformativeText(txt)
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
            self.__reconsWidget = TomoguiProjectWindow()
        if self.__reconsWidget.isHidden():
            self.__reconsWidget.show()
        self.__reconsWidget.raise_()

    def _deleteCorrelator(self, ddict):
        n = len(self.__correlator)
        if ddict['event'] == "RGBCorrelatorClosed":
            for i in range(n):
                if id(self.__correlator[i]) == ddict["id"]:
                    self.__correlator[i].deleteLater()
                    del self.__correlator[i]
                    break

    def __getStackOfFiles(self, typelist, message="", getfilter=False):
        wdir = PyMcaDirs.inputDir
        fileTypeList = typelist
        filterused = None
        #windows cannot handle thousands of files in a file dialog force Qt dialogs
        output = PyMcaFileDialogs.getFileList(self, filetypelist=typelist, message=message, currentdir=wdir,
                                        mode="OPEN", getfilter=getfilter, single=False, currentfilter=None, native=False)
        if getfilter:
            return output[0], output[1]
        else:
            return output

    def __roiImaging(self):
        if self.__imagingTool is None:
            rgbWidget = None
            try:
                widget = QStackWidget.QStackWidget(mcawidget=self.mcaWindow,
                                                   rgbwidget=rgbWidget,
                                                   primary=True)
                widget.notifyCloseEventToWidget(self)
                self.__imagingTool = id(widget)
                self._widgetDict[self.__imagingTool] = widget
                #w = StackSelector.StackSelector(self)
                #stack = w.getStack()
                widget.loadStack()
                widget.show()
            except IOError:
                widget = None
                del self._widgetDict[self.__imagingTool]
                self.__imagingTool = None
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                txt = "Input Output Error: %s" % (sys.exc_info()[1])
                msg.setInformativeText(txt)
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
            except Exception:
                widget = None
                del self._widgetDict[self.__imagingTool]
                self.__imagingTool = None
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                txt = "Error info = %s" % (sys.exc_info()[1])
                msg.setInformativeText(txt)
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
        else:
            widget = self._widgetDict[self.__imagingTool]
            if widget.isHidden():
                widget.show()
            widget.raise_()


    def customEvent(self, event):
        if hasattr(event, 'dict'):
            ddict = event.dict
            if 'event' in ddict:
                if ddict['event'] == "closeEventSignal":
                    if ddict['id'] in self._widgetDict:
                        if ddict['id'] == self.__imagingTool:
                            self.__imagingTool = None
                        del self._widgetDict[ddict['id']]

    def closeEvent(self, event):
        if __name__ == "__main__":
            app = qt.QApplication.instance()
            allWidgets = app.allWidgets()
            for widget in allWidgets:
                try:
                    # we cannot afford to crash here
                    if id(widget) != id(self):
                        if widget.parent() is None:
                            widget.close()
                except Exception:
                    _logger.debug("Error closing widget")
            from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
            PyMcaPrintPreview.resetSingletonPrintPreview()
        return PyMcaMdi.PyMcaMdi.closeEvent(self, event)

    def __xiaCorrect(self):
        qApp = qt.QApplication.instance()
        XiaCorrect.mainGUI(qApp)

    def _xrfmcPyMca(self):
        if self._xrfmcTool is None:
            self._xrfmcTool = XRFMCPyMca.XRFMCPyMca()
        self._xrfmcTool.show()
        self._xrfmcTool.raise_()

    def _sumRules(self):
        if self._sumRulesTool is None:
            self._sumRulesTool = SumRulesTool.SumRulesWindow()
        self._sumRulesTool.show()
        self._sumRulesTool.raise_()

    def onOpen(self):
        self.openMenu.exec(self.cursor().pos())

    def onSave(self):
        self._saveAs()

    def onSaveAs(self):
        index = self.mainTabWidget.currentIndex()
        text  = str(self.mainTabWidget.tabText(index))
        self.saveMenu = qt.QMenu()
        self.saveMenu.addAction("PyMca Configuration", self._onSaveAs)
        if text.upper() == 'MCA':
            self.saveMenu.addAction("Active Mca",
                             self.mcaWindow._saveIconSignal)
        elif text.upper() == 'SCAN':
            self.saveMenu.addAction("Active Scan",
                             self.scanWindow._saveIconSignal)
        elif text in self.imageWindowDict.keys():
            self.saveMenu.addAction("Active Image",
                  self.imageWindowDict[text].graphWidget._saveIconSignal)
        self.saveMenu.exec(self.cursor().pos())

    def _onSaveAs(self):
        cwd = os.getcwd()
        if os.path.exists(self.configDir):
            cwd = self.configDir

        outputFile = PyMcaFileDialogs.getFileList(self, filetypelist=['PyMca (*.ini)'],
                                                message="Provide output file",
                                                currentdir=cwd, mode="SAVE",
                                                getfilter=False, single=False,
                                                currentfilter=None, native=None)
        if not len(outputFile):
            return
        extension = ".ini"
        outputFile = outputFile[0]
        try:
            outputDir  = os.path.dirname(outputFile)
        except Exception:
            outputDir  = "."
        try:
            outputFile = os.path.basename(outputFile)
        except Exception:
            outputFile  = "PyMca.ini"

        #always overwrite for the time being
        if len(outputFile) < len(extension[:]):
            outputFile += extension[:]
        elif outputFile[-4:] != extension[:]:
            outputFile += extension[:]
        filename = os.path.join(outputDir, outputFile)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except IOError:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                txt = "Input Output Error: %s" % (sys.exc_info()[1])
                msg.setInformativeText(txt)
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
        try:
            self._saveAs(filename)
            self.configDir = outputDir
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error Saving Configuration: %s" % (sys.exc_info()[1]))
            msg.exec()
            return

    def _saveAs(self, filename=None):
        if filename is None:
            filename = PyMca5.getDefaultSettingsFile()
        self.saveConfig(self.getConfig(), filename)

    def loadTrainingData(self):
        if self.trainingDataMenu is None:
            self.trainingDataMenu = qt.QMenu()
            self.trainingSources = {"XRF Analysis": os.path.join(PyMcaDataDir.PYMCA_DATA_DIR, 'XRFSpectrum.mca'),
                        "Tertiary Excitation": os.path.join(PyMcaDataDir.PYMCA_DATA_DIR, 'Steel.spe')}
            self.trainingActions = []
            for key in ["XRF Analysis", "Tertiary Excitation"]:
                action = qt.QAction(key, None)
                self.trainingActions.append(action)
                self.trainingDataMenu.addAction(action)
        try:
            source = None
            selectedAction = self.trainingDataMenu.exec(qt.QCursor.pos())
            if selectedAction is not None:
                key = qt.safe_str(selectedAction.text())
                source = self.trainingSources[key]
                self.sourceWidget.sourceSelector.openSource(source)
                # only in case of the steel sample we set the input dir to simplify accessing the supplied cfg file
                if key in ["Tertiary Excitation"]:
                    # we do not change the input dir currently used by the source selector
                    #self.sourceWidget.sourceSelector.lastInputDir = os.path.dirname(source)
                    # but we change the input dir to allow easy loading of the config file from the
                    # fit configuration window
                    PyMcaDirs.inputDir = os.path.dirname(source)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Error opening data source")
            if source:
                msg.setText("Cannot open data source %s" % source)
            else:
                msg.setText("Cannot open data source")
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def openSource(self,index=0):
        _logger.debug("index = %d ", index)
        if index <= 0:
            if os.path.exists(self.configDir):
                currentdir = self.configDir
            else:
                currentdir = None
            filename = PyMcaFileDialogs.getFileList(parent=self,
                                                   filetypelist=['PyMca (*.ini)'],
                                                   message="Select PyMca Configuration File",
                                                   currentdir=currentdir,
                                                   mode="OPEN",
                                                   getfilter=False,
                                                   single=False,
                                                   currentfilter=None,
                                                   native=None)
            if not len(filename):
                return
            filename = filename[0]
            currentConfigDict = ConfigDict.ConfigDict()
            self.configDir  = os.path.dirname(filename)
            currentConfigDict.read(filename)
            self.setConfig(currentConfigDict)
            return
        else:
            index -= 1
        source = SOURCESLIST[index]
        if self.sourceFrame.isHidden():
            self.sourceFrame.show()
        self.sourceFrame.raise_()
        self.sourceBrowserTab.showPage(self.sourceWidget[source])
        qApp = qt.QApplication.instance()
        qApp.processEvents()
        self.sourceWidget[source].openFile()

    def onMenuHelp(self):
        if self.menuBrowser is None:
            self.menuBrowser= qt.QTextBrowser()
            self.menuBrowser.setWindowTitle(QString("Main Menu Help"))
            ddir=PyMcaDataDir.PYMCA_DOC_DIR
            if not os.path.exists(os.path.join(ddir,"HTML","Menu.html")):
                ddir = os.path.dirname(ddir)
            self.menuBrowser.setSearchPaths([os.path.join(ddir,"HTML")])
            self.menuBrowser.setSource(qt.QUrl(QString("Menu.html")))
            self.menuBrowser.show()
        if self.menuBrowser.isHidden():
            self.menuBrowser.show()
        self.menuBrowser.raise_()

    def onDisplayHowto(self):
        if self.displayBrowser is None:
            self.displayBrowser= qt.QTextBrowser()
            self.displayBrowser.setWindowTitle(QString("Data Display HOWTO"))
            ddir=PyMcaDataDir.PYMCA_DOC_DIR
            if not os.path.exists(os.path.join(ddir,"HTML","Display-HOWTO.html")):
                ddir = os.path.dirname(ddir)
            self.displayBrowser.setSearchPaths([os.path.join(ddir,"HTML")])
            self.displayBrowser.setSource(qt.QUrl(QString("Display-HOWTO.html")))
            self.displayBrowser.show()
        if self.displayBrowser.isHidden():
            self.displayBrowser.show()
        self.displayBrowser.raise_()

    def onMcaHowto(self):
        if self.mcaBrowser is None:
            self.mcaBrowser= MyQTextBrowser()
            self.mcaBrowser.setWindowTitle(QString("MCA HOWTO"))
            ddir=PyMcaDataDir.PYMCA_DOC_DIR
            if not os.path.exists(ddir+"/HTML"+"/MCA-HOWTO.html"):
                ddir = os.path.dirname(ddir)
            self.mcaBrowser.setSearchPaths([os.path.join(ddir,"HTML"),
                                            os.path.join(ddir,"HTML", "PyMCA_files"),
                                            os.path.join(ddir,"HTML", "images")])
            self.mcaBrowser.setSource(qt.QUrl(QString("MCA-HOWTO.html")))
            #f = open(os.path.join(dir,"HTML","MCA-HOWTO.html"))
            #self.mcaBrowser.setHtml(f.read())
            #f.close()
            self.mcaBrowser.show()
        if self.mcaBrowser.isHidden():
            self.mcaBrowser.show()
        self.mcaBrowser.raise_()

    def onAbout(self):
        qt.QMessageBox.about(self, "PyMca",
                "PyMca Application\nVersion: "+__version__)
        #self.onDebug()

    def onWebDocumentation(self):
        import webbrowser
        url = "http://www.silx.org/doc/PyMca/dev/"
        webbrowser.open(url)

    def onChanges(self):
        if self.changeLog is None:
            self.changeLog = qt.QTextEdit()
            self.changeLog.setCursor(self.cursor())
            self.changeLog.setWindowTitle("PyMCA %s Changes" % __version__)
            self.changeLog.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
            # Does this belong to the data dir or the doc dir?
            mpath = PyMcaDataDir.PYMCA_DATA_DIR
            fname = os.path.join(mpath,'changelog.txt')
            if not os.path.exists(fname):
               while len(mpath) > 3:
                 fname = os.path.join(mpath,'changelog.txt')
                 #print "looking for ", fname
                 if not os.path.exists(fname):
                     mpath = os.path.dirname(mpath)
                 else:
                     break
            if os.path.exists(fname):
                self.log = ChangeLog.ChangeLog(textfile='changelog.txt')
                self.changeLog.setDocument(self.log)
                self.changeLog.setMinimumWidth(500)
            else:
                self.log = ChangeLog.ChangeLog()
                self.log.setPlainText('Cannot find file changelog.txt')
        self.changeLog.show()

    def onDebug(self):
        if "PyQt5.QtCore" in sys.modules:
            _logger.debug("Module name PyQt  %s", qt.PYQT_VERSION_STR)
        for module in sys.modules.values():
            try:
                if 'Revision' in module.__revision__:
                    if module.__name__ != "__main__":
                        _logger.debug("Module name = %s, %s",
                                      module.__name__,
                                      module.__revision__.replace("$", ""))
            except Exception:
                pass

    def onPrint(self):
        _logger.debug("onPrint called")

        if not self.scanWindow.isHidden():
            self.scanWindow.printGraph()
            return

        if not self.__useTabWidget:
            self.mcaWindow.show()
            self.mcaWindow.raise_()
        else:
            self.mainTabWidget.setCurrentWidget(self.mcaWindow)
        self.mcaWindow.printGraph()

if 0:

    #
    # GraphWindow operations
    #
    def openGraph(self,name="MCA Graph"):
            """
            Creates a new GraphWindow on the MDI
            """
            self.setFollowActiveWindow(0)

            #name= self.__getNewGraphName()
            if name == "MCA Graph":
                graph = McaWindow.McaWindow(self.mdi, name=name)
            graph.windowClosed[()].connect(self.closeGraph)
            graph.show()

            if len(self.mdi.windowList())==1:
                    graph.showMaximized()
            else:   self.windowTile()

            self.setFollowActiveWindow(1)

    def getActiveGraph(self):
            """
            Return active GraphWindow instance or a new one
            """
            graph= self.mdi.activeWindow()
            if graph is None:
                    graph= self.openGraph()
            return graph

    def getGraph(self, name):
            """
            Return GraphWindow instance indexed by name
            Or None if not found
            """
            for graph in self.mdi.windowList():
                if qt.safe_str(graph.caption())== name:
                    return graph
            return None

    def closeGraph(self, name):
            """
            Called after a graph is closed
            """
            _logger.info("closeGraph", name)

    def __getGraphNames(self):
            return [ str(window.caption()) for window in self.mdi.windowList() ]


    def __getNewGraphName(self):
            names= self.__getGraphNames()
            idx= 0
            while "Graph %d"%idx in names:
                    idx += 1
            return "Graph %d"%(idx)

class MyQTextBrowser(qt.QTextBrowser):
    def myWrappedSource(self, name, ignored=None):
        if name == QString("./PyMCA.html") or ("PyMCA.html" in ("%s" % name)):
            if sys.platform == 'win32':
                ddir=PyMcaDataDir.PYMCA_DOC_DIR
                if not os.path.exists(os.path.join(ddir, "HTML", "PyMCA.html")):
                    ddir = os.path.dirname(ddir)
                cmd = os.path.join(ddir,"HTML", "PyMCA.pdf")
                os.system('"%s"' % cmd)
                return
            try:
                self.report.show()
            except Exception:
                self.report = qt.QTextBrowser()
                self.report.setCaption(QString("PyMca Report"))
                ddir=PyMcaDataDir.PYMCA_DOC_DIR
                self.report.mimeSourceFactory().addFilePath(QString(ddir+"/HTML"))
                self.report.mimeSourceFactory().addFilePath(QString(ddir+"/HTML/PyMCA_files"))
                self.report.setSource(name)
            if self.report.isHidden():
                self.report.show()
            self.report.raise_()
        else:
            if QTVERSION.startswith('6'):
                qt.QTextBrowser.doSetSource(self, name)
            else:
                qt.QTextBrowser.setSource(self, name)

    if QTVERSION.startswith('6'):
        def doSetSource(self, name, ignored=None):
            return self.myWrappedSource(name, ignored)
    else:
        def setSource(self, name):
            return self.myWrappedSource(name)

class Line(qt.QFrame):
    sigLineDoubleClickEvent = qt.pyqtSignal(object)
    def mouseDoubleClickEvent(self,event):
        _logger.debug("Double Click Event")
        ddict={}
        ddict['event']="DoubleClick"
        ddict['data'] = event
        self.sigLineDoubleClickEvent.emit(ddict)

class PixmapLabel(qt.QLabel):
    sigPixmapLabelMousePressEvent = qt.pyqtSignal(object)
    def mousePressEvent(self,event):
        _logger.debug("Mouse Press Event")
        ddict={}
        ddict['event']="MousePress"
        ddict['data'] = event
        self.sigPixmapLabelMousePressEvent.emit(ddict)

if __name__ == '__main__':
    PROFILING = 0
    if PROFILING:
        import profile
        import pstats
    PyMcaMainWidgetInstance = PyMcaMain(**keywords)
    if nativeFileDialogs is not None:
        PyMcaDirs.nativeFileDialogs = nativeFileDialogs
    if debugreport:
        PyMcaMainWidgetInstance.onDebug()
    app.lastWindowClosed.connect(app.quit)

    splash.finish(PyMcaMainWidgetInstance)
    PyMcaMainWidgetInstance.show()
    PyMcaMainWidgetInstance.raise_()
    PyMcaMainWidgetInstance.mcaWindow.replot()

    #try to interpret rest of command line arguments as data sources
    try:
        for source in args:
            PyMcaMainWidgetInstance.sourceWidget.sourceSelector.openSource(source)
    except Exception:
        msg = qt.QMessageBox(PyMcaMainWidgetInstance)
        msg.setIcon(qt.QMessageBox.Critical)
        msg.setWindowTitle("Error opening data source")
        msg.setText("Cannot open data source %s" % source)
        msg.setInformativeText(str(sys.exc_info()[1]))
        msg.setDetailedText(traceback.format_exc())
        msg.exec()

    if PROFILING:
        profile.run('sys.exit(app.exec())',"test")
        p=pstats.Stats("test")
        p.strip_dirs().sort_stats(-1).print_stats()
    else:
        ret = app.exec()
        app = None
        sys.exit(ret)

