# /*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
"""Common PyMca Appliction utilities to be used like this

.. code-block:: python

    # Top of the file
    from PyMca5.PyMcaGui import PyMcaAppInit

    if __name__== '__main__':
        PyMcaAppInit.init_before_app_import()

    ...  # Other imports and definitions


    def main(args):
        app = PyMcaAppInit.create_qt_app(cli_args=args)

        ...  # Main widget

        widget.show()

        # Auto-close Qt application for tests
        if args.cli_test:
            qt.QTimer.singleShot(0, app.quit)

        return app.exec()


    if __name__ == "__main__":
        PyMcaAppInit.init_before_app_create()
        ...
"""

__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import sys
import argparse
import logging

_logger = logging.getLogger(__name__)


def init_before_app_import(qt=True, mp=True, mpl=True, logging=True):
    """
    Call this before importing application dependencies.
    """
    cli_args = _silent_pre_cli_app()

    if mp:
        _init_multiprocessing()

    if logging:
        _init_logging_from_cli(cli_args)

    if qt:
        _init_qt_binding_from_cli(cli_args)

    if mpl:
        _init_matplotlib()


def init_before_app_create(qt=True, hdf5=True):
    """
    Call this after importing application dependencies and before instantiating the application.
    """
    if hdf5:
        _init_hdf5()

    if qt:
        _init_qt_before()


def create_qt_app(cli_args=None):
    from PyMca5.PyMcaGui import PyMcaQt as qt

    app = qt.QApplication.instance()

    if app is None:
        app = qt.QApplication([])
    else:
        _logger.warning("Use existing QApplication")

    _init_qt_after(app, cli_args)

    return app


def _silent_pre_cli_app():
    """
    CLI argument needed before creating the CLI parser.
    """
    try:
        parser = argparse.ArgumentParser(description="PyMca pre-import CLI", add_help=False)
        parser.add_argument("--binding", type=str, default=None)
        parser.add_argument("--qt", type=str, default=None)
        parser.add_argument("--log-level", type=str.upper, default=None)
        args, _ = parser.parse_known_args()
    except Exception:
        args = argparse.Namespace(binding=None, qt=None, logging=None)
    return args


def _init_logging_from_cli(cli_args):
    """
    Call this to log imports.
    """
    if cli_args.log_level:
        logging.basicConfig(level=getattr(logging, cli_args.log_level))


def _init_qt_binding_from_cli(cli_args):
    """
    Call this before importing PyMcaQt.
    """
    if cli_args.binding:
        _init_qt_binding(cli_args.binding)
    elif cli_args.qt:
        _init_qt_version(cli_args.qt)


def _init_qt_binding(binding):
    """
    Call this before importing PyMcaQt.
    """
    binding = binding.lower()
    if binding == "pyqt5":
        import PyQt5.QtCore
    elif binding == "pyside2":
        import PySide2.QtCore
    elif binding == "pyside6":
        import PySide6.QtCore
    elif binding == "pyqt6":
        import PyQt6.QtCore
    else:
        raise ValueError(f"Unsupported Qt binding {binding!r}")


def _init_qt_version(qtversion):
    if qtversion == "3":
        raise NotImplementedError("Qt3 is no longer supported")
    elif qtversion == "4":
        raise NotImplementedError("Qt4 is no longer supported")
    elif qtversion == "5":
        try:
            import PyQt5.QtCore
        except ImportError:
            import PySide2.QtCore
    elif qtversion == "6":
        import PySide6.QtCore
    else:
        raise ValueError(f"Unsupported Qt version {qtversion!r}")


def _init_multiprocessing():
    """
    Call this as soon as possible.
    """
    if getattr(sys, "frozen", False):
        try:
            import multiprocessing

            multiprocessing.freeze_support()
        except Exception:
            _logger.debug("Failed to import multiprocessing or enable freeze support")


def _init_matplotlib():
    """
    Call this before importing matplotlib.
    """
    try:
        # try to import silx prior to importing matplotlib to prevent
        # unnecessary warning
        import silx.gui.plot
    except Exception:
        _logger.debug("Failed to import silx.gui.plot")


def _init_hdf5():
    """
    Call this before importing h5py.
    """
    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    _logger.info("HDF5_USE_FILE_LOCKING set to %s", os.environ["HDF5_USE_FILE_LOCKING"])

    try:
        import hdf5plugin
    except Exception:
        _logger.info("Failed to import hdf5plugin")


def _init_qt_before():
    """
    Call this before instantiating the Qt application.
    """
    pass


def _init_qt_after(app, cli_args):
    """
    Call this after instantiating the Qt application.
    """
    from PyMca5.PyMcaGui import PyMcaQt as qt

    if cli_args and cli_args.binding:
        if cli_args.binding.lower() != qt.BINDING.lower():
            _logger.warning("Qt binding is %r instead of %r", qt.BINDING, cli_args.binding)

    if sys.platform not in ["win32", "darwin"]:
        # Some themes of Ubuntu 16.04 give black tool tips on black background
        try:
            _ttp = app.palette()
            _ttText = _ttp.color(qt.QPalette.ToolTipText).name()
            _ttBorder = _ttText
            _ttBase = _ttp.color(qt.QPalette.ToolTipBase).name()
            app.setStyleSheet("QToolTip { color: %s; background-color: %s; border: 1px solid %s; }" % (_ttText, _ttBase, _ttBorder))
        except Exception:
            app.setStyleSheet("QToolTip { color: #000000; background-color: #fff0cd; border: 1px solid black; }")

    if cli_args.nativefiledialogs is not None:
        from PyMca5.PyMcaCore import PyMcaDirs

        PyMcaDirs.nativeFileDialogs = bool(cli_args.nativefiledialogs)

    # This is the default behavior unless app.setQuitOnLastWindowClosed(False).
    # So do we need this explicitly?
    app.lastWindowClosed.connect(app.quit)

    if not cli_args.cli_test:
        # From now on errors are shown in Qt dialogs.
        sys.excepthook = qt.exceptionHandler
