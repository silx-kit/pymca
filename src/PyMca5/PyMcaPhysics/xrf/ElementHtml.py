#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2014 European Synchrotron Radiation Facility
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
from . import Elements

class ElementHtml(object):
    def __init__(self,element=None):
        self.element = None

    def gethtml(self,element=None):
        if element is None:element = self.element
        if element is None:return ""
        ele = element
        #text="<center><b><font color=red size=5>Summary</font></b></center>"
        text=""
        if ele not in Elements.Element.keys():
            text+="<br><b><font color=blue size=4>Unknown Element</font></b>"
            return text
        symbol = Elements.getsymbol(Elements.getz(ele))
        omegak = Elements.Element[ele]['omegak']
        omegal = [  Elements.Element[ele]['omegal1'],
                    Elements.Element[ele]['omegal2'],
                    Elements.Element[ele]['omegal3'] ]
        omegam = [  Elements.Element[ele]['omegam1'],
                    Elements.Element[ele]['omegam2'],
                    Elements.Element[ele]['omegam3'],
                    Elements.Element[ele]['omegam4'],
                    Elements.Element[ele]['omegam5'] ]

        #text+="<center>
        text+="<br><b><font color=#009999 size=4>Element Info</font></b>"
        #text+="</center>"
        text+="<nobr><table>"
        #symbol
        text+="<tr>"
        text+='<td align="left">'
        text+="<b><font size=3>Symbol</font></b>"
        text+="</td>"
        text+='<td align="center">'
        text+="<b><font size=3>=</font></b>"
        text+="</td>"
        text+='<td align="left">'
        text+="<b><font size=3>%s </font></b>"  % symbol
        text+="</td>"
        #Z
        text+="<tr>"
        text+='<td align="left">'
        text+="<b><font size=3>At. Number</font></b>"
        text+="</td>"
        text+='<td align="center">'
        text+="<b><font size=3>=</font></b>"
        text+="</td>"
        text+='<td align="left">'
        text+="<b><font size=3>%d </font></b>"  % Elements.Element[ele]['Z']
        text+="</td>"
        #name
        text+="<tr>"
        text+='<td align="left">'
        text+="<b><font size=3>Name</font></b>"
        text+="</td>"
        text+='<td align="center">'
        text+="<b><font size=3>=</font></b>"
        text+="</td>"
        text+='<td align="left">'
        name = Elements.Element[ele]['name'][0].upper()+Elements.Element[ele]['name'][1:]
        text+="<b><font size=3>%s </font></b>"  % name
        text+="</td>"
        #mass
        text+="<tr>"
        text+='<td align="left">'
        text+="<b><font size=3>At. Weight</font></b>"
        text+="</td>"
        text+='<td align="center">'
        text+="<b><font size=3>=</font></b>"
        text+="</td>"
        text+='<td align="left">'
        text+="<b><font size=3>%.5f </font></b>"  % Elements.Element[ele]['mass']
        text+="</td>"
        #density
        text+="<tr>"
        text+='<td align="left">'
        text+="<b><font size=3>Density</font></b>"
        text+="</td>"
        text+='<td align="center">'
        text+="<b><font size=3>=</font></b>"
        text+="</td>"
        text+='<td align="left">'
        text+="<b><font size=3>%.5f g/cm3</font></b>"  % Elements.Element[ele]['density']
        text+="</td>"
        text+="</tr>"
        text+="</table>"


        # Shell propierties
        if Elements.Element[ele]['Z'] > 2:
            text+="<br><b><font color=#009999 size=4>Fluorescence Yields</font></b>"
            text+="<nobr><table><tr>"
            text+='<td align="left"><b>'
            text+='Shell'
            text+="</b></td>"
            text+='<td align="right"><b>'
            text+='Yield'
            text+="</b></td>"
            text+="</tr>"
            text+="<tr>"
            text+='<td align="left">'
            text+="<b><font size=3>%s </font></b>"  % "K"
            text+="</td>"
            text+='<td align="right">'
            text+="<b><font size=3>%.3e </font></b>"  % omegak
            text+="</td>"
        for i in range(len(omegal)):
            if omegal[i] > 0.0:
                    text+="<tr>"
                    text+='<td align="left">'
                    text+="<b><font size=3>L%d </font></b>"  % (i+1)
                    text+="</td>"
                    text+='<td align="right">'
                    text+="<b><font size=3>%.3e </font></b>"  % omegal[i]
                    text+="</td>"
        for i in range(len(omegam)):
            if omegam[i] > 0.0:
                    text+="<tr>"
                    text+='<td align="left">'
                    text+="<b><font size=3>M%d </font></b>"  % (i+1)
                    text+="</td>"
                    text+='<td align="right">'
                    text+="<b><font size=3>%.3e </font></b>"  % omegam[i]
                    text+="</td>"
        text+="</tr>"
        text+="</table>"

        f  = ['f12','f13','f23']
        ck = []
        doit = 0
        for item in f:
            value = Elements.Element[ele]['CosterKronig']['L'][item]
            if value > 0:doit=1
            ck.append(value)
        if doit:
            text+="<br><b><font color=#009999 size=4>L-Shell Coster-Kronig</font></b>"
            text+="<nobr><table><tr>"
            for item in f:
                text+='<td align="left"><b>'
                text+=item
                text+="</b></td>"
            text+="</tr>"
            text+="<tr>"
            for i in range(len(f)):
                text+='<td align="left">'
                text+="<b><font size=3>%.3f </font></b>"  % ck[i]
            text+="</td>"
            text+="</tr>"
            text+="</table>"
            #M shell
            fs = [[ 'f12', 'f13', 'f14', 'f15'],
                          ['f23', 'f24', 'f25'],
                                 ['f34', 'f35'],
                                        ['f45']]
            doit = 0
            for f in fs:
                for item in f:
                    value = Elements.Element[ele]['CosterKronig']['M'][item]
                    if value > 0:doit=1
            if doit:
                text+="<br><b><font color=#009999 size=4>M-Shell Coster-Kronig</font></b>"
                text+="<nobr><table>"
                for f in fs:
                    text+="<tr>"
                    for item in f:
                        text+='<td align="left"><b>'
                        text+=item
                        text+="</b></td>"
                    text+="</tr>"
                    text+="<tr>"
                    for item in f:
                        text+='<td align="left">'
                        text+="<b><font size=3>%.3f </font></b>"  % Elements.Element[ele]['CosterKronig']['M'][item]
                    text+="</td>"
                    text+="</tr>"
                text+="</table>"

        for rays in Elements.Element[ele]['rays']:
            if rays == "Ka xrays":continue
            if rays == "Kb xrays":continue
            #text+="<center>"
            text+="<br><b><font color=#009999 size=4>%s Emission Energies</font></b>" % rays[0:-1]
            #text+="</center>"
            text+="<nobr><table><tr>"
            text+='<td align="left"><b>'
            text+='Line'
            text+="</b></td>"
            text+='<td align="right"><b>'
            text+='Energy (keV)'
            text+="</b></td>"
            text+='<td align="right"><b>'
            text+='Rate'
            text+="</b></td>"
            text+="</tr>"
            for transition in Elements.Element[ele][rays]:
                transitiontext = transition.replace('*','')
                text+="<tr>"
                text+='<td align="left">'
                text+="<b><font size=3>%s </font></b>"  % transitiontext
                text+="</td>"
                text+='<td align="right">'
                text+="<b><font size=3>%.5f</font></b>"  % Elements.Element[ele][transition]['energy']
                text+="</td>"
                text+='<td align="right">'
                text+="<b><font size=3>%.5f </font></b>"  % Elements.Element[ele][transition]['rate']
                text+="</td>"
            text+="</tr>"
            text+="</table>"

        #text+="<center>"
        text+="<br><b><font color=#009999 size=4>%s Binding Energies</font></b>" % "Electron"
        #text+="</center>"
        text+="<nobr><table><tr>"
        text+='<td align="left"><b>'
        text+='Shell'
        text+="</b></td>"
        text+='<td align="right"><b>'
        text+='Energy (keV)'
        text+="</b></td>"
        text+="</tr>"
        for shell in Elements.ElementShells:
            if Elements.Element[ele]['binding'][shell] > 0.0:
                text+="<tr>"
                text+='<td align="left">'
                text+="<b><font size=3>%s </font></b>"  % shell
                text+="</td>"
                text+='<td align="right">'
                text+="<b><font size=3>%.5f </font></b>"  % Elements.Element[ele]['binding'][shell]
                text+="</td>"
        text+="</tr>"
        text+="</table>"
        return text


if __name__ == "__main__":
    import sys
    from PyMca5 import PyMcaQt as qt
    app  = qt.QApplication(sys.argv)
    if len(sys.argv) > 1:
        ele = sys.argv[1]
    else:
        ele = "Fe"
    w= qt.QWidget()
    l=qt.QVBoxLayout(w)
    html = ElementHtml()
    text = qt.QTextEdit(w)
    text.insertHtml(html.gethtml(ele))
    text.setReadOnly(1)
    l.addWidget(text)
    w.show()
    app.exec()
