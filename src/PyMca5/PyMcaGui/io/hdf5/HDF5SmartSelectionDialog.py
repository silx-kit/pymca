#/*##########################################################################
# Copyright (C) 2026 European Synchrotron Radiation Facility
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
"""Selection of HDF5 entries (scans) by the numbers in their names or by the index.
"""

__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaIO import HDF5Utils

SYNTAX_HELP = [("1,3,7", "individual scans"),
               ("10-20", "range of scans (limits included)"),
               ("10-40:5", "every 5th scan between 10 and 40"),
               ("3::5", "every 5th scan from scan 3 on"),
               ("empty", "all the scans")]


def parseNumberSpec(text, available):
    """Return the numbers of `available` matching the specification `text`.

    :param text: Specification as described in :attr:`SYNTAX_HELP`
    :param available: Sorted list of the numbers actually present
    :return: The subset of `available` matching the specification
    :raise ValueError: In case of invalid specification
    """
    text = text.replace(" ", "")
    if not len(text) or not len(available):
        return list(available)
    selected = set()
    for token in text.split(","):
        if not len(token):
            continue
        # "3::5" is a range without upper limit
        rangeText, _, stepText = token.replace("::", "-:", 1).partition(":")
        startText, dash, stopText = rangeText.partition("-")
        if not len(dash):
            # a single number
            stopText = startText
        try:
            # missing limits are the first and the last available numbers
            start = int(startText or available[0])
            stop = int(stopText or available[-1])
            step = int(stepText or 1)
            selected.update(range(min(start, stop), max(start, stop) + 1, step))
        except ValueError:
            raise ValueError("Invalid specification '%s'" % token)
    return sorted(selected.intersection(available))


def parseEntryNames(names):
    """Return the numbers by which the entries can be selected.

    Split names to text and numbers.
    Check if first or last text is the same for all names.
    If yes, return the numbers.
    If no, return empty tuples.

    :param names: List of entry names
    :return: List of tuples of numbers, all of the same length, which is
             zero if no scan number is found
    """
    texts = []
    numbers = []
    count = None
    for name in names:
        # text and numbers splitting
        # starts and ends by text
        key = HDF5Utils._natural_sort_key(name)
        texts.append(key[0::2])
        numbers.append(key[1::2])
        # use the smallest set of numbers
        if count is None or len(numbers[-1]) < count:
            count = len(numbers[-1])
    starts = set()
    ends = set()
    for i in range(len(names)):
        starts.add(texts[i][0])
        ends.add(texts[i][-1])
    if not count or (len(starts) > 1 and len(ends) > 1):
        # no scan number found
        return [()] * len(names)
    parsed = []
    for i in range(len(names)):
        # e.g. 1_sample5A, 2_sampleB
        if len(starts) == 1:
            parsed.append(numbers[i][:count])
        # e.g. sample5A_1, sampleB_2
        else:
            parsed.append(numbers[i][-count:])
    return parsed


def matchEntries(names, specs, positions=False):
    """Return the entry names matching the specifications.

    :param names: List of entry names, in the order of the tree
    :param specs: Specifications of the numbers
    :param positions: If True, the first specification applies to the
                      position in the tree (start from 1), the others are ignored
    :return: The subset of `names` matching the specifications
    :raise ValueError: In case of invalid specification or of no match
    """
    if positions:
        specs = specs[:1]
        numbers = []
        for i in range(len(names)):
            numbers.append((i + 1,))
    else:
        numbers = parseEntryNames(names)
    requested = []
    for i in range(len(specs)):
        available = set()
        for values in numbers:
            available.add(values[i])
        requested.append(set(parseNumberSpec(specs[i], sorted(available))))
    selected = []
    for i in range(len(names)):
        matching = True
        for j in range(len(specs)):
            if numbers[i][j] not in requested[j]:
                matching = False
        if matching:
            selected.append(names[i])
    if not len(selected):
        raise ValueError("No scan matching the request")
    return selected


class HDF5SmartSelectionDialog(qt.QDialog):
    """Ask for the scans to be selected in the HDF5 tree.

    `selected` contains the matching entry names.
    """
    def __init__(self, parent=None, filename="", entryNames=()):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("Numeric selection of scans")
        self.selected = []
        self._entryNames = entryNames

        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setSpacing(2)

        label = qt.QLabel(self)
        label.setText("File: %s" % filename)
        self.mainLayout.addWidget(label, 0, 0, 1, 2)

        # a line per number in the names, the first one also takes the
        # position in the tree
        count = 0
        numbers = parseEntryNames(entryNames)
        if len(numbers):
            count = len(numbers[0])
        self.numberLabels = []
        self.numberLines = []
        for i in range(max(count, 1)):
            label = qt.QLabel(self)
            label.setText("%d%s number:" %
                          (i + 1, {1: "st", 2: "nd", 3: "rd"}.get(i + 1, "th")))
            line = qt.QLineEdit(self)
            line.setPlaceholderText("all")
            self.mainLayout.addWidget(label, i + 1, 0)
            self.mainLayout.addWidget(line, i + 1, 1)
            self.numberLabels.append(label)
            self.numberLines.append(line)
        row = len(self.numberLines) + 1

        self.positionBox = qt.QCheckBox(self)
        self.positionBox.setText("Use the position in the tree (1 to %d)" %
                                 len(entryNames))
        self.positionBox.toggled.connect(self._positionBoxToggled)
        if not count:
            self.positionBox.setChecked(True)
            self.positionBox.setEnabled(False)
            self.positionBox.setToolTip("No scan number found in the names")
        self.mainLayout.addWidget(self.positionBox, row, 0, 1, 2)

        helpBox = qt.QGroupBox(self)
        helpBox.setTitle("Accepted syntax")
        helpBoxLayout = qt.QGridLayout(helpBox)
        for i in range(len(SYNTAX_HELP)):
            for j in range(2):
                label = qt.QLabel(helpBox)
                label.setText(SYNTAX_HELP[i][j])
                helpBoxLayout.addWidget(label, i, j)
        self.mainLayout.addWidget(helpBox, row + 1, 0, 1, 2)

        self.selectButton = qt.QPushButton(self)
        self.selectButton.setText("Select")
        self.cancelButton = qt.QPushButton(self)
        self.cancelButton.setText("Cancel")
        buttonLayout = qt.QHBoxLayout()
        buttonLayout.addWidget(self.selectButton)
        buttonLayout.addWidget(self.cancelButton)
        self.mainLayout.addLayout(buttonLayout, row + 2, 0, 1, 2)

        self.selectButton.clicked.connect(self._selectClicked)
        self.cancelButton.clicked.connect(self.reject)

    def _positionBoxToggled(self, checked):
        # the position goes in the first line, the other lines are unused
        if checked:
            self.numberLabels[0].setText("Position:")
        else:
            self.numberLabels[0].setText("1st number:")
        for i in range(1, len(self.numberLines)):
            self.numberLabels[i].setEnabled(not checked)
            self.numberLines[i].setEnabled(not checked)

    def _selectClicked(self):
        specs = []
        for line in self.numberLines:
            specs.append(line.text())
        # the dialog stays open until the request is valid
        try:
            self.selected = matchEntries(self._entryNames, specs,
                                         self.positionBox.isChecked())
        except ValueError as error:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText(str(error))
            msg.exec()
            return
        self.accept()


if __name__ == "__main__":
    app = qt.QApplication([])
    entryNames = ["1.1", "1.2", "2.1", "2.2", "3.1", "4.1", "4.2", "5.1"]
    dialog = HDF5SmartSelectionDialog(filename="dummy.h5",
                                      entryNames=entryNames)
    if dialog.exec():
        print("selected = %s" % dialog.selected)
