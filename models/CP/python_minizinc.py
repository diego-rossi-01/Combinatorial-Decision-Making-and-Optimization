#Importing libraries
import os
import subprocess
import io
import math
import re
import json
import tempfile
import sys
import time
import numpy as np

# Minizinc Model definition
cp_model = "basemodel.mzn"
cp_model_popen = "popenmodel.mzn"
cp_last_model = "lastmodel_sb.mzn"

def extract_route_from_row(row, origin):
    """
    Given a row [origin, node1, node2, ..., origin, ...]
    outputs the route cancelling the initial origin and stopping when origin is found again.
    """
    route = []
    for x in row[1:]:
        if x == origin:
            break
        route.append(x)
    return route

def extract_solution(text):
    """
    Extracts the solution from the gecode solver output text.
    """
    if "=ERROR=" in text:
        return {"time": 300, "optimal": False, "obj": "Error", "sol": []}
    if "=UNSATISFIABLE=" in text:
        return {"time": 300, "optimal": False, "obj": "UNSAT", "sol": []}

    lines = text.strip().splitlines()
    if not lines:
        return {"time": 300, "optimal": False, "obj": "N/A", "sol": []}

    index = 1 if "WARNING" in text else 0
    try:
        obj_value = int(lines[index])
    except (ValueError, IndexError):
        obj_value = "N/A"

    rest = text.partition('\n')[2]
    try:
        orders = np.genfromtxt(io.StringIO(rest.split('%')[0]), dtype=int)
    except Exception:
        orders = []

    if isinstance(orders, np.ndarray):
        if orders.ndim == 1:
            orders = [orders.tolist()]
        else:
            orders = orders.tolist()

    sol = []
    for row in orders:
        if row:
            origin = row[0]
            route = extract_route_from_row(row, origin)
            sol.append(route)

    try:
        time_val = float(re.findall(r"time elapsed: (\d+\.\d+)", text)[0])
        time_val = math.floor(time_val)
    except Exception:
        time_val = 300

    optimal = (time_val < 300)
    return {"time": time_val, "optimal": optimal, "obj": obj_value, "sol": sol}

def extract_solution_chuffed(output_text):
    """
    Extracts the solution from the chuffed solver output text.
    """
    lines = output_text.strip().splitlines()

    if not lines:
        return {"time": 300, "optimal": False, "obj": "N/A", "sol": []}

    obj_value = "N/A"
    first_line = lines[0].strip()

    m = re.match(r"^\s*(\-?\d+)\s*$", first_line)
    if m:
        obj_value = int(m.group(1))
    else: 
        obj_value = int(re.match(r"^\s*(\-?\d+)\s*$", lines[1].strip()).group(1))

    sol = []
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('%') or line.startswith('----') or line.startswith('===='):
            break
        try:
            row = [int(x) for x in line.split()]
        except ValueError:
            continue
        if not row:
            continue
        origin = row[0]
        route = extract_route_from_row(row, origin)
        if route:
            sol.append(route)

    time_val = 300
    match = re.search(r"%\s*time elapsed:\s*([\d\.]+)\s*s", output_text)
    if match:
        try:
            t = float(match.group(1))
            time_val = math.floor(t)
        except:
            pass

    optimal = (time_val < 300)
    return {"time": time_val, "optimal": optimal, "obj": obj_value, "sol": sol}


def sort_instance_capacities(original_file):
    """
    Reads the .dzn file, extracts 'capacity' and 'original_indices' arrays,
    sorts capacities in descending order, writes a temporary .dzn with sorted capacities,
    and returns (tmp_file_name, mapping).
    """
    
    with open(original_file, "r") as f:
        content = f.read()

    match_cap = re.search(r"capacity\s*=\s*(\[[^\]]+\])", content)
    if not match_cap:
        raise ValueError("Array 'capacity' not found in the instance file")
    capacities = eval(match_cap.group(1))

    match_orig = re.search(r"original_indices\s*=\s*(\[[^\]]+\])", content)
    if not match_orig:
        raise ValueError("Array 'original_indices' not found in the instance file")
    orig_indices = eval(match_orig.group(1))

    indices = list(range(len(capacities)))
    sorted_order = sorted(indices, key=lambda i: capacities[i], reverse=True)

    sorted_capacities = [capacities[i] for i in sorted_order]
    mapping = [orig_indices[i] + 1 for i in sorted_order]

    new_content = re.sub(
        r"capacity\s*=\s*\[[^\]]+\]",
        f"capacity = {sorted_capacities}",
        content
    )

    tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".dzn")
    tmp_file.write(new_content)
    tmp_file.close()

    return tmp_file.name, mapping

def remap_solution(solution, original_indices):
    """
    Remaps the solver’s courier routes back to the original order.
    """
    remapped_routes = [None] * len(original_indices)
    original_routes = solution.get("sol", [])

    for i, route in enumerate(original_routes):
        if i < len(original_indices):
            original_index = original_indices[i] - 1
            if 0 <= original_index < len(remapped_routes):
                remapped_routes[original_index] = route

    solution["sol"] = [r for r in remapped_routes if r is not None]
    return solution

def run_solver_run(command, timeout):
    """
    Executes solvers with subprocess.run and outputs full stdout as a string.
    """
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print("Timeout (run)!")
        output_text = ''
        return output_text

def solve_with_run(instance_file):
    """
    Wrapper for subprocess.run
    In case of KeyboardInterrupt, cleans the temporary file and outputs a "Interrupted" dictionary.
    """
    tmp_instance_file, mapping = sort_instance_capacities(instance_file)

    model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), cp_model)
    cmd = [
        "minizinc",
        "--solver", "org.gecode.gecode",
        "--output-time", "--solver-time-limit", "300000",
        model_path,
        tmp_instance_file
    ]

    try:
        output_text = run_solver_run(cmd, timeout=300)
    except KeyboardInterrupt:
        print("Interrupted during execution.")
        os.remove(tmp_instance_file)
        return {"time": 300, "optimal": False, "obj": "N/A", "sol": []}

    solution_gecode = extract_solution(output_text)
    solution_gecode = remap_solution(solution_gecode, mapping)

    print("Finished running model Cp_model with gecode solver")
    print(solution_gecode)

    tmp_instance_file, mapping = sort_instance_capacities(instance_file)

    model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), cp_model)
    cmd = [
        "minizinc",
        "--solver", "org.chuffed.chuffed",
        "--output-time", "--solver-time-limit", "300000",
        model_path,
        tmp_instance_file
    ]

    try:
        output_text = run_solver_run(cmd, timeout=300)
    except KeyboardInterrupt:
        print("Interrupted during execution.")
        os.remove(tmp_instance_file)
        return {"time": 300, "optimal": False, "obj": "N/A", "sol": []}

    solution_chuffed = extract_solution_chuffed(output_text)
    solution_chuffed = remap_solution(solution_chuffed, mapping)

    print("Finished running model Cp_model with chuffed solver")
    print(solution_chuffed)

    os.remove(tmp_instance_file)    
    return solution_gecode, solution_chuffed

def run_solver_popen(command, timeout):
    """
    Executes the solver with subprocess.Popen, catching the output row by row
    mantaining only the last chunk, outputted as a string.
    """
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1 
        )
    except Exception as e:
        raise RuntimeError(f"Impossible to run solver: {e}")

        last_chunk_text = ""
    current_chunk = []
    start_time = time.time()

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        stripped = line.strip()
        if stripped == "==========":
            proc.kill()
            return last_chunk_text
        if stripped == "----------":
            chunk_text = "".join(current_chunk)
            if chunk_text.strip():
                last_chunk_text = chunk_text
            current_chunk = []
        else:
            current_chunk.append(line)

        if proc.poll() is not None:
            break

        if time.time() - start_time > timeout:
            proc.kill()
            break

    remaining = proc.stdout.read()
    if remaining:
        current_chunk.append(remaining)

    if current_chunk:
        chunk_text = "".join(current_chunk)
        if chunk_text.strip():
            last_chunk_text = chunk_text

    return last_chunk_text


def solve_with_popen(instance_file):
    """
    Wrapper for subprocess.Popen.
    In case of KeyboardInterrupt, cleans the temporary file and outputs an "Interrupted" dictionary.
    """
    tmp_instance_file, mapping = sort_instance_capacities(instance_file)

    model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), cp_model_popen)
    cmd = [
        "minizinc",
        "--solver", "org.gecode.gecode",
        "--output-time", "--solver-time-limit", "300000",
        model_path,
        tmp_instance_file
    ]

    try:
        last_chunk = run_solver_popen(cmd, timeout=300)
        solution = extract_solution(last_chunk)
        solution = remap_solution(solution, mapping)
        print("Finished running model Cp_model_popen")
        print(solution)
    except KeyboardInterrupt:
        os.remove(tmp_instance_file)
        return {"time": 300, "optimal": False, "obj": "Interrupted", "sol": []}

    tmp_instance_file, mapping = sort_instance_capacities(instance_file)

    model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), cp_last_model)
    cmd = [
        "minizinc",
        "--solver", "org.gecode.gecode",
        "--output-time", "--solver-time-limit", "300000",
        model_path,
        tmp_instance_file
    ]

    try:
        last_chunk = run_solver_popen(cmd, timeout=300)
        solution_last = extract_solution(last_chunk)
        solution_last = remap_solution(solution_last, mapping)
        print("Finished running model Cp_last_model")
        print(solution_last)
    except KeyboardInterrupt:
        os.remove(tmp_instance_file)
        return {"time": 300, "optimal": False, "obj": "Interrupted", "sol": []}

    return solution, solution_last

def run_both_and_save(instance_file, output_folder):
    """
    For a single instance (.dzn):
      – if < inst11 → solve_with_run() + solve_with_popen() are both executed
        and solutions are saved in a single JSON file.
    """
    sol_gecode, sol_chuffed = solve_with_run(instance_file)
    sol_popen, sol_gecode_sb = solve_with_popen(instance_file)

    combined = {
        "Cp_model_gecode": sol_gecode,
        "Cp_model_chuffed": sol_chuffed,
        "Cp_model_popen": sol_popen,
        "Cp_model_gecode_sb": sol_gecode_sb
    }

    basename = os.path.basename(instance_file)
    inst_number = int(basename[4:6])
    output_path = os.path.join(output_folder, f"{inst_number}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

def run_only_popen_and_save(instance_file, output_folder):
    """
    For instances ≥ inst11.dzn:
      – solve_with_popen() is executed and solution is saved in a JSON file.
    """
    sol_popen, sol_gecode_sb = solve_with_popen(instance_file)

    single = {
        "Cp_model_popen": sol_popen,
        "Cp_model_gecode_sb": sol_gecode_sb
    }
    
    basename = os.path.basename(instance_file)
    inst_number = int(basename[4:6])
    output_path = os.path.join(output_folder, f"{inst_number}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(single, f, indent=2, ensure_ascii=False)

def main(args):
    data_folder = "output_instances"
    output_folder1 = os.path.join("..", "..")
    output_folder2 = os.path.join("res", "CP")
    output_folder = os.path.join(output_folder1, output_folder2)
    os.makedirs(output_folder, exist_ok=True)

    instance_files = [
#        "inst01.dzn", "inst02.dzn", "inst03.dzn", "inst04.dzn", "inst05.dzn",
#        "inst06.dzn", "inst07.dzn", "inst08.dzn", "inst09.dzn", "inst10.dzn",
#        "inst13.dzn", "inst16.dzn", "inst19.dzn",
    ]

    for filename in instance_files:
        filepath = os.path.join(data_folder, filename)
        inst_number = int(filename[4:6])

        if inst_number >= 11:
            run_only_popen_and_save(filepath, output_folder)
        else:
            run_both_and_save(filepath, output_folder)

if __name__ == "__main__":
    main(sys.argv)
