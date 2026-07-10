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
__author__ = "V.A. Sole - ESRF Software Group"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
__doc__ =\
"""
The 1997 release of the Evaluated Atomic Data Library (EADL97)

This module parses the EADL.DAT file that can be downloaded from:

http://www-nds.iaea.org/epdl97/libsall.htm

EADL contains atomic relaxation information for use in particle transport
analysis for atomic number Z = 1-100 and for each subshell.

The original units are in cm and MeV.

The specific data are:

- Subshell data

    a) number of electrons
    b) binding and kinetic energy (MeV)
    c) average radius (cm)
    d) radiative and non-radiative level widths (MeV)
    e) average number of released electrons and x-rays
    f) average energy of released electrons and x-rays (MeV)
    g) average energy to the residual atom, i.e., local deposition (MeV)

- Transition probability data

    a) radiation transition probabilities
    b) non-radiative transition probabilities

The data are organized in blocks with headers.

The first line of the header:

Columns    Format   Definition
1-3         I3      Z  - atomic number
4-6         I3      A  - mass number (in all cases=0 for elemental data)
8-9         I2      Yi - incident particle designator (7 is photon)
11-12       I2      Yo - outgoing particle designator (0, no particle
                                                       7, photon
                                                       8, positron
                                                       9, electron)
14-24       E11.4   AW - atomic mass (amu)

26-31       I6      Date of evaluation (YYMMDD)

The second line of the header:

Columns    Format   Definition
1-2         I2      C  - reaction descriptor
                                  = 71, coherent scattering
                                  = 72, incoherent scattering
                                  = 73, photoelectric effect
                                  = 74, pair production
                                  = 75, triplet production
                                  = 91, subshell parameters
                                  = 92, transition probabilities
                                  = 93, whole atom parameters

3-5         I2      I  - reaction property:
                                  =   0, integrated cross section
                                  =  10, avg. energy of Yo
                                  =  11, avg. energy to the residual atom
                                  = 912, number of electrons
                                  = 913, binding energy
                                  = 914, kinetic energy
                                  = 915, average radius
                                  = 921, radiative level width
                                  = 922, non-radiative level width
                                  = 931, radiative transition probability
                                  = 932, non-radiative transition probability
                                  = 933, particles per initial vacancy
                                  = 934, energy of particles per initial vacancy
                                  = 935, average energy to the residual atom, i.e.
                                         local deposition, per initial vacancy
                                  --- moved to EPDL97 ---
                                  = 941, form factor
                                  = 942, scattering function
                                  = 943, imaginary anomalous scatt. factor
                                  = 944, real anomalous scatt. factor

6-8         I3      S  - reaction modifier:
                                  =  0 no X1 field data required
                                  = 91 X1 field data required

22-32       #11.4   X1 - subshell designator
                                      0 if S is 0
                                      if S is 91, subshell designator


                 Summary of the EADL Data Base
--------------------------------------------------------------------------
Yi    C    S    X1    Yo   I          Data Types
--------------------------------------------------------------------------
                     Subshell parameters
--------------------------------------------------------------------------
0    91    0    0.    0    912        number of electrons
0    91    0    0.    0    913        binding energy
0    91    0    0.    0    914        kinetic energy
0    91    0    0.    0    915        average radius
0    91    0    0.    0    921        radiative level width
0    91    0    0.    0    921        non-radiative level width
--------------------------------------------------------------------------
                     Transititon probabilities
--------------------------------------------------------------------------
0    92    0    0.    0    935        average energy to the residual atom
0    92    0    0.  7 or 9 933        average number of particles per
                                      initial vacancy
0    92    0    0.  7 or 9 934        average energy of particles per
                                      initial vacancy
0    92   91    *     0    931        radiative transition probability
0    92   91    *     0    932        non-radiative transition probability
---------------------------------------------------------------------------
Yi    C    S    X1    Yo   I          Data Types
--------------------------------------------------------------------------

* -> Subshell designator

Data sorted in ascending order Z -> C -> S -> X1 -> Yo -> I
"""
import numpy
#Translation from EADL index to actual shell (Table VI)
import EADLSubshells
SHELL_LIST = EADLSubshells.SHELL_LIST
getSubshellFromValue = EADLSubshells.getSubshellFromValue
getValueFromSubshell = EADLSubshells.getValueFromSubshell

_logger = logging.getLogger(__name__)

AVOGADRO_NUMBER = 6.02214179E23

#
Elements = ['H', 'He',
            'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
            'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
            'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
            'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se',
            'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
            'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
            'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce',
            'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
            'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W',
            'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
            'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
            'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
            'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg',
            'Bh', 'Hs', 'Mt']

#Read the EPDL library
# Try to find it in the local directory
EADL = os.path.join(os.path.dirname(__file__), 'EADL.DAT')

if not os.path.exists(EADL):
    from PyMca5 import PyMcaDataDir
    EADL = os.path.join(PyMcaDataDir.PYMCA_DATA_DIR, 'EPDL97', 'EADL.DAT')

infile = open(EADL, 'rb')
EADL97_DATA = infile.read().decode('UTF-8')
infile.close()

#speed up sequential access
LAST_INDEX = -1

#properly write exponential notation
#EADL97_DATA = EADL97_DATA.replace('- ', '  ')
#EADL97_DATA = EADL97_DATA.replace('+ ', '  ')
EADL97_DATA = EADL97_DATA.replace('- ', 'E-')
EADL97_DATA = EADL97_DATA.replace('+ ', 'E+')

#get rid of tabs if any
EADL97_DATA = EADL97_DATA.replace('\t', ' ')

#get rid of carriage returns if any
EADL97_DATA = EADL97_DATA.replace('\r\n', '\n')
EADL97_DATA = EADL97_DATA.split('\n')
#Now I have a huge list with all the lines
EADL97_ATOMIC_WEIGHTS = None

def getParticle(value):
    """
    Returns one of ['none', 'photon', 'positron', 'electron'] following
    the convention:
            0 = no particle
            7 = photon
            8 = positron
            9 = electron)
    """
    if value == 7:
        return 'photon'
    if value == 0:
        return 'none'
    if value == 9:
        return 'electron'
    if value == 8:
        return 'positron'
    raise ValueError('Invalid particle code')

def getReactionFromCode(value):
    """
    The input value must be one of: 91, 92, 73, 74, 75
    Returns one of coherent, incoherent, photoelectric, pair, triplet
    according to the integer EADL97 code of the reaction:
                    91 <-> subshell parameters
                    92 <-> transition probabilities
                    93 <-> whole atom parameters
    """
    if value == 91:
        return 'subshell'
    if value == 92:
        return 'transition'
    raise ValueError('Invalid reaction descriptor code')

def getReactionPropertyFromCode(value):
    """
    The input value must be one of: 0, 10, 11, 941, 942, 943, 944
    according to the integer EPDL97 code of the reaction property:
                     0 <-> integrated cross section
                    10 <-> avg. energy of Yo
                    11 <-> avg. energy to the residual atom
                   912 <-> number of electrons
                   913 <-> binding energy
                   914 <-> kinetic energy
                   915 <-> average radius
                   921 <-> radiative level width
                   922 <-> non-radiative level width
                   931 <-> radiative transition probability
                   932 <-> non-radiative transition probability
                   934 <-> energy of particles per initial vacancy
                   935 <-> average energy to the residual atom, i.e.
                   941 <-> form factor
                   942 <-> scattering function
                   943 <-> imaginary anomalous scatt. factor
                   944 <-> real anomalous scatt. factor
    """
    if value == 0:
        return 'cross_section'
    if value == 10:
        return 'secondary_particle_energy'
    if value == 11:
        return 'atom_energy_transfer'
    if value == 912:
        return 'number_of_electrons'
    if value == 913:
        return 'binding_energy'
    if value == 914:
        return 'kinetic_energy'
    if value == 915:
        return 'average_radius'
    if value == 921:
        return 'radiative_level_width'
    if value == 922:
        return 'non-radiative_level_width'
    if value == 931:
        return 'radiative_transition_probability'
    if value == 932:
        return 'non-radiative_transition_probability'
    if value == 933:
        return 'particles_per_initial_vacancy'
    if value == 934:
        return 'energy_of_particles_per_initial_vacancy'
    if value == 935:
        return 'average_energy_to_the_residual_atom'
    if value == 941:
        return 'form_factor'
    if value == 942:
        return 'scattering_function'
    if value == 943:
        return 'imaginary_anomalous_scattering_factor'
    if value == 944:
        return 'real_anomalous_scattering_factor'
    raise ValueError('Invalid reaction property descriptor code')

def parseHeader0(line):
    """
    Columns    Format   Definition
    1-3         I3      Z  - atomic number
    4-6         I3      A  - mass number (in all cases=0 for elemental data)
    8-9         I2      Yi - incident particle designator (7 is photon)
    11-12       I2      Yo - outgoing particle designator (0, no particle
                                                           7, photon
                                                           8, positron
                                                           9, electron)
    14-24       E11.4   AW - atomic mass (amu)

    26-31       I6      Date of evaluation (YYMMDD)
    """
    item0 = line[0:6]
    items = line[6:].split()
    Z  = int(item0[0:3])
    A  = int(item0[3:6])
    Yi = int(items[0])
    Yo = int(items[1])
    AW = float(items[2])
    Date = items[4]
    ddict={}
    ddict['atomic_number'] = Z
    ddict['mass_number'] = A
    ddict['atomic_mass'] = AW
    ddict['incident_particle'] = getParticle(Yi)
    ddict['incident_particle_value'] = Yi
    ddict['outgoing_particle'] = getParticle(Yo)
    ddict['outgoing_particle_value'] = Yo
    ddict['date'] = Date
    ddict['Z']  = Z
    ddict['A']  = A
    ddict['Yi'] = Yi
    ddict['Yo'] = Yo
    ddict['AW'] = AW
    return ddict

def parseHeader1(line):
    """
    The second line of the header:

    Columns    Format   Definition
    1-2         I2      C  - reaction descriptor
                                  = 71, coherent scattering
                                  = 72, incoherent scattering
                                  = 73, photoelectric effect
                                  = 74, pair production
                                  = 75, triplet production
                                  = 91, subshell parameters
                                  = 92, transition probabilities
                                  = 93, whole atom parameters

    3-5         I2      I  - reaction property:
                                  =   0, integrated cross section
                                  =  10, avg. energy of Yo
                                  =  11, avg. energy to the residual atom
                                  = 912, number of electrons
                                  = 913, binding energy
                                  = 914, kinetic energy
                                  = 915, average radius
                                  = 921, radiative level width
                                  = 922, non-radiative level width
                                  = 931, radiative transition probability
                                  = 932, non-radiative transition probability
                                  = 934, energy of particles per initial vacancy
                                  = 935, average energy to the residual atom, i.e.
                                         local deposition, per initial vacancy
                                  --- moved to EPDL97 ---
                                  = 941, form factor
                                  = 942, scattering function
                                  = 943, imaginary anomalous scatt. factor
                                  = 944, real anomalous scatt. factor

    6-8         I3      S  - reaction modifier:
                                      =  0 no X1 field data required
                                      = 91 X1 field data required

    22-32       #11.4   X1 - subshell designator
                                          0 if S is 0
                                          if S is 91, subshell designator
    """
    item0 = line[0:6]
    items = line[6:].split()
    C  = int(item0[0:2])
    I  = int(item0[2:6])
    S  = int(items[0])
    #there seems to be some dummy number in between
    X1 = float(items[2])
    ddict={}
    ddict['reaction_code'] = C
    ddict['reaction'] = getReactionFromCode(C)
    ddict['reaction_property'] = getReactionPropertyFromCode(I)
    ddict['reaction_property_code'] = I
    ddict['C'] = C
    ddict['I'] = I
    ddict['S'] = S
    ddict['X1'] = X1
    if S == 91:
        ddict['subshell_code'] = X1
        if X1 != 0.0:
            ddict['subshell'] = getSubshellFromValue(X1)
        else:
            ddict['subshell'] = 'none'
    elif (S == 0) and (X1 == 0.0):
        ddict['subshell_code'] = 0
        ddict['subshell'] = 'none'
    else:
        _logger.error("Inconsistent data")
        _logger.error("X1 = %s; S = %s", X1, S)
        sys.exit(1)
    return ddict

def parseHeader(line0, line1):
    #_logger.info "line0 = ", line0
    #_logger.info "line1 = ", line1
    ddict = parseHeader0(line0)
    ddict.update(parseHeader1(line1))
    return ddict

def getDataLineIndex(lines, z, Yi, C, S, X1, Yo, I):
    global LAST_INDEX
    if (z < 1) or (z>100):
        raise ValueError("Invalid atomic number %d" % z)
    nlines = len(lines)
    i = LAST_INDEX
    while i < (nlines-1):
        i += 1
        line = lines[i]
        if len(line.split()) < 9:
            """
            i += 2
            while len(lines[i+1].split()) != 1:
                print lines[i+1]
                if i>=5:
                    sys.exit(0)
                i += 1
            """
            continue
        try:
            ddict = parseHeader(lines[i], lines[i+1])
        except Exception:
            _logger.error("Error with lines")
            _logger.error("line index = %d", i)
            _logger.error(lines[i])
            _logger.error(lines[i+1])
            _logger.error(sys.exc_info())
            raise
        if ddict['Z'] == z:
            _logger.debug("Z found")
            if ddict['Yi'] == Yi:
                _logger.debug("Yi found")
                if ddict['C'] == C:
                    _logger.debug("C found")
                    if ddict['S'] == S:
                        _logger.debug("S found with X1 = %s", ddict['X1'])
                        _logger.debug("Requested    X1 = %s", X1)
                        _logger.debug(lines[i])
                        _logger.debug(lines[i+1])
                        if ddict['X1'] == X1:
                            _logger.debug("Requested    Yo = %s", Yo)
                            _logger.debug("Found        Yo = %s", ddict['Yo'])
                            if ddict['Yo'] == Yo:
                                _logger.debug("Requested I = %s", I)
                                if ddict['I'] == I:
                                    _logger.debug("FOUND!")
                                    _logger.debug(lines[i])
                                    _logger.debug(lines[i+1])
                                    LAST_INDEX = i - 1
                                    return i
        i += 1
    if LAST_INDEX > 0:
        _logger.debug("REPEATING")
        LAST_INDEX = -1
        return getDataLineIndex(lines, z, Yi, C, S, X1, Yo, I)
    return -1

def getActualDataFromLinesAndOffset(lines, index):
    data_begin = index + 2
    data_end   = index + 2
    end_line = lines[data_end+1]
    while (len(end_line) != 72) and (end_line[-1] != '1'):
        data_end += 1
        end_line = lines[data_end + 1]
    data_end += 1
    _logger.debug("COMPLETE DATA SET")
    _logger.debug(lines[index:data_end])
    _logger.debug("END DATA SET")
    _logger.debug("ADDITIONAL LINE")
    _logger.debug(lines[data_end])
    _logger.debug("END ADDITIONAL LINE")
    ndata = data_end - data_begin
    energy = numpy.zeros((ndata,), numpy.float64)
    t = lines[data_begin].split()
    if len(t) == 2:
        value  = numpy.zeros((ndata,), numpy.float64)
        for i in range(ndata):
            t = lines[data_begin+i].split()
            energy[i] = float(t[0])
            try:
                value[i]  = float(t[1])
            except ValueError:
                if ('E' not in t[1]) and (('+' in t[1]) or ('-' in t[1])):
                    t[1] = t[1].replace('-','E-')
                    t[1] = t[1].replace('+','E+')
                    value[i]  = float(t[1])
                else:
                    raise
    else:
        value = []
        for i in range(ndata):
            t = lines[data_begin+i].split()
            energy[i] = float(t[0])
            value.append([])
            for j in range(0, len(t)-1):
                tj = t[j+1]
                try:
                    value[i].append(float(tj))
                except ValueError:
                    if ('E' not in tj) and (('+' in tj) or ('-' in tj)):
                        tj = tj.replace('-','E-')
                        tj = tj.replace('+','E+')
                        value[i].append(float(tj))
                    else:
                        raise
    return energy, value

def getBaseShellDict(nvalues=None):
    bad_shells = ['L (', 'L23',
                  'M (', 'M23', 'M45',
                  'N (', 'N23', 'N45', 'N67',
                  'O (', 'O23', 'O45', 'O67', 'O89',
                  'P (', 'P23', 'P45', 'P67', 'P89', 'P101',
                  'Q (', 'Q23', 'Q45', 'Q67']
    ddict = {}
    for shell in SHELL_LIST:
        if shell[0:3] in bad_shells:
            continue
        if shell[0:4] in bad_shells:
            continue
        if nvalues is None:
            ddict[shell] = 0.0
        else:
            ddict[shell] = [0.0] * nvalues
    return ddict

def getBaseShellList():
    bad_shells = ['L (', 'L23',
                  'M (', 'M23', 'M45',
                  'N (', 'N23', 'N45', 'N67',
                  'O (', 'O23', 'O45', 'O67', 'O89',
                  'P (', 'P23', 'P45', 'P67', 'P89', 'P101',
                  'Q (', 'Q23', 'Q45', 'Q67']
    ddict = []
    for shell in SHELL_LIST:
        if shell[0:3] in bad_shells:
            continue
        if shell[0:4] in bad_shells:
            continue
        ddict.append(shell)
    return ddict

def getRadiativeWidths(z, lines=None):
    #Yi    C    S    X1    Yo   I
    #0    91    0    0.    0  921   Radiative widths
    ddict = getBaseShellDict()
    if z < 6:
        return ddict
    if lines is None:
        lines = EADL97_DATA
    index = getDataLineIndex(lines, z, 0, 91, 0, 0., 0, 921)
    if index < 0:
        raise IOError("Requested data not found")
    shell_codes, value = getActualDataFromLinesAndOffset(lines, index)
    _logger.debug("shell_codes %s, value %s", shell_codes, value)
    i = 0
    ddict = getBaseShellDict()
    for code in shell_codes:
        shell = getSubshellFromValue(code)
        ddict[shell] = value[i]
        i += 1
    return ddict

def getNonradiativeWidths(z, lines=None):
    #Yi    C    S    X1    Yo   I
    #0    91    0    0.    0  922   Nonradiative widths
    ddict = getBaseShellDict()
    if z < 6:
        return ddict
    if lines is None:
        lines = EADL97_DATA
    index = getDataLineIndex(lines, z, 0, 91, 0, 0., 0, 922)
    if index < 0:
        raise IOError("Requested data not found")
    shell_codes, value = getActualDataFromLinesAndOffset(lines, index)
    _logger.debug("shell_codes %s, value %s", shell_codes, value)
    i = 0
    ddict = getBaseShellDict()
    for code in shell_codes:
        shell = getSubshellFromValue(code)
        ddict[shell] = value[i]
        i += 1
    return ddict

def getRadiativeTransitionProbabilities(z, shell='K', lines=None):
    """
    getRadiativeTransitionProbabilities(z, shell='K')
    Returns a dictionary with the radiative transition probabilities
    from any shell to the given shell.
    """
    #Yi    C    S    X1    Yo   I
    #0    92   91    1.    7  931    K    Shell
    #0    92   91    2.    7  931    L1   Shell
    #0    92   91    5.    7  931    L2   Shell
    #0    92   91    6.    7  931    L3   Shell
    #0    92   91    8.    7  931    M1   Shell
    #0    92   91   10.    7  931    M2   Shell
    #0    92   91   11.    7  931    M3   Shell
    #0    92   91   13.    7  931    M4   Shell
    #0    92   91   14.    7  931    M5   Shell
    ddict = getBaseShellDict(nvalues=2)
    if z < 6:
        return ddict
    if lines is None:
        lines = EADL97_DATA
    X1 = getValueFromSubshell(shell)
    index = getDataLineIndex(lines, z, 0, 92, 91, X1, 7, 931)
    if index < 0:
        #this error may happen when requesting non existing data too
        raise IOError("Requested data not found")
    shell_codes, values = getActualDataFromLinesAndOffset(lines, index)
    _logger.debug("shell_codes %s, values %s", shell_codes, values)
    i = 0
    ddict = getBaseShellDict(nvalues=2)
    for code in shell_codes:
        key = getSubshellFromValue(code)
        ddict[key] = values[i]
        i += 1
    return ddict

def getNonradiativeTransitionProbabilities(z, shell='K', lines=None):
    """
    getNonradiativeTransitionProbabilities(z, shell='K')
    Returns the radiative transition probabilities and energies
    to the given shell.
    The output is a dictionary in IUPAC notation.
    """
    #Yi    C    S    X1    Yo   I
    #0    92   91    1.    9  932    K    Shell
    #0    92   91    2.    9  932    L1   Shell
    #0    92   91    5.    9  932    L2   Shell
    #0    92   91    6.    9  932    L3   Shell
    #0    92   91    8.    9  932    M1   Shell
    #0    92   91   10.    9  932    M2   Shell
    #0    92   91   11.    9  932    M3   Shell
    #0    92   91   13.    9  932    M4   Shell
    #0    92   91   14.    9  932    M5   Shell
    ddict = getBaseShellDict()
    #if z < 6:
    #    return ddict
    if lines is None:
        lines = EADL97_DATA
    X1 = getValueFromSubshell(shell)
    index = getDataLineIndex(lines, z, 0, 92, 91, X1, 9, 932)
    if index < 0:
        #this error may happen when requesting non existing data too
        raise IOError("Requested data not found")
    shell_codes, values = getActualDataFromLinesAndOffset(lines, index)
    _logger.debug("shell_codes %s, values %s", shell_codes, values)
    i = 0
    ddict = {}#getBaseShellDict()
    for code in shell_codes:
        key1 = getSubshellFromValue(code).split()[0]
        key2 = getSubshellFromValue(values[i][0]).split()[0]
        ddict[shell+'-'+key1+key2] = values[i][1:]
        i += 1
    return ddict

#The usefull stuff
def getBindingEnergies(z, lines=None):
    """
    getBindingEnergies(z)

    Returns the binding energies in MeV
    """
    #Yi    C    S    X1    Yo   I
    #0    91    0    0.    0  913
    if lines is None:
        lines = EADL97_DATA
    index = getDataLineIndex(lines, z, 0, 91, 0, 0., 0, 913)
    if index < 0:
        raise IOError("Requested data not found")
    shell_codes, value = getActualDataFromLinesAndOffset(lines, index)
    _logger.debug("shell_codes %s, value %s", shell_codes, value)
    i = 0
    ddict = getBaseShellDict()
    for code in shell_codes:
        shell = getSubshellFromValue(code)
        ddict[shell] = value[i]
        i += 1
    return ddict

def getFluorescenceYields(z, lines=None):
    if lines is None:
        lines = EADL97_DATA
    radiative_dict = getRadiativeWidths(z, lines)
    nonradiative_dict = getNonradiativeWidths(z, lines)
    ddict={}
    for key in radiative_dict.keys():
        x = radiative_dict[key]
        a = nonradiative_dict[key]
        if ( x > 0.0) or  ( a > 0.0):
            ddict[key] = x / (a + x)
    return ddict

def getCosterKronigYields(z, shell='L1', lines=None):
    """
    getCosterKronigYields(z, shell='L1')
    Returns the non-zero Coster-Kronig yields as keys of a dictionary
    or just an empty dictionary.
    """
    if lines is None:
        lines = EADL97_DATA
    #radiative_dict = getRadiativeWidths(z, lines)
    #nonradiative_dict = getNonradiativeWidths(z, lines)
    probabilities = getNonradiativeTransitionProbabilities(z,
                                                 shell=shell,
                                                 lines=lines)
    ddict = {}
    for key in probabilities:
        items = key.split('-')
        if items[0] != shell:
            raise ValueError("Inconsistent data!")
        if items[0][0] == items[1][0]:
            #coster kronig
            transition = 'f'+ items[0][1] + items[1][1]
            if transition not in ddict.keys():
                ddict[transition] = 0.0
            ddict[transition] += probabilities[key][0]
    return ddict

def getLShellCosterKronigYields(z, lines=None):
    """
    getLShellCosterKronigYields(z)
    Returns the L-shell Coster-Kronig yields of an element as keys of a
    dictionary
    """
    ddict = {}
    ddict['f12'] = 0.0
    ddict['f13'] = 0.0
    ddict['f23'] = 0.0
    for i in range(2):
        shell = 'L%d' % (i+1)
        try:
            ddict.update(getCosterKronigYields(z, shell=shell))
        except IOError:
            pass
    return ddict

def getMShellCosterKronigYields(z, lines=None):
    """
    getMShellCosterKronigYields(z)
    Returns the M-shell Coster-Kronig yields of an element as keys of a
    dictionary. It does not check for physical meaning. So, it will give
    zeroes when needed.
    """
    ddict = {}
    for i in range(1, 5):
        for j in range(i+1, 6):
            key = 'f%d%d' % (i,j)
            ddict[key] = 0.0
        shell = 'M%d' % i
        try:
            ddict.update(getCosterKronigYields(z, shell=shell))
        except IOError:
            pass
    return ddict

def getAtomicWeights():
    global EADL97_ATOMIC_WEIGHTS
    if EADL97_ATOMIC_WEIGHTS is None:
        lines = EADL97_DATA
        i = 1
        EADL97_ATOMIC_WEIGHTS = numpy.zeros((len(Elements),), numpy.float64)
        for line in lines:
            if line.startswith('%3d000 ' % i):
                ddict0 = parseHeader0(line)
                EADL97_ATOMIC_WEIGHTS[i-1] = ddict0['atomic_mass']
                i += 1
    return EADL97_ATOMIC_WEIGHTS * 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        element = sys.argv[1]
    else:
        element = 'Pb'
    _logger.info("Getting binding energies for element %s", element)
    ddict = getBindingEnergies(Elements.index(element)+1)
    for key in getBaseShellList():
        if ddict[key] > 0.0:
            _logger.info("Shell = %s Energy (keV) = %.7E", key, ddict[key] * 1000.)
    _logger.info("Getting fluorescence yields for element %s", element)
    ddict = getFluorescenceYields(Elements.index(element)+1)
    for key in getBaseShellList():
        if key in ddict:
            if ddict[key] > 0.0:
                _logger.info("Shell = %s Yield = %.7E", key, ddict[key])

    #total_emission = 0.0
    for shell in ['K', 'L1', 'L2', 'L3', 'M1', 'M2', 'M3', 'M4', 'M5']:
        try:
            ddict = getRadiativeTransitionProbabilities(Elements.index(element)+1,
                                                        shell=shell)
            _logger.info("%s Shell radiative emission probabilities ", shell)
        except IOError:
            continue
        total = 0.0
        for key in getBaseShellList():
            if key in ddict:
                if ddict[key][0] > 0.0:
                    _logger.info("Shell = %s Yield = %.7E Energy = %.7E",
                                 key, ddict[key][0], ddict[key][1] * 1000.)
                    total += ddict[key][0]
        _logger.info("Total %s-shell emission probability = %.7E", shell, total)
        #total_emission += total
    #_logger.info "total_emission = ", total_emission
    for shell in ['K', 'L1', 'L2', 'L3', 'M1', 'M2', 'M3', 'M4', 'M5']:
        try:
            ddict = getNonradiativeTransitionProbabilities(Elements.index(element)+1,
                                                           shell=shell)
            _logger.info("%s Shell Nonradiative emission probabilities ", shell)
        except IOError:
            continue
        total = 0.0
        shell_list = getBaseShellList()
        for key0 in shell_list:
            for key1 in shell_list:
                key = "%s-%s%s" % (shell, key0.split()[0], key1.split()[0])
                if key in ddict:
                    if ddict[key][0] > 0.0:
                        _logger.info("Shell = %s Yield = %.7E Energy = %.7E",
                                     key, ddict[key][0], ddict[key][1] * 1000.)
                        total += ddict[key][0]
        _logger.info("Total %s-shell non-radiative emission probability = %.7E",
                     shell, total)
        if shell in ['K']:
            for key0 in ['L1', 'L2', 'L3']:
                subtotal = 0.0
                for key1 in shell_list:
                    tmpKey =  key1.split()[0]
                    key = "%s-%s%s" % (shell, key0, tmpKey)
                    if key in ddict:
                        if ddict[key][0] > 0.0:
                            subtotal += ddict[key][0]
                            if tmpKey == key0:
                                subtotal += ddict[key][0]
                _logger.info("%s vacancies for nonradiative transition to %s shell = %.7E",
                             key0, shell, subtotal)

    #_logger.info(getNonradiativeTransitionProbabilities(Elements.index(element)+1, 'L1'))
    _logger.info(getMShellCosterKronigYields(Elements.index(element)+1))
    _logger.info("atomic weight = %s", getAtomicWeights()[Elements.index(element)])
    sys.exit(0)
