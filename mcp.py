import os, shutil

from models.MIP.mip import Mip_model
from models.SMT.smt import Z3_smt_model
from instance import Instance
from os import listdir, makedirs
from os.path import isfile, join, exists
import argparse
import json
from json_parser import Json_parser

from typing import Union

# Set up the argument parser to accept a configuration file path
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--configuration_file", type=str)
json_parser = Json_parser()

def load_parameters():
    
    """
    Parses command line argument to get the path to configuration JSON file,
    then opens and loads the JSON content into a Python dictionary.
    """
    
    args = parser.parse_args()
    with open(args.configuration_file, "r", encoding="utf-8") as f:
        parameters = json.load(f)
    
    return parameters


def load_instances(instances_path: 'str') -> 'list[Instance]':
    
    """
    Loads all instance files found in the given directory.
    Sorts filenames, then creates an Instance object for each file.
    """
    
    instances_names = sorted([f for f in listdir(instances_path) if isfile(join(instances_path, f))])
    instances = []

    for instance_name in instances_names:
        instances.append(Instance(join(instances_path, instance_name)))

    return instances

def solve_mip(config: 'dict', instances_path: 'str'):
    
    """
    Solves the problem instances using MIP models.
    For each library and solver specified in config,
    builds the model, solves it, and saves the results.
    """
    
    libraries = config['library']
    instances = load_instances(instances_path)

    # Create export folder if specified and does not exist
    if config.get("export_folder", "") != "":
        if not exists(config['export_folder']):
            makedirs(config['export_folder'])

    # Iterate through each library and each instance
    for lib in libraries:
        for instance in instances:
            key = lib + '_solvers'
            solver_to_use = config[key]
            for solver_name in solver_to_use:
                print("============================================================================")
                print(f'loaded Mip model implemented with library {lib} and solver {solver_name}')
                print("============================================================================")
                print(f"solving instance {instance.name}")

                # Instantiate the solver model depending on the library
                if lib == 'mip':
                    solver = Mip_model(lib, instance, solver_name=solver_name)

                else:
                    raise Exception(f"unknown lib {lib}")

                sub_folders = lib + '_' + solver_name

                print("model built, now solving...")
                solver.solve(timeout=config['timeout'])
                result = solver.get_result()

                # Save results using JSON parser helper
                json_parser.save_results('MIP', instance.name, result, instance.max_load_indexes, sub_folders)
                print("<----------------------------------------------->")
                print(f'solution for library {lib}:')
                print(result)


def solve_smt(config: 'dict', instances_path: 'str'):
    
    """
    Solves the problem instances using SMT models.
    Uses only the first solver in the config's SMT solver list.
    """

    solver_to_use = config['solvers'][0]

    instances = load_instances(instances_path)

    if config.get("export_folder", "") != "":
        if not exists(config['export_folder']):
            makedirs(config['export_folder'])
    print(f'loaded SMT model implemented with z3')
    for instance in instances:
        print(f"solving instance {instance.name}")
        print("building model...")
        solver = Z3_smt_model("z3", instance)
        print("model built, now solving...")
        solver.solve(timeout=config['timeout'])
        result = solver.get_result()
        json_parser.save_results('SMT', instance.name, result, instance.max_load_indexes, solver_to_use)
        print("<----------------------------------------------->")
        print(f'solution:')
        print(result)


def merge_json_files(input_dir, output_dir, used_models):

    """
    Merges multiple JSON result files from different solvers into unified files per model.
    Clears output directory for used models before merging.
    """

    solvers = ['mip_CBC', 'z3_smt']
    instance_result_id = ['00', '01', '02', '03', '04', '05', '06', '07', '08', '07', '08', '09',
                          '10', '13', '16', '19']

    # Delete old results folders if they exist
    if os.path.exists(output_dir):
        for model in used_models:
            model_dir = os.path.join(output_dir, model.upper())
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)

    # Create output folders and merge data
    for m in used_models:
        model = m.upper()
        out_model_dir_path = os.path.join(output_dir, model)
        os.makedirs(out_model_dir_path)
        for i in instance_result_id:
            model_result_dict = {}
            instance_name = 'inst' + i + '.json'
            out_file_path = os.path.join(out_model_dir_path, instance_name)

            # Read results from all solvers for this instance and model
            for solver in solvers:
                input_file_path = os.path.join(input_dir, model)
                input_file_path = os.path.join(input_file_path, solver)
                input_file_path = os.path.join(input_file_path, instance_name)

                if os.path.exists(input_file_path):
                    with open(input_file_path, "r") as f:
                        data = json.load(f)
                        tmp = data[model]
                        model_result_dict[solver] = tmp

            # Write merged result if any solver data found
            if model_result_dict != {}:
                with open(out_file_path, "w") as f:
                    json.dump(model_result_dict, f)

    print('Results ready')


def main(config: 'dict'):

    """
    Main workflow:
    - Clears the input cache folder if it exists
    - Solves instances using requested models (MIP and/or SMT)
    - Merges all JSON results into consolidated files
    """

    input_directory = ".cache/results"
    output_directory = "res"
    models_to_use = config['usage_mode']['models_to_use']

    # Clear old results cache
    if os.path.exists(input_directory):
        shutil.rmtree(input_directory)

    if 'mip' in models_to_use:
        print("============================================================================")
        solve_mip(config['mip'], config['instances_path'])
    if 'smt' in models_to_use:
        print("============================================================================")
        solve_smt(config['smt'], config['instances_path'])

    # Merge all JSON result files into final output directory
    merge_json_files(input_directory, output_directory, models_to_use)


if __name__ == '__main__':
    main(load_parameters())
