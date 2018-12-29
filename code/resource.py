from resource_usage import Resource_usage

class Resource:
	def __init__(self, name, number):
		self.name = name
		self.number = number
		self.size = 0
		self.usage = {}


	def get_size(self):
		"""
		return the number of operation_mode use this resource == |L(r)|.
		return: int
		"""
		return self.size


	def add_mode(self, operation_mode, start_time, duration):
		"""
		add mode that use this resource.
		operation_mode: string, receive in next format: (operation number, mode number)
		start_time: float, The start time of resource use
		duration: float, the duration of the use
		return: none
		"""
		if operation_mode in self.usage:
			print("{} already exist".format(operation_mode))
		else:
			self.usage[operation_mode] = Resource_usage(start_time, duration)
			self.size += 1
			print("{} was seccesfuly added".format(operation_mode))


	def __str__(self):
		usage = ""
		for key, value in self.usage.items():
			usage += "\toperation_mode({}): {}\n".format(key, value)
		return "#{}){}: size = {}, usage by: \n{}".format(self.number,
			self.name, self.size, usage)