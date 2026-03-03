#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2026 European Synchrotron Radiation Facility
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

# Filled by setup
PYMCA_DATA_DIR = r"DATA_DIR_FROM_SETUP"
PYMCA_DOC_DIR = r"DOC_DIR_FROM_SETUP"


def _apply_env_override(env_var_name, current_value):
    """Apply environment override."""
    env_value = os.getenv(env_var_name)
    if env_value is not None:
        current_value = env_value
        if not os.path.exists(current_value):
            raise IOError("%s directory set from environment not found" % current_value)
        else:
            txt = f"WARNING: Taking {env_var_name} from environment.\n"
            txt += "Use it at your own risk."
            print(txt)
    return current_value


def _search_data_dir(start_file):
    """DATA directory search."""
    tmp_dir = os.path.dirname(os.path.abspath(start_file))
    old_tmp_dir = tmp_dir + "dummy"
    basename = "PyMcaData"

    candidate = os.path.join(tmp_dir, "PyMca5", basename)

    while (len(candidate) > 20) and (tmp_dir != old_tmp_dir):
        if os.path.exists(candidate):
            return candidate
        old_tmp_dir = tmp_dir
        tmp_dir = os.path.dirname(tmp_dir)
        candidate = os.path.join(tmp_dir, "PyMca5", basename)

    return None


def _search_doc_dir(start_file):
    """DOC directory search."""
    tmp_dir = os.path.dirname(os.path.abspath(start_file))
    old_tmp_dir = tmp_dir + "dummy"
    basename = "PyMcaData"

    # IMPORTANT: first candidate differs from DATA logic
    candidate = os.path.join(tmp_dir, basename)

    while (len(candidate) > 20) and (tmp_dir != old_tmp_dir):
        if os.path.exists(candidate):
            return candidate
        old_tmp_dir = tmp_dir
        tmp_dir = os.path.dirname(tmp_dir)
        candidate = os.path.join(tmp_dir, "PyMca5", basename)

    return None


PYMCA_DATA_DIR = _apply_env_override("PYMCA_DATA_DIR", PYMCA_DATA_DIR)

if not os.path.exists(PYMCA_DATA_DIR):
    found = _search_data_dir(__file__)
    if found is not None:
        PYMCA_DATA_DIR = found

if not os.path.exists(PYMCA_DATA_DIR):
    raise IOError("%s directory not found" % PYMCA_DATA_DIR)


PYMCA_DOC_DIR = _apply_env_override("PYMCA_DOC_DIR", PYMCA_DOC_DIR)

if not os.path.exists(PYMCA_DOC_DIR):
    found = _search_doc_dir(__file__)
    if found is not None:
        PYMCA_DOC_DIR = found

    if not os.path.exists(PYMCA_DOC_DIR):
        print("Setting PYMCA_DOC_DIR equal to PYMCA_DATA_DIR")
        PYMCA_DOC_DIR = PYMCA_DATA_DIR
