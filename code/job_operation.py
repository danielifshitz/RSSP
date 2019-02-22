from mode import Mode
class Operation:

    def __init__(self, number):
        self.number = number
        self.modes = []
        self.all_resources = {}


    def add_mode(self, mode_number, resource, start, dur):
        """
        add mode to operation with the needed resource for the mode.
        if it is a new mode number, create him.
        save the resource in all_resources list.
        mode_number: string - the number of the mode
        resource: Resource - a resource that the mode need
        resource_start: float - local start time of the resource in the mode
        resource_dur: float - the duretion of the resource usage
        return: None
        """
        for mode in self.modes:
            # check if mode exists
            if mode.mode_number == mode_number:
                mode.add_resource(resource, start, dur)
                if resource not in self.all_resources:
                    self.all_resources[resource] = [mode_number]
                else:
                    self.all_resources[resource].append(mode_number)
                return
        # if it is new mode
        mode = Mode(mode_number,self.number)
        mode.add_resource(resource, start, dur)
        self.modes.append(mode)
        if resource not in self.all_resources:
            self.all_resources[resource] = [mode_number]
        else:
            self.all_resources[resource].append(mode_number)
