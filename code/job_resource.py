from resource_usage import Resource_usage

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
        if op_mode in self.usage:
            print("{} already exist".format(op_mode))
        else:
            self.usage[op_mode] = Resource_usage(start_time, duration)
            # the size of resource defined to be the number of operations that need this resource
            for registered_op_mode in self.usage.keys():
                op, mo = registered_op_mode.split(',')
                if op == operation and mo != mode:
                    return
            self.size += 1


    def __str__(self):
        usage = ""
        for key, value in self.usage.items():
            usage += "\n\t\t\toperation_mode({}): {}".format(key, value)
        return "{}: size = {}, usage by: {}".format(self.number, self.size, usage)