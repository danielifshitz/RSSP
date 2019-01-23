class Resource_usage:
    def __init__(self, start_time, duration):
        self.start_time = start_time
        self.duration = duration
        self.global_start_time = -1


    def set_global_starting_time(self, global_start_time=-1):
        """
        set the starting global time of resource use.
        global_start_time: float
        return: None
        """
        self.global_start_time = global_start_time


    def __str__(self):
        return "global time = {}, start time = {}, duration = {}".format(self.global_start_time,
            self.start_time, self.duration)
