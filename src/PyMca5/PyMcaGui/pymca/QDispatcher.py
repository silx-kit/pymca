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
import traceback
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()
from PyMca5.PyMcaGui.io import QSourceSelector
from . import QDataSource
#import weakref

_logger = logging.getLogger(__name__)


class QDispatcher(qt.QWidget):
    sigAddSelection = qt.pyqtSignal(object)
    sigRemoveSelection = qt.pyqtSignal(object)
    sigReplaceSelection = qt.pyqtSignal(object)
    sigOtherSignals = qt.pyqtSignal(object)

    def __init__(self, parent=None, pluginsIcon=False):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.sourceList = []
        fileTypeList = []
        if QDataSource.NEXUS:
            fileTypeList.append("HDF5 Files (*.nxs *.hdf *.h5 *.hdf5)")
            if "silx" in sys.modules:
                fileTypeList.append("HDF5-like Files (*)")
        fileTypeList += ["Spec Files (*mca)",
                        "Spec Files (*dat)",
                        "Spec Files (*spec)",
                        "SPE Files (*SPE *spe)",
                        "EDF Files (*edf)",
                        "EDF Files (*ccd)",
                        "TIFF Files (*.tif *.tiff *.TIF *.TIFF)",
                        "CSV Files (*csv)",
                        "JCAMP-DX Files (*.jdx *.JDX *.dx *.DX)"]
        fileTypeList.append("All Files (*)")

        self.sourceSelector = QSourceSelector.QSourceSelector(self,
                                    filetypelist=fileTypeList,
                                    pluginsIcon=pluginsIcon)
        if pluginsIcon:
            self.sourceSelector.pluginsButton.clicked.connect(self._pluginsClicked)
            self.pluginsCallback = None
        self._refreshInProgress = False
        self._autoRefreshFailures = 0
        self.selectorWidget = {}
        self.tabWidget = qt.QTabWidget(self)

        #for the time being just files
        for src_widget in QDataSource.source_widgets.keys():
            self.selectorWidget[src_widget] = QDataSource.source_widgets[src_widget]()
            self.tabWidget.addTab(self.selectorWidget[src_widget], src_widget)
            self.selectorWidget[src_widget].sigAddSelection.connect( \
                            self._addSelectionSlot)
            self.selectorWidget[src_widget].sigRemoveSelection.connect( \
                         self._removeSelectionSlot)
            self.selectorWidget[src_widget].sigReplaceSelection.connect( \
                         self._replaceSelectionSlot)
            if src_widget not in ['EdfFile']:
                self.selectorWidget[src_widget].sigOtherSignals.connect( \
                         self._otherSignalsSlot)

        self._connectAutoRefresh()

        self.mainLayout.addWidget(self.sourceSelector)
        self.mainLayout.addWidget(self.tabWidget)
        self.sourceSelector.sigSourceSelectorSignal.connect( \
                    self._sourceSelectorSlot)
        self.tabWidget.currentChanged[int].connect(self._tabChanged)

    def _connectAutoRefresh(self):
        """Connect the HDF5 actions to the source selector
        the action reports the state,
        the source selector starts/stops the timer and reports availability
        """
        if "HDF5" not in self.selectorWidget:
            return
        actions = self.selectorWidget["HDF5"].actions
        actions.sigAutoRefreshToggled.connect(
            self.sourceSelector.autoRefreshToggled)
        self.sourceSelector.sigAutoRefreshAvailable.connect(
            actions.setAutoRefreshEnabled)

    def _stopAutoRefresh(self):
        if "HDF5" not in self.selectorWidget:
            return
        actions = self.selectorWidget["HDF5"].actions
        if actions.autoRefreshBox.isChecked():
            actions.autoRefreshBox.setChecked(False)

    def _addSelectionSlot(self, sel_list, event=None):
        _logger.debug("QDispatcher._addSelectionSlot")
        _logger.debug("sel_list = %s", sel_list)

        if event is None:
            event = "addSelection"
        i = 0
        indices = []
        index = []
        affectedSources = []
        for sel in sel_list:
            sourceName = sel['SourceName']
            if not len(affectedSources):
                index += [i]
            elif sourceName == affectedSources[-1]:
                index += [i]
            else:
                indices.append(index)
                affectedSources.append(sourceName)
                index = [i]
            i += 1
        indices.append(index)
        affectedSources.append(sourceName)

        affectedSourceIndex = -1
        for affectedSource in affectedSources:
            affectedSourceIndex += 1
            selectionList = []
            lastEvent = None
            for source in self.sourceList:
                if source.sourceName == affectedSource:
                    for selIndex in indices[affectedSourceIndex]:
                        sel = sel_list[selIndex]
                        #The dispatcher should be a singleton to work properly
                        #implement a patch to make sure it is the targeted widget
                        targetwidgetid = sel.get('targetwidgetid', None)
                        if targetwidgetid not in [None, id(self)]:
                            continue
                        ddict = {}
                        ddict.update(sel)
                        ddict["event"]  = event
                        if lastEvent is None:
                            lastEvent = event
                        #we have found the source
                        #this recovers the data and the info
                        
                        #this creates a data object that is passed to everybody so
                        #there is only one read out.
                        #I should create a weakref to it in order to be informed
                        #about its deletion.
                        addToPoller = False
                        if source.sourceType == "SPS":
                            addToPoller = True
                        elif "addToPoller" in sel:
                            if sel["addToPoller"]:
                                addToPoller = True
                        if not addToPoller:
                            try:
                                dataObject = source.getDataObject(sel['Key'],
                                                        selection=sel['selection'])
                            except Exception:
                                if _logger.getEffectiveLevel() == logging.DEBUG:
                                    raise
                                error = sys.exc_info()
                                text = "Failed to read data source.\n"
                                text += "Source: %s\n" % source.sourceName
                                text += "Key: %s\n"  % sel['Key']
                                text += "Error: %s" % error[1]
                                self._stopAutoRefresh()
                                msg = qt.QMessageBox(self)
                                msg.setWindowTitle('Source Error')
                                msg.setIcon(qt.QMessageBox.Critical)
                                msg.setInformativeText(text)
                                msg.setDetailedText(\
                                    traceback.format_exc())
                                msg.exec()
                                continue
                        else:
                            dataObject = source.getDataObject(sel['Key'],
                                                        selection=sel['selection'],
                                                        poll=False)
                            if dataObject is not None:
                                dataObject.info['legend'] = sel['legend']
                                dataObject.info['targetwidgetid'] = targetwidgetid
                                source.addToPoller(dataObject)
                            else:
                                #this may happen on deletion??
                                return
                            if sel['Key'] == "SCAN_D":
                                # I have to inform the widget about any possible
                                # change in the associated environment
                                #print source.sourceType
                                #print source.sourceName
                                #print sel['Key']
                                #print self.selectorWidget[source.sourceType]
                                pass

                        ddict['dataobject'] = dataObject
                        selectionList.append(ddict)
                        if lastEvent != event:
                            if event.lower() == "addselection":
                                self.sigAddSelection.emit(selectionList)
                                selectionList = []
                            elif event.lower() == "replaceselection":
                                self.sigReplaceSelection.emit(selectionList)
                                selectionList = []
                            elif event.lower() == "removeselection":
                                self.sigRemoveSelection.emit(selectionList)
                                selectionList = []
                            else:
                                _logger.warning("Unhandled dispatcher event = %s", event)
                                del selectionList[-1]
            if len(selectionList):
                if event.lower() == "addselection":
                    self.sigAddSelection.emit(selectionList)
                elif event.lower() == "replaceselection":
                    self.sigReplaceSelection.emit(selectionList)
                elif event.lower() == "removeselection":
                    self.sigRemoveSelection.emit(selectionList)
            lastEvent = None

    def _removeSelectionSlot(self, sel_list):
        _logger.debug("_removeSelectionSlot")
        _logger.debug("sel_list = %s", sel_list)
        for sel in sel_list:
            ddict = {}
            ddict.update(sel)
            ddict["event"] = "removeSelection"
            self.sigRemoveSelection.emit(ddict)

    def _replaceSelectionSlot(self, sel_list):
        _logger.debug("_replaceSelectionSlot")
        _logger.debug("sel_list = %s", sel_list)

        if len(sel_list) == 1:
            self._addSelectionSlot([sel_list[0]], event="replaceSelection")
        elif len(sel_list) > 1:
            self._addSelectionSlot([sel_list[0]], event="replaceSelection")
            self._addSelectionSlot(sel_list[1:], event="addSelection")

    def _otherSignalsSlot(self, ddict):
        self.sigOtherSignals.emit(ddict)

    def _sourceSelectorSlot(self, ddict):
        _logger.debug("_sourceSelectorSlot(self, ddict)")
        _logger.debug("ddict = %s", ddict)
        if ddict["event"] == "NewSourceSelected":
            # use the supplied filter in case of HDF5-like (silx)
            ffilter = ddict.get("filter", "None")
            if ffilter in [None, "None"]:
                source_type = None
            elif ffilter.startswith("HDF5"):
                source_type = QDataSource.NexusDataSource.SOURCE_TYPE
            else:
                source_type = None
            source = QDataSource.QDataSource(ddict["sourcelist"], source_type=source_type)
            self.sourceList.append(source)
            sourceType = source.sourceType
            self.selectorWidget[sourceType].setDataSource(source)
            self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
            #if sourceType == "SPS":
            if hasattr(source, "sigUpdated"):
                _logger.debug("connecting source of type %s" % sourceType)
                source.sigUpdated.connect(self._selectionUpdatedSlot)

        elif ddict["event"] in ("SourceSelected", "SourceReloaded",
                                  "SourceAutoRefreshed"):
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                _logger.debug("WARNING: source not found")
                return
            sourceType = source.sourceType
            selectorWidget = self.selectorWidget[sourceType]
            if ddict["event"] == "SourceReloaded":
                # Protect refresh against rage clicking.
                if self._refreshInProgress:
                    _logger.debug("Refresh already in progress, ignoring")
                    return
                self._refreshInProgress = True
                refresh_btn = getattr(self.sourceSelector, 'refreshButton', None)
                f5_sc = getattr(self.sourceSelector, 'f5Shortcut', None)
                if refresh_btn:
                    refresh_btn.setEnabled(False)
                if f5_sc:
                    f5_sc.setEnabled(False)
                qt.QApplication.setOverrideCursor(
                    qt.QCursor(qt.Qt.WaitCursor))
                try:
                    # Tree-state save/restore is HDF5-only
                    if sourceType == "HDF5":
                        selectorWidget.hdf5Widget.saveTreeState()
                    source.refresh()
                    selectorWidget.setDataSource(source)
                except Exception:
                    _logger.error("source.refresh() failed: %s",
                                  sys.exc_info()[1])
                    if sourceType == "HDF5":
                        selectorWidget.hdf5Widget.clearSavedTreeState()
                finally:
                    self.tabWidget.setCurrentWidget(selectorWidget)
                    self._refreshInProgress = False
                    if refresh_btn:
                        refresh_btn.setEnabled(True)
                    if f5_sc:
                        f5_sc.setEnabled(True)
                    qt.QApplication.restoreOverrideCursor()
            elif ddict["event"] == "SourceAutoRefreshed":
                # Auto-refresh is HDF5-only; silently ignore for others
                if sourceType != "HDF5":
                    _logger.debug("Auto-refresh ignored for source. " \
                                  "Should not appear as the Auto-refresh is supposed to be unavailable.")
                    return
                try:
                    selectorWidget._autoRefreshDatasets(source)
                    self._autoRefreshFailures = 0
                except Exception:
                    n = self._autoRefreshFailures + 1
                    self._autoRefreshFailures = n
                    if n >= 3:
                        _logger.error(
                            "Auto-refresh failed %d times in a row, stopping: %s",
                            n, sys.exc_info()[1])
                        self._autoRefreshFailures = 0
                        self._stopAutoRefresh()
                    else:
                        _logger.warning(
                            "Auto-refresh attempt failed, will retry in one second"
                            )
            else: # SourceSelected
                selectorWidget.setDataSource(source)
                self.tabWidget.setCurrentWidget(selectorWidget)

        elif ddict["event"] == "SourceClosed":
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                _logger.debug("WARNING: source not found")
                return
            sourceType = source.sourceType
            del self.sourceList[self.sourceList.index(source)]
            for source in self.sourceList:
                if sourceType == source.sourceType:
                    self.selectorWidget[sourceType].setDataSource(source)
                    self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
                    return
            #there is no other selection of that type
            if len(self.sourceList):
                source = self.sourceList[0]
                sourceType = source.sourceType
                self.selectorWidget[sourceType].setDataSource(source)
            else:
                self.selectorWidget[sourceType].setDataSource(None)
            self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
        elif ddict["event"] == "SourceClosed":
            _logger.debug("not implemented yet")

    def _selectionUpdatedSlot(self, ddict):
        _logger.debug("_selectionUpdatedSlot(self, dict=%s)", ddict)
        if 'selectionlist' in ddict:
            sel_list = ddict['selectionlist']
        else:
            sel_list = []
            for objectReference in ddict["id"]:
                targetwidgetid = ddict.get('targetwidgetid', None)
                if targetwidgetid not in [None, id(self)]:
                    continue
                sel = {}
                sel['SourceName'] = ddict['SourceName']
                sel['SourceType'] = ddict['SourceType']
                sel['Key']        = ddict['Key']
                sel['selection']  = ddict['selection']
                sel['legend']     = ddict['legend']
                sel['scanselection']  = ddict['scanselection']
                sel['imageselection']  = ddict['imageselection']
                sel_list.append(sel)
        self._addSelectionSlot(sel_list)

    def _tabChanged(self, value):
        _logger.debug("self._tabChanged(value), value =  %s", value)
        text = str(self.tabWidget.tabText(value))
        ddict = {}
        ddict['SourceType'] = text
        if self.selectorWidget[text].data is not None:
            ddict['SourceType'] = self.selectorWidget[text].data.sourceType
            ddict['SourceName'] = self.selectorWidget[text].data.sourceName
        else:
            ddict['SourceName'] = None
        ddict['event'] = "SourceTypeChanged"
        self.sigOtherSignals.emit(ddict)

    def _pluginsClicked(self):
        ddict = {}
        value = self.tabWidget.currentIndex()
        text = str(self.tabWidget.tabText(value))
        ddict['SourceType'] = text
        if self.selectorWidget[text].data is not None:
            ddict['SourceType'] = self.selectorWidget[text].data.sourceType
            ddict['SourceName'] = self.selectorWidget[text].data.sourceName
        else:
            ddict['SourceName'] = None
        _logger.info("%s", ddict)
        _logger.info("===========================")
        for source in self.sourceList:
            _logger.info(source)
            _logger.info(source.sourceType)
            sourceType = source.sourceType
            _logger.info(self.selectorWidget[sourceType].currentSelectionList())

        # this seems unused (info is not defined)
        # if self.pluginsCallback is not None:
        #     self.pluginsCallback(info)


def test():
    app = qt.QApplication([])
    w = QDispatcher()
    w.show()
    app.lastWindowClosed.connect(app.quit)
    app.exec()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test()
