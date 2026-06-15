#/*##########################################################################
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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import sys
import time
MATPLOTLIB = True
from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()

#this is installation dependent I guess
from matplotlib import __version__ as matplotlib_version
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
MATPLOTLIB = True

from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaCore import PyMcaLogo
from PyMca5.PyMcaPhysics.xrf import ConcentrationsTool
ConcentrationsConversion = ConcentrationsTool.ConcentrationsConversion

class QtMcaAdvancedFitReport:
    def __init__(self, fitfile = None, outfile = None, outdir = None,
                    sourcename = None,
                    selection = None,
                    fitresult = None,htmltext=None,
                    concentrations=None, table = None,
                    plotdict=None):

        self.concentrations = concentrations
        self.concentrationsConversion = ConcentrationsConversion()
        if table is None: table = 2
        self.tableFlag = table
        if fitfile is not None:
            #generate output from fit result file
            self.fitfile = fitfile
            self.outfile = outfile
            self.outdir  = outdir
            self.generateReportFromFitFile()
        else:
            #generate output from fitresult INCLUDING fit file
            self.fitfile = fitfile
            self.outfile = outfile
            self.outdir  = outdir
            self.sourcename=sourcename
            self.selection =selection
            self.fitresult =fitresult
            if self.outfile is None:
                if selection is not None:
                    self.outfile = selection
            if (self.outfile is None) or (self.outfile == 'Unknown Origin'):
                if sourcename is not None:
                    self.outfile = os.path.basename(sourcename)
        self.outfile = self.outfile.replace(" ","_")
        self.outfile = self.outfile.replace("/","_over_")
        self.graph = None
        if htmltext is None:
            htmltext={}
        self.otherhtmltext=htmltext
        if plotdict is None:
            self.plotDict = {'logy':None,
                             'xmin':None,
                             'xmax':None,
                             'ymin':None,
                             'ymax':None}
        else:
            self.plotDict = plotdict

    def writeReport(self,text=None):
        if len(self.outfile) > 5:
            if self.outfile[-5:] != ".html":
                outfile = os.path.join(self.outdir, self.outfile+".html")
            else:
                outfile = os.path.join(self.outdir, self.outfile)
        else:
            outfile = os.path.join(self.outdir, self.outfile+".html")
        try:
            os.remove(outfile)
        except Exception:
            pass
        concentrationsfile = outfile[:-5]+"_concentrations.txt"
        try:
            os.remove(concentrationsfile)
        except Exception:
            pass
        if text is None:
            text = self.getText()
        f=open(outfile,"w")
        f.write(text)
        f.close()
        if len(self._concentrationsTextASCII) > 1:
             f=open(concentrationsfile, "w")
             f.write(self._concentrationsTextASCII)
             f.close()
        return outfile

    def generateReportFromFitFile(self):
        d=ConfigDict.ConfigDict()
        d.read(self.fitfile)
        sourcename = "Unknown Source"
        selection  = "Unknown Selection"
        if 'info' in d:
            if 'key' in d['info']:
                selection=d['info']['key']
            elif 'Key' in d['info']:
                selection=d['info']['Key']
            for key in d['info'].keys():
                if key.upper() == 'SOURCENAME':
                    sourcename = d['info'][key]
                elif (key.upper() == 'SELECTION') or\
                     (key.upper() == 'LEGEND'):
                    selection = d['info'][key]
        self.sourcename = sourcename
        self.selection  = selection
        if self.outfile is None:
            if  self.outdir is None:
                self.outdir = os.getcwd()
            self.outfile= os.path.basename(self.fitfile)
        else:
            if self.outdir is None:
                self.outdir = os.path.dirname(self.outfile)
            self.outfile= os.path.basename(self.outfile)
        if self.outdir == '':self.outdir = "."
        self.fitresult=d
        if 'concentrations' in d:
            self.concentrations = d['concentrations']

    def getText(self):
        newlinks = []
        for key in self.otherhtmltext.keys():
            newlinks.append(["#%s" % (key),"%s" % key])
        text =self.getHeader(newlinks)
        text+=self.getInfo()
        text+=self.getImage()
        text+=self.getParam()
        text+=self.getConcentrations()
        self._concentrationsTextASCII = self.getConcentrationsASCII()
        text+=self.getResult()
        for key in self.otherhtmltext.keys():
             text+="\n"
             text+= "<H2><a NAME=""%s""></a><FONT color=#009999>" % key
             text+= "%s:" % key
             text+= "</FONT></H2>"
             text+= '<div style="color:#000000">'
             text+= self.otherhtmltext[key]
             text+= '</div>'
             text+="<br>"
        text+=self.getFooter()
        return text

    def getHeader(self,addlink=None):
        link = [ ['http://pymca.sourceforge.net', 'PyMCA home'],
                 ['http://www.esrf.fr', 'ESRF home'],
                 ['http://www.esrf.fr/UsersAndScience/Experiments/TBS/BLISS', 'BLISS home']]
        if self.concentrations is not None:
            link.append(['#Concentrations', 'Concentrations'])
        if self.tableFlag:link.append(['#Fit_Peak_Results', 'Fit Peak Results'])
        if addlink is not None:
            for item in addlink:
                link.append(item)
        text =""
        text+= "<HTML>"
        text+= "<HEAD>"
        text+= "<TITLE>PyMCA : Advanced Fit Results</TITLE>"
        text+= "</HEAD>"
        text+= '<BODY style="color:#000000; background-color:#FFFFFF" ALINK=#ff6600 LINK=#0000cc VLINK=#0000cc marginwidth=10 marginheight=10  topmargin=10 leftmargin=10>'
        text+= "<CENTER>"
        text+= "<TABLE WIDTH=100%% border=0 Height=70>"
        text+= "  <TR>"
        text+= "    <TD><Font Size=5 Color=#009999>"
        text+= "        <b>PyMCA : Advanced Fit Results</b></Font>"
        text+= "    </td>"
        text+= "    <td rowspan=2 ALIGN=RIGHT VALIGN=bottom>"
        text+= "        <a HREF=""http://www.esrf.fr/"">"
        logofile = self.outdir + "/" + "PyMcaLogo.png"
        if not os.path.exists(logofile):
            pixmap = qt.QPixmap(PyMcaLogo.PyMcaLogo)
            pixmap.save(logofile,"PNG")
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

    def getInfo(self):
        text =""
        text+= "<nobr><H2><FONT color=#009999>"
        text+= "Computed File :&nbsp;"
        text+= "</FONT>"
        text+= "<FONT color=#000000>"
        if self.fitfile is not None:
            if os.path.basename(self.fitfile) == self.fitfile:
                text+= "<b><I>%s</I></b>" % (os.getcwd()+"/"+self.fitfile)
            else:
                text+= "<b><I>%s</I></b>" % (self.fitfile)
        else:
            text+= "<b><I>%s</I></b>" % (self.outdir+"/"+self.outfile+".fit")
            #and I have to generate it!!!!!!!!!!!!"
            d=ConfigDict.ConfigDict(self.fitresult)
            try:
                os.remove(self.outdir+"/"+self.outfile+".fit")
            except Exception:
                pass
            if self.concentrations is not None:
                d['concentrations'] = self.concentrations
            d.write(self.outdir+"/"+self.outfile+".fit")
        text+= "</FONT>"
        text+= "</H2>"
        text+= "</nobr>"
        text+= "<LEFT>"
        text+= "<TABLE border=0>"
        text+= "<TR><TD><SPACER TYPE=BLOCK WIDTH=50></TD><TD>"
        text+= '<TABLE border=0 cellpadding=1 cellspacing=2 style="color:#000000">'
        text+= "  <TR><TH ALIGN=LEFT>Source : &nbsp;</TH><TD ALIGN=LEFT>%s</TD></TR>"    % (self.sourcename)
        text+= "  <TR><TH ALIGN=LEFT>Selection : &nbsp;</TH><TD ALIGN=LEFT>%s</TD></TR>" % (self.selection)
        text+= "  <TR><TH ALIGN=LEFT>Parameters : &nbsp;</TH><TD ALIGN=LEFT>"
        d=ConfigDict.ConfigDict(self.fitresult['result']['config'])
        try:
            os.remove(self.outdir+"/"+self.outfile+".txt")
        except Exception:
            pass
        d.write(self.outdir+"/"+self.outfile+".txt")
        text+= "<a HREF=""%s"">%s</a>"% (self.outfile+".txt",self.outfile+".txt")
        text+="</TD></TR>"

        """
        text+= "  <TR><TH ALIGN=RIGHT>Source : </TH><TD ALIGN=LEFT>%s</TD>"%(self.sourcename)
        text+= "  <TH ALIGN=RIGHT>Selection : </TH><TD ALIGN=LEFT>%s</TD></TR>"%(self.selection)
        keys= [ key for key in info.keys() if key not in ['paramfile', 'peakfile'] ]
        for idx in range(0, len(keys), 2):
            text+= "  <TR><TH ALIGN=RIGHT>%s : </TH><TD ALIGN=LEFT>%s</TD>"%(keys[idx], info[keys[idx]])
            if idx+1<len(keys):
                text+= "  <TH ALIGN=RIGHT>%s : </TH><TD ALIGN=LEFT>%s</TD></TR>"%(keys[idx+1], info[keys[idx+1]])
            else:
                text+= "  <TD COLSPAN=2></TD></TR>"
        """
        text+= "</TABLE>"
        text+= "</TD></TR></TABLE>"
        text+= "</LEFT>"
        return text


    def getParam(self):
        text=""
        zero = self.fitresult['result']['fittedpar'][self.fitresult['result']['parameters'].index('Zero')]
        gain = self.fitresult['result']['fittedpar'][self.fitresult['result']['parameters'].index('Gain')]
        noise= self.fitresult['result']['fittedpar'][self.fitresult['result']['parameters'].index('Noise')]
        fano = self.fitresult['result']['fittedpar'][self.fitresult['result']['parameters'].index('Fano')]
        sum  = self.fitresult['result']['fittedpar'][self.fitresult['result']['parameters'].index('Sum')]
        stdzero = self.fitresult['result']['sigmapar'][self.fitresult['result']['parameters'].index('Zero')]
        stdgain = self.fitresult['result']['sigmapar'][self.fitresult['result']['parameters'].index('Gain')]
        stdnoise= self.fitresult['result']['sigmapar'][self.fitresult['result']['parameters'].index('Noise')]
        stdfano = self.fitresult['result']['sigmapar'][self.fitresult['result']['parameters'].index('Fano')]
        stdsum  = self.fitresult['result']['sigmapar'][self.fitresult['result']['parameters'].index('Sum')]

        hypermetflag = self.fitresult['result']['config']['fit']['hypermetflag']
        if not ('fitfunction' in self.fitresult['result']['config']['fit']):
            if hypermetflag:
                self.fitresult['result']['config']['fit']['fitfunction'] = 0
            else:
                self.fitresult['result']['config']['fit']['fitfunction'] = 1
        if self.fitresult['result']['config']['fit']['fitfunction'] or\
           (hypermetflag != 1):
            #the peaks are not pure gaussians
            if self.fitresult['result']['config']['fit']['fitfunction']:
                #peaks are pseudo-voigt functions
                hypermetnames = ['Eta Factor']
            else:
                hypermetnames = ['ST AreaR', 'ST SlopeR',
                                 'LT AreaR', 'LT SlopeR',
                                 'STEP HeightR']
            hypermetvalues=[]
            hypermetstd   =[]
            hypermetfinalnames = []
            for name in hypermetnames:
                if name in self.fitresult['result']['parameters']:
                    hypermetvalues.append(self.fitresult['result']['fittedpar'] \
                            [self.fitresult['result']['parameters'].index(name)])
                    hypermetstd.append(self.fitresult['result']['sigmapar'] \
                            [self.fitresult['result']['parameters'].index(name)])
                    hypermetfinalnames.append(name)

        # --- html table
        text+="<H2><FONT color=#009999>"
        text+="Fit Parameters :"
        text+="</FONT></H2>"
        text+="<CENTER>"
        text+="<TABLE border=0 cellpadding=0 cellspacing=2 width=80% style=\"color:#000000\">"
        text+="<TR>"
        text+="    <TD><TABLE border=1 cellpadding=1 cellspacing=0 width=100%>"
        text+="        <TR align=center>"
        text+="            <TH colspan=2>FIT parameters</TH>"
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Region of Fit</I></TD>"
        text+="            <TD>&nbsp;%d - %d</TD>" % (self.fitresult['result']['config']['fit']['xmin'],self.fitresult['result']['config']['fit']['xmax'])
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Number of iterations</I></TD>"
        #text+="            <TD>&nbsp;%d</TD>" % (fitpar['fit_numiter'])
        text+="            <TD>&nbsp;%d</TD>" % (self.fitresult['result']['niter'])
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Chi square</I></TD>"
        #text+="            <TD>&nbsp;%.4f</TD>" % (fitpar['fit_chi'])
        text+="            <TD>&nbsp;%.4f</TD>" % (self.fitresult['result']['chisq'])
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Last Chi square difference</I></TD>"
        #text+="            <TD>&nbsp;%.4f %%</TD>" % (fitpar['fit_lastchi'])
        text+="            <TD>&nbsp;%.4f %%</TD>" % (self.fitresult['result']['lastdeltachi']*100)
        text+="        </TR>"
        text+="        </TABLE>"
        text+="    </TD>"
        text+="</TR>"
        text+="<TR>"
        text+="    <TD><TABLE border=1 cellpadding=1 cellspacing=0 width=100%>"
        text+="        <TR align=center>"
        text+="            <TH colspan=2>Calibration parameters</TH>"
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Zero</I></TD>"
        text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (zero, stdzero)
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Gain</I></TD>"
        text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (gain, stdgain)
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Noise</I></TD>"
        text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (noise, stdnoise)
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Fano</I></TD>"
        text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (fano, stdfano)
        text+="        </TR>"
        text+="        <TR align=left>"
        text+="            <TD><I>&nbsp;Sum</I></TD>"
        text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (sum, stdsum)
        text+="        </TR>"
        text+="        </TABLE>"
        text+="    </TD>"
        text+="</TR>"

        # --- Peak shape parameters ---
        if hypermetflag != 1:
            text+="<TR>"
            text+="    <TD><TABLE border=1 cellpadding=1 cellspacing=0 width=100%>"
            text+="        <TR align=center>"
            text+="            <TH colspan=2>Peak shape parameters</TH>"
            text+="        </TR>"
            for i in range(len(hypermetfinalnames)):
                text+="        <TR align=left>"
                text+="            <TD><I>&nbsp;%s</I></TD>" % hypermetnames[i]
                text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (hypermetvalues[i],
                                                                      hypermetstd[i])
                text+="        </TR>"
            text+="        </TABLE>"
            text+="    </TD>"
            text+="</TR>"



        # --- Continuum parameters ---
        text+="<TR>"
        text+="    <TD><TABLE border=1 cellpadding=1 cellspacing=0 width=100%>"
        text+="        <TR align=center>"
        text+="            <TH colspan=2>Continuum parameters</TH>"
        text+="        </TR>"
        # Stripping
        if self.fitresult['result']['config']['fit']['stripflag']:
             constant    = 1.0
             iterations = 20000
             stripwidth = 1
             stripfilterwidth = 1
             stripalgorithm = 0
             snipwidth = 30
             if 'stripalgorithm' in self.fitresult['result']['config']['fit']:
                stripalgorithm=self.fitresult['result']['config']['fit']['stripalgorithm']
             if 'snipwidth' in self.fitresult['result']['config']['fit']:
                snipwidth=self.fitresult['result']['config']['fit']['snipwidth']
             if 'stripconstant' in self.fitresult['result']['config']['fit']:
                constant=self.fitresult['result']['config']['fit']['stripconstant']
             if 'stripiterations' in self.fitresult['result']['config']['fit']:
                iterations=self.fitresult['result']['config']['fit']['stripiterations']
             if 'stripwidth' in self.fitresult['result']['config']['fit']:
                stripwidth=self.fitresult['result']['config']['fit']['stripwidth']
             if 'stripfilterwidth' in self.fitresult['result']['config']['fit']:
                stripfilterwidth=self.fitresult['result']['config']['fit']['stripfilterwidth']
             if stripalgorithm == 1:
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;Type</I></TD>"
                 text+="            <TD>&nbsp;%s</TD>" % "SNIP Background"
                 text+="        </TR>"
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;%s<I></TD>" % "SNIP width"
                 text+="            <TD>&nbsp;%.5f</TD>" % snipwidth
                 text+="        </TR>"
             else:
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;Type</I></TD>"
                 text+="            <TD>&nbsp;%s</TD>" % "Strip Background"
                 text+="        </TR>"
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;%s<I></TD>" % "Strip Constant"
                 text+="            <TD>&nbsp;%.5f</TD>" % constant
                 text+="        </TR>"
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;%s<I></TD>" % "Strip Iterations"
                 text+="            <TD>&nbsp;%d</TD>" % iterations
                 text+="        </TR>"
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;%s<I></TD>" % "Strip Width"
                 text+="            <TD>&nbsp;%d</TD>" % stripwidth
                 text+="        </TR>"
             text+="        <TR align=left>"
             text+="            <TD><I>&nbsp;%s<I></TD>" % "Smoothing Filter Width"
             text+="            <TD>&nbsp;%d</TD>" % stripfilterwidth
             text+="        </TR>"
             stripanchorslist = []
             stripanchorsflag = self.fitresult['result']['config']['fit'].get('stripanchorsflag', 0)
             if stripanchorsflag:
                 stripanchorslist = self.fitresult['result']['config']['fit'].get('stripanchorslist', [])
             i = 0
             for anchor in stripanchorslist:
                 if anchor != 0:
                     text+="        <TR align=left>"
                     text+="            <TD><I>&nbsp;%s%d<I></TD>" % ("Anchor",i)
                     text+="            <TD>&nbsp;%d</TD>" % anchor
                     text+="        </TR>"
                     i += 1

        # --- Background Function
        if self.fitresult['result']['config']['fit']['continuum']:
             text+="        <TR align=left>"
             text+="            <TD><I>&nbsp;Type</I></TD>"
             if 'continuum_name' in self.fitresult['result']['config']['fit']:
                name = self.fitresult['result']['config']['fit']['continuum_name']
                text+="            <TD>&nbsp;%s</TD>" % name
             elif self.fitresult['result']['config']['fit']['continuum'] == 1:
                text+="            <TD>&nbsp;%s</TD>" % "Constant Polymomial"
             elif self.fitresult['result']['config']['fit']['continuum'] == 2:
                text+="            <TD>&nbsp;%s</TD>" % "1st Order Polymomial"
             elif self.fitresult['result']['config']['fit']['continuum'] == 3:
                text+="            <TD>&nbsp;%s</TD>" % "2nd Order Polymomial"
             else:
                #compatibility with previous versions
                text+="            <TD>&nbsp;%s</TD>" % "1st Order Polymomial"
             text+="        </TR>"
             isum = self.fitresult['result']['parameters'].index('Sum')
             a=0
             if hypermetflag:a=5
             nglobal = len(self.fitresult['result']['parameters']) - len(self.fitresult['result']['groups'])
             for i in range(isum+1,nglobal-a):
                 text+="        <TR align=left>"
                 text+="            <TD><I>&nbsp;%s<I></TD>" % self.fitresult['result']['parameters'][i]
                 value    = self.fitresult['result']['fittedpar'][i]
                 stdvalue = self.fitresult['result']['sigmapar'] [i]
                 text+="            <TD>&nbsp;% .5E +/- % .5E</TD>" % (value, stdvalue)
                 text+="        </TR>"
             text+="</TR>"
        text+="        </TABLE>"
        text+="    </TD>"
        text+="</TR>"
        text+="</TABLE>"
        text+="</CENTER>"
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
        text+= '        <TD><FONT size=1 color=#000000>created:  %s</font></TD>' % time.ctime(now)
        #text+= "        <TD ALIGN=RIGHT><FONT size=1 >last modified: %s" % time.ctime(now)
        text+= '        <TD ALIGN=RIGHT><FONT size=1 color=#000000>last modified: %s by' % time.ctime(now)
        #text+= "        <A STYLE=""color: #0000cc"" HREF=""mailto:papillon@esrf.fr"">papillon@esrf.fr</A></FONT></TD>"
        if sys.platform == 'win32':
            try:
                user = os.getenv('USERNAME')
                text+= "        <A STYLE=""color: #0000cc"">%s</A></FONT></TD>" % user
            except Exception:
                text +="</FONT></TD>"
        else:
            try:
                user = os.getenv("USER")
                text+= "        <A STYLE=""color: #0000cc"">%s</A></FONT></TD>" % user
            except Exception:
                text +="</FONT></TD>"
        text+= "    </TR>"
        text+= "</TABLE>"
        text+= "</center>"
        text+= "</BODY>"
        text+= "</HTML>"
        return text

    def __getFitImage(self,imagefile=None):
        if imagefile is None:imagefile=self.outdir+"/"+self.outfile+".png"
        filelink = "%s" % imagefile
        text = ""
        text+= "<H2><FONT color=#009999>"
        text+= "Spectrum, Continuum and Fitted values :"
        text+= "</FONT></H2>"
        text+= "<CENTER>"
        text+= "<IMG SRC=%s ALT=""fit graph"" ALIGN=center>"%filelink
        text+= "</CENTER>"
        return text

    def getImage(self):
        ddict=self.fitresult
        try:
            fig = Figure(figsize=(6,3)) # in inches
            canvas = FigureCanvas(fig)
            ax = fig.add_axes([.15, .15, .8, .8])
            ax.set_axisbelow(True)
            logplot = self.plotDict.get('logy', True)
            if logplot is None:
                if (ddict['result']['ydata'].max() - ddict['result']['ydata'].min()) < 200:
                    logplot = False
                elif ddict['result']['yfit'].min() < 0.01:
                    logplot = False
                else:
                    logplot = True
            if logplot:
                axplot = ax.semilogy
            else:
                axplot = ax.plot
            axplot(ddict['result']['energy'], ddict['result']['ydata'], 'k', lw=1.5)
            axplot(ddict['result']['energy'], ddict['result']['continuum'], 'g', lw=1.5)
            legendlist = ['spectrum', 'continuum', 'fit']
            axplot(ddict['result']['energy'], ddict['result']['yfit'], 'r', lw=1.5)
            fontproperties = FontProperties(size=8)
            if ddict['result']['config']['fit']['sumflag']:
                axplot(ddict['result']['energy'],
                       ddict['result']['pileup'] + ddict['result']['continuum'], 'y', lw=1.5)
                legendlist.append('pileup')
            if matplotlib_version < '0.99.0':
                legend = ax.legend(legendlist,0,
                                   prop = fontproperties, labelsep=0.02)
            elif matplotlib_version < '1.5':
                legend = ax.legend(legendlist,0,
                                   prop = fontproperties, labelspacing=0.02)
            else:
                legend = ax.legend(legendlist, loc=0,
                                   prop = fontproperties, labelspacing=0.02)
        except ValueError:
            # It seems this error is not caught with matplotlib 2.2.4 and the
            # report crashes instead of switching to a linear plot
            fig = Figure(figsize=(6,3)) # in inches
            canvas = FigureCanvas(fig)
            ax = fig.add_axes([.15, .15, .8, .8])
            ax.set_axisbelow(True)
            ax.plot(ddict['result']['energy'], ddict['result']['ydata'], 'k', lw=1.5)
            ax.plot(ddict['result']['energy'], ddict['result']['continuum'], 'g', lw=1.5)
            legendlist = ['spectrum', 'continuum', 'fit']
            ax.plot(ddict['result']['energy'], ddict['result']['yfit'], 'r', lw=1.5)
            fontproperties = FontProperties(size=8)
            if ddict['result']['config']['fit']['sumflag']:
                ax.plot(ddict['result']['energy'],
                            ddict['result']['pileup'] + ddict['result']['continuum'], 'y', lw=1.5)
                legendlist.append('pileup')
            if matplotlib_version < '0.99.0':
                legend = ax.legend(legendlist,0,
                               prop = fontproperties, labelsep=0.02)
            elif matplotlib_version < '1.5':
                legend = ax.legend(legendlist,0,
                               prop = fontproperties, labelspacing=0.02)
            else:
                legend = ax.legend(legendlist, loc=0,
                               prop = fontproperties, labelspacing=0.02)

        ax.set_xlabel('Energy')
        ax.set_ylabel('Counts')
        legend.draw_frame(False)

        outfile = self.outdir+"/"+self.outfile+".png"
        try:
            os.remove(outfile)
        except Exception:
            pass

        canvas.print_figure(outfile)
        return self.__getFitImage(self.outfile+".png")

    def getConcentrations(self):
        return self.concentrationsConversion.getConcentrationsAsHtml(\
                                                self.concentrations)

    def getConcentrationsASCII(self):
        return self.concentrationsConversion.getConcentrationsAsAscii(\
                                                self.concentrations)

    def getResult(self):
        text = ""
        if self.tableFlag == 0:
            return text
        text+="\n"
        text+= "<H2><a NAME=""%s""></a><FONT color=#009999>" % 'Fit_Peak_Results'
        text+= "%s:" % 'Fit Peak Results'
        text+= "</FONT></H2>"
        text+="<br>"
        result = self.fitresult['result']
        if self.tableFlag == 1:
            labels=['Element','Group','Fit&nbsp; Area','Sigma']
        else:
            labels=['Element','Group','Fit&nbsp; Area','Sigma','Energy','Ratio','FWHM','Chi&nbsp; square']
        lemmon = ("#%x%x%x" % (255,250,205)).upper()
        hcolor = ("#%x%x%x" % (230,240,249)).upper()
        text += "<CENTER>"
        text += ("<nobr>")
        text += '<table width="80%" border="0" cellspacing="1" cellpadding="1" >'
        text += ( "<tr><b>")
        for l in range(len(labels)):
            if l < 2:
                text += '<td align="left" bgcolor=%s style="color:#000000"><b>%s</b></td>' % (hcolor,labels[l])
            elif (l > 3) or (self.tableFlag == 1):
                text += '<td align="right" bgcolor=%s style="color:#000000"><b>%s</b></td>' % (hcolor,labels[l])
            else:
                text += '<td align="center" bgcolor=%s style="color:#000000"><b>%s</b></td>' % (hcolor,labels[l])
        text+="</b></tr>\n"

        for group in result['groups']:
            text+=("<tr>")
            ele,group0 = group.split()
            text += '<td align="left" style="color:#000000"><b>%s</b></td>' % ele
            text += '<td align="left" style="color:#000000"><b>%s</b></td>' % group0
            fitarea    = "%.6e" % result[group]['fitarea']
            sigmaarea  = "%.2e" % result[group]['sigmaarea']
            text += '<td align="right" style="color:#000000"><b>%s</b></td>' % fitarea
            text += '<td align="right" style="color:#000000"><b>%s</b></td>' % sigmaarea
            text += '<td align="right" style="color:#000000"><b>&nbsp;</b></td>'
            text += '<td align="right" style="color:#000000"><b>&nbsp;</b></td>'
            text += '<td align="right" style="color:#000000"><b>&nbsp;</b></td>'
            text += '<td align="right" style="color:#000000"><b>&nbsp;</b></td>'
            text += '</tr>\n'
            if type(result[group]['peaks']) != type([]):
                iterator = [result[group]['peaks']]
            else:
                iterator = 1 * result[group]['peaks']
            if self.tableFlag == 1:
                iterator = []
            for peak in iterator:
                text += '<tr><td>&nbsp;</td>'
                name  = peak
                energy = ("%.3f" % (result[group][peak]['energy']))
                ratio  = ("%.5f" % (result[group][peak]['ratio']))
                area   = ("%.6e" % (result[group][peak]['fitarea']))
                sigma  = ("%.2e" % (result[group][peak]['sigmaarea']))
                fwhm   = ("%.3f" % (result[group][peak]['fwhm']))
                chisq  = ("%.2f" % (result[group][peak]['chisq']))
                fields = [name,area,sigma,energy,ratio,fwhm,chisq]
                for field in fields:
                    if field == name:
                        text+=('<td align="left"  bgcolor=%s style="color:#000000">%s</td>' % (lemmon,field))
                    else:
                        text+=('<td align="right" bgcolor=%s style="color:#000000">%s</td>' % (lemmon,field))
                text+="</tr>\n"
            if type(result[group]['escapepeaks']) != type([]):
                iterator = [result[group]['escapepeaks']]
            else:
                iterator = 1 * result[group]['escapepeaks']
            if self.tableFlag == 1:
                iterator = []
            for peak0 in iterator:
                name  = peak0+"esc"
                peak  = peak0+"esc"
                if name not in result[group]:
                    # i.e. peak0 = "Al K" and Si detector
                    continue
                if result[group][name]['ratio'] > 0.0:
                    text += '<tr><td></td>'
                    energy = ("%.3f" % (result[group][peak]['energy']))
                    ratio  = ("%.5f" % (result[group][peak]['ratio']))
                    area   = ("%.6e" % (result[group][peak]['fitarea']))
                    sigma  = ("%.2e" % (result[group][peak]['sigmaarea']))
                    fwhm   = ("%.3f" % (result[group][peak]['fwhm']))
                    chisq  = ("%.2f" % (result[group][peak]['chisq']))
                    fields = [name,area,sigma,energy,ratio,fwhm,chisq]
                    for field in fields:
                        if field == name:
                            text+=('<td align="left"  bgcolor=%s style="color:#000000">%s</td>' % (lemmon,field))
                        else:
                            text+=('<td align="right" bgcolor=%s style="color:#000000">%s</td>' % (lemmon,field))
                    text+="</tr>\n"
        text+=("</table>")
        text+=("</nobr>")
        text+="</CENTER>"
        return text

def generateoutput(fitfile,outfile=None):
    report = QtMcaAdvancedFitReport(fitfile, outfile)
    report.writeReport()

if __name__ == "__main__":
    if len(sys.argv) <2 :
        print("Usage: %s Input_Fit_Result_File [optional_output_file]" %\
              sys.argv[0])
        sys.exit(1)
    app = qt.QApplication(sys.argv)
    fitfile=sys.argv[1]
    if len(sys.argv) > 2:
        outfile = sys.argv[2]
    else:
        outfile = None
    generateoutput(fitfile,outfile)
    app.quit()

