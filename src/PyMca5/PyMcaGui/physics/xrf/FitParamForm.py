#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "E. Papillon & V. Armando Sole - ESRF Software Group"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
from PyMca5.PyMcaGui import PyMcaQt as qt

QTVERSION = qt.qVersion()
QLabelAlignRight = qt.Qt.AlignRight
QLabelAlignCenter = qt.Qt.AlignCenter
QLabelAlignVCenter= qt.Qt.AlignVCenter
class Q3SpinBox(qt.QSpinBox):
    def setMinValue(self, v):
        self.setMinimum(v)

    def setMaxValue(self, v):
        self.setMaximum(v)

    def setLineStep(self, v):
        self.setSingleStep(v)

class Q3GridLayout(qt.QGridLayout):
    def addMultiCellWidget(self, w, r0, r1, c0, c1, *var):
        self.addWidget(w, r0, c0, 1 + r1 - r0, 1 + c1 - c0)


class FitParamForm(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self,parent)
        FitParamFormLayout = qt.QVBoxLayout(self)
        FitParamFormLayout.setContentsMargins(11, 11, 11, 11)
        FitParamFormLayout.setSpacing(6)
        self.mainTab = qt.QTabWidget(self)
        self.tabFit = qt.QWidget()
        tabFitLayout = qt.QVBoxLayout(self.tabFit)
        tabFitLayout.setContentsMargins(11, 11, 11, 11)
        tabFitLayout.setSpacing(6)
        layout5 = Q3GridLayout(None)
        #,1,1,
        layout5.setContentsMargins(11, 11, 11, 11)
        layout5.setSpacing(6)

        self.functionCombo = qt.QComboBox(self.tabFit)
        self.functionCombo.insertItem = self.functionCombo.addItem

        self.functionLabel = qt.QLabel(self.tabFit)
        self.functionLabel.setText("Fit Function")
        self.functionCombo.insertItem(str("Mca Hypermet"))
        self.functionCombo.insertItem(str("Mca Pseudo-Voigt"))


        self.snipWidthLabel = qt.QLabel(self.tabFit)
        self.snipWidthLabel.setText(str("SNIP Background Width"))

        self.stripWidthLabel = qt.QLabel(self.tabFit)
        self.stripWidthLabel.setText(str("Strip Background Width"))
        self.stripIterValue = qt.QLineEdit(self.tabFit)


        self.chi2Label = qt.QLabel(self.tabFit)
        self.chi2Label.setText(str("Minimum chi^2 difference (%)"))

        self.chi2Value = qt.QLineEdit(self.tabFit)

        self.linearFitFlagCheck = qt.QCheckBox(self.tabFit)
        self.linearFitFlagCheck.setText(str("Perform a Linear Fit Fixing non-linear Parameters to Initial Values"))

        self.strategyCheckBox = qt.QCheckBox(self.tabFit)
        self.strategyCheckBox.setText(str("Perform a fit using the selected strategy"))
        self.strategyCombo = qt.QComboBox(self.tabFit)
        self.strategyCombo.addItem(str("Single Layer"))
        self.strategySetupButton = qt.QPushButton(self.tabFit)
        self.strategySetupButton.setText('SETUP')
        self.strategySetupButton.setAutoDefault(False)

        self.mainTab.addTab(self.tabFit,str("FIT"))

        self.lastLabel = qt.QLabel(self.tabFit)
        lastLabel_font = qt.QFont(self.lastLabel.font())
        lastLabel_font.setItalic(1)
        self.lastLabel.setFont(lastLabel_font)
        self.lastLabel.setText(str("Fitting region last channel :"))
        self.lastLabel.setAlignment(QLabelAlignVCenter | QLabelAlignRight)

        self.regionCheck = qt.QCheckBox(self.tabFit)
        self.regionCheck.setText(str("Prevent overwriting of the fitting region on data update"))
        # limit tooltip
        limitToolTip = "Checking this box will prevent overwriting\n"
        limitToolTip += "the fitting region when updating the data\n"
        limitToolTip += "Use it to avoid setting the limits based on\n"
        limitToolTip += "a zoomed region"
        self.regionCheck.setToolTip(limitToolTip)

        self.topLine = qt.QFrame(self.tabFit)
        self.topLine.setFrameShape(qt.QFrame.HLine)
        self.topLine.setFrameShadow(qt.QFrame.Sunken)
        self.topLine.setFrameShape(qt.QFrame.HLine)


        ##########
        self.weightLabel = qt.QLabel(self.tabFit)
        self.weightLabel.setText("Statistical weighting of data")
        self.weightCombo = qt.QComboBox(self.tabFit)
        self.weightCombo.insertItem = self.weightCombo.addItem

        self.weightCombo.insertItem(str("NO Weight"))
        self.weightCombo.insertItem(str("Poisson (1/Y)"))
        #self.weightCombo.insertItem(str("Poisson (1/Y2)"))


        ##########
        self.iterLabel = qt.QLabel(self.tabFit)
        self.iterLabel.setText(str("Number of fit iterations"))


        self.contCombo = qt.QComboBox(self.tabFit)
        self.contCombo.insertItem = self.contCombo.addItem

        self.contCombo.insertItem(str("NO Continuum"))
        self.contCombo.insertItem(str("Constant"))
        self.contCombo.insertItem(str("Linear"))
        self.contCombo.insertItem(str("Parabolic"))
        self.contCombo.insertItem(str("Linear Polynomial"))
        self.contCombo.insertItem(str("Exp. Polynomial"))

        self.stripCombo = qt.QComboBox(self.tabFit)
        self.stripCombo.insertItem = self.stripCombo.addItem

        self.stripComboLabel = qt.QLabel(self.tabFit)
        self.stripComboLabel.setText("Non-analytical (or estimation) background algorithm")
        self.stripCombo.insertItem(str("Strip"))
        self.stripCombo.insertItem(str("SNIP"))
        self.stripCombo.activated[int].connect(self._stripComboActivated)

        self.snipWidthSpin = Q3SpinBox(self.tabFit)
        self.snipWidthSpin.setMaxValue(300)
        self.snipWidthSpin.setMinValue(0)

        self.stripWidthSpin = Q3SpinBox(self.tabFit)
        self.stripWidthSpin.setMaxValue(100)
        self.stripWidthSpin.setMinValue(1)


        self.orderSpin = Q3SpinBox(self.tabFit)
        self.orderSpin.setMaxValue(10)
        self.orderSpin.setMinValue(1)

        maxnchannel  = 16384*4

        self.maxSpin = Q3SpinBox(self.tabFit)
        self.maxSpin.setMaxValue(maxnchannel)
        self.maxSpin.setLineStep(128)

        self.minSpin = Q3SpinBox(self.tabFit)
        self.minSpin.setMaxValue(maxnchannel)
        self.minSpin.setLineStep(128)

        self.stripIterLabel = qt.QLabel(self.tabFit)
        self.stripIterLabel.setText(str("Strip Background Iterations"))

        self.iterSpin = Q3SpinBox(self.tabFit)
        self.iterSpin.setMaxValue(1000)
        self.iterSpin.setMinValue(1)

        self.stripFilterLabel = qt.QLabel(self.tabFit)
        self.stripFilterLabel.setText(str("Strip Background Smoothing Width (Savitsky-Golay)"))

        self.stripFilterSpin = Q3SpinBox(self.tabFit)
        self.stripFilterSpin.setMinValue(1)
        self.stripFilterSpin.setMaxValue(40)
        self.stripFilterSpin.setLineStep(2)

        ########
        self.anchorsContainer = qt.QWidget(self.tabFit)
        anchorsContainerLayout = qt.QHBoxLayout(self.anchorsContainer)
        anchorsContainerLayout.setContentsMargins(0, 0, 0, 0)
        anchorsContainerLayout.setSpacing(2)
        self.stripAnchorsFlagCheck = qt.QCheckBox(self.anchorsContainer)
        self.stripAnchorsFlagCheck.setText(str("Strip Background use Anchors"))
        anchorsContainerLayout.addWidget(self.stripAnchorsFlagCheck)

        self.stripAnchorsList = []
        for i in range(4):
            anchorSpin = Q3SpinBox(self.anchorsContainer)
            anchorSpin.setMinValue(0)
            anchorSpin.setMaxValue(maxnchannel)
            anchorsContainerLayout.addWidget(anchorSpin)
            self.stripAnchorsList.append(anchorSpin)
        #######

        self.firstLabel = qt.QLabel(self.tabFit)
        firstLabel_font = qt.QFont(self.firstLabel.font())
        firstLabel_font.setItalic(1)
        self.firstLabel.setFont(firstLabel_font)
        self.firstLabel.setText(str("Fitting region first channel :"))
        self.firstLabel.setAlignment(qt.Qt.AlignVCenter | qt.Qt.AlignRight)


        self.typeLabel = qt.QLabel(self.tabFit)
        self.typeLabel.setText(str("Continuum type"))

        self.orderLabel = qt.QLabel(self.tabFit)
        self.orderLabel.setText(str("Polynomial order"))

        self.bottomLine = qt.QFrame(self.tabFit)
        self.bottomLine.setFrameShape(qt.QFrame.HLine)
        self.bottomLine.setFrameShadow(qt.QFrame.Sunken)
        self.bottomLine.setFrameShape(qt.QFrame.HLine)

        layout5.addMultiCellWidget(self.functionLabel,0,0,0,1)
        layout5.addMultiCellWidget(self.functionCombo,0,0,3,4)


        layout5.addMultiCellWidget(self.typeLabel,1,1,0,1)
        layout5.addMultiCellWidget(self.contCombo,1,1,3,4)

        layout5.addMultiCellWidget(self.orderLabel,2,2,0,1)
        layout5.addMultiCellWidget(self.orderSpin,2,2,3,4)


        layout5.addMultiCellWidget(self.stripComboLabel, 3, 3, 0, 1)
        self.stripSetupButton = qt.QPushButton(self.tabFit)
        self.stripSetupButton.setText('SETUP')
        self.stripSetupButton.setAutoDefault(False)
        layout5.addWidget(self.stripCombo, 3, 3)
        layout5.addWidget(self.stripSetupButton, 3, 4)

        layout5.addMultiCellWidget(self.snipWidthLabel,4,4,0,1)
        layout5.addMultiCellWidget(self.snipWidthSpin,4,4,3,4)

        layout5.addMultiCellWidget(self.stripWidthLabel,5,5,0,1)
        layout5.addMultiCellWidget(self.stripWidthSpin,5,5,3,4)

        layout5.addMultiCellWidget(self.stripIterLabel,6,6,0,1)
        layout5.addMultiCellWidget(self.stripIterValue,6,6,3,4)

        layout5.addMultiCellWidget(self.stripFilterLabel,7,7,0,1)
        layout5.addMultiCellWidget(self.stripFilterSpin,7,7,3,4)

        layout5.addMultiCellWidget(self.anchorsContainer,8,8,0,4)

        layout5.addWidget(self.weightLabel,9,0)
        layout5.addMultiCellWidget(self.weightCombo,9,9,3,4)

        layout5.addWidget(self.iterLabel,10,0)
        layout5.addWidget(qt.HorizontalSpacer(self.tabFit),10,1)
        layout5.addMultiCellWidget(self.iterSpin,10,10,3,4)

        layout5.addWidget(self.chi2Label, 11, 0)
        layout5.addMultiCellWidget(self.chi2Value, 11, 11,3,4)

        layout5.addMultiCellWidget(self.strategyCheckBox, 12, 12, 0, 4)
        layout5.addWidget(self.strategyCombo, 12, 3)
        layout5.addWidget(self.strategySetupButton, 12, 4)
        layout5.addMultiCellWidget(self.linearFitFlagCheck, 13, 13, 0, 4)

        layout5.addMultiCellWidget(self.topLine, 14, 15,0,4)

        layout5.addMultiCellWidget(self.minSpin,15, 16,4,4)

        layout5.addWidget(self.regionCheck,16,0)
        layout5.addMultiCellWidget(self.firstLabel,16, 16,2,3)

        layout5.addMultiCellWidget(self.lastLabel,17,17,2,3)
        layout5.addWidget(self.maxSpin,17,4)
        layout5.addMultiCellWidget(self.bottomLine,18,18,0,4)

        tabFitLayout.addLayout(layout5)

        includeWidget = qt.QWidget(self.tabFit)
        includeLayout = Q3GridLayout(includeWidget)
        includeLayout.setContentsMargins(0, 0, 0, 0)
        includeLayout.setSpacing(3)

        self.stepCheck = qt.QCheckBox(includeWidget)
        self.stepCheck.setText(str("Step tail"))

        includeLayout.addWidget(self.stepCheck,2,2)

        self.escapeCheck = qt.QCheckBox(includeWidget)
        self.escapeCheck.setText(str("Escape peaks"))

        includeLayout.addWidget(self.escapeCheck,1,1)

        self.includeLabel = qt.QLabel(includeWidget)
        includeLabel_font = qt.QFont(self.includeLabel.font())
        includeLabel_font.setBold(1)
        self.includeLabel.setFont(includeLabel_font)
        self.includeLabel.setText(str("Include:"))

        includeLayout.addWidget(self.includeLabel,0,0)

        self.sumCheck = qt.QCheckBox(includeWidget)
        self.sumCheck.setText(str("Pile-up peaks"))

        includeLayout.addWidget(self.sumCheck,1,2)

        self.scatterCheck = qt.QCheckBox(includeWidget)
        self.scatterCheck.setText(str("Scattering peaks"))

        includeLayout.addWidget(self.scatterCheck,1,3)

        self.stripCheck = qt.QCheckBox(includeWidget)
        self.stripCheck.setText(str("Stripping"))

        includeLayout.addWidget(self.stripCheck,1,0)

        self.longCheck = qt.QCheckBox(includeWidget)
        self.longCheck.setText(str("Long tail"))

        includeLayout.addWidget(self.longCheck,2,1)

        self.shortCheck = qt.QCheckBox(includeWidget)
        self.shortCheck.setText(str("Short tail"))

        includeLayout.addWidget(self.shortCheck,2,0)
        #tabFitLayout.addLayout(includeLayout)
        layout5.addMultiCellWidget(includeWidget,18,19,0,4)

        spacer_2 = qt.QSpacerItem(20, 40,\
                                  qt.QSizePolicy.Minimum,\
                                  qt.QSizePolicy.Expanding)
        tabFitLayout.addItem(spacer_2)

        #self.mainTab.addTab(self.tabFit,str("FIT"))
        self.tabDetector = qt.QWidget()
        tabDetectorLayout = qt.QVBoxLayout(self.tabDetector)
        tabDetectorLayout.setContentsMargins(11, 11, 11, 11)
        tabDetectorLayout.setSpacing(6)

        detLayout = Q3GridLayout(None)
        detLayout.setContentsMargins(0, 0, 0, 0)
        detLayout.setSpacing(2)
        self.elementCombo = qt.QComboBox(self.tabDetector)

        self.elementCombo.insertItem(0, str("Si"))
        self.elementCombo.insertItem(1, str("Ge"))
        self.elementCombo.insertItem(2, str("Cd1Te1"))
        self.elementCombo.insertItem(3, str("Hg1I2"))
        self.elementCombo.insertItem(4, str("Ga1As1"))
        self.elementCombo.setEnabled(1)
        self.elementCombo.setDuplicatesEnabled(0)

        detLayout.addWidget(self.elementCombo,0,3)

        self.elementLabel = qt.QLabel(self.tabDetector)
        self.elementLabel.setText(str("Detector Composition"))

        detLayout.addWidget(self.elementLabel,0,0)
        self.escapeLabel = qt.QLabel(self.tabDetector)
        self.escapeLabel.setText(str("Maximum Number of Escape energies"))
        detLayout.addMultiCellWidget(self.escapeLabel,3,4,0,0)

        #self.intensityValue0 = QLineEdit(self.tabDetector,"intensityValue0")
        #self.intensityValue0.setText(str("1.0"))
        #self.intensityValue0.setReadOnly(1)
        self.nEscapeThreshold = Q3SpinBox(self.tabDetector)
        self.nEscapeThreshold.setMaxValue(20)
        self.nEscapeThreshold.setMinValue(1)
        self.nEscapeThreshold.setValue(4)
        #detLayout.addWidget(self.intensityValue0,3,3)
        detLayout.addWidget(self.nEscapeThreshold,3,3)
        spacer_4 = qt.QSpacerItem(89, 20,\
                                  qt.QSizePolicy.Expanding,
                                  qt.QSizePolicy.Minimum)
        detLayout.addItem(spacer_4,3,1)
        tabDetectorLayout.addLayout(detLayout)

        self.calibLine = qt.QFrame(self.tabDetector)
        self.calibLine.setFrameShape(qt.QFrame.HLine)
        self.calibLine.setFrameShadow(qt.QFrame.Sunken)
        self.calibLine.setFrameShape(qt.QFrame.HLine)
        tabDetectorLayout.addWidget(self.calibLine)

        layout5_2 = Q3GridLayout(None)
        layout5_2.setContentsMargins(11, 11, 11, 11)
        layout5_2.setSpacing(2)
        self.zeroError = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.zeroError,1,5)

        self.sumfacSepLabel = qt.QLabel(self.tabDetector)
        sumfacSepLabel_font = qt.QFont(self.sumfacSepLabel.font())
        sumfacSepLabel_font.setBold(1)
        self.sumfacSepLabel.setFont(sumfacSepLabel_font)
        self.sumfacSepLabel.setText(str("+/-"))

        layout5_2.addWidget(self.sumfacSepLabel,5,4)

        self.noiseLabel = qt.QLabel(self.tabDetector)
        self.noiseLabel.setText(str("Detector noise (keV)"))

        layout5_2.addWidget(self.noiseLabel,3,0)

        self.gainCheck = qt.QCheckBox(self.tabDetector)
        self.gainCheck.setText(str(""))

        layout5_2.addWidget(self.gainCheck,2,2)

        self.gainLabel = qt.QLabel(self.tabDetector)
        self.gainLabel.setText(str("Spectrometer gain (keV/ch)"))

        layout5_2.addWidget(self.gainLabel,2,0)

        self.sumfacLabel = qt.QLabel(self.tabDetector)
        self.sumfacLabel.setText(str("Pile-up Factor"))

        layout5_2.addWidget(self.sumfacLabel,5,0)

        self.noiseError = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.noiseError,3,5)

        self.zeroValue = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.zeroValue,1,3)

        self.fanoSepLabel = qt.QLabel(self.tabDetector)
        fanoSepLabel_font = qt.QFont(self.fanoSepLabel.font())
        fanoSepLabel_font.setBold(1)
        self.fanoSepLabel.setFont(fanoSepLabel_font)
        self.fanoSepLabel.setText(str("+/-"))

        layout5_2.addWidget(self.fanoSepLabel,4,4)

        self.fanoError = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.fanoError,4,5)

        self.zeroSepLabel = qt.QLabel(self.tabDetector)
        zeroSepLabel_font = qt.QFont(self.zeroSepLabel.font())
        zeroSepLabel_font.setBold(1)
        self.zeroSepLabel.setFont(zeroSepLabel_font)
        self.zeroSepLabel.setText(str("+/-"))

        layout5_2.addWidget(self.zeroSepLabel,1,4)

        self.valueLabel = qt.QLabel(self.tabDetector)
        valueLabel_font = qt.QFont(self.valueLabel.font())
        valueLabel_font.setItalic(1)
        self.valueLabel.setFont(valueLabel_font)
        self.valueLabel.setText(str("Value"))
        self.valueLabel.setAlignment(qt.Qt.AlignCenter)

        layout5_2.addWidget(self.valueLabel,0,3)
        layout5_2.addWidget(qt.HorizontalSpacer(self.tabDetector),1,1)

        self.noiseValue = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.noiseValue,3,3)

        self.fanoValue = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.fanoValue,4,3)

        self.zeroLabel = qt.QLabel(self.tabDetector)
        self.zeroLabel.setText(str("Spectrometer zero (keV)"))

        layout5_2.addWidget(self.zeroLabel,1,0)

        self.sumfacError = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.sumfacError,5,5)

        self.noiseSepLabel = qt.QLabel(self.tabDetector)
        noiseSepLabel_font = qt.QFont(self.noiseSepLabel.font())
        noiseSepLabel_font.setBold(1)
        self.noiseSepLabel.setFont(noiseSepLabel_font)
        self.noiseSepLabel.setText(str("+/-"))

        layout5_2.addWidget(self.noiseSepLabel,3,4)

        self.sumfacCheck = qt.QCheckBox(self.tabDetector)
        self.sumfacCheck.setText(str(""))

        layout5_2.addWidget(self.sumfacCheck,5,2)

        self.noiseCheck = qt.QCheckBox(self.tabDetector)
        self.noiseCheck.setText(str(""))

        layout5_2.addWidget(self.noiseCheck,3,2)

        self.errorLabel = qt.QLabel(self.tabDetector)
        errorLabel_font = qt.QFont(self.errorLabel.font())
        errorLabel_font.setItalic(1)
        self.errorLabel.setFont(errorLabel_font)
        self.errorLabel.setText(str("Delta "))
        self.errorLabel.setAlignment(QLabelAlignCenter)

        layout5_2.addWidget(self.errorLabel,0,5)

        self.fixedLabel = qt.QLabel(self.tabDetector)
        fixedLabel_font = qt.QFont(self.fixedLabel.font())
        fixedLabel_font.setItalic(1)
        self.fixedLabel.setFont(fixedLabel_font)
        self.fixedLabel.setText(str("Fixed "))
        self.fixedLabel.setAlignment(qt.Qt.AlignVCenter)

        layout5_2.addWidget(self.fixedLabel,0,2)

        self.zeroCheck = qt.QCheckBox(self.tabDetector)
        self.zeroCheck.setText(str(""))

        layout5_2.addWidget(self.zeroCheck,1,2)

        self.sumfacValue = qt.QLineEdit(self.tabDetector,)

        layout5_2.addWidget(self.sumfacValue,5,3)

        self.fanoLabel = qt.QLabel(self.tabDetector)
        self.fanoLabel.setText(str("Fano factor (Si ~ 0.12, Ge ~ 0.1)"))

        layout5_2.addWidget(self.fanoLabel,4,0)

        self.gainValue = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.gainValue,2,3)

        self.gainSepLabel = qt.QLabel(self.tabDetector)
        gainSepLabel_font = qt.QFont(self.gainSepLabel.font())
        gainSepLabel_font.setBold(1)
        self.gainSepLabel.setFont(gainSepLabel_font)
        self.gainSepLabel.setText(str("+/-"))

        layout5_2.addWidget(self.gainSepLabel, 2, 4)

        self.fanoCheck = qt.QCheckBox(self.tabDetector)
        self.fanoCheck.setText(str(""))

        layout5_2.addWidget(self.fanoCheck, 4, 2)

        self.gainError = qt.QLineEdit(self.tabDetector)

        layout5_2.addWidget(self.gainError, 2, 5)

        self.ignoreSpectrumCalibration = qt.QCheckBox(self.tabDetector)
        ignoreToolTip = "If checked, the starting calibration parameters "
        ignoreToolTip += "will not be replaced by the input spectrum "
        ignoreToolTip += "ones.\n"
        self.ignoreSpectrumCalibration.setToolTip(ignoreToolTip)
        ignoreText = "Ignore calibration from input data"
        self.ignoreSpectrumCalibration.setText(ignoreText)
        self.ignoreSpectrumCalibration.setChecked(False)
        layout5_2.addWidget(self.ignoreSpectrumCalibration, 6, 0)

        tabDetectorLayout.addLayout(layout5_2)
        spacer_6 = qt.QSpacerItem(20, 2,\
                                  qt.QSizePolicy.Minimum,\
                                  qt.QSizePolicy.Expanding)
        tabDetectorLayout.addItem(spacer_6)
        self.mainTab.addTab(self.tabDetector,str("DETECTOR"))
        self.TabBeam = qt.QWidget()
        self.mainTab.addTab(self.TabBeam,str("BEAM"))

        self.TabPeaks = qt.QWidget()
        self.mainTab.addTab(self.TabPeaks,str("PEAKS"))

        self.tabPeakShape = qt.QWidget()
        tabPeakShapeLayout = Q3GridLayout(self.tabPeakShape)
        tabPeakShapeLayout.setContentsMargins(11, 11, 11, 11)
        tabPeakShapeLayout.setSpacing(2)

        spacer_7 = qt.QSpacerItem(20, 90,\
                                  qt.QSizePolicy.Minimum,\
                                  qt.QSizePolicy.Expanding)
        tabPeakShapeLayout.addItem(spacer_7,8,0)

        self.staLabel = qt.QLabel(self.tabPeakShape)
        self.staLabel.setText(str("Short Tail Area"))

        tabPeakShapeLayout.addWidget(self.staLabel,2,0)
        spacer_8 = qt.QSpacerItem(59, 20,\
                                  qt.QSizePolicy.Expanding,\
                                  qt.QSizePolicy.Minimum)
        tabPeakShapeLayout.addItem(spacer_8,1,1)

        self.fixedLabel_2 = qt.QLabel(self.tabPeakShape)
        fixedLabel_2_font = qt.QFont(self.fixedLabel_2.font())
        fixedLabel_2_font.setItalic(1)
        self.fixedLabel_2.setFont(fixedLabel_2_font)
        self.fixedLabel_2.setText(str("Fixed"))
        self.fixedLabel_2.setAlignment(QLabelAlignVCenter)

        tabPeakShapeLayout.addWidget(self.fixedLabel_2, 1, 2)

        self.staCheck = qt.QCheckBox(self.tabPeakShape)
        self.staCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.staCheck,2,2)

        self.valueLabel_2 = qt.QLabel(self.tabPeakShape)
        valueLabel_2_font = qt.QFont(self.valueLabel_2.font())
        valueLabel_2_font.setItalic(1)
        self.valueLabel_2.setFont(valueLabel_2_font)
        self.valueLabel_2.setText(str("Value"))
        self.valueLabel_2.setAlignment(QLabelAlignCenter)

        tabPeakShapeLayout.addWidget(self.valueLabel_2,1,3)

        self.staValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.staValue,2,3)

        self.staSep = qt.QLabel(self.tabPeakShape)
        staSep_font = qt.QFont(self.staSep.font())
        staSep_font.setBold(1)
        self.staSep.setFont(staSep_font)
        self.staSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.staSep,2,4)

        self.errorLabel_2 = qt.QLabel(self.tabPeakShape)
        errorLabel_2_font = qt.QFont(self.errorLabel_2.font())
        errorLabel_2_font.setItalic(1)
        self.errorLabel_2.setFont(errorLabel_2_font)
        self.errorLabel_2.setText(str("Error"))
        self.errorLabel_2.setAlignment(QLabelAlignCenter)

        tabPeakShapeLayout.addWidget(self.errorLabel_2,1,5)

        self.staError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.staError,2,5)

        self.stsError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.stsError,3,5)

        self.stsSep = qt.QLabel(self.tabPeakShape)
        stsSep_font = qt.QFont(self.stsSep.font())
        stsSep_font.setBold(1)
        self.stsSep.setFont(stsSep_font)
        self.stsSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.stsSep,3,4)

        self.stsValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.stsValue,3,3)

        self.stsCheck = qt.QCheckBox(self.tabPeakShape)
        self.stsCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.stsCheck,3,2)

        self.stsLabel = qt.QLabel(self.tabPeakShape)
        self.stsLabel.setText(str("Short Tail Slope"))

        tabPeakShapeLayout.addWidget(self.stsLabel,3,0)

        self.ltaLabel = qt.QLabel(self.tabPeakShape)
        self.ltaLabel.setText(str("Long Tail Area"))

        tabPeakShapeLayout.addWidget(self.ltaLabel,4,0)

        self.ltaCheck = qt.QCheckBox(self.tabPeakShape)
        self.ltaCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.ltaCheck,4,2)

        self.ltaValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.ltaValue,4,3)

        self.ltaSep = qt.QLabel(self.tabPeakShape)
        ltaSep_font = qt.QFont(self.ltaSep.font())
        ltaSep_font.setBold(1)
        self.ltaSep.setFont(ltaSep_font)
        self.ltaSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.ltaSep,4,4)

        self.ltaError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.ltaError,4,5)

        self.ltsError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.ltsError,5,5)

        self.ltsSep = qt.QLabel(self.tabPeakShape)
        ltsSep_font = qt.QFont(self.ltsSep.font())
        ltsSep_font.setBold(1)
        self.ltsSep.setFont(ltsSep_font)
        self.ltsSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.ltsSep,5,4)

        self.ltsValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.ltsValue,5,3)

        self.ltsCheck = qt.QCheckBox(self.tabPeakShape)
        self.ltsCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.ltsCheck,5,2)

        self.ltsLabel = qt.QLabel(self.tabPeakShape)
        self.ltsLabel.setText(str("Long Tail Slope"))

        tabPeakShapeLayout.addWidget(self.ltsLabel,5,0)

        # Step Height
        self.shLabel = qt.QLabel(self.tabPeakShape)
        self.shLabel.setText(str("Step Height"))

        tabPeakShapeLayout.addWidget(self.shLabel,6,0)

        self.shCheck = qt.QCheckBox(self.tabPeakShape)
        self.shCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.shCheck,6,2)

        self.shValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.shValue,6,3)

        self.shSep = qt.QLabel(self.tabPeakShape)
        shSep_font = qt.QFont(self.shSep.font())
        shSep_font.setBold(1)
        self.shSep.setFont(shSep_font)
        self.shSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.shSep,6,4)

        self.shError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.shError,6,5)

        # Pseudo-Voigt Eta Factor
        self.etaLabel = qt.QLabel(self.tabPeakShape)
        self.etaLabel.setText(str("Pseudo-Voigt Eta"))

        tabPeakShapeLayout.addWidget(self.etaLabel,7,0)

        self.etaCheck = qt.QCheckBox(self.tabPeakShape)
        self.etaCheck.setText(str(""))

        tabPeakShapeLayout.addWidget(self.etaCheck,7,2)

        self.etaValue = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.etaValue,7,3)

        self.etaSep = qt.QLabel(self.tabPeakShape)
        etaSep_font = qt.QFont(self.etaSep.font())
        etaSep_font.setBold(1)
        self.etaSep.setFont(etaSep_font)
        self.etaSep.setText(str("+/-"))

        tabPeakShapeLayout.addWidget(self.etaSep,7,4)

        self.etaError = qt.QLineEdit(self.tabPeakShape)

        tabPeakShapeLayout.addWidget(self.etaError,7,5)

        self.mainTab.addTab(self.tabPeakShape,str("PEAK SHAPE"))

        FitParamFormLayout.addWidget(self.mainTab)

        self.setTabOrder(self.mainTab,self.elementCombo)
        self.setTabOrder(self.zeroCheck,self.zeroValue)
        self.setTabOrder(self.zeroValue,self.zeroError)
        self.setTabOrder(self.zeroError,self.gainCheck)
        self.setTabOrder(self.gainCheck,self.gainValue)
        self.setTabOrder(self.gainValue,self.gainError)
        self.setTabOrder(self.gainError,self.noiseCheck)
        self.setTabOrder(self.noiseCheck,self.noiseValue)
        self.setTabOrder(self.noiseValue,self.noiseError)
        self.setTabOrder(self.noiseError,self.fanoCheck)
        self.setTabOrder(self.fanoCheck,self.fanoValue)
        self.setTabOrder(self.fanoValue,self.fanoError)
        self.setTabOrder(self.fanoError,self.staCheck)
        self.setTabOrder(self.staCheck,self.staValue)
        self.setTabOrder(self.staValue,self.staError)
        self.setTabOrder(self.staError,self.stsCheck)
        self.setTabOrder(self.stsCheck,self.stsValue)
        self.setTabOrder(self.stsValue,self.stsError)
        self.setTabOrder(self.stsError,self.ltaCheck)
        self.setTabOrder(self.ltaCheck,self.ltaValue)
        self.setTabOrder(self.ltaValue,self.ltaError)
        self.setTabOrder(self.ltaError,self.ltsCheck)
        self.setTabOrder(self.ltsCheck,self.ltsValue)
        self.setTabOrder(self.ltsValue,self.ltsError)
        self.setTabOrder(self.ltsError,self.shCheck)
        self.setTabOrder(self.shCheck,self.shValue)
        self.setTabOrder(self.shValue,self.shError)
        self.setTabOrder(self.shError,self.contCombo)
        self.setTabOrder(self.contCombo,self.stripCombo)
        self.setTabOrder(self.stripCombo,self.iterSpin)
        self.setTabOrder(self.iterSpin,self.chi2Value)
        self.setTabOrder(self.chi2Value,self.regionCheck)
        self.setTabOrder(self.regionCheck,self.minSpin)
        self.setTabOrder(self.minSpin,self.maxSpin)
        self.setTabOrder(self.maxSpin,self.stripCheck)
        self.setTabOrder(self.stripCheck,self.escapeCheck)
        self.setTabOrder(self.escapeCheck,self.sumCheck)
        self.setTabOrder(self.sumCheck,self.scatterCheck)
        self.setTabOrder(self.scatterCheck,self.shortCheck)
        self.setTabOrder(self.shortCheck,self.longCheck)
        self.setTabOrder(self.longCheck,self.stepCheck)
        self._stripComboActivated(0)

    def _stripComboActivated(self, intValue):
        if intValue == 1:
            self.setSNIP(True)
        else:
            self.setSNIP(False)

    def setSNIP(self, bValue):
        if bValue:
            self.snipWidthSpin.setEnabled(True)
            self.stripWidthSpin.setEnabled(False)
            #self.stripFilterSpin.setEnabled(False)
            self.stripIterValue.setEnabled(False)
            self.stripCombo.setCurrentIndex(1)
        else:
            self.snipWidthSpin.setEnabled(False)
            #self.stripFilterSpin.setEnabled(True)
            self.stripWidthSpin.setEnabled(True)
            self.stripIterValue.setEnabled(True)
            self.stripCombo.setCurrentIndex(0)


if __name__ == "__main__":
    a = qt.QApplication(sys.argv)
    a.lastWindowClosed.connect(a.quit)
    w = FitParamForm()
    w.show()
    a.exec()
    a = None
