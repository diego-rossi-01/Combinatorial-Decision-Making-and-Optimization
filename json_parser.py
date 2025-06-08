import json
import os


class Json_parser:
    # Define the paths for each approach's result folder
    def __init__(self, result_directory_path: 'str' = '.cache/results'): 
        self.result_directory_path = result_directory_path
        self.model_folders = {
            "MIP": os.path.join(result_directory_path, "MIP"),
            "SMT": os.path.join(result_directory_path, "SMT")
        }

    def save_results(self, model_name, instance_number, result, reorder_values, sub_folder="_None_"):

        # Create the approach's result folder if it doesn't exist
        if result['time'] > 300:
            result['time'] = 300

        if model_name in self.model_folders:
            if not os.path.exists(self.model_folders[model_name]):
                os.makedirs(self.model_folders[model_name])
            if sub_folder != "_None_":
                if not os.path.exists(os.path.join(self.model_folders[model_name], sub_folder)):
                    os.makedirs(os.path.join(self.model_folders[model_name], sub_folder))
        if not result['sol'] is None:
            new_sol = result['sol'].copy()
            for i in range(len(reorder_values)):
                new_sol[i] = result['sol'][reorder_values[i]]

            result['sol'] = new_sol
        if sub_folder != "_None_":
            instance_path = os.path.join(self.model_folders[model_name], sub_folder, f"{instance_number}.json")
        else:
            instance_path = os.path.join(self.model_folders[model_name], f"{instance_number}.json")
        with open(instance_path, "w") as json_file:
            json_file.write(json.dumps({model_name: result}, indent=4))
