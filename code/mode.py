
class Mode:
    def __init__(self, num_mode, op_num):

        self.num_mode = num_mode
        self.op_num = op_num
        self.needed_resources = []
        self.r_tag = None
        self.tim = 0


    def add_info_to_mode(self, resource, resource_start, resource_dur):
        self.needed_resources.append(resource)
        om = self.op_num + ',' + self.num_mode
        resource.add_mode(om, resource_start, resource_dur)


    def find_rtag(self):
        min = float('inf')
        for resource in self.needed_resources:
            if resource.size < min:
                min = resource.size
                self.r_tag = resource


    def find_tim(self):
        max = 0
        for resource in self.needed_resources:
            if resource.usage.start_time + resource.usage.duration > max:
                max = resource.usage.start_time + resource.usage.duration
        self.tim = max

    def get_rtag(self):
        return self.r_tag

    def get_tim(self):
        return self.tim