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
import os.path
import numpy
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.plotting import PlotWidget


if not hasattr(qt, 'QString'):
    QString = qt.safe_str
    QStringList = list
else:
    QString = qt.QString
    QStringList = qt.QStringList
QTVERSION = qt.qVersion()
QT4=True
from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave
MATPLOTLIB = True
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.plotting import ColormapDialog
from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
from PyMca5.PyMcaIO import ArraySave
from PyMca5 import PyMcaDirs
from . import SpecFileDataInfo
from PyMca5 import spslut

_logger = logging.getLogger(__name__)


COLORMAPLIST = [spslut.GREYSCALE, spslut.REVERSEGREY, spslut.TEMP,
                spslut.RED, spslut.GREEN, spslut.BLUE, spslut.MANY]


DEBUG = 0
SOURCE_TYPE = 'EdfFile'
__revision__ = "$Revision: 1.35 $"


def convertToRowAndColumn(x, y, shape, xScale=None, yScale=None, safe=True):
    if xScale is None:
        c = x
    else:
        c = (x - xScale[0]) / xScale[1]
    if yScale is None:
        r = y
    else:
        r = ( y - yScale[0]) / yScale[1]

    if safe:
        c = min(int(c), shape[1] - 1)
        c = max(c, 0)
        r = min(int(r), shape[0] - 1)
        r = max(r, 0)
    else:
        c = int(c)
        r = int(r)
    return r, c


class EdfFile_StandardArray(qt.QWidget):
    sigWidgetSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, name="Edf_StandardArray", images=None, rows=None, cols=None):
        if images is None:
            images = 1
        if rows is None:
            rows = 0
        if cols is None:
            cols = 0
        qt.QWidget.__init__(self, parent)
        layout = qt.QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        ilab= qt.QLabel("Image:", self)
        self.plab= qt.QLabel("Plot", self)
        self.ylab= qt.QLabel("Columns :", self)

        layout.addWidget(ilab, 0, 0, qt.Qt.AlignRight)
        layout.addWidget(self.plab, 1, 0, qt.Qt.AlignRight)
        layout.addWidget(self.ylab, 2, 0, qt.Qt.AlignRight|qt.Qt.AlignTop)

        self.iCombo= qt.QComboBox(self)
        self.iCombo.setEditable(0)

        self.plotCombo= qt.QComboBox(self)
        self.plotCombo.setEditable(0)
        self.plotCombo.insertItems(0, ["Rows", "Columns"])
        self.yList= qt.QListWidget(self)
        #self.yList.setSelectionMode(qt.QListBox.Multi)


        layout.addWidget(self.iCombo,   0, 1)
        layout.addWidget(self.plotCombo,1, 1)
        layout.addWidget(self.yList,    2, 1)

        self.plotCombo.activated[int].connect(self.__plotChanged)
        self.iCombo.activated[int].connect(self.__iChanged)
        self.setImages(images)

        self.setDataSize(rows, cols)

    def setImages(self,images,info=None):
        self.iCombo.clear()
        if info is None:
            info = []
        for i in range(images):
            if len(info) == images:
                self.iCombo.insertItem(i, "Image %d Key %s" % (i,info[i]))
            else:
                self.iCombo.insertItem(i, "Image %d" % i)

    def setCurrentImage(self,image):
        if image < self.iCombo.count():
            self.iCombo.setCurrentIndex(image)

    def setDataSize(self, rows, cols):
        self.rows= rows
        self.cols= cols

        idx = self.cols <= self.rows
        self.plotCombo.setCurrentIndex(idx)
        self.__plotChanged(idx)

    def __plotChanged(self, index):
        if index==1:
            self.ylab.setText('Columns')
            txt= "Column"
            val= self.cols
        else:
            self.ylab.setText('Rows')
            txt= "Row"
            val= self.rows
        self.yList.clear()
        for x in range(val):
            self.yList.addItem("%s %d"%(txt,x))
        ddict={}
        ddict['event'] = "plotChanged"
        ddict['plot']  =  txt+"s"
        self.sigWidgetSignal.emit((ddict))

    def __iChanged(self, index):
        ddict={}
        ddict['event'] = "imageChanged"
        ddict['index'] =  index
        self.sigWidgetSignal.emit((ddict))

    def getSelection(self):
        selection= []

        idx = self.plotCombo.currentIndex()
        if idx==1:
            plot= "cols"
        else:
            plot= "rows"

        idx = self.iCombo.currentIndex()
        if idx==0:
            image= None
        else:
            image= idx-1

        if hasattr(self.yList, "isItemSelected"):
            ylist= [ idx for idx in range(self.yList.count()) \
                     if self.yList.isItemSelected(self.yList.item(idx))]
        else:
            selectedItems = self.yList.selectedItems()
            ylist = [self.yList.row(item) for item in selectedItems]
        for y in ylist:
            selection.append({"plot":plot, "image": image,"x":None, "y":y})
        return selection

    def markImageSelected(self,imagelist=[]):
        current = self.iCombo.currentIndex()
        images  = self.iCombo.count()
        #self.iCombo.clear()
        msg = " (selected)"
        for i in range(images):
            index = "%d" % i
            text = qt.safe_str(self.iCombo.itemText(i)).split(msg)[0]
            key  = text.split()[-1]
            if key in imagelist:
                self.iCombo.setItemText(i, "%s%s" % (text,msg))
            else:
                self.iCombo.setItemText(i, "%s" % (text))
        self.iCombo.setCurrentIndex(current)


    def markRowSelected(self, rowlist=[]):
        if not qt.safe_str(self.plotCombo.currentText()) == "Rows":
            return
        current = self.yList.currentItem()
        n       = self.yList.count()
        self.yList.clear()
        for index in range(n):
            if index in rowlist:
                self.yList.addItem(" Row %d (selected)" % index)
            else:
                self.yList.addItem(" Row %d" % index)

    def markColSelected(self, collist=[]):
        if not qt.safe_str(self.plotCombo.currentText()) == "Columns":
            return
        current = self.yList.currentItem()
        n       = self.yList.count()
        self.yList.clear()
        for index in range(n):
            if index in collist:
                self.yList.addItem(" Column %d (selected)" % index)
            else:
                self.yList.addItem(" Column %d" % index)
        self.yList.setCurrentItem(current)

class QEdfFileWidget(qt.QWidget):
    sigAddSelection = qt.pyqtSignal(object)
    sigRemoveSelection = qt.pyqtSignal(object)
    sigReplaceSelection = qt.pyqtSignal(object)

    def __init__(self, parent=None, justviewer=False):
        qt.QWidget.__init__(self, parent)
        self.justViewer = justviewer
        self.dataSource= None
        self.oldsource = ""
        self.oldcurrentArray = None
        self.data= None
        self.currentFile= None
        self.currentArray= 0
        self._matplotlibSaveImage = None
        self.selection= None
        self.__plotting = "Columns"
        self._edfstack = None
        self.lastInputDir = None
        self.colormapDialog = None
        self.colormap  = None
        self.printPreview = PyMcaPrintPreview.PyMcaPrintPreview(modal = 0)

        #self.selectPixmap= qt.QPixmap(icons.selected)
        #self.unselectPixamp= qt.QPixmap(icons.unselected)
        self.mapComboName= {}

        self.mainLayout= qt.QVBoxLayout(self)
        self.toolBar = None
        self._buildToolBar()

        # --- splitter
        self.splitter = qt.QSplitter(self)
        self.splitter.setOrientation(qt.Qt.Vertical)

        # --- graph
        self.graph = PlotWidget.PlotWidget(self.splitter, backend=None)
        self.graph.setGraphTitle('')
        self.graph.setGraphXLabel('Columns')
        self.graph.setGraphYLabel('Rows')
        self.graph.sigPlotSignal.connect(self.widgetSignal)
        self._x1Limit = self.graph.getGraphXLimits()[-1]
        self._y1Limit = self.graph.getGraphYLimits()[-1]
        #self.graph.hide()
        # --- array parameter
        self.__dummyW = qt.QWidget(self.splitter)
        self.__dummyW.layout =qt.QVBoxLayout(self.__dummyW)
        self.__dummyW.layout.setContentsMargins(0, 0, 0, 0)
        self.__dummyW.layout.setSpacing(0)
        if not justviewer:
            self.applygroupContainer = qt.QWidget(self.__dummyW)
            self.applytoone = qt.QCheckBox(self.applygroupContainer)
            self.applytoone.setText("Apply to seen  image")
            self.applytoone.setChecked(1)
            self.applytoall = qt.QCheckBox(self.applygroupContainer)
            self.applytoall.setText("Apply to all images in list")
            self.applygroup = qt.QButtonGroup()
            self.applygroup.addButton(self.applytoone, 0)
            self.applygroup.addButton(self.applytoall, 1)
            self.applygroup.setExclusive(True)
            self.applygroupLayout = qt.QHBoxLayout(self.applygroupContainer)
            self.applygroupLayout.setContentsMargins(0, 0, 0, 0)
            self.applygroupLayout.setSpacing(0)
            self.applygroupLayout.addWidget(self.applytoone)
            self.applygroupLayout.addWidget(self.applytoall)
            self.__dummyW.layout.addWidget(self.applygroupContainer)
            if hasattr(self.applygroup, "idClicked"):
                self.applygroup.idClicked[int].connect(self.groupSignal)
            else:
                # deprecated
                _logger.debug("Using deprecated signal")
                self.applygroup.buttonClicked[int].connect(self.groupSignal)

        self.dataInfoWidgetDict = {}
        self.paramWidget = EdfFile_StandardArray(self.__dummyW)
        self.__dummyW.layout.addWidget(self.paramWidget)
        self.paramWidget.sigWidgetSignal.connect(self.widgetSignal)

        if justviewer:
            self.paramWidget.plab.hide()
            self.paramWidget.plotCombo.hide()
            self.paramWidget.ylab.hide()
            self.paramWidget.yList.hide()

        self.allImages = 0
        # --- main layout
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(2)

        #self.mainLayout.addWidget(self.infoBar)
        self.mainLayout.addWidget(self.splitter)
        if not justviewer: self._buildActions()

    def _buildToolBar(self):
        self.hFlipIcon	= qt.QIcon(qt.QPixmap(IconDict["gioconda16mirror"]))
        self.solidCircleIcon = qt.QIcon(qt.QPixmap(IconDict["solidcircle"]))
        self.solidEllipseIcon = qt.QIcon(qt.QPixmap(IconDict["solidellipse"]))
        self.colormapIcon   = qt.QIcon(qt.QPixmap(IconDict["colormap"]))
        self.zoomResetIcon	= qt.QIcon(qt.QPixmap(IconDict["zoomreset"]))
        self.printIcon	= qt.QIcon(qt.QPixmap(IconDict["fileprint"]))
        self.copyIcon = qt.QIcon(qt.QPixmap(IconDict["clipboard"]))
        self.saveIcon	= qt.QIcon(qt.QPixmap(IconDict["filesave"]))
        try:
            self.infoIcon	= qt.QApplication.style().\
                              standardIcon(qt.QStyle.SP_MessageBoxInformation)
        except Exception:
            self.infoIcon = None

        self.toolBar = qt.QWidget(self)
        self.toolBarLayout = qt.QHBoxLayout(self.toolBar)
        self.toolBarLayout.setSpacing(0)
        self.toolBarLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addWidget(self.toolBar)
        # Autoscale
        self._addToolButton(self.zoomResetIcon,
                            self._zoomReset,
                            'Auto-Scale the Graph')

        self.aspectButton = self._addToolButton(self.solidCircleIcon,
                            self._aspectButtonSignal,
                            'Keep data aspect ratio',
                            toggle = False)
        self.aspectButton.setChecked(False)
        self._keepDataAspectRatioFlag = False

        # colormap
        self._addToolButton(self.colormapIcon,
                            self.selectColormap,
                            'Color-Scale the Graph')
        tb = self._addToolButton(self.hFlipIcon,
                             self._hFlipIconSignal,
                             'Flip Horizontal')
        self.hFlipToolButton = tb

        # info
        if self.infoIcon is not None:
            self._addToolButton(self.infoIcon,
                             self._showInformation,
                            'Show source information')

        # clipboard
        self.copyToolButton = self._addToolButton(self.copyIcon,
                                                  self._copyIconSignal,
                                                  "Copy graph to clipboard")
        # save
        if MATPLOTLIB:
            tb = self._addToolButton(self.saveIcon,
                                     self.__saveIconSignal,
                                     'Export Graph')
            self._saveMenu = qt.QMenu()
            self._saveMenu.addAction(QString("Standard"),    self._saveIconSignal)
            self._saveMenu.addAction(QString("Matplotlib") , self._saveMatplotlibImage)
        else:
            tb = self._addToolButton(self.saveIcon,
                                 self._saveIconSignal,
                                 'Export Graph')

        # info
        self.infoText = qt.QLabel(self.toolBar)
        self.infoText.setText("    X = ???? Y = ???? Z = ????")
        self.toolBarLayout.addWidget(self.infoText)

        self.toolBarLayout.addWidget(qt.HorizontalSpacer(self.toolBar))

        # ---print
        tb = self._addToolButton(self.printIcon,
                                 self.printGraph,
                                 'Print the Graph')
    def _hFlipIconSignal(self):
        _logger.debug("_hFlipIconSignal called")
        if self.graph.isYAxisInverted():
            self.graph.invertYAxis(False)
        else:
            self.graph.invertYAxis(True)
        self.graph.replot()

    def _aspectButtonSignal(self):
        _logger.debug("_aspectButtonSignal")
        if self._keepDataAspectRatioFlag:
            self.keepDataAspectRatio(False)
        else:
            self.keepDataAspectRatio(True)

    def keepDataAspectRatio(self, flag=True):
        if flag:
            self.aspectButton.setIcon(self.solidEllipseIcon)
            self.aspectButton.setToolTip("Set free data aspect ratio")
            self._keepDataAspectRatioFlag = True
        else:
            self._keepDataAspectRatioFlag = False
            self.aspectButton.setIcon(self.solidCircleIcon)
            self.aspectButton.setToolTip("Keep data aspect ratio")
        self.graph.keepDataAspectRatio(self._keepDataAspectRatioFlag)

    def _addToolButton(self, icon, action, tip, toggle=None):
        tb      = qt.QToolButton(self.toolBar)
        tb.setIcon(icon)
        tb.setToolTip(tip)
        if toggle is not None:
            if toggle:
                tb.setCheckable(1)
        self.toolBarLayout.addWidget(tb)
        tb.clicked.connect(action)
        return tb

    def _showInformation(self):
        if (self.data is None) or \
           (self.currentArray is None):
            qt.QMessageBox.information(self, "No data",\
                                       "No information to be shown")
            return

        #this could be cached because implies a new reading
        infoSource= self.data.getSourceInfo()
        info = self.data.getKeyInfo(infoSource['KeyList']\
                                             [self.currentArray])
        infoWidget = SpecFileDataInfo.SpecFileDataInfo(info, parent=None)
        infoWidget.show()
        infoWidget.notifyCloseEventToWidget(self)
        self.dataInfoWidgetDict[id(infoWidget)] = infoWidget

    def _dataInfoClosed(self, ddict):
        if ddict['event'] == "SpecFileDataInfoClosed":
            key = ddict['id']
            if key in self.dataInfoWidgetDict:
                del self.dataInfoWidgetDict[key]

    def customEvent(self, event):
        if hasattr(event, 'dict'):
            ddict = event.dict
            self._dataInfoClosed(ddict)

    def _zoomReset(self):
        _logger.debug("_zoomReset")
        self.graph.resetZoom()

    def _saveMatplotlibImage(self):
        if self._matplotlibSaveImage is None:
            if (self.currentArray is None) or \
                (self.data is None):
                self._matplotlibSaveImage = QPyMcaMatplotlibSave.SaveImageSetup(None,
                                                                                None)
            else:
                self._matplotlibSaveImage = QPyMcaMatplotlibSave.SaveImageSetup(None,
                                                                                self.lastData)
        else:
            self._matplotlibSaveImage.setImageData(self.lastData)
        self._matplotlibSaveImage.show()
        self._matplotlibSaveImage.raise_()

    def _copyIconSignal(self):
        self.graph.copyToClipboard()

    def __saveIconSignal(self):
        self._saveMenu.exec(self.cursor().pos())

    def _saveIconSignal(self):
        self.lastInputDir = PyMcaDirs.outputDir

        fileTypeList = ["Data *.dat",
                        "ImageData *.tif",
                        "Image *.png",
                        "Image *.jpg",
                        "ZoomedImage *.png",
                        "ZoomedImage *.jpg",
                        "Widget *.png",
                        "Widget *.jpg"]

        outfile, filterused = PyMcaFileDialogs.getFileList(parent=self,
                    filetypelist=fileTypeList, message="Output File Selection",
                    currentdir=self.lastInputDir, mode="SAVE",
                    getfilter=True,
                    single=False,
                    currentfilter=None,
                    native=None)
        if not len(outfile):
            return
        filterused = filterused.split()
        filetype = filterused[0]
        extension = filterused[1]
        outputFile  = outfile[0]
        outputDir  = os.path.dirname(outputFile)
        self.lastInputDir = outputDir

        #always overwrite for the time being
        if len(outputFile) < len(extension[1:]):
            outputFile += extension[1:]
        elif outputFile[-4:] != extension[1:]:
            outputFile += extension[1:]
        outputFile = os.path.join(outputDir, outputFile)
        if os.path.exists(outputFile):
            try:
                os.remove(outputFile)
            except Exception:
                qt.QMessageBox.critical(self, "Save Error", "Cannot overwrite existing file")
                return

        tiff = False
        if filetype.upper() == "IMAGEDATA":
            tiff = True
        if (filetype.upper() == "DATA") or tiff:
            if (self.data is None) or \
               (self.currentArray is None):
                qt.QMessageBox.information(self, "No data",\
                                           "No data to be saved")
                return
            i = 0
            for sname in self.data.sourceName:
                if i == 0:
                    selfdatasourceName = sname
                    i = 1
                else:
                    selfdatasourceName += "|"+sname
            key = self.data.getSourceInfo()['KeyList'][self.currentArray]
            label = selfdatasourceName +"_"+"Key"+"_"+key
            try:
                if tiff:
                    ArraySave.save2DArrayListAsMonochromaticTiff([self.lastData],
                                                                 outputFile,
                                                                 labels = [label],
                                                                 dtype=None)
                else:
                    ArraySave.save2DArrayListAsASCII([self.lastData],
                                                     outputFile,
                                                     labels = [label])
            except Exception:
                qt.QMessageBox.critical(self, "Save Error", "%s" % \
                                        sys.exc_info()[1])
                return
        elif filetype.upper() == "IMAGE":
            self.saveGraphImage(outputFile, original=True)
        elif filetype.upper() == "ZOOMEDIMAGE":
            self.saveGraphImage(outputFile,original=False)
        else:
            self.saveGraphWidget(outputFile)

    def saveGraphImage(self, filename,original=True):
        fformat = filename[-3:].upper()
        #This is the whole image, not the zoomed one ...
        rgbData, legend, info, pixmap = self.graph.getActiveImage()
        if original:
            # save whole image
            bgrData = numpy.array(rgbData, copy=True)
            bgrData[:,:,0] = rgbData[:, :, 2]
            bgrData[:,:,2] = rgbData[:, :, 0]
        else:
            shape = rgbData.shape[:2]
            xmin, xmax = self.graph.getGraphXLimits()
            ymin, ymax = self.graph.getGraphYLimits()
            # save zoomed image, for that we have to get the limits
            r0, c0 = convertToRowAndColumn(xmin, ymin, shape, xScale=None, yScale=None, safe=True)
            r1, c1 = convertToRowAndColumn(xmax, ymax, shape, xScale=None, yScale=None, safe=True)
            row0 = int(min(r0, r1))
            row1 = int(max(r0, r1))
            col0 = int(min(c0, c1))
            col1 = int(max(c0, c1))
            if row1 < shape[0]:
                row1 += 1
            if col1 < shape[1]:
                col1 += 1
            tmpArray = rgbData[row0:row1, col0:col1, :]
            bgrData = numpy.array(tmpArray, copy=True, dtype=rgbData.dtype)
            bgrData[:,:,0] = tmpArray[:, :, 2]
            bgrData[:,:,2] = tmpArray[:, :, 0]
        if self.graph.isYAxisInverted():
            qImage = qt.QImage(bgrData, bgrData.shape[1], bgrData.shape[0],
                                   qt.QImage.Format_RGB32)
        else:
            qImage = qt.QImage(bgrData, bgrData.shape[1], bgrData.shape[0],
                                   qt.QImage.Format_RGB32).mirrored(False, True)
        pixmap = qt.QPixmap.fromImage(qImage)
        if pixmap.save(filename, fformat):
            return
        else:
            qt.QMessageBox.critical(self, "Save Error", "%s" % sys.exc_info()[1])
            return

    def saveGraphWidget(self, filename):
        fformat = filename[-3:].upper()
        if hasattr(qt.QPixmap, "grabWidget"):
            # Qt4
            pixmap = qt.QPixmap.grabWidget(self.graph)
        else:
            #Qt5
            pixmap = self.graph.grab()
        if pixmap.save(filename, fformat):
            return
        else:
            qt.QMessageBox.critical(self, "Save Error", "%s" % sys.exc_info()[1])
            return

    def setSaveDirectory(self, wdir):
        if os.path.exists(wdir):
            self.lastInputDir = wdir
            return True
        else:
            return False

    def printGraph(self):
        if hasattr(qt.QPixmap, "graphWidget"):
            # Qt4
            pixmap = qt.QPixmap.grabWidget(self.graph)
        else:
            #Qt5
            pixmap = self.graph.grab()
        self.printPreview.addPixmap(pixmap)
        if self.printPreview.isHidden():
            self.printPreview.show()
        self.printPreview.raise_()

    def _buildActions(self):
        self.buttonBox = qt.QWidget(self)
        buttonBox = self.buttonBox
        self.buttonBoxLayout = qt.QGridLayout(buttonBox)
        self.buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonBoxLayout.setSpacing(2)

        self.add2DButton = qt.QPushButton(buttonBox)
        self.add2DButton.setText("ADD 2D")
        self.remove2DButton = qt.QPushButton(buttonBox)
        self.remove2DButton.setText("REMOVE 2D")
        self.replace2DButton = qt.QPushButton(buttonBox)
        self.replace2DButton.setText("REPLACE 2D")

        self.addButton = qt.QPushButton(buttonBox)
        self.addButton.setText("ADD")
        self.removeButton = qt.QPushButton(buttonBox)
        self.removeButton.setText("REMOVE")
        self.replaceButton = qt.QPushButton(buttonBox)
        self.replaceButton.setText("REPLACE")

        self.buttonBoxLayout.addWidget(self.add2DButton, 0, 0)
        self.buttonBoxLayout.addWidget(self.remove2DButton, 0, 1)
        self.buttonBoxLayout.addWidget(self.replace2DButton, 0, 2)

        self.buttonBoxLayout.addWidget(self.addButton, 1, 0)
        self.buttonBoxLayout.addWidget(self.removeButton, 1, 1)
        self.buttonBoxLayout.addWidget(self.replaceButton, 1, 2)

        self.mainLayout.addWidget(buttonBox)

        self.add2DButton.clicked.connect(self._add2DClicked)
        self.remove2DButton.clicked.connect(self._remove2DClicked)
        self.replace2DButton.clicked.connect(self._replace2DClicked)

        self.addButton.clicked.connect(self._addClicked)
        self.removeButton.clicked.connect(self._removeClicked)
        self.replaceButton.clicked.connect(self._replaceClicked)

    def _buildActionsQt3(self):
        self.buttonBox = qt.QWidget(self)
        buttonBox = self.buttonBox
        self.buttonBoxLayout = qt.QHBoxLayout(buttonBox)

        self.addButton = qt.QPushButton(buttonBox)
        self.addButton.setText("ADD")
        self.removeButton = qt.QPushButton(buttonBox)
        self.removeButton.setText("REMOVE")
        self.replaceButton = qt.QPushButton(buttonBox)
        self.replaceButton.setText("REPLACE")

        self.buttonBoxLayout.addWidget(self.addButton)
        self.buttonBoxLayout.addWidget(self.removeButton)
        self.buttonBoxLayout.addWidget(self.replaceButton)

        self.mainLayout.addWidget(buttonBox)

        self.addButton.clicked.connect(self._addClicked)

        self.removeButton.clicked.connect(self._removeClicked)

        self.replaceButton.clicked.connect(self._replaceClicked)


    def groupSignal(self,i):
        self.allImages = i

    def widgetSignal(self,dict=None):
        if dict is None:
            dict = {}
        if 'event' in dict:
            if dict['event']    == 'plotChanged':
                self.__plotting = dict['plot']
                self.__refreshSelection()
            elif dict['event'] in ['mouseMoved', 'MouseAt']:
                x = round(dict['y'])
                if x < 0: x = 0
                y = round(dict['x'])
                if y < 0: y = 0
                if (self.data is None) or \
                   (self.currentArray is None):
                    self.infoText.setText("    X = %d Y = %d Z = ????" %\
                                                   (y, x))
                else:
                    limits = self.lastData.shape
                    x = min(int(x), limits[0]-1)
                    y = min(int(y), limits[1]-1)

                    z = self.lastData[x, y]
                    self.infoText.setText("    X = %d Y = %d Z = %.4g" %\
                                                   (y, x, z))
            elif dict['event'] in ['mouseClicked', 'MouseClick']:
                if self.justViewer:
                    return
                col = min(int(round(dict['x'])), self._x1Limit - 1)
                row = min(int(round(dict['y'])), self._y1Limit - 1)
                if row < 0: row = 0
                if col < 0: col = 0
                if self.data is None:
                    self.graph.removeImage(legend="QEdfFileWidget")
                    wid = self.__getParamWidget('array')
                    wid.setImages(1)
                    return
                if self.data.sourceName is None:return
                if self.selection is None:
                    self.selection = {}
                nsel = {}
                i = 0
                for sname in self.data.sourceName:
                    if i == 0:
                        selfdatasourceName = sname
                        i = 1
                    else:
                        selfdatasourceName += "|"+sname
                nsel['SourceType'] = self.data.sourceType
                nsel['SourceName'] = selfdatasourceName
                nsel['selection']  = None
                key_list = self.data.getSourceInfo()['KeyList']
                if self.currentArray == len(key_list):
                    key = '0.0'
                else:
                    key = key_list[self.currentArray]
                if self.allImages:
                    arraynamelist = key_list
                else:
                    arraynamelist = [key]
                for key in arraynamelist:
                    nsel['Key']        = key
                    signalsel = {}
                    signalsel['SourceType'] = self.data.sourceType
                    signalsel['SourceName'] = self.data.sourceName
                    signalsel['selection']  = None
                    signalsel['Key']  = key
                    if self.__plotting == 'Rows':
                        ptype = 'rows'
                        nsel[key] = {'rows':[{'y':row,'x':None}],'cols':[]}
                        signalsel['Key'] += ".r.%d" % row
                    else:
                        nsel[key] = {'rows':[],'cols':[{'y':col,'x':None}]}
                        signalsel['Key'] += ".c.%d" % col
                        ptype = 'cols'
                    name = ""

                    i = int(key.split(".")[0])
                    if i > 0:
                        signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                    else:
                        signalsel['legend'] = "EDF Stack "+ os.path.basename(self.data.sourceName[0])+\
                                              " "+signalsel['Key']
                    if self.selection == {}:
                        self.setSelected([nsel],reset=0)
                        self.sigAddSelection.emit([signalsel])
                    elif not (nsel['SourceName'] in self.selection):
                        self.setSelected([nsel],reset=0)
                        self.sigAddSelection.emit([signalsel])
                    elif not (key in self.selection[nsel['SourceName']]):
                        self.setSelected([nsel],reset=0)
                        self.sigAddSelection.emit([signalsel])
                    elif len(self.selection[nsel['SourceName']][key][ptype]) == 0:
                        self.setSelected([nsel],reset=0)
                        self.sigAddSelection.emit([signalsel])
                    elif nsel[key][ptype][0] not in self.selection[nsel['SourceName']][key][ptype]:
                        self.setSelected([nsel],reset=0)
                        self.sigAddSelection.emit([signalsel])
                    else:
                        self.removeSelection([nsel])
            elif dict['event']  == 'imageChanged':
                _logger.debug("Image changed")
                if dict['index'] != self.currentArray:
                    self.currentArray = dict['index']
                    self.refresh()
                _logger.debug("self.currentArray = %s", self.currentArray)

    def openFile(self, filename=None,justloaded=None):
        _logger.debug("openfile = %s", filename)
        if justloaded is None:justloaded = 0
        if filename is None:
            self.lastInputDir = PyMcaDirs.inputDir
            wdir = self.lastInputDir
            filetypelist = ["EdfFiles (*.edf)",
                            "EdfFiles (*mca)",
                            "EdfFiles (*ccd)",
                            "All files (*)"]
            message = "Open new EdfFile(s)"
            filelist = PyMcaFileDialogs.getFileList(parent=None, filetypelist=None, message=None,
                                                    currentdir=wdir, mode="OPEN", getfilter=False,
                                                    single=False, currentfilter=None, native=None)
            if not len(filelist):
                return
            #respect selection choice
            #filelist.sort()
            filename=[]
            for f in filelist:
                filename.append(qt.safe_str(f))
            if not len(filename):
                return
            if len(filename):
                self.lastInputDir  = os.path.dirname(filename[0])
                PyMcaDirs.inputDir = os.path.dirname(filename[0])
            justloaded = 1
        if justloaded:
            if type(filename) != type([]):
                filename = [filename]
        if not os.path.exists(filename[0]):
            raise IOError("File %s does not exist" % filename[0])
        if (justloaded) and (filename in self.mapComboName.keys()):
            self.selectFile(filename,justloaded=justloaded)
        elif 1:
            combokey = os.path.basename(filename[0])
            self.mapComboName[combokey]= filename
            self.selectFile(combokey,justloaded=justloaded)
        else:
            if not self.data.SetSource(filename):
                qt.QMessageBox.critical(self, "ERROR opening EdfFile",
                        "Cannot open following EdfFile:\n%s"%(filename))
            else:
                filename= self.data.SourceName.split("|")
                if len(filename) > 1:
                    combokey = 'EDF Stack'
                    self._edfstack = filename
                else:
                    combokey = os.path.basename(filename[0])
                if combokey not in self.mapComboName.keys():
                    self.mapComboName[combokey]= filename[0]
                    self.fileCombo.insertItem(combokey)
                self.selectFile(combokey,justloaded=justloaded)

    def selectFile(self, filename=None, justloaded=None):
        if justloaded is None:justloaded=0
        if filename is not None:
            #if qt.safe_str(self.fileCombo.currentText()) !=\
            #   self.mapComboName[filename]:
            if filename == 'EDF Stack':
                filename= self._edfstack
            else:
                filename = self.mapComboName[filename]
            if justloaded and (filename==self._edfstack):
                self.currentArray=len(self.data.getSourceInfo()['KeyList'])
            else:
                self.currentArray=0
        self.refresh()

    def selectColormap(self):
        if self.colormap is None: return
        if self.colormapDialog.isHidden():
            self.colormapDialog.show()
        self.colormapDialog.raise_()
        self.colormapDialog.show()

    def getPixmapFromData(self, data, colormap):
        finiteData = numpy.isfinite(data)
        goodData = finiteData.min()

        if self.colormapDialog is not None:
            minData = self.colormapDialog.dataMin
            maxData = self.colormapDialog.dataMax
        else:
            if goodData:
                minData = data.min()
                maxData = data.max()
            else:
                tmpData = data[finiteData]
                if tmpData.size > 0:
                    minData = tmpData.min()
                    maxData = tmpData.max()
                else:
                    minData = None
                    maxData = None
                tmpData = None
        if colormap is None:
            if minData is None:
                (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                1,
                                (0, 1),
                                (0, 255), 1)
            else:
                (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                0,
                                (minData,maxData),
                                (0, 255), 1)
        else:
            if len(colormap) < 7:
                colormap.append(spslut.LINEAR)
            if goodData:
                (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                colormap[1],
                                (colormap[2],colormap[3]),
                                (0,255), 1)
            elif colormap[1]:
                #autoscale
                if minData is None:
                    (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (self.__defaultColormapType,3.0),
                                "RGBX",
                                self.__defaultColormap,
                                1,
                                (0, 1),
                                (0, 255), 1)
                else:
                    (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                0,
                                (minData,maxData),
                                (0,255), 1)
            else:
                (pixmap,size,minmax)= spslut.transform(\
                                data,
                                (1,0),
                                (colormap[6],3.0),
                                "RGBX",
                                COLORMAPLIST[int(str(colormap[0]))],
                                colormap[1],
                                (colormap[2],colormap[3]),
                                (0,255), 1)

        pixmap = pixmap.reshape(data.shape[0], data.shape[1], 4)
        if not goodData:
            pixmap[finiteData < 1] = 255
        return pixmap

    def updateColormap(self, *var):
        if len(var) == 1:
            var = var[0]
        if len(var) > 6:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5],
                             var[6]]
        elif len(var) > 5:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5]]
        else:
            self.colormap = [var[0],
                             var[1],
                             var[2],
                             var[3],
                             var[4],
                             var[5]]
        #self.graph.invertYAxis(True)
        pixmap = self.getPixmapFromData(self.lastData, self.colormap)
        self.graph.addImage(pixmap, legend="QEdfFileWidget")
        self.graph.replot()

    def closeFile(self, filename=None):
        if filename is None:
            ffile= qt.safe_str(self.fileCombo.currentText())
            #if file != "EDF Stack":
            #    filename = self.mapComboName[file]
            #else:
            #    filename ="EDF Stack"
            filename = ffile

        #print self.selection
        if (self.selection is not None) and filename in self.selection:
            nmca = 0
            mcakeys = list(self.selection[filename].keys())
            for key in mcakeys:
                nmca += len(self.selection[filename][key]['rows']) + len(self.selection[filename][key]['cols'])
            if nmca:
                msg= "%d mca are linked to that EdfFile source.\n"% nmca
                msg+="Do you really want to delete all these graphs ??"
                ans= qt.QMessageBox.information(self, "Remove SpecFile %s"%filename, msg,
                        qt.QMessageBox.No, qt.QMessageBox.Yes)
                if ans==qt.QMessageBox.No: return
                try:
                    self.sigDelSelection.emit((self.data.SourceName, mcakeys))
                except Exception:
                    _logger.debug("sigDelSelection is to be implemented")

        for idx in range(self.fileCombo.count()):
            itext = self.fileCombo.itemText(idx)
            if filename == "EDF Stack":
                if itext == filename:
                    self.fileCombo.removeItem(idx)
                    del self.mapComboName[filename]
                    break
            elif qt.safe_str(itext) ==\
                 os.path.basename(self.mapComboName[filename]):
                self.fileCombo.removeItem(idx)
                del self.mapComboName[filename]
                break

        if not self.fileCombo.count():
            self.data.sourceName = None
            self._reset()
            #self.selectFile()
        else:
            self.selectFile(self.mapComboName.keys()[0])

    def __fileSelection(self, ffile):
        ffile= qt.safe_str(ffile)
        for filename, comboname in self.mapComboName.items():
            if filename == ffile:
                self.selectFile(filename)
                break

    def _reset(self):
        self.graph.removeImage(legend="QEdfFileWidget")
        self.oldsource = None
        self.graph.clearMarkers()
        self.graph.replot()
        wid = self.__getParamWidget('array')
        wid.setImages(1)
        wid.setDataSize(0, 0)

    def setDataSource(self,data=None):
        _logger.debug("setData(self, data) called")
        _logger.debug("data = %s", data)
        self.data= data
        self.refresh()

    def refresh(self):
        _logger.debug("refresh method called")
        if self.data is None:
            self._reset()
            #wid = self.__getParamWidget('array')
            #wid.setImages(1)
            return
        if self.data.sourceName is None:
            return
        self.currentFile = self.data.sourceName
        #this gives the number of images in the file
        infoSource = self.data.getSourceInfo()
        _logger.debug("info :")
        _logger.debug("%s", infoSource)

        nimages=len(infoSource['KeyList'])
        #print self.data.SourceName,"nimages = ",nimages
        loadsum = 0
        if nimages == 1:
            self.currentArray =  0
        elif self.currentArray > nimages:
            self.currentArray =  0
        elif self.currentArray == nimages:
            loadsum=1
        #print "SUM = ",loadsum, infoSource['KeyList']
        #print self.currentArray
        if (self.oldsource != self.currentFile) or (self.oldcurrentArray != self.currentArray):
            _logger.debug("I have to read again ... ")
            if not loadsum:
                _logger.debug("Not Loading the sum")
                dataObject = self.data.getDataObject(infoSource['KeyList']\
                                                     [self.currentArray])
                info = dataObject.info
                data = dataObject.data
                imageinfo = infoSource['KeyList']
            else:
                _logger.debug("Loading the sum")
                dataObject = self.data.getDataObject('0.0')
                info = dataObject.info
                data = dataObject.data
                imageinfo = infoSource['KeyList']
            wid= self.__getParamWidget("array")
            if nimages > 1:
                if 'Title' in info:
                    i = 0
                    for key in self.data.getSourceInfo()['KeyList']:
                        source,image = key.split(".")
                        source = int(source)
                        image  = int(image)
                        dataObject = self.data.getDataObject(key)
                        header = dataObject.info
                        if 'Title' in header:
                            imageinfo[i] += "- " + header['Title']
                        i+=1
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    _logger.debug("ADDING 0.0 - SUM KEY")
                    wid.setImages(nimages+1, info = imageinfo+["0.0 - SUM"])
                wid.setImages(nimages,info = imageinfo)
            else:
                if 'Title' in info:
                    imageinfo [self.currentArray] += info['Title']
                wid.setImages(nimages,  info = imageinfo)
            wid.setCurrentImage(self.currentArray)
            #P.B. -> pointer(a,d1,d2,i1,i2) = a+ (i1+i2 * d1)
            wid.setDataSize(int(info["Dim_2"]), int(info["Dim_1"]))
            _logger.debug("Image size = %d x %d",
                          int(info["Dim_2"]), int(info["Dim_1"]))
            _logger.debug("data  size = %s", data.shape)

            if self.graph.isHidden():
                self.graph.show()
            ##self.graph.setx1axislimits(0, int(info["Dim_2"]))
            ##self.graph.sety1axislimits(0, int(info["Dim_1"]))
            self._x1Limit = int(info["Dim_1"])
            self._y1Limit = int(info["Dim_2"])
            self.graph.clear(replot=False)
            finiteData = numpy.isfinite(data)
            if finiteData.any():
                finiteData = data[finiteData]
                minData = finiteData.min()
                maxData = finiteData.max()
            else:
                minData = 0
                maxData = 1
            wasnone = 0
            self.lastData = data
            if self.colormapDialog is None:
                wasnone = 1
                self.colormapDialog = ColormapDialog.ColormapDialog()
                self.colormapDialog.colormapIndex  = self.colormapDialog.colormapList.index("Temperature")
                self.colormapDialog.colormapString = "Temperature"
                self.colormapDialog.sigColormapChanged.connect( \
                                self.updateColormap)
            self.colormapDialog.setDataMinMax(minData, maxData)
            if wasnone:
                self.colormapDialog.setAutoscale(1)
                self.colormapDialog.setColormap(self.colormapDialog.colormapIndex)
            self.colormap = (self.colormapDialog.colormapIndex,
                             self.colormapDialog.autoscale,
                             self.colormapDialog.minValue,
                             self.colormapDialog.maxValue,
                             minData, maxData)
            #self.graph.imagePlot(data=data, colormap = self.colormap)
            self.colormapDialog._update()
            pixmap = self.getPixmapFromData(data, self.colormap)
            self.graph.addImage(pixmap, legend="QEdfFileWidget")
        self.__refreshSelection()
        self.oldsource       = "%s" % self.data.sourceName
        self.oldcurrentArray = self.currentArray * 1

    def __getParamWidget(self, widtype):
        return self.paramWidget

    def _replaceClicked(self):
        _logger.debug("replace clicked")
        selkeys= self.__getSelectedKeys()
        if len(selkeys):
            #self.eh.event(self.repEvent, selkeys)
            _logger.debug("Replace event")
            if self.allImages:
                arraynamelist = self.data.getSourceInfo()['KeyList']
            else:
                arraynamelist = []
                for selection in selkeys:
                    arraynamelist.append(selection['Key'])
            sellist=[]
            signalsellist = []
            for arrayname in arraynamelist:
                sel = {}
                sel['SourceType'] = SOURCE_TYPE
                for selection in selkeys:
                    signalsel = {}
                    signalsel.update(sel)
                    signalsel['selection']  = None
                    signalsel['SourceName'] = self.data.sourceName
                    if not ('SourceName' in sel):
                        sel['SourceName'] = selection['SourceName']
                    arrayname = selection['Key']
                    if not ('Key' in sel):
                        sel['Key'] = selection['Key']
                    signalsel['Key'] = selection['Key']
                    if not (arrayname in sel):
                        sel[arrayname] = {'rows':[],'cols':[]}
                    if selection['plot'] == 'cols':
                        sel[arrayname]['cols'].append({'x':selection['x'],'y':selection['y']})
                        signalsel['Key'] += ".c.%d" % selection['y']
                    if selection['plot'] == 'rows':
                        sel[arrayname]['rows'].append({'x':selection['x'],'y':selection['y']})
                        signalsel['Key'] += ".r.%d" % selection['y']
                    i = int(signalsel['Key'].split(".")[0])
                    if i > 0:
                        signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                    else:
                        signalsel['legend'] = "EDF Stack "+ \
                                              os.path.basename(self.data.sourceName[0])+\
                                              " "+signalsel['Key']

                    """
                    if selection['plot'] == 0:
                         sel[arrayname]['mca'].append({'x':selection['x'],'y':selection['y']})
                    """
                    signalsellist.append(signalsel)
                sellist.append(sel)
            self.setSelected(sellist,reset=1)
            self.sigReplaceSelection.emit(signalsellist)

    def _add2DClicked(self, replace=False, emit=True):
        _logger.debug("ADD 2D clicked")
        if (self.data is None) or \
           (self.currentArray is None):
            return

        #this is not very efficient because it could be cached
        #while this implies a new reading
        infoSource= self.data.getSourceInfo()
        sel = {}
        sel['SourceType'] = infoSource['SourceType']
        sel['SourceName'] = self.data.sourceName
        sel['Key'] = infoSource['KeyList'][self.currentArray]
        f, i = sel['Key'].split(".")
        f = int(f) - 1
        sel['legend'] = os.path.basename(self.data.sourceName[f]) +\
                        " "+ ("%s" % self.paramWidget.iCombo.currentText())
        sel['selectiontype'] = '2D'
        sel['imageselection']  = True
        sel['mcaselection']  = False
        sel['scanselection'] = False
        sel['selection'] = None
        if emit:
            if replace:
                self.sigReplaceSelection.emit([sel])
            else:
                self.sigAddSelection.emit([sel])
        else:
            return [sel]

    def _remove2DClicked(self):
        _logger.debug("REMOVE 2D clicked")
        infoSource= self.data.getSourceInfo()
        sel = {}
        sel['SourceType'] = infoSource['SourceType']
        sel['SourceName'] = self.data.sourceName
        sel['Key'] = infoSource['KeyList'][self.currentArray]
        f, i = sel['Key'].split(".")
        f = int(f) - 1
        sel['legend'] = os.path.basename(self.data.sourceName[f]) +\
                        " "+ qt.safe_str(self.paramWidget.iCombo.currentText())
        sel['selectiontype'] = '2D'
        sel['imageselection']  = True
        sel['mcaselection']  = False
        sel['scanselection'] = False
        sel['selection'] = None
        self.sigRemoveSelection.emit([sel])

    def _replace2DClicked(self):
        _logger.debug("REPLACE 2D clicked")
        self._add2DClicked(replace=True)

    def currentSelectionList(self):
        a = self._addClicked(emit=False)
        if a in [None, []]:
            a = self._add2DClicked(emit=False)
        return a

    def _addClicked(self, emit=True):
        _logger.debug("select clicked")
        selkeys= self.__getSelectedKeys()
        _logger.debug("selected keys = %s", selkeys)
        if len(selkeys):
            #self.eh.event(self.addEvent, selkeys)
            _logger.debug("Select event")
            if self.allImages:
                arraynamelist = self.data.getSourceInfo()['KeyList']
            else:
                arraynamelist = []
                for selection in selkeys:
                    arraynamelist.append(selection['Key'])
            sellist=[]
            sellistsignal = []
            for arrayname in arraynamelist:
                sel = {}
                sel['SourceType'] = SOURCE_TYPE
                for selection in selkeys:
                    selsignal = {}
                    selsignal['SourceType'] = self.data.sourceType
                    selsignal['SourceName'] = self.data.sourceName
                    selsignal['selection'] = None
                    selsignal['Key'] = arrayname
                    if not ('SourceName' in sel):
                        sel['SourceName'] = selection['SourceName']
                    #arrayname = selection['Key']
                    if not ('Key' in sel):
                        sel['Key'] = arrayname
                    if not (arrayname in sel):
                        sel[arrayname] = {'rows':[],'cols':[]}
                    if selection['plot'] == 'cols':
                        sel[arrayname]['cols'].append({'x':selection['x'],
                                                        'y':selection['y']})
                        selsignal["Key"] += ".c.%d" % int(selection['y'])
                        i = int(selsignal["Key"].split(".")[0])
                        if i > 0:
                            selsignal['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+selsignal['Key']
                        else:
                            selsignal['legend'] = "EDF Stack "+ os.path.basename(self.data.sourceName[0])+\
                                                  " "+selsignal['Key']
                    if selection['plot'] == 'rows':
                        sel[arrayname]['rows'].append({'x':selection['x'],
                                                        'y':selection['y']})
                        selsignal["Key"] += ".r.%d" % int(selection['y'])
                        i = int(selsignal["Key"].split(".")[0])
                        if i > 0:
                            selsignal['legend'] = os.path.basename(self.data.sourceName[i-1]) +\
                                                  " "+selsignal['Key']
                        else:
                            selsignal['legend'] = "EDF Stack "+\
                                                  os.path.basename(self.data.sourceName[0])+\
                                                  " "+selsignal['Key']
                    sellistsignal.append(selsignal)
                sellist.append(sel)
            if self.selection is None:
                self.setSelected(sellist,reset=1)
            else:
                self.setSelected(sellist,reset=0)
            if emit:
                self.sigAddSelection.emit(sellistsignal)
            else:
                return sellistsignal


    def __getSelectedKeys(self):
        selkeys= []
        parwid= self.paramWidget
        #.visibleWidget()
        if self.currentArray is not None:
            for sel in parwid.getSelection():
                sel["SourceName"]= self.currentFile
                sel['SourceType'] = SOURCE_TYPE
                if 0:
                    sel["Key"]= "%d" % self.currentArray
                else:
                    keylist = self.data.getSourceInfo()['KeyList']
                    if self.currentArray == len(keylist):
                        sel["Key"]= "0.0"
                    else:
                        sel["Key"]= keylist[self.currentArray]
                selkeys.append(sel)
        return selkeys

    def _removeClicked(self):
        _logger.debug("remove clicked")
        selkeys= self.__getSelectedKeys()
        returnedselection=[]
        signalsellist = []
        if len(selkeys):
            #self.eh.event(self.delEvent, selkeys)
            _logger.debug("Remove Event")
            _logger.debug("self.selection before = %s", self.selection)
            if self.allImages:
                arraynamelist = self.data.getSourceInfo()['KeyList']
            else:
                arraynamelist = []
                for selection in selkeys:
                    arraynamelist.append(selection['Key'])
            for arrayname in arraynamelist:
                for selection in selkeys:
                    sel = {}
                    i = 0
                    for sname in self.data.sourceName:
                        if i == 0:
                            selfdatasourceName = sname
                            i = 1
                        else:
                            selfdatasourceName += "|"+sname
                    sel['SourceName'] = selfdatasourceName
                    sel['SourceType'] = SOURCE_TYPE
                    #sel['Key'] = selection['Key']
                    #arrayname = "%s" % selection['Key']
                    sel['Key'] = arrayname
                    sel[arrayname] = {'rows':[],'cols':[]}
                    if selection['plot'] == 'cols':
                         sel[arrayname]['cols'].append({'x':selection['x'],'y':selection['y']})
                    if selection['plot'] == 'rows':
                         sel[arrayname]['rows'].append({'x':selection['x'],'y':selection['y']})
                    if self.selection is not None:
                        _logger.debug("step 1")
                        if sel['SourceName'] in self.selection:
                            _logger.debug("step 2")
                            if arrayname in self.selection[sel['SourceName']]:
                                _logger.debug("step 3")
                                if 'rows' in self.selection[sel['SourceName']][arrayname]:
                                    _logger.debug("step 4")
                                    for couple in  sel[arrayname]['rows']:
                                        if couple in  self.selection[sel['SourceName']][arrayname]['rows']:
                                            index= self.selection[sel['SourceName']][arrayname]['rows'].index(couple)
                                            del self.selection[sel['SourceName']][arrayname]['rows'][index]
                                            signalsel = {}
                                            signalsel.update(sel)
                                            signalsel['SourceName'] = self.data.sourceName
                                            signalsel['Key'] += ".r.%d" % couple['y']
                                            i = int(signalsel['Key'].split(".")[0])
                                            if i > 0:
                                                signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                                            else:
                                                signalsel['legend'] = "EDF Stack "+ \
                                                                      os.path.basename(self.data.sourceName[0])+\
                                                                      " "+signalsel['Key']
                                            signalsellist.append(signalsel)
                                    for couple in  sel[arrayname]['cols']:
                                        if couple in  self.selection[sel['SourceName']][arrayname]['cols']:
                                            index= self.selection[sel['SourceName']][arrayname]['cols'].index(couple)
                                            del self.selection[sel['SourceName']][arrayname]['cols'][index]
                                            signalsel = {}
                                            signalsel.update(sel)
                                            signalsel['SourceName'] = self.data.sourceName
                                            signalsel['Key'] += ".c.%d" % couple['y']
                                            i = int(signalsel['Key'].split(".")[0])
                                            if i > 0:
                                                signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                                            else:
                                                signalsel['legend'] = "EDF Stack "+ \
                                                                      os.path.basename(self.data.sourceName[0])+\
                                                                      " "+signalsel['Key']
                                            signalsellist.append(signalsel)
                                    seln = {}
                                    seln['SourceName'] = sel['SourceName']
                                    seln['SourceType'] = SOURCE_TYPE
                                    seln['Key']        = sel['Key']
                                    seln[seln['Key']]  = self.selection[seln['SourceName']][seln['Key']]
                                    self.setSelected([seln],reset=0)
                    returnedselection.append(sel)
            self.sigRemoveSelection.emit(signalsellist)

    def removeSelection(self,selection):
        if type(selection) != type([]):
            selection=[selection]
        signalsellist = []
        for sel in selection:
                arrayname = sel['Key']
                if self.selection is not None:
                    _logger.debug("step 1")
                    if sel['SourceName'] in self.selection:
                        _logger.debug("step 2")
                        if arrayname in self.selection[sel['SourceName']]:
                            _logger.debug("step 3")
                            if 'rows' in self.selection[sel['SourceName']][arrayname]:
                                _logger.debug("step 4")
                                for couple in  sel[arrayname]['rows']:
                                    if couple in  self.selection[sel['SourceName']][arrayname]['rows']:
                                        index= self.selection[sel['SourceName']][arrayname]['rows'].index(couple)
                                        del self.selection[sel['SourceName']][arrayname]['rows'][index]
                                        signalsel = {}
                                        signalsel.update(sel)
                                        signalsel['SourceName'] = self.data.sourceName
                                        signalsel['Key'] += ".r.%d" % couple['y']
                                        i = int(signalsel['Key'].split(".")[0])
                                        if i > 0:
                                            signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                                        else:
                                            signalsel['legend'] = "EDF Stack "+ \
                                                                  os.path.basename(self.data.sourceName[0])+\
                                                                  " "+signalsel['Key']
                                        signalsellist.append(signalsel)
                                for couple in  sel[arrayname]['cols']:
                                    if couple in  self.selection[sel['SourceName']][arrayname]['cols']:
                                        index= self.selection[sel['SourceName']][arrayname]['cols'].index(couple)
                                        del self.selection[sel['SourceName']][arrayname]['cols'][index]
                                        signalsel = {}
                                        signalsel.update(sel)
                                        signalsel['SourceName'] = self.data.sourceName
                                        signalsel['Key'] += ".r.%d" % couple['y']
                                        i = int(signalsel['Key'].split(".")[0])
                                        if i > 0:
                                            signalsel['legend'] = os.path.basename(self.data.sourceName[i-1]) +" "+signalsel['Key']
                                        else:
                                            signalsel['legend'] = "EDF Stack "+ \
                                                                  os.path.basename(self.data.sourceName[0])+\
                                                                  " "+signalsel['Key']
                                        signalsellist.append(signalsel)
                                seln = {}
                                seln['SourceName'] = sel['SourceName']
                                seln['SourceType'] = SOURCE_TYPE
                                seln['Key']        = sel['Key']
                                seln[seln['Key']]  = self.selection[seln['SourceName']][seln['Key']]
                                self.setSelected([seln],reset=0)
        self.sigRemoveSelection.emit(signalsellist)

    def setSelected(self,sellist,reset=1):
        _logger.debug("setSelected(self,sellist,reset=1) called")
        _logger.debug("sellist = %s", sellist)
        _logger.debug("selection before = %s", self.selection)
        _logger.debug("reset = %s", reset)
        if reset:
            self.selection = {}
        elif self.selection is None:
            self.selection = {}
        for sel in sellist:
            specname = sel['SourceName']
            if type(specname) == type([]):
                for i in range(len(sel['SourceName'])):
                    if i == 0:
                        specname = sel['SourceName'][i]
                    else:
                        specname += "|"+sel['SourceName'][i]
            #selkey is the array name what to do if multiple array names?
            if type(sel["Key"]) == type([]):
                selkey = sel["Key"][0]
            else:
                selkey = sel["Key"]
            if not (specname in self.selection):
                self.selection[specname]= {}
            if not (selkey in self.selection[specname]):
                self.selection[specname][selkey] = {'rows':[],'cols':[]}
            if 'rows' in sel[selkey]:
                for rowsel in sel[selkey]['rows']:
                    if rowsel not in self.selection[specname][selkey]['rows']:
                        self.selection[specname][selkey]['rows'].append(rowsel)
            if 'cols' in sel[selkey]:
                for rowsel in sel[selkey]['cols']:
                    if rowsel not in self.selection[specname][selkey]['cols']:
                        self.selection[specname][selkey]['cols'].append(rowsel)
        _logger.debug("self.selection after = %s", self.selection)
        self.__refreshSelection()

    def getSelection(self):
        """
        Give the dicionary of dictionaries as an easy to understand list of
        individual selections
        """
        selection = []
        if self.selection is None: return selection
        for sourcekey in self.selection.keys():
            for arraykey in self.selection[sourcekey].keys():
                sel={}
                sel['SourceName']   = sourcekey
                sel['SourceType']   = 'EdfFile'
                sel['Key']          = arraykey
                sel[arraykey]        = self.selection[sourcekey][arraykey]
                selection.append(sel)
        return selection


    def __refreshSelection(self):
        _logger.debug("__refreshSelection(self) called")
        _logger.debug(self.selection)
        if self.data:
            _logger.debug("self.data.SourceName = %s", self.data.sourceName)
        if self.selection is not None:
            if self.data is None:
                return
            if self.data.sourceName is None:
                return
            if type(self.data.sourceName) == type([]):
                i = 0
                for sname in self.data.sourceName:
                    if i == 0:
                        selfdatasourceName = sname
                        i = 1
                    else:
                        selfdatasourceName += "|"+sname
            else:
                selfdatasourceName = self.data.sourceName
            if "|" in self.data.sourceName:
                #print "here should be the multiple"
                #sel = self.selection.get(self.data.SourceName[0], {})
                sel = self.selection.get(selfdatasourceName, {})
            else:
                sel = self.selection.get(selfdatasourceName, {})
            selkeys = []
            for key in sel.keys():
                if (sel[key]['rows'] != []) or (sel[key]['cols'] !=  []):
                    selkeys.append(key)
            _logger.debug("selected images = %s but self.selection = %s",
                          selkeys, self.selection)
            _logger.debug("and self.selection.get(self.data.SourceName, {}) = %s ", sel)

            wid = self.__getParamWidget("array")
            wid.markImageSelected(selkeys)
            #imagedict = sel.get("%d" % self.currentArray, {})
            keylist = self.data.getSourceInfo()['KeyList']
            if self.currentArray == len(keylist):
                imagedict = sel.get("0.0",{})
            else:
                imagedict = sel.get(keylist[self.currentArray],{})
            if not ('rows' in imagedict):
                imagedict['rows'] = []
            if not ('cols' in imagedict):
                imagedict['cols'] = []
            rows = []
            for ddict in imagedict['rows']:
                if 'y' in ddict:
                    if ddict['y'] not in rows:
                        rows.append(ddict['y'])
            wid.markRowSelected(rows)
            cols = []
            for ddict in imagedict['cols']:
                if 'y' in ddict:
                    if ddict['y'] not in cols:
                        cols.append(ddict['y'])
            wid.markColSelected(cols)
            self.graph.clearMarkers()
            for i in rows:
                label = "R%d" % i
                marker=self.graph.insertYMarker(i,
                                                label,
                                                text=label,
                                                color='white')
            for i in cols:
                label = "C%d" % i
                marker=self.graph.insertXMarker(i,
                                                label,
                                                text=label,
                                                color='white')
            self.graph.replot()
            return

    def closeEvent(self, event):
        if self.colormapDialog is not None:
            self.colormapDialog.close()
        if self._matplotlibSaveImage is not None:
            self._matplotlibSaveImage.close()
        qt.QWidget.closeEvent(self, event)


def test2():
    a= qt.QApplication(sys.argv)
    a.lastWindowClosed.connect(a.quit)

    w = EdfFile_StandardArray()
    w.show()
    a.exec()

def test():
    import sys
    from PyMca5.PyMcaCore import EdfFileDataSource
    def replaceSelection(sel):
        print("replaceSelection", sel)
    def removeSelection(sel):
        print("removeSelection", sel)
    def addSelection(sel):
        print("addSelection", sel)

    if qt.QApplication.instance() is None:
        a = qt.QApplication(sys.argv)
        a.lastWindowClosed.connect(a.quit)
        sys.excepthook = qt.exceptionHandler
    else:
        a = None
    w = QEdfFileWidget()
    #print w
    if len(sys.argv) > 1:
        d = EdfFileDataSource.EdfFileDataSource([sys.argv[1]])
    elif os.path.exists('test.edf'):
        d = EdfFileDataSource.EdfFileDataSource(['test.edf'])
    else:
        print("Usage:")
        print("python QEdfFileWidget edffile")
        sys.exit(0)
    w.setDataSource(d)
    w.sigAddSelection.connect(addSelection)
    w.sigRemoveSelection.connect(removeSelection)
    w.sigReplaceSelection.connect(replaceSelection)
    w.show()
    if a is not None:
        a.exec()
    else:
        return w

if __name__ == "__main__":
    test()

