#/*##########################################################################
# Copyright (C) 2004-2017 V.A. Sole, European Synchrotron Radiation Facility
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
"""This module defines a set of simple plot actions processing one or all
plotted curves in a ScanWindow:

    - :class:`AverageAction`
    - :class:`DerivativeAction`
    - :class:`SmoothAction`
    - :class:`SwapSignAction`
    - :class:`SubtractAction`
    - :class:`YMinToZeroAction`

"""
import copy

from silx.gui.plot.actions import PlotAction

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaMath import SimpleMath
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict

QString = qt.safe_str

_simpleMath = SimpleMath.SimpleMath()


def _getOneCurve(plot, qwarning=True):
    """Return active curve if any,
    else if there is a single curve return it,
    else return None.

    :param plot: Plot instance
    :param bool qwarning: If True, display a warning popup to
        inform that a curve must be selected when function is not
        successful.
    """
    curve = plot.getActiveCurve()
    if curve is None:
        curves = plot.getAllCurves()
        if not curves or len(curves) > 1:
            if qwarning:
                _QWarning(msg="You must select a curve.",
                          parent=plot)
            return None
        return curves[0]
    return curve


def _QWarning(msg, parent=None):
    """Print a warning message in a QMessageBox"""
    mb = qt.QMessageBox(parent)
    mb.setIcon(qt.QMessageBox.Warning)
    mb.setText(msg)
    mb.exec()

#
# def _isActive(legend, plot):
#     """
#
#     :param legend: curve legend
#     :param plot: plot instance
#     :return: True or False
#     """
#     active_legend = plot.getActiveCurve(just_legend=True)
#     if active_legend is None:
#         # No active curve
#         return False
#     return legend == active_legend


def _updated_info(info0, sourcename, operation):
    info1 = copy.deepcopy(info0)
    if not 'operations' in info1:
        info1['operations'] = []
    info1['operations'].append(operation)
    info1['SourceName'] = sourcename
    if 'selectionlegend' in info1:
        del info1['selectionlegend']
    return info1


class AverageAction(PlotAction):
    """Average all curves, clear plot, add average curve
    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["average16"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            text='Average Plotted Curves',
                            tooltip='Replace all curves by the average curve',
                            triggered=self._averageAllCurves,
                            parent=parent)

    def _averageAllCurves(self):
        curves = self.plot.getAllCurves()
        if not curves:
            return
        x0, y0, legend0, info0, _params0 = curves[0]
        avg_legend = legend0
        all_x = [x0]
        all_y = [y0]
        for x, y, legend, info, params in curves[1:]:
            avg_legend += " + " + legend
            all_x.append(x)
            all_y.append(y)

        avg_info = _updated_info(info0, avg_legend, "average")

        xavg, yavg = _simpleMath.average(all_x, all_y)
        avg_legend = "(%s)/%d" % (avg_legend, len(curves))

        self.plot.clearCurves()
        self.plot.addCurve(xavg, yavg, avg_legend,
                           info=avg_info)


class SmoothAction(PlotAction):
    """Plot smooth of the active curve if any,
    else plot smooth of the only existing curve if any.
    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["smooth"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            text='Smooth Active Curve',
                            tooltip='Smooth Active Curve',
                            triggered=self._smoothActiveCurve,
                            parent=parent)

    def _smoothActiveCurve(self):
        curve = _getOneCurve(self.plot)
        if curve is None:
            return
        x0, y0, legend0, info0, _params = curve

        x1 = x0 * 1
        y1 = _simpleMath.smooth(y0)

        if info0.get("operations") is None or \
                info0["operations"][-1] != "smooth":
            legend1 = "%s Smooth" % legend0
        else:
            # don't repeat "smooth"
            legend1 = legend0

        info1 = _updated_info(info0, legend0, "smooth")

        self.plot.addCurve(x1, y1, legend1,
                           info=info1)


class DerivativeAction(PlotAction):
    """Plot derivative of the active curve if any,
    else the derivative of the only existing curve.
    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["derive"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            tooltip='Plot Derivative of Active Curve',
                            text='Derivate Active Curve',
                            triggered=self._derivateActiveCurve,
                            parent=parent)

    def _derivateActiveCurve(self):
        curve = _getOneCurve(self.plot)
        if curve is None:
            return
        x0, y0, legend0, info0, params0 = curve

        x1, y1 = _simpleMath.derivate(x0, y0)
        legend1 = legend0 + "'"

        info1 = _updated_info(info0, legend0, "derivate")
        info1['plot_yaxis'] = "right"

        ylabel1 = params0.get("ylabel")
        if ylabel1 is None:
            ylabel1 = "Y"

        self.plot.addCurve(x1, y1, legend1,
                           ylabel=ylabel1 + "'",
                           info=info1,
                           yaxis="right")


class SwapSignAction(PlotAction):
    """Plot the active curve multiplied by -1
    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["swapsign"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            text='Multiply Active Curve by -1',
                            tooltip='Multiply Active Curve by -1',
                            triggered=self._swapSignCurve,
                            parent=parent)

    def _swapSignCurve(self):
        curve = _getOneCurve(self.plot)
        if curve is None:
            return
        x0, y0, legend0, info0, _params = curve

        x1 = 1 * x0
        y1 = -y0
        legend1 = "-(%s)" % legend0

        info1 = _updated_info(info0, legend0, "swapsign")

        self.plot.addCurve(x1, y1, legend1,
                           info=info1)


class YMinToZeroAction(PlotAction):
    """

    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["ymintozero"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            text='Y Min to Zero',
                            tooltip='Shift curve vertically to put min value at 0',
                            triggered=self._yMinToZeroCurve,
                            parent=parent)

    def _yMinToZeroCurve(self):
        curve = _getOneCurve(self.plot)
        if curve is None:
            return
        x0, y0, legend0, info0, _params = curve

        x1 = x0 * 1
        y1 = y0 - min(y0)
        legend1 = "(%s) - ymin" % legend0

        info1 = _updated_info(info0, legend0, "forceymintozero")

        self.plot.addCurve(x1, y1, legend1,
                           info=info1)


class SubtractAction(PlotAction):
    """Subtract active curve from all curves.

    """
    def __init__(self, plot, parent=None):
        self.icon = qt.QIcon(qt.QPixmap(IconDict["subtract"]))
        PlotAction.__init__(self,
                            plot,
                            icon=self.icon,
                            text='Subtract Active Curve',
                            tooltip='Subtract active curve from all curves',
                            triggered=self._subtractCurve,
                            parent=parent)

    def _subtractCurve(self):
        active_curve = _getOneCurve(self.plot)
        all_curves = self.plot.getAllCurves()

        #############################################################
        if active_curve is None:
            return

        x0, y0, legend0, info0, params0 = active_curve

        ylabel0 = params0.get("ylabel", "Y0")
        if ylabel0 is None:
            ylabel0 = "Y0"

        for x, y, legend, info, params in all_curves:
            # (y1 - y0) is equivalent to 2 * average(-y0, y1)
            XX = [x0, x]
            YY = [-y0, y]
            xplot, yplot = _simpleMath.average(XX, YY)
            yplot *= 2
            legend1 = "(%s - %s)" % (legend, legend0)

            ylabel = params0.get("ylabel", "Y")
            if ylabel is None:
                ylabel = "Y"

            ylabel1 = "(%s - %s)" % (ylabel, ylabel0)

            info1 = _updated_info(info, legend, "subtract")
            info1['LabelNames'] = [legend1]

            self.plot.removeCurve(legend)
            self.plot.addCurve(xplot, yplot, legend1,
                               info=info1, ylabel=ylabel1)
