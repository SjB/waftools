#!/usr/bin/env python
# encoding: utf-8
# Copyright © 2012 SjB <steve@nca.uwo.ca>. All Rights Reserved.

from waflib.Configure import conf

@conf
def check_nunit(self, nunit_name = 'nunit-console'):
    self.find_program(nunit_name, var='NUNIT')

from waflib.Build import BuildContext
class NUnitContext(BuildContext):
    cmd = 'nunit'
    fun = 'build'
