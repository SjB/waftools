#!/usr/bin/env python
# encoding: utf-8
# Steve Beaulac, 2013 (SjB)
# original author: Thomas Nagy, 2006-2010 (ita)

"""
C# support. A simple example::

	def configure(conf):
		conf.load('cs')
	def build(bld):
		bld(features='cs', source='main.cs', target='foo')

Note that the configuration may compile C# snippets::

	FRAG = '''
	namespace Moo {
		public class Test { public static int Main(string[] args) { return 0; } }
	}'''
	def configure(conf):
		conf.check(features='cs', fragment=FRAG, compile_filename='test.cs', target='test.exe',
			bintype='exe', csflags=['-pkg:gtk-sharp-2.0'], msg='Checking for Gtksharp support')
"""

import os, shutil, tempfile

from waflib import Context, Errors, Logs, Options, Task, Utils, Node
from waflib.Configure import conf
from waflib.TaskGen import after, before, extension, feature
from waflib.Tools import ccroot

ccroot.USELIB_VARS['cs'] = set(['CSFLAGS', 'ASSEMBLIES', 'RESOURCES'])
ccroot.lib_patterns['csshlib'] = ['%s']

@extension('.cs')
def process_cs(self, node):
	pass

@feature('cs')
@after('process_source')
def apply_cs(self):
	"""
	Create a C# task bound to the attribute *cs_task*. There can be only one C# task by task generator.
	"""
	cs_nodes = []
	no_nodes = []

	for x in self.to_nodes(self.source):
		if x.name.endswith('.cs'):
			cs_nodes.append(x)
		else:
			no_nodes.append(x)
	self.source = no_nodes
	bintype = getattr(self, 'bintype', self.target.endswith('.dll') and 'library' or 'exe')
	self.cs_task = tsk = self.create_task('mcs', cs_nodes, self.path.find_or_declare(self.target))
	tsk.env.CSTYPE = '/target:%s' % bintype
	tsk.env.OUT = '/out:%s' % tsk.outputs[0].abspath()
	self.env.append_value('CSFLAGS', '/platform:%s' % getattr(self, 'platform', 'anycpu'))

	inst_to = getattr(self, 'install_path', bintype=='exe' and '${BINDIR}' or '${LIBDIR}')
	if inst_to:
		# note: we are making a copy, so the files added to cs_task.outputs won't be installed automatically
		mod = getattr(self, 'chmod', bintype=='exe' and Utils.O755 or Utils.O644)
		self.install_task = self.bld.install_files(inst_to, self.cs_task.outputs[:], env=self.env, chmod=mod)

@feature('cs')
@after('apply_cs')
def use_cs(self):
	"""
	C# applications honor the **use** keyword::

		def build(bld):
			bld(features='cs', source='My.cs', bintype='library', gen='my.dll', name='mylib')
			bld(features='cs', source='Hi.cs', includes='.', bintype='exe', target='hi.exe', use='mylib', name='hi')
	"""
	names = self.to_list(getattr(self, 'use', []))
	get = self.bld.get_tgen_by_name
	for x in names:
		uselib = x.upper()

		pkg = getattr(self.env, 'PKG_' + uselib, [])
		if len(pkg) and self.env.CS_NAME == "mono":
			self.env.append_value('CSFLAGS', '/pkg:%s' % pkg)
			continue

		csflags = getattr(self.env, 'CSFLAGS_' + uselib, [])
		if len(csflags):
			self.env.append_value('CSFLAGS', csflags);
			continue

		try:
			y = get(x)
		except Errors.WafError:
			self.env.append_value('CSFLAGS', '/reference:%s' % x)
			continue
		y.post()

		tsk = getattr(y, 'cs_task', None) or getattr(y, 'link_task', None)
		if not tsk:
			self.bld.fatal('cs task has no link task for use %r' % self)

		self.cs_task.dep_nodes.extend(tsk.outputs) # dependency
		self.cs_task.set_run_after(tsk) # order (redundant, the order is infered from the nodes inputs/outputs)
		self.env.append_value('CSFLAGS', '/reference:%s' % tsk.outputs[0].abspath())

@feature('cs')
@after('apply_cs', 'use_cs')
def debug_cs(self):
	"""
	The C# targets may create .mdb or .pdb files::

		def build(bld):
			bld(features='cs', source='My.cs', bintype='library', target='my.dll', csdebug='full')
			# csdebug is a value in [True, 'full', 'pdbonly']
	"""
	csdebug = getattr(self, 'csdebug', self.env.CSDEBUG)
	if not csdebug:
		return

	node = self.cs_task.outputs[0]
	if self.env.CS_NAME == 'mono':
		out = node.parent.find_or_declare(node.name + '.mdb')
	else:
		out = node.change_ext('.pdb')
	self.cs_task.outputs.append(out)
	try:
		self.install_task.source.append(out)
	except AttributeError:
		pass

	if csdebug == 'pdbonly':
		val = ['/debug+', '/debug:pdbonly']
	elif csdebug == 'full':
		val = ['/debug+', '/debug:full']
	else:
		val = ['/debug-']
	self.env.append_value('CSFLAGS', val)


@extension('.cs.in')
def process_in(self, node):
	"""
	Converts the *.cs.in source files into *.cs files replacing all @var@ with
	the appropriate values in the related variable in the ctx.Define array
	"""

	tgt = node.change_ext('.cs', ext_in='.cs.in')
	tsk = self.create_task('subst', node, tgt)

	for x in self.env['DEFINES']:
		(k, v) = x.split('=')
		setattr(tsk.generator, k, v)

	self.source.append(tgt)

class mcs(Task.Task):
	"""
	Compile C# files
	"""
	color   = 'YELLOW'
	run_str = '${MCS} ${CSTYPE} ${CSFLAGS} ${ASS_ST:ASSEMBLIES} ${RES_ST:RESOURCES} ${OUT} ${SRC}'

	def exec_command(self, cmd, **kw):
		bld = self.generator.bld

		try:
			if not kw.get('cwd', None):
				kw['cwd'] = bld.cwd
		except AttributeError:
			bld.cwd = kw['cwd'] = bld.variant_dir

		try:
			tmp = None
			if isinstance(cmd, list) and len(' '.join(cmd)) >= 8192:
				program = cmd[0] #unquoted program name, otherwise exec_command will fail
				cmd = [self.quote_response_command(x) for x in cmd]
				(fd, tmp) = tempfile.mkstemp()
				os.write(fd, '\r\n'.join(i.replace('\\', '\\\\') for i in cmd[1:]).encode())
				os.close(fd)
				cmd = [program, '@' + tmp]
			# no return here, that's on purpose
			ret = self.generator.bld.exec_command(cmd, **kw)
		finally:
			if tmp:
				try:
					os.remove(tmp)
				except OSError:
					pass # anti-virus and indexers can keep the files open -_-
		return ret

	def quote_response_command(self, flag):
		# /noconfig is not allowed when using response files
		if flag.lower() == '/noconfig':
			return ''

		if flag.find(' ') > -1:
			for x in ('/r:', '/reference:', '/resource:', '/lib:', '/out:'):
				if flag.startswith(x):
					flag = '%s"%s"' % (x, '","'.join(flag[len(x):].split(',')))
					break
			else:
				flag = '"%s"' % flag
		return flag


def configure(conf):
	"""
	Find a C# compiler, set the variable MCS for the compiler and CS_NAME (mono or csc)
	"""
	csc = getattr(Options.options, 'cscbinary', None)
	if csc:
		conf.env.MCS = csc
	conf.find_program(['csc', 'dmcs', 'gmcs', 'mcs'], var='MCS')
	conf.env.ASS_ST = '/r:%s'
	conf.env.RES_ST = '/resource:%s'

	conf.env.CS_NAME = 'csc'
	if str(conf.env.MCS).lower().find('mcs') > -1:
		conf.env.CS_NAME = 'mono'

	conf.env.package_dep_lib = getattr(Options.options, 'package_dep_lib', False)

	# new variable that allow the sdk version to be specified at the command line.
	sdk_version = getattr(Options.options, 'sdk_version', None)
	if sdk_version:
		self.env.append_value('CSFLAGS', '/sdk:%s' % sdk_version)

	debug = getattr(Options.options, 'debug', None)
	if debug:
		conf.env.append_value('CSFLAGS', '/define:DEBUG')
		conf.env.CSDEBUG = debug;


def options(opt):
	"""
	Add a command-line option for the configuration::

		$ waf configure --with-csc-binary=/foo/bar/mcs
	"""
	opt.add_option('--with-csc-binary', type='string', dest='cscbinary')
	opt.add_option('--sdk', type='string', dest='sdk_version', default=None, help='Specifies SDK version of referenced assemlies')
	opt.add_option('--package-dep', dest='package_dep_lib', action='store_true', default=False, help='Package all dependent library with project')
	opt.add_option('--debug', '-d', type='string', dest='debug', default=None, help='Enable debug')


class fake_csshlib(Task.Task):
	"""
	Task used for reading a foreign .net assembly and adding the dependency on it
	"""
	color   = 'YELLOW'
	inst_to = None

	def runnable_status(self):
		for x in self.outputs:
			x.sig = Utils.h_file(x.abspath())
		return Task.SKIP_ME

@conf
def read_csshlib(self, name, paths=[]):
	"""
	Read a foreign .net assembly for the *use* system::

		def build(bld):
			bld.read_csshlib('ManagedLibrary.dll', paths=[bld.env.mylibrarypath])
			bld(features='cs', source='Hi.cs', bintype='exe', gen='hi.exe', use='ManagedLibrary.dll')

	:param name: Name of the library
	:type name: string
	:param paths: Folders in which the library may be found
	:type paths: list of string
	:return: A task generator having the feature *fake_lib* which will call :py:func:`waflib.Tools.ccroot.process_lib`
	:rtype: :py:class:`waflib.TaskGen.task_gen`
	"""
	try:
		return self.get_tgen_by_name(name)
	except Errors.WafError:
		pass
	return self(name=name, features='fake_lib', lib_paths=paths, lib_type='csshlib')

@conf
def read_assembly(self, name, install_path = None):
	"""
	Read a foreign .net assembly  that was validated via the check_assembly fun
	"""
	uselib = name.upper()

	if getattr(self.env, 'PKG_' + uselib, None):
		return

	csflags = getattr(self.env, 'CSFLAGS_' + uselib, None)
	if not csflags:
		self.fatal('Assembly %s not registered as a C sharp assembly' % name)

	flag = csflags[0]
	assembly = flag[3:]
	filename = os.path.basename(assembly)
	path = os.path.dirname(assembly)
	tg = self.read_csshlib(filename, paths=[path])
	if install_path:
		d = self.root.find_node(path)
		if not d:
			self.fatal('Can\'t find assembly path')
		f = d.find_node(filename)
		self.install_files(install_path, f)

		return tg


@conf
def import_resources(self, resources, namespace = None):
	return [res_to_str(x, namespace) for x in resources if x is not None]



def res_to_str(res, namespace = None):

	if res is None:
		return None

	if isinstance(res, Node.Node):
		(path, link) = (res.abspath(), res.name)
	else:
		(path, link) = (res, os.path.basename(res))

	if namespace is not None:
		link = '%s.%s' % (namespace, link)

	return '{0},{1}'.format(path, link)


@conf
def check_pkg(self, *k, **kw):
	if k:
		lst = k[0].split()
		kw['package'] = lst[0]
		kw['args'] = ' '.join(lst[1:])

	env = kw.get('env', self.env)
	uselib = kw.get('uselib_store', kw['package']).upper()

	if 'args' in kw:
		kw['args'] = Utils.to_list(kw['args'])
		kw['args'].append('--libs')

	ret = self.check_cfg(**kw)

	if self.get_define(self.have_define(kw.get('uselib_store', kw['package']))):


		if env.CS_NAME == 'mono':
			setattr(env, 'PKG_' + uselib, kw['package'])

		env.append_value('CSFLAGS_' + uselib, Utils.to_list(ret or []))

	return ret


@conf
def check_assembly(self, *k, **kw):
	if k:
		lst = k[0].split()
		kw['package'] = lst[0]

	env = kw.get('env', self.env)

	if not 'msg' in kw:
		kw['msg'] = 'Checking for %s' % kw['package']
	self.start_msg(kw['msg'])

	paths = ['.']
	if "path_list" in kw:
		for p in Utils.to_list(kw['path_list']):
			if p:
				paths.append(p)

	if not 'lib_type' in kw:
		kw['lib_type'] = 'csshlib'

	names = kw['package']
	if not names.endswith('.dll'):
		names += '.dll'

	try:
		ret = self.find_file(names, path_list=paths)
		if ret:
			self.define(self.have_define(kw.get('uselib_store', kw['package'])), 1, 0)
			uselib = kw.get('uselib_store', kw['package']).upper()
			env.append_value('CSFLAGS_' + uselib, '-r:' + os.path.abspath(ret))

			if not 'okmsg' in kw:
				kw['okmsg'] = 'yes'

	except self.errors.WafError:
		if 'errmsg' in kw:
			self.end_msg(kw['errmsg'], 'YELLOW')
		if Logs.verbose > 1:
			raise
		else:
			self.fatal('The configuration failed')
	else:
		kw['success'] = ret
		if 'okmsg' in kw:
			self.end_msg(self.ret_msg(kw['okmsg'], kw))

	return ret


# Add define params to the compile command line
@conf
def set_define(self, *k):
	'''
	set_define('DEBUG', 'LINUX', 'MONO')
	or
	set_define('DEBUG WIN32 TRACE')
	'''
	defines = Utils.to_list(k[0] or [])
	if 1 < len(k):
		defines.extend(k[1:])

	if len(defines):
		self.env.append_value('CSFLAGS', '/define:%s' % ';'.join(defines))

# Set the sdk version
@conf
def set_sdk_version(self, sdk_version):
   self.msg("Setting .Net SDK version", sdk_version)
   self.env.append_value('CSFLAGS', '/sdk:%s' % sdk_version)


# Simple Copy file Task
class copy_file(Task.Task):
	chmod = Utils.O644
	inst_to = None

	def run(self):
		infile = self.inputs[0].abspath()
		outfile = self.outputs[0].abspath()
		try:
			shutil.copy2(infile, outfile)
		except (OSError, IOError):
			return 1
		else:
			if self.chmod: os.chmod(outfile, self.chmod)
			return 0


# Copy all external (USE) library in the the build directory. This will allow use to
# run the codes from within that build directory.
@feature('cs_dev')
@after('use_cs')
def copy_dependent_library(self):
	names = self.to_list(getattr(self, 'use', []))

	for x in names:
		uselib = x.upper()

		pkg = getattr(self.env, 'PKG_' + uselib, [])
		if len(pkg):
			continue

		try:
			tg = self.bld.get_tgen_by_name(x)
			tg.post()
			tsk = getattr(tg, 'cs_task', None) or getattr(tg, 'link_task', None)
			lib = tsk.outputs[0]
		except Errors.WafError:
			csflags = getattr(self.env, 'CSFLAGS_' + uselib, [])
			if len(csflags) == 0:
				continue
			lib = self.bld.root.find_node(csflags[0][3:])

		copy_lib(self, lib)
		copy_config(self, lib)

def copy_lib(tgen, target):
	out = tgen.path.find_or_declare(target.name)
	tgen.copy_dependent_lib_task = tgen.create_task('copy_file', target, out)

def copy_config(tgen, target):
	config = target.change_ext('.dll.config');
	if os.path.isfile(config.abspath()):
		out = tgen.path.find_or_declare(config.name)
		tgen.copy_dependent_lib_config_task = tgen.create_task('copy_file', config, out)

