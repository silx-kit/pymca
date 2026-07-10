#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
__author__ = "Tonn Rueter - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import logging
import os
from os.path import isdir as osPathIsDir
from os.path import basename as osPathBasename
from os.path import join as osPathJoin

import numpy
from PyMca5.PyMcaMath.fitting.SpecfitFuns import upstep, downstep

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PlotWindow as DataDisplay
from PyMca5.PyMcaPhysics.xrf import Elements
from PyMca5.PyMcaIO import ConfigDict

from PyMca5 import PyMcaDataDir, PyMcaDirs
from PyMca5.PyMcaGui.io import QSpecFileWidget
from PyMca5.PyMcaCore import SpecFileDataSource
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict

if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
    QStringList = list

if hasattr(qt, "QStringList"):
    QStringList = qt.QStringList
else:
    QStringList = list


_logger = logging.getLogger(__name__)
NEWLINE = '\n'

class Calculations(object):
    def __init__(self):
        pass

    def cumtrapz(self, y, x=None, dx=1.0):
        y = y[:]
        if x is None:
            x = numpy.arange(len(y), dtype=y.dtype) * dx
        else:
            x = x[:]

        if not numpy.all(numpy.diff(x) > 0.):
            # assure monotonically increasing x
            idx = numpy.argsort(x)
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)
            # Avoid dublicates
            x.ravel()
            idx = numpy.nonzero(numpy.diff(x) > 0)[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)

        return numpy.cumsum(.5 * numpy.diff(x) * (y[1:] + y[:-1]))

    def magneticMoment(self, p, q, r, n, econf):
        """
        Input
        -----

        :param p: Integral over the (first) edge of the XMCD (difference) signal
        :type p: Float
        :param q: Integral over the (second) edge of the XMCD (difference) signal
        :type q: Float
        :param r: Integral over the complete XAS signal
        :type r: Float
        :param n: Electron occupation number of the sample material
        :type n: Float
        :param econf: Determines if material is of 3d or 4f type and thus the number of electronic states in the outer shell
        :type econf: String

        Returns the orbital resp. the spin part of the magnetic moment

        Paper references:
        3d materials: Chen et al., Phys. Rev. Lett., 75(1), 152
        4f materials: Krishnamurthy et al., Phys. Rev. B, 79(1), 014426
        """
        mOrbt, mSpin, mRatio = None, None, None

        # Check if r is non-zero
        if r == 0.:
            raise ZeroDivisionError()

        # Determine number of states in outer shell
        if econf == '3d':
            _logger.debug(
                    'Calculations.magneticMoment -- considering 3d material:'
                    '\n\tp: %s, q: %s, r:%s', str(p), str(q), str(r))
            nMax = 10.
            # Calculate Integrals
            if q is not None:
                #mOrbt = abs(-4./3. * q * (nMax - n) / (2.*r))
                mOrbt = abs(-2./3. * q * (nMax - n) / r)
            if (q is not None) and (p is not None):
                #mSpin  = abs((6.*p - 4.*q) * (nMax - n) / (2.*r))
                mSpin  = abs((3.*p - 2.*q) * (nMax - n) / r)
                mRatio = abs(2.*q/(9.*p-6.*q))
        elif econf == '4f':
            _logger.debug('Calculations.magneticMoment -- considering 4f material:'
                          '\n\tp: %s, q: %s, r:%s', str(p), str(q), str(r))
            nMax = 14.
            if q is not None:
                mOrbt = abs(q * (nMax - n) / r)
            if (q is not None) and (p is not None) and (r is not None):
                mSpin  = abs((3.*q - 5.*p) * (nMax - n) / (2. * r))
                mRatio = mOrbt / mSpin
        else:
            raise ValueError('Calculations.magneticMoment -- Element must either be 3d or 4f type!')

        return mOrbt, mSpin, mRatio

class MarkerSpinBox(qt.QDoubleSpinBox):

    intersectionsChangedSignal = qt.pyqtSignal()

    def __init__(self, window, plotWindow, label='', parent=None):
        qt.QDoubleSpinBox.__init__(self, parent)

        # Attributes
        self.label = label
        self.window = window
        self.plotWindow = plotWindow
        #self.graph = graph
        self.markerID = self.plotWindow.insertXMarker(0.,
                                                      legend=label,
                                                      text=label)

        # Initialize
        self.setMinimum(0.)
        self.setMaximum(10000.)
        self.setValue(0.)

        # Connects
        self.plotWindow.sigPlotSignal.connect(self._handlePlotSignal)
        self.valueChanged.connect(self._valueChanged)

    def getIntersections(self):
        dataList = self.plotWindow.getAllCurves()
        resDict  = {}
        pos      = self.value()
        if not isinstance(pos, float):
            return
        for x, y, legend, info in dataList:
            res  = float('NaN')
            if numpy.all(pos < x) or numpy.all(x < pos):
                continue
                #raise ValueError('Marker outside of data range')
            if pos in x:
                idx = numpy.where(x == pos)
                res = y[idx]
            else:
                # Intepolation needed, assume well
                # behaved data (c.f. copy routine)
                lesserIdx  = numpy.nonzero(x < pos)[0][-1]
                greaterIdx = numpy.nonzero(x > pos)[0][0]
                dy = y[lesserIdx] - y[greaterIdx]
                dx = x[lesserIdx] - x[greaterIdx]
                res = dy/dx * (pos - x[lesserIdx]) + y[lesserIdx]
            resDict[legend] = (pos, res)
        return resDict

    def hideMarker(self):
        self.plotWindow.removeMarker(self.label)
        self.markerID = None

    def showMarker(self):
        self.plotWindow.removeMarker(self.label)
        self.markerID = self.plotWindow.insertXMarker(
                                self.value(),
                                legend=self.label,
                                text=self.label,
                                color='blue',
                                selectable=False,
                                draggable=True)

    def _setMarkerFollowMouse(self, windowTitle):
        windowTitle = str(windowTitle)
        if self.window == windowTitle:
            # Blue, Marker is active
            color = 'blue'
            draggable  = True
        else:
            # Black, marker is inactive
            color = 'k'
            draggable  = False
        # Make shure that the marker is deleted
        # If marker is not present, removeMarker just passes..
        self.markerID = self.plotWindow.insertXMarker(
                                self.value(),
                                legend=self.label,
                                text=self.label,
                                color=color,
                                selectable=False,
                                draggable=draggable)

    def _handlePlotSignal(self, ddict):
        if ddict['event'] != 'markerMoving':
            return
        if ddict['label'] != self.label:
            return
        markerPos = ddict['x']
        self.blockSignals(True)
        self.setValue(markerPos)
        self.blockSignals(False)
        self.intersectionsChangedSignal.emit()

    def _valueChanged(self, val):
        try:
            val = float(val)
        except ValueError:
            _logger.debug('_valueChanged -- Sorry, it ain\'t gonna float: %s', str(val))
            return
        # Marker of same label as self.label gets replaced..
        self.markerID = self.plotWindow.insertXMarker(
                                val,
                                legend=self.label,
                                text=self.label,
                                color='blue',
                                selectable=False,
                                draggable=True)
        self.intersectionsChangedSignal.emit()

class LineEditDisplay(qt.QLineEdit):
    def __init__(self, controller, ddict=None, unit='', parent=None):
        qt.QLineEdit.__init__(self, parent)
        self.setReadOnly(True)
        self.setAlignment(qt.Qt.AlignRight)
        if ddict is None:
            self.ddict = {}
        else:
            self.ddict = ddict
        self.unit = unit
        self.setMaximumWidth(120)
        self.controller = controller
        if isinstance(self.controller, qt.QComboBox):
            if hasattr(self.controller, "textActivated"):
                self.controller.textActivated['QString'].connect(self.setText)
            else:
                self.controller.currentIndexChanged['QString'].connect(self.setText)
        elif isinstance(self.controller, qt.QDoubleSpinBox):
            # Update must be triggered otherwise
            #self.controller.valueChanged['QString'].connect(self.setText)
            pass
        else:
            raise ValueError('LineEditDisplay: Controller must be of type QComboBox or QDoubleSpinBox')
        #self.controller.destroyed.connect(self.destroy)

    def updateDict(self, ddict):
        # Only relevant if type(controller) == QComboBox
        self.ddict = ddict

    def updateUnit(self, unit):
        self.unit = unit

    def checkController(self):
        if isinstance(self.controller, qt.QComboBox):
            tmp = self.controller.currentText()
        elif isinstance(self.controller, qt.QDoubleSpinBox):
            tmp = self.controller.value()
        else:
            _logger.debug('LineEditDisplay.checkController -- Reached untreated case, setting empty string')
            tmp = ''
        self.setText(tmp)

    def setText(self, inp):
        inp = str(inp)
        if isinstance(self.controller, qt.QComboBox):
            if inp == '':
                text = ''
            else:
                tmp = self.ddict.get(inp,None)
                if tmp is not None:
                    try:
                        text = '%.2f meV'%(1000. * float(tmp))
                    except ValueError:
                        text = 'NaN'
                else:
                    text = '---'
        elif isinstance(self.controller, qt.QDoubleSpinBox):
            text = inp + ' ' + self.unit
        else:
            _logger.debug('LineEditDisplay.setText -- Reached untreated case, setting empty string')
            text = ''
        qt.QLineEdit.setText(self, text)


class SumRulesWindow(qt.QMainWindow):

    # Curve labeling
    __xasBGmodel = 'xas BG model'
    # Tab names
    __tabElem = 'element'
    __tabBG   = 'background'
    __tabInt  = 'integration'
    # Marker names
    __preMin = 'Pre Min'
    __preMax = 'Pre Max'
    __postMin = 'Post Min'
    __postMax = 'Post Max'
    __intP = 'p'
    __intQ = 'q'
    __intR = 'r'

    # Lists
    tabList = [__tabElem,
               __tabBG,
               __tabInt]
    xasMarkerList  = [__preMin,
                      __preMax,
                      __postMin,
                      __postMax]
    xmcdMarkerList = [__intP,
                      __intQ,
                      __intR]
    edgeMarkerList = []

    # Elements with 3d final state
    transitionMetals = ['Sc', 'Ti', 'V', 'Cr', 'Mn',
                         'Fe', 'Co', 'Ni', 'Cu']
    # Elements with 4f final state
    rareEarths = ['La', 'Ce', 'Pr', 'Nd', 'Pm',
                  'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
                  'Ho', 'Er', 'Tm', 'Yb']
    elementsDict = {
            ''  : [],
            '3d': transitionMetals,
            '4f': rareEarths
    }
    # Electron final states
    electronConfs = ['3d','4f']
    # Occuring Transitions
    occuringTransitions = ['L3M4', 'L3M5', 'L2M4', 'M5O3','M4O3']

    # Signals
    tabChangedSignal = qt.pyqtSignal('QString')

    def __init__(self, parent=None):
        qt.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Sum Rules Tool')
        if hasattr(DataDisplay,'PlotWindow'):
            self.plotWindow = DataDisplay.PlotWindow(
                parent=self,
                backend=None,
                plugins=False, # Hide plugin tool button
                newplot=False, # Hide mirror active curve, ... functionality
                roi=False,     # No ROI widget
                control=False, # Hide option button
                position=True, # Show x,y position display
                kw={'logx': False, # Hide logarithmic x-scale tool button
                    'logy': False, # Hide logarithmic y-scale tool button
                    'flip': False, # Hide whatever this does
                    'fit': False}) # Hide simple fit tool button
            self.plotWindow._buildLegendWidget()
        else:
            self.plotWindow = DataDisplay.ScanWindow(self)

        # Hide Buttons in the toolbar
        if hasattr(self.plotWindow,'scanWindowInfoWidget'):
            # Get rid of scanInfoWidget
            self.plotWindow.scanWindowInfoWidget.hide()
            self.plotWindow.graph.enablemarkermode()
            # Hide unnecessary buttons in the toolbar
            toolbarChildren = self.plotWindow.toolBar
            # QWidget.findChildren(<qt-type>) matches
            # all child widgets with the specified type
            toolbarButtons  = toolbarChildren.findChildren(qt.QToolButton)
            toolbarButtons[3].hide() # LogX
            toolbarButtons[4].hide() # LogY
            toolbarButtons[6].hide() # Simple Fit
            toolbarButtons[7].hide() # Average Plotted Curves
            toolbarButtons[8].hide() # Derivative
            toolbarButtons[9].hide() # Smooth
            toolbarButtons[11].hide() # Set active to zero
            toolbarButtons[12].hide() # Subtract active curve
            toolbarButtons[13].hide() # Save active curve
            toolbarButtons[14].hide() # Plugins
        else:
            self.plotWindow

        self.__savedConf = False
        self.__savedData = False

        # Marker Handling
        # spinboxDict connects marker movement to spinbox
        # keys() -> id(MarkerSpinBox)
        # values() -> MarkerSpinBox
        self.spinboxDict = {}
        self.valuesDict = dict(
                    [(item, {}) for item in self.tabList])

        # Tab Widget
        tabIdx = 0
        self.tabWidget = qt.QTabWidget()
        for window in self.tabList:
            if window == self.__tabElem:
                # BEGIN sampleGB
                sampleGB = qt.QGroupBox('Sample definition')
                sampleLayout = qt.QVBoxLayout()
                sampleGB.setLayout(sampleLayout)

                # electron shell combo box
                self.elementEConfCB = qt.QComboBox()
                self.elementEConfCB.setMinimumWidth(100)
                self.elementEConfCB.addItems(['']+self.electronConfs)
                if hasattr(self.elementEConfCB, "textActivated"):
                    self.elementEConfCB.textActivated['QString'].connect(self.setElectronConf)
                else:           
                    self.elementEConfCB.currentIndexChanged['QString'].connect(self.setElectronConf)
                elementEConfLayout = qt.QHBoxLayout()
                elementEConfLayout.setContentsMargins(0,0,0,0)
                elementEConfLayout.addWidget(qt.QLabel('Electron configuration'))
                elementEConfLayout.addWidget(qt.HorizontalSpacer())
                elementEConfLayout.addWidget(self.elementEConfCB)
                elementEConfWidget = qt.QWidget()
                elementEConfWidget.setLayout(elementEConfLayout)
                sampleLayout.addWidget(elementEConfWidget)
                # Element selection combo box
                self.elementCB = qt.QComboBox()
                self.elementCB.setMinimumWidth(100)
                self.elementCB.addItems([''])
                if hasattr(self.elementCB, "textActivated"):
                    self.elementCB.textActivated['QString'].connect(self.getElementInfo)
                else:
                    self.elementCB.currentIndexChanged['QString'].connect(self.getElementInfo)
                elementLayout = qt.QHBoxLayout()
                elementLayout.setContentsMargins(0,0,0,0)
                elementLayout.addWidget(qt.QLabel('Element'))
                elementLayout.addWidget(qt.HorizontalSpacer())
                elementLayout.addWidget(self.elementCB)
                elementWidget = qt.QWidget()
                elementWidget.setLayout(elementLayout)
                sampleLayout.addWidget(elementWidget)
                # electron occupation number
                self.electronOccupation = qt.QLineEdit('e.g. 3.14')
                self.electronOccupation.setMaximumWidth(120)
                electronOccupationValidator = qt.CLocaleQDoubleValidator(self.electronOccupation)
                electronOccupationValidator.setBottom(0.)
                electronOccupationValidator.setTop(14.)
                self.electronOccupation.setValidator(electronOccupationValidator)
                electronOccupationLayout = qt.QHBoxLayout()
                electronOccupationLayout.setContentsMargins(0,0,0,0)
                electronOccupationLayout.addWidget(qt.QLabel('Electron Occupation Number'))
                electronOccupationLayout.addWidget(qt.HorizontalSpacer())
                electronOccupationLayout.addWidget(self.electronOccupation)
                electronOccupationWidget = qt.QWidget()
                electronOccupationWidget.setLayout(electronOccupationLayout)
                sampleLayout.addWidget(electronOccupationWidget)
                # END sampleGB

                # BEGIN absorptionGB: X-ray absorption edge
                # selection combo box by transition (L3M1, etc.)
                absorptionGB     = qt.QGroupBox('X-ray absorption edges')
                absorptionLayout = qt.QVBoxLayout()
                absorptionGB.setLayout(absorptionLayout)

                self.edge1CB = qt.QComboBox()
                self.edge1CB.setMinimumWidth(100)
                self.edge1CB.addItems([''])
                self.edge1Line = LineEditDisplay(self.edge1CB)
                edge1Layout = qt.QHBoxLayout()
                edge1Layout.setContentsMargins(0,0,0,0)
                edge1Layout.addWidget(qt.QLabel('Edge 1'))
                edge1Layout.addWidget(qt.HorizontalSpacer())
                edge1Layout.addWidget(self.edge1CB)
                edge1Layout.addWidget(self.edge1Line)
                edge1Widget = qt.QWidget()
                edge1Widget.setLayout(edge1Layout)
                absorptionLayout.addWidget(edge1Widget)

                self.edge2CB = qt.QComboBox()
                self.edge2CB.setMinimumWidth(100)
                self.edge2CB.addItems([''])
                self.edge2Line = LineEditDisplay(self.edge2CB)
                edge2Layout = qt.QHBoxLayout()
                edge2Layout.setContentsMargins(0,0,0,0)
                edge2Layout.addWidget(qt.QLabel('Edge 2'))
                edge2Layout.addWidget(qt.HorizontalSpacer())
                edge2Layout.addWidget(self.edge2CB)
                edge2Layout.addWidget(self.edge2Line)
                edge2Widget = qt.QWidget()
                edge2Widget.setLayout(edge2Layout)
                absorptionLayout.addWidget(edge2Widget)
                absorptionLayout.setAlignment(qt.Qt.AlignTop)
                # END absorptionGB

                # Combine sampleGB & absorptionGB in one Line
                topLineLayout = qt.QHBoxLayout()
                topLineLayout.setContentsMargins(0,0,0,0)
                topLineLayout.addWidget(sampleGB)
                topLineLayout.addWidget(absorptionGB)

                topLine = qt.QWidget()
                topLine.setLayout(topLineLayout)

                # BEGIN tab layouting
                elementTabLayout = qt.QVBoxLayout()
                elementTabLayout.setContentsMargins(1,1,1,1)
                elementTabLayout.addWidget(topLine)
                elementTabLayout.addWidget(qt.VerticalSpacer())
                elementTabWidget = qt.QWidget()
                elementTabWidget.setLayout(elementTabLayout)
                self.tabWidget.addTab(
                            elementTabWidget,
                            window.upper())
                self.tabWidget.setTabToolTip(tabIdx,
                        'Shortcut: F2\n'
                       +'Define sample element here')
                # END tab layouting

                self.valuesDict[self.__tabElem]\
                    ['element'] = self.elementCB
                self.valuesDict[self.__tabElem]\
                    ['electron configuration'] = self.elementEConfCB
                self.valuesDict[self.__tabElem]\
                    ['electron occupation'] = self.electronOccupation
                self.valuesDict[self.__tabElem]\
                    ['edge1Transition'] = self.edge1CB
                self.valuesDict[self.__tabElem]\
                    ['edge2Transition'] = self.edge2CB
                self.valuesDict[self.__tabElem]\
                    ['edge1Energy'] = self.edge1Line
                self.valuesDict[self.__tabElem]\
                    ['edge2Energy'] = self.edge2Line
                self.valuesDict[self.__tabElem]['info'] = {}

            elif window == self.__tabBG:
                # BEGIN Pre/Post edge group box
                prePostLayout = qt.QGridLayout()
                prePostLayout.setContentsMargins(1,1,1,1)
                for idx, markerLabel in enumerate(self.xasMarkerList):
                    # Estimate intial xpos by estimateInt
                    markerWidget, spinbox = self.addMarker(window=window,
                                                  label=markerLabel,
                                                  xpos=0.,
                                                  unit='[eV]')
                    self.valuesDict[self.__tabBG][markerLabel] = spinbox
                    if idx == 0:
                        posx, posy = 0,0
                        markerWidget.setContentsMargins(0,0,0,-8)
                    elif idx == 1:
                        posx, posy = 1,0
                        markerWidget.setContentsMargins(0,-8,0,0)
                    elif idx == 2:
                        posx, posy = 0,1
                        markerWidget.setContentsMargins(0,0,0,-8)
                    elif idx == 3:
                        posx, posy = 1,1
                        markerWidget.setContentsMargins(0,-8,0,0)
                    else:
                        raise IndexError('Index out of bounds: %d -> %s'\
                                             %(idx, markerLabel))
                    prePostLayout.addWidget(markerWidget, posx, posy)
                prePostGB = qt.QGroupBox('Pre/Post edge')
                prePostGB.setLayout(prePostLayout)
                # END Pre/Post edge group box

                # BEGIN Edge group box
                numberOfEdges = 2
                edgeLayout = qt.QVBoxLayout()
                edgeLayout.setContentsMargins(1,1,1,1)
                for idx in range(numberOfEdges):
                    markerLabel = 'Edge %d'%(idx+1)
                    self.edgeMarkerList += [markerLabel]
                    markerWidget, spinbox = self.addMarker(window=window,
                                                  label=markerLabel,
                                                  xpos=0.,
                                                  unit='[eV]')
                    self.valuesDict[self.__tabBG][markerLabel] = spinbox
                    if idx == 0:
                        markerWidget.setContentsMargins(0,0,0,-8)
                    elif idx == (numberOfEdges-1):
                        markerWidget.setContentsMargins(0,-8,0,0)
                    else:
                        markerWidget.setContentsMargins(0,-8,0,-8)
                    edgeLayout.addWidget(markerWidget)
                    markerWidget.setEnabled(False)
                edgeGB = qt.QGroupBox('Edge positions')
                edgeGB.setLayout(edgeLayout)
                # END Edge group box

                # BEGIN Background model group box
                stepRatio = qt.QDoubleSpinBox()
                stepRatio.setMaximumWidth(100)
                stepRatio.setAlignment(qt.Qt.AlignRight)
                stepRatio.setMinimum(0.)
                stepRatio.setMaximum(1.)
                stepRatio.setSingleStep(.025)
                stepRatio.setValue(.5)
                stepRatioLayout = qt.QHBoxLayout()
                stepRatioLayout.addWidget(qt.QLabel('Step ratio'))
                stepRatioLayout.addWidget(qt.HorizontalSpacer())
                stepRatioLayout.addWidget(stepRatio)
                stepRatioWidget = qt.QWidget()
                stepRatioWidget.setContentsMargins(0,0,0,-8)
                stepRatioWidget.setLayout(stepRatioLayout)

                stepWidth = qt.QDoubleSpinBox()
                stepWidth.setMaximumWidth(100)
                stepWidth.setAlignment(qt.Qt.AlignRight)
                stepWidth.setMinimum(0.)
                stepWidth.setMaximum(1000.)
                stepWidth.setSingleStep(0.05)
                stepWidth.setValue(.0) # Start with step function
                stepWidthLayout = qt.QHBoxLayout()
                stepWidthLayout.addWidget(qt.QLabel('Step width [eV]'))
                stepWidthLayout.addWidget(qt.HorizontalSpacer())
                stepWidthLayout.addWidget(stepWidth)
                stepWidthWidget = qt.QWidget()
                stepWidthWidget.setContentsMargins(0,-8,0,0)
                stepWidthWidget.setLayout(stepWidthLayout)

                fitControlLayout = qt.QVBoxLayout()
                fitControlLayout.addWidget(stepRatioWidget)
                fitControlLayout.addWidget(stepWidthWidget)
                fitControlGB = qt.QGroupBox('Background model control')
                fitControlGB.setLayout(fitControlLayout)
                # END Background model group box

                # Combine edge position and background model in single line
                sndLine = qt.QWidget()
                sndLineLayout = qt.QHBoxLayout()
                sndLineLayout.setContentsMargins(1,1,1,1)
                sndLine.setLayout(sndLineLayout)
                sndLineLayout.addWidget(edgeGB)
                sndLineLayout.addWidget(fitControlGB)

                # Insert into tab
                backgroundTabLayout = qt.QVBoxLayout()
                backgroundTabLayout.setContentsMargins(1,1,1,1)
                backgroundTabLayout.addWidget(prePostGB)
                backgroundTabLayout.addWidget(sndLine)
                backgroundTabLayout.addWidget(qt.VerticalSpacer())
                backgroundWidget = qt.QWidget()
                backgroundWidget.setLayout(backgroundTabLayout)
                self.tabWidget.addTab(
                            backgroundWidget,
                            window.upper())
                self.tabWidget.setTabToolTip(tabIdx,
                        'Shortcut: F3\n'
                       +'Model background here.')

                stepRatio.valueChanged['double'].connect(self.estimateBG)
                stepWidth.valueChanged['double'].connect(self.estimateBG)

                self.valuesDict[self.__tabBG]\
                        ['Step Ratio'] = stepRatio
                self.valuesDict[self.__tabBG]\
                        ['Step Width'] = stepWidth

            elif window == self.__tabInt:
                # BEGIN Integral marker groupbox
                pqLayout = qt.QVBoxLayout()
                pqLayout.setContentsMargins(0,-8,0,-8)
                for markerLabel in self.xmcdMarkerList:
                    markerWidget, spinbox = self.addMarker(window=window,
                                                  label=markerLabel,
                                                  xpos=0.,
                                                  unit='[eV]')
                    self.valuesDict[self.__tabInt][markerLabel] = spinbox
                    if markerLabel == self.xmcdMarkerList[0]:
                        markerWidget.setContentsMargins(0,0,0,-8)
                    elif markerLabel == self.xmcdMarkerList[-1]:
                        # Last widget gets more content margin
                        # at the bottom
                        markerWidget.setContentsMargins(0,-8,0,0)
                    else:
                        markerWidget.setContentsMargins(0,-8,0,-8)
                    integralVal = qt.QLineEdit()
                    integralVal.setReadOnly(True)
                    integralVal.setMaximumWidth(120)
                    valLabel = qt.QLabel('Integral Value:')
                    mwLayout = markerWidget.layout()
                    mwLayout.addWidget(valLabel)
                    mwLayout.addWidget(integralVal)
                    pqLayout.addWidget(markerWidget)
                    #spinbox.valueChanged.connect(self.calcMagneticMoments)
                    spinbox.intersectionsChangedSignal.connect(self.calcMagneticMoments)
                    key = 'Integral ' + markerLabel
                    self.valuesDict[self.__tabInt][key] = integralVal
                pqGB = qt.QGroupBox('XAS/XMCD integrals')
                pqGB.setLayout(pqLayout)
                # END Integral marker groupbox

                # BEGIN magnetic moments groupbox
                mmLayout = qt.QVBoxLayout()
                mmLayout.setContentsMargins(0,-8,0,-8)

                text = 'Spin Magnetic Moment'
                mmLineLayout = qt.QHBoxLayout()
                self.mmSpin = qt.QLineEdit()
                self.mmSpin.setReadOnly(True)
                self.mmSpin.setMaximumWidth(120)
                mmLineLayout.addWidget(qt.QLabel(text))
                mmLineLayout.addWidget(qt.HorizontalSpacer())
                mmLineLayout.addWidget(qt.QLabel('mS = '))
                mmLineLayout.addWidget(self.mmSpin)
                mmLineWidget = qt.QWidget()
                mmLineWidget.setLayout(mmLineLayout)
                mmLineWidget.setContentsMargins(0,0,0,-8)
                mmLayout.addWidget(mmLineWidget)

                text = 'Orbital Magnetic Moment'
                mmLineLayout = qt.QHBoxLayout()
                self.mmOrbt = qt.QLineEdit()
                self.mmOrbt.setReadOnly(True)
                self.mmOrbt.setMaximumWidth(120)
                mmLineLayout.addWidget(qt.QLabel(text))
                mmLineLayout.addWidget(qt.HorizontalSpacer())
                mmLineLayout.addWidget(qt.QLabel('mO = '))
                mmLineLayout.addWidget(self.mmOrbt)
                mmLineWidget = qt.QWidget()
                mmLineWidget.setLayout(mmLineLayout)
                mmLineWidget.setContentsMargins(0,-8,0,-8)
                mmLayout.addWidget(mmLineWidget)

                text = 'Ratio Magnetic Moments'
                mmLineLayout = qt.QHBoxLayout()
                self.mmRatio = qt.QLineEdit()
                self.mmRatio.setReadOnly(True)
                self.mmRatio.setMaximumWidth(120)
                mmLineLayout.addWidget(qt.QLabel(text))
                mmLineLayout.addWidget(qt.HorizontalSpacer())
                mmLineLayout.addWidget(qt.QLabel('mO/mS = '))
                mmLineLayout.addWidget(self.mmRatio)
                mmLineWidget = qt.QWidget()
                mmLineWidget.setLayout(mmLineLayout)
                mmLineWidget.setContentsMargins(0,-8,0,0)
                mmLayout.addWidget(mmLineWidget)

                mmGB = qt.QGroupBox('Magnetic moments')
                mmGB.setLayout(mmLayout)
                # END magnetic moments groupbox

                # Combine Integral marker groupbox and
                # magnetic moments groupbox in single line
                topLineLayout = qt.QHBoxLayout()
                topLineLayout.setContentsMargins(0,0,0,0)
                topLineLayout.addWidget(pqGB)
                topLineLayout.addWidget(mmGB)
                topLine = qt.QWidget()
                topLine.setLayout(topLineLayout)

                # BEGIN XMCD correction
                self.xmcdDetrend = qt.QCheckBox()
                self.xmcdDetrend.stateChanged['int'].connect(self.triggerDetrend)
                xmcdDetrendLayout = qt.QHBoxLayout()
                #xmcdDetrendLayout.setContentsMargins(0,0,0,1)
                xmcdDetrendLayout.addWidget(qt.QLabel(
                        'Detrend XMCD Signal (Subtracts linear fit of pre-edge Region from the signal)'))
                xmcdDetrendLayout.addWidget(qt.HorizontalSpacer())
                xmcdDetrendLayout.addWidget(self.xmcdDetrend)
                xmcdDetrendWidget = qt.QWidget()
                xmcdDetrendWidget.setLayout(xmcdDetrendLayout)

                xmcdDetrendGB = qt.QGroupBox('XMCD Data Preprocessing')
                xmcdDetrendGB.setLayout(xmcdDetrendLayout)
                xmcdDetrendLayout.addWidget(xmcdDetrendWidget)
                # END XMCD correction

                xmcdTabLayout = qt.QVBoxLayout()
                xmcdTabLayout.setContentsMargins(2,2,2,2)
                xmcdTabLayout.addWidget(topLine)
                xmcdTabLayout.addWidget(xmcdDetrendGB)
                xmcdTabLayout.addWidget(qt.VerticalSpacer())
                xmcdWidget = qt.QWidget()
                xmcdWidget.setLayout(xmcdTabLayout)
                self.tabWidget.addTab(
                            xmcdWidget,
                            window.upper())
                self.tabWidget.setTabToolTip(tabIdx,
                        'Shortcut: F4\n'
                       +'Assign Markers p, q and r here')

                self.valuesDict[self.__tabInt]\
                    ['Orbital Magnetic Moment'] = self.mmOrbt
                self.valuesDict[self.__tabInt]\
                    ['Spin Magnetic Moment'] = self.mmSpin
                self.valuesDict[self.__tabInt]\
                    ['Ratio Magnetic Moments'] = self.mmRatio
                self.valuesDict[self.__tabInt]\
                    ['XMCD Detrend'] = self.xmcdDetrend
            tabIdx += 1
        # END TabWidget
        # Add to self.valuesDict
        self.tabWidget.currentChanged['int'].connect(
                            self._handleTabChangedSignal)

        # Estimate button in bottom of plot window layout
        self.buttonEstimate = qt.QPushButton('Estimate', self)
        self.buttonEstimate.setToolTip(
            'Shortcut: CRTL+E\n'
           +'Depending on the tab, estimate either the pre/post\n'
           +'edge regions and edge positions or the positions of\n'
           +'the p, q and r markers.')
        self.buttonEstimate.setShortcut(\
                    qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_E))
        self.buttonEstimate.clicked.connect(self.estimate)
        self.buttonEstimate.setEnabled(False)
        self.plotWindow.toolBar.addSeparator()
        self.plotWindow.toolBar.addWidget(self.buttonEstimate)

        self.plotWindow.sigPlotSignal.connect(self._handlePlotSignal)

        # Layout
        mainWidget = qt.QWidget()
        mainLayout = qt.QVBoxLayout()
        mainLayout.addWidget(self.plotWindow)
        mainLayout.addWidget(self.tabWidget)
        mainLayout.setContentsMargins(1,1,1,1)
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)

        #
        # Data handling:
        #
        # Each is Tuple (x,y)
        # type(x),type(y) == ndarray
        self.xmcdData     = None # XMCD Spectrum
        self.xasData      = None # XAS Spectrum
        self.xasDataCorr  = None # XAS minus Background model
        self.xasDataBG    = None # XAS Backgrouns
        self.xmcdCorrData = None
        # Integrated spectra: Notice that the shape
        # diminished by one..
        self.xmcdInt     = None
        self.xasInt      = None

        #
        # File (name) handling
        #
        self.dataInputFilename = None
        self.confFilename      = None
        self.baseFilename      = None

        self._createMenuBar()

    def _createMenuBar(self):
        # Creates empty menu bar, if none existed before
        menu = self.menuBar()
        menu.clear()

        #
        # 'File' Menu
        #
        ffile = menu.addMenu('&File')

        openAction = qt.QAction('&Open Spec File', self)
        openAction.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_O))
        openAction.setStatusTip('Opened file')
        openAction.setToolTip('Opens a data file (*.spec)')
        openAction.triggered.connect(self.loadData)

        loadAction = qt.QAction('&Load Configuration', self)
        loadAction.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_L))
        loadAction.setStatusTip('Loaded analysis file')
        loadAction.setToolTip('Loads an existing analysis file (*.sra)')
        loadAction.triggered.connect(self.loadConfiguration)

        saveConfAction = qt.QAction('&Save Configuration', self)
        saveConfAction.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_S))
        saveConfAction.setStatusTip('Saved analysis file')
        saveConfAction.setToolTip('Save analysis in file (*.sra)')
        saveConfAction.triggered.connect(self.saveConfiguration)

        saveConfAsAction = qt.QAction('Save &Configuration as', self)
        saveConfAsAction.setShortcut(\
                    qt.QKeySequence(qt.Qt.SHIFT|qt.Qt.CTRL|qt.Qt.Key_S))
        saveConfAsAction.setStatusTip('Saved analysis file')
        saveConfAsAction.setToolTip('Save analysis in file (*.sra)')
        saveConfAsAction.triggered.connect(self.saveConfigurationAs)

        saveDataAction = qt.QAction('Save &Data', self)
        saveDataAction.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_D))
        saveDataAction.setStatusTip('Saved analysis file')
        saveDataAction.setToolTip('Save analysis in file (*.sra)')
        saveDataAction.triggered.connect(self.saveData)

        saveDataAsAction = qt.QAction('Save D&ata as', self)
        saveDataAsAction.setShortcut(\
                    qt.QKeySequence(qt.Qt.SHIFT|qt.Qt.CTRL|qt.Qt.Key_D))
        saveDataAsAction.setStatusTip('Saved analysis file')
        saveDataAsAction.setToolTip('Save analysis in file (*.sra)')
        saveDataAsAction.triggered.connect(self.saveDataAs)

        # Populate the 'File' menu
        for action in [openAction,
                       loadAction,
                       'sep',
                       saveConfAction,
                       saveConfAsAction,
                       'sep',
                       saveDataAction,
                       saveDataAsAction,
                       'sep']:
            if isinstance(action, qt.QAction):
                ffile.addAction(action)
            else:
                ffile.addSeparator()
        ffile.addAction('E&xit', self.close)

        #
        # 'Help' Menu
        #
        hhelp = menu.addMenu('&Help')

        showHelpFileAction = qt.QAction('Show &documentation', self)
        showHelpFileAction.setShortcut(qt.QKeySequence(qt.Qt.Key_F1))
        showHelpFileAction.setStatusTip('')
        showHelpFileAction.setToolTip('Opens the documentation (html-file) in the systems native web browser')
        showHelpFileAction.triggered.connect(self.showInfoWindow)

        # Populate the 'Help' menu
        hhelp.addAction(showHelpFileAction)


    def showInfoWindow(self):
        """
        Opens a web browser and displays the help file
        """
        fileName = osPathJoin(PyMcaDataDir.PYMCA_DOC_DIR,
                                          "HTML",
                                          "SumRulesToolInfotext.html")
        helpFileName = qt.QDir(fileName)
        if not qt.QDesktopServices.openUrl(qt.QUrl(helpFileName.absolutePath())):
            os.system('"%s"' % fileName)

    def triggerDetrend(self, state):
        if (state == qt.Qt.Unchecked) or\
           (state == qt.Qt.PartiallyChecked):
            # Replot original data
            self.xmcdCorrData = None
        else:
            ddict = self.getValuesDict()
            if self.xmcdData is None:
                return
            x, y  = self.xmcdData
            preMin = ddict[self.__tabBG][self.__preMin]
            preMax = ddict[self.__tabBG][self.__preMax]

            mask = numpy.nonzero((preMin <= x) & (x <= preMax))[0]
            xFit = x.take(mask)
            yFit = y.take(mask)

            if (len(xFit) == 0) or (len(yFit) == 0):
                return

            # Fit linear model y = a*x + b
            a, b = numpy.polyfit(xFit, yFit, 1)
            trend = a*x + b
            self.xmcdCorrData = (x, y-trend)
        if self.getCurrentTab() == self.__tabInt:
            self.plotOnDemand(self.__tabInt)
            self.calcMagneticMoments()

    def calcMagneticMoments(self):
        ddict = self.valuesDict
        pqr = []
        mathObj = Calculations()
        for marker in self.xmcdMarkerList:
            if marker in [self.__intP, self.__intQ]:
                if self.xmcdCorrData is not None:
                    curve = 'xmcd corr Int'
                else:
                    curve = 'xmcd Int'
            else:
                curve = 'xas Int'
            spinbox = ddict[self.__tabInt][marker]
            integralVals = spinbox.getIntersections()
            x, y = integralVals.get(curve, (float('NaN'),float('NaN')))
            key = 'Integral ' + marker
            lineEdit = ddict[self.__tabInt][key]
            lineEdit.setText(str(y))
            pqr += [y]
        p, q, r = pqr
        electronOccupation = ddict[self.__tabElem]['electron occupation']
        try:
            n = float(electronOccupation.text())
        except ValueError:
            _logger.debug('calcMM -- Could not convert electron occupation')
            return
        electronConfiguration = ddict[self.__tabElem]['electron configuration']
        econf = str(electronConfiguration.currentText())
        try:
            mmO, mmS, mmR = mathObj.magneticMoment(p,q,r,n,econf)
        except ValueError as e:
            _logger.debug(e)
            mmO, mmS, mmR = 3*['---']
        self.mmOrbt.setText(str(mmO))
        self.mmSpin.setText(str(mmS))
        self.mmRatio.setText(str(mmR))

    def loadData(self):
        dial = LoadDichorismDataDialog()
        dial.setDirectory(PyMcaDirs.outputDir)
        if dial.exec():
            dataDict = dial.dataDict
        else:
            return

        # Reset calculated data
        self.xasDataCorr  = None
        self.xasDataBG    = None
        self.xmcdCorrData = None
        self.xmcdInt      = None
        self.xasInt       = None

        x = dataDict['x']
        xas = dataDict['xas']
        xmcd = dataDict['xmcd']
        self.dataInputFilename = dataDict['fn']
        self.setRawData(x, xas, 'xas')
        self.setRawData(x, xmcd, 'xmcd')

    def saveDataAs(self):
        self.baseFilename = None
        self.__savedData  = False
        self.saveData()

    def saveData(self):
        # Saves spectral data that is calculated during
        # the evaluation process:
        # First scan: XAS BG-Modell XAS-BG
        # Second scan: XAS/XMCD integrals
        dataList = [self.xasData,
                    self.xasDataCorr,
                    self.xasDataBG,
                    self.xmcdInt,
                    self.xasInt]
        if None in dataList:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Analysis Error')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('Analysis incomplete!\nCannot save generated data')
            msg.exec()
            return False

        if self.__savedData and self.baseFilename:
            pass
        else:
            ddict    = self.getValuesDict()
            saveDir  = PyMcaDirs.outputDir
            filters  = 'spec File (*.spec);;All files (*.*)'
            baseFilename = qt.QFileDialog.getSaveFileName(self,
                                   'Save Sum Rule Analysis Data',
                                   saveDir,
                                   filters)
            if len(baseFilename) == 0:
                # Leave self.baseFilename as it is..
                #self.baseFilename = None
                return False
            else:
                self.baseFilename = str(baseFilename)
            if not self.baseFilename.endswith('.spec'):
                # Append extension later
                self.baseFilename += '.spec'

        # Create filenames
        specFilename = self.baseFilename
        baseName = osPathBasename(self.dataInputFilename)

        self.__savedData = False

        # Acquire filehandle
        try:
            specFilehandle = open(specFilename, 'wb')
        except IOError:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Analysis Error')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('Unable to open file \'%s\''%specFilename)
            msg.exec()
            return False

        delim   = ' '

        # 1. Background Modell, XAS, XAS-Background
        # All share the same x-range
        xSpec, yXas   = self.xasData
        xSpec, yBG    = self.xasDataBG
        xSpec, yXasBG = self.xasDataCorr
        if self.xmcdCorrData:
            xInt, yXmcd = self.xmcdCorrData
        else:
            xInt, yXmcd = self.xmcdData
        dataSpec = numpy.vstack((xSpec, yXas, yBG, yXasBG, yXmcd)).T

        # 2. Integrals
        # Also share the same x-range
        xInt, yXasInt  = self.xasInt
        xInt, yXmcdInt = self.xmcdInt
        dataInt = numpy.vstack((xInt, yXasInt, yXmcdInt)).T

        # Construct spectra output
        outSpec = ''
        outSpec += (NEWLINE + '#S 1 XAS data %s'%baseName + NEWLINE)
        outSpec += ('#N %d'%5 + NEWLINE)
        if self.xmcdCorrData:
            outSpec += ('#L x  XAS  Background model  XAS corrected  XMCD corrected' + NEWLINE)
        else:
            outSpec += ('#L x  XAS  Background model  XAS corrected  XMCD' + NEWLINE)
        for line in dataSpec:
            tmp = delim.join(['%f'%num for num in line])
            outSpec += (tmp + NEWLINE)
        outSpec += (NEWLINE)

        # Construct integral output
        outInt = ''
        outInt += ('#S 2 Integral data %s'%baseName + NEWLINE)
        outInt += ('#N %d'%3 + NEWLINE)
        if self.xmcdCorrData:
            outInt += ('#L x  XAS Int  XMCD Int' + NEWLINE)
        else:
            outInt += ('#L x  XAS Int  XMCD Int corrected' + NEWLINE)
        for line in dataInt:
            tmp = delim.join(['%f'%num for num in line])
            outInt += (tmp + NEWLINE)
        outInt += (NEWLINE)

        for output in [outSpec, outInt]:
            specFilehandle.write(output.encode('ascii'))
        specFilehandle.close()

        self.__savedData = True
        return True

    def saveConfigurationAs(self, shortcut=False):
        self.confFilename = None
        self.__savedConf  = False
        self.saveConfiguration()

    def saveConfiguration(self):
        ddict    = self.getValuesDict()

        if self.__savedConf and self.confFilename:
            filename = self.confFilename
        else:
            saveDir  = PyMcaDirs.outputDir
            filters   = 'Sum Rules Analysis files (*.sra);;All files (*.*)'

            filename = qt.QFileDialog.getSaveFileName(self,
                                   'Save Sum Rule Analysis Configuration',
                                   saveDir,
                                   filters)
            if len(filename) == 0:
                return False
            else:
                filename = str(filename)
            if not filename.endswith('.sra'):
                filename += '.sra'
            self.confFilename = filename

        self.__savedConf = False
        confDict = ConfigDict.ConfigDict(self.getValuesDict())
        try:
            confDict.write(filename)
        except IOError:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Analysis Error')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('Unable to write configuration to \'%s\''%filename)
            msg.exec()
            return False
        self.__savedConf = True
        return True

    def loadConfiguration(self):
        confDict = ConfigDict.ConfigDict()
        loadDir  = PyMcaDirs.outputDir
        filters   = 'Sum Rules Analysis files (*.sra);;All files (*.*)'

        filename = qt.QFileDialog.getOpenFileName(self,
                               'Load Sum Rule Analysis Configuration',
                               loadDir,
                               filters)

        if type(filename) in [type(list()), type(tuple())]:
            if len(filename):
                filename = filename[0]

        if len(filename) == 0:
            return
        else:
            filename = str(filename)
        try:
            confDict.read(filename)
        except IOError:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Analysis Error')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('Unable to read configuration file \'%s\''%filename)
            return
        try:
            self.setValuesDict(confDict)
            #keysLoaded = confDict.keys()
            #keysValues = self.valuesDict.keys()
        except KeyError as e:
            _logger.debug('loadConfiguration -- Key Error in \'%s\'', filename)
            _logger.debug('\tMessage: %s', e)

            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Analysis Error')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('Malformed configuration file \'%s\''%filename)
            return
        self.__savedConf = True


    def close(self):
        if not self.__savedConf:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Sum Rules Tool')
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText('The configuration has changed!\nAre you shure you want to close the window?')
            msg.setStandardButtons(qt.QMessageBox.Cancel | qt.QMessageBox.Discard)
            if msg.exec() == qt.QMessageBox.Cancel:
                return
        qt.QMainWindow.close(self)

    def setElectronConf(self, eConf):
        eConf = str(eConf)
        if len(eConf) == 0:
            self.electronOccupation.setDisabled(True)
        else:
            self.electronOccupation.setDisabled(False)
        # updates the element combo box
        self.elementCB.clear()
        elementsList = self.elementsDict[eConf]
        self.elementCB.addItems(['']+elementsList)

    def getElementInfo(self, symbol):
        ddict = {}
        symbol = str(symbol)
        if len(symbol) == 0:
            self.valuesDict[self.__tabElem]['info'] = {}
            return
        try:
            ddict = Elements.Element[symbol]
        except KeyError:
            msg  = ('setElement -- \'%s\' not found in '%symbol)
            msg += 'Elements.Element dictionary'
            _logger.error(msg)
        # Update valuesDict
        self.valuesDict[self.__tabElem]['info'] = ddict
        # Update the EdgeCBs
        # Lookup all keys ending in 'xrays'
        keys = [item for item in ddict.keys() if item.endswith('xrays')]
        keys.sort()
        # keys is list of list, flatten it..
        transitions = sum([ddict[key] for key in keys],[])
        # Only take transitions that occur in the experiment
        transitions = [t for t in transitions if t in self.occuringTransitions]
        tmpDict = dict( [(transition, ddict[transition]['energy']) for transition in transitions])
        for cb, ed in [(self.edge1CB, self.edge1Line),
                       (self.edge2CB, self.edge2Line)]:
            curr = cb.currentText()
            cb.clear()
            ed.clear()
            ed.updateDict(tmpDict)
            cb.addItems(['']+transitions)
            # Try to set to old entry
            idx = cb.findText(QString(curr))
            if idx < 0: idx = 0
            cb.setCurrentIndex(idx)

    def getCurrentTab(self):
        idx = self.tabWidget.currentIndex()
        return self.tabList[idx]

    def getValuesDict(self):
        ddict = {}
        for tab, tabDict in self.valuesDict.items():
            if tab not in ddict.keys():
                ddict[tab] = {}
            for key, obj in tabDict.items():
                value = None
                if isinstance(obj, MarkerSpinBox):
                    value = obj.value()
                elif isinstance(obj, qt.QCheckBox):
                    state = obj.checkState()
                    if state == qt.Qt.Checked:
                        value = True
                    else:
                        # Also covers state == qt.Qt.PartiallyChecked
                        value = False
                elif isinstance(obj, qt.QComboBox):
                    tmp = obj.currentText()
                    value = str(tmp)
                elif isinstance(obj, LineEditDisplay) or\
                     isinstance(obj, qt.QLineEdit):
                    tmp = str(obj.text())
                    try:
                        value = float(tmp)
                    except ValueError:
                        value = tmp
                elif isinstance(obj, qt.QDoubleSpinBox):
                    value = obj.value()
                elif isinstance(obj, dict):
                    value = obj
                ddict[tab][key] = value
        return ddict

    def setValuesDict(self, ddict):
        markerList  = (self.xasMarkerList + self.xmcdMarkerList)
        elementList = (self.transitionMetals
                       + self.rareEarths
                       + self.electronConfs)
        # Check as early as possible if element symbol is present
        try:
            symbol = ddict[self.__tabElem]['element']
            self.getElementInfo(symbol)
        except KeyError:
            pass
        for tab, tabDict in ddict.items():
            if tab not in self.valuesDict.keys():
                raise KeyError('setValuesDict -- Tab not found')
            for key, value in tabDict.items():
                if not isinstance(key, str):
                    raise KeyError('setValuesDict -- Key is not str instance')
                obj = self.valuesDict[tab][key]
                if isinstance(obj, MarkerSpinBox):
                    try:
                        tmp = float(value)
                        obj.setValue(tmp)
                    except ValueError:
                        if hasattr(self.plotWindow,'graph'):
                            xmin, xmax = self.plotWindow.graph.getX1AxisLimits()
                        else:
                            xmin, xmax = self.plotWindow.getGraphXLimits()
                        tmp = xmin + (xmax-xmin)/10.
                        _logger.debug(
                                'setValuesDict -- Float conversion failed'
                                ' while setting marker positions. Value: %s',
                                value)
                elif isinstance(obj, qt.QCheckBox):
                    if value == 'True':
                        state = qt.Qt.Checked
                    else:
                        state = qt.Qt.Unchecked
                    obj.setCheckState(state)
                elif isinstance(obj, qt.QDoubleSpinBox):
                    try:
                        tmp = float(value)
                        obj.setValue(tmp)
                    except ValueError:
                        _logger.debug(
                                'setValuesDict -- Float conversion failed'
                                ' while setting QDoubleSpinBox value. Value: %s',
                                value)
                elif isinstance(obj, qt.QComboBox):
                    idx = obj.findText(QString(value))
                    obj.setCurrentIndex(idx)
                elif isinstance(obj, LineEditDisplay):
                    # Must be before isinstance(obj, qt.QLineEdit)
                    # since LineEditDisplay inherits from QLineEdit
                    obj.checkController()
                elif isinstance(obj, qt.QLineEdit):
                    if value:
                        tmp = str(value)
                        obj.setText(tmp)
                    else:
                        obj.setText('???')
                elif isinstance(obj, dict):
                    obj = value
                else:
                    raise KeyError('setValuesDict -- \'%s\' not found'%key)
        # In case electron shell is set after element..
        try:
            symbol = ddict[self.__tabElem]['element']
            cb = self.valuesDict[self.__tabElem]['element']
            idx = cb.findText(QString(symbol))
            cb.setCurrentIndex(idx)
        except KeyError:
            pass

    def setRawData(self, x, y, identifier):
        if identifier not in ['xmcd', 'xas']:
            msg  = 'Identifier must either be \'xmcd\' or \'xas\''
            raise ValueError(msg)
        # Sort energy range
        sortedIdx = x.argsort()
        xSorted = x.take(sortedIdx)[:]
        ySorted = y.take(sortedIdx)[:]
        # Ensure strictly monotonically increasing energy range
        dx = numpy.diff(x)
        if not numpy.all(dx > 0.):
            mask = numpy.nonzero(dx)
            xSorted = numpy.take(xSorted, mask)
            ySorted = numpy.take(ySorted, mask)
        # Add spectrum to plotWindow using the
        if identifier == 'xmcd':
            self.xmcdData = (xSorted, ySorted)
            #self.plotWindow.graph.mapToY2(intLegend)
        elif identifier == 'xas':
            self.xasData  = (xSorted, ySorted)
        # Trigger replot when data is added
        currIdx = self.tabWidget.currentIndex()
        self._handleTabChangedSignal(currIdx)

    def estimate(self):
        tab = self.getCurrentTab()
        if tab == self.__tabBG:
            self.estimatePrePostEdgePositions()
        elif tab == self.__tabInt:
            self.estimateInt()
        else:
            # Do nothing
            pass
        return

    def estimatePrePostEdgePositions(self):
        if self.xasData is None:
            return

        ddict = self.getValuesDict()
        edgeList = [ddict[self.__tabElem]['edge1Energy'],
                    ddict[self.__tabElem]['edge2Energy']]
        filterEdgeList = lambda inp:\
                            float(inp.replace('meV',''))\
                            if (len(inp)>0 and inp!='---')\
                            else 0.0
        # Use list comprehension instead of map(filterEdgeList, edgeList)
        edgeList = [filterEdgeList(edge) for edge in edgeList]
        x, y = self.xasData
        xLimMin, xLimMax = self.plotWindow.getGraphXLimits()

        xMin = x[0]
        xMax = x[-1]
        xLen = xMax - xMin
        xMiddle = .5 *(xMax + xMin)
        # Average step length (Watch out for uneven data!)
        xStep = (xMax + xMin) / float(len(x))
        # Look for the index closest to the physical middle
        mask = numpy.nonzero(x <= xMiddle)[0]
        idxMid = mask[-1]

        factor = 10./100.
        edge1, edge2 = edgeList
        if edge1 == 0.:
            edge1 = xMin + 0.4 * (xMax - xMin)
        if edge2 == 0.:
            edge2 = xMin + 0.6 * (xMax - xMin)

        maxEdge = max(edge1, edge2)
        minEdge = min(edge1, edge2)
        preMax  = minEdge - factor*xLen
        postMin = maxEdge + factor*xLen

        ddict[self.__tabBG][self.__preMin]  = max(xMin,xLimMin+xStep)
        ddict[self.__tabBG][self.__preMax]  = preMax
        ddict[self.__tabBG][self.__postMin] = postMin
        ddict[self.__tabBG][self.__postMax] = min(xMax,xLimMax-xStep)
        ddict[self.__tabBG]['Edge 1'] = edge1
        ddict[self.__tabBG]['Edge 2'] = edge2

        self.setValuesDict(ddict)
        self.estimateBG()

    def estimateInt(self):
        if self.xasDataCorr is None or\
           self.xasInt      is None or\
           self.xmcdInt     is None:
            # Nothing to do...
            return
        ddict = self.getValuesDict()

        x, y = self.xasData
        xMin = x[0]
        xMax = x[-1]
        xLen = xMax - xMin

        factor = 10./100.
        postMin = ddict[self.__tabBG][self.__postMin]
        postMax = ddict[self.__tabBG][self.__postMax]
        edge1 = ddict[self.__tabBG]['Edge 1']
        edge2 = ddict[self.__tabBG]['Edge 2']

        # Estimate intP
        if edge1 == 0.:
            intP = edge2 + factor * xLen
        elif edge2 == 0.:
            intP = edge1 + factor * xLen
        else:
            intP = min(edge1, edge2) + factor * xLen

        # Estimate intQ
        intQ = postMin + factor * xLen

        # Estimate intR
        intR = postMax - factor * xLen

        # Also estimate the p, q, r Markers:
        ddict[self.__tabInt][self.__intP] = intP
        ddict[self.__tabInt][self.__intQ] = intQ
        ddict[self.__tabInt][self.__intR] = intR

        self.setValuesDict(ddict)

    def estimateBG(self): # Removed default parameter val=None
        if self.xasData is None:
            return
        if self.tabWidget.currentIndex() != 1:
            # Only call from tab 1
            return

        x, y = self.xasData
        ddict = self.getValuesDict()
        x01 = ddict[self.__tabBG]['Edge 1']
        x02 = ddict[self.__tabBG]['Edge 2']
        preMin  = ddict[self.__tabBG][self.__preMin]
        preMax  = ddict[self.__tabBG][self.__preMax]
        postMin = ddict[self.__tabBG][self.__postMin]
        postMax = ddict[self.__tabBG][self.__postMax]
        width = ddict[self.__tabBG]['Step Width']
        ratio = ddict[self.__tabBG]['Step Ratio']

        if preMin > preMax:
            tmp = preMin
            preMin = preMax
            preMax = tmp
        if postMin > postMax:
            tmp = preMin
            preMin = preMax
            preMax = tmp

        idxPre  = numpy.nonzero((preMin <= x) & (x <= preMax))[0]
        idxPost = numpy.nonzero((postMin <= x) & (x <= postMax))[0]

        if (len(idxPre) == 0) or (len(idxPost) == 0):
            _logger.debug('estimateBG -- Somethings wrong with pre/post edge markers')
            return

        xPreMin  = x[idxPre.min()]
        xPreMax  = x[idxPre.max()]
        xPostMin = x[idxPost.min()]
        xPostMax = x[idxPost.max()]
        gap = abs(xPreMax - xPostMin)

        avgPre  = numpy.average(y[idxPre])
        avgPost = numpy.average(y[idxPost])
        bottom  = min(avgPre,avgPost)
        top     = max(avgPre,avgPost)
        if avgPost >= avgPre:
            sign = 1.
            erf  = upstep
        else:
            sign = -1.
            erf  = downstep
        diff = abs(avgPost - avgPre)

        if x02 < x01:
            par1 = (ratio, x02, width)
            par2 = ((1.-ratio), x01, width)
            _logger.debug('estimateBG -- x02 < x01, using par1: %s and par2: %s',
                          par1, par2)
            model = bottom + sign * diff * (erf(par1, x) + erf(par2, x))
        else:
            par1 = (ratio, x01, width)
            par2 = ((1.-ratio), x02, width)

            _logger.debug('estimateBG -- x01 < x02, using par1: %s and par2: %s',
                          par1, par2)
            model = bottom + sign * diff * (erf(par1, x) + erf(par2, x))

        preModel  = numpy.asarray(len(x)*[avgPre])
        postModel = numpy.asarray(len(x)*[avgPost])

        self.xasDataBG = x, model

        self.plotWindow.addCurve(x,
                                 model,
                                 self.__xasBGmodel,
                                 {},
                                 replot=False)
        self.plotWindow.addCurve(x,
                                 preModel,
                                 'Pre BG model',
                                 {},
                                 replot=False)
        self.plotWindow.addCurve(x,
                                 postModel,
                                 'Post BG model',
                                 {},
                                 replot=False)
        if hasattr(self.plotWindow, 'graph'):
            self.plotWindow.graph.replot()
        else:
            self.plotWindow.replot()
            self.plotWindow.updateLegends()

    def plotOnDemand(self, window):
        # Remove all curves
        if hasattr(self.plotWindow,'graph'):
            legends = self.plotWindow.getAllCurves(just_legend=True)
            for legend in legends:
                self.plotWindow.removeCurve(legend, replot=False)
        else:
            self.plotWindow.clearCurves()
        if (self.xmcdData is None) or (self.xasData is None):
            # Nothing to do
            return
        xyList  = []
        mapToY2 = False
        window = window.lower()
        if window == self.__tabElem:
            if self.xmcdCorrData is not None:
                _logger.debug('plotOnDemand -- __tabElem: Using self.xmcdCorrData')
                xmcdX, xmcdY = self.xmcdCorrData
                xmcdLabel = 'xmcd corr'
            else:
                _logger.debug('plotOnDemand -- __tabElem: Using self.xmcdData')
                xmcdX, xmcdY = self.xmcdData
                xmcdLabel = 'xmcd'
            xasX,  xasY  = self.xasData
            xyList = [(xmcdX, xmcdY, xmcdLabel, {'plot_yaxis': 'right'}),
                      (xasX, xasY, 'xas', {})]
            # At least one of the curve is going
            # to get plotted on secondary y axis
            mapToY2 = True
        elif window == self.__tabBG:
            xasX, xasY= self.xasData
            xyList = [(xasX, xasY, 'xas', {})]
            if self.xasDataBG is not None:
                xasBGX, xasBGY = self.xasDataBG
                xyList += [(xasBGX, xasBGY, self.__xasBGmodel, {})]
        elif window == self.__tabInt:
            if self.xasDataBG is None:
                self.xmcdInt = None
                self.xasInt  = None
                return
            # Calculate xasDataCorr
            xBG, yBG = self.xasDataBG
            x, y = self.xasData
            self.xasDataCorr = x, y-yBG
            if self.xmcdCorrData is not None:
                _logger.debug('plotOnDemand -- __tabInt: Using self.xmcdCorrData')
                xmcdX, xmcdY = self.xmcdCorrData
                xmcdIntLabel = 'xmcd corr Int'
            else:
                _logger.debug('plotOnDemand -- __tabInt: Using self.xmcdData')
                xmcdX, xmcdY = self.xmcdData
                xmcdIntLabel = 'xmcd Int'
            mathObj = Calculations()
            xasX,  xasY  = self.xasDataCorr
            xmcdIntY = mathObj.cumtrapz(y=xmcdY, x=xmcdX)
            xmcdIntX = .5 * (xmcdX[1:] + xmcdX[:-1])
            xasIntY  = mathObj.cumtrapz(y=xasY,  x=xasX)
            xasIntX  = .5 * (xasX[1:] + xasX[:-1])
            xyList = [(xmcdIntX, xmcdIntY, xmcdIntLabel, {'plot_yaxis': 'right'}),
                      (xasX,     xasY,     'xas corr', {}),
                      (xasIntX,  xasIntY,  'xas Int', {})]
            self.xmcdInt = xmcdIntX, xmcdIntY
            self.xasInt = xasIntX, xasIntY
        xmin, xmax = numpy.inf, -numpy.inf
        ymin, ymax = numpy.inf, -numpy.inf
        for x,y,legend,info in xyList:
            xmin = min(xmin, x.min())
            xmax = max(xmax, x.max())
            ymin = min(ymin, y.min())
            ymax = max(ymax, y.max())
            _logger.debug('plotOnDemand -- adding Curve..')
            """
            if mapToY2:
                if hasattr(self.plotWindow, 'graph'):
                    specLegend = self.plotWindow.dataObjectsList[-1]
                    self.plotWindow.graph.mapToY2(specLegend)
                else:
                    info['plot_yaxis'] = 'right'
            """
            self.plotWindow.addCurve(
                    x=x,
                    y=y,
                    legend=legend,
                    info=info,
                    replace=False,
                    replot=True)
        # Assure margins in plot when using matplotlibbackend
        if not hasattr(self.plotWindow, 'graph'):
            _logger.debug('plotOnDemand -- Setting margins..\n'
                      '\txmin: %s xmax: %s\n\tymin: %s ymax: %s',
                      xmin, xmax , ymin, ymax)
            # Pass if no curves present
            curves = self.plotWindow.getAllCurves(just_legend=True)
            if len(curves) == 0:
                # At this point xymin, xymax should be infinite..
                pass
            xmargin = 0.1 * (xmax - xmin)
            ymargin = 0.1 * (ymax - ymin)
            self.plotWindow.setGraphXLimits(xmin-xmargin,
                                            xmax+xmargin)
            self.plotWindow.setGraphYLimits(ymin-ymargin,
                                            ymax+ymargin)
            # Need to force replot here for correct display
            self.plotWindow.replot()
            self.plotWindow.updateLegends()

    def addMarker(self, window, label='X MARKER', xpos=None, unit=''):
        # Add spinbox controlling the marker
        spinbox = MarkerSpinBox(window, self.plotWindow, label)

        # Connects
        self.tabChangedSignal.connect(spinbox._setMarkerFollowMouse)

        if len(unit) > 0:
            text = label + ' ' + unit
        else:
            text = label

        # Widget & Layout
        spinboxWidget = qt.QWidget()
        spinboxLayout = qt.QHBoxLayout()
        spinboxLayout.addWidget(qt.QLabel(text))
        spinboxLayout.addWidget(qt.HorizontalSpacer())
        spinboxLayout.addWidget(spinbox)
        spinboxWidget.setLayout(spinboxLayout)

        return spinboxWidget, spinbox

    def _handlePlotSignal(self, ddict):
        #if 'marker' not in ddict:
        if ddict['event'] == 'markerMoved':
            if self.tabWidget.currentIndex() == 1: # 1 -> BG tab
                self.estimateBG()

    def _handleTabChangedSignal(self, idx):
        if idx >= len(self.tabList):
            _logger.info('Tab changed -- Index out of range')
            return
        tab = self.tabList[idx]
        self.plotOnDemand(window=tab)
        # Hide/Show markers depending on the selected tab
        # Problem: MarkerLabels are stored in markerList,
        # however the MarkerSpinBoxes are stores in
        # self.valuesDict ...
        # edgeMarkers & xasMarkers -> BACKGROUND  tab
        # xmcdMarker               -> INTEGRATION tab
        markerList = self.xasMarkerList\
                   + self.edgeMarkerList\
                   + self.xmcdMarkerList
        if tab == self.__tabBG:
            self.buttonEstimate.setEnabled(True)
            for marker in markerList:
                if (marker in self.xasMarkerList) or\
                   (marker in self.edgeMarkerList):
                    sb = self.valuesDict[self.__tabBG][marker]
                    sb.showMarker()
                else:
                    sb = self.valuesDict[self.__tabInt][marker]
                    sb.hideMarker()
            keys = [key for key in self.valuesDict[self.__tabElem].keys()\
                    if key.endswith('Transition')]
            ratioSB = self.valuesDict[self.__tabBG]['Step Ratio']
            for idx, keyElem in enumerate(keys):
                keyBG = 'Edge %d'%(idx+1)
                sb = self.valuesDict[self.__tabBG][keyBG]
                parentWidget  = sb.parent()
                parentWidget.setEnabled(True)
            self.estimateBG()
        elif tab == self.__tabInt:
            self.buttonEstimate.setEnabled(True)
            for marker in markerList:
                if marker in self.xmcdMarkerList:
                    sb = self.valuesDict[self.__tabInt][marker]
                    sb.showMarker()
                else:
                    sb = self.valuesDict[self.__tabBG][marker]
                    #sb.setValue(0.0) # Should be consistent with estimateBG
                    sb.hideMarker()
            self.calcMagneticMoments()
        else: # tab == self.__tabElem:
            self.buttonEstimate.setEnabled(False)
            for marker in markerList:
                if marker in self.xmcdMarkerList:
                    sb = self.valuesDict[self.__tabInt][marker]
                else:
                    sb = self.valuesDict[self.__tabBG][marker]
                sb.showMarker()
        self.tabChangedSignal.emit(tab)

    def keyPressEvent(self, event):
        if event.key() == qt.Qt.Key_F2:
            # Switch to tab Element
            idx = self.tabList.index(self.__tabElem)
            self.tabWidget.setCurrentIndex(idx)
        elif event.key() == qt.Qt.Key_F3:
            # Switch to tab Background
            idx = self.tabList.index(self.__tabBG)
            self.tabWidget.setCurrentIndex(idx)
        elif event.key() == qt.Qt.Key_F4:
            # Switch to tab Integration
            idx = self.tabList.index(self.__tabInt)
            self.tabWidget.setCurrentIndex(idx)
        elif event.key() == qt.Qt.Key_F5:
            # Trigger estimation
            self.estimate()
        else:
            qt.QWidget.keyPressEvent(self, event)

class LoadDichorismDataDialog(qt.QFileDialog):

    dataInputSignal = qt.pyqtSignal(object)

    def __init__(self, parent=None):
        #qt.QDialog.__init__(self, parent)
        qt.QFileDialog.__init__(self, parent)
        self.dataDict = {}
        self.validated = False

        self.setWindowTitle('Load Dichorism Data')
        if hasattr(self, "setNameFilters"):
            self.setNameFilters(['Spec Files (*.spec)',
                                 'Text Files (*.txt; *.dat)',
                                 'All Files (*.*)'])
            self.setOption(qt.QFileDialog.DontUseNativeDialog, True)
        else:
            self.setFilter('Spec Files (*.spec);;'
                          +'Text Files (*.txt; *.dat);;'
                          +'All Files (*.*)')

        # Take the QSpecFileWidget class as used
        # in the main window to select data and
        # insert it into a QFileDialog. Emit the
        # selected data at acceptance
        self.specFileWidget = QSpecFileWidget.QSpecFileWidget(
                                        parent=parent,
                                        autoreplace=False)
        # Hide the widget containing the Auto Add/Replace
        # checkboxes
        self.specFileWidget.autoAddBox.parent().hide()
        # Remove the tab widget, only the counter widget
        # is needed. Remember: close() only hides a widget
        # however the widget persists in the memory.
        #self.specFileWidget.mainTab.removeTab(1)
        self.specFileWidget.mainTab.hide()
        #self.counterTab = self.specFileWidget.mainTab.widget(0)
        self.specFileWidget.mainLayout.addWidget(self.specFileWidget.cntTable)
        self.specFileWidget.cntTable.show()
        # Change the table headers in cntTable
        # Note: By conicidence, the original SpecFileCntTable
        # has just enough columns as we need. Here, we rename
        # the last two:
        # 'y'   -> 'XAS'
        # 'mon' -> 'XMCD'
        labels = ['Counter', 'X', 'XAS', 'XMCD']
        table  = self.specFileWidget.cntTable
        for idx in range(len(labels)):
            item = table.horizontalHeaderItem(idx)
            if item is None:
                item = qt.QTableWidgetItem(labels[idx],
                                           qt.QTableWidgetItem.Type)
            item.setText(labels[idx])
            table.setHorizontalHeaderItem(idx,item)


        # Hide the widget containing the Add, Replace, ...
        # PushButtons
        self.specFileWidget.buttonBox.hide()

        # Change selection behavior/mode in the scan list so
        # that only a single scan can be selected at a time
        self.specFileWidget.list.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.specFileWidget.list.setSelectionMode(qt.QAbstractItemView.SingleSelection)

        # Tinker with the native layout of QFileDialog
        mainLayout = self.layout()
        mainLayout.addWidget(self.specFileWidget, 0, 4, 4, 1)

        #
        # Signals
        #
        self.currentChanged.connect(self.setDataSource)

    def setDataSource(self, filename):
        # Opens a spec file and allows to browse its
        # contents in the top right widget
        filename = str(filename)
        if osPathIsDir(filename):
            _logger.debug('LoadDichorismDataDialog.setDataSource -- Invalid path or filename..')
            return
        try:
            src = SpecFileDataSource.SpecFileDataSource(filename)
        except ValueError:
            return
        self.specFileWidget.setDataSource(src)

    def accept(self):
        llist = self.selectedFiles()
        if len(llist) == 1:
            filename = str(llist[0])
        else:
            return
        self.processSelectedFile(filename)
        if self.validated:
            super(LoadDichorismDataDialog, self).accept()

    def processSelectedFile(self, filename):
        self.dataDict = {}
        filename = str(filename)

        scanList = self.specFileWidget.list.selectedItems()
        if len(scanList) == 0:
            self.errorMessageBox('No scan selected!')
            return
        else:
            scan   = scanList[0]
            scanNo = str(scan.text(1))

        table = self.specFileWidget.cntTable
        # ddict['x'] -> 'X'
        # ddict['y'] -> 'XAS'
        # ddict['m'] -> 'XMCD'
        ddict   = table.getCounterSelection()
        colX    = ddict['x']
        colXas  = ddict['y']
        colXmcd = ddict['m']
        # Check if only one is selected
        if len(colX) != 1:
            self.errorMessageBox('Single counter must be set as X')
            return
        else:
            colX = colX[0]

        if len(colXas) != 1:
            self.errorMessageBox('Single counter must be set as XAS')
            return
        else:
            colXas = colXas[0]

        if len(colXmcd) != 1:
            self.errorMessageBox('Single counter must be set as XMCD')
            return
        else:
            colXmcd = colXmcd[0]

        if colXas == colX:
            self.errorMessageBox('X and XAS use the same counter')
            return
        elif colX == colXmcd:
            self.errorMessageBox('X and XMCD use the same counter')
            return
        elif colXmcd == colXas:
            self.errorMessageBox('XAS and XMCD use the same counter')
            return

        # Extract data
        dataObj = self.specFileWidget.data.getDataObject(scanNo)
        # data has format (rows, cols) -> (steps, counters)
        self.dataDict['fn']   = filename
        self.dataDict['x']    = dataObj.data[:, colX]
        self.dataDict['xas']  = dataObj.data[:, colXas]
        self.dataDict['xmcd'] = dataObj.data[:, colXmcd]

        self.validated = True
        self.dataInputSignal.emit(self.dataDict)

    def errorMessageBox(self, msg):
        box = qt.QMessageBox()
        box.setWindowTitle('Sum Rules Load Data Error')
        box.setIcon(qt.QMessageBox.Warning)
        box.setText(msg)
        box.exec()

if __name__ == '__main__':

    app = qt.QApplication([])
    win = SumRulesWindow()
    #r'C:\Users\tonn\lab\datasets\sum_rules\sum_rules_4f_example_EuRhj2Si2'
    #win = DataDisplay.PlotWindow()
    #xmin, xmax = win.getGraphXLimits()
    #win.insertXMarker(50., draggable=True)
    #win = LoadDichorismDataDialog()
    #x, avgA, avgB, xmcd, xas = getData()
    #win.plotWindow.newCurve(x,xmcd, legend='xmcd', xlabel='ene_st', ylabel='zratio', info={}, replot=False, replace=False)
    #win.setRawData(x,xmcd, identifier='xmcd')
    #win.plotWindow.newCurve(x,xas, legend='xas', xlabel='ene_st', ylabel='zratio', info={}, replot=False, replace=False)
    #win.setRawData(x,xas, identifier='xas')
    #win = LoadDichorismDataDialog()
    win.show()
    app.exec()
