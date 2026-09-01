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
"""The :class:`Hdf5NodeView` widget in this module aims to replace
:class:`HDF5DatasetTable` in :class:`QNexusWidget` for visualization of HDF5
datasets and groups, with support of NXdata groups as plot.

It uses the silx :class:`DataViewerFrame` widget with views modified
to handle plugins."""
__author__ = "P. Knobel - ESRF Data Analysis"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"


import os

import PyMca5
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.misc import CloseEventNotifyingWidget

from PyMca5.PyMcaGui.PluginsToolButton import PluginsToolButton

import silx
from silx.gui.data.DataViewerFrame import DataViewerFrame
from silx.gui.data.DataViewer import DataViewer
from silx.gui.data import DataViews
from silx.gui import icons



PLUGINS_DIR = []
if os.path.exists(os.path.join(os.path.dirname(PyMca5.__file__), "PyMcaPlugins")):
    from PyMca5 import PyMcaPlugins
    PLUGINS_DIR.append(os.path.dirname(PyMcaPlugins.__file__))
else:
    directory = os.path.dirname(__file__)
    while True:
        if os.path.exists(os.path.join(directory, "PyMcaPlugins")):
            PLUGINS_DIR.append(os.path.join(directory, "PyMcaPlugins"))
            break
        directory = os.path.dirname(directory)
        if len(directory) < 5:
            break

userPluginsDirectory = PyMca5.getDefaultUserPluginsDirectory()
if userPluginsDirectory is not None:
    PLUGINS_DIR.append(userPluginsDirectory)


class Plot1DViewWithPlugins(DataViews._Plot1dView):
    """Add a :class:`PluginsToolButton`
    to the widget silx uses for 1D plots.
    """
    def createWidget(self, parent):
        widget = super().createWidget(parent)
        widget._plotType = "SCAN"    # needed by legacy plugins

        pymcaToolbar = qt.QToolBar(widget)
        widget.addToolBar(pymcaToolbar)
        pluginsToolButton = PluginsToolButton(plot=widget, parent=widget)
        if PLUGINS_DIR:
            pluginsToolButton.getPlugins(
                    method="getPlugin1DInstance",
                    directoryList=PLUGINS_DIR)
        pymcaToolbar.addWidget(pluginsToolButton)
        return widget

class Plot2DViewWithPlugins(DataViews._Plot2dView):
    def createWidget(self, parent):
        widget = super().createWidget(parent)
        widget.setKeepDataAspectRatio(False)
        pymcaToolbar = qt.QToolBar(widget)
        widget.addToolBar(pymcaToolbar)
        pluginsToolButton = PluginsToolButton(plot=widget, parent=widget,
                                              method="getPlugin2DInstance")

        if PLUGINS_DIR:
            pluginsToolButton.getPlugins(
                    method="getPlugin2DInstance",
                    directoryList=PLUGINS_DIR)
        pymcaToolbar.addWidget(pluginsToolButton)
        widget.getIntensityHistogramAction().setVisible(True)
        return widget

class NXdataCurveViewWithPlugins(DataViews._NXdataCurveView):
    """Add a :class:`PluginsToolButton`
    to the widget silx uses for NXdata curves.
    """
    def createWidget(self, parent):
        # ArrayCurvePlot before 3.1, NxCurvePlot after
        widget = super().createWidget(parent)
        plot = widget._plot
        # patch the Plot1D to make it compatible with plugins
        plot._plotType = "SCAN"

        pymcaToolbar = qt.QToolBar(widget)
        plot.addToolBar(pymcaToolbar)
        pluginsToolButton = PluginsToolButton(plot=plot, parent=widget)
        if PLUGINS_DIR:
            pluginsToolButton.getPlugins(
                    method="getPlugin1DInstance",
                    directoryList=PLUGINS_DIR)
        pymcaToolbar.addWidget(pluginsToolButton)
        return widget


class NXdataImageViewWithPlugins(DataViews._NXdataImageView):
    """Add a :class:`PluginsToolButton`
    to the widget silx uses for NXdata images.
    """
    def createWidget(self, parent):
        # silx already sets the default colormap and the colormap dialog
        widget = super().createWidget(parent)
        plot = widget.getPlot()

        pymcaToolbar = qt.QToolBar(widget)
        plot.addToolBar(pymcaToolbar)
        pluginsToolButton = PluginsToolButton(plot=plot, parent=widget,
                                              method="getPlugin2DInstance")
        if PLUGINS_DIR:
            pluginsToolButton.getPlugins(
                    method="getPlugin2DInstance",
                    directoryList=PLUGINS_DIR)
        pymcaToolbar.addWidget(pluginsToolButton)
        return widget


class Hdf5NodeView(CloseEventNotifyingWidget.CloseEventNotifyingWidget):
    """QWidget displaying data as raw values in a table widget, or as a
    curve, image or stack in a plot widget. It can also display information
    related to HDF5 groups (attributes, compression, ...) and interpret
    a NXdata group to plot its data.

    The plot features depend on *silx*'s availability.
    """
    def __init__(self, parent=None):
        CloseEventNotifyingWidget.CloseEventNotifyingWidget.__init__(self,
                                                                     parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self.viewWidget = DataViewerFrame(self)
        self.viewWidget.replaceView(DataViews.PLOT1D_MODE,
                                    Plot1DViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.PLOT2D_MODE,
                                    Plot2DViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.NXDATA_CURVE_MODE,
                                    NXdataCurveViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.NXDATA_IMAGE_MODE,
                                    NXdataImageViewWithPlugins(self))

        self.mainLayout.addWidget(self.viewWidget)

    def setData(self, dataset):
        self.viewWidget.setData(dataset)


class Hdf5NodeViewer(CloseEventNotifyingWidget.CloseEventNotifyingWidget):
    """QWidget displaying data as raw values in a table widget, or as a
    curve, image or stack in a plot widget. It can also display information
    related to HDF5 groups (attributes, compression, ...) and interpret
    a NXdata group to plot its data.

    The plot features depend on *silx*'s availability.
    """
    def __init__(self, parent=None):
        CloseEventNotifyingWidget.CloseEventNotifyingWidget.__init__(self,
                                                                     parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self.viewWidget = DataViewer(self)
        self.viewWidget.replaceView(DataViews.PLOT1D_MODE,
                                    Plot1DViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.PLOT2D_MODE,
                                    Plot2DViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.NXDATA_CURVE_MODE,
                                    NXdataCurveViewWithPlugins(self))
        self.viewWidget.replaceView(DataViews.NXDATA_IMAGE_MODE,
                                    NXdataImageViewWithPlugins(self))

        self.mainLayout.addWidget(self.viewWidget)

    def setData(self, dataset):
        self.viewWidget.setData(dataset)

