import json
import ast

def chomped_lines(it):
    return map(operator.methodcaller('rstrip', '\r\n'), it)
c = []
with open("workflowdata.dat") as json_file:
    data = json.load(json_file)
    """
    for line in infile:
        #process(line)
        line = line.strip("\n")
        #print(line)
        c.append(line)
    """
#print(json.dumps(json.loads(ast.literal_eval(c))))
print(str(data))
