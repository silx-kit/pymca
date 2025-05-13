#/*##########################################################################
# Copyright (C) 2004-2025 V.A. Sole, ESRF - D. Dale CHESS
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
__author__ = "Darren Dale (CHESS) & V.A. Sole (ESRF)"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import os
import posixpath
import gc
import logging
_logger = logging.getLogger(__name__)

if "hdf5plugin" not in sys.modules:
    # try to import hdf5plugins
    try:
        import hdf5plugin
    except Exception:
        _logger.info("Cannot import hdf5plugin")
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
        try:
            return h5py.File(filename, "r")
        except OSError:
            if h5py.version.hdf5_version_tuple < (1, 10):
                # no reason to try SWMR mode
                raise
            _logger.info("Cannot open %s. Trying in SWMR mode" % filename)
            return h5py.File(filename, "r", libver='latest', swmr=True)

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaIO.HDF5Utils import sort_h5items

safe_str = qt.safe_str

if hasattr(qt, 'QStringList'):
    MyQVariant = qt.QVariant
else:
    def MyQVariant(x=None):
        return x

QVERSION = qt.qVersion()


class BrokenLink(object):
    pass


class QRLock(qt.QMutex):
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
    def sortChildren(self, column, order):
        #print("sort children called with ", column, order)
        self.__sorting = True
        if column == 1:
            self.__sorting_list = ["title"]
        else:
            self.__sorting_list = None
        self.__sorting_order = order

    def raw_keys(self):
        for node in self.children:
            yield node.name

    def raw_values(self):
        node = self.getNode(self.name)
        if hasattr(node, "values"):
            return node.values()
        else:
            # spech5 does not implement values() prior to silx 0.6.0
            for _, value in self.raw_items():
                yield value

    def raw_items(self):
        return self.getNode(self.name).items()

    @property
    def children(self):
        if not self.hasChildren:
            return []

        if self.__sorting or not self._children:
            # obtaining the lock here is necessary, otherwise application can
            # freeze if navigating tree while data is processing
            if 1: #with self.file.plock:
                if 1:
                    try:
                        # this returns (str, str) in case of dealing with a broken link
                        items = list(self.raw_items())
                    except Exception:
                        items = []
                        _logger.warning("Cannot obtain items list. Ignoring")
                else:
                    # this returns (str, None) in case of dealing with a broken link
                    items = list(self.getNode(self.name).items())
                try:
                    # better handling of external links
                    finalList = sort_h5items(items, sorting_list=self.__sorting_list)
                    for i in range(len(finalList)):
                        # avoid an error at silx level with the linechecking "if finalList[i][1] and "
                        dataset = finalList[i][1]
                        if dataset is None:
                            finalListIsTrue = False
                        else:
                            finalListIsTrue = True
                        if hasattr(dataset, "shape"):
                            if not len(dataset.shape):
                                # it can still be a string
                                if hasattr(dataset, "dtype"):
                                    if safe_str(dataset.dtype).startswith("|S"):
                                        pass
                                    elif safe_str(dataset.dtype) == "object":
                                        # issue 1059
                                        pass
                                    else:
                                        finalListIsTrue = False
                                else:
                                    finalListIsTrue = False
                        if finalListIsTrue and not isinstance(finalList[i][1], str):
                            finalList[i][1]._posixPath = posixpath.join(self.name,
                                                               finalList[i][0])
                        else:
                            finalList[i] = [x for x in finalList[i]]
                            finalList[i][1] = BrokenLink()
                            finalList[i][1]._posixPath = posixpath.join(self.name,
                                                               finalList[i][0])
                    self._children = [H5NodeProxy(self.file, i[1], self)
                                      for i in finalList]
                except Exception:
                    # one cannot afford any error, so I revert to the old
                    # method where values where used instead of items
                    if 1 or _logger.getEffectiveLevel() == logging.DEBUG:
                        raise
                    tmpList = list(self.raw_values())
                    finalList = tmpList
                    for i in range(len(finalList)):
                        finalList[i]._posixPath = posixpath.join(self.name,
                                                               items[i][0])
                    self._children = [H5NodeProxy(self.file, i, self)
                                      for i in finalList]
        self.__sorting = False
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
        if self._shape is None:
            return ""
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
        self.__sorting = False
        self.__sorting_list = None
        self.__sorting_order = qt.Qt.AscendingOrder
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
                        elif ("default" in attrs):
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
        try:
            return self.file[name]
        except Exception:
            _logger.critical("Cannot access HDF5 file path <%s>" % name)
            return name

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
        return self.file.close()

    def __getitem__(self, path):
        if path == '/':
            return self
        else:
            return H5NodeProxy(self.file, self.file[path], self)

    def raw_keys(self):
        if isinstance(self.file, h5py.File):
            file_path = self.file.filename
            data_path = self.name
            try:
                if sys.platform.startswith("win") and \
                   getattr(sys, 'frozen', False):
                    _logger.debug("Frozen executable. Using standard approach")
                    return self.file[data_path].keys()
                else:
                    from PyMca5.PyMcaIO import HDF5Utils
                    return HDF5Utils.safe_hdf5_group_keys(file_path,
                                                      data_path=data_path)
            except Exception:
                _logger.debug("Using standard approach")
                return self.file[data_path].keys()
        else:
            file_path = self.file.filename
            data_path = self.name
            return self.file[data_path].keys()

    def raw_values(self):
        for _, value in self.raw_items():
            yield value

    def raw_items(self):
        for data_path in self.raw_keys():
            yield data_path, self.getNode(data_path)


class FileModel(qt.QAbstractItemModel):
    """
    """
    sigFileUpdated = qt.pyqtSignal(object)
    sigFileAppended = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        qt.QAbstractItemModel.__init__(self, parent)
        self.rootItem = RootItem(['File/Group/Dataset', 'Description', 'Shape', 'DType'])
        self._idMap = {qt.QModelIndex().internalId(): self.rootItem}

    def sort(self, column, order):
        #print("FileModel sort called with ", column, order)
        for item in self.rootItem:
            item.sortChildren(column, order)

    def clearRows(self, index):
        self.getProxyFromIndex(index).clearChildren()

    def close(self):
        for item in self.rootItem:
            item.close()
        self._idMap = {}

    def columnCount(self, parent):
        return 4

    def data(self, index, role):
        try:
            if role == qt.Qt.DisplayRole:
                item = self.getProxyFromIndex(index)
                column = index.column()
                if column == 0:
                    if isinstance(item, H5FileProxy):
                        try:
                            return MyQVariant(os.path.basename(item.file.filename))
                        except Exception:
                            _logger.critical("Cannot retrieve file name")
                            return MyQVariant("Unknown file. Please refresh")
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
                                if hasattr(item, "children"):
                                    children = item.children
                                    names = [posixpath.basename(o.name) for o in children]
                                    if "title" in names:
                                        idx = names.index("title")
                                        node = children[idx].getNode()
                                        if hasattr(node, "shape") and len(node.shape):
                                            #stored as an array of strings???
                                            #return just the first item
                                            if hasattr(node, "asstr"):
                                                try:
                                                    return MyQVariant("%s" % node.asstr()[()][0])
                                                except Exception:
                                                    return MyQVariant("%s" % node[()][0])
                                        else:
                                            #stored as a string
                                            try:
                                                try:
                                                    return MyQVariant("%s" % node.asstr()[()])
                                                except Exception:
                                                    return MyQVariant("%s" % node[()])
                                            except Exception:
                                                # issue #745
                                                return MyQVariant("Unknown %s" % node)
                                else:
                                    _logger.critical("Entry %s has no children" % item.name)
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
        except Exception:
            return MyQVariant("Unhandled exception filling tree. Reload?")

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
        self.setAutoScroll(False)

        self._adjust()
        if 0:
            self.activated[qt.QModelIndex].connect(self.itemActivated)

        self.clicked[qt.QModelIndex].connect(self.itemClicked)
        self.doubleClicked[qt.QModelIndex].connect(self.itemDoubleClicked)
        self.collapsed[qt.QModelIndex].connect(self._adjust)
        self.expanded[qt.QModelIndex].connect(self._adjust)
        self.setSortingEnabled(False)
        self.header().sectionDoubleClicked[int].connect( \
                         self._headerSectionDoubleClicked)
        tip = "Double click on first two columns to change order"
        self.header().setToolTip(tip)

    def _headerSectionDoubleClicked(self, index):
        self.sortItems(index, qt.Qt.AscendingOrder)

    def __updateOrder(self):
        rootModelIndex = self.rootIndex()
        filelist = []
        if self.model().hasChildren(rootModelIndex):
            rootItem = self.model().getProxyFromIndex(rootModelIndex)
            for row in range(len(rootItem)):
                if self.model().hasIndex(row, 0, rootModelIndex):
                    modelIndex = self.model().index(row, 0, rootModelIndex)
                    item = self.model().getProxyFromIndex(modelIndex)
                    try:
                        filename = item.file.filename
                        if filename not in filelist:
                            filelist.append(filename)
                    except Exception:
                        continue
        if len(filelist):
            for file in filelist:
                ddict = {}
                ddict['event'] = "fileUpdated"
                ddict['filename'] = filename
                self.fileUpdated(ddict)

    def sortByColumn(self, column, order):
        #reimplement QTreeWidget sorting
        _logger.info("sort by column %d setting indicator %s" % (column, order))
        self.setSortingEnabled(True)
        self.header().setSortIndicator(column, order)
        self.__updateOrder()
        self.setSortingEnabled(False)

    def sortItems(self, column, order):
        #reimplement QTreeWidget sorting
        _logger.info("sort items")
        self.sortByColumn(column, order)

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
            # Qt5 only sends itemClicked on left button mouse click
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
        # awful patch to support tiled sources where silx removes "tiled:" from the name
        #if ddict['file'].startswith("http"):
        #    print("TODO: Issue with silx removing tiled: from the file name")
        #    ddict['file'] = "tiled:" + ddict['file']
        ddict['name']  = item.name
        ddict['type']  = item.type
        ddict['dtype'] = item.dtype
        ddict['shape'] = item.shape
        ddict['color'] = item.color
        ddict['mouse'] = getattr(self, '_lastMouse', 'left') * 1
        self.sigHDF5WidgetSignal.emit(ddict)

    def getSelectedEntries(self):
        modelIndexList = self.selectedIndexes()
        entryList = []
        analyzedPaths = []
        for modelIndex in modelIndexList:
            item = self.model().getProxyFromIndex(modelIndex)
            if item.type in ["weakproxy", "File"]:
                continue
            filename = item.file.filename
            path = item.name * 1
            if (path, filename) in analyzedPaths:
                continue
            else:
                analyzedPaths.append((path, filename))
            entry = "/" + path.split("/")[1]
            if (entry, filename) not in entryList:
                entryList.append((entry, filename))
        _logger.info("Returned entryList %s" % entryList)
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
            filename = _getFilenameDialog(parent=parent)
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

    def exec(self):
        with h5open(self.filename) as hdf5File:
            self.fileModel.appendPhynxFile(hdf5File, weakreference=True)
            ret = qt.QDialog.exec(self)
        return ret

    def exec_(self):
        return self.exec()


def _getFilenameDialog(parent=None):
    """Open a dialog to select a file in a filesystem tree view.
    Return the selected filename."""
    from PyMca5.PyMcaGui.io import PyMcaFileDialogs
    fileTypeList = ['HDF5 Files (*.h5 *.nxs *.hdf)',
                    'HDF5 Files (*)']
    message = "Open HDF5 file"
    filenamelist, ffilter = PyMcaFileDialogs.getFileList(parent=parent,
                                filetypelist=fileTypeList,
                                message=message,
                                getfilter=True,
                                single=True,
                                currentfilter=None)
    if len(filenamelist) < 1:
        return None
    return filenamelist[0]


def getDatasetValueDialog(filename=None, message=None, parent=None):
    """Open a dialog to select a dataset in a HDF5 file.
    Return the value of the dataset.

    If the dataset selection was cancelled, None is returned.

    :param str filename: HDF5 file path. If None, a file dialog
        is used to select the file.
    :param str message: Message used as window title for dialog
    :return: HDF5 dataset as numpy array, or None
    """
    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message,
                                     "dataset")
    ret = hdf5Dialog.exec()
    if not ret:
        return None

    selectedHdf5Uri = hdf5Dialog.selectedItemUri

    with h5open(filename) as hdf5File:
        hdf5Item = hdf5File[selectedHdf5Uri.split("::")[-1]]
        data = hdf5Item[()]

    return data

def getDatasetUri(parent=None, filename=None, message=None):
    # TODO: Accept a filter for type of dataset
    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message, "dataset")
    ret = hdf5Dialog.exec()
    if not ret:
        return None
    selectedHdf5Uri = hdf5Dialog.selectedItemUri
    return selectedHdf5Uri

def getGroupUri(parent=None, filename=None, message=None):
    # TODO: Accept a filter for a particular attribute (NXclass)
    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message, "dataset")
    ret = hdf5Dialog.exec()
    if not ret:
        return None
    selectedHdf5Uri = hdf5Dialog.selectedItemUri
    return selectedHdf5Uri

def getUri(parent=None, filename=None, message=None):
    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message, "any")
    ret = hdf5Dialog.exec()
    if not ret:
        return None
    selectedHdf5Uri = hdf5Dialog.selectedItemUri
    return selectedHdf5Uri

def getDatasetDialog(filename=None, value=False, message=None, parent=None):
    # function kept for backward compatibility, in case someone
    # uses it with value=False outside PyMca5
    if value:
        return getDatasetValueDialog(filename=filename, message=message,
                                     parent=parent)

    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message, "dataset")
    ret = hdf5Dialog.exec()
    if not ret:
        return None
    selectedHdf5Uri = hdf5Dialog.selectedItemUri
    hdf5File = h5open(filename)
    return hdf5File[selectedHdf5Uri.split("::")[-1]]


def getGroupNameDialog(filename=None, message=None, parent=None):
    """Open a dialog to select a group in a HDF5 file.
    Return the name of the group.

    :param str filename: HDF5 file path. If None, a file dialog
        is used to select the file.
    :param str message: Message used as window title for dialog
    :return: HDF5 group name
    """
    hdf5Dialog = Hdf5SelectionDialog(parent, filename, message, "group")
    ret = hdf5Dialog.exec()
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
    ret = app.exec()
    app = None
    sys.exit(ret)
