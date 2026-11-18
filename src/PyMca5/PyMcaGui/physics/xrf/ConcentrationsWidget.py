#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import copy
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt

if hasattr(qt, 'QString'):
    QString = qt.QString
else:
    QString = str

QTVERSION = qt.qVersion()

XRFMC_FLAG = True

_logger = logging.getLogger(__name__)

try:
    from PyMca5.PyMcaGui.misc.TableWidget import TableWidget
    QTable = TableWidget
    USE_QTABLE_WIDGET = False
except Exception:
    _logger.warning("Cannot import clipboard enabled table")
    QTable = qt.QTableWidget
    USE_QTABLE_WIDGET = True

from PyMca5.PyMcaGui.misc import CalculationThread
from PyMca5.PyMcaPhysics.xrf import ConcentrationsTool
from PyMca5.PyMcaPhysics.xrf import Elements
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaMisc import CliUtils


class Concentrations(qt.QWidget):
    sigConcentrationsSignal = qt.pyqtSignal(object)
    sigClosed = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="Concentrations"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.build()
        self.setParameters = self.concentrationsWidget.setParameters
        self.getParameters = self.concentrationsWidget.getParameters
        self.setTimeFactor = self.concentrationsWidget.setTimeFactor
        self.__lastVar = None
        self.__lastKw = None

    def build(self):
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.concentrationsTool = ConcentrationsTool.ConcentrationsTool()
        self.concentrationsWidget = ConcentrationsWidget(self)
        self.concentrationsTable = ConcentrationsTable(self)
        layout.addWidget(self.concentrationsWidget)
        layout.addWidget(self.concentrationsTable)
        layout.setStretchFactor(self.concentrationsWidget, 0)
        layout.setStretchFactor(self.concentrationsTable, 1)
        self.concentrationsWidget.sigConcentrationsWidgetSignal.connect( \
                        self.mySlot)
        self.concentrationsTool.configure(
            self.concentrationsWidget.getParameters())
        self.__connected = True

    def mySlot(self, ddict=None):
        if ddict is None:
            ddict = {}
        if not self.__connected:
            return
        try:
            # try to avoid multiple triggering on Mac OS
            self.__connected = False
            self.concentrationsTable.setFocus()
            app = qt.QApplication.instance()
            app.processEvents()
        finally:
            self.__connected = True
        if ddict['event'] == 'updated':
            self.concentrationsTool.configure(ddict)
            if self.__lastKw is not None:
                addInfo = False
                if 'addinfo' in self.__lastKw:
                    if self.__lastKw['addinfo']:
                        addInfo = True
                try:
                    if addInfo:
                        concentrations, info = self.processFitResult(*self.__lastVar, **self.__lastKw)
                    else:
                        concentrations = self.processFitResult(*self.__lastVar, **self.__lastKw)
                    ddict['concentrations'] = concentrations
                except Exception:
                    self.__lastKw = None
                    raise
            self.mySignal(ddict)

    def mySignal(self, ddict=None):
        if ddict is None:
            ddict = {}
        self.sigConcentrationsSignal.emit(ddict)

    def processFitResult(self, *var, **kw):
        self.__lastVar = var
        self.__lastKw = kw
        addInfo = False
        if 'addinfo' in kw:
            if kw['addinfo']:
                addInfo = True
        if _logger.getEffectiveLevel() == logging.DEBUG:
            if addInfo:
                ddict, info = self.concentrationsTool.processFitResult(*var, **kw)
                self.concentrationsTable.fillFromResult(ddict)
                return ddict, info
            else:
                ddict = self.concentrationsTool.processFitResult(*var, **kw)
                self.concentrationsTable.fillFromResult(ddict)
                return ddict
        try:
            threadResult = self._submitThread(*var, **kw)
            if type(threadResult) == type((1,)):
                if len(threadResult):
                    if threadResult[0] == "Exception":
                        raise Exception(threadResult[1], threadResult[2])
            if addInfo:
                ddict, info = threadResult
                self.concentrationsTable.fillFromResult(ddict)
                return ddict, info
            else:
                ddict = threadResult
                self.concentrationsTable.fillFromResult(ddict)
                return ddict
        except Exception:
            self.__lastKw = None
            self.concentrationsTable.setRowCount(0)
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("%s" % sys.exc_info()[1])
            msg.exec()

    def closeEvent(self, event):
        qt.QWidget.closeEvent(self, event)
        ddict = {}
        ddict['event'] = 'closed'
        self.sigClosed.emit(ddict)

    def _submitThread(self, *var, **kw):
        message = "Calculating concentrations"
        sthread = CalculationThread.CalculationThread( \
                                calculation_method=self.concentrationsTool.processFitResult,
                                calculation_vars=var,
                                calculation_kw=kw,
                                expand_vars=True,
                                expand_kw=True)
        sthread.start()
        CalculationThread.waitingMessageDialog(sthread,
                                           message=message,
                                           parent=self,
                                           modal=False,
                                           update_callback=None,
                                           frameless=True)
        threadResult = sthread.getResult()
        self.raise_()
        return threadResult

class ConcentrationsWidget(qt.QWidget):
    sigConcentrationsWidgetSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="Concentrations"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self._liveTime = None

        self.build()
        ddict = {}
        ddict['usematrix'] = 0
        ddict['useattenuators'] = 1
        ddict['usexrfmc'] = 0
        ddict['flux'] = 1.0E10
        ddict['time'] = 1.0
        ddict['useautotime'] = 0
        ddict['area'] = 30.0
        ddict['distance'] = 10.0
        ddict['reference'] = "Auto"
        ddict['mmolarflag'] = 0
        self.setParameters(ddict)

    def build(self):
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        buttonGroup = qt.QGroupBox(self)
        buttonGroup.layout = qt.QVBoxLayout(buttonGroup)
        buttonGroup.layout.setContentsMargins(0, 0, 0, 0)
        buttonGroup.layout.setSpacing(0)
        layout.addWidget(buttonGroup)
        self.fluxCheckBox = qt.QCheckBox(buttonGroup)
        self.fluxCheckBox.setText("From fundamental parameters")
        wf = qt.QWidget(buttonGroup)
        wf.layout = qt.QHBoxLayout(wf)
        wf.layout.setContentsMargins(0, 0, 0, 0)
        wf.layout.setSpacing(0)
        wf.layout.addWidget(qt.HorizontalSpacer(wf))
        self.fundamentalWidget = FundamentalWidget(wf)
        wf.layout.addWidget(self.fundamentalWidget)
        wf.layout.addWidget(qt.HorizontalSpacer(wf))
        self.matrixCheckBox = qt.QCheckBox(buttonGroup)
        self.matrixCheckBox.setText("From matrix composition")
        self.fluxCheckBox.setChecked(True)

        wm = qt.QWidget(buttonGroup)
        wm.layout = qt.QHBoxLayout(wm)
        wm.layout.setContentsMargins(0, 0, 0, 0)
        wm.layout.setSpacing(0)
        wm.layout.addWidget(qt.HorizontalSpacer(wm))
        referenceLabel = qt.QLabel(wm)
        wm.layout.addWidget(referenceLabel)
        referenceLabel.setText("Matrix Reference Element:")
        #self.referenceCombo=MyQComboBox(wm)
        #self.referenceCombo=qt.QComboBox(wm)
        #self.referenceCombo.setEditable(True)
        #self.referenceCombo.insertItem('Auto')
        self.referenceLine = MyQLineEdit(wm)
        wm.layout.addWidget(self.referenceLine)
        fmetrics = self.referenceLine.fontMetrics()
        fmtext = '#######'
        if hasattr(fmetrics, "maxWidth"):
            self.referenceLine.setFixedWidth(fmetrics.maxWidth()*len(fmtext))
        else:
            #deprecated
            _logger.info("Using deprecated method")
            self.referenceLine.setFixedWidth(fmetrics.width(fmtext))

        wm.layout.addWidget(qt.HorizontalSpacer(wm))
        self.referenceLine.sigMyQLineEditSignal.connect( \
                     self._referenceLineSlot)
        buttonGroup.layout.addWidget(self.fluxCheckBox)
        buttonGroup.layout.addWidget(wf)
        buttonGroup.layout.addWidget(self.matrixCheckBox)
        buttonGroup.layout.addWidget(wm)

        #self.fundamentalWidget.setEnabled(False)
        self.attenuatorsCheckBox = qt.QCheckBox(self)
        self.attenuatorsCheckBox.setText("Consider attenuators in calculations")
        self.attenuatorsCheckBox.setDisabled(True)
        #Multilayer secondary excitation
        self.secondaryCheckBox = qt.QCheckBox(self)
        self.secondaryCheckBox.setText("Consider secondary excitation")
        self.tertiaryCheckBox = qt.QCheckBox(self)
        self.tertiaryCheckBox.setText("Consider tertiary excitation")
        layout.addWidget(self.attenuatorsCheckBox)
        layout.addWidget(self.secondaryCheckBox)
        layout.addWidget(self.tertiaryCheckBox)
        #XRFMC secondary excitation
        if XRFMC_FLAG:
            self.xrfmcCheckBox = qt.QCheckBox(self)
            self.xrfmcCheckBox.setText("use Monte Carlo code to correct higher order excitations")
            layout.addWidget( self.xrfmcCheckBox)

        #mM checkbox
        self.mMolarCheckBox = qt.QCheckBox(self)
        self.mMolarCheckBox.setText("Elemental mM concentrations (assuming 1 l of solution is 1000 * matrix_density grams)")
        layout.addWidget(self.mMolarCheckBox)

        layout.addWidget(qt.VerticalSpacer(self))
        buttonGroup.show()
        self.fluxCheckBox.clicked.connect(self._fluxCheckBoxSlot)
        self.matrixCheckBox.clicked.connect(self.checkBoxSlot)
        self.attenuatorsCheckBox.clicked.connect(self.checkBoxSlot)
        self.secondaryCheckBox.clicked.connect(self._secondaryCheckBoxSlot)
        self.tertiaryCheckBox.clicked.connect(self._tertiaryCheckBoxSlot)
        if XRFMC_FLAG:
            self.xrfmcCheckBox.clicked.connect(self._xrfmcCheckBoxSlot)

        self.mMolarCheckBox.clicked.connect(self.checkBoxSlot)

        self.fundamentalWidget.flux.sigMyQLineEditSignal.connect( \
            self._mySignal)
        self.fundamentalWidget.area.sigMyQLineEditSignal.connect( \
            self._mySignal)
        self.fundamentalWidget.time.sigMyQLineEditSignal.connect( \
            self._mySignal)
        self.fundamentalWidget.distance.sigMyQLineEditSignal.connect( \
            self._mySignal)
        self.fundamentalWidget.autoTimeCheckBox.clicked.connect( \
                self.__autoTimeSlot)

    def __autoTimeSlot(self):
        return self._autoTimeSlot()

    def _autoTimeSlot(self, signal=True):
        if self.fundamentalWidget.autoTimeCheckBox.isChecked():
            if self._liveTime is None:
                self.fundamentalWidget.autoTimeCheckBox.setChecked(False)
                self.fundamentalWidget.time.setEnabled(True)
            else:
                self.fundamentalWidget.time.setText("%.8g" % self._liveTime)
                self.fundamentalWidget.time.setEnabled(False)
                if signal:
                    self._mySignal()
        else:
            self.fundamentalWidget.time.setEnabled(True)

    def setTimeFactor(self, factor=None, signal=False):
        self._liveTime = factor
        if factor is None:
            self.fundamentalWidget.autoTimeCheckBox.setChecked(False)
            self.fundamentalWidget.time.setEnabled(True)
        else:
            # act according to the settings
            self._autoTimeSlot(signal=signal)

    def _fluxCheckBoxSlot(self):
        if self.fluxCheckBox.isChecked():
            self.matrixCheckBox.setChecked(False)
        else:
            self.matrixCheckBox.setChecked(True)
        self.checkBoxSlot()

    def _secondaryCheckBoxSlot(self):
        if self.secondaryCheckBox.isChecked():
            if XRFMC_FLAG:
                self.xrfmcCheckBox.setChecked(False)
            self.tertiaryCheckBox.setChecked(False)
        self.checkBoxSlot()

    def _tertiaryCheckBoxSlot(self):
        if self.tertiaryCheckBox.isChecked():
            if XRFMC_FLAG:
                self.xrfmcCheckBox.setChecked(False)
            self.secondaryCheckBox.setChecked(False)
        self.checkBoxSlot()

    def _xrfmcCheckBoxSlot(self):
        if self.xrfmcCheckBox.isChecked():
            self.secondaryCheckBox.setChecked(False)
        self.checkBoxSlot()

    def checkBoxSlot(self):
        if self.matrixCheckBox.isChecked():
            self.fundamentalWidget.setInputDisabled(True)
            self.referenceLine.setEnabled(True)
            self.fluxCheckBox.setChecked(False)
        else:
            self.fundamentalWidget.setInputDisabled(False)
            self.referenceLine.setEnabled(False)
            self.fluxCheckBox.setChecked(True)
        self._mySignal()

    def _referenceLineSlot(self, ddict):
        if ddict['event'] == "returnPressed":
            current = str(self.referenceLine.text())
            current = current.replace(' ', '')
            if (current == '') or (current.upper() == 'AUTO'):
                pass
            elif len(current) == 2:
                current = current.upper()[0] + current.lower()[1]
            elif len(current) == 1:
                current = current.upper()[0]
            else:
                self.referenceLine.setText('Auto')
                msg = qt.QMessageBox(self.referenceLine)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Element %s" % current)
                msg.exec()
                self.referenceLine.setFocus()
                return
            if (current == '') or (current.upper() == 'AUTO'):
                self.referenceLine.setText('Auto')
                self._mySignal()
            elif not Elements.isValidFormula(current):
                self.referenceLine.setText('Auto')
                msg = qt.QMessageBox(self.referenceLine)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Element %s" % current)
                msg.exec()
                self.referenceLine.setFocus()
            else:
                self.referenceLine.setText(current)
                self._mySignal()

    def _mySignal(self, dummy=None):
        ddict = self.getParameters()
        ddict['event'] = 'updated'
        self.sigConcentrationsWidgetSignal.emit(ddict)

    def getParameters(self):
        ddict = {}
        if self.matrixCheckBox.isChecked():
            ddict['usematrix'] = 1
        else:
            ddict['usematrix'] = 0

        if self.attenuatorsCheckBox.isChecked():
            ddict['useattenuators'] = 1
        else:
            ddict['useattenuators'] = 0
        if self.tertiaryCheckBox.isChecked():
            ddict['usemultilayersecondary'] = 2
        elif self.secondaryCheckBox.isChecked():
            ddict['usemultilayersecondary'] = 1
        else:
            ddict['usemultilayersecondary'] = 0
        ddict['usexrfmc'] = 0
        if XRFMC_FLAG:
            if self.xrfmcCheckBox.isChecked():
                ddict['usexrfmc'] = 1
        if self.mMolarCheckBox.isChecked():
            ddict['mmolarflag'] = 1
        else:
            ddict['mmolarflag'] = 0
        ddict['flux'] = float(str(self.fundamentalWidget.flux.text()))
        ddict['time'] = float(str(self.fundamentalWidget.time.text()))
        ddict['area'] = float(str(self.fundamentalWidget.area.text()))
        ddict['distance'] = float(str(self.fundamentalWidget.distance.text()))
        #ddict['reference'] = str(self.referenceCombo.currentText())
        ddict['reference'] = str(self.referenceLine.text())
        if self.fundamentalWidget.autoTimeCheckBox.isChecked():
            ddict['useautotime'] = 1
            if self._liveTime is None:
                #ddict["useautotime"] = 0
                #self.fundamentalWidget.autoTimeCheckBox.setChecked(False)
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Cannot use automatic concentrations time setting!!!")
                msg.exec()
            else:
                ddict['time'] = float(self._liveTime)
        else:
            ddict['useautotime'] = 0
        return ddict

    def setParameters(self, ddict, signal=None):
        if signal is None:
            signal = True
        if 'usemultilayersecondary' in ddict:
            if ddict['usemultilayersecondary']:
                if ddict['usemultilayersecondary'] == 2:
                    self.tertiaryCheckBox.setChecked(True)
                    self.secondaryCheckBox.setChecked(False)
                else:
                    self.tertiaryCheckBox.setChecked(False)
                    self.secondaryCheckBox.setChecked(True)
            else:
                self.secondaryCheckBox.setChecked(False)
                self.tertiaryCheckBox.setChecked(False)
        else:
            self.secondaryCheckBox.setChecked(False)
            self.tertiaryCheckBox.setChecked(False)

        if XRFMC_FLAG:
            if 'usexrfmc' in ddict:
                if ddict['usexrfmc']:
                    self.xrfmcCheckBox.setChecked(True)
                else:
                    self.xrfmcCheckBox.setChecked(False)

        if 'mmolarflag' in ddict:
            if ddict['mmolarflag']:
                self.mMolarCheckBox.setChecked(True)
            else:
                self.mMolarCheckBox.setChecked(False)
        else:
            self.mMolarCheckBox.setChecked(False)

        usematrix = ddict.get('usematrix', False)
        if usematrix:
            self.fluxCheckBox.setChecked(False)
            self.matrixCheckBox.setChecked(True)
        else:
            self.fluxCheckBox.setChecked(True)
            self.matrixCheckBox.setChecked(False)
        ddict['useattenuators'] = 1
        if ddict['useattenuators']:
            self.attenuatorsCheckBox.setChecked(True)
        else:
            self.attenuatorsCheckBox.setChecked(False)
        if 'reference' in ddict:
            #self.referenceCombo.setCurrentText(QString(ddict['reference']))
            self.referenceLine.setText(QString(ddict['reference']))
        else:
            #self.referenceCombo.setCurrentText(QString("Auto"))
            self.referenceLine.setText(QString("Auto"))

        self.fundamentalWidget.flux.setText("%.8g" % ddict['flux'])
        self.fundamentalWidget.area.setText("%.8g" % ddict['area'])
        self.fundamentalWidget.distance.setText("%.8g" % ddict['distance'])
        if ddict['time'] is not None:
            self.fundamentalWidget.time.setText("%.8g" % ddict['time'])
        autotime = ddict.get("useautotime", False)
        if autotime:
            self.fundamentalWidget.autoTimeCheckBox.setChecked(True)
            if self._liveTime is not None:
                self.fundamentalWidget.time.setText("%.8g" % self._liveTime)
        else:
            self.fundamentalWidget.autoTimeCheckBox.setChecked(False)

        if self.matrixCheckBox.isChecked():
            self.fundamentalWidget.setInputDisabled(True)
            self.referenceLine.setEnabled(True)
        else:
            self.fundamentalWidget.setInputDisabled(False)
            self.referenceLine.setEnabled(False)
        if signal:
            self._mySignal()

    def setReferenceOptions(self, options=None):
        if options is None:
            options = ['Auto']
        old = self.referenceCombo.currentText()
        if 'Auto' not in options:
            options = ['Auto'] + options
        self.referenceCombo.clear()
        self.referenceCombo.insertStrList(options)
        if old in options:
            self.referenceCombo.setCurrentText(old)
        else:
            self.referenceCombo.setCurrentText('Auto')


class FundamentalWidget(qt.QWidget):
    def __init__(self, parent=None, name=""):
        qt.QWidget.__init__(self, parent)
        self.build()

    def build(self, spacing=2):
        layout = qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)

        #column 0
        c0 = qt.QWidget(self)
        c0.layout = qt.QVBoxLayout(c0)
        c0.layout.setContentsMargins(0, 0, 0, 0)
        c0.layout.setSpacing(spacing)

        c0l0 = qt.QLabel(c0)
        c0l0.setText("Flux (photons/s)")

        c0l1 = qt.QLabel(c0)
        c0l1.setText("Active Area (cm2)")

        c0.layout.addWidget(c0l0)
        c0.layout.addWidget(c0l1)

        #column 1
        c1 = qt.QWidget(self)
        c1.layout = qt.QVBoxLayout(c1)
        c1.layout.setContentsMargins(0, 0, 0, 0)
        c1.layout.setSpacing(spacing)

        self.flux = MyQLineEdit(c1)
        self.flux.setValidator(qt.CLocaleQDoubleValidator(self.flux))

        self.area = MyQLineEdit(c1)
        self.area.setValidator(qt.CLocaleQDoubleValidator(self.area))

        c1.layout.addWidget(self.flux)
        c1.layout.addWidget(self.area)

        #column 2
        c2 = qt.QWidget(self)
        c2.layout = qt.QVBoxLayout(c2)
        c2.layout.setContentsMargins(0, 0, 0, 0)
        c2.layout.setSpacing(spacing)

        c2l0 = qt.QLabel(c2)
        c2l0.setText("x time(seconds)")

        c2l1 = qt.QLabel(c2)
        c2l1.setText("distance (cm)")

        c2.layout.addWidget(c2l0)
        c2.layout.addWidget(c2l1)

        #column 3
        c3 = qt.QWidget(self)
        c3.layout = qt.QGridLayout(c3)
        c3.layout.setContentsMargins(0, 0, 0, 0)
        c3.layout.setSpacing(spacing)

        self.time = MyQLineEdit(c3)
        self.time.setValidator(qt.CLocaleQDoubleValidator(self.time))

        self.autoTimeCheckBox = qt.QCheckBox(c3)
        self.autoTimeCheckBox.setText("Use Automatic Factor")
        self.autoTimeCheckBox.setChecked(False)
        self.autoTimeCheckBox.setToolTip("Attempt to read from the incoming data generating an error if factor not present")

        self.distance = MyQLineEdit(c3)
        self.distance.setValidator(qt.CLocaleQDoubleValidator(self.distance))

        c3.layout.addWidget(self.time, 0, 0)
        c3.layout.addWidget(self.autoTimeCheckBox, 0, 1)
        c3.layout.addWidget(self.distance, 1, 0)

        layout.addWidget(c0)
        layout.addWidget(c1)
        layout.addWidget(c2)
        layout.addWidget(c3)

    def setInputDisabled(self, a=None):
        if a is None:
            a = True
        if a:
            self.flux.setEnabled(False)
            self.time.setEnabled(False)
            self.area.setEnabled(False)
            self.distance.setEnabled(False)
        else:
            self.flux.setEnabled(True)
            self.time.setEnabled(True)
            self.area.setEnabled(True)
            self.distance.setEnabled(True)


class ConcentrationsTable(QTable):
    def __init__(self, parent=None, **kw):
        QTable.__init__(self, parent)
        if 'labels' in kw:
            self.labels = []
            for label in kw['labels']:
                self.labels.append(label)
        else:
            self.labels = ['Element', 'Group', 'Fit Area', 'Mass fraction']
        self.setColumnCount(len(self.labels))
        self.setRowCount(1)
        for i in range(len(self.labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(self.labels[i],
                                           qt.QTableWidgetItem.Type)
            self.setHorizontalHeaderItem(i, item)
            self.resizeColumnToContents(i)

    def fillFromResult(self, result):
        if 'mmolar' in result:
            mmolarflag = True
        else:
            mmolarflag = False
        groupsList = result['groups']
        nrows = len(groupsList)
        if nrows != self.rowCount():
            self.setRowCount(nrows)
        if mmolarflag:
            self.labels = ['Element', 'Group', 'Fit Area', 'Sigma Area',
                           'mM concentration']
        else:
            self.labels = ['Element', 'Group', 'Fit Area', 'Sigma Area',
                           'Mass fraction']
        if 'layerlist' in result:
            for label in result['layerlist']:
                self.labels += [label]
        self.setColumnCount(len(self.labels))
        for i in range(len(self.labels)):
            item = self.horizontalHeaderItem(i)
            if item is None:
                item = qt.QTableWidgetItem(self.labels[i],
                                           qt.QTableWidgetItem.Type)
            item.setText(self.labels[i])
            self.setHorizontalHeaderItem(i, item)

        line = 0
        for group in groupsList:
            element, group0 = group.split()
            # transitions = group0 + " xrays"
            fitarea = QString("%.6e" % (result['fitarea'][group]))
            sigmaarea = QString("%.2e" % (result['sigmaarea'][group]))
            area = QString("%.6e" % (result['area'][group]))
            if result['mass fraction'][group] < 0.0:
                fraction = QString("Unknown")
            else:
                if mmolarflag:
                    fraction = QString("%.4g" % (result['mmolar'][group]))
                else:
                    fraction = QString("%.4g" % (result['mass fraction'][group]))
            if line % 2:
                color = qt.QApplication.instance().palette().color(qt.QPalette.AlternateBase)
            else:
                color = qt.QApplication.instance().palette().color(qt.QPalette.Base)
            if 'Expected Area' in self.labels:
                fields = [element, group0, fitarea, sigmaarea, area, fraction]
            else:
                fields = [element, group0, fitarea, sigmaarea, fraction]
            if 'layerlist' in result:
                for layer in result['layerlist']:
                    if result[layer]['mass fraction'][group] < 0.0:
                        fraction = QString("Unknown")
                    else:
                        if mmolarflag:
                            fraction = QString("%.4g" % (result[layer]['mmolar'][group]))
                        else:
                            fraction = QString("%.4g" % (result[layer]['mass fraction'][group]))
                    fields += [fraction]
            col = 0
            for field in fields:
                item = self.item(line, col)
                if item is None:
                    item = qt.QTableWidgetItem(field,
                                               qt.QTableWidgetItem.Type)
                    self.setItem(line, col, item)
                else:
                    item.setText(field)
                if hasattr(item, "setBackground"):
                    # Qt5
                    item.setBackground(color)
                else:
                    # Qt4
                    item.setBackgroundColor(color)
                item.setFlags(qt.Qt.ItemIsSelectable |
                              qt.Qt.ItemIsEnabled)
                col += 1
            line += 1

        for i in range(self.columnCount()):
            if (i > 1) and (i < 5):
                self.resizeColumnToContents(i)

    def getHtmlText(self):
        _palette = qt.QApplication.instance().palette()
        lemon = _palette.color(qt.QPalette.AlternateBase).name().upper()
        white = _palette.color(qt.QPalette.Base).name().upper()
        hcolor = _palette.color(qt.QPalette.Midlight).name().upper()
        text = ""
        text += ("<nobr>")
        text += ("<table>")
        text += ("<tr>")
        for l in range(self.columnCount()):
            text += ('<td align="left" bgcolor="%s"><b>' % hcolor)
            item = self.horizontalHeaderItem(l)
            text += str(item.text())
            text += ("</b></td>")
        text += ("</tr>")
        #text+=( str(QString("</br>"))
        for r in range(self.rowCount()):
            text += ("<tr>")
            if r % 2:
                color = white
                b = "<b>"
            else:
                b = "<b>"
                color = lemon
            for c in range(self.columnCount()):
                moretext = ""
                item = self.item(r, c)
                if item is not None:
                    moretext = str(item.text())
                if len(moretext):
                    finalcolor = color
                else:
                    finalcolor = white
                if c < 2:
                    text += ('<td align="left" bgcolor="%s">%s' % (finalcolor, b))
                else:
                    text += ('<td align="right" bgcolor="%s">%s' % (finalcolor, b))
                text += moretext
                if len(b):
                    text += ("</td>")
                else:
                    text += ("</b></td>")
            moretext = ""
            item = self.item(r, 0)
            if item is not None:
                moretext = str(item.text())
            if len(moretext):
                text += ("</b>")
            text += ("</tr>")
            text += ("\n")
        text += ("</table>")
        text += ("</nobr>")
        return text

    def _copySelection(self):
        selected_idx = self.selectedIndexes()
        selected_idx_tuples = [(idx.row(), idx.column()) for idx in selected_idx]

        selected_rows = [idx[0] for idx in selected_idx_tuples]
        selected_columns = [idx[1] for idx in selected_idx_tuples]

        if sys.platform.startswith("win"):
            newline = "\r\n"
        else:
            newline = "\n"
        copied_text = ""
        for row in range(min(selected_rows), max(selected_rows) + 1):
            for col in range(min(selected_columns), max(selected_columns) + 1):
                item_text = self.item(row, col).text()
                if (row, col) in  selected_idx_tuples:
                    copied_text += item_text
                copied_text += "\t"
            # remove the right-most tabulation
            copied_text.rstrip("\t")
            # add a newline
            copied_text += newline
        # remove final newline
        copied_text.rstrip(newline)

        # put this text into clipboard
        qapp = qt.QApplication.instance()
        qapp.clipboard().setText(copied_text)

    if USE_QTABLE_WIDGET:
        def keyPressEvent(self, keyEvent):
            #if there is a control-C event copy data to the clipboard
            if (keyEvent.key() == qt.Qt.Key_C) and \
               (keyEvent.modifiers() & qt.Qt.ControlModifier):
               self._copySelection()

class MyQLineEdit(qt.QLineEdit):
    sigMyQLineEditSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name=None):
        qt.QLineEdit.__init__(self, parent)
        self.editingFinished[()].connect(self._mySignal)
    #TODO: Focus in to set yellow color, focus out to set white color

    def _mySignal(self):
        ddict = {}
        ddict['event'] = "returnPressed"
        self.sigMyQLineEditSignal.emit(ddict)


class MyQComboBox(qt.QComboBox):
    def __init__(self, parent=None, name=None, fl=0):
        qt.QComboBox.__init__(self, parent)
        self.setEditable(True)
        self._lineEdit = MyQLineEdit()
        self.setLineEdit(self._lineEdit)
        self._lineEdit.sigMyQLineEditSignal.connect(self._mySlot)

    def _mySlot(self, ddict):
        if ddict['event'] == "returnPressed":
            current = str(self.currentText())
            current = current.replace(' ', '')
            if (current == '') or (current.upper() == 'AUTO'):
                pass
            elif len(current) == 2:
                current = current.upper()[0] + current.lower()[1]
            elif len(current) == 1:
                current = current.upper()[0]
            else:
                msg = qt.QMessageBox(self._lineEdit)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Element %s" % current)
                msg.exec()
                self._lineEdit.setFocus()
            if not Elements.isValidFormula(current):
                msg = qt.QMessageBox(self._lineEdit)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Element %s" % current)
                msg.exec()
                self._lineEdit.setFocus()
            else:
                self.setCurrentText(current)


def main(args):
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    demo = Concentrations()
    config = demo.getParameters()

    # Update configuration from CLI arguments
    if args.flux is not None:
        config["flux"] = args.flux
    if args.area is not None:
        config["area"] = args.area
    if args.time is not None:
        config["time"] = args.time
    if args.distance is not None:
        config["distance"] = args.distance
    if args.attenuators is not None:
        config["useattenuators"] = int(args.attenuators)
    if args.usematrix is not None:
        config["usematrix"] = int(args.usematrix)

    demo.setParameters(config)

    # Process fit result files
    for filename in args.files:
        d = ConfigDict.ConfigDict()
        d.read(filename)

        for material in d["result"]["config"]["materials"].keys():
            Elements.Material[material] = copy.deepcopy(
                d["result"]["config"]["materials"][material]
            )

        demo.processFitResult(
            fitresult=d,
            elementsfrommatrix=False
        )

    demo.show()

    # Auto-close Qt for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="Concentrations tool", add_qt_options=True)

    parser.add_argument("--flux", type=float)
    parser.add_argument("--time", type=float)
    parser.add_argument("--area", type=float)
    parser.add_argument("--distance", type=float)
    parser.add_argument("--attenuators", type=float)
    parser.add_argument("--usematrix", type=float)

    parser.add_argument("files", nargs="*", help="Fit result files")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
