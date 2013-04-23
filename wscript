#! /usr/bin/env python
#
# waf build script

from waflib import Options

APPNAME = "WafTestApp"

top = '.'
out = 'build'

def options(ctx):
	ctx.load('cs_ext', tooldir='waftools')

	ctx.add_option('--debug', '-d', dest='debug', action='store_true', default=False, help='Enable debug')

def configure(ctx):
	ctx.load('cs_ext', tooldir='waftools')

	if Options.options.debug:
		ctx.set_define('DEBUG')

	ctx.env.APPNAME = APPNAME

def build(bld):
	bld.recurse([
		'tests/csharp'
	])
