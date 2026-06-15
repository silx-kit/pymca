#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
import numpy
from numpy.linalg import inv
import time
# codes understood by the routine
CFREE       = 0
CPOSITIVE   = 1
CQUOTED     = 2
CFIXED      = 3
CFACTOR     = 4
CDELTA      = 5
CSUM        = 6
CIGNORED    = 7

ONED = 0

def LeastSquaresFit(model, parameters0, data=None, maxiter = 100,constrains=None,
                        weightflag = 0,model_deriv=None,deltachi=None,fulloutput=0,
                        xdata=None,ydata=None,sigmadata=None,linear=None):
    """
    Typical use:

    LeastSquaresFit(model_function, parameters, xdata=xvalues, ydata=yvalues)

        model_function - it has the form model_function(parameters, x) where parameters is a sequence
                         containing the parameters to be refined and x is the array of values in which
                         the function is to be evaluated.

        parameters - sequence with the initial values to be refined

        xdata - array with the x axis data points

        ydata - array with the y axis data points

    Additional keywords:

        sigmadata - array with the uncertainties associated to ydata (default is sqrt(y) )

        weightflag - 0 Means no weighted fit 1 means weighted fit

        constrains - if provided, it is a 2D sequence of dimension (3, n_parameters) where, for each
                     parameter denoted by the index i, the meaning is

                     constrains[0][i] -> 0 - Free (Gefit.CFREE)
                                         1 - Positive (Gefit.CPOSITIVE)
                                         2 - Quoted (Gefit.CQUOTED)
                                         3 - Fixed (Gefit.CFIXED)
                                         4 - Factor (Gefit.CFACTOR)
                                         5 - Delta (Gefit.CDELTA)
                                         6 - Sum (Gefit.CSUM)


                     constrains[1][i] -> Ignored if constrains[0][i] is 0, 1, 3
                                         Min value of the parameter if constrains[0][i] is Gefit.CQUOTED
                                         Index of fitted parameter to which it is related

                     constrains[2][i] -> Ignored if constrains[0][i] is 0, 1, 3
                                         Max value of the parameter if constrains[0][i] is Gefit.CQUOTED
                                         Factor to apply to related parameter with index constrains[1][i]
                                         Difference with parameter with index constrains[1][i]
                                         Sum obtained when adding parameter with index constrains[1][i]

        model_deriv - function providing the derivatives of the fitting function respect to the fitted parameters.
                      It will be called as model_deriv(parameters, index, x) where parameters are the current values
                      of the fitting parameters, index is the fitting parameter index of which the the derivative has
                      to be provided in the supplied array of x points.

        linear - Flag to indicate a linear fit instead of a non-linear. Default is non-linear fit (=false)

        maxiter - Maximum number of iterations (default is 100)

    Output:

        fitted_parameters, reduced_chi_square, uncertainties

    """
    if constrains is None:
        constrains = []
    parameters = numpy.asarray(parameters0, dtype=numpy.float64)
    if linear is None:linear=0
    if deltachi is None:
        deltachi = 0.01
    if ONED:
      data0 = numpy.array(data)
      x = data0[0:2,0]
    #import SimplePlot
    #SimplePlot.plot([data[:,0],data[:,1]],yname='Received data')
    else:
        if xdata is None:
            x=numpy.array([y[0] for y in data])
        else:
            x=xdata
    if linear:
           return LinearLeastSquaresFit(model,parameters,
                                        data,maxiter,
                                        constrains,weightflag,model_deriv=model_deriv,
                                        deltachi=deltachi,
                                        fulloutput=fulloutput,
                                        xdata=xdata,
                                        ydata=ydata,
                                        sigmadata=sigmadata)
    elif len(constrains) == 0:
        try:
            model(parameters,x)
            constrains = [[],[],[]]
            for i in range(len(parameters0)):
                constrains[0].append(0)
                constrains[1].append(0)
                constrains[2].append(0)
            return RestreinedLeastSquaresFit(model,parameters,
                                    data,maxiter,
                                    constrains,weightflag,
                                    model_deriv=model_deriv,
                                    deltachi=deltachi,
                                    fulloutput=fulloutput,
                                    xdata=xdata,
                                    ydata=ydata,
                                    sigmadata=sigmadata)
        except TypeError:
            print("You should reconsider how to write your function")
            raise TypeError("You should reconsider how to write your function")
    else:
        return RestreinedLeastSquaresFit(model,parameters,
                                data,maxiter,
                                constrains,weightflag,model_deriv=model_deriv,
                                deltachi=deltachi,
                                fulloutput=fulloutput,
                                xdata=xdata,
                                ydata=ydata,
                                sigmadata=sigmadata)

def LinearLeastSquaresFit(model0,parameters0,data0,maxiter,
                                constrains0,weightflag,model_deriv=None,deltachi=0.01,fulloutput=0,
                                    xdata=None,
                                    ydata=None,
                                    sigmadata=None):
    #get the codes:
    # 0 = Free       1 = Positive     2 = Quoted
    # 3 = Fixed      4 = Factor       5 = Delta
    # 6 = Sum        7 = ignored
    constrains = [[],[],[]]
    if len(constrains0) == 0:
        for i in range(len(parameters0)):
            constrains[0].append(0)
            constrains[1].append(0)
            constrains[2].append(0)
    else:
        for i in range(len(parameters0)):
            constrains[0].append(constrains0[0][i])
            constrains[1].append(constrains0[1][i])
            constrains[2].append(constrains0[2][i])
    for i in range(len(parameters0)):
        if type(constrains[0][i]) == type('string'):
            #get the number
            if   constrains[0][i] == "FREE":
                 constrains[0][i] = CFREE
            elif constrains[0][i] == "POSITIVE":
                 constrains[0][i] = CPOSITIVE
            elif constrains[0][i] == "QUOTED":
                 constrains[0][i] = CQUOTED
            elif constrains[0][i] == "FIXED":
                 constrains[0][i] = CFIXED
            elif constrains[0][i] == "FACTOR":
                 constrains[0][i] = CFACTOR
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "DELTA":
                 constrains[0][i] = CDELTA
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "SUM":
                 constrains[0][i] = CSUM
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "IGNORED":
                 constrains[0][i] = CIGNORED
            elif constrains[0][i] == "IGNORE":
                 constrains[0][i] = CIGNORED
            else:
               #I should raise an exception
                #constrains[0][i] = 0
                raise ValueError("Unknown constraint %s" % constrains[0][i])
        if (constrains[0][i] == CQUOTED):
            raise ValueError("Linear fit cannot handle quoted constraint")
    # make a local copy of the function for an easy speed up ...
    model = model0
    parameters = numpy.asarray(parameters0, dtype=numpy.float64)
    if data0 is not None:
        selfx = numpy.array([x[0] for x in data0])
        selfy = numpy.array([x[1] for x in data0])
    else:
        selfx = xdata
        selfy = ydata
    selfweight = numpy.ones(selfy.shape,numpy.float64)
    # nr0 = len(selfy)
    if data0 is not None:
        nc =  len(data0[0])
    else:
        if sigmadata is None:
            nc = 2
        else:
            nc = 3
    if weightflag == 1:
        if nc == 3:
            #dummy = abs(data[0:nr0:inc,2])
            if data0 is not None:
                dummy = abs(numpy.array([x[2] for x in data0]))
            else:
                dummy = abs(numpy.array(sigmadata))
            selfweight = 1.0 / (dummy + numpy.equal(dummy,0))
            selfweight = selfweight * selfweight
        else:
            selfweight = 1.0 / (abs(selfy) + numpy.equal(abs(selfy),0))

    #linear fit, use at own risk since there is no check for the
    #function being linear on its parameters.
    #Only the fixed constrains are handled properly
    x=selfx
    y=selfy
    weight = selfweight
    iiter  = maxiter
    niter = 0
    newpar = parameters.copy()
    while (iiter>0):
        niter+=1
        chisq0, alpha0, beta,\
        n_free, free_index, noigno, fitparam, derivfactor  =ChisqAlphaBeta(
                                                 model,newpar,
                                                 x,y,weight,constrains,model_deriv=model_deriv,
                                                 linear=1)
        nr, nc = alpha0.shape
        fittedpar = numpy.dot(beta, inv(alpha0))
        #check respect of constraints (only positive is handled -force parameter to 0 and fix it-)
        error = 0
        for i in range(n_free):
            if constrains [0] [free_index[i]] == CPOSITIVE:
                if fittedpar[0,i] < 0:
                    #fix parameter to 0.0 and re-start the fit
                    newpar[free_index[i]] = 0.0
                    constrains[0][free_index[i]] = CFIXED
                    error = 1
        if error:continue
        for i in range(n_free):
            newpar[free_index[i]] = fittedpar[0,i]
        newpar=numpy.array(getparameters(newpar,constrains))
        iiter=-1
    yfit = model(newpar,x)
    chisq = (weight * pow(y-yfit , 2)).sum()
    sigma0 = numpy.sqrt(abs(numpy.diag(inv(alpha0))))
    sigmapar = getsigmaparameters(newpar,sigma0,constrains)
    lastdeltachi = chisq
    if not fulloutput:
        return newpar.tolist(), chisq/(len(y)-len(sigma0)), sigmapar.tolist()
    else:
        return newpar.tolist(), chisq/(len(y)-len(sigma0)), sigmapar.tolist(),niter,lastdeltachi

def RestreinedLeastSquaresFit(model0,parameters0,data0,maxiter,
                constrains0,weightflag,model_deriv=None,deltachi=0.01,fulloutput=0,
                                    xdata=None,
                                    ydata=None,
                                    sigmadata=None):
    #get the codes:
    # 0 = Free       1 = Positive     2 = Quoted
    # 3 = Fixed      4 = Factor       5 = Delta
    # 6 = Sum        7 = ignored
    constrains=[[],[],[]]
    for i in range(len(parameters0)):
        constrains[0].append(constrains0[0][i])
        constrains[1].append(constrains0[1][i])
        constrains[2].append(constrains0[2][i])
    for i in range(len(parameters0)):
        if type(constrains[0][i]) == type('string'):
            #get the number
            if   constrains[0][i] == "FREE":
                 constrains[0][i] = CFREE
            elif constrains[0][i] == "POSITIVE":
                 constrains[0][i] = CPOSITIVE
            elif constrains[0][i] == "QUOTED":
                 constrains[0][i] = CQUOTED
            elif constrains[0][i] == "FIXED":
                 constrains[0][i] = CFIXED
            elif constrains[0][i] == "FACTOR":
                 constrains[0][i] = CFACTOR
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "DELTA":
                 constrains[0][i] = CDELTA
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "SUM":
                 constrains[0][i] = CSUM
                 constrains[1][i] = int(constrains[1][i])
            elif constrains[0][i] == "IGNORED":
                 constrains[0][i] = CIGNORED
            elif constrains[0][i] == "IGNORE":
                 constrains[0][i] = CIGNORED
            else:
               #I should raise an exception
                #constrains[0][i] = 0
                raise ValueError("Unknown constraint %s" % constrains[0][i])
    # make a local copy of the function for an easy speed up ...
    model = model0
    parameters = numpy.asarray(parameters0, dtype=numpy.float64)
    if ONED:
        data = numpy.array(data0)
        x = data[1:2,0]
    fittedpar = parameters.copy()
    flambda = 0.001
    iiter = maxiter
    niter = 0
    if ONED:
        selfx = data [:,0]
        selfy = data [:,1]
    else:
        if data0 is not None:
            selfx = numpy.array([x[0] for x in data0])
            selfy = numpy.array([x[1] for x in data0])
        else:
            selfx = xdata
            selfy = ydata
    selfweight = numpy.ones(selfy.shape,numpy.float64)
    if ONED:
        nr0, nc = data.shape
    else:
        nr0 = len(selfy)
        if data0 is not None:
            nc =  len(data0[0])
        else:
            if sigmadata is None:
                nc = 2
            else:
                nc = 3

    if weightflag == 1:
            if nc == 3:
                #dummy = abs(data[0:nr0:inc,2])
                if ONED:
                    dummy = abs(data [:,2])
                else:
                    if data0 is not None:
                        dummy = abs(numpy.array([x[2] for x in data0]))
                    else:
                        dummy = abs(numpy.array(sigmadata))
                selfweight = 1.0 / (dummy + numpy.equal(dummy,0))
                selfweight = selfweight * selfweight
            else:
                selfweight = 1.0 / (abs(selfy) + numpy.equal(abs(selfy),0))
    n_param = len(parameters)
    index = numpy.arange(0,nr0,2)
    while (iiter > 0):
        niter = niter + 1
        if (niter < 2) and (n_param*3 < nr0):
                x=numpy.take(selfx,index)
                y=numpy.take(selfy,index)
                weight=numpy.take(selfweight,index)
        else:
                x=selfx
                y=selfy
                weight = selfweight

        chisq0, alpha0, beta,\
        n_free, free_index, noigno, fitparam, derivfactor  =ChisqAlphaBeta(
                                                 model,fittedpar,
                                                 x,y,weight,constrains,model_deriv=model_deriv)
        nr, nc = alpha0.shape
        flag = 0
        lastdeltachi = chisq0
        while flag == 0:
            newpar = parameters.copy()
            alpha = alpha0 + flambda * numpy.identity(nr) * alpha0
            deltapar = numpy.dot(beta, inv(alpha))
            pwork = numpy.zeros(deltapar.shape, numpy.float64)
            for i in range(n_free):
                if constrains [0] [free_index[i]] == CFREE:
                    pwork [0] [i] = fitparam [i] + deltapar [0] [i]
                elif constrains [0] [free_index[i]] == CPOSITIVE:
                    #abs method
                    pwork [0] [i] = fitparam [i] + deltapar [0] [i]
                    #square method
                    #pwork [0] [i] = (numpy.sqrt(fitparam [i]) + deltapar [0] [i]) * \
                    #                (numpy.sqrt(fitparam [i]) + deltapar [0] [i])
                elif constrains [0] [free_index[i]] == CQUOTED:
                    pmax=max(constrains[1] [free_index[i]],
                            constrains[2] [free_index[i]])
                    pmin=min(constrains[1] [free_index[i]],
                            constrains[2] [free_index[i]])
                    A = 0.5 * (pmax + pmin)
                    B = 0.5 * (pmax - pmin)
                    if (B != 0):
                        pwork [0] [i] = A + \
                                    B * numpy.sin(numpy.arcsin((fitparam[i] - A)/B)+ \
                                    deltapar [0] [i])
                    else:
                        print("Error processing constrained fit")
                        print("Parameter limits are",pmin,' and ',pmax)
                        print("A = ",A,"B = ",B)
                newpar [free_index[i]] = pwork [0] [i]
            newpar=numpy.array(getparameters(newpar,constrains))
            workpar = numpy.take(newpar,noigno)
            #yfit = model(workpar.tolist(), x)
            yfit = model(workpar,x)
            chisq = (weight * pow(y-yfit, 2)).sum()
            if chisq > chisq0:
                flambda = flambda * 10.0
                if flambda > 1000:
                    flag = 1
                    iiter = 0
            else:
                flag = 1
                fittedpar = newpar.copy()
                lastdeltachi = (chisq0-chisq)/(chisq0+(chisq0==0))
                if (lastdeltachi) < deltachi:
                    iiter = 0
                chisq0 = chisq
                flambda = flambda / 10.0
                #print "iter = ",iter,"chisq = ", chisq
        iiter = iiter - 1
    sigma0 = numpy.sqrt(abs(numpy.diag(inv(alpha0))))
    sigmapar = getsigmaparameters(fittedpar,sigma0,constrains)
    if not fulloutput:
        return fittedpar.tolist(), chisq/(len(yfit)-len(sigma0)), sigmapar.tolist()
    else:
        return fittedpar.tolist(), chisq/(len(yfit)-len(sigma0)), sigmapar.tolist(),niter,lastdeltachi

def ChisqAlphaBeta(model0, parameters, x,y,weight, constrains,model_deriv=None,linear=None):
    if linear is None:linear=0
    model = model0
    #nr0, nc = data.shape
    n_param = len(parameters)
    n_free = 0
    fitparam=[]
    free_index=[]
    noigno = []
    derivfactor = []
    for i in range(n_param):
        if constrains[0] [i] != CIGNORED:
            noigno.append(i)
        if constrains[0] [i] == CFREE:
            fitparam.append(parameters [i])
            derivfactor.append(1.0)
            free_index.append(i)
            n_free += 1
        elif constrains[0] [i] == CPOSITIVE:
            fitparam.append(abs(parameters[i]))
            derivfactor.append(1.0)
            #fitparam.append(numpy.sqrt(abs(parameters[i])))
            #derivfactor.append(2.0*numpy.sqrt(abs(parameters[i])))
            free_index.append(i)
            n_free += 1
        elif constrains[0] [i] == CQUOTED:
            pmax=max(constrains[1] [i],constrains[2] [i])
            pmin=min(constrains[1] [i],constrains[2] [i])
            if ((pmax-pmin) > 0) & \
               (parameters[i] <= pmax) & \
               (parameters[i] >= pmin):
                A = 0.5 * (pmax + pmin)
                B = 0.5 * (pmax - pmin)
                fitparam.append(parameters[i])
                derivfactor.append(B*numpy.cos(numpy.arcsin((parameters[i] - A)/B)))
                free_index.append(i)
                n_free += 1
            elif (pmax-pmin) > 0:
                print("WARNING: Quoted parameter outside boundaries")
                print("Initial value = %f" % parameters[i])
                print("Limits are %f and %f" % (pmin, pmax))
                print("Parameter will be kept at its starting value")
    fitparam = numpy.array(fitparam, numpy.float64)
    alpha = numpy.zeros((n_free, n_free),numpy.float64)
    beta = numpy.zeros((1,n_free),numpy.float64)
    delta = (fitparam + numpy.equal(fitparam,0.0)) * 0.00001
    nr  = x.shape[0]
    ##############
    # Prior to each call to the function one has to re-calculate the
    # parameters
    pwork = parameters.copy()
    for i in range(n_free):
        pwork [free_index[i]] = fitparam [i]
    newpar = getparameters(pwork.tolist(),constrains)
    newpar = numpy.take(newpar,noigno)
    if n_free == 0:
        raise ValueError("No free parameters to fit")
    for i in range(n_free):
        if model_deriv is None:
            #pwork = parameters.copy()
            pwork [free_index[i]] = fitparam [i] + delta [i]
            newpar = getparameters(pwork.tolist(),constrains)
            newpar=numpy.take(newpar,noigno)
            f1 = model(newpar, x)
            pwork [free_index[i]] = fitparam [i] - delta [i]
            newpar = getparameters(pwork.tolist(),constrains)
            newpar=numpy.take(newpar,noigno)
            f2 = model(newpar, x)
            help0 = (f1-f2) / (2.0 * delta [i])
            help0 = help0 * derivfactor[i]
            pwork [free_index[i]] = fitparam [i]
            #removed I resize outside the loop:
            #help0 = numpy.resize(help0,(1,nr))
        else:
            help0=model_deriv(pwork,free_index[i],x)
            help0 = help0 * derivfactor[i]

        if i == 0 :
            deriv = help0
        else:
            deriv = numpy.concatenate((deriv,help0), 0)
    #line added to resize outside the loop
    deriv=numpy.resize(deriv,(n_free,nr))
    if linear:
        pseudobetahelp = weight * y
    else:
        newpar = getparameters(pwork.tolist(),constrains)
        newpar = numpy.take(newpar,noigno)
        yfit = model(newpar, x)
        deltay = y - yfit
        help0 = weight * deltay
    for i in range(n_free):
        derivi = numpy.resize(deriv [i,:], (1,nr))
        if linear:
            if i==0:
                beta = numpy.resize(numpy.sum((pseudobetahelp * derivi),1),(1,1))
            else:
                beta = numpy.concatenate((beta, numpy.resize(numpy.sum((pseudobetahelp * derivi),1),(1,1))), 1)
        else:
            help1 = numpy.resize(numpy.sum((help0 * derivi),1),(1,1))
            if i == 0:
                beta = help1
            else:
                beta = numpy.concatenate((beta, help1), 1)
        help1 = numpy.inner(deriv,weight*derivi)
        if i == 0:
            alpha = help1
        else:
            alpha = numpy.concatenate((alpha, help1),1)
    if linear:
        #not used
        chisq = 0.0
    else:
        chisq = (help0 * deltay).sum()
    return chisq, alpha, beta, \
           n_free, free_index, noigno, fitparam, derivfactor

def getparameters(parameters,constrains):
    # 0 = Free       1 = Positive     2 = Quoted
    # 3 = Fixed      4 = Factor       5 = Delta
    newparam=[]
    #first I make the free parameters
    #because the quoted ones put troubles
    for i in range(len(constrains [0])):
        if constrains[0][i] == CFREE:
            newparam.append(parameters[i])
        elif constrains[0][i] == CPOSITIVE:
            #newparam.append(parameters[i] * parameters[i])
            newparam.append(abs(parameters[i]))
        elif constrains[0][i] == CQUOTED:
            newparam.append(parameters[i])
        elif abs(constrains[0][i]) == CFIXED:
            newparam.append(parameters[i])
        else:
            newparam.append(parameters[i])
    for i in range(len(constrains [0])):
        if constrains[0][i] == CFACTOR:
            newparam[i] = constrains[2][i]*newparam[int(constrains[1][i])]
        elif constrains[0][i] == CDELTA:
            newparam[i] = constrains[2][i]+newparam[int(constrains[1][i])]
        elif constrains[0][i] == CIGNORED:
            newparam[i] = 0
        elif constrains[0][i] == CSUM:
            newparam[i] = constrains[2][i]-newparam[int(constrains[1][i])]
    return newparam

def getsigmaparameters(parameters,sigma0,constrains):
    # 0 = Free       1 = Positive     2 = Quoted
    # 3 = Fixed      4 = Factor       5 = Delta
    n_free = 0
    sigma_par = numpy.zeros(parameters.shape,numpy.float64)
    for i in range(len(constrains [0])):
        if constrains[0][i] == CFREE:
            sigma_par [i] = sigma0[n_free]
            n_free += 1
        elif constrains[0][i] == CPOSITIVE:
            #sigma_par [i] = 2.0 * sigma0[n_free]
            sigma_par [i] = sigma0[n_free]
            n_free += 1
        elif constrains[0][i] == CQUOTED:
            pmax = max(constrains [1] [i], constrains [2] [i])
            pmin = min(constrains [1] [i], constrains [2] [i])
            # A = 0.5 * (pmax + pmin)
            B = 0.5 * (pmax - pmin)
            if (B > 0) & (parameters [i] < pmax) & (parameters [i] > pmin):
                sigma_par [i] = abs(B * numpy.cos(parameters[i]) * sigma0[n_free])
                n_free += 1
            else:
                sigma_par [i] = parameters[i]
        elif abs(constrains[0][i]) == CFIXED:
            sigma_par[i] = parameters[i]
    for i in range(len(constrains [0])):
        if constrains[0][i] == CFACTOR:
            sigma_par [i] = constrains[2][i]*sigma_par[int(constrains[1][i])]
        elif constrains[0][i] == CDELTA:
            sigma_par [i] = sigma_par[int(constrains[1][i])]
        elif constrains[0][i] == CSUM:
            sigma_par [i] = sigma_par[int(constrains[1][i])]
    return sigma_par

def fitpar2par(fitpar,constrains,free_index):
    newparam = []
    for i in range(len(constrains [0])):
        if constrains[0][free_index[i]] == CFREE:
            newparam.append(fitpar[i])
        elif constrains[0][free_index[i]] == CPOSITIVE:
            newparam.append(fitpar[i] * fitpar [i])
        elif abs(constrains[0][free_index[i]]) == CQUOTED:
            pmax=max(constrains[1] [free_index[i]],constrains[2] [free_index[i]])
            pmin=min(constrains[1] [free_index[i]],constrains[2] [free_index[i]])
            A = 0.5 * (pmax + pmin)
            B = 0.5 * (pmax - pmin)
            newparam.append(A + B * numpy.sin(fitpar[i]))
    return newparam

def gauss(param0,t0):
    param=numpy.array(param0)
    t=numpy.array(t0)
    dummy=2.3548200450309493*(t-param[3])/param[4]
    return param[0] + param[1] * t + param[2] * myexp(-0.5 * dummy * dummy)

def myexp(x):
    # put a (bad) filter to avoid over/underflows
    # with no python looping
    return numpy.exp(x*numpy.less(abs(x),250))-1.0 * numpy.greater_equal(abs(x),250)


def test(npoints):
    xx = numpy.arange(npoints)
    xx=numpy.resize(xx,(npoints,1))
    #yy = 1000.0 * exp (- 0.5 * (xx * xx) /15)+ 2.0 * xx + 10.5
    yy = gauss([10.5,2,1000.0,20.,15],xx)
    yy=numpy.resize(yy,(npoints,1))
    sy = numpy.sqrt(abs(yy))
    sy=numpy.resize(sy,(npoints,1))
    data = numpy.concatenate((xx, yy, sy),1)
    parameters = [0.0,1.0,900.0, 25., 10]
    stime = time.time()
    #easier to handle
    fittedpar, chisq, sigmapar = LeastSquaresFit(gauss,parameters,
                                                 xdata=xx.reshape((-1,)),
                                                 ydata=yy.reshape((-1,)),
                                                 sigmadata=sy.reshape((-1,)))
    etime = time.time()
    print("Took ",etime - stime, "seconds")
    print("chi square  = ",chisq)
    print("Fitted pars = ",fittedpar)
    print("Sigma pars  = ",sigmapar)


if __name__ == "__main__":
  import profile
  profile.run('test(10000)',"test")
  import pstats
  p=pstats.Stats("test")
  p.strip_dirs().sort_stats(-1).print_stats()
