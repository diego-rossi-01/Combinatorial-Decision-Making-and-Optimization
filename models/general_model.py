import time
from instance import Instance # type: ignore

class general_model:
    
    """
    General model base class for routing problems, designed to support different solver backends
    such as MIP and Z3. It handles instance setup, timing, solution extraction, and route formatting.
    """

    def __init__(self, lib: 'str', instance: 'Instance'):

        """
        Initialize the general model with solver type and problem instance.
        """ 

        self._lib = lib

        self._start_time = time.time()
        self._end_time = None

        self._inst_time = None
        self._instance = instance
        self._table = None
        self._u = {}
        self._status = None
        self._result = {}

        #_courier_routes is a dictionary where keys are couriers k and values are empty lists
        self._courier_routes = {k: [] for k in range(instance.m)}

    def _get_solution(self) -> 'list':

        """
        Extracts the computed courier routes from solver variables and formats them
        into readable sequences of visited nodes. Removes redundant depot entries.
        """
        
        # Extract and populate courier routes
        for k in range(self._instance.m):

            if self._lib == "mip":
                # For MIP solvers, use .x attribute to check active routes
                self._courier_routes[k] = [[i + 1, j + 1] for i in range(self._instance.origin) for j in
                                           range(self._instance.origin) if
                                           self._table[k, i, j].x == 1]

            elif self._lib == "z3":
                # For Z3 solvers, values are boolean
                self._courier_routes[k] = [[i + 1, j + 1] for i in range(self._instance.origin) for j in
                                           range(self._instance.origin) if
                                           self._table[k][i][j]]


        # Reconstruct full routes from arc pairs
        for k in range(self._instance.m):
            self._courier_routes[k] = self.compute_route(self._instance.origin, self._instance.origin, self._courier_routes[k])
        # Reorder the routes to start from the origin
        # Remove instance.origin - 1 from the routes
        for k in range(self._instance.m):
            if len(self._courier_routes[k]) > 0:
                m = max(self._courier_routes[k])
                self._courier_routes[k] = list(filter(lambda d: d < m, self._courier_routes[k]))

        # Create a list to store the routes for each courier
        routes = [self._courier_routes[k] for k in range(self._instance.m)]
        
        return routes

    def get_result(self) -> dict:
        
        """
        Returns the final result dictionary after solving.
        """
        
        return self._result


    def compute_route(self, start, end, pairs):
        
        """
        Reconstructs a route sequence from a list of (i, j) arc pairs.
        Assumes a valid path exists from start to end.
        """

        route = [start] #start with the intiial location
        current = start
        def get_next(current): #define a help function to find the next step
            for pair in pairs:
                if pair[0] == current:
                    return pair[1]
        while True:
            current = get_next(current)
            route.append(current)
            if current == end:
                return route
