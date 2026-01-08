#/*##########################################################################
#
#
# Copyright (c) 2002-2023 European Synchrotron Radiation Facility
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
__author__ = "A. Mirone - ESRF"
__license__ = "MIT"
import math
sparsamodulo=0
PARALLEL=0

import numpy
import numpy.linalg
try:
    import numpy.core._dotblas as dotblas
except ImportError:
    dotblas = numpy
import random

######################################
## interfaccia per sparse
# __class__
# static    .getClass4Vect()
# object    .gohersch()
# object    .goherschMax()
# object    .goherschMin()

######################################
## interfaccia per vettori
# __class__ === class4vect
# class Vector(dim)
# object.set_value(n,v)
# object.set_all_random(v)

class LanczosNumericMatrix(object):
    tipo=numpy.float64
    def __init__(self, mR):
        self.mR=mR
        self.dim= self.mR[0].shape[0]
        self.shift=0.0

    def Moltiplica(self,res,v):
        if( len(self.mR)==1 ):
            res.vr[:]+=dotblas.dot(self.mR[0],v.vr)
        else:
            res.vr[:]+=dotblas.dot(self.mR[0],dotblas.dot(self.mR[1],v.vr))

        if( self.shift !=0.0):
          res.add_from_vect_with_fact(v,self.shift)

    def trasforma(self, fattore, addendo):
        self.shift+=addendo
        if( fattore!=1):
            self.mR[0][:]=self.mR[0]*numpy.array([fattore], self.tipo)


    def getClass4Vect(self):
        return LanczosNumericVector


class LanczosNumericVector(object):
    tipo=numpy.float64
    def __init__(self, *dim):
        if( dim!=(0,) ):
            self.vr=numpy.zeros(dim,self.tipo)
        else:
            pass

    def __getitem__(self, i):
        res=LanczosNumericVector(0)
        res.vr=self.vr[i]
        return res

    def mat_mult(self, evect , q):
        self.vr[:evect.shape[0]]=dotblas.dot(evect.astype(self.tipo),q.vr[:evect.shape[1]])

    def dividebyarray(self,prec):
        self.vr[:]=self.vr/prec

    def multbyarray(self,prec):
        self.vr[:]=self.vr*prec

    def len(self):
        return len(self.vr)

    def copy(self):
        duma=numpy.array(self.vr)
        res=numpy.Vector(0)
        res.vr=duma
        return res

    def copy_to_a_from_b(self,b):
        self.vr[:]=b.vr

    def set_value(self, n, val):
        self.vr[n]=val

    def set_to_zero(self):
        self.vr[:]=0

    def set_to_one(self):
        self.vr[:]=1


    def set_all_random(self, v):
        self.vr[:]=[random.random() for i in range(len(self.vr)) ]



    def scalare(self,b         ):
        resR =numpy.sum(self.vr*b.vr)
        return resR

    def sqrtscalare(self,b):
        assert( self is b)
        return numpy.sqrt( self.scalare(b) )

    def normalizzaauto(self):
        norma = self.sqrtscalare(self)
        self.vr[:]=self.vr/norma


    def normalizza(self,norma):
        self.vr.normalizza(norma)


    def rescale(self,fact):
      if(fact==0.0):
        self.set_to_zero()
      else:
        norma=1.0/fact
        self.normalizza(norma)


    def add_from_vect(self, b):
        self.vr[:]=self.vr+b.vr


    def add_from_vect_with_fact(self, b, fact):
        self.vr[:]=self.vr+numpy.array([fact],self.tipo)*b.vr


def REAL(a):
    if( type(a)==type(1.0+1.0j) ):
        return a.real
    else:
        return a

def Real(x):
    if( x.__class__ == complex):
        return x.real
    else:
        return x

class Lanczos:
    dump_count=0;
    countdumpab=0

    def __init__(self, sparse, metrica=None, tol=1.0e-15):

        self.matrice=sparse
        self.metrica=metrica

        self.class4sparse = sparse.__class__
        try:
            self.class4vect   = self.class4sparse.getClass4Vect()
        except Exception:
            self.class4vect   = sparse.getClass4Vect()


        self.nsteps = 0
        self.dim=self.matrice.dim

        self.q = None

        self.alpha = None
        self.beta = None
        self.omega=None

        self.tol = tol
        self.maxIt = 50

        self.old = False




    def diagoCustom(self, minDim=5, shift=None):

        if shift is  None:
            self.matrice.gohersch()
            shift = - self.matrice.goherschMax()
        self.cerca(minDim, shift)

        for ne in range(len(self.eval)):
            self.eval[ne] =  self.eval[ne] - shift

    def passeggia(self, k, m, start, gram=0, NT=4):

        if k<0 or m>self.nsteps:
            print("k = ",k," m = ",m," nsteps = ",self.nsteps)
            print("Something wrong in passe k<0 or m>nsteps")
            raise ValueError(\
                "Lanczos. Something wrong in passe k<0 or m>nsteps")

        sn   = math.sqrt(float(self.dim))
        eu   = 1.1e-16
        eusn = eu*sn

        if k==0:


            self.class4vect.copy_to_a_from_b(self.q[0],start)

            if self.metrica is None:
                self.q[0].normalizzaauto()
            else:
                self.tmp4met.set_to_zero()
                self.metrica.Moltiplica( self.tmp4met , self.q[0] )
                tmpfat = math.sqrt(REAL(self.class4vect.scalare(self.q[0] , self.tmp4met)))
                self.q[0].normalizza(tmpfat)



            # self.q[0].dumptofile("q_0")



        p= self.class4vect(self.dim)

        for i in range(k,m):
            p.set_to_zero()
            # self.q[i].dumptofile("qbef_"+str(self.dump_count) )

            self.matrice.Moltiplica(p,self.q[i])


            if self.metrica is not None:

                self.tmp4met.set_to_zero()
                self.metrica.Moltiplica(self.tmp4met , self.q[i])
                self.alpha[i] = REAL(self.class4vect.scalare(p , self.tmp4met))

            else:
                self.alpha[i] = REAL(self.class4vect.scalare(p , self.q[i]))

            # p.dumptofile("p"+str(self.dump_count) )
            self.dump_count+=1


            if i==k:
                p.add_from_vect_with_fact( self.q[k] ,   -self.alpha[k]     )
                for l in range(k):
                    p.add_from_vect_with_fact( self.q[l] ,  -self.beta[l]     )

            else:
                # self.q[i].dumptofile("q_i"+str(self.dump_count) )
                # self.q[i-1].dumptofile("q_im1"+str(self.dump_count) )
                p.add_from_vect_with_fact(self.q[i]  ,    -self.alpha[i]    )
                p.add_from_vect_with_fact(self.q[i-1]  ,  -self.beta[i-1]   )


            # p.dumptofile("pp"+str(self.dump_count) )
            self.dump_count+=1


            if self.metrica is not None:
                self.tmp4met.set_to_zero()
                self.metrica.Moltiplica(self.tmp4met , p)
                self.beta[i] = math.sqrt(REAL(self.class4vect.scalare(p , self.tmp4met)))

            else:
                self.beta[i]=self.class4vect.sqrtscalare(p,p)


            self.omega[i,i]=1.

            max0 = 0.0

            if self.beta[i] != 0:  #and  not scipy.isnan(self.beta[i]):
                for j in range(i+1):
                    self.omega[i+1,j] = eusn



                    if j<k:
                        add = 2 * eusn + abs(self.alpha[j]-self.alpha[i]) \
                              * abs(self.omega[i,j])
                        if i!=k:
                            add += self.beta[j]*abs(self.omega[i,k])
                        if i>0 and j!=i-1:
                            add += self.beta[i-1]*abs(self.omega[i-1,j])
                        self.omega[i+1,j] += add / self.beta[i]


                    elif j==k :
                        add = 2 * eusn + abs(self.alpha[j]-self.alpha[i]) \
                              * abs(self.omega[i,j])

                        for w in range(k):
                            add += self.beta[w]*abs(self.omega[i,w])

                        if i!=k+1:
                            add += self.beta[k]*abs(self.omega[i,k+1])
                        if i>0 and i!=k+1:
                            add += self.beta[i-1]*abs(self.omega[i-1,k])

                        self.omega[i+1,j] += add / self.beta[i]



                    elif j<i :

                        add = 2 * eusn + abs(self.alpha[j]-self.alpha[i]) \
                              * abs(self.omega[i,j])

                        if i!=j+1:
                            add += self.beta[j]*abs(self.omega[i,j+1])

                        if i>0 and j>0:
                            add += self.beta[j-1]*abs(self.omega[i-1,j-1])

                        if i>0 and i!=j+1:
                            add += self.beta[i-1]*abs(self.omega[i-1,j])

                        self.omega[i+1,j] += add / self.beta[i]



                    else:

                        add = eusn

                        if i>0:
                            add += self.beta[i-1]*abs(self.omega[i,i-1] )

                        self.omega[i+1,j] += add / self.beta[i]


                    self.omega[j,i+1] = self.omega[i+1,j]

                    max0 += self.omega[i+1,j]**2
            if self.beta[i]==0 or max0>eu or gram :
##            if self.beta[i]==0 or max0>0. :

                if i>0:
                    #print " GRAMO  self.beta[i]==0 or max0>eu and i>0", i,"  ", self.dump_count
                    self.GramSchmidt(self.q[i],i, NT)


                    if self.metrica is None:
                        self.q[i].normalizzaauto()
                    else:
                        self.tmp4met.set_to_zero()
                        self.metrica.Moltiplica( self.tmp4met , self.q[i] )
                        tmpfat = math.sqrt(REAL(self.class4vect.scalare(self.q[i] , self.tmp4met)))
                        self.q[i].normalizza(tmpfat)


                    p.set_to_zero()

                    self.matrice.Moltiplica(p, self.q[i])

                    if self.metrica is not None:

                        self.tmp4met.set_to_zero()
                        self.metrica.Moltiplica(self.tmp4met , self.q[i])
                        self.alpha[i] = REAL(self.class4vect.scalare(p , self.tmp4met))

                    else:
                        self.alpha[i] = REAL(self.class4vect.scalare(p , self.q[i]))



                #print " GRAMO bis ", i
##                print self.alpha[:20]
##                raise " OK "


                if self.metrica is None:

                    self.GramSchmidt(p,i+1,NT)

                    self.beta[i] = self.class4vect.sqrtscalare(p,p)
                    p.normalizzaauto()
                else:

                    # p.add_from_vect_with_fact( self.q[i] ,   -self.alpha[i]     )
                    # p.add_from_vect_with_fact( self.q[i-1] ,   -self.beta[i-1]     )

                    self.GramSchmidt(p,i+1,NT)

                    self.tmp4met.set_to_zero()
                    self.metrica.Moltiplica(self.tmp4met , p)
                    tmpfat = math.sqrt(REAL(self.class4vect.scalare(p , self.tmp4met)))
                    self.beta[i] = tmpfat
                    p.normalizza(tmpfat)




                if i>0:
                    condition = eu * \
                                math.sqrt(self.dim * (self.alpha[i]**2+\
                                                      self.beta[i-1]**2))
                else:
                    condition = eu * math.sqrt(self.dim * (self.alpha[i]**2))


                if self.beta[i]< condition:

                    self.beta[i]=0.

                    p.set_all_random(1.0)

                    self.GramSchmidt(p,i+1)

                    if self.metrica is None:
                        p.normalizzaauto()
                    else:
                        self.tmp4met.set_to_zero()
                        self.metrica.Moltiplica( self.tmp4met , p )
                        tmpfat = math.sqrt(REAL(self.class4vect.scalare(p , self.tmp4met)))
                        p.normalizza(tmpfat)



                for l in range(i) :
                    self.omega[i,l]=self.omega[l,i]=eusn
                for l in range(i+1):
                    self.omega[i+1,l]=self.omega[l,i+1]=eusn

            else:

                if self.metrica is None:
                    p.normalizzaauto()
                else:
                    self.tmp4met.set_to_zero()
                    self.metrica.Moltiplica( self.tmp4met , p )
                    tmpfat = math.sqrt(REAL(self.class4vect.scalare(p , self.tmp4met)))
                    p.normalizza(tmpfat)


                # p.dumptofile("normprelude"+str(self.dump_count))

            self.class4vect.copy_to_a_from_b(self.q[i+1],p)



    def GramSchmidt(self, vect , n, NT=4):
        for h in range(NT):

            if self.metrica is None :
                for i in range(n):
                    s=self.class4vect.scalare( self.q[i], vect)
                    vect.add_from_vect_with_fact(self.q[i],-s)
            else:
                self.tmp4met.set_to_zero()
                self.metrica.Moltiplica(self.tmp4met, vect)
                for i in range(n):

                    s=self.class4vect.scalare( self.q[i], self.tmp4met)
                    vect.add_from_vect_with_fact(self.q[i],-s)



    def allocaMemory(self):
        self.alpha = numpy.zeros(self.nsteps,numpy.float64)
        self.beta  = numpy.zeros(self.nsteps,numpy.float64)
        self.omega = numpy.zeros((self.nsteps+1,self.nsteps+1),numpy.float64)
        self.evect = numpy.zeros((self.nsteps,self.nsteps),numpy.float64)
        self.eval  = numpy.zeros((self.nsteps),numpy.float64)
        self.oldalpha = numpy.zeros((self.nsteps),numpy.float64)

        self.q=self.class4vect(self.nsteps+1,self.dim)
        if self.metrica is not None:
            self.tmp4met = self.class4vect( self.dim )


    def cerca(self, nd, shift):

        self.shift=shift



        self.matrice.trasforma(1.0, shift)


        m = min(4*nd, self.dim)

        self.nsteps = m

        self.allocaMemory()

        vect_init = self.class4vect(self.dim)
        # vect_init.set_value(0,1.0)

        vect_init.set_all_random(1.0)
        # vect_init.set_to_one()



        k=0
        nc=0
        self.passeggia(k,m,vect_init)

        while nc<nd :
            #print " DIAGONALIZZAZIONE "
            self.diago(k,m)

            nc = self.converged(m)

            if k and not numpy.any(abs(self.beta[:k])>self.tol) :
                break

            if (nc+2*nd) >= m:
                k=m-1
            else:
                k=nc+2*nd

            #print "KKKKKKKKK  " ,  k
            self.ricipolla(k,m)
            self.countdumpab+=1

            #print " k,m , dim", k, m, self.dim
            # return m # sentinell

            self.passeggia(k,m,self.q[m])

        if m==self.dim:
            return m
        else:
            return k


    def converged(self, m):

        for j in range(1,m):
            for i in range(m-j):
                if abs(self.eval[i]) < abs(self.eval[i+1]):
                    self.eval[i],self.eval[i+1]=self.eval[i+1],self.eval[i]
                    self.evect[i:i+2]= numpy.array(self.evect[i+1],self.evect[i])


        # print "eval", self.eval[0:m]
        res = 0
        if self.old:
            while res<m:
                #print self.oldalpha[res]
                if (abs(self.eval[res]-self.oldalpha[res])\
                    /abs(self.oldalpha[res])>self.tol):
                    break
                res+=1
        else:
            self.old=True

        self.oldalpha[0:m]=self.eval[0:m]

        return res

    def ricipolla(self, k,m):

        #print "k,m",k,m
        self.alpha[0:k]= self.eval[0:k]


        self.beta[0:k] = self.beta[m-1]*self.evect[0:k,m-1]
        #print "beta beta",self.beta,self.beta[m-1],self.evect[0:k,m-1]

        # E = self.evect[0:k,0:m].copy()

        a=self.class4vect(k,  self.dim )

        #print " LANCIO mat MULT "

        self.class4vect.mat_mult(a, self.evect[0:k,0:m] , self.q)

        for i in range(k):
            a[i].normalizzaauto()
            self.class4vect.copy_to_a_from_b( self.q[i] , a[i]     )

        a=None

        self.class4vect.copy_to_a_from_b(self.q[k]  ,  self.q[m] )


        o = self.omega[0:m,0:m].copy()


        o = dotblas.dot(o, numpy.transpose(self.evect))


        for i in range(k):
            self.omega[i,k]=self.omega[k,i]=o[i,k]


        o = dotblas.dot(self.evect,o)


        self.omega[0:k,0:k]=o[0:k,0:k]

    def diago(self, k, m):
        mat = numpy.zeros([m,m], numpy.float64)
        mat = mat.reshape(m * m)
        mat[0:m*m:m+1] = self.alpha
        mat[k*m+k+1:m*m:m+1] =self.beta[k:m-1]
        mat[(k+1)*m+k:m*m:m+1] =self.beta[k:m-1]
        mat = mat.reshape(m,m)
        mat[   k     ,0:k  ] = self.beta[:k]
        mat[   0:k, k ] = self.beta[:k]
        self.eval,self.evect = numpy.linalg.eigh(mat)


def solveEigenSystem( S_base , nsearchedeigen, shift=None, metrica=None,  tol=1.0e-15):
    lnczs=Lanczos( S_base , metrica=metrica, tol=tol)
    lnczs.diagoCustom(minDim=nsearchedeigen, shift=shift)
    return lnczs.eval, lnczs.q
