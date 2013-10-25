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
	ctx.load('cs etoform csproj', tooldir='extra')

	ctx.add_option('--debug', '-d', dest='debug', action='store_true', default=False, help='Enable debug')
	ctx.add_option('--with-assemblydir', type='string', dest='assembly_dir',
					help='localtion of personal library')

def configure(ctx):
	ctx.load('cs etoform nunit csproj', tooldir='extra')

	if Options.options.debug:
		ctx.set_define('DEBUG')

	assembly_dir = Options.options.assembly_dir
	if not assembly_dir:
		assembly_dir = os.environ.get('ASSEMBLY_DIR', './libs')

	ctx.check_pkg("gtk-sharp-2.0")
	ctx.check_pkg("glib-sharp-2.0", uselib_store = "GLIB")

	ctx.check_assembly("AudiologyWidgets", path_list = [x % assembly_dir for x in ['%s', '%s/AudiologyWidgets']])
	ctx.check_etoform(path_list = [x % assembly_dir for x in ['%s', '%s/Eto']])

	ctx.check_nunit()

	ctx.env.APPNAME = APPNAME

def build(bld):
	bld.recurse([
		'tests/csharp'
	])
