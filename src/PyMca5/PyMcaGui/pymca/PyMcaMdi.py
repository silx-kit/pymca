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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str

QTVERSION = qt.qVersion()

from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
IconDict0 = PyMca_Icons.IconDict0

from PyMca5.PyMcaMisc import CliUtils

_logger = logging.getLogger(__name__)

__version__ = "1.5"


class PyMcaMdi(qt.QMainWindow):
    def __init__(self, parent=None, name="PyMca Mdi", fl=None, options={}):
        qt.QMainWindow.__init__(self, parent)
        self.setWindowTitle(name)
        if fl is None:
            fl = qt.Qt.WA_DeleteOnClose

        if sys.platform.startswith("darwin"):
            self.menuBar().setNativeMenuBar(False)

        self.options= {}
        self.options["FileToolBar"]= options.get("FileToolBar", 1)
        self.options["WinToolBar"] = options.get("WinToolBar", 1)
        self.options["MenuFile"]   = options.get("MenuFile", 1)
        self.options["MenuTools"]  = options.get("MenuTools", 1)
        self.options["MenuWindow"] = options.get("MenuWindow", 1)
        self.options["MenuHelp"]   = options.get("MenuHelp", 1)

        self.splitter = qt.QSplitter(self)
        self.splitter.setOrientation(qt.Qt.Horizontal)
        #self.splitterLayout = qt.QVBoxLayout(self.splitter)
        #self.splitterLayout.setContentsMargins(0, 0, 0, 0)
        #self.splitterLayout.setSpacing(0)

        self.printer= qt.QPrinter()
        self.mdi = qt.QMdiArea(self.splitter)

        if not hasattr(self.mdi, "windowList"):
            # Qt5
            self.mdi.windowList = self.mdi.subWindowList
            self.mdi.activeWindow = self.mdi.activeSubWindow
            self.mdi.tile = self.mdi.tileSubWindows
            self.mdi.cascade = self.mdi.cascadeSubWindows
        else:
            # Qt4
            self.mdi.subWindowList = self.mdi.windowList
            self.mdi.activeSubWindow = self.mdi.activeWindow
            self.mdi.tileSubWindows = self.mdi.tile
            self.mdi.cascadeSubWindows = self.mdi.cascade
        #self.mdi.setBackground(qt.QBrush(qt.QColor(238,234,238)))
        #self.setCentralWidget(self.mdi)
        #self.splitterLayout.addWidget(self.mdi)

        self.setCentralWidget(self.splitter)

        self.splitter.insertWidget(1, self.mdi)
        self.windowMapper = qt.QSignalMapper(self)

        if QTVERSION > '6.0.0':
            self.windowMapper.mappedObject[qt.QObject].connect(self.mdi.setActiveSubWindow)
        else:
            self.windowMapper.mapped[qt.QWidget].connect(self.mdi.setActiveSubWindow)


        #self.setDockEnabled(qt.Qt.DockTop, 0)



        self.initIcons()
        self.createActions()

        self.initMenuBar()
        self.initToolBar()

        self.followActiveWindow= 0

        self.mdi.show()
        #self.resize(600,400)

    def createActions(self):
        #fileopen
        self.actionOpen = qt.QAction(self)
        self.actionOpen.setText(QString("&Open"))
        self.actionOpen.setIcon(self.Icons["fileopen"])
        self.actionOpen.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_O))
        self.actionOpen.triggered[bool].connect(self.onOpen)
        #filesaveas
        self.actionSaveAs = qt.QAction(self)
        self.actionSaveAs.setText(QString("&Save"))
        self.actionSaveAs.setIcon(self.Icons["filesave"])
        self.actionSaveAs.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_S))
        self.actionSaveAs.triggered[bool].connect(self.onSaveAs)

        #filesave
        self.actionSave = qt.QAction(self)
        self.actionSave.setText(QString("Save &Defaults"))
        #self.actionSave.setIcon(self.Icons["filesave"])
        #self.actionSave.setShortcut(qt.Qt.CTRL|qt.Qt.Key_S)
        self.actionSave.triggered[bool].connect(self.onSave)

        #fileprint
        self.actionPrint = qt.QAction(self)
        self.actionPrint.setText(QString("&Print"))
        self.actionPrint.setIcon(self.Icons["fileprint"])
        self.actionPrint.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_P))
        self.actionPrint.triggered[bool].connect(self.onPrint)

        #filequit
        self.actionQuit = qt.QAction(self)
        self.actionQuit.setText(QString("&Quit"))
        #self.actionQuit.setIcon(self.Icons["fileprint"])
        self.actionQuit.setShortcut(qt.QKeySequence(qt.Qt.CTRL|qt.Qt.Key_Q))
        qApp = qt.QApplication.instance()
        self.actionQuit.triggered[bool].connect(qApp.closeAllWindows)

    def initIcons(self):
        self.Icons= {}
        for (name, icon) in IconDict.items():
            pixmap= qt.QPixmap(icon)
            self.Icons[name]= qt.QIcon(pixmap)

    def initToolBar(self):
        if self.options["FileToolBar"]:
            self.fileToolBar= self.addToolBar("filetoolbar")
            self.fileToolBar.addAction(self.actionOpen)
            self.fileToolBar.addAction(self.actionSaveAs)
            self.fileToolBar.addAction(self.actionPrint)
            self.fileToolBar.addSeparator()

        self.onInitToolBar()

        if self.options["WinToolBar"]:
            self.winToolBar = self.addToolBar("wintoolbar")

    def onWinToolMenu(self, idx):
        _logger.debug("onWinToolMenu %d ", idx)
        for midx in self.winToolMenuIndex:
                self.winToolMenu.setItemChecked(midx, midx==idx)
        act= self.winToolMenuIndex.index(idx)
        self.winToolButton.setTextLabel(self.winToolMenuText[act])
        if act==0:
            self.winToolMenuAction= self.windowCascade
        elif act==1:
            self.winToolMenuAction= self.windowTile
        elif act==2:
            self.winToolMenuAction= self.windowHorizontal
        elif act==3:
            self.winToolMenuAction= self.windowVertical
        self.onWinToolAction()

    def onWinToolAction(self):
            apply(self.winToolMenuAction, ())

    #
    # Mdi windows geometry
    #
    def windowCascade(self):
        if self.followActiveWindow:
            self.__disconnectFollow()
        self.mdi.cascade()
        for window in self.mdi.windowList():
            window.resize(0.7*self.mdi.width(),0.7*self.mdi.height())
        if self.followActiveWindow:
            self.__connectFollow()

    def windowTile(self):
        if self.followActiveWindow: self.__disconnectFollow()
        self.mdi.tile()
        if self.followActiveWindow: self.__connectFollow()

    def windowHorizontal(self):
        #if self.followActiveWindow: self.__disconnectFollow()
        if not len(self.mdi.windowList()): return
        windowheight=float(self.mdi.height())/len(self.mdi.windowList())
        i=0
        for window in self.mdi.windowList():
                window.parentWidget().showNormal()
                window.parentWidget().setGeometry(0, int(windowheight*i),
                                        self.mdi.width(),int(windowheight))
                window.parentWidget().raise_()
                i+=1
        self.mdi.update()
        self.update()
        #if self.followActiveWindow: self.__connectFollow()

    def windowVertical(self):
        #if self.followActiveWindow: self.__disconnectFollow()
        if not len(self.mdi.windowList()): return
        windowwidth=float(self.mdi.width())/len(self.mdi.windowList())
        i=0
        for window in self.mdi.windowList():
            window.parentWidget().showNormal()
            window.parentWidget().setGeometry(int(windowwidth*i),0,
                                    int(windowwidth),self.mdi.height())

            window.parentWidget().raise_()
            i+=1
        self.mdi.update()
        self.update()
        #if self.followActiveWindow: self.__connectFollow()

    def windowFullScreen(self):
        if len(self.mdi.windowList()):
            self.mdi.activeWindow().showMaximized()


    def initMenuBar(self):
        if self.options["MenuFile"]:
            #self.menubar = qt.QMenuBar(self)
            self.menuFile= qt.QMenu()
            self.menuFile.addAction(self.actionOpen)
            self.menuFile.addAction(self.actionSaveAs)
            self.menuFile.addAction(self.actionSave)
            self.menuFile.addSeparator()
            self.menuFile.addAction(self.actionPrint)
            self.menuFile.addSeparator()
            self.menuFile.addAction(self.actionQuit)
            self.menuFile.setTitle("&File")
            self.menuBar().addMenu(self.menuFile)
            self.onInitMenuBar(self.menuBar())

        if self.options["MenuTools"]:
            self.menuTools= qt.QMenu()
            #self.menuTools.setCheckable(1)
            self.menuTools.aboutToShow[()].connect(self.menuToolsAboutToShow)
            self.menuTools.setTitle("&Tools")
            self.menuBar().addMenu(self.menuTools)

        if self.options["MenuWindow"]:
            self.menuWindow= qt.QMenu()
            #self.menuWindow.setCheckable(1)
            self.menuWindow.aboutToShow[()].connect(self.menuWindowAboutToShow)
            self.menuWindow.setTitle("&Window")
            self.menuBar().addMenu(self.menuWindow)

        if self.options["MenuHelp"]:
            self.menuHelp= qt.QMenu()
            self.menuHelp.addAction("&About", self.onAbout)
            self.menuHelp.addAction("About &Qt",self.onAboutQt)
            self.menuBar().addSeparator()
            self.menuHelp.setTitle("&Help")
            self.menuBar().addMenu(self.menuHelp)

    def menuWindowAboutToShow(self):
        _logger.debug("menuWindowAboutToShow")
        self.menuWindow.clear()
        if len(self.mdi.windowList())==0:
            return
        self.menuWindow.addAction("&Cascade", self.windowCascade)
        self.menuWindow.addAction("&Tile", self.windowTile)
        self.menuWindow.addAction("&Tile Horizontally", self.windowHorizontal)
        self.menuWindow.addAction("&Tile Vertically", self.windowVertical)
        windows=self.mdi.windowList()
        if len(windows) > 0:
            self.menuWindow.addSeparator()
        num = 0
        for window in windows:
            text = "&%d %s"%(num, str(window.windowTitle()))
            num += 1
            action = self.menuWindow.addAction(text)
            action.setCheckable(True)
            action.setChecked(window == self.mdi.activeWindow())
            action.triggered.connect(self.windowMapper.map)
            self.windowMapper.setMapping(action, window)

    def _windowMapperMapSlot(self):
        return self.windowMapper.map()

    def menuWindowActivated(self, idx=None):
        _logger.debug("menuWindowActivated idx = %s", idx)
        if idx is None:
            return
        if self.menuWindowMap[idx].isHidden():
            self.menuWindowMap[idx].show()
            self.menuWindowMap[idx].raise_()
        self.menuWindowMap[idx].setFocus()

    def __connectFollow(self):
        self.mdi.windowActivated.connect(self.onWindowActivated)

    def __disconnectFollow(self):
        self.mdi.windowActivated.disconnect(self.onWindowActivated)

    def setFollowActiveWindow(self, follow):
        if follow != self.followActiveWindow:
            if not follow:
                self.__disconnectFollow()
            else:
                self.__connectFollow()
            self.followActiveWindow= follow

    def onWindowActivated(self, win):
        _logger.info("Window activated")
        pass

    #
    # Dock windows
    #
    def isCustomizable(self):
        nb= 0
        for win in self.dockWindows():
                nb += isinstance(win, DockWindow)
        return (nb>0)

    def customize(self, *args):
        dg= DockPlaceDialog(self, window=self, title="Tool Places")
        dg.exec_loop()

    #
    # Menus customization
    #
    def onInitMenuBar(self, menubar):
        pass

    def onInitFileToolBar(self, toolbar):
        pass

    def onInitToolBar(self):
        pass

    def onInitWinToolBar(self, toolbar):
        pass

    def menuToolsAboutToShow(self):
        _logger.debug("menuToolsAboutToShow")
        self.menuTools.clear()
        self.menuToolsMap= {}
        """
        for win in self.dockWindows():
            if isinstance(win, DockWindow):
                    idx= self.menuTools.insertItem("%s"%str(win.caption()), self.menuToolsActivated)
                    self.menuToolsMap[idx]= win
                    self.menuTools.setItemChecked(idx, not win.isHidden())
        """
        if len(self.menuToolsMap.keys()):
            self.menuTools.insertSeparator()
            self.menuTools.insertItem("Customize", self.customize)

    def menuToolsActivated(self, idx):
        _logger.debug("menuToolsActivated idx = %s", idx)
        if self.menuTools.isItemChecked(idx):
            self.menuToolsMap[idx].hide()
        else:
            self.menuToolsMap[idx].show()



    #
    # Menus customization
    #
    def onInitMenuBar(self, menubar):
        pass

    def onInitFileToolBar(self, toolbar):
        pass

    def onInitToolBar(self):
        pass

    def onInitWinToolBar(self, toolbar):
        pass

    #
    # Menus callback
    #
    def onAboutQt(self):
        qt.QMessageBox.aboutQt(self, "About Qt")

    def onAbout(self):
        qt.QMessageBox.about(self, "MDI",
                "MDI Application Framework\nVersion: "+__version__)

    def onOpen(self):
        qt.QMessageBox.about(self, "Open", "Not implemented")

    def onSave(self):
        qt.QMessageBox.about(self, "Save", "Not implemented")

    def onSaveAs(self):
        qt.QMessageBox.about(self, "SaveAs", "Not implemented")

    def onPrint(self):
        qt.QMessageBox.about(self, "Print", "Not implemented")


def main(args):
    # Qt application
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    # Extract optional keyword args
    kw = {}
    if args.spec:
        kw["spec"] = args.spec
    if args.shm:
        kw["shm"] = args.shm

    # Launch PyMcaMdi
    demo = PyMcaMdi(**kw)
    demo.show()

    # If running in test mode, quit immediately
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="PyMcaMdi launcher", add_qt_options=True)

    parser.add_argument("--spec", type=str, default=None, help="Optional spec file")
    parser.add_argument("--shm", type=str, default=None, help="Optional shared memory")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
