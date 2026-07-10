#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
LOGLOG = True
import sys
import os
import numpy
import re
import weakref
from PyMca5.PyMcaIO import ConfigDict
from . import CoherentScattering
from . import IncoherentScattering
from . import PyMcaEPDL97
from PyMca5 import PyMcaDataDir

"""
Constant                     Symbol      2006 CODATA value          Relative uncertainty
Electron relative atomic mass   Ar(e) 5.485 799 0943(23) x 10-4     4.2 x 10-10
Molar mass constant             Mu    0.001 kg/mol                   defined
Rydberg constant                R    10 973 731.568 527(73) m-1      6.6 x 10-12
Planck constant                 h     6.626 068 96(33) x 10-34 Js    5.0 x 10-8
Speed of light                  c     299 792 458 m/s                defined
Fine structure constant         alpha 7.297 352 5376(50) x 10-3      6.8 x 10-10
Avogadro constant               NA    6.022 141 79(30) x 10+23 mol-1 5.0 x 10-8
"""
MINENERGY = 0.175
AVOGADRO_NUMBER = 6.02214179E23
#
#   Symbol  Atomic Number   x y ( positions on table )
#       name,  mass, density
#
ElementsInfo = [
   ["H",   1,    1,1,   "hydrogen",   1.00800,     0.08988   ],
   ["He",  2,   18,1,   "helium",     4.00300,     0.17860   ],
   ["Li",  3,    1,2,   "lithium",    6.94000,     534.000   ],
   ["Be",  4,    2,2,   "beryllium",  9.01200,     1848.00   ],
   ["B",   5,   13,2,   "boron",      10.8110,     2340.00   ],
   ["C",   6,   14,2,   "carbon",     12.0100,     1580.00   ],
   ["N",   7,   15,2,   "nitrogen",   14.0080,     1.25000   ],
   ["O",   8,   16,2,   "oxygen",     16.0000,     1.42900   ],
   ["F",   9,   17,2,   "fluorine",   19.0000,     1108.00   ],
   ["Ne",  10,  18,2,   "neon",       20.1830,     0.90020   ],
   ["Na",  11,   1,3,   "sodium",     22.9970,     970.000   ],
   ["Mg",  12,   2,3,   "magnesium",  24.3200,     1740.00   ],
   ["Al",  13,  13,3,   "aluminium",  26.9700,     2720.00   ],
   ["Si",  14,  14,3,   "silicon",    28.0860,     2330.00   ],
   ["P",   15,  15,3,   "phosphorus", 30.9750,     1820.00   ],
   ["S",   16,  16,3,   "sulphur",    32.0660,     2000.00   ],
   ["Cl",  17,  17,3,   "chlorine",   35.4570,     1560.00   ],
   ["Ar",  18,  18,3,   "argon",      39.9440,     1.78400   ],
   ["K",   19,   1,4,   "potassium",  39.1020,     862.000   ],
   ["Ca",  20,   2,4,   "calcium",    40.0800,     1550.00   ],
   ["Sc",  21,   3,4,   "scandium",   44.9600,     2992.00   ],
   ["Ti",  22,   4,4,   "titanium",   47.9000,     4540.00   ],
   ["V",   23,   5,4,   "vanadium",   50.9420,     6110.00   ],
   ["Cr",  24,   6,4,   "chromium",   51.9960,     7190.00   ],
   ["Mn",  25,   7,4,   "manganese",  54.9400,     7420.00   ],
   ["Fe",  26,   8,4,   "iron",       55.8500,     7860.00   ],
   ["Co",  27,   9,4,   "cobalt",     58.9330,     8900.00   ],
   ["Ni",  28,  10,4,   "nickel",     58.6900,     8900.00   ],
   ["Cu",  29,  11,4,   "copper",     63.5400,     8940.00   ],
   ["Zn",  30,  12,4,   "zinc",       65.3800,     7140.00   ],
   ["Ga",  31,  13,4,   "gallium",    69.7200,     5903.00   ],
   ["Ge",  32,  14,4,   "germanium",  72.5900,     5323.00   ],
   ["As",  33,  15,4,   "arsenic",    74.9200,     5730.00   ],
   ["Se",  34,  16,4,   "selenium",   78.9600,     4790.00   ],
   ["Br",  35,  17,4,   "bromine",    79.9200,     3120.00   ],
   ["Kr",  36,  18,4,   "krypton",    83.8000,     3.74000   ],
   ["Rb",  37,   1,5,   "rubidium",   85.4800,     1532.00   ],
   ["Sr",  38,   2,5,   "strontium",  87.6200,     2540.00   ],
   ["Y",   39,   3,5,   "yttrium",    88.9050,     4405.00   ],
   ["Zr",  40,   4,5,   "zirconium",  91.2200,     6530.00   ],
   ["Nb",  41,   5,5,   "niobium",    92.9060,     8570.00   ],
   ["Mo",  42,   6,5,   "molybdenum", 95.9500,     10220.0   ],
   ["Tc",  43,   7,5,   "technetium", 99.0000,     11500.0   ],
   ["Ru",  44,   8,5,   "ruthenium",  101.0700,    12410.0   ],
   ["Rh",  45,   9,5,   "rhodium",    102.9100,    12440.0   ],
   ["Pd",  46,  10,5,   "palladium",  106.400,     12160.0   ],
   ["Ag",  47,  11,5,   "silver",     107.880,     10500.0   ],
   ["Cd",  48,  12,5,   "cadmium",    112.410,     8650.00   ],
   ["In",  49,  13,5,   "indium",     114.820,     7280.00   ],
   ["Sn",  50,  14,5,   "tin",        118.690,     5310.00   ],
   ["Sb",  51,  15,5,   "antimony",   121.760,     6691.00   ],
   ["Te",  52,  16,5,   "tellurium",  127.600,     6240.00   ],
   ["I",   53,  17,5,   "iodine",     126.910,     4940.00   ],
   ["Xe",  54,  18,5,   "xenon",      131.300,     5.90000   ],
   ["Cs",  55,   1,6,   "caesium",    132.910,     1873.00   ],
   ["Ba",  56,   2,6,   "barium",     137.360,     3500.00   ],
   ["La",  57,   3,6,   "lanthanum",  138.920,     6150.00   ],
   ["Ce",  58,   4,9,   "cerium",     140.130,     6670.00   ],
   ["Pr",  59,   5,9,   "praseodymium",140.920,    6769.00   ],
   ["Nd",  60,   6,9,   "neodymium",  144.270,     6960.00   ],
   ["Pm",  61,   7,9,   "promethium", 147.000,     6782.00   ],
   ["Sm",  62,   8,9,   "samarium",   150.350,     7536.00   ],
   ["Eu",  63,   9,9,   "europium",   152.000,     5259.00   ],
   ["Gd",  64,  10,9,   "gadolinium", 157.260,     7950.00   ],
   ["Tb",  65,  11,9,   "terbium",    158.930,     8272.00   ],
   ["Dy",  66,  12,9,   "dysprosium", 162.510,     8536.00   ],
   ["Ho",  67,  13,9,   "holmium",    164.940,     8803.00   ],
   ["Er",  68,  14,9,   "erbium",     167.270,     9051.00   ],
   ["Tm",  69,  15,9,   "thulium",    168.940,     9332.00   ],
   ["Yb",  70,  16,9,   "ytterbium",  173.040,     6977.00   ],
   ["Lu",  71,  17,9,   "lutetium",   174.990,     9842.00   ],
   ["Hf",  72,   4,6,   "hafnium",    178.500,     13300.0   ],
   ["Ta",  73,   5,6,   "tantalum",   180.950,     16600.0   ],
   ["W",   74,   6,6,   "tungsten",   183.920,     19300.0   ],
   ["Re",  75,   7,6,   "rhenium",    186.200,     21020.0   ],
   ["Os",  76,   8,6,   "osmium",     190.200,     22500.0   ],
   ["Ir",  77,   9,6,   "iridium",    192.200,     22420.0   ],
   ["Pt",  78,  10,6,   "platinum",   195.090,     21370.0   ],
   ["Au",  79,  11,6,   "gold",       197.200,     19370.0   ],
   ["Hg",  80,  12,6,   "mercury",    200.610,     13546.0   ],
   ["Tl",  81,  13,6,   "thallium",   204.390,     11860.0   ],
   ["Pb",  82,  14,6,   "lead",       207.210,     11340.0   ],
   ["Bi",  83,  15,6,   "bismuth",    209.000,     9800.00   ],
   ["Po",  84,  16,6,   "polonium",   209.000,     9320.00   ],
   ["At",  85,  17,6,   "astatine",   210.000,     0         ],
   ["Rn",  86,  18,6,   "radon",      222.000,     9.73000   ],
   ["Fr",  87,   1,7,   "francium",   223.000,     0         ],
   ["Ra",  88,   2,7,   "radium",     226.000,     5500.00   ],
   ["Ac",  89,   3,7,   "actinium",   227.000,     0         ],
   ["Th",  90,   4,10,  "thorium",    232.000,     11700.0   ],
   ["Pa",  91,   5,10,  "proactinium",231.03588,   15370.0   ],
   ["U",   92,   6,10,  "uranium",    238.070,     19050.0   ],
   ["Np",  93,   7,10,  "neptunium",  237.000,     20250.0   ],
   ["Pu",  94,   8,10,  "plutonium",  239.100,     19700.0   ],
   ["Am",  95,   9,10,  "americium",  243,         13670.0   ],
   ["Cm",  96,  10,10,  "curium",     247,         13510.0   ],
   ["Bk",  97,  11,10,  "berkelium",  247,         13250.0   ],
   ["Cf",  98,  12,10,  "californium",251,         15100.0   ],
   ["Es",  99,  13,10,  "einsteinium",252,         0         ],
   ["Fm",  100,  14,10, "fermium",    257,         0         ],
   ["Md",  101,  15,10, "mendelevium",258,         0         ],
   ["No",  102,  16,10, "nobelium",   259,         0         ],
   ["Lr",  103,  17,10, "lawrencium", 262,         0         ],
   ["Rf",  104,   4,7,  "rutherfordium",261,       0         ],
   ["Db",  105,   5,7,  "dubnium",    262,         0         ],
   ["Sg",  106,   6,7,  "seaborgium", 266,         0         ],
   ["Bh",  107,   7,7,  "bohrium",    264,         0         ],
   ["Hs",  108,   8,7,  "hassium",    269,         0         ],
   ["Mt",  109,   9,7,  "meitnerium", 268,         0         ],
]
ElementList= [ elt[0] for elt in ElementsInfo ]

from . import BindingEnergies
ElementShells = BindingEnergies.ElementShells[1:]
ElementBinding = BindingEnergies.ElementBinding

from . import KShell
from . import LShell
from . import MShell
#Scofield's photoelectric dictionary
from . import Scofield1973

ElementShellTransitions = [KShell.ElementKShellTransitions,
                           KShell.ElementKAlphaTransitions,
                           KShell.ElementKBetaTransitions,
                           LShell.ElementLShellTransitions,
                           LShell.ElementL1ShellTransitions,
                           LShell.ElementL2ShellTransitions,
                           LShell.ElementL3ShellTransitions,
                           MShell.ElementMShellTransitions,
                           MShell.ElementM1ShellTransitions,
                           MShell.ElementM2ShellTransitions,
                           MShell.ElementM3ShellTransitions,
                           MShell.ElementM4ShellTransitions,
                           MShell.ElementM5ShellTransitions]
ElementShellRates = [KShell.ElementKShellRates,
                     KShell.ElementKAlphaRates,
                     KShell.ElementKBetaRates,
                     LShell.ElementLShellRates,
                     LShell.ElementL1ShellRates,
                     LShell.ElementL2ShellRates,
                     LShell.ElementL3ShellRates,
                     MShell.ElementMShellRates,
                     MShell.ElementM1ShellRates,
                     MShell.ElementM2ShellRates,
                     MShell.ElementM3ShellRates,
                     MShell.ElementM4ShellRates,
                     MShell.ElementM5ShellRates]

ElementXrays      = ['K xrays', 'Ka xrays', 'Kb xrays', 'L xrays','L1 xrays','L2 xrays','L3 xrays','M xrays',
                     'M1 xrays', 'M2 xrays', 'M3 xrays', 'M4 xrays', 'M5 xrays']

def getsymbol(z):
    if (z > 0) and (z<=len(ElementList)):
        return ElementsInfo[int(z)-1][0]
    else:
        return None

def getname(z):
    if (z > 0) and (z<=len(ElementList)):
        return ElementsInfo[int(z)-1][4]
    else:
        return None

def getz(ele):
    if ele in ElementList:
        return ElementList.index(ele)+1
    else:
        return None

#fluorescence yields
def getomegak(ele):
    index = KShell.ElementKShellConstants.index('omegaK')
    return  KShell.ElementKShellValues[getz(ele)-1][index]

def getomegal1(ele):
    index = LShell.ElementL1ShellConstants.index('omegaL1')
    return  LShell.ElementL1ShellValues[getz(ele)-1][index]

def getomegal2(ele):
    index = LShell.ElementL2ShellConstants.index('omegaL2')
    return  LShell.ElementL2ShellValues[getz(ele)-1][index]

def getomegal3(ele):
    index = LShell.ElementL3ShellConstants.index('omegaL3')
    return  LShell.ElementL3ShellValues[getz(ele)-1][index]

def getomegam1(ele):
    return MShell.getomegam1(ele)

def getomegam2(ele):
    return MShell.getomegam2(ele)

def getomegam3(ele):
    return MShell.getomegam3(ele)

def getomegam4(ele):
    return MShell.getomegam4(ele)

def getomegam5(ele):
    return MShell.getomegam5(ele)

#CosterKronig
def getCosterKronig(ele):
    return LShell.getCosterKronig(ele)

#Jump ratios following Veigele: Atomic Data Tables 5 (1973) 51-111. p 54 and 55
VEIGELE = True
def getjkVeigele(z):
    return (125.0/z) + 3.5

def getjl1Veigele(z):
    return 1.2

def getjl2Veigele(z):
    return 1.4

def getjl3Veigele(z):
    return (80.0/z) + 1.5

def getjm1Veigele(z):
    return 1.1

def getjm2Veigele(z):
    return 1.1

def getjm3Veigele(z):
    return 1.2

def getjm4Veigele(z):
    return 1.5

def getjm5Veigele(z):
    return (225.0/z) - 0.35

def getjk(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjkVeigele(z)
    ele = getsymbol(z)
    if 'JK' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JK']*1.0
    else:
        return None

def getjl1(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjl1Veigele(z)
    ele = getsymbol(z)
    if 'JL1' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JL1']*1.0
    else:
        return None

def getjl2(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjl2Veigele(z)
    ele = getsymbol(z)
    if 'JL2' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JL2']*1.0
    else:
        return None

def getjl3(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjl3Veigele(z)
    ele = getsymbol(z)
    if 'JL3' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JL3']*1.0
    else:
        return None

def getjm1(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjm1Veigele(z)
    ele = getsymbol(z)
    if 'JM1' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JM1']*1.0
    else:
        return None

def getjm2(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjm2Veigele(z)
    ele = getsymbol(z)
    if 'JM3' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JM2']*1.0
    else:
        return None

def getjm3(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjm3Veigele(z)
    ele = getsymbol(z)
    if 'JM3' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JM3']*1.0
    else:
        return None

def getjm4(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjm4Veigele(z)
    ele = getsymbol(z)
    if 'JM4' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JM4']*1.0
    else:
        return None

def getjm5(z, veigele=None):
    if z > 101:z=101
    if veigele is None:
        veigele = VEIGELE
    if VEIGELE: return getjm5Veigele(z)
    ele = getsymbol(z)
    if 'JM5' in Scofield1973.dict[ele].keys():
        return Scofield1973.dict[ele]['JM5']*1.0
    else:
        return None

def getLJumpWeight(ele,excitedshells=[1.0,1.0,1.0]):
    """
    wjump represents the probability for a vacancy to be created
    on the respective L-Shell by direct photoeffect on that shell
    """
    z = getz(ele)
    #weights due to photoeffect
    jl  = [getjl1(z), getjl2(z), getjl3(z)]
    wjump = []
    i = 0
    cum = 0.00
    for jump in jl:
        if jump is not None:
            v = excitedshells[i]*(jump-1.0)/jump
        else:
            v = 0.0
        wjump.append(v)
        cum += v
        i+=1
    for i in range(len(wjump)):
        if cum > 0.0:
            wjump[i] = wjump[i] / cum
        else:
            wjump[i] = 0.0
    return wjump

def getMJumpWeight(ele,excitedshells=[1.0,1.0,1.0,1.0,1.0]):
    """
    wjump represents the probability for a vacancy to be created
    on the respective M-Shell by direct photoeffect on that shell
    """
    z = getz(ele)
    #weights due to photoeffect
    jm  = [getjm1(z), getjm2(z), getjm3(z), getjm4(z), getjm5(z)]
    wjump = []
    i = 0
    cum = 0.00
    for jump in jm:
        if jump is not None:
            v = excitedshells[i]*(jump-1.0)/jump
        else:
            v = 0.0
        wjump.append(v)
        cum += v
        i+=1
    for i in range(len(wjump)):
        if cum > 0.0:
            wjump[i] = wjump[i] / cum
        else:
            wjump[i] = 0.0
    return wjump

def getPhotoWeight(ele,shelllist,energy, normalize = None, totals = None):
    #shellist = ['M1', 'M2', 'M3', 'M4', 'M5']
    # or ['L1', 'L2', 'L3']
    if normalize is None:normalize = True
    if totals is None: totals = False
    w = []
    z = getz(ele)
    if z > 101:
        element = getsymbol(101)
        if z > 104:
            elework = getsymbol(104)
        else:
            elework = ele
    else:
        elework = ele
        element = ele
    if totals and (energy < 1.0):
        raise ValueError("Incompatible combination")
    elif (energy < 1.0):
        #make sure the binding energies are correct
        if PyMcaEPDL97.EPDL97_DICT[ele]['original']:
            #make sure the binding energies are those used by this module and not EADL ones
            PyMcaEPDL97.setElementBindingEnergies(ele,
                                                  Element[ele]['binding'])
        return PyMcaEPDL97.getPhotoelectricWeights(ele,
                                                   shelllist,
                                                   energy,
                                                   normalize=normalize,
                                                   totals=False)
    elif totals:
        totalPhoto = []
    logf = numpy.log
    expf = numpy.exp
    for key in shelllist:
        wi = 0.0
        totalPhotoi = 0.0
        if key != "all other":
            bindingE = Element[elework]['binding'][key]
        else:
            bindingE = 0.001
        if (key == "all other") and (key not in Scofield1973.dict[element].keys()):
            doit = False
        else:
            doit = True

        if doit and bindingE > 0.0:
            if energy >= bindingE:
                deltae = energy - bindingE
                if key != "all other":
                    ework  = Scofield1973.dict[element]['binding'][key]+deltae
                else:
                    ework  = energy
                if ework > Scofield1973.dict[element]['energy'][-1]:
                    #take last
                    wi =  Scofield1973.dict[element][key][-1]
                    totalPhotoi=Scofield1973.dict[element]['total'][-1]
                else:
                    #interpolate
                    i=0
                    while (Scofield1973.dict[element]['energy'][i] < ework):
                        i+=1
                    #if less than 5 eV take that value (Scofield calculations
                    #do not seem to be self-consistent in tems of energy grid
                    #and binding energy -see Lead with e=2.5 -> ework = 2.506
                    #that is below the binding energy of Scofield)
                    if False and (Scofield1973.dict[element]['energy'][i] - ework) < 0.005:
                        #this does not work for Cd and E=3.5376"
                        print("Not interpolate for key = ",key,'ework = ',ework,"taken ",Scofield1973.dict[element]['energy'][i])
                        wi =  Scofield1973.dict[element][key][i]
                    elif (key != 'all other') and Scofield1973.dict[element]['energy'][i-1] < Scofield1973.dict[element]['binding'][key]:
                        wi =  Scofield1973.dict[element][key][i]
                        totalPhotoi = Scofield1973.dict[element]['total'][i]
                    elif Scofield1973.dict[element][key][i-1] <= 0.0:
                        #equivalent to previous case, solves problem of Fr at excitation = 3.0
                        wi =  Scofield1973.dict[element][key][i]
                        totalPhotoi = Scofield1973.dict[element]['total'][i]
                    else:
                        #if element == "Fr":
                        #    print "energy = ",energy," ework = ",ework
                        #    print Scofield1973.dict[element]['energy'][i]
                        #    print Scofield1973.dict[element]['energy'][i-1]
                        #    print Scofield1973.dict[element][key][i]
                        #    print Scofield1973.dict[element][key][i-1]
                        #    print type( Scofield1973.dict[element][key][i-1] )
                        x2 = logf(Scofield1973.dict[element]['energy'][i])
                        x1 = logf(Scofield1973.dict[element]['energy'][i-1])
                        y2 = logf(Scofield1973.dict[element][key][i])
                        y1 = logf(Scofield1973.dict[element][key][i-1])
                        slope = (y2 - y1)/(x2 - x1)
                        wi = expf(y1 + slope * (logf(ework) - x1))
                        if totals:
                            y2 = logf(Scofield1973.dict[element]['total'][i])
                            y1 = logf(Scofield1973.dict[element]['total'][i-1])
                            totalPhotoi = expf(y1 + slope * (logf(ework) - x1))


        w += [wi]
        if totals:
            totalPhoto += [totalPhotoi]
    if normalize:
        total = sum(w)
        for i in range(len(w)):
            if total > 0.0:
                w[i] = w[i]/total
            else:
                w[i] = 0.0
    if totals:
        return w, totalPhoto
    else:
        return w

def _getFluorescenceWeights(ele, energy, normalize = None, cascade = None):
    if normalize is None:normalize = True
    if cascade   is None:cascade   = False
    #python 3
    if type(ele) == type(" "):
        #unicode, fine
        pass
    elif 'bytes' in str(type(ele)):
        #bytes object, convert to unicode
        ele = ele.decode()
    else:
        ele = getsymbol(int(ele))
    wall = getPhotoWeight(ele,['K','L1','L2','L3','M1','M2','M3','M4','M5','all other'],energy, normalize=True)
    #weights due to Coster - Kronig transitions
    #k shell is not affected
    ck= LShell.getCosterKronig(ele)

    if cascade and (sum(wall[1:4]) > 0.0) and (wall[0] > 0.0):
        #l shell (considering holes due to k shell transitions)
        #I assume that approximately the auger transitions give
        #single equaly distributed vacancies
        # I guess this will be better than ignoring them
        if Element[ele]['omegak'] > 0.001:
            auger = 0.32 * (1.0 - Element[ele]['omegak'])
            #assume rest goes to other shells ...
            cor   = [auger,
                     auger + Element[ele]['KL2']['rate'] * Element[ele]['omegak'],
                     auger + Element[ele]['KL3']['rate'] * Element[ele]['omegak']]
            w = [wall[1]+cor[0] * wall[0],
                 wall[2]+cor[1] * wall[0],
                 wall[3]+cor[2] * wall[0]]
        else:
            cor = 0.3 * wall[0]
            w = [wall[1]+cor, wall[2]+cor, wall[3]+cor]
    else:
        #l shell (neglecting holes due to k shell transitions)
        w = [wall[1], wall[2], wall[3]]

    w[0] = w[0]
    w[1] = w[1] + ck['f12'] * w[0]
    w[2] = w[2] + ck['f13'] * w[0] + ck['f23'] * w[1]

    wall[1] = w[0] * 1.0
    wall[2] = w[1] * 1.0
    wall[3] = w[2] * 1.0
    #mshell
    ck= MShell.getCosterKronig(ele)
    if cascade and (sum(wall[4:]) > 0):
        cor = [0.0, 0.0, 0.0, 0.0, 0.0]
        augercor = 0.0
        if wall[0] > 0.0:
            #K shell
            if 'KM2' in Element[ele]['K xrays']:
                cor[1] += wall[0] * Element[ele]['KM2']['rate'] * \
                           Element[ele]['omegak']
            if 'KM3' in Element[ele]['K xrays']:
                cor[2] += wall[0] * Element[ele]['KM3']['rate'] * \
                           Element[ele]['omegak']
            #auger K transitions (5 % total of shells M1, M2, M3)
            cor[0] += wall[0] * 0.05 * (1.0 - Element[ele]['omegak'])
            cor[1] += wall[0] * 0.05 * (1.0 - Element[ele]['omegak'])
            cor[2] += wall[0] * 0.05 * (1.0 - Element[ele]['omegak'])
            cor[3] += wall[0] * 0.01 * (1.0 - Element[ele]['omegak'])
            cor[4] += wall[0] * 0.01 * (1.0 - Element[ele]['omegak'])

        if sum(wall[1:4]) > 0:
            #L shell
            #X rays I can take them rigorously
            mlist = ['M1','M2','M3','M4','M5']
            i = 0
            #for the auger I take 95% of the value and
            #equally distribute it among the shells
            augerfactor = 0.95/ 5.0
            augercor    = 0.0
            for key in ['L1 xrays', 'L2 xrays', 'L3 xrays']:
                i = i + 1
                if   i == 1:
                    omega=Element[ele]['omegal1']
                    auger= 1.0 - omega \
                           - Element[ele]['CosterKronig']['L']['f12'] \
                           - Element[ele]['CosterKronig']['L']['f13']
                    augercor += augerfactor * auger
                elif i == 2:
                    omega=Element[ele]['omegal2']
                    auger= 1.0 - omega \
                           - Element[ele]['CosterKronig']['L']['f23']
                    augercor += augerfactor * auger
                elif i == 3:
                    omega=Element[ele]['omegal3']
                    auger= 1.0 - omega
                    augercor += augerfactor * auger
                else:
                    print("Error unknown shell, Please report")
                    omega = 0.0
                    #for the elements

                #I consider Coster-Kronig for L1
                if (i == 1) and (Element[ele]['Z'] >= 80):
                    #f13 is the main transition
                    if Element[ele]['Z'] >= 90:
                        #L1-L3M5 is ~ 40 %
                        #L1-L3M4 is ~ 32 %
                        #rest is other shells
                        cor[3] += 0.32 * wall[1] * \
                                  Element[ele]['CosterKronig']['L']['f13']
                        cor[4] += 0.43 * wall[1] * \
                                  Element[ele]['CosterKronig']['L']['f13']
                        if Element[ele]['Z'] > 90:
                            cor[2] += 0.5 * wall[1] * \
                                  Element[ele]['CosterKronig']['L']['f13']
                    else:
                        #L1-L3M5 is ~ 43 %
                        #L1-L3M4 is ~ 32 %
                        #rest is other shells
                        cor[3] += 0.32 * wall[1] * \
                                  Element[ele]['CosterKronig']['L']['f13']
                        cor[4] += 0.44 * wall[1] * \
                                  Element[ele]['CosterKronig']['L']['f13']
                #L2
                elif (i == 2) and (Element[ele]['Z'] >= 90):
                    if Element[ele]['Z'] >= 94:
                        #L2-L3M5 ~ 3 %
                        #L2-L3M4 ~ 50%
                        cor[3] += 0.50 * wall[2] * \
                            Element[ele]['CosterKronig']['L']['f23']
                        cor[4] += 0.03 * wall[2] * \
                            Element[ele]['CosterKronig']['L']['f23']
                    else:
                        #L2-L3M5 ~ 6 %
                        cor[4] += 0.06 * wall[2] * \
                            Element[ele]['CosterKronig']['L']['f23']
                elif (i==3):
                    #missing pages from article
                    pass
                if key in Element[ele]:
                    for t in Element[ele][key]:
                        if t[2:] in mlist:
                            index = mlist.index(t[2:])
                            cor[index] +=  Element[ele][t]['rate'] * \
                                            wall[i] * omega
        cor[0] += augercor
        cor[1] += augercor
        cor[2] += augercor
        cor[3] += augercor
        cor[4] += augercor
        w = [wall[4]+cor[0], wall[5]+cor[1], wall[6]+cor[2], wall[7]+cor[3], wall[8]+cor[4]]
    else:
        w = [wall[4], wall[5], wall[6], wall[7], wall[8]]

    w[0] =  w[0]
    w[1] =  w[1] + ck['f12'] * w[0]
    w[2] =  w[2] + ck['f13'] * w[0] + ck['f23'] * w[1]
    w[3] =  w[3] + ck['f14'] * w[0] + ck['f24'] * w[1] + ck['f34'] * w[2]
    w[4] =  w[4] + ck['f15'] * w[0] + ck['f25'] * w[1] + ck['f35'] * w[2] +\
                                                             ck['f45'] * w[3]
    wall[4] = w[0] * 1.0
    wall[5] = w[1] * 1.0
    wall[6] = w[2] * 1.0
    wall[7] = w[3] * 1.0
    wall[8] = w[4] * 1.0

    #weights due to omega
    omega = [ getomegak(ele),
              getomegal1(ele), getomegal2(ele), getomegal3(ele),
              getomegam1(ele), getomegam2(ele), getomegam3(ele), getomegam4(ele), getomegam5(ele)]
    w = wall[0:9]
    for i in range(len(w)):
        w[i] *= omega[i]
    if normalize:
        cum = sum(w)
        for i in range(len(w)):
            if cum > 0.0:
                w[i] /= cum
    return w

def getEscape(matrix, energy, ethreshold=None, ithreshold=None, nthreshold = None,
                        alphain = None, cascade = None, fluorescencemode=None):
    """
    getEscape(matrixlist, energy,
              ethreshold=None, ithreshold=None, nthreshold = None,
              alphain = None)
    matrixlist is a list of the form [material, density, thickness]
    energy is the incident beam energy
    ethreshold is the difference in keV between two peaks to be considered the same
    ithreshold is the minimum absolute peak intensity to consider
    nthreshold is maximum number of escape peaks to consider
    alphain  is the incoming beam angle with detector surface
    It gives back a list of the form  [[energy0, intensity0, label0],
                                       [energy1, intensity1, label1],
                                       ....
                                       [energyn, intensityn, labeln]]
    with the escape energies, intensities and labels
    """
    if alphain  is None: alphain  = 90.0
    if fluorescencemode is None:fluorescencemode = False
    sinAlphaIn   = numpy.sin(alphain * (numpy.pi)/180.)
    sinAlphaOut  = 1.0
    elementsList = None
    if cascade is None:cascade=False
    if elementsList is None:
        #get material elements and concentrations
        eleDict = getMaterialMassFractions([matrix[0]], [1.0])
        if eleDict == {}: return {}
        #sort the elements according to atomic number (not needed because the output will be a dictionary)
        keys = eleDict.keys()
        elementsList = [[getz(x),x] for x in keys]
        elementsList.sort()
        #do the job

    outputDict = {}
    shelllist = ['K', 'L1', 'L2', 'L3','M1', 'M2', 'M3', 'M4', 'M5']
    for z,ele in elementsList:
        #use own unfiltered dictionary
        elementDict = _getUnfilteredElementDict(ele, energy)
        outputDict[ele] ={}
        outputDict[ele]['mass fraction'] = eleDict[ele]
        outputDict[ele]['rates'] = {}
        #get the fluorescence term for all shells
        fluoWeights = _getFluorescenceWeights(ele, energy, normalize = False,
                                                cascade=cascade)
        outputDict[ele]['rays'] = elementDict['rays'] * 1
        for rays in elementDict['rays']:
            outputDict[ele][rays] = []
            rates    = []
            energies = []
            transitions = elementDict[rays]
            for transition in transitions:
                outputDict[ele][rays] += [transition]
                outputDict[ele][transition]={}
                outputDict[ele][transition]['rate'] = 0.0
                if transition[0] == "K":
                    """
                    if transition[-1] == 'a':

                    elif transition[-1] == 'b':

                    else:
                    """
                    rates.append(fluoWeights[0] *  elementDict[transition]['rate'])
                else:
                    rates.append(fluoWeights[shelllist.index(transition[0:2])] * elementDict[transition]['rate'])
                ene = elementDict[transition]['energy']
                energies += [ene]
                outputDict[ele][transition]['energy'] = ene
                if ene < 0.0:
                    print("element = ", ele, "transition = ", transition, "exc. energy = ", energy)

            #matrix term
            formula   = matrix[0]
            thickness = matrix[1] * matrix[2]
            energies += [energy]
            allcoeffs   =  getMaterialMassAttenuationCoefficients(formula,1.0,energies)
            mutotal  = allcoeffs['total']
            #muphoto  = allcoeffs['photo']
            muphoto  = getMaterialMassAttenuationCoefficients(ele,1.0,energy)['photo']
            # correct respect to Reed and Ware
            # because there can be more than one element and
            # I also weight the mass fraction
            notalone = (muphoto[-1]/mutotal[-1]) *\
                        0.5 * outputDict[ele]['mass fraction']
            del energies[-1]
            i = 0
            for transition in transitions:
                trans = (mutotal[i]/sinAlphaOut)/(mutotal[-1]/sinAlphaIn)
                trans = notalone * \
                        (1.0 - trans * numpy.log(1.0 + 1.0/trans))
                if thickness > 0.0:
                    #extremely thin case
                    trans0 = notalone * thickness * mutotal[-1]/sinAlphaIn
                    trans = min(trans0, trans)
                rates[i] *=  trans
                outputDict[ele][transition]['rate'] = rates[i]
                i += 1
            outputDict[ele]['rates'][rays] = sum(rates)
            #outputDict[ele][rays]= Element[ele]['rays'] * 1
    peaklist = []
    for key in outputDict:
        rays = []
        if 'M xrays' in outputDict[key]:
            rays += outputDict[key]['M xrays']
        if 'L xrays' in outputDict[key]:
            rays += outputDict[key]['L xrays']
        if 'K xrays' in outputDict[key]:
            rays += outputDict[key]['K xrays']
        for label in rays:
            if fluorescencemode:
                peaklist.append([outputDict[key][label]['energy'],
                                 outputDict[key][label]['rate'],
                                 key+' '+label.replace('*','')])
            else:
                peaklist.append([energy - outputDict[key][label]['energy'],
                             outputDict[key][label]['rate'],
                             key+' '+label.replace('*','')])

    return _filterPeaks(peaklist, ethreshold = ethreshold,
                                  ithreshold = ithreshold,
                                  nthreshold = nthreshold,
                                  absoluteithreshold = True,
                                  keeptotalrate = False)


    #return outputDict


def _filterPeaks(peaklist, ethreshold = None, ithreshold = None,
                 nthreshold = None,
                 absoluteithreshold=None,
                 keeptotalrate=None):
    """
    Given a list of peaks of the form [[energy0, intensity0, label0],
                                       [energy1, intensity1, label1],
                                       ....
                                       [energyn, intensityn, labeln]]
    gives back a filtered list of the same form
    ethreshold -> peaks within that threshold are considered one
    ithreshold -> intensity threshold relative to maximum unless
                   absoluteithreshold is set to True
    The total rate is kept unless keeptotal rate is set to false (for instance for
    the escape peak calculation
    """
    if absoluteithreshold is None:absoluteithreshold=False
    if keeptotalrate == None:
        keeptotalrate = True
    div = []
    for i in range(len(peaklist)):
        if peaklist[i][1] > 0.0:
            div.append([peaklist[i][0],[peaklist[i][1],peaklist[i][0]],peaklist[i][2]])
    #div =[[peaklist[i][0],[peaklist[i][1],peaklist[i][0]],peaklist[i][2]] for i in range(len(peaklist))]
    div.sort()
    totalrate = sum([x[1] for x in peaklist])
    newpeaks     =[div[i][1] for i in range(len(div))]
    newpeaksnames=[div[i][2] for i in range(len(div))]
    tojoint=[]
    deltaonepeak = ethreshold
    mix = []

    if len(newpeaks) > 1:
        for i in range(len(newpeaks)):
            #print "i = ",i,"energy = ",newpeaks[i][1], \
            #         " rate = ",newpeaks[i][0], \
            #         "name = ",newpeaksnames[i]
            for j in range(i,len(newpeaks)):
                if i != j:
                    if abs(newpeaks[i][1]-newpeaks[j][1]) < deltaonepeak:
                        if len(tojoint):
                            if (i in tojoint[-1]) and (j in tojoint[-1]):
                                #print "i and j already there"
                                pass
                            elif (i in tojoint[-1]):
                                #print "i was there"
                                tojoint[-1]+=[j]
                            elif (j in tojoint[-1]):
                                #print "j was there"
                                tojoint[-1]+=[i]
                            else:
                                tojoint.append([i,j])
                        else:
                            tojoint.append([i,j])
        if len(tojoint):
            mix=[]
            iDelete = []
            for _group in tojoint:
                rate = 0.0
                rateMax  = 0.0
                for i in _group:
                    rate += newpeaks[i][0]
                    if newpeaks[i][0] > rateMax:
                        rateMax = newpeaks[i][0]
                        iMax    = i
                    iDelete += [i]
                transition = newpeaksnames[iMax]
                ene  = 0.0
                for i in _group:
                    ene  += newpeaks[i][0] * newpeaks[i][1]/rate
                mix.append([ene,rate,transition])
            iDelete.sort()
            iDelete.reverse()
            for i in iDelete:
                del newpeaks[i]
                del newpeaksnames[i]
    output = []
    for i in range(len(newpeaks)):
        output.append([newpeaks[i][1], newpeaks[i][0], newpeaksnames [i]])
    for peak in mix:
        output.append(peak)
    output.sort()

    #intensity threshold
    if len(output) <= 1:return output
    if ithreshold is not None:
        imax = max([x[1] for x in output])
        if absoluteithreshold:
            threshold = ithreshold
        else:
            threshold = ithreshold * imax
        for i in range(-len(output)+1,1):
            if output[i][1] < threshold:
                del output[i]

    #number threshold
    if nthreshold is not None:
        if nthreshold < len(output):
            div = [[x[1],x] for x in output]
            div.sort()
            div.reverse()
            div = div[:nthreshold]
            output = [x[1] for x in div]
            output.sort()

    #recover original rates
    if keeptotalrate:
        currenttotal = sum([x[1] for x in output])
        if currenttotal > 0:
            totalrate = totalrate/currenttotal
            output = [[x[0],x[1]*totalrate,x[2]] for x in output]

    return output


def _getAttFilteredElementDict(elementsList,
                               attenuators=None,
                               detector=None,
                               funnyfilters=None,
                               energy=None,
                               userattenuators=None):
    if energy is None:
        energy = 100.
    if attenuators is None:
        attenuators = []
    if userattenuators is None:
        userattenuators = []
    if funnyfilters is None:
        funnyfilters = []
    outputDict = {}
    for group in elementsList:
        ele  = group[1] * 1
        if not (ele in outputDict):
            outputDict[ele] = {}
            outputDict[ele]['rays'] = []
        raysforloop = [group[2] + " xrays"]
        elementDict = _getUnfilteredElementDict(ele, energy)
        for rays in raysforloop:
            if rays not in elementDict:continue
            else:outputDict[ele]['rays'].append(rays)
            outputDict[ele][rays] = []
            rates    = []
            energies = []
            transitions = elementDict[rays]
            for transition in transitions:
                outputDict[ele][rays] += [transition]
                outputDict[ele][transition]={}
                ene = elementDict[transition]['energy'] * 1
                energies += [ene]
                rates.append(elementDict[transition]['rate'] * 1.0)
                outputDict[ele][transition]['energy'] = ene
            #I do not know if to include this loop in the previous one (because rates are 0.0 sometimes)

            #attenuators
            coeffs = numpy.zeros(len(energies), numpy.float64)
            for attenuator in attenuators:
                formula   = attenuator[0]
                thickness = attenuator[1] * attenuator[2]
                coeffs +=  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
            try:
                trans = numpy.exp(-coeffs)
            except OverflowError:
                #deal with underflows reported as overflows
                trans = numpy.zeros(len(energies), numpy.float64)
                for i in range(len(energies)):
                    coef = coeffs[i]
                    if coef < 0.0:
                        raise ValueError("Positive exponent in attenuators transmission term")
                    else:
                        try:
                            trans[i] = numpy.exp(-coef)
                        except OverflowError:
                            #if we are here we know it is not an overflow and trans[i] has the proper value
                            pass

            #funnyfilters (only make sense to have more than one if same opening and aligned)
            coeffs = numpy.zeros(len(energies), numpy.float64)
            funnyfactor = None
            for attenuator in funnyfilters:
                formula   = attenuator[0]
                thickness = attenuator[1] * attenuator[2]
                if funnyfactor is None:
                    funnyfactor = attenuator[3]
                else:
                    if abs(attenuator[3]-funnyfactor) > 0.0001:
                        raise ValueError("All funny type filters must have same openning fraction")
                coeffs +=  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
            if funnyfactor is None:
                for i in range(len(rates)):
                    rates[i] *= trans[i]
            else:
                try:
                    transFunny = funnyfactor * numpy.exp(-coeffs) +\
                                 (1.0 - funnyfactor)
                except OverflowError:
                    #deal with underflows reported as overflows
                    transFunny = numpy.zeros(len(energies), numpy.float64)
                    for i in range(len(energies)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError("Positive exponent in funnyfilters transmission term")
                        else:
                            try:
                                transFunny[i] = numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                    transFunny = funnyfactor * transFunny + \
                                 (1.0 - funnyfactor)
                for i in range(len(rates)):
                    rates[i] *= (trans[i] * transFunny[i])

            #user attenuators
            if userattenuators:
                utrans = numpy.ones((len(energies),), numpy.float64)
                for userattenuator in userattenuators:
                    utrans *= getTableTransmission(userattenuator, energies)
                for i in range(len(rates)):
                    rates[i] *= utrans[i]

            #detector term
            if detector is not None:
                formula   = detector[0]
                thickness = detector[1] * detector[2]
                coeffs   =  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
                try:
                    trans = (1.0 - numpy.exp(-coeffs))
                except OverflowError:
                    #deal with underflows reported as overflows
                    trans = numpy.ones(len(energies), numpy.float64)
                    for i in range(len(energies)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError("Positive exponent in detector transmission term")
                        else:
                            try:
                                trans[i] = 1.0 - numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                for i in range(len(rates)):
                    rates[i] *= trans[i]
            i = 0
            for transition in transitions:
                outputDict[ele][transition]['rate'] = rates[i] * 1
                i += 1
    return outputDict

def getMultilayerFluorescence(multilayer0,
                              energyList,
                              layerList = None,
                              weightList=None,
                              flagList  = None,
                              fulloutput = None,
                              beamfilters = None,
                              elementsList = None,
                              attenuators  = None,
                              userattenuators = None,
                              alphain      = None,
                              alphaout     = None,
                              cascade = None,
                              detector= None,
                              funnyfilters=None,
                              forcepresent=None,
                              secondary=None):

    if multilayer0 is None:
        return []
    if secondary:
        print("Use fisx library ro deal with secondary excitation")
        print("Ignoring secondary excitation request")
    secondary=False
    if len(multilayer0):
        if type(multilayer0[0]) != type([]):
            multilayer=[multilayer0 * 1]
        else:
            multilayer=multilayer0 * 1
    if fulloutput  is None:fulloutput  = 0
    if (type(energyList) != type([])) and \
       (type(energyList) != numpy.ndarray):
        energyList = [energyList]

    energyList = numpy.array(energyList, dtype=numpy.float64)
    if layerList is None:
        layerList = list(range(len(multilayer)))
    if type(layerList) != type([]):
        layerList = [layerList]
    if elementsList is not None:
        if type(elementsList) != type([]):
            elementsList = [elementsList]

    if weightList is not None:
        if (type(weightList) != type([])) and \
           (type(weightList) != numpy.ndarray):
            weightList = [weightList]
        weightList = numpy.array(weightList, dtype=numpy.float64)
    else:
        weightList = numpy.ones(len(energyList)).astype(numpy.float64)
    if flagList is not None:
        if (type(flagList) != type([])) and \
           (type(flagList) != numpy.ndarray):
            flagList = [flagList]
        flagList   = numpy.array(flagList)
    else:
        flagList = numpy.ones(len(energyList)).astype(numpy.float64)

    optimized = 0
    if beamfilters is None:beamfilters = []
    if len(beamfilters):
        if type(beamfilters[0]) != type([]):
            beamfilters=[beamfilters]
    if elementsList is not None:
        if len(elementsList):
            if type(elementsList[0]) == type([]):
                if len(elementsList[0]) == 3:
                    optimized = 1

    if attenuators is None:
        attenuators = []
    if userattenuators is None:
        userattenuators = []
    if beamfilters is None:
        beamfilters = []
    if alphain  is None:
        alphain =  45.0
    if alphaout is None:
        alphaout = 45.0
    if alphain >= 0:
        sinAlphaIn  = numpy.sin(alphain  * numpy.pi / 180.)
    else:
        sinAlphaIn  = numpy.sin(-alphain  * numpy.pi / 180.)
    sinAlphaOut = numpy.sin(alphaout * numpy.pi / 180.)
    origattenuators = attenuators * 1
    newbeamfilters  = beamfilters * 1
    if alphain < 0:
        ilayerindexes = list(range(len(multilayer)))
        ilayerindexes.reverse()
        for ilayer in ilayerindexes:
            newbeamfilters.append(multilayer[ilayer] * 1)
            newbeamfilters[-1][2] = newbeamfilters[-1][2]/sinAlphaIn
        del newbeamfilters[-1]

    #normalize incoming beam
    i0 = numpy.nonzero(flagList>0)[0]
    weightList = numpy.take(weightList, i0).astype(numpy.float64)
    energyList = numpy.take(energyList, i0).astype(numpy.float64)
    flagList   = numpy.take(flagList, i0).astype(numpy.float64)
    #normalize selected weights
    total = sum(weightList)
        #new way will be made later
        #formula  = []
        #thickness = []
        #for beamfilter in newbeamfilters:
        #    formula.append(beamfilter[0] * 1)
        #    thickness.append(beamfilter[1] * beamfilter[2])
        #trans = getMaterialTransmission(formula, thickness, energyList,
        #        density=1.0, thickness = sum(thickness))['transmission']
        #weightList = weightList * trans
    if total <= 0.0:
        raise ValueError("Sum of weights lower or equal to 0")
    weightList = weightList / total


    #forcepresent is to set concentration 1 for the fit
    #useless if elementsList is not given
    if forcepresent is None:forcepresent=0
    forcedElementsList = []
    if elementsList is not None:
        if forcepresent:
            forcedElementsList = elementsList * 1
            keys = []
            for ilayer in list(range(len(multilayer))):
                pseudomatrix = multilayer[ilayer] * 1
                eleDict = getMaterialMassFractions([pseudomatrix[0]], [1.0])
                keys += eleDict.keys()

            for ele in keys:
                todelete = []
                for i in list(range(len(forcedElementsList))):
                    group = forcedElementsList[i]
                    if optimized: groupElement = group[1] * 1
                    else: groupElement = group * 1
                    if ele == groupElement:
                        todelete.append(i)
                todelete.reverse()
                for i in todelete:
                    del forcedElementsList[i]
        else:
            forcedElementsList = []

    #print "forcedElementsList = ",forcedElementsList
    #import time
    #t0 = time.time()
    result       = []
    dictListList = []
    elementsListFinal = []
    for ilayer in list(range(len(multilayer))):
        dictList     = []
        if ilayer > 0:
            #arrange attenuators
            origattenuators.append(multilayer[ilayer-1] * 1)
            origattenuators[-1][2] = origattenuators[-1][2]/sinAlphaOut
            #arrange beamfilters
            if alphain >= 0:
                newbeamfilters.append(multilayer[ilayer-1] * 1)
                newbeamfilters[-1][2] = newbeamfilters[-1][2]/sinAlphaIn
            else:
                del newbeamfilters[-1]
        if ilayer not in layerList:continue
        pseudomatrix = multilayer[ilayer] * 1
        newelementsList = []
        eleDict = getMaterialMassFractions([pseudomatrix[0]], [1.0])
        if eleDict == {}:
            raise ValueError("Invalid layer material %s" % pseudomatrix[0])
        keys = list(eleDict.keys())
        if elementsList is None:
            newelementsList = keys
            for key in keys:
                if key not in elementsListFinal:
                    elementsListFinal.append(key)
        else:
            newelementsList = []
            if optimized:
                for ele in keys:
                    for group in elementsList:
                        if ele == group[1]:
                            newelementsList.append(group)
            else:
                for ele in keys:
                    for group in elementsList:
                        if ele == group:
                            newelementsList.append(group)
            for group in forcedElementsList:
                newelementsList.append(group * 1)
                if optimized:
                    eleDict[group[1] * 1] = {}
                    eleDict[group[1] * 1] = 1.0
                else:
                    eleDict[group * 1] = {}
                    eleDict[group * 1] = 1.0
            if not len(newelementsList):
                dictList.append({})
                result.append({})
                continue

        #here I could recalculate the dictionary
        if optimized:
            userElementDict = _getAttFilteredElementDict(newelementsList,
                               attenuators=origattenuators,
                               userattenuators=userattenuators,
                               detector=detector,
                               funnyfilters=funnyfilters,
                               energy=max(energyList))
            workattenuators = None
            workuserattenuators = None
            workdetector = None
            workfunnyfilters = None
        else:
            userElementDict = None
            workattenuators = origattenuators * 1
            workuserattenuators = userattenuators * 1
            if detector is not None:
                workdetector = detector * 1
            else:
                workdetector = None
            if funnyfilters is not None:
                workfunnyfilters = funnyfilters * 1
            else:
                workfunnyfilters = None

        newweightlist = numpy.ones(weightList.shape,numpy.float64)
        if len(newbeamfilters):
            coeffs = numpy.zeros(len(energyList), numpy.float64)
            for beamfilter in newbeamfilters:
                formula   = beamfilter[0]
                thickness = beamfilter[1] * beamfilter[2]
                coeffs   +=  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energyList)['total'])
            try:
                trans = numpy.exp(-coeffs)
            except OverflowError:
                #deal with underflows reported as overflows
                trans = numpy.zeros(len(energyList), numpy.float64)
                for i in range(len(energyList)):
                    coef = coeffs[i]
                    if coef < 0.0:
                        raise ValueError("Positive exponent in attenuators transmission term")
                    else:
                        try:
                            trans[i] = numpy.exp(-coef)
                        except OverflowError:
                            #if we are here we know it is not an overflow and trans[i] has the proper value
                            pass
            newweightlist = weightList * trans
        else:
            newweightlist = weightList * 1

        #nobody warrants the list ordered
        if optimized:
            newelementsListWork =  newelementsList * 1
        else:
            newelementsListWork = [newelementsList * 1]
        matrixmutotalexcitation = getMaterialMassAttenuationCoefficients(pseudomatrix[0],
                                                        1.0,
                                                        energyList)['total']
        for justone in newelementsListWork:
            if optimized:
                if justone[2].upper()[0] == 'K':
                    shellIdent = 'K'
                elif len(justone[2]) == 2:
                    shellIdent = justone[2].upper()
                elif justone[2].upper() == 'L':
                    shellIdent = 'L3'
                elif justone[2].upper() == 'M':
                    shellIdent = 'M5'
                else:
                    raise ValueError("Unknown Element shell %s" % justone[2])
                bindingEnergy = Element[justone[1]]['binding'][shellIdent]
                nrgi = numpy.nonzero(energyList >= bindingEnergy)[0]
                if len(nrgi) == 0:nrgi=[0]
                justoneList = [justone]
                matrixmutotalfluorescence = None
                if len(nrgi) > 1:
                    #calculate all the matrix mass attenuation coefficients
                    #for the fluorescent energies outside the energy loop.
                    #the energy list could also be taken out of this loop.
                    element_energies = []
                    for item in userElementDict[justone[1]][justone[2]+ " xrays"]:
                        element_energies.append(userElementDict[justone[1]]\
                                                [item]['energy'])
                    matrixmutotalfluorescence = getMaterialMassAttenuationCoefficients(pseudomatrix[0],
                                                        1.0,
                                                        element_energies)['total']
                else:
                    matrixmutotalfluorescence = None
            else:
                justoneList = justone
                nrgi = range(len(energyList))
                matrixmutotalfluorescence= None
            for iene in nrgi:
                energy   = energyList[iene]  * 1.0
                #print "before origattenuators = ",origattenuators
                dict = getFluorescence(pseudomatrix, energy,
                                attenuators = workattenuators,
                                userattenuators = workuserattenuators,
                                alphain = alphain,
                                alphaout = alphaout,
                                #elementsList = newelementsList,
                                elementsList = justoneList,
                                cascade  = cascade,
                                detector = workdetector,
                                funnyfilters = workfunnyfilters,
                                userElementDict = userElementDict,
                                matrixmutotalfluorescence=matrixmutotalfluorescence,
                                matrixmutotalexcitation=matrixmutotalexcitation[iene]*1.0)
                #print "after origattenuators = ",origattenuators
                if optimized:
                    #give back with concentration 1
                    for ele in dict.keys():
                        dict[ele]['weight'] = newweightlist[iene] * 1.0
                        dict[ele]['mass fraction'] = eleDict[ele] * 1.0
                else:
                    #already corrected for concentration
                    for ele in dict.keys():
                        dict[ele]['weight'] = newweightlist[iene] * eleDict[ele]
                        dict[ele]['mass fraction'] = eleDict[ele] * 1.0
                #if ele == "Cl":print "dict[ele]['mass fraction'] ",eleDict[ele]
                dictList.append(dict)
        if optimized:
            pass
        else:
            newelementsList = [[getz(x),x] for x in newelementsList]
        if fulloutput:
            result.append(_combineMatrixFluorescenceDict(dictList, newelementsList))
        dictListList += dictList
    #print "total elapsed = ",time.time() - t0
    if fulloutput:
        if optimized:
            return [_combineMatrixFluorescenceDict(dictListList, elementsList)] + result
        else:
            newelementsList = [[getz(x),x] for x in (elementsListFinal + forcedElementsList)]
            return [_combineMatrixFluorescenceDict(dictListList, newelementsList)] +result
    else:
        if optimized:
            return _combineMatrixFluorescenceDict(dictListList, elementsList)
        else:
            newelementsList = [[getz(x),x] for x in (elementsListFinal + forcedElementsList)]
            return _combineMatrixFluorescenceDict(dictListList, newelementsList)

def _combineMatrixFluorescenceDict(dictList, elementsList0):
    finalDict = {}
    elementsList = [[x[0], x[1]] for x in elementsList0]
    for z,ele in elementsList:
        #print ele
        finalDict[ele] = {}
        finalDict[ele]['rates'] = {}
        finalDict[ele]['mass fraction'] = {}
        finalDict[ele]['rays']=[]
        for dict in dictList:
            if not (ele in dict):continue
            if not len(dict[ele]['rays']):continue
            finalDict[ele]['mass fraction'] = dict[ele]['mass fraction'] * 1.0
            for key in dict[ele]['rates'].keys():
                if key not in finalDict[ele]['rates']:
                    if not ('weight' in dict[ele]):
                        dict[ele]['weight']=dict['weight'] * 1.0
                    finalDict[ele]['rates'][key] = dict[ele]['rates'][key] *  dict[ele]['weight']
                else:
                    if not ('weight' in dict[ele]):
                        dict[ele]['weight']=dict['weight'] * 1.0
                    finalDict[ele]['rates'][key] += dict[ele]['rates'][key] *  dict[ele]['weight']
            for transitions0 in dict[ele]['rays']:
                #try to avoid creation of new references
                transitions = transitions0 * 1
                if transitions not in dict[ele]['rates'].keys(): continue
                if transitions not in finalDict[ele]['rays']:
                    finalDict[ele]['rays'].append(transitions)
                    finalDict[ele][transitions] = []
                if not (dict[ele]['weight'] > 0.0): continue
                else: w = dict[ele]['weight']
                for transition0 in dict[ele][transitions]:
                    transition = transition0 * 1
                    #print ele,"transition = ",transition
                    if not (transition in finalDict[ele]):
                        finalDict[ele][transition] = {'rate':0.0,
                                   'energy':dict[ele][transition]['energy'] * 1}
                    if transition not in finalDict[ele][transitions]:
                        finalDict[ele][transitions].append(transition)
                    if transition not in finalDict[ele].keys():
                        finalDict[ele][transition] = {'rate':0.0}
                    if transition in dict[ele]:
                      if transition in finalDict[ele]:
                        finalDict[ele][transition]['rate'] += w * dict[ele][transition]['rate']
                      else:
                        finalDict[ele][transition] = {}
                        finalDict[ele][transition]['rate'] = w * dict[ele][transition]['rate']
                    else:
                        print(dict[ele][transitions])
                        print(transition)
                        print("is this an error?")
                        sys.exit(0)
    return finalDict

def getScattering(matrix, energy, attenuators = None, alphain = None, alphaout = None,
                                                elementsList = None, cascade=None,
                                                detector=None):
    if alphain  is None: alphain  = 45.0
    if alphaout is None: alphaout = 45.0
    sinAlphaIn   = numpy.sin(alphain * (numpy.pi)/180.)
    sinAlphaOut  = numpy.sin(alphaout * (numpy.pi)/180.)
    if attenuators is None: attenuators = []
    if len(attenuators):
        if type(attenuators[0]) != type([]):
            attenuators=[attenuators]
    if detector is not None:
        if type(detector) != type([]):
            raise TypeError("Detector must be a list as [material, density, thickness]")
        elif len(detector) != 3:
            raise ValueError("Detector must have the form [material, density, thickness]")

    if energy is None:
        raise ValueError("Invalid Energy")

    if elementsList is None:
        #get material elements and concentrations
        eleDict = getMaterialMassFractions([matrix[0]], [1.0])
        if eleDict == {}: return {}
        #sort the elements according to atomic number (not needed because the output will be a dictionary)
        keys = eleDict.keys()
        elementsList = [[getz(x),x] for x in keys]
        elementsList.sort()
    else:
        if (type(elementsList) != type([])) and (type(elementsList) != tuple):
            elementsList  = [elementsList]
        elementsList = [[getz(x),x] for x in elementsList]
        elementsList.sort()
        eleDict = {}
        for z, ele in elementsList:
            eleDict[ele] = 1.0

    if energy <= 0.10:
        raise ValueError("Invalid Energy %.5g keV" % energy)

    #do the job
    outputDict = {}
    for z,ele in elementsList:
        outputDict[ele] ={}
        outputDict[ele]['mass fraction'] = eleDict[ele]
        outputDict[ele]['rates'] = {}
        outputDict[ele]['rays'] = ['Coherent','Compton']
        for rays in outputDict[ele]['rays']:
            theta = alphain + alphaout
            outputDict[ele][rays] = {}
            if rays == 'Coherent':
                outputDict[ele][rays]['energy'] = energy
                rates=[getElementCoherentDifferentialCrossSection(ele, theta, energy)]
            else:
                outputDict[ele][rays]['energy'] = IncoherentScattering.getComptonScatteringEnergy(energy,
                                                            theta)
                rates=[getElementComptonDifferentialCrossSection(ele, theta, energy)]
            ene = outputDict[ele][rays]['energy']
            energies =[ene]

            #I do not know if to include this loop in the previous one (because rates are 0.0 sometimes)
            #attenuators
            for attenuator in attenuators:
                formula   = attenuator[0]
                thickness = attenuator[1] * attenuator[2]
                coeffs   =  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
                try:
                    trans = numpy.exp(-coeffs)
                except OverflowError:
                    #deal with underflows reported as overflows
                    trans = numpy.zeros(len(energies), numpy.float64)
                    for i in range(len(energies)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError("Positive exponent in attenuators transmission term")
                        else:
                            try:
                                trans[i] = numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                    trans = trans
                for i in range(len(rates)):
                    rates[i] *= trans[i]

            #detector term
            if detector is not None:
                formula   = detector[0]
                thickness = detector[1] * detector[2]
                coeffs   =  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
                try:
                    trans = (1.0 - numpy.exp(-coeffs))
                except OverflowError:
                    #deal with underflows reported as overflows
                    trans = numpy.ones(len(rates), numpy.float64)
                    for i in range(len(rates)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError("Positive exponent in attenuators transmission term")
                        else:
                            try:
                                trans[i] = 1.0 - numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                for i in range(len(rates)):
                    rates[i] *= trans[i]
            #matrix term
            formula   = matrix[0]
            thickness = matrix[1] * matrix[2]
            energies += [energy]
            allcoeffs   =  getMaterialMassAttenuationCoefficients(formula,1.0,energies)
            mutotal  = allcoeffs['total']
            del energies[-1]
            i = 0
            trans = outputDict[ele]['mass fraction'] * 1.0/(mutotal[-1] + mutotal[i] * (sinAlphaIn/sinAlphaOut))
            #correction term
            if thickness > 0.0:
                if abs(sinAlphaIn) > 0.0:
                    try:
                        expterm = numpy.exp(-((mutotal[-1]/sinAlphaIn) +(mutotal[i]/sinAlphaOut)) * thickness)
                    except OverflowError:
                        if -((mutotal[-1]/sinAlphaIn) +(mutotal[i]/sinAlphaOut)) * thickness > 0.0:
                            raise ValueError("Positive exponent in transmission term")
                        expterm = 0.0
                    trans *= (1.0 -  expterm)
            #if ele == 'Pb':
            #    oldRatio.append(newpeaks[i][0])
            #    print "energy = %.3f ratio=%.5f transmission = %.5g final=%.5g" % (newpeaks[i][1], newpeaks[i][0],trans,trans * newpeaks[i][0])
            rates[i] *=  trans
            outputDict[ele][rays]['rate'] = rates[i]
            outputDict[ele]['rates'][rays] = sum(rates)
            #outputDict[ele][rays]= Element[ele]['rays'] * 1
    return outputDict

def getFluorescence(matrix, energy, attenuators = None,
                    alphain = None, alphaout = None,
                                                elementsList = None, cascade=None,
                                                detector=None,
                                                funnyfilters=None,
                                                userElementDict=None,
                                                matrixmutotalfluorescence=None,
                                                matrixmutotalexcitation=None,
                                                userattenuators=None):
    """
    getFluorescence(matrixlist, energy, attenuators = None, alphain = None, alphaout = None,
                            elementsList = None, cascade=None, detector=None)
    matrixlist is a list of the form [material, density, thickness]
    energy is the incident beam energy
    attenuators is a list of the form [[material1, density1, thickness1],....]
    alphain  is the incoming beam angle with sample surface
    alphaout is the outgoing beam angle with sample surface
    if a given elements list is given, the fluorescence rate will be calculated for ONLY
    for those elements without taking into account if they are present in the matrix and
    considering a mass fraction of 1 to all of them. This should allow a program to fit
    directly concentrations.
    cascade is a flag to consider vacancy propagation (it is a crude approximation)
    detector is just one attenuator more but treated as (1 - Transmission)
             [material, density, thickness]

    These formulae are strictly valid only for parallel beams.
    Needs to be corrected for detector efficiency (at least solid angle) and incoming intensity.
    Secondary transitions are neglected.
    """
    if alphain  is None: alphain  = 45.0
    if alphaout is None: alphaout = 45.0
    if userElementDict is None:userElementDict = {}
    bottomExcitation = False
    if   (alphain < 0.0) and (alphaout < 0.0):
        #it is the same
        sinAlphaIn   = numpy.sin(-alphain  * (numpy.pi)/180.)
        sinAlphaOut  = numpy.sin(-alphaout * (numpy.pi)/180.)
    elif (alphain < 0.0) and (alphaout > 0.0):
        #bottom excitation
        #print "bottom excitation case"
        bottomExcitation = True
        sinAlphaIn   = numpy.sin(-alphain * (numpy.pi)/180.)
        sinAlphaOut  = numpy.sin(alphaout * (numpy.pi)/180.)
    else:
        sinAlphaIn   = numpy.sin(alphain * (numpy.pi)/180.)
        sinAlphaOut  = numpy.sin(alphaout * (numpy.pi)/180.)
    if cascade is None:cascade=False
    if attenuators is None:
        attenuators = []
    if userattenuators is None:
        userattenuators = []
    if len(attenuators):
        if type(attenuators[0]) != type([]):
            attenuators=[attenuators]
    if funnyfilters is None:
        funnyfilters = []
    if len(funnyfilters):
        if type(funnyfilters[0]) != type([]):
            funnyfilters=[funnyfilters]
    if detector is not None:
        if type(detector) != type([]):
            raise TypeError(\
                  "Detector must be a list as [material, density, thickness]")
        elif len(detector) != 3:
            raise ValueError(\
                  "Detector must have the form [material, density, thickness]")

    if energy is None:
        raise ValueError("Invalid Energy")

    elementsRays = None
    if elementsList is None:
        #get material elements and concentrations
        eleDict = getMaterialMassFractions([matrix[0]], [1.0])
        if eleDict == {}: return {}
        #sort the elements according to atomic number
        #(not needed because the output will be a dictionary)
        keys = eleDict.keys()
        elementsList = [[getz(x),x] for x in keys]
        elementsList.sort()
    else:
        if (type(elementsList) != type([])) and\
           (type(elementsList) != tuple):
            elementsList  = [elementsList]
        if len(elementsList[0]) == 3:
            raysforloopindex = 0
            elementsList.sort()
            elementsRays = [x[2] for x in elementsList]
            elementsList = [[x[0],x[1]] for x in elementsList]
        else:
            elementsList = [[getz(x),x] for x in elementsList]
            elementsList.sort()
        eleDict = {}
        for z, ele in elementsList:
            eleDict[ele] = 1.0

    if energy <= 0.10:
        raise ValueError("Invalid Energy %.5g keV" % energy)

    #do the job
    outputDict = {}
    shelllist = ['K', 'L1', 'L2', 'L3','M1', 'M2', 'M3', 'M4', 'M5']
    for z,ele in elementsList:
        #use own unfiltered dictionary
        if ele in userElementDict:
            elementDict = userElementDict[ele]
        else:
            elementDict = _getUnfilteredElementDict(ele, energy)
        if not (ele in outputDict):
            outputDict[ele] ={}
        outputDict[ele]['mass fraction'] = eleDict[ele]
        if not ('rates' in outputDict[ele]):
            outputDict[ele]['rates'] = {}
        #get the fluorescence term for all shells
        fluoWeights = _getFluorescenceWeights(ele, energy, normalize = False,
                                                             cascade=cascade)
        outputDict[ele]['rays'] = elementDict['rays'] * 1

        if elementsRays is None:
            raysforloop = elementDict['rays']
        else:
            if type(elementsRays[raysforloopindex]) != type([]):
                raysforloop = [elementsRays[raysforloopindex] + " xrays"]
            else:
                raysforloop = []
                for item in elementsRays[raysforloopindex]:
                    raysforloop.append(item + " xrays")
            raysforloopindex +=1
        for rays in raysforloop:
            if rays not in elementDict['rays']:continue
            outputDict[ele][rays] = []
            rates    = []
            energies = []
            transitions = elementDict[rays]
            for transition in transitions:
                outputDict[ele][rays] += [transition]
                outputDict[ele][transition]={}
                outputDict[ele][transition]['rate'] = 0.0
                if transition[0] == "K":
                    rates.append(fluoWeights[0] *  elementDict[transition]['rate'])
                else:
                    rates.append(fluoWeights[shelllist.index(transition[0:2])] * elementDict[transition]['rate'])
                ene = elementDict[transition]['energy']
                energies += [ene]
                outputDict[ele][transition]['energy'] = ene

            #I do not know if to include this loop in the previous one (because rates are 0.0 sometimes)
            #attenuators
            coeffs = numpy.zeros(len(energies), numpy.float64)
            for attenuator in attenuators:
                formula   = attenuator[0]
                thickness = attenuator[1] * attenuator[2]
                coeffs +=  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])

            try:
                trans = numpy.exp(-coeffs)
            except OverflowError:
                for coef in coeffs:
                    if coef < 0.0:
                        raise ValueError("Positive exponent in attenuators transmission term")
                trans = 0.0 * coeffs

            #funnyfilters
            coeffs = numpy.zeros(len(energies), numpy.float64)
            funnyfactor = None
            for attenuator in funnyfilters:
                formula   = attenuator[0]
                thickness = attenuator[1] * attenuator[2]
                if funnyfactor is None:
                    funnyfactor = attenuator[3]
                else:
                    if abs(attenuator[3] - funnyfactor) > 0.0001:
                        raise ValueError(\
                            "All funny type filters must have same openning fraction")
                coeffs +=  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
            if funnyfactor is None:
                for i in range(len(rates)):
                    rates[i] *= trans[i]
            else:
                try:
                    transFunny = funnyfactor * numpy.exp(-coeffs) +\
                                 (1.0 - funnyfactor)
                except OverflowError:
                    #deal with underflows reported as overflows
                    transFunny = numpy.zeros(len(energies), numpy.float64)
                    for i in range(len(energies)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError(\
                                "Positive exponent in funnyfilters transmission term")
                        else:
                            try:
                                transFunny[i] = numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                    transFunny = funnyfactor * transFunny + \
                                 (1.0 - funnyfactor)
                for i in range(len(rates)):
                    rates[i] *= (trans[i] * transFunny[i])

            #user attenuators
            if userattenuators:
                utrans = numpy.ones((len(energies),), numpy.float64)
                for userattenuator in userattenuators:
                    utrans *= getTableTransmission(userattenuator, energies)
                for i in range(len(rates)):
                    rates[i] *= utrans[i]

            #detector term
            if detector is not None:
                formula   = detector[0]
                thickness = detector[1] * detector[2]
                coeffs   =  thickness * numpy.array(getMaterialMassAttenuationCoefficients(formula,1.0,energies)['total'])
                try:
                    trans = (1.0 - numpy.exp(-coeffs))
                except OverflowError:
                    #deal with underflows reported as overflows
                    trans = numpy.ones(len(rates), numpy.float64)
                    for i in range(len(rates)):
                        coef = coeffs[i]
                        if coef < 0.0:
                            raise ValueError(\
                                "Positive exponent in attenuators transmission term")
                        else:
                            try:
                                trans[i] = 1.0 - numpy.exp(-coef)
                            except OverflowError:
                                #if we are here we know it is not an overflow and trans[i] has the proper value
                                pass
                for i in range(len(rates)):
                    rates[i] *= trans[i]
            #matrix term
            formula   = matrix[0]
            thickness = matrix[1] * matrix[2]
            energies += [energy]
            if matrixmutotalfluorescence is None:
                allcoeffs   =  getMaterialMassAttenuationCoefficients(formula,1.0,energies)
                mutotal  = allcoeffs['total']
            else:
                mutotal = matrixmutotalfluorescence * 1
                if matrixmutotalexcitation is None:
                    mutotal.append(getMaterialMassAttenuationCoefficients(formula,
                                                                      1.0,
                                                                      energy)['total'][0])
                else:
                    mutotal.append(matrixmutotalexcitation)
            #muphoto  = allcoeffs['photo']
            muphoto  = getMaterialMassAttenuationCoefficients(ele,1.0,energy)['photo']
            del energies[-1]
            i = 0
            for transition in transitions:
                #thick target term
                if rates[i] <= 0.0:trans=0.0
                else:
                    if bottomExcitation:
                        denominator = (mutotal[-1] - mutotal[i] * (sinAlphaIn/sinAlphaOut))
                        if denominator == 0.0:
                            trans = thickness/sinAlphaIn
                            trans = -outputDict[ele]['mass fraction'] *\
                                     muphoto[-1] * trans *\
                                     numpy.exp(-trans*mutotal[-1])
                        else:
                            trans = -outputDict[ele]['mass fraction'] *\
                                     muphoto[-1]/denominator
                            #correction term
                            if thickness > 0.0:
                                try:
                                    expterm = numpy.exp(-(mutotal[-1]/sinAlphaIn) * thickness) -\
                                              numpy.exp(-(mutotal[i]/sinAlphaOut) * thickness)
                                except OverflowError:
                                    #print "overflow"
                                    if ((-(mutotal[-1]/sinAlphaIn) * thickness) > 0.0) or\
                                       ((-(mutotal[i]/sinAlphaOut) * thickness) > 0.0):
                                        raise ValueError("Positive exponent in transmission term")
                                    expterm = 0.0
                                trans *= expterm
                            else:
                                raise ValueError("Incorrect target density and/or thickness")
                        if trans < 0.0:
                            print("trans lower than 0.0. Reset to 0.0")
                            trans = 0.0

                    else:
                        trans = outputDict[ele]['mass fraction'] *\
                                 muphoto[-1]/(mutotal[-1] + mutotal[i] * (sinAlphaIn/sinAlphaOut))
                        #correction term
                        if thickness > 0.0:
                            if abs(sinAlphaIn) > 0.0:
                                try:
                                    expterm = numpy.exp(-((mutotal[-1]/sinAlphaIn) +(mutotal[i]/sinAlphaOut)) * thickness)
                                except OverflowError:
                                    #print "overflow"
                                    if -((mutotal[-1]/sinAlphaIn) +(mutotal[i]/sinAlphaOut)) * thickness > 0.0:
                                        raise ValueError(\
                                            "Positive exponent in transmission term")
                                    expterm = 0.0
                                trans *= (1.0 -  expterm)
                    #if ele == 'Pb':
                    #    oldRatio.append(newpeaks[i][0])
                    #    print "energy = %.3f ratio=%.5f transmission = %.5g final=%.5g" % (newpeaks[i][1], newpeaks[i][0],trans,trans * newpeaks[i][0])
                    rates[i] *=  trans
                outputDict[ele][transition]['rate'] = rates[i]
                i += 1
            outputDict[ele]['rates'][rays] = sum(rates)
            #outputDict[ele][rays]= Element[ele]['rays'] * 1
    return outputDict


def getLWeights(ele,energy=None, normalize = None, shellist = None):
    if normalize is None:normalize = True
    if shellist is None: shellist  = ['L1', 'L2', 'L3']
    if type(ele) == type(" "):
        pass
    else:
        ele = getsymbol(int(ele))
    if energy is None:
        #Use the L shell jumps
        w = getLJumpWeight(ele,excitedshells=[1.0,1.0,1.0])
        #weights due to Coster Kronig transitions and fluorescence yields
        ck= LShell.getCosterKronig(ele)
        w[0] = w[0]
        w[1] = w[1] + ck['f12'] * w[0]
        w[2] = w[2] + ck['f13'] * w[0] + ck['f23'] * w[1]
        omega = [ getomegal1(ele), getomegal2(ele), getomegal3(ele)]
        for i in range(len(w)):
            w[i] *= omega[i]
    else:
        #Take into account the cascade as in the getFluorescence method
        #The PyMCA fit was already using that when there was a matrix but
        #it was not shown in the Elements Info window.
        allweights = _getFluorescenceWeights(ele, energy, normalize = False, cascade = True)
        w   = allweights[1:4]
    if normalize:
        cum = sum(w)
        if cum > 0.0:
            for i in range(len(w)):
                w[i] /= cum
    return w

def getMWeights(ele,energy=None, normalize = None, shellist = None):
    if normalize is None:normalize = True
    if shellist is None: shellist  = ['M1', 'M2', 'M3', 'M4', 'M5']
    if type(ele) == type(" "):
        pass
    else:
        ele = getsymbol(int(ele))
    if energy is None:
        w = getMJumpWeight(ele,excitedshells=[1.0,1.0,1.0,1.0,1.0])
        #weights due to Coster Kronig transitions and fluorescence yields
        ck= MShell.getCosterKronig(ele)
        w[0] =  w[0]
        w[1] =  w[1] + ck['f12'] * w[0]
        w[2] =  w[2] + ck['f13'] * w[0] + ck['f23'] * w[1]
        w[3] =  w[3] + ck['f14'] * w[0] + ck['f24'] * w[1] + ck['f34'] * w[2]
        w[4] =  w[4] + ck['f15'] * w[0] + ck['f25'] * w[1] + ck['f35'] * w[2] + ck['f45'] * w[3]
        omega = [ getomegam1(ele), getomegam2(ele), getomegam3(ele), getomegam4(ele), getomegam5(ele)]
        for i in range(len(w)):
            w[i] *= omega[i]
    else:
        #Take into account the cascade as in the getFluorescence method
        #The PyMCA fit was already using that when there was a matrix but
        #it was not shown in the Elements Info window.
        allweights = _getFluorescenceWeights(ele, energy, normalize = False, cascade = True)
        w   = allweights[4:9]
    if normalize:
        cum = sum(w)
        for i in range(len(w)):
            if cum > 0.0:
                w[i] /= cum
    return w


def getxrayenergy(symbol,transition):
    if len(symbol) > 1:
        ele = symbol[0].upper() + symbol[1].lower()
    else:
        ele = symbol.upper()
    trans   = transition.upper()
    z = getz(ele)
    if z > len(ElementBinding):
        #Give the bindings of the last element
        energies = ElementBinding[-1]
    else:
        energies = ElementBinding[z-1]

    if len(trans) == 2:
        trans=trans[0:2]+'2'
    if trans[0:1] == 'K':
        i=1
        emax = energies[ElementShells.index('K')+1]
    elif trans[0:2] in ElementShells:
        i=2
        emax = energies[ElementShells.index(trans[0:2])+1]
    else:
        #print transition
        #print "Shell %s not in Element %s Shells" % (trans[0:2], ele)
        return -1

    if trans[i:i+2] in ElementShells:
        emin = energies[ElementShells.index(trans[i:i+2])+1]
    else:
        if (z > 80) and (trans[i:i+2] == "Q1"):
            emin = 0.003
        else:
            #print "HERE ",trans[i:i+2],transition,z
            #print "Final shell %s not in Element %s Shells" % (trans[i:i+1], ele)
            return -1

    if emin > emax:
        if z != 13:
            print("Warning, negative energy!")
            print("Please report this message:")
            print("Symbol=",symbol)
            print("emin = ",emin)
            print("emax = ",emax)
            print("z    = ",z)
            print("transition = ",transition)
            print("the transition will be ignored")
    return emax - emin

def isValidFormula(compound):
    #Avoid Fe 2 or Fe-2 or SRM-1832 being considered as valid formulae
    for c in [" ", "-", "_"]:
        if c in compound:
            return False
    #single element case
    if compound in Element.keys():return True
    try:
        elts= [ w for w in re.split('[0-9]', compound) if w != '' ]
        nbs= [ int(w) for w in re.split('[a-zA-Z]', compound) if w != '' ]
    except Exception:
        return False
    if len(elts)==1 and len(nbs)==0:
        if type(elts) == type([]):
            return False
        if elts in Element.keys():
            return True
        else:
            return False
    if (len(elts)==0 and len(nbs)==0) or (len(elts) != len(nbs)):return False
    return True

def isValidMaterial(compound):
    if compound in Material.keys():return True
    elif isValidFormula(compound):return True
    else:return False

def getMaterialKey(compound):
    matkeys = Material.keys()
    if compound in matkeys:return compound
    compoundHigh = compound.upper()
    matkeysHigh  = []
    for key in matkeys:
        matkeysHigh.append(key.upper())
    if compoundHigh in matkeysHigh:
        index = matkeysHigh.index(compoundHigh)
        return matkeys[index]
    return None

def getmassattcoef(compound, energy=None):
    """
    Usage: getmassattcoef(element symbol/composite, energy in kev)
	    Computes mass attenuation coefficients for a single element or a compound.
        It gets the info from files generated by XCOM
        If energy is not given, it gives back a dictionary with the form:
            dict['energy']     = [energies]
            dict['coherent']   = [coherent scattering cross section(energies)]
            dict['compton']    = [incoherent scattering cross section(energies)]
            dict['photo']      = [photoelectic effect cross section(energies)]
            dict['pair']       = [pair production cross section(energies)]
            dict['total']      = [total cross section]

	    A compound is defined with a string as follow:
		'C22H10N2O5' means 22 * C, 10 * H, 2 * N, 5 * O

		xsection = SUM(xsection(zi)*ni*ai) / SUM(ai*ni)

		zi = Z of each element
		ni = number of element zi
		ai = atomic weight of element zi

	    Result in cm2/g
	"""
    #single element case
    if compound in Element.keys():
        return getelementmassattcoef(compound,energy)
    elts= [ w for w in re.split('[0-9]', compound) if w != '' ]
    nbs= [ int(w) for w in re.split('[a-zA-Z]', compound) if w != '' ]
    if len(elts)==1 and len(nbs)==0:
        if elts in Element.keys():
            return getelementmassattcoef(compound,energy)
        else:
            return {}
    if (len(elts)==0 and len(nbs)==0) or (len(elts) != len(nbs)):
        return {}

    fraction = [Element[elt]['mass'] *nb for (elt, nb) in zip(elts, nbs) ]
    div      = sum(fraction)
    fraction = [x/div for x in fraction]
    #print "fraction = ",fraction
    ddict={}
    ddict['energy']   = []
    ddict['coherent'] = []
    ddict['compton']  = []
    ddict['photo']    = []
    ddict['pair']     = []
    ddict['total']    = []
    eltindex = 0
    if energy is None:
        energy=[]
        for ele in elts:
            xcom_data = getelementmassattcoef(ele,None)['energy']
            for ene in xcom_data:
                if ene not in energy:
                    energy.append(ene)
        energy.sort()

    for ele in elts:
        xcom_data = getelementmassattcoef(ele,None)
        #now I have to interpolate at the different energies
        if not hasattr(energy, "__len__"):
            energy =[energy]
        eneindex = 0
        for ene in energy:
            if ene < 1.0:
                if PyMcaEPDL97.EPDL97_DICT[ele]['original']:
                    #make sure the binding energies are those used by this module and not EADL ones
                    PyMcaEPDL97.setElementBindingEnergies(ele,
                                                          Element[ele]['binding'])
                tmpDict = PyMcaEPDL97.getElementCrossSections(ele, ene)
                cohe  = tmpDict['coherent'][0]
                comp  = tmpDict['compton'][0]
                photo = tmpDict['photo'][0]
                pair  = 0.0
            else:
                i0=max(numpy.nonzero(xcom_data['energy'] <= ene)[0])
                i1=min(numpy.nonzero(xcom_data['energy'] >= ene)[0])
                if (i1 == i0) or (i0>i1):
                    cohe=xcom_data['coherent'][i1]
                    comp=xcom_data['compton'][i1]
                    photo=xcom_data['photo'][i1]
                    pair=xcom_data['pair'][i1]
                else:
                    if LOGLOG:
                        A=xcom_data['energylog10'][i0]
                        B=xcom_data['energylog10'][i1]
                        logene = numpy.log10(ene)
                        c2=(logene-A)/(B-A)
                        c1=(B-logene)/(B-A)
                    else:
                        A=xcom_data['energy'][i0]
                        B=xcom_data['energy'][i1]
                        c2=(ene-A)/(B-A)
                        c1=(B-ene)/(B-A)
                    cohe= pow(10.0,c2*xcom_data['coherentlog10'][i1]+\
                                   c1*xcom_data['coherentlog10'][i0])
                    comp= pow(10.0,c2*xcom_data['comptonlog10'][i1]+\
                                   c1*xcom_data['comptonlog10'][i0])
                    photo=pow(10.0,c2*xcom_data['photolog10'][i1]+\
                                   c1*xcom_data['photolog10'][i0])
                    if xcom_data['pair'][i1] > 0.0:
                        c2 = c2*numpy.log10(xcom_data['pair'][i1])
                        if xcom_data['pair'][i0] > 0.0:
                            c1 = c1*numpy.log10(xcom_data['pair'][i0])
                            pair = pow(10.0,c1+c2)
                        else:
                            pair =0.0
                    else:
                        pair =0.0
            if eltindex == 0:
                ddict['energy'].append(ene)
                ddict['coherent'].append(cohe *fraction[eltindex])
                ddict['compton'].append(comp *fraction[eltindex])
                ddict['photo'].append(photo *fraction[eltindex])
                ddict['pair'].append(pair*fraction[eltindex])
                ddict['total'].append((cohe+comp+photo+pair)*fraction[eltindex])
            else:
                ddict['coherent'][eneindex] += cohe  *fraction[eltindex]
                ddict['compton'] [eneindex] += comp  *fraction[eltindex]
                ddict['photo']   [eneindex] += photo *fraction[eltindex]
                ddict['pair']    [eneindex] += pair  *fraction[eltindex]
                ddict['total']   [eneindex] += (cohe+comp+photo+pair) * fraction[eltindex]
            eneindex += 1
        eltindex += 1
    return ddict

def __materialInCompoundList(lst):
    for item in lst:
        if item in Material.keys():
            return True
    return False

def getTableTransmission(tableDict, energy):
    """
    tableDict is a dictionary containing the keys energy and transmission.
    It gets the transmission at the given energy by linear interpolation.

    The energy is in keV.
    Values below the lowest energy get transmission equal to the first table value.
    Values above the greates energy get transmission equal to the last table value.
    """
    # use a lazy import
    from fisx import TransmissionTable
    tTable = TransmissionTable()
    if type(tableDict) == type([]):
        tTable.setTransmissionTableFromLists(tableDict[0], tableDict[1]) 
    else:
        tTable.setTransmissionTableFromLists(tableDict["energy"],
                                    tableDict["transmission"])
    return tTable.getTransmission(energy)


def getMaterialTransmission(compoundList0, fractionList0, energy0 = None,
                            density=None, thickness=None, listoutput=True):
    """
    Usage:
    getMaterialTransmission(compoundList, fractionList, energy = None,
                            density=None, thickness=None):

    Input

    compoundlist - List of elements, compounds or materials
    fractionlist - List of floats indicating the amount of respective material
    energy       - Photon energy (it can be a list)
    density      - Density in g/cm3 (default is 1.0)
    thickness    - Thickness in cm  (default is 1.0)

    The product density * thickness has to be in g/cm2

    Output

    Detailed dictionary.
    """
    if density   is None: density = 1.0
    if thickness is None: thickness = 1.0
    dict = getMaterialMassAttenuationCoefficients(compoundList0,
                                                 fractionList0, energy0)
    energy = numpy.array(dict['energy'],numpy.float64)
    mu     = numpy.array(dict['total'],numpy.float64) * density * thickness
    if energy0 is not None:
        if type(energy0) != type([]):
            listoutput = False
    if listoutput:
        dict['energy']   = energy.tolist()
        dict['density']  = density
        dict['thickness'] = thickness
        dict['transmission'] = numpy.exp(-mu).tolist()
    else:
        dict['energy']   = energy
        dict['density']  = density
        dict['thickness'] = thickness
        dict['transmission'] = numpy.exp(-mu)
    return dict

def getMaterialMassFractions(compoundList0, fractionList0):
    return getMaterialMassAttenuationCoefficients(compoundList0, fractionList0, None, massfractions=True)

def getMaterialMassAttenuationCoefficients(compoundList0, fractionList0, energy0 = None,massfractions=False):
    """
    Usage:
        getMaterialMassAttenuationCoefficients(compoundList, fractionList,
                                     energy = None,massfractions=False)
    compoundList - List of compounds into the material
    fractionList - List of masses of each compound
    energy       - Energy at which the values are desired
    massfractions- Flag to supply mass fractions on output
    """
    if type(compoundList0) != type([]):
        compoundList = [compoundList0]
    else:
        compoundList = compoundList0
    if type(fractionList0) == numpy.ndarray:
        fractionList = fractionList0.tolist()
    elif type(fractionList0) != type([]):
        fractionList = [fractionList0]
    else:
        fractionList = fractionList0
    fractionList = [float(x) for x in fractionList]

    while __materialInCompoundList(compoundList):
        total=sum(fractionList)
        compoundFractionList = [x/total for x in fractionList]
        #allow materials in compoundList
        newcompound = []
        newfraction = []
        deleteitems = []
        for compound in compoundList:
            if compound in Material.keys():
                if type(Material[compound]['CompoundList']) != type([]):
                    Material[compound]['CompoundList']=[Material[compound]['CompoundList']]
                if type(Material[compound]['CompoundFraction']) != type([]):
                    Material[compound]['CompoundFraction']=[Material[compound]['CompoundFraction']]
                Material[compound]['CompoundFraction'] = [float(x) for x in Material[compound]['CompoundFraction']]
                total = sum(Material[compound]['CompoundFraction'])
                j = compoundList.index(compound)
                compoundfraction = fractionList[j]
                i = 0
                for item in Material[compound]['CompoundList']:
                    newcompound.append(item)
                    newfraction.append(Material[compound]['CompoundFraction'][i] * compoundfraction /total)
                    i += 1
                deleteitems.append(j)
        if len(deleteitems):
            deleteitems.reverse()
            for i in deleteitems:
                del compoundList[i]
                del fractionList[i]
            for i in range(len(newcompound)):
                compoundList.append(newcompound[i])
                fractionList.append(newfraction[i])
    total=sum(fractionList)
    compoundFractionList = [float(x)/total for x in fractionList]
    materialElements = {}
    energy = energy0
    if energy0 is not None:
        if type(energy0) == type(2.):
            energy = [energy0]
        elif type(energy0) == type(1):
            energy = [1.0 * energy0]
        elif type(energy0) == numpy.ndarray:
            energy = energy0.tolist()

    for compound, compoundFraction in zip(compoundList, compoundFractionList):
        elts=[]
        #get energy list
        if compound in Element.keys():
            elts=[compound]
            nbs =[1]
        else:
            elts= [ w for w in re.split('[0-9]', compound) if w != '' ]
            try:
                nbs= [ int(w) for w in re.split('[a-zA-Z]', compound) if w != '' ]
            except Exception:
                raise ValueError("Compound '%s' not understood" % compound)
            if len(elts)==1 and len(nbs)==0:
                elts=[compound]
                nbs =[1]
        if (len(elts)==0 and len(nbs)==0) or (len(elts) != len(nbs)):
            print("compound %s not understood" % compound)
            raise ValueError("compound %s not understood" % compound)

        #the proportion of the element in that compound times the compound fraction
        fraction = [Element[elt]['mass'] *nb for (elt, nb) in zip(elts, nbs) ]
        div      = compoundFraction/sum(fraction)
        fraction = [x * div for x in fraction]
        if energy is None:
            #get energy list
            energy = []
            for ele in elts:
                xcom_data = getelementmassattcoef(ele,None)['energy']
                for ene in xcom_data:
                    if ene not in energy:
                        energy.append(ene)
        for ele in elts:
            if ele not in materialElements.keys():
                materialElements[ele]  = fraction[elts.index(ele)]
            else:
                materialElements[ele] += fraction[elts.index(ele)]
    if massfractions == True:
        return materialElements
    if energy0 is None:
        energy.sort()

    #I have the energy grid, the elements and their fractions
    dict={}
    dict['energy']   = []
    dict['coherent'] = []
    dict['compton']  = []
    dict['photo']    = []
    dict['pair']     = []
    dict['total']    = []
    eltindex = 0
    for ele in materialElements.keys():
        if 'xcom' in Element[ele]:
            xcom_data = Element[ele]['xcom']
        else:
            xcom_data = getelementmassattcoef(ele,None)
        #now I have to interpolate at the different energies
        if (type(energy) != type([])):
            energy =[energy]
        eneindex = 0
        for ene in energy:
            if ene < 1.0:
                if PyMcaEPDL97.EPDL97_DICT[ele]['original']:
                    #make sure the binding energies are those used by this module and not EADL ones
                    PyMcaEPDL97.setElementBindingEnergies(ele,
                                                          Element[ele]['binding'])
                tmpDict = PyMcaEPDL97.getElementCrossSections(ele, ene)
                cohe  = tmpDict['coherent'][0]
                comp  = tmpDict['compton'][0]
                photo = tmpDict['photo'][0]
                pair  = 0.0
            else:
                i0=max(numpy.nonzero(xcom_data['energy'] <= ene)[0])
                i1=min(numpy.nonzero(xcom_data['energy'] >= ene)[0])
                if (i1 == i0) or (i0>i1):
                    cohe=xcom_data['coherent'][i1]
                    comp=xcom_data['compton'][i1]
                    photo=xcom_data['photo'][i1]
                    pair=xcom_data['pair'][i1]
                else:
                    if LOGLOG:
                        A=xcom_data['energylog10'][i0]
                        B=xcom_data['energylog10'][i1]
                        logene = numpy.log10(ene)
                        c2=(logene-A)/(B-A)
                        c1=(B-logene)/(B-A)
                    else:
                        A=xcom_data['energy'][i0]
                        B=xcom_data['energy'][i1]
                        c2=(ene-A)/(B-A)
                        c1=(B-ene)/(B-A)
                    cohe= pow(10.0,c2*xcom_data['coherentlog10'][i1]+\
                                   c1*xcom_data['coherentlog10'][i0])
                    comp= pow(10.0,c2*xcom_data['comptonlog10'][i1]+\
                                   c1*xcom_data['comptonlog10'][i0])
                    photo=pow(10.0,c2*xcom_data['photolog10'][i1]+\
                                   c1*xcom_data['photolog10'][i0])
                    if xcom_data['pair'][i1] > 0.0:
                        c2 = c2*numpy.log10(xcom_data['pair'][i1])
                        if xcom_data['pair'][i0] > 0.0:
                            c1 = c1*numpy.log10(xcom_data['pair'][i0])
                            pair = pow(10.0,c1+c2)
                        else:
                            pair =0.0
                    else:
                        pair =0.0
            if eltindex == 0:
                dict['energy'].append(ene)
                dict['coherent'].append(cohe * materialElements[ele])
                dict['compton'].append(comp * materialElements[ele])
                dict['photo'].append(photo * materialElements[ele])
                dict['pair'].append(pair* materialElements[ele])
                dict['total'].append((cohe+comp+photo+pair)* materialElements[ele])
            else:
                dict['coherent'][eneindex] += cohe  * materialElements[ele]
                dict['compton'] [eneindex] += comp  * materialElements[ele]
                dict['photo']   [eneindex] += photo * materialElements[ele]
                dict['pair']    [eneindex] += pair  * materialElements[ele]
                dict['total']   [eneindex] += (cohe+comp+photo+pair) *  materialElements[ele]
            eneindex += 1
        eltindex += 1
    return dict


def getcandidates(energy,threshold=None,targetrays=None):
    if threshold  is None:
        threshold = 0.010
    if targetrays is None:
        targetrays=['K', 'L1', 'L2', 'L3', 'M']
    if type(energy) != type([]):
        energy = [energy]
    if type(targetrays) != type([]):
        targetrays = [targetrays]
    #K lines
    lines ={}
    index = 0
    for ene in energy:
        lines[index] = {'energy':ene,
                        'elements':[]}
        for ele in ElementList:
            for ray in targetrays:
                rays = ray + " xrays"
                if 'rays' in Element[ele]:
                    for transition in Element[ele][rays]:
                        e = Element[ele][transition]['energy']
                        r = Element[ele][transition]['rate']
                        if abs(ene-e) < threshold:
                            if ele not in lines[index]['elements']:
                                lines[index]['elements'].append(ele)
                                lines[index][ele]=[]
                            lines[index][ele].append([transition, e, r])
        index += 1
    return lines


def getElementFormFactor(ele, theta, energy):
    if ele in CoherentScattering.COEFFICIENTS.keys():
        return CoherentScattering.getElementFormFactor(ele, theta, energy)
    else:
        try:
            z = int(ele)
            ele = getsymbol(z)
            return CoherentScattering.getElementFormFactor(ele, theta, energy)
        except Exception:
            raise ValueError("Unknown element %s" % ele)


def getElementCoherentDifferentialCrossSection(ele, theta, energy, p1=None):
    #if ele in CoherentScattering.COEFFICIENTS.keys():
    if ele in ElementList:
        value=CoherentScattering.\
            getElementCoherentDifferentialCrossSection(ele, theta, energy, p1)
    else:
        try:
          z = int(ele)
          ele = getsymbol(z)
          value=CoherentScattering.\
            getElementCoherentDifferentialCrossSection(ele, theta, energy, p1)
        except Exception:
          raise ValueError("Unknown element %s" % ele)
    #convert from cm2/atom to cm2/g
    return (value * AVOGADRO_NUMBER)/ Element[ele]['mass']


def getElementIncoherentScatteringFunction(ele, theta, energy):
    if ele in ElementList:
        value = IncoherentScattering.\
            getElementIncoherentScatteringFunction(ele, theta, energy)
    else:
        try:
          z = int(ele)
          ele = getsymbol(z)
          value = IncoherentScattering.\
                getElementIncoherentScatteringFunction(ele, theta, energy)
        except Exception:
          raise ValueError("Unknown element %s" % ele)
    return value

def getElementComptonDifferentialCrossSection(ele, theta, energy, p1=None):
    if ele in ElementList:
        value = IncoherentScattering.\
            getElementComptonDifferentialCrossSection(ele, theta, energy, p1)
    else:
        try:
          z = int(ele)
          ele = getsymbol(z)
          value = IncoherentScattering.\
            getElementComptonDifferentialCrossSection(ele, theta, energy, p1)
        except Exception:
          raise ValueError("Unknown element %s" % ele)
    return (value * 6.022142E23)/ Element[ele]['mass']

def getelementmassattcoef(ele,energy=None):
    """
    Usage: getelementmassattcoef(element symbol, energy in kev)
        It gets the info from files generated by XCOM
        If energy is not given, it gives back a dictionary with the form:
            dict['energy']     = [energies]
            dict['coherent']   = [coherent scattering cross section(energies)]
            dict['compton']    = [incoherent scattering cross section(energies)]
            dict['photo']      = [photoelectic effect cross section(energies)]
            dict['pair']       = [pair production cross section(energies)]
            dict['total']      = [total cross section]
    """
    if 'xcom' not in Element[ele].keys():
        dirmod = PyMcaDataDir.PYMCA_DATA_DIR
        #read xcom file
        #print dirmod+"/"+ele+".mat"
        xcomfile = os.path.join(dirmod, "attdata")
        xcomfile = os.path.join(xcomfile, ele+".mat")
        if not os.path.exists(xcomfile):
            #freeze does bad things with the path ...
            dirmod = os.path.dirname(dirmod)
            xcomfile = os.path.join(dirmod, "attdata")
            xcomfile = os.path.join(xcomfile, ele+".mat")
            if dirmod.lower().endswith(".zip"):
                dirmod = os.path.dirname(dirmod)
                xcomfile = os.path.join(dirmod, "attdata")
                xcomfile = os.path.join(xcomfile, ele+".mat")
            if not os.path.exists(xcomfile):
                print("Cannot find file ",xcomfile)
                raise IOError("Cannot find %s" % xcomfile)
        f = open(xcomfile, 'r')
        line=f.readline()
        while (line.split('ENERGY')[0] == line):
            line = f.readline()
        Element[ele]['xcom'] = {}
        Element[ele]['xcom']['energy']   =[]
        Element[ele]['xcom']['coherent'] =[]
        Element[ele]['xcom']['compton']  =[]
        Element[ele]['xcom']['photo']  =[]
        Element[ele]['xcom']['pair']     =[]
        Element[ele]['xcom']['total']    =[]
        line = f.readline()
        while (line.split('COHERENT')[0] == line):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['energy'].append(float(value)*1000.)
            line = f.readline()
        Element[ele]['xcom']['energy']=numpy.array(Element[ele]['xcom']['energy'])
        line = f.readline()
        while (line.split('INCOHERENT')[0] == line):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['coherent'].append(float(value))
            line = f.readline()
        Element[ele]['xcom']['coherent']=numpy.array(Element[ele]['xcom']['coherent'])
        line = f.readline()
        while (line.split('PHOTO')[0] == line):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['compton'].append(float(value))
            line = f.readline()
        Element[ele]['xcom']['compton']=numpy.array(Element[ele]['xcom']['compton'])
        line = f.readline()
        while (line.split('PAIR')[0] == line):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['photo'].append(float(value))
            line = f.readline()
        line = f.readline()
        while (line.split('PAIR')[0] == line):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['pair'].append(float(value))
            line = f.readline()
        i = 0
        line = f.readline()
        while (len(line)):
            line = line.split()
            for value in line:
                Element[ele]['xcom']['pair'][i] += float(value)
                i += 1
            line = f.readline()
        f.close()
        # next line gave problems under windows
        # just try numpy.argsort([1,1,1,1,1]) under linux and windows to see
        # what I mean
        # i1=numpy.argsort(Element[ele]['xcom']['energy']) did not work
        # (uses quicksort and gives problems with Pb not passing tests)
        i1=numpy.argsort(Element[ele]['xcom']['energy'], kind='mergesort')
        Element[ele]['xcom']['energy']=numpy.take(Element[ele]['xcom']['energy'],i1)
        Element[ele]['xcom']['coherent']=numpy.take(Element[ele]['xcom']['coherent'],i1)
        Element[ele]['xcom']['compton']=numpy.take(Element[ele]['xcom']['compton'],i1)
        Element[ele]['xcom']['photo']=numpy.take(Element[ele]['xcom']['photo'],i1)
        Element[ele]['xcom']['pair']=numpy.take(Element[ele]['xcom']['pair'],i1)
        if Element[ele]['xcom']['coherent'][0] <= 0:
           Element[ele]['xcom']['coherent'][0] = Element[ele]['xcom']['coherent'][1] * 1.0
        try:
            Element[ele]['xcom']['energylog10']=numpy.log10(Element[ele]['xcom']['energy'])
            Element[ele]['xcom']['coherentlog10']=numpy.log10(Element[ele]['xcom']['coherent'])
            Element[ele]['xcom']['comptonlog10']=numpy.log10(Element[ele]['xcom']['compton'])
            Element[ele]['xcom']['photolog10']=numpy.log10(Element[ele]['xcom']['photo'])
        except Exception:
            raise ValueError("Problem calculating logaritm of %s.mat file data" % ele)
        for i in range(0,len(Element[ele]['xcom']['energy'])):
            Element[ele]['xcom']['total'].append(Element[ele]['xcom']['coherent'][i]+\
                                                 Element[ele]['xcom']['compton'] [i]+\
                                                 Element[ele]['xcom']['photo'] [i]+\
                                                 Element[ele]['xcom']['pair'] [i])

    if energy is None:
        return  Element[ele]['xcom']
    ddict={}
    ddict['energy']   = []
    ddict['coherent'] = []
    ddict['compton']  = []
    ddict['photo']    = []
    ddict['pair']     = []
    ddict['total']    = []
    if not hasattr(energy, "__len__"):
        energy =[energy]
    for ene in energy:
        if ene < 1.0:
            if PyMcaEPDL97.EPDL97_DICT[ele]['original']:
                #make sure the binding energies are those used by this module and not EADL ones
                PyMcaEPDL97.setElementBindingEnergies(ele,
                                                      Element[ele]['binding'])
            tmpDict = PyMcaEPDL97.getElementCrossSections(ele, ene)
            cohe  = tmpDict['coherent'][0]
            comp  = tmpDict['compton'][0]
            photo = tmpDict['photo'][0]
            pair  = 0.0
        else:
            i0=max(numpy.nonzero(Element[ele]['xcom']['energy'] <= ene)[0])
            i1=min(numpy.nonzero(Element[ele]['xcom']['energy'] >= ene)[0])
            if i1 <= i0:
                cohe=Element[ele]['xcom']['coherent'][i1]
                comp=Element[ele]['xcom']['compton'][i1]
                photo=Element[ele]['xcom']['photo'][i1]
                pair=Element[ele]['xcom']['pair'][i1]
            else:
                if LOGLOG:
                    A=Element[ele]['xcom']['energylog10'][i0]
                    B=Element[ele]['xcom']['energylog10'][i1]
                    logene = numpy.log10(ene)
                    c2=(logene-A)/(B-A)
                    c1=(B-logene)/(B-A)
                else:
                    A=Element[ele]['xcom']['energy'][i0]
                    B=Element[ele]['xcom']['energy'][i1]
                    c2=(ene-A)/(B-A)
                    c1=(B-ene)/(B-A)

                cohe= pow(10.0,c2*Element[ele]['xcom']['coherentlog10'][i1]+\
                               c1*Element[ele]['xcom']['coherentlog10'][i0])
                comp= pow(10.0,c2*Element[ele]['xcom']['comptonlog10'][i1]+\
                               c1*Element[ele]['xcom']['comptonlog10'][i0])
                photo=pow(10.0,c2*Element[ele]['xcom']['photolog10'][i1]+\
                               c1*Element[ele]['xcom']['photolog10'][i0])
                if Element[ele]['xcom']['pair'][i1] > 0.0:
                    c2 = c2*numpy.log10(Element[ele]['xcom']['pair'][i1])
                    if Element[ele]['xcom']['pair'][i0] > 0.0:
                        c1 = c1*numpy.log10(Element[ele]['xcom']['pair'][i0])
                        pair = pow(10.0,c1+c2)
                    else:
                        pair =0.0
                else:
                    pair =0.0
        ddict['energy'].append(ene)
        ddict['coherent'].append(cohe)
        ddict['compton'].append(comp)
        ddict['photo'].append(photo)
        ddict['pair'].append(pair)
        ddict['total'].append(cohe+comp+photo+pair)
    return ddict

def getElementLShellRates(symbol,energy=None,photoweights = None):
    """
    getElementLShellRates(symbol,energy=None, photoweights = None)
    gives LShell branching ratios at a given energy
    weights due to photoeffect, fluorescence and Coster-Kronig
    transitions are calculated and used unless photoweights is False,
    in that case weights = [1.0, 1.0, 1.0, 1.0, 1.0]
    """
    if photoweights is None:photoweights=True
    if photoweights:
        weights = getLWeights(symbol,energy=energy)
    else:
        weights = [1.0, 1.0, 1.0]
    z = getz(symbol)
    index = z-1
    shellrates = numpy.arange(len(LShell.ElementLShellTransitions)).astype(numpy.float64)
    shellrates[0] = z
    shellrates[1] = 0
    lo = 0
    if 'Z' in LShell.ElementL1ShellTransitions[0:2]:lo=1
    if 'TOTAL' in LShell.ElementL1ShellTransitions[0:2]:lo=lo+1
    n1 = len(LShell.ElementL1ShellTransitions)
    rates = numpy.array(LShell.ElementL1ShellRates[index]).astype(numpy.float64)
    shellrates[lo:n1] = (rates[lo:] / (sum(rates[lo:]) + (sum(rates[lo:])==0))) * weights[0]
    n2 = n1 + len(LShell.ElementL2ShellTransitions) - lo
    rates = numpy.array(LShell.ElementL2ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[lo:] / (sum(rates[lo:]) + (sum(rates[lo:])==0))) * weights[1]
    n1 = n2
    n2 = n1 + len(LShell.ElementL3ShellTransitions) - lo
    rates = numpy.array(LShell.ElementL3ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[lo:] / (sum(rates[lo:]) + (sum(rates[lo:])==0))) * weights[2]
    return shellrates

def getElementMShellRates(symbol,energy=None, photoweights = None):
    """
    getElementMShellRates(symbol,energy=None, photoweights = None)
    gives MShell branching ratios at a given energy
    weights due to photoeffect, fluorescence and Coster-Kronig
    transitions are calculated and used unless photoweights is False,
    in that case weights = [1.0, 1.0, 1.0, 1.0, 1.0]
    """
    if photoweights is None:photoweights=True
    if photoweights:
        weights = getMWeights(symbol,energy=energy)
    else:
        weights = [1.0, 1.0, 1.0, 1.0, 1.0]
    z = getz(symbol)
    index = z-1
    shellrates = numpy.arange(len(MShell.ElementMShellTransitions)).astype(numpy.float64)
    shellrates[0] = z
    shellrates[1] = 0
    n1 = len(MShell.ElementM1ShellTransitions)
    rates = numpy.array(MShell.ElementM1ShellRates[index]).astype(numpy.float64)
    shellrates[2:n1] = (rates[2:] / (sum(rates[2:]) + (sum(rates[2:])==0))) * weights[0]
    n2 = n1 + len(MShell.ElementM2ShellTransitions) - 2
    rates = numpy.array(MShell.ElementM2ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[2:] / (sum(rates[2:]) + (sum(rates[2:])==0))) * weights[1]
    n1 = n2
    n2 = n1 + len(MShell.ElementM3ShellTransitions) - 2
    rates = numpy.array(MShell.ElementM3ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[2:] / (sum(rates[2:]) + (sum(rates[2:])==0))) * weights[2]
    n1 = n2
    n2 = n1 + len(MShell.ElementM4ShellTransitions) - 2
    rates = numpy.array(MShell.ElementM4ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[2:] / (sum(rates[2:]) + (sum(rates[2:])==0)))* weights[3]
    n1 = n2
    n2 = n1 + len(MShell.ElementM5ShellTransitions) - 2
    rates = numpy.array(MShell.ElementM5ShellRates[index]).astype(numpy.float64)
    shellrates[n1:n2] = (rates[2:] / (sum(rates[2:]) + (sum(rates[2:])==0)))* weights[4]
    return shellrates


def _getUnfilteredElementDict(symbol, energy, photoweights=None):
    if photoweights == None:photoweights = False
    ddict = {}
    if len(symbol) > 1:
        ele = symbol[0].upper() + symbol[1].lower()
    else:
        ele = symbol.upper()
    #fill the dictionary
    ddict['rays']=[]
    z = getz(ele)
    for n in range(len(ElementXrays)):
        rays = ElementXrays[n]
        if   (rays == 'L xrays'):
            shellrates = getElementLShellRates(ele,energy=energy,photoweights=photoweights)
        elif (rays == 'M xrays'):
            shellrates = getElementMShellRates(ele,energy=energy,photoweights=photoweights)
        else:
            shellrates = ElementShellRates[n][z-1]
        shelltransitions = ElementShellTransitions[n]
        ddict[rays] = []
        minenergy = MINENERGY
        if 'TOTAL' in shelltransitions:
            indexoffset = 2
        else:
            indexoffset = 1
        for i in range(indexoffset, len(shelltransitions)):
                rate = shellrates [i]
                transition = shelltransitions[i]
                if n==0:ddict[transition] = {}
                if (rays == "Ka xrays"):
                    xenergy = getxrayenergy(ele,transition.replace('a',''))
                elif (rays == "Kb xrays"):
                    xenergy = getxrayenergy(ele,transition.replace('b',''))
                else:
                    xenergy = getxrayenergy(ele,transition.replace('*',''))
                if xenergy > minenergy:
                    ddict[transition] = {}
                    ddict[rays].append(transition)
                    ddict[transition]['energy'] = xenergy
                    ddict[transition]['rate']   = rate
                    if rays not in ddict['rays']:
                        ddict['rays'].append(rays)
    ddict['buildparameters']={}
    ddict['buildparameters']['energy']    = energy
    ddict['buildparameters']['minenergy'] = minenergy
    ddict['buildparameters']['minrate']   = 0.0
    return ddict


def _updateElementDict(symbol, dict, energy=None, minenergy=MINENERGY, minrate=0.0010,
                                                     normalize = None, photoweights = None):
    if normalize   is None: normalize   = True
    if photoweights is None: photoweights = True
    if len(symbol) > 1:
        ele = symbol[0].upper() + symbol[1].lower()
    else:
        ele = symbol[0].upper()
    #reset existing dictionary
    if 'rays' in dict:
        for rays in dict['rays']:
            for transition in dict[rays]:
                #print("transition deleted = ",transition)
                del dict[transition]
            #print "rays deleted = ",rays
            del dict[rays]
    #fill the dictionary
    dict['rays']=[]
    z = getz(ele)
    for n in range(len(ElementXrays)):
        rays = ElementXrays[n]
        if rays == 'L xrays':
            shellrates = getElementLShellRates(ele,energy=energy,photoweights=photoweights)
        elif rays == 'M xrays':
            shellrates = getElementMShellRates(ele,energy=energy,photoweights=photoweights)
        else:
            shellrates = ElementShellRates[n][z-1]
        shelltransitions = ElementShellTransitions[n]
        dict[rays] = []
        if 'TOTAL' in shelltransitions:
            transitionoffset = 2
        else:
            transitionoffset = 1
        maxrate = max(shellrates[transitionoffset:])
        cum     = 0.0
        if maxrate > minrate:
            for i in range(transitionoffset, len(shelltransitions)):
                rate = shellrates [i]
                if (rate/maxrate) > minrate:
                    transition = shelltransitions[i]
                    if (rays == "Ka xrays"):
                        xenergy = getxrayenergy(ele,transition.replace('a',''))
                    elif (rays == "Kb xrays"):
                        xenergy = getxrayenergy(ele,transition.replace('b',''))
                    else:
                        xenergy = getxrayenergy(ele,transition.replace('*',''))
                    if (xenergy > minenergy) or (n == 0) :
                        dict[transition] = {}
                        dict[rays].append(transition)
                        dict[transition]['energy'] = xenergy
                        dict[transition]['rate']   = rate
                        cum += rate
                        if rays not in dict['rays']:
                            dict['rays'].append(rays)
            #cum = 1.00
            if normalize:
                if cum > 0.0:
                    for transition in dict[rays]:
                        dict[transition]['rate'] /= cum
    dict['buildparameters']={}
    dict['buildparameters']['energy']    = energy
    dict['buildparameters']['minenergy'] = minenergy
    dict['buildparameters']['minrate']   = minrate

def updateDict(energy=None, minenergy=MINENERGY, minrate=0.0010, cb=True):
    for ele in ElementList:
        _updateElementDict(ele, Element[ele], energy=energy, minenergy=minenergy, minrate=minrate)
    if cb:
        _updateCallback()
    return

def _getMaterialDict():
    cDict = ConfigDict.ConfigDict()
    dirmod = PyMcaDataDir.PYMCA_DATA_DIR
    matdict = os.path.join(dirmod,"attdata")
    matdict = os.path.join(matdict,"MATERIALS.DICT")
    if not os.path.exists(matdict):
        #freeze does bad things with the path ...
        dirmod = os.path.dirname(dirmod)
        matdict = os.path.join(dirmod, "attdata")
        matdict = os.path.join(matdict, "MATERIALS.DICT")
        if not os.path.exists(matdict):
            if dirmod.lower().endswith(".zip"):
                dirmod = os.path.dirname(dirmod)
                matdict = os.path.join(dirmod, "attdata")
                matdict = os.path.join(matdict, "MATERIALS.DICT")
    if not os.path.exists(matdict):
        print("Cannot find file ", matdict)
        #raise IOError("Cannot find %s" % matdict)
        return {}
    cDict.read(matdict)
    return cDict

class BoundMethodWeakref:
    """Helper class to get a weakref to a bound method"""
    def __init__(self, bound_method, onDelete=None):
        def remove(ref):
            if self.deleteCb is not None:
                self.deleteCb(self)

        self.deleteCb = onDelete
        self.func_ref = weakref.ref(bound_method.im_func, remove)
        self.obj_ref = weakref.ref(bound_method.im_self, remove)

    def __call__(self):
        obj = self.obj_ref()
        if obj is not None:
            func = self.func_ref()
            if func is not None:
                return func.__get__(obj)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.func_ref == other.func_ref and
                self.obj_ref == other.obj_ref)

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        if self.func_ref != other.func_ref:
            return self.func_ref < other.func_ref
        return self.obj_ref < other.obj_ref

_registeredCallbacks=[]

def registerUpdate(callback):
    if not hasattr(callback, "__call__"):
        raise TypeError("It should be a callable method")

    def delCallback(ref):
        try:
            i = _registeredCallbacks.index(ref)
            del _registeredCallbacks[i]
        except Exception:
            pass

    if hasattr(callback, 'im_self') and callback.im_self is not None:
        ref = BoundMethodWeakref(callback, delCallback)
    else:
        # function weakref
        ref = weakref.ref(callback, delCallback)

    if ref not in  _registeredCallbacks:
        _registeredCallbacks.append(ref)


def _updateCallback():
    for methodref in _registeredCallbacks:
        method = methodref()
        if method is not None:
            method()


Element={}
for ele in ElementList:
    z = getz(ele)
    Element[ele]={}
    Element[ele]['Z']       = z
    Element[ele]['name']    = ElementsInfo[z-1][4]
    Element[ele]['mass']    = ElementsInfo[z-1][5]
    Element[ele]['density'] = ElementsInfo[z-1][6]/1000.
    Element[ele]['binding'] = {}
    i=0
    for shell in ElementShells:
        i = i + 1
        if z > len(ElementBinding):
            #Give the bindings of the last element
            Element[ele]['binding'][shell] = ElementBinding[-1][i]
        else:
            Element[ele]['binding'][shell] = ElementBinding[z-1][i]
    #fluorescence yields
    Element[ele]['omegak']  = getomegak(ele)
    Element[ele]['omegal1'] = getomegal1(ele)
    Element[ele]['omegal2'] = getomegal2(ele)
    Element[ele]['omegal3'] = getomegal3(ele)
    Element[ele]['omegam1'] = getomegam1(ele)
    Element[ele]['omegam2'] = getomegam2(ele)
    Element[ele]['omegam3'] = getomegam3(ele)
    Element[ele]['omegam4'] = getomegam4(ele)
    Element[ele]['omegam5'] = getomegam5(ele)


    #Coster-Kronig
    Element[ele]['CosterKronig'] = {}
    Element[ele]['CosterKronig']['L'] = getCosterKronig(ele)
    Element[ele]['CosterKronig']['M'] = MShell.getCosterKronig(ele)

    #jump ratios

    #xrays
    #Element[ele]['rays']=[]
    #updateElementDict(ele, Element[ele], energy=None, minenergy=0.399, minrate=0.001,cb=False)
Material = _getMaterialDict()

updateDict()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ele = sys.argv[1]
        if ele in Element.keys():
            print("Symbol        = ",getsymbol(getz(ele)))
            print("Atomic Number = ",getz(ele))
            print("Name          = ",getname(getz(ele)))
            print("K-shell yield = ",Element[ele]['omegak'])
            print("L1-shell yield = ",Element[ele]['omegal1'])
            print("L2-shell yield = ",Element[ele]['omegal2'])
            print("L3-shell yield = ",Element[ele]['omegal3'])
            print("M1-shell yield = ",Element[ele]['omegam1'])
            print("M2-shell yield = ",Element[ele]['omegam2'])
            print("M3-shell yield = ",Element[ele]['omegam3'])
            print("M4-shell yield = ",Element[ele]['omegam4'])
            print("M5-shell yield = ",Element[ele]['omegam5'])
            print("L Coster-Kronig= ",Element[ele]['CosterKronig']['L'])
            print("M Coster-Kronig= ",Element[ele]['CosterKronig']['M'])
            if len(sys.argv) > 2:
                def testCallback():
                    print("callback called")
                registerUpdate(testCallback)
                e = float(sys.argv[2])
                import time
                t0=time.time()
                updateDict(energy=e)
                print("update took ",time.time() - t0)
            for rays in Element[ele]['rays']:
                print(rays,":")
                for transition in Element[ele][rays]:
                    print("%s energy = %.5f  rate = %.5f" %\
                          (transition,Element[ele][transition]['energy'],
                                        Element[ele][transition]['rate']))

        if len(sys.argv) > 2:
            LOGLOG = False
            print("OLD VALUES")
            print(getmassattcoef(ele,float(sys.argv[2])))
            LOGLOG = True
            print("NEW VALUES")
            print(getmassattcoef(ele,float(sys.argv[2])))
            if len(sys.argv) >3:
                print(getcandidates(float(sys.argv[2]),
                                    threshold=float(sys.argv[3])))
            else:
                print(getcandidates(float(sys.argv[2])))
        else:
            print(getmassattcoef(ele,[10.,11,12,12.5]))
