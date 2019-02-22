class Mode:

    def __init__(self, mode_number, op_number):
        self.mode_number = mode_number
        self.op_number = op_number
        self.resources = []
        self.r_tag = None
        self.tim = 0


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
        min = float('inf')
        for resource in self.resources:
            if resource.size <= min:
                min = resource.size
                self.r_tag = resource


    def find_tim(self):
        """
        tim is the time that take to mode to end, it is the 
        MAX(start_time + duration) of all mode's resources.
        return: None
        """
        max = 0
        op_mode = self.op_number + ',' + self.mode_number
        for resource in self.resources:
            sum = resource.usage[op_mode]["start_time"] + resource.usage[op_mode]["duration"]
            if sum > max: max = sum
        self.tim = max
