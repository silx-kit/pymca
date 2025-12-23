#!/usr/bin/env python
#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2014 European Synchrotron Radiation Facility
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
import os
import numpy
import logging
from matplotlib import cm
from matplotlib import __version__ as matplotlib_version
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.ticker import MaxNLocator, AutoLocator


_logger = logging.getLogger(__name__)

colordict = {}
colordict['blue']   = '#0000ff'
colordict['red']    = '#ff0000'
colordict['green']  = '#00ff00'
colordict['black']  = '#000000'
colordict['white']  = '#ffffff'
colordict['pink']   = '#ff66ff'
colordict['brown']  = '#a52a2a'
colordict['orange'] = '#ff9900'
colordict['violet'] = '#6600ff'
colordict['grey']   = '#808080'
colordict['yellow'] = '#ffff00'
colordict['darkgreen'] = 'g'
colordict['darkbrown'] = '#660000'
colordict['magenta']   = 'm'
colordict['cyan']      = 'c'
colordict['bluegreen'] = '#33ffff'
colorlist  = [colordict['black'],
              colordict['red'],
              colordict['blue'],
              colordict['green'],
              colordict['pink'],
              colordict['brown'],
              colordict['cyan'],
              colordict['orange'],
              colordict['violet'],
              colordict['bluegreen'],
              colordict['grey'],
              colordict['magenta'],
              colordict['darkgreen'],
              colordict['darkbrown'],
              colordict['yellow']]

class PyMcaMatplotlibSave(FigureCanvas):
    def __init__(self, size = (7,3.5),
                 logx = False,
                 logy = False,
                 legends = True,
                 bw = False):

        self.fig = Figure(figsize=size) #in inches
        FigureCanvas.__init__(self, self.fig)

        self._logX = logx
        self._logY = logy
        self._bw   = bw
        self._legend   = legends
        self._legendList = []
        self._dataCounter = 0

        if not legends:
            if self._logY:
                ax = self.fig.add_axes([.15, .15, .75, .8])
            else:
                ax = self.fig.add_axes([.15, .15, .75, .75])
        else:
            if self._logY:
                ax = self.fig.add_axes([.15, .15, .7, .8])
            else:
                ax = self.fig.add_axes([.15, .15, .7, .8])

        ax.set_axisbelow(True)

        self.ax = ax


        if self._logY:
            self._axFunction = ax.semilogy
        else:
            self._axFunction = ax.plot

        if self._bw:
            self.colorList = ['k']   #only black
            self.styleList = ['-', ':', '-.', '--']
            self.nColors   = 1
        else:
            self.colorList = colorlist
            self.styleList = ['-', '-.', ':']
            self.nColors   = len(colorlist)
        self.nStyles   = len(self.styleList)

        self.colorIndex = 0
        self.styleIndex = 0

        self.xmin = None
        self.xmax = None
        self.ymin = None
        self.ymax = None
        self.limitsSet = False

    def setLimits(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.limitsSet = True


    def _filterData(self, x, y):
        index = numpy.flatnonzero((self.xmin <= x) & (x <= self.xmax))
        x = numpy.take(x, index)
        y = numpy.take(y, index)
        index = len(index)
        if index:
            index = numpy.flatnonzero((self.ymin <= y) & (y <= self.ymax))
            index = len(index)
        return index

    def _getColorAndStyle(self):
        color = self.colorList[self.colorIndex]
        style = self.styleList[self.styleIndex]
        self.colorIndex += 1
        if self.colorIndex >= self.nColors:
            self.colorIndex = 0
            self.styleIndex += 1
            if self.styleIndex >= self.nStyles:
                self.styleIndex = 0
        return color, style

    def addDataToPlot(self, x, y, legend = None,
                      color = None,
                      linewidth = None,
                      linestyle = None, **kw):
        n = max(x.shape)
        if self.limitsSet is not None:
            n = self._filterData(x, y)
        if n == 0:
            #nothing to plot
            _logger.debug("nothing to plot")
            return
        style = None
        if color is None:
            color, style = self._getColorAndStyle()
        if linestyle is None:
            if style is None:
                style = '-'
        else:
            style = linestyle

        if linewidth is None:linewidth = 1.0
        self._axFunction( x, y, linestyle = style, color=color, linewidth = linewidth, **kw)
        self._dataCounter += 1
        if legend is None:
            #legend = "%02d" % self._dataCounter    #01, 02, 03, ...
            legend = "%c" % (96+self._dataCounter)  #a, b, c, ..
        self._legendList.append(legend)

    def setXLabel(self, label):
        self.ax.set_xlabel(label)

    def setYLabel(self, label):
        self.ax.set_ylabel(label)

    def setTitle(self, title):
        self.ax.set_title(title)

    def plotLegends(self):
        if not self._legend:return
        if not len(self._legendList):return
        loc = (1.01, 0.0)
        labelsep = 0.015
        drawframe = True
        fontproperties = FontProperties(size=10)
        if len(self._legendList) > 14:
            drawframe = False
            if matplotlib_version < '0.99.0':
                fontproperties = FontProperties(size=8)
                loc = (1.05, -0.2)
            else:
                if len(self._legendList) < 18:
                    #drawframe = True
                    loc = (1.01,  0.0)
                elif len(self._legendList) < 25:
                    loc = (1.05,  0.0)
                    fontproperties = FontProperties(size=8)
                elif len(self._legendList) < 28:
                    loc = (1.05,  0.0)
                    fontproperties = FontProperties(size=6)
                else:
                    loc = (1.05,  -0.1)
                    fontproperties = FontProperties(size=6)

        if matplotlib_version < '0.99.0':
            legend = self.ax.legend(self._legendList,
                                loc = loc,
                                prop = fontproperties,
                                labelsep = labelsep,
                                pad = 0.15)
        else:
            legend = self.ax.legend(self._legendList,
                                loc = loc,
                                prop = fontproperties,
                                labelspacing = labelsep,
                                borderpad = 0.15)
        legend.draw_frame(drawframe)


    def saveFile(self, filename, format=None):
        if format is None:
            format = filename[-3:]

        if format.upper() not in ['EPS', 'PNG', 'SVG']:
            raise ValueError("Unknown format %s" % format)

        if os.path.exists(filename):
            os.remove(filename)

        if self.limitsSet:
            self.ax.set_ylim(self.ymin, self.ymax)
            self.ax.set_xlim(self.xmin, self.xmax)
        #self.plotLegends()
        self.print_figure(filename)
        return

class PyMcaMatplotlibSaveImage:
    def __init__(self, imageData=None, fileName=None,
                     dpi=300,
                     size=(5, 5),
                     xaxis='off',
                     yaxis='off',
                     xlabel='',
                     ylabel='',
                     nxlabels=0,
                     nylabels=0,
                     colorbar=None,
                     title='',
                     interpolation='nearest',
                     colormap=None,
                     linlogcolormap='linear',
                     origin='lower',
                     contour='off',
                     contourlabels='on',
                     contourlabelformat='%.3f',
                     contourlevels=10,
                     contourlinewidth=10,
                     xorigin=0.0,
                     yorigin=0.0,
                     xpixelsize=1.0,
                     ypixelsize=1.0,
                     xlimits=None,
                     ylimits=None,
                     vlimits=None,
                     extent=None):

        self.figure = Figure(figsize=size) #in inches
        self.canvas = FigureCanvas(self.figure)
        self.imageData = imageData
        self.pixmapImage = None
        self.config={'xaxis':xaxis,
                    'yaxis':yaxis,
                    'title':title,
                    'xlabel':xlabel,
                    'ylabel':ylabel,
                    'nxlabels':nxlabels,
                    'nylabels':nylabels,
                    'colorbar':colorbar,
                    'colormap':colormap,
                    'linlogcolormap':linlogcolormap,
                    'interpolation':interpolation,
                    'origin':origin,
                    'contour':contour,
                    'contourlabels':contourlabels,
                    'contourlabelformat':contourlabelformat,
                    'contourlevels':contourlevels,
                    'contourlinewidth':contourlinewidth,
                    'xpixelsize':xpixelsize,
                    'ypixelsize':ypixelsize,
                    'xorigin':xorigin,
                    'yorigin':yorigin,
                    'zoomxmin':None,
                    'zoomxmax':None,
                    'zoomymin':None,
                    'zoomymax':None,
                    'valuemin':None,
                    'valuemax':None,
                    'xlimits':xlimits,
                    'ylimits':ylimits,
                    'vlimits':vlimits,
                    'extent':extent}

        #generate own colormaps
        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 1.0, 1.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}
        self.__redCmap = LinearSegmentedColormap('red',cdict,256)

        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 1.0, 1.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}
        self.__greenCmap = LinearSegmentedColormap('green',cdict,256)

        cdict = {'red': ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 0.0, 0.0),
                          (1.0, 1.0, 1.0))}
        self.__blueCmap = LinearSegmentedColormap('blue',cdict,256)

        # Temperature as defined in spslut
        cdict = {'red': ((0.0, 0.0, 0.0),
                         (0.5, 0.0, 0.0),
                         (0.75, 1.0, 1.0),
                         (1.0, 1.0, 1.0)),
                 'green': ((0.0, 0.0, 0.0),
                           (0.25, 1.0, 1.0),
                           (0.75, 1.0, 1.0),
                           (1.0, 0.0, 0.0)),
                 'blue': ((0.0, 1.0, 1.0),
                          (0.25, 1.0, 1.0),
                          (0.5, 0.0, 0.0),
                          (1.0, 0.0, 0.0))}

        #Do I really need as many colors?
        self.__temperatureCmap = LinearSegmentedColormap('temperature',
                                                         cdict, 65536)

        #reversed gray
        cdict = {'red':     ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0)),
                 'green':   ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0)),
                 'blue':    ((0.0, 1.0, 1.0),
                             (1.0, 0.0, 0.0))}

        self.__reversedGrayCmap = LinearSegmentedColormap('yerg', cdict, 256)

        if fileName is not None:
            self.saveImage(fileName)

    def setImage(self, image=None):
        self.imageData = image

    def setParameters(self, ddict):
        self.config.update(ddict)

    def saveImage(self, filename):
        self.figure.clear()
        if (self.imageData is None) and\
           (self.pixmapImage is None):
            return
        # The axes
        self.axes = self.figure.add_axes([.15, .15, .75, .8])
        if self.config['xaxis'] == 'off':
            self.axes.xaxis.set_visible(False)
        else:
            self.axes.xaxis.set_visible(True)
            nLabels = self.config['nxlabels']
            if nLabels not in ['Auto', 'auto', '0', 0]:
                self.axes.xaxis.set_major_locator(MaxNLocator(nLabels))
            else:
                self.axes.xaxis.set_major_locator(AutoLocator())
        if self.config['yaxis'] == 'off':
            self.axes.yaxis.set_visible(False)
        else:
            self.axes.yaxis.set_visible(True)
            if nLabels not in ['Auto', 'auto', '0', 0]:
                self.axes.yaxis.set_major_locator(MaxNLocator(nLabels))
            else:
                self.axes.yaxis.set_major_locator(AutoLocator())

        if self.pixmapImage is not None:
            self._savePixmapFigure(filename)
            return

        interpolation = self.config['interpolation']
        origin = self.config['origin']

        cmap = self.__temperatureCmap
        ccmap = cm.gray
        if self.config['colormap'] in ['grey','gray']:
            cmap  = cm.gray
            ccmap = self.__temperatureCmap
        elif self.config['colormap'] in ['yarg','yerg']:
            cmap  = self.__reversedGrayCmap
            ccmap = self.__temperatureCmap
        elif self.config['colormap']=='jet':
            cmap = cm.jet
        elif self.config['colormap']=='hot':
            cmap = cm.hot
        elif self.config['colormap']=='cool':
            cmap = cm.cool
        elif self.config['colormap']=='copper':
            cmap = cm.copper
        elif self.config['colormap']=='spectral':
            cmap = cm.spectral
        elif self.config['colormap']=='hsv':
            cmap = cm.hsv
        elif self.config['colormap']=='rainbow':
            cmap = cm.gist_rainbow
        elif self.config['colormap']=='red':
            cmap = self.__redCmap
        elif self.config['colormap']=='green':
            cmap = self.__greenCmap
        elif self.config['colormap']=='blue':
            cmap = self.__blueCmap
        elif self.config['colormap']=='temperature':
            cmap = self.__temperatureCmap
        elif self.config['colormap'] == 'paired':
            cmap = cm.Paired
        elif self.config['colormap'] == 'paired_r':
            cmap = cm.Paired_r
        elif self.config['colormap'] == 'pubu':
            cmap = cm.PuBu
        elif self.config['colormap'] == 'pubu_r':
            cmap = cm.PuBu_r
        elif self.config['colormap'] == 'rdbu':
            cmap = cm.RdBu
        elif self.config['colormap'] == 'rdbu_r':
            cmap = cm.RdBu_r
        elif self.config['colormap'] == 'gist_earth':
            cmap = cm.gist_earth
        elif self.config['colormap'] == 'gist_earth_r':
            cmap = cm.gist_earth_r
        elif self.config['colormap'] == 'blues':
            cmap = cm.Blues
        elif self.config['colormap'] == 'blues_r':
            cmap = cm.Blues_r
        elif self.config['colormap'] == 'ylgnbu':
            cmap = cm.YlGnBu
        elif self.config['colormap'] == 'ylgnbu_r':
            cmap = cm.YlGnBu_r
        else:
            _logger.warning("Unsupported colormap %s", self.config['colormap'])
            _logger.warning("Defaulting to grayscale.")

        if self.config['extent'] is None:
            h, w = self.imageData.shape
            x0 = self.config['xorigin']
            y0 = self.config['yorigin']
            w = w * self.config['xpixelsize']
            h = h * self.config['ypixelsize']
            if origin == 'upper':
                extent = (x0, w+x0,
                          h+y0, y0)
            else:
                extent = (x0, w+x0,
                          y0, h+y0)
        else:
            extent = self.config['extent']

        vlimits = self.__getValueLimits()
        if vlimits is None:
            imageData = self.imageData
            vmin = self.imageData.min()
            vmax = self.imageData.max()
        else:
            vmin = min(vlimits[0], vlimits[1])
            vmax = max(vlimits[0], vlimits[1])
            imageData = self.imageData.clip(vmin,vmax)

        if self.config['linlogcolormap'] != 'linear':
            if vmin <= 0:
                if vmax > 0:
                    vmin = min(imageData[imageData>0])
                else:
                    vmin = 0.0
                    vmax = 1.0
            self._image  = self.axes.imshow(imageData.clip(vmin,vmax),
                                        interpolation=interpolation,
                                        origin=origin,
                                        cmap=cmap,
                                        extent=extent,
                                        norm=LogNorm(vmin, vmax))
        else:
            self._image  = self.axes.imshow(imageData,
                                        interpolation=interpolation,
                                        origin=origin,
                                        cmap=cmap,
                                        extent=extent,
                                        norm=Normalize(vmin, vmax))

        ylim = self.axes.get_ylim()

        if self.config['colorbar'] is not None:
            barorientation = self.config['colorbar']
            self._colorbar = self.figure.colorbar(self._image,
                                        orientation=barorientation)

        #contour plot
        if self.config['contour'] != 'off':
            dataMin = imageData.min()
            dataMax = imageData.max()
            ncontours = int(self.config['contourlevels'])
            contourlinewidth = int(self.config['contourlinewidth'])/10.
            levels = (numpy.arange(ncontours)) *\
                     (dataMax - dataMin)/float(ncontours)
            if self.config['contour'] == 'filled':
                self._contour = self.axes.contourf(imageData, levels,
                     origin=origin,
                     cmap=ccmap,
                     extent=extent)
            else:
                self._contour = self.axes.contour(imageData, levels,
                     origin=origin,
                     cmap=ccmap,
                     linewidths=contourlinewidth,
                     extent=extent)
            if self.config['contourlabels'] != 'off':
                self.axes.clabel(self._contour, fontsize=9,
                         inline=1, fmt=self.config['contourlabelformat'])
            if 0 and  self.config['colorbar'] is not None:
                if barorientation == 'horizontal':
                    barorientation = 'vertical'
                else:
                    barorientation = 'horizontal'
                self._ccolorbar=self.figure.colorbar(self._contour,
                                                     orientation=barorientation,
                                                     extend='both')

        self.__postImage(ylim, filename)


    def setPixmapImage(self, image=None, bgr=False):
        if bgr:
            self.pixmapImage = image * 1
            self.pixmapImage[:,:,0] = image[:,:,2]
            self.pixmapImage[:,:,2] = image[:,:,0]
        else:
            self.pixmapImage = image

    def _savePixmapFigure(self, filename):
        interpolation = self.config['interpolation']
        origin = self.config['origin']
        if self.config['extent'] is None:
            h= self.pixmapImage.shape[0]
            w= self.pixmapImage.shape[1]
            x0 = self.config['xorigin']
            y0 = self.config['yorigin']
            w = w * self.config['xpixelsize']
            h = h * self.config['ypixelsize']
            if origin == 'upper':
                extent = (x0, w+x0,
                          h+y0, y0)
            else:
                extent = (x0, w+x0,
                          y0, h+y0)
        else:
            extent = self.config['extent']
        self._image = self.axes.imshow(self.pixmapImage,
                                       interpolation=interpolation,
                                       origin=origin,
                                       extent=extent)

        ylim = self.axes.get_ylim()
        self.__postImage(ylim, filename)

    def __getValueLimits(self):
        if (self.config['valuemin'] is not None) and\
           (self.config['valuemax'] is not None) and\
           (self.config['valuemin'] != self.config['valuemax']):
            vlimits = (self.config['valuemin'],
                           self.config['valuemax'])
        elif self.config['vlimits'] is not None:
            vlimits = self.config['vlimits']
        else:
            vlimits = None
        return vlimits

    def __postImage(self, ylim, filename):
        self.axes.set_title(self.config['title'])
        self.axes.set_xlabel(self.config['xlabel'])
        self.axes.set_ylabel(self.config['ylabel'])

        origin = self.config['origin']
        if (self.config['zoomxmin'] is not None) and\
           (self.config['zoomxmax'] is not None)and\
           (self.config['zoomxmax'] != self.config['zoomxmin']):
            xlimits = (self.config['zoomxmin'],
                           self.config['zoomxmax'])
        elif self.config['xlimits'] is not None:
            xlimits = self.config['xlimits']
        else:
            xlimits = None

        if (self.config['zoomymin'] is not None) and\
           (self.config['zoomymax'] is not None) and\
           (self.config['zoomymax'] != self.config['zoomymin']):
            ylimits = (self.config['zoomymin'],
                           self.config['zoomymax'])
        elif self.config['ylimits'] is not None:
            ylimits = self.config['ylimits']
        else:
            ylimits = None

        if ylimits is None:
            self.axes.set_ylim(ylim[0],ylim[1])
        else:
            ymin = min(ylimits)
            ymax = max(ylimits)
            if origin == "lower":
                self.axes.set_ylim(ymin, ymax)
            else:
                self.axes.set_ylim(ymax, ymin)

        if xlimits is not None:
            xmin = min(xlimits)
            xmax = max(xlimits)
            self.axes.set_xlim(xmin, xmax)

        self.canvas.print_figure(filename)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        a=numpy.arange(1200.)
        a = a.reshape(20, 60)
        PyMcaMatplotlibSaveImage(a, "filename.png", colormap="rainbow")
        print("Image filename.png saved")
    else:
        w=PyMcaMatplotlibSave(legends=True)
        x = numpy.arange(1200.)
        w.setLimits(0, 1200., 0, 12000.)
        if len(sys.argv) > 2:
            n = int(sys.argv[2])
        else:
            n = 14
        for i in range(n):
            y = x * i
            w.addDataToPlot(x,y, legend="%d" % i)
        #w.setTitle('title')
        w.setXLabel('Channel')
        w.setYLabel('Counts')
        w.plotLegends()
        w.saveFile("filename.png")
        print("Plot filename.png saved")
    sys.exit(0)

