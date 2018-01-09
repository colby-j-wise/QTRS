#!/usr/bin/python3

from abc import ABCMeta, abstractmethod
from eventhandler import MarketEvent

import datetime
import os, os.path
import numpy as np 
import pandas as pd 

"""
TO DO: create a live market feed handler to replace
the historical data feed handler of the backtester system
"""
class DataHandler(object):
	"""
	DataHandler is an abstract base class providing an interface for
	all subsequent (inherited) data handlers (both live and historic).
	The goal of a (derived) DataHandler object is to output a generated
	set of bars (OHLCVI) for each symbol requested.
	"""

	__metaclass__ = ABCMeta

	@abstractmethod
	def get_latest_bar(self, symbol):
		"""
		Returns the last bar updated.
		"""
		raise NotImplementedError("Should implement get_latest_bar()")


	@abstractmethod
	def get_latest_bars(self, symbol, N=1):
		"""
		Returns the last N bars updated.
		"""
		raise NotImplementedError("Should implement get_latest_bars()")

	@abstractmethod
	def get_latest_bar_datetime(self, symbol):
		"""
		Returns a Python datetime object for the last bar.
		"""
		raise NotImplementedError("Should implement get_latest_bar_datetime()")

	@abstractmethod
	def get_latest_bar_value(self, symbol, val_type):
		"""
		Returns one of the Open, High, Low, Close, Volume or OI
		from the last bar.
		"""
		raise NotImplementedError("Should implement get_latest_bar_value()")

	@abstractmethod
	def get_latest_bars_values(self, symbol, val_type, N=1):
		"""
		Returns the last N bar values from the
		latest_symbol list, or N-k if less available.
		"""
		raise NotImplementedError("Should implement get_latest_bars_values()")

	@abstractmethod
	def update_bars(self):
		"""
		Pushes the latest bars to the bars_queue for each symbol
		in a tuple OHLCVI format: (datetime, open, high, low,
		close, volume, open interest).
		"""
		raise NotImplementedError("Should implement update_bars()")


class HistoricCSVDataHandler(DataHandler):
	"""
	HistoricCSVDataHandler is designed to read CSV files for
	each requested symbol from disk and provide an interface
	to obtain the "latest" bar in a manner identical to a live
	trading interface.
	"""

	def __init__(self, events_queue, csv_dir, symbol_list):
		"""
		Initializes the historic data handler by requesting
		the location of the CSV files and a list of symbols.
		Assyms all files are of form 'symbol'.csv, where
		symbol is a string in the list.

		Parameters:
			events_queue - The Event Queue
			csv_dir - Absolute directory path to the CSV files.
			symbol_list - A list of symbol strings.
		"""

		self.events_queue = events_queue
		self.csv_dir = csv_dir
		self.symbol_list = symbol_list

		self.symbol_data = {}
		self.latest_symbol_data = {}
		self.continue_backtest = True

		self.open_csv_files()

		def open_csv_files(self):
			"""
			Opens CSV files from data directory. Converts
			them into pandas DF within a symbol dictionary

			#### Assumed to be Yahoo! data currently ####
			"""

			comb_idx = None 
			for s in self.symbol_list:
				# Load the CSV file with no header information, idxed on date
				self.symbol_data[s] = pd.read_csv(os.path.join(self.csv_dir, "{}.csv".format(s)),
													header=False, index_col=False, parse_dates=True,
													names=[ 'datetime', 'open','high','low', 
															'close', 'volume', 'adj_close']).sort()
				
				# Combine the index to pad forward vals
				if comb_idx is None:
					comb_idx = self.symbol_data[s].index
				else:
					comb_idx.union(self.symbol_data[s].index)

				# Set the latest symbol_data to None
				self.latest_symbol_data[s] = []
				# Reindex the dataframes
				for s in self.symbol_list:
					self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_idx, method='pad').iterrows()

		def get_new_bar(self, symbol):
			"""
			Returns the latest bar from the data feed.
			"""
			for bar in self.symbol_data[symbol]:
				yield bar

		def get_latest_bar(self, symbol):
			"""
			Returns the last bar from the latest_symbol list.
			"""
			try:
				bars_list = self.latest_symbol_data[symbol] # why create copy slow
			except KeyError:
				print("Symbol not found in historical dataset.")
				raise
			else:
				return bars_list[-1]

		def get_latest_bars(self, symbol, N=1):
			"""
			Returns the last N bars from latest_symbol list
			"""
			try:
				bars_list = self.latest_symbol_data[symbol] # why create copy slow
			except KeyError:
				print("Symbol not found in historical dataset.")
				raise
			else:
				return bars_list[-N:]

		def get_latest_bar_datetime(self, symbol):
			"""
			Returns a python datetime object for the last bar.
			"""
			try:
				bars_list = self.latest_symbol_data[symbol]
			except KeyError:
				print("Symbol not found in hostorical dataset.")
				raise
			else:
				return bars_list[-1][0]

		def get_latest_bar_value(self, symbol, val_type):
			"""
			Returns one of the Open, High, Low, Close, Volume or OI
			values from the pandas Bar series object.
			"""
			try:
				bars_list = self.latest_symbol_data[symbol]
			except KeyError:
				print("That symbol is not available in the historical data set.")
				raise
			else:
				return getattr(bars_list[-1][1], val_type)

		def get_latest_bars_values(self, symbol, val_type, N=1):
			"""
			Returns the last N bar values from the latest_symbol list
			"""
			try:
				bars_list = self.get_latest_bars(symbol, N)
			except KeyError:
				print("That symbol is not available in the hostrical data set.")
				raise
			else:
				return np.array([getattr(b[1], val_type) for b in bars_list])

		def update_bars(self):
			"""
			Pushes the latest bar to the latest_symbol_data structure
			for all symbols in the symbol list.
			"""

			for s in self.symbol_list:
				try:
					bar = next(self.get_new_bar(s))
				except StopIteration:
					print("Not more bars to fetch.")
					self.continue_backtest = False
				else:
					if bar:
						self.latest_symbol_data[s].append(bar)
			self.events_queue.put(MarketEvent())
