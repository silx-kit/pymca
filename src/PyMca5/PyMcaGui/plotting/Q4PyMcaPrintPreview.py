#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
import traceback
from PyMca5.PyMcaGui import PyMcaQt as qt
DEBUG = 0
__revision__="$Revision: 1.7 $"

# TODO:
# - automatic picture centering
# - print quality

QTVERSION = qt.qVersion()


################################################################################
##################             PyMcaPrintPreview               ###################
################################################################################
class PyMcaPrintPreview(qt.QDialog):
    def __init__(self, parent = None, printer = None, name = "PyMcaPrintPreview", \
                 modal = 0, fl = 0):

        qt.QDialog.__init__(self, parent)
        self.setWindowTitle(name)
        self.setModal(modal)
        self.resize(400, 500)
        self.printDialog = None
        self._toBeCleared = False
        self._svgItems = []
        self.printer = printer
        """
        if printer is None:
            printer = qt.QPrinter(qt.QPrinter.HighResolution)
            printer.setPageSize(qt.QPrinter.A4)
            printerName = "%s"  % printer.printerName()
            if printerName in ['id24b2u']:
                #id24 printer very slow in color mode
                printer.setColorMode(qt.QPrinter.GrayScale)
            printer.setFullPage(True)
            if (printer.width() <= 0) or (printer.height() <= 0):
                filename = "PyMCA_print.ps"
                if sys.platform == 'win32':
                    home = os.getenv('USERPROFILE')
                    try:
                        l = len(home)
                        directory = os.path.join(home,"My Documents")
                    except Exception:
                        home = '\\'
                        directory = '\\'
                    if os.path.isdir('%s' % directory):
                        directory = os.path.join(directory,"PyMca")
                    else:
                        directory = os.path.join(home,"PyMca")
                    if not os.path.exists('%s' % directory):
                        os.mkdir('%s' % directory)
                    finalfile = os.path.join(directory, filename)
                else:
                    home = os.getenv('HOME')
                    directory = os.path.join(home,"PyMca")
                    if not os.path.exists('%s' % directory):
                        os.mkdir('%s' % directory)
                    finalfile =  os.path.join(directory, filename)
                printer.setOutputFileName(finalfile)
                printer.setColorMode(qt.QPrinter.Color)

        """
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self._buildToolbar()

        self.scene = None
        self.page = None
        self.view = None
        self._viewScale = 1.0
        self.badNews = None

    def exec_(self):
        return self.exec()

    def exec(self):
        if self._toBeCleared:
            self.__clearAll()
        return qt.QDialog.exec(self)

    def raise_(self):
        if self._toBeCleared:
            self.__clearAll()
        return qt.QDialog.raise_(self)

    def show(self):
        if self._toBeCleared:
            self.__clearAll()
        return qt.QDialog.show(self)

    def setOutputFileName(self, name):
        if self.printer is not None:
            self.printer.setOutputFileName(name)
        else:
            raise IOError("setOutputFileName : a printer must be defined before")

    def _buildToolbar(self):
        # --- command buttons
        # buttonSize = 65
        toolBar = qt.QWidget(self)
        # a layout for the toolbar
        toolsLayout = qt.QHBoxLayout(toolBar)
        toolsLayout.setContentsMargins(0, 0, 0, 0)
        toolsLayout.setSpacing(0)

        # Margin
        # marginLabel = qt.QLabel("Margins:", toolBar)
        # if QTVERSION < '4.0.0':
        #     self.marginSpin = qt.QSpinBox(0, 50, 10, toolBar)
        # else:
        #     self.marginSpin = qt.QSpinBox(toolBar)
        #     self.marginSpin.setRange(0, 50)
        #     self.marginSpin.setSingleStep(10)
        # self.marginSpin.valueChanged[int].connect( \
        #          self.__marginChanged)

        # Scale / Zoom
        # scaleLabel = qt.QLabel("Zoom:", toolBar)
        # scaleCombo = qt.QComboBox(toolBar)
        # self.scaleValues = [20, 40, 60, 80, 100, 150, 200]
        #
        # for scale in self.scaleValues:
        #     scaleCombo.addItem("%3d %%"%scale)
        #
        # self.scaleCombo = scaleCombo
        # self.scaleCombo.activated[int].connect(self.__scaleChanged)

        hideBut   = qt.QPushButton("Hide", toolBar)
        #hideBut.setFixedWidth(buttonSize-10)
        hideBut.clicked.connect(self.hide)

        cancelBut = qt.QPushButton("Clear All", toolBar)
        #cancelBut.setFixedWidth(buttonSize+10)
        cancelBut.clicked.connect(self.__clearAll)

        removeBut = qt.QPushButton("Remove", toolBar)
        #removeBut.setFixedWidth(buttonSize)
        removeBut.clicked.connect(self.__remove)

        setupBut  = qt.QPushButton("Setup", toolBar)
        #setupBut.setFixedWidth(buttonSize-5)
        setupBut.clicked.connect(self.setup)

        printBut  = qt.QPushButton("Print", toolBar)
        #printBut.setFixedWidth(buttonSize-5)
        printBut.clicked.connect(self.__print)

        zoomPlusBut  = qt.QPushButton("Zoom +", toolBar)
        #zoomPlusBut.setFixedWidth(buttonSize-5)
        zoomPlusBut.clicked.connect(self.__zoomPlus)

        zoomMinusBut  = qt.QPushButton("Zoom -", toolBar)
        #zoomMinusBut.setFixedWidth(buttonSize-5)
        zoomMinusBut.clicked.connect(self.__zoomMinus)

        # now we put widgets in the toolLayout
        toolsLayout.addWidget(hideBut)
        toolsLayout.addWidget(printBut)
        toolsLayout.addWidget(cancelBut)
        toolsLayout.addWidget(removeBut)
        toolsLayout.addWidget(setupBut)
        #toolsLayout.addStretch()
        #toolsLayout.addWidget(marginLabel)
        #toolsLayout.addWidget(self.marginSpin)
        toolsLayout.addStretch()
        #toolsLayout.addWidget(scaleLabel)
        #toolsLayout.addWidget(scaleCombo)
        toolsLayout.addWidget(zoomPlusBut)
        toolsLayout.addWidget(zoomMinusBut)
        #toolsLayout.addStretch()
        self.toolBar = toolBar
        self.mainLayout.addWidget(self.toolBar)

    def _buildStatusBar(self):
        # status bar
        statusBar = qt.QStatusBar(self)
        self.targetLabel = qt.QLabel(statusBar)
        self.__updateTargetLabel()
        statusBar.addWidget(self.targetLabel)
        self.mainLayout.addWidget(statusBar)

    def __updateTargetLabel(self):
        if self.printer is None:
            self.targetLabel.setText("???")
            return
        if hasattr(qt, "QString"):
            if len(self.printer.outputFileName()):
                self.targetLabel.setText(qt.QString("File:").append(
                    self.printer.outputFileName()))
            else:
                self.targetLabel.setText(qt.QString("Printer:").append(
                    self.printer.printerName()))
        else:
            if len(self.printer.outputFileName()):
                self.targetLabel.setText("File:"+\
                    self.printer.outputFileName())
            else:
                self.targetLabel.setText("Printer:"+\
                    self.printer.printerName())

    def __print(self):
        printer = self.printer
        painter = qt.QPainter()
        try:
            if not(painter.begin(printer)):
                print("CANOT INITIALIZE PRINTER")
                return 0
            self.scene.render(painter, qt.QRectF(0, 0, printer.width(), printer.height()),
                              qt.QRectF(self.page.rect().x(), self.page.rect().y(),
                              self.page.rect().width(),self.page.rect().height()),
                              qt.Qt.KeepAspectRatio)
            painter.end()
            self.hide()
            self.accept()
            self._toBeCleared = True
        except Exception:
            painter.end()
            qt.QMessageBox.critical(self, "ERROR",
                                    'Printing problem:\n %s' % sys.exc_info()[1])
            return

    def __scaleChanged(self, value):
        if DEBUG:
            print("current scale = ",   self._viewScale)
        if value > 2:
            self.view.scale(1.20, 1.20)
        else:
            self.view.scale(0.80, 0.80)

    def __zoomPlus(self):
        if DEBUG:
            print("current scale = ",   self._viewScale)
        self._viewScale *= 1.20
        self.view.scale(1.20, 1.20)

    def __zoomMinus(self):
        if DEBUG:
            print("current scale = ",   self._viewScale)
        self._viewScale *= 0.80
        self.view.scale(0.80, 0.80)

    def addImage(self, image, title = None, comment = None, commentPosition=None):
        """
        add an image item to the print preview scene
        """
        self.addPixmap(qt.QPixmap.fromImage(image),
                       title = title, comment = comment,
                       commentPosition=commentPosition)

    def addPixmap(self, pixmap, title = None, comment = None, commentPosition=None):
        """
        add a pixmap to the print preview scene
        """
        if self._toBeCleared:
            self.__clearAll()
        if self.printer is None:
            self.setup()
        if title is None:
            title  = '                                            '
            title += '                                            '
        if comment is None:
            comment  = '                                            '
            comment += '                                            '
        if commentPosition is None:
            commentPosition = "CENTER"
        if self.badNews:
            return
        rectItem = qt.QGraphicsRectItem(self.page)
        scale = 1.0 # float(0.5 * self.scene.width()/pixmap.width())
        rectItem.setRect(qt.QRectF(1, 1,
                        pixmap.width(), pixmap.height()))

        pen = rectItem.pen()
        color = qt.QColor(qt.Qt.red)
        color.setAlpha(1)
        pen.setColor(color)
        rectItem.setPen(pen)
        rectItem.setZValue(1)
        rectItem.setFlag(qt.QGraphicsItem.ItemIsSelectable, True)
        rectItem.setFlag(qt.QGraphicsItem.ItemIsMovable, True)
        rectItem.setFlag(qt.QGraphicsItem.ItemIsFocusable, False)

        #I add the resize tool
        rectItemResizeRect = GraphicsResizeRectItem(rectItem, self.scene)
        rectItemResizeRect.setZValue(2)

        #I add a pixmap item
        pixmapItem = qt.QGraphicsPixmapItem(rectItem)
        pixmapItem.setPixmap(pixmap)
        #pixmapItem.moveBy(0, 0)
        pixmapItem.setZValue(0)

        #I add the title
        textItem = qt.QGraphicsTextItem(title, rectItem)
        textItem.setTextInteractionFlags(qt.Qt.TextEditorInteraction)
        offset = 0.5 * textItem.boundingRect().width()
        textItem.moveBy(0.5 * pixmap.width() - offset, -20)
        textItem.setZValue(2)

        #I add the comment
        commentItem = qt.QGraphicsTextItem(comment, rectItem)
        commentItem.setTextInteractionFlags(qt.Qt.TextEditorInteraction)
        offset = 0.5 * commentItem.boundingRect().width()
        if commentPosition.upper() == "LEFT":
            x = 1
        else:
            x = 0.5 * pixmap.width() - offset
        commentItem.moveBy(x, pixmap.height()+20)
        commentItem.setZValue(2)

        #I should adjust text size here
        #textItem.scale(2,2)
        #commentItem.scale(2,2)
        rectItem.setScale(scale)
        rectItem.moveBy(20 , 40)

    def isReady(self):
        if self.badNews:
            return False
        else:
            return True

    def addSvgItem(self, item, title = None, comment = None, commentPosition=None):
        if self._toBeCleared:
            self.__clearAll()
        if self.printer is None:
            self.setup()
        if self.badNews:
            # printer not properly initialized
            return
        if not isinstance(item, qt.QSvgRenderer):
            raise TypeError("addSvgItem: QSvgRenderer expected")
        if title is None:
            title  = 50 * ' '
        if comment is None:
            comment  = 80 * ' '
        if commentPosition is None:
            commentPosition = "CENTER"

        if 0 and hasattr(item, "_viewBox"):
            svgItem = GraphicsSvgItem(self.page)
            svgItem.setSharedRenderer(item)
            svgItem.setBoundingRect(item._viewBox)
        elif 1:
            svgItem = GraphicsSvgRectItem(item._viewBox, self.page)
            svgItem.setSvgRenderer(item)
        else:
            svgItem = qt.QGraphicsSvgItem(self.page)
            svgItem.setSharedRenderer(item)
            if hasattr(item, "_viewBox"):
                svgScaleX = item._viewBox.width()/svgItem.boundingRect().width()
                svgScaleY = item._viewBox.height()/svgItem.boundingRect().height()
                svgItem.scale(svgScaleX, svgScaleY)

        svgItem.setCacheMode(qt.QGraphicsItem.NoCache)
        svgItem.setZValue(0)
        svgItem.setFlag(qt.QGraphicsItem.ItemIsSelectable, True)
        svgItem.setFlag(qt.QGraphicsItem.ItemIsMovable, True)
        svgItem.setFlag(qt.QGraphicsItem.ItemIsFocusable, False)

        #I add the resize tool
        rectItemResizeRect = GraphicsResizeRectItem(svgItem, self.scene)
        rectItemResizeRect.setZValue(2)


        #make sure the life time of the item is enough to print it!
        self._svgItems.append(item)

        #I add the title
        textItem = qt.QGraphicsTextItem(title, svgItem)
        textItem.setTextInteractionFlags(qt.Qt.TextEditorInteraction)
        offset = 0.5 * textItem.boundingRect().width()
        textItem.setZValue(1)
        textItem.setFlag(qt.QGraphicsItem.ItemIsMovable, True)

        #I add the comment
        dummyComment = 80 * "1"
        commentItem = qt.QGraphicsTextItem(dummyComment, svgItem)
        commentItem.setTextInteractionFlags(qt.Qt.TextEditorInteraction)
        scaleCalculationRect = qt.QRectF(commentItem.boundingRect())
        commentItem.setPlainText(comment)
        commentItem.moveBy(svgItem.boundingRect().x(),
                           svgItem.boundingRect().y() + svgItem.boundingRect().height())

        commentItem.setZValue(1)
        scale = svgItem.boundingRect().width() / scaleCalculationRect.width()
        commentItem.setFlag(qt.QGraphicsItem.ItemIsMovable, True)
        commentItem.setScale(scale)
        textItem.moveBy(svgItem.boundingRect().x()+\
                        0.5 * svgItem.boundingRect().width() - offset * scale,
                        svgItem.boundingRect().y())
        textItem.setScale(scale)

    def setup(self):
        """
        """
        if self.printer is None:
            self.printer = qt.QPrinter()
        if (self.printDialog is None) or (not self.isReady()):
            self.printDialog = qt.QPrintDialog(self.printer, self)
        if self.printDialog.exec():
            if (self.printer.width() <= 0) or (self.printer.height() <= 0):
                self.message = qt.QMessageBox(self)
                self.message.setIcon(qt.QMessageBox.Critical)
                self.message.setText("Unknown library error \non printer initialization")
                self.message.setWindowTitle("Library Error")
                self.message.setModal(0)
                self.badNews = True
                self.printer = None
                return
            self.badNews = False
            self.printer.setFullPage(True)
            self.updatePrinter()
        else:
            if self.page is None:
                # not initialized
                self.badNews = True
                self.printer = None
            else:
                self.badNews = False

    def updatePrinter(self):
        if DEBUG:
            print("UPDATE PRINTER")
        printer = self.printer
        if self.scene is None:
            self.scene = qt.QGraphicsScene()
            self.scene.setBackgroundBrush(qt.QColor(qt.Qt.lightGray))
            self.scene.setSceneRect(qt.QRectF(0,0, printer.width(), printer.height()))

        if self.page is None:
            self.page = qt.QGraphicsRectItem(0,0, printer.width(), printer.height())
            self.page.setBrush(qt.QColor(qt.Qt.white))
            self.scene.addItem(self.page)

        self.scene.setSceneRect(qt.QRectF(0,0, self.printer.width(), self.printer.height()))
        self.page.setPos(qt.QPointF(0.0, 0.0))
        self.page.setRect(qt.QRectF(0,0, self.printer.width(), self.printer.height()))

        if self.view is None:
            self.view = qt.QGraphicsView(self.scene)
            self.mainLayout.addWidget(self.view)
            self._buildStatusBar()
        self.view.fitInView(self.page.rect(), qt.Qt.KeepAspectRatio)
        self._viewScale = 1.00
        #self.view.scale(1./self._viewScale, 1./self._viewScale)
        #self.view.fitInView(self.page.rect(), qt.Qt.KeepAspectRatio)
        #self._viewScale = 1.00
        self.__updateTargetLabel()

    def __cancel(self):
        """
        """
        self.reject()

    def __clearAll(self):
        """
        Clear the print preview window, remove all items
        but and keep the page.
        """
        itemlist = self.scene.items()
        keep = self.page
        while (len(itemlist) != 1):
            if itemlist.index(keep) == 0:
                self.scene.removeItem(itemlist[1])
            else:
                self.scene.removeItem(itemlist[0])
            itemlist = self.scene.items()
        self._svgItems = []
        self._toBeCleared = False

    def __remove(self):
        """
        """
        itemlist = self.scene.items()
        i = None

        #this loop is not efficient if there are many items ...
        for item in itemlist:
            if item.isSelected():
                i = itemlist.index(item)
                break

        if i is not None:
            self.scene.removeItem(item)
            #this line is not really needed because the list
            #should be deleted at the end of the method
            del itemlist[i]


if hasattr(qt, 'QGraphicsSvgItem'):
    class GraphicsSvgItem(qt.QGraphicsSvgItem):
        def setBoundingRect(self, rect):
            self._rect = rect

        def boundingRect(self):
            return self._rect

        def paint(self, painter, *var, **kw):
            if not self.renderer().isValid():
                print("Invalid renderer")
                return
            if self.elementId().isEmpty():
                self.renderer().render(painter, self._rect)
            else:
                self.renderer().render(painter,  self.elementId(), self._rect)

    class GraphicsSvgRectItem(qt.QGraphicsRectItem):
        def setSvgRenderer(self, renderer):
            self._renderer = renderer

        def paint(self, painter, *var, **kw):
            #self._renderer.render(painter, self._renderer._viewBox)
            self._renderer.render(painter, self.boundingRect())

class GraphicsResizeRectItem(qt.QGraphicsRectItem):
    """Resizable QGraphicsRectItem."""
    def __init__(self, parent=None, scene=None, keepratio=True):
        qt.QGraphicsRectItem.__init__(self, parent)
        rect = parent.boundingRect()
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        self._newRect = None
        self.keepRatio = keepratio
        self.setRect(qt.QRectF(x + w - 40, y + h - 40, 40, 40))
        self.setAcceptHoverEvents(True)
        pen = qt.QPen()
        color = qt.QColor(qt.Qt.white)
        color.setAlpha(0)
        pen.setColor(color)
        pen.setStyle(qt.Qt.NoPen)
        self.setPen(pen)
        self.setBrush(color)
        self.setFlag(qt.QGraphicsItem.ItemIsMovable, True)
        self.show()

    def hoverEnterEvent(self, event):
        if self.parentItem().isSelected():
            self.parentItem().setSelected(False)
        if self.keepRatio:
            self.setCursor(qt.QCursor(qt.Qt.SizeFDiagCursor))
        else:
            self.setCursor(qt.QCursor(qt.Qt.SizeAllCursor))
        self.setBrush(qt.QBrush(qt.Qt.yellow, qt.Qt.SolidPattern))
        return qt.QGraphicsRectItem.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.setCursor(qt.QCursor(qt.Qt.ArrowCursor))
        pen = qt.QPen()
        color = qt.QColor(qt.Qt.white)
        color.setAlpha(0)
        pen.setColor(color)
        pen.setStyle(qt.Qt.NoPen)
        self.setPen(pen)
        self.setBrush(color)
        return qt.QGraphicsRectItem.hoverLeaveEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if DEBUG:
            print("ResizeRect mouseDoubleClick")

    def mousePressEvent(self, event):
        if self._newRect is not None:
            self._newRect = None
        self._point0 = self.pos()
        parent = self.parentItem()
        scene = self.scene()
        # following line prevents dragging along the previously selected
        # item when resizing another one
        scene.clearSelection()

        rect = parent.boundingRect()
        self._x = rect.x()
        self._y = rect.y()
        self._w = rect.width()
        self._h = rect.height()
        self._ratio = self._w / self._h
        self._newRect = qt.QGraphicsRectItem(parent)
        self._newRect.setRect(qt.QRectF(self._x,
                                        self._y,
                                        self._w,
                                        self._h))
        qt.QGraphicsRectItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        point1 = self.pos()
        deltax = point1.x() - self._point0.x()
        deltay = point1.y() - self._point0.y()
        if self.keepRatio:
            r1 = (self._w + deltax) / self._w
            r2 = (self._h + deltay) / self._h
            if r1 < r2:
                self._newRect.setRect(qt.QRectF(self._x,
                                                self._y,
                                                self._w + deltax,
                                                (self._w + deltax) / self._ratio))
            else:
                self._newRect.setRect(qt.QRectF(self._x,
                                                self._y,
                                                (self._h + deltay) * self._ratio,
                                                self._h + deltay))
        else:
            self._newRect.setRect(qt.QRectF(self._x,
                                            self._y,
                                            self._w + deltax,
                                            self._h + deltay))
        qt.QGraphicsRectItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        point1 = self.pos()
        deltax = point1.x() - self._point0.x()
        deltay = point1.y() - self._point0.y()
        self.moveBy(-deltax, -deltay)
        parent = self.parentItem()

        # deduce scale from rectangle
        if self.keepRatio:
            scalex = self._newRect.rect().width() / self._w
            scaley = scalex
        else:
            scalex = self._newRect.rect().width() / self._w
            scaley = self._newRect.rect().height() / self._h

        # apply the scale to the previous transformation matrix
        previousTransform = parent.transform()
        parent.setTransform(
                previousTransform.scale(scalex, scaley))

        self.scene().removeItem(self._newRect)
        self._newRect = None
        qt.QGraphicsRectItem.mouseReleaseEvent(self, event)


################################################################################
#####################    TEST -- PyMcaPrintPreview  -- TEST   ##################
################################################################################
def testPreview():
    """
    """
    import sys
    import os

    if len(sys.argv) < 2:
        print("give an image file as parameter please.")
        sys.exit(1)

    if len(sys.argv) > 2:
        print("only one parameter please.")
        sys.exit(1)

    filename = sys.argv[1]
    if filename[-3:] == "svg":
        if 0:
            item = qt.QSvgWidget()
            item.load(filename)
            item.show()
        else:
            w = PyMcaPrintPreview( parent = None, printer = None, name = 'Print Prev',
                      modal = 0, fl = 0)
            w.resize(400,500)
            item = qt.QGraphicsSvgItem(filename, w.page)
            item.setFlag(qt.QGraphicsItem.ItemIsMovable, True)
            item.setCacheMode(qt.QGraphicsItem.NoCache)
        sys.exit(w.exec())

    w = PyMcaPrintPreview( parent = None, modal=0)
    # we need to initialize a printer to get a proper page
    w.setup()
    w.resize(400,500)
    comment = ""
    for i in range(20):
        comment += "Line number %d: En un lugar de La Mancha de cuyo nombre ...\n"
    w.addPixmap(qt.QPixmap.fromImage(qt.QImage(filename)),
                title=filename,
                comment=comment,
                commentPosition="CENTER")
    w.addImage(qt.QImage(filename), comment=comment, commentPosition="LEFT")
    #w.addImage(qt.QImage(filename))
    w.exec()

def testSimple():
    import sys
    import os
    filename = sys.argv[1]

    w = qt.QWidget()
    l = qt.QVBoxLayout(w)

    button = qt.QPushButton(w)
    button.setText("Print")

    scene = qt.QGraphicsScene()
    pixmapItem = qt.QGraphicsPixmapItem(qt.QPixmap.fromImage(qt.QImage(filename)))
    pixmapItem.setFlag(pixmapItem.ItemIsMovable, True)


    printer = qt.QPrinter(qt.QPrinter.HighResolution)
    printer.setFullPage(True)
    printer.setOutputFileName(os.path.splitext(filename)[0]+".ps")

    page = qt.QGraphicsRectItem(0,0, printer.width(), printer.height())
    scene.setSceneRect(qt.QRectF(0,0, printer.width(), printer.height()))
    scene.addItem(page)
    scene.addItem(pixmapItem)
    view = qt.QGraphicsView(scene)
    view.fitInView(page.rect(), qt.Qt.KeepAspectRatio)
    #view.setSceneRect(
    view.scale(2, 2)
    #page.scale(0.05, 0.05)

    def printFile():
        painter = qt.QPainter(printer)
        scene.render(painter, qt.QRectF(0, 0, printer.width(), printer.height()),
                              qt.QRectF(page.rect().x(), page.rect().y(),
                              page.rect().width(),page.rect().height()),
                              qt.Qt.KeepAspectRatio)
        painter.end()
    l.addWidget(button)
    l.addWidget(view)
    w.resize(300, 600)
    w.show()
    button.clicked.connect(printFile)

##  MAIN
if  __name__ == '__main__':
    a = qt.QApplication(sys.argv)
    testPreview()
    # a.exec()
