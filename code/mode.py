class Mode:
    def __init__(self, num_mode, op_num):
        self.num_mode = num_mode
        self.op_num = op_num
        self.needed_resources = []
        self.r_tag = None
        self.tim = 0


    def add_resource(self, resource, resource_start, resource_dur):
        """
        add resource to mode
        resource: Resource - a resource that the mode need
        resource_start: float - local start time of the resource in the mode
        resource_dur: float - the duretion of the resource usage
        return: None
        """
        self.needed_resources.append(resource)
        resource.add_mode(self.op_num, self.num_mode, resource_start, resource_dur)


    def find_rtag(self):
        """
        every mode have a r' which is the smallest usage resource
        return: None
        """
        min = float('inf')
        for resource in self.needed_resources:
            if resource.size <= min:
                min = resource.size
                self.r_tag = resource


    def find_tim(self):
        """
        tim is the time that take to mode to end, it is the MAX(start_time + duration) 
        of all mode's resources
        return: None
        """
        max = 0
        op_mode = self.op_num + ',' + self.num_mode
        for resource in self.needed_resources:
            if resource.usage[op_mode].start_time + resource.usage[op_mode].duration > max:
                max = resource.usage[op_mode].start_time + resource.usage[op_mode].duration
        self.tim = max


    def __str__(self):
        string = ""
        for res in self.needed_resources:
            string += "\n\t\t" + str(res)
        return "num_mode = {} , num_op = {} , resources = {}".format(self.num_mode, self.op_num, string)
