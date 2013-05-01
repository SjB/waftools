#! /usr/bin/env python
#
# waf build script

import os
from waflib import Options

APPNAME = "WafTestApp"
VERSION = "0.8"

top = '.'
out = 'build'

def options(ctx):
	ctx.load('cs_extra etoform', tooldir='waftools')

	ctx.add_option('--debug', '-d', dest='debug', action='store_true', default=False, help='Enable debug')
	ctx.add_option('--with-assemblydir', type='string', dest='assembly_dir',
					help='localtion of personal library')

def configure(ctx):
	ctx.load('cs_extra test etoform', tooldir='waftools')

	if Options.options.debug:
		ctx.set_define('DEBUG')

	assembly_dir = Options.options.assembly_dir
	if not assembly_dir:
		assembly_dir = os.environ.get('ASSEMBLY_DIR', './libs')

	ctx.check_assembly("AudiologyWidgets", path_list = [x % assembly_dir for x in ['%s', '%s/AudiologyWidgets']])

	ctx.env.APPNAME = APPNAME

def build(bld):
	bld.recurse([
		'tests/csharp'
	])
