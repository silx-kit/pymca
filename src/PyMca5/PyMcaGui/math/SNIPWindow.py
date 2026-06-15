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
import sys
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaGui.pymca import ScanWindow
from PyMca5.PyMcaMath import SNIPModule
#TODO: Add this functionality using SilxGLWindow
OBJECT3D = False

class SNIP1DParametersWidget(qt.QWidget):
    sigSNIPParametersSignal = qt.pyqtSignal(object)
    def __init__(self, parent = None, length=2000, smooth=False):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)

        i = 0
        self.parametersDict = {'roi_min':0,
                               'roi_max':length,
                               'width':min(30, length/10),
                               'smoothing':1}
        textLabels = ["SNIP background width (2 to 3 times fwhm) :",
                     "Minimum channel considered:",
                     "Maximum channel considered:",
                     "Preliminar smoothing level:"]
        if smooth:
            textLabels[0] = "SNIP width :"
            self.parametersDict['width'] = 3

        for text in textLabels:
            label = qt.QLabel(self)
            label.setText(text)
            self.mainLayout.addWidget(label, i, 0)
            #self.mainLayout.addWidget(qt.HorizontalSpacer(self), i, 1)
            i +=1

        i = 0
        self.widgetDict = {}
        for key in ['width', 'roi_min', 'roi_max', 'smoothing']:
            self.widgetDict[key] = qt.QSpinBox(self)
            self.widgetDict[key].setMinimum(0)
            self.widgetDict[key].setMaximum(self.parametersDict['roi_max'])
            self.widgetDict[key].setValue(self.parametersDict[key])
            self.widgetDict[key].valueChanged[int].connect(self._updateParameters)
            self.mainLayout.addWidget(self.widgetDict[key], i, 1)
            i += 1
        self.widgetDict['smoothing'].setMaximum(100)

    def _updateParameters(self, val):
        for key in ['width', 'roi_min', 'roi_max', 'smoothing']:
            self.parametersDict[key] = self.widgetDict[key].value()
        ddict = {}
        ddict['event']='SNIPParametersChanged'
        ddict.update(self.parametersDict)
        self.sigSNIPParametersSignal.emit(ddict)

    def getParameters(self):
        return self.parametersDict

    def setParameters(self, ddict=None):
        if ddict is None:
            return
        actualKeys = self.widgetDict.keys()
        for key in ddict.keys():
            if key in actualKeys:
                w = self.widgetDict[key]
                #w.setMaximum(max(ddict[key], w.value()))
                #w.setMinimum(min(ddict[key], w.value()))
                w.setValue(ddict[key])
        self._updateParameters("dummy")

class SNIP2DParametersWidget(qt.QWidget):
    sigSNIPParametersSignal = qt.pyqtSignal(object)
    def __init__(self, parent = None, shape=(4000,4000)):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)

        i = 0
        self.parametersDict = {'roi_min':[0,0],
                               'roi_max':[shape[0], shape[1]],
                               'width':min(30, int(min(shape)/10)),
                               'smoothing':1}
        for text in ["SNIP background width (2 to 3 times fwhm) :",
                     "Minimum ROI channels considered:",
                     "Maximum ROI channels considered:",
                     "Pleliminar smoothing level:"]:
            label = qt.QLabel(self)
            label.setText(text)
            self.mainLayout.addWidget(label, i, 0)
            #self.mainLayout.addWidget(qt.HorizontalSpacer(self), i, 1)
            i +=1

        i = 0
        self.widgetDict = {}
        for key in ['width', 'roi_min', 'roi_max', 'smoothing']:
            if key in ['width', 'smoothing']:
                spinBox = qt.QSpinBox(self)
                spinBox.setMinimum(0)
                spinBox.setMaximum(min(self.parametersDict['roi_max']))
                spinBox.setValue(self.parametersDict[key])
                spinBox.valueChanged[int].connect(self._updateParameters)
                self.mainLayout.addWidget(spinBox, i, 2)
                self.widgetDict[key] = spinBox
            else:
                lineEdit = qt.QLineEdit(self)
                validator = qt.QIntValidator(lineEdit)
                lineEdit.setValidator(validator)
                lineEdit._validator = validator
                lineEdit.setText("%d" % self.parametersDict[key][0])
                lineEdit.editingFinished[()].connect( \
                         self._updateParameters)
                self.mainLayout.addWidget(lineEdit, i, 1)
                self.widgetDict[key] = [lineEdit]
                lineEdit = qt.QLineEdit(self)
                validator = qt.QIntValidator(lineEdit)
                lineEdit.setValidator(validator)
                lineEdit._validator = validator
                lineEdit.setText("%d" % self.parametersDict[key][1])
                lineEdit.editingFinished.connect(self._updateParameters)
                self.mainLayout.addWidget(lineEdit, i, 2)
                self.widgetDict[key].append(lineEdit)
            i += 1
        self.widgetDict['smoothing'].setMaximum(100)

    def _updateParameters(self, val=None):
        for key in ['width', 'smoothing']:
            self.parametersDict[key] = self.widgetDict[key].value()
        for key in ['roi_min', 'roi_max']:
            self.parametersDict[key] = [int(self.widgetDict[key][0].text()),
                                        int(self.widgetDict[key][1].text())]
        ddict = {}
        ddict['event']='SNIPParametersChanged'
        ddict.update(self.parametersDict)
        self.sigSNIPParametersSignal.emit(ddict)

    def getParameters(self):
        return self.parametersDict

    def setParameters(self):
        raise NotImplemented("Set parameters not implemented for SNIP 2D")

class SNIPWindow(qt.QWidget):
    def __init__(self, parent, data, image=None, x=None, smooth=False):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle("SNIP Configuration Window")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        if image is None:
            image = False
            if data.shape == 2:
                if 1 not in data.shape:
                    image = True
                else:
                    spectrum = data.ravel()
            else:
                spectrum = data
        elif not image:
            spectrum = data
        self.__smooth = smooth
        self.__image = image
        if self.__image:
            self.spectrum = None
        else:
            if x is None:
                self.xValues = range(len(spectrum))
            else:
                self.xValues = x
        if self.__image:
            self.image = data
            self.graphWidget = MaskImageWidget.MaskImageWidget(self,
                                                            colormap=True,
                                                            selection=False,
                                                            imageicons=False,
                                                            standalonesave=True)
            self.parametersWidget = SNIP2DParametersWidget(self, shape=self.image.shape)
            self.graph = self.graphWidget.graphWidget.graph
            self.graphWidget.setImageData(data)
            self.mainLayout.addWidget(self.parametersWidget)
            self.mainLayout.addWidget(self.graphWidget)
            self.o3dScene = None
        else:
            self.image = None
            self.spectrum = spectrum
            self.parametersWidget = SNIP1DParametersWidget(self,
                                                           length=len(spectrum),
                                                           smooth=smooth)
            self.graph = ScanWindow.ScanWindow(self)
            self.graph.newCurve(self.xValues,
                            spectrum, "Spectrum", replace=True)
            self.mainLayout.addWidget(self.parametersWidget)
            self.mainLayout.addWidget(self.graph)
        self.xMarkers = []
        self.yMarkers = []
        self.getParameters = self.parametersWidget.getParameters
        self.setParameters = self.parametersWidget.setParameters
        self.parametersWidget.sigSNIPParametersSignal.connect( \
                     self.updateGraph)
        self.updateGraph(self.getParameters())

    def updateGraph(self, ddict):
        width = ddict['width']
        roi_min = ddict['roi_min']
        roi_max = ddict['roi_max']
        smoothing = ddict['smoothing']
        if self.__image:
            if self.xMarkers == []:
                xMin, xMax = self.graph.getGraphXLimits()
                yMin, yMax = self.graph.getGraphYLimits()
                xMean = 0.5 * (xMin + xMax)
                yMean = 0.5 * (yMin + yMax)
                self.xMarkers.append(self.graph.insertXMarker(roi_min[1],
                                                              legend='C Min',
                                                              text='C Min'))
                self.xMarkers.append(self.graph.insertXMarker(roi_max[1],
                                                            legend='C Max',
                                                            text='C Max'))
                self.yMarkers.append(self.graph.insertYMarker(roi_min[0],
                                                            legend='R Min',
                                                            text='R Min'))
                self.yMarkers.append(self.graph.insertYMarker(roi_max[0],
                                                            legend='R Max',
                                                            text='R Max'))
            else:
                self.graph.insertXMarker(roi_min[1],
                                         legend='C Min',
                                         text='C Min')
                self.graph.insertXMarker(roi_max[1],
                                         legend='C Max',
                                         text='C Max')
                self.graph.insertYMarker(roi_min[0],
                                         legend='R Min',
                                         text='R Min')
                self.graph.insertYMarker(roi_max[0],
                                         legend='R Max',
                                         text='R Max')
            self.background = SNIPModule.getImageBackground(self.image, width,
                                                   roi_min=roi_min,
                                                   roi_max=roi_max,
                                                   smoothing=smoothing)
            difference = self.image-self.background
            self.graphWidget.setImageData(difference)
            #if OBJECT3D:
            #    if self.o3dScene is None:
            #        self.o3dScene = Object3DScene.Object3DScene()
            #        self.o3dScene.show()
            #    if 0:
            #        imageData =(self.image * 1).astype(numpy.float32)
            #        backgroundData = (self.background * 1).astype(numpy.float32)
            #        self.o3dScene.mesh(imageData,      z=imageData * 1, legend='Data', update_scene=True)
            #        self.o3dScene.mesh(backgroundData, z=backgroundData , legend='Background', update_scene=True)
            #    else:
            #        self.o3dScene.mesh(difference, z=difference, legend='Data-Background')
            #    self.o3dScene.show()
        else:
            self.background = SNIPModule.getSpectrumBackground(self.spectrum, width,
                                                   roi_min=roi_min,
                                                   roi_max=roi_max,
                                                   smoothing=smoothing)
            if self.__smooth:
                legend0 = "Smoothed Spectrum"
            else:
                legend0 = "Background"
            self.graph.addCurve(self.xValues,
                            self.background, legend0, replace=False)

            #Force information update
            legend = self.graph.getActiveCurve(just_legend=True)
            if legend.startswith(legend0[0:5]):
                self.graph.setActiveCurve(legend)


class SNIPDialog(qt.QDialog):
    def __init__(self, parent, data, x=None, smooth=False):
        qt.QDialog.__init__(self, parent)
        self.setWindowTitle("SNIP Configuration Dialog")
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(2)
        self.__image = False
        self.__smooth = smooth
        if len(data.shape) == 2:
            if 1 not in data.shape:
                image = data
                self.__image = True
            else:
                spectrum = data.ravel()
        else:
            spectrum = data
        if self.__image:
            self.parametersWidget = SNIPWindow(self, image, image=True, x=x)
        else:
            self.parametersWidget = SNIPWindow(self, spectrum, image=False,
                                               x=x, smooth=smooth)
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
        if self.__image:
            parametersDict['function'] = SNIPModule.subtractSnip2DBackgroundFromStack
        elif self.__smooth:
            parametersDict['function'] = SNIPModule.replaceStackWithSnip1DBackground
        else:
            parametersDict['function'] = SNIPModule.subtractSnip1DBackgroundFromStack
        parametersDict['arguments'] = [parametersDict['width'],
                                       parametersDict['roi_min'],
                                       parametersDict['roi_max'],
                                       parametersDict['smoothing']]
        return parametersDict

    def setParameters(self, ddict0):
        if 'arguments' in ddict0:
            ddict = {}
            ddict['width'] = ddict0['arguments'][0]
            ddict['roi_min'] = ddict0['arguments'][1]
            ddict['roi_max'] = ddict0['arguments'][2]
            ddict['smoothing'] = ddict0['arguments'][3]
            self.parametersWidget.setParameters(ddict)
        else:
            self.parametersWidget.setParameters(ddict0)

if __name__ == "__main__":
    import numpy
    app = qt.QApplication([])
    if len(sys.argv) > 1:
        from PyMca5.PyMcaIO import EdfFile
        edf = EdfFile.EdfFile(sys.argv[1])
        data = edf.GetData(0)
        w = SNIPDialog(None, data)
    else:
        x, y = numpy.ogrid[0:200:200j, 0:200:200j]
        data =  50 * numpy.exp(-(x-64)*(x-64)/20.) +\
                50 * numpy.exp(-(y-128)*(y-128)/20.) +\
               100 * numpy.exp(-(1./20) * ((x-64)*(x-64) + (y-128)*(y-128)))
        w = SNIPDialog(None, data)
    w.show()
    ret = w.exec()
    if ret:
        print(w.getParameters())
