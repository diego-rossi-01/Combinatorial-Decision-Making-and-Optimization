import os
import numpy as np

def read_dat_file(dat_file):
    with open(dat_file, 'r') as file:
        lines = [line.strip() for line in file.readlines()]

    #M and n    
    m = int(lines[0])                     
    n = int(lines[1])                    

    #Capacities (ordered from the biggest to the smallest)
    original_capacities = list(map(int, lines[2].split()))
    
    indexed_capacities = list(enumerate(original_capacities))
    sorted_capacities_desc = sorted(indexed_capacities, key=lambda x: x[1], reverse=True)
    ordered_capacities = [cap for _, cap in sorted_capacities_desc]
    original_indices = [idx for idx, _ in sorted_capacities_desc]

    max_load = sorted(original_capacities)
    
    item_sizes = list(map(int, lines[3].split()))
    
    #Distance Matrix
    distance_matrix = [list(map(int, line.split())) for line in lines[4:]]
    
    return m, n, ordered_capacities, original_indices, max_load, item_sizes, distance_matrix

def compute_bounds(distance_matrix, max_load, size, m, n):
    o = n

    # Recursive function for calculating paths
    def compute_path(current_cost, nodes, select, steps):
        if steps > len(nodes) - 1:
            next_step, cost = select(nodes)
            updated_nodes = nodes + [next_step]
            cost += current_cost
            return compute_path(cost, updated_nodes, select, steps)
        return {'p': nodes, 'c': current_cost}
    
    # Function that selects the min_path
    def min_select(nodes):
        row = list(distance_matrix[nodes[-1]])
        high_value = max(row) + 1
        for j in nodes:
            row[j] = high_value
        c = min(row)
        i = row.index(c)
        return i, c

    max_weight = sum(max_load[1:])
    ordered_size = sorted(size)
    
    k = 1
    while k < n and sum(ordered_size[:n - k]) > max_weight:
        k += 1

    if k == 1:
        min_path = max([ distance_matrix[o][i] + distance_matrix[i][o] for i in range(n) ])
    else:
        min_origin = min([ distance_matrix[i][o] for i in range(n) ])
        min_path = max([ int(compute_path(distance_matrix[o][i], [o, i], min_select, k)['c']) + min_origin for i in range(n) ])
    
    #min_packs = smallest number of packs that each courier has to carry
    k_temp = 1
    while k_temp < n and sum(ordered_size[:n - k_temp]) > max_weight:
        k_temp += 1
    min_packs = k_temp 
    
    #max_packs = maximum number of packs that a courier can carry
    k_val = 1
    while k_val < n and sum(ordered_size[:k_val]) < max_load[-1]:
        k_val += 1
    max_packs = min(k_val, n - m + 1) 
    
    # Function that selects the max_path
    def max_select(nodes):
        row = list(distance_matrix[nodes[-1]])
        for j in nodes:
            row[j] = -1
        c = max(row)
        i = row.index(c)
        return i, c

    max_paths = [ compute_path(distance_matrix[o][i], [o, i], max_select, k_val) for i in range(n) ]
    max_path = max([ int(item['c']) + distance_matrix[item['p'][-1]][o] for item in max_paths ])
    
    return min_path, max_path, min_packs, max_packs

def write_dzn_file(dzn_file, m, n, ordered_capacities, original_indices, max_load, item_sizes, distance_matrix,
                   min_path, max_path, min_packs, max_packs):
    
    n_array = [i+1 for i in range(n+1)]         # array[1..n+1]
    origin = n + 1                              # origin = n+1
    number_of_origin_stops = ((max_packs + 2) * m) - n
    count_array = [1]*n + [number_of_origin_stops]  # array[1..n+1]
    
    with open(dzn_file, 'w') as file:
        file.write(f"m = {m};\n")
        file.write(f"n = {n};\n")
        file.write(f"capacity = {ordered_capacities};\n")
        file.write(f"item_size = {item_sizes};\n")
        file.write("dist_matrix = [|")
        for row in distance_matrix:
            file.write(", ".join(map(str, row)) + "\n             |")
        file.write("];\n")
        file.write(f"original_indices = {original_indices};\n")
        file.write(f"min_path = {min_path};\n")
        file.write(f"max_path = {max_path};\n")
        file.write(f"n_array = {n_array};\n")
        file.write(f"count_array = {count_array};\n")
        file.write(f"max_packs = {max_packs};\n")
        file.write(f"origin = {origin};\n")
        file.write(f"min_packs = {min_packs};\n")

if __name__ == "__main__":
    input_folder = "instances"
    output_folder = "output_instances"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".dat"):
            input_dat_file = os.path.join(input_folder, filename)
            output_dzn_file = os.path.join(output_folder, filename.replace(".dat", ".dzn"))
            
            m, n, ordered_capacities, original_indices, max_load, item_sizes, distance_matrix = read_dat_file(input_dat_file)
            
            min_path, max_path, min_packs, max_packs = compute_bounds(distance_matrix, max_load, item_sizes, m, n)
            
            write_dzn_file(output_dzn_file, m, n, ordered_capacities, original_indices, max_load, item_sizes,
                           distance_matrix, min_path, max_path, min_packs, max_packs)
            
            print(f"{input_dat_file} -> {output_dzn_file} updated")