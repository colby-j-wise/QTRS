#!/usr/bin/python

from event import FillEvent, OrderEvent
from risk_metrics import calc_sharpe_ratio, calc_drawdowns
from math import floor

import datetime
import queue
import numpy as np 
import pandas as pd

class portfolio(object):
	"""
	The portfolio class handles the positions and market
	value of all instruments at a resolution of a bar. 

	Positions DataFrame - time-index of quantity of positions
	held

	Holdings DataFrame - Total mrkt value for each symbol and
	percentage changing in portfolio value per bar
	"""

	def __init__(self, bars, events, start_data, initial_capital=10000.0):
		"""
		Initialises the portfolio with data bars and event queue.

		Parameters:
			bars - datahandler object with current mrkt data
			events - eventhandler queue object
			start_date - start date (bar) of portfolio
			initial_capital
		"""
		self.bars = bars
		self.events_queue = events
		self.symbol_list = self.bars.symbol_list
		self.start_date = start_date
		self.initial_capital = initial_capital

		self.all_positions = self.construct_all_positions()
		self.current_positions = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
		self.all_holdings = self.construct_all_holdings()
		self.current_holdings = self.construct_current_holdings()

		def construct_all_positions(self):
			"""
			Builds positions list using the start_date to
			determine when the time index begins
			"""
			d = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
			d['datetime'] = self.start_date
			return [d]

		def construct_all_holdings(self):
			"""
			Builds the holdings list using the start_date
			"""
			d = dict( (k,v) for k,v in [(s,0.0) for s in self.symbol_list] )
			d['datetime'] = self.start_date
			d['cash'] = self.initial_capital
			d['commission'] = 0.0
			d['total'] = self.initial_capital
			return [d]

		def construct_current_holdings(self):
			"""
			Builds the holdings list using the start_date
			"""
			d = dict( (k,v) for k,v in [(s,0.0) for s in self.symbol_list] )
			d['datetime'] = self.start_date
			d['cash'] = self.initial_capital
			d['commission'] = 0.0
			d['total'] = self.initial_capital
			return d

		def update_timeindex(self, event):
			"""
			Adds new record to positions matrix for
			current mrkt bar. Note this is done using the 
			previous bar. 

			Uses MarketEvent from events queue
			"""
			latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])
			# Update positions
			dp = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
			dp['datetime'] = latest_datetime

			for s in self.symbol_list:
				dp[s] = self.current_positions[s]
			# Append the current positions
			self.all_positions.append(dp)

			# Update holdings
			dh = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
			dh['datetime'] = latest_datetime
			dh['cash'] = self.current_holdings['cash']
			dh['commission'] = self.current_holdings['commission']
			dh['total'] = self.current_holdings['cash']

			for s in self.symbol_list:
				# Approximate real value
				market_value = self.current_positions[s] * \
						self.bars.get_latest_bar_value(s, "adj_close")
				dh[s] = market_value
				dh['total'] += market_value

			# Append the current holdings
			self.all_holdings.append(dh)

		def update_positions_from_fill(self, fill):
			"""
			Takes a Fill object and updates the position matrix to
			reflect the new position.

			Parameters:
				fill - The Fill object to update the positions with.
			"""
			# Check whether the fill is a buy or sell
			fill_dir = 0
			if fill.direction is 'BUY': 
				fill_dir = 1
			if fill.direction is 'SELL':
				fill_dir = -1

			# Update positions list with new quantities
			self.current_positions[fill.symbol] += fill_dir*fill.quantity

		def update_holdings_from_fill(self, fill):
			"""
			Takes a Fill object and updates the holdings matrix to
			reflect the holdings value.

			Parameters:
				fill - The Fill object to update the holdings.
			"""
			fill_dir = 0
			if fill.direction == 'BUY':
				fill_dir = 1
			if fill.direction == 'SELL':
				fill_dir = -1

			# Update holdings list with new quantities
			fill_cost = self.bars.get_latest_bar_value(fill.symbol_list, "adj_close")
			cost = fill_dir * fill_cost * fill.quantity
			self.current_holdings[fill.symbol] += cost
			self.current_holdings['commission'] += fill.commission
			self.current_holdings['cash'] -= (cost + fill.commission)
			self.current_holdings['total'] -= (cost + fill.commission)

		def update_fill(self, event):
			"""
			Update the current portfolio positions and holdings
			given FillEvent.
			"""
			if event.type is 'FILL':
				self.update_positions_from_fill(event)
				self.update_holdings_from_fill(event)

		def generate_naive_order(self, signal):
			"""
			Creates an Order object of constant quantity
			sizing of the signal object.

			**To Do: implement non-naive i.e. with
			risk management & position sizing factored in

			Parameters:
				signal - The tuple containing Signal information
			"""
			order = None 
			symbol = signal.symbol
			direction = signal.signal_type
			strength = signal.strength
			mkt_quantity = 100 # TO DO: implement dynamic order size based on equity (close or real-time)
			cur_quantity = self.current_positions[symbol]
			order_type = 'MKT' # TO DO: implement limits/ONC/OOO functionality

			# Initiate new positions
			if direction == 'LONG' and cur_quantity == 0:
				order = OrderEvent(symbol, order_type, mkt_quantity, 'BUY')
			if direction == 'SHORT' and cur_quantity == 0:
				order = OrderEvent(symbol, order_type, mkt_quantity, 'SELL')
			# Exit current positions | exit long or exit a short
			if direction == 'EXIT' and cur_quantity > 0: 
				order = OrderEvent(symbol, order_type, abs(cur_quantity), 'SELL')
			if direction == 'EXIT' and cur_quantity < 0:
				order = OrderEvent(symbol, order_type, abs(cur_quantity), 'BUY')

			return order

		def update_signal(self, event):
			"""
			Uses SignalEvent to generate new order based on portfolio rules
			"""
			if event.type == 'SIGNAL':
				order_event = self.generate_naive_order(event)
				self.events_queue.put(order_event)

		def create_equity_curve(self):
			"""
			Creates a pandas DataFrame from the all_holdings
			list of dictionaries.
			"""
			curve = pd.DataFrame(self.all_holdings)
			curve.set_index('datetime', inplace=True)
			curve['returns'] = curve['total'].pct_change()
			curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
			self.equity_curve = curve

		def output_summary_stats(self, period='minute'):
			"""
			Creates a list of summary statistics for the portfolio
			"""
			total_return = self.equity_curve['equity_curve'][-1]
			returns = self.equity_curve['returns']
			pnl = self.equity_curve['equity_curve']

			sharpe_ratio = calc_sharpe_ratio(returns, period=period)
			drawdown, max_dd, dd_duration = calc_drawdowns(pnl)
			self.equity_curve['drawdown'] = drawdown

			# Build list of tuples with performance stats
			stats = [("Total Return", "%0.2f%%" % ((total_return - 1.0) * 100.0)),
					 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
					 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
					 ("Drawdown Duration", "%d" % dd_duration)]
					 
			self.equity_curve.to_csv('equity.csv')
			return stats




