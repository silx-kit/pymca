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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.pymca import ScanWindow
from PyMca5.PyMcaMath import SGModule


class SGParametersWidget(qt.QWidget):
    sigSGParametersSignal = qt.pyqtSignal(object)
    def __init__(self, parent = None, length=2000):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)

        i = 0
        self._keyList = ['points', 'degree', 'order']
        self.parametersDict = {'points':3,
                               'degree':1,
                               'order':0}
        for text in ["Savitzky-Golay filter width:",
                     "Interpolating polynomial degree:",
                     "Derivative order (0=smoothing):"]:
            label = qt.QLabel(self)
            label.setText(text)
            self.mainLayout.addWidget(label, i, 0)
            #self.mainLayout.addWidget(qt.HorizontalSpacer(self), i, 1)
            i +=1

        i = 0
        self.widgetDict = {}
        for key in self._keyList:
            self.widgetDict[key] = qt.QSpinBox(self)
            self.widgetDict[key].setMinimum(1)
            self.widgetDict[key].setMaximum(100)
            self.widgetDict[key].setValue(self.parametersDict[key])
            self.widgetDict[key].valueChanged[int].connect( \
                     self._updateParameters)
            self.mainLayout.addWidget(self.widgetDict[key], i, 1)
            i += 1
        self.widgetDict['order'].setMinimum(0)
        self.widgetDict['order'].setValue(0)
        self.widgetDict['order'].setMaximum(4)

    def setParameters(self, ddict):
        for key in ddict:
            if key in self._keyList:
                self.widgetDict[key].setValue(ddict[key])
        dummy = 0
        self._updateParameters(dummy)

    def _updateParameters(self, val):
        for key in self._keyList:
            self.parametersDict[key] = self.widgetDict[key].value()
        self.widgetDict['order'].setMaximum(self.parametersDict['degree'])
        if self.parametersDict['order'] > self.parametersDict['degree']:
            self.parametersDict['order']=self.parametersDict['degree']
            self.widgetDict['order'].setValue(self.parametersDict['order'])
        ddict = {}
        ddict['event']='SGParametersChanged'
        ddict.update(self.parametersDict)
        self.sigSGParametersSignal.emit(ddict)

    def getParameters(self):
        return self.parametersDict

class SGWindow(qt.QWidget):
    def __init__(self, parent, data, image=None, x=None):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("Savitzky-Golay Filter Configuration Window")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        spectrum = data
        if x is None:
            self.xValues = range(len(spectrum))
        else:
            self.xValues = x
        self.image = None
        self.spectrum = spectrum
        self.parametersWidget = SGParametersWidget(self, length=len(spectrum))
        self.graph = ScanWindow.ScanWindow(self)
        self.graph.addCurve(self.xValues,
                            spectrum, "Spectrum",
                            replace=True)
        self.mainLayout.addWidget(self.parametersWidget)
        self.mainLayout.addWidget(self.graph)
        self.getParameters = self.parametersWidget.getParameters
        self.setParameters = self.parametersWidget.setParameters
        self.parametersWidget.sigSGParametersSignal.connect(self.updateGraph)
        self.updateGraph(self.getParameters())

    def updateGraph(self, ddict):
        points = ddict['points']
        degree = ddict['degree']
        order  = ddict['order']
        self.background = SGModule.getSavitzkyGolay(self.spectrum,
                                                    points,
                                                    degree=degree,
                                                    order=order)

        # if the x are decreasing the result is not correct
        if order % 2:
            if self.xValues is not None:
                if self.xValues[0] > self.xValues[-1]:
                    self.background *= -1

        if order > 0:
            maptoy2 = "right"
        else:
            maptoy2 = "left"
        self.graph.addCurve(self.xValues,
                    self.background, "Filtered Spectrum",
                    replace=False,
                    yaxis=maptoy2)

        #Force information update
        legend = self.graph.getActiveCurve(just_legend=True)
        if legend.startswith('Filtered'):
            self.graph.setActiveCurve(legend)

class SGDialog(qt.QDialog):
    def __init__(self, parent, data, x=None):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("Savitzky-Golay Configuration Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(2)
        self.__image = False
        if len(data.shape) == 2:
            spectrum = data.ravel()
        else:
            spectrum = data
        self.parametersWidget = SGWindow(self, spectrum, image=False, x=x)
        self.graph = self.parametersWidget.graph
        self.mainLayout.addWidget(self.parametersWidget)
        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        hboxLayout.setSpacing(0)
        self.okButton = qt.QPushButton(hbox)
        self.okButton.setText("OK")
        self.okButton.setAutoDefault(False)
        self.dismissButton = qt.QPushButton(hbox)
        self.dismissButton.setText("Cancel")
        self.dismissButton.setAutoDefault(False)
        hboxLayout.addWidget(self.okButton)
        hboxLayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxLayout.addWidget(self.dismissButton)
        self.mainLayout.addWidget(hbox)
        self.dismissButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)

    def getParameters(self):
        parametersDict = self.parametersWidget.getParameters()
        parametersDict['function'] = SGModule.replaceStackWithSavitzkyGolay
        parametersDict['arguments'] = [parametersDict['points'],
                                       parametersDict['degree'],
                                       parametersDict['order']]
        return parametersDict

    def setParameters(self, ddict):
        return self.parametersWidget.setParameters(ddict)


if __name__ == "__main__":
    import numpy
    app = qt.QApplication([])
    noise = numpy.random.randn(1000)
    y=numpy.arange(1000.)
    w = SGDialog(None, y+numpy.sqrt(y)* noise)
    w.show()
    ret = w.exec()
    if ret:
        print(w.getParameters())
