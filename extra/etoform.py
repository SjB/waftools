#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2013 SjB <steve@sagacity.ca>. All Rights Reserved.

#
# Waf script to comfigure and use EtoForm

import os, sys
from waflib import Options, Utils
from waflib.Configure import conf

def options(ctx):
    ctx.add_option('--with-eto-forms', type='string', dest='eto_forms_dir', default = None,
            help='Specify the path where the Eto.Forms library are located')
    ctx.add_option('--with-eto-platform', type='string', dest='eto_platform_dir', default = None,
            help='Specify the path where the Eto.Platform library are located')

    def configure(ctx):
        ctx.load('cs', tooldir='extra')

@conf
def check_etoform(self, *k, **kw):
    etoform_dir = [Options.options.eto_forms_dir, Options.options.eto_platform_dir]
    etoform_dir.append(os.environ.get('ETO_FORMS_DIR', None))
    etoform_dir.append(os.environ.get('ETO_PLATFORM_DIR', None))

    if 'path_list' in kw:
        etoform_dir.extend(Utils.to_list(kw['path_list']))

    if 'platform' in kw:
        platform = 'Eto.Platform.' + kw['platform'];
    else:
        os_platform = Utils.unversioned_sys_platform()
        if 'linux' == os_platform:
            platform = 'Eto.Platform.Gtk'
        elif 'win32' == os_platform:
            platform = 'Eto.Platform.Windows'
        else:
            self.fatal('Platform not supported')

    uselib_etoplatform = 'Eto.Platform'

    self.check_assembly('Eto', path_list = [x for x in etoform_dir if x is not None])
    self.check_assembly(platform, path_list = [x for x in etoform_dir if x is not None], uselib_store=uselib_etoplatform)


@conf
def read_etoform(self, install_path = None):
    self.read_assembly('Eto', install_path)
    self.read_assembly('Eto.Platform', install_path)

