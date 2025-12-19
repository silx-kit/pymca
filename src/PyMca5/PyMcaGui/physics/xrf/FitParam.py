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
__author__ = "E. Papillon & V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import traceback
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()

from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaGui.plotting import PyMca_Icons as Icons
import os.path
import copy
from PyMca5.PyMcaPhysics import Elements
from .FitParamForm import FitParamForm
from .FitPeakSelect import FitPeakSelect
from . import AttenuatorsTable
from . import ConcentrationsWidget
from . import EnergyTable
from PyMca5.PyMcaCore import PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.io import ConfigurationFileDialogs
XRFMC_FLAG = False
_logger = logging.getLogger(__name__)
try:
    from . import XRFMCPyMca
    XRFMC_FLAG = True
except ImportError:
    _logger.warning("XRFMC_TO_BE_IMPORTED")
    # no XRFMC support
    pass
from PyMca5.PyMcaGui.math import StripBackgroundWidget
from PyMca5.PyMcaGui.plotting import PlotWindow
from PyMca5.PyMcaGui.physics.xrf import StrategyHandler
import numpy


FitParamSections= ["fit", "detector", "peaks", "peakshape", "attenuators","concentrations"]
FitParamHeaders= ["FIT", "DETECTOR","BEAM","PEAKS", "PEAK SHAPE", "ATTENUATORS","MATRIX","CONCENTRATIONS"]

class FitParamWidget(FitParamForm):
    attenuators= ["Filter 0", "Filter 1", "Filter 2", "Filter 3", "Filter 4", "Filter 5",
                   "Filter 6","Filter 7","BeamFilter0", "BeamFilter1", "BeamFilter2","Detector", "Matrix"]
    def __init__(self, parent=None):
        FitParamForm.__init__(self, parent)
        self._channels = None
        self._counts   = None
        self._stripDialog = None
        self._strategyDialog  = None
        self._info = None
        self.setWindowIcon(qt.QIcon(qt.QPixmap(Icons.IconDict["gioconda16"])))
        self.tabAtt = qt.QWidget()
        tabAttLayout = qt.QGridLayout(self.tabAtt)
        tabAttLayout.setContentsMargins(11, 11, 11, 11)
        tabAttLayout.setSpacing(6)
        self.graphDialog = qt.QDialog(self)
        self.graphDialog.mainLayout = qt.QVBoxLayout(self.graphDialog)
        self.graphDialog.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.graphDialog.mainLayout.setSpacing(0)
        self.graphDialog.graph = PlotWindow.PlotWindow(self.graphDialog,
                                                       newplot=False,
                                                       fit=False,
                                                       plugins=False,
                                                       control=True,
                                                       position=True)
        self.graph = self.graphDialog.graph
        self.graph._togglePointsSignal()
        self.graph.setDataMargins(0.05, 0.05, 0.05, 0.05)
        self.tabAttenuators = AttenuatorsTable.AttenuatorsTab(self.tabAtt,
                                                graph=self.graphDialog)
        self.graphDialog.mainLayout.addWidget(self.graph)
        self.graphDialog.okButton = qt.QPushButton(self.graphDialog)
        self.graphDialog.okButton.setText('OK')
        self.graphDialog.okButton.setAutoDefault(True)
        self.graphDialog.mainLayout.addWidget(self.graphDialog.okButton)
        self.graphDialog.okButton.clicked.connect( \
                                 self.graphDialog.accept)
        self.attTable = self.tabAttenuators.table
        #self.multilayerTable =self.tabAttenuators.matrixTable
        tabAttLayout.addWidget(self.tabAttenuators,0,0)
        self.mainTab.addTab(self.tabAtt, str("ATTENUATORS"))
        maxheight = qt.QDesktopWidget().height()
        #self.graph.hide()
        self.attPlotButton = qt.QPushButton(self.tabAttenuators)
        self.attPlotButton.setAutoDefault(False)
        text = 'Plot T(filters) * (1 - T(detector)) Efficienty Term'
        self.attPlotButton.setText(text)
        self.tabAttenuators.layout().insertWidget(1, self.attPlotButton)
        self.attPlotButton.clicked.connect(self.__attPlotButtonSlot)
        if maxheight < 801:
            self.setMaximumHeight(int(0.8*maxheight))
            self.setMinimumHeight(int(0.8*maxheight))
        maxWidth = int(min(900, 0.8*qt.QDesktopWidget().width()))
        self.tabAttenuators.setMaximumWidth(maxWidth)

        #This was previously into FitParamForm.py: END
        self.tabMul = qt.QWidget()
        tabMultilayerLayout = qt.QGridLayout(self.tabMul)
        tabMultilayerLayout.setContentsMargins(11, 11, 11, 11)
        tabMultilayerLayout.setSpacing(6)
        self.tabMultilayer  = AttenuatorsTable.MultilayerTab(self.tabMul)
        self.multilayerTable =self.tabMultilayer.matrixTable
        tabMultilayerLayout.addWidget(self.tabMultilayer,0,0)
        self.mainTab.addTab(self.tabMul, str("MATRIX"))
        self.matrixGeometry = self.tabMultilayer.matrixGeometry

        #The concentrations
        self.tabConcentrations =  qt.QWidget()
        tabConcentrationsLayout = qt.QGridLayout(self.tabConcentrations)
        tabConcentrationsLayout.setContentsMargins(11, 11, 11, 11)
        tabConcentrationsLayout.setSpacing(6)
        self.concentrationsWidget   = ConcentrationsWidget.ConcentrationsWidget(self.tabConcentrations,"tabConcentrations")
        tabConcentrationsLayout.addWidget(self.concentrationsWidget,0,0)
        self.mainTab.addTab(self.tabConcentrations, str("CONCENTRATIONS"))
        #end concentrations tab

        #self.matrixGeometry = self.tabAttenuators.matrixGeometry
        if 0:
            #The compound fit tab
            self.tabCompoundFit =  qt.QWidget()
            tabCompoundFitLayout = qt.QGridLayout(self.tabCompoundFit)
            tabCompoundFitLayout.setContentsMargins(11, 11, 11, 11)
            tabCompoundFitLayout.setSpacing(6)
            self.compoundFitWidget   = AttenuatorsTable.CompoundFittingTab(self.tabCompoundFit,
                                                                           "tabCompound_fit")
            tabCompoundFitLayout.addWidget(self.compoundFitWidget,0,0)
            self.mainTab.addTab(self.tabCompoundFit, str("COMPOUND FIT"))
            #end compound fit tab

        if XRFMC_FLAG:
            self.tabXRFMC =  qt.QWidget()
            tabXRFMCLayout = qt.QGridLayout(self.tabXRFMC)
            tabXRFMCLayout.setContentsMargins(11, 11, 11, 11)
            tabXRFMCLayout.setSpacing(6)
            self.tabXRFMCWidget   = XRFMCPyMca.XRFMCTabWidget(\
                                                self.tabXRFMC)
            tabXRFMCLayout.addWidget(self.tabXRFMCWidget,0,0)
            self.mainTab.addTab(self.tabXRFMC, str("XRFMC"))

        self.layout().setContentsMargins(0, 0, 0, 0)

        if "PyQt4" in sys.modules:
            #I had to add this line to prevent a crash. Why?
            qApp = qt.QApplication.instance()
            qApp.processEvents()
        else:
            qt.QApplication.instance().processEvents()
        self.attTable.verticalHeader().hide()
        #The beam energies tab
        beamlayout= qt.QGridLayout(self.TabBeam)
        self.energyTab = EnergyTable.EnergyTab(self.TabBeam)
        beamlayout.addWidget(self.energyTab, 0, 0)
        self.energyTable = self.energyTab.table

        #the x-ray tube (if any)
        self.xRayTube = self.energyTab.tube

        #The peak select tab
        layout= qt.QGridLayout(self.TabPeaks)
        if 0:
            self.peakTable= FitPeakSelect(self.TabPeaks)
            layout.addWidget(self.peakTable, 0, 0)
            self.peakTable.setMaximumSize(self.tabDetector.sizeHint())
        else:
            self.peakTable= FitPeakSelect(self.TabPeaks,
                                          energyTable=self.energyTable)
            self.peakTable.energy.setToolTip("Energy is set in the BEAM tab")
            maxWidth = int(min(900, 0.8*qt.QDesktopWidget().width()))
            self.peakTable.setMaximumWidth(maxWidth)
            layout.addWidget(self.peakTable, 0, 0)
            #self.peakTable.setMaximumSize(self.tabDetector.sizeHint())
        #self.energyTable = self.peakTable.energyTable
        self._inputParameters = None
        self.linpolOrder= None
        self.exppolOrder= None
        pardict={'attenuators':{'Air'       :[0,"Air",0.001204790,1.0],
                                'Contact'   :[0,"Au1",19.370,1.0E-06],
                                'Deadlayer' :[0,"Si1",2.330,0.0020],
                                'Window'    :[0,"Be1",1.848,0.0100]},
                 'concentrations':self.concentrationsWidget.getParameters()}
        if XRFMC_FLAG:
            pardict = self.tabXRFMCWidget.getParameters()
        # TODO: This line makes PySide crash
        self.setParameters(pardict=pardict)

        self.prevTabIdx= None
        self.tabLabel= []
        n = self.mainTab.count()
        for idx in range(n):
            self.tabLabel.append(qt.safe_str(self.mainTab.tabText(idx)))
        self.mainTab.currentChanged[int].connect(self.__tabChanged)
        self.contCombo.activated[int].connect(self.__contComboActivated)
        self.functionCombo.activated[int].connect(self.__functionComboActivated)
        self.orderSpin.valueChanged[int].connect(self.__orderSpinChanged)
        self._backgroundWindow = None
        self.stripSetupButton.clicked.connect(self.__stripSetupButtonClicked)

        # strategy related
        self.strategyCheckBox.clicked.connect(self._strategyCheckBoxClicked)
        self.strategySetupButton.clicked.connect(self._strategySetupButtonClicked)
        self.strategyCombo.activated[int].connect(self._strategyComboActivated)

        # calibration update handling related
        self.ignoreSpectrumCalibration.clicked.connect( \
                            self.__ignoreSpectrumCalibrationClicked)

    def __ignoreSpectrumCalibrationClicked(self):
        return self._ignoreSpectrumCalibrationClicked()

    def _ignoreSpectrumCalibrationClicked(self):
        if not self.ignoreSpectrumCalibration.isChecked():
            # update the values with the received ones (if any)
            if self._info is not None:
                calibration = self._info.get('calibration', [])
                if calibration is not None:
                    if len(calibration) > 1:
                        self.zeroValue.setText("%f" % calibration[0])
                        self.gainValue.setText("%f" % calibration[1])

    def __attPlotButtonSlot(self):
        try:
            self.computeEfficiency()
        except Exception:
            msg=qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Error %s" % sys.exc_info()[1]
            msg.setInformativeText(text)
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def computeEfficiency(self):
        pars = self.__getAttPar()
        attenuators = []
        funnyfilters = []
        detector = []
        for key in pars.keys():
            if pars[key][0]:
                l = key.lower()
                if l.startswith('matrix') or l.startswith('beamfilter'):
                    continue
                if l.startswith('detector'):
                    detector.append(pars[key][1:])
                else:
                    if abs(pars[key][4] - 1.0) > 1.0e-10:
                        funnyfilters.append(pars[key][1:])
                    else:
                        attenuators.append(pars[key][1:])

        maxenergy = qt.safe_str(self.peakTable.energy.text())
        if maxenergy=='None':
            maxenergy = 100.
            energies = numpy.arange(0.3, maxenergy, 0.1)
        else:
            maxenergy = float(maxenergy)
            if maxenergy < 50:
                energies = numpy.arange(0.3, maxenergy, 0.01)
            elif maxenergy > 100:
                energies = numpy.arange(0.3, maxenergy, 0.1)
            else:
                energies = numpy.arange(0.3, maxenergy, 0.02)
        efficiency = numpy.ones(len(energies), numpy.float64)
        if (len(attenuators)+len(detector)+len(funnyfilters)) != 0:
            massatt = Elements.getMaterialMassAttenuationCoefficients
            if len(attenuators):
                coeffs = numpy.zeros(len(energies), numpy.float64)
                for attenuator in attenuators:
                    formula   = attenuator[0]
                    thickness = attenuator[1] * attenuator[2]
                    coeffs +=  thickness *\
                              numpy.array(massatt(formula,1.0,energies)['total'])
                efficiency *= numpy.exp(-coeffs)

            if len(funnyfilters):
                coeffs = numpy.zeros(len(energies), numpy.float64)
                funnyfactor = None
                for attenuator in funnyfilters:
                    formula   = attenuator[0]
                    thickness = attenuator[1] * attenuator[2]
                    if funnyfactor is None:
                        funnyfactor = attenuator[3]
                    else:
                        if abs(attenuator[3]-funnyfactor) > 0.0001:
                            raise ValueError("All funny type filters must have same openning fraction")
                    coeffs +=  thickness *\
                              numpy.array(massatt(formula,1.0,energies)['total'])
                efficiency *= (funnyfactor * numpy.exp(-coeffs)+\
                               (1.0 - funnyfactor))
            if len(detector):
                detector = detector[0]
                formula = detector[0]
                thickness = detector[1] * detector[2]
                coeffs = thickness *\
                           numpy.array(massatt(formula,1.0,energies)['total'])
                efficiency *= (1.0 - numpy.exp(-coeffs))

        userattenuators = []
        userAtt = self.tabAttenuators.userAttenuators.getParameters()
        for key in userAtt:
            if userAtt[key]["use"]:
                efficiency *= Elements.getTableTransmission( \
                                                [userAtt[key]["energy"],
                                                 userAtt[key]["transmission"]],
                                                 energies)

        self.graph.setGraphTitle('Filter (not beam filter) and detector correction')
        self.graph.addCurve(energies, efficiency,
                            legend='Ta * (1.0 - Td)',
                            xlabel='Energy (keV)',
                            ylabel='Efficiency Term',
                            replace=True)
        self.graphDialog.exec()

    def __contComboActivated(self, idx):
        if idx==4:
            self.orderSpin.setEnabled(1)
            self.orderSpin.setValue(self.linpolOrder or 1)
        elif idx==5:
            self.orderSpin.setEnabled(1)
            self.orderSpin.setValue(self.exppolOrder or 1)
        else:
            self.orderSpin.setEnabled(0)

    def __functionComboActivated(self, idx):
        if idx==0:
            #hypermet flag = 1
            pass
        else:
            #hypermet flag = 0
            pass

    def __orderSpinChanged(self, value):
        continuum= int(self.contCombo.currentIndex())
        if continuum==4:
            self.linpolOrder= self.orderSpin.value()
        elif continuum==5:
            self.exppolOrder= self.orderSpin.value()

    def setData(self, x, y, info=None):
        self._channels = x
        self._counts = y
        self._info = info
        autoTime = info.get("time", None)
        self.concentrationsWidget.setTimeFactor(autoTime, signal=False)

    def _strategyCheckBoxClicked(self, *var):
        if self.strategyCheckBox.isChecked():
            maxEnergy = qt.safe_str(self.peakTable.energy.text())
            if maxEnergy == 'None':
                self.strategyCheckBox.setChecked(False)
                msg=qt.QMessageBox(self)
                msg.setWindowTitle("Strategy Error")
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error configuring strategy")
                msg.setInformativeText("You need to specify incident beam energy")
                msg.exec()
        #_logger.debug("TO check for matrix composition")
        #_logger.debug("TO check for peaks")

    def _strategySetupButtonClicked(self):
        maxEnergy = qt.safe_str(self.peakTable.energy.text())
        if maxEnergy == 'None':
            self.strategyCheckBox.setChecked(False)
            msg=qt.QMessageBox(self)
            msg.setWindowTitle("Strategy Error")
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error configuring strategy")
            msg.setInformativeText("You need to specify incident beam energy")
            msg.exec()
            return
        if self._strategyDialog is None:
            self._strategyDialog = StrategyHandler.StrategyHandlerDialog(self.parent())
            self._strategyDialog.setWindowIcon(qt.QIcon(\
                                qt.QPixmap(Icons.IconDict["gioconda16"])))
            if self.height() < 801:
                self._strategyDialog.setMinimumHeight(int(0.85*self.height()))
                self._strategyDialog.setMaximumHeight(int(0.85*self.height()))
        before = self.getParameters()
        try:
            self._strategyDialog.setFitConfiguration(before)
        except Exception:
            msg=qt.QMessageBox(self)
            msg.setWindowTitle("Strategy Error: %s" % \
                               qt.safe_str(sys.exc_info()[1]))
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error configuring strategy")
            msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return
        self._strategyDialog.raise_()
        ret = self._strategyDialog.exec()
        if ret != qt.QDialog.Accepted:
            self._strategyDialog.setFitConfiguration(before)

    def _strategyComboActivated(self, intValue):
        # only one strategy implemented untill now
        pass

    def  __stripSetupButtonClicked(self):
        if self._counts is None:
            msg=qt.QMessageBox(self)
            msg.setWindowTitle("No data supplied")
            msg.setIcon(qt.QMessageBox.Information)
            msg.setText("Please enter the values in the fields")
            msg.exec()
            return

        pars = self.__getFitPar()
        y = numpy.ravel(numpy.array(self._counts)).astype(numpy.float64)
        x = numpy.ravel(numpy.array(self._channels))
        if self._stripDialog is None:
            self._stripDialog = StripBackgroundWidget.StripBackgroundDialog(self)
            self._stripDialog.setWindowIcon(qt.QIcon(\
                                qt.QPixmap(Icons.IconDict["gioconda16"])))
            if self.height() < 801:
                self._stripDialog.setMinimumHeight(int(0.85*self.height()))
                self._stripDialog.setMaximumHeight(int(0.85*self.height()))

        self._stripDialog.setParameters(pars)
        self._stripDialog.setData(x, y)
        ret = self._stripDialog.exec()
        if not ret:
            return
        pars = self._stripDialog.getParameters()
        key = "stripalgorithm"
        if key in pars:
            stripAlgorithm = int(pars[key])
            self.setSNIP(stripAlgorithm)

        key = "snipwidth"
        if key in pars:
            self.snipWidthSpin.setValue(int(pars[key]))

        key = "stripwidth"
        if key in pars:
            self.stripWidthSpin.setValue(int(pars[key]))

        key = "stripiterations"
        if key in pars:
            self.stripIterValue.setText("%d" % int(pars[key]))

        key = "stripfilterwidth"
        if key in pars:
            self.stripFilterSpin.setValue(int(pars[key]))

        key = "stripanchorsflag"
        if key in pars:
            self.stripAnchorsFlagCheck.setChecked(int(pars[key]))

        key = "stripanchorslist"
        if key in pars:
            anchorslist = pars[key]
            if anchorslist in [None, 'None']:
                anchorslist = []
            for spin in self.stripAnchorsList:
                spin.setValue(0)

            i = 0
            for value in anchorslist:
                self.stripAnchorsList[i].setValue(int(value))
                i += 1


    def __tabChanged(self, idx):
        if self.prevTabIdx is None:
            self.prevTabIdx= idx

        if idx != self.prevTabIdx:
            if self.__tabCheck(self.prevTabIdx):
                self.prevTabIdx= idx

    def __tabCheck(self, tabIdx):
        label= self.tabLabel[tabIdx]
        if self.__getPar(label) is None:
            return 0
        return 1

    def __get(self, section, key, default=0., conv=str):
        sect = self._inputParameters.get(section, None)
        if sect is None:
            ret = default
        else:
            ret = sect.get(key, default)
        if (conv is not None) and (ret is not None) and (ret != "None"):
            return conv(ret)
        else:
            return ret

    def __setInput(self, ndict):
        if self._inputParameters is None:
            self._inputParameters = {}
        self._inputParameters.update(ndict)

    def setParameters(self, pardict=None):
        if pardict is None:
            pardict={}
        self.__setInput(pardict)
        self.__setFitPar()
        self.__setPeaksPar()
        self.__setAttPar(pardict)
        self.__setMultilayerPar(pardict)
        self.__setConPar(pardict)
        self.__setDetPar()
        self.__setPeakShapePar()
        if "tube" in pardict:
            self.xRayTube.setParameters(pardict["tube"])
        if "userattenuators"  in pardict:
            self.tabAttenuators.userAttenuators.setParameters( \
                                        pardict["userattenuators"])
        if "xrfmc" in pardict:
            if XRFMC_FLAG:
                self.tabXRFMCWidget.setParameters(pardict)

    def getParameters(self):
        pars = copy.deepcopy(self._inputParameters)
        sections = FitParamSections * 1
        sections.append('multilayer')
        sections.append('materials')
        sections.append('tube')
        sections.append('userattenuators')
        if XRFMC_FLAG:
            sections.append('xrfmc')
        for key in sections:
            pars[key]= self.__getPar(key)
        if self._strategyDialog is not None:
            pars.update(self._strategyDialog.getParameters())
        return pars

    def __getPar(self, parname):
        if parname in ["fit", "FIT"]:
            return self.__getFitPar()
        if parname in ["detector", "DETECTOR"]:
            return self.__getDetPar()
        if parname in ["peaks", "PEAKS"]:
            return self.__getPeaksPar()
        if parname in ["peakshape", "PEAK SHAPE"]:
            return self.__getPeakShapePar()
        if parname in ["attenuators", "ATTENUATORS"]:
            return self.__getAttPar()
        if parname in ["userattenuators"]:
            return self.tabAttenuators.userAttenuators.getParameters()
        if parname in ["multilayer", "MULTILAYER"]:
            return self.__getMultilayerPar()
        if parname in ["materials", "MATERIALS"]:
                return self.__getMaterialsPar()
        if parname in ["tube", "TUBE"]:
            return self.__getTubePar()
        if parname in ["concentrations", "CONCENTRATIONS"]:
            return self.__getConPar()
        if parname in ["xrfmc", "XRFMC"]:
            if XRFMC_FLAG:
                return self.tabXRFMCWidget.getParameters()["xrfmc"]
        return None

    def __setAttPar(self, pardict):
        if "attenuators" in pardict.keys():
            attenuatorsList = list(pardict['attenuators'].keys())
        else:
            attenuatorsList = []
        if "materials" in pardict.keys():
            for key in pardict["materials"]:
                filteredkey = Elements.getMaterialKey(key)
                if filteredkey is None:
                    Elements.Material[key] = copy.deepcopy(pardict['materials'][key])
                else:
                    Elements.Material[filteredkey] = copy.deepcopy(pardict['materials'][key])
        matlist = list(Elements.Material.keys())
        matlist.sort()
        #lastrow = -1
        lastrow = -1
        for idx in range(len(self.attenuators)):
            if idx < len(attenuatorsList):
                att = attenuatorsList[idx]
            else:
                att= self.attenuators[idx]
            if att.upper() == "MATRIX":
                attpar= self.__get("attenuators", att, [0, "MULTILAYER", 0., 0., 45., 45.], None)
                row = self.attTable.rowCount() - 1
                current={'Material':  attpar[1],
                         'Density':   attpar[2],
                         'Thickness': attpar[3],
                         'AlphaIn':   attpar[4],
                         'AlphaOut':  attpar[5]}
                if len(attpar) == 8:
                    current['AlphaScatteringFlag'] = attpar[6]
                    current['AlphaScattering'] = attpar[7]
                else:
                    current['AlphaScatteringFlag'] = 0
                self.matrixGeometry.setParameters(current)
            elif att.upper().startswith("BEAMFILTER"):
                attpar= self.__get("attenuators", att, [0, "-", 0., 0.], None)
                row = self.attTable.rowCount() - 2 - (3 - int(att[-1])) # maximum 3 BeamFilter
            elif att.upper() == "DETECTOR":
                attpar= self.__get("attenuators", att, [0, "-", 0., 0.], None)
                row = self.attTable.rowCount() - 2
            else:
                attpar= self.__get("attenuators", att, [0, "-", 0., 0.], None)
                lastrow += 1
                row = lastrow
            self.attTable.cellWidget(row, 0).setChecked(int(attpar[0]))
            self.attTable.setText(row, 1, att)
            #self.attTable.setText(idx, 2, str(attpar[1]))
            combo = self.attTable.cellWidget(row, 2)
            if combo is not None:
                if att.upper() == "MATRIX":
                    combo.setOptions(matlist+["MULTILAYER"])
                else:
                    combo.setOptions(matlist)
                combo.lineEdit().setText(str(attpar[1]))
            else:
                _logger.warning("ERROR in __setAttPar")
            if len(attpar) == 4:
                attpar.append(1.0)
            self.attTable.setText(row, 3, str(attpar[2]))
            self.attTable.setText(row, 4, str(attpar[3]))
            if not (att.upper() in ["MATRIX", "DETECTOR"] or att.upper().startswith("BEAMFILTER")):
                self.attTable.setText(row, 5, str(attpar[4]))
            else:
                self.attTable.setText(row, 5, "1.0")
        current = self.tabAttenuators.editor.matCombo.currentText()
        self.tabAttenuators.editor.matCombo.setOptions(matlist)

        #force update of all the parameters
        if current in matlist:
            self.tabAttenuators.editor.matCombo._mySignal(current)

    def __getAttPar(self):
        pars= {}
        for idx in range(self.attTable.rowCount()):
            #att= self.attenuators[idx]
            att = str(self.attTable.text(idx,1))
            attpar= []
            attpar.append(int(self.attTable.cellWidget(idx,0).isChecked()))
            attpar.append(str(self.attTable.text(idx,2)))
            try:
                attpar.append(float(str(self.attTable.text(idx, 3))))
                attpar.append(float(str(self.attTable.text(idx, 4))))
                if att.upper() == "MATRIX":
                    attpar.append(self.matrixGeometry.getParameters("AlphaIn"))
                    attpar.append(self.matrixGeometry.getParameters("AlphaOut"))
                    attpar.append(self.matrixGeometry.getParameters("AlphaScatteringFlag"))
                    attpar.append(self.matrixGeometry.getParameters("AlphaScattering"))
                else:
                    attpar.append(float(str(self.attTable.text(idx, 5))))
            except Exception:
                if att.upper() not in ["MATRIX"]:
                    attpar= [0, '-', 0., 0., 1.0]
                else:
                    attpar= [0, '-', 0., 0., 45.0, 45.0, 0, 90.0]
                self.__parError("ATTENUATORS",
                                "Attenuators parameters error on:\n%s\nI reset it to zero." % \
                                self.attenuators[idx])
            pars[att]= attpar
        return pars


    def __setMultilayerPar(self, pardict):
        if "multilayer" in pardict.keys():
            attenuatorsList = list(pardict['multilayer'].keys())
        else:
            attenuatorsList = []
        matlist = list(Elements.Material.keys())
        matlist.sort()
        #lastrow = -1
        lastrow = -1
        lastrow=-1
        for idx in range(max(self.multilayerTable.rowCount(),len(attenuatorsList))):
            att= "Layer%d" % idx
            attpar= self.__get("multilayer", att, [0, "-", 0., 0.], None)
            lastrow += 1
            row = lastrow
            self.multilayerTable.cellWidget(row, 0).setChecked(int(attpar[0]))
            self.multilayerTable.setText(row, 1, att)
            #self.attTable.setText(idx, 2, str(attpar[1]))
            combo = self.multilayerTable.cellWidget(row, 2)
            if combo is not None:
                combo.setOptions(matlist)
                combo.lineEdit().setText(str(attpar[1]))
            else:
                _logger.warning("ERROR in __setAttPar")
            self.multilayerTable.setText(row, 3, str(attpar[2]))
            self.multilayerTable.setText(row, 4, str(attpar[3]))

    def __getMultilayerPar(self):
        pars= {}
        for idx in range(self.multilayerTable.rowCount()):
            #att= self.attenuators[idx]
            att = str(self.multilayerTable.text(idx,1))
            attpar= []
            attpar.append(int(self.multilayerTable.cellWidget(idx,0).isChecked()))
            attpar.append(str(self.multilayerTable.text(idx,2)))
            try:
            #if 1:
                attpar.append(float(str(self.multilayerTable.text(idx, 3))))
                attpar.append(float(str(self.multilayerTable.text(idx, 4))))
            #else:
            except Exception:
                attpar= [0, '-', 0., 0.]
                self.__parError("ATTENUATORS",
                                "Multilayer parameters error on:\n%s\nReset it to zero." % att)
            pars[att]= attpar
        return pars

    def __getTubePar(self):
        pars = self.xRayTube.getParameters()
        return pars

    def __getMaterialsPar(self):
        pars = {}
        for key in Elements.Material.keys():
            pars[key] = copy.deepcopy(Elements.Material[key])
        return pars

    def __setConPar(self, pardict):
        if 'concentrations' in pardict:
            self.concentrationsWidget.setParameters(pardict['concentrations'])

    def __getConPar(self):
        return self.concentrationsWidget.getParameters()

    def __setPeakShapePar(self):
        hypermetflag = (self.__get("fit", "hypermetflag", 1, int))
        if hypermetflag:
            index = 0
        else:
            index = 1
        self.functionCombo.setCurrentIndex(index)

        self.staCheck.setChecked(self.__get("peakshape", "fixedst_arearatio", 0, int))
        self.staValue.setText(self.__get("peakshape", "st_arearatio"))
        self.staError.setText(self.__get("peakshape","deltast_arearatio"))
        self.stsCheck.setChecked(self.__get("peakshape","fixedst_sloperatio", 0, int))
        self.stsValue.setText(self.__get("peakshape","st_sloperatio"))
        self.stsError.setText(self.__get("peakshape","deltast_sloperatio"))
        self.ltaCheck.setChecked(self.__get("peakshape","fixedlt_arearatio", 0, int))
        self.ltaValue.setText(self.__get("peakshape","lt_arearatio"))
        self.ltaError.setText(self.__get("peakshape","deltalt_arearatio"))
        self.ltsCheck.setChecked(self.__get("peakshape","fixedlt_sloperatio", 0, int))
        self.ltsValue.setText(self.__get("peakshape","lt_sloperatio"))
        self.ltsError.setText(self.__get("peakshape","deltalt_sloperatio"))
        self.shCheck.setChecked(self.__get("peakshape","fixedstep_heightratio", 0, int))
        self.shValue.setText(self.__get("peakshape","step_heightratio"))
        self.shError.setText(self.__get("peakshape","deltastep_heightratio"))
        self.etaCheck.setChecked(self.__get("peakshape","fixedeta_factor", 0, int))
        eta = self.__get("peakshape","eta_factor", 0.2, str)
        self.etaValue.setText(eta)
        deltaeta = self.__get("peakshape","deltaeta_factor", 0.2, str)
        if float(deltaeta) > float(eta):
            deltaeta = eta
        self.etaError.setText(deltaeta)

    def __getPeakShapePar(self):
        pars= {}
        try:
            err= "Short Tail Area Value"
            pars["st_arearatio"]= float(str(self.staValue.text()))
            err= "Short Tail Area Error"
            pars["deltast_arearatio"]= float(str(self.staError.text()))
            pars["fixedst_arearatio"]= int(self.staCheck.isChecked())
            err= "Short Tail Slope Value"
            pars["st_sloperatio"]= float(str(self.stsValue.text()))
            err= "Short Tail Slope Error"
            pars["deltast_sloperatio"]= float(str(self.stsError.text()))
            pars["fixedst_sloperatio"]= int(self.stsCheck.isChecked())
            err= "Long Tail Area Value"
            pars["lt_arearatio"]= float(str(self.ltaValue.text()))
            err= "Long Tail Area Error"
            pars["deltalt_arearatio"]= float(str(self.ltaError.text()))
            pars["fixedlt_arearatio"]= int(self.ltaCheck.isChecked())
            err= "Long Tail Slope Value"
            pars["lt_sloperatio"]= float(str(self.ltsValue.text()))
            err= "Long Tail Slope Error"
            pars["deltalt_sloperatio"]= float(str(self.ltsError.text()))
            pars["fixedlt_sloperatio"]= int(self.ltsCheck.isChecked())
            err= "Step Heigth Value"
            pars["step_heightratio"]= float(str(self.shValue.text()))
            err= "Step Heigth Error"
            pars["deltastep_heightratio"]= float(str(self.shError.text()))
            pars["fixedstep_heightratio"]= int(self.shCheck.isChecked())
            err= "Eta Factor Value"
            pars["eta_factor"]= float(str(self.etaValue.text()))
            err= "Step Heigth Error"
            pars["deltaeta_factor"]= float(str(self.etaError.text()))
            pars["fixedeta_factor"]= int(self.etaCheck.isChecked())
            return pars
        except Exception:
            self.__parError("PEAK SHAPE",
                            "Peak Shape Parameter error on:\n%s" % err)
            return None

    def __setFitPar(self):
        #Default 10 eV separation between two peaks only accessible
        #through file editing for the time being
        #self.deltaOnePeak = self.__get("fit", "deltaonepeak", 0.010)

        self.linpolOrder= self.__get("fit", "linpolorder", 1, int)
        self.exppolOrder= self.__get("fit", "exppolorder", 1, int)
        continuum= self.__get("fit", "continuum", 0, int)
        self.contCombo.setCurrentIndex(continuum)
        self.__contComboActivated(continuum)

        self.fitWeight = self.__get("fit", "fitweight", 1, int)
        self.weightCombo.setCurrentIndex(self.fitWeight)

        stripAlgorithm = self.__get("fit", "stripalgorithm", 0, int)
        self.setSNIP(stripAlgorithm)
        self.snipWidthSpin.setValue(self.__get("fit", "snipwidth", 20, int))

        self.stripWidthSpin.setValue(self.__get("fit", "stripwidth", 1, int))
        self.stripFilterSpin.setValue(self.__get("fit", "stripfilterwidth", 1, int))

        self.stripAnchorsFlagCheck.setChecked(self.__get("fit",
                                                         "stripanchorsflag",
                                                         0, int))
        anchorslist = self.__get("fit", "stripanchorslist", [0, 0, 0, 0], None)
        if anchorslist is None:anchorslist = []
        for spin in self.stripAnchorsList:
            spin.setValue(0)

        i = 0
        for value in anchorslist:
            self.stripAnchorsList[i].setValue(value)
            i += 1

        #self.stripConstValue.setText(self.__get("fit", "stripconstant",1.0))
        #self.stripConstValue.setDisabled(1)
        self.stripIterValue.setText(self.__get("fit", "stripiterations",20000))
        self.chi2Value.setText(self.__get("fit", "deltachi"))
        self.linearFitFlagCheck.setChecked(self.__get("fit", "linearfitflag", 0, int))
        self.iterSpin.setValue(self.__get("fit", "maxiter", 5, int))
        self.minSpin.setValue(self.__get("fit", "xmin", 0, int))
        self.maxSpin.setValue(self.__get("fit", "xmax", 16384, int))
        self.regionCheck.setChecked(self.__get("fit", "use_limit", 0, int))
        self.stripCheck.setChecked(self.__get("fit", "stripflag", 0, int))
        self.escapeCheck.setChecked(self.__get("fit", "escapeflag", 0, int))
        self.sumCheck.setChecked(self.__get("fit", "sumflag", 0, int))
        self.scatterCheck.setChecked(self.__get("fit", "scatterflag", 0, int))
        hypermetflag= self.__get("fit", "hypermetflag", 1, int)
        shortflag= (hypermetflag >> 1) & 1
        longflag= (hypermetflag >> 2) & 1
        stepflag= (hypermetflag >> 3) & 1
        self.shortCheck.setChecked(shortflag)
        self.longCheck.setChecked(longflag)
        self.stepCheck.setChecked(stepflag)
        energylist  = self.__get("fit", "energy", None, None)
        if type(energylist) != type([]):
            energy     = self.__get("fit", "energy", None, float)
            energylist = [energy]
            weightlist = [1.0]
            flaglist   = [1]
            scatterlist   = [1]
        else:
            energy      = energylist[0]
            weightlist  = self.__get("fit", "energyweight", None, None)
            flaglist    = self.__get("fit", "energyflag", None, None)
            scatterlist    = self.__get("fit", "energyscatter", None, None)
        self.energyTable.setParameters(energylist, weightlist, flaglist, scatterlist)
        self.strategyCheckBox.setChecked(self.__get("fit", "strategyflag", 0, int))

    def __getFitPar(self):
        pars= {}
        #Default 10 eV separation between two peaks accessible through file
        pars['deltaonepeak'] = self.__get("fit", "deltaonepeak", 0.010, float)
        err = "__getFitPar"
        #if 1:
        # fot the time being is nto necessary to read the combo box and
        # ask the strategy handler
        pars["strategy"] = "SingleLayerStrategy"
        pars["strategyflag"] = int(self.strategyCheckBox.isChecked())
        try:
            pars["fitfunction"]= int(self.functionCombo.currentIndex())
            pars["continuum"]= int(self.contCombo.currentIndex())
            pars["fitweight"]= int(self.weightCombo.currentIndex())
            pars["stripalgorithm"] = int(self.stripCombo.currentIndex())
            pars["linpolorder"]= self.linpolOrder or 1
            pars["exppolorder"]= self.exppolOrder or 1
            #pars["stripconstant"]= float(str(self.stripConstValue.text()))
            pars["stripconstant"]= 1.0
            pars["snipwidth"] = self.snipWidthSpin.value()
            pars["stripiterations"]= int(str(self.stripIterValue.text()))
            pars["stripwidth"]= self.stripWidthSpin.value()
            pars["stripfilterwidth"] = self.stripFilterSpin.value()
            pars["stripanchorsflag"] = int(self.stripAnchorsFlagCheck.isChecked())
            pars["stripanchorslist"] = []
            for spin in self.stripAnchorsList:
                pars["stripanchorslist"].append(spin.value())
            pars["maxiter"]= self.iterSpin.value()
            err= "Minimum Chi2 difference"
            pars["deltachi"]= float(str(self.chi2Value.text()))
            pars["xmin"]= self.minSpin.value()
            pars["xmax"]= self.maxSpin.value()
            pars["linearfitflag"] = int(self.linearFitFlagCheck.isChecked())
            pars["use_limit"]= int(self.regionCheck.isChecked())
            pars["stripflag"]= int(self.stripCheck.isChecked())
            pars["escapeflag"]= int(self.escapeCheck.isChecked())
            pars["sumflag"]= int(self.sumCheck.isChecked())
            pars["scatterflag"]= int(self.scatterCheck.isChecked())
            shortflag= int(self.shortCheck.isChecked())
            longflag= int(self.longCheck.isChecked())
            stepflag= int(self.stepCheck.isChecked())
            index = pars['fitfunction']
            if index == 0:
                hypermetflag = 1
            else:
                hypermetflag = 0
            if hypermetflag:
                pars["hypermetflag"]= 1 + shortflag*2 + longflag*4 + stepflag*8
            else:
                pars["hypermetflag"]= 0
            pars['energy'],pars['energyweight'],pars['energyflag'], pars['energyscatter']= \
                                self.energyTable.getParameters()
            return pars
        #else:
        except Exception:
            self.__parError("FIT",
                            "Fit parameter error on:\n%s" % err)
            return None

    def __setPeaksPar(self):
        pars= self._inputParameters.get("peaks", {})
        self.peakTable.setSelection(pars)

    def __getPeaksPar(self):
        return self.peakTable.getSelection()

    def __setDetPar(self):
        elt= self.__get("detector", "detele", "Si")
        for idx in range(self.elementCombo.count()):
            if str(self.elementCombo.itemText(idx))==elt:
                self.elementCombo.setCurrentIndex(idx)
                break

        #self.energyValue0.setText(self.__get("detector", "detene"))
        #self.energyValue1.setText("0.0")
        #self.intensityValue0.setText(self.__get("detector", "detint", "1.0"))
        #self.intensityValue1.setText("0.0")
        self.nEscapeThreshold.setValue(self.__get("detector", "nthreshold",4,int))
        self.zeroValue.setText(self.__get("detector", "zero"))
        self.zeroError.setText(self.__get("detector", "deltazero"))
        self.zeroCheck.setChecked(self.__get("detector", "fixedzero", 0, int))
        self.gainValue.setText(self.__get("detector", "gain"))
        self.gainError.setText(self.__get("detector", "deltagain"))
        self.gainCheck.setChecked(self.__get("detector", "fixedgain", 0, int))
        self.noiseValue.setText(self.__get("detector", "noise"))
        self.noiseError.setText(self.__get("detector", "deltanoise"))
        self.noiseCheck.setChecked(self.__get("detector", "fixednoise", 0, int))
        self.fanoValue.setText(self.__get("detector", "fano"))
        self.fanoError.setText(self.__get("detector", "deltafano"))
        self.fanoCheck.setChecked(self.__get("detector", "fixedfano", 0, int))
        self.sumfacValue.setText(self.__get("detector", "sum"))
        self.sumfacError.setText(self.__get("detector", "deltasum"))
        self.sumfacCheck.setChecked(self.__get("detector", "fixedsum", 0, int))
        self.ignoreSpectrumCalibration.setChecked( \
                    self.__get("detector", "ignoreinputcalibration", 0, int))

    def __getDetPar(self):
        pars= {}
        try:
        #if 1:
            err= "Detector Element"
            pars["detele"]= str(self.elementCombo.currentText())
            #err= "First Escape Energy Value"
            #pars["detene"]= float(str(self.energyValue0.text()))
            #err= "Second Escape Energy Value"
            #pars["energy1"]= float(str(self.energyValue1.text()))
            #err= "First Escape Energy Intensity"
            #pars["detint"]= float(str(self.intensityValue0.text()))
            #err= "Second Escape Energy Intensity"
            #pars["intensity1"]= float(str(self.intensityValue1.text()))
            err= "Maximum Number of Escape Peaks"
            pars["nthreshold"] = int(self.nEscapeThreshold.value())
            err= "Spectrometer Zero value"
            pars["zero"]= float(str(self.zeroValue.text()))
            err= "Spectrometer Zero error"
            pars["deltazero"]= float(str(self.zeroError.text()))
            pars["fixedzero"]= int(self.zeroCheck.isChecked())
            err= "Spectrometer Gain value"
            pars["gain"]= float(str(self.gainValue.text()))
            err= "Spectrometer Gain error"
            pars["deltagain"]= float(str(self.gainError.text()))
            pars["fixedgain"]= int(self.gainCheck.isChecked())
            err= "Detector Noise value"
            pars["noise"]= float(str(self.noiseValue.text()))
            err= "Detector Noise error"
            pars["deltanoise"]= float(str(self.noiseError.text()))
            pars["fixednoise"]= int(self.noiseCheck.isChecked())
            err= "Fano Factor value"
            pars["fano"]= float(str(self.fanoValue.text()))
            err= "Fano Factor error"
            pars["deltafano"]= float(str(self.fanoError.text()))
            pars["fixedfano"]= int(self.fanoCheck.isChecked())
            err= "Sum Factor value"
            pars["sum"]= float(str(self.sumfacValue.text()))
            err= "Sum Factor error"
            pars["deltasum"]= float(str(self.sumfacError.text()))
            pars["fixedsum"]= int(self.sumfacCheck.isChecked())
            pars["ignoreinputcalibration"] = \
                        int(self.ignoreSpectrumCalibration.isChecked())
            return pars
        #else:
        except Exception:
            self.__parError("DETECTOR", "Detector parameter error on:\n%s"%err)
            return None

    def __parError(self, tab, message):
        idx= self.tabLabel.index(tab)
        self.prevTabIdx= idx
        self.mainTab.setCurrentIndex(idx)
        qt.QMessageBox.critical(self, "ERROR on %s"%tab, message,
            qt.QMessageBox.Ok, qt.QMessageBox.NoButton, qt.QMessageBox.NoButton)

class SectionFileDialog(qt.QFileDialog):
    def __init__(self, parent=None, name="SectionFileDialog", sections=[], labels=None,
                     mode=None,modal =1, initdir=None):
        qt.QFileDialog.__init__(self, parent)
        self.setModal(modal)
        self.setWindowTitle(name)
        #layout = qt.QHBoxLayout(self)
        if hasattr(qt, "QStringList"):
            strlist = qt.QStringList()
        else:
            strlist = []
        strlist.append("Config Files *.cfg")
        strlist.append("All Files *")
        self.setFilters(strlist)
        if initdir is not None:
            if os.path.isdir(initdir):
                if hasattr(qt, "QString"):
                    self.setDir(qt.QString(initdir))
                else:
                    self.setDir(qt.safe_str(initdir))

        _logger.debug("right to be added")
        if 0:
            self.sectionWidget= SectionFileWidget(self,
                                              sections=sections,
                                              labels=labels)
            self.layout().addWidget(self.sectionWidget)
        if mode is not None:
            self.setFileMode(mode)

    def getFilename(self):
        filename= qt.safe_str(self.selectedFiles()[0])
        filetype= qt.safe_str(self.selectedFilter())
        if filetype.find("Config")==0:
            fileext= os.path.splitext(filename)[1]
            if not len(fileext):
                filename= "%s.cfg"%filename
        return filename

    def getSections(self):
        return self.sectionWidget.getSections()

class SectionFileWidget(qt.QWidget):
    def __init__(self, parent=None, name="FitParamSectionWidget", sections=[], labels=None, fl=0):
        qt.QWidget.__init__(self, parent)
        layout= qt.QVBoxLayout(self)
        self.sections= sections
        if labels is None:
            self.labels = []
            for label in self.sections:
                self.labels.append(label.upper())
        else:
            self.labels= labels

        group= qt.QGroupBox("Read sections", self)
        group.setAlignment(qt.Qt.Vertical)
        group.layout = qt.QVBoxLayout(group)

        layout.addWidget(group)
        self.allCheck= qt.QCheckBox("ALL", group)
        group.layout.addWidget(self.allCheck)
        self.check= {}
        for (sect, txt) in zip(self.sections, self.labels):
            self.check[sect]= qt.QCheckBox(txt, group)
            if QTVERSION > '4.0.0':
                group.layout.addWidget(self.check[sect])

        self.allCheck.setChecked(1)
        self.__allClicked()

        self.allCheck.clicked.connect(self.__allClicked)

    def __allClicked(self):
        state= self.allCheck.isChecked()
        for but in self.check.values():
            but.setChecked(state)
            but.setDisabled(state)

    def getSections(self):
        if self.allCheck.isChecked():
            return None
        else:
            sections= []
            for sect in self.check.keys():
                if self.check[sect].isChecked():
                    sections.append(sect)
            return sections


class FitParamDialog(qt.QDialog):
    def __init__(self, parent=None, name="FitParam",
                 modal=1, fl=0, initdir = None, fitresult=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("PyMca - MCA Fit Parameters")
        self.setWindowIcon(qt.QIcon(qt.QPixmap(Icons.IconDict["gioconda16"])))

        self.initDir = initdir
        layout= qt.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.fitparam= FitParamWidget(self)
        layout.addWidget(self.fitparam)
        self.setData = self.fitparam.setData

        #buts= qt.QButtonGroup(4, qt.Qt.Horizontal, self)
        buts= qt.QGroupBox(self)
        buts.layout = qt.QHBoxLayout(buts)
        loadfit = qt.QPushButton(buts)
        loadfit.setAutoDefault(False)
        loadfit.setText("Load From Fit")
        loadfit.setToolTip("Take non linear parameters\nfrom last fit")
        self.fitresult = fitresult
        load= qt.QPushButton(buts)
        load.setAutoDefault(False)
        load.setText("Load")
        save= qt.QPushButton(buts)
        save.setAutoDefault(False)
        save.setText("Save")
        reject= qt.QPushButton(buts)
        reject.setAutoDefault(False)
        reject.setText("Cancel")
        accept= qt.QPushButton(buts)
        accept.setAutoDefault(False)
        accept.setText("OK")

        if loadfit is not None:
            buts.layout.addWidget(loadfit)
        buts.layout.addWidget(load)
        buts.layout.addWidget(save)
        buts.layout.addWidget(reject)
        buts.layout.addWidget(accept)
        layout.addWidget(buts)
        self.loadfit = loadfit

        if self.fitresult is None:
            self.loadfit.setEnabled(False)
        else:
            self.loadfit.setEnabled(True)

        maxheight = qt.QDesktopWidget().height()
        maxwidth = qt.QDesktopWidget().width()
        self.setMaximumWidth(maxwidth)
        self.setMaximumHeight(maxheight)
        self.resize(qt.QSize(min(800, maxwidth), min(int(0.7 * maxheight), 750)))

        self.loadfit.clicked.connect(self.__loadFromFit)
        load.clicked.connect(self.load)
        save.clicked.connect(self.save)
        reject.clicked.connect(self.reject)
        accept.clicked.connect(self.accept)

    def setParameters(self, pars):
        actualPars = pars
        if 'fit' not in pars:
            if 'result' in pars:
                if 'config' in pars['result']:
                    #we are dealing with a .fit file ...
                    if 'fit' in pars['result']['config']:
                        actualPars = pars['result']['config']
        return self.fitparam.setParameters(actualPars)

    def getParameters(self):
        return self.fitparam.getParameters()

    def loadParameters(self, filename, sections=None):
        _logger.info("Filename to be read <%s>" % filename)
        cfg = ConfigDict.ConfigDict()
        if sections is not None:
            if 'attenuators' in sections:
                sections.append('materials')
                sections.append('multilayer')
        try:
        #if 1:
            cfg.read(filename, sections)
            self.initDir = os.path.dirname(filename)
        except Exception:
        #else:
            #self.initDir = None
            msg=qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            text = "Error %s" % sys.exc_info()[1]
            msg.setInformativeText(text)
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return 0
        self.setParameters(copy.deepcopy(cfg))
        return 1


    def __copyElementsMaterial(self):
        pars = {}
        for material in Elements.Material.keys():
            pars[material] = {}
            for key in Elements.Material[material].keys():
                pars[material][key] = Elements.Material[material][key]
        return pars

    def saveParameters(self, filename, sections=None):
        pars= self.getParameters()
        if sections is None:
            pars['materials'] = self.__copyElementsMaterial()
        elif 'attenuators' in sections:
            pars['materials'] = self.__copyElementsMaterial()
            sections.append('materials')
            sections.append('multilayer')
        cfg= ConfigDict.ConfigDict(initdict=pars)
        if sections is not None:
            for key in list(cfg.keys()):
                if key not in sections:
                    del cfg[key]
        try:
            cfg.write(filename, sections)
            self.initDir = os.path.dirname(filename)
            return 1
        except Exception:
            qt.QMessageBox.critical(self, "Save Parameters",
                "ERROR while saving parameters to\n%s"%filename,
                qt.QMessageBox.Ok, qt.QMessageBox.NoButton, qt.QMessageBox.NoButton)
            #self.initDir = None
            return 0

    def setFitResult(self, result = None):
        self.fitresult = result
        if result is None:
            self.loadfit.setEnabled(False)
        else:
            self.loadfit.setEnabled(True)

    def __loadFromFit(self):
        """
        Fill nonlinear parameters from last fit
        """
        if self.fitresult is None:
            text =  "Sorry. No fit parameters to be loaded.\n"
            text += "You need to have performed a fit."
            qt.QMessageBox.critical(self, "No fit data",
                                    text,
                                    qt.QMessageBox.Ok,
                                    qt.QMessageBox.NoButton,
                                    qt.QMessageBox.NoButton)
            return
        #detector
        zero = self.fitresult['fittedpar'][self.fitresult['parameters'].index('Zero')]
        gain = self.fitresult['fittedpar'][self.fitresult['parameters'].index('Gain')]
        noise= self.fitresult['fittedpar'][self.fitresult['parameters'].index('Noise')]
        fano = self.fitresult['fittedpar'][self.fitresult['parameters'].index('Fano')]
        sumf  = self.fitresult['fittedpar'][self.fitresult['parameters'].index('Sum')]

        self.fitparam.zeroValue.setText("%.6g" % zero)
        self.fitparam.gainValue.setText("%.6g" % gain)
        self.fitparam.noiseValue.setText("%.6g" % noise)
        self.fitparam.fanoValue.setText("%.6g" % fano)
        self.fitparam.sumfacValue.setText("%.6g" % sumf)

        #peak shape
        hypermetflag = self.fitresult['config']['fit']['hypermetflag']
        fitfunction = self.fitresult['config']['fit'].get('fitfunction', 0)
        if (fitfunction == 0) and (hypermetflag == 0):
            fitfunction = 1
        if fitfunction == 1:
            name = 'Eta Factor'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.etaValue.setText("%.6g" % value)
                deltaeta = min(value, float(self.fitparam.etaError.text()))
                self.fitparam.etaError.setText("%.6g" % deltaeta)
        elif hypermetflag > 1:
            # hypermetnames = ['ST AreaR', 'ST SlopeR',
            #                 'LT AreaR', 'LT SlopeR',
            #                 'STEP HeightR']
            name = 'ST AreaR'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.staValue.setText("%.6g" % value)

            name = 'ST SlopeR'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.stsValue.setText("%.6g" % value)

            name = 'LT AreaR'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.ltaValue.setText("%.6g" % value)

            name = 'LT SlopeR'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.ltsValue.setText("%.6g" % value)

            name = 'STEP HeightR'
            if name in self.fitresult['parameters']:
                value = self.fitresult['fittedpar'] \
                        [self.fitresult['parameters'].index(name)]
                self.fitparam.shValue.setText("%.6g" % value)


        text  = "If you do not use an exponential background, "
        text += "you can now ask the program to perform a linear "
        text += "fit, save the configuration, and you will be ready "
        text += "for a speedy batch."
        qt.QMessageBox.information(self,
                                "Batch tip",
                                text)
    def load(self):
        if self.initDir is None:
            self.initDir = PyMcaDirs.inputDir
        fileList = ConfigurationFileDialogs.getFitConfigurationFilePath(self,
                            mode="OPEN",
                            currentdir=self.initDir,
                            single=True)
        if fileList:
            filename = qt.safe_str(fileList[0])
            if filename:
                self.loadParameters(filename, None)
                self.initDir = os.path.dirname(filename)

    def save(self):
        #diag= SectionFileDialog(self, "Save Parameters", FitParamSections, FitParamHeaders, qt.QFileDialog.AnyFile)
        if self.initDir is None:
            self.initDir = PyMcaDirs.outputDir
        fileList = PyMcaFileDialogs.getFileList(self,
                            filetypelist=["Fit configuration files (*.cfg)"],
                            mode="SAVE",
                            message="Enter output fit configuration file",
                            currentdir=self.initDir,
                            single=True)
        if fileList:
            filename = qt.safe_str(fileList[0])
            if len(filename):
                if not filename.endswith(".cfg"):
                    filename += ".cfg"
                self.saveParameters(filename, None)
                self.initDir = os.path.dirname(filename)

def openDialog():
    wid= FitParamDialog(modal=1)
    ret = wid.exec()
    if ret == qt.QDialog.Accepted:
        npar = wid.getParameters()
        print(npar)
        del wid
    return ret

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    openDialog()
    app = None
