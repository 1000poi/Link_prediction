# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 20:41:54 2015

@author: Timber
"""
import functools
import numpy as np
from scipy.optimize import fmin_bfgs, fmin_l_bfgs_b

# ***function: iterPageRank
# this function takes initial node probabilities and a 
# transition matrix then use power iteration to find 
# the PageRank of nodes
def iterPageRank(pp, trans):
    ppnew = np.dot(pp, trans)
    while not(np.allclose(pp, ppnew)):
        pp = ppnew
        ppnew = np.dot(pp, trans)
    return ppnew


# ***function: genCopyGraph
# generate an undirected random graph with copyig model
# the generated graph has the property of preferencial attachment
# an edge list is returned
def genCopyGraph(nnodes, alpha):
    # since the copy model starts with a triad, the input number of 
    # nodes should be larger than 3
    if nnodes <= 3:
        print "Number of nodes should be larger than 3..."
        return
    # inital setting with a triad
    degrees = np.repeat(2, 3)
    edges = [(0, 1), (0, 2), (1, 2)]
    # growing the graph node by node
    for i in range(3, nnodes):
        # add three edges for the new node
        for nedge in range(3):
            if np.random.rand() < alpha:
                # uniformly choose node to connect
                tar = np.random.choice(i, 1)[0]
                while (tar, i) in edges:
                    tar = np.random.choice(i, 1)[0]
                edges.append((tar, i))
                degrees[tar] += 1
            else:
                # select target to connect according to degree
                sDeg = sum(degrees)
                tar = -1
                firstRound = True
                while (tar, i) in edges or firstRound:
                    firstRound = False
                    randPick = np.random.randint(1, sDeg+1)
                    accu = 0
                    for j in range(len(degrees)):
                        accu += degrees[j]
                        if randPick <= accu:
                            tar = j
                            break
                        
                edges.append((tar, i))
                degrees[tar] += 1
        
        degrees = np.append(degrees, 3)
    return [edges, degrees]


# ***function: calStrength
# return edge strength calculated by logistic function
# the inputs are two vectors, features and the parameters
def calStrength(features, beta):
    #return np.exp(np.dot(features, beta))
	# use logistic strength function to prevent potential overflow or under flow
	# of floating point numbers
	return  1.0 / (1+ np.exp(-1 * np.dot(features, beta) ))


# ***function: strengthDiff
# calculate an returns the gradient of strength functioin with 
# respect to beta, the returned value is a vector
def strengthDiff(features, beta):
	# return a vector of gradient of strength
	diff = []
	denom = calStrength(features, beta) ** 2
	numer_exp = np.exp(-1 * np.dot(features, beta))
	for k in range(len(beta)):
		diff.append(-1 * features[k] * numer_exp * denom)
	return diff


# ***function: genTrans
# this function takes in a graph (edge list and number of nodes), 
# node features, source node, and alpha/beta parameters to generate
# a random walk transition matrix.
# transition probabilities are determined by edge strength
# beta is the parameter in the edge strength function
# alpha is the teleportation rate back to the source node
def genTrans(nnodes, g, features, s, alpha, beta):
    # feature is supplied in per-edge manner
    # the transition matrix is created with teleportation
    trans = np.zeros((nnodes, nnodes))
    for i in range(len(g)):
        #strength = calStrength(np.asarray(features[g[i][0],])*np.asarray(features[g[i][1],])
        #, beta)
        strength = calStrength(features[g[i][0]][g[i][1]], beta)
        trans[g[i][0], g[i][1]] = strength
        trans[g[i][1], g[i][0]] = strength
    
    # normalize the transition matrix
    for i in range(nnodes):
        tempSum = sum(trans[i,])
        if tempSum > 0:
            trans[i,] = map(lambda x: x/tempSum, trans[i, ])
    
    # create the one matrix
    one = np.zeros((nnodes, nnodes))
    for i in range(nnodes):
        one[i, s] = 1
        
    # combine the regular transition matrix and the one matrix
    trans = (1-alpha)*trans + alpha*one
    
    return trans

# ***function: genTrans_plain
# this function construct transition matrix for random walk
# with unweighted edge strenght, i.e. each eade has strength 1
def genTrans_plain(nnodes, g, s, alpha):
    trans = np.zeros((nnodes, nnodes))
    for i in range(len(g)):
        trans[g[i][0], g[i][1]] = 1
        trans[g[i][1], g[i][0]] = 1
    
    # normalize the transition matrix
    for i in range(nnodes):
        tempSum = sum(trans[i,])
        if tempSum > 0:
            trans[i,] = map(lambda x: x/tempSum, trans[i, ])
    
    # create the one matrix
    one = np.zeros((nnodes, nnodes))
    for i in range(nnodes):
        one[i, s] = 1
        
    # combine the regular transition matrix and the one matrix
    trans = (1-alpha)*trans + alpha*one
    
    return trans


def genFeatures(nnodes, g, features):
    #fea = np.zeros((nnodes, nnodes))
    fea = [[ [] for x in range(nnodes) ] for x in range(nnodes) ]
    # create a feature matrix
    for i in range(len(g)):
        fea[g[i][0]][g[i][1]] = features[i]
        fea[g[i][1]][g[i][0]] = features[i]
    
    return fea


############################################
############################################
## Below are the functions for learning process

# ***function: iterPageDiff
# this function use power-iteration-like method to return the gradient of 
# Supervised Random Walk pagerank scores
def iterPageDiff(pdiff, p, trans, transdiff):
    pdiffnew = np.dot(pdiff, trans) + np.dot(p, transdiff)
    while not(np.allclose(pdiff, pdiffnew)):
        pdiff = pdiffnew
        pdiffnew = np.dot(pdiff, trans) + np.dot(p, transdiff)
    return pdiffnew[0]


# ***function: diffQelem
# this function is called by diffQ, return the (i, j)-th element of the 
# derivative of transition matrix with respect to k-th element of beta
def diffQelem(features, beta, trans_p, alpha, row, col, k):
    # calculates the element value of transition matrix's differentiation
    # first calculate the denominator part    
    denom = 0
    xdenom = 0
    for j in range(int(np.shape(trans_p)[1])):
        if trans_p[row, j] > 0:
            # should check on the original version of transition matrix, 
            # because teleportation does not contribute to gradient
            #temp = calStrength(np.asarray(features[row,])*np.asarray(features[j,])
            #, beta)
            temp = calStrength(features[row][j], beta)
            denom += temp
            #xdenom += (np.asarray(features[row,])*np.asarray(features[j,]))[k] * temp
            xdenom += features[row][j][k] * temp
    #curFeat = np.asarray(features[row,])*np.asarray(features[col,])
    curFeat = features[row][col]
    strength = calStrength(curFeat, beta)
    
    elem = (1-alpha)*(curFeat[k]*strength*denom - strength*xdenom) / (denom**2)
    
    return elem


# ***function: diffQ
# given a Supervised Random Walk transition matrix, return the derivative of 
# transition matrix with respect to the k-th element in parameter beta
def diffQ(features, beta, trans_p, alpha):
    
    nnodes = int(np.shape(trans_p)[0])
	
    # first compute the (unnormalized) edge strength matrix and the gradient matrix
    sMat = np.zeros((nnodes, nnodes))
    for i in range(int(np.shape(trans_p)[0])):
        for j in range(i, int(np.shape(trans_p)[1])):
            if trans_p[i, j] > 0:
                strength = calStrength(features[i][j], beta)
                sMat[i, j] = strength
                sMat[j, i] = strength
    
    gradS = []
    for i in range(len(beta)):
        gradS.append(np.zeros((nnodes, nnodes)))    
    
    
	# gradQ is the gradient of strength matrix
	# for a matrix of gradient of strength, each element in the matrix is a vecotr
	#gradS = [[ [] for x in range(nnodes) ] for x in range(nnodes) ]
    for i in range(int(np.shape(trans_p)[0])):
        for j in range(int(np.shape(trans_p)[1])):
            if trans_p[i, j] > 0:
                gradTemp = strengthDiff(features[i][j], beta)
                #gradS[i][j] = strengthDiff(features[i][j], beta)
                for k in range(len(beta)):
                    gradS[k][i, j] = gradTemp[k]
    
    
    # compute the gradient of transition matrix
    # a list of matrices is computed, with k-th element in the list be 
    # the derivative of transition matrix with respect to the k-th 
    # element in parameter vecotor beta
        
    qp = []
    for i in range(len(beta)):
        qp.append(np.zeros((nnodes, nnodes)))
    
    for i in range(int(np.shape(trans_p)[0])):
        # for each row in the gradient matrix, some common factors can be 
        # computed first
        sumStrength = 0
        sumDiff = [0] * len(beta)
        for j in range(int(np.shape(trans_p)[1])):
            if trans_p[i, j] > 0:
                sumStrength += sMat[i, j]
                for k in range(len(beta)):
                    sumDiff[k] += gradS[k][i, j]
        # individual entries can then be computed
        
        for j in range(int(np.shape(trans_p)[1])):
            if trans_p[i, j] > 0:
                for k in range(len(beta)):
                    qp[k][i, j] = (sumStrength ** -2)*( gradS[k][i, j]*sumStrength -
                    sMat[i, j]*sumDiff[k])*(1 - alpha)
        
    """
    #qp = np.zeros(np.shape(trans_p))
    #for i in range(int(np.shape(trans_p)[0])):
		# many factors in diffQ is identical for the same row, compute the common items first
		
		
        for j in range(int(np.shape(trans_p)[1])):
            # should check on the original version of transition matrix, 
            # because teleportation does not contribute to gradient
            if trans_p[i, j] > 0:
                qp[i, j] = diffQelem(features, beta, trans_p, alpha, i, j, k)
		"""
    
    return qp


# ***function: costFunc
# this is the cost function in learning process
# given the page rank socres of two nodes, one in future link set
# one in no-link set, and an offset parameter, the cost function value is 
# returned. (return value is a scalar)
def costFunc(pl, pd, offset):
    return (max(0, pl - pd + offset))**2


# ***function: costDiff
# this is the gradient of cost function
# given the page rank socres of two nodes, one in future link set
# one in no-link set, and an offset parameter, the gradient of cost function 
# is returned. (return value is a scalar)
def costDiff(pl, pd, offset):
    return 2.0*(max(0, pl - pd + offset))


# ***function: minObj
# this is the object function to be minimized in the learning process
# the future link set and no-link from training set should be given, also, 
# parameters in the learning process and the graph of training set should be 
# given.
# Supervised Random Walk pagerank scores are calculated for each node based on 
# input training graph and features, then cost function value is calculated 
# according to the derived pagerank scores.
# (return value is a scalar)
def minObj(Dset, Lset, offset, lam, nnodes, g, features, source, alpha, beta):
    # calculate PageRank according to features and beta values
    
    # transform input features into matrix form
    features_m = genFeatures(nnodes, g, features)
    
    trans = genTrans(nnodes, g, features_m, source, alpha, beta)
    pp = np.repeat(1.0/nnodes, nnodes)
    pgrank = iterPageRank(pp, trans)
    
    # compute cost from the generated PageRank value
    cost = 0
    for d in Dset:
        for l in Lset:
            cost += costFunc(pgrank[l], pgrank[d], offset)
    penalty = lam * np.dot(beta, beta)
    
    return (cost + penalty)


# ***function: objDiff
# this is the gradient of the object function
# given training graph, training sets and parameters, gradient of the object 
# function is returned. This is required in gradient descent and BFGS optimization
# processes.
# Supervised Random Walk pagerank is calculated then served as a basis to compute
# the gradient of pagerank scores. Gradient of pagerank scores are derived by 
# power-iteration-like method.
# (return value is a vector with the dimension of parameter beta)
def objDiff(Dset, Lset, offset, lam, nnodes, g, features, source, alpha, beta):
    diffVec = []
    # calculate PageRank according to features and beta values
    
    # transform input features into matrix form
    features_m = genFeatures(nnodes, g, features)        
    
    trans = genTrans(nnodes, g, features_m, source, alpha, beta)
    pp = np.repeat(1.0/nnodes, nnodes)
    pgrank = iterPageRank(pp, trans)
    
    # trans_p is the original transition matrix 
    # (without teleportation and varying strength)
    # this is used to calculate gradient of transition matrix
    trans_p = genTrans_plain(nnodes, g, source, 0)
    
    for k in range(len(beta)):
        tempObjDiff = 0
        pDiff = np.zeros((1, nnodes))
        transDiff = diffQ(features_m, beta, trans_p, alpha, k)
        pDiff = iterPageDiff(pDiff, pgrank, trans, transDiff)
        for d in Dset:
            for l in Lset:
                tempObjDiff += costDiff(pgrank[l], pgrank[d], offset)*(pDiff[l] - pDiff[d])
        # penalty term
        tempObjDiff += 2.0 * lam * beta[k]
        
        diffVec.append(tempObjDiff)
    return np.asarray(diffVec)

        
# ***function: trainModel
# users call this function to train beta parameter of Supervised Random Walk algorithm
# a training set and training graph must be specified as well as the parameters for the 
# learning process. Also, initial guess of beta parameter shall be given
# scipy's BFGS optimizer is called to iteratively optimize the object function,
# object function and the gradient of cost function is the main input to BFGS
# optimizer
def trainModel(Dset, Lset, offset, lam, nnodes, g, features, source, alpha, beta_init):
    beta_Opt = fmin_bfgs(functools.partial(minObj, Dset, Lset, 0, 0, nnodes, g, features, 
                            source, alpha), beta_init, fprime = functools.partial(objDiff, 
                            Dset, Lset, 0, 0, nnodes, g, features, source, alpha))
    
    #beta_Opt = fmin_l_bfgs_b(functools.partial(minObj, Dset, Lset, 0, 0, nnodes, g, features, 
    #                        source, alpha), beta_init, fprime = functools.partial(objDiff, 
    #                        Dset, Lset, 0, 0, nnodes, g, features, source, alpha))
    
    return beta_Opt


############################################
############################################

