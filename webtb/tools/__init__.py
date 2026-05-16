def list_tools():
	import os
	import ast
	toolsdir = os.path.dirname(__file__)
	tools = []
	for tool in os.listdir(toolsdir):
		if not tool.startswith("__"):
			with open(os.path.join(toolsdir, tool), "r", encoding="utf-8") as fh:
				tree = ast.parse(fh.read())
			tools.append((
				os.path.splitext(tool)[0].replace("_","-"),
				ast.get_docstring(tree)
				))
	return tools
