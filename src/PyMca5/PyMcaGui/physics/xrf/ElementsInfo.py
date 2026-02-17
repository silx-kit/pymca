#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2026 European Synchrotron Radiation Facility
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
import sys
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaPhysics.xrf import ElementHtml
from PyMca5.PyMcaPhysics.xrf import Elements
from PyMca5.PyMcaGui.physics.xrf.QPeriodicTable import QPeriodicTable

_logger = logging.getLogger(__name__)

CLOSE_ICON =[
"16 16 18 1",
". c None",
"d c #000000",
"c c #080808",
"k c #080c08",
"b c #181818",
"a c #212021",
"# c #212421",
"j c #292829",
"e c #313031",
"f c #393839",
"i c #424542",
"m c #525152",
"h c #525552",
"g c #5a595a",
"l c #636163",
"p c #6b696b",
"n c #7b797b",
"o c #ffffff",
"................",
"................",
"......#abcd.....",
"....efghijkdd...",
"...elmgnliaddd..",
"...fmoopnhoodd..",
"..#ggooogoooddd.",
"..ahnpooooocddd.",
"..bilngoooadddd.",
"..cjihooooodddd.",
"..dkaoooaoooddd.",
"...ddoocddoodd..",
"...ddddddddddd..",
"....ddddddddd...",
"......ddddd.....",
"................"
]


class ElementsInfo(qt.QWidget):
    def __init__(self, parent=None, name="Elements Info"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)

        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.energyValue = None
        self.splitter = qt.QSplitter(self)
        layout.addWidget(self.splitter)
        self.splitter.setOrientation(qt.Qt.Horizontal)
        self.table = QPeriodicTable(self.splitter)
        self.html  = ElementHtml.ElementHtml()
        self.infoWidget = None
        self.table.setMinimumSize(500,
                                  400)

        self.table.sigElementClicked.connect(self.elementClicked)

        self.lastElement = None
        #Elements.registerUpdate(self._updateCallback)

    def elementClicked(self, symbol):
        if self.infoWidget is None:
            self.__createInfoWidget(symbol)
        else:
            self.infoText.clear()
            self.infoText.insertHtml(self.html.gethtml(symbol))
        if self.infoWidget.isHidden():
            self.infoWidget.show()
        self.lastElement = symbol
        self.infoWidget.setWindowTitle(symbol)
        self.infoWidget.raise_()

    def __createInfoWidget(self,symbol=""):
        #Dock window like widget
        frame = qt.QWidget(self.splitter)
        layout = qt.QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        #The dock functionnality
        toolbar = qt.QWidget(frame)
        layout.addWidget(toolbar)
        layout1       = qt.QHBoxLayout(toolbar)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(0)

        # --- the line
        self.line1 = Line(toolbar)
        self.line1.setFrameShape(qt.QFrame.HLine)
        self.line1.setFrameShadow(qt.QFrame.Sunken)
        self.line1.setFrameShape(qt.QFrame.HLine)
        layout1.addWidget(self.line1)

        # --- the close button
        self.closelabel = PixmapLabel(toolbar)
        self.closelabel.setPixmap(qt.QPixmap(CLOSE_ICON))
        layout1.addWidget(self.closelabel)
        self.closelabel.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))

        # --- connections
        self.line1.sigLineDoubleClickEvent.connect(self.infoReparent)
        self.closelabel.sigPixmapLabelMousePressEvent.connect(self.infoToggle)

        # --- The text edit widget
        w= qt.QWidget(frame)
        layout.addWidget(w)
        l=qt.QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        hbox = qt.QWidget(w)
        hbox.layout = qt.QHBoxLayout(hbox)
        hbox.layout.setContentsMargins(0, 0, 0, 0)
        hbox.layout.setSpacing(0)
        l.addWidget(hbox)
        hbox.layout.addWidget(qt.HorizontalSpacer(hbox))
        l1=qt.QLabel(hbox)
        l1.setText('<b><nobr>Excitation Energy (keV)</nobr></b>')
        self.energy=MyQLineEdit(hbox)
        self.energy.setFixedWidth(self.energy.fontMetrics().maxWidth()*len('#####.###'))
        self.energy.setText("")
        hbox.layout.addWidget(l1)
        hbox.layout.addWidget(self.energy)
        hbox.layout.addWidget(qt.HorizontalSpacer(hbox))
        self.energy.editingFinished[()].connect(self._energySlot)

        #if both signals are emitted and there is an error then we are in an
        #endless loop
        #self.connect(self.energy, qt.SIGNAL('focusOut'), self._energySlot)

        self.infoText = qt.QTextEdit(w)
        self.infoText.setReadOnly(1)
        self.infoText.clear()
        self.infoText.insertHtml(self.html.gethtml(symbol))
        l.addWidget(self.infoText)
        w.show()
        self.infoWidget=frame
        frame.show()

    def infoReparent(self):
        if self.infoWidget.parent() is not None:
            self.infoWidget.setParent(None)
            self.infoWidget.move(self.cursor().pos())
            self.infoWidget.show()
            #,self.cursor().pos(),1)
        else:
            self.infoWidget.setParent(self.splitter)
            self.splitter.insertWidget(1,self.infoWidget)
            #,qt.QPoint(),1)
            #self.splitter.moveToFirst(self.sourceFrame)
        self.infoWidget.setFocus()

    def infoToggle(self,**kw):
        _logger.debug("toggleSource called")
        if self.infoWidget.isHidden():
            self.infoWidget.show()
            self.infoWidget.raise_()
        else:
            self.infoWidget.hide()

    def _energySlot(self):
        string = str(self.energy.text())
        if len(string):
            try:
                value = float(string)
            except Exception:
                msg=qt.QMessageBox(self.energy)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Float")
                msg.exec()
                self.energy.setFocus()
                return
            if self.energyValue is not None:
                if value != self.energyValue:
                    self.energyValue = value
                    Elements.updateDict(energy=value)
            else:
                self.energyValue = value
                Elements.updateDict(energy=value)
            self._updateCallback()
            self.energy.setPaletteBackgroundColor(qt.QColor('white'))
            self.infoWidget.setFocus()
        else:
            self.energyValue = None
            self.energy.setText("")


    def _updateCallback(self):
        _logger.debug("_updateCallback called")
        if self.lastElement is not None:
            self.elementClicked(self.lastElement)
            if Elements.Element[self.lastElement]['buildparameters']['energy'] is not None:
                self.energy.setText("%.3f" % Elements.Element[self.lastElement]['buildparameters']['energy'])
            else:
                self.energy.setText("")

class Line(qt.QFrame):
    sigLineDoubleClickEvent = qt.pyqtSignal(object)
    def mouseDoubleClickEvent(self,event):
        _logger.debug("Double Click Event")
        ddict={}
        ddict['event']="DoubleClick"
        ddict['data'] = event
        self.sigLineDoubleClickEvent.emit(ddict)

class PixmapLabel(qt.QLabel):
    sigPixmapLabelMousePressEvent = qt.pyqtSignal(object)
    def mousePressEvent(self,event):
        _logger.debug("Mouse Press Event")
        ddict={}
        ddict['event']="MousePress"
        ddict['data'] = event
        self.sigPixmapLabelMousePressEvent.emit(ddict)


class MyQLineEdit(qt.QLineEdit):
    sigFocusOut = qt.pyqtSignal()
    def __init__(self,parent=None,name=None):
        qt.QLineEdit.__init__(self,parent)

    def setPaletteBackgroundColor(self, color):
        palette = self.palette()
        role = self.backgroundRole()
        palette.setColor(role,color)
        self.setPalette(palette)

    def focusInEvent(self,event):
        self.setPaletteBackgroundColor(qt.QColor('yellow'))


    def focusOutEvent(self,event):
        self.setPaletteBackgroundColor(qt.QColor('white'))
        self.sigFocusOut.emit()

def main():
    logging.basicConfig(level=logging.INFO)
    app  = qt.QApplication([])
    winpalette = qt.QPalette(qt.QColor(230,240,249),qt.QColor(238,234,238))
    app.setPalette(winpalette)
    w= ElementsInfo()
    w.show()
    app.exec()

if __name__ == "__main__":
    main()
