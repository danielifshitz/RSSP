class Mode:

    """
    this class present a mode of an operation.
    each mode have name(mode number), operation name(operation number),
    all needed resources, r' which is the less used resource and tim
    which is the total time that takes to the mode to be done.
    """

    def __init__(self, mode_number, op_number):
        self.mode_number = mode_number
        self.op_number = op_number
        self.resources = []
        self.r_tag = None
        self.tim = 0
        self.sim = 0


    def add_resource(self, resource, resource_start, resource_dur):
        """
        add resource to mode.
        resource: Resource - a resource that the mode need
        resource_start: float - local start time of the resource in the mode
        resource_dur: float - the duretion of the resource usage
        return: None
        """
        self.resources.append(resource)
        resource.add_mode(self.op_number, self.mode_number, resource_start, resource_dur)


    def find_rtag(self):
        """
        every mode have a r' which is the last smallest usage resource
        return: None
        """
        min_usage = float('inf')
        for resource in self.resources:
            if resource.size <= min_usage:
                min_usage = resource.size
                self.r_tag = resource


    def find_tim(self):
        """
        tim is the time that take to mode to end, it is the 
        MAX(start_time + duration) of all mode's resources.
        return: None
        """
        start_max = 0
        finish_max = 0
        op_mode = self.op_number + ',' + self.mode_number
        for resource in self.resources:
            end_time = resource.usage[op_mode]["start_time"] + resource.usage[op_mode]["duration"]
            if end_time > finish_max:
                finish_max = end_time
                start_max = resource.usage[op_mode]["start_time"]
        self.tim = finish_max
        self.sim = start_max
