from pytrends.request import TrendReq
from functools import reduce

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
        pytrend.build_payload(kw_list=[keyword], cat=str(category), geo='US', timeframe='today 8-y')
        
        # Interest Over Time & drop isPartial col
        interest_over_time_df = pytrend.interest_over_time().drop('isPartial', 1)
        interest_over_time_df.columns=[catName]
        data_frames.append(interest_over_time_df)
    
    # Merge the list of data frames to create one dataframe
    merged_data = reduce(lambda  left,right: pd.merge(left, right, how='outer',left_index=True, right_index=True), data_frames)
    if print_data:
        print(merged_data.head())
    merged_data.to_csv("Weekly_{}_Google_Trends_Data_raw.csv".format(keyword), index=True)
    return merged_data

def get_home_sales_data(fileName):
    df = pd.read_csv(fileName)
    df['Period'] = pd.to_datetime(df['Period'])
    df['date'] = df.Period.dt.to_period('M')
    df = df.drop('Period', 1)
    df = df.set_index('date')
    return df.dropna()
        
def test_train_split(data, train_start='2013-01-01', test_start='2018-01-01'):
    train_df = data.loc[train_start : test_start]
    test_df = data.loc[test_start : ]
    return train_df, test_df

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

def extract_weekly_trend(data, week_num=3):
    df = data.reset_index()
    df['calendar_wom'] = df['date'].apply(week_of_month)
    df = df.loc[df['calendar_wom'] == week_num]
    df = df.drop('calendar_wom', 1)
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df.date.dt.to_period('M')
    return df.set_index('date')

def trend_pct_change(trend_data):
    cols = trend_data.columns
    pct_chges = pd.DataFrame()
    for idx, colName in enumerate(cols):
        pct_chges["%chg_trend"+str(idx+1)] = np.log(trend_data[colName]).diff()
    pct_chges = pct_chges.reset_index()
    pct_chges['date'] = pd.to_datetime(pct_chges['date'])
    pct_chges['date'] = pct_chges.date.dt.to_period('M')
    pct_chges = pct_chges.set_index('date')
    return pct_chges

def preprocess_data(y_raw, raw_trend_data, train_start, test_start, week_num=3):
    # Log of index level
    y_raw = np.log(y_raw)
    # Split home sales data by date into train/test
    y_train, y_test = test_train_split(y_raw, train_start, test_start)
    
    # Split raw search data into train/test
    _tr, _te = test_train_split(raw_trend_data, train_start, test_start)
    # Extract Google Trend Search result for specific week = week_num
    _tr = extract_weekly_trend(_tr, week_num)
    _te = extract_weekly_trend(_te, week_num)
    # Compute percentage changes for Google Trend data
    
    # Create X_train data
    X_train = pd.DataFrame()
    X_train['lag1'] = y_train['Value'].shift(1)
    X_train['lag2'] = y_train['Value'].shift(2)
    X_train = pd.merge(X_train, _tr, how='outer', left_index=True, right_index=True).dropna()
    
    # Create X_test data
    X_test = pd.DataFrame()
    X_test['lag1'] = y_test['Value'].shift(1)
    X_test['lag2'] = y_test['Value'].shift(2)
    X_test = pd.merge(X_test, _te, how='outer', left_index=True, right_index=True).dropna()
    
    # Ensure indexes match
    y_train = y_train[y_train.index.isin(X_train.index)]
    y_test = y_test[y_test.index.isin(X_test.index)]
    
    # Merge Train and Test sets
    train_data = pd.merge(X_train, y_train, how='inner', left_index=True, right_index=True)
    test_data = pd.merge(X_test, y_test, how='inner', left_index=True, right_index=True)
    
    return train_data, test_data
    