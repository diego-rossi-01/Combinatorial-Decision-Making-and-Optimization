import numpy as np
from time import time
from more_itertools import locate

class Instance:

    """
    Represents a single instance of the courier routing problem.
    Parses input data from a `.dat` file and computes relevant bounds
    and structures for solver integration.
    """

    def __init__(self, file_path: 'str') -> None:

        """
        Initialize the instance from a given data file.
        """

        self.name = file_path.split('/')[-1].replace('.dat', '')

        # Read and preprocess file content
        file = open(file_path, "r")
        lines = [line.replace('\n', '') for line in file]
        file.close()

        self.m = int(lines[0])
        self.n = int(lines[1])
        loads = lines[2].split(' ')

        # Parse max loads and sort them
        self.max_load = [int(l) for l in loads]
        self.max_load_indexes = np.argsort(self.max_load)
        self.max_load = list(sorted(self.max_load))
        
        # Parse package sizes
        sizes = lines[3].split(' ')
        self.size = [int(s) for s in sizes if s != '']

        # Parse distance matrix
        lines = lines[4:]
        self.distances = np.zeros(shape=(self.n + 1, self.n + 1), dtype=int)
        for i in range(self.n + 1):
            line = lines[i].split(' ')
            for j in range(self.n + 1):
                self.distances[i, j] = int(line[j])

        self.optimal_paths = None
        self.min_path = 0
        start_time = time()
        
        # Compute package count bounds
        self.max_packs = self.n-self.m+1
        self.compute_bounds()

        # Compute depot/origin representation
        self.number_of_origin_stops = int(((self.max_packs + 2) * self.m) - self.n)
        self.origin = int(self.n+1)
        
        self.n_array = [i+1 for i in range(self.n + 1)]
        self.count_array = [1 for _ in range(self.n)] + [self.number_of_origin_stops]
        
        self.presolve_time = time() - start_time

    def compute_bounds(self) -> 'None':

        """
        Compute lower and upper bounds for travel distance and number of packages per courier.
        These are used to guide and constrain the optimization model.
        """

        # Depot index in distance matrix
        o = self.n

        def compute_path(current_cost, nodes, select, steps):
            if steps > len(nodes) - 1:
                next_step, cost = select(nodes)
                updated_nodes = nodes + [next_step]
                cost += current_cost
                return compute_path(cost, updated_nodes, select, steps)
            return {'p': nodes, 'c': current_cost}

        # Exclude the weakest courier
        max_weight = sum(self.max_load[1:])

        def min_select(nodes):
            dist = np.copy(self.distances[nodes[-1], :])
            dist[nodes] = np.max(dist) + 1
            c = np.min(dist)
            i, = np.where(dist == c)
            return i[0], c

        ordered_size = sorted(self.size)

        # Compute minimum number of packages needed to exceed load
        k = 1
        while sum(ordered_size[:self.n - k]) > max_weight:
            k += 1
        if k == 1:
            self.min_path = int(np.max(
                [self.distances[o, i] + self.distances[i, o] for i in range(self.n)]
            ))
        else:
            min_origin = int(min([self.distances[i, o] for i in range(self.n)]))
            self.min_path = int(
                max([
                    int(compute_path(self.distances[o, i], [o, i], min_select, k)['c']) + min_origin
                    for i in range(self.n)
                ]
                ))

        # Compute max_packs bound
        k = 1
        while sum(ordered_size[:self.n - k]) > max_weight:
            k += 1
        self.min_packs = k

        k = 1
        while sum(ordered_size[:k]) < self.max_load[-1] and k < self.n:
            k += 1

        self.max_packs = min(k, self.max_packs)

        def max_select(nodes):
            dist = np.copy(self.distances[nodes[-1], :])
            dist[nodes] = -1
            c = np.max(dist)
            i, = np.where(dist == c)
            return i[0], c

        maxes = [compute_path(self.distances[o, i], [o, i], max_select, k) for i in range(self.n)]
        self.max_path = int(np.max([int(m['c']) + self.distances[m['p'][-1], o] for m in maxes]))

    def get_similar(self, loads):

        """
        Identify groups of couriers with equal max load capacity.
        """

        ret_lst = []
        added_list = []
        for load in loads:
            if loads.count(load) > 1 and not load in added_list:
                ret_lst.append([i+1 for i in locate(loads, lambda x: x == load)])
                added_list.append(load)
        return ret_lst
