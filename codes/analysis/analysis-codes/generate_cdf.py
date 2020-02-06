""" This script produces a CDF plot from a list input.

"""

import pandas as pd
import numpy as np
import os

def generateCDF(file_path, cdf_path, sep,  weight=False, exclude_last = False):
    df = pd.read_csv(file_path, sep=sep, names=["cnt"])
    if(exclude_last):
        df = df[:-1]
    df['v'] = np.ones(len(df))
    cdf = df.groupby('cnt').sum()
    if(weight):
        cdf['v'] = cdf.index * cdf.v
    new_df =  cdf.cumsum()
    new_df = new_df.v / max(new_df.v)

    new_df.to_csv(cdf_path, sep="\t")#, header=False, index=False)

def generateCDFFromList(nums, cdf_path, weight=False, exclude_last = False):

    #df = pd.read_csv(file_path, names=["cnt"])
    df = pd.DataFrame({"cnt":nums})
    if(exclude_last):
        df = df[:-1]
    df['v'] = np.ones(len(df))
    cdf = df.groupby('cnt').sum()
    if(weight):
        cdf['v'] = cdf.index * cdf.v
    new_df =  cdf.cumsum()
    new_df = new_df.v / max(new_df.v)

    new_df.to_csv(cdf_path, sep="\t")#, header=False, index=False)

def generateCDFBasedRollingSum(file_path, cdf_path, sep, weight=False, exclude_last = False):
    df = pd.read_csv(file_path, sep=sep, names=["cnt"])
    
    if(exclude_last): df = df[:-1]
    sum = df['cnt'].sum()

    new_df = df 

    new_df['cdf'] = df['cnt'].cumsum()
    new_df['cdf'] = new_df['cdf'] / sum

    new_df['ratio'] = df['cnt'] / sum

    with open(cdf_path, 'w') as f:
        f.write('#')
    new_df.to_csv(cdf_path, sep="\t", header=True, mode ='a')#, header=False, index=False)

