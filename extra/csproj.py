#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2012 SjB <steve@sagacity.ca>. All Rights Reserved.

"""
Visual Studio csproj file support. A simple example::

    def configure(conf):
        conf.load('csproj', tooldir='tooldir_path')
    def csproj(ctx):
        ctx(features='csproj', source='main.cs', target='sample.csproj', template='template.csproj' use='gtk-sharp')

"""

import os, uuid, sys
import xml.etree.ElementTree as XML
from hashlib import md5

from waflib import Utils, Task, Build, Options, Logs, Errors, Scripting, TaskGen, Context

DEFAULT_CSPROJ_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003" ToolsVersion="3.5">
    <PropertyGroup Label="Global">
        <ProductVersion>9.0.30729</ProductVersion>
        <SchemaVersion>2.0</SchemaVersion>
    </PropertyGroup>
    <PropertyGroup Label="Debug" Condition=" '$(Configuration)|$(Platform)' == 'Debug|AnyCPU' ">
        <DebugSymbols>true</DebugSymbols>
        <DebugType>full</DebugType>
        <Optimize>false</Optimize>
        <DefineConstants>DEBUG</DefineConstants>
        <ErrorReport>prompt</ErrorReport>
        <WarningLevel>4</WarningLevel>
    </PropertyGroup>
    <PropertyGroup Label="Release" Condition=" '$(Configuration)|$(Platform)' == 'Release|AnyCPU' ">
        <DebugType>none</DebugType>
        <Optimize>false</Optimize>
        <ErrorReport>prompt</ErrorReport>
        <WarningLevel>4</WarningLevel>
    </PropertyGroup>
    <Import Project="$(MSBuildBinPath)\Microsoft.CSharp.targets" />
 </Project>
 '''

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def strip_ext(filename):
    if (filename.endswith('.dll') or filename.endswith('.exe')):
        filename = filename[:-4]
    return filename

def make_uuid(k):
    d = md5(k.encode()).hexdigest().upper()
    guid = uuid.UUID(d, version=4)
    return '{%s}' % str(guid).upper()


class MSBuildContext(Build.BuildContext):
    xml_namespace = 'http://schemas.microsoft.com/developer/msbuild/2003'

    cmd = 'msbuild'
    fun = Scripting.default_cmd

    def execute(self):
        """
        Entry point
        """

        self.restore()
        if not self.all_envs:
            self.load_envs()
        self.recurse([self.run_dir])

        # new to create the solution file here
        self.create_csproj_files()

        self.generate_solution()

    def create_csproj_files(self):
        """
        Create a csproj file for each task_gen with a cs_task.
        """

        template_file = getattr(self.env, 'CSProjTemplate', None)

        template = template_file and Utils.readf(template_file) or DEFAULT_CSPROJ_TEMPLATE
        xml_template = XML.fromstring(template);

        for g in self.groups:
            for tg in g:
                if not isinstance(tg, TaskGen.task_gen):
                    continue

                tg.post()
                if not getattr(tg, 'cs_task', None):
                    continue

                tgt = tg.cs_task.outputs[0]
                project_name = strip_ext(tg.name)
                guid = make_uuid(project_name)
                csproj_filename = tg.path.make_node(tg.name).change_ext('.csproj').get_src().abspath()
                output_path = os.path.join(self.out_dir, tgt.bld_dir())
                assembly_name = tgt.change_ext('').name

                print("------ {0} ------".format(csproj_filename))
                print("Guid {0}".format(guid))
                print("OutputPath {0}".format(output_path))
                for s in tg.cs_task.inputs:
                    print("Compile {0}".format(s.path_from(tg.path)))
                print("AssemblyName {0}".format(assembly_name))

                (dotnet_refs, packages, ext_refs, projects) = self.group_dependent_assembly(tg)


    def group_dependent_assembly(self, tg):

        get = self.get_tgen_by_name
        packages = []
        projects = []
        dotnet_refs = []
        ext_refs = []

        for x in Utils.to_list(getattr(tg, 'use', [])):
            pkg = getattr(self.env, 'PKG_' + x.upper(), None)
            if pkg and self.env.CS_NAME == "mono":
                print("Package: {0}".format(pkg))
                packages.append(x)
                continue

            csflags = getattr(self.env, 'CSFLAGS_' + x.upper(), None)
            if csflags:
                print("HintPath Reference: {0}".format(csflags[0][3:]))
                ext_refs.append(csflags[3:])
                continue

            try:
                y = get(x)
            except Errors.WafError:
                print(".Net Reference: {0}".format(x))
                dotnet_refs.append(x)
                continue

            y.post()
            tsk = getattr(y, 'cs_task', None) or getattr(y, 'link_task', None)
            if tsk:
                print("Project {0} {1}".format(strip_ext(y.name), make_uuid(strip_ext(y.name))))
                projects.append(tsk)

        return (dotnet_refs, packages, ext_refs, projects)

    def generate_solution(self):
        pass
        #xml_template.write(self.outputs[0].parent.abspath(), xml_declaration=True, encoding='utf-8')
