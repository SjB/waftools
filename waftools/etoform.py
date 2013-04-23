#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2013 SjB <steve@sagacity.ca>. All Rights Reserved.

#
# Waf script to comfigure and use EtoForm

from waflib import Options, Utils

def options(ctx):
	ctx.load('cs_ext', tooldir='waftools')
	ctx.add_option('--with-EtoForms', type='string', dest='etoform_dir',
                    help='Specify the path where the EtoForms library are located')

def configure(ctx):
	etoform_dir = getattr(Options.options, 'etoform_dir', './libs')

	ctx.check_assembly('Eto', path_list = [etoform_dir])

	os_platform = Utils.unversioned_sys_platform()
	uselib_etoplatform = 'Eto.Platform'

	if 'linux' == os_platform:
		ctx.check_assembly('Eto.Platform.Gtk', path_list = [etoform_dir], uselib_store=uselib_etoplatform)
	elif 'win32' == os_platform:
		ctx.check_assembly('Eto.Platform.Windows', path_list = [etoform_dir], uselib_store=uselib_etoplatform)
	else:
		ctx.fatal('Platform not supported')
