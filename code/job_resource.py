class Resource:

    """
    this class present a resource that used by operations.
    each resource have name(number), size which is how many times
    this resource is used in all modes and for each (operation,mode) we
    save the time that this mode need this resource.
    """

    def __init__(self, number):
        self.number = number
        self.size = 0
        self.usage = {}


    def add_mode(self, operation, mode, start_time, duration):
        """
        save a mode that use this resource.
        operation : string, operatoin number
        mode: string, mode number
        start_time: float, The start time of resource use
        duration: float, the duration of the use
        return: None
        """
        op_mode = operation + ',' + mode
        # each operation in each mode can use the same resource at most one time
        assert op_mode not in self.usage, op_mode + ": can't use the same resource twice in the same operation+mode"
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
