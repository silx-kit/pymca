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
"""Common CLI utilities to be used like this

.. code-block:: python

    import sys
    import logging
    from PyMca5.PyMcaMisc import CliUtils

    _logger = logging.getLogger(__name__)

    def main(args):
        ...
        return 0

    def build_parser():
        parser = CliUtils.create_parser(description="...")
        ...
        return parser

    if __name__ == "__main__":
        exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
        sys.exit(exit_code)
"""

__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import argparse
import logging
from typing import List, Union

LOGGING_FORMAT = "%(levelname)s: %(message)s"


def cli_main(main_func, parser, args=None, loggers=tuple()):
    """
    Standard CLI entry point wrapper.
    """
    args = parser.parse_args(args)

    # Apply common arguments; handle early exit
    early_exit = _apply_common_arguments(args, loggers=loggers)
    if early_exit is not None:
        return early_exit

    # Run main
    exit_code = main_func(args)

    # Ensure exit code is an int
    if not isinstance(exit_code, int):
        return int(bool(exit_code))
    return exit_code


def create_parser(
    add_common_options=True,
    add_qt_options=False,
    add_backend_options=False,
    default_log_level="WARNING",
    **parser_options
):
    """
    Standard CLI parser with common features.
    """
    parser_options.setdefault(
        "formatter_class", argparse.ArgumentDefaultsHelpFormatter
    )
    parser = argparse.ArgumentParser(**parser_options)

    if add_common_options:
        _add_common_arguments(parser, default_log_level=default_log_level)

    if add_qt_options:
        _add_qt_arguments(parser)

    if add_backend_options:
        _add_backend_argument(parser)

    parser.add_argument("--cli-test", action="store_true", help=argparse.SUPPRESS)

    return parser


def int_or_list(value:Union[str, None]) -> Union[List[int], int, None]:
    """Parse comma-separated string."""
    if value is None:
        return None
    parts = [int(s) for s in value.split(",")]
    if len(parts) == 1:
        return parts[0]
    return parts


def _add_common_arguments(parser, default_log_level):
    """
    Common CLI arguments.
    """
    parser.add_argument("--debug", type=int, default=0, help="Enable debug mode")

    parser.add_argument(
        "--log-level",
        default=default_log_level,
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )

    parser.add_argument("--version", action="store_true", help="Show version and exit")


def _add_backend_argument(parser):
    """
    Plotting backends accepted by `PyMca5.PyMcaGraph.Plot.Plot`
    """
    backend_choices = [
        "matplotlib", "mpl",
        "gl", "opengl",
        "glut",
        "osmesa", "mesa",
        "silx", "silx-mpl", "silxmpl",
        "silx-gl", "silxgl"
    ]

    help = """The plot backend to use:\n
    Matplotlib,
    OpenGL 2.1 (requires appropriate OpenGL drivers), or
    Off-screen Mesa OpenGL software pipeline (requires OSMesa library).
    """

    parser.add_argument(
        "-b", "--backend", type=str, choices=backend_choices, default="mpl", help=help
    )


def _add_qt_arguments(parser):
    """
    Common Qt arguments.
    """
    parser.add_argument("--qt", type=str, default=None, choices=["5","6"], help="Force Qt version")
    parser.add_argument(
        "--binding", type=str, default=None, choices=["pyqt5","pyqt6","pyside2","pyside6"], help="Qt binding"
    )
    parser.add_argument("--nativefiledialogs", type=int, default=None, help="Use native file dialogs")


def _apply_common_arguments(args, loggers=None):
    """
    Apply common arguments and handle early exit.
    """
    if getattr(args, "version", False):
        from pymca import __version__

        print(__version__)
        return 0

    _configure_logging(args, loggers=loggers)
    return None


def _configure_logging(args, loggers=tuple()):
    """
    Local and global logging configuration.
    """
    local_level = getattr(args, "log_level", None)
    debug = getattr(args, "debug", None)

    if loggers:
        for logger in loggers:
            if debug:
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)

    if local_level:
        level = getattr(logging, local_level.upper(), logging.INFO)
    else:
        level = None

    logging.basicConfig(level=level, format=LOGGING_FORMAT)
