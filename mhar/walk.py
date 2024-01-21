# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_walk.ipynb.

# %% auto 0
__all__ = ['sample_inner_points', 'create_h', 'draw_uniform', 'update_progress_bars', 'walk']

# %% ../nbs/03_walk.ipynb 2
import torch

from typing import Union
from tqdm import tqdm

from .polytope import Polytope, NFDPolytope
from .utils import print_progress

# %% ../nbs/03_walk.ipynb 3
def sample_inner_points(X0, z):
    n, k = X0.shape
    if z > k:
        # Pad by repeating vectors from X to fill z columns
        num_repeats = z // k
        remainder = z % k
        I = torch.cat([X0] * num_repeats + [X0[:, :remainder]], dim=1)
    elif z < k:
        # Take the first z columns from X
        I = X0[:, :z]
    else:
        # z == k, I equals X
        I = X0.clone()
    return I

# %% ../nbs/03_walk.ipynb 4
def create_h(n,z,generator,dtype,device):
    """
    Creates a Tensor (z x n x 1) where each entry ~ N(0,1). Automatically detects the
    precision 64 bits or 32 bits.
    -------------
    :param n:   int
                Dimension of the Space where the Polytope Lives
    :param z:   int
                Padding Parameter
    :param generator:
    :param device:  String, default = cpu
                    Hardware used to make the computations and allocate the result.
                    If equal to cpu then the CPUs are used for computing the inverse.
                    If equal to cuda then the a GPU is used for computing the inverse.
    -------------
    :return:    Torch Tensor
                Tensor (z x n x 1) where each entry ~ N(0,1)Contains a tensor

    """
    if '64' in str(dtype):
        if 'cuda' in device:
            h = torch.cuda.DoubleTensor(n, z).normal_(generator=generator)
        elif 'cpu' == device:
            h = torch.DoubleTensor(n, z).normal_(generator=generator)
    elif '32' in str(dtype):
        if 'cuda' in device:
            h = torch.cuda.FloatTensor(n, z).normal_(generator=generator)
        elif 'cpu' == device:
            h = torch.FloatTensor(n, z).normal_(generator=generator)
    elif '16' in str(dtype):
        if 'cuda' in device:
            h = torch.cuda.HalfTensor(n, z).normal_(generator=generator)
        elif 'cpu' == device:
            h = torch.HalfTensor(n, z).normal_(generator=generator)

    return h

# %% ../nbs/03_walk.ipynb 5
def draw_uniform(z, generator,dtype,device='cpu'):
    """
    Creates a tensor (z x 1) where each entry ~ U(0,1). Automatically detects the
    precision 64 bits or 32 bits.
    -------------
    :param n:   int
                Dimension of the Space where the Polytope Lives
    :param z:   int
                Padding Parameter
    :param generator:
    :param device:  String, default = cpu
                    Hardware used to make the computations and allocate the result.
                    If equal to cpu then the CPUs are used for computing the inverse.
                    If equal to cuda then the a GPU is used for computing the inverse.
    -------------
    :return:    Torch Tensor
                Tensor (z x 1) where each entry ~ U(0,1)

    """

    if '64' in str(dtype):
        if 'cuda' in device:
            u = torch.cuda.DoubleTensor(1, z).uniform_(generator=generator)
        elif 'cpu' == device:
            u = torch.DoubleTensor(1,z).uniform_(generator=generator)
    elif '32' in str(dtype):
        if 'cuda' in device:
            u = torch.cuda.FloatTensor(1, z).uniform_(generator=generator)
        elif 'cpu' == device:
            u = torch.FloatTensor(1, z).uniform_(generator=generator)
    elif '16' in str(dtype):
        if 'cuda' in device:
            u = torch.cuda.HalfTensor(1, z).uniform_(generator=generator)
        elif 'cpu' == device:
            u = torch.HalfTensor(1, z).uniform_(generator=generator)

    return u
    

# %% ../nbs/03_walk.ipynb 6
import sys

def update_progress_bars(burned, thinning, t, T, new_t: bool = False):
    # Generate progress bar string for burned samples
    progress_burned = print_progress(iteration=burned, prefix='% of burned samples', total=thinning, length=30)

    # Clear the current line
    sys.stdout.write('\033[K')

    if new_t:
        # Generate progress bar string for iid samples
        progress_iid = print_progress(iteration=t, prefix='% of iid samples', total=T, length=30)
        # Print both progress bars
        print(progress_burned, end='\n')
        print(progress_iid, end='\n')
        # Move cursor up two lines for the next update
        #sys.stdout.write("\033[F\033[F")
    else:
        # Print only the progress bar for burned samples
        print(progress_burned, end='\r')

    # If new_t is False, the cursor will remain on the same line ready for the next update


# %% ../nbs/03_walk.ipynb 7
def walk(
        polytope:Union[Polytope, NFDPolytope], # Polytope Object
        X0:torch.Tensor,    # Initial Interior point(s) of dim=(n,k).     
                            #- If z > k (number of columns in X0), pad  by repeating vectors from X to fill z columns.
                            #- If z < k, take the first z columns from X0.
                            #- If z == k, equal to X0.
        z:int=1, # The number of simultaneous to be executed (padding parameter).
        T:int=1, # id-iterations, total_iid_points = T*z. Each iid iteration will burn the samples established by the thinning factor.
        warm:int=None, # Number of iid-iterations needed to warm. The walk will execute warm steps before saving the points.
        thinning:int=None, # Thinning Factor. Default O(n^3)
        device:str = None, # Deveice to use, cpu or cuda
        seed:int=None, # Seed for Pseudo-Random Number Generation
        verbosity:int=1, # Verbosity of the execution
        ) -> torch.Tensor:
        
        
    ## Check validity 
    # Device
    device = device if device is not None else polytope.device
    assert(device in ['cpu', 'cuda']), print('The device is not correctly specified: ', device,
                                        '\n Please choose cpu or cuda')
    # X0 dimension
    assert(X0.shape[0] == polytope.n)
    
    ## Set min and max values
    min_ = torch.finfo(polytope.dtype).min + 2.0
    max_ = torch.finfo(polytope.dtype).max - 2.0
    if verbosity > 1:
        print(f'Minimum number allowed {min_}')
        print(f'Maximum number allowed {max_}')
    
    
    ## Set seed
    random_gen = torch.Generator(device=device)
    if seed:
        random_gen.manual_seed(seed)
    else:
        random_gen.seed()
    
    
    ## Check Dimensions
    n = polytope.n
    mI = polytope.mI
    if isinstance(polytope, NFDPolytope) :
        mE = polytope.mE
    else:
        mE=None            
    if verbosity >=1:
        print('n: ', n, '  mI:', mI, '  mE:', mE, '  z:', z)
        
    
    ## Compute/set thinning factor
    if thinning is not None:
        pass
    else:
        thinning = int(n * n * n)
        if verbosity >= 1:
            print('Automatic Thinning factor: ', thinning)
            
    if warm is not None:
        pass
    else:
        warm = thinning
        if verbosity >= 1:
            print('Warming iterations: ', thinning)
     
            
    ## Prepare and send Matrices
    init_x0 = sample_inner_points(X0,z).to(device)  
    polytope.send_to_device(device)
    
    ## Iteration Loop
    t = 1
    burned = 0
    dtype = polytope.dtype
    x = init_x0
    X = torch.empty((T,n, z))
    while t <= T:
        h = create_h(n, z, generator=random_gen, dtype=dtype,device=device)
        if isinstance(polytope, NFDPolytope) :
            d = polytope.project_h(h)
        else:
            d = h
        #print('H',h.shape)
        # Compute B - AX / AD

        numerator = polytope.b_in - torch.matmul(polytope.A_in, x)
        #print('numerator',numerator.shape)
        denominator = torch.matmul(polytope.A_in, d)
        #print('denomitanr',denominator.shape)
        
        # Overwrite numerator to keep memory free
        numerator = numerator / denominator
        # From the positive denominators you want the smallest one
        lambda_pos = torch.min(~(denominator > 0.0) * max_ +
                               (denominator > 0.0) * numerator, 0).values.to(dtype)[None,:]
        # From the negative denominators you want the biggest
        lambda_neg = torch.max(~(denominator < 0.0) * min_ +
                               (denominator < 0.0) * numerator, 0).values.to(dtype)[None,:]
        
    
        # Uniform draw
        u = draw_uniform(z, generator=random_gen, dtype=dtype,device=polytope.device)
        # print('u',u.shape)
        # print('lambda_pos',lambda_pos.shape)
        # print('lambda_neg',lambda_neg.shape)
        
        theta = (1.0 - u) * lambda_pos + u * lambda_neg
        # print('theta', theta.shape)
        # print('d', d.shape)
        # print('theta_2', (d * theta).shape)
        
        # New X
        x = x + d * theta
        #print('x: ',x.shape) 
        if verbosity >=1:
            update_progress_bars(burned, thinning, t, T)        
        
        if (warm > 0) & (burned >= thinning):
            warm = warm - 1
            burned = 0
        
        # Manage the burning rate and save points
        if burned >= thinning:
            X[t-1,:, :] = x.to('cpu')        
            
            
            if verbosity >=1:
                update_progress_bars(burned, thinning, t, T, new_t=True)
            t = t + 1
            burned = 0

        burned = burned + 1

    return X

    
