---
description: mhar
output-file: index.html
title: mhar (Mentat/Matrix Hit and Run)

---


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

This package constains one of the fastest polytope samplers known to date.
It only works with linear inequality restrictions, it does not accept V-representation.  
 
Peer Reviewed Paper: [Novel matrix hit and run for sampling polytopes and its GPU implementation](https://link.springer.com/article/10.1007/s00180-023-01411-y)  
Free Peer Reviwed Paper: [ Free: Novel matrix hit and run for sampling polytopes and its GPU implementation](https://github.com/sonder-art/mhar/blob/released/mhar_modified-3.pdf)  
Conference Presentation: [Youtube LACSC2021 conference](https://www.youtube.com/watch?v=o2CxnI6onts)  
Github: [Repo](https://github.com/sonder-art/mhar)  
MHAR pypi: [pip library](https://pypi.org/project/mhar/)

## What is Mentat-HAR?

We propose and analyze a new Markov Chain Monte Carlo algorithm that generates a uniform sample over full and non-full-dimensional polytopes. This algorithm, termed “Matrix Hit and Run” (MHAR), is a modification of the Hit and Run framework. For a polytope in (R^n) defined by m linear constraints, the regime (n^ 1 + 1/3) has a lower asymptotic cost per sample in terms of soft-O notation () than do existing sampling algorithms after a warm start. MHAR is designed to take advantage of matrix multiplication routines that require less computational and memory resources. Our tests show this implementation to be substantially faster than the hitandrun R package, especially for higher dimensions. Finally, we provide a python library based on PyTorch and a Colab notebook with the implementation ready for deployment in architectures with GPU or just CPU.

## Install

```sh
!pip install mhar
```

## How to use

You can acces to example jupyter notebooks with colab linksm they explain everything in detail:  
+ [Fully dimensional polytopes](https://github.com/sonder-art/mhar/blob/released/nbs/tutorial_full_dimensional.ipynb)  
+ [Non-fully dimensional polytoes](https://github.com/sonder-art/mhar/blob/released/nbs/tutorial_nonfull_dimensional.ipynb)  

A quick example using automatically generated polytopes from mhar

## Fully Dimensional

> $A^IX \leq b^I$

We will sample the unit hypercube that is defined as:  
> $n-hypercube = \{x \in R^n || x \in [-1,1]^n \} $  

Which we can represent in matrix restrictions:  
$ Ix \leq 1$  
$ -Ix \leq 1$  
Where $I$ is the identity matrix of dimension $n \times n$ 


```python
import torch
```


```python
# Find available devices (cpu or gpu)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu').type
print('Device:', device)
```

    Device: cuda


We also need to decide the data-type `dtype` we are going to use. Depending on your necessities you can choose it, we recomend to use `64` bits for non-fully dimentional polytopes in order to maintain numerical inestability of the projections. Otherwiise the precision depends on the dimension of your polytope and speed you want.  
  
As of now `16` bit precision is only available for `gpu` and not `cpu`.


```python
# We will choose 64-bits
dtype = torch.float64
```

### Defining the polytope

Lets generate a sample polytope hypercube. For other polytopes you need to supply the constraints in torch tensors [see tutorial](https://github.com/sonder-art/mhar/blob/released/nbs/tutorial_full_dimensional.ipynb),and for non fully dimensional polytopes [see tutorial](https://github.com/sonder-art/mhar/blob/released/nbs/tutorial_nonfull_dimensional.ipynb)  


```python
from mhar.polytope_examples import Hypercube

# Create a polytope (Hypercube)
hypercube_sim = Hypercube(3,
                      dtype=torch.float32,
                      device=device
                      )
hypercube_sim
```

    /home/uumami/sonder-art/mhar/mhar/polytope.py:45: UserWarning:
      The object will not create a copy of the tensors, so modifications will be reflected in the object
    





    Numeric Precision (dtype) torch.float32
    Device: cuda
    A_in: torch.Size([6, 3]) 
    b_in: torch.Size([6, 1])



We will use this restrictions to define the polytope as:  
$A^Ix = [I | -I]x \leq 1 = b^I$


```python
print('Equality Matrix',hypercube_sim.A_in)
print('Inequality Vector',hypercube_sim.b_in)
```

    Equality Matrix tensor([[ 1.,  0.,  0.],
            [ 0.,  1.,  0.],
            [ 0.,  0.,  1.],
            [-1., -0., -0.],
            [-0., -1., -0.],
            [-0., -0., -1.]])
    Inequality Vectpr tensor([[1.],
            [1.],
            [1.],
            [1.],
            [1.],
            [1.]])


### Inner point(s)


```python
from mhar.inner_point import ChebyshevCenter
import numpy as np
```

In order to start the algorithm we need at least one inner point $x_0$. If you know your inner point you can supply it to the algorithm, `mhar` also contains functions to compute one inner point using the [chebyshev center](https://en.wikipedia.org/wiki/Chebyshev_center) which finds the center of the smallest ball inside the polytope.

 `from mhar.inner_point import ChebyshevCenter`. The solver is in numpy so precision must be specified as `numpy.dtype`. It uses `linprog` from `scipy.optimize`. You can see the documentation [here](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html). 
  
It could also be the last points produced by a previous walk/run of the `mhar` 


```python
x0 = ChebyshevCenter(polytope=hypercube_sim, # Polytope Object
                    lb=None,  # Lowerbound (lb <= x ), if unknown leave it as None 
                    ub=None,  # Upperbound ( x <= up), if unknown leave it as None 
                    tolerance=1e-4, # Tolerance for equality restrictions (A_eqx = b_eq)
                    device=device, # device used cpu or cuda
                    solver_precision=np.float32 # numpy dtype
                    )
x0
```

    
    Simplex Status for the Chebyshev Center
     Optimization proceeding nominally.





    tensor([[-0.],
            [-0.],
            [-0.]], device='cuda:0')



If we want to manually input the inner points then it is enough to use a torch tensor of size $n \times l$. Where $l$ is ne number of inner points you want to supply. Just write them in column notation.  
  
We are going to manually add an other starting point to the one calcualted by the `chebyshev center` to show its functionality later.


```python
x0 = torch.cat([x0, 
            torch.tensor([[.5], [.5], [.5]]).to(device).to(dtype)
             ], dim=1)
x0
```


    tensor([[-0.0000, 0.5000],
            [-0.0000, 0.5000],
            [-0.0000, 0.5000]], device='cuda:0')


Now we can proceed to sample the `hypercube`

### Walk

We are going to sample the polytope starting from the inner points we supply using the method `walk.walk`. It has the next arguments:

+ `polytope` is an object of the type [`Polytope`](https://uumami.github.io/mhar/polytope.html#polytope) or [`NFDPolytope`](https://uumami.github.io/mhar/polytope.html#nfdpolytope) that defines it. In our example hypercube is a [`Polytope`](https://uumami.github.io/mhar/polytope.html#polytope), [`NFDPolytope`](https://uumami.github.io/mhar/polytope.html#nfdpolytope) is for npt fully dimensional objects.
+ `X0` a tensor containing the inner points to start the walks from.
+ `z` determines the number of simoultaneous `walks`. If the number of initial points supplied are less than `z`  ($ncols($ `x0` $) < $ `z`) then some points will be reused as starting points.  
+ `T` is the number of uncorrelated iterations you want. The number of total uncorrelated points produced by the algorithm is `z` $\times$ `T`, since `z` points are sampled at each iteration.  
+ `thinning` determines the number of points that we need to burn between iterations in order to get uncorrelated points. The suggested factor should be in the order of $O(n^3)$.
+ `warm` determines a thinning for warming the walks only at the beggining, after the this war the walks resumes as normal. It is used if you want to lose the dependency from the starting points.
+ `device` device where the tenros live `cpu` or `cuda`
+ `seed` for reproducibility
+ `verbosity` for printing what is going on


```python
from mhar.walk import walk
X = walk(polytope=hypercube_sim,
        X0 = x0,  
        z=100, 
        T=1, 
        warm=0,
        thinning=3**3, 
        device= None, 
        seed=None,
        verbosity=2
)
print(f'Sampled points shape{X.shape}')
X
```

    Minimum number allowed -3.4028234663852886e+38
    Maximum number allowed 3.4028234663852886e+38
    Eps:  1.1920928955078125e-07
    Values close to zero will be converted to 3eps or -3eps: 3.5762786865234375e-07
    n:  3   mI: 6   mE: None   z: 100
    % of burned samples |██████████████████████████████| 100.0%
    % of iid samples |██████████████████████████████| 100.0%
    Sampled points shapetorch.Size([1, 3, 100])





    tensor([[[-0.3338, -0.5635,  0.2466, -0.2501, -0.0603,  0.9541, -0.3222,
               0.1137, -0.8737,  0.9419, -0.2837,  0.6530,  0.6781,  0.1492,
               0.9140, -0.7611,  0.2826, -0.2357, -0.8645,  0.8267,  0.8019,
              -0.4441,  0.4958, -0.6613,  0.7441, -0.2193, -0.1340, -0.4858,
              -0.6970, -0.4413,  0.3817,  0.4279, -0.1637, -0.2693, -0.0182,
              -0.9639, -0.0314,  0.6485,  0.2268, -0.9117,  0.1562, -0.8305,
               0.9049, -0.0106,  0.8320, -0.5444, -0.1228,  0.2520, -0.5334,
               0.7400, -0.6726, -0.4790, -0.2184, -0.4502,  0.5855, -0.7953,
               0.8199,  0.6050, -0.3904,  0.4861,  0.6425, -0.9872, -0.7829,
              -0.4209, -0.9521,  0.8352,  0.6761, -0.8160,  0.0826,  0.6692,
               0.9779, -0.5642,  0.6161,  0.4993, -0.0903,  0.2990, -0.1937,
              -0.0180,  0.0693, -0.1304,  0.4572,  0.8642,  0.8992,  0.6749,
              -0.6140,  0.3952, -0.7586,  0.5815,  0.4864,  0.6536, -0.0772,
              -0.0545, -0.7530, -0.2361, -0.0823,  0.1008,  0.5498,  0.0942,
              -0.2037,  0.5652],
             [-0.9025,  0.7198, -0.0500,  0.3864,  0.3559, -0.2199,  0.3232,
              -0.2868,  0.9847,  0.9554,  0.4867, -0.1136,  0.5854, -0.9230,
               0.2347,  0.6331,  0.5619, -0.4740,  0.1774, -0.7327,  0.8773,
               0.6989,  0.1388, -0.1482,  0.1736,  0.4433,  0.1400,  0.3644,
              -0.8856,  0.0750, -0.3866,  0.6695,  0.2725,  0.9922, -0.4999,
              -0.3959, -0.7405, -0.1488,  0.6785, -0.9745,  0.0872,  0.2047,
               0.0891,  0.6642,  0.6600,  0.6670, -0.0544,  0.1954, -0.1161,
              -0.3343,  0.1930,  0.1275,  0.1545,  0.8708,  0.6549, -0.3574,
               0.9794,  0.2172, -0.2096,  0.3311, -0.7018,  0.5225, -0.8472,
               0.9820, -0.9980, -0.6618, -0.7188,  0.0205,  0.2136, -0.4699,
               0.5595, -0.7285, -0.3282, -0.8630,  0.5291, -0.4996,  0.6968,
               0.5358, -0.0416,  0.7241,  0.8022, -0.7639,  0.6258, -0.5334,
               0.5954, -0.9207, -0.3290,  0.3947,  0.2246,  0.7631,  0.1384,
               0.2143,  0.3654,  0.6176, -0.9192, -0.3199,  0.4385,  0.3193,
               0.9837, -0.4685],
             [-0.3506,  0.1149,  0.7728,  0.7332,  0.6196, -0.3987,  0.7881,
              -0.6913,  0.5762,  0.4079, -0.0977,  0.7422,  0.7344,  0.5729,
              -0.8242,  0.6081, -0.3565, -0.1740, -0.5077,  0.7384, -0.2856,
               0.6730,  0.4888,  0.4643,  0.2829, -0.0420, -0.3754, -0.7870,
               0.7831,  0.3965, -0.0324, -0.9271,  0.2641, -0.7741, -0.6429,
               0.6231, -0.8245,  0.3725,  0.9428, -0.6745,  0.4491,  0.5827,
              -0.1114, -0.1080, -0.4661, -0.8422,  0.2048,  0.7947, -0.6277,
              -0.2252,  0.9385, -0.6995,  0.9694,  0.3595,  0.1326, -0.9594,
               0.3394,  0.1757, -0.5100, -0.2042,  0.6624, -0.3272,  0.3097,
               0.4163, -0.1994,  0.3934, -0.6676,  0.2880, -0.0119,  0.4966,
               0.2620,  0.5617,  0.7632,  0.7716,  0.8719,  0.0938,  0.8886,
              -0.5205, -0.7433, -0.9057, -0.0528, -0.2449, -0.5712, -0.1866,
              -0.0519, -0.2303,  0.3796, -0.7370,  0.7556,  0.6878, -0.7005,
              -0.5419,  0.0863,  0.9560,  0.5770,  0.7278,  0.1542, -0.7797,
               0.8863,  0.1376]]])



## Development

For development you can use `pip` files available in `environment_files`. You can choose either `dev_gpu` or `dev_cpu` depending on your current architechture. Both install all the necessary libraries for development.  

### nbdev

We use [nbdev](https://nbdev.fast.ai/tutorials/tutorial.html) for development, so after installation you can follow the tutorial [here](https://nbdev.fast.ai/tutorials/tutorial.html). Usually is enough to use the `nbdev_install_quarto` and `nbdev_install_hooks`.  

If you experience problems installing `Quarto` try to install it manually (it depends on your OS).
