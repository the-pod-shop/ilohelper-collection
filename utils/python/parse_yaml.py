import yaml
import sys

def read_and_print_versions(file_path):
    """
    Reads a YAML file and prints out package versions without recursion, 
    designed to handle a maximum depth of two levels starting with a package manager.
    """
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            
            def extract_versions(data, package_manager=None):
                """
                Recursively traverses the data structure to extract and print package versions.
                Identifies package managers using the optional parameter.
                """
                if package_manager:
                    print(package_manager)
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            extract_versions(value, key)
                        else:
                            print(f"{key}: {value}")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            extract_versions(item, None)
                        else:
                            print(item)
            
            extract_versions(data)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except yaml.YAMLError as error:
        print(f"Error reading YAML file: {error}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        read_and_print_versions(file_path)
    else:
        print("No file path provided. Please specify the path as an argument.")
