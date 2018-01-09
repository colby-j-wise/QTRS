#!/usr/bin/python3

import numpy as np 
import pandas as pd 


def calc_sharpe_ratio(returns, period='day', benchmark=None):
	"""
	Create the Sharpe ratio for the strategy.
	Currently assumes no benchmark (i.e. 0 risk-free rate)

	Parameters:
		returns - Pandas series representing period percentage returns
		periods - Daily(252), Hourly(252*6.5), Minutely(252*6.5*60)
	"""
	per = { 'day' : 252, 'hour': 252*6.5, 'minute': 252*60*6.5}
	
	if benchmark: # To Do: implement
		print("Calculating Sharpe Ratio using benchmark")

	if period is 'day':
		return np.sqrt(per['day']) * (np.mean(returns)) / np.std(returns)
	elif period is 'hour':
		return np.sqrt(per['hour']) * (np.mean(returns)) / np.std(returns)
	elif period is 'minute':
		return np.sqrt(per['minute']) * (np.mean(returns)) / np.std(returns)
	else:
		except KeyError:
			print('Type of period \'{}\' not found'.format(period))
			raise
	return None

def calc_drawdowns(pnl):
	"""
	Calculate the largest peak-to-trough drawdown of the PnL curve
	as well as the duration of the drawdown. Requires that the
	pnl_returns is a pandas Series.
	
	Parameters:
		pnl - A pandas Series representing period percentage returns.
		Returns:
		drawdown, duration - Highest peak-to-trough drawdown and duration.
	"""
	hwm = [0] # High Water Mark
	# Create drawdown & duration series
	idx = pnl.index
	drawdown = pd.Series(index = idx)
	duration = pd.Series(index = idx)
	# Loop over the index range
	for t in range(1, len(idx)):
		hwm.append(max(hwm[t-1], pnl[t]))
		drawdown[t] = (hwm[t]-pnl[t])
		duration[t] = (0 if drawdown[t] == 0 else duration[t-1]+1)
	return drawdown, drawdown.max(), duration.max()
