#! /usr/bin/env python
# encoding: utf-8
# Steve Beaulac, 2013 (SjB)

import os
from waflib import Task
from waflib.TaskGen import extension

def options(opt):
	opt.add_option('--with-resgen-binary', type='string', dest='resgenbinary', help='localtion of the resgen binary')

def configure(conf):
	resgen = getattr(Options.options, 'resgenbinary', 'resgen')
	conf.find_program([resgen], var='RESGEN')
	conf.env.RESGENFLAGS = '/useSourcePath'

@extension('.resx')
def resx_file(self, node):
	"""
	Bind the .resx extension to a resgen task
	"""
	if not getattr(self, 'cs_task', None):
		self.bld.fatal('resx_file has no link task for use %r' % self)

	# Given assembly 'Foo' and file 'Sub/Dir/File.resx', create 'Foo.Sub.Dir.File.resources'
	assembly = os.path.splitext(self.gen)[0]
	res = os.path.splitext(node.path_from(self.path))[0].replace('/', '.')
	out = self.path.find_or_declare(assembly + '.' + res + '.resources')

	tsk = self.create_task('resgen', node, out)

	self.cs_task.dep_nodes.extend(tsk.outputs) # dependency
	self.env.append_value('RESOURCES', tsk.outputs[0].bldpath())

class resgen(Task.Task):
	"""
	Compile C# resource files
	"""
	color   = 'YELLOW'
	run_str = '${RESGEN} ${RESGENFLAGS} ${SRC} ${TGT}'
