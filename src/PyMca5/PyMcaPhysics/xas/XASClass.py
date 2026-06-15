#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2015 European Synchrotron Radiation Facility
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
__author__ = "M. Sanchez del Rio & V.A. Sole - ESRF"
__doc__ = """Processing of XAS data. For the time being, processing is very
basic. For state-of-the-art XAS you should take a look at dedicated packages
like IFEFFIT or Viper/XANES dactyloscope. Hopefully this module can be enhanced
to use those packages if present."""
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import copy
import logging
import numpy
import time
from PyMca5.PyMca import XASNormalization
from PyMca5.PyMca import linalg
try:
    from PyMca5.PyMca import _xas
    _XAS = True
except ImportError:
    _XAS = False
_logger = logging.getLogger(__name__)


def polynom(x, parameters):
    if hasattr(x, 'shape'):
        output = numpy.zeros(x.shape)
    else:
        output = 0.0
    for i in range(len(parameters)):
        output += parameters[i] * pow(x, i)
    return output

def victoreen(x, parameters):
    return parameters[0] * pow(x, -3) + parameters[1] * pow(x, -4)

def modifiedVictoreen(x, parameters):
    return parameters[0] * pow(x, -3) + parameters[1]

def e2k(energy, e0=0.0):
    r"""
        e2k(energy,e0=0.0): converts from E (eV) to k (A^-1)
        note: we use the convention that points with E<e0 will have negative k
    """
    codata_ec = numpy.array(1.602176565e-19)
    codata_me = numpy.array(9.10938291e-31)
    codata_h = numpy.array(6.62606957e-34)
    codata_hbar = codata_h/2.0/numpy.pi
    #; converts a set in energy to a set in k
    #; the negative energies (below edge) are treated as negative k
    tmpx = energy - e0
    ccte = numpy.sqrt(codata_ec*2*codata_me/codata_hbar/codata_hbar)*1e-10
    tmpxx = ((tmpx > 0) * 2-1) * numpy.sqrt(numpy.abs(tmpx)) * ccte
    return tmpxx

def k2e(kvalues):
    codata_ec = numpy.array(1.602176565e-19)
    codata_me = numpy.array(9.10938291e-31)
    codata_h = numpy.array(6.62606957e-34)
    codata_hbar = codata_h/2.0/numpy.pi

    #; converts a set in k to energy
    #; the negative energies (below edge) are treated as negative k
    ccte = numpy.power(codata_hbar,2) / (2 / codata_me / codata_ec * 1e20)
    tmpx = kvalues
    tmpx = ((tmpx > 0) * 2-1) * tmpx * tmpx * ccte
    return tmpx

def polspl_evaluate(set2,xl,xh,c,nc,nr):
    r"""
        polspl_evaluate(set2,xl,xh,c,nc,nr): for internal use of postedge

     PURPOSE:
    	evaluate the combined spline fitted from its coefficients.

     INPUTS:
    	set2: the set with the original data
    	xl,xh arrays contain nr adjacent ranges over which to fit individual polynomials.
           c array containing the polynomial coefficients resulting from the fit
           nc array that specifies how many poly coeffs to use in each range
           nr the number of adjacent ranges

     OUTPUTS:
    	a variable to receive a set with the same abscissas of the input one and
        the coordinates evaluated from the fit parameters

     MODIFICATION HISTORY:
     	Written by:	Manuel Sanchez del Rio. ESRF,  February, 1993
    	2009-05-13 srio@esrf.eu updated doc
        2014-12-04 srio@esrf.eu Translated to python
    """

    fit = set2*0.0
    #;change xl(1) and xh(nr) to extrapolate the fit
    xl[1] = numpy.min(set2[0,:])
    xh[nr] = numpy.max(set2[0,:])

    #;
    #; calculatest the first point
    #;
    xval=set2[0,0]
    yval=0.0
    for k in range(1,int(nc[1]+1)):
        yval =  yval+ c[k] * numpy.power(xval,(k-1))
    fit[0,0] = xval
    fit[1,0] = yval

    #;
    #; now the rest of the points
    #;
    if _logger.getEffectiveLevel() == logging.DEBUG:
        fit2 = fit *1
        for i in range(len(set2[0,:])):  # loop over all the points
            for j in range(1,int(nr+1)): # loop over the # of intervals
                if ((set2[0,i] > xl[j]) and (set2[0,i] <= xh[j])):
                    cstart=numpy.sum(nc[0:j])
                    xval = set2[0,i]
                    yval = 0.0
                    for k in range(1,int(nc[j]+1)):
                        yval =  yval+ c[cstart+k] * numpy.power(xval,(k-1))
                    fit2[0,i] = xval
                    fit2[1,i] = yval

    for j in range(1,int(nr+1)): # loop over the # of intervals
        idx = (set2[0, :] > xl[j]) & (set2[0,:] <= xh[j])
        xval = set2[0, idx]
        cstart=numpy.sum(nc[0:j])
        yval = 0.0 * xval
        for k in range(1,int(nc[j]+1)):
            yval += c[cstart+k] * numpy.power(xval,(k-1))
        fit[0, idx] = xval
        fit[1, idx] = yval

    if _logger.getEffectiveLevel() == logging.DEBUG:
        _logger.debug("GOOD? = %s", numpy.allclose(fit, fit2))
    return fit

def polspl(x,y,w,npts,xl,xh,nr,nc):
    r"""
        polspl(x,y,w,npts,xl,xh,nr,nc): for internal use of postedge

     PURPOSE:
    	polynomial spline least squares fit to data points Y(I).
    	only the function and it's first derivative are matched at the knots,
    	in order to give more degrees of freedom in the fit.

     INPUTS:
    	x(i),i=1,npts           abscissas
    	y(i),i=1,npts           ordinates
    	w(i),i=1,npts           weighting factor in least squares fit
    	fit minimizes the sum of w(i)*(y(i)-poly(x(i)))**2
    	if uniform weighting is desired, w(i) must be 1.
    	npts: points in x,y arrays.  xl,xh arrays contain NR adjacent ranges
    	over which to fit individual polynomials.  Array nc specifies
    	how many poly coeffs to use in each range.

     OUTPUTS:
    	array with all coeffs, the first nc(1) of which belong to the first range,
    	the second nc(2) of which belong to the second range, and so forth.

     SIDE EFFECTS:
    	Quite inefficient, because it uses a lot of loops inherited from
    	the Fortran code. However, for small set of data it is useful.

     PROCEDURE:
    	(Translated from a Fortran Code)
    	The method here is to fit ordinary polynomials in X, not B-splines,
    	in order to save space on a mini-computer.  This means that the
    	is rather poorly conditioned, and hence the limits on the
    	degree of the polynomial.  The method of solution is Lagrange's
    	undetermined multipliers for the knot constraints and gaussian
    	elimination to solve the linear system.

     MODIFICATION HISTORY:
     	Written by:	Manuel Sanchez del Rio. ESRF February, 1993
        2014-12-04 srio@esrf.eu Translated to python

        this subroutine is a translation of the fortran subroutine
        poslpl.for (found in the Frascati's package of EXAFS data analysis)
        which header states:

        	SUBROUTINE POLSPL(X,Y,W,NPTS,XL,XH,NR,C,NC)
        C
        C	POLYNOMIAL SPLINE LEAST SQUARES FIT TO DATA POINTS Y(I).
        C	ONLY THE FUNCTION AND IT'S FIRST DERIVATIVE ARE MATCHED AT THE KNOTS,
        C	IN ORDER TO GIVE MORE DEGREES OF FREEDOM IN THE FIT.
        C
        C	X(I),I=1,NPTS		ABSCISSAS
        C	Y(I),I=1,NPTS		ORDINATES
        C	W(I),I=1,NPTS		WEIGHTING FACTOR IN LEAST SQUARES FIT
        C			FIT MINIMIZES THE SUM OF W(I)*(Y(I)-POLY(X(I)))**2
        C			IF UNIFORM WEIGHTING IS DESIRED, W(I) MUST BE 1.
        C
        C	NPTS POINTS IN X,Y ARRAYS.  XL,XH ARRAYS CONTAIN NR ADJACENT RANGES
        C	OVER WHICH TO FIT INDIVIDUAL POLYNOMIALS.  ARRAY NC SPECIFIES
        C	HOW MANY POLY COEFFS TO USE IN EACH RANGE.  ARRAY C RETURNS
        C	ALL COEFFS, THE FIRST NC(1) OF WHICH BELONG TO THE FIRST RANGE,
        C	THE SECOND NC(2) OF WHICH BELONG TO THE SECOND RANGE, AND SO FORTH.
        C
        C	THE METHOD HERE IS TO FIT ORDINARY POLYNOMIALS IN X, NOT B-SPLINES,
        C	IN ORDER TO SAVE SPACE ON A MINI-COMPUTER.  THIS MEANS THAT THE
        C	FIT IS RATHER POORLY CONDITIONED, AND HENCE THE LIMITS ON THE
        C	DEGREE OF THE POLYNOMIAL.  THE METHOD OF SOLUTION IS LAGRANGE'S
        C	UNDETERMINED MULTIPLIERS FOR THE KNOT CONSTRAINTS AND GAUSSIAN
        C	ELIMINATION TO SOLVE THE LINEAR SYSTEM.
        C

    """

    # ;
    # ; few definitions
    # ;
    df = numpy.zeros(26)
    a = numpy.zeros((36,37))
    nbs = numpy.zeros(11,dtype=int)
    xk = numpy.zeros(10)
    c = numpy.zeros(36)
    j=0
    i=0
    ne_idl=0
    n = 0
    k = 0
    ibl = 0
    ns = 0
    ns1 = 0

    nbs[1]=1
    for i in range(1,nr+1):
        n=n+int(nc[i])
        nbs[i+1]=n+1
        if xl[i] < xh[i]:
            pass
        else:
            t=xl[i]
            xl[i]=xh[i]
            xh[i]=t

    n=n+2*(nr-1)
    n1=n+1
    xl[nr+1]=0.
    xh[nr+1]=0.
    # this loop ...
    for ibl in range(1,nr+1):
        xk[ibl]=.5*(xh[ibl]+xl[ibl+1])
        if (xl[ibl] > xl[ibl+1]):
            xk[ibl]=.5*(xl[ibl]+xh[ibl+1])
        ns=nbs[ibl]
        ne_idl=nbs[ibl+1]-1
        for i in range(1, npts+1):
            if((x[i] < xl[ibl]) or (x[i] > xh[ibl])):
                pass
            else:
                df[ns]=1.0
                ns1=ns+1
                for j in range(ns1,ne_idl+1):
                    df[j]=df[j-1]*x[i]
                for j in range(ns,ne_idl+1):
                    for k in range(j,ne_idl+1):
                        a[j,k]=a[j,k]+df[j]*df[k]*w[i]
                    a[j,n1]=a[j,n1]+df[j]*y[i]*w[i]
    # ... has to be faster
    ncol=nbs[nr+1]-1
    nk=nr-1

    if (nk == 0):
        pass
    else:
        for ik in range(1,nk+1):
            ncol=ncol+1
            ns=nbs[ik]
            ne_idl=nbs[ik+1]-1
            a[ns,ncol]=-1.
            ns=ns+1
            for i in range(ns,ne_idl+1):
                a[i,ncol]=a[i-1,ncol]*xk[ik]
            ncol=ncol+1
            a[ns,ncol]=-1.
            ns=ns+1
            if (ns > ne_idl):
                pass
            else:
                for i in range(ns,ne_idl+1):
                    a[i,ncol]=(ns-i-2)*numpy.power(xk[ik],(i-ns+1))
            ncol=ncol-1
            ns=nbs[ik+1]
            ne_idl=nbs[ik+2]-1
            a[ns,ncol]=1.0
            ns=ns+1
            for i in range(ns,ne_idl+1):
                a[i,ncol]=a[i-1,ncol]*xk[ik]
            ncol=ncol+1
            a[ns,ncol]=1.0
            ns=ns+1
            if (ns > ne_idl):
                pass
            else:
                for i in range(ns,ne_idl+1):
                    a[i,ncol]=(i-ns+2)*numpy.power(xk[ik],(i-ns+1))

    for i in range(1,n+1):
        i1=i-1
        for j in range(1,i1+1):
            a[i,j]=a[j,i]
    nm1=n-1

    for i in range(1,nm1+1):
        i1=i+1
        m=i
        t=numpy.abs(a[i,i])
        for j in range(i1,n+1):
            if (t >= numpy.abs(a[j,i])):
                pass
            else:
                m=j
                t=numpy.abs(a[j,i])
        if (m == i):
            pass
        else:
            for j in range(1,n1+1):
                t=a[i,j]
                a[i,j]=a[m,j]
                a[m,j]=t
        for j in range(i1,n+1):
            t=a[j,i]/a[i,i]
            for k in range(i1,n1+1):
                a[j,k]=a[j,k]-t*a[i,k]
    c[n]=a[n,n1]/a[n,n]
    for i in range(1,nm1+1):
        ni=n-i
        t=a[ni,n1]
        ni1=ni+1
        for j in range(ni1,n+1):
            t=t-c[j]*a[ni,j]
        c[ni]=t/a[ni,ni]
    return c

def polspl_test():
    r"""
        polspl_test(): to test polspl ()
    """
    set22 = numpy.loadtxt('set22.dat')
    set22 = set22.T

    npts = len(set22[1,:])
    w = numpy.ones(npts+1)
    xx = numpy.zeros(npts+1)
    yy = numpy.zeros(npts+1)
    #w=w*0.0+1.0

    xx[1:npts+1]=set22[0,:]
    yy[1:npts+1]=set22[1,:]
    xl = numpy.array( [ 0.0000000, 0.0000000, \
                        7.6354497, 15.270899, 0.0000000,\
                        0.0000000, 0.0000000, 0.0000000, 0.0000000, 0.0000000 ])
    xh = numpy.array( [  0.0000000, 7.6354497,\
                         15.270899, 22.906349, 0.0000000, 0.0000000,\
                         0.0000000, 0.0000000, 0.0000000, 0.0000000 ] )
    nc = numpy.array( [ 0.0000000, 4.0000000,\
                        4.0000000, 4.0000000, 0.0000000, 0.0000000,\
                        0.0000000, 0.0000000, 0.0000000, 0.0000000 ],
                        dtype=numpy.int32)
    nr =       3
    c = polspl(xx,yy,w,npts,xl,xh,nr,nc)
    #print("set22.shape",set22.shape)
    fit = polspl_evaluate(set22,xl,xh,c,nc,nr)
    #print("fit.shape",fit.shape)
    #print("c: ",c)
    #print("fit: ",fit)
    return


def postEdge(set2,kmin=None,kmax=None,polDegree=[3,3,3],knots=None, full=False):
    r"""
        postEdge(set2,kmin=None,kmax=None,polDegree=[3,3,3],knots=None)

     PURPOSE:
    	This procedure calculates the post edge fit of a xafs spectrum

     INPUTS:
    	set2: input set of data

     KEYWORD PARAMETERS:
        kmin the bottom limit for the fit (defaults kmin=0)
        kmax the upper limit for the fit (defaults max)

     OUTPUTS:
    	a set with the fit

     MODIFICATION HISTORY:
     	Written by:	Manuel Sanchez del Rio. ESRF
    	February, 1993
        1996-08-13 MSR (srio@esrf.fr) changes wmenu->wmenu2 and
                   xtext->widget_message
    	1998-10-01 srio@esrf.fr adapts for delia.
    	2000-02-12 MSR (srio@esrf.fr) adds Dialog_Parent keyword
    	2014-12-04 srio@esrf.eu Translated to python

    """
    #Note that in/out arrays are numpy way: numpy.array((npoints,2))

    xl = numpy.zeros(10)
    xh = numpy.zeros(10)
    c = numpy.zeros(36)
    nc = numpy.zeros(10, numpy.int32)
    if len(polDegree) > 10:
        _logger.warning("Error: Maximum number of intervals is 10")
        _logger.warning("       Number of intervals forced to 10")
        polDegree = polDegree[0:9]

    x1 = 0.0 # set2[:,0].min()
    x2 = set2[:,0].max()

    if kmin != None:
        x1 = kmin
    if kmax != None:
        x2 = kmax

    xrange1 = [x1,x2]
    _logger.debug("++++++++++++++++++%s", xrange1)
    if knots not in [None, []]:
        if len(knots) == len(polDegree):
            if knots[0] > kmin:
                knots = [kmin] + list(knots)
            elif knots[-1] < kmax:
                knots = list(knots) + [kmax]
        elif len(knots) == (len(polDegree) - 1):
            # probably just given the intermediate knots
            if knots[0] > kmin:
                knots = [kmin] + list(knots)
            if knots[-1] < kmax:
                knots = list(knots) + [kmax]
        if ( (len(polDegree)+1) != len(knots) ):
            _logger.warning("Error: dimension of knots must be dimension of polDegree+1")
            _logger.warning("       Forced automatic (equidistant) knot definition.")
            knots = None
        else:
            xrange1 = knots[0],knots[-1]


    nr = len(polDegree)
    xl[1] = xrange1[0]
    xh[nr] = xrange1[1]

    for i in range(1,nr+1):
        nc[i] = polDegree[i-1] + 1

    if knots == None:
        step = (xh[nr]-xl[1])/float(nr)
        for i in range(1,nr):
            xl[i+1] = xl[i] + step
            xh[i]   = xl[i+1]
    else:
        for i in range(1,nr):
            xl[i+1] = knots[i]
            xh[i]   = xl[i+1]

    #
    # select only points in selected interval
    #
    goodi = (set2[:,0] >= xrange1[0]) & (set2[:,0] <= xrange1[1])
    set22 = set2[goodi,:]

    _logger.debug(' Number of fitting points: %d', len(set22[:,0]))
    _logger.debug(' polynomials used for fitting: %d', nr)
    _logger.debug('#        degree   min      max')
    for i in range(1,nr+1):
        _logger.debug("%d %9d %9.2f %9.2f ",
                      i, nc[i]-1, xl[i], xh[i])

    # ;
    # ; call spline
    # ;
    npts = len(set22[:,0])
    w = numpy.ones(npts+1)
    xx = numpy.zeros(npts+1)
    yy = numpy.zeros(npts+1)
    xx[1:] = set22[:,0]
    yy[1:] = set22[:,1]

    #t0 = time.time()
    if _XAS:
        c = _xas.polspl(xx,yy,w,npts,xl,xh,nr,nc)
        if _logger.getEffectiveLevel() == logging.DEBUG:
            t0 = time.time()
            c2 = polspl(xx,yy,w,npts,xl,xh,nr,nc)
            _logger.debug("polspl elapsed = %s", time.time() - t0)
            _logger.debug("OK? %s", numpy.allclose(c, c2))
    else:
        c = polspl(xx,yy,w,npts,xl,xh,nr,nc)

    #TODO: polspl_evaluate receives and returns arrays like IDL (2,npoints)
    #t0 = time.time()
    fit0 = polspl_evaluate(set2.T,xl,xh,c,nc,nr)
    #print("polspl_evaluate elapsed = ", time.time() - t0)

    if full:
        xNodes = numpy.zeros((nr-1,), dtype=numpy.float32)
        yNodes = numpy.zeros((nr-1,), dtype=numpy.float32)
        for j in range(1,int(nr)): # loop over the # of intervals
            xval = xh[j]
            cstart=numpy.sum(nc[0:j])
            yval = 0.0
            for k in range(1,int(nc[j]+1)):
                yval += c[cstart+k] * numpy.power(xval,(k-1))
            xNodes[j-1] = xval
            yNodes[j-1] = yval
        return fit0.T, xNodes, yNodes
    else:
        return fit0.T

def postEdge0(k, mu, kmin=None, kmax=None, degrees=(3, 3, 3), knots=None, full=False):
    set0 = numpy.zeros((k.size, 2), dtype=k.dtype)
    set0[:, 0] = k
    set0[:, 1] = mu
    return postEdge(set0, kmin, kmax, degrees, knots=knots, full=full)

def getFTWindowWeights(tk, window="Gaussian", windpar=0.2, wrange=None):

    r"""
        window_ftr(setin,window=1,windpar=0.2,wrange=None)

      PURPOSE:
     	This procedure calculates and applies a weighting window to a set

      INPUTS:
     	setin:	either:
                 numpy.array(npoints,ncols) set of data  (CASE A)
                 numpy.array(npoints) array of abscissas  (CASE B)

      OUTPUT:
     	depends on the case:
           CASE A: numpy.array(npoints,ncol) set with the weigted set (in index [:,1])
           CASE B: numpy.array(npoints) the values of the weights

      KEYWORD PARAMETERS:
     	window = kind of window:
     		0 Gaussian Window (default)
     		1 Hanning Window
     		2 Box
     		3 Parzen (triangular)
     		4 Welch
     		5 Hamming
     		6 Tukey
     		7 Papul
     	windpar Parameter for windowing
     		If WINDOW=(2,3,4,5,6) this sets the width of the apodization (default=0.2)
     	wrange = [xmin,xmax] the limits of the window. If wrange
     		is not set, the take the minimum and maximum values
     		of the abscisas. The window has value zero outside
     		this interval.

      MODIFICATION HISTORY:
      	Written by:	Manuel Sanchez del Rio. ESRF
     	March, 1993
     	96-08-14 MSR (srio@esrf.fr) adds names keyword.
     	06-03-14 srio@esrf.fr always exits "names"
     	2014-12-03 srio@esrf.eu translated to python
    ;-
    """
    names = ['Gaussian', 'Hanning', 'Box','Parzen','Welch',
             'Hamming', 'Tukey', 'Papul', 'Kaiser']
    if hasattr(window, "lower"):
        window = window[0].upper() + window[1:].lower()
    else:
        window = names[window]
    _logger.debug("Using window %s", window)

    if wrange == None:
        xmax = tk.max()
        xmin = tk.min()
    else:
        xmin = wrange[0]
        xmax = wrange[1]

    xp = (xmax + xmin) / 2.
    xm = xmax - xmin
    apo1 = xmin + windpar
    apo2 = xmax - windpar

    npoint = len(tk)
    wind = numpy.ones(npoint, dtype=numpy.float64)

    if window in ["Gaussian", "Gauss"]:
        wind = numpy.power((tk - xp)/xm, 2)
        wind = numpy.exp(-wind * 9.2)

    elif window == "Hanning":
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = 0.5*(1.0-numpy.cos(numpy.pi*(tk[i]-xmin)/windpar))
            if tk[i] >= apo2:
                wind[i] = 0.5*(1.0+numpy.cos(numpy.pi*(tk[i]-apo2)/windpar))
    elif window == "Box":
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = 0.0
            if tk[i] >= apo2:
                wind[i] = 0.0
    elif window in ["Parzen", "Triangle", "Triangular"]:
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = (tk[i]-xmin)/windpar
            if tk[i] >= apo2:
                wind[i] = 1 - (tk[i]-apo2)/windpar
    elif window == "Welch":
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = 1.0 - numpy.power( ( (tk[i]-apo1) / windpar), 2)
            if tk[i] >= apo2:
                wind[i] =  1.0 - numpy.power( (tk[i]-apo2) / windpar, 2 )
    elif window == "Hamming":
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = 1.08 - (.54+0.46*numpy.cos(numpy.pi*(tk[i]-xmin)/windpar))
            if tk[i] >= apo2:
                wind[i] =   1.08 - (.54-0.46*numpy.cos(numpy.pi*(tk[i]-apo2)/windpar))
    elif window == "Tukey":
        for i in range(npoint):
            if tk[i] <= apo1:
                wind[i] = 1.0 - numpy.power(numpy.cos(0.5*numpy.pi*(tk[i]-xmin)/windpar),2)
            if tk[i] >= apo2:
                wind[i] = numpy.power(numpy.cos(-0.5*numpy.pi*(tk[i]-apo2)/windpar),2)
    elif window == "Papul":
        for i in range(npoint):
            if tk[i] <= apo1:
                a=(1./numpy.pi)*numpy.sin(numpy.pi*(tk[i]-xmin)/windpar) + \
                  (1.-(tk[i]-xmin)/windpar)*numpy.cos(numpy.pi*(tk[i]-xmin)/windpar)
                wind[i] = 1.0 - a
            if tk[i] >= apo2:
                a=(1./numpy.pi)*numpy.sin(numpy.pi*(tk[i]-apo2)/windpar) + \
                  (1.-(tk[i]-apo2)/windpar)*numpy.cos(numpy.pi*(tk[i]-apo2)/windpar)
                wind[i] = a
    elif _XAS and window in ["Kaiser", "Kasel"]:
        wind= (_xas.j0(windpar * numpy.sqrt(1. - 4.0 * pow((tk-xp)/xm, 2))) - 1.0)/ (_xas.j0(windpar) - 1.0)
    else:
        raise ValueError("Window <%s> not implemented" % window)
    return wind

def getFT(k, exafs, npoints=2048, rrange=(0.0, 7.0),
           krange=None, kstep=0.02, kweight=0,
           window="gaussian", apodization=0.2, wweights=None):
    if krange is not None:
        idx = (k >= krange[0]) & (k <= krange[1])
        k = k[idx]
        exafs = exafs[idx]
    if wweights is None:
        wweights = getFTWindowWeights(k,
                                      window=window,
                                      windpar=apodization,
                                      wrange=krange)


    # ;
    # ; creates the input interpolated values
    # ;
    interpolatedDataX = numpy.linspace(0.0, npoints-1, npoints) * kstep
    interpolatedDataY = numpy.interp( interpolatedDataX , k, wweights * exafs * pow(k, kweight),
                                      left=0.0, right=0.0)

    # ; calculates the fft and generates the conjugated variable (rr)

    ff = numpy.fft.ifft(interpolatedDataY)
    rstep = numpy.pi / npoints / kstep
    rr = numpy.linspace(0.0, npoints-1, npoints) * rstep


    # ;
    # ; prepare the results
    # ;

    coef = npoints * kstep / numpy.sqrt(numpy.pi) * numpy.sqrt(2.)
    f12 = coef*numpy.real(ff)             # real part of fft
    f13 = coef*numpy.imag(ff)*(-1.)       # imaginary part of fft

    # ;
    # ; cut the results to the selected interval in r (rrange)
    # ;

    goodi = (rr  >= rrange[0]) & (rr  <= rrange[1])
    f13 = f13[goodi]
    f12 = f12[goodi]
    f10 = rr[goodi]
    f11 = numpy.sqrt( f12*f12 + f13*f13)

    # ;
    # ; define the result array
    # ;
    fourier = numpy.zeros((len(f10),4))
    fourier[:,0] = f10
    fourier[:,1] = f11
    fourier[:,2] = f12
    fourier[:,3] = f13
    #print("OK = ", numpy.allclose(fourier, setFT))
    ddict = {}
    ddict["Set"] = fourier
    ddict["InterpolatedK"] = interpolatedDataX
    ddict["InterpolatedSignal"] = interpolatedDataY
    ddict["KWeight"] = kweight
    ddict["K"] = k
    ddict["WindowWeight"] = wweights
    ddict["FTRadius"] = f10
    ddict["FTIntensity"] = f11
    ddict["FTReal"] = f12
    ddict["FTImaginary"] = f13
    return ddict

def getBackFT(fourier,npoint=4096,krange=[2.0,12.0],rstep=None,rmin=None,rmax=None):
    r"""
        fastbftr(fourier,npoint=4096,krange=[2.0,12.0],rstep=None,rmin=None,rmax=None)

     PURPOSE:
    	This procedure calculates the Back Fast Fourier Transform of a set

     INPUTS:
           fourier:  a 4 col set with r,modulus,real and imaginary part
                   of a Fourier Transform of an Exafs spectum, as produced
                   by FTR or FASTFTR procedures

     KEYWORD PARAMETERS:
    	krange=[kmin,kmax] : range of the conjugated variable for
    		the transformation (default = [2,15])
    	npoint= number of points of the the fft calculation (default = 4096)
    	rstep = when this keyword is set then the fourier set is
    		interpolated using the indicated value as step. Otherwise
    		the fourier set is not interpolated.
        rmin = the mimimun r for the back fourier filtering
        rmax = the maximum r for the back fourier filtering

     OUTPUTS:
           This procedure returns a 4-columns set (backftr) with
           the conjugated variable (k) in column 0, the real part of the
           BFT in col 1, the modulus in col 2 and the phase in col 3.

     MODIFICATION HISTORY:
     	Written by:	Manuel Sanchez del Rio. ESRF March, 1993
    	98-10-26 srio@esrf.fr uses Dialog_Message for error messages.
        20141204 srio@esrf.eu Translated to python
    """

    kmin = krange[0]
    kmax = krange[1]

    npt = len(fourier[:,0])
    fou = numpy.zeros((npoint,4))

    if rmin == None:
        rmin = (fourier[:,0]).min()
    if rmax == None:
        rmax = (fourier[:,0]).max()

    #;
    #; fill "fou" set
    #;
    if rstep == None: #;--- no interpolation
        nn = int(npt/2)
        rstep = fourier[nn+1,0] - fourier[nn,0]
        rstep2 = fourier[nn+2,0] - fourier[nn+1,0]
        rdiff = numpy.abs (rstep - rstep2)
        _logger.debug(' back rstep = %f', rstep)
        _logger.debug(' rdiff = %f', rdiff)
        if (rdiff >= 1e-6):
            raise ValueError("r griding is not regular; Use rstep keyword -> Abort")
            #return fou
        ptstart = int(rmin/rstep)
        _logger.debug(' ptstart = %d', ptstart)
        _logger.debug(' ptstart+npt = %d', ptstart+npt)
        fou[ptstart:ptstart+npt,:]=fourier
    else: #;--- interpolation
        fou[:,0] = numpy.linspace(0,0,npoint-1,npoint)*rstep
        fou[:,1] = numpy.interp(fou[:,0],fourier[:,0],fourier[:,1],left=0.0,right=0.0)
        fou[:,2] = numpy.interp(fou[:,0],fourier[:,0],fourier[:,2],left=0.0,right=0.0)
        fou[:,3] = numpy.interp(fou[:,0],fourier[:,0],fourier[:,3],left=0.0,right=0.0)

    #;
    #; call back fft
    #;
    c = fou[:,2] - 1.0j * fou[:,3]
    af = numpy.fft.fft(c)

    #;
    #; create the array of the conjugated variable
    #;
    kstep = numpy.pi/npoint/rstep
    kk = numpy.linspace(0.0,npoint-1,npoint)*kstep


    #;
    #; prepare the output array
    #;
    coef = npoint*kstep/numpy.sqrt(numpy.pi)*numpy.sqrt(2.) # coefficienu used for direct fft
    coef1 = 2./coef                                         # 2 because we are only
    afr = coef1 * af.real                                   # real part of back fft
    afi = coef1 * af.imag                                   # imaginary part of back fft

    #;
    #; cut the results to the selected interval in k (krange)
    #;

    goodi = (kk  >= kmin) & (kk  <= kmax)
    afr = afr[goodi]
    afi = afi[goodi]
    afk = kk[goodi]
    nptout = len(afr)

    #;
    #; define the output set
    #;
    backftr = numpy.zeros((nptout,4))
    backftr[:,0] = afk                  # the conjugated variable (k [A^-1])
    backftr[:,1] = afr                  # the real part of backftr or atra
    backftr[:,2] = numpy.sqrt(afr*afr+afi*afi)    # the modulus of backftr
    backftr[:,3] = numpy.arctan2(afi,afr)          # the phase

    return backftr


class XASClass(object):
    def __init__(self, backend=None):
        # This lists are to be updated as larch or any other backend
        # is available
        self._e0MethodList = ("Manual",
                              "Auto - No Smooth",
                              "Auto - 3pt SG",
                              "Auto - 5pt SG",
                              "Auto - 7pt SG",
                              "Auto - 9pt SG")
        self._e0MethodDict = {
            "Manual": {"function": self._calculateE0, "vars":None, "kw":None},
            "Auto - No Smooth":  {"function": self._calculateE0,
                                  "vars":None,
                                  "kw":None},
            "Auto - 3pt SG": {"function": self._calculateE0, "vars":None, "kw":None},
            "Auto - 5pt SG": {"function": self._calculateE0, "vars":None, "kw":None},
            "Auto - 7pt SG": {"function": self._calculateE0, "vars":None, "kw":None},
            "Auto - 9pt SG": {"function": self._calculateE0, "vars":None, "kw":None}}

        # list of polynomials available
        self._polynomList = ['Modif. Victoreen',
                             'Victoreen',
                             'Constant',
                             'Linear',
                             'Parabolic',
                             'Cubic']
        self._polynomDict = {
            "Modif. Victoreen":{"function":modifiedVictoreen,
                                "vars":None,
                                "kw":None},
            "Victoreen":{"function":victoreen, "vars":None, "kw":None},
            "Constant":{"function":polynom, "vars":None, "kw":None},
            "Linear":{"function":polynom, "vars":None, "kw":None},
            "Parabolic":{"function":polynom, "vars":None, "kw":None},
            "Cubic":{"function":polynom, "vars":None, "kw":None}}

        self._configuration = self.getDefaultConfiguration(backend)

        self._processingPending = True
        self._energy = None
        self._mu = None

    def getDefaultConfiguration(self, backend=None):
        configuration = {}
        if backend in [None, "Default", "DefaultBackend"]:
            configuration["DefaultBackend"] = {}
            config = configuration["DefaultBackend"]
        else:
            raise ValueError("Only default backend supported")

        # normalization
        # E0 and pre-edge will be used for EXAFS extraction
        # PostEdge will only be used for the normalized spectrum
        # because EXAFS extraction follows its own methods
        # None parameters are to be derived from input spectrum
        config["Normalization"] = {}
        ddict = config["Normalization"]
        ddict["E0Method"] = "Auto - 5pt SG"
        ddict["E0Value"] = None
        ddict["E0MinValue"] = None
        ddict["E0MaxValue"] = None
        ddict["JumpNormalizationMethod"] = "Flattened"
        ddict["JumpNormalizationMethodList"] = ["Constant", "Flattened"]
        # limits to be used (relative to E0)
        ddict["PreEdge"] = {}
        ddict["PreEdge"] ["Method"] = "Polynomial"
        ddict["PreEdge"] ["Polynomial"] = "Linear"
        # Regions is a single list with 2 * n values delimiting n regions.
        ddict["PreEdge"] ["Regions"] = [-1000., -40.]
        ddict["PostEdge"] = {}
        ddict["PostEdge"] ["Method"] = "Polynomial"
        ddict["PostEdge"] ["Polynomial"] = "Linear"
        ddict["PostEdge"] ["Regions"] = [20., 500.]

        # EXAFS
        config["EXAFS"] = {}
        ddict = config["EXAFS"]
        # k grid
        # None parameters are to be derived from spectrum
        ddict["Grid"] = {}
        ddict["KMin"] = None
        ddict["KMax"] = None
        ddict["KWeight"] = 0
        ddict["Delta"] = None
        ddict["Nodes"] = None

        # extraction
        ddict["Normalization"] = "Fit"
        #ddict["Normalization"] = "Jump"
        # Normalization possibilities: Fit, Jump, Extrapolation"
        ddict["ExtractionMethod"] = "Knots"
        # Implement "Knots", "Victoreen", "Modif. Victoreen"
        ddict["Knots"] = {}
        ddict["Knots"] ["Number"] = 3
        ddict["Knots"] ["Values"] = None
        ddict["Knots"] ["Orders"] = [3, 2, 2, 3] # one more than knots

        # FT
        """
     	window = kind of window:
     		1 Gaussian Window (default)
     		2 Hanning Window
     		3 Box
     		4 Parzen (triangular)
     		5 Welch
     		6 Hamming
     		7 Tukey
     		8 Papul
     	windpar Parameter for windowing
     		If WINDOW=(2,3,4,5,6) this sets the width of the apodization (default=0.2)
     	wrange = [xmin,xmax] the limits of the window. If wrange
     		is not set, the take the minimum and maximum values
     		of the abscisas. The window has value zero outside
     		this interval.
     	"""
        config["FT"] = {}
        ddict = config["FT"]
        ddict["Window"] = "Gaussian"
        ddict["WindowList"] = ["Gaussian", "Hanning", "Box", "Parzen",
                               "Welch", "Hamming", "Tukey", "Papul"]
        ddict["WindowApodization"] = 0.02
        ddict["WindowRange"] = None
        ddict["KStep"] = 0.04
        ddict["Points"] = 2048
        ddict["Range"] = [0.0, 7.0]

        # Back-FT
        config["BFT"] = {}
        ddict = config["BFT"]
        ddict["KRange"] = [2.0, 12.0]
        ddict["Points"] = 2048
        ddict["Range"] = [0.0, 6.0]
        return configuration

    def setConfiguration(self, configuration, backend=None):
        if backend not in [None, "Default", "DefaultBackend"]:
            raise ValueError("Only default backend implemented")
        else:
            if "DefaultBackend" in configuration:
                inputConfig = configuration["DefaultBackend"]
            else:
                inputConfig = configuration
            backend = "DefaultBackend"
        currentConfig = self.getConfiguration(backend=backend)
        newConfiguration = \
                self.mergeConfigurationDicts(currentConfig, inputConfig)
        self._configuration[backend] = newConfiguration
        self._processingPending = True

    def mergeConfigurationDicts(self, referenceDict,
                                      inputDict):
        destinationDict = {}
        referenceKeys = list(referenceDict.keys())
        for referenceKey in referenceKeys:
            ref = referenceDict[referenceKey]
            referenceLower = referenceKey.lower()
            treated = False
            for key in inputDict:
                if key.lower() == referenceLower:
                    if hasattr(referenceDict[referenceKey], "keys"):
                        inp = inputDict[key]
                        destinationDict[referenceKey] = \
                                self.mergeConfigurationDicts(ref, inp)
                    else:
                        destinationDict[referenceKey] = inputDict[key]
                    treated = True
                    break
            if not treated:
                if hasattr(referenceDict[referenceKey], "keys"):
                    destinationDict[referenceKey] = copy.deepcopy(ref)
                else:
                    destinationDict[referenceKey] = ref
        return destinationDict

    def getConfiguration(self, backend=None):
        if backend not in [None, "Default", "DefaultBackend", "All", "all"]:
            raise ValueError("Only default backend implemented")
        if backend in ["all", "All"]:
            return copy.deepcopy(self._configuration)
        else:
            return copy.deepcopy(self._configuration["DefaultBackend"])

    def setSpectrum(self, energy, mu, units=None, sanitize=True):
        self._lastE0CalculationDict = None
        energy0 = numpy.array(energy, dtype=numpy.float64, copy=True)
        mu0 = numpy.array(mu, dtype=numpy.float64, copy=True)
        energy0 = numpy.ravel(energy0)
        mu0 = numpy.ravel(mu0)
        self._equidistant = False

        # TODO: This should become a function to be called on its own
        # make sure data are sorted
        idx = energy.argsort(kind='mergesort')
        energy = numpy.take(energy0, idx)
        mu = numpy.take(mu0, idx)

        # make sure data are strictly increasing
        delta = energy[1:] - energy[:-1]
        dmin = delta.min()
        dmax = delta.max()
        if delta.min() <= 1.0e-10:
            # force data to be strictly increasing
            # although we do not consider last point
            idx = numpy.nonzero(delta>0)[0]
            energy = numpy.take(energy, idx)
            mu = numpy.take(mu, idx)
            delta = None

        if dmin == dmax:
            equidistant = True
        else:
            equidistant = False

        if units is None:
            if (energy[-1] - energy[0]) < 10:
                units = "keV"
            else:
                units = "eV"
        if units.lower() not in ["kev", "ev"]:
            raise ValueError("Unhandled units %s" % units)
        elif units.lower() == "kev":
            energy *= 1000.
            energy0 *= 1000.

        # everything went well, update internal variables
        self._energy0 = energy0
        self._mu0 = mu0
        self._energy = energy
        self._mu = mu
        self._units = units
        self._equidistant = equidistant

    def processSpectrum(self):
        e0 = self.calculateE0()
        ddict = self.normalize()
        """
        return {"Jump": jump,
                "NormalizedEnergy": energy,
                "NormalizedMu":normalizedSpectrum,
                "NormalizedBackground": data["PreEdge"],
                "NormalizedSignal":data["PostEdge"]}
        """
        ddict["Energy"] = self._energy
        ddict["Mu"] = self._mu
        cleanMu = self._mu - ddict["NormalizedBackground"]
        kValues = e2k(self._energy - e0)
        ddict.update(self.postEdge(kValues, cleanMu))

        dataSet = numpy.zeros((cleanMu.size, 2), numpy.float64)
        dataSet[:, 0] = kValues
        dataSet[:, 1] = cleanMu

        # normalization
        exafs = (cleanMu - ddict["PostEdgeB"]) / ddict["PostEdgeB"]
        ddict["EXAFSEnergy"] = k2e(kValues)
        ddict["EXAFSKValues"] = kValues
        ddict["EXAFSSignal"] = cleanMu
        if ddict["KWeight"]:
            exafs *= pow(kValues, ddict["KWeight"])
        ddict["EXAFSNormalized"] = exafs

        set2 = dataSet * 1
        set2[:,1] = exafs

        #remove points with k<2
        goodi = (set2[:,0] >= ddict["KMin"]) & (set2[:,0] <= ddict["KMax"])
        set2 = set2[goodi,:]

        #plotSet(set2,xtitle="k [$A^{-1}$]",ytitle="$\chi$", toptitle=" CUCU EXAFS")


        # FT
        # window
        setFT = self.fourierTransform(set2[:,0], set2[:, 1], kMin=ddict["KMin"], kMax=ddict["KMax"])
        ddict["FT"] = setFT
        THOUGHTS = """
            # for BFT
            setBFT = getBackFT(setFT["Set"],rmin=1.0,rmax=3.0,krange=[2.0,20.0])
            ddict["BFT"] = setBFT
            """
        return ddict


    def fourierTransform(self, k, mu, kMin=None, kMax=None, backend=None):
        if backend not in [None, "Default", "DefaultBackend"]:
            raise ValueError("Only default backend implemented")
        else:
            backend = "DefaultBackend"
        config = self._configuration[backend]["FT"]
        if kMin is None:
            kMin = k.min()
        if kMax is None:
            kMax = k.max()
        kRange = config["WindowRange"]
        if config["WindowRange"] in [None, "None"]:
            kRange = [kMin, kMax]
        else:
            kRange = [max(kRange[0], kMin), min(kRange[1], kMax)]
        return getFT(k, mu, npoints=config["Points"],
                     krange=kRange,\
                     window=config.get("Window", "Gaussian"),
                     apodization=config.get("WindowApodization", 0.02),
                     rrange=config["Range"],
                     kstep=config["KStep"])

    def postEdge(self, k, mu, backend=None):
        if backend not in [None, "Default", "DefaultBackend"]:
            raise ValueError("Only default backend implemented")
        else:
            backend = "DefaultBackend"
        config = self._configuration[backend]["EXAFS"]
        method = config["ExtractionMethod"]
        # Grid
        kMin = config["KMin"]
        kMax = config["KMax"]
        kWeight = config["KWeight"]
        if kMin is None:
            kMin = 2
        if kMax is None:
            kMax = k.max()
        else:
            kMax = min(k.max(), kMax)
        number = config["Knots"].get("Number", 0)
        if number == 0:
            knots = None
            if not hasattr(config["Knots"]["Orders"], "__len__"):
                config["Knots"]["Orders"] = [config["Knots"]["Orders"]]
        else:
            knots = config["Knots"]["Values"]
            if not hasattr(knots, "__len__"):
                knots = [knots]
        fit0, xNodes, yNodes = postEdge0(k, mu, kMin, kMax,
                         config["Knots"]["Orders"],
                         knots=knots, full=True)
        ddict = {}
        ddict["PostEdgeK"] = fit0[:, 0]
        ddict["PostEdgeB"] = fit0[:, 1]
        ddict["KnotsX"] = xNodes
        ddict["KnotsY"] = yNodes
        ddict["KMin"] = kMin
        ddict["KMax"] = kMax
        ddict["KWeight"] = kWeight
        # TODO: add polynomials?
        return ddict

    def calculateE0(self, energy=None, mu=None, backend=None):
        self._lastE0CalculationDict = None
        if energy is None:
            energy = self._energy
        if mu is None:
            mu = self._mu
        if backend not in [None, "Default", "DefaultBackend"]:
            raise ValueError("Only default backend implemented")
        else:
            backend = "DefaultBackend"
        config = self._configuration[backend]["Normalization"]
        method = config["E0Method"]

        fun = self._e0MethodDict[method]["function"]
        varList = self._e0MethodDict[method]["vars"]
        kwDict = self._e0MethodDict[method]["kw"]
        if (varList is None) and (kwDict is None):
            outputDict = fun(energy, mu, config)
        elif varList is None:
            outputDict = fun(energy, mu, config, **kwDict)
        else:
            outputDict = fun(energy, mu, config, *varList)
        return outputDict["edge"]

    def _calculateE0(self, energy, mu, config):
        method = config["E0Method"]
        methodLower = method.lower()
        e0 = config["E0Value"]
        eMin = config["E0MinValue"]
        eMax = config["E0MaxValue"]
        if eMin is None:
            eMin = energy.min()
        if eMax is None:
            eMax = energy.max()
        if (e0 is None) and methodLower.endswith("manual"):
            raise ValueError("Edge energy not set")
        if (id(energy) == id(self._energy)) and self._equidistant:
            # data do not need to be interpolated
            _logger.debug("NO INTERPOLATION")
            eWork = energy
            muWork = mu
        else:
            nWorkingPoints = 10 * energy.size
            eWork = numpy.linspace(energy[1], energy[-2], nWorkingPoints)
            muWork = numpy.interp(eWork, energy, mu, mu[0], mu[-1])
        eWork = numpy.ravel(eWork)
        muWork = numpy.ravel(muWork)

        methodLower = method.lower()
        if methodLower.endswith("manual"):
            return {"edge":e0}
        elif methodLower.endswith("no smooth"):
            idx = numpy.gradient(muWork).argmax()
            return eWork[idx]
        elif methodLower.endswith("3pt sg"):
            npoints = 3
        elif methodLower.endswith("5pt sg"):
            npoints = 5
        elif methodLower.endswith("7pt sg"):
            npoints = 7
        elif methodLower.endswith("9pt sg"):
            npoints = 9
        else:
            raise ValueError("Method <%s> not implemented" % method)

        # Returning dictionary can contain:
        # The edge energy (mandatory)
        # The interpolated spectrum (if any)
        # The derivative spectrum (if any)
        ddict = XASNormalization.getE0SavitzkyGolay(eWork, muWork, \
                                                    points=npoints, full=True)
        self._lastE0CalculationDict = ddict
        return ddict

    def _getRegionsData(self, x0, y0, regions):
        x = x0[:]
        y = y0[:]
        x = numpy.ravel(x)
        y = numpy.ravel(y)
        i = 0
        for region in regions:
            xmin, xmax = region
            toidx = numpy.nonzero((x >=xmin) & (x <= xmax))[0]
            if i == 0:
                i = 1
                idx = toidx
            else:
                idx = numpy.concatenate((idx, toidx), axis = 0)
        xOut = numpy.take(x, idx)
        yOut = numpy.take(y, idx)
        return xOut, yOut

    def normalize(self, energy=None, mu=None, backend=None):
        if energy is None:
            energy = self._energy
        else:
            self._lastE0CalculationDict = None
        if mu is None:
            mu = self._mu
        else:
            self._lastE0CalculationDict = None
        if backend not in [None, "Default", "DefaultBackend"]:
            raise ValueError("Only default backend implemented")
        else:
            backend = "DefaultBackend"
        config = self._configuration[backend]["Normalization"]
        # reference values
        eMin = energy.min()
        eMax = energy.max()
        # e0
        if self._lastE0CalculationDict is None:
            e0 = self.calculateE0(energy, mu, backend=backend)
        else:
            e0 = self._lastE0CalculationDict["edge"]

        parameters = {}
        data = {}
        for key in ["PreEdge", "PostEdge"]:
            # pre-edge
            # Regions is a single list with 2 * n values delimiting n regions.
            regions = config [key] ["Regions"]
            edgeMethod = config[key]["Method"]
            if edgeMethod.lower() != "polynomial":
                raise ValueError("Only normalization with polynomials implemented")
            method = config[key]["Polynomial"]
            methodLower = method.lower()
            if regions is None:
                if key == "PreEdge":
                    regions = [-1000., -40.]
                else:
                    regions = [20., 1000.]
            workingRegions = []
            if key == "PreEdge":
                plotMin = eMax
                for i in range(0, len(regions), 2):
                    vMin = e0 + regions[2 * i]
                    vMax = e0 + regions[2 * i + 1]
                    if vMin < eMin:
                        vMin = eMin
                    if vMax < eMin:
                        vMax = 0.5 * (eMin + e0)
                    if vMin < plotMin:
                        plotMin = vMin
                    workingRegions.append([vMin, vMax])
            else:
                plotMax = eMin
                for i in range(0, len(regions), 2):
                    vMin = e0 + regions[2 * i]
                    vMax = e0 + regions[2 * i + 1]
                    if vMin > eMax:
                        vMin = 0.5 * (e0 + eMax)
                    if vMax < eMin:
                        vMax = eMax
                    if vMax > plotMax:
                        plotMax = vMax
                    workingRegions.append([vMin, vMax])
            x, y = self._getRegionsData(energy, mu, workingRegions)
            if methodLower == "constant":
                modelMatrix = numpy.ones((x.size, 1), numpy.float64)
                #parameters[key] = y.mean()
            elif methodLower == "linear":
                modelMatrix = numpy.empty((x.size, 2), numpy.float64)
                modelMatrix[:, 0] = 1.0
                modelMatrix[:, 1] = x
            elif methodLower == "parabolic":
                modelMatrix = numpy.empty((x.size, 3), numpy.float64)
                modelMatrix[:, 0] = 1.0
                modelMatrix[:, 1] = x
                modelMatrix[:, 2] = pow(x, 2)
            elif methodLower == "cubic":
                modelMatrix = numpy.empty((x.size, 4), numpy.float64)
                modelMatrix[:, 0] = 1.0
                modelMatrix[:, 1] = x
                modelMatrix[:, 2] = pow(x, 2)
                modelMatrix[:, 3] = pow(x, 3)
            elif methodLower == "victoreen":
                modelMatrix = numpy.empty((x.size, 2), numpy.float64)
                modelMatrix[:,0] = pow(x, -3)
                modelMatrix[:,1] = pow(x, -4)
            elif methodLower == "modif. victoreen":
                modelMatrix = numpy.empty((x.size, 2), numpy.float64)
                modelMatrix[:,0] = pow(x, -3)
                modelMatrix[:,1] = 1.0
            else:
                raise ValueError("Unhandled %s polynomial <%s> " % \
                                 (key, config[key]["Polynomial"]))
            # if only one point has been picked from region
            if len(y) == 1:
                if methodLower != 'constant':
                    _logger.warning('Only one data point in region, '
                                    'assuming constant function.')
                parameters[key] = y
            else:
                parameters[key] = linalg.lstsq(modelMatrix, y,
                                               uncertainties=False, weight=False)[0]
            fun = self._polynomDict[method]["function"]
            if key == "PreEdge":
                funPre = fun
            data[key] = fun(energy, parameters[key])
        jump = fun(e0, parameters["PostEdge"]) - \
               funPre(e0, parameters["PreEdge"])
        #normalizedSpectrum = (mu - data["PreEdge"])/(data["PostEdge"]
        jumpMethod = config.get("JumpNormalizationMethod", "Flattened")
        normalizedSpectrum = (mu - data["PreEdge"])/jump
        if jumpMethod in [0, "Constant", "constant"]:
            jumpMethod = "Constant"
            pass
        elif jumpMethod in [1, "Flattened", "flattened", "Flatten", "flatten"]:
            jumpMethod = "Flattened"
            i = numpy.argmin(energy < e0)
            normalizedSpectrum[i:] *= (jump / \
                                      (data["PostEdge"] - data["PreEdge"])[i:])
        else:
            _logger.warning("WARNING: Undefined jump normalization method. Assume Flattened")
            jumpMethod = "Flattened"
            i = numpy.argmin(energy < e0)
            normalizedSpectrum[i:] *= (jump / \
                                      (data["PostEdge"] - data["PreEdge"])[i:])

        return {"Jump": jump,
                "JumpNormalizationMethod":jumpMethod,
                "Edge":e0,
                "NormalizedEnergy": energy,
                "NormalizedMu":normalizedSpectrum,
                "NormalizedBackground": data["PreEdge"],
                "NormalizedSignal":data["PostEdge"],
                "NormalizedPlotMin": plotMin,
                "NormalizedPlotMax":plotMax}

if __name__ == "__main__":
    import os
    import sys
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR
    if len(sys.argv) > 1:
        fileName = sys.argv[1]
    else:
        fileName = os.path.join(PYMCA_DATA_DIR, "EXAFS_Ge.dat")
    if len(sys.argv) > 2:
        cfg = sys.argv[2]
    else:
        cfg = None
    scan = specfile.Specfile(fileName)[0]
    data = scan.data()
    if data.shape[0] == 2:
        energy = data[0, :]
        mu = data[1, :]
    else:
        energy = None
        mu = None
        labels = scan.alllabels()
        i = 0
        for label in labels:
            if label.lower() == "energy":
                energy = data[i, :]
            elif label.lower() in ["counts", "mu", "absorption"]:
                mu = data[i, :]
            i = i + 1
        if (energy is None) or (mu is None):
            if len(labels) == 3:
                if labels[0].lower() == "point":
                    energy = data[1, :]
                    mu = data[2, :]
                else:
                    energy = data[0, :]
                    mu = data[1, :]
            else:
                energy = data[0, :]
                mu = data[1, :]

    exafs = XASClass()
    if cfg is not None:
        from PyMca5.PyMca import ConfigDict
        config = ConfigDict.ConfigDict()
        config.read(cfg)
        exafs.setConfiguration(config['XASParameters'])
    exafs.setSpectrum(energy, mu)
    t0 = time.time()
    ddict = exafs.processSpectrum()
    print("Elapsed = ", time.time() - t0)
    #sys.exit()
    from PyMca5.PyMca import PyMcaQt as qt
    app = qt.QApplication([])
    from silx.gui.plot import Plot1D
    w = Plot1D()
    w.addCurve(energy, mu, legend="original")
    w.addCurve(ddict["NormalizedEnergy"],
               ddict["NormalizedMu"], legend="Mu", yaxis="right")
    w.addCurve(ddict["NormalizedEnergy"],
               ddict["NormalizedSignal"], legend="Post")
    w.addCurve(ddict["NormalizedEnergy"],
               ddict["NormalizedBackground"], legend="Pre")
    w.resetZoom()
    w.show()
    exafs = Plot1D()
    idx = (ddict["EXAFSKValues"] >= ddict["KMin"]) & \
          (ddict["EXAFSKValues"] <= ddict["KMax"])
    exafs.addCurve(ddict["EXAFSKValues"][idx], ddict["EXAFSNormalized"][idx],
                   legend="Normalized EXAFS")
    exafs.show()
    #"""
    ft = Plot1D()
    ft.addCurve(ddict["FT"]["FTRadius"], ddict["FT"]["FTIntensity"])
    ft.resetZoom()
    ft.show()
    #"""
    app.exec()
