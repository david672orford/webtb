import sys
from webtb.tools import list_tools
from importlib import import_module

def main():
	if len(sys.argv) < 2:
		print(f"Usage: {sys.argv[0]} [command] [options...]")
		print("Available commands:")
		for name, docstring in sorted(list_tools()):
			print(f" {name:20} {docstring}")
		sys.exit(0)
	tool_name = sys.argv[1]
	tool_module = import_module(f"webtb.tools.{tool_name.replace('-','_')}")
	retval = tool_module.main(sys.argv[2:])
	sys.exit(retval)
