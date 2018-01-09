#!/usr/bin/python3
# -*- coding: utf-8 -*-


class Event(object):
	"""
	Event is base class providing an interface for all subsequent
	(inherited) events, that will trigger further events in the
	trading infrastructure
	"""

	pass 


class MarketEvent(Event):
	"""
	Handles the event of receiving a new market update with
	corresponding bars.
	"""

	def __init__(self):
		"""
		Initialises the MarketEvent
		"""
		self.type = 'MARKET'


class SignalEvent(Event):
	"""
	Handles the event of sending a Signal from a Strategy object.
	This is received by a Portfolio object and acted upon.
	"""

	def __init__(self, strategy_id, symbol, datetime, signal_type, strength): #strength poor word
		"""
		Initialises the SignalEvent

		Parameters:
			strategy_id - The unique identifier for the strategy that generated the signal.
			symbol - The ticker symbol, e.g. 'GOOG'
			datetime - The timestamp at which the signal was generated
			signal_type - 'LONG' or 'SHORT'.
			strength - An adjustment factor 'suggestion' used to scale quantity at portfolio level
		"""

		self.type = 'SIGNAL'
		self.strategy_id = strategy_id
		self.symbol = symbol
		self.datetime = datetime
		self.signal_type = signal_type
		self.strength = strength


class OrderEvent(Event):
	"""
	Handles the event of sending an Order to an execution system.
	The order contains a symbol (e.g. GOOG), a type (market or limit),
	quantity and direction.
	"""

	def __init__(self, symbol, order_type, quantity, direction):
		"""
		Initialises the order type, setting whether it is a MArket order
		('MKT') or limit order ('LMT'), has a quantity and it direction
		('BUY' or 'SELL').

		Parameters:
			symbol - The instrument to trade.
			order_type - 'MKT' or 'LMT' for Market or Limit
			quantity - Non-negative integer for quantity
			direction - 'BUY' or 'SELL' for long or short
		"""

		self.type = 'ORDER'
		self.symbol = symbol
		self.order_type = order_type
		self.quantity = quantity
		self.direction = direction

	def print_order(self):
		"""
		Outputs generated order
		"""
		print(
			"Order -- \n \
			   Symbol: {} \n\
			   Type: {} \n\
			   Quantity: {} \n\
			   Direction: {} \n".format(self.symbol, self.type, self.quantity, self.direction)
			 )


class FillEvent(Event):
	"""
	Encapsulates the notion of a Filled Order, as returned
	from a brokerage. Stores the quantity of an instrument
	actually filled and at what price. In addition, stores
	the commission of the trade from the brokerage.
	"""

	def __init__(self, timeindex, symbol, exchange, quantity, direction, 
				 fill_cost, commission=None):

		"""
		Initialises the FillEvent object. Sets the symbol, exchange,
		quantity, direction, cost of fill and an optional
		commission. If commission is not provided, the Fill object will
		calculate it based on the trade size and Interactive
		Brokers fees.

		Parameters:
			timeindex - The bar-resolution when the order was filled.
			symbol - The instrument which was filled.
			exchange - The exchange where the order was filled.
			quantity - The filled quantity.
			direction - The direction of fill (’BUY’ or ’SELL’)
			fill_cost - The holdings value in dollars.
			commission - An optional commission sent from IB.
		"""

		self.type = 'FILL'
		self.timeindex = timeindex
		self.symbol = symbol
		self.exchange = exchange
		self.quantity = quantity
		self.direction = direction
		self.fill_cost = fill_cost

		self.share_threshold = 500
		self.max_commission = 1.3 # Fix! Now == 0.5% of trade value i.e. Cost = max(min(0.005*qty,0.005*qty*px),1.00)
		self.min_commission = 0.8 # Fix! Now == 0.35   

		# Calculate commission
		if commission:
			self.commission = commission
		else:
			self.commission = self.calculate_commission()

	def calculate_commission(self):
		"""
		Calculates the fees of trading based on an Interactive
		Brokers fee structure for API, in USD. This does not include 
		exchange or ECN fees.

		Based on "US API Directed Orders":
		https://www.interactivebrokers.com/en/index.php?%20f=commission&p=stocks2
		"""

		full_cost = self.max_commission
		if self.quantity <= self.share_threshold:
			full_cost = max( self.max_commission, (self.max_commission/100) * self.quantity )
		else:
			full_cost = max( self.max_commission, (self.min_commission/100) * self.quantity )
		return full_cost





