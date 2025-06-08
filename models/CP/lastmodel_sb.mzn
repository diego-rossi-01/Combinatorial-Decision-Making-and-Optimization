include "globals.mzn";
int: m; % number of couriers
int: n; % number of items

array[1..m] of int: capacity; % maximum load size for each courier
array[1..n] of int: item_size; % size of each item
array[1..n+1, 1..n+1] of int: dist_matrix; % distance matrix
array[1..m] of int: original_indices;



int: min_path; % lower bound
int: max_path; % upper bound
array[1..n+1] of int: n_array;
array[1..n+1] of int: count_array;
int: max_packs;
int: origin;
int: min_packs;
array[int] of set of int: similars;

int: max_path_length = max_packs +2;

array[1..m, 1..max_path_length] of var 1..n+1: route; % route of each courier
array[1..m] of var int: courier_distance; % distance traveled by each courier
array[1..n] of var 1..m: packs;
var int: max_distance; % max distance traveled

constraint forall(j in 1..m)(
	route[j,1] = origin /\ route[j,max_path_length] = origin
); % each courier start from the origin, end at the origin and at time 2 his path must start

constraint forall(j in 1..m, i in 2..min_packs+1)(
	route[j,i] != origin
);

constraint forall(j in 1..m)(
  sum(i in 2..max_path_length-1)(
    if route[j,i] < origin then item_size[ route[j,i] ] else 0 endif
  ) <= capacity[j]
);

constraint forall(j in 1..m, i in 2..max_path_length-1)(
	route[j,i] = origin -> forall(k in i..max_path_length-1)(route[j,k] = origin)
);

constraint global_cardinality_closed(route, n_array, count_array);

constraint forall(j in 1..m) (
  courier_distance[j] = sum(i in 2..max_path_length) (dist_matrix[route[j,i-1], route[j,i]])
); % compute courier distance

constraint max_distance = max(j in 1..m) (courier_distance[j]); % minimize maximum distance traveled

constraint max_distance >= min_path; % do not search for impossible solutions
constraint max_distance <= max_path; % do not search for impossible solutions

constraint symmetry_breaking_constraint(
  let {
    array[1..m] of var int: load =
      [ sum(i in 1..n where packs[i]=j)(item_size[i]) | j in 1..m ]
  } in
    forall(s in similars) (
      load[min(s)] <= load[max(s)]
      /\ courier_distance[min(s)] <= courier_distance[max(s)]
    )
);


solve :: int_search(route, dom_w_deg, indomain_min)
      :: restart_geometric(1.5, 1000)
      :: relax_and_reconstruct(array1d(route), 85)
      minimize max_distance;

output  [show(max_distance) ++ "\n"] ++
        [show(route[i,j]) ++ if j == max_path_length then "\n" else " " endif | i in 1..m, j in 1..max_path_length]
