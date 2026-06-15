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
import sys
from PyMca5.PyMcaGui import PyMcaQt as qt
# if not, we miss profile fitting ...
from PyMca5.PyMcaGui.pymca.ScanWindow import ScanWindow as Window
DEBUG = 0

class ProfileScanWidget(Window):
    sigAddClicked = qt.pyqtSignal(object)
    sigRemoveClicked = qt.pyqtSignal(object)
    sigReplaceClicked = qt.pyqtSignal(object)
    def __init__(self, parent=None, actions=False, **kw):
        super(ProfileScanWidget, self).__init__(parent, **kw)
        if actions:
            self._buildActionsBox()

    def _buildActionsBox(self):
        widget = self.centralWidget()
        self.labelBox = qt.QWidget(widget)
        self.labelBox.mainLayout = qt.QHBoxLayout(self.labelBox)

        self.labelLabel = qt.QLabel(self.labelBox)

        self.labelLabel.setText("Selection Label = ")
        self.label = qt.QLineEdit(self.labelBox)
        self.labelBox.mainLayout.addWidget(self.labelLabel)
        self.labelBox.mainLayout.addWidget(self.label)

        self.buttonBox = self.labelBox
        buttonBox = self.buttonBox
        self.buttonBoxLayout = self.labelBox.mainLayout
        self.buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonBoxLayout.setSpacing(0)
        self.addButton = qt.QPushButton(buttonBox)
        self.addButton.setText("ADD")
        self.addButton.setToolTip("Add curves to destination widget")
        self.removeButton = qt.QPushButton(buttonBox)
        self.removeButton.setText("REMOVE")
        self.removeButton.setToolTip("Remove curves from destination widget")
        self.buttonBoxLayout.addWidget(self.addButton)
        self.buttonBoxLayout.addWidget(self.removeButton)
        self.replaceButton = qt.QPushButton(buttonBox)
        self.replaceButton.setText("REPLACE")
        self.replaceButton.setToolTip("Replace curves in destination widget")
        self.buttonBoxLayout.addWidget(self.replaceButton)

        #self.mainLayout.addWidget(buttonBox)
        widget.layout().addWidget(buttonBox)
        self.addButton.clicked.connect(self._addClicked)
        self.removeButton.clicked.connect(self._removeClicked)
        self.replaceButton.clicked.connect(self._replaceClicked)

    def _addClicked(self):
        if DEBUG:
            print("ADD clicked")
        self._emitActionSignal(action='ADD')

    def _removeClicked(self):
        if DEBUG:
            print("REMOVE clicked")
        self._emitActionSignal(action='REMOVE')

    def _replaceClicked(self):
        if DEBUG:
            print("REPLACE clicked")
        self._emitActionSignal(action='REPLACE')

    def _emitActionSignal(self, action='ADD'):
        if action not in ['ADD', 'REMOVE', 'REPLACE']:
            print("Unrecognized action %s" % action)

        curveList = self.getAllCurves()
        if curveList in [None, []]:
            return
        text = self.label.text()

        ddict = {}
        ddict['event']   = action
        ddict['action']  = action
        ddict['label']   = text
        ddict['curves']  = curveList
        if action == 'ADD':
            self.sigAddClicked.emit(ddict)
        elif action == 'REMOVE':
            self.sigRemoveClicked.emit(ddict)
        else:
            self.sigReplaceClicked.emit(ddict)

def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    def testSlot(ddict):
        print(ddict)
    w = ProfileScanWidget(actions=True)
    w.addCurve([1, 2, 3, 4], [1, 4, 9, 16], legend='Dummy')
    w.sigAddClicked.connect(testSlot)
    w.sigRemoveClicked.connect(testSlot)
    w.sigReplaceClicked.connect(testSlot)
    w.show()
    app.exec()

if __name__ == "__main__":
    DEBUG = 1
    test()
