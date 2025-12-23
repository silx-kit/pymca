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
__author__ = "Tonn Rueter & V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Due to uncertainties in the experimental set-up, recorded data might be shifted unrelated
to physical effects probed in the experiment. The present plug-in calculates this shift and
corrects the data using a variety of different methods.

Usage and Description
---------------------

Data that is subject to a shift must be loaded into the plot window of the main application.
The plug-in offers two ways to treat the data:

 - A shortcut options, called *Perform FFT Shift*, calculates the shift and directly corrects
   the data.
 - The *Show Alignment Window* option, showing a window that allows for specification of the
   shift and alignment methods, as well as offering the possibility to save calculated shifts
   and load previously calculated shifts from a file.
   It is also possible to enter shift values by hand.


Once the *Alignment Window* is opened, the alignment method and the shift method must be specified.
The alignment method specifies how the shift is calculated, while the shift method determines
how the shift is applied to the data.

The table shows three columns:

 - The first one shows the plot legend of the data that will be
   corrected by the shift method.
 - The second column shows the plot legend from which the shift
   is calculated.
 - The third column shows the shift values calculated by the alignment method in
   units of the plot windows x-axis.

While columns one and two can not be edited, shift values
can be entered by hand. Another way of setting the shift values is to load them from a
existing .shift file using the Load button.

Once the shift values are set, they can either be directly applied to the data present in the
plot window, using the *Apply* button, or the data can be stored in memory. The latter options allow
to use a reference signal recorded during the experiment, to determine the shift and then apply
the shift values to a different set of data.

.. note::

  In order to match different sets of data to another, as necessary in the case of a
  reference signal, the order in which the data is added to the plot window is crucial. If one
  switches between two sets of data, where one set aligns the other one, it is highly encouraged
  to consult the table in the *Alignment window* to check if every element in the two different
  sets of data is assigned to its correct counterpart before applying the shift.


If the data in the plot window is zoomed-in to a distinct feature, only this range of the data
is used to calculate the shift.

Methods used by the plug-in
---------------------------

Alignment methods are used to calculate the shift. Present methods include FFT, MAX, FIT and
FIT DRV.

*FFT*:

    Uses the Fourier Transform of the curves to calculate their cross-correlation. The maximum
    of the correlation is determined, and yields the shift value. This method is the default option.
    Since it is not affected by the peak shape, it is fast and numerically robust.

    .. note:: The shifts are given in real space values.

*MAX*:

    Determines the maximum of each curve. The shift is given by the differences in the x-position
    of the maxima. Note that this method is highly vulnerable to noise in the data and spikes.

*FIT*:

    This method subtracts a background from the data using the SNIP algorithm and searches for peaks
    in the data. For every curve, the single most pronounced feature is selected.
    The peak is fitted by a Gaussian model. The shifts are then given by differences in the x-offsets
    of the fitted Gaussians.

*FIT DRV*:

    Uses the same procedure as the FIT method. However the fit is applied to the first derivative of
    the data. This method is only recommended for X-ray absorption data.

Shift methods are used to apply the calculated shift to the data. Present methods include *Shift x-range*
and *Inverse FFT shift*.

*Shift x-range*:

    This method adds the calculated shift value to every point.

*Inverse FFT shift*:

    Takes the Fourier Transform of a curve and multiplies the shift as a phase factor. The multiplication
    of a phase factor in Fourier space translates to a shift in the x-range in real space. The shifted data
    is given by the inverse Fourier transform.

    .. note::

        For this  process, the data needs to have a equidistant x-range. If this is not the case, the data
        will be interpolated on a equidistant x-range. Due to the cyclic nature of the Fourier transform, this
        method is recommended for data that has linear background.
"""
import numpy
import logging
import sys
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5 import PyMcaDataDir, PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaMath.fitting import SpecfitFunctions as SF
from PyMca5.PyMcaMath import SNIPModule as snip
from PyMca5.PyMcaMath.fitting.Gefit import LeastSquaresFit as LSF
from PyMca5.PyMcaMath.fitting.SpecfitFuns import gauss
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from os.path import join as pathjoin

_logger = logging.getLogger(__name__)

try:
    from PyMca5 import Plugin1DBase
except ImportError:
    _logger.warning("WARNING:AlignmentScanPlugin import from somewhere else")
    from . import Plugin1DBase


class AlignmentWidget(qt.QDialog):

    _storeCode = 2
    _colLegend      = 0 # Column number of current legends from plot window
    _colShiftLegend = 1 # Column number of curve from which the shift was calculated
    _colShift       = 2 # Shift

    def __init__(self, parent, ddict, llist, plugin):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle('Alignment Window')

        nCols = 2
        nRows = len(ddict)
        self.plugin = plugin

        # Buttons
        buttonSave = qt.QPushButton('Save')
        buttonSave.setToolTip('Shortcut: CTRL+S\n'
                             +'Save shifts to file')
        buttonSave.setShortcut(qt.QKeySequence(qt.Qt.CTRL + qt.Qt.Key_S))
        buttonLoad = qt.QPushButton('Load')
        buttonLoad.setToolTip('Shortcut: CTRL+O\n'
                             +'Load shifts from file')
        buttonLoad.setShortcut(qt.QKeySequence(qt.Qt.CTRL + qt.Qt.Key_O))
        buttonStore = qt.QPushButton('Store')
        buttonStore.setToolTip('Shortcut: ALT+S\n'
                              +'Store shifts in memory.\n')
        buttonStore.setShortcut(qt.QKeySequence(qt.Qt.ALT + qt.Qt.Key_S))
        buttonApply = qt.QPushButton('Apply')
        buttonApply.setToolTip('Shortcut: CTRL+Return\n'
                              +'Apply shift to curves present'
                              +' in the plot window')
        buttonApply.setShortcut(qt.QKeySequence(qt.Qt.CTRL + qt.Qt.Key_Return))
        buttonCancel = qt.QPushButton('Cancel')
        buttonCancel.setToolTip('Shortcut: ESC\n'
                               +'Closes the window')
        buttonCalc = qt.QPushButton('Calculate')
        buttonCalc.setToolTip('Shortcut: F5')
        buttonCalc.setShortcut(qt.QKeySequence(qt.Qt.Key_F5))

        # Table
        self.shiftTab = qt.QTableWidget(nRows, nCols)
        self.shiftTab.verticalHeader().hide()
        self.shiftTab.horizontalHeader().setStretchLastSection(True)
        self.shiftTab.setHorizontalHeaderLabels(['Legend','Shift'])

        # Shift Method selector
        self.shiftMethodComboBox = qt.QComboBox()
        self.shiftMethodComboBox.addItems(
            ['Shift x-range',
            'Inverse FFT shift'])
        shiftMethodToolTip =\
            ('Select the method that shifts the spectra\n\n'
            +'Shift x-range:\n'
            +'     Directly applies the shift to the data\'s\n'
            +'     x-range\n'
            +'Inverse FFT shift:\n'
            +'     Shifts the spectra by multiplying a\n'
            +'     phase factor to their Fourier transform. The result is\n'
            +'     transformed back to real space. Recommended for data with\n'
            +'     resp. regions with constant background.')
        self.shiftMethodComboBox.setToolTip(shiftMethodToolTip)

        # Alignment Method selector
        self.alignmentMethodComboBox = qt.QComboBox()
        self.alignmentMethodComboBox.addItems(
            ['FFT',
             'MAX',
             'FIT',
             'FIT DRV'])
        alignmentMethodToolTip =\
            ('Select the method used to calculate the shift is calculated.\n\n'
            +'FFT:\n'
            +'     Calculates the correlation between two curves using its\n'
            +'     Fourier transform. The shift is proportional to the distance of\n'
            +'     the correlation function\'s maxima.\n'
            +'MAX:\n'
            +'     Determines the shift as the distance between the maxima of\n'
            +'     two peaks\n'
            +'FIT:\n'
            +'     Guesses the most prominent feature in a spectrum and tries\n'
            +'     to fit it with a Gaussian peak. Before the fit is perform, the\n'
            +'     background is substracted. The shift is given by the difference\n'
            +'     of the center of mass between two peaks.\n'
            +'FIT DRV:\n'
            +'     Like FIT, but the fit is performed on the derivate of the\n'
            +'     spectrum. Recommended procedure for XAFS data.')
        self.alignmentMethodComboBox.setToolTip(alignmentMethodToolTip)

        # Fill table with data
        self.setDict(llist, ddict)
        self.shiftTab.resizeColumnToContents(self._colLegend)
        self.shiftTab.resizeColumnToContents(self._colShiftLegend)

        #Layouts
        topLayout = qt.QHBoxLayout()
        topLayout.addWidget(buttonCalc)
        topLayout.addWidget(qt.HorizontalSpacer())
        topLayout.addWidget(qt.QLabel('Alignment method:'))
        topLayout.addWidget(self.alignmentMethodComboBox)
        topLayout.addWidget(qt.QLabel('Shift method:'))
        topLayout.addWidget(self.shiftMethodComboBox)

        buttonLayout = qt.QHBoxLayout()
        buttonLayout.addWidget(buttonSave)
        buttonLayout.addWidget(buttonLoad)
        buttonLayout.addWidget(qt.HorizontalSpacer())
        buttonLayout.addWidget(buttonApply)
        buttonLayout.addWidget(buttonStore)
        buttonLayout.addWidget(buttonCancel)

        mainLayout = qt.QVBoxLayout()
        mainLayout.addLayout(topLayout)
        mainLayout.addWidget(self.shiftTab)
        mainLayout.addLayout(buttonLayout)
        mainLayout.setContentsMargins(1,1,1,1)
        self.setLayout(mainLayout)

        # Connects
        self.shiftTab.cellChanged.connect(self.validateInput)
        buttonApply.clicked.connect(self.accept)
        buttonCancel.clicked.connect(self.reject)
        buttonStore.clicked.connect(self.store)
        buttonSave.clicked.connect(self.saveDict)
        buttonLoad.clicked.connect(self.loadDict)

        # ..to Plugin instance
        buttonCalc.clicked.connect(self._triggerCalculateShiftClickedSlot)
        self.alignmentMethodComboBox.activated['QString'].\
                            connect(self.triggerCalculateShift)

    def _triggerCalculateShiftClickedSlot(self):
        return self.triggerCalculateShift()

    def triggerCalculateShift(self, methodName=None):
        # Need to call the plugin instance to perform calculations
        try:
            if methodName is not None:
                self.plugin.setAlignmentMethod(methodName)
            llist, ddict = self.plugin.calculateShifts()
            self.setDict(llist, ddict)
        except Exception:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Plugin error")
            msg.setText("An error has occured while executing the plugin:")
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def store(self):
        self.done(self._storeCode)

    def loadDict(self):
        openDir = PyMcaDirs.outputDir
        filters = 'PyMca (*.shift)'
        filename = qt.QFileDialog.\
                    getOpenFileName(self,
                                    'Load Shifts obtained from FFTAlignment',
                                    openDir,
                                    filters)
        # PyQt5 gives back a tuple
        if type(filename) in [type([]), type(())]:
            filename = filename[0]
        if len(filename) == 0:
            return
        inDict = ConfigDict.ConfigDict()
        try:
            inDict.read(filename)
        except IOError:
            msg = qt.QMessageBox()
            msg.setTitle('FFTAlignment Load Error')
            msg.setText('Unable to read shifts form file \'%s\''%filename)
            msg.exec()
            return
        if 'Shifts' not in inDict.keys():
            # Only if the shift file consists exclusively of ShiftList
            orderedLegends = [legend for legend in self.plugin.getOrder()]
            try:
                shiftList = inDict['ShiftList']['ShiftList']
            except KeyError:
                msg = qt.QMessageBox()
                msg.setWindowTitle('FFTAlignment Load Error')
                msg.setText('No shift information found in file \'%s\''%filename)
                msg.exec()
            ddict = dict(zip(orderedLegends, shiftList))
            llist = self.plugin.getOrder()
        else:
            llist = inDict['Order']['Order']
            ddict = inDict['Shifts']
        self.setDict(llist, ddict)

    def saveDict(self):
        saveDir = PyMcaDirs.outputDir
        ffilter = ['PyMca (*.shift)']
        try:
            filename = PyMcaFileDialogs.\
                        getFileList(parent=self,
                            filetypelist=ffilter,
                            message='Save FFT Alignment shifts',
                            mode='SAVE',
                            single=True)[0]
        except IndexError:
            # Returned list is empty
            return False
        if len(filename) == 0:
            return False
        if not str(filename).endswith('.shift'):
            filename += '.shift'
        _logger.debug('saveOptions -- Filename: "%s"', filename)
        currentOrder = self.plugin.getOrder()
        outDict = ConfigDict.ConfigDict()
        llist, ddict = self.getDict()
        outDict['Order'] = {'Order': currentOrder}
        outDict['Shifts'] = ddict
        outDict['ShiftList'] = {
            'ShiftList':[ddict[legend] for legend in currentOrder]}
        try:
            outDict.write(filename)
        except IOError:
            msg = qt.QMessageBox()
            msg.setWindowTitle('FFTAlignment Save Error')
            msg.setText('Unable to write configuration to \'%s\''%filename)
            msg.exec()
        return True

    def getAlignmentMethodName(self):
        return self.alignmentMethodComboBox.currentText()

    def getShiftMethodName(self):
        return self.shiftMethodComboBox.currentText()

    def getDict(self):
        llist, ddict = [], {}
        for idx in range(self.shiftTab.rowCount()):
            # Loop through rows
            legend      = self.shiftTab.item(idx, self._colLegend)
            shiftLegend = self.shiftTab.item(idx, self._colShiftLegend)
            value       = self.shiftTab.item(idx, self._colShift)
            try:
                floatValue = float(value.text())
            except ValueError:
                floatValue = float('NaN')
            ddict[str(legend.text())] = floatValue
            llist.append(str(shiftLegend.text()))
        return llist, ddict

    def setDict(self, llist, ddict):
        # Order in which shift are shown is not
        # necessarily the order in which they were
        # added to plot window

        curr = self.plugin.getOrder()
        keys = llist
        vals = [ddict[k] for k in keys]
        # ..or just leave them in random ddict order
        #dkeys = ddict.keys()
        #dvals = ddict.values()

        self.shiftTab.clear()
        self.shiftTab.setColumnCount(3)
        self.shiftTab.setHorizontalHeaderLabels(
                ['Legend','Shift calculated from','Shift'])
        self.shiftTab.setRowCount(len(keys))
        if len(ddict) == 0:
            return

        for j, dlist in enumerate([curr, keys, vals]):
            # j denotes the column of the table
            # j = 0: Legend, set cells inactive (greyed out)
            # j = 1: Legend from which the shift was calculated (greyed out)
            # j = 2: Shift values, set cells active
            for i in range(len(dlist)):
                # i loops through the contents of each list
                # setting every row of the table
                if (j == 0) or (j == 1):
                    elem = qt.QTableWidgetItem(dlist[i])
                    elem.setFlags(qt.Qt.ItemIsSelectable)
                elif j == 2:
                    elem = qt.QTableWidgetItem(str(dlist[i]))
                    elem.setTextAlignment(qt.Qt.AlignRight)
                    elem.setTextAlignment(qt.Qt.AlignRight + qt.Qt.AlignVCenter)
                    elem.setFlags(qt.Qt.ItemIsEditable | qt.Qt.ItemIsEnabled)
                else:
                    elem = qt.QTableWidgetItem('')
                self.shiftTab.setItem(i,j, elem)
        self.shiftTab.resizeColumnToContents(self._colLegend)
        self.shiftTab.resizeColumnToContents(self._colShiftLegend)
        self.shiftTab.resizeRowsToContents()

    def validateInput(self, row, col):
        if (col == 0) or (col == 1):
            return
        elif col == 2:
            item  = self.shiftTab.item(row, 2)
            try:
                floatValue = float(item.text())
                item.setText('%.6g'%floatValue)
            except ValueError:
                floatValue = float('NaN')
                item.setText(str(floatValue))

class AdvancedAlignmentScanPlugin(Plugin1DBase.Plugin1DBase):
    '''It calculates and corrects shifts using a variety of different methods.'''
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        self.__randomization = True
        self.__methodKeys = []
        self.methodDict = {}

        function = self.calculateAndApplyShifts
        method = "Perform FFT Alignment"
        text  = "Performs FFT based alignment and\n"
        text += "inverse FFT based shift"
        info = text
        icon = None
        self.methodDict[method] = [function,
                                   info,
                                   icon]
        self.__methodKeys.append(method)

        function = self.showShifts
        method = "Show Alignment Window"
        text  = "Displays the calculated shifts and\n"
        text += "allows to fine tune the plugin"
        info = text
        icon = None
        self.methodDict[method] = [function,
                                   info,
                                   icon]
        self.__methodKeys.append(method)

        function = self.showDocs
        method = "Show documentation"
        text  = "Shows the plug-ins documentation\n"
        text += "in a browser window"
        info = text
        icon = None
        self.methodDict[method] = [function,
                                   info,
                                   icon]
        self.__methodKeys.append(method)

        self.alignmentMethod = self.calculateShiftsFFT
        self.shiftMethod     = self.fftShift
        self.shiftDict       = {}
        self.shiftList      = []

    #Methods to be implemented by the plugin
    def getMethods(self, plottype=None):
        """
        A list with the NAMES  associated to the callable methods
        that are applicable to the specified plot.

        Plot type can be "SCAN", "MCA", None, ...
        """
#        if self.__randomization:
#            return self.__methodKeys[0:1] +  self.__methodKeys[2:]
#        else:
#            return self.__methodKeys[1:]
        return self.__methodKeys

    def getMethodToolTip(self, name):
        """
        Returns the help associated to the particular method name or None.
        """
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        """
        Returns the pixmap associated to the particular method name or None.
        """
        return None

    def applyMethod(self, name):
        """
        The plugin is asked to apply the method associated to name.
        """
        return self.methodDict[name][0]()


    def calculateAndApplyShifts(self):
        # Assure that FFT alignment & shift methods are set
        self.alignmentMethod = self.calculateShiftsFFT
        self.shiftMethod     = self.fftShift
        self.calculateShifts()
        self.applyShifts()
        # Reset shift Dictionary and legend List
        self.shiftDict  = {}
        self.shiftList = []

    def calculateShifts(self):
        """
        Generic alignment method, executes the method
        that is set under self.alignmentMethod.

        Choices are:
        - calculateShiftsFit
        - calculateShiftsFFT
        - calculateShiftsMax

        Sets self.shiftList and self.shiftDict
        """
        self.shiftList, self.shiftDict = self.alignmentMethod()
        return  self.shiftList, self.shiftDict

    def getOrder(self):
        """
        Returns the legends of the curves in the plot winow
        in the order they were added.
        """
        return self.getAllCurves(just_legend=True)

    # BEGIN Alignment Methods
    def calculateShiftsFitDerivative(self):
        return self.calculateShiftsFit(derivative=True)

    def calculateShiftsFit(self, derivative=False, thr=30):
        retDict = {}
        retList = []

        curves = self.getAllCurves()
        nCurves = len(curves)
        if nCurves < 2:
            raise ValueError("At least 2 curves needed")

        # Check if scan window is zoomed in
        xmin, xmax = self.getGraphXLimits()
        # Determine largest overlap between curves
        xmin0, xmax0 = self.getXLimits(x for (x,y,leg,info) in curves)
        if xmin0 > xmin:
            xmin = xmin0
        if xmax0 < xmax:
            xmax = xmax0
        _logger.debug('calculateShiftsFit -- xmin = %.3f, xmax = %.3f', xmin, xmax)

        # Get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            # If active curve is not set, continue with first curve
            activeCurve = curves[0]
        else:
            activeLegend = activeCurve[2]
            idx = list.index([curve[2] for curve in curves],
                             activeLegend)
            activeCurve = curves[idx]

        x0, y0 = activeCurve[0], activeCurve[1]
        idx = numpy.nonzero((xmin <= x0) & (x0 <= xmax))[0]
        x0 = numpy.take(x0, idx)
        y0 = numpy.take(y0, idx)

        if derivative:
            # Take first derivative
            y0 = numpy.diff(y0)/numpy.diff(x0)
            x0 = .5 * (x0[1:] + x0[:-1])

        peak0 = self.findPeaks(x0, y0, .80, derivative)
        if peak0:
            xp0, yp0, fwhm0, fitrange0 = peak0
        else:
            raise ValueError("No peak identified in '%s'"%activeCurve[2])
        fitp0, chisq0, sigma0 = LSF(gauss,
                                    numpy.asarray([yp0, xp0, fwhm0]),
                                    xdata=x0[fitrange0],
                                    ydata=y0[fitrange0])

        if derivative:
            _logger.debug('calculateShiftsFit -- Results (Leg, PeakPos, Shift):')
        else:
            _logger.debug('calculateShiftsFitDerivative -- Results (Leg, PeakPos, Shift):')
        for x,y,legend,info in curves:
            idx = numpy.nonzero((xmin <= x) & (x <= xmax))[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)

            if derivative:
                # Take first derivative
                y = numpy.diff(y)/numpy.diff(x)
                x = .5 * (x[1:] + x[:-1])

            peak = self.findPeaks(x, y, .80, derivative)
            if peak:
                xp, yp, fwhm, fitrange = peak
            else:
                raise ValueError("No peak identified in '%s'"%activeCurve[2])
            try:
                fitp, chisq, sigma = LSF(gauss,
                                         numpy.asarray([yp, xp, fwhm]),
                                         xdata=x[fitrange],
                                         ydata=y[fitrange])
                # Shift is difference in peak's x position
                shift = fitp0[1] - fitp[1]
            except numpy.linalg.linalg.LinAlgError:
                msg = qt.QMessageBox(None)
                msg.setWindowTitle('Alignment Error')
                msg.setText('Singular matrix encountered during least squares fit.')
                msg.setStandardButtons(qt.QMessageBox.Ok)
                msg.exec()
                shift = float('NaN')
                fitp, chisq, sigma = [None, None, None], 0., 0.
            key = legend
            retList.append(key)
            retDict[key] = shift
            _logger.debug('\t%s\t%.3f\t%.3f', legend, fitp[1], shift)
        return retList, retDict

    def calculateShiftsMax(self):
        retDict = {}
        retList = []

        curves = self.getAllCurves()
        nCurves = len(curves)

        if nCurves < 2:
            raise ValueError("At least 2 curves needed")
            return

        # Check if plotwindow is zoomed in
        xmin, xmax = self.getGraphXLimits()
        # Determine largest overlap between curves
        xmin0, xmax0 = self.getXLimits(x for (x,y,leg,info) in curves)
        if xmin0 > xmin:
            xmin = xmin0
        if xmax0 < xmax:
            xmax = xmax0

        # Get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            # If active curve is not set, continue with first curve
            activeCurve = curves[0]
        else:
            activeLegend = activeCurve[2]
            idx = list.index([curve[2] for curve in curves],
                             activeLegend)
            activeCurve = curves[idx]

        x0, y0 = activeCurve[0], activeCurve[1]
        idx = numpy.nonzero((xmin <= x0) & (x0 <= xmax))[0]
        x0 = numpy.take(x0, idx)
        y0 = numpy.take(y0, idx)

        # Determine the index of maximum in active curve
        shift0 = numpy.argmax(y0)
        _logger.debug('calculateShiftsMax -- Results:')
        _logger.debug('\targmax(y) shift')
        for x, y, legend, info in curves:
            idx = numpy.nonzero((xmin <= x) & (x <= xmax))[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)

            shifty = numpy.argmax(y)
            shift = x0[shift0] - x[shifty]
            key = legend
            retList.append(key)
            retDict[key] = shift
            _logger.debug('\t%d %.3f', x[shifty], shift)
        return retList, retDict

    def calculateShiftsFFT(self, portion=.95):
        retDict = {}
        retList = []

        curves = self.interpolate()
        nCurves = len(curves)
        if nCurves < 2:
            raise ValueError("At least 2 curves needed")

        # Check if scan window is zoomed in
        xmin, xmax = self.getGraphXLimits()
        # Determine largest overlap between curves
        xmin0, xmax0 = self.getXLimits(x for (x,y,leg,info) in curves)
        if xmin0 > xmin:
            xmin = xmin0
        if xmax0 < xmax:
            xmax = xmax0
        _logger.debug('calculateShiftsFFT -- xmin = %.3f, xmax = %.3f', xmin, xmax)

        # Get active curve
        activeCurve = self.getActiveCurve()
        if activeCurve is None:
            # If active curve is not set, continue with first curve
            activeCurve = curves[0]
        else:
            activeLegend = activeCurve[2]
            idx = list.index([curve[2] for curve in curves],
                             activeLegend)
            activeCurve = curves[idx]

        x0, y0 = activeCurve[0], activeCurve[1]
        idx = numpy.nonzero((xmin <= x0) & (x0 <= xmax))[0]
        x0 = numpy.take(x0, idx)
        y0 = self.normalize(y0)
        y0 = numpy.take(y0, idx)

        fft0 = numpy.fft.fft(y0)
        _logger.debug('calculateShiftsFFT -- results (Legend len(idx) shift):')
        for x,y,legend,info in curves:
            idx = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)
            ffty = numpy.fft.fft(y)
            shiftTmp = numpy.fft.ifft(fft0 * ffty.conjugate()).real
            shiftPhase = numpy.zeros(shiftTmp.shape, dtype=shiftTmp.dtype)
            m = shiftTmp.size//2
            shiftPhase[m:] = shiftTmp[:-m]
            shiftPhase[:m] = shiftTmp[-m:]
            # Normalize shiftPhase to standardize thresholding
            shiftPhase = self.normalize(shiftPhase)

            # Thresholding
            xShiftMax = shiftPhase.argmax()
            left, right = xShiftMax, xShiftMax
            threshold = portion * shiftPhase.max()
            while (shiftPhase[left] > threshold)&\
                  (shiftPhase[right] > threshold):
                left  -= 1
                right += 1
            idx = numpy.arange(left, right+1, 1, dtype=int)
            # The shift is determined by center-of-mass around shiftMax
            shiftTmp = (shiftPhase[idx] * idx/shiftPhase[idx].sum()).sum()
            shift = (shiftTmp - m) * (x[1] - x[0])

            key = legend
            retList.append(key)
            retDict[key] = shift
            _logger.debug('\t%s\t%d\t%f', legend, len(idx), shift)
        return retList, retDict
    # END Alignment Methods

    def applyShifts(self):
        """
        Generic shift method. The method shifts curves
        according to the shift stored in self.shiftDict
        and executes the method stored in self.shiftMethod.

        Curves are sorted with respect to their legend,
        the values of self.shiftDict are sorted with
        respect to their key.
        """
        if len(self.shiftDict) == 0:
            msg = qt.QMessageBox(None)
            msg.setWindowTitle('Alignment Error')
            msg.setText('No shift data present.')
            msg.setStandardButtons(qt.QMessageBox.Ok)
            msg.exec()
            return False

        # Check if interpolation is needed
        if self.shiftMethod == self.fftShift:
            curves = self.interpolate()
        else:
            curves = self.getAllCurves()

        if len(self.shiftList) != len(curves):
            msg = qt.QMessageBox(None)
            msg.setWindowTitle('Alignment Error')
            msg.setText(
                """Number of shifts does not match the number of curves.
                Do you want to continue anyway?""")
            msg.setStandardButtons(qt.QMessageBox.Ok)
            msg.setStandardButtons(qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
            msg.setDefaultButton(qt.QMessageBox.Ok)

            if msg.exec() != qt.QMessageBox.Ok:
                return False

        _logger.debug('applyShifts -- Shifting ...')
        for idx, (x, y, legend, info) in enumerate(curves):
            shift = self.shiftDict[legend]

            if shift is None:
                _logger.debug('\tCurve \'%s\' not found in shiftDict\n%s',
                              legend, str(self.shiftDict))
                continue
            if shift == float('NaN'):
                _logger.debug('\tCurve \'%s\' has NaN shift', legend)
                continue

            # Limit shift to zoomed in area
            xmin, xmax = self.getGraphXLimits()
            mask = numpy.nonzero((xmin<=x) & (x<=xmax))[0]
            # Execute method stored in self.shiftMethod
            xShifted, yShifted = self.shiftMethod(shift, x[mask], y[mask])
            if idx == 0:
                replace = True
            else:
                replace = False
            if idx == (len(curves)-1):
                replot = True
            else:
                replot = False
            # Check if scan number is adopted by new curve
            _logger.debug('\'%s\' -- shifts -> \'%s\' by %f', self.shiftList[idx], legend, shift)
            #selectionlegend = info.get('selectionlegend', legend)
            selectionlegend = legend
            self.addCurve(xShifted, yShifted,
                          (selectionlegend + ' SHIFT'),
                          info=info,
                          replace=replace,
                          replot=replot)
        return True


    # BEGIN Shift Methods
    def fftShift(self, shift, x, y):
        yShifted = numpy.fft.ifft(
             numpy.exp(-2.0*numpy.pi*numpy.sqrt(numpy.complex(-1))*\
                numpy.fft.fftfreq(len(x), d=x[1]-x[0])*shift)*numpy.fft.fft(y))
        return x, yShifted.real

    def xShift(self, shift, x, y):
        return x+shift, y
    # END Shift Methods

    def showShifts(self):
        """
        Creates an instance of Alignment Widget that
        allows to

        - Calculate, display  & save/store shifts
        - Load existing shift data
        - Select different alignment and shift methods
        """
        # Empty shift table in the beginning
        widget = AlignmentWidget(None, self.shiftDict, self.shiftList, self)
        ret = widget.exec()
        if ret == 1:
            # Result code Apply
            self.shiftList, self.shiftDict = widget.getDict()
            # self.shiftList = self.getOrder()
            self.setShiftMethod(widget.getShiftMethodName())
            self.applyShifts()
            self.shiftDict = {}
            self.shiftList = []
        elif ret == 2:
            # Result code Store
            self.shiftList, self.shiftDict = widget.getDict()
            self.shiftList = self.getOrder() # Remember order of scans
            self.setShiftMethod(widget.getShiftMethodName())
        else:
            # Dialog is canceled
            self.shiftDict = {}
            self.shiftList = []
        widget.destroy() # Widget should be destroyed after finishing method
        return

    # BEGIN Helper Methods
    def setShiftMethod(self, methodName):
        """
        Method receives methodName from AlignmentWidget
        instance and assigns the according shift method.
        """
        _logger.debug('setShiftMethod -- %s', methodName)
        methodName = str(methodName)
        if methodName == 'Inverse FFT shift':
            self.shiftMethod = self.fftShift
        elif methodName == 'Shift x-range':
            self.shiftMethod = self.xShift
        else:
            # Unknown method name, use fftShift as default
            self.shiftMethod = self.fftShift

    def setAlignmentMethod(self, methodName):
        """
        Method receives methodName from AlignmentWidget
        instance and assigns the according alignment method.
        """
        _logger.debug('setAlignmentMethod -- %s', methodName)
        methodName = str(methodName)
        if methodName == 'FFT':
            self.alignmentMethod = self.calculateShiftsFFT
        elif methodName == 'MAX':
            self.alignmentMethod = self.calculateShiftsMax
        elif methodName == 'FIT':
            self.alignmentMethod = self.calculateShiftsFit
        elif methodName == 'FIT DRV':
            self.alignmentMethod = self.calculateShiftsFitDerivative
        else:
            # Unknown method name, use fftShift as default
            self.alignmentMethod = self.calculateShiftsFFT

    def getAllCurves(self, just_legend=False):
        """
        Ensures that the x-range of the curves
        is strictly monotonically increasing.
        Conserves curves legend and info dictionary.
        """
        curves = Plugin1DBase.Plugin1DBase.getAllCurves(self, just_legend=just_legend)
        if just_legend:
            return curves

        processedCurves = []
        for curve in curves:
            x, y, legend, info = curve[0:4]
            xproc = x[:]
            yproc = y[:]
            # Sort
            idx = numpy.argsort(xproc, kind='mergesort')
            xproc = numpy.take(xproc, idx)
            yproc = numpy.take(yproc, idx)
            # Ravel, Increasing
            xproc = xproc.ravel()
            idx = numpy.nonzero((xproc[1:] > xproc[:-1]))[0]
            xproc = numpy.take(xproc, idx)
            yproc = numpy.take(yproc, idx)
            processedCurves += [(xproc, yproc, legend, info)]
        return processedCurves

    def interpolate(self, factor=1.):
        """
        Input
        -----
        factor : float
            factor used to oversample existing data, use
            with caution.

        Interpolates all existing curves to an equidistant
        x-range using the either the active or the first
        curve do determine the number of data points.
        Use this method instead of self.getAllCurves() when
        performin FFT related tasks.

        Returns
        -------
        interpCurves : ndarray
            Array containing the interpolated curves shown
            in the plot window.
            Format: [(x0, y0, legend0, info0), ...]
        """
        curves = self.getAllCurves()
        if len(curves) < 1:
            _logger.debug('interpolate -- no curves present')
            raise ValueError("At least 1 curve needed")
            return

        activeCurve = self.getActiveCurve()
        if not activeCurve:
            activeCurve = curves[0]
        else:
            activeLegend = activeCurve[2]
            idx = list.index([curve[2] for curve in curves],
                             activeLegend)
            activeCurve = curves[idx]
        activeX, activeY, activeLegend, activeInfo = activeCurve[0:4]

        # Determine average spaceing between Datapoints
        step = numpy.average(numpy.diff(activeX))
        xmin, xmax = self.getXLimits([x for (x,y,leg,info) in curves],
                                     overlap=False)
        num  = int(factor * numpy.ceil((xmax-xmin)/step))

        # Create equidistant x-range, exclude first and last point
        xeq = numpy.linspace(xmin, xmax, num, endpoint=False)[:-1]

        # Interpolate on sections of xeq
        interpCurves = []
        for (x,y,legend,info) in curves:
            idx = numpy.nonzero((x.min()<xeq) & (xeq<x.max()))[0]
            xi = numpy.take(xeq, idx)
            yi = SpecfitFuns.interpol([x], y, xi.reshape(-1,1), y.min())
            yi = numpy.ravel(yi)
            interpCurves += [(xi, yi, legend, info)]
        return interpCurves

    def getXLimits(self, values, overlap=True):
        """
        Input
        -----
        overlap : bool
            True  -> returns minimal and maximal x-values
                     that are that are still lie within the
                     x-ranges of all curves in plot window
            False -> returns minimal and maximal x-values of
                     all curves in plot window

        Returns
        -------
        xmin0, xmax0 : float
        """
        if overlap:
            xmin0, xmax0 = -numpy.inf, numpy.inf
        else:
            xmin0, xmax0 = numpy.inf, -numpy.inf
        for x in values:
            xmin = x.min()
            xmax = x.max()
            if overlap:
                if xmin > xmin0:
                    xmin0 = xmin
                if xmax < xmax0:
                    xmax0 = xmax
            else:
                if xmin < xmin0:
                    xmin0 = xmin
                if xmax > xmax0:
                    xmax0 = xmax
        _logger.debug('getXLimits -- overlap = %s, xmin = %.3f, xmax =%.3f',
                      overlap, xmin0, xmax0)
        return xmin0, xmax0

    def normalize(self, y):
        """
        Normalizes spectrum to values between zero and one.
        """
        ymax, ymin = y.max(), y.min()
        return (y-ymin)/(ymax-ymin)

    def findPeaks(self, x, y, thr, derivative):
        """
        Input
        -----
        x,y : ndarrays
            Arrays contain curve intformation
        thr : float
            Threshold in percent of normalized maximum
        derivative : bool
            The derivative of a curve is being fitted

        Finds most prominent feature contained in y
        and tries to estimate starting parameters for a
        Gaussian least squares fit (LSF). Recommends values
        used to fit the Gaussian.

        Return
        ------
        xpeak, ypeak, fwhm : float
            Estimated values for x-position, amplitude
            and width of the Gaussian
        fwhmIdx : ndarray
            Indices determine the range on which the LSF
            is performed
        """
        # Use SNIP algorithm for background substraction &
        # seek method for peak detection
        sffuns = SF.SpecfitFunctions()
        if derivative:
            # Avoid BG substraction & normalization if
            # fitting the derivate of a curve
            ybg = y
            ynorm = y/(abs(y.max())+abs(y.min()))
        else:
            ybg = y-snip.getSnip1DBackground(y, len(y)//thr) # USER INPUT!!!
            # Normalize background substracted data to
            # standardize the yscaling of seek method
            #ynorm = (ybg - ybg.min())/(ybg.max()-ybg.min())
            ynorm = self.normalize(ybg)

        # Replace by max()?
        try:
            # Calculate array with all peak indices
            peakIdx = numpy.asarray(sffuns.seek(ybg, yscaling=1000.), dtype=int)
            # Extract highest peak
            sortIdx = y[peakIdx].argsort()[-1]
        except IndexError:
            _logger.debug('No peaks found..')
            return None
        except SystemError:
            _logger.debug('Peak search failed. Continue with y maximum')
            peakIdx = [ybg.argmax()]
            sortIdx = 0
        xpeak = float(x[peakIdx][sortIdx])
        ypeak = float(y[peakIdx][sortIdx])
        ypeak_norm = float(ynorm[peakIdx][sortIdx])
        ypeak_bg   = float(ybg[peakIdx][sortIdx])

        # Estimate FWHM
        fwhmIdx = numpy.nonzero(ynorm >= thr*ypeak_norm)[0]
        #fwhmIdx = numpy.nonzero(ybg >= thr*ypeak_bg)[0]
        # Underestimates FWHM
        x0, x1 = x[fwhmIdx].min(), x[fwhmIdx].max()
        fwhm = x1 - x0

        return xpeak, ypeak, fwhm, fwhmIdx
    # END Helper Methods

    def showDocs(self):
        """
        Displays QTextBrowser showing the documentation
        """
        helpFileName = pathjoin(PyMcaDataDir.PYMCA_DOC_DIR,
                                "HTML",
                                "AdvancedAlignmentScanPlugin.html")
        self.helpFileBrowser = qt.QTextBrowser()
        self.helpFileBrowser.setWindowTitle('Alignment Scan Plug-in Documentation')
        self.helpFileBrowser.setLineWrapMode(qt.QTextEdit.FixedPixelWidth)
        self.helpFileBrowser.setLineWrapColumnOrWidth(500)
        self.helpFileBrowser.resize(520,300)
        try:
            helpFileHandle = open(helpFileName)
            helpFileHTML = helpFileHandle.read()
            helpFileHandle.close()
            self.helpFileBrowser.setHtml(helpFileHTML)
        except IOError:
            msg = qt.QMessageBox()
            msg.setWindowTitle('Alignment Scan Error')
            msg.setText('No help file found.')
            msg.exec()
            _logger.debug('XMCDWindow -- init: Unable to read help file')
            self.helpFileBrowser = None
        if self.helpFileBrowser is not None:
            self.helpFileBrowser.show()
            self.helpFileBrowser.raise_()

MENU_TEXT = "Advanced Alignment Plugin"
def getPlugin1DInstance(plotWindow, **kw):
    ob = AdvancedAlignmentScanPlugin(plotWindow)
    return ob

if __name__ == "__main__":
    app = qt.QApplication([])

    a = AlignmentWidget()
    a.show()

    x = numpy.arange(250, 750, 2, dtype=float)
    y1 = 1.0 + 50.0 * numpy.exp(-0.001*(x-500)**2) + 2.*numpy.random.random(250)
    y2 = 1.0 + 20.5 * numpy.exp(-0.005*(x-600)**2) + 2.*numpy.random.random(250)

    app.exec()
