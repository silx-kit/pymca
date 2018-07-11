#/*##########################################################################
# Copyright (C) 2004-2018 V.A. Sole, ESRF - D. Dale CHESS
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
__author__ = "Darren Dale (CHESS) & V.A. Sole (ESRF)"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import os
import posixpath
import gc
import re
from operator import itemgetter
import logging

import h5py
import weakref

try:
    from silx.io import is_group
    from silx.io import open as h5open
    import logging
    logging.getLogger("silx.io.fabioh5").setLevel(logging.CRITICAL)
except ImportError:
    def is_group(node):
        return isinstance(node, h5py.Group)

    def h5open(filename):
        return h5py.File(filename, "r")

from PyMca5.PyMcaGui import PyMcaQt as qt
safe_str = qt.safe_str

if hasattr(qt, 'QStringList'):
    MyQVariant = qt.QVariant
else:
    def MyQVariant(x=None):
        return x


_logger = logging.getLogger(__name__)

QVERSION = qt.qVersion()


#sorting method
def h5py_sorting(object_list):
    sorting_list = ['start_time', 'end_time', 'name']
    n = len(object_list)
    if n < 2:
        return object_list

    # we have received items, not values
    # perform a first sort based on received names
    # this solves a problem with Eiger data where all the
    # external data have the same posixName. Without this sorting
    # they arrive "unsorted"
    object_list.sort()
    try:
        posixNames = [item[1].name for item in object_list]
    except AttributeError:
        # Typical of broken external links
        _logger.debug("HDF5Widget: Cannot get posixNames")
        return object_list

    # This implementation only sorts entries
    if posixpath.dirname(posixNames[0]) != "/":
        return object_list

    sorting_key = None
    if hasattr(object_list[0][1], "items"):
        for key in sorting_list:
            if key in [x[0] for x in object_list[0][1].items()]:
                sorting_key = key
                break

    if sorting_key is None:
        if 'name' in sorting_list:
            sorting_key = 'name'
        else:
            return object_list

    try:
        if sorting_key != 'name':
            sorting_list = [(o[1][sorting_key].value, o)
                           for o in object_list]
            sorted_list = sorted(sorting_list, key=itemgetter(0))
            return [x[1] for x in sorted_list]

        if sorting_key == 'name':
            sorting_list = [(_get_number_list(o[1].name),o)
                           for o in object_list]
            sorting_list.sort()
            return [x[1] for x in sorting_list]
    except:
        #The only way to reach this point is to have different
        #structures among the different entries. In that case
        #defaults to the unfiltered case
        print("WARNING: Default ordering")
        print("Probably all entries do not have the key %s" % sorting_key)
        return object_list

def _get_number_list(txt):
    rexpr = '[/a-zA-Z:-]'
    nbs= [float(w) for w in re.split(rexpr, txt) if w not in ['',' ']]
    return nbs

class BrokenLink(object):
    pass

class QRLock(qt.QMutex):

    """
    """

    def __init__(self):
        qt.QMutex.__init__(self, qt.QMutex.Recursive)

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, type, value, traceback):
        self.unlock()


class RootItem(object):

    @property
    def children(self):
        return self._children

    @property
    def hasChildren(self):
        if len(self._children):
            return True
        else:
            return False

    @property
    def header(self):
        return self._header

    @property
    def parent(self):
        return None

    def __init__(self, header):
        self._header = header
        self._children = []
        self._identifiers = []

    def __iter__(self):
        def iter_files(files):
            for f in files:
                yield f
        return iter_files(self.children)

    def __len__(self):
        return len(self.children)

    def appendChild(self, item):
        self.children.append(H5FileProxy(item, self))
        self._identifiers.append(id(item))

    def deleteChild(self, child):
        idx = self._children.index(child)
        del self._children[idx]
        del self._identifiers[idx]

class H5NodeProxy(object):
    @property
    def children(self):
        if not self.hasChildren:
            return []

        if not self._children:
            # obtaining the lock here is necessary, otherwise application can
            # freeze if navigating tree while data is processing
            if 1: #with self.file.plock:
                items = list(self.getNode(self.name).items())
                if posixpath.dirname(self.name) == "/":
                    # top level item
                    doit = True
                else:
                    doit = False
                try:
                    # better handling of external links
                    finalList = h5py_sorting(items)
                    for i in range(len(finalList)):
                        if finalList[i][1] is not None:
                            finalList[i][1]._posixPath = posixpath.join(self.name,
                                                               finalList[i][0])
                        else:
                            finalList[i] = [x for x in finalList[i]]
                            finalList[i][1] = BrokenLink()
                            finalList[i][1]._posixPath = posixpath.join(self.name,
                                                               finalList[i][0])
                    self._children = [H5NodeProxy(self.file, i[1], self)
                                      for i in finalList]
                except:
                    #one cannot afford any error, so I revert to the old
                    # method where values where used instead of items
                    if _logger.getEffectiveLevel() == logging.DEBUG:
                        raise
                    else:
                        # tmpList = list(self.getNode(self.name).values())
                        # spech5 does not implement values() prior to silx 0.6.0
                        tmpList = list(map(self.getNode(self.name).__getitem__,
                                           self.getNode(self.name).keys()))
                        finalList = tmpList
                    for i in range(len(finalList)):
                        finalList[i]._posixPath = posixpath.join(self.name,
                                                               items[i][0])
                    self._children = [H5NodeProxy(self.file, i, self)
                                      for i in finalList]
        return self._children

    @property
    def file(self):
        return self._file

    @property
    def hasChildren(self):
        return self._hasChildren

    @property
    def name(self):
        return self._name

    @property
    def row(self):
        if 1:#with self.file.plock:
            try:
                return self.parent.children.index(self)
            except ValueError:
                return
    @property
    def type(self):
        return self._type

    @property
    def shape(self):
        if type(self._shape) == type(""):
            return self._shape
        if len(self._shape) == 1:
            return "%d" % self._shape[0]
        elif len(self._shape) > 1:
            text = "%d" % self._shape[0]
            for a in range(1, len(self._shape)):
                text += " x %d" % self._shape[a]
            return text
        else:
            return ""

    @property
    def dtype(self):
        return self._dtype

    @property
    def parent(self):
        return self._parent

    #@property
    #def attrs(self):
    #    return self._attrs

    @property
    def color(self):
        return self._color

    def __init__(self, ffile, node, parent=None, path=None):
        if 1:#with ffile.plock:
            self._file = ffile
            self._parent = parent
            if hasattr(node, '_posixPath'):
                self._name = node._posixPath
            else:
                self._name = node.name
            """
            if hasattr(node, "_sourceName"):
                self._name = node._sourceName
            else:
                self._name = posixpath.basename(node.name)
            """
            self._type = type(node).__name__

            self._hasChildren = is_group(node)
            #self._attrs = []
            self._color = qt.QColor(qt.Qt.black)
            if hasattr(node, 'attrs'):
                attrs = list(node.attrs)
                for cname in ['class', 'NX_class']:
                    if cname in attrs:
                        nodeattr = node.attrs[cname]
                        if sys.version <'3.0':
                            _type = "%s" % nodeattr
                        elif hasattr(nodeattr, "decode"):
                            _type = nodeattr.decode('utf=8')
                        else:
                            _type = "%s" % nodeattr
                        self._type = _type
                        if _type in ["NXdata"]:
                            self._color = qt.QColor(qt.Qt.blue)
                        elif _type in ["NXroot", "NXentry"] and ("default" in attrs):
                            self._color = qt.QColor(qt.Qt.blue)                        
                        #self._attrs = attrs
                        break
                        #self._type = _type[2].upper() + _type[3:]
            self._children = []
            if hasattr(node, 'dtype'):
                self._dtype = safe_str(node.dtype)
            else:
                self._dtype = ""
            if hasattr(node, 'shape'):
                if 0:
                    self._shape = safe_str(node.shape)
                else:
                    self._shape = node.shape
            else:
                self._shape = ""

    def clearChildren(self):
        self._children = []
        self._hasChildren = False

    def getNode(self, name=None):
        if not name:
            name = self.name
        return self.file[name]

    def __len__(self):
        return len(self.children)


class H5FileProxy(H5NodeProxy):

    @property
    def name(self):
        return '/'

    @property
    def filename(self):
        return self._filename

    def __init__(self, ffile, parent=None):
        super(H5FileProxy, self).__init__(ffile, ffile, parent)
        self._name = ffile.name
        self._filename = self.file.name

    def close(self):
        if 1: # with self.file.plock:
            return self.file.close()

    def __getitem__(self, path):
        if path == '/':
            return self
        else:
            return H5NodeProxy(self.file, self.file[path], self)


class FileModel(qt.QAbstractItemModel):
    """
    """
    sigFileUpdated = qt.pyqtSignal(object)
    sigFileAppended = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        qt.QAbstractItemModel.__init__(self, parent)
        self.rootItem = RootItem(['File/Group/Dataset', 'Description', 'Shape', 'DType'])
        self._idMap = {qt.QModelIndex().internalId(): self.rootItem}

    def clearRows(self, index):
        self.getProxyFromIndex(index).clearChildren()

    def close(self):
        for item in self.rootItem:
            item.close()
        self._idMap = {}

    def columnCount(self, parent):
        return 4

    def data(self, index, role):
        if role == qt.Qt.DisplayRole:
            item = self.getProxyFromIndex(index)
            column = index.column()
            if column == 0:
                if isinstance(item, H5FileProxy):
                    return MyQVariant(os.path.basename(item.file.filename))
                else:
                    if hasattr(item, "name"):
                        return MyQVariant(posixpath.basename(item.name))
                    else:
                        # this can only happen with the root
                        return MyQVariant("/")
            if column == 1:
                showtitle = True
                if showtitle:
                    if hasattr(item, 'type'):
                        if item.type in ["Entry", "NXentry"]:
                            children = item.children
                            names = [posixpath.basename(o.name) for o in children]
                            if "title" in names:
                                idx = names.index("title")
                                if len(children[idx].getNode().shape):
                                    #stored as an array of strings!!!
                                    #return just the first item
                                    return MyQVariant("%s" % children[idx].getNode().value[0])
                                else:
                                    #stored as a string
                                    return MyQVariant("%s" % children[idx].getNode().value)
                return MyQVariant(item.type)
            if column == 2:
                return MyQVariant(item.shape)
            if column == 3:
                return MyQVariant(item.dtype)
        elif role == qt.Qt.ForegroundRole:
            item = self.getProxyFromIndex(index)
            column = index.column()
            if column == 0:
                if hasattr(item, "color"):
                    return MyQVariant(qt.QColor(item.color))
        elif role == qt.Qt.ToolTipRole:
            item = self.getProxyFromIndex(index)
            if hasattr(item, "color"):
                if item.color == qt.Qt.blue:
                    return MyQVariant("Item has a double click NXdata associated action")
        return MyQVariant()

    def getNodeFromIndex(self, index):
        try:
            return self.getProxyFromIndex(index).getNode()
        except AttributeError:
            return None

    def getProxyFromIndex(self, index):
        try:
            return self._idMap[index.internalId()]
        except KeyError:
            try:
                #Linux 32-bit problem
                return self._idMap[index.internalId() & 0xFFFFFFFF]
            except KeyError:
                return self.rootItem

    def hasChildren(self, index):
        return self.getProxyFromIndex(index).hasChildren

    def headerData(self, section, orientation, role):
        if orientation == qt.Qt.Horizontal and \
                role == qt.Qt.DisplayRole:
            return MyQVariant(self.rootItem.header[section])

        return MyQVariant()

    def hasIndex(self, row, column, parent):
        parentItem = self.getProxyFromIndex(parent)
        if row >= len(parentItem.children):
            return False
        return True

    def index(self, row, column, parent):
        parentItem = self.getProxyFromIndex(parent)
        if row >= len(parentItem.children):
            return qt.QModelIndex()
        child = parentItem.children[row]
        #force a pointer to child and not use id(child)
        index = self.createIndex(row, column, child)
        self._idMap.setdefault(index.internalId(), child)
        return index

    def parent(self, index):
        child = self.getProxyFromIndex(index)
        parent = child.parent
        if parent == self.rootItem:
            return qt.QModelIndex()
        if parent is None:
            return qt.QModelIndex()
        if parent.row is None:
            return qt.QModelIndex()
        else:
            return self.createIndex(parent.row, 0, parent)

    def rowCount(self, index):
        return len(self.getProxyFromIndex(index))

    def openFile(self, filename, weakreference=False):
        gc.collect()
        for item in self.rootItem:
            if item.file.filename == filename:
                ddict = {}
                ddict['event'] = "fileUpdated"
                ddict['filename'] = filename
                self.sigFileUpdated.emit(ddict)
                return item.file
        phynxFile = h5open(filename)
        if weakreference:
            def phynxFileInstanceDistroyed(weakrefObject):
                idx = self.rootItem._identifiers.index(id(weakrefObject))
                child = self.rootItem._children[idx]
                child.clearChildren()
                del self._idMap[id(child)]
                self.rootItem.deleteChild(child)
                if not self.rootItem.hasChildren:
                    self.clear()
                return
            refProxy = weakref.proxy(phynxFile, phynxFileInstanceDistroyed)
            self.rootItem.appendChild(refProxy)
        else:
            self.rootItem.appendChild(phynxFile)
        ddict = {}
        ddict['event'] = "fileAppended"
        ddict['filename'] = filename
        self.sigFileAppended.emit(ddict)
        return phynxFile

    def appendPhynxFile(self, phynxFile, weakreference=True):
        """
        I create a weak reference to a phynx file instance, get informed when
        the instance disappears, and delete the entry from the view
        """
        if hasattr(phynxFile, "_sourceName"):
            name = phynxFile._sourceName
        else:
            name = phynxFile.name
        gc.collect()
        present = False
        for child in self.rootItem:
            if child.file.filename == name:
                #already present
                present = True
                break

        if present:
            ddict = {}
            ddict['event'] = "fileUpdated"
            ddict['filename'] = name
            self.sigFileUpdated.emit(ddict)
            return

        if weakreference:
            def phynxFileInstanceDistroyed(weakrefObject):
                idx = self.rootItem._identifiers.index(id(weakrefObject))
                child = self.rootItem._children[idx]
                child.clearChildren()
                del self._idMap[id(child)]
                self.rootItem.deleteChild(child)
                if not self.rootItem.hasChildren:
                    self.clear()
                return
            phynxFileProxy = weakref.proxy(phynxFile, phynxFileInstanceDistroyed)
            self.rootItem.appendChild(phynxFileProxy)
        else:
            self.rootItem.appendChild(phynxFile)
        ddict = {}
        ddict['event'] = "fileAppended"
        ddict['filename'] = name
        self.sigFileAppended.emit(ddict)

    def clear(self):
        _logger.debug("Clear called")
        # reset is considered obsolete under Qt 5.
        if hasattr(self, "reset"):
            self.reset()
        else:
            rootItem = self.rootItem
            self.beginResetModel()
            #for idx in range(len(rootItem._children)):
            #    child = rootItem._children[idx]
            #    child.clearChildren()
            #    del self._idMap[id(child)]
            #    rootItem.deleteChild(child)
            rootItem.children.clear()
            self.endResetModel()

class FileView(qt.QTreeView):

    sigHDF5WidgetSignal = qt.pyqtSignal(object)

    def __init__(self, fileModel, parent=None):
        qt.QTreeView.__init__(self, parent)
        self.setModel(fileModel)
        self.setColumnWidth(0, 250)
        #This removes the children after a double click
        #with no possibility to recover them
        #self.collapsed[QModelIndex].connect(fileModel.clearRows)
        fileModel.sigFileAppended.connect(self.fileAppended)
        fileModel.sigFileUpdated.connect(self.fileUpdated)

    def fileAppended(self, ddict=None):
        self.doItemsLayout()
        if ddict is None:
            return
        self.fileUpdated(ddict)


    def fileUpdated(self, ddict):
        rootModelIndex = self.rootIndex()
        if self.model().hasChildren(rootModelIndex):
            rootItem = self.model().getProxyFromIndex(rootModelIndex)
            for row in range(len(rootItem)):
                if self.model().hasIndex(row, 0, rootModelIndex):
                    modelIndex = self.model().index(row, 0, rootModelIndex)
                    item = self.model().getProxyFromIndex(modelIndex)
                    if item.name == ddict['filename']:
                        self.selectionModel().setCurrentIndex(modelIndex,
                                              qt.QItemSelectionModel.NoUpdate)
                        self.scrollTo(modelIndex,
                                      qt.QAbstractItemView.PositionAtTop)
                        break
        self.doItemsLayout()


class HDF5Widget(FileView):
    def __init__(self, model, parent=None):
        FileView.__init__(self, model, parent)
        self.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self._adjust()
        if 0:
            self.activated[qt.QModelIndex].connect(self.itemActivated)

        self.clicked[qt.QModelIndex].connect(self.itemClicked)
        self.doubleClicked[qt.QModelIndex].connect(self.itemDoubleClicked)
        self.collapsed[qt.QModelIndex].connect(self._adjust)
        self.expanded[qt.QModelIndex].connect(self._adjust)

    def _adjust(self, modelIndex=None):
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)

    def mousePressEvent(self, e):
        button = e.button()
        if button == qt.Qt.LeftButton:
            self._lastMouse = "left"
        elif button == qt.Qt.RightButton:
            self._lastMouse = "right"
        elif button == qt.Qt.MidButton:
            self._lastMouse = "middle"
        else:
            #Should I set it to no button?
            self._lastMouse = "left"
        qt.QTreeView.mousePressEvent(self, e)
        if self._lastMouse != "left":
            # Qt5 only sends itenClicked on left button mouse click
            if QVERSION > "5":
                event = "itemClicked"
                modelIndex = self.indexAt(e.pos())
                self.emitSignal(event, modelIndex)

    def itemActivated(self, modelIndex):
        event = "itemActivated"
        self.emitSignal(event, modelIndex)

    def itemClicked(self, modelIndex):
        event ="itemClicked"
        self.emitSignal(event, modelIndex)

    def itemDoubleClicked(self, modelIndex):
        event ="itemDoubleClicked"
        self.emitSignal(event, modelIndex)

    def selectionChanged(self, selected, deselected):
        super(HDF5Widget, self).selectionChanged(selected, deselected)
        event = "itemSelectionChanged"
        modelIndex = self.currentIndex()
        self.emitSignal(event, modelIndex)

    def emitSignal(self, event, modelIndex):
        if self.model() is None:
            return
        item = self.model().getProxyFromIndex(modelIndex)
        if QVERSION > "5":
            # prevent crash clicking on empty space
            if not hasattr(item, "file"):
                # RootItem
                return
        ddict = {}
        ddict['event'] = event
        ddict['file']  = item.file.filename
        ddict['name']  = item.name
        ddict['type']  = item.type
        ddict['dtype'] = item.dtype
        ddict['shape'] = item.shape
        ddict['color'] = item.color
        ddict['mouse'] = self._lastMouse * 1
        self.sigHDF5WidgetSignal.emit(ddict)

    def getSelectedEntries(self):
        modelIndexList = self.selectedIndexes()
        entryList = []
        analyzedPaths = []
        for modelIndex in modelIndexList:
            item = self.model().getProxyFromIndex(modelIndex)
            path = item.name * 1
            if path in analyzedPaths:
                continue
            else:
                analyzedPaths.append(path)
            if item.type in ["weakproxy", "File"]:
                continue
            entry = "/" + path.split("/")[1]
            if entry not in entryList:
                entryList.append((entry, item.file.filename))
        return entryList


class Hdf5SelectionDialog(qt.QDialog):
    """Dialog widget to select a HDF5 item in a file.

    It is composed of a :class:`HDF5Widget` tree view,
    and two buttons Ok and Cancel.

    When the dialog's execution is ended with a click on the OK button,
    or with a double-click on an item of the proper type, the URI of
    the selected item will be available in attribute :attr:`selectedItemUri`.

    If the user clicked cancel or closed the dialog
    without selecting an item, :attr:`selectedItemUri` will be None."""
    datasetTypes = ['dataset',
                    'spech5dataset', 'spech5linktodataset',  # spech5
                    'framedata', 'rawheaderdata']            # fabioh5

    def __init__(self, parent=None,
                 filename=None, message=None, itemtype="any"):
        """

        :param filename: Name of the HDF5 file
        :param value: If True returns dataset value instead of just the dataset.
            This must be False if itemtype is not "dataset".
        :param str itemtype: "dataset" or "group" or "any" (default)
        """
        message = message if message is not None else 'Select your item'
        self.itemtype = itemtype if itemtype is not None else "any"

        if self.itemtype not in ["any", "dataset", "group"]:
            raise AttributeError(
                    "Invalid itemtype %s, should be 'group', 'dataset' or 'any'" % itemtype)

        if filename is None:
            filename = _getFilenameDialog()
        if filename is None:
            raise IOError("No filename specified")

        qt.QDialog.__init__(self, parent)

        self.setWindowTitle(message)
        mainLayout = qt.QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.fileModel = FileModel()
        self.fileView = HDF5Widget(self.fileModel)
        self.filename = filename

        self.fileView.sigHDF5WidgetSignal.connect(self._hdf5WidgetSlot)

        mainLayout.addWidget(self.fileView)

        buttonContainer = qt.QWidget(self)
        buttonContainerLayout = qt.QHBoxLayout(buttonContainer)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        self.okb = qt.QPushButton("OK", buttonContainer)
        cancelb = qt.QPushButton("Cancel", buttonContainer)

        self.okb.clicked.connect(self.onOk)
        self.okb.setEnabled(False)    # requires item to be clicked or activated
        cancelb.clicked.connect(self.reject)

        buttonContainerLayout.addWidget(self.okb)
        buttonContainerLayout.addWidget(cancelb)

        mainLayout.addWidget(buttonContainer)

        self.resize(400, 200)
        self.selectedItemUri = None
        """URI of selected HDF5 item, with format 'filename::item_name'
        """

        self._lastEvent = None
        """Dictionary with info about latest event"""

    def _hdf5WidgetSlot(self, ddict):
        self._lastEvent = ddict
        eventType = ddict['type'].lower()

        isExpectedType = self.itemtype.lower() == "any" or \
                (eventType in self.datasetTypes and self.itemtype == "dataset") or \
                (eventType not in self.datasetTypes and self.itemtype == "group")

        if isExpectedType:
            self.okb.setEnabled(True)
        else:
            self.okb.setEnabled(False)

        if ddict['event'] == "itemDoubleClicked":
            if isExpectedType:
                self.selectedItemUri = ddict['file'] + "::" + ddict['name']
                self.accept()

    def onOk(self):
        self.selectedItemUri = self._lastEvent['file'] + "::" + self._lastEvent['name']
        self.accept()

    def exec_(self):
        with h5open(self.filename) as hdf5File:
            self.fileModel.appendPhynxFile(hdf5File, weakreference=True)
            ret = qt.QDialog.exec_(self)
        return ret


def _getFilenameDialog():
    """Open a dialog to select a file in a filesystem tree view.
    Return the selected filename."""
    from PyMca5.PyMcaGui.io import PyMcaFileDialogs
    fileTypeList = ['HDF5 Files (*.h5 *.nxs *.hdf)',
                    'HDF5 Files (*)']
    message = "Open HDF5 file"
    filenamelist, ffilter = PyMcaFileDialogs.getFileList(parent=None,
                                filetypelist=fileTypeList,
                                message=message,
                                getfilter=True,
                                single=True,
                                currentfilter=None)
    if len(filenamelist) < 1:
        return None
    return filenamelist[0]


def getDatasetValueDialog(filename=None, message=None):
    """Open a dialog to select a dataset in a HDF5 file.
    Return the value of the dataset.

    If the dataset selection was cancelled, None is returned.

    :param str filename: HDF5 file path. If None, a file dialog
        is used to select the file.
    :param str message: Message used as window title for dialog
    :return: HDF5 dataset as numpy array, or None
    """
    hdf5Dialog = Hdf5SelectionDialog(None, filename, message,
                                     "dataset")
    ret = hdf5Dialog.exec_()
    if not ret:
        return None

    selectedHdf5Uri = hdf5Dialog.selectedItemUri

    with h5open(filename) as hdf5File:
        hdf5Item = hdf5File[selectedHdf5Uri.split("::")[-1]]
        data = hdf5Item.value

    return data


def getDatasetDialog(filename=None, value=False, message=None):
    # function kept for backward compatibility, in case someone
    # uses it with value=False outside PyMca5
    if value:
        return getDatasetValueDialog(filename, message)

    hdf5Dialog = Hdf5SelectionDialog(None, filename, message,
                                     "dataset")
    ret = hdf5Dialog.exec_()
    if not ret:
        return None
    selectedHdf5Uri = hdf5Dialog.selectedItemUri
    hdf5File = h5open(filename)
    return hdf5File[selectedHdf5Uri.split("::")[-1]]


def getGroupNameDialog(filename=None, message=None):
    """Open a dialog to select a group in a HDF5 file.
    Return the name of the group.

    :param str filename: HDF5 file path. If None, a file dialog
        is used to select the file.
    :param str message: Message used as window title for dialog
    :return: HDF5 group name
    """
    hdf5Dialog = Hdf5SelectionDialog(None, filename, message,
                                     "group")
    ret = hdf5Dialog.exec_()
    if not ret:
        return None

    selectedHdf5Uri = hdf5Dialog.selectedItemUri

    return selectedHdf5Uri.split("::")[-1]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("python HDF5Widget.py path_to_hdf5_file_name")
        sys.exit(0)
    app = qt.QApplication(sys.argv)
    fileModel = FileModel()
    fileView = HDF5Widget(fileModel)
    phynxFile = fileModel.openFile(sys.argv[1])
    def mySlot(ddict):
        print(ddict)
        if ddict['type'].lower() in Hdf5SelectionDialog.datasetTypes:
            print(phynxFile[ddict['name']].dtype, phynxFile[ddict['name']].shape)
    fileView.sigHDF5WidgetSignal.connect(mySlot)
    fileView.show()
    sys.exit(app.exec_())
