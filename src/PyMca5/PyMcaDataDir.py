#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2019 European Synchrotron Radiation Facility
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
# this will be filled by the setup
PYMCA_DATA_DIR = r'DATA_DIR_FROM_SETUP'
# This is to be filled by the setup
PYMCA_DOC_DIR = r'DOC_DIR_FROM_SETUP'

PYMCA_DATA_DIR_ENV = os.getenv("PYMCA_DATA_DIR")
if PYMCA_DATA_DIR_ENV is not None:
    PYMCA_DATA_DIR = PYMCA_DATA_DIR_ENV
    if not os.path.exists(PYMCA_DATA_DIR):
        raise IOError('%s directory set from environment not found' % \
                      PYMCA_DATA_DIR)
    else:
        txt = "WARNING: Taking PYMCA_DATA_DIR from environment.\n"
        txt += "Use it at your own risk."
        print(txt)


# this is used in build directory
if not os.path.isabs(PYMCA_DATA_DIR) or not os.path.exists(PYMCA_DATA_DIR):
    tmp_dir = os.path.dirname(os.path.abspath(__file__))
    old_tmp_dir = tmp_dir + "dummy"
    basename = "PyMcaData"
    PYMCA_DATA_DIR_BUILD = os.path.join(tmp_dir, "PyMca5", basename)
    while (len(PYMCA_DATA_DIR_BUILD) > 20) and (tmp_dir != old_tmp_dir):
        if os.path.exists(PYMCA_DATA_DIR_BUILD):
            PYMCA_DATA_DIR = PYMCA_DATA_DIR_BUILD
            break
        old_tmp_dir = tmp_dir
        tmp_dir = os.path.dirname(tmp_dir)
        PYMCA_DATA_DIR_BUILD = os.path.join(tmp_dir, "PyMca5", basename)

if not os.path.exists(PYMCA_DATA_DIR):
    raise IOError('%s directory not found' % PYMCA_DATA_DIR)

PYMCA_DATA_DIR = os.path.abspath(PYMCA_DATA_DIR)

PYMCA_DOC_DIR_ENV = os.getenv("PYMCA_DOC_DIR")
if PYMCA_DOC_DIR_ENV is not None:
    PYMCA_DOC_DIR = PYMCA_DOC_DIR_ENV
    if not os.path.exists(PYMCA_DOC_DIR):
        raise IOError('%s directory set from environent not found' % \
                          PYMCA_DATA_DIR)
    else:
        txt = "WARNING: Taking PYMCA_DOC_DIR from environment.\n"
        txt += "Use it at your own risk."
        print(txt)

# do the same for the directory containing HTML files
if not os.path.isabs(PYMCA_DOC_DIR) or not os.path.exists(PYMCA_DOC_DIR):
    tmp_dir = os.path.dirname(os.path.abspath(__file__))
    old_tmp_dir = tmp_dir + "dummy"
    basename = "PyMcaData"
    PYMCA_DOC_DIR = os.path.join(tmp_dir,basename)
    while (len(PYMCA_DOC_DIR) > 20) and (tmp_dir != old_tmp_dir):
        if os.path.exists(PYMCA_DOC_DIR):
            break
        old_tmp_dir = tmp_dir
        tmp_dir = os.path.dirname(tmp_dir)
        PYMCA_DOC_DIR = os.path.join(tmp_dir, "PyMca5", basename)
    if not os.path.exists(PYMCA_DOC_DIR):
        print("Setting PYMCA_DOC_DIR equal to PYMCA_DATA_DIR")
        PYMCA_DOC_DIR = PYMCA_DATA_DIR

PYMCA_DOC_DIR = os.path.abspath(PYMCA_DOC_DIR)
