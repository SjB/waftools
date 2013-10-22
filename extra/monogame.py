#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2012 SjB <steve@sagacity.ca>. All Rights Reserved.

import os, sys
from waflib import Options, Utils
from waflib.Configure import conf

library = 'MonoGame.Framework'
libname = 'MonoGame.Framework'
libpath = './libs'

os_platform = Utils.unversioned_sys_platform()
if 'linux' == os_platform:
    libname = 'MonoGame.Framework.Linux'
    libpath = '/usr/lib/monogame'

def options(ctx):
    ctx.add_option('--with-monogame', type='string', dest='monogame_dir',
        help='Specif the path where the MonoGame cli libraries are located')

def configure(ctx):
    ctx.load('cs_extra', tooldir='extra')

@conf
def check_monogame(self, *k, **kw):

    monogame_dir = Options.options.monogame_dir
    if not monogame_dir:
        if None != self.check_pkg('monogame', uselib_store=library, mandatory = False):
            return
        monogame_dir = os.environ.get('MONOGAME_DIR', libpath)

    monogame_dir = [monogame_dir]
    if 'path_list' in kw:
        monogame_dir.extend(Utils.to_list(kw['path_list']))

    self.check_assembly(libname, path_list = monogame_dir, uselib_store=library)

def read_monogame(self, install_path = None):
    # if assembly is a package skip it.
    self.read_assembly(library, install_path)


