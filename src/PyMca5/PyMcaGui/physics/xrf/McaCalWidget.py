#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import numpy
from numpy.linalg import inv as inverse
import copy
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting.PlotWidget import PlotWidget

if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
QTVERSION = qt.qVersion()
from PyMca5.PyMcaMath.fitting import Gefit
from PyMca5.PyMcaMath.fitting import Specfit
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from . import PeakTableWidget
if 0:
    from PyMca5 import XRDPeakTableWidget
_logger = logging.getLogger(__name__)

LOW_HEIGHT_THRESHOLD = 660


class McaCalWidget(qt.QDialog):
    def __init__(self, parent=None, name="MCA Calibration Widget",
                x = None,y=None,current=None,peaks=None,caldict=None,
                specfit=None,legend="", xrd=False, lambda_="-", modal=0,fl=0):
                #fl=qt.Qt.WDestructiveClose):
        self.name= name
        if QTVERSION < '4.0.0':
            qt.QDialog.__init__(self, parent, name, modal,fl)
            self.setCaption(self.name)
        else:
            qt.QDialog.__init__(self, parent)
            self.setModal(modal)
            self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
            self.setWindowTitle(self.name)
            maxheight = qt.QDesktopWidget().height()
            if maxheight < 770:
                self.setMinimumHeight(int(0.9*(maxheight)))
                self.setMaximumHeight(int(1.0*(maxheight)))
        self.__xrdMode = xrd
        self.__xrdLambda = lambda_
        self.__xrdEnergy = ""
        self.__xrdParticle = "Photon"
        self.__manualsearch = 0
        self.foundPeaks = []
        if caldict is None:
            caldict = {}
        self.dict = {}
        if x is None:
            if len(y):
                x = numpy.arange(len(y)).astype(numpy.float64)
        self.dict ['x'] = x
        self.dict ['y'] = y
        self.dict ['legend'] = legend
        self.current = legend
        self.caldict = caldict
        if legend not in self.caldict.keys():
            self.caldict[legend] = {}
            self.caldict[legend]['order'] = 1
            self.caldict[legend]['A'] = 0.0
            self.caldict[legend]['B'] = 1.0
            self.caldict[legend]['C'] = 0.0
        if not ('order' in self.caldict[legend]):
                if abs(self.caldict[legend]['C']) > 0.0:
                    self.caldict[legend]['order'] = 2
                else:
                    self.caldict[legend]['order'] = 1
        self.callist           = self.caldict.keys()
        if specfit is None:
            self.specfit = Specfit.Specfit()
        else:
            self.specfit = specfit
        self.build()
        self.initIcons()
        self.initToolBar()
        self.connections()
        if self.dict ['y'] is not None:
            self.plot(x,y,legend)
        self.markermode = 0
        self.linewidgets=[]
        self._toggleLogY()
        self.__peakmarkermode()


    def build(self):
        self.layout = qt.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.toolbar   = qt.QWidget(self)
        self.toolbar.layout = qt.QHBoxLayout(self.toolbar)
        self.toolbar.layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar.layout.setSpacing(0)
        self.layout.addWidget(self.toolbar)
        self.container = qt.QWidget(self)
        self.container.layout = qt.QVBoxLayout(self.container)
        self.container.layout.setContentsMargins(0, 0, 0, 0)
        self.container.layout.setSpacing(0)

        self.layout.addWidget(self.container)
        #The graph
        self.graph = PlotWidget(self.container,
                                backend=None)
        self.graph.setGraphXLabel('Channel')
        self.graph.setGraphYLabel('Counts')
        self.graph.setDataMargins(0.0, 0.0, 0.0, 0.0)

        #The calibration Widget
        self.bottomPanel = qt.QWidget(self.container)
        self.bottomPanel.layout = qt.QHBoxLayout(self.bottomPanel)
        self.bottomPanel.layout.setSpacing(6)
        if qt.QDesktopWidget().height() < LOW_HEIGHT_THRESHOLD:
            self.bottomPanel.layout.setContentsMargins(2, 2, 2, 2)
        else:
            self.bottomPanel.layout.setContentsMargins(10, 10, 10, 10)
        self.peakParameters        = PeakSearchParameters(self.bottomPanel)
        self.bottomPanel.layout.addWidget(self.peakParameters)
        """
        self.calpar         = CalibrationParameters(self.bottomPanel)
        self.calpar. setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        """
        if QTVERSION < '4.0.0':
            self.bottomPanel.layout.addWidget(qt.HorizontalSpacer(self.bottomPanel))
        #self.cal.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.MinimumExpanding)
        self.peakParameters.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,
                                                  qt.QSizePolicy.Fixed))
        if self.__xrdMode:
            self.peakTable      = XRDPeakTableWidget.XRDPeakTableWidget(self.bottomPanel)
        else:
            self.peakTable      = PeakTableWidget.PeakTableWidget(self.bottomPanel)
        self.bottomPanel.layout.addWidget(self.peakTable)
        self.peakTable.verticalHeader().hide()
        if QTVERSION < '4.0.0':
            self.peakTable.setLeftMargin(0)
        self.container.layout.addWidget(self.graph)
        self.container.layout.addWidget(self.bottomPanel)

        #self.peakTable.setRowReadOnly(0,1)


    def initIcons(self):
        self.normalIcon	= qt.QIcon(qt.QPixmap(IconDict["normal"]))
        self.zoomIcon	= qt.QIcon(qt.QPixmap(IconDict["zoom"]))
        self.roiIcon	= qt.QIcon(qt.QPixmap(IconDict["roi"]))
        self.peakIcon	= qt.QIcon(qt.QPixmap(IconDict["peak"]))

        self.zoomResetIcon	= qt.QIcon(qt.QPixmap(IconDict["zoomreset"]))
        self.roiResetIcon	= qt.QIcon(qt.QPixmap(IconDict["roireset"]))
        self.peakResetIcon	= qt.QIcon(qt.QPixmap(IconDict["peakreset"]))
        self.refreshIcon	= qt.QIcon(qt.QPixmap(IconDict["reload"]))

        self.logxIcon	= qt.QIcon(qt.QPixmap(IconDict["logx"]))
        self.logyIcon	= qt.QIcon(qt.QPixmap(IconDict["logy"]))
        self.fitIcon	= qt.QIcon(qt.QPixmap(IconDict["fit"]))
        self.searchIcon	= qt.QIcon(qt.QPixmap(IconDict["peaksearch"]))

    def _resetZoom(self, dummyValue=None):
        return self.graph.resetZoom()

    def initToolBar(self):
        toolbar = self.toolbar
        #Zoom Reset
        self._addToolButton(self.zoomResetIcon,
                            self._resetZoom,
                            'Auto-Scale the Graph')
        # Logarithmic
        self.yLogButton = self._addToolButton(self.logyIcon,
                                    self._toggleLogY,
                                    'Toggle Logarithmic Y Axis (On/Off)',
                                    toggle=True)
        self.yLogButton.setChecked(False)
        self.yLogButton.setDown(False)
        # Search
        self._addToolButton(self.searchIcon,
                            self.peakSearch,
                            'Clear Peak Table and Search Peaks')
        # Clear peaks
        self._addToolButton(self.peakResetIcon,
                            self.clearPeaks,
                            'Clear Peak Table')
        # Manual Search
        self.__msb = self._addToolButton(self.peakIcon,
                            self.manualsearch,
                            'Add a peak to the graph',
                            toggle=True)
        self.toolbar.layout.addWidget(qt.HorizontalSpacer(toolbar))
        label=qt.QLabel(toolbar)
        label.setText('<b>Channel:</b>')
        self.toolbar.layout.addWidget(label)
        self.xpos = qt.QLineEdit(toolbar)
        self.xpos.setText('------')
        self.xpos.setReadOnly(1)
        self.xpos.setFixedWidth(self.xpos.fontMetrics().maxWidth()*len('########'))
        self.toolbar.layout.addWidget(self.xpos)
        label=qt.QLabel(toolbar)
        label.setText('<b>Counts:</b>')
        self.toolbar.layout.addWidget(label)
        self.ypos = qt.QLineEdit(toolbar)
        self.ypos.setText('------')
        self.ypos.setReadOnly(1)
        self.ypos.setFixedWidth(self.ypos.fontMetrics().maxWidth()*len('#########'))
        self.toolbar.layout.addWidget(self.ypos)
        label=qt.QLabel(toolbar)
        if self.__xrdMode:
            label.setText('<b>2Theta:</b>')
        else:
            label.setText('<b>Energy:</b>')
        self.toolbar.layout.addWidget(label)
        self.epos = qt.QLineEdit(toolbar)
        self.epos.setText('------')
        self.epos.setReadOnly(1)
        self.epos.setFixedWidth(self.epos.fontMetrics().maxWidth()*len('#########'))
        self.toolbar.layout.addWidget(self.epos)

        #rest
        toolbar2 = qt.QWidget(self)
        self.layout.addWidget(toolbar2)
        toolbar2.layout = qt.QHBoxLayout(toolbar2)
        toolbar2.layout.setContentsMargins(0, 0, 0, 0)
        toolbar2.layout.setSpacing(0)
        self.calpar         = CalibrationParameters(toolbar2,
                                calname=self.current,caldict=self.caldict,
                                xrd=self.__xrdMode)
        self.calpar. setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.okButton       = qt.QPushButton(toolbar2)
        self.okButton.setText('OK')
        self.cancelButton       = qt.QPushButton(toolbar2)
        self.cancelButton.setText('Cancel')
        if QTVERSION < '4.0.0':
            pass
        else:
            self.okButton.setAutoDefault(False)
            self.cancelButton.setAutoDefault(False)
        self.okButton. setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.cancelButton. setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        toolbar2.layout.addWidget(self.calpar)
        toolbar2.layout.addWidget(self.okButton)
        toolbar2.layout.addWidget(self.cancelButton)


    def _addToolButton(self, icon, action, tip, toggle=None):
        toolbar = self.toolbar
        tb      = qt.QToolButton(toolbar)
        tb.setIcon(icon)
        tb.setToolTip(tip)
        if toggle is not None:
            if toggle:
                tb.setCheckable(1)
        self.toolbar.layout.addWidget(tb)
        tb.clicked.connect(action)
        return tb

    def _toggleLogY(self):
        _logger.debug("_toggleLogY")
        if self.graph.isYAxisLogarithmic():
            self.setYAxisLogarithmic(False)
        else:
            self.setYAxisLogarithmic(True)

    def setYAxisLogarithmic(self, flag=True):
        self.graph.setYAxisLogarithmic(flag)
        self.yLogButton.setChecked(flag)
        self.yLogButton.setDown(flag)
        self._resetZoom()

    def connections(self):
        self.peakParameters.searchButton.clicked.connect(self.peakSearch)
        self.graph.sigPlotSignal.connect(self.__graphsignal)
        self.peakTable.sigPeakTableWidgetSignal.connect(self.__peakTableSignal)
        self.calpar.sigCalibrationParametersSignal.connect( \
                     self.__calparsignal)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    def plot(self, x, y, legend):
        #clear graph
        self.graph.clear()
        self.graph.addCurve(x, y , legend=legend, replot=True)
        self.dict['x']      = x
        self.dict['y']      = y
        self.dict['legend'] = legend
        #reset the zoom
        self._resetZoom()

    def peakSearch(self):
        _logger.debug("Peak search called")
        if self.__manualsearch:
            self.__manualsearch = 0
            if QTVERSION < '4.0.0':
                self.__msb.setState(qt.QButton.Off)
            else:
                self.__msb.setChecked(0)
        #get current plot limits
        xmin,xmax=self.graph.getGraphXLimits()
        #set the data into specfit
        self.specfit.setdata(x=self.dict['x'],
                             y=self.dict['y'],
                             xmin=xmin,
                             xmax=xmax)
        #get the search parameters from the interface
        pars = self.peakParameters.getParameters()
        if pars["AutoFwhm"]:
            fwhm = self.specfit.guess_fwhm()
        else:
            fwhm = pars["FwhmPoints"]
        if pars["AutoYscaling"]:
            yscaling = self.specfit.guess_yscaling()
        else:
            yscaling = pars["Yscaling"]
        sensitivity  = pars["Sensitivity"]
        self.peakParameters.fwhmText.setText("%d" % fwhm)
        self.peakParameters.yscalingText.setText("%f" % yscaling)
        ysearch = self.specfit.ydata*yscaling
        peaksidx=SpecfitFuns.seek(ysearch,1,len(ysearch),
                                    fwhm,
                                    sensitivity)
        self.foundPeaks = []
        self.graph.clearMarkers()
        self.__destroylinewidgets()
        self.peakTable.setRowCount(0)
        i = 0
        for idx in peaksidx:
            self.foundPeaks.append(self.specfit.xdata[int(idx)])
            #self.graph.insertx1marker(self.specfit.xdata[int(idx)],self.specfit.ydata[int(idx)])
            self.graph.insertXMarker(self.specfit.xdata[int(idx)],
                                     legend="%d" % i,
                                     text=None,
                                     selectable=True,
                                     draggable=False,
                                     replot=False)
            i += 1
        self.graph.replot()
        #make sure marker mode is on
        self.markermode = 0
        self.__peakmarkermode()

    def clearpeaks(self):
        _logger.info("DEPRECATED: Use clearPeaks")
        return self.clearPeaks()

    def clearPeaks(self):
        self.foundPeaks = []
        self.graph.clearMarkers()
        self.__destroylinewidgets()
        self.peakTable.clearPeaks()
        self.graph.replot()

    def manualsearch(self):
        #disable peak selection
        self.markermode     = 1
        self.__peakmarkermode()
        self.__manualsearch = 1

    def __destroylinewidgets(self):
        for widget in self.linewidgets:
            widget.close(1)
        self.linewidgets=[]

    def __peakmarkermode(self):
        self.__manualsearch = 0
        if self.markermode:
            self.graph.setCursor(qt.QCursor(qt.Qt.CrossCursor))
            self.markermode = 0
            self.graph.setZoomModeEnabled(False)
        else:
            self.markermode = 1
            self.nomarkercursor = self.graph.cursor().shape()
            self.graph.setCursor(qt.QCursor(qt.Qt.PointingHandCursor))
            self.graph.setZoomModeEnabled(True)
        #self.markerButton.setOn(self.markermode == 1)

    def __calparsignal(self,dict):
        _logger.debug("__calparsignal called dict = %s", dict)
        if dict['event'] == 'coeff':
            current = dict['calname' ]
            self.current  = current
            self.caldict[current]['order'] =dict['caldict'][dict['calname']]['order']
            self.caldict[current]['A'] =dict['caldict'][dict['calname']]['A']
            self.caldict[current]['B'] =dict['caldict'][dict['calname']]['B']
            self.caldict[current]['C'] =dict['caldict'][dict['calname']]['C']
            peakdict = self.peakTable.getDict()
            for peak in peakdict.keys():
                channel = peakdict[peak]['channel']
                calenergy  = self.caldict[current]['A'] + \
                                 self.caldict[current]['B'] * channel +\
                                 self.caldict[current]['C'] * channel * channel
                self.peakTable.configure(name=peak,use=0,
                                         calenergy=calenergy)
        elif dict['event'] == 'order':
            current = dict['calname' ]
            self.current  = current
            order = dict['caldict'][current]['order']
            self.caldict[current]['order'] = order
            if order in ["ID18", "ID14"]:
                result = self.timeCalibratorCalibration()
                if result is None:
                    return
                peak0, npeaks, delta, deltat = result[:]
                self.clearPeaks()
                self.foundPeaks = []
                for i in range(int(npeaks)):
                    channel = peak0 + i * delta
                    calenergy = deltat * (i + 1)
                    self.foundPeaks.append(channel)
                    name = "%d" % i
                    marker = self.graph.insertXMarker(channel,
                                                      legend=name,
                                                      color="red",
                                                      replot=False)
                    if name in self.peakTable.peaks.keys():
                        self.peakTable.configure(number=name,
                                             channel=channel,
                                             use=1,
                                             setenergy=calenergy,
                                             calenery=calenergy)
                    else:
                        nlines=self.peakTable.rowCount()
                        self.peakTable.newpeakline(name, nlines+1)
                        self.peakTable.configure(number=name,
                                             channel=channel,
                                             use=1,
                                             setenergy=calenergy,
                                             calenery=calenergy)
                #make sure we cannot select the peaks again
                self.markermode = 1
                self.__peakmarkermode()
                self.graph.replot()
            else:
                self.caldict[current]['A']     = dict['caldict'][current]['A']
                self.caldict[current]['B']     = dict['caldict'][current]['B']
                self.caldict[current]['C']     = dict['caldict'][current]['C']
                if self.caldict[current]['order'] == 'TOF':
                    self.caldict[current]['vfix'] = dict['caldict'][current]['vfix']

            self.__peakTableSignal({'event':'use'})

        elif dict['event'] == 'savebox':
            current = dict['calname' ]
            if current not in self.caldict.keys():
                self.caldict[current] = {}
            self.current  = current
            self.caldict[current]['order'] = dict['caldict'][current]['order']
            self.caldict[current]['A']     = dict['caldict'][current]['A']
            self.caldict[current]['B']     = dict['caldict'][current]['B']
            self.caldict[current]['C']     = dict['caldict'][current]['C']

        elif dict['event'] == 'activated':
            # A comboBox has been selected
            if   dict['boxname'] == 'Source':
                pass
            elif dict['boxname'] == 'Calibration':
                pass
            else:
                _logger.debug("Unknown combobox %s", dict['boxname'])
        else:
            _logger.warning("Unknown signal %s", dict)

    def __graphsignal(self, ddict):
        _logger.debug("__graphsignal called with dict = %s", ddict)
        if ddict['event'] in ['markerClicked', 'markerSelected']:
            _logger.debug("Setting marker color")
            marker = int(ddict['label'])
            #The marker corresponds to the peak number
            channel = self.foundPeaks[marker]
            self.graph.insertXMarker(channel,
                                     legend=ddict['label'],
                                     color='red',
                                     replot=False)
            self.graph.replot()
            current = self.current
            calenergy = self.caldict[current]['A']+ \
                        self.caldict[current]['B'] * channel+ \
                        self.caldict[current]['C'] * channel * channel
            name = "Peak %d" % marker
            number = marker
            channel = ddict['x']
            if self.__xrdMode:
                linewidget = XRDPeakTableWidget.XRDInputLine(self,name="Enter Selected Peak Parameters",
                                    peakpars={'name':name,
                                              'number':number,
                                              'channel':channel,
                                              'use':1,
                                              'cal2theta':calenergy,
                                              'energy':self.__xrdEnergy,
                                              'lambda_':self.__xrdLambda,
                                              'particle':self.__xrdParticle})
            else:
                linewidget = InputLine(self,name="Enter Selected Peak Parameters",
                                    peakpars={'name':name,
                                    'number':number,
                                    'channel':channel,
                                    'use':1,
                                    'calenergy':calenergy})
            if QTVERSION < '4.0.0':
                ret = linewidget.exec_loop()
            else:
                ret = linewidget.exec()
            if ret == qt.QDialog.Accepted:
                ddict=linewidget.getDict()
                _logger.debug("dict got from dialog = %s", ddict)
                if ddict != {}:
                    if name in self.peakTable.peaks.keys():
                        self.peakTable.configure(*ddict)
                    else:
                        nlines=self.peakTable.rowCount()
                        ddict['name'] = name
                        self.peakTable.newpeakline(name, nlines+1)
                        self.peakTable.configure(**ddict)
                    peakdict = self.peakTable.getDict()
                    usedpeaks = []
                    for peak in peakdict.keys():
                        if peakdict[peak]['use'] == 1:
                            if self.__xrdMode:
                                self.__xrdLambda = ddict['lambda_']
                                self.__xrdParticle = ddict['particle']
                                self.__xrdEnergy = ddict['energy']
                                usedpeaks.append([peakdict[peak]['channel'],
                                              peakdict[peak]['set2theta']])
                            else:
                                usedpeaks.append([peakdict[peak]['channel'],
                                              peakdict[peak]['setenergy']])
                    if len(usedpeaks):
                        newcal = self.calculate(usedpeaks,order=self.caldict[current]['order'])
                        if newcal is None:
                            return
                        self.caldict[current]['A'] = newcal[0]
                        self.caldict[current]['B'] = newcal[1]
                        self.caldict[current]['C'] = newcal[2]
                    self.__peakTableSignal({'event':'use'}, calculate=False)
            else:
                _logger.debug("Dialog cancelled or closed ")
                self.graph.insertXMarker(channel,
                                         legend=ddict['label'],
                                         color='black',
                                         replot=False)
                self.graph.replot()
            del linewidget
        elif ddict['event'] in ["mouseMoved", 'MouseAt']:
            self.xpos.setText('%.1f' % ddict['x'])
            self.ypos.setText('%.1f' % ddict['y'])
            current = self.current
            if self.caldict[current]['order'] == 'TOF':
                calenergy = self.getTOFEnergy(ddict['x'])
            else:
                calenergy = self.caldict[current]['A']+ \
                        self.caldict[current]['B'] * ddict['x']+ \
                        self.caldict[current]['C'] * ddict['x'] * ddict['x']
            self.epos.setText('%.3f' % calenergy)
        elif ddict['event'] in ['mouseClicked', 'MouseClick']:
            if self.__manualsearch:
                x = ddict['x']
                y = ddict['y']
                if (y <= 1.0): y=1.1
                # insert the marker
                self.foundPeaks.append(x)
                legend = "%d" % (len(self.foundPeaks)-1)
                #self.graph.insertx1marker(self.specfit.xdata[int(idx)],self.specfit.ydata[int(idx)])
                self.graph.insertXMarker(x, legend=legend,
                                         selectable=True, replot=False)
                self.graph.replot()
                self.markermode = 0
                self.__peakmarkermode()
            self.__msb.setChecked(0)
        else:
            _logger.debug("Unhandled event %s", ddict['event'])

    def __peakTableSignal(self, ddict, calculate=True):
        _logger.debug("__peaktablesignal called dict = %s", ddict)
        if (ddict['event'] == 'use') or (ddict['event'] == 'setenergy'):
            #get table dictionary
            peakdict = self.peakTable.getDict()
            usedpeaks = []
            for peak in peakdict.keys():
                if peakdict[peak]['use'] == 1:
                    if self.__xrdMode:
                        usedpeaks.append([peakdict[peak]['channel'],
                                      peakdict[peak]['set2theta']])
                    else:
                        usedpeaks.append([peakdict[peak]['channel'],
                                      peakdict[peak]['setenergy']])
            if len(usedpeaks):
              if usedpeaks != [[0.0,0.0]]:
                current = self.current
                if calculate:
                    newcal = self.calculate(usedpeaks,order=self.caldict[current]['order'])
                    if newcal is None:
                        return
                    self.caldict[current]['A'] = newcal[0]
                    self.caldict[current]['B'] = newcal[1]
                    self.caldict[current]['C'] = newcal[2]
                self.calpar.setParameters(self.caldict[current])
                for peak in peakdict.keys():
                    channel = peakdict[peak]['channel']
                    if self.caldict[current]['order'] == 'TOF':
                        calenergy = self.getTOFEnergy(channel)
                    else:
                        calenergy  = self.caldict[current]['A'] + \
                                 self.caldict[current]['B'] * channel +\
                                 self.caldict[current]['C'] * channel * channel
                    if self.__xrdMode:
                        self.peakTable.configure(name=peak, cal2theta=calenergy)
                    else:
                        self.peakTable.configure(name=peak, calenergy=calenergy)

    def timeCalibratorCalibration(self):
        self.peakSearch()
        # now we should have a list of peaks and the proper data to fit
        if 'Periodic Gaussians' not in self.specfit.theorylist:
            self.specfit.importfun("SpecfitFunctions.py")
        self.specfit.settheory('Periodic Gaussians')
        self.specfit.setbackground('Constant')
        fitconfig = {}
        fitconfig.update(self.specfit.fitconfig)
        fitconfig['WeightFlag'] = 1
        fitconfig['McaMode']    = 0
        self.specfit.configure(**fitconfig)
        try:
            self.specfit.estimate()
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error on estimate: %s" % sys.exc_info()[1])
            msg.exec()
            return
        try:
            self.specfit.startfit()
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error on Fit")
            msg.exec()
            return
        npeaks = 0
        delta  = 0.0
        peak0  = 0.0
        for i in range(len(self.specfit.paramlist)):
            name = self.specfit.paramlist[i]['name']
            if name == "Delta1":
                delta = self.specfit.paramlist[i]['fitresult']
            elif name == 'N1':
                npeaks = self.specfit.paramlist[i]['fitresult']
            elif name == 'Position1':
                peak0 = self.specfit.paramlist[i]['fitresult']
            else:
                continue

        if (npeaks < 2) or (delta==0):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Less than two peaks found")
            msg.exec()
            return


        d = DoubleDialog(self, text='Enter peak separation in time:')
        d.setWindowTitle('Time calibration')
        ret = d.exec()
        if ret != qt.QDialog.Accepted:
            return
        text = str(d.lineEdit.text())
        if not len(text):
            deltat = 0.0
        else:
            deltat = float(text)
        if (deltat == 0):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid peak separation %g" % deltat)
            msg.exec()
            return

        return peak0, npeaks, delta, deltat


    def getTOFEnergy(self, x, calibration = None):
        if calibration is None:
            current = self.current
            A = self.caldict[current]['A']
            B = self.caldict[current]['B']
            C = self.caldict[current]['C']
        else:
            A = calibration[0]
            B = calibration[1]
            C = calibration[2]

        return C + A / ((x - B) * (x - B))

    def calculateTOF(self, usedpeaks):
        """
        The calibration has the form:
                           A
            E = Vret + ---------
                       (x - B)^2

        and Vret is given as input by the user.
        """
        npeaks = len(usedpeaks)
        if npeaks < 2:
            return

        ch0, e0 = usedpeaks[0]
        ch1, e1 = usedpeaks[1]
        Vret    = float(self.caldict[self.current]['C'])
        fixed = self.caldict[self.current]['vfix']

        #calculate B
        Eterm = (e0 - Vret)/(e1 - Vret)

        a = Eterm - 1.0
        b = -2 * (Eterm * ch0 - ch1)
        c = Eterm * ch0 * ch0 - ch1 * ch1


        # I should check if b^2 - 4ac is less than zero
        # and I have to choose the appropriate sign
        B = 0.5 * (-b + numpy.sqrt(b * b - 4.0 * a * c))/a

        #calculate A
        A = (e0 - Vret) * (ch0 - B) * (ch0 - B)

        #refine if more than three peaks
        if npeaks > 3:
            parameters = numpy.array([A, B, Vret])
            x = numpy.arange(npeaks * 1.0)
            y = numpy.arange(npeaks * 1.0)
            for i in range(npeaks):
                x[i] = usedpeaks[i][0]
                y[i] = usedpeaks[i][1]
            try:
                codes = numpy.zeros((3,3), numpy.float64)
                if fixed:
                    codes[0,2] = Gefit.CFIXED
                fittedpar, chisq, sigmapar = Gefit.LeastSquaresFit(self.functionTOF,
                                               parameters,
                                               xdata=x, ydata=y,
                                               constrains=codes,
                                               model_deriv=self.functionTOFDerivative)
                if chisq != None:
                    A= fittedpar[0]
                    B= fittedpar[1]
                    Vret= fittedpar[2]
            except Exception:
                msg=qt.QMessageBox(self.AText)
                msg.setWindowTitle(sys.exc_info()[0])
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error on fit:\n%s" % sys.exc_info()[1])
                msg.exec()
        return (A, B, Vret)

    def functionTOF(self, param, x):
        A = param[0]
        B = param[1]
        C = param[2]
        return C + A / ((x - B) * (x - B))

    def functionTOFDerivative(self, param, index, x):
        A = param[0]
        B = param[1]
        if index == 0:
            return self.functionTOF([1.0, B, 0.0], x)
        if index == 1:
            return A * pow((x-B), -3)
        if index == 2:
            return numpy.ones(x.shape, numpy.float64)


    def calculate(self, usedpeaks, order=1):
        """
        used peaks has the form [[x0,e0],[x1,e1],...]
        """
        if order == "TOF":
            return self.calculateTOF(usedpeaks)
        if order in ["ID18", "ID14"]:
            order = 2
        if len(usedpeaks) == 1:
            if (usedpeaks[0][0] - 0.0) > 1.0E-20:
                return [0.0, usedpeaks[0][1]/usedpeaks[0][0], 0.0]
            else:
                _logger.debug("Division by zero")
                current = self.current
                return [self.caldict[current]['A'],
                        self.caldict[current]['B'],
                        self.caldict[current]['C']]
        if (order > 1) and (len(usedpeaks) == 2):
            usedpeaks.append([0.0,0.0])
        usedarray = numpy.array(usedpeaks).astype(numpy.float64)
        energy = usedarray[:,1]
        channel= usedarray[:,0]

        if order < 2:
            X = numpy.array([numpy.ones(len(channel)), channel])
        else:
            X= numpy.array([numpy.ones(len(channel)), channel, channel*channel])
        TX = numpy.transpose(X)
        XTX= numpy.dot(X, TX)
        INV= inverse(XTX)
        PC = numpy.dot(energy, TX)
        C  = numpy.dot(PC, INV)

        if order==1:
            result= tuple(C.tolist())+(0.,)
        else:
            result= tuple(C.tolist())
        return result

    def getdict(self):
        _logger.info("DEPRECATED. Use getDict")
        return self.getDict()

    def getDict(self):
        ddict = {}
        ddict.update(self.caldict)
        return ddict

class PeakSearchParameters(qt.QWidget):
    def __init__(self, parent=None, name="", specfit=None, config=None,
                searchbutton=1, fl=0):
        if QTVERSION < '4.0.0':
            qt.QWidget.__init__(self, parent, name, fl)
            self.setCaption(name)
        else:
            qt.QWidget.__init__(self, parent)
            self.setWindowTitle(name)

        if specfit is None:
            self.specfit = Specfit.Specfit()
        else:
            specfit      = specfit
        if config is None:
            config=self.specfit.fitconfig
        if "AutoYscaling" in config:
            autoscaling = config["AutoYscaling"]
        else:
            autoscaling = 0
        self.searchButtonFlag = searchbutton
        parameters= { "FwhmPoints":  config["FwhmPoints"],
                      "Sensitivity": config["Sensitivity"],
                      "Yscaling":    config["Yscaling"],
                      "AutoYscaling": autoscaling,
                      "AutoFwhm": 0
                     }
        self.build()
        self.setParameters(parameters)

    def build(self):
        if 1:
            if QTVERSION < '4.0.0':
                layout= qt.QVBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

            # --- parameters
                parf= qt.QHGroupBox(self)
                parf.setTitle('Search Parameters')
                parf.setAlignment(qt.Qt.AlignHCenter)
                parw= qt.QWidget(parf)
            else:
                layout= qt.QVBoxLayout(self)
                if qt.QDesktopWidget().height() < LOW_HEIGHT_THRESHOLD:
                    lowHeight = True
                else:
                    lowHeight = False
                if lowHeight:
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(0)

            # --- parameters
                parf= qt.QGroupBox(self)
                parf.layout = qt.QVBoxLayout(parf)
                parf.setTitle('Search Parameters')
                parf.setAlignment(qt.Qt.AlignHCenter)
                parw= qt.QWidget(parf)
                parf.layout.addWidget(parw)
        else:
            parw = self
        if QTVERSION < '4.0.0':
            if self.searchButtonFlag:
                grid= qt.QGridLayout(parw, 4, 3)
            else:
                grid= qt.QGridLayout(parw, 3, 3)
        else:
            grid= qt.QGridLayout(parw)
            if lowHeight:
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(2)
        lab= qt.QLabel("Sensitivity", parw)
        grid.addWidget(lab, 0, 0, qt.Qt.AlignLeft)
        lab= qt.QLabel("Fwhm (pts)", parw)
        grid.addWidget(lab, 1, 0, qt.Qt.AlignLeft)
        lab= qt.QLabel("Yscaling", parw)
        grid.addWidget(lab, 2, 0, qt.Qt.AlignLeft)
        self.sensitivityText= MyQLineEdit(parw)
        grid.addWidget(self.sensitivityText, 0, 1)
        self.fwhmText= MyQLineEdit(parw)
        grid.addWidget(self.fwhmText, 1, 1)
        self.yscalingText= MyQLineEdit(parw)
        grid.addWidget(self.yscalingText, 2, 1)
        self.fwhmAuto= qt.QCheckBox("Auto", parw)
        self.fwhmAuto.toggled[bool].connect(self.__fwhmToggled)
        grid.addWidget(self.fwhmAuto, 1, 2, qt.Qt.AlignLeft)
        self.yscalingAuto= qt.QCheckBox("Auto", parw)
        self.yscalingAuto.toggled[bool].connect(self.__yscalingToggled)
        grid.addWidget(self.yscalingAuto, 2, 2, qt.Qt.AlignLeft)
        if self.searchButtonFlag:
            self.searchButton = qt.QPushButton(parw)
            self.searchButton.setText('Search')
            grid.addWidget(self.searchButton, 3, 1)
            self.searchButton.setAutoDefault(0)
        layout.addWidget(parf)
        text  = "Enter a positive number above 2.0\n"
        text += "A higher number means a lower sensitivity."
        self.sensitivityText.setToolTip(text)
        text  = "Enter a positive integer."
        self.fwhmText.setToolTip(text)
        text  = "If your data are averaged or normalized,\n"
        text += "enter the scaling factor for your data to\n"
        text += "follow a normal distribution."
        self.yscalingText.setToolTip(text)
        for w in [self.sensitivityText, self.fwhmText, self.yscalingText]:
            validator = qt.CLocaleQDoubleValidator(w)
            w.setValidator(validator)

    def setParameters(self, pars):
        self.sensitivityText.setText(str(pars["Sensitivity"]))
        self.fwhmText.setText(str(pars["FwhmPoints"]))
        self.yscalingText.setText(str(pars["Yscaling"]))
        self.fwhmAuto.setChecked(pars["AutoFwhm"])
        self.yscalingAuto.setChecked(pars["AutoYscaling"])
        #self.specfit.configure(pars)

    def getParameters(self):
        pars= {}
        pars["Sensitivity"]= float(str(self.sensitivityText.text()))
        pars["FwhmPoints"]= float(str(self.fwhmText.text()))
        pars["Yscaling"]= float(str(self.yscalingText.text()))
        pars["AutoFwhm"]= self.fwhmAuto.isChecked()
        pars["AutoYscaling"]= self.yscalingAuto.isChecked()
        self.specfit.configure(**pars)
        return pars

    def __fwhmToggled(self, on):
        if on: self.fwhmText.setReadOnly(1)
        else: self.fwhmText.setReadOnly(0)

    def __yscalingToggled(self, on):
        if on:
            self.yscalingText.setReadOnly(1)
        else:
            self.yscalingText.setReadOnly(0)


class CalibrationParameters(qt.QWidget):
    sigCalibrationParametersSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="", calname="",
                 caldict = {},fl=0, xrd=False):
        if QTVERSION < '4.0.0':
            qt.QWidget.__init__(self, parent, name, fl)
            self.setCaption(name)
        else:
            qt.QWidget.__init__(self, parent)
        self.__xrdMode = xrd
        self.caldict=caldict
        if calname not in self.caldict.keys():
            self.caldict[calname] = {}
            self.caldict[calname]['order'] = 1
            self.caldict[calname]['A'] = 0.0
            self.caldict[calname]['B'] = 1.0
            self.caldict[calname]['C'] = 0.0
        self.currentcal = calname
        self.build()
        self.setParameters(self.caldict[calname])
        self.connections()

    def build(self):
        layout= qt.QHBoxLayout(self)
        if qt.QDesktopWidget().height() < LOW_HEIGHT_THRESHOLD:
            layout.setContentsMargins(0, 0, 0, 0)
        parw = self

        lab= qt.QLabel("Order:", parw)

        if QTVERSION <  '4.0.0':
            self.orderbox = SimpleComboBox(parw,
                                       options=['1st','2nd'])
        else:
            if self.__xrdMode:
                self.orderbox = SimpleComboBox(parw,
                                       options=['1st','2nd'])
            else:
                self.orderbox = SimpleComboBox(parw,
                                       options=['1st','2nd','TOF', 'ID14'])
        layout.addWidget(lab)
        layout.addWidget(self.orderbox)
        lab= qt.QLabel("A:", parw)
        #self.AText= qt.QLineEdit(parw)
        self.AText= MyQLineEdit(parw)
        layout.addWidget(lab)
        layout.addWidget(self.AText)
        lab= qt.QLabel("B:", parw)
        self.BText= MyQLineEdit(parw)
        layout.addWidget(lab)
        layout.addWidget(self.BText)
        self.CLabel= qt.QLabel("C:", parw)
        layout.addWidget(self.CLabel)
        self.CText= MyQLineEdit(parw)
        if QTVERSION > '4.0.0':
            self.CFixed = qt.QCheckBox(self)
            self.CFixed.setText('Fixed')
            self.CFixed.setChecked(True)
            layout.addWidget(self.CFixed)
            self.CFixed.hide()
        layout.addWidget(self.CText)

        if 0:
            self.savebut= qt.QPushButton(parw)
            self.savebut.setText("Add as")
        else:
            lab = qt.QLabel("Add as", parw)
            layout.addWidget(lab)
        self.savebox = SimpleComboBox(parw,
                                       options=self.caldict.keys())
        layout.addWidget(self.savebox)

        self.savebox.setEditable(1)
        self.savebox.setDuplicatesEnabled(0)

    def connections(self):
        self.AText.editingFinished[()].connect(self._Aslot)
        self.BText.editingFinished[()].connect(self._Bslot)
        self.CText.editingFinished[()].connect(self._Cslot)
        self.CFixed.clicked.connect(self._CFixSlot)

        if hasattr(self.orderbox, "textActivated"):
            self.orderbox.textActivated[str].connect(self.__orderbox)
            self.savebox.textActivated[str].connect(self.__savebox)
        else:
            self.orderbox.activated[str].connect(self.__orderbox)
            self.savebox.activated[str].connect(self.__savebox)
        if hasattr(self.savebox.lineEdit(), "editingFinished"):
            self.savebox.lineEdit().editingFinished[()].connect(self.__savebox)

    def setParameters(self, pars):
        self.AText.setText("%.4g" % pars["A"])
        self.BText.setText("%.4g" % pars["B"])
        self.CText.setText("%.4g" % pars["C"])
        if pars['order'] != 1:
            if pars['order'] == 'TOF':
                self.orderbox.setCurrentIndex(2)
            else:
                self.orderbox.setCurrentIndex(1)
            self.CText.setReadOnly(0)
        else:
            self.orderbox.setCurrentIndex(0)
            self.CText.setReadOnly(1)
        self.caldict[self.currentcal]["A"] = pars["A"]
        self.caldict[self.currentcal]["B"] = pars["B"]
        self.caldict[self.currentcal]["C"] = pars["C"]
        self.caldict[self.currentcal]["order"] = pars["order"]


    def getcurrentdict(self):
        return self.caldict[self.currentcal]

    def getcurrentcal(self):
        return self.current

    def getdict(self):
        _logger.info("DEPRECATED. Use getDict")
        return self.getDict()

    def getDict(self):
        return self.caldict

    def _CFixSlot(self):
        self.__orderbox(QString('TOF'))

    def __orderbox(self,qstring):
        qstring = str(qstring)
        if qstring == "1st":
            self.caldict[self.currentcal]['order'] = 1
            self.CText.setText("0.0")
            self.CText.setReadOnly(1)
            self.CLabel.setText("C:")
            self.caldict[self.currentcal]['C'] = 0.0
            if QTVERSION > '4.0.0':
                self.CFixed.hide()
        elif qstring == "TOF":
            self.caldict[self.currentcal]['order'] = 'TOF'
            self.caldict[self.currentcal]['vfix'] = self.CFixed.isChecked()
            self.CLabel.setText("Vr:")
            self.CText.setReadOnly(0)
            self.CFixed.show()
        elif qstring in ["ID14", "ID18"]:
            self.caldict[self.currentcal]['order'] = 'ID14'
            self.CLabel.setText("C:")
            self.CText.setReadOnly(1)
            if QTVERSION > '4.0.0':
                self.CFixed.hide()
        else:
            self.caldict[self.currentcal]['order'] = 2
            self.CLabel.setText("C:")
            self.CText.setReadOnly(0)
            if QTVERSION > '4.0.0':
                self.CFixed.hide()
        self.myslot(event='order')

    def __savebox(self, qstring=None):
        if qstring is None:
            qstring = self.savebox.currentText()
        key = qt.safe_str(qstring)
        if key not in self.caldict.keys():
            self.caldict[key] = {}
        if QTVERSION < '4.0.0':
            self.caldict[key]['order'] = self.orderbox.currentItem()+1
        else:
            self.caldict[key]['order'] = self.orderbox.currentIndex()+1
            if self.caldict[key]['order'] == 3:
                self.caldict[key]['order'] = "TOF"
        self.caldict[key]['A']     = float(str(self.AText.text()))
        self.caldict[key]['B']     = float(str(self.BText.text()))
        self.caldict[key]['C']     = float(str(self.CText.text()))
        self.currentcal = key
        self.myslot(event='savebox')

    def _Aslot(self):
        qstring = self.AText.text()
        try:
            value = float(str(qstring))
            self.caldict[self.currentcal]['A'] = value
            self.myslot(event='coeff')
        except Exception:
            msg=qt.QMessageBox(self.AText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            if QTVERSION < '4.0.0':
                msg.exec_loop()
            else:
                msg.exec()
            self.AText.setFocus()

    def _Bslot(self):
        qstring = self.BText.text()
        try:
            value = float(str(qstring))
            self.caldict[self.currentcal]['B'] = value
            self.myslot(event='coeff')
        except Exception:
            msg=qt.QMessageBox(self.BText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.BText.setFocus()

    def _Cslot(self):
        qstring = self.CText.text()
        try:
            value = float(str(qstring))
            self.caldict[self.currentcal]['C'] = value
            self.myslot(event='coeff')
        except Exception:
            msg=qt.QMessageBox(self.CText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.CText.setFocus()

    def myslot(self, *var, **kw):
        _logger.debug("Cal Parameters Slot %s %s", var, kw)
        _logger.debug("%s", self.caldict[self.currentcal])
        if 'event' in kw:
            ddict={}
            if (kw['event'] == 'order'):
                ddict={}
                ddict['event']         = "order"
                ddict['calname']       = self.currentcal
                ddict['caldict']       = self.caldict

            if (kw['event'] == 'coeff'):
                ddict={}
                ddict['event']         = "coeff"
                ddict['calname' ]      = self.currentcal
                ddict['caldict']       = self.caldict
            if (kw['event'] == 'savebox'):
                ddict={}
                ddict['event']         = "savebox"
                ddict['calname' ]      = self.currentcal
                ddict['caldict']       = self.caldict
            self.sigCalibrationParametersSignal.emit(ddict)

class MyQLineEdit(qt.QLineEdit):
    def __init__(self,parent=None,name=None):
        qt.QLineEdit.__init__(self,parent)
        if QTVERSION > '4.0.0':
            self.setAutoFillBackground(True)

    def setPaletteBackgroundColor(self, color):
        if QTVERSION < '4.0.0':
            qt.QLineEdit.setPaletteBackgroundColor(self,color)
        else:
            palette = self.palette()
            role = self.backgroundRole()
            palette.setColor(role,color)
            self.setPalette(palette)

    def focusInEvent(self,event):
        if QTVERSION < '4.0.0':
            self.backgroundcolor = self.paletteBackgroundColor()
        self.setPaletteBackgroundColor(
            qt.QApplication.instance().palette().color(qt.QPalette.Highlight))
        qt.QLineEdit.focusInEvent(self, event)

    def focusOutEvent(self,event):
        self.setPaletteBackgroundColor(
            qt.QApplication.instance().palette().color(qt.QPalette.Base))
        qt.QLineEdit.focusOutEvent(self, event)

class DoubleDialog(qt.QDialog):
    def __init__(self, parent=None, text=None, value=None):
        qt.QDialog.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        label = qt.QLabel(self)
        if text is None:
            text = ""
        label.setText(text)
        self.lineEdit = qt.QLineEdit(self)
        validator = qt.CLocaleQDoubleValidator(self.lineEdit)
        self.lineEdit.setValidator(validator)
        if value is not None:
            self.lineEdit.setValue('%g' % value)

        self.okButton = qt.QPushButton(self)
        self.okButton.setText('OK')

        self.cancelButton = qt.QPushButton(self)
        self.cancelButton.setText('Cancel')
        self.okButton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,
                                              qt.QSizePolicy.Fixed))
        self.cancelButton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,
                                                  qt.QSizePolicy.Fixed))

        self.mainLayout.addWidget(label, 0, 0)
        self.mainLayout.addWidget(self.lineEdit, 0, 1)
        self.mainLayout.addWidget(self.okButton, 1, 0)
        self.mainLayout.addWidget(self.cancelButton, 1, 1)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)


class InputLine(qt.QDialog):
    def __init__(self,parent ,name = "Peak Parameters",modal=1,
                 peakpars={}):
        qt.QDialog.__init__(self, parent)
        self.setModal(modal)
        self.setWindowTitle(name)
        self.resize(600,200)
        layout = qt.QVBoxLayout(self)
        self.table = PeakTableWidget.PeakTableWidget(self)
        layout.addWidget(self.table)
        self.bottom = qt.QWidget(self)
        self.bottom.layout = qt.QHBoxLayout(self.bottom)
        layout.addWidget(self.bottom)
        self.bottom.layout.addWidget(qt.HorizontalSpacer(self.bottom))
        okbutton       = qt.QPushButton(self.bottom)
        self.bottom.layout.addWidget(okbutton)
        okbutton.setText('OK')
        cancelbutton   = qt.QPushButton(self.bottom)
        cancelbutton.setText('Cancel')
        self.bottom.layout.addWidget(cancelbutton)

        okbutton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        cancelbutton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.bottom.layout.addWidget(qt.HorizontalSpacer(self.bottom))
        cancelbutton.clicked.connect(self.reject)
        okbutton.clicked.connect(self.accept)
        if 'name' in peakpars:
            peakname = peakpars['name']
        else:
            peakname = 'PEAK 1'
        if 'number' in peakpars:
            number = peakpars['number']
        else:
            number = 1
        if 'channel' in peakpars:
            channel = peakpars['channel']
        else:
            channel = 0
        if 'element' in peakpars:
            element = peakpars['element']
        else:
            element = '-'
        if 'elementline' in peakpars:
            elementline = peakpars['elementline']
        else:
            elementline = '-'
        if elementline == '-':
            if 'setenergy' in peakpars:
                setenergy = peakpars['setenergy']
            else:
                setenergy = '0.0'
        if 'use' in peakpars:
            use = peakpars['use']
        else:
            use = 1
        if 'calenergy' in peakpars:
            calenergy = peakpars['calenergy']
        else:
            calenergy = ""
        self.table.newpeakline(peakname, 1)
        self.peakname = peakname
        self.table.configure(name=peakname,
                             number=number,
                             channel=channel,
                             element=element,
                             elementline=elementline,
                             setenergy=setenergy,
                             use=use,
                             calenergy=calenergy)

    def getdict(self):
        _logger.info("DEPRECATED. Use getDict")
        return self.getDict()

    def getDict(self):
        ddict=self.table.getDict(self.peakname)
        return ddict

class McaCalCopy(qt.QDialog):
    def __init__(self,parent=None ,name = None,modal=1,fl=0,
                        legend=None,sourcecal=None,currentcal=None,caldict=None):
        #fl=qt.Qt.WDestructiveClose):
        if legend is None:
            legend= 'Active Curve'
        name = "Enter Calibration for %s" % legend
        if QTVERSION < '4.0.0':
            qt.QDialog.__init__(self, parent, name, modal, fl)
            self.setCaption(name)
        else:
            qt.QDialog.__init__(self, parent)
            self.setWindowTitle(name)
            self.setModal(modal)
        layout0 = qt.QVBoxLayout(self)
        layout0.setContentsMargins(0, 0, 0, 0)
        layout0.setSpacing(0)

        currentcal = legend
        if sourcecal is None:
            sourcecal  = [0.0,1.0,0.0]
        if caldict is None:
            caldict    = {}
        self.caldict    = caldict
        self.currentcal = currentcal
        if currentcal in caldict.keys():
            currentval = [caldict[currentcal]['A'],
                                  caldict[currentcal]['B'],
                                  caldict[currentcal]['C']]
        else:
            currentval = [0.0,1.0,0.0]

        # --- source ---
        if QTVERSION < '4.0.0':
            sgroup = qt.QHGroupBox(self)
        else:
            sgroup = qt.QGroupBox(self)
            sgrouplayout = qt.QHBoxLayout(sgroup)
            sgrouplayout.setContentsMargins(0, 0, 0, 0)
            sgrouplayout.setSpacing(0)
        sgroup.setTitle('Calibration from Source (Read Only)')
        sgroup.setAlignment(qt.Qt.AlignHCenter)
        layout0.addWidget(sgroup)
        w      = qt.QWidget(sgroup)
        wlayout= qt.QVBoxLayout(w)
        wlayout.setContentsMargins(0, 0, 0, 0)
        wlayout.setSpacing(0)
        if QTVERSION < '4.0.0':
            pass
        else:
            sgroup.layout().addWidget(w)

        """
        l           = qt.QHBox(w)
        qt.HorizontalSpacer(l)
        sourcelabel = qt.QLabel(l)
        qt.HorizontalSpacer(l)
        f = sourcelabel.font()
        f.setBold(1)
        sourcelabel.setText('Calibration from Source')
        """

        lines  = qt.QWidget(w)
        lineslayout = qt.QHBoxLayout(lines)
        lineslayout.setContentsMargins(0, 0, 0, 0)
        lineslayout.setSpacing(0)

        asl=qt.QLabel(lines)
        asl.setText('A:')
        asl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))

        as_=qt.QLineEdit(lines)
        as_.setReadOnly(1)
        as_.setText("%.4g" % sourcecal[0])


        bsl=qt.QLabel(lines)
        bsl.setText('B:')
        bsl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        bs=qt.QLineEdit(lines)
        bs.setReadOnly(1)
        bs.setText("%.4g" % sourcecal[1])

        csl=qt.QLabel(lines)
        csl.setText('C:')
        csl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        cs=qt.QLineEdit(lines)
        cs.setReadOnly(1)
        cs.setText("%.4g" % sourcecal[2])

        lineslayout.addWidget(asl)
        lineslayout.addWidget(as_)
        lineslayout.addWidget(bsl)
        lineslayout.addWidget(bs)
        lineslayout.addWidget(csl)
        lineslayout.addWidget(cs)
        wlayout.addWidget(lines)

        # --- PyMca/Current ---
        if QTVERSION < '4.0.0':
            cgroup = qt.QHGroupBox(self)
        else:
            cgroup = qt.QGroupBox(self)
            cgrouplayout = qt.QHBoxLayout(cgroup)
            cgrouplayout.setContentsMargins(0, 0, 0, 0)
            cgrouplayout.setSpacing(0)
        layout0.addWidget(cgroup)
        fontc = cgroup.font()
        fontc.setBold(1)
        cgroup.setFont(fontc)
        cgroup.setTitle('Enter New Calibration (PyMca)')
        cgroup.setAlignment(qt.Qt.AlignHCenter)
        wc = qt.QWidget(cgroup)
        wclayout = qt.QVBoxLayout(wc)
        wclayout.setContentsMargins(0, 0, 0, 0)
        wclayout.setSpacing(3)
        if QTVERSION < '4.0.0':
            pass
        else:
            cgrouplayout.addWidget(wc)

        linec  = qt.QWidget(wc)
        lineclayout = qt.QHBoxLayout(linec)
        lineclayout.setContentsMargins(0, 0, 0, 0)
        lineclayout.setSpacing(0)
        wclayout.addWidget(linec)

        acl=qt.QLabel(linec)
        #acl.setFont(font)
        acl.setText('A:')
        acl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.AText=MyQLineEdit(linec)
        self.AText.setReadOnly(0)
        self.AText.setText("%.4g" % currentval[0])

        bcl=qt.QLabel(linec)
        #bcl.setFont(font)
        bcl.setText('B:')
        bcl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.BText=MyQLineEdit(linec)
        self.BText.setReadOnly(0)
        self.BText.setText("%.4g" % currentval[1])


        ccl=qt.QLabel(linec)
        #ccl.setFont(font)
        ccl.setText('C:')
        ccl.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        self.CText=MyQLineEdit(linec)
        self.CText.setReadOnly(0)
        self.CText.setText("%.4g" % currentval[2])

        lineclayout.addWidget(acl)
        lineclayout.addWidget(self.AText)
        lineclayout.addWidget(bcl)
        lineclayout.addWidget(self.BText)
        lineclayout.addWidget(ccl)
        lineclayout.addWidget(self.CText)

        self.AText.editingFinished[()].connect(self._Aslot)
        self.BText.editingFinished[()].connect(self._Bslot)
        self.CText.editingFinished[()].connect(self._Cslot)

        # --- available for copy ---
        if len(caldict.keys()):
            wid = qt.QWidget(wc)
            wfont = wid.font()
            wfont.setBold(0)
            wid.setFont(wfont)
            layout2=qt.QHBoxLayout(wid)
            layout2.setContentsMargins(0, 0, 0, 0)
            layout2.setSpacing(3)

            copybut = qt.QPushButton(wid)
            copybut.setText('Copy From')
            copybut.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,qt.QSizePolicy.Fixed))
            copybut.clicked.connect(self.__copybuttonclicked)

            self.combo = SimpleComboBox(wid,options=caldict.keys())
            self.combo.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Fixed))
            layout2.addWidget(copybut)
            layout2.addWidget(self.combo)
            wclayout.addWidget(wid)

        # --- dialog buttons ---
        bottom = qt.QWidget(self)
        bottomlayout = qt.QHBoxLayout(bottom)
        bottomlayout.setContentsMargins(0, 0, 0, 0)
        bottomlayout.setSpacing(0)

        layout0.addWidget(bottom)
        bottomlayout.addWidget(qt.HorizontalSpacer(bottom))

        okbutton       = qt.QPushButton(bottom)
        okbutton.setText('OK')
        bottomlayout.addWidget(okbutton)


        cancelbutton   = qt.QPushButton(bottom)
        cancelbutton.setText('Cancel')
        bottomlayout.addWidget(cancelbutton)

        okbutton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        cancelbutton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
        bottomlayout.addWidget(qt.HorizontalSpacer(bottom))

        cancelbutton.clicked.connect(self.reject)
        okbutton.clicked.connect(self.accept)

        self.AText.setFocus()

    def _Aslot(self):
        qstring = self.AText.text()
        try:
            float(str(qstring))
        except Exception:
            msg=qt.QMessageBox(self.AText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.AText.setFocus()

    def _Bslot(self):
        qstring = self.BText.text()
        try:
            float(str(qstring))
        except Exception:
            msg=qt.QMessageBox(self.BText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.BText.setFocus()

    def _Cslot(self):
        qstring = self.CText.text()
        try:
            float(str(qstring))
        except Exception:
            msg=qt.QMessageBox(self.CText)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.exec()
            self.CText.setFocus()

    def __copybuttonclicked(self):
        item, text = self.combo.getCurrent()
        self.AText.setText("%.7g" % self.caldict[text]['A'])
        self.BText.setText("%.7g" % self.caldict[text]['B'])
        self.CText.setText("%.7g" % self.caldict[text]['C'])

    def getdict(self):
        _logger.info("DEPRECATED. Use getDict")
        return self.getDict()

    def getDict(self):
        ddict = {}
        ddict[self.currentcal] = {}
        ddict[self.currentcal]['A'] = float(str(self.AText.text()))
        ddict[self.currentcal]['B'] = float(str(self.BText.text()))
        ddict[self.currentcal]['C'] = float(str(self.CText.text()))
        if ddict[self.currentcal]['C'] != 0.0:
            ddict[self.currentcal]['order'] = 2
        else:
            ddict[self.currentcal]['order'] = 1
        self.caldict.update(ddict)
        return copy.deepcopy(self.caldict)


class SimpleComboBox(qt.QComboBox):
    def __init__(self,parent = None,name = None,fl = 0,options=['1','2','3']):
        qt.QComboBox.__init__(self,parent)
        self.setOptions(options)

    def setOptions(self,options=['1','2','3']):
        self.clear()
        for item in options:
            self.addItem(QString(item))

    def getCurrent(self):
        return   self.currentIndex(),str(self.currentText())

def test(x,y,legend):
    app = qt.QApplication(args)
    demo = McaCalWidget(x=x,y=y,modal=1,legend=legend)
    ret=demo.exec()
    if ret == qt.QDialog.Accepted:
        ddict=demo.getDict()
    else:
        ddict={}
    print(" output = ", ddict)
    demo.close()
    del demo
    #app.exec_loop()

if __name__ == '__main__':
    import os
    import getopt
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    options     = 'f:s:o'
    longoptions = ['file=','scan=','pkm=',
                    'output=','linear=','strip=',
                    'maxiter=','sumflag=','plotflag=']
    opts, args = getopt.getopt(
        sys.argv[1:],
        options,
        longoptions)
    inputfile = None
    scan      = None
    pkm       = None
    scankey   = None
    plotflag  = 0
    strip = 1
    linear    = 0
    for opt,arg in opts:
        if opt in ('-f','--file'):
            inputfile = arg
        if opt in ('-s','--scan'):
            scan = arg
        if opt in ('--pkm'):
            pkm = arg
        if opt in ('--linear'):
            linear = int(float(arg))
        if opt in ('--strip'):
            strip = int(float(arg))
        if opt in ('--maxiter'):
            maxiter = int(float(arg))
        if opt in ('--sum'):
            sumflag = int(float(arg))
        if opt in ('--plotflag'):
            plotflag = int(float(arg))
    if len(sys.argv) > 1:
        inputfile = sys.argv[1]
    if inputfile is None:
        from PyMca5 import PyMcaDataDir
        inputfile = os.path.join(PyMcaDataDir.PYMCA_DATA_DIR,
                                 'XRFSpectrum.mca')
    sf=specfile.Specfile(inputfile)
    if scankey is None:
        scan=sf[len(sf) - 1]
    else:
        scan=sf.select(scankey)
    nbmca=scan.nbmca()
    mcadata=scan.mca(nbmca)
    y=numpy.array(mcadata).astype(numpy.float64)
    x=numpy.arange(len(y)).astype(numpy.float64)
    test(x,y,inputfile)
