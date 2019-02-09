class Resource:

    def __init__(self, number):
        self.number = number
        self.size = 0
        self.usage = {}


    def add_mode(self, operation, mode, start_time, duration):
        """
        add mode that use this resource.
        operation : string, operatoin number
        mode: string, mode number
        start_time: float, The start time of resource use
        duration: float, the duration of the use
        return: None
        """
        op_mode = operation + ',' + mode
        assert op_mode not in self.usage, op_mode + " already exist"
        self.usage[op_mode] = {"start_time" : start_time, "duration" : duration}
        # the size of resource defined to be the number of operations that need this resource
        for registered_op_mode in self.usage.keys():
            i, m = registered_op_mode.split(',')
            if i == operation and m != mode:
                return
        self.size += 1


    def get_usage_duration(self, operation, mode):
        """
        return the duration of the usage of this resource by the given operation and mode
        operation : string, operatoin number
        mode: string, mode number
        return: int
        """
        op_mode = operation + ',' + mode
        return self.usage[op_mode]["duration"]
