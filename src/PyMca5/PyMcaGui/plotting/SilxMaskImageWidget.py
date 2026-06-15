# /*#########################################################################
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
# ###########################################################################*/
""":class:`SilxMaskImageWidget` uses a silx PlotWidget to display a stack,
while offering the same tools as the :class:`StackRoiWindow` (median filter,
background subtraction, ...). In addition to reimplementing existing tools,
it also provides methods to plot a background image underneath the stack
images.

"""

__authors__ = ["P. Knobel"]
__license__ = "MIT"


import copy
import numpy
import os

from PyMca5.PyMcaMath.PyMcaSciPy.signal.median import medfilt2d

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaIO import ArraySave
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaPlugins import MotorInfoWindow

try:
    from PyMca5.PyMcaGui.pymca import QPyMcaMatplotlibSave
except ImportError:
    QPyMcaMatplotlibSave = None


# temporarily disable logging when importing silx and fabio
import logging
logging.basicConfig()
logging.disable(logging.ERROR)

import silx
from silx.gui.plot import PlotWidget
from PyMca5.PyMcaGui.plotting import SilxPlotActions as PlotActions

from silx.gui.plot import PlotToolButtons
from silx.gui.plot.MaskToolsWidget import MaskToolsWidget, MaskToolsDockWidget
from silx.gui.plot.AlphaSlider import NamedImageAlphaSlider
from silx.gui.plot.Profile import ProfileToolBar
from silx.gui.plot.tools.profile.manager import ProfileWindow

from silx.gui import icons

logging.disable(logging.NOTSET)   # restore default logging behavior


def convertToRowAndColumn(x, y, shape,
                          xScale=None, yScale=None,
                          safe=True):
    """Return (row, column) of a pixel defined by (x, y) in an image.

    :param float x: Abscissa of point
    :param float x: Ordinate of point
    :param shape: Shape of image (nRows, nColumns)
    :param xScale: Tuple of linear scaling parameters (a, b),
        x = a + b * column
    :param yScale: Tuple of linear scaling parameters (a, b),
        y = a + b * row
    :param bool safe: If True, always return coordinates within the image's
        bounds.
    :return: 2-tuple (r, c)
    """
    if xScale is None:
        c = x
    else:
        c = (x - xScale[0]) / xScale[1]
    if yScale is None:
        r = y
    else:
        r = (y - yScale[0]) / yScale[1]

    if safe:
        c = min(int(c), shape[1] - 1)
        c = max(c, 0)
        r = min(int(r), shape[0] - 1)
        r = max(r, 0)
    else:
        c = int(c)
        r = int(r)
    return r, c

class MyProfileWindow(ProfileWindow):

    def createPlot1D(self, parent, backend):
        from PyMca5.PyMcaGui.pymca.SilxScanWindow import ScanWindow as PlotWindow
        plot = PlotWindow(parent, backend=backend)
        plot.setDataMargins(yMinMargin=0.1, yMaxMargin=0.1)
        plot.setGraphYLabel('Profile')
        plot.setGraphXLabel('')
        # do not overwrite the title by the legend
        plot.sigActiveCurveChanged.disconnect(plot._updateGraphTitle)
        positionInfo = plot.getPositionInfoWidget()
        positionInfo.setSnappingMode(positionInfo.SNAPPING_CURVE)
        return plot

class MyMaskToolsWidget(MaskToolsWidget):
    """Backport of the setSelectionMask behavior implemented in silx 0.6.0,
    to synchronize mask parameters with the active image.
    This widget must not be used with silx >= 0.6"""
    def setSelectionMask(self, mask, copy=True):
        """Set the mask to a new array.
        :param numpy.ndarray mask: The array to use for the mask.
        :type mask: numpy.ndarray of uint8 of dimension 2, C-contiguous.
                    Array of other types are converted.
        :param bool copy: True (the default) to copy the array,
                          False to use it as is if possible.
        :return: None if failed, shape of mask as 2-tuple if successful.
                 The mask can be cropped or padded to fit active image,
                 the returned shape is that of the active image.
        """
        mask = numpy.asarray(mask, dtype=numpy.uint8)
        if len(mask.shape) != 2:
            # _logger.error('Not an image, shape: %d', len(mask.shape))
            return None

        # ensure all mask attributes are synchronized with the active image
        activeImage = self.plot.getActiveImage()
        if activeImage is not None and activeImage.getLegend() != self._maskName:
            self._activeImageChanged()
            self.plot.sigActiveImageChanged.connect(self._activeImageChanged)

        if self._data.shape[0:2] == (0, 0) or mask.shape == self._data.shape[0:2]:
            self._mask.setMask(mask, copy=copy)
            self._mask.commit()
            return mask.shape
        else:
            resizedMask = numpy.zeros(self._data.shape[0:2],
                                      dtype=numpy.uint8)
            height = min(self._data.shape[0], mask.shape[0])
            width = min(self._data.shape[1], mask.shape[1])
            resizedMask[:height, :width] = mask[:height, :width]
            self._mask.setMask(resizedMask, copy=False)
            self._mask.commit()
            return resizedMask.shape


class MyMaskToolsDockWidget(MaskToolsDockWidget):
    """
    Regular MaskToolsDockWidget if silx version is at least 0.6.0,
    else it uses a backported MaskToolsWidget
    """
    def __init__(self, parent=None, plot=None, name='Mask'):
        super(MyMaskToolsDockWidget, self).__init__(parent, plot, name)
        if silx.version_info < (0, 6):
            self.setWidget(MyMaskToolsWidget(plot=plot))
            self.widget().sigMaskChanged.connect(self._emitSigMaskChanged)


class SaveImageListAction(qt.QAction):
    """Save current image  and mask (if any) in a :class:`MaskImageWidget`
    to EDF or CSV"""
    def __init__(self, title, maskImageWidget,
                 clipped=False, subtract=False):
        super(SaveImageListAction, self).__init__(QString(title),
                                                  maskImageWidget)
        self.maskImageWidget = maskImageWidget
        self.triggered[bool].connect(self.onTrigger)

        self.outputDir = PyMcaDirs.outputDir
        """Default output dir. After each save operation, this is updated
        to re-use the same folder for next save."""
        self.clipped = clipped
        """If True, clip data range to colormap min and max."""
        self.subtract = subtract
        """If True, subtract data min value."""

    def onTrigger(self):
        filename, saveFilter = self.getOutputFileNameFilter()
        if not filename:
            return

        if filename.lower().endswith(".csv"):
            csvseparator = "," if "," in saveFilter else\
                ";" if ";" in saveFilter else\
                "\t"
        else:
            csvseparator = None
        images, labels = self.getImagesLabels()

        self.saveImageList(filename, images, labels, csvseparator)

    def saveImageList(self, filename, imageList, labels,
                      csvseparator=None):
        if not imageList:
            qt.QMessageBox.information(
                    self,
                    "No Data",
                    "Image list is empty.\nNothing to be saved")
            return

        if filename.lower().endswith(".edf"):
            ArraySave.save2DArrayListAsEDF(imageList, filename, labels)
        elif filename.lower().endswith(".tif"):
            ArraySave.save2DArrayListAsMonochromaticTiff(imageList,
                                                         filename,
                                                         labels)
        elif filename.lower().endswith(".csv"):
            assert csvseparator is not None
            ArraySave.save2DArrayListAsASCII(imageList, filename, labels,
                                             csv=True,
                                             csvseparator=csvseparator)
        else:
            ArraySave.save2DArrayListAsASCII(imageList, filename, labels,
                                             csv=False)

    def getImagesLabels(self):
        """Return images to be saved and corresponding labels.

        Images are:
             - image currently displayed clipped to visible colormap range
             - mask

        If :attr:`subtract` is True, subtract the minimum image sample value
        to all samples."""
        imageList = []
        labels = []
        imageData = self.maskImageWidget.getImageData()
        colormapDict = self.maskImageWidget.getCurrentColormap()
        label = self.maskImageWidget.plot.getGraphTitle()
        if not label:
            label = "Image01"
        label.replace(' ', '_')
        if self.clipped and colormapDict is not None:
            autoscale = colormapDict['autoscale']
            if not autoscale:
                vmin = colormapDict['vmin']
                vmax = colormapDict['vmax']
                imageData = imageData.clip(vmin, vmax)
                label += ".clip(%f,%f)" % (vmin, vmax)
        if self.subtract:
            vmin = imageData.min()
            imageData = imageData - vmin
            label += "-%f" % vmin
        imageList.append(imageData)
        labels.append(label)

        mask = self.maskImageWidget.getSelectionMask()
        if mask is not None and mask.max() > 0:
            imageList.append(mask)
            labels.append(label + "_Mask")

        return imageList, labels

    def getOutputFileNameFilter(self):
        """Open a file dialog to get the output file name, and return the
        file name and the selected format filter.

        Remember output directory in attribute :attr:`outputDir`"""
        if os.path.exists(self.outputDir):
            initdir = self.outputDir
        else:
            # folder deleted, reset
            initdir = PyMcaDirs.outputDir

        formatlist = ["TIFF Files *.tif",
                      "ASCII Files *.dat",
                      "EDF Files *.edf",
                      'CSV(, separated) Files *.csv',
                      'CSV(; separated) Files *.csv',
                      'CSV(tab separated) Files *.csv']
        filelist, saveFilter = PyMcaFileDialogs.getFileList( \
                    parent=self.maskImageWidget,
                    filetypelist=formatlist,
                    message="",
                    currentdir=initdir,
                    mode="SAVE",
                    getfilter=True,
                    single=False,
                    currentfilter=None,
                    native=None)
        if not len(filelist):
            return "", ""
        filename = filelist[0]
        if filename:
            self.outputDir = os.path.dirname(filename)
            filterused = "." + saveFilter[-3:]
            PyMcaDirs.outputDir = os.path.dirname(filename)
            if len(filename) < 4 or filename[-4:] != filterused:
                filename += filterused
        else:
            filename = ""
        return filename, saveFilter

class SaveMatplotlib(qt.QAction):
    """Save current image ho high quality graphics using matplotlib"""
    def __init__(self, title, maskImageWidget):
        super(SaveMatplotlib, self).__init__(QString(title),
                                             maskImageWidget)
        self.maskImageWidget = maskImageWidget
        self.triggered[bool].connect(self.onTrigger)

        self._matplotlibSaveImage = None

    def onTrigger(self):
        imageData = self.maskImageWidget.getImageData()
        if self._matplotlibSaveImage is None:
            self._matplotlibSaveImage = QPyMcaMatplotlibSave.SaveImageSetup(
                    None, image=None)
        title = "Matplotlib " + self.maskImageWidget.plot.getGraphTitle()
        self._matplotlibSaveImage.setWindowTitle(title)
        ddict = self._matplotlibSaveImage.getParameters()

        colormapDict = self.maskImageWidget.getCurrentColormap()

        if colormapDict is not None:
            autoscale = colormapDict['autoscale']
            vmin = colormapDict['vmin']
            vmax = colormapDict['vmax']
            colormapType = colormapDict['normalization']  # 'log' or 'linear'
            if colormapType == 'log':
                colormapType = 'logarithmic'

            ddict['linlogcolormap'] = colormapType
            if not autoscale:
                ddict['valuemin'] = vmin
                ddict['valuemax'] = vmax
            else:
                ddict['valuemin'] = 0
                ddict['valuemax'] = 0

        # this sets the actual dimensions
        origin = self.maskImageWidget._origin
        delta = self.maskImageWidget._deltaXY

        ddict['xpixelsize'] = delta[0]
        ddict['xorigin'] = origin[0]
        ddict['ypixelsize'] = delta[1]
        ddict['yorigin'] = origin[1]

        ddict['xlabel'] = self.maskImageWidget.plot.getGraphXLabel()
        ddict['ylabel'] = self.maskImageWidget.plot.getGraphYLabel()
        limits = self.maskImageWidget.plot.getGraphXLimits()
        ddict['zoomxmin'] = limits[0]
        ddict['zoomxmax'] = limits[1]
        limits = self.maskImageWidget.plot.getGraphYLimits()
        ddict['zoomymin'] = limits[0]
        ddict['zoomymax'] = limits[1]

        self._matplotlibSaveImage.setParameters(ddict)
        self._matplotlibSaveImage.setImageData(imageData)
        self._matplotlibSaveImage.show()
        self._matplotlibSaveImage.raise_()


class SaveToolButton(qt.QToolButton):
    def __init__(self, parent=None, maskImageWidget=None):
        """

        :param maskImageWidget: Parent SilxMaskImageWidget
        """
        qt.QToolButton.__init__(self, parent)
        self.maskImageWidget = maskImageWidget
        self.setIcon(icons.getQIcon("document-save"))
        self.clicked.connect(self._saveToolButtonSignal)
        self.setToolTip('Save Graph')

        self._saveMenu = qt.QMenu()
        self._saveMenu.addAction(
                SaveImageListAction("Image Data", self.maskImageWidget))
        self._saveMenu.addAction(
                SaveImageListAction("Colormap Clipped Seen Image Data",
                                    self.maskImageWidget, clipped=True))
        self._saveMenu.addAction(
                SaveImageListAction("Clipped and Subtracted Seen Image Data",
                                    self.maskImageWidget, clipped=True, subtract=True))
        # standard silx save action
        self._saveMenu.addAction(PlotActions.SaveAction(
                plot=self.maskImageWidget.plot, parent=self))

        if QPyMcaMatplotlibSave is not None:
            self._saveMenu.addAction(SaveMatplotlib("Matplotlib",
                                                    self.maskImageWidget))

    def _saveToolButtonSignal(self):
        self._saveMenu.exec(self.parent().cursor().pos())


class MedianParameters(qt.QWidget):
    def __init__(self, parent=None, use_conditional=False):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.label = qt.QLabel(self)
        self.label.setText("Median filter width: ")
        self.widthSpin = qt.QSpinBox(self)
        self.widthSpin.setMinimum(1)
        self.widthSpin.setMaximum(99)
        self.widthSpin.setValue(1)
        self.widthSpin.setSingleStep(2)
        if use_conditional:
            self.conditionalLabel = qt.QLabel(self)
            self.conditionalLabel.setText("Conditional:")
            self.conditionalSpin = qt.QSpinBox(self)
            self.conditionalSpin.setMinimum(0)
            self.conditionalSpin.setMaximum(1)
            self.conditionalSpin.setValue(0)
        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.widthSpin)
        if use_conditional:
            self.mainLayout.addWidget(self.conditionalLabel)
            self.mainLayout.addWidget(self.conditionalSpin)


class SilxMaskImageWidget(qt.QMainWindow):
    """Main window with a plot widget, a toolbar and a slider.

    A list of images can be set with :meth:`setImages`.
    The mask can be accessed through getter and setter methods:
    :meth:`setSelectionMask` and :meth:`getSelectionMask`.

    The plot widget can be accessed as :attr:`plot`. It is a silx
    plot widget.

    The toolbar offers some basic interaction tools:
    zoom control, colormap, aspect ratio, y axis orientation,
    "save image" menu and a mask widget.
    """
    sigMaskImageWidget = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        qt.QMainWindow.__init__(self, parent=parent)
        if parent is not None:
            # behave as a widget
            self.setWindowFlags(qt.Qt.Widget)
        else:
            self.setWindowTitle("PyMca - Image Selection Tool")

        centralWidget = qt.QWidget(self)
        layout = qt.QVBoxLayout(centralWidget)
        centralWidget.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Plot
        self.plot = PlotWidget(parent=centralWidget)
        self.plot.setWindowFlags(qt.Qt.Widget)
        self.plot.setDefaultColormap({'name': 'temperature',
                                      'normalization': 'linear',
                                      'autoscale': True,
                                      'vmin': 0.,
                                      'vmax': 1.})

        layout.addWidget(self.plot)

        try:
            from silx.gui.widgets import ElidedLabel
            self.infoWidget = ElidedLabel.ElidedLabel(self)
        except Exception:
            self.infoWidget = qt.QLabel(self)
        layout.addWidget(self.infoWidget)
        self.infoWidget.hide()

        # Mask Widget
        self._maskToolsDockWidget = None

        # Image selection slider
        self.slider = qt.QSlider(self.centralWidget())
        self.slider.setOrientation(qt.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        layout.addWidget(self.slider)
        self.slider.valueChanged[int].connect(self.showImage)

        # ADD/REMOVE/REPLACE IMAGE buttons
        buttonBox = qt.QWidget(self)
        buttonBoxLayout = qt.QHBoxLayout(buttonBox)
        buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        buttonBoxLayout.setSpacing(0)
        self.addImageButton = qt.QPushButton(buttonBox)
        icon = qt.QIcon(qt.QPixmap(IconDict["rgb16"]))
        self.addImageButton.setIcon(icon)
        self.addImageButton.setText("ADD IMAGE")
        self.addImageButton.setToolTip("Add image to RGB correlator")
        buttonBoxLayout.addWidget(self.addImageButton)

        self.removeImageButton = qt.QPushButton(buttonBox)
        self.removeImageButton.setIcon(icon)
        self.removeImageButton.setText("REMOVE IMAGE")
        self.removeImageButton.setToolTip("Remove image from RGB correlator")
        buttonBoxLayout.addWidget(self.removeImageButton)

        self.replaceImageButton = qt.QPushButton(buttonBox)
        self.replaceImageButton.setIcon(icon)
        self.replaceImageButton.setText("REPLACE IMAGE")
        self.replaceImageButton.setToolTip(
                "Replace all images in RGB correlator with this one")
        buttonBoxLayout.addWidget(self.replaceImageButton)

        self.addImageButton.clicked.connect(self._addImageClicked)
        self.removeImageButton.clicked.connect(self._removeImageClicked)
        self.replaceImageButton.clicked.connect(self._replaceImageClicked)

        layout.addWidget(buttonBox)
        self._buttonBox = buttonBox

        # median filter widget
        self._medianParameters = {'row_width': 1,
                                  'column_width': 1,
                                  'conditional': 0}
        self._medianParametersWidget = MedianParameters(self,
                                                        use_conditional=True)
        self._medianParametersWidget.widthSpin.setValue(1)
        self._medianParametersWidget.widthSpin.valueChanged[int].connect(
                     self._setMedianKernelWidth)
        self._medianParametersWidget.conditionalSpin.valueChanged[int].connect(
                     self._setMedianConditionalFlag)
        layout.addWidget(self._medianParametersWidget)

        # motor positions (hidden by default)
        self.motorPositionsWidget = MotorInfoWindow.MotorInfoDialog(self,
                                                                    [""],
                                                                    [{}])
        self.motorPositionsWidget.setMaximumHeight(100)
        self.plot.sigPlotSignal.connect(self._updateMotors)
        self.motorPositionsWidget.hide()
        self._motors_first_update = True

        layout.addWidget(self.motorPositionsWidget)

        self.setCentralWidget(centralWidget)

        # Init actions
        self.group = qt.QActionGroup(self)
        self.group.setExclusive(False)

        self.resetZoomAction = self.group.addAction(
                PlotActions.ResetZoomAction(plot=self.plot, parent=self))
        self.addAction(self.resetZoomAction)

        self.zoomInAction = PlotActions.ZoomInAction(plot=self.plot, parent=self)
        self.addAction(self.zoomInAction)

        self.zoomOutAction = PlotActions.ZoomOutAction(plot=self.plot, parent=self)
        self.addAction(self.zoomOutAction)

        self.xAxisAutoScaleAction = self.group.addAction(
            PlotActions.XAxisAutoScaleAction(plot=self.plot, parent=self))
        self.addAction(self.xAxisAutoScaleAction)

        self.yAxisAutoScaleAction = self.group.addAction(
            PlotActions.YAxisAutoScaleAction(plot=self.plot, parent=self))
        self.addAction(self.yAxisAutoScaleAction)

        self.colormapAction = self.group.addAction(
                PlotActions.ColormapAction(plot=self.plot, parent=self))
        self.addAction(self.colormapAction)

        self.pixelIntensitiesHistoAction = self.group.addAction(
                PlotActions.PixelIntensitiesHistoAction(plot=self.plot, parent=self))
        self.addAction(self.pixelIntensitiesHistoAction)
        self.pixelIntensitiesHistoAction.setVisible(True)

        self.copyAction = self.group.addAction(
                PlotActions.CopyAction(plot=self.plot, parent=self))
        self.addAction(self.copyAction)

        self.group.addAction(self.getMaskAction())

        # Init toolbuttons
        self.saveToolbutton = SaveToolButton(parent=self,
                                             maskImageWidget=self)

        self.yAxisInvertedButton = PlotToolButtons.YAxisOriginToolButton(
            parent=self, plot=self.plot)

        self.keepDataAspectRatioButton = PlotToolButtons.AspectToolButton(
            parent=self, plot=self.plot)

        self.backgroundButton = qt.QToolButton(self)
        self.backgroundButton.setCheckable(True)
        self.backgroundButton.setIcon(qt.QIcon(qt.QPixmap(IconDict["subtract"])))
        self.backgroundButton.setToolTip(
            'Toggle background image subtraction from current image\n' +
            'No action if no background image available.')
        self.backgroundButton.clicked.connect(self._subtractBackground)

        # Creating the toolbar also create actions for toolbuttons
        self._toolbar = self._createToolBar(title='Plot', parent=None)
        self.addToolBar(self._toolbar)
        self._profile = ProfileToolBar(plot=self.plot,
                                       profileWindow=MyProfileWindow())
        self.addToolBar(self._profile)
        self.setProfileToolbarVisible(False)

        # add a transparency slider for the stack data
        self._alphaSliderToolbar = qt.QToolBar("Alpha slider", parent=self)
        self._alphaSlider = NamedImageAlphaSlider(parent=self._alphaSliderToolbar,
                                                  plot=self.plot,
                                                  legend="current")
        self._alphaSlider.setOrientation(qt.Qt.Vertical)
        self._alphaSlider.setToolTip("Adjust opacity of stack image overlay")
        self._alphaSliderToolbar.addWidget(self._alphaSlider)
        self.addToolBar(qt.Qt.RightToolBarArea, self._alphaSliderToolbar)

        # hide optional tools and actions
        self.setAlphaSliderVisible(False)
        self.setBackgroundActionVisible(False)
        self.setMedianFilterWidgetVisible(False)
        self.setProfileToolbarVisible(False)

        self._images = []
        """List of images, as 2D numpy arrays or 3D numpy arrays (RGB(A)).
        """

        self._labels = []
        """List of image labels.
        """

        self._bg_images = []
        """List of background images, as 2D numpy arrays or 3D numpy arrays
        (RGB(A)).
        These images are not active, their colormap cannot be changed and
        they cannot be the base image used for drawing a mask.
        """

        self._bg_labels = []

        self._deltaXY = (1.0, 1.0)             # TODO: allow different scale and origin for each image
        """Current image scale (Xscale, Yscale) (in axis units per image pixel).
        The scale is adjusted to keep constant width and height for the image
        when a crop operation is applied."""

        self._origin = (0., 0.)
        """Current image origin: coordinate (x, y) of sample located at
        (row, column) = (0, 0)"""

        # scales and origins for background images
        self._bg_deltaXY = []
        self._bg_origins = []

    def sizeHint(self):
        return qt.QSize(500, 400)

    def _createToolBar(self, title, parent):
        """Create a QToolBar with crop, rotate and flip operations

        :param str title: The title of the QMenu
        :param qt.QWidget parent: See :class:`QToolBar`
        """
        toolbar = qt.QToolBar(title, parent)

        # Order widgets with actions
        objects = self.group.actions()

        # Add standard push buttons to list
        index = objects.index(self.colormapAction)
        objects.insert(index + 1, self.keepDataAspectRatioButton)
        objects.insert(index + 2, self.yAxisInvertedButton)
        objects.insert(index + 4, self.saveToolbutton)
        objects.insert(index + 5, self.backgroundButton)
        for obj in objects:
            if isinstance(obj, qt.QAction):
                toolbar.addAction(obj)
            else:
                # keep reference to toolbutton's action for changing visibility
                if obj is self.keepDataAspectRatioButton:
                    self.keepDataAspectRatioAction = toolbar.addWidget(obj)
                elif obj is self.yAxisInvertedButton:
                    self.yAxisInvertedAction = toolbar.addWidget(obj)
                elif obj is self.saveToolbutton:
                    self.saveAction = toolbar.addWidget(obj)
                elif obj is self.backgroundButton:
                    self.bgAction = toolbar.addWidget(obj)
                else:
                    raise RuntimeError()

        return toolbar

    def _getMaskToolsDockWidget(self):
        """DockWidget with image mask panel (lazy-loaded)."""
        if self._maskToolsDockWidget is None:
            self._maskToolsDockWidget = MyMaskToolsDockWidget(
                plot=self.plot, name='Mask')
            self._maskToolsDockWidget.hide()
            self.addDockWidget(qt.Qt.RightDockWidgetArea,
                               self._maskToolsDockWidget)
            # self._maskToolsDockWidget.setFloating(True)
            self._maskToolsDockWidget.sigMaskChanged.connect(
                    self._emitMaskImageWidgetSignal)
            # At the very least silx 1.1.0 was not restoring the plot mode prior
            # to activate the mask. Force zoom state when closing the mask dock widget
            self._maskToolsDockWidget.visibilityChanged[bool].connect(
                    self._maskToolsDockWidgetVisibilityChanged)
        return self._maskToolsDockWidget

    def _maskToolsDockWidgetVisibilityChanged(self, visibility):
        if not visibility:
            self.plot.setInteractiveMode("zoom")

    def _setMedianKernelWidth(self, value):
        kernelSize = numpy.asarray(value)
        if len(kernelSize.shape) == 0:
            kernelSize = [kernelSize.item()] * 2
        self._medianParameters['row_width'] = kernelSize[0]
        self._medianParameters['column_width'] = kernelSize[1]
        self._medianParametersWidget.widthSpin.setValue(int(kernelSize[0]))
        self.showImage(self.slider.value())

    def _setMedianConditionalFlag(self, value):
        self._medianParameters['conditional'] = int(value)
        self._medianParametersWidget.conditionalSpin.setValue(int(value))
        self.showImage(self.slider.value())

    def _subtractBackground(self):
        """When background button is clicked, this causes showImage to
        display the data after subtracting the stack background image.

        This background image is unrelated to the background images set
        with :meth:`setBackgroundImages`, it is simply the first data image
        whose label ends with 'background'."""
        current = self.getCurrentIndex()
        self.showImage(current)

    def _updateMotors(self, ddict):
        if not ddict["event"] == "mouseMoved":
            return
        if not self.motorPositionsWidget.isVisible():
            return

        motorsValuesAtCursor = self._getPositionersFromXY(ddict["x"],
                                                          ddict["y"])
        if motorsValuesAtCursor is None:
            return

        self.motorPositionsWidget.table.updateTable(
                legList=[self.plot.getActiveImage().getLegend()],
                motList=[motorsValuesAtCursor])

        if self._motors_first_update:
            self._select_motors()
            self._motors_first_update = False

    def _select_motors(self):
        """This methods sets the motors in the comboboxes when the widget
        is first initialized."""
        for i, combobox in enumerate(self.motorPositionsWidget.table.header.boxes):
            # First item (index 0) in combobox is "", so first motor name is at index 1.
            # First combobox in header.boxes is at index 1 (boxes[0] is None).
            if i == 0:
                continue
            if i < combobox.count():
                combobox.setCurrentIndex(i)

    def _getPositionersFromXY(self, x, y):
        """Return positioner values for a stack pixel identified
        by it's (x, y) coordinates.
        """
        activeImage = self.plot.getActiveImage()
        if activeImage is None:
            return None
        info = activeImage.getInfo()
        if not info or not isinstance(info, dict):
            return None
        positioners = info.get("positioners", {})

        nRows, nCols = activeImage.getData().shape
        xScale, yScale = activeImage.getScale()
        xOrigin, yOrigin = activeImage.getOrigin()
        r, c = convertToRowAndColumn(
                x, y,
                shape=(nRows, nCols),
                xScale=(xOrigin, xScale),
                yScale=(yOrigin, yScale),
                safe=True)

        idx1d = r * nCols + c
        positionersAtIdx = {}

        for motorName, motorValues in positioners.items():
            if numpy.isscalar(motorValues):
                positionersAtIdx[motorName] = motorValues
            elif len(motorValues.shape) == 1:
                positionersAtIdx[motorName] = motorValues[idx1d]
            else:
                positionersAtIdx[motorName] = motorValues.reshape((-1,))[idx1d]

        return positionersAtIdx

    # widgets visibility toggling
    def setBackgroundActionVisible(self, visible):
        """Set visibility of the background toolbar button.

        :param visible: True to show tool button, False to hide it.
        """
        self.bgAction.setVisible(visible)

    def setButtonBoxWidgetVisible(self, visible):
        """Set visibility of the image actions widget

        :param visible: True to show the buttons, False to hide them.
        """
        if visible:
            self._buttonBox.show()
        else:
            self._buttonBox.hide()

    def setProfileToolbarVisible(self, visible):
        """Set visibility of the profile toolbar

        :param visible: True to show toolbar, False to hide it.
        """
        self._profile.setVisible(visible)

    def setMedianFilterWidgetVisible(self, visible):
        """Set visibility of the median filter parametrs widget.

        :param visible: True to show widget, False to hide it.
        """
        self._medianParametersWidget.setVisible(visible)

    def setMotorPositionsVisible(self, flag):
        """Show or hide motor positions widget"""
        self.motorPositionsWidget.setVisible(flag)

    def setAlphaSliderVisible(self, visible):
        """Set visibility of the transparency slider widget in the right
        toolbar area.

        :param visible: True to show widget, False to hide it.
        """
        self._alphaSliderToolbar.setVisible(visible)

    def setImagesAlpha(self, alpha):
        """Set the opacity of the images layer.

        Full opacity means that the background images layer will not
        be visible.

        :param float alpha: Opacity of images layer, in [0., 1.]
        """
        self._alphaSlider.setValue(round(alpha * 255))

    def getMaskAction(self):
        """QAction toggling image mask dock widget

        :rtype: QAction
        """
        return self._getMaskToolsDockWidget().toggleViewAction()

    def _emitMaskImageWidgetSignal(self):
        mask = self.getSelectionMask()
        if not mask.size:
            # workaround to ignore the empty mask emitted when the mask widget
            # is initialized
            return
        self.sigMaskImageWidget.emit(
            {"event": "selectionMaskChanged",
             "current": self.getSelectionMask(),
             "id": id(self)})

    def setSelectionMask(self, mask, copy=True):
        """Set the mask to a new array.

        :param numpy.ndarray mask: The array to use for the mask.
                    Mask type: array of uint8 of dimension 2,
                    Array of other types are converted.
        :param bool copy: True (the default) to copy the array,
                          False to use it as is if possible.
        :return: None if failed, shape of mask as 2-tuple if successful.
                 The mask can be cropped or padded to fit active image,
                 the returned shape is that of the active image.
        """
        # disconnect temporarily to avoid infinite loop
        self._getMaskToolsDockWidget().sigMaskChanged.disconnect(
                    self._emitMaskImageWidgetSignal)
        if mask is None and silx.version_info <= (0, 7, 0):
            self._getMaskToolsDockWidget().resetSelectionMask()
            ret = None
        else:
            # from silx 0.8 onwards, setSelectionMask(None) is supported
            ret = self._getMaskToolsDockWidget().setSelectionMask(mask,
                                                                  copy=copy)
        self._getMaskToolsDockWidget().sigMaskChanged.connect(
                    self._emitMaskImageWidgetSignal)
        return ret

    def getSelectionMask(self, copy=True):
        """Get the current mask as a 2D array.

        :param bool copy: True (default) to get a copy of the mask.
                          If False, the returned array MUST not be modified.
        :return: The array of the mask with dimension of the 'active' image.
                 If there is no active image, None is returned.
        :rtype: 2D numpy.ndarray of uint8
        """
        return self._getMaskToolsDockWidget().getSelectionMask(copy=copy)

    @staticmethod
    def _RgbaToGrayscale(image):
        """Convert RGBA image to 2D array of grayscale values
        (Luma coding)

        :param image: RGBA image, as a numpy array of shapes
             (nrows, ncols, 3/4)
        :return: Image as a 2D array
        """
        if len(image.shape) == 2:
            return image
        assert len(image.shape) == 3

        imageData = image[:, :, 0] * 0.299 +\
                    image[:, :, 1] * 0.587 +\
                    image[:, :, 2] * 0.114
        return imageData

    def getImageData(self):
        """Return current image data to be sent to RGB correlator

        :return: Image as a 2D array
        """
        index = self.slider.value()
        image = self._images[index]
        return self._RgbaToGrayscale(image)

    def getFirstBgImageData(self):
        """Return first bg image data to be sent to RGB correlator
        :return: Image as a 2D array
        """
        image = self._bg_images[0]
        return self._RgbaToGrayscale(image)

    def getBgImagesDict(self):
        """Return a dict containing the data for all background images."""
        bgimages = {}
        for i, label in enumerate(self._bg_labels):
            data = self._bg_images[i]
            origin = self._bg_origins[i]
            delta_w, delta_h = self._bg_deltaXY[i]
            w, h = delta_w * data.shape[1], delta_h * data.shape[0]
            bgimages[label] = {"data": data,
                               "origin": origin,
                               "width": w,
                               "height": h}
        return bgimages

    def _addImageClicked(self):
        imageData = self.getImageData()
        ddict = {
            'event': "addImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    def _replaceImageClicked(self):
        imageData = self.getImageData()
        ddict = {
            'event': "replaceImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    def _removeImageClicked(self):
        imageData = self.getImageData()
        ddict = {
            'event': "removeImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    def showImage(self, index=0):
        """Show data image corresponding to index. Update slider to index.
        """
        if not self._images:
            return
        assert index < len(self._images)

        bg_index = None
        if self.backgroundButton.isChecked():
            for i, imageName in enumerate(self._labels):
                if imageName.lower().endswith('background'):
                    bg_index = i
                    break

        mf_text = ""
        a = self._medianParameters['row_width']
        b = self._medianParameters['column_width']
        if max(a, b) > 1:
            mf_text = "MF(%d,%d) " % (a, b)

        imdata = self._getMedianData(self._images[index])
        if bg_index is None:
            self.plot.setGraphTitle(mf_text + self._labels[index])
        else:
            self.plot.setGraphTitle(mf_text + self._labels[index] + " Net")
            imdata -= self._images[bg_index]

        if len(self._infos) > 1:
            info = self._infos[index]
        else:
            info = self._infos[0]

        self.plot.addImage(imdata,
                           legend="current",
                           origin=self._origin,
                           scale=self._deltaXY,
                           replace=False,
                           z=0,
                           info=info)
        self.plot.setActiveImage("current")
        self.slider.setValue(index)

    def _getMedianData(self, data):
        data = copy.copy(data)
        if max(self._medianParameters['row_width'],
               self._medianParameters['column_width']) > 1:
            data = medfilt2d(data,
                             [self._medianParameters['row_width'],
                              self._medianParameters['column_width']],
                             conditional=self._medianParameters['conditional'])
        return data

    def setImages(self, images, labels=None,
                  origin=None, height=None, width=None,
                  infos=None):
        """Set the list of data images.

        All images share the same origin, width and height.

        :param images: List of 2D or 3D (for RGBA data) numpy arrays
            of image data. All images must have the same shape.
        :type images: List of ndarrays
        :param labels: list of image names
        :param origin: Image origin: coordinate (x, y) of sample located at
            (row, column) = (0, 0). If None, use (0., 0.)
        :param height: Image height in Y axis units. If None, use the
            image height in number of pixels.
        :param width: Image width in X axis units. If None, use the
            image width in number of pixels.
        :param infos: List of info dicts, one per image, or None.
        """
        self._images = images
        if labels is None:
            labels = ["Image %d" % (i + 1) for i in range(len(images))]
        if infos is None:
            infos = [{} for _img in images]

        self._labels = labels
        self._infos = infos

        height_pixels, width_pixels = images[0].shape[0:2]
        height = height or height_pixels
        width = width or width_pixels

        self._deltaXY = (float(width) / width_pixels,
                         float(height) / height_pixels)

        self._origin = origin or (0., 0.)

        current = self.slider.value()
        self.slider.setMaximum(len(self._images) - 1)
        if current < len(self._images):
            self.showImage(current)
        else:
            self.showImage(0)

        # _maskParamsCache = width, height, self._origin, self._deltaXY
        # if _maskParamsCache != self._maskParamsCache:
        #     self._maskParamsCache = _maskParamsCache
        #     self.resetMask(width, height, self._origin, self._deltaXY)

    def setImageData(self, data, clearmask=False, xScale=None, yScale=None):
        """ Compatibility method with PyMca when handling single images
        """
        if xScale is None:
            xScale = [0.0, 1.0]
        if yScale is None:
            yScale = [0.0, 1.0]
        self._origin = (xScale[0], yScale[0])
        self._deltaXY = (xScale[1], yScale[1])
        info = None
        self.setImages([data],
                   labels=[""],
                   origin=self._origin,
                   width=xScale[1] * data.shape[1],
                   height=yScale[1]* data.shape[0])

    def plotImage(self, update=True):
        """ Compatibility method with PyMca when handling single images
        """
        pass

    def showInfo(self):
        if self.infoWidget.isHidden():
            self.infoWidget.show()

    def setInfoText(self, text):
        """ Compatibility method with PyMca when handling single images
        """
        self.infoWidget.setText(text)

    def _updateBgScales(self, heights, widths):
        """Recalculate BG scales
        (e.g after a crop operation on :attr:`_bg_images`)"""
        self._bg_deltaXY = []
        for w, h, img in zip(widths,
                             heights,
                             self._bg_images):
            self._bg_deltaXY.append(
                (float(w) / img.shape[1], float(h) / img.shape[0])
            )

    def setBackgroundImages(self, images, labels=None,
                            origins=None, heights=None, widths=None):
        """Set the list of background images.

        Each image should be a tile and have an origin (x, y) tuple,
        a height and a width defined, so that all images can be plotted
        on the same background layer.

        :param images: List of 2D or 3D (for RGBA data) numpy arrays
            of image data. All images must have the same shape.
        :type images: List of ndarrays
        :param labels: list of image names
        :param origins: Images origins: list of coordinate tuples (x, y)
            of sample located at (row, column) = (0, 0).
            If None, use (0., 0.) for all images.
        :param heights: Image height in Y axis units. If None, use the
            image height in number of pixels.
        :param widths: Image width in X axis units. If None, use the
            image width in number of pixels.
        """
        self._bg_images = images
        if labels is None:
            labels = ["Background image %d" % (i + 1) for i in range(len(images))]

        # delete existing images
        for label in self._bg_labels:
            self.plot.removeImage(label)

        self._bg_labels = labels

        if heights is None:
            heights = [image.shape[0] for image in images]
        else:
            assert len(heights) == len(images)
        if widths is None:
            widths = [image.shape[1] for image in images]
        else:
            assert len(widths) == len(images)

        if origins is None:
            origins = [(0, 0) for _img in images]
        else:
            assert len(origins) == len(images)

        self._bg_origins = origins
        self._updateBgScales(heights, widths)

        for bg_deltaXY, bg_orig, label, img in zip(self._bg_deltaXY,
                                                  self._bg_origins,
                                                  labels,
                                                  images):
            # FIXME: we use z=-1 because the mask is always on z=1,
            # so the data must be on z=0. To be fixed after the silx mask
            # is improved
            self.plot.addImage(img,
                               origin=bg_orig,
                               scale=bg_deltaXY,
                               legend=label,
                               replace=False,
                               z=-1)  # TODO: z=0

    def getCurrentIndex(self):
        """
        :return: Index of slider widget used for image selection.
        """
        return self.slider.value()

    def getCurrentColormap(self):
        """Return colormap dict associated with the current image.
        If the current image is a RGBA Image, return None.

        See doc of silx.gui.plot.Plot for an explanation about the colormap
        dictionary.
        """
        image = self.plot.getImage(legend="current")
        if not hasattr(image, "getColormap"):    # isinstance(image, silx.gui.plot.items.ImageRgba):
            return None
        return self.plot.getImage(legend="current").getColormap()

    def showAndRaise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = qt.QApplication([])
    w = SilxMaskImageWidget()
    w.setProfileToolbarVisible(True)
    w.show()
    w.setImages([numpy.array([[0, 1, 2], [2, 1, -1]])])
    app.exec()
