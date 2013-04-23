## Waf ##

### The flexible build system ###

Waf is a Python-based framework for configuring, compiling and installing applications.
It derives from the concepts of other build tools such as Scons, Autotools, CMake or Ant.

[waf website][waf]

### This repo ###

This repo contains extra tools not included in the default waf system.

These tools can be copied into your source tree and used by waf by 
include these line in your waf **wscript**


	def options(opt):
		opt.tool_options('cs', tooldir='tools')

where `cs` is the python tool file and `tools` is the directory containing the `cs.py` file

[waf]: http://waf.googlecode.com
