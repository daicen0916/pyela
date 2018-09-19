import os
import pandas as pd
import numpy as np
import datetime as dt
import sys
from datetime import datetime

pkg_dir = os.path.join(os.path.dirname(__file__),'..')

sys.path.append(pkg_dir)

from ela.textproc import *
from ela.spatial import *
from ela.classification import *

def test_create_meshgrid():
    xx, yy = create_meshgrid_cartesian(x_min=0.0, x_max=1.1, y_min=1.0, y_max=1.51, grid_res = 0.5)
    assert xx.shape[0] == 3
    assert xx.shape[1] == 2
    assert yy.shape[0] == 3
    assert yy.shape[1] == 2

def test_make_training_set():
    obs_colname = 'fake_obs'
    mock_obs = pd.DataFrame({EASTING_COL:np.array([.0, 1., 1., 0.]), NORTHING_COL:np.array([2., 2., 3., 3.]), obs_colname: np.array([.1, .2, .3, .4])})
    X, y = make_training_set(mock_obs, obs_colname)
    assert X.shape[0] == 4
    assert X.shape[1] == 2
    assert y.shape[0] == 4

class MockSlicePredictor:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    def f(self, x, y):
        return self.a * x + self.b * y + self.c

    def predict_one_sample(self, sample):
        x = sample[0]
        y = sample[1]
        return self.f(x, y)

    def predict(self, X):
        z = [self.predict_one_sample(x) for x in X]
        return np.array(z)

def test_interpolate_slice():
    m = create_meshgrid_cartesian(x_min=0.0, x_max=1.1, y_min=1.0, y_max=1.51, grid_res = 0.5)
    xx, yy = m
    a = 1.0
    b = 0.1
    c = 0.01
    p = MockSlicePredictor(a, b, c)
    def z_func(xi, yi):
        return p.f(xx[xi, yi], yy[xi, yi])
    
    predicted = interpolate_over_meshgrid(p, m)
    assert predicted.shape[0] == 3
    assert predicted.shape[1] == 2
    assert predicted[0,0] == z_func(0, 0)
    assert predicted[1,0] == z_func(1, 0)
    assert predicted[2,0] == z_func(2, 0)
    assert predicted[0,1] == z_func(0, 1)
    assert predicted[1,1] == z_func(1, 1)
    assert predicted[2,1] == z_func(2, 1)

def test_height_coordinate_functor():
    z_index_for_ahd = z_index_for_ahd_functor(b=+100)
    assert z_index_for_ahd(-100) == 0
    assert z_index_for_ahd(-99) == 1
    assert z_index_for_ahd(0) == 100
    assert z_index_for_ahd(+50) == 150

def test_burn_volume():
    dims = (3,4,5)
    dim_x,dim_y,dim_z = dims
    x = np.arange(0.0, dim_x*dim_y*dim_z, 1.0)
    test_vol = np.reshape(x, dims)
    z_index_for_ahd = z_index_for_ahd_functor(b=+1) # z = 0 is datum height -1, z = 4 is datum height 3
    xx, yy = create_meshgrid_cartesian(x_min=0.0, x_max=0.51, y_min=0.0, y_max=0.76, grid_res = 0.25)
    dem = xx + yy
    assert dem[0,0] == 0.0
    assert dem[1,1] == 0.5
    assert dem[2,2] == 1.0
    burnt = test_vol.copy()
    burn_volume(burnt, dem, z_index_for_ahd, below=False, inclusive=False)
    assert not np.isnan(burnt[0,0,0]) 
    assert not np.isnan(burnt[0,0,1]) 
    assert np.isnan(burnt[0,0,2]) 

    assert not np.isnan(burnt[2,2,0]) 
    assert not np.isnan(burnt[2,2,1]) 
    assert not np.isnan(burnt[2,2,2]) 
    assert np.isnan(burnt[2,2,3]) 

    burnt = test_vol.copy()
    burn_volume(burnt, dem, z_index_for_ahd, below=False, inclusive=True)
    assert not np.isnan(burnt[0,0,0]) 
    assert np.isnan(burnt[0,0,1]) 
    assert np.isnan(burnt[0,0,2]) 

    assert not np.isnan(burnt[2,2,0]) 
    assert not np.isnan(burnt[2,2,1]) 
    assert np.isnan(burnt[2,2,2]) 
    assert np.isnan(burnt[2,2,3]) 

def test_slice_volume():
    dims = (3,4,5)
    dim_x,dim_y,dim_z = dims
    x = np.arange(0.0, dim_x*dim_y*dim_z, 1.0)
    test_vol = np.reshape(x, dims)
    dem = np.empty((3, 4))
    z_index_for_ahd = z_index_for_ahd_functor(b=+1) # z = 0 is datum height -1, z = 4 is datum height 3
    dem[0,0] = -2.0
    dem[0,1] = +5.0
    dem[0,2] = -1.0
    dem[0,3] = -1.0
    dem[1,0] = -1.0
    dem[1,1] = -1.0
    dem[1,2] = -1.0
    dem[1,3] = -1.0
    dem[2,0] = -1.0
    dem[2,1] = -1.0
    dem[2,2] = np.nan
    dem[2,3] = -1.0

    def f(x, y):
        return drill_volume(test_vol, dem, z_index_for_ahd, x, y)

    assert np.isnan(f(0,0))
    assert np.isnan(f(0,1))
    assert f(0,2) == test_vol[0,2,0]
    assert f(0,3) == test_vol[0,3,0]
    assert f(1,0) == test_vol[1,0,0]
    assert f(1,1) == test_vol[1,1,0]
    assert f(1,2) == test_vol[1,2,0]
    assert f(1,3) == test_vol[1,3,0]
    assert f(2,0) == test_vol[2,0,0]
    assert f(2,1) == test_vol[2,1,0]
    assert np.isnan(f(2,2))
    assert f(2,3) == test_vol[2,3,0]

# test_slice_volume()
# test_interpolate_slice()
# test_burn_volume()
# test_height_coordinate_functor()
# test_make_training_set()
