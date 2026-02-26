#/*##########################################################################
# Copyright (C) 2004-2014 V.A. Sole, European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
from PyMca5.PyMcaGui import PyMcaQt as qt

QTVERSION = qt.qVersion()


def uic_load_pixmap_FitActionsGui(name):
    pix = qt.QPixmap()
    return pix


class FitActionsGui(qt.QWidget):
    def __init__(self,parent = None,name = None,fl = 0):
        qt.QWidget.__init__(self,parent)

        self.resize(234,53)

        FitActionsGUILayout = qt.QGridLayout(self)
        FitActionsGUILayout.setContentsMargins(11, 11, 11, 11)
        FitActionsGUILayout.setSpacing(6)
        Layout9 = qt.QHBoxLayout(None)
        Layout9.setContentsMargins(0, 0, 0, 0)
        Layout9.setSpacing(6)

        self.EstimateButton = qt.QPushButton(self)
        self.EstimateButton.setText("Estimate")
        Layout9.addWidget(self.EstimateButton)
        spacer = qt.QSpacerItem(20,20,
                                qt.QSizePolicy.Expanding,
                                qt.QSizePolicy.Minimum)
        Layout9.addItem(spacer)

        self.StartfitButton = qt.QPushButton(self)
        self.StartfitButton.setText("Start Fit")
        Layout9.addWidget(self.StartfitButton)
        spacer_2 = qt.QSpacerItem(20,20,
                                  qt.QSizePolicy.Expanding,
                                  qt.QSizePolicy.Minimum)
        Layout9.addItem(spacer_2)

        self.DismissButton = qt.QPushButton(self)
        self.DismissButton.setText("Dismiss")
        Layout9.addWidget(self.DismissButton)

        FitActionsGUILayout.addLayout(Layout9,0,0)

if __name__ == "__main__":
    app = qt.QApplication([])
    w = FitActionsGui()
    w.show()
    app.exec()
