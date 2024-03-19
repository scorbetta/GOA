import numpy as np
import sys

all_data = []

# activation function and its derivative
def tanh(x):
    for vdx in range(len(x)):
        all_data.append(x[0][vdx])
    return np.tanh(x);

def tanh_prime(x):
    return 1-np.tanh(x)**2;

def get_line(x0, x1):
    y0 = np.tanh(x0)
    y1 = np.tanh(x1)
    m = (y0 - y1) / (x0 - x1)
    q = y1 - m * x1
    return m,q

def afun_test_primitive(x):
    # (-inf,-2]
    if x <= -2:
        m = 0
        q = -1.0
        #return -1.0
    # [-2,arctanh(-sqrt(2/3))]
    elif x >= -2.0 and x <= np.arctanh(-np.sqrt(2.0/3)):
        m,q = get_line(-2.0, np.arctanh(-np.sqrt(2.0/3)))
        #return 0.2149 * x - 0.5702
    # [arctanh(-sqrt(2/3)),arctanh(-sqrt(1/3))]
    elif x >= np.arctanh(-np.sqrt(2.0/3)) and x <= np.arctanh(-np.sqrt(1.0/3)):
        m,q = get_line(np.arctanh(-np.sqrt(2.0/3)), np.arctanh(-np.sqrt(1.0/3)))
        #return 0.4903 * x - 0.2545
    # [arctanh(sqrt(-1/3)),0]
    elif x >= np.arctanh(-np.sqrt(1.0/3)) and x <= 0:
        m,q = get_line(np.arctanh(-np.sqrt(1.0/3)), 0)
        #return 0.8768 * x
    # [0,arctanh(sqrt(1/3))]
    elif x >= 0 and x <= np.arctanh(np.sqrt(1.0/3)):
        m,q = get_line(0, np.arctanh(np.sqrt(1.0/3)))
        #return 0.8768 * x
    # [arctanh(sqrt(1/3)),arctanh(sqrt(2/3))]
    elif x >= np.arctanh(np.sqrt(1.0/3)) and x <= np.arctanh(np.sqrt(2.0/3)):
        m,q = get_line(np.arctanh(np.sqrt(1.0/3)), np.arctanh(np.sqrt(2.0/3)))
        #return 0.4903 * x + 0.2545
    # [arctanh(sqrt(2/3)),2]
    elif x >= np.arctanh(np.sqrt(2.0/3)) and x <= 2.0:
        m,q = get_line(np.arctanh(np.sqrt(2.0/3)), 2.0)
        #return 0.2149 * x + 0.5702
    # [2,+inf)
    elif x >= 2:
        m = 0
        q = 1.0
        #return 1.0
    
    return m * x + q

def afun_test(x):
    foovec = np.vectorize(afun_test_primitive)
    return foovec(x)

def afun_test_prime_primitive(x):
    # (-inf,-2]
    if x <= -2:
        m = 1e-4
        #return 1e-4
    # [-2,arctanh(-sqrt(2/3))]
    elif x >= -2.0 and x <= np.arctanh(-np.sqrt(2.0/3)):
        m,q = get_line(-2.0, np.arctanh(-np.sqrt(2.0/3)))
        #return 0.2149
    # [arctanh(-sqrt(2/3)),arctanh(-sqrt(1/3))]
    elif x >= np.arctanh(-np.sqrt(2.0/3.0)) and x <= np.arctanh(-np.sqrt(1.0/3.0)):
        m,q = get_line(np.arctanh(-np.sqrt(2.0/3)), np.arctanh(-np.sqrt(1.0/3)))
        #return 0.4903
    # [arctanh(sqrt(-1/3)),0]
    elif x >= np.arctanh(-np.sqrt(1.0/3.0)) and x <= 0:
        m,q = get_line(np.arctanh(-np.sqrt(1.0/3)), 0)
        #return 0.8768
    # [0,arctanh(sqrt(1/3))]
    elif x >= 0 and x <= np.arctanh(np.sqrt(1.0/3.0)):
        m,q = get_line(0, np.arctanh(np.sqrt(1.0/3)))
        #return 0.8768
    # [arctanh(sqrt(1/3)),arctanh(sqrt(2/3))]
    elif x >= np.arctanh(np.sqrt(1.0/3.0)) and x <= np.arctanh(np.sqrt(2.0/3.0)):
        m,q = get_line(np.arctanh(np.sqrt(1.0/3)), np.arctanh(np.sqrt(2.0/3)))
        #return 0.4903
    # [arctanh(sqrt(2/3)),2]
    elif x >= np.arctanh(np.sqrt(2.0/3.0)) and x <= 2.0:
        m,q = get_line(np.arctanh(np.sqrt(2.0/3)), 2.0)
        #return 0.2149
    # [2,+inf)
    elif x >= 2:
        m = 1e-4
        #return 1e-4

    return m

def afun_test_prime(x):
    foovec = np.vectorize(afun_test_prime_primitive)
    return foovec(x)
