#/*##########################################################################
# Copyright (C) 2004-2021 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

from PyMca5.PyMcaGui import PyMcaQt as qt
class HDF5Selection(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.selectionWidgetsDict = {}
        row = 0
        for key in ['entry', 'x', 'y', 'm']:
            label = qt.QLabel(self)
            label.setText(key+":")
            line  = qt.QLineEdit(self)
            line.setReadOnly(True)
            self.mainLayout.addWidget(label, row, 0)
            self.mainLayout.addWidget(line,  row, 1)
            self.selectionWidgetsDict[key] = line
            row += 1

    def setSelection(self, selection):
        if 'cntlist' in selection:
            # "Raw" selection
            cntlist = selection['cntlist']
            for key in ['entry', 'x', 'y', 'm']:
                if key not in selection:
                    self.selectionWidgetsDict[key].setText("")
                    continue
                n = len(selection[key])
                if not n:
                    self.selectionWidgetsDict[key].setText("")
                    continue
                idx = selection[key][0]
                text = "%s" % cntlist[idx]
                if n > 1:
                    for idx in range(1, n):
                        text += ", %s" % cntlist[selection[key][idx]]
                self.selectionWidgetsDict[key].setText(text)
        else:
            # "Digested" selection
            for key in ['entry', 'x', 'y', 'm']:
                if key not in selection:
                    self.selectionWidgetsDict[key].setText("")
                    continue
                n = len(selection[key])
                if not n:
                    self.selectionWidgetsDict[key].setText("")
                    continue
                text = "%s" % selection[key][0]
                if n > 1:
                    for idx in range(1, n):
                        text += ", %s" % selection[key][idx]
                self.selectionWidgetsDict[key].setText(text)

    def getSelection(self):
        selection = {}
        for key in ['entry', 'x', 'y', 'm']:
            selection[key] = []
            text = str(self.selectionWidgetsDict[key].text())
            text = text.replace(" ","")
            if len(text):
                selection[key] = text.split(',')
        return selection

def main():
    app = qt.QApplication([])
    tab = HDF5Selection()
    tab.setSelection({'x':[1, 2], 'y':[4], 'cntlist':["dummy", "Cnt0", "Cnt1", "Cnt2", "Cnt3"]})
    tab.show()
    app.exec()

if __name__ == "__main__":
    main()

