#/*##########################################################################
# Copyright (C) 2004-2024 European Synchrotron Radiation Facility
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
import posixpath
import weakref
import gc
import h5py
import logging
_logger = logging.getLogger(__name__)

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaCore import NexusTools
safe_str = qt.safe_str

if hasattr(qt, 'QString'):
    QString = qt.QString
else:
    QString = str

from . import HDF5Widget
from . import NexusInfo
from . import HDF5CounterTable
from . import HDF5McaTable
from . import QNexusWidgetActions
try:
    from . import Hdf5NodeView
except Exception:
    # prevent crushing due to other silx-related errors
    _logger.info("Cannot use silx Hdf5NodeView")
    from . import HDF5DatasetTable
    Hdf5NodeView = None
try:
    from . import DataViewerSelector
    SINGLE_ENABLED = True
except Exception:
    _logger.debug("Cannot import DataViewerSelector")
    SINGLE_ENABLED = False
from PyMca5.PyMcaIO import ConfigDict
from PyMca5 import PyMcaDirs

class Buttons(qt.QWidget):

    sigButtonsSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, options=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.buttonGroup = qt.QButtonGroup(self)
        self.buttonList = []
        i = 0
        if options is None:
            optionList = ['SCAN', 'MCA']
        else:
            optionList = options
        actionList = ['ADD', 'REMOVE', 'REPLACE']
        for option in optionList:
            row = optionList.index(option)
            for action in actionList:
                col = actionList.index(action)
                button = qt.QPushButton(self)
                button.setText(action + " " + option)
                self.mainLayout.addWidget(button, row, col)
                self.buttonGroup.addButton(button)
                self.buttonList.append(button)
        if hasattr(self.buttonGroup, "idClicked"):
            self.buttonGroup.idClicked[int].connect(self.emitSignal)
        else:
            # deprecated
            _logger.debug("Using deprecated signal")
            self.buttonGroup.buttonClicked[int].connect(self.emitSignal)

    def emitSignal(self, idx):
        button = self.buttonGroup.button(idx)
        ddict={}
        ddict['event'] = 'buttonClicked'
        ddict['action'] = safe_str(button.text())
        self.sigButtonsSignal.emit(ddict)

class QNexusWidget(qt.QWidget):
    sigAddSelection = qt.pyqtSignal(object)
    sigRemoveSelection = qt.pyqtSignal(object)
    sigReplaceSelection = qt.pyqtSignal(object)
    sigOtherSignals = qt.pyqtSignal(object)
    def __init__(self, parent=None, mca=False, buttons=False):
        qt.QWidget.__init__(self, parent)
        self.data = None
        self._dataSourceList = []
        self._oldCntSelection = None
        self._cntList = []
        self._aliasList = []
        self._shapeList = []
        self._autoCntList = []
        self._autoAliasList = []
        self._defaultModel = HDF5Widget.FileModel()
        self.getInfo = NexusInfo.getInfo
        self._modelDict = {}
        self._widgetDict = {}
        self._lastWidgetId = None
        self._dir = None
        self._lastAction = None
        self._lastEntry = None
        self._lastMcaSelection = None
        self._lastCntSelection = None
        self._mca = mca
        self._BUTTONS = buttons
        self.build()

    def sizeHint(self):
        originalHint = qt.QWidget.sizeHint(self)
        if isinstance(self.parent(), qt.QDialog):
            return qt.QSize(2 * originalHint.width(),
                            originalHint.height())
        else:
            return qt.QSize(originalHint.width(),
                            originalHint.height())
    def build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(5, 5, 5, 0)
        self.splitter = qt.QSplitter(self)
        self.splitter.setOrientation(qt.Qt.Vertical)
        self.hdf5Widget = HDF5Widget.HDF5Widget(self._defaultModel,
                                                self.splitter)
        self.hdf5Widget.setExpandsOnDoubleClick(False)
        self.hdf5Widget.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)
        self.tableTab = qt.QTabWidget(self.splitter)
        self.tableTab.setContentsMargins(0, 0, 0, 0)
        self.cntTable = HDF5CounterTable.HDF5CounterTable(self.tableTab)
        self.autoTable = HDF5CounterTable.HDF5CounterTable(self.tableTab)
        self.tableTabOrder = ["AUTO", "USER", "MCA"]
        self.tableTab.addTab(self.autoTable, "AUTO")
        self.tableTab.addTab(self.cntTable, "USER")
        if self._mca:
            self.mcaTable = HDF5McaTable.HDF5McaTable(self.tableTab)
            self.tableTab.addTab(self.mcaTable, "MCA")
        self.mainLayout.addWidget(self.splitter)
        #Enable 3D
        BUTTONS = self._BUTTONS
        if BUTTONS:
            if ('PyMca5.PyMcaGui.pymca.SilxGLWindow' in sys.modules) or \
               ('PyMca5.PyMca.SilxGLWindow' in sys.modules):
                self.buttons = Buttons(self, options=['SCAN', 'MCA', '2D', '3D'])
                self.cntTable.set3DEnabled(True)
                self.autoTable.set3DEnabled(True)
            else:
                self.buttons = Buttons(self, options=['SCAN', 'MCA', '2D'])
                self.cntTable.set3DEnabled(False)
                self.autoTable.set3DEnabled(False)
            if self._mca:
                self.tableTab.removeTab(2)
            self.tableTab.removeTab(0)
            self.mainLayout.addWidget(self.buttons)
        else:
            self.actions = QNexusWidgetActions.QNexusWidgetActions(self)
            if ('PyMca5.PyMcaGui.pymca.SilxGLWindow' in sys.modules) or \
               ('PyMca5.PyMca.SilxGLWindow' in sys.modules):
                self.actions.set3DEnabled(True)
            else:
                self.actions.set3DEnabled(False)
            self.cntTable.set2DEnabled(False)
            self.autoTable.set2DEnabled(False)
            self.mainLayout.addWidget(self.actions)
        self.hdf5Widget.sigHDF5WidgetSignal.connect(self.hdf5Slot)
        self.cntTable.customContextMenuRequested[qt.QPoint].connect(\
                        self._counterTableCustomMenuSlot)

        if BUTTONS:
            self.buttons.sigButtonsSignal.connect(self.buttonsSlot)
        else:
            self.actions.sigAddSelection.connect(self._addAction)
            self.actions.sigRemoveSelection.connect(self._removeAction)
            self.actions.sigReplaceSelection.connect(self._replaceAction)
            self.actions.sigActionsConfigurationChanged.connect(\
                self._configurationChangedAction)
            self.autoTable.sigHDF5CounterTableSignal.connect(\
                                    self._autoTableUpdated)
            self.cntTable.sigHDF5CounterTableSignal.connect(\
                                    self._userTableUpdated)
            if self._mca:
                self.mcaTable.sigHDF5McaTableSignal.connect(\
                                    self._mcaTableUpdated)

        # Some convenience functions to customize the table
        # They could have been included in other class inheriting
        # this one.
        self.cntTable.setContextMenuPolicy(qt.Qt.CustomContextMenu)

        self._cntTableMenu = qt.QMenu(self)
        self._cntTableMenu.addAction(QString("Load"),
                                    self._loadCounterTableConfiguration)
        self._cntTableMenu.addAction(QString("Merge"),
                                    self._mergeCounterTableConfiguration)
        self._cntTableMenu.addAction(QString("Save"),
                                    self._saveCounterTableConfiguration)
        self._cntTableMenu.addSeparator()
        self._cntTableMenu.addAction(QString("Delete All"),
                                    self._deleteAllCountersFromTable)
        self._cntTableMenu.addAction(QString("Delete Selected"),
                                    self._deleteSelectedCountersFromTable)

    def _counterTableCustomMenuSlot(self, qpoint):
        self.getWidgetConfiguration()
        self._cntTableMenu.exec(qt.QCursor.pos())

    def _getConfigurationFromFile(self, fname):
        ddict = ConfigDict.ConfigDict()
        ddict.read(fname)

        keys = ddict.keys
        if 'PyMca' in keys():
            ddict = ddict['PyMca']

        if 'HDF5' not in ddict.keys():
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("File does not contain HDF5 configuration")
            msg.exec()
            return None

        if 'WidgetConfiguration' not in ddict['HDF5'].keys():
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("File does not contain HDF5 WidgetConfiguration")
            msg.exec()
            return None

        ddict =ddict['HDF5']['WidgetConfiguration']
        keys = ddict.keys()

        if ('counters' not in keys) or\
           ('aliases' not in keys):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("File does not contain HDF5 counters information")
            msg.exec()
            return None

        if len(ddict['counters']) != len(ddict['aliases']):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Number of counters does not match number of aliases")
            msg.exec()
            return None

        return ddict


    def _loadCounterTableConfiguration(self):
        fname = self.getInputFilename()
        if not len(fname):
            return

        ddict = self._getConfigurationFromFile(fname)
        if ddict is not None:
            if "shapes" not in ddict:
                ddict["shapes"] = [None,] * len(ddict["counters"])
            elif not hasattr(ddict["shapes"], "__len__"):
                ddict["shapes"] = [ddict["shapes"]]
            elif len(ddict["shapes"]) != len(ddict["counters"]):
                ddict["shapes"] = [ddict["shapes"]]
            assert len(ddict["shapes"]) == len(ddict["counters"])
            self.setWidgetConfiguration(ddict)

    def _mergeCounterTableConfiguration(self):
        fname = self.getInputFilename()
        if not len(fname):
            return

        ddict = self._getConfigurationFromFile(fname)
        if ddict is None:
            return

        current = self.getWidgetConfiguration()
        cntList = ddict['counters']
        aliasList = ddict['aliases']
        shapeList = ddict['shapes']
        for i in range(len(cntList)):
            cnt = cntList[i]
            if cnt not in current['counters']:
                current['counters'].append(cnt)
                current['aliases'].append(aliasList[i])
                current['shapes'].append(shapeList[i])

        self.setWidgetConfiguration(current)

    def _saveCounterTableConfiguration(self):
        fname = self.getOutputFilename()
        if not len(fname):
            return
        if not fname.endswith('.ini'):
            fname += '.ini'

        ddict = ConfigDict.ConfigDict()
        if "PyMcaDirs" in sys.modules:
            ddict['PyMca'] = {}
            ddict['PyMca']['HDF5'] = {'WidgetConfiguration':\
                                      self.getWidgetConfiguration()}
        else:
            ddict['HDF5'] ={'WidgetConfiguration':\
                             self.getWidgetConfiguration()}
        _logger.debug("TODO - Add selection options")
        ddict.write(fname)

    def _deleteAllCountersFromTable(self):
        current = self.cntTable.getCounterSelection()
        current['x'] = []
        current['y'] = []
        current['m'] = []
        self.cntTable.setCounterSelection(current)
        self.setWidgetConfiguration(None)

    def _deleteSelectedCountersFromTable(self):
        itemList = self.cntTable.selectedItems()
        _logger.debug("Selected items = %s" % itemList)
        rowList = []
        for item in itemList:
            row = item.row()
            if row not in rowList:
                rowList.append(row)

        rowList.sort()
        rowList.reverse()
        current = self.cntTable.getCounterSelection()
        _logger.debug("current = %s" % current)
        for row in rowList:
            for key in ['x', 'y', 'm']:
                if row in current[key]:
                    idx = current[key].index(row)
                    del current[key][idx]

        ddict = {}
        ddict['counters'] = []
        ddict['aliases'] = []
        ddict['shapes'] = []
        for i in range(self.cntTable.rowCount()):
            if i not in rowList:
                #name = safe_str(self.cntTable.item(i, 0).text())
                #alias = safe_str(self.cntTable.item(i, 4).text())
                ddict['counters'].append(current["cntlist"][i])
                ddict['aliases'].append(current["aliaslist"][i])
                ddict['shapes'].append(current["shapelist"][i])

        for i in rowList:
            del current['cntlist'][i]
            del current['aliaslist'][i]
            del current['shapelist'][i]

        self.setWidgetConfiguration(ddict)
        self.cntTable.setCounterSelection(current)

    def getInputFilename(self):
        if self._dir is None:
            inidir = PyMcaDirs.inputDir
        else:
            inidir = self._dir

        if not os.path.exists(inidir):
            inidir = os.getcwd()

        fileList = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=["ini files (*.ini)"],
                                                message="Select a .ini file",
                                                currentdir=inidir,
                                                mode="OPEN",
                                                getfilter=False)

        if len(fileList):
            ret = fileList[0]
        else:
            ret = ""

        if len(ret):
            self._dir = os.path.dirname(ret)
            PyMcaDirs.inputDir = os.path.dirname(ret)
        return ret

    def getOutputFilename(self):
        if self._dir is None:
            inidir = PyMcaDirs.outputDir
        else:
            inidir = self._dir

        if not os.path.exists(inidir):
            inidir = os.getcwd()

        fileList = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=["ini files (*.ini)"],
                                                message="Select a .ini file",
                                                currentdir=inidir,
                                                mode="SAVE",
                                                getfilter=False)
        if len(fileList):
            ret = fileList[0]
        else:
            ret = ""

        if len(ret):
            self._dir = os.path.dirname(ret)
            PyMcaDirs.outputDir = os.path.dirname(ret)
        return ret

    def getWidgetConfiguration(self):
        cntSelection = self.cntTable.getCounterSelection()
        if hasattr(self, "actions"):
            ddict =self.actions.getConfiguration()
        else:
            ddict = {}
        ddict['counters'] = cntSelection['cntlist']
        ddict['aliases'] = cntSelection['aliaslist']
        ddict['shapes'] = cntSelection['shapelist']
        return ddict

    def setWidgetConfiguration(self, ddict=None):
        _logger.debug("setWidgetConfiguration %s" % ddict)
        if ddict is None:
            self._cntList = []
            self._aliasList = []
            self._shapeList = []
        elif "counters" in ddict and len(ddict["counters"]):
            self._cntList = ddict['counters']
            self._aliasList = ddict['aliases']
            if type(self._cntList) == type(""):
                self._cntList = [ddict['counters']]
            if type(self._aliasList) == type(""):
                self._aliasList = [ddict['aliases']]
            if 'shapes' in ddict:
                self._shapeList = ddict['shapes']
            else:
                self._shapeList = [None,] * len(self._cntList)
        self.cntTable.build(self._cntList, self._aliasList, shapelist=self._shapeList)
        if hasattr(self, "actions"):
            if hasattr(self.actions, "setConfiguration"):
                self.actions.setConfiguration(ddict)

    def setDataSource(self, dataSource):
        self.data = dataSource
        if self.data is None:
            self.hdf5Widget.collapseAll()
            self.hdf5Widget.setModel(self._defaultModel)
            return
        def dataSourceDestroyed(weakrefReference):
            idx = self._dataSourceList.index(weakrefReference)
            del self._dataSourceList[idx]
            del self._modelDict[weakrefReference]
            return
        ref = weakref.ref(dataSource, dataSourceDestroyed)
        if ref not in self._dataSourceList:
            self._dataSourceList.append(ref)
            self._modelDict[ref] = HDF5Widget.FileModel()
        model = self._modelDict[ref]
        self.hdf5Widget.setModel(model)
        for source in self.data._sourceObjectList:
            self.hdf5Widget.model().appendPhynxFile(source, weakreference=True)
        if len(self.data._sourceObjectList) == 1:
            # only one file, expand by default
            if hasattr(self.hdf5Widget, "expandToDepth"):
                self.hdf5Widget.expandToDepth(0)

    def setFile(self, filename):
        self._data = self.hdf5Widget.model().openFile(filename, weakreference=True)

    def showInfoWidget(self, filename, name, dset=False):
        # delete references to all the closed widgets
        self._checkWidgetDict()

        # we can use the existing instance or a new one
        # the former solution seems more robust
        if 1:
            useInstance = True
        else:
            if h5py.version.version < '2.0':
                useInstance = True
            else:
                useInstance = False
        if useInstance:
            fileIndex = self.data.sourceName.index(filename)
            phynxFile  = self.data._sourceObjectList[fileIndex]
        else:
            phynxFile  = HDF5Widget.h5open(filename)

        info = self.getInfo(phynxFile, name)
        nxclass = phynxFile[name].attrs.get("NX_class")
        widget = NexusInfo.NexusInfoWidget(nxclass=nxclass)
        widget.notifyCloseEventToWidget(self)
        title = os.path.basename(filename)
        title += " %s" % name
        widget.setWindowTitle(title)
        wid = id(widget)
        if self._lastWidgetId is not None:
            try:
                width = self._widgetDict[self._lastWidgetId].width()
                height = self._widgetDict[self._lastWidgetId].height()
                widget.resize(max(150, width), max(150, height))
            except Exception:
                pass
        self._lastWidgetId = wid
        self._widgetDict[wid] = widget
        if useInstance:
            def sourceObjectDestroyed(weakrefReference):
                if wid == self._lastWidgetId:
                    self._lastWidgetId = None
                if wid in self._widgetDict:
                    del self._widgetDict[wid]
            widget._sourceObjectWeakReference = weakref.ref(phynxFile,
                                                 sourceObjectDestroyed)

        widget.setInfoDict(info)
        # todo: this first `if` block can be dropped when silx is a hard dependency
        if dset and Hdf5NodeView is None:
            dataset = phynxFile[name]
            if isinstance(dataset, h5py.Dataset):
                if len(dataset.shape):
                    #0 length datasets do not need a table
                    widget.w = HDF5DatasetTable.HDF5DatasetTable(widget)
                    try:
                        widget.w.setDataset(dataset)
                    except Exception:
                        _logger.error("Error filling table")
                    widget.addTab(widget.w, 'DataView')
                    widget.setCurrentWidget(widget.w)
        elif Hdf5NodeView is not None:
            data = phynxFile[name]
            widget.w = Hdf5NodeView.Hdf5NodeView(widget)
            widget.w.setData(data)
            widget.addTab(widget.w, 'DataView')
            widget.setCurrentWidget(widget.w)
        widget.show()
        return widget

    def itemRightClickedSlot(self, ddict):
        _hdf5WidgetDatasetMenu = qt.QMenu(self)
        self._lastItemDict = ddict
        if ddict['dtype'].startswith('|S') or ddict['dtype'] == '' or \
           ddict['dtype'].startswith('object'):
            # handle a right click on a group or a dataset of string type
            _hdf5WidgetDatasetMenu.addAction(QString("Show Information"),
                                             self._showInfoWidgetSlot)
            _hdf5WidgetDatasetMenu.addAction(QString("Copy Path to Clipboard"),
                                             self._copyPathSlot)
            _hdf5WidgetDatasetMenu.exec(qt.QCursor.pos())
        else:
            #handle a right click on a numeric dataset
            _hdf5WidgetDatasetMenu.addAction(QString("Add to selection table"),
                                             self._addToSelectionTable)

            if 0:
                #these two options can be combined into one for the time being
                _hdf5WidgetDatasetMenu.addAction(QString("Open"),
                                                 self._openDataset)
                _hdf5WidgetDatasetMenu.addAction(QString("Show Properties"),
                                                 self._showDatasetProperties)
            else:
                _hdf5WidgetDatasetMenu.addAction(QString("Show Information"),
                                                 self._showInfoWidgetSlot)
                _hdf5WidgetDatasetMenu.addAction(QString("Copy Path to Clipboard"),
                                             self._copyPathSlot)
                _hdf5WidgetDatasetMenu.exec(qt.QCursor.pos())
        self._lastItemDict = None
        return

    def _addToSelectionTable(self, ddict=None):
        if ddict is None:
            ddict = self._lastItemDict
        #handle as a double click
        ddict['event'] = "itemDoubleClicked"
        self.hdf5Slot(ddict)

    def _showInfoWidgetSlot(self, ddict=None):
        if ddict is None:
            ddict = self._lastItemDict
        is_numeric_dataset = (not ddict['dtype'].startswith('|S') and not
                              ddict['dtype'].startswith('|U') and not
                              ddict['dtype'].startswith('|O') and not
                              ddict['dtype'] == '')
        return self.showInfoWidget(ddict['file'],
                                   ddict['name'],
                                   dset=is_numeric_dataset)

    def _copyPathSlot(self, ddict=None):
        if ddict is None:
            ddict = self._lastItemDict
        try:
            clipboard = qt.QApplication.clipboard()
            clipboard.setText(ddict["name"])
        except Exception:
            _logger.warning("Unsuccessful copy to clipboard")

    def _openDataset(self, ddict=None):
        if ddict is None:
            ddict = self._lastItemDict
        filename = ddict['file']
        name = ddict['name']
        self._checkWidgetDict()
        fileIndex = self.data.sourceName.index(filename)
        phynxFile  = self.data._sourceObjectList[fileIndex]
        dataset = phynxFile[name]
        if Hdf5NodeView is not None:
            widget = Hdf5NodeView.Hdf5NodeView()
            widget.setData(dataset)
        else:
            widget = HDF5DatasetTable.HDF5DatasetTable()
            widget.setDataset(dataset)
        title = os.path.basename(filename)
        title += " %s" % name
        widget.setWindowTitle(title)
        if self._lastWidgetId is not None:
            ids = self._widgetDict.keys()
            if len(ids):
                if self._lastWidgetId in ids:
                    try:
                        width = self._widgetDict[self._lastWidgetId].width()
                        height = self._widgetDict[self._lastWidgetId].height()
                        widget.resize(max(150, width), max(300, height))
                    except Exception:
                        pass
                else:
                    try:
                        width = self._widgetDict[ids[-1]].width()
                        height = self._widgetDict[ids[-1]].height()
                        widget.resize(max(150, width), max(300, height))
                    except Exception:
                        pass
        widget.notifyCloseEventToWidget(self)
        wid = id(widget)
        self._lastWidgetId = wid
        self._widgetDict[wid] = widget
        widget.show()

    def _showDatasetProperties(self, ddict=None):
        if ddict is None:
            ddict = self._lastItemDict
        filename = ddict['file']
        name = ddict['name']
        return self.showInfoWidget(filename, name)

    def _isNumericType(self, dtype):
        if dtype.startswith('|S') or dtype.startswith('|U') or \
           dtype.startswith('|O') or dtype.startswith('object'):
            return False
        else:
            return True

    def _isNumeric(self, hdf5item):
        if hasattr(hdf5item, "dtype"):
            dtype = safe_str(hdf5item.dtype)
            return self._isNumericType(dtype)
        else:
            return False

    def hdf5Slot(self, ddict):
        _logger.debug("hdf5Slot %s" % ddict)
        entryName = NexusTools.getEntryName(ddict['name'])
        currentEntry = "%s::%s" % (ddict['file'], entryName)
        if (currentEntry != self._lastEntry) and not self._BUTTONS:
            self._lastEntry = None
            cntList = []
            cntShapeList = []
            aliasList = []
            measurement = None
            scanned = []
            scannedShapeList = []
            mcaList = []
            mcaShapeList = []
            if posixpath.dirname(entryName) != entryName:
                h5file = HDF5Widget.h5open(ddict['file'])
                try:
                    measurement = NexusTools.getMeasurementGroup(h5file,
                                                                 ddict['name'])
                    scanned = NexusTools.getScannedPositioners(h5file,
                                                               ddict['name'])
                    if measurement is not None:
                        measurementDatasets = [item for key,item in measurement.items() \
                                       if self._isNumeric(item)]
                        measurement = [item.name for key,item in measurement.items() \
                                       if self._isNumeric(item)]
                        try:
                            # case insensitive sorting of measurement
                            if sys.version_info > (3, 3):
                                measurement.sort(key=str.casefold)
                        except Exception:
                            _logger.error("Cannot apply sorting %s" % sys.exc_info()[1])
                        nmeasurement = len(measurement)
                        cntShapeList = [None] * nmeasurement
                        for item in measurementDatasets:
                            if item.name in measurement:
                                idx = measurement.index(item.name)
                                if hasattr(item, "shape"):
                                    shape = item.shape
                                else:
                                    shape = (0,)
                                cntShapeList[idx] = shape
                    if self._mca:
                        mcaList = NexusTools.getMcaList(h5file, entryName)
                        mcaShapeList = []
                        for mca in mcaList:
                            try:
                                dataset = h5file[mca]
                            except KeyError:
                                dataset = h5file[NexusTools.sanitizeFilePath(h5file, 
                                                                             mca,
                                                                             entry=entryName)]
                            if hasattr(dataset, "shape"):
                                mcaShapeList.append(dataset.shape)
                            else:
                                mcaShapeList.append((0,))
                    if scanned:
                        scannedShapeList = []
                        for itemName in scanned:
                            try:
                                dataset = h5file[itemName]
                            except KeyError:
                                newItemName = NexusTools.sanitizeFilePath(h5file,
                                                                         itemName,
                                                                         entry=entryName)
                                dataset = h5file[newItemName]
                            if hasattr(dataset, "shape"):
                                scannedShapeList.append(dataset.shape)
                            else:
                                scannedShapeList.append((0,))
                finally:
                    h5file.close()
                    h5file = None
                    del h5file
            self._autoCntList = []
            self._autoCntShapeList = []
            for i in range(len(scanned)):
                key = scanned[i]
                self._autoCntList.append(key)
                self._autoCntShapeList.append(scannedShapeList[i])
                aliasList.append(posixpath.basename(key))

            if measurement is not None:
                for i in range(len(measurement)):
                    key = measurement[i]
                    if key not in self._autoCntList:
                        self._autoCntList.append(key)
                        self._autoCntShapeList.append(cntShapeList[i])
                        aliasList.append(posixpath.basename(key))

            cleanedCntList = []
            for key in self._autoCntList:
                root = key.split('/')
                root = "/" + root[1]
                if len(key) == len(root):
                    cleanedCntList.append(key)
                else:
                    cleanedCntList.append(key[len(root):])

            self._autoAliasList = aliasList

            self._autoCntList = cleanedCntList

            _logger.info("building autoTable")

            self.autoTable.build(self._autoCntList,
                                 self._autoAliasList,
                                 selection=self._lastCntSelection,
                                 shapelist=self._autoCntShapeList)
            currentTab = qt.safe_str(self.tableTab.tabText( \
                                    self.tableTab.currentIndex()))
            if self._mca:
                mcaAliasList = []
                cleanedMcaList = []
                for key in mcaList:
                    root = key.split('/')
                    root = "/" + root[1]
                    if len(key) == len(root):
                        cleanedMcaList.append(key)
                    else:
                        cleanedMcaList.append(key[len(root):])
                    mcaAliasList.append(posixpath.basename(key))
                self.mcaTable.build(cleanedMcaList, mcaAliasList, mcaShapeList)
                nTabs = self.tableTab.count()
                if (len(mcaList) > 0) and (nTabs < 3):
                    self.tableTab.insertTab(2, self.mcaTable, "MCA")
                elif (len(mcaList)==0) and (nTabs > 2):
                    self.tableTab.removeTab(2)
            _logger.debug("currentTab = %s", currentTab)
            if currentTab not in ["USER", "AUTO"]:
                if (len(mcaList) > 0) and (len(cntList) == 0):
                    idx = self.tableTabOrder.index("MCA")
                    self.tableTab.setCurrentIndex(idx)
                    _logger.debug("setting tab = %s MCA", idx)
                elif (len(mcaList) == 0) and (len(cntList) > 0):
                    idx = self.tableTabOrder.index("AUTO")
                    self.tableTab.setCurrentIndex(idx)
                    _logger.debug("setting tab = %s AUTO", idx)
            self._lastEntry = currentEntry
        if ddict['event'] == 'itemClicked':
            if ddict['mouse'] == "right":
                return self.itemRightClickedSlot(ddict)
            if ddict['mouse'] == "left":
                # If parent is root do it even if not NXentry??
                if ddict['type'] in ['NXentry', 'Entry']:
                    if not self._BUTTONS:
                        auto = self.actions.getConfiguration()["auto"]
                        if auto == "ADD":
                            self._addAction()
                        elif auto == "REPLACE":
                            self._replaceAction()
        if ddict['event'] == "itemDoubleClicked":
            if ddict['type'] in ['Dataset', "TiledDataset"]:
                currentIndex = self.tableTab.currentIndex()
                text = safe_str(self.tableTab.tabText(currentIndex))
                if text.upper() != "USER":
                    if currentIndex == 0:
                        self.tableTab.setCurrentIndex(1)
                    else:
                        self.tableTab.setCurrentIndex(0)
                if not self._isNumericType(ddict['dtype']):
                    _logger.debug("string like %s", ddict['dtype'])
                else:
                    root = ddict['name'].split('/')
                    root = "/" + root[1]
                    if len(ddict['name']) == len(root):
                        cnt = ddict['name']
                    else:
                        cnt  = ddict['name'][len(root):]
                    if cnt not in self._cntList:
                        self._cntList.append(cnt)
                        basename = posixpath.basename(cnt)
                        if basename not in self._aliasList:
                            self._aliasList.append(basename)
                        else:
                            self._aliasList.append(cnt)
                        if 'shape' in ddict and 'x' in ddict['shape']:
                            shape = [int(item) for item in ddict['shape'].split('x')]
                        else:
                            shape = None
                        self._shapeList.append(shape)
                        self.cntTable.build(self._cntList, self._aliasList, shapelist=self._shapeList)
            elif ddict.get('_isLink', False) and ("silx" in sys.modules):
                # there is an action to be applied
                self.showInfoWidget(ddict["file"], ddict["name"], dset=False)
            elif ddict['type'] in ['NXentry', 'Entry']:
                if self._lastAction is None:
                    return
                action, selectionType = self._lastAction.split()
                if action == 'REMOVE':
                    action = 'ADD'
                ddict['action'] = "%s %s" % (action, selectionType)
                self.buttonsSlot(ddict)
            else:
                if self.data is not None:
                    name = ddict['name']
                    filename = ddict['file']
                    fileIndex = self.data.sourceName.index(filename)
                    phynxFile  = self.data._sourceObjectList[fileIndex]
                    dataset = phynxFile[name]
                    if isinstance(dataset, h5py.Dataset):
                        root = ddict['name'].split('/')
                        root = "/" + root[1]
                        cnt  = ddict['name'].split(root)[-1]
                        if cnt not in self._cntList:
                            _logger.debug("USING SECOND WAY")
                            self._cntList.append(cnt)
                            basename = posixpath.basename(cnt)
                            if basename not in self._aliasList:
                                self._aliasList.append(basename)
                            else:
                                self._aliasList.append(cnt)
                            try:
                                self._shapeList.append(dataset.shape)
                            except Exception:
                                self._shapeList.append(None)
                            self.cntTable.build(self._cntList, self._aliasList, shapelist=self._shapeList)
                        return
                _logger.debug("Unhandled item type: %s", ddict['dtype'])


    def _addMcaAction(self):
        _logger.debug("_addMcaAction received")
        self.mcaAction("ADD")

    def _removeMcaAction(self):
        _logger.debug("_removeMcaAction received")
        self.mcaAction("REMOVE")

    def _replaceMcaAction(self):
        _logger.debug("_replaceMcaAction received")
        self.mcaAction("REPLACE")

    def mcaAction(self, action="ADD"):
        _logger.debug("mcaAction %s", action)
        self.mcaTable.getMcaSelection()
        ddict = {}
        ddict['action'] = "%s MCA" % action
        self.buttonsSlot(ddict, emit=True)

    def _addAction(self):
        _logger.debug("_addAction received")
        # formerly we had action and selection type
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "MCA":
            self._addMcaAction()
        else:
            ddict = {}
            mca = self.actions.getConfiguration()["mca"]
            if mca:
                ddict['action'] = "ADD MCA"
            else:
                ddict['action'] = "ADD SCAN"
            self.buttonsSlot(ddict, emit=True)

    def _removeAction(self):
        _logger.debug("_removeAction received")
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "MCA":
            self._removeMcaAction()
        else:
            ddict = {}
            mca = self.actions.getConfiguration()["mca"]
            if mca:
                ddict['action'] = "REMOVE MCA"
            else:
                ddict['action'] = "REMOVE SCAN"
            self.buttonsSlot(ddict, emit=True)

    def _replaceAction(self):
        _logger.debug("_replaceAction received")
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "MCA":
            self._replaceMcaAction()
        else:
            ddict = {}
            mca = self.actions.getConfiguration()["mca"]
            if mca:
                ddict['action'] = "REPLACE MCA"
            else:
                ddict['action'] = "REPLACE SCAN"
            self.buttonsSlot(ddict, emit=True)

    def _configurationChangedAction(self, ddict):
        _logger.debug("_configurationChangedAction received %s", ddict)
        if ddict["3d"]:
            self.autoTable.set3DEnabled(True, emit=False)
            self.cntTable.set3DEnabled(True, emit=False)
        elif ddict["2d"]:
            self.autoTable.set2DEnabled(True, emit=False)
            self.cntTable.set2DEnabled(True, emit=False)
        else:
            self.autoTable.set2DEnabled(False, emit=False)
            self.cntTable.set2DEnabled(False, emit=False)

    def _autoTableUpdated(self, ddict):
        _logger.debug("_autoTableUpdated(self, ddict) %s", ddict)
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "AUTO":
            actions = self.actions.getConfiguration()
            if len(self.autoTable.getCounterSelection()['y']):
                if actions["auto"] == "ADD":
                    self._addAction()
                elif actions["auto"] == "REPLACE":
                    self._replaceAction()

    def _userTableUpdated(self, ddict):
        _logger.debug("_userTableUpdated(self, ddict) %s", ddict)
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "USER":
            actions = self.actions.getConfiguration()
            if len(self.cntTable.getCounterSelection()['y']):
                if actions["auto"] == "ADD":
                    self._addAction()
                elif actions["auto"] == "REPLACE":
                    self._replaceAction()

    def _mcaTableUpdated(self, ddict):
        _logger.debug("_mcaTableUpdated(self, ddict) %s", ddict)
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        if text.upper() == "MCA":
            actions = self.actions.getConfiguration()
            if len(self.mcaTable.getMcaSelection()['selectionindex']):
                if actions["auto"] == "ADD":
                    self._addAction()
                elif actions["auto"] == "REPLACE":
                    self._replaceAction()

    def buttonsSlot(self, ddict, emit=True):
        _logger.debug("buttonsSlot(self, %s,emit=%s)", ddict, emit)
        if self.data is None:
            return
        action, selectionType = ddict['action'].split()
        entryList = self.getSelectedEntries()
        if not len(entryList):
            return
        text = qt.safe_str(self.tableTab.tabText(self.tableTab.currentIndex()))
        mcaSelection = {'mcalist':[], 'selectionindex':[]}
        cntSelection = {'cntlist':[], 'y':[]}
        if text.upper() == "AUTO":
            cntSelection = self.autoTable.getCounterSelection()
            # self._aliasList = cntSelection['aliaslist']
        elif text.upper() == "MCA":
            mcaSelection = self.mcaTable.getMcaSelection()
        else:
            cntSelection = self.cntTable.getCounterSelection()
            self._aliasList = cntSelection['aliaslist']
        selectionList = []
        for entry, filename in entryList:
            if not len(cntSelection['cntlist']) and \
               not len(mcaSelection['mcalist']):
                continue
            if not len(cntSelection['y']) and \
               not len(mcaSelection['selectionindex']):
                #nothing to plot
                continue
            mcaIdx = 0
            if filename not in self.data.sourceName:
                if ("tiled:" + filename) in self.data.sourceName:
                    filename = "tiled:" + filename 

            for yMca in mcaSelection['selectionindex']:
                sel = {}
                sel['SourceName'] = self.data.sourceName * 1
                sel['SourceType'] = "HDF5"
                fileIndex = self.data.sourceName.index(filename)
                phynxFile  = self.data._sourceObjectList[fileIndex]
                entryIndex = list(phynxFile["/"].keys()).index(entry[1:])
                sel['Key']        = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['legend']     = os.path.basename(filename)+\
                                    " " + posixpath.basename(entry) #it was sel['Key']
                sel['selection'] = {}
                sel['selection']['sourcename'] = filename
                #deal with the case the "entry" is a dataset hunging at root level
                if isinstance(phynxFile[entry], h5py.Dataset):
                    entry = "/"
                sel['selection']['entry'] = entry
                sel['selection']['key'] = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['selection']['mca'] = [yMca]
                sel['selection']['mcaselectiontype'] = mcaSelection['selectiontype'][mcaIdx]
                sel['legend'] += " " + mcaSelection['aliaslist'][yMca] + \
                                 " " + sel['selection']['mcaselectiontype']
                mcaIdx += 1
                sel['selection']['mcalist'] = mcaSelection['mcalist']
                sel['selection']['LabelNames'] = mcaSelection['aliaslist']
                #sel['selection']['aliaslist'] = cntSelection['aliaslist']
                sel['selection']['selectiontype'] = "MCA"
                sel['mcaselection']  = True
                aliases = mcaSelection['aliaslist']
                selectionList.append(sel)

            for yCnt in cntSelection['y']:
                sel = {}
                sel['SourceName'] = self.data.sourceName * 1
                sel['SourceType'] = "HDF5"
                fileIndex = self.data.sourceName.index(filename)
                phynxFile  = self.data._sourceObjectList[fileIndex]
                if entry == "/":
                    entryIndex = 1
                else:
                    entryIndex = list(phynxFile["/"].keys()).index(entry[1:])
                sel['Key']        = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['legend']     = os.path.basename(filename)+\
                                    " " + posixpath.basename(entry) #it was sel['Key']
                sel['selection'] = {}
                sel['selection']['sourcename'] = filename
                #deal with the case the "entry" is a dataset hunging at root level
                if isinstance(phynxFile[entry], h5py.Dataset):
                    _logger.info("HDF5 dataset at root level")
                    entry = "/"
                elif hasattr(phynxFile[entry], "shape"):
                    # HDF5-like dataset at top level
                    _logger.info("HDF5-like dataset at root level")
                    entry = "/"
                sel['selection']['entry'] = entry
                sel['selection']['key'] = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['selection']['x'] = cntSelection['x']
                sel['selection']['xselectiontype'] = cntSelection['xselectiontype']
                sel['selection']['y'] = [yCnt]
                sel['selection']['yselectiontype'] = [cntSelection['yselectiontype'][cntSelection['y'].index(yCnt)]]
                sel['selection']['m'] = cntSelection['m']
                sel['selection']['mselectiontype'] = cntSelection['monselectiontype']
                sel['selection']['cntlist'] = cntSelection['cntlist']
                sel['selection']['LabelNames'] = cntSelection['aliaslist']
                #sel['selection']['aliaslist'] = cntSelection['aliaslist']
                sel['selection']['selectiontype'] = selectionType
                if selectionType.upper() == "SCAN":
                    if cntSelection['cntlist'][yCnt].startswith("/"):
                        actualDatasetPath = posixpath.join(entry,
                                                cntSelection['cntlist'][yCnt][1:])
                    else:
                        actualDatasetPath = posixpath.join(entry,
                                                cntSelection['cntlist'][yCnt])
                    _logger.info("actualDatasetPath = %s" % actualDatasetPath)
                    try:
                        actualDataset = phynxFile[actualDatasetPath]
                    except KeyError:
                        # filter x.1 and x.2 ESRF case
                        if len(entryList) > 4:
                            _logger.info("Ignoring %s in %s" % \
                                         (actualDatasetPath, entry))
                            continue
                        else:
                            raise
                    sel['scanselection'] = True
                    if hasattr(actualDataset, "shape"):
                        if len(actualDataset.shape) > 1 and sel['selection']['yselectiontype'][0] in ["full", ""]:
                            if 1 in actualDataset.shape[-2:]:
                                #shape (1, n) or (n, 1)
                                pass
                            else:
                                # at least twoD dataset
                                selectionType= "2D"
                                sel['scanselection'] = False
                        elif len(actualDataset.shape) > 1 and sel['selection']['yselectiontype'][0].startswith("index"):
                            if len(actualDataset.shape) <= 2:
                                # 1D selection
                                pass
                            else:
                                # at least twoD dataset
                                selectionType= "2D"
                                sel['scanselection'] = False
                        elif len(actualDataset.shape) > 1 and sel['selection']['yselectiontype'][0].startswith("slice"):
                            # 1D selection
                            pass
                    n_axes = len(sel['selection']['x'])
                    if n_axes > 1:
                        selectionType = "%dD" % len(sel['selection']['x'])
                        selectionTypeDecided = False
                        nAxesItems = 1
                        if n_axes == len(actualDataset.shape):
                            for xCnt in cntSelection['x']:
                                if cntSelection['cntlist'][xCnt].startswith("/"):
                                    xDatasetPath = posixpath.join(entry,
                                                            cntSelection['cntlist'][xCnt][1:])
                                else:
                                    xDatasetPath = posixpath.join(entry,
                                                            cntSelection['cntlist'][xCnt])
                                nAxesItems *= phynxFile[xDatasetPath].size
                            if nAxesItems == actualDataset.size:
                                # we have an image with the associated dimensions
                                selectionTypeDediced = True

                        if selectionTypeDecided:
                            pass
                        elif n_axes == 2:
                            try:
                                from silx import version_info as silx_version
                            except ImportError:
                                silx_version = (0, 0, 0)
                            if silx_version < (0, 11):
                                # we have to use the 3D visualization
                                selectionType = "3D"
                            else:
                                # we can afford a scatter view
                                selectionType = "2D"
                        else:
                            selectionType = "%dD" % n_axes
                        sel['scanselection'] = False
                    sel['mcaselection']  = False
                elif selectionType.upper() == "MCA":
                    sel['scanselection'] = False
                    sel['mcaselection']  = True
                    if cntSelection['cntlist'][yCnt].startswith("/"):
                        actualDatasetPath = posixpath.join(entry,
                                                cntSelection['cntlist'][yCnt][1:])
                    else:
                        actualDatasetPath = posixpath.join(entry,
                                                cntSelection['cntlist'][yCnt])
                    actualDataset = phynxFile[actualDatasetPath]
                    if hasattr(actualDataset, "shape"):
                        actualDatasetLen = len(actualDataset.shape)
                        if sel['selection']['yselectiontype'][0] not in ["", "full", None]:
                            sel['selection']['mcaselectiontype'] = sel['selection']['yselectiontype'][0]
                        else:
                            if (actualDatasetLen == 2) and (1 in actualDataset.shape):
                                # still can be used
                                pass
                            elif (actualDatasetLen > 1) and (not hasattr(self, "_messageShown")):
                                # at least twoD dataset
                                msg = qt.QMessageBox(self)
                                msg.setIcon(qt.QMessageBox.Information)
                                msg.setText("Multidimensional data set as MCA. Using Average.\n Consider slicing or use ROI Imaging tool")
                                msg.exec()
                                self._messageShown = True
                            sel['selection']['mcaselectiontype'] = "avg"
                else:
                    sel['scanselection'] = False
                    sel['mcaselection']  = False
                sel['selection']['selectiontype'] = selectionType
                aliases = cntSelection['aliaslist']
                if sel['selection']['yselectiontype'][0] not in ["", "full", None]:
                     aliases[yCnt] += " " + sel['selection']['yselectiontype'][0]

                if len(cntSelection['m']):
                     if sel['selection']['mselectiontype'][0] not in ["", "full", None]:
                         aliases[cntSelection['m'][0]] += " " + sel['selection']['mselectiontype'][0]

                if len(cntSelection['x']):
                     if sel['selection']['xselectiontype'][0] not in ["", "full", None]:
                         aliases[cntSelection['x'][0]] += " " + sel['selection']['xselectiontype'][0]

                if len(cntSelection['x']) and len(cntSelection['m']):
                    addLegend = " (%s/%s) vs %s" % (aliases[yCnt],
                                                   aliases[cntSelection['m'][0]],
                                                   aliases[cntSelection['x'][0]])
                elif len(cntSelection['x']):
                    addLegend = " %s vs %s" % (aliases[yCnt],
                                               aliases[cntSelection['x'][0]])
                elif len(cntSelection['m']):
                    addLegend = " (%s/%s)" % (aliases[yCnt],
                                            aliases[cntSelection['m'][0]])
                else:
                    addLegend = " %s" % aliases[yCnt]
                sel['legend'] += addLegend
                selectionList.append(sel)

        if not emit:
            return selectionList
        self._lastAction = "%s" % ddict['action']
        if len(selectionList):
            if text.upper() == "MCA":
                self._lastMcaSelection = mcaSelection
            else:
                self._lastCntSelection = cntSelection
            if selectionType.upper() in ["SCAN", "MCA"]:
                ddict = {}
                ddict['event'] = "SelectionTypeChanged"
                ddict['SelectionType'] = selectionType.upper()
                self.sigOtherSignals.emit(ddict)
            if action.upper() == "ADD":
                self.sigAddSelection.emit(selectionList)
            if action.upper() == "REMOVE":
                self.sigRemoveSelection.emit(selectionList)
            if action.upper() == "REPLACE":
                self.sigReplaceSelection.emit(selectionList)

    def currentSelectionList(self):
        ddict={}
        ddict['event'] = 'buttonClicked'
        ddict['action'] = 'ADD DUMMY'
        return self.buttonsSlot(ddict, emit=False)

    def getSelectedEntries(self):
        return self.hdf5Widget.getSelectedEntries()

    def closeEvent(self, event):
        keyList = list(self._widgetDict.keys())
        for key in keyList:
            self._widgetDict[key].close()
            del self._widgetDict[key]
        return qt.QWidget.closeEvent(self, event)

    def _checkWidgetDict(self):
        keyList = list(self._widgetDict.keys())
        for key in keyList:
            if self._widgetDict[key].isHidden():
                del self._widgetDict[key]

    def customEvent(self, event):
        if hasattr(event, 'dict'):
            ddict = event.dict
            if 'event' in ddict:
                if ddict['event'] == "closeEventSignal":
                    if ddict['id'] in self._widgetDict:
                        if _logger.getEffectiveLevel() == logging.DEBUG:
                            try:
                                widget = self._widgetDict[ddict['id']]
                                _logger.debug("DELETING %s", widget.windowTitle())
                            except Exception:
                                pass
                        del self._widgetDict[ddict['id']]

if __name__ == "__main__":
    import sys
    _logger.setLevel(logging.DEBUG)
    app = qt.QApplication(sys.argv)
    try:
        #this is to add the 3D buttons ...
        from PyMca5.PyMcaGui.pymca import SilxGLWindow
    except Exception:
        pass
    w = QNexusWidget()
    if 0:
        w.setFile(sys.argv[1])
    else:
        from PyMca5.PyMcaCore import NexusDataSource
        dataSource = NexusDataSource.NexusDataSource(sys.argv[1:])
        w.setDataSource(dataSource)
    def addSelection(sel):
        print(sel)
    def removeSelection(sel):
        print(sel)
    def replaceSelection(sel):
        print(sel)
    w.show()
    w.sigAddSelection.connect(addSelection)
    w.sigRemoveSelection.connect(removeSelection)
    w.sigReplaceSelection.connect(replaceSelection)
    ret = app.exec()
    sys.exit(ret)
