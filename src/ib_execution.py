import datetime
import time

from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.opt import ibConnection, message

from event import FillEvent, OrderEvent
from execution import ExecutionHandler



class IBExecutionHandler(ExecutionHandler):
	"""
	Handles order execution via Inter. Brokers API.
	Used in live trading directly only.

	Note: 'SMART' is IB's internal algo for best exch pricing

	TO DO: Need to validate syntax is same.
			Assumption is that it's changed a bit
	"""
	def __init__(self, events_queue, order_routing="SMART", currency="USD"):
		"""
		Initialises the IBExecution instance.
		"""
		self.events_queue = events_queue
		self.order_routing = order_routing 
		self.currency = currency
		self.fill_dict = {}

		self.tws_conn = self.create_tws_connection()
		self.order_id = self.create_initial_order_id()
		self.register_handlers()

	def _error_handler(self, msg):
		"""
		Handles the capturing of error messages

		TO DO: Implement more robust error handling based
				on IB API error types
		"""
		# Currently no error handling.
		print("Server Error: {}".format(msg))

	def _reply_handler(self, msg):
		"""
		Handles of server replies
		"""
		# Handle open order orderID processing
		if msg.typeName == "openOrder" and msg.orderID == self.order_id \
			and not self.fill_dict.has_key(msg.orderID):

			self.create_fill_dict_entry(msg)
		# Handle Fills
		if msg.typeName == "orderStatus" and msg.status == "Filled" \
			and self.fill_dict[msg.orderID]["filled"] == False:

			self.create_fill(msg)
			print("Server Response: {}, {}\n".format(msg.typeName, msg))

	def create_tws_connection(self):
		"""
		Connect to the Trader Workstation (TWS) running on 
		usual port of 7496, with clientID 10. The clientID
		is chosen; two seperate IDs - one for execution 
		connection and market data connection.
		"""
		tws_conn = ibConnection() #ibConnection().connect()
		return tws_conn.connect()

	def create_initial_order_id(self):
	"""
	Shittly written method which needs to improved.
	Basically creates initial order ID to keep track
	of submitted IB orders
	"""
	return 1

	def register_handlers(self):
		"""
		Register the error and server reply
		message handling functions.
		"""
		# Assign error handling function above 
		# to TWS connection
		self.tws_conn.register(self._error_handler, 'Error')

		# Assign all the server reply messages to the 
		# reply_handler function
		self.tws_conn.regsterAll(self._reply_handler)

	def create_contract(self, symbol, sec_type, exchange, prime_exch, currency):
		"""
		IB API requires both a IbPy Contract instance and IbPy Order instance.
		This method creates the Contract instance based on method args
		
		Parameters:
			symbol - The ticker symbol for the contract
			sec_type - The security for the contract ('STK' is 'stock')
			exchange - The exchange to carry out the contract
			prime_exch - The primary exchange to carry out the contract
			currency - The currency in which to purchase the contract
		"""
		contract = Contract()
		contract.m_symbol = symbol # Check API for valid syntax
		contract.m_secType = sec_type
		contract.m_exchange = exchange
		contract.m_primaryExch = prime_exch
		contract.m_currency = curr
		return contract

	def create_order(self, order_type, quantity, action):
		"""
		Create an order object (Market/Limit) to go long/short.

		order_type - 'MKT', 'LMT' for Market or Limit orders
		quantity - (Int) number of assets to order
		action - 'BUY' or 'SELL'
		"""
		order = Order()
		order.m_orderType = order_type
		order.m_totalQuantity = quantity
		order.m_action = action
		return order 

	def create_fill_dict_entry(self, msg):
		"""
		Creates an entry in the Fill Dictionary that lists
		orderIDs and provides security information. Needed
		to properly handle event-driven behavior of IB client-
		server responses
		"""
		self.fill_dict[msg.orderID] = {
										"symbol": msg.contract.m_symbol,
										"exchange": msg.contract.m_exchange,
										"direction": msg.order.m_action,
										"filled": False
									}

	def create_fill(self, msg):
		"""
		Handles the creation of the FillEvent that will be
		placed onto the events queue after an order is filled.
		"""
		fd = self.fill_dict[msg.orderID]

		# Parse the fill data from fill_dict
		symbol = fd["symbol"]
		exchange = fd["exchange"]
		filled = msg.filled
		direction = fd["direction"]
		fill_cost = msg.avgFillPrice

		# Create a FillEvent object
		fill_event = FillEvent(
			datetime.datetime.utcnow(), symbol,
			exchange, filled, direction, fill_cost
		)

		# Ensure that multiple messages don't create
		# additional fills by setting "filled" to True
		self.fill_dict[msg.orderID]["filled"] = True

		# Place FillEvent onto the events queue
		self.events_queue.put(fill_event)

	def execute_order(self, event):
		"""
		Creates the necessary IB order object and submits 
		it to the IB via their API. The results are then 
		queried to generate a FillEvent object which is 
		then placed back on the event queue.

		Parameters:
			event - Contrains an Event object with order information.
		"""
		if event.type == 'ORDER':
			# Prepare parameters for the asset order
			symbol = event.symbol
			sec_type = "STK"
			order_type = event.order_type
			quantity = event.quantity
			direction = event.direction

			# Create the IB Contract from the Order event
			ib_contract = self.create_contract(
				symbol, sec_type, self.order_routing,
				self.order_routing, self.currency
			)

			# Create IB Order from the Order event
			ib_order = self.create_order(
				order_type, quantity, direction
			)

			# Now send the order to IB via tws_conn
			self.tws_conn.placeOrder(
				self.order_id, ib_contract, ib_order
			)

			# NOTE: Appears following line is needed!
			# Seems like sleeping ensure order is recieved
			# by IB server. 
			# TO DO: Why? Check latency or Bithub error logs
			time.sleep(1)

			# Increment order ID for session to ensure no dup order
			self.order_id += 1




