#/*##########################################################################
# Copyright (C) 2018-2023 European Synchrotron Radiation Facility
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
import sys
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt

_logger = logging.getLogger(__name__)


class QNexusWidgetActions(qt.QWidget):
    sigAddSelection = qt.pyqtSignal()
    sigRemoveSelection = qt.pyqtSignal()
    sigReplaceSelection = qt.pyqtSignal()
    sigActionsConfigurationChanged = qt.pyqtSignal(object)
    def __init__(self, parent=None, autoreplace=False):
        self.autoReplace = autoreplace
        if self.autoReplace:
            self.autoAdd     = False
        else:
            self.autoAdd     = True
        self._oldCntSelection = None
        self.autoRefreshBox = None
        qt.QWidget.__init__(self, parent)
        self._build()

    def _build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        autoBox = qt.QWidget(self)
        self.autoBoxLayout = qt.QGridLayout(autoBox)
        self.autoBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.autoBoxLayout.setSpacing(0)
        self.autoOffBox = qt.QCheckBox(autoBox)
        self.autoOffBox.setText("Auto OFF")
        self.autoAddBox = qt.QCheckBox(autoBox)
        self.autoAddBox.setText("Auto ADD")
        self.autoReplaceBox = qt.QCheckBox(autoBox)
        self.autoReplaceBox.setText("Auto REPLACE")

        row = 0
        self.autoBoxLayout.addWidget(self.autoOffBox, row, 0)
        self.autoBoxLayout.addWidget(self.autoAddBox, row, 1)
        self.autoBoxLayout.addWidget(self.autoReplaceBox, row, 2)

        if self.autoReplace:
            self.autoAddBox.setChecked(False)
            self.autoReplaceBox.setChecked(True)
        else:
            self.autoAddBox.setChecked(True)
            self.autoReplaceBox.setChecked(False)
        row += 1

        self.object3DBox = qt.QCheckBox(autoBox)
        self.object3DBox.setText("3D On")
        self.object3DBox.setToolTip("Use OpenGL and Enable 3-Axes selections")
        self.autoBoxLayout.addWidget(self.object3DBox, row, 0)

        self.meshBox = qt.QCheckBox(autoBox)
        self.meshBox.setText("2D On")
        self.meshBox.setToolTip("Enable 2-Axes selections (mesh and scatter)")
        self.autoBoxLayout.addWidget(self.meshBox, row, 1)


        self.forceMcaBox = qt.QCheckBox(autoBox)
        self.forceMcaBox.setText("Force MCA")
        self.forceMcaBox.setToolTip("Interpret selections as MCA")
        self.autoBoxLayout.addWidget(self.forceMcaBox, row, 2)

        self.mainLayout.addWidget(autoBox)

        self.buttonBox = qt.QWidget(self)
        buttonBox = self.buttonBox
        self.buttonBoxLayout = qt.QHBoxLayout(buttonBox)

        self.addButton = qt.QPushButton(buttonBox)
        self.addButton.setText("ADD")
        self.removeButton = qt.QPushButton(buttonBox)
        self.removeButton.setText("REMOVE")
        self.replaceButton = qt.QPushButton(buttonBox)
        self.replaceButton.setText("REPLACE")

        self.buttonBoxLayout.addWidget(self.addButton)
        self.buttonBoxLayout.addWidget(self.removeButton)
        self.buttonBoxLayout.addWidget(self.replaceButton)

        self.mainLayout.addWidget(buttonBox)

        # --- signal handling
        self.object3DBox.clicked.connect(self._setObject3DBox)
        self.meshBox.clicked.connect(self._setMeshBox)
        self.autoOffBox.clicked.connect(self._setAutoOff)
        self.autoAddBox.clicked.connect(self._setAutoAdd)
        self.autoReplaceBox.clicked.connect(self._setAutoReplace)
        self.forceMcaBox.clicked.connect(self._setForcedMca)
        self.addButton.clicked.connect(self._addClickedSlot)
        self.removeButton.clicked.connect(self._removeClicked)
        self.replaceButton.clicked.connect(self._replaceClicked)

    def _setObject3DBox(self):
        if self.object3DBox.isChecked():
            self.meshBox.setChecked(False)
            self.autoOffBox.setChecked(True)
            self.autoReplaceBox.setChecked(False)
            self.autoAddBox.setChecked(False)
        self.configurationChanged()

    def _setMeshBox(self):
        if self.meshBox.isChecked():
            self.autoAddBox.setChecked(False)
            self.autoReplaceBox.setChecked(False)
            self.autoOffBox.setChecked(True)
            self.object3DBox.setChecked(False)
        self.configurationChanged()

    def _setAutoOff(self):
        self.autoAddBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoOffBox.setChecked(True)
        self.object3DBox.setChecked(False)
        self.meshBox.setChecked(False)
        self.configurationChanged()

    def _setAutoAdd(self):
        self.object3DBox.setChecked(False)
        self.meshBox.setChecked(False)
        self.autoOffBox.setChecked(False)
        self.autoReplaceBox.setChecked(False)
        self.autoAddBox.setChecked(True)
        self.configurationChanged()

    def _setAutoReplace(self):
        self.object3DBox.setChecked(False)
        self.meshBox.setChecked(False)
        self.autoOffBox.setChecked(False)
        self.autoAddBox.setChecked(False)
        self.autoReplaceBox.setChecked(True)
        self.configurationChanged()

    def addAutoRefreshCheckBox(self, checkbox):
        self.autoRefreshBox = checkbox
        self.autoBoxLayout.addWidget(checkbox)
        checkbox.toggled.connect(self._autoRefreshBoxToggled)
        self.autoReplaceBox.toggled.connect(self._autoReplaceToggledForRefresh)

    def _autoRefreshBoxToggled(self, checked):
        if checked and not self.autoReplaceBox.isChecked():
            self._setAutoReplace()

    def _autoReplaceToggledForRefresh(self, checked):
        if (not checked) and self.autoRefreshBox is not None \
                and self.autoRefreshBox.isChecked():
            self.autoRefreshBox.setChecked(False)

    def _setForcedMca(self):
        if self.forceMcaBox.isChecked():
            self.object3DBox.setChecked(False)
            self.object3DBox.setEnabled(False)
            self.meshBox.setChecked(False)
            self.meshBox.setEnabled(False)
        else:
            self.object3DBox.setEnabled(True)
            self.meshBox.setEnabled(True)
        self.configurationChanged()

    def _addClickedSlot(self):
        self._addClicked()

    def _addClicked(self):
        _logger.debug("_addClicked()")
        self.sigAddSelection.emit()

    def _removeClicked(self):
        _logger.debug("_removeClicked()")
        self.sigRemoveSelection.emit()

    def _replaceClicked(self):
        _logger.debug("_replaceClicked()")
        self.sigReplaceSelection.emit()

    def configurationChanged(self):
        _logger.debug("configurationChanged(object)")
        ddict = self.getConfiguration()
        self.sigActionsConfigurationChanged.emit(ddict)

    def set3DEnabled(self, flag):
        if flag:
            self.object3DBox.setEnabled(True)
        else:
            wasChecked = self.object3DBox.isChecked()
            self.object3DBox.setChecked(False)
            self.object3DBox.setEnabled(False)
            if wasChecked:
                self.configurationChanged()

    def getConfiguration(self):
        ddict = {}
        ddict["mca"]= self.forceMcaBox.isChecked()
        if self.autoReplaceBox.isChecked():
            ddict['auto'] = "REPLACE"
        elif self.autoAddBox.isChecked():
            ddict['auto'] = "ADD"
        else:
            ddict['auto'] = "OFF"
        ddict["2d"]= self.meshBox.isChecked()
        ddict["3d"]= self.object3DBox.isChecked()
        ddict["mca"]= self.forceMcaBox.isChecked()
        return ddict

    def setConfiguration(self, ddict):
        mca = ddict.get("mca", False)
        if mca in ["False", "0", 0, "", "false"]:
            mca = False
        else:
            mca = True
        auto = ddict.get("auto", "ADD")
        twod = ddict.get("2d", "False")
        if twod in ["False", "0", 0, "", "false"]:
            twod = False
        else:
            twod = True
        threed = ddict.get("3d", "False")
        if threed in ["False", "0", 0, "", "false"]:
            threed = False
        else:
            threed = True
        self.forceMcaBox.setChecked(mca)
        if auto == "ADD":
            self._setAutoAdd()
        elif auto == "OFF":
            # this is compatible with 2d or 3d selections
            self._setAutoOff()
            self.set3DEnabled(threed)
            self.meshBox.setChecked(twod)
        elif auto == "REPLACE":
            self._setAutoReplace()

if __name__ == "__main__":
    app = qt.QApplication([])
    w = QNexusWidgetActions()
    w.show()
    def addSelection():
        print("addSelectionCalled")
    def removeSelection():
        print("removeSelectionCalled")
    def replaceSelection():
        print("replaceSelectionCalled")
    def configurationChanged(ddict):
        print("configurationChanged ", ddict)
    w.show()
    w.sigAddSelection.connect(addSelection)
    w.sigRemoveSelection.connect(removeSelection)
    w.sigReplaceSelection.connect(replaceSelection)
    w.sigActionsConfigurationChanged.connect(configurationChanged)
    sys.exit(app.exec())

