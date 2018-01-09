#!/usr/bin/python3

from abc import ABCMeta, abstractmethod
from eventhandler import SignalEvent 

import datetime
import numpy as np 
import pandas as pandas
import queue


class Strategy(object):
	"""
	Strategy is an abstract base class providing an interface for
	all subsequent strategy handling objects. The goal of a 
	Strategy object is to generate Signal objects for particular 
	symbols based on the inputs of Bars (OHLCV) generated 
	by a DataHandler object.

	This is designed to work both with historic and live data as
	the Strategy object is agnostic to where the data came from,
	since it obtains the bar tuples from a queue object.
	"""

	__metaclass__ = ABCMeta

	@abstractmethod
	def calculate_signals(self):
		"""
		Provides the mechanisms to calculate the list of signals.
		"""
		raise NotImplementedError("Should implement calculate_signals()")

	
