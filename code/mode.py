class Mode:
    def __init__(self, num_mode, op_num):
        self.num_mode = num_mode
        self.op_num = op_num
        self.needed_resources = []
        self.r_tag = None
        self.tim = 0

    def add_info_to_mode(self, resource, resource_start, resource_dur):
        self.needed_resources.append(resource)
        resource.add_mode(self.op_num, self.num_mode, resource_start, resource_dur)

    def find_rtag(self):
        min = float('inf')
        for resource in self.needed_resources:
            if resource.size <= min:
                min = resource.size
                self.r_tag = resource

    def find_tim(self):
        max = 0
        op_mode = self.op_num + ',' + self.num_mode
        for resource in self.needed_resources:
            if resource.usage[op_mode].start_time + resource.usage[op_mode].duration > max:
                max = resource.usage[op_mode].start_time + resource.usage[op_mode].duration
        self.tim = max

    def get_rtag(self):
        return self.r_tag

    def get_tim(self):
        return self.tim

    def __str__(self):
        string = ""
        for res in self.needed_resources:
            string += "\n\t\t" + str(res)
        return "num_mode = {} , num_op = {} , resources = {}".format(self.num_mode, self.op_num, string)
