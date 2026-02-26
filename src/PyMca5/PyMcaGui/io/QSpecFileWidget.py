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
__author__ = "E. Papillon, V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import QSelectorWidget
from PyMca5.PyMcaGui.io import SpecFileDataInfo
from PyMca5.PyMcaGui.io import SpecFileCntTable
OBJECT3D = SpecFileCntTable.OBJECT3D
from PyMca5.PyMcaGui.io import SpecFileMcaTable

_logger = logging.getLogger(__name__)

QTVERSION = qt.qVersion()

class MyQTreeWidgetItem(qt.QTreeWidgetItem):
    def __lt__(self, other):
        c = self.treeWidget().sortColumn()
        if  c == 0:
            return False
        if c !=  2:
            return (float(self.text(c)) <  float(other.text(c)))
        return (self.text(c) < other.text(c))

#class QSpecFileWidget(qt.QWidget):
class QSpecFileWidget(QSelectorWidget.QSelectorWidget):
    sigAddSelection = qt.pyqtSignal(object)
    sigRemoveSelection = qt.pyqtSignal(object)
    sigReplaceSelection = qt.pyqtSignal(object)
    sigOtherSignals = qt.pyqtSignal(object)
    sigScanSelection = qt.pyqtSignal(object)
    sigScanDoubleClicked = qt.pyqtSignal(object)
    def __init__(self, parent=None, autoreplace=False):
        self.autoReplace = autoreplace
        if self.autoReplace:
            self.autoAdd     = False
        else:
            self.autoAdd     = True
        self._oldCntSelection = None
        QSelectorWidget.QSelectorWidget.__init__(self, parent)
        self.dataInfoWidgetDict = {}

    def _build(self):
        #self.layout= qt.QVBoxLayout(self)
        self.splitter = qt.QSplitter(self)
        self.splitter.setOrientation(qt.Qt.Vertical)
        self.list  = qt.QTreeWidget(self.splitter)
        self.list.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)
        self.mainTab = qt.QTabWidget(self.splitter)

        self.cntTable = SpecFileCntTable.SpecFileCntTable()
        self.mcaTable = SpecFileMcaTable.SpecFileMcaTable()

        self.mainTab.addTab(self.cntTable, str("Counters"))
        self.mainTab.addTab(self.mcaTable, str("MCA"))
        self.mainTab.setCurrentWidget(self.mcaTable)

        autoBox = qt.QWidget(self)
        autoBoxLayout = qt.QGridLayout(autoBox)
        autoBoxLayout.setContentsMargins(0, 0, 0, 0)
        autoBoxLayout.setSpacing(0)
        self.autoOffBox = qt.QCheckBox(autoBox)
        self.autoOffBox.setText("Auto OFF")
        self.autoAddBox = qt.QCheckBox(autoBox)
        self.autoAddBox.setText("Auto ADD")
        self.autoReplaceBox = qt.QCheckBox(autoBox)
        self.autoReplaceBox.setText("Auto REPLACE")

        row = 0
        autoBoxLayout.addWidget(self.autoOffBox, row, 0)
        autoBoxLayout.addWidget(self.autoAddBox, row, 1)
        autoBoxLayout.addWidget(self.autoReplaceBox, row, 2)

        if self.autoReplace:
            self.autoAddBox.setChecked(False)
            self.autoReplaceBox.setChecked(True)
        else:
            self.autoAddBox.setChecked(True)
            self.autoReplaceBox.setChecked(False)
        row += 1

        if OBJECT3D:
            self.object3DBox = qt.QCheckBox(autoBox)
            self.object3DBox.setText("3D On")
            self.object3DBox.setToolTip("Use OpenGL and enable 2D & 3D selections")
            autoBoxLayout.addWidget(self.object3DBox, row, 0)
            self.mcaTable.sigMcaDeviceSelected.connect(self.mcaDeviceSelected)

        self.meshBox = qt.QCheckBox(autoBox)
        self.meshBox.setText("2D On")
        self.meshBox.setToolTip("Enable 2D selections (mesh and scatter)")
        autoBoxLayout.addWidget(self.meshBox, row, 1)


        self.forceMcaBox = qt.QCheckBox(autoBox)
        self.forceMcaBox.setText("Force MCA")
        self.forceMcaBox.setToolTip("Interpret selections as MCA")
        autoBoxLayout.addWidget(self.forceMcaBox, row, 2)

        self.mainLayout.addWidget(self.splitter)
        self.mainLayout.addWidget(autoBox)


        # --- list headers
        labels = ["X", "S#", "Command", "Points", "Nb. Mca"]
        ncols  = len(labels)
        self.list.setColumnCount(ncols)
        self.list.setHeaderLabels(labels)
        #size=50
        #self.list.header().resizeSection(0, size)
        #self.list.header().resizeSection(1, size)
        #self.list.header().resizeSection(2, 4 * size)
        #self.list.header().resizeSection(3, size)
        #self.list.header().resizeSection(4, size)

        self.list.header().setStretchLastSection(False)
        self.list.header().setSectionResizeMode(0, qt.QHeaderView.Interactive)
        self.list.header().setSectionResizeMode(1, qt.QHeaderView.Interactive)
        self.list.header().setSectionResizeMode(2, qt.QHeaderView.Interactive)
        self.list.header().setSectionResizeMode(3, qt.QHeaderView.Interactive)
        self.list.header().setSectionResizeMode(4, qt.QHeaderView.Interactive)
        fm = self.list.header().fontMetrics()
        if hasattr(fm, "width"):
            size = fm.width("X")
        else:
            size = fm.maxWidth()
        self.list.header().setMinimumSectionSize(size)
        self.list.header().resizeSection(0, size)
        #    self.list.header().resizeSection(1, size * 4)
        self.list.header().resizeSection(2, size * 25)
        #    self.list.header().resizeSection(3, size * 7)
        #    self.list.header().resizeSection(4, size * 8)

        # --- signal handling
        self.list.itemSelectionChanged.connect(self.__selectionChanged)
        self.list.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.__contextMenu)
        self.list.itemClicked[qt.QTreeWidgetItem, int].connect( \
                    self.__singleClicked)
        self.list.itemDoubleClicked[qt.QTreeWidgetItem, int].connect( \
                     self.__doubleClicked)
        self.cntTable.sigSpecFileCntTableSignal.connect(self._cntSignal)

        self.list.setSortingEnabled(False)
        self.list.header().sectionDoubleClicked[int].connect( \
                     self.__headerSectionDoubleClicked)
        if OBJECT3D:
            self.object3DBox.clicked.connect(self._setObject3DBox)
        if hasattr(self, 'meshBox'):
            self.meshBox.clicked.connect(self._setMeshBox)

        self.autoOffBox.clicked.connect(self._setAutoOff)
        self.autoAddBox.clicked.connect(self._setAutoAdd)
        self.autoReplaceBox.clicked.connect(self._setAutoReplace)

        self.forceMcaBox.clicked.connect(self._setForcedMca)

        self.mainTab.currentChanged[int].connect(self._tabChanged)

        self.disableMca    = 0 #(type=="scan")
        self.disableScan   = 0 #(type=="mca")

        # -- last scan watcher
        self.lastScanWatcher = qt.QTimer()
        self.lastScanWatcher.setSingleShot(True)
        self.lastScanWatcher.setInterval(2000) # 2 seconds
        self.lastScanWatcher.timeout.connect(self._timerSlot)

        # --- context menu
        self.data= None
        self.scans= []


    def _setObject3DBox(self):
        self.autoAddBox.setChecked(False)
        self.meshBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoOffBox.setChecked(False)
        self.cntTable.set3DEnabled(True)
        self.object3DBox.setChecked(True)

    def _setMeshBox(self):
        self.autoAddBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoOffBox.setChecked(False)
        self.cntTable.set2DEnabled(True)
        if hasattr(self, "object3DBox"):
            self.object3DBox.setChecked(False)
        self.meshBox.setChecked(True)

    def _setAutoOff(self):
        if OBJECT3D:
            self.cntTable.set3DEnabled(False)
            self.object3DBox.setChecked(False)
        if hasattr(self, "meshBox"):
            self.cntTable.set2DEnabled(False)
            self.meshBox.setChecked(False)
        self.autoAddBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoOffBox.setChecked(True)

    def _setAutoAdd(self):
        if OBJECT3D:
            self.cntTable.set3DEnabled(False)
            self.object3DBox.setChecked(False)
        if hasattr(self, "meshBox"):
            self.meshBox.setChecked(False)
            self.cntTable.set2DEnabled(False)
        self.autoOffBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoAddBox.setChecked(True)

    def _setAutoReplace(self):
        if OBJECT3D:
            self.cntTable.set3DEnabled(False)
            self.object3DBox.setChecked(False)
        if hasattr(self, "meshBox"):
            self.cntTable.set2DEnabled(False)
            self.meshBox.setChecked(False)
        self.autoOffBox.setChecked(False)
        self.autoAddBox.setChecked(False)
        self.autoReplaceBox.setChecked(True)

    def _setForcedMca(self):
        if self.forceMcaBox.isChecked():
            if OBJECT3D:
                self.object3DBox.setChecked(False)
                self.object3DBox.setEnabled(False)
            if hasattr(self, "meshBox"):
                self.meshBox.setChecked(False)
                self.meshBox.setEnabled(False)
        else:
            if OBJECT3D:
                self.object3DBox.setEnabled(True)
            if hasattr(self, "meshBox"):
                self.meshBox.setEnabled(True)

    #
    # Data management
    #
    #NEW data management
    def setDataSource(self, datasource):
        _logger.debug("setDataSource(self, datasource) called")
        _logger.debug("datasource = %s", datasource)
        self.data = datasource
        self.refresh()

        if not self.autoAddBox.isChecked():
            return
        #If there is only one mca containing scan
        # and we are in auto add mode, I plot it.
        if len(self.scans) == 1:
            item = self.list.itemAt(qt.QPoint(0,0))
            if item is not None:
                item.setSelected(True)
                # this call is not needed
                # triggered by the selectionChanged signal
                # self.__selectionChanged()

    #OLD data management
    def setData(self, specfiledata):
        _logger.debug("setData(self, specfiledata) called")
        _logger.debug("specfiledata = %s", specfiledata)
        self.data= specfiledata
        self.refresh()

    def refresh(self):
        self.list.clear()
        if self.data is None: return
        try:
            if self.data.sourceName is None: return
        except Exception:
            if self.data.SourceName is None: return
        try:
            #new
            info= self.data.getSourceInfo()
        except Exception:
            #old
            if not hasattr(self.data, "GetSourceInfo"):
                raise
            info= self.data.GetSourceInfo()
        self.scans= []
        after= None
        i = 0
        for (sn, cmd, pts, mca) in zip(info["KeyList"], info["Commands"], info["NumPts"], info["NumMca"]):
            if after is not None:
                #print "after is not none"
                #item= qt.QTreeWidgetItem(self.list, [after, "", sn, cmd, str(pts), str(mca)])
                item= MyQTreeWidgetItem(self.list, ["", sn, cmd, str(pts), str(mca)])
            else:
                item= MyQTreeWidgetItem(self.list, ["", sn, cmd, str(pts), str(mca)])
            if (self.disableMca and not mca) or (self.disableScan and not pts):
                item.setSelectable(0)
                #XXX: not possible to put in italic: other solutions ??
            self.scans.append(sn)
            after= item
            i = i + 1
        self.list.resizeColumnToContents(0)
        self.list.resizeColumnToContents(1)
        #self.list.resizeColumnToContents(2)
        self.list.resizeColumnToContents(3)
        self.list.resizeColumnToContents(4)

    def clear(self):
        self.list.clear()
        self.data= None
        self.scans= []

    def markScanSelected(self, scanlist):
        for sn in self.scans:
            item= self.list.findItem(sn, 1)
            if item is not None:
                if sn in scanlist:
                    item.setText(0, "X")
                else:
                    item.setText(0, "")

    def _autoReplace(self, scanlist=None):
        _logger.debug("autoreplace called with %s", scanlist)
        if self.autoReplaceBox.isChecked():
            self._replaceClicked()
        elif self.autoAddBox.isChecked():
            self._addClicked()

    #
    # signal/slot handling
    #
    def _cntSignal(self, ddict):
        if ddict["event"] == "updated":
            itemlist = self.list.selectedItems()
            sel = [str(item.text(1)) for item in itemlist]
            self._autoReplace(sel)


    def __selectionChanged(self):
        _logger.info("__selectionChanged")
        itemlist = self.list.selectedItems()
        sel = [str(item.text(1)) for item in itemlist]
        _logger.debug("selection = %s", sel)
        if not len(sel):
            return
        info = self.data.getKeyInfo(sel[0])
        self.mcaTable.build(info)
        if False:
            # This does not work properly yet
            # TODO: mca as function of other parameter
            NbMca = info.get('NbMcaDet', 0)
            self.cntTable.build(info['LabelNames'], nmca=NbMca)
        else:
            self.cntTable.build(info['LabelNames'], nmca=0)

        autoReplaceCall = True
        if (info['Lines'] > 0) and len(info['LabelNames']):
            if self._oldCntSelection is not None:
                if len(self._oldCntSelection['y']):
                    self.cntTable.setCounterSelection(self._oldCntSelection)
                else:
                    if len(self.cntTable.cntList):
                        self.cntTable.setCounterSelection({'x':[0],
                                                           'y':[-1],
                                            'cntlist':info['LabelNames']*1})
            else:
                if len(self.cntTable.cntList):
                   self.cntTable.setCounterSelection({'x':[0],
                                                      'y':[-1],
                                        'cntlist':info['LabelNames']*1})
            # That already emitted a signal, no need to repeat with
            # autoreplace
            autoReplaceCall = False

        # Emit this signal for the case someone else uses it ...
        self.sigScanSelection.emit((sel))
        if (info['NbMca'] > 0) and (info['Lines'] > 0):
            pass
        elif (info['NbMca'] > 0) and (info['Lines'] == 0):
            self.mainTab.setCurrentWidget(self.mcaTable)
        elif (info['NbMca'] == 0) and (info['Lines'] > 0):
            self.mainTab.setCurrentWidget(self.cntTable)
        else:
            pass
        # Next call is needed to handle the direct opening of MCAs
        # when using a single scan, single mca file.
        if autoReplaceCall:
            self._autoReplace(sel)

    def __headerSectionDoubleClicked(self, index):
        if index == 0:
            return
        else:
            self.list.sortItems(index, qt.Qt.AscendingOrder)
            #print "index = ", index

    def _timerSlot(self):
        _logger.info("_timerSlot")
        # check if last scan is selected
        if not len(self.scans):
            if self.lastScanWatcher:
                if self.lastScanWatcher.isActive():
                    self.lastScanWatcher.stop()
            return
        scan = self.scans[-1]
        itemList = self.list.findItems(scan, qt.Qt.MatchExactly,1)
        if len(itemList) == 1:
            itemlist = self.list.selectedItems()
            scan_sel = [str(item.text(1)) for item in itemlist]
            if itemList[0].isSelected():
                if len(scan_sel) == 1:
                    # allow the user to perform multiple selections
                    # that include the last scan
                    if hasattr(self.data, "isUpdated") and hasattr(self.data, "refresh"):
                        if hasattr(self.data.sourceName, "upper"):
                            source = self.data.sourceName
                        else:
                            source = self.data.sourceName[0]
                        try:
                            updated = self.data.isUpdated(self.data.sourceName, scan)
                        except Exception:
                            _logger.warning("Error trying to verify if source was updated")
                            updated = False
                        if updated:
                            self.data.refresh()
                            self.refresh()
                            # make sure the item is found and selected after the update
                            itemList = self.list.findItems(scan, qt.Qt.MatchExactly,1)
                            if len(itemList) == 1:
                                itemList[0].setSelected(True)
                if not self.lastScanWatcher.isActive():
                    self.lastScanWatcher.start()
        else:
            self.lastScanWatcher.setActive(False)

    def __singleClicked(self, item):
        _logger.info("__singleClicked")
        if item is not None:
            sn  = str(item.text(1))
            ddict={}
            ddict['Key']      = sn
            ddict['Command']  = str(item.text(2))
            ddict['NbPoints'] = int(str(item.text(3)))
            ddict['NbMca']    = int(str(item.text(4)))
            selected = item.isSelected()
            if len(self.scans) and self.lastScanWatcher:
                if sn == self.scans[-1]:
                    if hasattr(self.data, "isUpdated") and hasattr(self.data, "refresh"):
                        if hasattr(self.data.sourceName, "upper"):
                            source = self.data.sourceName
                        else:
                            source = self.data.sourceName[0]
                        if os.path.exists(source):
                            _logger.info("last scan watcher disabled on actual files")
                            if self.lastScanWatcher.isActive():
                                self.lastScanWatcher.stop()
                            return
                        if not self.lastScanWatcher.isActive():
                            self.lastScanWatcher.start()
                        _logger.info("last scan watcher started")
                        return
            if self.lastScanWatcher.isActive():
                self.lastScanWatcher.stop()

    def __doubleClicked(self, item):
        _logger.info("__doubleClicked")
        if item is not None:
            sn  = str(item.text(1))
            ddict={}
            ddict['Key']      = sn
            ddict['Command']  = str(item.text(2))
            ddict['NbPoints'] = int(str(item.text(3)))
            ddict['NbMca']    = int(str(item.text(4)))
            self.sigScanDoubleClicked.emit(ddict)
            if len(self.scans):
                if sn == self.scans[-1]:
                    if hasattr(self.data, "isUpdated") and hasattr(self.data, "refresh"):
                        if hasattr(self.data.sourceName, "upper"):
                            source = self.data.sourceName
                        else:
                            source = self.data.sourceName[0]
                        if os.path.exists(source) and self.data.isUpdated(self.data.sourceName, sn):
                            updated = True
                        else:
                            # bliss case, it takes as long to check as to update
                            updated = True
                        if updated:
                            self.data.refresh()
                            self.refresh()
                            # make sure the item is selected
                            itemList = self.list.findItems(sn, qt.Qt.MatchExactly,1)
                            if len(itemList) == 1:
                                itemList[0].setSelected(True)
            #shortcut selec + remove?
            #for the time being just add
            self._addClicked()

    def __contextMenu(self, point):
        _logger.info("__contextMenu %s", point)
        item = self.list.itemAt(point)
        if item is not None:
            sn= str(item.text(1))
            self.menu= qt.QMenu()
            self.menu.addAction("Show scan header", self.__showScanInfo)
            self.menu_idx = self.scans.index(sn)
            self.menu.popup(self.cursor().pos())

    def mcaDeviceSelected(self, ddict):
        action, actiontype = ddict['action'].split()
        mca = ddict['mca'] + 1
        sel_list = []
        itemlist = self.list.selectedItems()
        scan_sel = [str(item.text(1)) for item in itemlist]
        for scan in scan_sel:
            sel = {}
            sel['SourceName'] = self.data.sourceName
            sel['SourceType'] = self.data.sourceType
            sel['Key'] = "%s.%d"% (scan, mca)
            #sel['selection'] = None
            sel['selection'] = {}
            if actiontype.upper() == "STACK":
                sel['selection']['selectiontype'] = "STACK"
                sel['imageselection'] = False
            else:
                sel['selection']['selectiontype'] = "2D"
                sel['imageselection'] = True
            sel['scanselection'] = False
            sel['mcaselection']  = False
            sel['legend']    = os.path.basename(sel['SourceName'][0]) +" "+ sel['Key']
            sel_list.append(sel)
        if len(scan_sel):
            if action == 'ADD':
                self.sigAddSelection.emit(sel_list)
            elif action == 'REMOVE':
                self.sigRemoveSelection.emit(sel_list)
            elif action == 'REPLACE':
                self.sigReplaceSelection.emit(sel_list)

    def __showScanInfo(self, idx = None):
        if idx is None:
            idx = self.menu_idx
        _logger.debug("Scan information:")

        try:
            info = self.data.getDataObject(self.scans[idx]).info
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Error: %s\n accessing scan information." % (sys.exc_info()[1])
            msg.setText(text)
            msg.exec()
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise
            return

        dataInfoWidget= SpecFileDataInfo.SpecFileDataInfo(info)
        if "Header" in info:
            if info['Header'] is not None:
                dataInfoWidget.setWindowTitle(info['Header'][0])
        dataInfoWidget.show()
        wid = id(dataInfoWidget)
        self.dataInfoWidgetDict[wid] = dataInfoWidget
        dataInfoWidget.notifyCloseEventToWidget(self)

    def _dataInfoClosed(self, ddict):
        if ddict['event'] == "SpecFileDataInfoClosed":
            del self.dataInfoWidgetDict[ddict['id']]

    def customEvent(self, event):
        if hasattr(event, 'dict'):
            ddict = event.dict
            self._dataInfoClosed(ddict)

    def _addClicked(self, emit=True):
        _logger.debug("Overwritten _addClicked method")

        #get selected scan keys
        itemlist = self.list.selectedItems()
        scan_sel = [str(item.text(1)) for item in itemlist]

        #get selected counter keys
        cnt_sel = self.cntTable.getCounterSelection()
        if len(cnt_sel['cntlist']):
            if len(cnt_sel['y']):
                self._oldCntSelection = cnt_sel
        mca_sel = self.mcaTable.getCurrentlySelectedMca()

        sel_list = []
        #build the appropriate selection for mca's
        for scan in scan_sel:
            for mca in mca_sel:
                sel = {}
                sel['SourceName'] = self.data.sourceName
                sel['SourceType'] = self.data.sourceType
                sel['Key'] = scan
                sel['Key'] += "." + mca
                sel['selection'] = None #for the future
                #sel['scanselection']  = False
                sel['legend']    = os.path.basename(sel['SourceName'][0]) +" "+ sel['Key']
                sel_list.append(sel)
            if len(cnt_sel['cntlist']):
                if len(cnt_sel['y']): #if there is something to plot
                    sel = {}
                    sel['SourceName'] = self.data.sourceName
                    sel['SourceType'] = self.data.sourceType
                    sel['Key'] = scan
                    sel['selection'] = {}
                    if self.forceMcaBox.isChecked():
                        sel['scanselection']  = "MCA"
                    else:
                        sel['scanselection']  = True
                    sel['selection']['x'] = cnt_sel['x']
                    sel['selection']['y'] = cnt_sel['y']
                    sel['selection']['m'] = cnt_sel['m']
                    sel['selection']['cntlist'] = cnt_sel['cntlist']
                    sel['legend']    = os.path.basename(sel['SourceName'][0]) +" "+ sel['Key']
                    if len(sel['selection']['x']) == 2:
                        if self.meshBox.isChecked():
                            sel['selection']['selectiontype'] = "2D"
                    if cnt_sel['y'][0] >= len(cnt_sel['cntlist']):
                        if 'mcalist' in cnt_sel:
                            sel['selection']['mcalist'] = cnt_sel['mcalist']
                        else:
                            # I could rise the exception here
                            # but I let the data source to rise it.
                            pass
                    elif len(sel['selection']['x']) == 2:
                        if not self.meshBox.isChecked():
                            # no regular mesh attempted
                            # try scatter or 3D
                            sel['legend'] += " " + cnt_sel['cntlist'][cnt_sel['y'][0]]

                    sel_list.append(sel)
        if emit:
            if len(sel_list):
                self.sigAddSelection.emit(sel_list)
        else:
            return sel_list

    def currentSelectionList(self):
        return self._addClicked(emit=False)

    def _removeClicked(self):
        _logger.debug("Overwritten _removeClicked method")

        #get selected scan keys
        itemlist = self.list.selectedItems()
        scan_sel = [str(item.text(1)) for item in itemlist]

        #get selected counter keys
        cnt_sel = self.cntTable.getCounterSelection()
        mca_sel = self.mcaTable.getCurrentlySelectedMca()

        sel_list = []
        #build the appropriate selection for mca's
        for scan in scan_sel:
            for mca in mca_sel:
                sel = {}
                sel['SourceName'] = self.data.sourceName
                sel['SourceType'] = self.data.sourceType
                sel['Key'] = scan
                sel['Key'] += "."+mca
                sel['selection'] = None #for the future
                #sel['scanselection']  = False
                sel['legend'] = os.path.basename(sel['SourceName'][0]) +" "+sel['Key']
                sel_list.append(sel)
            if len(cnt_sel['cntlist']):
                if len(cnt_sel['y']): #if there is something to plot
                    sel = {}
                    sel['SourceName'] = self.data.sourceName
                    sel['SourceType'] = self.data.sourceType
                    sel['Key'] = scan
                    sel['selection'] = {}
                    if self.forceMcaBox.isChecked():
                        sel['scanselection']  = "MCA"
                    else:
                        sel['scanselection']  = True
                    sel['selection']['x'] = cnt_sel['x']
                    if len(sel['selection']['x']) == 2:
                        if self.meshBox.isChecked():
                            sel['selection']['selectiontype'] = "2D"
                    sel['selection']['y'] = cnt_sel['y']
                    sel['selection']['m'] = cnt_sel['m']
                    sel['selection']['cntlist'] = cnt_sel['cntlist']
                    sel['legend']    = os.path.basename(sel['SourceName'][0]) +" "+ sel['Key']
                    sel_list.append(sel)

        if len(sel_list):
            self.sigRemoveSelection.emit(sel_list)

    def _replaceClicked(self):
        _logger.debug("Overwritten _replaceClicked method")
        #get selected scan keys
        itemlist = self.list.selectedItems()
        scan_sel = [str(item.text(1)) for item in itemlist]

        #get selected counter keys
        cnt_sel = self.cntTable.getCounterSelection()
        if len(cnt_sel['cntlist']):
            if len(cnt_sel['y']):
                self._oldCntSelection = cnt_sel
        mca_sel = self.mcaTable.getCurrentlySelectedMca()

        sel_list = []
        #build the appropriate selection for mca's
        for scan in scan_sel:
            for mca in mca_sel:
                sel = {}
                sel['SourceName'] = self.data.sourceName
                sel['SourceType'] = self.data.sourceType
                sel['Key'] = scan
                sel['Key'] += "."+mca
                sel['selection'] = None #for the future
                #sel['scanselection']  = False #This could also be MCA
                sel['legend'] = os.path.basename(sel['SourceName'][0]) +" "+sel['Key']
                sel_list.append(sel)
            if len(cnt_sel['cntlist']):
                sel = {}
                sel['SourceName'] = self.data.sourceName
                sel['SourceType'] = self.data.sourceType
                sel['Key'] = scan
                if len(cnt_sel['y']): #if there is something to plot
                    if self.forceMcaBox.isChecked():
                        sel['scanselection']  = "MCA"
                    else:
                        sel['scanselection']  = True #This could also be SCAN
                    sel['selection'] = {}
                    sel['selection']['x'] = cnt_sel['x']
                    if len(sel['selection']['x']) == 2:
                        if self.meshBox.isChecked():
                            sel['selection']['selectiontype'] = "2D"
                    sel['selection']['y'] = cnt_sel['y']
                    sel['selection']['m'] = cnt_sel['m']
                    sel['selection']['cntlist'] = cnt_sel['cntlist']
                    sel['legend']    = os.path.basename(sel['SourceName'][0]) +" "+ sel['Key']
                    if cnt_sel['y'][0] >= len(cnt_sel['cntlist']):
                        if 'mcalist' in cnt_sel:
                            sel['selection']['mcalist'] = cnt_sel['mcalist']
                        else:
                            # I could rise the exception here
                            # but I let the data source to rise it.
                            pass
                    sel_list.append(sel)
        if len(sel_list):
            self.sigReplaceSelection.emit(sel_list)

    def _tabChanged(self, value):
        _logger.debug("self._tabChanged(value), value = %s", value)
        text = str(self.mainTab.tabText(value))
        if self.data is None: return

        ddict = {}
        ddict['SourceName'] = self.data.sourceName
        ddict['SourceType'] = self.data.sourceType
        ddict['event'] = "SelectionTypeChanged"
        ddict['SelectionType'] = text
        self.sigOtherSignals.emit(ddict)

    def getWidgetConfiguration(self):
        # just limited to the actions
        ddict = {}
        ddict["mca"]= self.forceMcaBox.isChecked()
        if self.autoReplaceBox.isChecked():
            ddict['auto'] = "REPLACE"
        elif self.autoAddBox.isChecked():
            ddict['auto'] = "ADD"
        else:
            ddict['auto'] = "OFF"
        ddict["2d"]= self.meshBox.isChecked()
        if hasattr(self, "object3DBox"):
            ddict["3d"] = self.object3DBox.isChecked()
        else:
            ddict["3d"] = False
        ddict["mca"]= self.forceMcaBox.isChecked()
        return ddict

    def setWidgetConfiguration(self, ddict):
        # just limited to the actions
        mca = ddict.get("mca", False)
        if mca in ["False", "0", 0, "", "false"]:
            mca = False
        else:
            mca = True
        auto = ddict.get("auto", "ADD")
        twod = ddict.get("2d", "False")
        if twod in ["False", "0", 0, "", "false"]:
            twod = False
        else:
            twod = True
        threed = ddict.get("3d", "False")
        if threed in ["False", "0", 0, "", "false"]:
            threed = False
        else:
            threed = True
        self.forceMcaBox.setChecked(mca)
        if auto == "ADD":
            self._setAutoAdd()
        elif auto == "OFF":
            self._setAutoOff()
            # this is compatible with 2D or 3D selections
            if OBJECT3D:
                if threed:
                    self._setObject3DBox()
                else:
                    self.object3DBox.setChecked(False)
            if twod:
                self._setMeshBox()
            else:
                self.meshBox.setChecked(False)
        elif auto == "REPLACE":
            self._setAutoReplace()

def test():
    from PyMca5.PyMcaGui.pymca import QDataSource
    a = qt.QApplication(sys.argv)
    w = QSpecFileWidget()
    if len(sys.argv) > 1:
        d = QDataSource.QDataSource(sys.argv[1])
    else:
        if os.path.exists('03novs060sum.mca'):
            d = QDataSource.QDataSource('03novs060sum.mca')
        else:
            print("Usage:")
            print("      python QSpecFileWidget.py filename")
            a.quit()
            sys.exit(0)
    w.setData(d)
    w.show()
    def mySlot(selection):
        print(selection)
        try:
            # this is only for "addSelection"
            print(d.getDataObject(selection[0]['Key'], selection[0]['selection']))
        except Exception:
            pass
        return
    w.sigAddSelection.connect(mySlot)
    w.sigRemoveSelection.connect(mySlot)
    w.sigReplaceSelection.connect(mySlot)
    a.lastWindowClosed.connect(a.quit)

    a.exec()


if __name__=="__main__":
    test()
