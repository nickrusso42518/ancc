# TODO decouple json and data normalization
# TODO re-add csv output
"""
keys = to_csv[0].keys()

with open('people.csv', 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(to_csv)
"""

import json
import textfsm
import csv
import os
from ntc_templates.parse import parse_output

# Specify your desired parsed outputs here
OUTPUTS = [
    {"platform": "cisco_ios", "command": "show ip ospf neighbor"},
    {"platform": "cisco_ios", "command": "show ip ospf interface brief"},
    {"platform": "cisco_ios", "command": "show ip ospf database"},
    {"platform": "juniper_junos", "command": "show ospf neighbor"},
    {"platform": "juniper_junos", "command": "show ospf interface"},
    {"platform": "juniper_junos", "command": "show ospf database"},
]


def to_json_file(prefix, records, fsm=None):
    """
    Write the records to the output file named <prefix>.json on disk. If
    fsm is defined, it indicates a custom template. If not, it assumes
    an NTC template. The resulting JSON structure is always a single-depth
    list of dictionaries.
    """

    # If fsm is defined, it's a custom template. Need to map variable names
    # (fsm.headers) with the tabular values, which isn't automatic
    new_records = []
    if fsm:
        #data = [dict(zip(fsm.header, _try_ints(record))) for record in records]

        # Loop over each row in matrix, then try to convert each value to
        # an integer without creating a new list. Ignore failure; retain value.
        for record in records:
            for i in range(len(record)):
                try:
                    record[i] = int(record[i])
                except ValueError:
                    pass

            # Add a new dict to the list with the headers (keys) and values
            new_records.append(dict(zip(fsm.header, record)))

    # Else, it's an NTC template, records is a list of dicts, not a matrix
    else:

        # Loop over each dict in list, then iterate over the keys. Try to parse
        # integers without creating a new dict. Ignore failure; retain value.
        for record in records:
            for key in record.keys():
                try:
                    record[key] = int(record[key])
                except ValueError:
                    pass

            # Basic reference so generic write operation can succeed
            new_records = records

    with open(f"outputs/{prefix}.json", "w", encoding="utf-8") as handle:
        json.dump(new_records, handle, indent=2)


def main():
    """
    Execution starts here.
    """

    #features = ["junos_ospf_intfs", "junos_ospf_lsdb"]
    #output_functions = [to_csv_file, to_json_file]
    output_functions = [to_json_file]

    # Create the outputs/ directory if it doesn't exist
    if not os.path.exists("outputs"):
        os.makedirs("outputs")

    # For each desired output in the global list
    for output in OUTPUTS:

        # Assemble the file prefix for each desired output
        prefix = f"{output['platform']}_{output['command'].replace(' ', '_')}"
        print(f"Processing output: {prefix}")

        # Load the input data from plain-text file
        with open(f"input/{prefix}.txt", "r", encoding="utf-8") as handle:
            data = handle.read()

        # Try to parse using an NTC template. It only raises a generic
        # "Exception", but we can catch it and check the message
        try:
            records = parse_output(data=data, **output)
            fsm = None
        except Exception as exc:
            # Don't have a template, try a custom one
            if "No template found" in str(exc):
                fsm, records = parse_custom(prefix, data)
            # Some other error occurred; re-raise
            else:
                raise

        # Print the output using a variety of outputs
        for output_function in output_functions:
            output_function(prefix, records, fsm)
        

def parse_custom(prefix, data):
    """
    Given a file prefix and plain-text input data, load a custom
    textfsm template and attempt to parse records from the data.
    Returns the list of records in matrix form.
    """

    # Open the textfsm template, initialize the FSM, and parse the records
    with open(f"templates/{prefix}.textfsm", "r", encoding="utf-8") as handle:
        fsm = textfsm.TextFSM(handle)
        records = fsm.ParseText(data.strip())

    # Ensure that the number of column headers equals the number
    # of fields in each record, or else tabular format is ruined
    assert all([len(fsm.header) == len(record) for record in records])
    return (fsm, records)


if __name__ == "__main__":
    main()
