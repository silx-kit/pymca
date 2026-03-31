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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import numpy
import logging
arctan = numpy.arctan
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaMath.fitting.Gefit import LeastSquaresFit

_logger = logging.getLogger(__name__)


try:
    HOME=os.getenv('HOME')
except Exception:
    HOME=None
if HOME is not None:
    os.environ['HOME'] = HOME
else:
    os.environ['HOME'] = "."
SPECFITFUNCTIONS_DEFAULTS={'FileAction':0,
                 'infile':os.environ['HOME']+'/.specfitdefaults.py',
                 'outfile':os.environ['HOME']+'/.specfitdefaults.py',
                 'Geometry':"600x400+50+50",
                 'NoConstrainsFlag':0,
                 'BackgroundIndex':1,
                 #'TheoryIndex':0,
                 'PosFwhmFlag':1,
                 'HeightAreaFlag':1,
                 'SameFwhmFlag':1,
                 'PositionFlag':0,
                 'EtaFlag':0,
                 'WeightFlag':0,
                 'Yscaling':1.0,
                 'Xscaling':1.0,
                 'FwhmPoints':8,
                 'AutoFwhm':0,
                 'Sensitivity':2.5,
                 'ForcePeakPresence':0,
                 'McaMode':0,
                 #Hypermet
                 'HypermetTails':15,
                 'QuotedFwhmFlag':0,
                 'MaxFwhm2InputRatio':1.5,
                 'MinFwhm2InputRatio':0.4,
                 #short tail parameters
                 'MinGaussArea4ShortTail':50000.,
                 'InitialShortTailAreaRatio':0.050,
                 'MaxShortTailAreaRatio':0.100,
                 'MinShortTailAreaRatio':0.0010,
                 'InitialShortTailSlopeRatio':0.70,
                 'MaxShortTailSlopeRatio':2.00,
                 'MinShortTailSlopeRatio':0.50,
                 #long tail parameters
                 'MinGaussArea4LongTail':1000.0,
                 'InitialLongTailAreaRatio':0.050,
                 'MaxLongTailAreaRatio':0.300,
                 'MinLongTailAreaRatio':0.010,
                 'InitialLongTailSlopeRatio':20.0,
                 'MaxLongTailSlopeRatio':50.0,
                 'MinLongTailSlopeRatio':5.0,
                 #step tail
                 'MinGaussHeight4StepTail':5000.,
                 'InitialStepTailHeightRatio':0.002,
                 'MaxStepTailHeightRatio':0.0100,
                 'MinStepTailHeightRatio':0.0001,
                 #Hypermet constraints
                 'QuotedPositionFlag':1,
                 'DeltaPositionFwhmUnits':0.5,
                 'SameSlopeRatioFlag':1,
                 'SameAreaRatioFlag':1}
CFREE       = 0
CPOSITIVE   = 1
CQUOTED     = 2
CFIXED      = 3
CFACTOR     = 4
CDELTA      = 5
CSUM        = 6
CIGNORED    = 7


class SpecfitFunctions(object):
    def __init__(self,config=None):
        if config is None:
            self.config=SPECFITFUNCTIONS_DEFAULTS
        else:
            self.config=config

    def gauss(self,pars,x):
       """
       A fit function.
       """
       return SpecfitFuns.gauss(pars,x)

    def agauss(self,pars,x):
       """
       A fit function.
       """
       return SpecfitFuns.agauss(pars,x)

    def hypermet(self,pars,x):
       """
       A fit function.
       """
       return SpecfitFuns.ahypermet(pars,x,self.config['HypermetTails'],0)

    def lorentz(self,pars,x):
       """
       Fit function.
       """
       #return pars[0] + pars [1] * x + SpecfitFuns.lorentz(pars[2:len(pars)],x)
       return SpecfitFuns.lorentz(pars,x)

    def alorentz(self,pars,x):
       """
       Fit function.
       """
       return SpecfitFuns.alorentz(pars,x)

    def pvoigt(self,pars,x):
       """
       Fit function.
       """
       return SpecfitFuns.pvoigt(pars,x)
       #return pars[0] + pars [1] * x + SpecfitFuns.pvoigt(pars[2:len(pars)],x)

    def apvoigt(self,pars,x):
       """
       Fit function.
       """
       return SpecfitFuns.apvoigt(pars,x)
       #return pars[0] + pars [1] * x + SpecfitFuns.apvoigt(pars[2:len(pars)],x)

    def splitgauss(self,pars,x):
       """
       Asymmetric gaussian.
       """
       return SpecfitFuns.splitgauss(pars,x)

    def splitlorentz(self,pars,x):
       """
       Asymmetric lorentz.
       """
       return SpecfitFuns.splitlorentz(pars,x)

    def splitpvoigt(self,pars,x):
       """
       Asymmetric pseudovoigt.
       """
       return SpecfitFuns.splitpvoigt(pars,x)

    def stepdown(self,pars,x):
        """
        A fit function.
        """
        return SpecfitFuns.downstep(pars,x)

    def stepup(self,pars,x):
        """
        A fit function.
        """
        return SpecfitFuns.upstep(pars,x)

    def slit(self,pars,x):
        """
        A fit function.
        """
        return 0.5*SpecfitFuns.slit(pars,x)

    def atan(self, pars, x):
        return pars[0] * (0.5 + (arctan((1.0*x-pars[1])/pars[2]) / numpy.pi))

    def periodic_gauss(self, pars, x):
        """
        Fit function periodic_gauss(pars, x)
        pars = [npeaks, delta, height, position, fwhm]
        """
        newpars = numpy.zeros((int(pars[0]), 3), numpy.float64)
        for i in range(int(pars[0])):
            newpars[i, 0] = pars[2]
            newpars[i, 1] = pars[3] + i * pars[1]
            newpars[:, 2] = pars[4]
        return SpecfitFuns.gauss(newpars,x)

    def gauss2(self,param0,t0):
        param=numpy.array(param0)
        t=numpy.array(t0)
        dummy=2.3548200450309493*(t-param[1])/param[2]
        return param[0] * self.myexp(-0.5 * dummy * dummy)

    def myexp(self,x):
        # put a (bad) filter to avoid over/underflows
        # with no python looping
        return numpy.exp(x * numpy.less(abs(x),250))-1.0*numpy.greater_equal(abs(x),250)

    def indexx(x):
        #adapted from runningReport (Mike Fletcher, Python newsgroup)
        set = map(None,x,range(len(x)))
        set.sort() #sorts by values and then by index
        return map(lambda x:x[1],set)

    def bkg_constant(self, pars, x):
        """
        Constant background
        """
        return pars[0] * numpy.ones_like(x)

    def bkg_linear(self, pars, x):
        """
        Linear background
        """
        return pars[0] + pars[1] * x

    def bkg_internal(self,pars,x):
        """
        Internal Background
        """
        #fast
        #return self.zz
        #slow: recalculate the background as function of the parameters
        #yy=SpecfitFuns.subac(self.ydata*self.fitconfig['Yscaling'],
        #                     pars[0],pars[1])
        yy=SpecfitFuns.subac(self.ydata*1.0,
                             pars[0],pars[1])
        nrx=numpy.shape(x)[0]
        nry=numpy.shape(yy)[0]
        if nrx == nry:
            return SpecfitFuns.subac(yy,pars[0],pars[1])
        else:
            return SpecfitFuns.subac(numpy.take(yy,numpy.arange(0,nry,2)),pars[0],pars[1])

    def bkg_none(self,pars,x):
        """
        Internal Background
        """
        return numpy.zeros(x.shape,numpy.float64)

    def fun(self,param, t):
        gterm = param[2] * numpy.exp(-0.5 * ((t - param[3]) * (t - param[3]))/param[4])
        #gterm = gterm + param[3] * numpy.exp(-0.5 * ((t - param[4]) * (t - param[4]))/param[5])
        bterm = param[1] * t + param[0]
        return gterm + bterm

    def estimate(self,x,y,z,xscaling=1.0,yscaling=1.0):
        ngauss = input(' Number of Gaussians : ')
        ngauss=int(ngauss)
        if ngauss < 1:
            ngauss=1
        newpar=[]
        for i in range(ngauss):
            _logger.info("Defining Gaussian numer %d ", i+1)
            newpar.append(input('Height   = '))
            newpar.append(input('Position = '))
            newpar.append(input('FWHM     = '))
            #newpar.append(in)
        return newpar,numpy.zeros((3,len(newpar)),numpy.float64)

    def seek(self,y,x=None,yscaling=None,
                           fwhm=None,
                           sensitivity=None,
                           mca=None):
        """
        SpecfitFunctions.seek(self,y,
                                x=None,
                                yscaling=None,fwhm=None,sensitivity=None,
                                mca=None)
        It searches for peaks in the y array. If x it is given, it gives back
        the closest x(s) to the position of the peak(s). Otherways it gives back
        the index of the closest point to the peak.
        """
        if yscaling is None:
            yscaling=self.config['Yscaling']

        if fwhm is None:
            if self.config['AutoFwhm']:
                fwhm=self.guess_fwhm(x=x,y=y)
            else:
                fwhm=self.config['FwhmPoints']
        if sensitivity is None:
            sensitivity=self.config['Sensitivity']
        if mca is None:
            mca=self.config['McaMode']

        search_fwhm=int(max(fwhm,3))
        search_sensitivity=max(1.0,sensitivity)
        mca=1.0
        if mca:
            ysearch = numpy.array(y) * yscaling
        else:
            ysearch = numpy.ones([len(y) + 2 * search_fwhm,], numpy.float64)
            if y[0]:
                ysearch[0:(search_fwhm+1)]=ysearch[0:(search_fwhm+1)]*y[0]*yscaling
            else:
                ysearch[0:(search_fwhm+1)]=ysearch[0:(search_fwhm+1)]*yscaling*sum(y[0:3])/3.0
            ysearch[-1:-(search_fwhm+1):-1]=ysearch[-1:-(search_fwhm+1):-1]*y[len(y)-1]*yscaling
            ysearch[search_fwhm:(search_fwhm+len(y))]=y*yscaling
        npoints=len(ysearch)
        if npoints > (1.5)*search_fwhm:
            peaks=SpecfitFuns.seek(ysearch,0,npoints,
                                    search_fwhm,
                                    search_sensitivity)
        else:
            peaks=[]

        if len(peaks) > 0:
            if mca == 0:
                for i in range(len(peaks)):
                    peaks[i]=int(peaks[i]-search_fwhm)
            for i in peaks:
                if (i < 1) | (i > (npoints-1)):
                    peaks.remove(i)
            if x is not None:
                if len(x) == len(y):
                    for i in range(len(peaks)):
                        peaks[i]=x[int(max(peaks[i],0))]
        #print "peaks found = ",peaks,"mca =",mca,"fwhm=",search_fwhm,\
        #        "sensi=",search_sensitivity,"scaling=",yscaling
        return peaks


    def guess_fwhm(self, **kw):
        if 'y' in kw:
            y=kw['y']
        else:
            return self.config['FwhmPoints']
        if 'x' in kw:
            x=kw['x']
        else:
            x=numpy.arange(len(y))*1.0

        #set at least a default value for the fwhm
        fwhm=4

        zz=SpecfitFuns.subac(y,1.000,1000)
        yfit=y-zz

        #now I should do some sort of peak search ...
        maximum = max(yfit)
        idx = numpy.nonzero(yfit == maximum)[0]
        pos = numpy.take(x,idx)[-1]
        posindex = idx[-1]
        height = yfit[posindex]
        imin = posindex
        while ((yfit[imin] > 0.5*height) & (imin >0)):
            imin=imin - 1
        imax=posindex
        while ((yfit[imax] > 0.5*height) & (imax <(len(yfit)-1))):
            imax=imax + 1
        fwhm=max(imax-imin-1,fwhm)

        return fwhm

    def estimate_constant(self, xx, yy, zzz, xscaling=1.0, yscaling=None):
        estimated_par = [min(yy)]
        constraints = [[0], [0], [0]]
        return estimated_par, constraints

    def estimate_linear(self, xx, yy, zzz, xscaling=1.0, yscaling=None):
        # compute strip bg and use it to estimate the linear bg parameters
        zz = SpecfitFuns.subac(yy, 1.000, 10000)
        n = float(len(zz))
        Sy = numpy.sum(zz)
        Sx = float(numpy.sum(xx))
        Sxx = float(numpy.sum(xx * xx))
        Sxy = float(numpy.sum(xx * zz))

        deno = n * Sxx - (Sx * Sx)
        if deno != 0:
            bg = (Sxx * Sy - Sx * Sxy) / deno
            slope = (n * Sxy - Sx * Sy) / deno
        else:
            bg = 0.0
            slope = 0.0
        estimated_par = [bg, slope]
        # code = 0: FREE
        constraints = [[0, 0], [0, 0], [0, 0]]
        return estimated_par, constraints

    def estimate_gauss(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       if yscaling == None:
            try:
                yscaling=self.config['Yscaling']
            except KeyError:
                yscaling=1.0
       if yscaling == 0:
            yscaling=1.0
       fittedpar=[]
       zz=SpecfitFuns.subac(yy,1.000,10000)

       npoints = len(zz)
       if self.config['AutoFwhm']:
            search_fwhm=self.guess_fwhm(x=xx,y=yy)
       else:
            search_fwhm=int(float(self.config['FwhmPoints']))
       search_sens=float(self.config['Sensitivity'])
       search_mca=int(float(self.config['McaMode']))

       if search_fwhm < 3:
            search_fwhm = 3
            self.config['FwhmPoints']=3

       if search_sens < 1:
            search_sens = 1
            self.config['Sensitivity']=1

       if npoints > 1.5*search_fwhm:
            peaks=self.seek(yy,fwhm=search_fwhm,
                               sensitivity=search_sens,
                               yscaling=yscaling,
                               mca=search_mca)
            #print "estimate peaks = ",peaks
            #peaks=self.seek(yy-zz,fwhm=search_fwhm,
            #                   sensitivity=search_sens,
            #                   yscaling=yscaling,
            #                   mca=search_mca)
       else:
            peaks = []
       if not len(peaks):
            mca = int(float(self.config.get('McaMode', 0)))
            forcePeak =  int(float(self.config.get('ForcePeakPresence', 0)))
            if (not mca) and forcePeak:
                delta = yy - zz
                peaks  = [int(numpy.nonzero(delta == delta.max())[0])]

       #print "peaks = ",peaks
       #print "peaks subac = ",self.seek(yy-zz,fwhm=search_fwhm,
       #                        sensitivity=search_sens,
       #                        yscaling=yscaling,
       #                        mca=search_mca)
       largest_index = 0
       if len(peaks) > 0:
            j = 0
            for i in peaks:
                if j == 0:
                    sig=5*abs(xx[npoints-1]-xx[0])/npoints
                    peakpos = xx[int(i)]
                    if abs(peakpos) < 1.0e-16:
                        peakpos = 0.0
                    param = numpy.array([yy[int(i)] - zz[int(i)], peakpos ,sig])
                    largest = param
                else:
                    param2 = numpy.array([yy[int(i)] - zz [int(i)], xx[int(i)] ,sig])
                    param = numpy.concatenate((param,param2))
                    if (param2[0] > largest[0]):
                        largest = param2
                        largest_index = j
                j = j + 1
            xw = numpy.resize(xx,(npoints,1))
            if (0):
                sy = numpy.sqrt(abs(yy))
                yw = numpy.resize(yy-zz,(npoints,1))
                sy = numpy.resize(sy,(npoints,1))
                datawork = numpy.concatenate((xw,yw,sy),1)
            else:
                yw = numpy.resize(yy-zz,(npoints,1))
                datawork = numpy.concatenate((xw,yw),1)
            cons = numpy.zeros((3,len(param)),numpy.float64)
            cons [0] [0:len(param):3] = CPOSITIVE
            #force peaks to stay around their position
            if (1):
                cons [0] [1:len(param):3] = CQUOTED
                #This does not work!!!!
                #FWHM should be given in terms of X not of points!
                #cons [1] [1:len(param):3] = param[1:len(param):3]-0.5*search_fwhm
                #cons [2] [1:len(param):3] = param[1:len(param):3]+0.5*search_fwhm
                if len(xw) > search_fwhm:
                    fwhmx = numpy.fabs(xw[int(search_fwhm)]-xw[0])
                    cons [1] [1:len(param):3] = param[1:len(param):3]-0.5*fwhmx
                    cons [2] [1:len(param):3] = param[1:len(param):3]+0.5*fwhmx
                else:
                    cons [1] [1:len(param):3] = numpy.ones(numpy.shape(param[1:len(param):3]),numpy.float64)*min(xw)
                    cons [2] [1:len(param):3] = numpy.ones(numpy.shape(param[1:len(param):3]),numpy.float64)*max(xw)

            if 0:
                cons [0] [2:len(param):3] = CFACTOR
                cons [1] [2:len(param):3] = 2
                cons [2] [2:len(param):3] = 1.0
                cons [0] [2] = CPOSITIVE
                cons [1] [2] = 0
                cons [2] [2] = 0
            else:
                cons [0] [2:len(param):3] = CPOSITIVE
            fittedpar, chisq, sigmapar = LeastSquaresFit(SpecfitFuns.gauss,param,
                                            datawork,
                                            weightflag=self.config['WeightFlag'],
                                            maxiter=4,constrains=cons.tolist())
            #I already have the estimation
            #yw=yy-zz-SpecfitFuns.gauss(fittedpar,xx)
            #if DEBUG:
            #    SimplePlot.plot([xx,yw])
            #print self.seek(yw,\
            #                   fwhm=search_fwhm,\
            #                   sensitivity=search_sens,\
            #                   yscaling=yscaling)
       #else:
       #     #Use SPEC estimate ...
       #     peakpos,height,myidx = SpecArithmetic.search_peak(xx,yy-zz)
       #     fwhm,cfwhm         = SpecArithmetic.search_fwhm(xx,yy-zz,
       #                                    peak=peakpos,index=myidx)
       #     xx = numpy.array(xx)
       #     if npoints > 2:
       #         #forget SPEC estimation of fwhm
       #         fwhm=5*abs(xx[npoints-1]-xx[0])/npoints
       #     fittedpar=[height,peakpos,fwhm]
       #     largest=numpy.array([height,peakpos,fwhm])
       #     peaks=[peakpos]
       cons = numpy.zeros((3,len(fittedpar)),numpy.float64)
       j=0
       for i in range(len(peaks)):
                #Setup height area constrains
                if self.config['NoConstrainsFlag'] == 0:
                    if self.config['HeightAreaFlag']:
                        #POSITIVE = 1
                        cons[0] [j] = 1
                        cons[1] [j] = 0
                        cons[2] [j] = 0
                j=j+1


                #Setup position constrains
                if self.config['NoConstrainsFlag'] == 0:
                    if self.config['PositionFlag']:
                                #QUOTED = 2
                                cons[0][j]=2
                                cons[1][j]=min(xx)
                                cons[2][j]=max(xx)
                j=j+1

                #Setup positive FWHM constrains
                if self.config['NoConstrainsFlag'] == 0:
                    if self.config['PosFwhmFlag']:
                                #POSITIVE=1
                                cons[0][j]=1
                                cons[1][j]=0
                                cons[2][j]=0
                    if self.config['SameFwhmFlag']:
                        if (i != largest_index):
                                #FACTOR=4
                                cons[0][j]=4
                                cons[1][j]=3*largest_index+2
                                cons[2][j]=1.0
                j=j+1
       return fittedpar,cons

    def estimate_lorentz(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
       return  fittedpar,cons

    def estimate_agauss(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
        fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
        #get the number of found peaks
        npeaks=int(len(cons[0])/3)
        for i in range(npeaks):
            height = fittedpar[3*i]
            fwhm = fittedpar[3*i+2]
            fittedpar[3*i] = (height * fwhm / (2.0*numpy.sqrt(2*numpy.log(2))))*numpy.sqrt(2 * numpy.pi)
        return fittedpar,cons

    def estimate_alorentz(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
        fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
        #get the number of found peaks
        npeaks=int(len(cons[0])/3)
        for i in range(npeaks):
            height = fittedpar[3*i]
            fwhm = fittedpar[3*i+2]
            fittedpar[3*i] = (height * fwhm * 0.5 * numpy.pi)
        return fittedpar,cons

    def estimate_splitgauss(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
        fittedpar, cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
        #get the number of found peaks
        npeaks=int(len(cons[0])/3)
        estimated_parameters = []
        estimated_constraints = numpy.zeros((3, 4*npeaks),numpy.float64)
        for i in range(npeaks):
            for j in range(3):
                estimated_parameters.append(fittedpar[3*i+j])
            estimated_parameters.append(fittedpar[3*i+2])
            estimated_constraints[0][4*i]   = cons [0][3*i]
            estimated_constraints[0][4*i+1] = cons [0][3*i+1]
            estimated_constraints[0][4*i+2] = cons [0][3*i+2]
            estimated_constraints[0][4*i+3] = cons [0][3*i+2]
            estimated_constraints[1][4*i]   = cons [1][3*i]
            estimated_constraints[1][4*i+1] = cons [1][3*i+1]
            estimated_constraints[1][4*i+2] = cons [1][3*i+2]
            estimated_constraints[1][4*i+3] = cons [1][3*i+2]
            estimated_constraints[2][4*i]   = cons [2][3*i]
            estimated_constraints[2][4*i+1] = cons [2][3*i+1]
            estimated_constraints[2][4*i+2] = cons [2][3*i+2]
            estimated_constraints[2][4*i+3] = cons [2][3*i+2]
            if cons[0][3*i+2] == 4:
                #same FWHM case
                estimated_constraints[1][4*i+2] = int(cons[1][3*i+2]/3) * 4 + 2
                estimated_constraints[1][4*i+3] = int(cons[1][3*i+2]/3) * 4 + 3
        return estimated_parameters, estimated_constraints

    def estimate_splitlorentz(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
        fittedpar, cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
        #get the number of found peaks
        npeaks=int(len(cons[0])/3)
        estimated_parameters = []
        estimated_constraints = numpy.zeros((3, 4*npeaks),numpy.float64)
        for i in range(npeaks):
            for j in range(3):
                estimated_parameters.append(fittedpar[3*i+j])
            estimated_parameters.append(fittedpar[3*i+2])
            estimated_constraints[0][4*i]   = cons [0][3*i]
            estimated_constraints[0][4*i+1] = cons [0][3*i+1]
            estimated_constraints[0][4*i+2] = cons [0][3*i+2]
            estimated_constraints[0][4*i+3] = cons [0][3*i+2]
            estimated_constraints[1][4*i]   = cons [1][3*i]
            estimated_constraints[1][4*i+1] = cons [1][3*i+1]
            estimated_constraints[1][4*i+2] = cons [1][3*i+2]
            estimated_constraints[1][4*i+3] = cons [1][3*i+2]
            estimated_constraints[2][4*i]   = cons [2][3*i]
            estimated_constraints[2][4*i+1] = cons [2][3*i+1]
            estimated_constraints[2][4*i+2] = cons [2][3*i+2]
            estimated_constraints[2][4*i+3] = cons [2][3*i+2]
            if cons[0][3*i+2] == 4:
                #same FWHM case
                estimated_constraints[1][4*i+2] = int(cons[1][3*i+2]/3) * 4 + 2
                estimated_constraints[1][4*i+3] = int(cons[1][3*i+2]/3) * 4 + 3
        return estimated_parameters, estimated_constraints

    def estimate_pvoigt(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
       npeaks=int(len(cons[0])/3)
       newpar=[]
       newcons=numpy.zeros((3,4*npeaks),numpy.float64)
       #find out related parameters proper index
       if self.config['NoConstrainsFlag'] == 0:
            if self.config['SameFwhmFlag']:
                j=0
                #get the index of the free FWHM
                for i in range(npeaks):
                    if cons[0][3*i+2] != 4:
                        j=i
                for i in range(npeaks):
                    if i != j:
                       cons[1][3*i+2] = 4*j+2
       for i in range(npeaks):
            newpar.append(fittedpar[3*i])
            newpar.append(fittedpar[3*i+1])
            newpar.append(fittedpar[3*i+2])
            newpar.append(0.5)
            newcons[0][4*i]=cons[0][3*i]
            newcons[0][4*i+1]=cons[0][3*i+1]
            newcons[0][4*i+2]=cons[0][3*i+2]
            newcons[1][4*i]=cons[1][3*i]
            newcons[1][4*i+1]=cons[1][3*i+1]
            newcons[1][4*i+2]=cons[1][3*i+2]
            newcons[2][4*i]=cons[2][3*i]
            newcons[2][4*i+1]=cons[2][3*i+1]
            newcons[2][4*i+2]=cons[2][3*i+2]
            #Eta constrains
            newcons[0][4*i+3]=0
            newcons[1][4*i+3]=0
            newcons[2][4*i+3]=0
            if self.config['NoConstrainsFlag'] == 0:
                if self.config['EtaFlag']:
                      #QUOTED=2
                      newcons[0][4*i+3]=2
                      newcons[1][4*i+3]=0.0
                      newcons[2][4*i+3]=1.0
       return  newpar,newcons

    def estimate_splitpvoigt(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
       npeaks=int(len(cons[0])/3)
       newpar=[]
       newcons=numpy.zeros((3,5*npeaks),numpy.float64)
       #find out related parameters proper index
       if self.config['NoConstrainsFlag'] == 0:
            if self.config['SameFwhmFlag']:
                j=0
                #get the index of the free FWHM
                for i in range(npeaks):
                    if cons[0][3*i+2] != 4:
                        j=i
                for i in range(npeaks):
                    if i != j:
                       cons[1][3*i+2] = 4*j+2
       for i in range(npeaks):
            #height
            newpar.append(fittedpar[3*i])
            #position
            newpar.append(fittedpar[3*i+1])
            #fwhm1
            newpar.append(fittedpar[3*i+2])
            #fwhm2 equal to the first
            newpar.append(fittedpar[3*i+2])
            #eta
            newpar.append(0.5)
            newcons[0][5*i]=cons[0][3*i]
            newcons[0][5*i+1]=cons[0][3*i+1]
            newcons[0][5*i+2]=cons[0][3*i+2]
            newcons[0][5*i+3]=cons[0][3*i+2]
            newcons[1][5*i]=cons[1][3*i]
            newcons[1][5*i+1]=cons[1][3*i+1]
            newcons[1][5*i+2]=cons[1][3*i+2]
            newcons[1][5*i+3]=cons[1][3*i+2]
            newcons[2][5*i]=cons[2][3*i]
            newcons[2][5*i+1]=cons[2][3*i+1]
            newcons[2][5*i+2]=cons[2][3*i+2]
            newcons[2][5*i+3]=cons[2][3*i+2]
            if cons[0][3*i+2] == 4:
                newcons[1][5*i+3] = newcons[1][5*i+2]+1
            #Eta constrains
            newcons[0][5*i+4]=0
            newcons[1][5*i+4]=0
            newcons[2][5*i+4]=0
            if self.config['NoConstrainsFlag'] == 0:
                if self.config['EtaFlag']:
                      #QUOTED=2
                      newcons[0][5*i+4]=2
                      newcons[1][5*i+4]=0.0
                      newcons[2][5*i+4]=1.0
       return  newpar,newcons

    def estimate_apvoigt(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       fittedpar,cons = self.estimate_pvoigt(xx,yy,zzz,xscaling,yscaling)
       npeaks=int(len(cons[0])/4)
       for i in range(npeaks):
            height = fittedpar[4*i]
            fwhm = fittedpar[4*i+2]
            fittedpar[4*i] = 0.5*(height * fwhm * 0.5 * numpy.pi)+\
                         0.5*(height * fwhm / (2.0*numpy.sqrt(2*numpy.log(2))))* numpy.sqrt(2 * numpy.pi)
       return fittedpar,cons

    def estimate_hypermet(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
       """
       if yscaling == None:
            try:
                yscaling=self.config['Yscaling']
            except Exception:
                yscaling=1.0
       if yscaling == 0:
            yscaling=1.0
       """
       fittedpar,cons = self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
       npeaks=int(len(cons[0])/3)
       newpar=[]
       newcons=numpy.zeros((3,8*npeaks),numpy.float64)
       main_peak=0
       #find out related parameters proper index
       if self.config['NoConstrainsFlag'] == 0:
            if self.config['SameFwhmFlag']:
                j=0
                #get the index of the free FWHM
                for i in range(npeaks):
                    if cons[0][3*i+2] != 4:
                        j=i
                for i in range(npeaks):
                    if i != j:
                       cons[1][3*i+2] = 8*j+2
                main_peak=j
       for i in range(npeaks):
                if fittedpar[3*i] > fittedpar[3*main_peak]:
                    main_peak = i

       for i in range(npeaks):
            height = fittedpar[3*i]
            position=fittedpar[3*i+1]
            fwhm = fittedpar[3*i+2]
            area = (height * fwhm / (2.0*numpy.sqrt(2*numpy.log(2))))*numpy.sqrt(2 * numpy.pi)
            #the gaussian parameters
            newpar.append(area)
            newpar.append(position)
            newpar.append(fwhm)
            #print "area, pos , fwhm = ",area,position,fwhm
            #Avoid zero derivatives because of not calculating contribution
            g_term    = 1
            st_term   = 1
            lt_term   = 1
            step_term = 1
            if self.config['HypermetTails'] != 0:
                    g_term    = self.config['HypermetTails'] & 1
                    st_term   = (self.config['HypermetTails']>>1) & 1
                    lt_term   = (self.config['HypermetTails']>>2) & 1
                    step_term = (self.config['HypermetTails']>>3) & 1
            if g_term == 0:
                    #fix the gaussian parameters
                    newcons[0][8*i]=CFIXED
                    newcons[0][8*i+1]=CFIXED
                    newcons[0][8*i+2]=CFIXED
            #else:
            #    newcons[0][8*i]=cons[0][3*i]
            #    newcons[0][8*i+1]=cons[0][3*i+1]
            #    newcons[0][8*i+2]=cons[0][3*i+2]
            #    newcons[1][8*i]=cons[1][3*i]
            #    newcons[1][8*i+1]=cons[1][3*i+1]
            #    newcons[1][8*i+2]=cons[1][3*i+2]
            #    newcons[2][8*i]=cons[2][3*i]
            #    newcons[2][8*i+1]=cons[2][3*i+1]
            #    newcons[2][8*i+2]=cons[2][3*i+2]
            #the short tail parameters
            if ((area*yscaling) < \
               self.config['MinGaussArea4ShortTail']) | \
               (st_term == 0):
               newpar.append(0.0)
               newpar.append(0.0)
               newcons[0][8*i+3]=CFIXED
               newcons[1][8*i+3]=0.0
               newcons[2][8*i+3]=0.0
               newcons[0][8*i+4]=CFIXED
               newcons[1][8*i+4]=0.0
               newcons[2][8*i+4]=0.0
            else:
               newpar.append(self.config['InitialShortTailAreaRatio'])
               newpar.append(self.config['InitialShortTailSlopeRatio'])
               newcons[0][8*i+3]=CQUOTED
               newcons[1][8*i+3]=self.config['MinShortTailAreaRatio']
               newcons[2][8*i+3]=self.config['MaxShortTailAreaRatio']
               newcons[0][8*i+4]=CQUOTED
               newcons[1][8*i+4]=self.config['MinShortTailSlopeRatio']
               newcons[2][8*i+4]=self.config['MaxShortTailSlopeRatio']
            #the long tail parameters
            if ((area*yscaling) < \
               self.config['MinGaussArea4LongTail']) | \
               (lt_term == 0):
               newpar.append(0.0)
               newpar.append(0.0)
               newcons[0][8*i+5]=CFIXED
               newcons[1][8*i+5]=0.0
               newcons[2][8*i+5]=0.0
               newcons[0][8*i+6]=CFIXED
               newcons[1][8*i+6]=0.0
               newcons[2][8*i+6]=0.0
            else:
               newpar.append(self.config['InitialLongTailAreaRatio'])
               newpar.append(self.config['InitialLongTailSlopeRatio'])
               newcons[0][8*i+5]=CQUOTED
               newcons[1][8*i+5]=self.config['MinLongTailAreaRatio']
               newcons[2][8*i+5]=self.config['MaxLongTailAreaRatio']
               newcons[0][8*i+6]=CQUOTED
               newcons[1][8*i+6]=self.config['MinLongTailSlopeRatio']
               newcons[2][8*i+6]=self.config['MaxLongTailSlopeRatio']
            #the step parameters
            if ((height*yscaling) < \
               self.config['MinGaussHeight4StepTail'])| \
               (step_term == 0):
               newpar.append(0.0)
               newcons[0][8*i+7]=CFIXED
               newcons[1][8*i+7]=0.0
               newcons[2][8*i+7]=0.0
            else:
               newpar.append(self.config['InitialStepTailHeightRatio'])
               newcons[0][8*i+7]=CQUOTED
               newcons[1][8*i+7]=self.config['MinStepTailHeightRatio']
               newcons[2][8*i+7]=self.config['MaxStepTailHeightRatio']
            #if self.config['NoConstrainsFlag'] == 1:
            #   newcons=numpy.zeros((3,8*npeaks),numpy.float64)
       if npeaks > 0:
          if g_term:
            if self.config['HeightAreaFlag']:
                for i in range(npeaks):
                    newcons[0] [8*i] = CPOSITIVE
            if self.config['PosFwhmFlag']:
                for i in range(npeaks):
                    newcons[0] [8*i+2] = CPOSITIVE
            if self.config['SameFwhmFlag']:
                for i in range(npeaks):
                    if i != main_peak:
                        newcons[0] [8*i+2] = CFACTOR
                        newcons[1] [8*i+2] = 8*main_peak+2
                        newcons[2] [8*i+2] = 1.0
            if self.config['QuotedPositionFlag']:
                for i in range(npeaks):
                    delta=self.config['DeltaPositionFwhmUnits'] * \
                      int(float(self.config['FwhmPoints']))
                    #that was delta in points
                    #I need it in terms of FWHM
                    delta=self.config['DeltaPositionFwhmUnits'] * fwhm
                    newcons[0][8*i+1] = CQUOTED
                    newcons[1][8*i+1] = newpar[8*i+1]-delta
                    newcons[2][8*i+1] = newpar[8*i+1]+delta
          if self.config['SameSlopeRatioFlag']:
            for i in range(npeaks):
                if i != main_peak:
                    newcons[0] [8*i+4] = CFACTOR
                    newcons[1] [8*i+4] = 8*main_peak+4
                    newcons[2] [8*i+4] = 1.0
                    newcons[0] [8*i+6] = CFACTOR
                    newcons[1] [8*i+6] = 8*main_peak+6
                    newcons[2] [8*i+6] = 1.0
          if self.config['SameAreaRatioFlag']:
            for i in range(npeaks):
                if i != main_peak:
                    newcons[0] [8*i+3] = CFACTOR
                    newcons[1] [8*i+3] = 8*main_peak+3
                    newcons[2] [8*i+3] = 1.0
                    newcons[0] [8*i+5] = CFACTOR
                    newcons[1] [8*i+5] = 8*main_peak+5
                    newcons[2] [8*i+5] = 1.0
       return  newpar,newcons

    def estimate_stepdown(self,xxx,yyy,zzz,xscaling=1.0,yscaling=1.0):
        crappyfilter=[-0.25,-0.75,0.0,0.75,0.25]
        cutoff = 2
        yy = numpy.convolve(yyy, crappyfilter, mode=1)[2:-2]
        if max(yy) > 0:
            yy = yy * max(yyy)/max(yy)
        xx=xxx[2:-2]
        # use height and not area
        fittedpar,cons=self.estimate_gauss(xx,yy,zzz,xscaling,yscaling)
        npeaks=int(len(fittedpar)/3)
        largest_index=0
        largest=[fittedpar[3*largest_index],
                 fittedpar[3*largest_index+1],
                 fittedpar[3*largest_index+2]]
        newcons=numpy.zeros((3,3),numpy.float64)
        for i in range(npeaks):
            if fittedpar[3*i] > largest[0]:
                largest_index=i
                largest=[fittedpar[3*largest_index],
                         fittedpar[3*largest_index+1],
                         fittedpar[3*largest_index+2]]
        largest[0] = max(yyy)-min(yyy)
        #Setup constrains
        if self.config['NoConstrainsFlag'] == 0:
                #Setup height constrains
                if self.config['HeightAreaFlag']:
                        #POSITIVE = 1
                        cons[0] [0] = 1
                        cons[1] [0] = 0
                        cons[2] [0] = 0

                #Setup position constrains
                if self.config['PositionFlag']:
                                #QUOTED = 2
                                cons[0][1]=2
                                cons[1][1]=min(xxx)
                                cons[2][1]=max(xxx)

                #Setup positive FWHM constrains
                if self.config['PosFwhmFlag']:
                                #POSITIVE=1
                                cons[0][2]=1
                                cons[1][2]=0
                                cons[2][2]=0

        return largest,cons

    def estimate_slit(self, xxx, yyy, zzz, xscaling=1.0, yscaling=1.0):
        largestup, cons = self.estimate_stepup(xxx, yyy, zzz, xscaling, yscaling)
        largestdown, cons = self.estimate_stepdown(xxx, yyy, zzz, xscaling, yscaling)
        height = 0.5*(largestup[0] + largestdown[0])
        position = 0.5*(largestup[1] + largestdown[1])
        fwhm = numpy.fabs(largestdown[1] - largestup[1])
        beamfwhm = 0.5 * (largestup[2] + largestdown[1])
        beamfwhm = min(beamfwhm, fwhm / 10.0)
        beamfwhm = max(beamfwhm,(max(xxx)-min(xxx))*3.0/len(xxx))
        #own estimation
        yy=yyy-zzz
        height=max(yyy-zzz)
        i1=numpy.nonzero(yy>=0.5*height)[0]
        xx=numpy.take(xxx,i1)
        position=(xx[0]+xx[-1])/2.0
        fwhm=xx[-1]-xx[0]
        largest=[height,position,fwhm,beamfwhm]
        cons=numpy.zeros((3,4),numpy.float64)
        #Setup constrains
        if self.config['NoConstrainsFlag'] == 0:
                #Setup height constrains
                if self.config['HeightAreaFlag']:
                        #POSITIVE = 1
                        cons[0] [0] = 1
                        cons[1] [0] = 0
                        cons[2] [0] = 0

                #Setup position constrains
                if self.config['PositionFlag']:
                                #QUOTED = 2
                                cons[0][1]=2
                                cons[1][1]=min(xxx)
                                cons[2][1]=max(xxx)

                #Setup positive FWHM constrains
                if self.config['PosFwhmFlag']:
                                #POSITIVE=1
                                cons[0][2]=1
                                cons[1][2]=0
                                cons[2][2]=0

                #Setup positive FWHM constrains
                if self.config['PosFwhmFlag']:
                                #POSITIVE=1
                                cons[0][3]=1
                                cons[1][3]=0
                                cons[2][3]=0
        return largest,cons

    def estimate_stepup(self, xxx, yyy, zzz, xscaling=1.0, yscaling=1.0):
        crappyfilter = [0.25, 0.75, 0.0, -0.75, -0.25]
        cutoff = 2
        yy = numpy.convolve(yyy, crappyfilter, mode=1)[2:-2]
        if max(yy) > 0:
            yy = yy * max(yyy)/max(yy)
        xx = xxx[2:-2]
        fittedpar, cons = self.estimate_gauss(xx, yy, zzz, xscaling, yscaling)
        npeaks = int(len(fittedpar) / 3)
        largest_index = 0
        largest = [fittedpar[3 * largest_index],
                   fittedpar[3 * largest_index + 1],
                   fittedpar[3 * largest_index + 2]]
        newcons=numpy.zeros((3,3),numpy.float64)
        for i in range(npeaks):
            if fittedpar[3*i] > largest[0]:
                largest_index=i
                largest=[fittedpar[3*largest_index],
                         fittedpar[3*largest_index+1],
                         fittedpar[3*largest_index+2]]
        largest[0] = max(yyy)-min(yyy)
        #Setup constrains
        if self.config['NoConstrainsFlag'] == 0:
                #Setup height constrains
                if self.config['HeightAreaFlag']:
                        #POSITIVE = 1
                        cons[0] [0] = 1
                        cons[1] [0] = 0
                        cons[2] [0] = 0

                #Setup position constrains
                if self.config['PositionFlag']:
                                #QUOTED = 2
                                cons[0][1]=2
                                cons[1][1]=min(xxx)
                                cons[2][1]=max(xxx)

                #Setup positive FWHM constrains
                if self.config['PosFwhmFlag']:
                                #POSITIVE=1
                                cons[0][2]=1
                                cons[1][2]=0
                                cons[2][2]=0

        return largest,cons

    def estimate_atan(self, *var, **kw):
        return self.estimate_stepup(*var, **kw)

    def estimate_periodic_gauss(self,xx,yy,zzz,xscaling=1.0,yscaling=None):
        if yscaling == None:
            try:
                yscaling=self.config['Yscaling']
            except Exception:
                yscaling=1.0
        if yscaling == 0:
            yscaling=1.0
        fittedpar=[]
        zz=SpecfitFuns.subac(yy,1.000,10000)

        npoints = len(zz)
        if self.config['AutoFwhm']:
            search_fwhm=self.guess_fwhm(x=xx,y=yy)
        else:
            search_fwhm=int(float(self.config['FwhmPoints']))
        search_sens=float(self.config['Sensitivity'])
        search_mca=int(float(self.config['McaMode']))

        if search_fwhm < 3:
            search_fwhm = 3
            self.config['FwhmPoints']=3

        if search_sens < 1:
            search_sens = 1
            self.config['Sensitivity']=1

        if npoints > 1.5*search_fwhm:
            peaks=self.seek(yy,fwhm=search_fwhm,
                               sensitivity=search_sens,
                               yscaling=yscaling,
                               mca=search_mca)
        else:
             peaks = []
        npeaks = len(peaks)
        if not npeaks:
            fittedpar = []
            cons = numpy.zeros((3,len(fittedpar)), numpy.float64)
            return fittedpar, cons

        fittedpar = [0.0, 0.0, 0.0, 0.0, 0.0]

        #The number of peaks
        fittedpar[0] = npeaks

        #The separation between peaks in x units
        delta  = 0.0
        height = 0.0
        for i in range(npeaks):
            height += yy[int(peaks[i])] - zz [int(peaks[i])]
            if i != ((npeaks)-1):
                delta += (xx[int(peaks[i+1])] - xx[int(peaks[i])])

        #delta between peaks
        if npeaks > 1:
            fittedpar[1] = delta/(npeaks-1)

        #starting height
        fittedpar[2] = height/npeaks

        #position of the first peak
        fittedpar[3] = xx[int(peaks[0])]

        #Estimate the fwhm
        fittedpar[4] = search_fwhm

        #setup constraints
        cons = numpy.zeros((3, 5), numpy.float64)
        cons [0] [0] = CFIXED     #the number of gaussians
        if npeaks == 1:
            cons[0][1] = CFIXED  #the delta between peaks
        else:
            cons[0][1] = CFREE   #the delta between peaks
        j = 2
        #Setup height area constrains
        if self.config['NoConstrainsFlag'] == 0:
            if self.config['HeightAreaFlag']:
                #POSITIVE = 1
                cons[0] [j] = 1
                cons[1] [j] = 0
                cons[2] [j] = 0
        j=j+1

        #Setup position constrains
        if self.config['NoConstrainsFlag'] == 0:
            if self.config['PositionFlag']:
                        #QUOTED = 2
                        cons[0][j]=2
                        cons[1][j]=min(xx)
                        cons[2][j]=max(xx)
        j=j+1

        #Setup positive FWHM constrains
        if self.config['NoConstrainsFlag'] == 0:
            if self.config['PosFwhmFlag']:
                        #POSITIVE=1
                        cons[0][j]=1
                        cons[1][j]=0
                        cons[2][j]=0
        j=j+1
        return fittedpar,cons


    def configure(self, *vars, **kw):
        if len(vars) == 1:
            if isinstance(vars[0], dict):
                kw.update(vars[0])
        for key in kw:
            notdone = 1
            #take care of lower / upper case problems ...
            for config_key in self.config:
                if config_key.lower() == key.lower():
                    self.config[config_key] = kw[key]
                    notdone = 0
            if notdone:
                self.config[key] = kw[key]
        return self.config

fitfuns=SpecfitFunctions()

FUNCTION=[fitfuns.gauss,
          fitfuns.lorentz,
          fitfuns.agauss,
          fitfuns.alorentz,
          fitfuns.pvoigt,
          fitfuns.apvoigt,
          fitfuns.splitgauss,
          fitfuns.splitlorentz,
          fitfuns.splitpvoigt,
          fitfuns.stepdown,
          fitfuns.stepup,
          fitfuns.slit,
          fitfuns.atan,
          fitfuns.hypermet,
          fitfuns.periodic_gauss,
          fitfuns.bkg_constant,
          fitfuns.bkg_linear]

PARAMETERS=[['Height','Position','FWHM'],
            ['Height','Position','Fwhm'],
            ['Area','Position','Fwhm'],
            ['Area','Position','Fwhm'],
            ['Height','Position','Fwhm','Eta'],
            ['Area','Position','Fwhm','Eta'],
            ['Height','Position','LowFWHM', 'HighFWHM'],
            ['Height','Position','LowFWHM', 'HighFWHM'],
            ['Height','Position','LowFWHM', 'HighFWHM', 'Eta'],
            ['Height','Position','FWHM'],
            ['Height','Position','FWHM'],
            ['Height','Position','FWHM','BeamFWHM'],
            ['Height','Position','Width'],
            ['G_Area','Position','FWHM',
             'ST_Area','ST_Slope','LT_Area','LT_Slope','Step_H'],
            ['N', 'Delta', 'Height', 'Position', 'FWHM'],
            ['Constant'],
            ['Constant', 'Slope']]

THEORY=['Gaussians',
        'Lorentz',
        'Area Gaussians',
        'Area Lorentz',
        'Pseudo-Voigt Line',
        'Area Pseudo-Voigt',
        'Split Gaussian',
        'Split Lorentz',
        'Split Pseudo-Voigt',
        'Step Down',
        'Step Up',
        'Slit',
        'Atan',
        'Hypermet',
        'Periodic Gaussians',
        'Constant',
        'Linear']

ESTIMATE=[fitfuns.estimate_gauss,
          fitfuns.estimate_lorentz,
          fitfuns.estimate_agauss,
          fitfuns.estimate_alorentz,
          fitfuns.estimate_pvoigt,
          fitfuns.estimate_apvoigt,
          fitfuns.estimate_splitgauss,
          fitfuns.estimate_splitlorentz,
          fitfuns.estimate_splitpvoigt,
          fitfuns.estimate_stepdown,
          fitfuns.estimate_stepup,
          fitfuns.estimate_slit,
          fitfuns.estimate_atan,
          fitfuns.estimate_hypermet,
          fitfuns.estimate_periodic_gauss,
          fitfuns.estimate_constant,
          fitfuns.estimate_linear]

CONFIGURE=[fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure,
           fitfuns.configure]

def test(a):
    from PyMca5.PyMcaGui import PyMcaQt as qt
    from PyMca5.PyMcaMath.fitting import Specfit
    from PyMca5.PyMcaGui.pymca import ScanWindow
    #print dir(a)
    x = numpy.arange(1000).astype(numpy.float64)
    p1 = numpy.array([1500,100.,50.0])
    p2 = numpy.array([1500,700.,50.0])
    y = a.gauss(p1,x)+1
    y = y + a.gauss(p2,x)
    app=qt.QApplication([])
    fit=Specfit.Specfit(x,y)
    fit.addtheory('Gaussians',a.gauss,['Height','Position','FWHM'],
                    a.estimate_gauss)
    fit.settheory('Gaussians')
    fit.setbackground('Linear')

    fit.estimate()
    fit.startfit()
    yfit=fit.gendata(x=x,parameters=fit.paramlist)
    print("I set an offset of 1 to see the difference in log scale :-)")
    w = ScanWindow.ScanWindow()
    w.addCurve(x, y + 1, "Data + 1")
    w.addCurve(x, yfit, "Fit")
    w.show()
    app.exec()


if __name__ == "__main__":
    test(fitfuns)
