def display(bf, directory):
    # Identify the questions to ask (not calling methods yet)
    questions = {
	"proc": bf.q.ospfProcessConfiguration,
	"intf": bf.q.ospfInterfaceConfiguration,
	"area": bf.q.ospfAreaConfiguration,
	"l3if": bf.q.layer3Edges,
	"scmp": bf.q.ospfSessionCompatibility,
	"nbrs": bf.q.ospfEdges,
	"rtes": bf.q.routes,
    }

    # Unpack dictionary tuples and iterate over them
    for short_name, question in questions.items():
	# Ask the question and store the response pandas frame
	pandas_frame = question().answer().frame()
	print(f"---{short_name}---\n{pandas_frame}\n")

	# Assemble the generic file name prefix
	file_name = f"outputs/{short_name}_{directory}"

	# Generate JSON data for programmatic consumption
	json_data = json.loads(pandas_frame.to_json(orient="records"))
	with open(f"{file_name}.json", "w") as handle:
	    json.dump(json_data, handle, indent=2)
