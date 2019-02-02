from mode import Mode
class Operation:

    def __init__(self, num_of_op):
        self.num_of_op = num_of_op
        self.modes = []
        self.all_resources = {}
        self.global_start_time = -1


    def add_mode_to_operation(self,num_mode,resource,start,dur):
        """
        add mode to operation, in the same time add resource to mode
        num_mode: string - the number of the new mode
        resource: Resource - a resource that the mode need
        resource_start: float - local start time of the resource in the mode
        resource_dur: float - the duretion of the resource usage
        return: None
        """
        for mode in self.modes:
            if mode.num_mode == num_mode: # check if mode exists
                mode.add_resource(resource, start, dur)
                if resource not in self.all_resources:
                    self.all_resources[resource] = [num_mode]
                else:
                    self.all_resources[resource].append(num_mode)
                return
        mode = Mode(num_mode,self.num_of_op)
        mode.add_resource(resource, start, dur)
        self.modes.append(mode)
        if resource not in self.all_resources:
            self.all_resources[resource] = [num_mode]
        else:
            self.all_resources[resource].append(num_mode)


    def set_global_start_time(self, global_start_time):
        self.global_start_time = global_start_time
