#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
import logging
import os
import sys
import time
from . import PyMcaLogo

_logger = logging.getLogger(__name__)

class HtmlIndex(object):
    def __init__(self, htmldir):
        if htmldir is None:
            htmldir = "/tmp/HTML"
        self.htmldir = htmldir

    def isHtml(self, x):
        if len(x) < 5:
            return 0
        if x[-5:] == ".html":
            return 1

    def isHtmlDir(self, x):
        if len(x) < 7:
            return 0
        if x[-7:] == "HTMLDIR":
            return 1

    def getHeader(self,addlink=None):
        link= [ ['http://www.esrf.fr', 'ESRF home'],
                ['http://www.esrf.fr/computing/bliss/', 'BLISS home'],
          ]
        if addlink is not None:
            for item in addlink:
                link.append(item)
        text =""
        text+= "<HTML>"
        text+= "<HEAD>"
        text+= "<TITLE>PyMCA : Advanced Fit Results</TITLE>"
        text+= "</HEAD>"
        text+= "<BODY TEXT=#000000 BGCOLOR=#FFFFFF ALINK=#ff6600 LINK=#0000cc VLINK=#0000cc marginwidth=10 marginheight=10  topmargin=10 leftmargin=10>"
        text+= "<CENTER>"
        text+= "<TABLE WIDTH=100%% border=0 Height=70>"
        text+= "  <TR>"
        text+= "    <TD><Font Size=5 Color=#0000cc>"
        text+= "        <b>PyMCA : Advanced Fit Results</b></Font>"
        text+= "    </td>"
        text+= "    <td rowspan=2 ALIGN=RIGHT VALIGN=bottom>"
        text+= "        <a HREF=""http://www.esrf.fr/"">"
        logofile = self.htmldir + "/" + "PyMcaLogo.png"
        if not os.path.exists(logofile):
            try:
                import qt
                pixmap = qt.QPixmap(PyMcaLogo.PyMcaLogo)
                pixmap.save(logofile,"PNG")
            except Exception:
                pass
        text+= "        <img SRC=%s ALT=""ESRF home"" WIDTH=55 HEIGHT=68 BORDER=0></a>" % "PyMcaLogo.png"
        text+= "    </td>"
        text+= "  </tr>"
        text+= "  <tr>"
        text+= "     <td width=100%%  VALIGN=bottom>"
        text+= "        <TABLE BORDER=0 CELLPADDING=0 CELLSPACING=0 WIDTH=100%%>"
        text+= "          <TR>"
        text+= "            <TD WIDTH=100%% BGCOLOR=#ee22aa HEIGHT=17  ALIGN=LEFT VALIGN=middle>"
        text+= "            <FONT color=#000000>&nbsp;"
        for name in link:
            text+= "|&nbsp;&nbsp;<A STYLE=""color: #FFFFFF"" HREF=""%s"">%s</a>&nbsp;&nbsp;"%(tuple(name))
        text+= "            </FONT>"
        text+= "            </TD>"
        text+= "          </TR>"
        text+= "        </TABLE>"
        text+= "     </td>"
        text+= "  </tr>"
        text+= "  <tr>"
        text+= "     <td colspan=2 height=5><spacer type=block height=10 width=0>"
        text+= "     </td>"
        text+= "  </tr>"
        text+= "</table>"
        text+= "</center>"
        return text

    def getFooter(self):
        now = time.time()
        text =""
        text+= "<center>"
        text+= "<table width=100%% border=0 cellspacing=0 cellpadding=0>"
        text+= "    <tr><td colspan=2 height=10><spacer type=block height=10 width=0></td></tr>"
        text+= "    <tr><td colspan=2 bgcolor=#cc0066 height=5><spacer type=block height=5 width=0></td></tr>"
        text+= "    <tr><td colspan=2 height=5><spacer type=block height=5 width=0></td></tr>"
        text+= "    <TR>"
        text+= "        <TD><FONT size=1 >created:  %s</font></TD>" % time.ctime(now)
        text+= "        <TD ALIGN=RIGHT><FONT size=1 >last modified: %s by" % time.ctime(now)
        #text+= "        <A STYLE=""color: #0000cc"" HREF=""mailto:papillon@esrf.fr"">papillon@esrf.fr</A></FONT></TD>"
        if sys.platform == 'win32':
            try:
                user = os.environ['USERNAME']
                text+= "        <A STYLE=""color: #0000cc"">%s</A></FONT></TD>" % user
            except Exception:
                text +="</FONT></TD>"
        else:
            try:
                user = os.getlogin()
                text+= "        <A STYLE=""color: #0000cc"">%s</A></FONT></TD>" % user
            except Exception:
                text +="</FONT></TD>"
        text+= "    </TR>"
        text+= "</TABLE>"
        text+= "</center>"
        text+= "</BODY>"
        text+= "</HTML>"
        return text

    def getBody(self, htmldir=None):
        if htmldir is None:htmldir = self.htmldir
        dirlist  = filter(self.isHtmlDir, os.listdir(htmldir))
        filelist = []
        for directory in dirlist:
            fulldir = os.path.join(self.htmldir,directory)
            filelist += filter(self.isHtml, os.listdir(fulldir))


        #I have a list of directories and of indexes
        for directory in dirlist:
            fulldir = os.path.join(htmldir,directory)
            index   = os.path.join(fulldir,"index.html")
            if os.path.exists(index):
                try:
                    os.remove(index)
                except Exception:
                    _logger.error("getBody cannot delete file %s", index)
                    continue

    def _getHtmlFileList(self, directory):
        return filter(self.isHtml, os.listdir(directory))

    def _getHtmlDirList(self, directory):
        return filter(self.isHtmlDir, os.listdir(directory))

    def buildIndex(self, directory=None):
        if directory is None:
            directory = self.htmldir
        index = os.path.join(directory, "index.html")
        if os.path.exists(index):
            try:
                os.remove(index)
            except Exception:
                _logger.error("buildindex cannot delete file %s", index)
                return
        filelist = self._getHtmlFileList(directory)
        text = ""
        text += self.getHeader()
        for ffile in filelist:
            text +="<a href=""%s"">%s</a><BR>" % (ffile, ffile.split(".html")[0])
        text += self.getFooter()
        fformat = 'w'
        ffile = open(index, fformat)
        ffile.write(text)
        ffile.close()

    def buildRecursiveIndex(self, directory=None):
        if directory is None:
            directory = self.htmldir
        index = os.path.join(directory, "index.html")
        if os.path.exists(index):
            try:
                os.remove(index)
            except Exception:
                _logger.error("cannot delete file %s", index)
                return
        directorylist = self._getHtmlDirList(directory)
        text = ""
        text += self.getHeader()
        for ffile in directorylist:
            fulldir = os.path.join(directory, ffile)
            self.buildIndex(fulldir)
            fileroot = ffile.split('_HTMLDIR')[0]
            link     = "./" + ffile + "/index.html"
            text +="<a href=""%s"">%s</a><BR>" % (link, fileroot)
        text += self.getFooter()
        fformat = 'w'
        ffile = open(index, fformat)
        ffile.write(text)
        ffile.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        a = HtmlIndex(sys.argv[1])
    else:
        print("Trying /tmp/HTML as input directory")
        a = HtmlIndex('/tmp/HTML')
    a.buildRecursiveIndex()
