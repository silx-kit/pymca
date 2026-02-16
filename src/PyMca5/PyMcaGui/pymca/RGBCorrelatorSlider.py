#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
import logging
from PyMca5.PyMcaGui.misc import DoubleSlider
qt = DoubleSlider.qt

QTVERSION = qt.qVersion()
_logger = logging.getLogger(__name__)


class RGBCorrelatorSlider(qt.QWidget):
    sigRGBCorrelatorSliderSignal = qt.pyqtSignal(object)
    def __init__(self, parent = None, scale = False, autoscalelimits=None):
        qt.QWidget.__init__(self, parent)
        self.__emitSignals = True
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self._buttonBox = qt.QWidget(self)
        self._buttonBoxLayout = qt.QGridLayout(self._buttonBox)
        self._buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._buttonBoxLayout.setSpacing(0)

        if autoscalelimits is None:
            self.fromA =  5.0
            self.toB   = 95.0
        else:
            self.fromA = autoscalelimits[0]
            self.toB   = autoscalelimits[1]
            if self.fromA > self.toB:
                self.fromA = autoscalelimits[1]
                self.toB   = autoscalelimits[0]

        self.autoScaleButton = qt.QPushButton(self._buttonBox)
        self.autoScaleButton.setText("Autoscale")
        self.autoScaleFromAToBButton = qt.QPushButton(self._buttonBox)
        self.autoScaleFromAToBButton.setText("Autoscale %d-%d" %
                                             (int(self.fromA), int(self.toB)))
        self.autoScale90Button = qt.QPushButton(self._buttonBox)
        self.autoScale90Button.setText("Autoscale 0-90")
        self._buttonBoxLayout.addWidget(self.autoScaleButton, 0, 0)
        self._buttonBoxLayout.addWidget(self.autoScaleFromAToBButton, 0, 1)
        self._buttonBoxLayout.addWidget(self.autoScale90Button, 0, 2)

        self._gridBox = qt.QWidget(self)
        self._gridBoxLayout = qt.QGridLayout(self._gridBox)
        self._gridBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._gridBoxLayout.setSpacing(0)

        redLabel = MyQLabel(self._gridBox, color = qt.Qt.red)
        redLabel.setText("RED")
        self.redSlider = DoubleSlider.DoubleSlider(self._gridBox)

        greenLabel = MyQLabel(self._gridBox, color = qt.Qt.green)
        greenLabel.setText("GREEN")
        self.greenSlider = DoubleSlider.DoubleSlider(self._gridBox)

        blueLabel = MyQLabel(self._gridBox, color = qt.Qt.blue)
        blueLabel.setText("BLUE")
        self.blueSlider = DoubleSlider.DoubleSlider(self._gridBox, scale = True)

        self._gridBoxLayout.addWidget(redLabel, 0, 0)
        self._gridBoxLayout.addWidget(self.redSlider, 0, 1)

        self._gridBoxLayout.addWidget(greenLabel, 1, 0)
        self._gridBoxLayout.addWidget(self.greenSlider, 1, 1)

        self._gridBoxLayout.addWidget(blueLabel, 2, 0)
        self._gridBoxLayout.addWidget(self.blueSlider, 2, 1)

        self.mainLayout.addWidget(self._buttonBox)
        self.mainLayout.addWidget(self._gridBox)


        self.redSlider.sigDoubleSliderValueChanged.connect(\
                     self._redSliderChanged)

        self.greenSlider.sigDoubleSliderValueChanged.connect(\
                     self._greenSliderChanged)

        self.blueSlider.sigDoubleSliderValueChanged.connect(\
                     self._blueSliderChanged)

        self.autoScaleButton.clicked.connect(self.autoScale)

        self.autoScaleFromAToBButton.clicked.connect(self.autoScaleFromAToB)

        self.autoScale90Button.clicked.connect(self.autoScale90)

    def autoScale(self):
        self.__emitSignals = False
        self.redSlider.setMinMax(0., 100.)
        self.greenSlider.setMinMax(0.0, 100.)
        self.blueSlider.setMinMax(0., 100.)
        self.__emitSignals = True
        self._allChangedSignal()

    def autoScaleFromAToB(self):
        self.__emitSignals = False
        self.redSlider.setMinMax( self.fromA, self.toB)
        self.greenSlider.setMinMax(self.fromA, self.toB)
        self.blueSlider.setMinMax(self.fromA, self.toB)
        self.__emitSignals = True
        self._allChangedSignal()

    def autoScale90(self):
        self.__emitSignals = False
        self.redSlider.setMinMax(0., 90.)
        self.greenSlider.setMinMax(0.0, 90.)
        self.blueSlider.setMinMax(0., 90.)
        self.__emitSignals = True
        self._allChangedSignal()

    def _allChangedSignal(self):
        ddict = {}
        ddict['event'] = "allChanged"
        ddict['red']   = self.redSlider.getMinMax()
        ddict['green'] = self.greenSlider.getMinMax()
        ddict['blue']  = self.blueSlider.getMinMax()
        self.sigRGBCorrelatorSliderSignal.emit(ddict)

    def _redSliderChanged(self, ddict):
        _logger.debug("RGBCorrelatorSlider._redSliderChanged()")
        if self.__emitSignals:
            ddict['event'] = "redChanged"
            self.sigRGBCorrelatorSliderSignal.emit(ddict)

    def _greenSliderChanged(self, ddict):
        _logger.debug("RGBCorrelatorSlider._greenSliderChanged()")
        if self.__emitSignals:
            ddict['event'] = "greenChanged"
            self.sigRGBCorrelatorSliderSignal.emit(ddict)

    def _blueSliderChanged(self, ddict):
        _logger.debug("RGBCorrelatorSlider._blueSliderChanged()")
        if self.__emitSignals:
            ddict['event'] = "blueChanged"
            self.sigRGBCorrelatorSliderSignal.emit(ddict)

class MyQLabel(qt.QLabel):
    def __init__(self,parent=None,name=None,fl=0,bold=True, color= qt.Qt.red):
        qt.QLabel.__init__(self,parent)
        if qt.qVersion() <'4.0.0':
            self.color = color
            self.bold  = bold
        else:
            palette = qt.QPalette(self.palette())
            role = self.foregroundRole()
            palette.setColor(role,color)
            self.setPalette(palette)
            self.font().setBold(bold)


    if qt.qVersion() < '4.0.0':
        def drawContents(self, painter):
            painter.font().setBold(self.bold)
            pal =self.palette()
            pal.setColor(qt.QColorGroup.Foreground,self.color)
            self.setPalette(pal)
            qt.QLabel.drawContents(self,painter)
            painter.font().setBold(0)

def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)

    def slot(ddict):
        print("received dict = ", ddict)
    w = RGBCorrelatorSlider()
    w.sigRGBCorrelatorSliderSignal.connect(slot)
    w.show()
    app.exec()

if __name__ == "__main__":
    test()

