from mode import Mode

class Operation:

    """
    this class present an operation that need to be done to finish a job.
    for every operation we will save its name(number), modes, ann all resource that all modes need.
    """

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
        # save all needed resources for every mode in all_resources dictionary
        if resource not in self.all_resources:
            self.all_resources[resource] = [mode_number]

        else:
            self.all_resources[resource].append(mode_number)

        for mode in self.modes:
            # check if mode exists
            if mode.mode_number == mode_number:
                # add mode data to existing mode
                mode.add_resource(resource, start, dur)
                return

        # if it is new mode, create it and add it to operation modes list
        mode = Mode(mode_number,self.number)
        mode.add_resource(resource, start, dur)
        self.modes.append(mode)

    def get_mode_by_name(self, name):
        for mode in self.modes:
            if mode.mode_number == name:
                return mode

        return None


    def get_min_tim(self):
        """
        return the shortest mode time of this operation
        return: number
        """
        return min(self.modes, key=lambda mode: mode.tim).tim
