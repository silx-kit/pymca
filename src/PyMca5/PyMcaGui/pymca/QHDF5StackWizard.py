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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import posixpath
from PyMca5.PyMcaGui import PyMcaQt as qt
safe_str = qt.safe_str
from PyMca5.PyMcaGui.io.hdf5 import QNexusWidget
from PyMca5.PyMcaCore import NexusDataSource
from PyMca5 import PyMcaDirs
import logging
import numpy

_logger = logging.getLogger(__name__)


class IntroductionPage(qt.QWizardPage):
    def __init__(self, parent):
        qt.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Stack Selection Wizard")
        text  = "This wizard will help you to select the "
        text += "appropriate dataset(s) belonging to your stack"
        self.setSubTitle(text)


class FileListPage(qt.QWizardPage):
    def __init__(self, parent):
        qt.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Stack File Selection")
        text  = "The files below belong to your stack"
        self.setSubTitle(text)
        self.fileList = []
        self.inputDir = None
        self.mainLayout= qt.QVBoxLayout(self)
        listlabel   = qt.QLabel(self)
        listlabel.setText("Input File list")
        self._listView = qt.QTextEdit(self)
        self._listView.setMaximumHeight(30*listlabel.sizeHint().height())
        self._listView.setReadOnly(True)

        self._listButton = qt.QPushButton(self)
        self._listButton.setText('Browse')
        self._listButton.setAutoDefault(False)

        self.mainLayout.addWidget(listlabel)
        self.mainLayout.addWidget(self._listView)
        self.mainLayout.addWidget(self._listButton)

        self._listButton.clicked.connect(self.browseList)

    def setFileList(self, filelist):
        text = ""
        #filelist.sort()
        for ffile in filelist:
            text += "%s\n" % ffile
        self.fileList = filelist
        self._listView.setText(text)

    def validatePage(self):
        if not len(self.fileList):
            return False
        return True

    def browseList(self):
        if self.inputDir is None:
            self.inputDir = PyMcaDirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        filedialog = qt.QFileDialog(self)
        filedialog.setWindowTitle("Open a set of files")
        filedialog.setDirectory(wdir)
        if hasattr(filedialog, "setFilters"):
            filedialog.setFilters(["HDF5 Files (*.nxs *.h5 *.hdf *.hdf5)",
                                   "HDF5 Files (*.h5)",
                                   "HDF5 Files (*.hdf)",
                                   "HDF5 Files (*.hdf5)",
                                   "HDF5 Files (*.nxs)",
                                   "HDF5 Files (*)"])
        else:
            filedialog.setNameFilters(["HDF5 Files (*.nxs *.h5 *.hdf *.hdf5)",
                                       "HDF5 Files (*.h5)",
                                       "HDF5 Files (*.hdf)",
                                       "HDF5 Files (*.hdf5)",
                                       "HDF5 Files (*.nxs)",
                                       "HDF5 Files (*)"])
        filedialog.setModal(1)
        filedialog.setFileMode(filedialog.ExistingFiles)
        ret = filedialog.exec()
        if  ret == qt.QDialog.Accepted:
            filelist0=filedialog.selectedFiles()
        else:
            self.raise_()
            return
        filelist = []
        for f in filelist0:
            filelist.append(safe_str(f))
        if len(filelist):
            self.setFileList(filelist)
        PyMcaDirs.inputDir = os.path.dirname(filelist[0])
        self.inputDir = os.path.dirname(filelist[0])
        self.raise_()


class StackIndexWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        #self.mainLayout.setContentsMargins(0, 0, 0, 0)
        #self.mainLayout.setSpacing(0)

        self.buttonGroup = qt.QButtonGroup(self)
        options = [
            ("1D data is first dimension",
             'The channel (1D-data) axis is always the first selected axis '
             '("Axis X").',
             self._setFirstDimension),
            ("1D data is last dimension",
             'The channel (1D-data) axis is the last selected axis: "Axis X" '
             'if a single axis is selected, or "Axis Z" if three are.',
             self._setLastDimension),
            ("No 1D data",
             "No axis is used as the channel (1D-data) axis: the whole dataset is treated "
             "as an image.",
             self._setNoMca),
        ]
        i = 0
        for text, tip, slot in options:
            rButton = qt.QRadioButton(self)
            rButton.setText(text)
            rButton.setToolTip(tip)
            rButton.clicked.connect(slot)
            self.mainLayout.addWidget(rButton)
            self.buttonGroup.addButton(rButton, i)
            i += 1
        self.buttonGroup.button(1).setChecked(True)
        self._stackIndex = -1
        self._noMca = False

    def _setFirstDimension(self, checked=False):
        self._stackIndex = 0
        self._noMca = False

    def _setLastDimension(self, checked=False):
        self._stackIndex = -1
        self._noMca = False

    def _setNoMca(self, checked=False):
        self._stackIndex = -1
        self._noMca = True

    def setIndex(self, index):
        if index == 0:
            self._stackIndex = 0
            button_number = 0
            self._noMca = False
        elif index == -1:
            self._stackIndex = -1
            button_number = 1
            self._noMca = False
        else:
            self._stackIndex = -1
            button_number = 2
            self._noMca = True

        self.buttonGroup.button(button_number).setChecked(True)


class DatasetSelectionPage(qt.QWizardPage):
    def __init__(self, parent):
        qt.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Dataset Selection")
        text  = "Double click on the datasets you want to consider "
        text += "and select the role they will play at the end by "
        text += "selecting the appropriate checkbox(es)"
        self.selection = None
        self.setSubTitle(text)
        self.mainLayout = qt.QVBoxLayout(self)
        self.nexusWidget = LocalQNexusWidget(self)
        self.nexusWidget.buttons.hide()
        self.mainLayout.addWidget(self.nexusWidget, 1)

        self.stackIndexWidget = StackIndexWidget(self)
        self.mainLayout.addWidget(self.stackIndexWidget, 0)

        self._scatterCheckBox = qt.QCheckBox(
            "Scatter plot (X, Y coordinates are set per 1D data)", self)
        self._scatterCheckBox.setChecked(False)
        self.mainLayout.addWidget(self._scatterCheckBox, 0)

    def setFileList(self, filelist):
        self.dataSource = NexusDataSource.NexusDataSource(filelist[0])
        self.nexusWidget.setDataSource(self.dataSource)
        phynxFile = self.dataSource._sourceObjectList[0]
        keys = list(phynxFile.keys())
        if len(keys) != 1:
            return

        #check if it is an NXentry
        entry = phynxFile[keys[0]]
        attrs = list(entry.attrs)
        if 'NX_class' in attrs:
            attr = entry.attrs['NX_class']
            if hasattr(attr, "decode"):
                try:
                    attr = attr.decode('utf-8')
                except Exception:
                    _logger.warning("Cannot decode NX_class attribute")
                    attr = None
        else:
            attr = None
        if attr is None:
            return
        if attr not in ['NXentry', b'NXentry']:
            return

        #check if there is only one NXdata
        nxDataList = []
        for key in entry.keys():
            attr = entry[key].attrs.get('NX_class', None)
            if attr is None:
                continue
            if hasattr(attr, "decode"):
                try:
                    attr = attr.decode('utf-8')
                except Exception:
                    _logger.warning("Cannot decode NX_class attribute")
                    continue
            if attr in ['NXdata', b'NXdata']:
                nxDataList.append(key)
        if len(nxDataList) != 1:
            return
        nxData = entry[nxDataList[0]]

        ddict = {'counters': [],
                 'aliases': []}
        signalList = []
        axesList = []
        interpretation = ""

        signal_key = nxData.attrs.get("signal")
        if signal_key is not None:
            # recent NXdata specification
            if hasattr(signal_key, "decode"):
                try:
                    signal_key = signal_key.decode('utf-8')
                except AttributeError:
                    _logger.warning("Cannot decode NX_class attribute")

            signal_dataset = nxData.get(signal_key)
            if signal_dataset is None:
                return

            interpretation = signal_dataset.attrs.get("interpretation", "")
            if hasattr(interpretation, "decode"):
                try:
                    interpretation = interpretation.decode('utf-8')
                except AttributeError:
                    _logger.warning("Cannot decode interpretation")

            axesList = list(nxData.attrs.get("axes", []))
            if not axesList:
                # try the old method, still documented on nexusformat.org:
                # colon-delimited "array" of dataset names as a signal attr
                axes = signal_dataset.attrs.get('axes')
                if axes is not None:
                    if hasattr(axes, "decode"):
                        try:
                            axes = axes.decode('utf-8')
                        except AttributeError:
                            _logger.warning("Cannot decode axes")
                    axes = axes.split(":")
                    axesList = [ax for ax in axes if ax in nxData]
            signalList.append(signal_key)
        else:
            # old specification
            for key in nxData.keys():
                if 'signal' in nxData[key].attrs.keys():
                    if int(nxData[key].attrs['signal']) == 1:
                        signalList.append(key)
                        if len(signalList) == 1:
                            if 'interpretation' in nxData[key].attrs.keys():
                                interpretation = nxData[key].attrs['interpretation']
                                try:
                                    interpretation = interpretation.decode('utf-8')
                                except Exception:
                                    _logger.warning("Cannot decode interpretation")

                            if 'axes' in nxData[key].attrs.keys():
                                axes = nxData[key].attrs['axes']
                                try:
                                    axes = axes.decode('utf-8')
                                except Exception:
                                    _logger.warning("Cannot decode axes")
                                axes = axes.split(":")
                                for axis in axes:
                                    if axis in nxData.keys():
                                        axesList.append(axis)

            if not len(signalList):
                return

        if interpretation in ["image", b"image"]:
            self.stackIndexWidget.setIndex(0)
            # the typical image should not have 1D data
            data = nxData[signalList[0]]
            if hasattr(data, "shape") and len(data.shape) <= 2:
                self.stackIndexWidget.setIndex(None)

        for signal_key in signalList:
            path = posixpath.join("/", nxDataList[0], signal_key)
            ddict['counters'].append(path)
            ddict['aliases'].append(posixpath.basename(signal_key))

        for axis in axesList:
            path = posixpath.join("/", nxDataList[0], axis)
            ddict['counters'].append(path)
            ddict['aliases'].append(posixpath.basename(axis))

        if sys.platform == "darwin" and\
           len(ddict['counters']) > 3 and\
           qt.qVersion().startswith('4.8'):
            # workaround a strange bug on Mac:
            # when the counter list has to be scrolled
            # the selected button also changes!!!!
            return

        self.nexusWidget.setWidgetConfiguration(ddict)

        if self.stackIndexWidget._noMca:
            self.nexusWidget.cntTable.setCounterSelection({'y': [0]})
        elif axesList and (interpretation in ["image", b"image"]):
            self.nexusWidget.cntTable.setCounterSelection({'y': [0], 'x': [1]})
        elif axesList and (interpretation in ["spectrum", b"spectrum"]):
            self.nexusWidget.cntTable.setCounterSelection({'y': [0], 'x': [len(axesList)]})
        else:
            self.nexusWidget.cntTable.setCounterSelection({'y': [0]})

    def validatePage(self):
        """
        Validate data while wizard is open
        """
        selection = self._buildSelection()
        if selection is None:
            return False
        if not self._validateScatterSelection(selection):
            return False

        signalShapes, nPoints, axisSizes = self._collectValidationData(selection)
        if signalShapes:
            if not self._validateSignalShapes(signalShapes):
                return False
            rawShape = tuple(signalShapes[0])
            # a dataset is pure singleton - there is no image.
            if not any(d > 1 for d in rawShape):
                self.showMessage("The selected dataset is all size-1; "
                                 "there is nothing to image.")
                return False
            
            # Resolve singletons before other validation
            if not self._resolveSingletonDrop(selection, rawShape):
                # back to Wizard
                return False 
            
            effShape = self._effectiveShape(selection, rawShape)

            if not self._validateDimensionality(selection, effShape):
                return False

            if axisSizes:
                if not self._validateAxisSelection(selection, effShape, axisSizes):
                    return False

        self.selection = selection
        return True

    def _buildSelection(self):
        """
        Build the selection dictionary from the counter table.
        """
        cntSelection = self.nexusWidget.cntTable.getCounterSelection()
        cntlist = cntSelection['cntlist']
        if not len(cntlist):
            self.showMessage("No dataset selection")
            return None
        if not len(cntSelection['y']):
            self.showMessage("No dataset selected as y")
            return None
        selection = {}
        selection['x'] = []
        selection['y'] = []
        selection['m'] = []
        selection['index'] = self.stackIndexWidget._stackIndex
        for key in ['x', 'y', 'm']:
            if len(cntSelection[key]):
                for idx in cntSelection[key]:
                    selection[key].append(cntlist[idx])
        selection['scatter'] = self._scatterCheckBox.isChecked()
        selection['allowPadding'] = False
        selection['squeeze'] = False
        selection['noMca'] = self.stackIndexWidget._noMca
        return selection

    def _validateScatterSelection(self, selection):
        if selection['scatter'] and len(selection['x']) < 2:
            self.showMessage("Scatter mode requires two datasets selected as axes")
            return False
        else:
            return True

    def _collectValidationData(self, selection):
        """
        Read the signal and axes shapes from the selected datasets.
        """
        try:
            # choose selected entry, or first entry if none selected
            h5file = self.dataSource._sourceObjectList[0]
            entries = self.nexusWidget.getSelectedEntries()
            entry = entries[0][0] if entries else list(h5file.keys())[0]

            signalShapes = []
            for yPath in selection['y']:
                yShape = h5file[posixpath.join(entry, yPath.lstrip("/"))].shape
                signalShapes.append(yShape)

            if selection['noMca']:
                nPoints = int(numpy.prod(signalShapes[0]))
            else:
                if selection['index'] == -1:
                    mcaAxis = len(signalShapes[0]) - 1
                else:
                    mcaAxis = selection['index']
                nPoints = int(numpy.prod(numpy.delete(signalShapes[0], mcaAxis)))

            axisSizes = []
            for xPath in selection['x']:
                dataset = h5file[posixpath.join(entry, xPath.lstrip("/"))].shape
                axisSizes.append(int(numpy.prod(dataset)))

            return signalShapes, nPoints, axisSizes
            
        except Exception:
            _logger.warning("Fail to identify number of 1D datasets and/or axes sizes")
            return None, None, None

    def _validateSignalShapes(self, signalShapes):
        # the selected signals are summed later so they must have the same shape
        if not all(shape == signalShapes[0] for shape in signalShapes):
            self.showMessage("Not all signal shapes are equal")
            return False
        return True

    def _resolveSingletonDrop(self, selection, signalShape):
        """
        Ask whether an explicit singleton is real or should be dropped.
        
        To be noticed that most of cases do not require a question:
        when dataset is 1x1xN, 1xNx1, Nx1x1, 1xN, Nx1
            a) "No 1D data" - singletons should/could be dropped
            b) "1D data is first/last dimension" then the singletons should/could be kept
        """
        selection['squeeze'] = False
        if selection['scatter'] or selection['noMca']:
            return True
        nSingletons = sum(1 for d in signalShape if d == 1)
        if (len(signalShape) == 3) and (nSingletons == 1):
            choice = self._askDropSingleton(signalShape)
            if choice is None:
                return False
            selection['squeeze'] = choice
        return True

    def _askDropSingleton(self, signalShape):
        msg = qt.QMessageBox(self)
        msg.setIcon(qt.QMessageBox.Question)
        msg.setWindowTitle("Size-1 dimension")
        msg.setText(
            "The selected dataset has a size-1 dimension.\n\n"
            "Keep it as a real dimension, or drop it?"
            )
        keepButton = msg.addButton("Keep",
                                   qt.QMessageBox.AcceptRole)
        dropButton = msg.addButton("Drop and reshape",
                                   qt.QMessageBox.ApplyRole)
        msg.addButton(qt.QMessageBox.Cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is keepButton:
            return False
        if clicked is dropButton:
            return True
        # Cancel return user to Wizard
        return None

    @staticmethod
    def _effectiveShape(selection, rawShape):
        """
        "No 1D data" and "drop" both squeeze all singletons.
        """
        if selection['noMca'] or selection['squeeze']:
            return tuple(d for d in rawShape if d > 1)
        return rawShape

    def _validateDimensionality(self, selection, effShape):
        """
        Validates dimensions for selected options.
        """
        ndim = len(effShape)
        if selection['noMca']:
            if ndim > 2:
                self.showMessage(
                    "Three dimensions could not represent an image. "
                    "'No 1D data' supports only 2D and 1D datasets. "
                    )
                return False
        else:
            if ndim < 2:
                self.showMessage(
                    "A 1D dataset could not represent an image with channels. "
                    "Use 'No 1D data' in case there are no channels.")
                return False
        return True

    def _validateAxisSelection(self, selection, effShape, axisSizes):
        """
        Validate the axes against the dataset.
        """
        noMca = selection['noMca']
        scatter = selection['scatter']
        chan, mapDims = self._channelAxisAndMap(selection, effShape)
        if noMca:
            channelSize = 1
        else:
            channelSize = effShape[chan]
        nPoints = int(numpy.prod(mapDims)) if mapDims else 1
        spatial = list(axisSizes)

        # should never happen
        if len(axisSizes) > 3:
            self.showMessage(
                "Too many axes selected")
            return False

        if len(axisSizes) == 1:
            if noMca:
                self.showMessage(
                    "A single selected axis is the channel (1D-data) axis, but "
                    "'No 1D data' has no channels. Select two axes, or none.")
                return False
            if axisSizes[0] != channelSize:
                self.showMessage(
                    "The selected channel axis has %d values but the 1D data "
                    "has %d channels." % (axisSizes[0], channelSize))
                return False
            return True

        if len(axisSizes) == 3:
            if noMca:
                self.showMessage(
                    "Three axes describe two map dimensions plus channels, but "
                    "'No 1D data' has no channels.")
                return False
            channelsFirst = (len(effShape) == 3) and (selection['index'] == 0)
            slot = 0 if channelsFirst else len(spatial) - 1
            if spatial[slot] != channelSize:
                where = "first" if channelsFirst else "last"
                self.showMessage(
                    "The channel axis must be selected %s of the three axes "
                    "(it must have length %d = the number of channels)."
                    % (where, channelSize))
                return False
            spatial.pop(slot)

        if scatter:
            # scatter sometimes will be actually squeezed but it depends on other selections
            # thus, validation appeared to be here. 
            effMap = [d for d in mapDims if d > 1]
            if len(effMap) != 1:
                self.showMessage(
                    "Scatter needs a flat per-point scan (one scan dimension); "
                    "this map is %dD. Disable 'Scatter plot'." % len(effMap))
                return False
            if spatial[0] != spatial[1]:
                self.showMessage(
                    "Scatter motors (X and Y) must have equal length ")
                return False
            return self._validateScatterGeometry(selection, spatial[0], nPoints)

        if len(mapDims) == 1:
            # normal grid
            return self._validateGridGeometry(selection, spatial, nPoints)
        if len(mapDims) == 2:
            if sorted(spatial) != sorted(mapDims):
                self.showMessage(
                    "The two grid axes must match the map dimensions; " 
                    "the image shape is fixed by the data. " 
                    "Consider to drop singletons (if kept) or to select `No 1D data`.")
                return False
            return True
        self.showMessage(
            "Grid mode needs a 1D or 2D map. This one (considering selected 1D data position) is bigger. ")
        return False

    def _channelAxisAndMap(self, selection, effShape):
        if selection['noMca']:
            return None, list(effShape)
         
        ndim = len(effShape)
        if selection['index'] == 0:
            chan = 0
        else:
            chan = ndim - 1
        mapDims = []
        for i in range(ndim):
            if i == chan:
                continue
            mapDims.append(effShape[i])
        return chan, mapDims

    def _validateScatterGeometry(self, selection, axisSize, nPoints):
        if axisSize < nPoints:
            self.showMessage("Fewer positions than 1D data is impossible")
            return False
        if axisSize > nPoints:
            if not self._confirmPadding(
                "There are %d motor positions but only %d 1D datasets. "
                "The missing points can be padded with NaN and will be shown as empty."
                % (axisSize, nPoints)):
                return False
            selection['allowPadding'] = True
        return True

    def _validateGridGeometry(self, selection, axisSizes, nPoints):
        nA, nB = axisSizes
        # can cause a problem but only in unrealistic scenario
        # when user want to pad symmetric scan which failed almost at the start
        if (nA == nB) and (nA >= nPoints):
            self.showMessage(
                "Most probably the selected motor positions hold one value per 1D data. "
                "The regular grid can not be defined. "
                "Enable 'Scatter plot' or select different axes.")
            return False
        elif (nA * nB) < nPoints:
            self.showMessage(
                "The selected axes define %d positions (%d x %d) but the "
                "signal has %d 1D datasets. Please select differently." % (nA * nB, nA, nB, nPoints))
            return False
        elif (nA * nB) > nPoints:
            if not self._confirmPadding(
                "The %d x %d grid has %d positions but there are only %d 1D datasets. "
                "The missing 1D datasets can be padded with NaN and will be shown as empty."
                % (nA, nB, nA * nB, nPoints)):
                return False
            # protecting from accidental padding
            selection['allowPadding'] = True
        return True

    def _confirmPadding(self, text):
        """Confirm padding while wizard is open"""
        msg = qt.QMessageBox(self)
        msg.setIcon(qt.QMessageBox.Warning)
        msg.setWindowTitle("Unfinished scan")
        msg.setText(text + "\n\nContinue, or cancel to change the selection?")
        contButton = msg.addButton("Continue", qt.QMessageBox.AcceptRole)
        msg.addButton("Cancel", qt.QMessageBox.RejectRole)
        msg.exec()
        clicked = msg.clickedButton()
        return clicked is contButton

    def showMessage(self, text):
        msg = qt.QMessageBox(self)
        msg.setIcon(qt.QMessageBox.Information)
        msg.setText(text)
        msg.exec()


class ShapePage(qt.QWizardPage):
    def __init__(self, parent):
        qt.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Map Shape Selection")
        text  = "Adjust the shape of your map if necessary"
        self.setSubTitle(text)


class LocalQNexusWidget(QNexusWidget.QNexusWidget):
    def __init__(self, parent=None, mca=False):
        QNexusWidget.QNexusWidget.__init__(self, parent=parent,
                                           mca=mca,
                                           buttons=True)

    def showInfoWidget(self, filename, name, dset=False):
        w = QNexusWidget.QNexusWidget.showInfoWidget(self, filename, name, dset)
        w.hide()
        w.setWindowModality(qt.Qt.ApplicationModal)
        w.show()


class QHDF5StackWizard(qt.QWizard):
    def __init__(self, parent=None):
        qt.QWizard.__init__(self, parent)
        try:
            self.setWizardStyle(qt.QWizard.ClassicStyle)
        except AttributeError:
            self.setWizardStyle(qt.QWizard.WizardStyle.ClassicStyle)
        self.setWindowTitle("HDF5 Stack Wizard")
        #self._introduction = self.createIntroductionPage()
        self._fileList     = self.createFileListPage()
        self._datasetSelection = self.createDatasetSelectionPage()
        #self._shape        = self.createShapePage()
        #self.addPage(self._introduction)
        self.addPage(self._fileList)
        self.addPage(self._datasetSelection)
        #self.addPage(self._shape)
        #self.connect(qt.SIGNAL("currentIdChanged(int"),
        #             currentChanged)

    def sizeHint(self):
        width = qt.QWizard.sizeHint(self).width()
        height = qt.QWizard.sizeHint(self).height()
        return qt.QSize(width, int(1.5 * height))

    def createIntroductionPage(self):
        return IntroductionPage(self)

    def setFileList(self, filelist):
        self._fileList.setFileList(filelist)

    def createFileListPage(self):
        return FileListPage(self)

    def createDatasetSelectionPage(self):
        return DatasetSelectionPage(self)

    def createShapePage(self):
        return ShapePage(self)

    def initializePage(self, value):
        if value == 1:
            #dataset page
            self._datasetSelection.setFileList(self._fileList.fileList)

    def getParameters(self):
        return self._fileList.fileList,\
               self._datasetSelection.selection,\
               [x[0] for x in self._datasetSelection.nexusWidget.getSelectedEntries()]


if __name__ == "__main__":
    import sys
    app = qt.QApplication(sys.argv)
    w = QHDF5StackWizard()
    ret = w.exec()
    if ret == qt.QDialog.Accepted:
        print(w.getParameters())
