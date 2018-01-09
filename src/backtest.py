#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import pprint
import queue
import time


class Backtest(object):
	"""
	Enscapsulates the settings and components for carrying out
	an event-driven backtest.
	"""
	def __init__(self, csv_dir, symbol_list, initial_capital, heartbeat, start_date, 
				data_handler, execution_handler, portfolio, strategy):
		"""
		Initialises the backtest.

		Parameters:
			csv_dir - The hard root to the CSV data directory.
			symbol_list - The list of symbol strings.
			intial_capital - The starting capital for the portfolio.
			heartbeat - Backtest "heartbeat" in seconds
			start_date - The start datetime of the strategy.
			data_handler (Class) -  Handles the market data feed.
			execution_handler (Class) -  Handles the orders/fills for trades.
			portfolio (Class) -  Keeps track of portfolio current and prior positions.
			strategy (Class)  - Generates signals based on market data.
		"""
		self.csv_dir = csv_dir
		self.symbol_list = symbol_list
		self.initial_capital = initial_capital
		self.heartbeat = heartbeat
		self.start_date = start_date

		self.dataHandler_class = data_handler
		self.executionHandler_class = execution_handler
		self.portfolio_class = portfolio
		self.strategy_class = strategy

		self.events_queue = queue.Queue()

		self.signals = 0
		self.orders = 0
		self.fills = 0
		self.num_strates = 1

		self._generate_trading_instances()

	def _generate_trading_instances(self):
		"""
		Creates trading instance objects from
		respectively class types
		"""
		print("Creating DataHandler, Strategy, Portfolio & ExecutionHander")
		self.data_handler = self.dataHandler_class( self.events_queue,
												   	self.csv_dir,
												   	self.symbol_list
												   )
		self.strategy = self.strategy_class(self.data_handler, self.events_queue)
		self.portfolio = self.portfolio_class(	self.data_handler, self.events_queue,
												self.start_date, self.initial_capital
											)
		self.execution_handler = self.executionHandler_class(self.events_queue)

	def _run_backtest(self):
		"""
		Executes the backtest.
		"""
		i = 0
		while True:
			i += 1
			print(i)
			# Update the market bars
			if self.data_handler.continue_backtest == True:
				self.data_handler.update_bars()
			else:
				break

			# Handle the events
			while True:
				try:
					event = self.events_queue.get(False)
				except queue.Empty:
					break
				else:
					if event is not None:
						if event.type == 'MARKET':
							self.strategy.calculate_signals(event)
							self.portfolio.update_timeindex(event)

						elif event.type == 'SIGNAL':
							self.signals += 1
							self.portfolio.update_signal(event)

						elif event.type == 'ORDDER':
							self.orders += 1
							self.execution_handler.execute_order(event)

						elif event.type == 'FILL':
							self.fills += 1
							self.portfolio.update_fill(event)
			time.sleep(self.heartbeat)

	def _output_performance(self):
		"""
		Outputs the strategy performance from backtest.
		"""
		print("Creating summary stats...")
		stats = self.portfolio.output_summary_stats()
		
		print("Creating equity curve...")
		print(self.portfolio.equity_curve.tail(10))
		pprint.pprint(stats)
		print("Signals: {}".format(self.signals))
		print("Orders: {}".format(self.orders))
		print("Fills: {}".format(self.fills))

	def simulate_trading(self):
		"""
		Simulates the backtest and outputs portfolio performance.
		"""
		self._run_backtest()
		self._output_performance()
		