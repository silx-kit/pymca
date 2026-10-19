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
"""Selection of HDF5 entries (scans) by number.

Entry names that are not numbers are handled by their position in the tree.
"""

__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import re
from PyMca5.PyMcaGui import PyMcaQt as qt

# an entry name is expected to end by <scan> or by <scan>.<subscan>
_ENTRY_NUMBER = re.compile(r"(?:^|\s)(\d+)(?:\.(\d+))?$")

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
    """Return the (scan, subscan) numbers associated to the entry names.

    The sub-scan number is None if the name does not contain any.

    :param names: List of entry names
    :return: List of (scan, subscan) tuples or None if any name is not
             a number
    """
    parsed = []
    for name in names:
        match = _ENTRY_NUMBER.search(name)
        if match is None:
            return None
        subScan = match.group(2)
        # in case if subscanes are missing
        if subScan is not None:
            subScan = int(subScan)
        parsed.append((int(match.group(1)), subScan))
    return parsed


def matchEntries(names, scanSpec, subScanSpec=""):
    """Return the entry names matching the specifications.

    :param names: List of entry names, in the order of the tree
    :param scanSpec: Specification of the scan numbers
    :param subScanSpec: Specification of the sub-scan numbers. If empty,
                        all the sub-scans of the selected scans are taken.
    :return: The subset of `names` matching the specifications
    :raise ValueError: In case of invalid specification or of no match
    """
    selected = []
    parsed = parseEntryNames(names)
    if parsed is None:
        # the names are not numbers, then use their position
        positions = list(range(1, len(names) + 1))
        for position in parseNumberSpec(scanSpec, positions):
            selected.append(names[position - 1])
    else:
        scans = set()
        subScans = set()
        for scan, subScan in parsed:
            scans.add(scan)
            if subScan is not None:
                subScans.add(subScan)
        requestedScans = set(parseNumberSpec(scanSpec, sorted(scans)))
        requestedSubScans = None
        if len(subScanSpec.strip()):
            requestedSubScans = set(parseNumberSpec(subScanSpec,
                                                    sorted(subScans)))
        for i in range(len(names)):
            scan, subScan = parsed[i]
            if scan not in requestedScans:
                continue
            if requestedSubScans is None or subScan in requestedSubScans:
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
        self.setWindowTitle("Smart selection of scans")
        self.selected = []
        self._entryNames = entryNames

        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setSpacing(2)

        label = qt.QLabel(self)
        label.setText("File: %s" % filename)
        self.mainLayout.addWidget(label, 0, 0, 1, 2)

        label = qt.QLabel(self)
        label.setText("Scan numbers:")
        self.scanLine = qt.QLineEdit(self)
        self.scanLine.setPlaceholderText("all the scans")
        self.mainLayout.addWidget(label, 1, 0)
        self.mainLayout.addWidget(self.scanLine, 1, 1)

        label = qt.QLabel(self)
        label.setText("Sub-scan numbers:")
        self.subScanLine = qt.QLineEdit(self)
        self.subScanLine.setPlaceholderText("all the sub-scans")
        self.mainLayout.addWidget(label, 2, 0)
        self.mainLayout.addWidget(self.subScanLine, 2, 1)

        if parseEntryNames(entryNames) is None:
            label = qt.QLabel(self)
            label.setText("Non standard entry names: the numbers refer to\n"
                          "the position in the tree (from 1 to %d)." %
                          len(entryNames))
            self.mainLayout.addWidget(label, 3, 0, 1, 2)

        helpBox = qt.QGroupBox(self)
        helpBox.setTitle("Accepted syntax")
        helpBoxLayout = qt.QGridLayout(helpBox)
        for i in range(len(SYNTAX_HELP)):
            for j in range(2):
                label = qt.QLabel(helpBox)
                label.setText(SYNTAX_HELP[i][j])
                helpBoxLayout.addWidget(label, i, j)
        self.mainLayout.addWidget(helpBox, 4, 0, 1, 2)

        self.selectButton = qt.QPushButton(self)
        self.selectButton.setText("Select")
        self.cancelButton = qt.QPushButton(self)
        self.cancelButton.setText("Cancel")
        buttonLayout = qt.QHBoxLayout()
        buttonLayout.addWidget(self.selectButton)
        buttonLayout.addWidget(self.cancelButton)
        self.mainLayout.addLayout(buttonLayout, 5, 0, 1, 2)

        self.selectButton.clicked.connect(self._selectClicked)
        self.cancelButton.clicked.connect(self.reject)

    def _selectClicked(self):
        # the dialog stays open until the request is valid
        try:
            self.selected = matchEntries(self._entryNames,
                                         qt.safe_str(self.scanLine.text()),
                                         qt.safe_str(self.subScanLine.text()))
        except ValueError as error:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText("%s" % error)
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
