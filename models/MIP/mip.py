from os.path import join
import time
import mip

from models.general_model import general_model  # type: ignore
from instance import Instance  # type: ignore


class Mip_model(general_model):
    
    """
    A Mixed Integer Programming (MIP) model to solve a multi-courier routing problem.

    Each courier starts and ends at a common depot and must deliver items under specific constraints:
    - Each item is delivered exactly once.
    - Couriers have load and distance limitations.
    - Sub-tours are eliminated using the MTZ formulation.
    - The objective is to minimize the longest route among all couriers.
    """

    def __init__(self, lib: 'str', i: 'Instance', verbose: 'bool' = False, solver_name='CBC'):
        super().__init__(lib, i)
        self._table = {}

        # Create model
        self.__model = mip.Model(solver_name=solver_name)

        # Decision variables: whether courier k travels from node i to node j
        self._table = {}
        for k in range(self._instance.m):
            for i in range(self._instance.origin):
                for j in range(self._instance.origin):
                    self._table[k, i, j] = self.__model.add_var(var_type=mip.INTEGER, name=f'table_{k}_{i}_{j}')

        # Total distance per courier
        self.__courier_distance = [self.__model.add_var(var_type=mip.INTEGER, name=f'courier_distance_{k}') for k in
                                   range(self._instance.m)]

        # Auxiliary variables to avoid sub-tours
        for k in range(self._instance.m):
            for i in range(self._instance.origin):
                self._u[k, i] = self.__model.add_var(var_type=mip.INTEGER, lb=1, ub=self._instance.origin,
                                                     name=f'u_{k}_{i}')

        if not verbose:
            self.__model.verbose = 0



    def solve(self, processes:'int' = 1, timeout:'int' = 300) -> None:

        """
        Builds and solves the optimization model.
        """

        # Objective function
        obj = self.__model.add_var(var_type=mip.INTEGER, name='obj')

        # Define total distance per courier
        for k in range(self._instance.m):
            self.__model += self.__courier_distance[k] == mip.xsum(
                self._instance.distances[i][j] * self._table[k, i, j] for i in range(self._instance.origin) for j in
                range(self._instance.origin))

        # Upper and lower bounds
        self.__model += obj <= self._instance.max_path
        self.__model += obj >= self._instance.min_path

        # Ensure obj is at least the max courier distance
        for k in range(self._instance.m):
            self.__model += obj >= self.__courier_distance[k]

        # Add model constraints
        self.__add_constraint()

        # Set the objective: minimize the longest courier path
        self.__model.objective = mip.minimize(obj)

        self._status = self.__model.optimize(max_seconds=int(timeout))
        self._end_time = time.time()
        self._inst_time = self._end_time - self._start_time
        
        # Store solution
        if self._status == mip.OptimizationStatus.OPTIMAL or self._status == mip.OptimizationStatus.FEASIBLE:
            self._result['time'] = round(self._inst_time, 3)
            self._result['optimal'] = self._status == mip.OptimizationStatus.OPTIMAL
            self._result['obj'] = int(self.__model.objective_value)
            self._result['sol'] = self._get_solution()

        else:
            self._result['time'] = round(self._inst_time, 3)
            self._result['optimal'] = self._status == mip.OptimizationStatus.OPTIMAL
            self._result['obj'] = None
            self._result['sol'] = None

    def __add_constraint(self) -> None:
        
        """
        Defines and adds all problem-specific constraints to the MIP model.
        These constraints enforce feasibility, courier rules, delivery requirements,
        and ensure sub-tour elimination.
        """
        
        # Basic flow constraints: for every node and courier
        for i in range(self._instance.origin):
            for k in range(self._instance.m):
                # A courier can't move to the same item
                self.__model += self._table[k, i, i] == 0
                # If an item is reached, it is also left by the same courier
                self.__model += mip.xsum(self._table[k, i, j] for j in range(self._instance.origin)) == mip.xsum(
                    self._table[k, j, i] for j in range(self._instance.origin))

        # Every item is delivered
        for j in range(self._instance.origin - 1):
            self.__model += mip.xsum(
                self._table[k, i, j] for k in range(self._instance.m) for i in range(self._instance.origin)) == 1

        # Courier-specific constraints
        for k in range(self._instance.m):
            # Couriers start at the origin and end at the origin
            self.__model += mip.xsum(
                self._table[k, self._instance.origin - 1, j] for j in range(self._instance.origin - 1)) == 1
            self.__model += mip.xsum(
                self._table[k, j, self._instance.origin - 1] for j in range(self._instance.origin - 1)) == 1

            # Each courier can carry at most max_load items
            self.__model += mip.xsum(
                self._table[k, i, j] * self._instance.size[j] for i in range(self._instance.origin) for j in
                range(self._instance.origin - 1)) <= self._instance.max_load[k]

            # Each courier must visit at least min_packs items and at most max_path_length items
            self.__model += mip.xsum(self._table[k, i, j] for i in range(self._instance.origin) for j in
                                     range(self._instance.origin - 1)) >= self._instance.min_packs
            self.__model += mip.xsum(self._table[k, i, j] for i in range(self._instance.origin) for j in
                                     range(self._instance.origin - 1)) <= self._instance.max_packs

        # If a courier goes for i to j then it cannot go from j to i, except for the origin
        # (this constraint it is not necessary for the model to work, but check if it improves the solution)
        for k in range(self._instance.m):
            for i in range(self._instance.origin - 1):
                for j in range(self._instance.origin - 1):
                    if i != j:
                        self.__model += self._table[k, i, j] + self._table[k, j, i] <= 1

        # Sub-tour elimination
        for k in range(self._instance.m):
            for i in range(self._instance.origin - 1):
                for j in range(self._instance.origin - 1):
                    if i != j:
                        self.__model += self._u[k, j] - self._u[k, i] >= 1 - self._instance.origin * (
                                1 - self._table[k, i, j])

    def update(self, path: 'str') -> None:
        """
        Loads a previously saved MIP model from a given file path.
        """
        self.__model.read(path)
