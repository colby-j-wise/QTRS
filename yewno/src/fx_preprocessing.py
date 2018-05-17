from pytrends.request import TrendReq
from functools import reduce
import matplotlib.pyplot as plt #plotting/graphics

import datetime
import calendar
import pandas as pd
import numpy as np


def get_search_data(keyword, cat_dict, print_data=False):
    # Login to Google
    pytrend = TrendReq()

    # List captures each category's trend history dataframe
    data_frames = [] 
    for category in cat_dict.keys():
        # Lookup category name
        catName = cat_dict[category]

        # Create payload and capture API tokens.
        pytrend.build_payload(kw_list=[keyword], cat=str(category), geo='US', timeframe='today 5-y')
        
        # Interest Over Time & drop isPartial col
        interest_over_time_df = pytrend.interest_over_time().drop('isPartial', 1)
        interest_over_time_df.columns=[catName]
        data_frames.append(interest_over_time_df)
    
    # Merge the list of data frames to create one dataframe
    raw_data = reduce(lambda  left,right: pd.merge(left, right, how='outer',left_index=True, right_index=True), data_frames)
    if print_data:
        print(raw_data.head())
    raw_data.to_csv("Weekly_{}_Google_Trends_Data_raw.csv".format(keyword), index=True)
    return raw_data

def rolling_slope(ts):
    x = np.arange(0, len(ts))
    y = np.array(ts)
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y)[0]
    return m

def get_GTrend_slopes(data):
    for colName in data:
        data = data.reset_index()
        data[colName] = data[colName].rolling(window=4, min_periods=4).apply(rolling_slope).shift(1)
        data = data.set_index('date')
        #data.dropna(inplace=True)
    return data

def week_of_month(tgtdate):
    tgtdate = tgtdate.to_pydatetime()

    days_this_month = calendar.mdays[tgtdate.month]
    for i in range(1, days_this_month):
        d = datetime.datetime(tgtdate.year, tgtdate.month, i)
        if d.day - d.weekday() > 0:
            startdate = d
            break
    # now we can use the modulo 7 appraoch
    return (tgtdate - startdate).days //7 + 1

def add_wom(df):
    df = df.reset_index()
    df['WoM'] = df['date'].apply(week_of_month)
    df['date_orig'] = df['date']
    df['date'] = df['date'].dt.to_period('M')
    #df = df.set_index('date')
    df = df.iloc[:, ::-1] # reverse column order
    return df

def load_fx_data(fileName):
    df = pd.read_csv(fileName)
    cols = [col for col in df.columns if (col == 'End_Week') or ('Close' in col)]
    df = df[cols]
    df = df.rename(columns={'End_Week':'date'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    # Wk over wk percentage change & then +/-1 for classifier
    df = df.pct_change().apply(binarize_return)
    df = add_wom(df)
    return df

def binarize_return(series):
    return np.where(series.isnull(), np.nan, np.where(series >= 0.,   1, -1))
    
def test_train_split(data, train_start='2013-01-01', test_start='2017-01-01'):
    train_df = data.loc[train_start : test_start]
    test_df = data.loc[test_start : ]
    return train_df, test_df

def run_preprocessing(fx_file, 
                      search_key1, 
                      search_key2, 
                      news_categories, 
                      travel_categories):
    
    us_GTNews = get_search_data(search_key1, news_categories)
    eu_GTNews = get_search_data(search_key2, news_categories)
    us_GTravel = get_search_data(search_key1, travel_categories)
    eu_GTravel = get_search_data(search_key2, travel_categories)
    
    # Convert to rolling window slopes
    us_N = get_GTrend_slopes(us_GTNews)
    us_T = get_GTrend_slopes(us_GTravel)
    eu_N = get_GTrend_slopes(eu_GTNews)
    eu_T = get_GTrend_slopes(eu_GTravel)
    
    # Add week_of_month columns
    df1_GTNews = add_wom(us_N)
    df2_GTravel = add_wom(us_T)
    df3_GTNews = add_wom(eu_N)
    df4_GTravel = add_wom(eu_T)
    
    # Load FX Data & Process
    fx_data = load_fx_data(fx_file)
    
    # Load all dataframes
    df_list = [df1_GTNews, df2_GTravel, df3_GTNews, df4_GTravel, fx_data]
    merged_data = reduce(lambda  left,right: pd.merge(left, 
                                                  right, 
                                                  how='inner',
                                                  left_on=['date','WoM'], 
                                                  right_on = ['date','WoM']), df_list)
    # Drop WoM
    merged_data = merged_data.reset_index()
    merged_data['date'] = merged_data['date_orig_x']
    merged_data= merged_data.drop('date_orig_x', 1)
    merged_data = merged_data.set_index('date')
    merged_data = merged_data.drop('WoM', 1)
    merged_data = merged_data.drop('index', 1)
    return merged_data.dropna()
