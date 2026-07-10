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
import os
import sys
import traceback
import logging

"""
This module simplifies writing code that has to deal with with PySideX and PyQtX.

"""

_logger = logging.getLogger(__name__)

BINDING = None
"""The name of the Qt binding in use: PyQt5, PySide6, PySide2, PyQt6"""

HAS_SVG = False
"""True if Qt provides support for Scalable Vector Graphics (QtSVG)."""

HAS_OPENGL = False
"""True if Qt provides support for OpenGL (QtOpenGL)."""

# force cx_freeze to consider sip among the modules to add
# to the binary packages
if 'PySide2.QtCore' in sys.modules:
    BINDING = 'PySide2'

elif 'PySide6.QtCore' in sys.modules:
    BINDING = 'PySide6'

elif 'PyQt5.QtCore' in sys.modules:
    BINDING = 'PyQt5'

elif 'PyQt6.QtCore' in sys.modules:
    BINDING = 'PyQt6'

elif hasattr(sys, 'argv') and ('--binding=PySide2' in sys.argv):
    BINDING = 'PySide2'

elif hasattr(sys, 'argv') and ('--binding=PySide6' in sys.argv):
    # argv might not be defined for embedded python (e.g., in Qt designer)
    BINDING = 'PySide6'
else:
    BINDING = os.environ.get("QT_API", None)

if BINDING is None: # Try the different bindings
    try:
        import PyQt5.QtCore
        BINDING = "PyQt5"
    except ImportError:
        if "PyQt5" in sys.modules:
            del sys.modules["PyQt5"]
        try:
            import PySide6.QtCore
            BINDING = "PySide6"
        except ImportError:
            if "PySide6" in sys.modules:
                del sys.modules["PySide6"]
            try:
                import PyQt6.QtCore
                BINDING = "PyQt6"
            except ImportError:
                if 'PyQt6' in sys.modules:
                    del sys.modules["PyQt6"]
                try:
                    import PySide2.QtCore  # noqa
                    BINDING = "PySide2"
                except ImportError:
                    if 'PySide2' in sys.modules:
                        del sys.modules["PySide2"]
                    raise ImportError(
                    'No Qt wrapper found. Install PyQt5, PySide6 or PyQt6.')

    _logger.info("BINDING set to %s" % BINDING)

if BINDING.lower() == "pyqt5":
    BINDING = "PyQt5"
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtPrintSupport import *

    try:
        from PyQt5.QtOpenGL import *
        HAS_OPENGL = True
    except Exception:
        _logger.info("PyQt5.QtOpenGL not available")

    try:
        from PyQt5.QtSvg import *
        HAS_SVG = True
    except Exception:
        _logger.info("PyQt5.QtSVG not available")

    Signal = pyqtSignal
    Slot = pyqtSlot

elif BINDING.lower() == "pyside2":
    BINDING = "PySide2"
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtPrintSupport import *

    try:
        from PySide2.QtOpenGL import *
        HAS_OPENGL = True
    except Exception:
        _logger.info("PySide2.QtOpenGL not available")


    try:
        from PySide2.QtSvg import *
        HAS_SVG = True
    except Exception:
        _logger.info("PySide2.QtSVG not available")
    pyqtSignal = Signal
    pyqtSlot = Slot

    # Qt6 compatibility:
    # with PySide2 `exec` method has a special behavior
    class _ExecMixIn:
        """Mix-in class providind `exec` compatibility"""
        def exec(self, *args, **kwargs):
            return super().exec_(*args, **kwargs)

    # QtWidgets
    QApplication.exec = QApplication.exec_
    class QColorDialog(_ExecMixIn, QColorDialog): pass
    class QDialog(_ExecMixIn, QDialog): pass
    class QErrorMessage(_ExecMixIn, QErrorMessage): pass
    class QFileDialog(_ExecMixIn, QFileDialog): pass
    class QFontDialog(_ExecMixIn, QFontDialog): pass
    class QInputDialog(_ExecMixIn, QInputDialog): pass
    class QMenu(_ExecMixIn, QMenu): pass
    class QMessageBox(_ExecMixIn, QMessageBox): pass
    class QProgressDialog(_ExecMixIn, QProgressDialog): pass
    #QtCore
    class QCoreApplication(_ExecMixIn, QCoreApplication): pass
    class QEventLoop(_ExecMixIn, QEventLoop): pass
    if hasattr(QTextStreamManipulator, "exec_"):
        # exec_ only wrapped in PySide2 and NOT in PyQt5
        class QTextStreamManipulator(_ExecMixIn, QTextStreamManipulator): pass
    class QThread(_ExecMixIn, QThread): pass

    # workaround not finding the Qt platform plugin "windows" in "" error
    # when creating a QApplication
    if sys.platform.startswith("win")and QApplication.instance() is None:
        _platform_plugin_path = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH",
                                                 None)
        if _platform_plugin_path:
            if not os.path.exists(_platform_plugin_path):
                _logger.info("QT_QPA_PLATFORM_PLUGIN_PATH <%s> ignored" % \
                             _platform_plugin_path)
                _platform_plugin_path = None
        if not _platform_plugin_path:
            import PySide2
            _platform_plugin_path = os.path.join( \
                            os.path.dirname(PySide2.__file__),
                            "plugins", "platforms")
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = \
                                                _platform_plugin_path
            _logger.info("QT_QPA_PLATFORM_PLUGIN_PATH set to <%s>" % \
                             _platform_plugin_path)
elif BINDING.lower() == 'pyside6':
    _logger.debug('Using PySide6 bindings')
    BINDING = "PySide6"
    import PySide6

    from PySide6.QtCore import *  # noqa
    from PySide6.QtGui import *  # noqa
    from PySide6.QtWidgets import *  # noqa
    from PySide6.QtPrintSupport import *  # noqa

    try:
        from PySide6.QtOpenGL import *  # noqa
        from PySide6.QtOpenGLWidgets import QOpenGLWidget  # noqa
    except ImportError:
        _logger.info("PySide6.QtOpenGL not available")
        HAS_OPENGL = False
    else:
        HAS_OPENGL = True

    try:
        from PySide6.QtSvg import *  # noqa
        # In Qt6 QGraphicsSvgItem moved from QtSvg to QtSvgWidgets
        from PySide6.QtSvgWidgets import *  # noqa
    except ImportError:
        _logger.info("PySide6.QtSvg not available")
        HAS_SVG = False
    else:
        HAS_SVG = True

    pyqtSignal = Signal

    # use a (bad) replacement for QDesktopWidget
    class QDesktopWidget:
        def height(self):
            _logger.info("Using obsolete QDesktopWidget class")
            screen = QApplication.instance().primaryScreen() 
            return screen.availableGeometry().height()


        def width(self):
            _logger.info("Using obsolete QDesktopWidget class")
            screen = QApplication.instance().primaryScreen() 
            return screen.availableGeometry().width()

elif BINDING.lower() == 'pyqt6':
    _logger.debug('Using PyQt6 bindings')
    BINDING = "PyQt6"
    import enum
    from PyQt6 import QtCore
    if QtCore.PYQT_VERSION < int("0x60300", 16):
        raise RuntimeError(
            "PyQt6 v%s is not supported, please upgrade it." % QtCore.PYQT_VERSION_STR
        )

    # Monkey-patch module to expose enum values for compatibility
    # All Qt modules loaded here should be patched.
    import PyQt6.sip
    def patch_enums(*modules):
        """Patch PyQt6 modules to provide backward compatibility of enum values

        :param modules: Modules to patch (e.g., PyQt6.QtCore).
        """
        for module in modules:
            for clsName in dir(module):
                cls = getattr(module, clsName, None)
                if isinstance(cls, PyQt6.sip.wrappertype) and clsName.startswith('Q'):
                    for qenumName in dir(cls):
                        if qenumName[0].isupper():
                            qenum = getattr(cls, qenumName, None)
                            if isinstance(qenum, enum.EnumMeta):
                                if qenum is getattr(cls.__mro__[1], qenumName, None):
                                    continue  # Only handle it once
                                for item in qenum:
                                    # Special cases to avoid overrides and mimic PySide6
                                    if clsName == 'QColorSpace' and qenumName in (
                                            'Primaries', 'TransferFunction'):
                                        break
                                    if qenumName in ('DeviceType', 'PointerType'):
                                        break

                                    setattr(cls, item.name, item)

    from PyQt6 import QtGui, QtWidgets, QtPrintSupport, QtOpenGL, QtSvg
    from PyQt6 import QtTest as _QtTest

    patch_enums(
        QtCore, QtGui, QtWidgets, QtPrintSupport, QtOpenGL, QtSvg, _QtTest)

    from PyQt6.QtCore import *  # noqa
    from PyQt6.QtGui import *  # noqa
    from PyQt6.QtWidgets import *  # noqa
    from PyQt6.QtPrintSupport import *  # noqa

    try:
        from PyQt6.QtOpenGL import *  # noqa
        from PyQt6.QtOpenGLWidgets import QOpenGLWidget  # noqa
    except ImportError:
        _logger.info("PyQt6's QtOpenGL or QtOpenGLWidgets not available")
        HAS_OPENGL = False
    else:
        HAS_OPENGL = True

    try:
        from PyQt6.QtSvg import *  # noqa
        # In Qt6 QGraphicsSvgItem moved from QtSvg to QtSvgWidgets
        from PyQt6.QtSvgWidgets import *  # noqa
    except ImportError:
        _logger.info("PyQt6.QtSvg not available")
        HAS_SVG = False
    else:
        HAS_SVG = True
    
    Signal = pyqtSignal

    Property = pyqtProperty

    Slot = pyqtSlot

    if not hasattr(Qt, "AlignCenter"):
        Qt.AlignLeft = Qt.AlignmentFlag.AlignLeft
        Qt.AlignRight = Qt.AlignmentFlag.AlignRight
        Qt.AlignHCenter = Qt.AlignmentFlag.AlignHCenter
        Qt.AlignJustify = Qt.AlignmentFlag.AlignJustify
        Qt.AlignTop = Qt.AlignmentFlag.AlignTop
        Qt.AlignBottom = Qt.AlignmentFlag.AlignBottom
        Qt.AlignVCenter = Qt.AlignmentFlag.AlignVCenter
        Qt.AlignBaseline = Qt.AlignmentFlag.AlignBaseline
        Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
        Qt.AlignAbsolute = Qt.AlignmentFlag.AlignAbsolute

    if not hasattr(Qt, "NoDockWidgetArea"):
        Qt.LeftDockWidgetArea = Qt.DockWidgetArea.LeftDockWidgetArea
        Qt.RightDockWidgetArea = Qt.DockWidgetArea.RightDockWidgetArea
        Qt.TopDockWidgetArea = Qt.DockWidgetArea.TopDockWidgetArea
        Qt.BottomDockWidgetArea = Qt.DockWidgetArea.BottomDockWidgetArea
        Qt.AllDockWidgetAreas = Qt.DockWidgetArea.AllDockWidgetAreas
        Qt.NoDockWidgetArea = Qt.DockWidgetArea.NoDockWidgetArea

    if not hasattr(Qt, "Widget"):
        Qt.Widget = Qt.WindowType.Widget
        Qt.Window = Qt.WindowType.Window
        Qt.Dialog = Qt.WindowType.Dialog
        Qt.Drawer = Qt.WindowType.Drawer
        Qt.Popup = Qt.WindowType.Popup
        Qt.Tool = Qt.WindowType.Tool
        Qt.ToolTip = Qt.WindowType.ToolTip
        Qt.SplashScreen = Qt.WindowType.SplashScreen
        Qt.Subwindow = Qt.WindowType.SubWindow
        Qt.ForeignWindow = Qt.WindowType.ForeignWindow
        Qt.CoverWindow = Qt.WindowType.CoverWindow

    if not hasattr(Qt, "StrongFocus"):
        Qt.TabFocus = Qt.FocusPolicy.TabFocus
        Qt.ClickFocus = Qt.FocusPolicy.ClickFocus
        Qt.StrongFocus = Qt.FocusPolicy.StrongFocus
        Qt.WheelFocus = Qt.FocusPolicy.WheelFocus
        Qt.NoFocus = Qt.FocusPolicy.NoFocus

    if not hasattr(QAbstractItemView, "NoEditTriggers"):
        QAbstractItemView.NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers
        QAbstractItemView.CurrentChanged = QAbstractItemView.EditTrigger.CurrentChanged
        QAbstractItemView.DoubleClicked = QAbstractItemView.EditTrigger.DoubleClicked
        QAbstractItemView.SelectedClicked = QAbstractItemView.EditTrigger.SelectedClicked
        QAbstractItemView.AnyKeyPressed = QAbstractItemView.EditTrigger.AnyKeyPressed
        QAbstractItemView.AllEditTriggers = QAbstractItemView.EditTrigger.AllEditTriggers

    if not hasattr(QPalette, "Normal"):
        if hasattr(QPalette, "Active"):
            QPalette.Normal = QPalette.Active
        else:
            QPalette.Disabled = QPalette.ColorGroup.Disabled
            QPalette.Active = QPalette.ColorGroup.Active
            QPalette.Inactive = QPalette.ColorGroup.Inactive
            QPalette.Normal = QPalette.ColorGroup.Normal

            QPalette.Window = QPalette.ColorRole.Window
            QPalette.WindowText = QPalette.ColorRole.WindowText
            QPalette.Base = QPalette.ColorRole.Base
            QPalette.AlternateBase = QPalette.ColorRole.AlternateBase
            QPalette.ToolTipBase = QPalette.ColorRole.ToolTipBase
            QPalette.ToolTipText = QPalette.ColorRole.ToolTipText
            QPalette.PlaceholderText = QPalette.ColorRole.PlaceholderText
            QPalette.Text = QPalette.ColorRole.Text
            QPalette.Button = QPalette.ColorRole.Button
            QPalette.ButtonText = QPalette.ColorRole.ButtonText
            QPalette.BrightText = QPalette.ColorRole.BrightText
            QPalette.Highlight = QPalette.ColorRole.Highlight
            QPalette.Shadow = QPalette.ColorRole.Shadow
            QPalette.Midlight = QPalette.ColorRole.Midlight
            QPalette.Link = QPalette.ColorRole.Link

        try:
            from silx.gui import qt as SilxQt
            if not hasattr(SilxQt.QPalette, "Normal"):
                if hasattr(SilxQt.QPalette, "Active"):
                    SilxQt.QPalette.Normal = SilxQt.QPalette.Active
                else:
                    SilxQt.QPalette.Disabled = SilxQt.QPalette.ColorGroup.Disabled
                    SilxQt.QPalette.Active = SilxQt.QPalette.ColorGroup.Active
                    SilxQt.QPalette.Inactive = SilxQt.QPalette.ColorGroup.Inactive
                    SilxQt.QPalette.Normal = SilxQt.QPalette.ColorGroup.Normal

                    SilxQt.QPalette.Window = SilxQt.QPalette.ColorRole.Window
                    SilxQt.QPalette.WindowText = SilxQt.QPalette.ColorRole.WindowText
                    SilxQt.QPalette.Base = SilxQt.QPalette.ColorRole.Base
                    SilxQt.QPalette.AlternateBase = SilxQt.QPalette.ColorRole.AlternateBase
                    SilxQt.QPalette.ToolTipBase = SilxQt.QPalette.ColorRole.ToolTipBase
                    SilxQt.QPalette.ToolTipText = SilxQt.QPalette.ColorRole.ToolTipText
                    SilxQt.QPalette.PlaceholderText = SilxQt.QPalette.ColorRole.PlaceholderText
                    SilxQt.QPalette.Text = SilxQt.QPalette.ColorRole.Text
                    SilxQt.QPalette.Button = SilxQt.QPalette.ColorRole.Button
                    SilxQt.QPalette.ButtonText = SilxQt.QPalette.ColorRole.ButtonText
                    SilxQt.QPalette.BrightText = SilxQt.QPalette.ColorRole.BrightText
                    SilxQt.QPalette.Highlight = SilxQt.QPalette.ColorRole.Highlight
                    SilxQt.QPalette.Shadow = SilxQt.QPalette.ColorRole.Shadow
                    SilxQt.QPalette.Midlight = SilxQt.QPalette.ColorRole.Midlight
                    SilxQt.QPalette.Link = SilxQt.QPalette.ColorRole.Link
        except Exception:
            _logger.info("Exception patching silx")
            pass

    # use a (bad) replacement for QDesktopWidget
    class QDesktopWidget:
        def height(self):
            _logger.info("Using obsolete QDesktopWidget class")
            screen = QApplication.instance().primaryScreen() 
            return screen.availableGeometry().height()


        def width(self):
            _logger.info("Using obsolete QDesktopWidget class")
            screen = QApplication.instance().primaryScreen() 
            return screen.availableGeometry().width()

    # Disable PyQt6 cooperative multi-inheritance since other bindings do not provide it.
    # See https://www.riverbankcomputing.com/static/Docs/PyQt6/multiinheritance.html?highlight=inheritance
    class _Foo(object): pass
    class QObject(QObject, _Foo): pass

else:
    raise ImportError('No Qt wrapper found. Install one of PyQt5, PySide6, PyQt6')

_logger.info("PyMcaQt.BINDING set to %s" % BINDING)

# provide a exception handler but not implement it by default
def exceptionHandler(type_, value, trace):
    _logger.error("%s %s %s", type_, value, ''.join(traceback.format_tb(trace)))
    if QApplication.instance():
        msg = QMessageBox()
        msg.setWindowTitle("Unhandled exception")
        msg.setIcon(QMessageBox.Critical)
        msg.setInformativeText("%s %s\nPlease report details" % (type_, value))
        msg.setDetailedText(("%s " % value) + \
                            ''.join(traceback.format_tb(trace)))
        msg.raise_()
        msg.exec()

# Overwrite the QFileDialog to make sure that by default it
# returns non-native dialogs as it was the traditional behavior of Qt
_QFileDialog = QFileDialog
class QFileDialog(_QFileDialog):
    def __init__(self, *args, **kwargs):
        try:
            _QFileDialog.__init__(self, *args, **kwargs)
        except Exception:
            # not all versions support kwargs
            _QFileDialog.__init__(self, *args)
        try:
            self.setOptions(_QFileDialog.DontUseNativeDialog)
        except Exception:
            print("WARNING: Cannot force default QFileDialog behavior")

class HorizontalSpacer(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                          QSizePolicy.Fixed))

class VerticalSpacer(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                          QSizePolicy.Expanding))
_QToolButton = QToolButton
class QToolButton(_QToolButton):
    def __init__(self, *var, **kw):
        _QToolButton.__init__(self, *var, **kw)
        if "silx" in sys.modules:
            try:
                # this should be set via a user accessible parameter
                tb = QToolBar()
                size = tb.iconSize()
                if (size.width() > 15) and (size.height() > 15):
                    self.setIconSize(size)
            except Exception:
                print("unable to setIconSize")
                pass

safe_str = str

if BINDING.lower()=="pyside2":
    _logger = logging.warning("PyMca PySide2 support deprecated and not reliable")

class CLocaleQDoubleValidator(QDoubleValidator):
    """
    A QDoubleValidator using C locale
    """
    def __init__(self, *var):
        QDoubleValidator.__init__(self, *var)
        self._localeHolder = QLocale("C")
        self.setLocale(self._localeHolder)
