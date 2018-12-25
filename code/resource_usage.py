class Resource_usage:
	def __init__(self, start_time, duration):
		self.start_time = start_time
		self.duration = duration
		self.global_start_time = -1


	def set_global_starting_time(self, global_start_time=-1):
		"""
		set the starting global time of resource use.
		global_start_time: float
		return: none
		"""
		self.global_start_time = global_start_time


	def get_start_time(self):
		"""
		return: float
		"""
		return self.start_time


	def get_duration(self):
		"""
		return: float
		"""
		return self.duration


	def get_global_start_time(self):
		"""
		return: float
		"""
		return self.global_start_time


	def __str__(self):
		return "global time = {}, start time = {}, duration = {}".format(self.global_start_time,
			self.start_time, self.duration)