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
import os
import sys
import numpy
import copy
import logging
from .Strategies import STRATEGIES
from . import ConcentrationsTool
FISX = ConcentrationsTool.FISX
if FISX:
    FisxHelper = ConcentrationsTool.FisxHelper
from . import Elements
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaMath.fitting import Gefit
from PyMca5 import PyMcaDataDir
_logger = logging.getLogger(__name__)
#"python ClassMcaTheory.py -s1.1 --file=03novs060sum.mca --pkm=McaTheory.dat --continuum=0 --strip=1 --sumflag=1 --maxiter=4"
CONTINUUM_LIST = [None,'Constant','Linear','Parabolic','Linear Polynomial','Exp. Polynomial']
OLDESCAPE = 0
MAX_ATTENUATION = 1.0E-300
class McaTheory(object):
    def __init__(self, initdict=None, filelist=None, **kw):
        self.ydata0  = None
        self.xdata0  = None
        self.sigmay0 = None
        self.__lastTime = None
        self.strategyInstances = {}
        self.__toBeConfigured = False
        self.useFisxEscape(False)
        if initdict is None:
            dirname = PyMcaDataDir.PYMCA_DATA_DIR
            initdict = os.path.join(dirname, "McaTheory.cfg")
            if not os.path.exists(initdict):
                #Frozen version deals differently with the path
                dirname = os.path.dirname(dirname)
                initdict = os.path.join(dirname, "McaTheory.cfg")
                if not os.path.exists(initdict):
                    if dirname.lower().endswith(".zip"):
                        dirname = os.path.dirname(dirname)
                        initdict = os.path.join(dirname, "McaTheory.cfg")
            if os.path.exists(initdict):
                self.config = ConfigDict.ConfigDict(filelist=initdict)
            else:
                print("Cannot find file McaTheory.cfg")
                raise IOError("File %s does not exist" % initdict)
        else:
            if os.path.exists(initdict.split('::')[0]):
                self.config = ConfigDict.ConfigDict(filelist = initdict)
            else:
                raise IOError("File %s does not exist" % initdict)
                self.config = {}
                self.config['fit'] = {}
                self.config['attenuators'] = {}
        if 'config' in kw:
            self.config.update(kw['config'])
        SpecfitFuns.fastagauss([1.0,10.0,1.0],numpy.arange(10.))
        self.config['fit']['sumflag']     = kw.get('sumflag',self.config['fit']['sumflag'])
        self.config['fit']['escapeflag']  = kw.get('escapeflag', self.config['fit']['escapeflag'])
        self.config['fit']['continuum']   = kw.get('continuum', self.config['fit']['continuum'])
        self.config['fit']['stripflag']   = kw.get('stripflag',  self.config['fit']['stripflag'])
        self.config['fit']['maxiter']     = kw.get('maxiter',self.config['fit']['maxiter'])
        self.config['fit']['hypermetflag']= kw.get('hypermetflag',self.config['fit']['hypermetflag'])
        self.attflag   = kw.get('attenuatorsflag',1)
        self.lastxmin = None
        self.lastxmax = None
        self.laststrip = None
        self.laststripconstant = None
        self.laststripiterations = None
        self.laststripalgorithm = None
        self.lastsnipwidth = None
        self.laststripwidth = None
        self.laststripfilterwidth = None
        self.laststripanchorsflag = None
        self.laststripanchorslist = None
        self.disableOptimizedLinearFit()
        self.__configure()
        self.startFit = self.startfit
        #incompatible with multiple energies
        #Elements.registerUpdate(self._updateCallback)

    def useFisxEscape(self, flag=None):
        if flag:
            if FisxHelper.xcom is None:
                FisxHelper.xcom =FisxHelper.getElementsInstance()
            xcom = FisxHelper.xcom
            if hasattr(xcom, "setEscapeCacheEnabled"):
                xcom.setEscapeCacheEnabled(1)
                self.__USE_FISX_ESCAPE = True
            else:
                self.__USE_FISX_ESCAPE = False
        else:
            self.__USE_FISX_ESCAPE = False

    def enableOptimizedLinearFit(self):
        self._batchFlag = True

    def disableOptimizedLinearFit(self):
        self._batchFlag = False
        self.linearMatrix = None

    def setConfiguration(self, ddict):
        """
        The current fit configuration dictionary is updated, but not replaced,
        by the input dictionary.
        It returns a copy of the final fit configuration.
        """
        return self.configure(ddict)

    def getConfiguration(self):
        """
        returns a copy of the current fit configuration parameters
        """
        return self.configure()

    def getStartingConfiguration(self):
        # same output as calling configure but with the calling program
        # knowing what is going on (no warning)
        if self.__toBeConfigured:
            return copy.deepcopy(self.__originalConfiguration)
        else:
            return self.configure()

    def configure(self, newdict=None):
        if newdict in [None, {}]:
            if self.__toBeConfigured:
                _logger.debug("WARNING: This configuration is the one of last fit.\n"
                              "It does not correspond to the one of next fit.")
            return copy.deepcopy(self.config)
        self.config.update(newdict)
        self.__toBeConfigured = False
        self.__configure()
        return copy.deepcopy(self.config)

    def _updateCallback(self):
        print("no update callback")
        #self.config['fit']['energy'] = Elements.Element['Fe']['buildparameters']['energy']
        #self.__configure()

    def __configure(self):
        self.linearMatrix = None
        #user attenuators key
        self.config['userattenuators'] = self.config.get('userattenuators',{})
        #multilayer key
        self.config['multilayer'] = self.config.get('multilayer',{})
        #update Elements material information
        self.config['materials'] = self.config.get('materials',{})
        for material in self.config['materials'].keys():
            Elements.Material[material] = copy.deepcopy(self.config['materials'][material])
        #that was it

        #default peak shape parameters for pseudo-voigt function
        self.config['peakshape']['eta_factor'] = self.config['peakshape'].get('eta_factor', 0.02)
        self.config['peakshape']['fixedeta_factor'] = self.config['peakshape'].get('fixedeta_factor',
                                                                                       0)
        self.config['peakshape']['deltaeta_factor'] = self.config['peakshape'].get('deltaeta_factor',
                                                    self.config['peakshape']['eta_factor'])
        #fit function
        self.config['fit']['fitfunction'] = self.config['fit'].get('fitfunction',
                                                                   None)
        if self.config['fit']['fitfunction'] is None:
            if self.config['fit']['hypermetflag']:
                self.config['fit']['fitfunction'] = 0
            else:
                self.config['fit']['fitfunction'] = 1

        #default strip function parameters
        self.config['fit']['stripalgorithm']  = self.config['fit'].get('stripalgorithm',0)
        self.config['fit']['snipwidth']  = self.config['fit'].get('snipwidth', 30)

        #linear fitting option
        self.config['fit']['linearfitflag']   = self.config['fit'].get('linearfitflag', 0)
        self.config['fit']['fitweight']    = self.config['fit'].get('fitweight', 1)
        self.config['fit']['energy']       = self.config['fit'].get('energy',None)
        if type(self.config['fit']['energy']) == type(""):
            self.config['fit']['energy']          = None
            self.config['fit']['energyweight']    = [1.0]
            self.config['fit']['energyflag']      = [1]
            self.config['fit']['energyscatter']   = [1]
        elif type(self.config['fit']['energy']) == type([]):
            pass
        else:
            self.config['fit']['energy']=[self.config['fit']['energy']]
            self.config['fit']['energyweight'] = [1.0]
            self.config['fit']['energyflag']   = [1]
            self.config['fit']['energyscatter']   = [1]
        maxenergy = None
        energylist= None
        if self.config['fit']['energy'] is not None:
          if max(self.config['fit']['energyflag']) == 0:
              energylist = None
          else:
            energylist    = []
            energyweight  = []
            energyflag    = []
            energyscatter = []

            for i in range(len(self.config['fit']['energy'])):
                if self.config['fit']['energy'][i] == "None":
                    self.config['fit']['energy'][i] = None
                if self.config['fit']['energyflag'][i]:
                    if self.config['fit']['energy'][i] is not None:
                        energyflag.append(self.config['fit']['energyflag'][i])
                        energylist.append(self.config['fit']['energy'][i])
                        energyweight.append(self.config['fit']['energyweight'][i])
                        if 'energyscatter' in self.config['fit']:
                            energyscatter.append(self.config['fit']['energyscatter'][i])
                        elif i==1:
                            energyscatter.append(1)
                        else:
                            energyscatter.append(0)
                        if maxenergy is None:maxenergy=self.config['fit']['energy'][i]
                        if maxenergy < self.config['fit']['energy'][i]:
                            maxenergy = self.config['fit']['energy'][i]
        self.config['fit']['scatterflag']  = self.config['fit'].get('scatterflag',0)
        self.config['fit']['deltaonepeak'] = self.config['fit'].get('deltaonepeak',0.010)
        self.config['fit']['linpolorder']  = self.config['fit'].get('linpolorder',6)
        self.config['fit']['exppolorder']  = self.config['fit'].get('exppolorder',6)
        self.config['fit']['stripconstant']= self.config['fit'].get('stripconstant',1.0)
        self.config['fit']['stripwidth']= int(self.config['fit'].get('stripwidth',1))
        self.config['fit']['stripfilterwidth']= int(self.config['fit'].get('stripfilterwidth',5))
        self.config['fit']['stripiterations'] = int(self.config['fit'].get('stripiterations',20000))
        self.config['fit']['stripanchorsflag']= int(self.config['fit'].get('stripanchorsflag',0))
        self.config['fit']['stripanchorslist']= self.config['fit'].get('stripanchorslist',[0,0,0,0])
        deltaonepeak = self.config['fit']['deltaonepeak']
        detele       = self.config['detector']['detele']
        detene       = self.config['detector'].get('detene', 1.7420)
        self.config['detector']['detene'] = detene
        ethreshold   = self.config['detector'].get('ethreshold', 0.020)
        nthreshold   = self.config['detector'].get('nthreshold', 4)
        ithreshold   = self.config['detector'].get('ithreshold', 1.0E-07)
        self.config['detector']['ethreshold'] = ethreshold
        self.config['detector']['ithreshold'] = ithreshold
        self.config['detector']['nthreshold'] = nthreshold
        usematrix = 0
        attenuatorlist =[]
        userattenuatorlist =[]
        filterlist = []
        funnyfilters = []
        detector = None
        multilayerlist = None
        self._fluoRates = None
        if self.attflag:
            for userattenuator in self.config['userattenuators']:
                if self.config['userattenuators'][userattenuator]["use"]:
                    userattenuatorlist.append(self.config['userattenuators'][userattenuator])
            for attenuator in self.config['attenuators'].keys():
                if not self.config['attenuators'][attenuator][0]:
                    continue
                # this should not be needed any longer
                #if len(self.config['attenuators'][attenuator]) == 4:
                #    self.config['attenuators'][attenuator].append(1.0)
                if attenuator.upper() == "MATRIX":
                    if self.config['attenuators'][attenuator][0]:
                        usematrix = 1
                        matrix = self.config['attenuators'][attenuator][1:4]
                        alphain= self.config['attenuators'][attenuator][4]
                        alphaout= self.config['attenuators'][attenuator][5]
                    else:
                        usematrix = 0
                        break
                elif attenuator.upper() == "DETECTOR":
                        detector = self.config['attenuators'][attenuator][1:]
                elif attenuator.upper()[0:-1] == "BEAMFILTER":
                    filterlist.append(self.config['attenuators'][attenuator][1:])
                else:
                    if len(self.config['attenuators'][attenuator]) > 4:
                        if abs(self.config['attenuators'][attenuator][4]-1.0) > 1.0e-10:
                            #funny attenuator
                            funnyfilters.append( \
                                self.config['attenuators'][attenuator][1:])
                        else:
                            attenuatorlist.append( \
                                self.config['attenuators'][attenuator][1:])
                    else:
                        attenuatorlist.append( \
                            self.config['attenuators'][attenuator][1:])
            if usematrix:
                layerkeys = list(self.config['multilayer'].keys())
                if len(layerkeys):
                    layerkeys.sort()
                    for layer in layerkeys:
                        if self.config['multilayer'][layer][0]:
                            if multilayerlist is None:multilayerlist = []
                            multilayerlist.append(self.config['multilayer'][layer][1:])

        if (maxenergy is not None) and usematrix:
          #sort the peaks by atomic number
          data  = []
          for element in self.config['peaks'].keys():
              if len(element) > 1:
                  ele = element[0:1].upper()+element[1:2].lower()
              else:
                  ele = element.upper()
              if maxenergy != Elements.Element[ele]['buildparameters']['energy']:
                  Elements.updateDict (energy= maxenergy)
              if type(self.config['peaks'][element]) == type([]):
                  for peak in self.config['peaks'][element]:
                      data.append([Elements.getz(ele),ele,peak])
              else:
                  for peak in [self.config['peaks'][element]]:
                      data.append([Elements.getz(ele),ele,peak])

          data.sort()
          #build the peaks description
          PEAKS0       = []
          PEAKS0NAMES  = []
          PEAKS0ESCAPE = []
          PEAKSW=[]
          if self.config['fit']['fitfunction'] == 0:
              HYPERMET =  self.config['fit']['hypermetflag']
          else:
              HYPERMET = 0
          noise =     self.config['detector']['noise']
          fano  =     self.config['detector']['fano']
          elementsList =[]
          for item in data:
                if len(item[1]) > 1:
                    elementsList.append(item[1][0].upper()+\
                                        item[1][1].lower())
                else:
                    elementsList.append(item[1][0].upper())
          #import time
          #t0=time.time()
          if matrix[0].upper() != "MULTILAYER":
              multilayer = [matrix * 1]
          else:
              if multilayerlist is not None:
                  multilayer  = multilayerlist * 1
              else:
                  text  = "Your matrix is not properly defined.\n"
                  text += "If you used the graphical interface,\n"
                  text += "Please check the MATRIX tab"
                  raise ValueError(text)
          self._fluoRates=Elements.getMultilayerFluorescence(multilayer,
                                 energylist,
                                 layerList = None,
                                 weightList = energyweight,
                                 flagList = energyflag,
                                 fulloutput=1,
                                 attenuators=attenuatorlist,
                                 alphain = alphain,
                                 alphaout = alphaout,
                                 #elementsList = elementsList,
                                 elementsList = data,
                                 cascade = True,
                                 detector=detector,
                                 funnyfilters=funnyfilters,
                                 beamfilters=filterlist,
                                 forcepresent=1,
                                 userattenuators=userattenuatorlist)
          dict = self._fluoRates[0]

          # this will not be needed once fisx replaces the Elements module
          if 'fisx' in self.config:
              if 'corrections' in self.config['fisx']:
                  del self.config['fisx']['corrections']
              if 'secondary' in self.config['fisx']:
                  del self.config['fisx']['secondary']
          self.config['fisx'] = {}
          secondary = False
          if 'concentrations' in self.config:
              secondary = self.config['concentrations'].get('usemultilayersecondary', False)
              if secondary and FISX:
                  self.config['fisx'] = {}
                  self.config['fisx']['corrections'] = FisxHelper.getFisxCorrectionFactorsFromFitConfiguration(self.config,
                                                                                elementsFromMatrix=False)
                  self.config['fisx']['secondary'] = secondary
          # done with the calculation of the corrections to the total rate. For accurate line ratios,
          # the correction is to be applied layer by layer.
          # TODO:That implies the future use of fisx library for *everything*

          #print "getMatrixFluorescence elapsed = ",time.time()-t0
          for item in data:
            newpeaks      = []
            newpeaksnames = []
            element = item[1]
            if len(element) > 1:
                    ele = element[0:1].upper()+element[1:2].lower()
            else:
                    ele = element.upper()
            rays= item[2] +' xrays'
            if not rays in dict[ele]['rays']:continue
            for transition in dict[ele][rays]:
                if dict[ele][transition]['rate'] > 0.0:
                    fwhm = numpy.sqrt(noise*noise + \
                        0.00385 *dict[ele][transition]['energy']* fano*2.3548*2.3548)
                    newpeaks.append([dict[ele][transition]['rate'],
                                     dict[ele][transition]['energy'],
                                     fwhm,0.0])
               #               1.00,eta])
                    newpeaksnames.append(transition)
                    #if ele == 'Au':
                    #if 0:
                    #  print transition, 'energy  = ',dict[ele][transition]['energy'],\
                    # 'rate = ',dict[ele][transition]['rate'],' fwhm =',fwhm

#######################################
            #--- renormalize to account for filter effects ---
            div = sum([x[0] for x in newpeaks])
            try:
                for i in range(len(newpeaks)):
                    newpeaks[i][0] /= div
            except ZeroDivisionError:
                text  = "Intensity of %s %s is zero\n"% (ele, rays)
                text += "Too high attenuation?"
                raise ZeroDivisionError(text)

            #--- sort ---
            div=[[newpeaks[i][1],newpeaks[i][0],newpeaksnames[i]] for i in range(len(newpeaks))]
            div.sort()
            #print "before = ",len(newpeaksnames)
            div = Elements._filterPeaks(div, ethreshold = deltaonepeak,
                                            ithreshold = 0.00005,
                                            #ithreshold = ithreshold,
                                            nthreshold = None,
                                            keeptotalrate=True)
            newpeaks = [[x[1],x[0],0.00385*x[0]*fano*2.3548*2.3548,0.0] for x in div]
            newpeaksnames = [x[2] for x in div]
            #print "after = ",len(newpeaksnames)
            #print "newpeaks = ",newpeaks
            if not len(newpeaks):
                text  = "No %s for element %s" % (rays, ele)
                text += "\nToo high attenuation?"
                raise ValueError(text)
            (r,c)=(numpy.array(newpeaks)).shape
            PEAKS0ESCAPE.append([])
            _nescape_ = 0
            if self.config['fit']['escapeflag']:
                if self.__USE_FISX_ESCAPE:
                    _logger.debug("Using fisx escape")
                    xcom = FisxHelper.xcom
                    detector_composition = Elements.getMaterialMassFractions([detele],
                                                                             [1.0])
                    xcom.updateEscapeCache(detector_composition,
                                           [newpeaks[i][1] for i in range(len(newpeaks))],
                                           energyThreshold=ethreshold,
                                           intensityThreshold=ithreshold,
                                           nThreshold=nthreshold)
                    for i in range(len(newpeaks)):
                        _esc_ = xcom.getEscape(detector_composition,
                                       newpeaks[i][1],
                                       energyThreshold=ethreshold,
                                       intensityThreshold=ithreshold,
                                       nThreshold=nthreshold)
                        _esc_ = [[_esc_[x]["energy"],
                                  _esc_[x]["rate"],
                                   x[:-3].replace("_"," ")] for x in _esc_]
                        _esc_ = Elements._filterPeaks(_esc_, ethreshold=ethreshold,
                                          ithreshold=ithreshold,
                                          nthreshold=nthreshold,
                                           absoluteithreshold=True,
                                           keeptotalrate=False)
                        PEAKS0ESCAPE[-1].append(_esc_)
                        _nescape_ += len(_esc_)
                else:
                    for i in range(len(newpeaks)):
                        _esc_ = Elements.getEscape([detele,1.0,1.0], newpeaks[i][1],
                                            ethreshold=ethreshold, ithreshold=ithreshold,
                                            nthreshold=nthreshold)
                        PEAKS0ESCAPE[-1].append(_esc_)
                        _nescape_ += len(_esc_)
            PEAKS0.append(numpy.array(newpeaks))
            PEAKS0NAMES.append(newpeaksnames)
            #print ele,"PEAKS0ESCAPE[-1] = ",PEAKS0ESCAPE[-1]
            if not HYPERMET:
                if self.config['fit']['escapeflag']:
                    if OLDESCAPE:
                        PEAKSW.append(numpy.ones((2*r,3+1),numpy.float64))
                    else:
                        PEAKSW.append(numpy.ones(((r+_nescape_),3+1),
                                                    numpy.float64))
                else:
                    PEAKSW.append(numpy.ones((r,3+1),numpy.float64))
            else:
                if self.config['fit']['escapeflag']:
                    if OLDESCAPE:
                        PEAKSW.append(numpy.ones((2*r,3+5),numpy.float64))
                    else:
                        PEAKSW.append(numpy.ones(((r+_nescape_),3+5),
                                                    numpy.float64))
                else:
                    PEAKSW.append(numpy.ones((r,3+5),numpy.float64))


#######################################
        else:
            if usematrix and (maxenergy is None):
                text  = "Invalid energy for matrix configuration.\n"
                text += "Please check your BEAM parameters."
                raise ValueError(text)
            elif ((not usematrix) and (self.config['fit']['energy'] is None)) or \
                 ((not usematrix) and (self.config['fit']['energy'] == [None])) or\
                 ((not usematrix) and (self.config['fit']['energy'] == ["None"])) or\
                 ((not usematrix) and (energylist is None)) or\
                 ((not usematrix) and (len(energylist) == 1)):
                #print "OLD METHOD"
                data  = []
                for element in self.config['peaks'].keys():
                    if len(element) > 1:
                        ele = element[0:1].upper()+element[1:2].lower()
                    else:
                        ele = element.upper()
                    if maxenergy != Elements.Element[ele]['buildparameters']['energy']:
                        Elements.updateDict (energy= maxenergy)
                    if type(self.config['peaks'][element]) == type([]):
                        for peak in self.config['peaks'][element]:
                            data.append([Elements.getz(ele),ele,peak])
                    else:
                        for peak in [self.config['peaks'][element]]:
                            data.append([Elements.getz(ele),ele,peak])

                data.sort()
                #build the peaks description
                PEAKS0       = []
                PEAKS0NAMES  = []
                PEAKS0ESCAPE = []
                PEAKSW=[]
                if self.config['fit']['fitfunction'] == 0:
                    HYPERMET =  self.config['fit']['hypermetflag']
                else:
                    HYPERMET = 0
                noise =     self.config['detector']['noise']
                fano  =     self.config['detector']['fano']
                for item in data:
                    newpeaks      = []
                    newpeaksnames = []
                    element = item[1]
                    if len(element) > 1:
                        ele = element[0:1].upper()+element[1:2].lower()
                    else:
                        ele = element.upper()
                    rays= item[2] +' xrays'
                    if not rays in Elements.Element[ele]['rays']:continue
                    eta = 0.0
                    for transition in Elements.Element[ele][rays]:
                        eta = 0.0
                        fwhm = numpy.sqrt(noise*noise + \
                                0.00385 *Elements.Element[ele][transition]['energy']* fano*2.3548*2.3548)
                        newpeaks.append([Elements.Element[ele][transition]['rate'],
                                      Elements.Element[ele][transition]['energy'],
                                       fwhm,eta])
                       #               1.00,eta])
                        newpeaksnames.append(transition)
                    if self.attflag:
                        transmissionenergies = [x[1] for x in newpeaks]
                        oldfunnyfactor = None
                        for attenuator in self.config['attenuators'].keys():
                            if self.config['attenuators'][attenuator][0]:
                                formula  = self.config['attenuators'][attenuator][1]
                                thickness= self.config['attenuators'][attenuator][2] * \
                                                self.config['attenuators'][attenuator][3]
                                if len(self.config['attenuators'][attenuator]) == 4:
                                    funnyfactor = 1.0
                                else:
                                    funnyfactor = self.config['attenuators'][attenuator][4]
                                if attenuator.upper() != "MATRIX":
                                    #coeffs   = thickness * numpy.array(Elements.getmassattcoef(formula,transmissionenergies)['total'])
                                    coeffs   =  thickness * numpy.array(Elements.getMaterialMassAttenuationCoefficients(formula,1.0,transmissionenergies)['total'])
                                    try:
                                        if attenuator.upper() != "DETECTOR":
                                            if abs(funnyfactor-1.0) > 1.0e-10:
                                                #we have a funny attenuator
                                                if (funnyfactor < 0.0) or (funnyfactor > 1.0):
                                                    text = "Funny factor should be between 0.0 and 1.0., got %g" % attenuator[4]
                                                    raise ValueError(text)
                                                if oldfunnyfactor is None:
                                                    #only has to be multiplied once!!!
                                                    oldfunnyfactor = funnyfactor
                                                    trans = funnyfactor * numpy.exp(-coeffs) + \
                                                        (1.0 - funnyfactor)
                                                else:
                                                    if abs(oldfunnyfactor-funnyfactor) > 0.0001:
                                                        text = "All funny type attenuators must have same openning fraction"
                                                        raise ValueError(text)
                                                    trans = numpy.exp(-coeffs)
                                            else:
                                                #standard
                                                trans = numpy.exp(-coeffs)
                                        else:
                                            trans = (1.0 - numpy.exp(-coeffs))
                                    except OverflowError:
                                        if coeffs < 0:
                                            raise ValueError("Positive exponent on transmission term")
                                        else:
                                            if attenuator.upper() == "DETECTOR":
                                                trans = 1.0
                                            else:
                                                trans = 0.0
                                    for i in range(len(newpeaks)):
                                        #if ele == 'Pb':
                                        #    print "energy = %.3f ratio=%.5f transmission = %.5g final=%.5g" % (newpeaks[i][1], newpeaks[i][0],trans[i],trans[i] * newpeaks[i][0])
                                        newpeaks[i][0] *=  trans[i]
                                        if newpeaks[i][0] < MAX_ATTENUATION:
                                            newpeaks[i][0] = 0.0
                                else:
                                    #add the excitation energy
                                    #excitation  energy =  self.config['fit']['energy'] or be registered to
                                    #                      elements callback
                                    try:
                                        alphaIn  = self.config['attenuators'][attenuator][4]
                                    except Exception:
                                        print("warning, alphaIn set to 45 degrees")
                                        alphaIn  = 45.0
                                    try:
                                        alphaOut = self.config['attenuators'][attenuator][5]
                                    except Exception:
                                        print("warning, alphaOut set to 45 degrees")
                                        alphaOut  = 45.0
                                    matrixExcitationEnergy = Elements.Element[ele]['buildparameters']['energy']
                                    #matrixExcitationEnergy = self.config['fit']['energy']
                                    if matrixExcitationEnergy is not None:
                                        transmissionenergies.append(matrixExcitationEnergy)
                                        #transmissionenergies.append(self.config['fit']['energy'])
                                        coeffs   = Elements.getMaterialMassAttenuationCoefficients(formula,1.0,transmissionenergies)['total']
                                        sinAlphaIn   = numpy.sin(alphaIn * (numpy.pi)/180.)
                                        sinAlphaOut  = numpy.sin(alphaOut * (numpy.pi)/180.)
                                        #if ele == 'Pb':
                                        #    oldRatio = []
                                        for i in range(len(newpeaks)):
                                            #thick target term
                                            trans = 1.0/(coeffs[-1] + coeffs[i] * (sinAlphaIn/sinAlphaOut))
                                            if thickness > 0.0:
                                                if abs(sinAlphaIn) > 0.0:
                                                    expterm = -((coeffs[-1]/sinAlphaIn) +(coeffs[i]/sinAlphaOut)) * thickness
                                                    if expterm > 0.0:
                                                        raise ValueError("Positive exponent on transmission term")
                                                    if expterm < 30:
                                                        #avoid overflow error in frozen versions
                                                        try:
                                                            expterm = numpy.exp(expterm)
                                                        except OverflowError:
                                                            expterm = 0.0
                                                        trans *= (1.0 - expterm)
                                            #if ele == 'Pb':
                                            #    oldRatio.append(newpeaks[i][0])
                                            #    print "energy = %.3f ratio=%.5f transmission = %.5g final=%.5g" % (newpeaks[i][1], newpeaks[i][0],trans,trans * newpeaks[i][0])
                                            newpeaks[i][0] *=  trans
                                            if newpeaks[i][0] < MAX_ATTENUATION:
                                                newpeaks[i][0] = 0.0
                                        del transmissionenergies[-1]
                                    else:
                                        raise ValueError(\
                                            "Invalid excitation energy")

                        # user attenuators
                        for userattenuator in self.config['userattenuators']:
                            if self.config['userattenuators'][userattenuator]["use"]:
                                ttrans = Elements.getTableTransmission(
                                                            self.config['userattenuators'][userattenuator],
                                                            [x[1] for x in newpeaks])
                                for i in range(len(newpeaks)):
                                    newpeaks[i][0] *= ttrans[i]

                    #--- renormalize
                    div = sum([x[0] for x in newpeaks])
                    try:
                        for i in range(len(newpeaks)):
                            newpeaks[i][0] /= div
                    except ZeroDivisionError:
                        text  = "Intensity of %s %s is zero\n"% (ele, rays)
                        text += "Too high attenuation?"
                        raise ZeroDivisionError(text)
                    """
                    if ele == 'Pb':
                        dummyNew = [[newpeaks[i][1],oldRatio[i],newpeaks[i][0],newpeaks[i][0]/ oldRatio[i] ] for i in range(len(newpeaks))]
                        dummyNew.sort()
                        for i in range(len(newpeaks)):
                            print "FINAL energy = %.3f oldratio = %.5g  newratio=%.5g new/old = %.5g" % (dummyNew[i][0],
                                                                                                         dummyNew[i][1],
                                                                                                         dummyNew[i][2],
                                                                                                         dummyNew[i][3])
                    """

                    #--- sort ---
                    div=[[newpeaks[i][1],newpeaks[i],newpeaksnames[i]] for i in range(len(newpeaks))]
                    div.sort()
                    newpeaks     =[div[i][1] for i in range(len(div))]
                    newpeaksnames=[div[i][2] for i in range(len(div))]
                    #print "BEFORE "
                    #for i in range(len(newpeaksnames)):
                    #    print newpeaksnames[i], newpeaks[i][1], newpeaks[i][0]
                    tojoint=[]
                    if len(newpeaks) > 1:
                        if 0: #if ele == "Kr":
                            print("ELEMENTS FILTERING ")
                            testPeaks =  [[div[i][0], div[i][1][0], div[i][2]] for i in range(len(div))]
                            testPeaks = Elements._filterPeaks(testPeaks,
                                                        ethreshold=deltaonepeak,
                                                        keeptotalrate=True)
                            for i in range(len(testPeaks)):
                                print(testPeaks[i][2], testPeaks[i][0], testPeaks[i][1])


                        for i in range(len(newpeaks)):
                            for j in range(i,len(newpeaks)):
                                if i != j:
                                    if abs(newpeaks[i][1]-newpeaks[j][1]) < deltaonepeak:
                                        if len(tojoint):
                                            if (i in tojoint[-1]) and (j in tojoint[-1]):
                                                pass
                                            elif (i in tojoint[-1]):
                                                tojoint[-1].append(j)
                                            elif (j in tojoint[-1]):
                                                tojoint[-1].append(i)
                                            else:
                                                tojoint.append([i,j])
                                        else:
                                            tojoint.append([i,j])
                        if len(tojoint):
                            mix=[]
                            mixname=[]
                            for _group in tojoint:
                                rate = 0.0
                                for i in _group:
                                    rate += newpeaks[i][0]
                                ene  = 0.0
                                fwhm = 0.0
                                eta  = 0.0
                                j = 0
                                for i in _group:
                                    if j == 0:
                                        _threshold = newpeaks[i][0]
                                        transition = newpeaksnames[i]
                                        j = 1
                                    ene  += newpeaks[i][0] * newpeaks[i][1]/rate
                                    fwhm += newpeaks[i][0] * newpeaks[i][2]/rate
                                    eta  += newpeaks[i][0] * newpeaks[i][3]/rate
                                    if newpeaks[i][0] > _threshold:
                                        _threshold = newpeaks[i][0]
                                        transition=newpeaksnames[i]
                                mix.append([rate,ene,fwhm,eta])
                                mixname.append(transition)
                            for i in range(1,len(tojoint)+1):
                                for j in range(1,len(tojoint[-i])+1):
                                    del newpeaks[tojoint[-i][-j]]
                                    del newpeaksnames[tojoint[-i][-j]]
                            for peak in mix:
                                newpeaks.append(peak)
                            for peakname in mixname:
                                newpeaksnames.append(peakname)

                    #if ele == "Fe":
                    if 0:
                        for i in range(len(newpeaks)):
                            print(newpeaksnames[i],newpeaks[i])
                    #print "len newpeaks = ",len(newpeaks)
                    (r,c)=(numpy.array(newpeaks)).shape
                    PEAKS0ESCAPE.append([])
                    _nescape_ = 0
                    if self.config['fit']['escapeflag']:
                        if self.__USE_FISX_ESCAPE:
                            _logger.debug("Using fisx escape")
                            xcom = FisxHelper.xcom
                            detector_composition = Elements.getMaterialMassFractions([detele],
                                                                             [1.0])
                            xcom.updateEscapeCache(detector_composition,
                                                   [newpeaks[i][1] for i in range(len(newpeaks))],
                                                   energyThreshold=ethreshold,
                                                   intensityThreshold=ithreshold,
                                                   nThreshold=nthreshold)
                            for i in range(len(newpeaks)):
                                _esc_ = xcom.getEscape(detector_composition,
                                               newpeaks[i][1],
                                               energyThreshold=ethreshold,
                                               intensityThreshold=ithreshold,
                                               nThreshold=nthreshold)
                                _esc_ = [[_esc_[x]["energy"],
                                          _esc_[x]["rate"],
                                           x[:-3].replace("_"," ")] for x in _esc_]
                                _esc_ = Elements._filterPeaks(_esc_, ethreshold=ethreshold,
                                                  ithreshold=ithreshold,
                                                  nthreshold=nthreshold,
                                                   absoluteithreshold=True,
                                                   keeptotalrate=False)
                                PEAKS0ESCAPE[-1].append(_esc_)
                                _nescape_ += len(_esc_)
                        else:
                            for i in range(len(newpeaks)):
                                _esc_ = Elements.getEscape([detele,1.0,1.0], newpeaks[i][1],
                                                    ethreshold=ethreshold, ithreshold=ithreshold,
                                                    nthreshold=nthreshold)
                                PEAKS0ESCAPE[-1].append(_esc_)
                                _nescape_ += len(_esc_)
                    PEAKS0.append(numpy.array(newpeaks))
                    PEAKS0NAMES.append(newpeaksnames)
                    #print ele,"PEAKS0ESCAPE[-1] = ",PEAKS0ESCAPE[-1]
                    if not HYPERMET:
                        if self.config['fit']['escapeflag']:
                            if OLDESCAPE:
                                PEAKSW.append(numpy.ones((2*r,3 + 1),numpy.float64))
                            else:
                                PEAKSW.append(numpy.ones(((r+_nescape_),3 + 1),
                                                            numpy.float64))
                        else:
                            PEAKSW.append(numpy.ones((r,3 + 1),numpy.float64))
                    else:
                        if self.config['fit']['escapeflag']:
                            if OLDESCAPE:
                                PEAKSW.append(numpy.ones((2*r,3+5),numpy.float64))
                            else:
                                PEAKSW.append(numpy.ones(((r+_nescape_),3+5),
                                                            numpy.float64))
                        else:
                            PEAKSW.append(numpy.ones((r,3+5),numpy.float64))
            elif (not usematrix) and (len(energylist) > 1):
                raise ValueError("Multiple energies require a matrix definition")
            else:
                print("Unknown case")
                print("usematrix = ",usematrix)
                print("self.config['fit']['energy'] =",self.config['fit']['energy'])
                raise ValueError("Unhandled Sample Matrix and Energy combination")
###############
        #add scatter peak
        if energylist is not None:
            if len(energylist) and \
               (self.config['fit']['scatterflag']):
                for scatterindex in range(len(energylist)):
                    if energyscatter[scatterindex]:
                        ene = energylist[scatterindex]
                        #print "ene = ",ene,"scatterindex = ",scatterindex
                        #print "scatter for first energy"
                        if ene > 0.2:
                            for i in range(2):
                                ene = energylist[scatterindex]
                                if i == 1:
                                    try:
                                        alphaIn  = self.config['attenuators']['Matrix'][4]
                                    except Exception:
                                        print("WARNING: Matrix incident angle set to 45 deg.")
                                        alphaIn  = 45.0
                                    try:
                                        alphaOut = self.config['attenuators']['Matrix'][5]
                                    except Exception:
                                        print("WARNING: Matrix outgoing angle set to 45 deg.")
                                        alphaOut  = 45.0

                                    scatteringAngle = (alphaIn + alphaOut)
                                    if len(self.config['attenuators']['Matrix']) == 8:
                                        if self.config['attenuators']['Matrix'][6]:
                                            scatteringAngle = self.config['attenuators']\
                                                              ['Matrix'][7]
                                    scatteringAngle = scatteringAngle * numpy.pi/180.
                                    ene = ene / (1.0 + (ene/511.0) * (1.0 - numpy.cos(scatteringAngle)))
                                fwhm = numpy.sqrt(noise*noise + \
                                        0.00385 *ene* fano*2.3548*2.3548)
                                PEAKS0.append(numpy.array([[1.0, ene, fwhm, 0.0]]))
                                PEAKS0NAMES.append(['Scatter %03d' % scatterindex])
                                PEAKS0ESCAPE.append([])
                                _nescape_ = 0
                                if self.config['fit']['escapeflag']:
                                    if self.__USE_FISX_ESCAPE:
                                        _logger.debug("Using fisx escape")
                                        xcom = FisxHelper.xcom
                                        detector_composition = Elements.getMaterialMassFractions([detele],
                                                                                                 [1.0])
                                        xcom.updateEscapeCache(detector_composition,
                                                               [ene],
                                                               energyThreshold=ethreshold,
                                                               intensityThreshold=ithreshold,
                                                               nThreshold=nthreshold)
                                        _esc_ = xcom.getEscape(detector_composition,
                                                       ene,
                                                       energyThreshold=ethreshold,
                                                       intensityThreshold=ithreshold,
                                                       nThreshold=nthreshold)
                                        _esc_ = [[_esc_[x]["energy"],
                                                  _esc_[x]["rate"],
                                                  x[:-3].replace("_"," ")] for x in _esc_]
                                        _esc_ = Elements._filterPeaks(_esc_, ethreshold=ethreshold,
                                                              ithreshold=ithreshold,
                                                              nthreshold=nthreshold,
                                                              absoluteithreshold=True,
                                                              keeptotalrate=False)
                                    else:
                                        _esc_ = Elements.getEscape([detele,1.0,1.0],
                                                            ene,
                                                            ethreshold=ethreshold, ithreshold=ithreshold,
                                                            nthreshold=nthreshold)
                                    PEAKS0ESCAPE[-1].append(_esc_)
                                    _nescape_ += len(_esc_)
                                r = 1
                                if not HYPERMET:
                                    if self.config['fit']['escapeflag']:
                                        if OLDESCAPE:
                                            PEAKSW.append(numpy.ones((2*r, 3 + 1),numpy.float64))
                                        else:
                                            PEAKSW.append(numpy.ones(((r+_nescape_), 3 + 1),
                                                                        numpy.float64))
                                    else:
                                        PEAKSW.append(numpy.ones((r, 3 + 1),numpy.float64))
                                else:
                                    if self.config['fit']['escapeflag']:
                                        if OLDESCAPE:
                                            PEAKSW.append(numpy.ones((2*r, 3+5),numpy.float64))
                                        else:
                                            PEAKSW.append(numpy.ones(((r+_nescape_),3+5),
                                                                        numpy.float64))
                                    else:
                                        PEAKSW.append(numpy.ones((r,3+5),numpy.float64))
#########
        PARAMETERS=['Zero','Gain','Noise','Fano','Sum']
        CONTINUUM    = self.config['fit']['continuum']

        #CONTINUUM_LIST = [None,'Constant','Linear','Parabolic',
        #                    'Linear Polynomial','Exp. Polynomial']
        if CONTINUUM < CONTINUUM_LIST.index('Linear Polynomial'):
            PARAMETERS.append('Constant')
            PARAMETERS.append('1st Order')
            if CONTINUUM >2:
                PARAMETERS.append('2nd Order')
        elif CONTINUUM == CONTINUUM_LIST.index('Linear Polynomial'):
            for i in range(self.config['fit']['linpolorder']+1):
                PARAMETERS.append('A%d'  % i)
        elif CONTINUUM == CONTINUUM_LIST.index('Exp. Polynomial'):
            for i in range(self.config['fit']['exppolorder']+1):
                PARAMETERS.append('A%d'  % i)
        if HYPERMET:
            PARAMETERS.append('ST AreaR')
            PARAMETERS.append('ST SlopeR')
            PARAMETERS.append('LT AreaR')
            PARAMETERS.append('LT SlopeR')
            PARAMETERS.append('STEP HeightR')
        else:
            PARAMETERS.append('Eta Factor')
        NGLOBAL   = len(PARAMETERS)
        for item in data:
            PARAMETERS.append(item[1]+" "+item[2])
        if energylist is not None:
            if len(energylist) and \
               (self.config['fit']['scatterflag']):
                for scatterindex in range(len(energylist)):
                    if energyscatter[scatterindex]:
                        ene = energylist[scatterindex]
                        #print "ene = ",ene,"scatterindex = ",scatterindex
                        #print "scatter for first energy"
                        if ene > 0.2:
                            PARAMETERS.append("Scatter Peak%03d" % scatterindex)
                            PARAMETERS.append("Scatter Compton%03d" % scatterindex)
                            #PARAMETERS.append("Scatter Peak")
                            #PARAMETERS.append("Scatter Compton")

        self.PEAKS0     = PEAKS0
        self.PEAKS0ESCAPE = PEAKS0ESCAPE
        #for i in range(len(PEAKS0)):
        #    print self.PEAKS0[i]
        #    print self.PEAKS0ESCAPE[i]
        self.PEAKS0NAMES= PEAKS0NAMES
        self.PEAKSW     = PEAKSW
        self.FASTER     = 1
        self.__HYPERMET   = HYPERMET
        self.NGLOBAL    = NGLOBAL
        self.PARAMETERS = PARAMETERS
        self.ESCAPE     = self.config['fit']['escapeflag']
        self.__SUM        = self.config['fit']['sumflag']
        self.__CONTINUUM     = CONTINUUM
        self.MAXITER    = self.config['fit']['maxiter']
        self.STRIP      = self.config['fit']['stripflag']
        #if self.laststrip is not None:
        self.__mycounter = 0
        calculateStrip = False
        if (self.STRIP != self.laststrip) or \
           (self.config['fit']['stripalgorithm'] != self.laststripalgorithm) or \
           (self.config['fit']['stripfilterwidth'] != self.laststripfilterwidth) or \
           (self.config['fit']['stripanchorsflag'] != self.laststripanchorsflag) or \
           (self.config['fit']['stripanchorslist'] != self.laststripanchorslist):
            calculateStrip = True
        if not calculateStrip:
            if self.config['fit']['stripalgorithm'] == 1:
                #checking if needed to calculate SNIP
                if (self.config['fit']['snipwidth'] != self.lastsnipwidth):
                    calculateStrip = True
            else:
                #checking if needed to calculate strip
                if (self.config['fit']['stripiterations'] != self.laststripiterations) or \
                   (self.config['fit']['stripwidth'] != self.laststripwidth) or \
                   (self.config['fit']['stripconstant'] != self.laststripconstant):
                    calculateStrip = True
        if (self.lastxmin != self.config['fit']['xmin']) or\
           (self.lastxmax != self.config['fit']['xmax']):
            if self.ydata0 is not None:
                _logger.debug("Limits changed")
                self.setData(x=self.xdata0,
                             y=self.ydata0,
                             sigmay=self.sigmay0,
                             xmin = self.config['fit']['xmin'],
                             xmax = self.config['fit']['xmax'],
                             time = self.__lastTime)
                return

        if hasattr(self, "xdata"):
            if self.STRIP:
                if calculateStrip:
                    _logger.debug("Calling to calculate non analytical background in config")
                    self.__getselfzz()
                else:
                    _logger.debug("Using previous non analytical background in config")
                self.datatofit = numpy.concatenate((self.xdata,
                                self.ydata-self.zz, self.sigmay),1)
                self.laststrip = 1
            else:
                _logger.debug("Using previous data")
                self.datatofit = numpy.concatenate((self.xdata,
                                self.ydata, self.sigmay),1)
                self.laststrip = 0

    def setdata(self, *var, **kw):
        print("ClassMcaTheory.setdata deprecated, please use setData")
        return self.setData(*var, **kw)

    def setData(self,*var,**kw):
        """
        Method to update the data to be fitted.
        It accepts several combinations of input arguments, the simplest to
        take into account is:

        setData(x, y sigmay=None, xmin=None, xmax=None)

        x corresponds to the spectrum channels
        y corresponds to the spectrum counts
        sigmay is the uncertainty associated to the counts. If not given,
               Poisson statistics will be assumed. If the fit configuration
               is set to no weight, it will not be used.
        xmin and xmax define the limits to be considered for performing the fit.
               If the fit configuration flag self.config['fit']['use_limit'] is
               set, they will be ignored. If xmin and xmax are not given, the
               whole given spectrum will be considered for fitting.
        time (seconds) is the factor associated to the flux, only used when using
               a strategy based on concentrations
        """
        if self.__toBeConfigured:
            _logger.debug("setData RESTORE ORIGINAL CONFIGURATION")
            self.configure(self.__originalConfiguration)
        if 'x' in kw:
            x=kw['x']
        elif len(var) >1:
            x=var[0]
        else:
            x=None
        if 'y' in kw:
            y=kw['y']
        elif len(var) > 1:
            y=var[1]
        elif len(var) == 1:
            y=var[0]
        else:
            y=None
        if 'sigmay' in kw:
            sigmay=kw['sigmay']
        elif len(var) >2:
            sigmay=var[2]
        else:
            sigmay=None
        if y is None:
            return 1
        else:
            self.ydata0=numpy.array(y)
            self.ydata=numpy.array(y)

        if x is None:
            self.xdata0=numpy.arange(len(self.ydata0))
            self.xdata=numpy.arange(len(self.ydata0))
        else:
            self.xdata0=numpy.array(x)
            self.xdata=numpy.array(x)

        if sigmay is None:
            dummy = numpy.sqrt(abs(self.ydata0))
            self.sigmay0=numpy.reshape(dummy + numpy.equal(dummy,0),self.ydata0.shape)
            self.sigmay=numpy.reshape(dummy + numpy.equal(dummy,0),self.ydata0.shape)
        else:
            self.sigmay0=numpy.array(sigmay)
            self.sigmay=numpy.array(sigmay)

        timeFactor = kw.get("time", None)
        self.__lastTime = timeFactor
        if timeFactor is None:
            if "concentrations" in self.config:
                if self.config["concentrations"].get("useautotime", False):
                    if not self.config["concentrations"]["usematrix"]:
                        msg = "Requested to use time from data but not present!!"
                        raise ValueError(msg)
        elif self.config["concentrations"].get("useautotime", False):
            self.config["concentrations"]["time"] = timeFactor

        xmin = kw.get("xmin")
        if xmin is None and self.config['fit']['use_limit']:
            xmin = self.config['fit']['xmin']
        if xmin is None and len(self.xdata):
            xmin = min(self.xdata)

        xmax = kw.get("xmax")
        if xmax is None and self.config['fit']['use_limit']:
            xmax = self.config['fit']['xmax']
        if xmax is None and len(self.xdata):
            xmax = max(self.xdata)

        _logger.info("X-axis fit limits: xmin=%s, xmax=%s", xmin, xmax)

        self.lastxmin = xmin
        self.lastxmax = xmax

        if len(self.xdata):
            #sort the data
            i1=numpy.argsort(self.xdata)
            self.xdata=numpy.take(self.xdata,i1)
            self.ydata=numpy.take(self.ydata,i1)
            self.sigmay=numpy.take(self.sigmay,i1)

            #take the data between limits
            i1=numpy.nonzero((self.xdata >=xmin) & (self.xdata<=xmax))[0]
            self.xdata=numpy.take(self.xdata,i1)
            n=len(self.xdata)
            #Calculate the background just of the regions gives better results
            #self.zz=SpecfitFuns.subac(self.ydata,1.000,20000)
            #self.zz   =numpy.take(self.zz,i1)
            self.ydata=numpy.take(self.ydata,i1)

            #calculate the background here gives better results
            if not self.config['fit']['linearfitflag']:
                self.__getselfzz()
            else:
                if self.STRIP:
                    self.__getselfzz()
                else:
                    self.laststrip = None
                    self.zz     = numpy.zeros((n,1),numpy.float64)

            self.sigmay=numpy.take(self.sigmay,i1)
            self.xdata = numpy.resize(self.xdata,(n,1))
            self.ydata = numpy.resize(self.ydata,(n,1))
            self.sigmay= numpy.resize(self.sigmay,(n,1))
            if self.STRIP:
                self.datatofit = numpy.concatenate((self.xdata, self.ydata-self.zz, self.sigmay),1)
                self.laststrip = 1
            else:
                self.datatofit = numpy.concatenate((self.xdata,self.ydata,self.sigmay),1)
                if self.config['fit']['linearfitflag']:
                    self.laststrip = None
                else:
                    self.laststrip = 0

    def getLastTime(self):
        return self.__lastTime

    def __smooth(self,y):
        f=[0.25,0.5,0.25]
        try:
            if hasattr(y, "shape"):
                if len(y.shape) > 1:
                    result=SpecfitFuns.SavitskyGolay(numpy.ravel(y).astype(numpy.float64),
                                    self.config['fit']['stripfilterwidth'])
                else:
                    result=SpecfitFuns.SavitskyGolay(numpy.array(y).astype(numpy.float64),
                                    self.config['fit']['stripfilterwidth'])
            else:
                result=SpecfitFuns.SavitskyGolay(numpy.array(y).astype(numpy.float64),
                                    self.config['fit']['stripfilterwidth'])
        except Exception:
            print("Unsuccessful Savitsky-Golay smoothing: %s" % sys.exc_info())
            raise
            result=numpy.array(y).astype(numpy.float64)
        if len(result) > 1:
            result[1:-1]=numpy.convolve(result,f,mode=0)
            result[0]=0.5*(result[0]+result[1])
            result[-1]=0.5*(result[-1]+result[-2])
        return result


    def __getselfzz(self):
        n=len(self.xdata)

        #loop for anchors
        anchorslist = []
        if self.config['fit']['stripanchorsflag']:
            if self.config['fit']['stripanchorslist'] is not None:
                ravelled = numpy.ravel(self.xdata)
                for channel in self.config['fit']['stripanchorslist']:
                    if channel <= ravelled[0]:continue
                    index = numpy.nonzero(ravelled >= channel)[0]
                    if len(index):
                        index = min(index)
                        if index > 0:
                            anchorslist.append(index)

        #work with smoothed data
        ysmooth = numpy.ravel(self.__smooth(self.ydata))

        #SNIP algorithm
        if self.config['fit']['stripalgorithm'] == 1:
            _logger.debug("CALCULATING SNIP")
            if len(anchorslist) == 0:
                anchorslist = [0, len(ysmooth)-1]
            anchorslist.sort()
            self.zz = 0.0 * ysmooth
            lastAnchor = 0
            width = self.config['fit']['snipwidth']
            for anchor in anchorslist:
                if (anchor > lastAnchor) and (anchor < len(ysmooth)):
                    self.zz[lastAnchor:anchor] =\
                            SpecfitFuns.snip1d(ysmooth[lastAnchor:anchor], width, 0)
                    lastAnchor = anchor
            if lastAnchor < len(ysmooth):
                self.zz[lastAnchor:] =\
                        SpecfitFuns.snip1d(ysmooth[lastAnchor:], width, 0)
            self.zz = self.zz.reshape(n, 1)
            self.laststripalgorithm  = self.config['fit']['stripalgorithm']
            self.lastsnipwidth       = self.config['fit']['snipwidth']
            self.laststripfilterwidth = self.config['fit']['stripfilterwidth']
            self.laststripanchorsflag     = self.config['fit']['stripanchorsflag']
            self.laststripanchorslist     = self.config['fit']['stripanchorslist']
            return

        #strip background
        niter = self.config['fit']['stripiterations']
        if niter > 0:
            _logger.debug("CALCULATING STRIP")
            if (niter > 1000) and (self.config['fit']['stripwidth'] == 1):
                self.zz=SpecfitFuns.subac(ysmooth,
                                      self.config['fit']['stripconstant'],
                                      niter/20,4, anchorslist)
                self.zz=SpecfitFuns.subac(self.zz,
                                      self.config['fit']['stripconstant'],
                                      niter/4,
                                      self.config['fit']['stripwidth'],
                                      anchorslist)
            else:
                self.zz=SpecfitFuns.subac(ysmooth,
                                      self.config['fit']['stripconstant'],
                                      niter,
                                      self.config['fit']['stripwidth'],
                                      anchorslist)
                if niter > 1000:
                    #make sure to get something smooth
                    self.zz = SpecfitFuns.subac(self.zz,
                                      self.config['fit']['stripconstant'],
                                      500,1,
                                      anchorslist)
                else:
                    #make sure to get something smooth but with less than
                    #500 iterations
                    self.zz = SpecfitFuns.subac(self.zz,
                                      self.config['fit']['stripconstant'],
                                      int(self.config['fit']['stripwidth']*2),
                                      1,
                                      anchorslist)
            self.zz     = numpy.resize(self.zz,(n,1))
        else:
            self.zz     = numpy.zeros((n,1),numpy.float64) + min(ysmooth)

        self.laststripalgorithm  = self.config['fit']['stripalgorithm']
        self.laststripwidth      = self.config['fit']['stripwidth']
        self.laststripfilterwidth = self.config['fit']['stripfilterwidth']
        self.laststripconstant   = self.config['fit']['stripconstant']
        self.laststripiterations = self.config['fit']['stripiterations']
        self.laststripanchorsflag     = self.config['fit']['stripanchorsflag']
        self.laststripanchorslist     = self.config['fit']['stripanchorslist']

    def getPeakMatrixContribution(self,param0,t0=None,hypermet=None,
                                  continuum=None,summing=None):
        """
        For the time being a huge copy paste from mcatheory
        """
        if continuum is None:
            continuum = self.__CONTINUUM
        if hypermet is None:
            hypermet = self.__HYPERMET
        if summing is None:
            summing  = self.__SUM
        param= numpy.array(param0)
        #param= numpy.ones(param.shape, numpy.float64)
        if t0 is None:t0 = self.xdata
        x    = numpy.array(t0)
        matrix = numpy.zeros((len(x),len(param)-self.NGLOBAL)).astype(numpy.float64)


        zero = param[0]
        gain = param[1]
        energy=zero + gain * x
        #print energy
        noise= param[2] * param[2]
        fano = param[3] * 2.3548*2.3548*0.00385
        #t=time.time()
        PEAKS0 = self.PEAKS0
        PEAKS0ESCAPE = self.PEAKS0ESCAPE
        PEAKSW = self.PEAKSW
        PARAMETERS = self.PARAMETERS
        FASTER = 0
        for i in range(len(param[self.NGLOBAL:])):
            result = 0 * energy
            if self.ESCAPE:
                #area = param[NGLOBAL+i]
                (r,c) = (PEAKS0[i]).shape
                PEAKSW[i][0:r,0] = PEAKS0[i][:,0] * 1 * gain
                PEAKSW[i][0:r,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][0:r,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                #escape
                if OLDESCAPE:
                    PEAKSW[i][r:,0] = PEAKSW[i][0:r,0] * PEAKS0[i][:,3]
                    PEAKSW[i][r:,1] = PEAKS0[i][:,1] - self.config['detector']['detene']
                    PEAKSW[i][r:,2] = numpy.sqrt(noise + \
                                        (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                else:
                    ii=0
                    j=0
                    for esc_group in PEAKS0ESCAPE[i]:
                        for esc_line in esc_group:
                            esc_ene  = esc_line[0] * 1.0
                            esc_rate = esc_line[1]
                            PEAKSW[i][j+r,0] =  PEAKSW[i][ii,0] * esc_rate
                            PEAKSW[i][j+r,1] =  esc_ene
                            j = j + 1
                        ii = ii + 1
                    PEAKSW[i][r:, 2] = numpy.sqrt(noise + \
                                    (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                (rw,cw) = (PEAKSW[i]).shape
                if 0 and self.PARAMETERS[self.NGLOBAL+i] =='Fe K':
                  for ii in range(rw):
                    if ii < r:
                        print(self.PARAMETERS[self.NGLOBAL+i],"PEAK ",ii,PEAKSW[i][ii])
                    else:
                        print(self.PARAMETERS[self.NGLOBAL+i],"PEAKesc ",ii,PEAKSW[i][ii])
                #print PARAMETERS[self.NGLOBAL+i]
                #print PEAKSW[i][:,1]
                #print PEAKS0ESCAPE[i]
                #for j in range(PEAKSW[i].shape[0]):
                #    print "H = ", PEAKSW[i][j*r,0],"E = ",PEAKSW[i][j*r,1]

                #if HYPERMET:
                if hypermet:
                    PEAKSW[i] [0:r,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [0:r,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [0:r,7] = param[PARAMETERS.index('STEP HeightR')]
                    #neglect tails in escape peaks
                    PEAKSW[i] [r:,3] = 0.0
                    PEAKSW[i] [r:,5] = 0.0
                    PEAKSW[i] [r:,7] = 0.0
                if not FASTER:
                    #if HYPERMET:
                    if hypermet:
                        if i == 0:
                            result = SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                        else:
                            result += SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                    else:
                        if i == 0:
                            result = SpecfitFuns.apvoigt(PEAKSW[i],energy)
                        else:
                            result += SpecfitFuns.apvoigt(PEAKSW[i],energy)
            else:
                PEAKSW[i][:,0] = PEAKS0[i][:,0] * param[self.NGLOBAL+i] * gain
                PEAKSW[i][:,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][:,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                if hypermet:
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [:,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [:,7] = param[PARAMETERS.index('STEP HeightR')]
                else:
                    #pseudo voigt
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('Eta Factor')]
                if not FASTER:
                    if hypermet:
                        if i == 0:
                            result = SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                        else:
                            result += SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                    else:
                        if i == 0:
                            result = SpecfitFuns.apvoigt(PEAKSW[i],energy)
                        else:
                            result += SpecfitFuns.apvoigt(PEAKSW[i],energy)
            #print "shape = ",result.shape
            #print "matrix = ",matrix.shape
            matrix[:,i] = result[:,0]
        return matrix

    def linearMcaTheory(self, param0, t0, hypermet=None, continuum=None, summing=None):
        if continuum is None:
            continuum = self.__CONTINUUM
        if hypermet is None:
            hypermet = self.__HYPERMET
        if summing is None:
            summing  = self.__SUM
        param= numpy.array(param0)
        x    = numpy.array(t0)
        zero = param[0]
        gain = param[1]
        #the loop in mcatheory is replaced by this single line
        if len(self.PEAKSW[:]):
            result = numpy.sum(param[self.NGLOBAL:] * self.linearMatrix, 1)
        else:
            result = 0.0 * x
        if continuum:
            result += self.continuum(param,x)
        if summing:
            xmin=int(x[0])
            return result+param[4]*SpecfitFuns.pileup(result, xmin, zero, gain)
        else:
            return result

    def mcatheory(self,param0,t0,hypermet=None,continuum=None,summing=None):
        if continuum is None:
            continuum = self.__CONTINUUM
        if hypermet is None:
            hypermet = self.__HYPERMET
        if summing is None:
            summing  = self.__SUM
        param= numpy.array(param0)
        x    = numpy.array(t0)
        zero = param[0]
        gain = param[1]
        energy=zero + gain * x
        #print energy
        noise= param[2] * param[2]
        fano = param[3] * 2.3548*2.3548*0.00385
        #t=time.time()
        PEAKS0 = self.PEAKS0
        PEAKS0ESCAPE = self.PEAKS0ESCAPE
        PEAKSW = self.PEAKSW
        PARAMETERS = self.PARAMETERS
        FASTER = self.FASTER
        for i in range(len(param[self.NGLOBAL:])):
            if self.ESCAPE:
                #area = param[NGLOBAL+i]
                (r,c) = (PEAKS0[i]).shape
                PEAKSW[i][0:r,0] = PEAKS0[i][:,0] * param[self.NGLOBAL+i] * gain
                PEAKSW[i][0:r,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][0:r,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                #escape
                if OLDESCAPE:
                    PEAKSW[i][r:,0] = PEAKSW[i][0:r,0] * PEAKS0[i][:,3]
                    PEAKSW[i][r:,1] = PEAKS0[i][:,1] - self.config['detector']['detene']
                    PEAKSW[i][r:,2] = numpy.sqrt(noise + \
                                        (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                else:
                    ii=0
                    j=0
                    for esc_group in PEAKS0ESCAPE[i]:
                        for esc_line in esc_group:
                            esc_ene  = esc_line[0] * 1.0
                            esc_rate = esc_line[1]
                            PEAKSW[i][j+r,0] =  PEAKSW[i][ii,0] * esc_rate
                            PEAKSW[i][j+r,1] =  esc_ene
                            j = j + 1
                        ii = ii + 1
                    PEAKSW[i][r:, 2] = numpy.sqrt(noise + \
                                    (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                (rw,cw) = (PEAKSW[i]).shape
                if 0 and self.PARAMETERS[self.NGLOBAL+i] =='Fe K':
                  for ii in range(rw):
                    if ii < r:
                        print(self.PARAMETERS[self.NGLOBAL+i],"PEAK ",ii,PEAKSW[i][ii])
                    else:
                        print(self.PARAMETERS[self.NGLOBAL+i],"PEAKesc ",ii,PEAKSW[i][ii])
                #print PARAMETERS[self.NGLOBAL+i]
                #print PEAKSW[i][:,1]
                #print PEAKS0ESCAPE[i]
                #for j in range(PEAKSW[i].shape[0]):
                #    print "H = ", PEAKSW[i][j*r,0],"E = ",PEAKSW[i][j*r,1]

                #if HYPERMET:
                if hypermet:
                    PEAKSW[i] [0:r,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [0:r,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [0:r,7] = param[PARAMETERS.index('STEP HeightR')]
                    #neglect tails in escape peaks
                    PEAKSW[i] [r:,3] = 0.0
                    PEAKSW[i] [r:,5] = 0.0
                    PEAKSW[i] [r:,7] = 0.0
                else:
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('Eta Factor')]
                if not FASTER:
                    print("not FASTER")
                    #if HYPERMET:
                    if hypermet:
                        if i == 0:
                            result = SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                        else:
                            result += SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                    else:
                        if i == 0:
                            result = SpecfitFuns.apvoigt(PEAKSW[i],energy)
                        else:
                            result += SpecfitFuns.apvoigt(PEAKSW[i],energy)
            else:
                PEAKSW[i][:,0] = PEAKS0[i][:,0] * param[self.NGLOBAL+i] * gain
                PEAKSW[i][:,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][:,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                if hypermet:
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [:,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [:,7] = param[PARAMETERS.index('STEP HeightR')]
                else:
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('Eta Factor')]
                if not FASTER:
                    if hypermet:
                        if i == 0:
                            result = SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                        else:
                            result += SpecfitFuns.ahypermet(PEAKSW[i],energy,hypermet)
                    else:
                        if i == 0:
                            result = SpecfitFuns.apvoigt(PEAKSW[i],energy)
                        else:
                            result += SpecfitFuns.apvoigt(PEAKSW[i],energy)
        #print PARAMETERS[self.NGLOBAL+4]
        #print self.PEAKS0NAMES[4]
        #print PEAKSW[4]
        #print "loop takes ",time.time()-t
        #loop takes 0.006 seconds
        #t=time.time()
        if FASTER:
            if len(PEAKSW[:]):
                a=numpy.concatenate(PEAKSW[:])
                #t=time.time()
                #result = SpecfitFuns.agauss(a,energy)
                #if HYPERMET:
                if hypermet:
                    result = SpecfitFuns.fastahypermet(a,energy,hypermet)
                else:
                    result = SpecfitFuns.apvoigt(a,energy)
            else:
                result = 0.0 * x
            #print "eval = ",time.time()-t
        #evaluation takes 0.058 seconds
        #with less peaks 0.036
        #with tabulated function 0.018
        if continuum:
            result += self.continuum(param,x)
        if summing:
          if 0:
            pileup = numpy.arange(3*len(x))*0.0
            sumfactor = param[4]
            xmin=int(x[0])
            offset = zero / gain
            for i in range(len(result)):
                pileup[i+xmin-offset:i+len(result)+xmin-i-offset] += sumfactor * result[i] *result[0:len(result)-i]
            return result+pileup[0:len(result)]
          else:
            #summing takes 0.0047 seconds
            xmin=int(x[0])
            return result+param[4]*SpecfitFuns.pileup(result, xmin, zero, gain)
        else:
            return result

    def continuum(self,param,x):
        #CONTINUUM_LIST = [None,'Constant','Linear','Parabolic','Linear Polynomial','Exp. Polynomial']
        if self.__CONTINUUM == CONTINUUM_LIST.index('Constant'):
            return param[self.PARAMETERS.index('Constant')] + 0.0 * x
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Linear'):
            return param[self.PARAMETERS.index('Constant')] + \
                    param[self.PARAMETERS.index('1st Order')] * x
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Parabolic'):
            return param[self.PARAMETERS.index('Constant')] + \
                    param[self.PARAMETERS.index('1st Order')] * x +\
                    param[self.PARAMETERS.index('2nd Order')] * x * x
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Linear Polynomial'):
            energy = param[0] + param[1] * (x - numpy.sum(x)/len(x))
            if self.__HYPERMET:
                return self.linpol(param[(self.PARAMETERS.index('Sum')+1):self.NGLOBAL-5],energy)
            else:
                return self.linpol(param[(self.PARAMETERS.index('Sum')+1):self.NGLOBAL-1],energy)
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Exp. Polynomial'):
            energy = param[0] + param[1] * (x - numpy.sum(x)/len(x))
            if self.__HYPERMET:
                return self.exppol(param[(self.PARAMETERS.index('Sum')+1):self.NGLOBAL-5],energy)
            else:
                return self.exppol(param[(self.PARAMETERS.index('Sum')+1):self.NGLOBAL-1],energy)
        else:
            return 0.0 * x
    def num_deriv(self, param0,index,t0):
            #numerical derivative
            x=numpy.array(t0)
            delta = (param0[index] + numpy.equal(param0[index],0.0)) * 0.00001
            newpar = param0.copy()
            newpar[index] = param0[index] + delta
            f1 = self.mcatheory(newpar, x)
            newpar[index] = param0[index] - delta
            f2 = self.mcatheory(newpar, x)
            return (f1-f2) / (2.0 * delta)

    def linearMcaTheoryDerivative(self, param0, index, t0):
        NGLOBAL = self.NGLOBAL
        if index > NGLOBAL-1:
             return self.linearMatrix[:, index-NGLOBAL]
        PARAMETERS = self.PARAMETERS
        if self.__CONTINUUM and (PARAMETERS[index] == 'Constant'):
            return numpy.ones(len(t0)).astype(numpy.float64)
        elif self.__CONTINUUM and (PARAMETERS[index] == '1st Order'):
            return numpy.array(t0).astype(numpy.float64)
        elif self.__CONTINUUM and (PARAMETERS[index] == '2nd Order'):
            a = numpy.array(t0).astype(numpy.float64)
            return a*a
        elif (self.__CONTINUUM == CONTINUUM_LIST.index('Linear Polynomial')) and \
             (PARAMETERS[index] == ( 'A%d' % (index-PARAMETERS.index('Sum')-1))):
            param=numpy.asarray(param0)
            x=numpy.asarray(t0)
            zero = param[0]
            gain = param[1] * 1.0
            energy=zero + gain * x
            energy -= numpy.sum(energy)/len(energy)
            return pow(energy,index-PARAMETERS.index('Sum')-1)
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Exp. Polynomial') and \
            PARAMETERS[index] == ('A%d' % (index-PARAMETERS.index('Sum')-1)):
            text  = "Linear Least-Squares Fit incompatible\n"
            text += "with Exponential Background"
            raise ValueError(text)
        else:
            #I guess I will not arrive here
            #numerical derivative
            #print "index = ",index
            x=numpy.array(t0)
            delta = (param0[index] + numpy.equal(param0[index],0.0)) * 0.00001
            newpar = param0.copy()
            newpar[index] = param0[index] + delta
            f1 = self.linearMcaTheory(newpar, x)
            newpar[index] = param0[index] - delta
            f2 = self.linearMcaTheory(newpar, x)
            #print "f1,f2,delta = ",f1,f2,delta
            return (f1-f2) / (2.0 * delta)

    def analyticalDerivative(self, param0, index, t0):
        """
        analyticalDerivative(self, parameters, index, x)
        Internal function to calculate the derivative of the fitting function
        f(parameters, x) respect to the parameter given by the index at the
        array of points x.
        """
        NGLOBAL = self.NGLOBAL
        HYPERMET = self.__HYPERMET
        PARAMETERS = self.PARAMETERS
        ESCAPE = self.ESCAPE
        PEAKS0 = self.PEAKS0
        if index > NGLOBAL-1:
         param=numpy.array(param0)
         x=numpy.array(t0)
         zero = param[0]
         gain = param[1] * 1.0
         energy=zero + gain * x
         #print energy
         noise= param[2]*param[2]
         fano = param[3]*2.3548*2.3548*0.00385
         i=index-NGLOBAL
         #for i in range(len(param[index-4]))):
         if ESCAPE:
            (r,c) = (PEAKS0[i]).shape
            if OLDESCAPE:
                if HYPERMET:
                    dummy      = numpy.ones((2*r,3+5*(HYPERMET > 0)), numpy.float64)
                else:
                    dummy      = numpy.ones((2*r,3+1), numpy.float64)
                dummy[0:r,0] = PEAKS0[i][:,0] * gain
                dummy[0:r,1] = PEAKS0[i][:,1] * 1.0
                dummy[0:r,2] = numpy.sqrt(noise+ PEAKS0[i][:,1] * fano)
                dummy[r:,0] = PEAKS0[i][:,0] * gain * PEAKS0[i][:,3]
                dummy[r:,1] = PEAKS0[i][:,1] - self.config['detector']['detene']
                dummy[r:,2] = numpy.sqrt(noise + (dummy[r:,1]>0) * dummy[r:,1] * fano)
            else:
                n_escape_lines = self.PEAKSW[i].shape[0] - r
                #if 1:print "nlines = ",r, "n escape lines =",n_escape_lines
                if HYPERMET:
                    dummy    = numpy.ones((r + n_escape_lines, 3+5*(HYPERMET > 0)), numpy.float64)
                else:
                    dummy    = numpy.ones((r + n_escape_lines, 3+1), numpy.float64)
                dummy[0:r,0] = PEAKS0[i][:,0] * gain
                dummy[0:r,1] = PEAKS0[i][:,1] * 1.0
                dummy[0:r,2] = numpy.sqrt(noise+ PEAKS0[i][:,1] * fano)
                ii=0
                j=0
                for esc_group in self.PEAKS0ESCAPE[i]:
                    for esc_line in esc_group:
                        esc_ene  = esc_line[0] * 1.0
                        esc_rate = esc_line[1]
                        dummy[j+r, 0] =  dummy[ii,0] * esc_rate
                        dummy[j+r, 1] =  esc_ene
                        j = j + 1
                    ii = ii + 1
                dummy[r:, 2] = numpy.sqrt(noise + (dummy[r:,1]>0) * dummy[r:,1] * fano)
                #for jj in range(r+n_escape_lines):
                #    print index, dummy[jj, 1], dummy[jj, 0], dummy[jj, 2]
         else:
            (r,c) = (PEAKS0[i]).shape
            if HYPERMET:
                dummy      = numpy.ones((r,3+5*(HYPERMET > 0)),numpy.float64)
            else:
                dummy      = numpy.ones((r,3+1),numpy.float64)
            dummy[0:r,0] = PEAKS0[i][:,0] * gain
            dummy[0:r,1] = PEAKS0[i][:,1] * 1.0
            dummy[0:r,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
         if HYPERMET:
                dummy[0:r,3] = param[PARAMETERS.index('ST AreaR')]
                dummy[r:,3]  = 0.0
                dummy[:,4] = param[PARAMETERS.index('ST SlopeR')]
                dummy[0:r,5] = param[PARAMETERS.index('LT AreaR')]
                dummy[r:,5]  = 0.0
                dummy[:,6] = param[PARAMETERS.index('LT SlopeR')]
                dummy[0:r,7] = param[PARAMETERS.index('STEP HeightR')]
                dummy[r:,7]  = 0.0
         else:
                dummy[0:,3] = param[PARAMETERS.index('Eta Factor')]
         if self.FASTER:
            if HYPERMET:
                return SpecfitFuns.fastahypermet(dummy,energy,HYPERMET)
            else:
                return SpecfitFuns.apvoigt(dummy,energy)
         else:
            if HYPERMET:
                return SpecfitFuns.ahypermet(dummy,energy,HYPERMET)
            else:
                return SpecfitFuns.apvoigt(dummy,energy)

        elif HYPERMET and  (PARAMETERS[index] == 'ST AreaR'):
          param=numpy.array(param0)
          x=numpy.array(t0)
          param[index] = 1.0
          return self.mcatheory(param,x,hypermet=2,continuum=0)
        elif HYPERMET and  (PARAMETERS[index] == 'LT AreaR'):
          param=numpy.array(param0)
          x=numpy.array(t0)
          param[index] = 1.0
          return self.mcatheory(param,x,hypermet=4,continuum=0)
        elif HYPERMET and  (PARAMETERS[index] == 'STEP HeightR'):
          param=numpy.array(param0)
          x=numpy.array(t0)
          param[index] = 1.0
          return self.mcatheory(param,x,hypermet=8,continuum=0)
        elif self.__CONTINUUM and (PARAMETERS[index] == 'Constant'):
            return numpy.ones(len(t0))
        elif self.__CONTINUUM and (PARAMETERS[index] == '1st Order'):
            return numpy.array(t0)
        elif self.__CONTINUUM and (PARAMETERS[index] == '2nd Order'):
            return numpy.array(t0)*numpy.array(t0)
        elif (self.__CONTINUUM == CONTINUUM_LIST.index('Linear Polynomial')) and \
             (PARAMETERS[index] == ( 'A%d' % (index-PARAMETERS.index('Sum')-1))):
            param=numpy.array(param0)
            x=numpy.array(t0)
            zero = param[0]
            gain = param[1] * 1.0
            energy=zero + gain * x
            energy -= numpy.sum(energy)/len(energy)
            return pow(energy,index-PARAMETERS.index('Sum')-1)
        elif self.__CONTINUUM == CONTINUUM_LIST.index('Exp. Polynomial') and \
            PARAMETERS[index] == ('A%d' % (index-PARAMETERS.index('Sum')-1)):
            param=numpy.array(param0)
            x=numpy.array(t0)
            zero = param[0]
            gain = param[1] * 1.0
            energy=zero + gain * x
            energy -= numpy.sum(energy)/len(energy)
            if HYPERMET:
                parameters = param[(PARAMETERS.index('Sum')+1):NGLOBAL-5]
            else:
                parameters = param[(PARAMETERS.index('Sum')+1):NGLOBAL]
            return self.exppol_deriv(parameters,index-PARAMETERS.index('Sum')-1,energy)
        else:
            #numerical derivative
            #print "index = ",index
            x=numpy.array(t0)
            delta = (param0[index] + numpy.equal(param0[index],0.0)) * 0.00001
            newpar = param0.copy()
            newpar[index] = param0[index] + delta
            f1 = self.mcatheory(newpar, x)
            newpar[index] = param0[index] - delta
            f2 = self.mcatheory(newpar, x)
            #print "f1,f2,delta = ",f1,f2,delta
            return (f1-f2) / (2.0 * delta)

    def estimate(self):
        if self.__toBeConfigured:
            _logger.debug("CONFIGURING FROM ESTIMATION")
            self.configure(self.__originalConfiguration)
        self.parameters, self.codes = self.specfitestimate(self.xdata, self.ydata,self.zz)
        #self.estimatelinpoly(self.xdata, self.ydata,self.zz)
        #self.estimateexppoly(self.xdata, self.ydata,self.zz)
        #print self.codes[:,3]

    def specfitestimate(self,x,y,z,xscaling=1.0,yscaling=1.0):
        if self.PARAMETERS is None:
            self.__configure()
        PARAMETERS = self.PARAMETERS
        HYPERMET   = self.__HYPERMET
        NGLOBAL    = self.NGLOBAL
        CONTINUUM     = self.__CONTINUUM
        #linear fit flag
        linearfit = self.config['fit'].get("linearfitflag", 0)

        newpar=[]
        #default parameters from config
        zero      = self.config['detector']['zero']
        if self.config['detector']['fixedzero'] or linearfit:
            pass
        elif abs(zero) < 1.0E-10:
            #try to avoid a zero derivative because
            #the initial zero is too small
            zero = 0.0
        gain      = self.config['detector']['gain']
        sumfactor = self.config['detector']['sum']
        newpar.append(zero)
        newpar.append(gain)
        newpar.append(self.config['detector']['noise'])
        newpar.append(self.config['detector']['fano'])
        newpar.append(sumfactor)

        #####################
        if CONTINUUM == CONTINUUM_LIST.index('Linear Polynomial'):
            if linearfit:
                #no need to estimate background
                backpar = []
                for i in range(self.config['fit']['linpolorder']+1):
                    backpar.append(0.0)
                backcodes=numpy.zeros((3,len(backpar)),numpy.float64)
            else:
                backpar,backcodes=self.estimatelinpol(self.xdata, self.ydata,self.zz)
        elif CONTINUUM == CONTINUUM_LIST.index('Exp. Polynomial'):
            if linearfit:
                if 1:
                    text  = "Linear fit is incompatible with current implementation\n"
                    text += "of the Exponential Polynomial background"
                    raise ValueError(text)
                else:
                    #no need to estimate background
                    backpar = []
                    for i in range(self.config['fit']['exppolorder']+1):
                        backpar.append(0.0)
                    backcodes=numpy.zeros((3,len(backpar)),numpy.float64)
            else:
                backpar,backcodes=self.estimateexppol(self.xdata, self.ydata,self.zz)
        else:
            backpar = []
            if HYPERMET:
                for i in range(5,NGLOBAL-5):
                    backpar.append(0.0)
            else:
                for i in range(5,NGLOBAL-1):
                    backpar.append(0.0)
            backcodes=numpy.zeros((3,len(backpar)),numpy.float64)
            if CONTINUUM == 0:
                backcodes[0,:] = Gefit.CFIXED
            elif CONTINUUM == CONTINUUM_LIST.index('Constant'):
                backcodes[0,1] = Gefit.CFIXED
        for par in backpar:
            newpar.append(par)

        #initial areas
        if HYPERMET:
            hypermetflag = HYPERMET
            # g_term   = hypermetflag & 1
            st_term   = (hypermetflag >>1) & 1
            lt_term   = (hypermetflag >>2) & 1
            step_term = (hypermetflag >>3) & 1
            st_area     = self.config['peakshape']['st_arearatio']
            st_slope    = self.config['peakshape']['st_sloperatio']
            lt_area     = self.config['peakshape']['lt_arearatio']
            lt_slope    = self.config['peakshape']['lt_sloperatio']
            step_height = self.config['peakshape']['step_heightratio']
            if st_term:
                newpar.append(st_area)
                newpar.append(st_slope)
            else:
                newpar.append(0.0)
                newpar.append(st_slope)
            if lt_term:
                newpar.append(lt_area)
                newpar.append(lt_slope)
            else:
                newpar.append(0.0)
                newpar.append(lt_slope)
            if step_term:
                newpar.append(step_height)
            else:
                newpar.append(0.0)
        else:
            eta_factor = self.config['peakshape']['eta_factor']
            newpar.append(eta_factor)

        if not linearfit:
            for i in range(len(PARAMETERS)-NGLOBAL):
                newpar.append(10000.0)
        else:
            for i in range(len(PARAMETERS)-NGLOBAL):
                newpar.append(1.0)
        # the codes
        codes = numpy.zeros((3,len(newpar)),numpy.float64)
        codes[0,:]   = Gefit.CPOSITIVE # POSITIVE
        codes[0,0:4] = Gefit.CQUOTED # QUOTED
        if self.__SUM==0:
            newpar[PARAMETERS.index('Sum')]  = 0.0
            codes[0,PARAMETERS.index('Sum')] = Gefit.CFIXED

        else:
            codes[0,PARAMETERS.index('Sum')] = Gefit.CQUOTED

        for i in range(len(backpar)):
            newpar[PARAMETERS.index('Sum')+i+1]  = backpar[i]
            codes [0,PARAMETERS.index('Sum')+i+1]= backcodes[0,i]
            codes [1,PARAMETERS.index('Sum')+i+1]= backcodes[1,i]
            codes [2,PARAMETERS.index('Sum')+i+1]= backcodes[2,i]

        #in case of linear fit all non linear parameters have to be fixed to the initial values
        if self.config['detector']['fixedzero'] or linearfit :codes[0,PARAMETERS.index('Zero')] = Gefit.CFIXED
        if self.config['detector']['fixedgain'] or linearfit :codes[0,PARAMETERS.index('Gain')] = Gefit.CFIXED
        if self.config['detector']['fixednoise']or linearfit :codes[0,PARAMETERS.index('Noise')]= Gefit.CFIXED
        if self.config['detector']['fixedfano'] or linearfit :codes[0,PARAMETERS.index('Fano')] = Gefit.CFIXED
        if self.config['detector']['fixedsum']  or linearfit :codes[0,PARAMETERS.index('Sum')]  = Gefit.CFIXED
        codes[1,0] = newpar[0] - self.config['detector']['deltazero']
        codes[1,1] = newpar[1] - self.config['detector']['deltagain']
        codes[1,2] = newpar[2] - self.config['detector']['deltanoise']
        codes[1,3] = newpar[3] - self.config['detector']['deltafano']
        codes[1,4] = newpar[4] - self.config['detector']['deltasum']
        codes[2,0] = newpar[0] + self.config['detector']['deltazero']
        codes[2,1] = newpar[1] + self.config['detector']['deltagain']
        codes[2,2] = newpar[2] + self.config['detector']['deltanoise']
        codes[2,3] = newpar[3] + self.config['detector']['deltafano']
        codes[2,4] = newpar[4] + self.config['detector']['deltasum']
        if HYPERMET:
            i = PARAMETERS.index('ST AreaR')
            for j in range(5):
                codes[0,i+j] = Gefit.CFIXED
            if st_term:
                i = PARAMETERS.index('ST AreaR')
                codes[0,i] = Gefit.CQUOTED
                if self.config['peakshape']['fixedst_arearatio'] or linearfit:codes[0,i] = Gefit.CFIXED
                codes[1,i] = newpar[i] + self.config['peakshape']['deltast_arearatio']
                codes[2,i] = newpar[i] - self.config['peakshape']['deltast_arearatio']
                i = PARAMETERS.index('ST SlopeR')
                codes[0,i] = Gefit.CQUOTED
                if self.config['peakshape']['fixedst_sloperatio'] or linearfit:codes[0,i] = Gefit.CFIXED
                codes[1,i] = newpar[i] + self.config['peakshape']['deltast_sloperatio']
                codes[2,i] = newpar[i] - self.config['peakshape']['deltast_sloperatio']
            if lt_term:
                i = PARAMETERS.index('LT AreaR')
                codes[0,i] = Gefit.CQUOTED
                if self.config['peakshape']['fixedlt_arearatio'] or linearfit:codes[0,i] = Gefit.CFIXED
                codes[1,i] = newpar[i] + self.config['peakshape']['deltalt_arearatio']
                codes[2,i] = newpar[i] - self.config['peakshape']['deltalt_arearatio']
                i = PARAMETERS.index('LT SlopeR')
                codes[0,i] = Gefit.CQUOTED
                if self.config['peakshape']['fixedlt_sloperatio'] or linearfit:codes[0,i] = Gefit.CFIXED
                codes[1,i] = newpar[i] + self.config['peakshape']['deltalt_sloperatio']
                codes[2,i] = newpar[i] - self.config['peakshape']['deltalt_sloperatio']
            if step_term:
                i = PARAMETERS.index('STEP HeightR')
                codes[0,i] = Gefit.CQUOTED
                if self.config['peakshape']['fixedstep_heightratio'] or linearfit:codes[0,i] = Gefit.CFIXED
                codes[1,i] = newpar[i] + self.config['peakshape']['deltastep_heightratio']
                codes[2,i] = newpar[i] - self.config['peakshape']['deltastep_heightratio']
        else:
            i = PARAMETERS.index('Eta Factor')
            codes[0, i] = Gefit.CQUOTED
            if self.config['peakshape']['fixedeta_factor'] or linearfit:
                codes[0,i] = Gefit.CFIXED
            codes[1,i] = max(newpar[i] + self.config['peakshape']['deltaeta_factor'], 0.0)
            codes[2,i] = min(newpar[i] - self.config['peakshape']['deltaeta_factor'], 1.0)
        #"""
        #firstshot=mcatheory(newpar,x)
        #a linear fit does not need an initial estimate of the areas
        noise = pow(self.config['detector']['noise'], 2)
        fano = self.config['detector']['fano'] * 2.3548*2.3548*0.00385
        if not linearfit:
         for i in range(len(PARAMETERS)-NGLOBAL):
            rates     =  self.PEAKS0[i][:, 0]
            positions = (self.PEAKS0[i][:, 1] - zero)/gain
            # fwhms   = (self.PEAKS0[i][:, 2])/gain
            i1 = numpy.nonzero((positions >= x[0]) & (positions <= x[-1]))[0]
            # numpy.take uses by default axis=None
            # Numeric.take uses by default axis=0
            inpeaks = numpy.take(self.PEAKS0[i],i1, axis=0)
            if len(inpeaks):
                 fmax = max(inpeaks[:,0])
                 jmax = 0
                 for j in range(len(inpeaks[:,1])):
                     if fmax < inpeaks[j,0]:
                         fmax = inpeaks[j,0]
                         jmax = j
                 j = jmax
                 position  = (inpeaks[j,1] - zero)/gain
                 fwhm      = (inpeaks[j,2])/gain
                 n      = max(numpy.nonzero(numpy.ravel(x)<=position)[0])
                 height = numpy.ravel(y - z)[n]
                 #area = ((height * fwhm/2.3548)*sqrt(2*3.14159))/fmax
                 area = ((height * fwhm/2.3548)*numpy.sqrt(2*3.14159))
                 newpar[i+NGLOBAL] = area
            elif not self.config['fit']['escapeflag']:
                #peaks outside fitting region
                #force zero area
                newpar[i+NGLOBAL] = 0.0
                codes[0,i+NGLOBAL]= Gefit.CFIXED
            else:
                #peaks outside fitting region
                #prior to force them to zero area, let's
                #check if their escape peaks fall into the
                #fitting region
                #print "expected shape = ",self.PEAKSW[i].shape
                #print "n escape lines = ",self.PEAKSW[i].shape[0] - len(rates)
                #get the number of escape lines to get a proper buffer
                n_escape_lines = self.PEAKSW[i].shape[0] - len(rates)
                peak_buffer    = numpy.zeros((n_escape_lines, 3)).astype(numpy.float64)
                ii=0
                jj=0
                for esc_group in self.PEAKS0ESCAPE[i]:
                    for esc_line in esc_group:
                        esc_ene  = esc_line[0] * 1.0
                        esc_rate = esc_line[1]
                        peak_buffer[jj,0] =  self.PEAKS0[i][ii,0] * esc_rate
                        peak_buffer[jj,1] =  esc_ene
                        jj = jj + 1
                    ii = ii + 1
                peak_buffer[:, 2] = numpy.sqrt(noise + \
                                    (peak_buffer[:,1]>0) * peak_buffer[:,1] * \
                                     fano)
                rates     =  peak_buffer[:,0]
                positions = (peak_buffer[:,1] - zero)/gain
                i1 = numpy.nonzero((positions >= x[0]) & (positions <= x[-1]))[0]
                inpeaks = numpy.take(peak_buffer, i1, axis=0)
                if len(inpeaks):
                     fmax = max(inpeaks[:,0])
                     jmax = 0
                     for j in range(len(inpeaks[:,1])):
                         if fmax < inpeaks[j,0]:
                             fmax = inpeaks[j,0]
                             jmax = j
                     if fmax <= 0:
                         newpar[i+NGLOBAL] = 0.0
                         codes[0,i+NGLOBAL]= Gefit.CFIXED
                     else:
                         j = jmax
                         position  = (inpeaks[j,1] - zero)/gain
                         fwhm      = (inpeaks[j,2])/gain
                         n      = max(numpy.nonzero(numpy.ravel(x)<=position)[0])
                         height = numpy.ravel(y - z)[n]
                         #area = ((height * fwhm/2.3548)*sqrt(2*3.14159))/fmax
                         area = ((height * fwhm/2.3548)*numpy.sqrt(2*3.14159))
                         newpar[i+NGLOBAL] = area/fmax
                         #print PARAMETERS[i+NGLOBAL], "index = ", i + NGLOBAL
                         #print "Starting area = ", area/fmax
                         #print "alternative =   ", area
                else:
                    #none of the escape peaks falls into the fitting region
                    newpar[i+NGLOBAL] = 0.0
                    codes[0,i+NGLOBAL]= Gefit.CFIXED
        else:
            #import time
            #e0 = time.time()
            if self.linearMatrix is None:
                self.__oldLinearFixed = []
                for i in range(len(PARAMETERS)-NGLOBAL):
                    positions = (self.PEAKS0[i][:,1] - zero)/gain
                    i1 = numpy.nonzero((positions >= x[0]) & (positions <= x[-1]))[0]
                    inpeaks = numpy.take(self.PEAKS0[i],i1,axis=0)
                    if len(inpeaks):
                        continue
                    elif not self.config['fit']['escapeflag']:
                        #peaks outside fitting region
                        #force zero area
                        newpar[i+NGLOBAL] = 0.0
                        codes[0,i+NGLOBAL]= Gefit.CFIXED
                        self.__oldLinearFixed.append(i)
                        continue
                    #peaks outside fitting region
                    #prior to force them to zero area, let's
                    #check if their escape peaks fall into the
                    #fitting region
                    #get the number of escape lines to get a proper buffer
                    rates     =  self.PEAKS0[i][:,0]
                    n_escape_lines = self.PEAKSW[i].shape[0] - len(rates)
                    peak_buffer    = numpy.zeros((n_escape_lines, 3)).astype(numpy.float64)
                    ii=0
                    jj=0
                    for esc_group in self.PEAKS0ESCAPE[i]:
                        for esc_line in esc_group:
                            esc_ene  = esc_line[0] * 1.0
                            esc_rate = esc_line[1]
                            peak_buffer[jj,0] =  self.PEAKS0[i][ii,0] * esc_rate
                            peak_buffer[jj,1] =  esc_ene
                            jj = jj + 1
                        ii = ii + 1
                    peak_buffer[:, 2] = numpy.sqrt(noise + \
                                        (peak_buffer[:,1]>0) * peak_buffer[:,1] * \
                                         fano)
                    rates     =  peak_buffer[:,0]
                    positions = (peak_buffer[:,1] - zero)/gain
                    i1 = numpy.nonzero((positions >= x[0]) & (positions <= x[-1]))[0]
                    inpeaks = numpy.take(peak_buffer,i1, axis=0)
                    if len(inpeaks):
                        continue
                    else:
                        newpar[i+NGLOBAL] = 0.0
                        codes[0,i+NGLOBAL]= Gefit.CFIXED
                        self.__oldLinearFixed.append(i)
            else:
                for i in self.__oldLinearFixed:
                    newpar[i+NGLOBAL] = 0.0
                    codes[0,i+NGLOBAL]= Gefit.CFIXED
            #print "Elapsed = ",time.time() - e0
            if self._batchFlag and self.linearMatrix is None:
                    self.linearMatrix = self.getPeakMatrixContribution(newpar)
        return newpar, codes

    def startfit(self,digest=0, linear=None, currentIteration=None):
        if self.__toBeConfigured:
            self.estimate()
        if linear is None:
            linear = self.config['fit'].get("linearfitflag", 0)

        if linear and self._batchFlag and (self.linearMatrix is not None):
            fitresult =  Gefit.LeastSquaresFit(self.linearMcaTheory,
                                           self.parameters,
                                           self.datatofit,
                                           constrains=self.codes,
                                           weightflag=self.config['fit']['fitweight'],
                                           maxiter=self.MAXITER,
                                    model_deriv=self.linearMcaTheoryDerivative,
                                           deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1, linear=linear)
            if self.__SUM:
                #This is a patch but the alternative is
                #to forbid linear fits with pile-up.
                self.parameters = fitresult[0]
                zero = self.parameters[0]
                gain = self.parameters[1]
                xw = self.datatofit[:,0]
                yfitw = self.mcatheory(fitresult[0], xw,summing=0)
                pileup= self.parameters[4]*SpecfitFuns.pileup(yfitw,int(xw[0]), zero, gain)
                self.datatofit[:,1] -= pileup
                fitresult =  Gefit.LeastSquaresFit(self.linearMcaTheory,
                                           self.parameters,
                                           self.datatofit,
                                           constrains=self.codes,
                                           weightflag=self.config['fit']['fitweight'],
                                           maxiter=self.MAXITER,
                                    model_deriv=self.linearMcaTheoryDerivative,
                                           deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1, linear=linear)

        else:
            fitresult =  Gefit.LeastSquaresFit(self.mcatheory,
                                           self.parameters,
                                           self.datatofit,
                                           constrains=self.codes,
                                           weightflag=self.config['fit']['fitweight'],
                                           maxiter=self.MAXITER,
                                           model_deriv=self.analyticalDerivative,
                                           deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1, linear=linear)
            if self.__SUM and linear:
                #This is a patch but the alternative is
                #to forbid linear fits with pile-up.
                self.parameters = fitresult[0]
                zero = self.parameters[0]
                gain = self.parameters[1]
                xw = self.datatofit[:,0]
                yfitw = self.mcatheory(fitresult[0], xw,summing=0)
                pileup= self.parameters[4]*SpecfitFuns.pileup(yfitw,int(xw[0]), zero, gain)
                self.datatofit[:,1] -= pileup
                fitresult =  Gefit.LeastSquaresFit(self.mcatheory,
                                           self.parameters,
                                           self.datatofit,
                                           constrains=self.codes,
                                           weightflag=self.config['fit']['fitweight'],
                                           maxiter=self.MAXITER,
                                           model_deriv=self.analyticalDerivative,
                                           deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1, linear=linear)
        self.fittedpar=fitresult[0]
        self.chisq    =fitresult[1]
        self.sigmapar =fitresult[2]
        self.__niter  =fitresult[3]
        self.__lastdeltachi = fitresult[4]
        if self.__niter >= self.MAXITER:
            print("WARNING: Needed %d iterations" % self.__niter) 

        callStrategy = False
        if currentIteration is None:
            if self.config['fit'].get("strategyflag", False):
                callStrategy = True
                self.__originalConfiguration = copy.deepcopy(self.config)
        elif currentIteration > 0:
            callStrategy = True

        self.__toBeConfigured = False
        if callStrategy:
            try:
                # get the strategy to be applied
                strategyKey = self.config['fit']["strategy"]
                if strategyKey not in self.strategyInstances:
                    self.strategyInstances[strategyKey] = STRATEGIES[strategyKey]()
                strategyInstance = self.strategyInstances[strategyKey]
                # digestresult takes about 0.1 seconds per iteration
                import time
                t0 = time.time()
                newConfig, iteration = strategyInstance.applyStrategy( \
                                                self.digestresult(),
                                                self._fluoRates,
                                                currentIteration=currentIteration)
                #print("Strategy elapsed = ", time.time() - t0)
                if (iteration >= 0) and (len(newConfig.keys())):
                    print("RECONFIGURING")
                    t0 = time.time()
                    self.configure(newConfig)
                    print("RECONFIGURING elapsed = ", time.time() - t0)
                    self.estimate()
                    if digest:
                        fitresult = self.startfit(digest=digest,
                                              linear=linear,
                                              currentIteration=iteration)[0]
                    else:
                        fitresult = self.startfit(digest=digest,
                                              linear=linear,
                                              currentIteration=iteration)
                    self.fittedpar=fitresult[0]
                    self.chisq    =fitresult[1]
                    self.sigmapar =fitresult[2]
                    self.__niter  =fitresult[3]
                    self.__lastdeltachi = fitresult[4]
                    if self.__niter >= self.MAXITER:
                        print("WARNING: Needed %d iterations" % self.__niter) 
            except Exception:
                _logger.error( \
                    "Exception during strategy. Restoring configuration")
                self.configure(self.__originalConfiguration)
                raise

        self.digest = digest
        if digest:
            digestedResult = self.digestresult()
            #self.result=self.digestresult()
            if currentIteration is None:
                if callStrategy:
                    # restore old configuration with the new materials
                    self.__originalConfiguration["materials"].update(\
                        self.config["materials"])
                    self.__toBeConfigured = True
            return fitresult, digestedResult
        else:
            if currentIteration is None:
                if callStrategy:
                    # restore old configuration with the new materials
                    self.__originalConfiguration["materials"].update(\
                        self.config["materials"])
                    self.__toBeConfigured = True
            return fitresult

    def imagingDigestResult(self):
        """
        minimalist dictionary for imaging purposes
        """
        i = 0
        result = {}
        result['groups'] = []
        result["chisq"] = self.chisq
        n= self.NGLOBAL
        for group in self.PARAMETERS[n:]:
            # fitatea = self.fittedpar[n + i]
            sigmaarea = self.sigmapar[n + i]
            [ele, group0] = group.split()
            result['groups'].append(group)
            result[group]     = {}
            result[group]['peaks']    = self.PEAKS0NAMES[i]
            if self.__HYPERMET:
                result[group]['fitarea']  = self.fittedpar[n+i] * \
                                    (1.0 + self.fittedpar[self.PARAMETERS.index('ST AreaR')])
            else:
                result[group]['fitarea']  = self.fittedpar[n+i]
            result[group]['sigmaarea'] = sigmaarea
            i += 1
        return result

    def digestresult(self,outfile=None, info=None):
        param = self.fittedpar
        xw    = numpy.ravel(self.xdata)
        if self.STRIP:
            yw    = numpy.ravel(self.ydata-self.zz)
        else:
            yw    = numpy.ravel(self.ydata)
        #print "delta yw actual data = ",numpy.sum(self.datatofit[:,1] - yw)
        sy    = numpy.ravel(self.sigmay)
        zzw   = numpy.ravel(self.zz)
        zero = param[0]
        gain = param[1]
        energyw=zero + gain * xw
        #print energy
        yfitw = self.mcatheory(param,xw,summing=0)
        pileup= param[4]*SpecfitFuns.pileup(yfitw,int(xw[0]), zero, gain)
        yfitw += pileup
        # + numpy.ravel(self.zz)
        #reduced chi square
        weightw =  1.0 / (sy + numpy.equal(sy,0))
        weightw = weightw * weightw
        nfree_par = numpy.sum(self.codes[0,:] < 3)
        prechisq = weightw * (yw - yfitw) *(yw - yfitw)/ (len(yw) - nfree_par)
        #print "CHISQ = ",numpy.sum(prechisq)


        n = self.NGLOBAL
        gain = self.fittedpar[self.PARAMETERS.index('Gain')]
        result={}
        result['xdata']    = xw
        result['energy']   = energyw
        result['ydata']    = numpy.ravel(self.ydata)
        if self.STRIP:
            result['yfit']     = yfitw + zzw
        else:
            result['yfit']     = yfitw
        if self.__CONTINUUM:
            if self.STRIP:
                result['continuum']= self.continuum(param,xw) + zzw
            else:
                result['continuum']= self.continuum(param,xw) * 1.0
        elif self.STRIP:
                result['continuum']= zzw
        else:
                result['continuum']= 0.0 * xw
        result['pileup']       = pileup
        result['parameters']= self.PARAMETERS
        #result['parameters']= self.parameters
        result['fittedpar'] = self.fittedpar
        result['chisq']     = self.chisq
        result['sigmapar']  = self.sigmapar
        result['config']    = {}
        result['config'].update(self.config)
        result['config']['fit']['continuum_name']=CONTINUUM_LIST[self.__CONTINUUM]
        result['groups'] = []

        PEAKSW = copy.deepcopy(self.getpeaksw(self.fittedpar))

        """
        #EVALUATION:
        if FASTER:
            a=numpy.concatenate(PEAKSW[:])
            #t=time.time()
            #result = SpecfitFuns.agauss(a,energy)
            #if HYPERMET:
            if hypermet:
                result = SpecfitFuns.fastahypermet(a,energy,hypermet)
            else:
                result = SpecfitFuns.fastagauss(a,energy)
        """
        i = 0
        for group in self.PARAMETERS[n:]:
            fitarea   = self.fittedpar[n+i]
            sigmaarea = self.sigmapar[n+i]
            [ele, group0] = group.split()
            result['groups'].append(group)
            result[group]     = {}
            result[group]['peaks']    = self.PEAKS0NAMES[i]
            if self.__HYPERMET:
                result[group]['fitarea']  = self.fittedpar[n+i] * \
                                    (1.0 + self.fittedpar[self.PARAMETERS.index('ST AreaR')])
            else:
                result[group]['fitarea']  = self.fittedpar[n+i]
            result[group]['sigmaarea'] = sigmaarea
            result[group]['statistics'] = 0
            j = 0
            p =  PEAKSW[i][:,:]
            if self.__HYPERMET:
                contrib = SpecfitFuns.fastahypermet(p, energyw,self.__HYPERMET)
            else:
                contrib = SpecfitFuns.apvoigt(p, energyw)
            result["y" + group] = contrib
            index = []
            for peak in result[group]['peaks']:
                result[group][peak] = {}
                result[group][peak]['ratio']     = self.PEAKS0[i][j,0]
                result[group][peak]['energy']    = PEAKSW[i][j,1]
                result[group][peak]['fwhm']      = PEAKSW[i][j,2]
                result[group][peak]['statistics']= 0

                #detailed parameters
                peakpos = result[group][peak]['energy']
                sigma   = result[group][peak]['fwhm']/2.3548
                index0   = numpy.nonzero(((peakpos-3*sigma)<energyw) & (energyw<(peakpos+3*sigma)))[0]
                if len(index0):
                    chisq = numpy.sum(numpy.take(prechisq,index0))*len(yw)/len(index0)
                else:
                    chisq = 0.000
                for ind in index0:
                    if ind not in index:
                        index.append(ind)
                result[group][peak]['chisq']     = chisq
                if fitarea == 0:
                    result[group][peak]['fitarea']   = 0.0
                    result[group][peak]['sigmaarea'] = 0.0
                elif self.__HYPERMET:
                    result[group][peak]['fitarea']   = PEAKSW[i][j,0] * (1.0 + PEAKSW[i] [j,3]) / gain
                    result[group][peak]['sigmaarea'] = result[group][peak]['fitarea']* \
                                                        abs(sigmaarea/fitarea)
                else:
                    result[group][peak]['fitarea']   = PEAKSW[i][j,0] / gain
                    result[group][peak]['sigmaarea'] = result[group][peak]['fitarea'] * abs(sigmaarea/fitarea)

                if len(index0):
                    if result[group][peak]['fitarea'] > 0:
                        result[group][peak]['statistics'] = numpy.take(self.ydata, index0).sum()
                        pseudoArea = numpy.take(contrib, index0).sum()
                        result[group]['statistics'] += result[group][peak]['ratio']*\
                                                   abs(result[group][peak]['statistics']-pseudoArea)
                j += 1
            result[group]['escapepeaks'] = []
            if self.ESCAPE:
                if OLDESCAPE:
                    result[group]['escapepeaks'] = self.PEAKS0NAMES[i]
                    j = 0
                    for peak0 in result[group]['peaks']:
                        (r,c) = (self.PEAKS0[i]).shape
                        peak = peak0+"esc"
                        result[group][peak] = {}
                        result[group][peak]['energy']    = PEAKSW[i][j+r,1]
                        result[group][peak]['fwhm']      = PEAKSW[i][j+r,2]
                        result[group][peak]['ratio']     = self.PEAKS0[i][j,3]
                        chisq     = 0.0
                        if result[group][peak]['ratio'] > 0:
                            peakpos = result[group][peak]['energy']
                            sigma   = result[group][peak]['fwhm']/2.3548
                            index0   = numpy.nonzero(((peakpos-4*sigma)<energyw) & (energyw<(peakpos+4*sigma)))[0]
                            if len(index0):
                                chisq = numpy.sum(numpy.take(prechisq,index0))*len(yw)/len(index0)
                            else:
                                #chisq = -1
                                chisq = 0.000
                        result[group][peak]['chisq']     = chisq
                        if 1:
                            """
                            if self.__HYPERMET:
                                result[group][peak]['fitarea']   = PEAKSW[r][j,0] * (1.0 + PEAKSW[r] [j,3])
                                result[group][peak]['sigmaarea'] = PEAKSW[r][j,0] * (1.0 + PEAKSW[r] [j,3]) * \
                                                                    abs(sigmaarea/fitarea)
                            else:
                            """
                            if fitarea != 0.0:
                               result[group][peak]['fitarea']   = PEAKSW[i][j+r,0] /gain
                               result[group][peak]['sigmaarea'] = result[group][peak]['fitarea']  * abs(sigmaarea/fitarea)
                            else:
                               result[group][peak]['fitarea']   = 0.0
                               result[group][peak]['sigmaarea'] = 0.0
                        j += 1
                else:
                    result[group]['escapepeaks'] = []
                    j  = 0
                    ii = 0
                    (r,c) = (self.PEAKS0[i]).shape
                    #result[group]['escapepeaks'] = self.PEAKS0NAMES[i]
                    for _esc_group in self.PEAKS0ESCAPE[i]:
                        peak0 = result[group]['peaks'][ii]
                        #if group == 'Fe K':print "_esc_group = ",_esc_group
                        for esc_line in _esc_group:
                            _name_root_ = peak0+" "+esc_line[2].replace(' ','_')
                            peak = _name_root_+"esc"
                            if _name_root_ not in result[group]['escapepeaks']:
                                result[group]['escapepeaks']+=[peak0+" "+esc_line[2].replace(' ','_')]
                            result[group][peak] = {}
                            (rw,cw) = (PEAKSW[i]).shape
                            result[group][peak]['energy']    = PEAKSW[i][j+r,1]
                            result[group][peak]['fwhm']      = PEAKSW[i][j+r,2]
                            result[group][peak]['ratio']     = esc_line[1]
                            result[group][peak]['statistics']= 0
                            #if group == 'Fe K':print "peak =",peak," energy = ",PEAKSW[i][j+r,1]
                            chisq     = 0.0
                            if result[group][peak]['ratio'] > 0:
                                peakpos = result[group][peak]['energy']
                                sigma   = result[group][peak]['fwhm']/2.3548
                                index0   = numpy.nonzero(((peakpos-3*sigma)<energyw) & (energyw<(peakpos+3*sigma)))[0]
                                if len(index0):
                                    chisq = numpy.sum(numpy.take(prechisq,index0))*len(yw)/len(index0)
                                else:
                                    #chisq = -1
                                    chisq = 0.000
                            result[group][peak]['chisq']     = chisq
                            if 1:
                                """
                                if self.__HYPERMET:
                                    result[group][peak]['fitarea']   = PEAKSW[r][j,0] * (1.0 + PEAKSW[r] [j,3])
                                    result[group][peak]['sigmaarea'] = PEAKSW[r][j,0] * (1.0 + PEAKSW[r] [j,3]) * \
                                                                        abs(sigmaarea/fitarea)
                                else:
                                """
                                if fitarea != 0.0:
                                   result[group][peak]['fitarea']   = PEAKSW[i][j+r,0] /gain
                                   result[group][peak]['sigmaarea'] = result[group][peak]['fitarea']  * abs(sigmaarea/fitarea)
                                else:
                                   result[group][peak]['fitarea']   = 0.0
                                   result[group][peak]['sigmaarea'] = 0.0
                                if len(index0):
                                    if result[group][peak]['fitarea'] > 0:
                                        result[group][peak]['statistics'] = numpy.take(self.ydata, index0).sum()
                                        pseudoArea = numpy.take(contrib, index0).sum()
                                        result[group]['statistics'] += result[group][peak]['ratio']*\
                                                            abs(result[group][peak]['statistics']-pseudoArea)
                            j = j + 1
                        ii=ii+1
            #areaenergies.sort()
            index.sort()
            #print "areaenergies",areaenergies[0],areaenergies[-1]
            #index = numpy.nonzero((energyw>=areaenergies[0]) & (energyw <=areaenergies[-1]))
            energy = numpy.take(energyw     ,index)
            yfit  = numpy.take(yfitw  ,index)
            if 0:
                #this takes into account summing ...
                buff = self.PEAKS0[i][:,0] * 1.0
                self.PEAKS0[i][:,0] = 0.0
                yconw = self.mcatheory(self.fittedpar,xw)
                self.PEAKS0[i][:,0] = buff * 1.0
                ycon   = numpy.take(yconw     ,index)
            else:
                #(r,c) = (self.PEAKS0[i]).shape
                #p =  PEAKSW[i][0:r,:]
                if 0:
                    p =  PEAKSW[i][:,:]
                    if self.__HYPERMET:
                        contrib = SpecfitFuns.fastahypermet(p,energy,self.__HYPERMET)
                    else:
                        contrib = SpecfitFuns.apvoigt(p,energy)
                else:
                    contrib = numpy.take(contrib     ,index)
                ycon = yfit - contrib
            y   = numpy.take(yw     ,index)
            #pmcaarea      = numpy.sum(y-(yfit-contrib))
            pmcaarea      = numpy.sum(y-ycon)
            result[group]['mcaarea']    = pmcaarea
            result[group]['statistics'] = max(pmcaarea, result[group]['fitarea']) +\
                                          result[group]['statistics']
            #pmcasigmaarea = numpy.sqrt(numpy.sum(numpy.where(y<0, -y, y)))
            #result[group]['mcasigmaarea'] = pmcasigmaarea
            i+=1
        result['niter']        = self.__niter * 1
        result['lastdeltachi'] = self.__lastdeltachi * 1.0
        if outfile is not None:
            try:
                os.remove(outfile)
            except Exception:
                pass
            if info is not None:
                d=ConfigDict.ConfigDict({'result':result, 'info':info})
            else:
                d=ConfigDict.ConfigDict({'result':result})
            d.write(outfile)
        return result

    def getpeaksw(self,param,hypermet=None,continuum=None):
        if continuum is None:
            continuum = self.__CONTINUUM
        if hypermet is None:
            hypermet = self.__HYPERMET
        # zero = param[0]
        gain = param[1]
        #energy=zero + gain * x
        #print energy
        noise= param[2] * param[2]
        fano = param[3] * 2.3548*2.3548*0.00385
        #t=time.time()
        PEAKS0 = self.PEAKS0
        PEAKS0ESCAPE = self.PEAKS0ESCAPE
        PEAKSW = self.PEAKSW
        PARAMETERS = self.PARAMETERS
        for i in range(len(param[self.NGLOBAL:])):
            if self.ESCAPE:
                #area = param[NGLOBAL+i]
                (r,c) = (PEAKS0[i]).shape
                PEAKSW[i][0:r,0] = PEAKS0[i][:,0] * param[self.NGLOBAL+i] * gain
                PEAKSW[i][0:r,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][0:r,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                #escape
                if OLDESCAPE:
                    PEAKSW[i][r:,0] = PEAKSW[i][0:r,0] * PEAKS0[i][:,3]
                    PEAKSW[i][r:,1] = PEAKS0[i][:,1] - self.config['detector']['detene']
                    PEAKSW[i][r:,2] = numpy.sqrt(noise + (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                else:
                    ii=0
                    j=0
                    for esc_group in PEAKS0ESCAPE[i]:
                        for esc_line in esc_group:
                            esc_ene  = esc_line[0] * 1.0
                            esc_rate = esc_line[1]
                            PEAKSW[i][j+r,0] =  PEAKSW[i][ii,0] * esc_rate
                            PEAKSW[i][j+r,1] =  esc_ene
                            j = j + 1
                        ii = ii + 1
                    PEAKSW[i][r:, 2] = numpy.sqrt(noise + \
                                    (PEAKSW[i][r:,1]>0) * PEAKSW[i][r:,1] * fano)
                #if HYPERMET:
                if hypermet:
                    PEAKSW[i] [0:r,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [0:r,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [0:r,7] = param[PARAMETERS.index('STEP HeightR')]
                    #neglect tails in escape peaks
                    PEAKSW[i] [r:,3] = 0.0
                    PEAKSW[i] [r:,5] = 0.0
                    PEAKSW[i] [r:,7] = 0.0
            else:
                # area = param[self.NGLOBAL + i]
                PEAKSW[i][:,0] = PEAKS0[i][:,0] * param[self.NGLOBAL+i] * gain
                PEAKSW[i][:,1] = PEAKS0[i][:,1] * 1.0
                PEAKSW[i][:,2] = numpy.sqrt(noise + PEAKS0[i][:,1] * fano)
                if hypermet:
                    PEAKSW[i] [:,3] = param[PARAMETERS.index('ST AreaR')]
                    PEAKSW[i] [:,4] = param[PARAMETERS.index('ST SlopeR')]
                    PEAKSW[i] [:,5] = param[PARAMETERS.index('LT AreaR')]
                    PEAKSW[i] [:,6] = param[PARAMETERS.index('LT SlopeR')]
                    PEAKSW[i] [:,7] = param[PARAMETERS.index('STEP HeightR')]
        return PEAKSW

    # UTILITIES #
    def roifit(self,x, y, background = None, width=None):
        if width is None: width = 200.
        if width > 10 : width = width / 1000.
        xw     = numpy.ravel(numpy.array(x))
        if background is not None:
            yw = numpy.ravel(numpy.array(y) - numpy.array(background))
        else:
            yw = numpy.ravel(y)
        zero   = self.config['detector']['zero']
        gain   = self.config['detector']['gain']
        energy = zero + gain * xw
        ddict={}
        for group in self.PARAMETERS[self.NGLOBAL:]:
            ele,shell = group.split()
            if ele not in Elements.Element.keys(): continue
            lines = self.__getlines(ele,shell,width)
            ddict[group] = {}
            for line in lines:
                emin = Elements.Element[ele][line]['energy'] - 0.5 * width
                emax = Elements.Element[ele][line]['energy'] + 0.5 * width
                i1 = numpy.nonzero((energy >= emin) & (energy <= emax))[0]
                ddict[group][line + " ROI"] = numpy.sum(numpy.take(yw,i1))
        return ddict


    def __getlines(self, ele, shell, width, threshold = 0.010):
        rays = shell + " xrays"
        ratelines    = []
        linestotreat = []
        if rays not in Elements.Element[ele]['rays']:return {}
        for transition in Elements.Element[ele][rays]:
            if Elements.Element[ele][transition]['rate'] > threshold:
                ratelines.append  ([Elements.Element[ele][transition]['rate'],
                          transition])
                linestotreat.append(transition)
        #sort according rate
        ratelines.sort()
        ratelines.reverse()
        lines = []
        for rate,transition in ratelines:
            #print " rate, transition, energy = ",rate, transition, Elements.Element[ele][transition]['energy']
            if not len(linestotreat):break
            if transition in linestotreat:
                linestotreatcopy = linestotreat * 1
                for line in linestotreatcopy:
                    if abs(Elements.Element[ele][line]['energy'] - \
                           Elements.Element[ele][transition]['energy']) < width:
                           del linestotreat[linestotreat.index(line)]
                lines.append(transition)
        return lines

    def smooth(self,ydata,ntimes=1):
            f=[0.25,0.5,0.25]
            result=numpy.array(ydata)
            if len(result > 1):
                for i in range(ntimes):
                    result[1:-1]=numpy.convolve(result,f,mode=0)
                    result[0]=0.5*(result[0]+result[1])
                    result[-1]=0.5*(result[-1]+result[-2])
            return result

    def __getmcaareas(self,param=None):
        #one should calculate Ka and Kb separately to search for errors!!!!
        #one should calculate the reduced chis square in that area!!!
        if param is None:
            param = self.fittedpar
        xw    = numpy.ravel(self.xdata)
        yw    = numpy.ravel(self.ydata)
        sy    = numpy.ravel(self.sigmay)
        zero = param[0]
        gain = param[1]
        energy=zero + gain * xw
        #print energy
        noise= param[2] * param[2]
        fano = param[3] * 2.3548*2.3548*0.00385
        areas=[]
        chisq=[]
        yfitw = self.mcatheory(param,xw) + numpy.ravel(self.zz)
        #reduced chi square
        weightw =  1.0 / (sy + numpy.equal(sy,0))
        weightw = weightw * weightw
        nfree_par = numpy.sum(self.codes[0,:] < 3)
        #chisqtotal = (numpy.sum((yw - yfitted) * (yw - yfitted) * weight))/(len(yw) - nfree_par)
        for i in range(len(self.PARAMETERS[self.NGLOBAL:])):
            j = 0
            for peakpos in self.PEAKS0[i][:,1]:
                sigma = numpy.sqrt(noise + peakpos * fano)/2.3548
                index = numpy.nonzero(((peakpos-3*sigma)<energy) & (energy<(peakpos+3*sigma)))[0]
                x     = numpy.take(xw     ,index)
                y     = numpy.take(yw     ,index)
                yfit  = numpy.take(yfitw  ,index)
                weight= numpy.take(weightw,index)
                #store =param[self.NGLOBAL+i] * 1.0
                store = self.PEAKS0[i][j,0] * 1.0
                self.PEAKS0[i][j,0] = 0.0
                ycalc               = self.mcatheory(param,x)
                self.PEAKS0[i][j,0] = store * 1.0
                areas.append(numpy.sum(y-ycalc))
                chisq.append(numpy.sum((y - yfit) * (y - yfit) * weight/(len(y) - nfree_par)))
                j += 1
        return areas,chisq

    def detectMissingPeaks(self,ordata,fitdata,meanfwhm,separation=0.4):
        orpeaks  = SpecfitFuns.seek(ordata,0,len(ordata), meanfwhm,3)
        fitpeaks = SpecfitFuns.seek(fitdata,0,len(fitdata),meanfwhm,3)
        missingpeaks = []
        for orpeak in orpeaks:
            considered = 0
            for fitpeak in fitpeaks:
                if (abs(fitpeak-orpeak) <= separation * meanfwhm):
                    considered = 1
            if not considered:
                missingpeaks.append(orpeak)
        return missingpeaks

    def exppol(self,p0,x):
        p=numpy.array(p0)
        xw=numpy.array(x)
        y = 0.0 * xw
        for i in range(1,len(p)):
            y+= p[i] * pow(xw,i)
        #return p[0]*self.myexp(y)
        return p[0]*numpy.exp(y)

    def exppol_deriv(self,p0,index,x):
        p=numpy.array(p0)
        xw=numpy.array(x)
        if index == 0:
            p[0]=1.0
            return self.exppol(p,xw)
        else:
            return self.exppol(p,xw)*pow(xw,index)

    def myexp(self,x):
        # put a (bad) filter to avoid over/underflows
        # with no python looping
        return numpy.exp(x*numpy.less(abs(x),250))


    def linpol(self,p0,x):
        p=numpy.array(p0)
        xw=numpy.array(x)
        y = p[0]* numpy.ones(len(x))
        for i in range(1,len(p)):
            y+= p[i] * pow(xw,i)
        return y

    def linpol_deriv(self,p0,index,x):
        xw=numpy.array(x)
        if index==0:
            return numpy.ones(len(x)).astype(numpy.float64)
        else:
            return pow(xw,index)

    def estimatelinpol(self,x,y,z,xscaling=1.0,yscaling=1.0):
        #initial fit on zz
        n=len(z)
        xmean = numpy.sum(x)/len(x)
        xmean = 0
        xw=numpy.resize(x-xmean,(n,1))
        zw=numpy.resize(z,(n,1))
        sw=numpy.ones((n,1))
        datatofit = numpy.concatenate((xw, zw, sw),1)
        p=[]
        for i in range(self.config['fit']['linpolorder']+1):
            p.append(0.0)
        fitresult =  Gefit.LeastSquaresFit(self.linpol,
                                           p,
                                           datatofit,
                                           #constrains=self.codes,
                                           weightflag=self.config['fit']['fitweight'],
                                           maxiter=10,
                                           model_deriv=self.linpol_deriv,
                                           #deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1)
        fittedpar=fitresult[0]
        return fittedpar,numpy.zeros((3,len(fittedpar)),numpy.float64)

    def estimateexppol(self,x,y,z,xscaling=1.0,yscaling=1.0):
        #initial fit on zz
        i1=numpy.nonzero(numpy.ravel(z)>0.0)[0]
        n=len(i1)
        zero      = self.config['detector']['zero']
        gain      = self.config['detector']['gain']
        xmean = numpy.sum(x)/len(x)
        xw=zero+gain*numpy.resize(numpy.take(x,i1)-xmean,(n,1))
        zw=numpy.resize(numpy.log(numpy.take(z,i1)),(n,1))
        sw=numpy.ones((n,1))
        datatofit = numpy.concatenate((xw, zw, sw),1)
        p=[]
        for i in range(self.config['fit']['exppolorder']+1):
            p.append(0.0)
        fitresult =  Gefit.LeastSquaresFit(self.linpol,
                                           p,
                                           datatofit,
                                           #constrains=self.codes,
                                           #weightflag=1,
                                           maxiter=40,
                                           model_deriv=self.linpol_deriv,
                                           #deltachi=self.config['fit']['deltachi'],
                                           fulloutput=1)
        fittedpar=fitresult[0]
        fittedpar[0] = numpy.exp(fittedpar[0])
        return fittedpar,numpy.zeros((3,len(fittedpar)),numpy.float64)


class ClassMcaTheory(McaTheory):
    pass

"""
def agauss(param0,t0):
        param=resize(ravel(array(param0)),(len(param0),3))
        t=array(t0)
        result=t*0.0
        for param in param0:
            sigma=param[2]/2.3548200450309493
            dummy=(t-param[1])/sigma
            result += 0.3989422804014327*(param[0]/sigma) * myexp(-0.5 * dummy * dummy)
        return result

def myexp(x):
        # put a (bad) filter to avoid over/underflows
        # with no python looping
        return exp(x*less(abs(x),250))-1.0*greater_equal(abs(x),250)


def expini(nmax):
    global EXP
    EXP = exp(-arange(0,nmax,0.01))

def myexp2(x):
    i = array(map(int,x * 100))
    return take(EXP,i) * (1.0 - (x - 0.01 * i))
"""


def test(inputfile=None,scankey=None,pkm=None,
                continuum=0,stripflag=1,maxiter=10,sumflag=1,
                hypermetflag=1,plotflag=0,escapeflag=1,attenuatorsflag=1,outfile=None):
    import sys
    from PyMca5.PyMca import specfilewrapper as specfile
    mcafit = McaTheory(initdict=None,maxiter=maxiter,sumflag=sumflag,
                    continuum=continuum,escapeflag=escapeflag,stripflag=stripflag,hypermetflag=hypermetflag,
                    attenuatorsflag=attenuatorsflag)
    initdict=ConfigDict.ConfigDict()
    initdict.read(pkm)
    t0=time.time()
    config = mcafit.configure(initdict)
    print("configuration time ",time.time()-t0)
    xmin = config['fit']['xmin']
    xmax = config['fit']['xmax']

    if inputfile is None:
        print("USAGE")
        print("python -m PyMca5.PyMcaPhysics.xrf.ClassMcaTheory.py -s1.1 --file=filename --cfg=cfgfile [--plotflag=1]")
        #python ClassMcaTheory.py -s2.1 --file=ch09__mca_0005.mca --pkm=TEST.cfg --continuum=0 --stripflag=1 --sumflag=1 --maxiter=4
        sys.exit(0)
    print("assuming is a specfile ...")
    sf=specfile.Specfile(inputfile)
    if scankey is None:
        scan=sf[0]
    else:
        scan=sf.select(scankey)
    mcadata=scan.mca(1)
    y0= numpy.array(mcadata)
    x = numpy.arange(len(y0))*1.0
    t0=time.time()
    mcafit.setData(x,y0,xmin=xmin,xmax=xmax)
    print("set data time",time.time()-t0)
    mcafit.estimate()
    print("estimation time ",time.time()-t0)
    #fitresult, mcafitresult=mcafit.startfit(digest=1)
    fitresult    = mcafit.startfit(digest=0)
    mcafitresult = mcafit.digestresult(outfile)
    print("fit took ",time.time()-t0)
    fittedpar=fitresult[0]
    chisq    =fitresult[1]
    sigmapar =fitresult[2]
    i = 0
    print("chisq = ",chisq)

    for param in mcafit.PARAMETERS:
        if i < mcafit.NGLOBAL:
            print(param, ' = ',fittedpar[i],' +/- ',sigmapar[i])
        else:
            print(param, ' = ',fittedpar[i],' +/- ',sigmapar[i])
        #,'mcaarea = ',areas[i-mcafit.NGLOBAL]
        i += 1
    i = 0
    #mcafit.digestresult()
    for group in mcafitresult['groups']:
        print(group,mcafitresult[group]['fitarea'],' +/- ', \
            mcafitresult[group]['sigmaarea'],mcafitresult[group]['mcaarea'])

    #print("##################### ROI fitting ######################")
    #print(mcafit.roifit(mcafit.xdata,mcafit.ydata))

    if plotflag:
        from PyMca5.PyMcaGui import PyMcaQt as qt
        from PyMca5.PyMcaGui.pymca import ScanWindow
        app = qt.QApplication(sys.argv)
        graph = ScanWindow.ScanWindow()
        xw = numpy.ravel(mcafit.xdata)
        yfit0 = mcafit.mcatheory(fittedpar,xw)+numpy.ravel(mcafit.zz)
        xw = xw*fittedpar[1]+fittedpar[0]
        graph.addCurve(mcafitresult['energy'],mcafitresult['ydata'], "Input  Data")
        graph.addCurve(mcafitresult['energy'],mcafitresult['yfit'],"Fitted Data")
        graph.addCurve(mcafitresult['energy'],
                                    mcafitresult['continuum']+mcafitresult['pileup'],
                                    "Summing")
        graph.addCurve(mcafitresult['energy'],mcafitresult['continuum'],"Continuum")
        graph.show()
        app.exec()

PROFILING = 0
if __name__ == "__main__":
    import time
    t0=time.time()
    if PROFILING:
        import profile
        import pstats
        profile.run('test()',"test")
        p=pstats.Stats("test")
        p.strip_dirs().sort_stats(-1).print_stats()
    else:
        import getopt
        if 1:
        #try:
            options     = 'f:s:o'
            longoptions = ['file=','scan=','pkm=','cfg=',
                            'output=','continuum=','stripflag=',
                            'maxiter=','sumflag=','escapeflag=','hypermetflag=','plotflag=',
                            'attenuatorsflag=','outfile=']
            opts, args = getopt.getopt(
                sys.argv[1:],
                options,
                longoptions)
            inputfile = None
            outfile   = None
            scan      = None
            pkm       = None
            maxiter   = 100
            sumflag   = 0
            hypermetflag   = 1
            plotflag  = 0
            stripflag = 1
            escapeflag= 1
            continuum = 0
            attenuatorsflag    = 1
            for opt,arg in opts:
                if opt in ('-f','--file'):
                    inputfile = arg
                if opt in ('-s','--scan'):
                    scan = arg
                if opt in ('--pkm','--cfg'):
                    pkm = arg
                if opt in ('--continuum'):
                    continuum = int(float(arg))
                if opt in ('--strip'):
                    strip = int(float(arg))
                if opt in ('--maxiter'):
                    maxiter = int(float(arg))
                if opt in ('--sumflag'):
                    sumflag = int(float(arg))
                if opt in ('--escapeflag'):
                    escapeflag = int(float(arg))
                if opt in ('--stripflag'):
                    stripflag = int(float(arg))
                if opt in ('--plotflag'):
                    plotflag = int(float(arg))
                if opt in ('--hypermetflag'):
                    hypermetflag = int(float(arg))
                if opt in ('--attenuatorsflag'):
                    attenuatorsflag = int(float(arg))
                if opt in ('--outfile'):
                    outfile = arg
            test(inputfile=inputfile,scankey=scan,pkm=pkm,
                maxiter=maxiter,continuum=continuum,stripflag=stripflag,sumflag=sumflag,
                hypermetflag=hypermetflag,escapeflag=escapeflag,plotflag=plotflag,
                attenuatorsflag=attenuatorsflag,outfile=outfile)
            print("TIME = ",time.time()-t0)
