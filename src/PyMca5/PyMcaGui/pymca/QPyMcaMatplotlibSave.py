#!/usr/bin/env python
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import numpy
import traceback
from io import StringIO
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaCore import PyMcaMatplotlibSave
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
from PyMca5 import PyMcaDirs

from matplotlib import colormaps as mpl_colormaps
from matplotlib.font_manager import FontProperties
from PyMca5.PyMcaGraph.backends.MatplotlibBackend import FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.ticker import MaxNLocator, AutoLocator

_logger = logging.getLogger(__name__)


class TopWidget(qt.QWidget):
    def __init__(self, parent = None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.labelList = ['Title', 'X Label', 'Y Label']
        self.keyList   = ['title', 'xlabel', 'ylabel']
        self.lineEditList = []
        for i in range(len(self.labelList)):
            label = qt.QLabel(self)
            label.setText(self.labelList[i])
            lineEdit = qt.QLineEdit(self)
            self.mainLayout.addWidget(label, i, 0)
            self.mainLayout.addWidget(lineEdit, i, 1)
            self.lineEditList.append(lineEdit)

    def getParameters(self):
        ddict = {}
        i = 0
        for label in self.keyList:
            ddict[label] = qt.safe_str(self.lineEditList[i].text())
            i = i + 1
        return ddict

    def setParameters(self, ddict):
        for label in ddict.keys():
            if label.lower() in self.keyList:
                i = self.keyList.index(label)
                self.lineEditList[i].setText(ddict[label])
        return

class ButtonsWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)

        self.updateButton = qt.QPushButton(self)
        self.updateButton.setText("Update")

        self.printButton = qt.QPushButton(self)
        self.printButton.setText("Print")

        self.saveButton = qt.QPushButton(self)
        self.saveButton.setText("Save")

        self.mainLayout.addWidget(self.updateButton)
        self.mainLayout.addWidget(self.printButton)
        self.mainLayout.addWidget(self.saveButton)

class SaveImageSetup(qt.QWidget):
    def __init__(self, parent=None, image=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setColumnStretch(0, 1)
        self.mainLayout.setColumnStretch(1, 0)
        self.setWindowTitle("PyMca - Matplotlib save image")
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.lastOutputDir = None
        self.printPreview = PyMcaPrintPreview.PyMcaPrintPreview(modal = 0)

        #top
        self.top = TopWidget(self)
        self.mainLayout.addWidget(self.top, 0, 0)

        #image
        self.imageWidget = QPyMcaMatplotlibImage(self, image)
        self.mainLayout.addWidget(self.imageWidget, 1, 0)

        #right
        self.right = RightWidget(self)
        self.mainLayout.addWidget(self.right, 1, 1)

        #buttons
        self._buttonContainer = ButtonsWidget(self)
        self.mainLayout.addWidget(self._buttonContainer, 0, 1)

        self._buttonContainer.updateButton.clicked.connect(\
                self.updateClicked)

        self._buttonContainer.printButton.clicked.connect(self.printClicked)
        self._buttonContainer.saveButton.clicked.connect(self.saveClicked)


    def sizeHint(self):
        return qt.QSize(3 * qt.QWidget.sizeHint(self).width(),
                        3 * qt.QWidget.sizeHint(self).height())

    def setImageData(self, image=None):
        self.imageWidget.imageData = image
        self.updateClicked()

    def setPixmapImage(self, image=None, bgr=False):
        #this is not to loose time plotting twice
        self.imageWidget.setPixmapImage(None, bgr)
        if image is None:
            self.right.setPixmapMode(False)
        else:
            self.right.setPixmapMode(True)
        #update configuration withoutplotting because of having
        #set the current pixmap to None
        self.updateClicked()
        #and plot
        self.imageWidget.setPixmapImage(image, bgr)

    def getParameters(self):
        ddict = self.imageWidget.getParameters()
        ddict.update(self.top.getParameters())
        ddict.update(self.right.getParameters())
        return ddict

    def setParameters(self, ddict):
        self.top.setParameters(ddict)
        self.imageWidget.setParameters(ddict)
        self.right.setParameters(ddict)

    def updateClicked(self):
        try:
            ddict = self.getParameters()
            self.imageWidget.setParameters(ddict)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error updating image:")
            msg.setInformativeText("%s" % sys.exc_info()[1])
            msg.setDetailedText(traceback.format_exc())
            msg.setWindowTitle('Matplotlib Save Image')
            msg.exec()

    def printClicked(self):
        try:
            pixmap = qt.QPixmap.grabWidget(self.imageWidget)
            self.printPreview.addPixmap(pixmap)
            if self.printPreview.isHidden():
                self.printPreview.show()
            self.printPreview.raise_()
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error printing image: %s" % sys.exc_info()[1])
            msg.setWindowTitle('Matplotlib Save Image')
            msg.exec()


    def saveClicked(self):
        if self.lastOutputDir is None:
            self.lastOutputDir = PyMcaDirs.outputDir

        format_list = []
        format_list.append('Graphics PNG *.png')
        format_list.append('Graphics EPS *.eps')
        format_list.append('Graphics SVG *.svg')
        outputFile, filterused = PyMcaFileDialogs.getFileList(self, filetypelist=format_list,
                                                              message="Output File Selection",
                                                              currentdir=self.lastOutputDir,
                                                              mode="SAVE", getfilter=True,
                                                              single=False, currentfilter=None, native=None)
        if not len(outputFile):
            return

        filterused = filterused.split()
        filedescription = filterused[0]
        filetype  = filterused[1]
        extension = filterused[2]

        outputFile = outputFile[0]
        try:
            outputDir  = os.path.dirname(outputFile)
            self.lastOutputDir = outputDir
            PyMcaDirs.outputDir = outputDir
        except Exception:
            outputDir  = "."
        try:
            outputFile = os.path.basename(outputFile)
        except Exception:
            outputFile  = outputFile

        #always overwrite for the time being
        if len(outputFile) < len(extension[1:]):
            outputFile += extension[1:]
        elif outputFile[-4:] != extension[1:]:
            outputFile += extension[1:]

        finalFile = os.path.join(outputDir, outputFile)
        if os.path.exists(finalFile):
            try:
                os.remove(finalFile)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Cannot overwrite file: %s" % sys.exc_info()[1])
                msg.setWindowTitle('Matplotlib Save Image')
                msg.exec()
                return
        try:
            self.imageWidget.print_figure(finalFile,
                                          edgecolor='w',
                                          facecolor='w',
                                          format=finalFile[-3:],
                                          dpi=self.imageWidget.config['outputdpi'])
        except Exception:
            _logger.warning("trying to save using obsolete method")
            config = self.imageWidget.getParameters()
            try:
                s=PyMcaMatplotlibSave.PyMcaMatplotlibSaveImage(self.imageWidget.imageData)
                if self.imageWidget.pixmapImage is not None:
                    s.setPixmapImage(self.imageWidget.pixmapImage)
                s.setParameters(config)
                s.saveImage(finalFile)
            except Exception:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error saving file: %s" % sys.exc_info()[1])
                msg.setWindowTitle('Matplotlib Save Image')
                msg.exec()

class SimpleComboBox(qt.QComboBox):
    def __init__(self, parent=None, options=['1', '2', '3']):
        qt.QComboBox.__init__(self,parent)
        self.setOptions(options)
        self.setDuplicatesEnabled(False)
        self.setEditable(False)

    def setOptions(self,options=['1','2','3']):
        self.clear()
        for item in options:
            self.addItem(item)

    def setCurrentText(self, text):
        for i in range(self.count()):
            if qt.safe_str(self.itemText(i)) == text:
                self.setCurrentIndex(i)
                break

class RightWidget(qt.QWidget):
    def __init__(self, parent = None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.gridWidget = qt.QWidget(self)
        self.gridLayout = qt.QGridLayout(self.gridWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(2)
        self.labelList = ['X Axis',
                        'Y Axis',
                        'N X Labels',
                        'N Y Labels',
                        'Origin',
                        'Interpolation',
                        'Colormap',
                        'Lin/Log Colormap',
                        'Colorbar',
                        'Contour',
                        'Contour Labels',
                        'Contour Label Format',
                        'Contour Levels',
                        'Contour Line Width',
                        'Image Background',
                        'X Pixel Size',
                        'Y Pixel Size',
                        'X Origin',
                        'Y Origin',
                        'Zoom X Min',
                        'Zoom X Max',
                        'Zoom Y Min',
                        'Zoom Y Max',
                        'Value Min',
                        'Value Max',
                        'Output dpi']
        self.keyList = []
        for label in self.labelList:
            self.keyList.append(label.lower().replace(' ','').replace('/',""))
        self.comboBoxList = []
        for i in range(len(self.labelList)):
            label = qt.QLabel(self)
            label.setText(self.labelList[i])
            if self.labelList[i] in ['X Axis', 'Y Axis']:
                options = ['Off', 'On']
            if self.labelList[i] in ['N X Labels', 'N Y Labels']:
                options = ['Auto', '1', '2', '3', '4', '5', '6', '7', '8', '9']
            elif self.labelList[i] in ['Colormap']:
                options = ['Temperature','Grey', 'Yerg',\
                           'Red', 'Green', 'Blue',\
                           'Rainbow', 'Jet','Hot', 'Cool', 'Copper']
                for candidate in ['Spectral', 'Paired', 'Paired_r',
                                  'PuBu', 'PuBu_r', 'RdBu', 'RdBu_r',
                                  'gist_earth', 'gist_earth_r',
                                  'Blues', 'Blues_r',
                                  'YlGnBu', 'YlGnBu_r']:
                    if candidate in mpl_colormaps:
                        options.append(candidate)
            elif self.labelList[i] in ['Lin/Log Colormap']:
                options = ['Linear','Logarithmic']
            elif self.labelList[i] in ['Colorbar']:
                options = ['None', 'Vertical', 'Horizontal']
            elif self.labelList[i] in ['Origin']:
                options = ['Lower', 'Upper']
            elif self.labelList[i] in ['Interpolation']:
                options = ['Nearest', 'Bilinear']
            elif self.labelList[i] in ['Contour']:
                options = ['Off', 'Line']
            elif self.labelList[i] in ['Contour Labels']:
                options = ['On', 'Off']
            elif self.labelList[i] in ['Contour Label Format']:
                options = ['%.3f', '%.2f', '%.1f', '%.0f', '%.1e', '%.2e', '%.3e']
            elif self.labelList[i] in ['Contour Levels']:
                options = ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1"]
            elif self.labelList[i] in ['Image Background']:
                options = ['Black', 'White', 'Grey']

            if self.labelList[i] in ['Contour Levels']:
                line = qt.QSpinBox(self)
                line.setMinimum(1)
                line.setMaximum(1000)
                line.setValue(10)
            elif self.labelList[i] in ['Contour Line Width']:
                line = qt.QSpinBox(self)
                line.setMinimum(1)
                line.setMaximum(100)
                line.setValue(10)
            elif i <= self.labelList.index('Image Background'):
                line = SimpleComboBox(self, options)
            else:
                line = MyLineEdit(self)
                validator = qt.CLocaleQDoubleValidator(line)
                line.setValidator(validator)
                if 'Zoom' in self.labelList[i]:
                    tip  = "This zoom is in physical units.\n"
                    tip += "This means pixel size corrected.\n"
                    tip += "To disable zoom, just set both\n"
                    tip += "limits to the same value."
                    line.setToolTip(tip)
                    line.setText('0.0')
                elif 'Origin' in self.labelList[i]:
                    tip  = "First pixel coordinates in physical units.\n"
                    tip += "This means pixel size corrected.\n"
                    line.setToolTip(tip)
                    line.setText('0.0')
                elif 'Value' in self.labelList[i]:
                    tip  = "Clipping values of the data.\n"
                    tip += "To disable clipping, just set both\n"
                    tip += "limits to the same value."
                    line.setToolTip(tip)
                    line.setText('0.0')
                elif 'Output dpi' in self.labelList[i]:
                    tip  = "=Output file resolution."
                    line.setToolTip(tip)
                    line.setText("%d" % 100)
                else:
                    line.setText('1.0')
            self.gridLayout.addWidget(label, i, 0)
            self.gridLayout.addWidget(line, i, 1)
            self.comboBoxList.append(line)

        self.mainLayout.addWidget(self.gridWidget)
        self.mainLayout.addWidget(qt.VerticalSpacer(self))
        self.setPixmapMode(False)

    def setPixmapMode(self, flag):
        if flag:
            disable = ['Colormap', 'Lin/Log Colormap', 'Contour', 'Contour Labels',
                       'Contour Label Format',
                       'Contour Levels', 'Colorbar', 'Value Min','Value Max']
        else:
            disable = ['Image Background']

        for label in self.labelList:
            index = self.labelList.index(label)
            if label in disable:
                self.comboBoxList[index].setEnabled(False)
            else:
                self.comboBoxList[index].setEnabled(True)

    def getParameters(self):
        ddict = {}
        i = 0
        for label in self.keyList:
            if i == self.labelList.index('Contour Levels'):
                ddict[label] = self.comboBoxList[i].value()
            elif i == self.labelList.index('Contour Line Width'):
                ddict[label] = self.comboBoxList[i].value()
            elif i > self.labelList.index('Image Background'):
                text = qt.safe_str(self.comboBoxList[i].text())
                if len(text):
                    if label in ['Output dpi', "N X Labels", "N Y Labels"]:
                        if ddict[label] in ['Auto', 'auto', '0', 0]:
                            ddict['label'] = 0
                        else:
                            ddict[label] = int(text)
                    else:
                        ddict[label] = float(text)
                else:
                    ddict[label] = None
            else:
                ddict[label] = qt.safe_str(self.comboBoxList[i].currentText()).lower()
            if (ddict[label] == 'none') or (ddict[label] == 'default'):
                ddict[label] = None
            i = i + 1
        return ddict

    def setParameters(self, ddict):
        for label in ddict.keys():
            if label.lower() in self.keyList:
                i = self.keyList.index(label)
                if i == self.labelList.index('Contour Levels'):
                    self.comboBoxList[i].setValue(int(ddict[label]))
                elif i == self.labelList.index('Contour Line Width'):
                    self.comboBoxList[i].setValue(int(ddict[label]))
                elif i > self.labelList.index('Image Background'):
                    if ddict[label] is not None:
                        if label in ['Output dpi']:
                            self.comboBoxList[i].setText("%d" % int(ddict[label]))
                        elif label in ['N X Labels', 'N Y Labels']:
                            if ddict[label] in ['Auto', 'auto', '0', 0]:
                                self.comboBoxList[i].setText("Auto")
                            else:
                                self.comboBoxList[i].setText("%d" %\
                                                             int(ddict[label]))
                        else:
                            self.comboBoxList[i].setText("%f" % ddict[label])
                else:
                    txt = ddict[label]
                    if ddict[label] is not None:
                        try:
                            txt = ddict[label][0].upper() +\
                                  ddict[label][1:].lower()
                        except Exception:
                            pass
                    self.comboBoxList[i].setCurrentText(txt)
        return

class MyLineEdit(qt.QLineEdit):
    def sizeHint(self):
        return qt.QSize(int(0.6 * qt.QLineEdit.sizeHint(self).width()),
                        qt.QLineEdit.sizeHint(self).height())


class QPyMcaMatplotlibImage(FigureCanvas):
    def __init__(self, parent, imageData=None,
                     dpi=100,
                     size=(5, 5),
                     xaxis='off',
                     yaxis='off',
                     xlabel='',
                     ylabel='',
                     nxlabels=0,
                     nylabels=0,
                     colorbar=None,
                     title='',
                     interpolation='nearest',
                     colormap=None,
                     linlogcolormap='linear',
                     origin='lower',
                     contour='off',
                     contourlabels='on',
                     contourlabelformat='%.3f',
                     contourlevels=2,
                     contourlinewidth=10,
                     extent=None,
                     xpixelsize=1.0,
                     ypixelsize=1.0,
                     xorigin=0.0,
                     yorigin=0.0,
                     xlimits=None,
                     ylimits=None,
                     vlimits=None):
        self.figure = Figure(figsize=size, dpi=dpi) #in inches

        #How to set this color equal to the other widgets color?
        #self.figure.set_facecolor('1.0')
        #self.figure.set_edgecolor('1.0')

        FigureCanvas.__init__(self, self.figure)
        FigureCanvas.setSizePolicy(self,
                                   qt.QSizePolicy.Expanding,
                                   qt.QSizePolicy.Expanding)

        self.imageData = imageData
        self.pixmapImage = None
        self.config={'xaxis':xaxis,
                     'yaxis':yaxis,
                     'title':title,
                     'xlabel':xlabel,
                     'ylabel':ylabel,
                     'nxlabels':nxlabels,
                     'nylabels':nylabels,
                     'colorbar':colorbar,
                     'colormap':colormap,
                     'linlogcolormap':linlogcolormap,
                     'interpolation':interpolation,
                     'origin':origin,
                     'contour':contour,
                     'contourlabels':contourlabels,
                     'contourlabelformat':contourlabelformat,
                     'contourlevels':contourlevels,
                     'contourlinewidth':contourlinewidth,
                     'extent':extent,
                     'imagebackground':'black',
                     'xorigin':xorigin,
                     'yorigin':yorigin,
                     'xpixelsize':xpixelsize,
                     'ypixelsize':ypixelsize,
                     'zoomxmin':None,
                     'zoomxmax':None,
                     'zoomymin':None,
                     'zoomymax':None,
                     'valuemin':None,
                     'valuemax':None,
                     'xlimits':xlimits,
                     'ylimits':ylimits,
                     'vlimits':vlimits,
                     'outputdpi':dpi}

        #generate own colormaps
        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 1.0, 1.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}
        self.__redCmap = LinearSegmentedColormap('red',cdict,256)

        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 1.0, 1.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}
        self.__greenCmap = LinearSegmentedColormap('green',cdict,256)

        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 1.0, 1.0))}
        self.__blueCmap = LinearSegmentedColormap('blue',cdict,256)

        # Temperature as defined in spslut
        cdict = {'red': ((0.0, 0.0, 0.0),
                         (0.5, 0.0, 0.0),
                         (0.75, 1.0, 1.0),
                         (1.0, 1.0, 1.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (0.25, 1.0, 1.0),
                           (0.75, 1.0, 1.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 1.0, 1.0),
                          (0.25, 1.0, 1.0),
                          (0.5, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}
        #but limited to 256 colors for a faster display (of the colorbar)
        self.__temperatureCmap = LinearSegmentedColormap('temperature',
                                                         cdict, 256)

        #reversed gray
        cdict = {'red':     ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0)),
                 'green':   ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0)),
                 'blue':    ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0))}

        self.__reversedGrayCmap = LinearSegmentedColormap('yerg', cdict, 256)

        self.updateFigure()

    def updateFigure(self):
        self.figure.clear()
        if (self.imageData is None) and \
           (self.pixmapImage is None):
            return

        # The axes
        self.axes = self.figure.add_axes([.15, .15, .75, .8])
        if self.config['xaxis'] == 'off':
            self.axes.xaxis.set_visible(False)
        else:
            self.axes.xaxis.set_visible(True)
            nLabels = self.config['nxlabels']
            if nLabels not in ['Auto', 'auto', '0', 0]:
                self.axes.xaxis.set_major_locator(MaxNLocator(nLabels))
            else:
                self.axes.xaxis.set_major_locator(AutoLocator())
        if self.config['yaxis'] == 'off':
            self.axes.yaxis.set_visible(False)
        else:
            self.axes.yaxis.set_visible(True)
            nLabels = self.config['nylabels']
            if nLabels not in ['Auto', 'auto', '0', 0]:
                self.axes.yaxis.set_major_locator(MaxNLocator(nLabels))
            else:
                self.axes.yaxis.set_major_locator(AutoLocator())

        if self.pixmapImage is not None:
            self._updatePixmapFigure()
            return

        interpolation = self.config['interpolation']
        origin = self.config['origin']

        cmap = self.__temperatureCmap
        ccmap = mpl_colormaps['gray']
        if self.config['colormap'] in ['grey','gray']:
            cmap  = mpl_colormaps['gray']
            ccmap = self.__temperatureCmap
        elif self.config['colormap'] in ['yarg','yerg']:
            cmap  = self.__reversedGrayCmap
            ccmap = self.__temperatureCmap
        elif self.config['colormap']=='jet':
            cmap = mpl_colormaps['jet']
        elif self.config['colormap']=='hot':
            cmap = mpl_colormaps['hot']
        elif self.config['colormap']=='cool':
            cmap = mpl_colormaps['cool']
        elif self.config['colormap']=='copper':
            cmap = mpl_colormaps['copper']
        elif self.config['colormap']=='spectral':
            cmap = mpl_colormaps['Spectral']
        elif self.config['colormap']=='hsv':
            cmap = mpl_colormaps['hsv']
        elif self.config['colormap']=='rainbow':
            cmap = mpl_colormaps['gist_rainbow']
        elif self.config['colormap']=='red':
            cmap = self.__redCmap
        elif self.config['colormap']=='green':
            cmap = self.__greenCmap
        elif self.config['colormap']=='blue':
            cmap = self.__blueCmap
        elif self.config['colormap']=='temperature':
            cmap = self.__temperatureCmap
        elif self.config['colormap'] == 'paired':
            cmap = mpl_colormaps['Paired']
        elif self.config['colormap'] == 'paired_r':
            cmap = mpl_colormaps['Paired_r']
        elif self.config['colormap'] == 'pubu':
            cmap = mpl_colormaps['PuBu']
        elif self.config['colormap'] == 'pubu_r':
            cmap = mpl_colormaps['PuBu_r']
        elif self.config['colormap'] == 'rdbu':
            cmap = mpl_colormaps['RdBu']
        elif self.config['colormap'] == 'rdbu_r':
            cmap = mpl_colormaps['RdBu_r']
        elif self.config['colormap'] == 'gist_earth':
            cmap = mpl_colormaps['gist_earth']
        elif self.config['colormap'] == 'gist_earth_r':
            cmap = mpl_colormaps['gist_earth_r']
        elif self.config['colormap'] == 'blues':
            cmap = mpl_colormaps['Blues']
        elif self.config['colormap'] == 'blues_r':
            cmap = mpl_colormaps['Blues_r']
        elif self.config['colormap'] == 'ylgnbu':
            cmap = mpl_colormaps['YlGnBu']
        elif self.config['colormap'] == 'ylgnbu_r':
            cmap = mpl_colormaps['YlGnBu_r']
        else:
            _logger.warning("Unsupported colormap %s", self.config['colormap'])

        if self.config['extent'] is None:
            h, w = self.imageData.shape
            x0 = self.config['xorigin']
            y0 = self.config['yorigin']
            w = w * self.config['xpixelsize']
            h = h * self.config['ypixelsize']
            if origin == 'upper':
                extent = (x0, w+x0,
                          h+y0, y0)
            else:
                extent = (x0, w+x0,
                          y0, h+y0)
        else:
            extent = self.config['extent']


        vlimits = self.__getValueLimits()
        if vlimits is None:
            imageData = self.imageData
            vmin = self.imageData.min()
            vmax = self.imageData.max()
        else:
            vmin = min(vlimits[0], vlimits[1])
            vmax = max(vlimits[0], vlimits[1])
            imageData = self.imageData.clip(vmin,vmax)

        if self.config['linlogcolormap'] != 'linear':
            if vmin <= 0:
                if vmax > 0:
                    vmin = min(imageData[imageData>0])
                else:
                    vmin = 0.0
                    vmax = 1.0
            self._image  = self.axes.imshow(imageData.clip(vmin,vmax),
                                        interpolation=interpolation,
                                        origin=origin,
                                        cmap=cmap,
                                        extent=extent,
                                        norm=LogNorm(vmin, vmax))
        else:
            self._image  = self.axes.imshow(imageData,
                                        interpolation=interpolation,
                                        origin=origin,
                                        cmap=cmap,
                                        extent=extent,
                                        norm=Normalize(vmin, vmax))

        ylim = self.axes.get_ylim()

        if self.config['colorbar'] is not None:
            barorientation = self.config['colorbar']
            if barorientation == "vertical":
                xlim = self.axes.get_xlim()
                deltaX = abs(xlim[1] - xlim[0])
                deltaY = abs(ylim[1] - ylim[0])
                ratio = deltaY/ float(deltaX)
                shrink = ratio
                self._colorbar = self.figure.colorbar(self._image,
                                        fraction=0.046, pad=0.04,
                                        #shrink=shrink,
                                        aspect=20 * shrink,
                                        orientation=barorientation)
                if ratio < 0.51:
                    nTicks = 5
                    if ratio < 0.2:
                        nTicks = 3
                    try:
                        tick_locator = MaxNLocator(nTicks)
                        self._colorbar.locator = tick_locator
                        self._colorbar.update_ticks()
                    except Exception:
                        _logger.warning("Colorbar error %s", sys.exc_info())
                        pass
            else:
                self._colorbar = self.figure.colorbar(self._image,
                                        orientation=barorientation)

        #contour plot
        if self.config['contour'] != 'off':
            dataMin = imageData.min()
            dataMax = imageData.max()
            ncontours = int(self.config['contourlevels'])
            levels = (numpy.arange(ncontours)) *\
                     (dataMax - dataMin)/float(ncontours)
            contourlinewidth = int(self.config['contourlinewidth'])/10.
            if self.config['contour'] == 'filled':
                self._contour = self.axes.contourf(imageData, levels,
                     origin=origin,
                     cmap=ccmap,
                     extent=extent)
            else:
                self._contour = self.axes.contour(imageData, levels,
                     origin=origin,
                     cmap=ccmap,
                     linewidths=contourlinewidth,
                     extent=extent)
            if self.config['contourlabels'] != 'off':
                self.axes.clabel(self._contour, fontsize=9,
                        inline=1, fmt=self.config['contourlabelformat'])
            if 0 and  self.config['colorbar'] is not None:
                if barorientation == 'horizontal':
                    barorientation = 'vertical'
                else:
                    barorientation = 'horizontal'
                self._ccolorbar=self.figure.colorbar(self._contour,
                                                     orientation=barorientation,
                                                     extend='both')

        self.__postImage(ylim)

    def getParameters(self):
        return self.config

    def setParameters(self, ddict):
        self.config.update(ddict)
        self.updateFigure()

    def setPixmapImage(self, image=None, bgr=False):
        if image is None:
            self.pixmapImage = None
            self.updateFigure()
            return

        if bgr:
            self.pixmapImage = image * 1
            self.pixmapImage[:,:,0] = image[:,:,2]
            self.pixmapImage[:,:,2] = image[:,:,0]
        else:
            self.pixmapImage = image

        shape = self.pixmapImage.shape
        self.pixmapMask = numpy.ones(shape, numpy.uint8)
        shape = self.pixmapImage.shape
        if 0:
            # This is slow, but I do not expect huge images
            for i in range(shape[0]):
                for j in range(shape[1]):
                    if (self.pixmapImage[i,j,0] == 0):
                        if (self.pixmapImage[i,j,1] == 0):
                            if (self.pixmapImage[i,j,2] == 0):
                                self.pixmapMask[i,j,0:3] = [0, 0, 0]
        else:
            #the image is RGBA, so the sum when there is nothing is 255
            s = self.pixmapImage.sum(axis=-1)
            self.pixmapMask[s==255, 0:3] = 0
        self.updateFigure()

    def _updatePixmapFigure(self):
        interpolation = self.config['interpolation']
        origin = self.config['origin']
        if self.config['extent'] is None:
            h= self.pixmapImage.shape[0]
            w= self.pixmapImage.shape[1]
            x0 = self.config['xorigin']
            y0 = self.config['yorigin']
            w = w * self.config['xpixelsize']
            h = h * self.config['ypixelsize']
            if origin == 'upper':
                extent = (x0, w+x0,
                          h+y0, y0)
            else:
                extent = (x0, w+x0,
                          y0, h+y0)
        else:
            extent = self.config['extent']
        if self.config['imagebackground'].lower() == 'white':
            if 0:
                self.pixmapImage[:] = (self.pixmapImage * self.pixmapMask) +\
                               (self.pixmapMask == 0) * 255
            else:
                self.pixmapImage[self.pixmapMask == 0] = 255
        elif self.config['imagebackground'].lower() == 'grey':
            if 0:
                self.pixmapImage[:] = (self.pixmapImage * self.pixmapMask) +\
                               (self.pixmapMask == 0) * 128
            else:
                self.pixmapImage[self.pixmapMask == 0] = 128
        else:
            if 0:
                self.pixmapImage[:] = (self.pixmapImage * self.pixmapMask)
            else:
                self.pixmapImage[self.pixmapMask == 0]= 0
        self._image = self.axes.imshow(self.pixmapImage,
                                       interpolation=interpolation,
                                       origin=origin,
                                       extent=extent)

        ylim = self.axes.get_ylim()
        self.__postImage(ylim)

    def __getValueLimits(self):
        if (self.config['valuemin'] is not None) and\
           (self.config['valuemax'] is not None) and\
           (self.config['valuemin'] != self.config['valuemax']):
            vlimits = (self.config['valuemin'],
                           self.config['valuemax'])
        elif self.config['vlimits'] is not None:
            vlimits = self.config['vlimits']
        else:
            vlimits = None
        return vlimits

    def __postImage(self, ylim):
        self.axes.set_title(self.config['title'])
        self.axes.set_xlabel(self.config['xlabel'])
        self.axes.set_ylabel(self.config['ylabel'])

        origin = self.config['origin']
        if (self.config['zoomxmin'] is not None) and\
           (self.config['zoomxmax'] is not None)and\
           (self.config['zoomxmax'] != self.config['zoomxmin']):
            xlimits = (self.config['zoomxmin'],
                           self.config['zoomxmax'])
        elif self.config['xlimits'] is not None:
            xlimits = self.config['xlimits']
        else:
            xlimits = None

        if (self.config['zoomymin'] is not None) and\
           (self.config['zoomymax'] is not None) and\
           (self.config['zoomymax'] != self.config['zoomymin']):
            ylimits = (self.config['zoomymin'],
                           self.config['zoomymax'])
        elif self.config['ylimits'] is not None:
            ylimits = self.config['ylimits']
        else:
            ylimits = None

        if ylimits is None:
            self.axes.set_ylim(ylim[0],ylim[1])
        else:
            ymin = min(ylimits)
            ymax = max(ylimits)
            if origin == "lower":
                self.axes.set_ylim(ymin, ymax)
            else:
                self.axes.set_ylim(ymax, ymin)

        if xlimits is not None:
            xmin = min(xlimits)
            xmax = max(xlimits)
            self.axes.set_xlim(xmin, xmax)

        self.draw()

def test():
    app = qt.QApplication([])
    a=numpy.arange(256.)
    a = a.reshape(8, 32)
    w = SaveImageSetup(None, a)
    ddict = w.getParameters()
    ddict["colorbar"] = "vertical"
    w.setParameters(ddict)
    w.show()
    app.exec()

if __name__ == "__main__":
    test()
