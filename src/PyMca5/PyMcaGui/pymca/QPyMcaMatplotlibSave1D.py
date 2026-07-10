#!/usr/bin/env python
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import numpy
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict

from matplotlib import __version__ as matplotlib_version
from matplotlib.font_manager import FontProperties
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

_logger = logging.getLogger(__name__)

colordict = {}
colordict['blue']   = '#0000ff'
colordict['red']    = '#ff0000'
colordict['green']  = '#00ff00'
colordict['black']  = '#000000'
colordict['white']  = '#ffffff'
colordict['pink']   = '#ff66ff'
colordict['brown']  = '#a52a2a'
colordict['orange'] = '#ff9900'
colordict['violet'] = '#6600ff'
colordict['grey']   = '#808080'
colordict['yellow'] = '#ffff00'
colordict['darkgreen'] = 'g'
colordict['darkbrown'] = '#660000'
colordict['magenta']   = 'm'
colordict['cyan']      = 'c'
colordict['bluegreen'] = '#33ffff'
colorlist  = [colordict['black'],
              colordict['red'],
              colordict['blue'],
              colordict['green'],
              colordict['pink'],
              colordict['brown'],
              colordict['cyan'],
              colordict['orange'],
              colordict['violet'],
              colordict['bluegreen'],
              colordict['grey'],
              colordict['magenta'],
              colordict['darkgreen'],
              colordict['darkbrown'],
              colordict['yellow']]


class MatplotlibCurveTable(qt.QTableWidget):
    sigCurveTableSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        labels = ["Curve", "Alias", "Color", "Line Style", "Line Symbol"]
        n = len(labels)
        self.setColumnCount(len(labels))
        for i in range(len(labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[i])
            self.setHorizontalHeaderItem(i,item)
        rheight = self.horizontalHeader().sizeHint().height()
        self.setMinimumHeight(5*rheight)
        self.labels = labels

    def setCurveListAndDict(self, curvelist, curvedict):
        n = len(curvelist)
        self.setRowCount(n)
        if n < 1:
            return
        rheight = self.horizontalHeader().sizeHint().height()
        for i in range(n):
            self.setRowHeight(i, rheight)

        i = 0
        #self.__disconnect = True
        for legend in curvelist:
            self.addCurve(i, legend, curvedict[legend])
            i += 1
        #self.__disconnect = False
        #self.resizeColumnToContents(0)
        #self.resizeColumnToContents(3)

    def addCurve(self, i, legend, ddict):
        j = 0
        widget = self.cellWidget(i, j)
        if widget is None:
            widget = CheckBoxItem(self, i, j)
            self.setCellWidget(i, j, widget)
            widget.sigCheckBoxItemSignal.connect(self._mySlot)
        widget.setChecked(True)
        widget.setText(legend)

        #alias
        alias = ddict.get('alias', None)
        if alias is None:
            alias = legend
        j = 1
        item = self.item(i, j)
        if item is None:
            item = qt.QTableWidgetItem(alias,
                                       qt.QTableWidgetItem.Type)
            item.setTextAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.setItem(i, j, item)
        else:
            item.setText(alias)
        #item.setFlags(qt.Qt.ItemIsEnabled | qt.Qt.ItemIsSelectable)

        #color
        j = 2
        widget = self.cellWidget(i, j)
        if widget is None:
            options = list(colordict.keys())
            options.sort()
            widget = ComboBoxItem(self, i, j, options=options)
            self.setCellWidget(i, j, widget)
            widget.sigComboBoxItemSignal.connect(self._mySlot)
        color = ddict['color']
        if color == 'k':
            color = '#000000'
        for key in colordict.keys():
            if colordict[key] == color:
                break
        idx = widget.findText(key)
        widget.setCurrentIndex(idx)

        #linestyle
        j = 3
        widget = self.cellWidget(i, j)
        options = ['-','--','-.',':','']
        if widget is None:
            widget = ComboBoxItem(self, i, j, options=options)
            self.setCellWidget(i, j, widget)
            widget.sigComboBoxItemSignal.connect(self._mySlot)

        idx = widget.findText(ddict['linestyle'])
        widget.setCurrentIndex(idx)

        #line marker
        j = 4
        widget = self.cellWidget(i, j)
        options = ['','o','+','x','^']
        if widget is None:
            widget = ComboBoxItem(self, i, j, options=options)
            self.setCellWidget(i, j, widget)
            widget.sigComboBoxItemSignal.connect(self._mySlot)

        idx = widget.findText(ddict['linemarker'])
        widget.setCurrentIndex(idx)


    def _mySlot(self, ddict):
        #if self.__disconnect:
        #    return
        ddict = {}
        ddict['curvelist'] = []
        ddict['curvedict'] = {}
        for i in range(self.rowCount()):
            widget = self.cellWidget(i, 0)
            legend = str(widget.text())
            ddict['curvelist'].append(legend)
            ddict['curvedict'][legend] = {}
            alias = str(self.item(i, 1).text())
            if widget.isChecked():
                plot = 1
            else:
                plot = 0
            ddict['curvedict'][legend]['plot']  = plot
            ddict['curvedict'][legend]['alias'] = alias
            widget = self.cellWidget(i, 2)
            color = colordict[str(widget.currentText())]
            ddict['curvedict'][legend]['color'] = color
            widget = self.cellWidget(i, 3)
            linestyle = str(widget.currentText())
            ddict['curvedict'][legend]['linestyle'] = linestyle
            widget = self.cellWidget(i, 4)
            linemarker = str(widget.currentText())
            ddict['curvedict'][legend]['linemarker'] = linemarker
        self.sigCurveTableSignal.emit(ddict)

class ComboBoxItem(qt.QComboBox):
    sigComboBoxItemSignal = qt.pyqtSignal(object)
    def __init__(self, parent, row, col, options=[1,2,3]):
        qt.QComboBox.__init__(self, parent)
        self.__row = row
        self.__col = col
        for option in options:
            self.addItem(option)
        self.activated[int].connect(self._mySignal)

    def _mySignal(self, value):
        ddict = {}
        ddict["event"] = "activated"
        ddict["item"] = value
        ddict["row"] = self.__row * 1
        ddict["col"] = self.__col * 1
        self.sigComboBoxItemSignal.emit(ddict)

class CheckBoxItem(qt.QCheckBox):
    sigCheckBoxItemSignal = qt.pyqtSignal(object)
    def __init__(self, parent, row, col):
        qt.QCheckBox.__init__(self, parent)
        self.__row = row
        self.__col = col
        self.clicked[bool].connect(self._mySignal)

    def _mySignal(self, value):
        ddict = {}
        ddict["event"] = "clicked"
        ddict["state"] = value
        ddict["row"] = self.__row * 1
        ddict["col"] = self.__col * 1
        self.sigCheckBoxItemSignal.emit(ddict)


class QPyMcaMatplotlibSaveDialog(qt.QDialog):
    def __init__(self, parent=None, **kw):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("Matplotlib preview - Resize to your taste")
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self._lastGoodSize = None

        self.axesLabelsWidget = qt.QWidget(self)
        layout = qt.QHBoxLayout(self.axesLabelsWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        xLabelLabel = qt.QLabel(self.axesLabelsWidget)
        xLabelLabel.setText("X Axis Label: ")
        self.xLabelLine = qt.QLineEdit(self.axesLabelsWidget)
        yLabelLabel = qt.QLabel(self.axesLabelsWidget)
        yLabelLabel.setText("Y Axis Label: ")
        self.yLabelLine = qt.QLineEdit(self.axesLabelsWidget)
        layout.addWidget(xLabelLabel)
        layout.addWidget(self.xLabelLine)
        layout.addWidget(yLabelLabel)
        layout.addWidget(self.yLabelLine)


        self.curveTable = MatplotlibCurveTable(self)
        self.plot = QPyMcaMatplotlibSave(self, **kw)
        self.plot.setCurveTable(self.curveTable)
        self.actionsWidget = qt.QWidget(self)
        layout = qt.QHBoxLayout(self.actionsWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.doNotShowAgain = qt.QCheckBox(self.actionsWidget)
        self.doNotShowAgain.setChecked(False)
        self.doNotShowAgain.setText("Don't show again this dialog")

        self.acceptButton = qt.QPushButton(self.actionsWidget)
        self.acceptButton.setText("Accept")
        self.acceptButton.setAutoDefault(False)
        self.dismissButton = qt.QPushButton(self.actionsWidget)
        self.dismissButton.setText("Dismiss")
        self.dismissButton.setAutoDefault(False)
        layout.addWidget(self.doNotShowAgain)
        layout.addWidget(qt.HorizontalSpacer(self.actionsWidget))
        layout.addWidget(self.acceptButton)
        layout.addWidget(self.dismissButton)
        horizontal = False
        if horizontal:
            self.mainLayout.addWidget(self.axesLabelsWidget, 0, 0)
            self.mainLayout.addWidget(self.plot, 1, 0)
            self.mainLayout.addWidget(self.curveTable, 1, 1)
            self.mainLayout.addWidget(self.actionsWidget, 2, 0, 1, 2)
            self.mainLayout.setColumnStretch(0, 1)
        else:
            self.mainLayout.addWidget(self.axesLabelsWidget, 0, 0)
            self.mainLayout.addWidget(self.curveTable, 1, 0)
            self.mainLayout.addWidget(self.plot, 2, 0)
            self.mainLayout.addWidget(self.actionsWidget, 3, 0)
            self.mainLayout.setRowStretch(1, 1)

        self.xLabelLine.editingFinished[()].connect(self._xLabelSlot)
        self.yLabelLine.editingFinished[()].connect(self._yLabelSlot)

        self.acceptButton.clicked.connect(self.accept)
        self.dismissButton.clicked.connect(self.reject)

    def exec_(self):
        return self.exec()

    def exec(self):
        self.plot.draw()
        if self.doNotShowAgain.isChecked():
            return qt.QDialog.Accepted
        else:
            if self._lastGoodSize is not None:
                self.resize(self._lastGoodSize)
            return qt.QDialog.exec(self)

    def accept(self):
        self._lastGoodSize = self.size()
        return qt.QDialog.accept(self)

    def _xLabelSlot(self):
        label = self.xLabelLine.text()
        self.plot.setXLabel(label)
        self.plot.draw()

    def _yLabelSlot(self):
        label = self.yLabelLine.text()
        self.plot.setYLabel(label)
        self.plot.draw()

    def setXLabel(self, label):
        self.xLabelLine.setText(label)
        self.plot.setXLabel(label)

    def setYLabel(self, label):
        self.yLabelLine.setText(label)
        self.plot.setYLabel(label)

class QPyMcaMatplotlibSave(FigureCanvas):
    def __init__(self, parent=None,
                 size = (7,3.5),
                 dpi = 100,
                 logx = False,
                 logy = False,
                 legends = True,
                 bw = False):

        self.fig = Figure(figsize=size, dpi=dpi) #in inches
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self,
                                   qt.QSizePolicy.Expanding,
                                   qt.QSizePolicy.Expanding)
        self.curveTable = None
        self.dpi=dpi
        ddict = {'logx':logx,
                 'logy': logy,
                 'legends':legends,
                 'bw':bw}
        self.ax=None
        self.curveList = []
        self.curveDict = {}
        self.setParameters(ddict)
        #self.setBlackAndWhiteEnabled(bw)
        #self.setLogXEnabled(logx)
        #self.setLogYEnabled(logy)
        #self.setLegendsEnabled(legends)

        self.xmin = None
        self.xmax = None
        self.ymin = None
        self.ymax = None
        self.limitsSet = False

    def setCurveTable(self, table):
        self.curveTable = table
        self.curveTable.sigCurveTableSignal.connect(self.updateFromTable)

    def setParameters(self,kw):
        if 'bw' in kw:
            self.setBlackAndWhiteEnabled(kw['bw'])
        if 'logx' in kw:
            self.setLogXEnabled(kw['logx'])
        if 'logy' in kw:
            self.setLogYEnabled(kw['logy'])
        if 'legends' in kw:
            self.setLegendsEnabled(kw['legends'])
        self._dataCounter = 0
        self.createAxes()

    def setBlackAndWhiteEnabled(self, flag):
        self._bw = flag
        if self._bw:
            self.colorList = ['k']   #only black
            self.styleList = ['-', ':', '-.', '--']
            self.nColors   = 1
        else:
            self.colorList = colorlist
            self.styleList = ['-', '-.', ':']
            self.nColors   = len(colorlist)
        self._dataCounter = 0
        self.nStyles   = len(self.styleList)
        self.colorIndex = 0
        self.styleIndex = 0

    def setLogXEnabled(self, flag):
        self._logX = flag

    def setLogYEnabled(self, flag):
        self._logY = flag

    def setLegendsEnabled(self, flag):
        self._legend   = flag
        self._legendList = []

    def createAxes(self):
        self.fig.clear()
        if self.ax is not None:
            self.ax.cla()
        if not self._legend:
            if self._logY:
                ax = self.fig.add_axes([.15, .15, .75, .8])
            else:
                ax = self.fig.add_axes([.15, .15, .75, .75])
        else:
            if self._logY:
                ax = self.fig.add_axes([.15, .15, .7, .8])
            else:
                ax = self.fig.add_axes([.15, .15, .7, .8])

        ax.set_axisbelow(True)
        self.ax = ax
        if self._logY:
            self._axFunction = ax.semilogy
        else:
            self._axFunction = ax.plot
        self._legendList=[]
        self.curveList = []
        self.curveDict = {}

    def setLimits(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.limitsSet = True


    def _filterData(self, x, y):
        index = numpy.flatnonzero((self.xmin <= x) & (x <= self.xmax)&\
                                  (self.ymin <= y) & (y <= self.ymax))
        return index

    def _getColorAndStyle(self):
        color = self.colorList[self.colorIndex]
        style = self.styleList[self.styleIndex]
        self.colorIndex += 1
        if self.colorIndex >= self.nColors:
            self.colorIndex = 0
            self.styleIndex += 1
            if self.styleIndex >= self.nStyles:
                self.styleIndex = 0
        return color, style

    def addDataToPlot(self, x, y, legend = None,
                      color = None,
                      linewidth = None,
                      linestyle = None,
                      marker=None,
                      alias = None,**kw):
        x = numpy.asarray(x)
        y = numpy.asarray(y)
        if self.limitsSet is not None:
            n = self._filterData(x, y)
            if not len(n):
                return
            #x = x[n]
            #y = y[n]
        n = max(x.shape)
        if n == 0:
            #nothing to plot
            _logger.debug("nothing to plot")
            return

        style = None
        if color is None:
            color, style = self._getColorAndStyle()
        if linestyle is None:
            if style is None:
                style = '-'
        else:
            style = linestyle
        if marker is None:
            marker = ''
        if linewidth is None:linewidth = 1.0
        self._axFunction( x, y, linestyle = style, color=color, linewidth = linewidth, **kw)
        self._dataCounter += 1
        if legend is None:
            #legend = "%02d" % self._dataCounter    #01, 02, 03, ...
            legend = "%c" % (96+self._dataCounter)  #a, b, c, ..
        self._legendList.append(legend)
        if legend not in self.curveList:
            self.curveList.append(legend)
        self.curveDict[legend] = {}
        self.curveDict[legend]['x'] = x
        self.curveDict[legend]['y'] = y
        self.curveDict[legend]['linestyle'] = style
        self.curveDict[legend]['color'] = color
        self.curveDict[legend]['linewidth'] = linewidth
        self.curveDict[legend]['linemarker'] = marker
        if alias is not None:
            self.curveDict[legend]['alias'] = alias
            self._legendList[-1] = alias
        if self.curveTable is not None:
            self.curveTable.setCurveListAndDict(self.curveList, self.curveDict)

    def setXLabel(self, label):
        self.ax.set_xlabel(label)

    def setYLabel(self, label):
        self.ax.set_ylabel(label)

    def setTitle(self, title):
        self.ax.set_title(title)

    def plotLegends(self, legendlist=None):
        if not self._legend:return
        if legendlist is None:
            legendlist = self._legendList
        if not len(legendlist):return
        loc = (1.01, 0.0)
        labelsep = 0.015
        drawframe = True
        fontproperties = FontProperties(size=10)
        if len(legendlist) > 14:
            drawframe = False
            if matplotlib_version < '0.99.0':
                fontproperties = FontProperties(size=8)
                loc = (1.05, -0.2)
            else:
                if len(legendlist) < 18:
                    #drawframe = True
                    loc = (1.01,  0.0)
                elif len(legendlist) < 25:
                    loc = (1.05,  0.0)
                    fontproperties = FontProperties(size=8)
                elif len(legendlist) < 28:
                    loc = (1.05,  0.0)
                    fontproperties = FontProperties(size=6)
                else:
                    loc = (1.05,  -0.1)
                    fontproperties = FontProperties(size=6)

        if matplotlib_version < '0.99.0':
            legend = self.ax.legend(legendlist,
                                loc = loc,
                                prop = fontproperties,
                                labelsep = labelsep,
                                pad = 0.15)
        else:
            legend = self.ax.legend(legendlist,
                                loc = loc,
                                prop = fontproperties,
                                labelspacing = labelsep,
                                borderpad = 0.15)
        legend.draw_frame(drawframe)

    def draw(self):
        if self.limitsSet:
            self.ax.set_xlim(self.xmin, self.xmax)
            self.ax.set_ylim(self.ymin, self.ymax)
        FigureCanvas.draw(self)

    def updateFromTable(self, ddict):
        #for line2D in self.ax.lines:
        #    #label = line2D.get_label()
        #    #if label == legend:
        #    line2D.remove()
        xlabel = self.ax.get_xlabel()
        ylabel = self.ax.get_ylabel()
        if self.limitsSet:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
        self.ax.cla()
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        if self.limitsSet:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        legendList = []
        curvelist = ddict['curvelist']
        for legend in curvelist:
            if not ddict['curvedict'][legend]['plot']:
                continue
            x = self.curveDict[legend]['x']
            y = self.curveDict[legend]['y']
            alias = ddict['curvedict'][legend]['alias']
            linestyle = self.curveDict[legend]['linestyle']
            color = ddict['curvedict'][legend]['color']
            linewidth = self.curveDict[legend]['linewidth']
            linestyle = ddict['curvedict'][legend]['linestyle']
            linemarker = ddict['curvedict'][legend]['linemarker']
            if linestyle in ['None', '']:
                linestyle = ''
            if linemarker in ['None', '']:
                linemarker = ''
            self._axFunction( x, y,
                              linestyle=linestyle,
                              marker=linemarker,
                              color=color,
                              linewidth=linewidth)
            legendList.append(alias)
        if self._legend:
            self.plotLegends(legendList)
        self.draw()

    def saveFile(self, filename, format=None):
        if format is None:
            format = filename[-3:]

        if format.upper() not in ['EPS', 'PNG', 'SVG']:
            raise "Unknown format %s" % format

        if os.path.exists(filename):
            os.remove(filename)

        if self.limitsSet:
            self.ax.set_ylim(self.ymin, self.ymax)
            self.ax.set_xlim(self.xmin, self.xmax)
        #self.plotLegends()
        self.print_figure(filename, dpi=self.dpi)
        return

if __name__ == "__main__":
    app = qt.QApplication([])
    w0=QPyMcaMatplotlibSaveDialog(legends=True)
    w=w0.plot
    x = numpy.arange(1200.)
    w.setLimits(0, 1200., 0, 12000.)
    if len(sys.argv) > 2:
        n = int(sys.argv[2])
    else:
        n = 14
    for i in range(n):
        y = x * i
        w.addDataToPlot(x, y, legend="%d" % i)
    #w.setTitle('title')
    w0.setXLabel('Channel')
    w0.setYLabel('Counts')
    w.plotLegends()
    ret = w0.exec()
    if ret:
        w.saveFile("filename.png")
        print("Plot filename.png saved")
    w.setParameters({'logy':True, 'bw':True})
    for i in range(n):
        y = x * i + 1
        w.addDataToPlot(x,y, legend="%d" % i)
    #w.setTitle('title')
    w.setXLabel('Channel')
    w.setYLabel('Counts')
    w.plotLegends()
    ret = w0.exec()
