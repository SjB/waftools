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

@TaskGen.taskgen_method
def csproj_filename(self):
    project_name = strip_ext(self.name)
    return os.path.join(self.path.abspath(), '%s.csproj' % project_name)

@TaskGen.taskgen_method
def project_guid(self):
    return make_uuid(self.name)

@TaskGen.taskgen_method
def csproj_properties(self):
    pass

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
        XML.register_namespace(self.xml_namespace);

        self.create_csproj_files()

    def create_csproj_files(self):
        """
        Create a csproj file for each task_gen with a cs_task.
        """

        for g in self.groups:
            for tg in g:
                if not isinstance(tg, TaskGen.task_gen):
                    continue

                tg.post()
                if not getattr(tg, 'cs_task', None):
                    continue

                csproj = CSProjectBuilder(self, tg)
                csproj.add_properties(getattr(tg, 'PropertyGroup', {}))
                csproj.write()


class CSProjectBuilder(object):

    packages = []
    projects = []
    dotnet_refs = []
    external_refs = []

    properties = {}

    def __init__(self, bld, tg):
        self.bld = bld
        self.env = bld.env
        self.tg = tg

        self.src_dir = tg.path
        self.bld_dir = tg.path.get_bld()

        XML.register_namespace('', 'http://schemas.microsoft.com/developer/msbuild/2003')
        self.csproj = XML.fromstring(self.get_project_xmlstr())
        self.add_properties(getattr(self.bld.env, 'PropertyGroup', {}))

    def get_project_xmlstr(self):
        tpl = getattr(self.bld, 'CSProjTemplate', None)
        return (tpl and Utils.readf(tpl)) or DEFAULT_CSPROJ_TEMPLATE

    def add_properties(self, prop):
        self.properties.update(prop)


    def project_name():
        return self.tg.csproj_filename()


    def write(self):
        self.group_dependent_assembly()
        self.get_property_from_tg()

        project = self.csproj.getroot()
        self.write_property_group(project)
        self.write_source(project)
        self.write_dotnet_refs(project)
        self.write_ext_refs(project)
        self.write_packages(project)
        self.write_project(project)

        self.csproj.write(self.project_name(), xml_declaration=True, encoding='utf-8')


    def group_dependent_assembly(self):
        '''
        cycle over all dependencies and sort them into types
        '''
        get = self.get_tgen_by_name
        for x in Utils.to_list(getattr(tg, 'use', [])):
            pkg = getattr(self.env, 'PKG_' + x.upper(), None)
            if pkg and self.env.CS_NAME == "mono":
                self.packages.append(x)
                continue

            csflags = getattr(self.env, 'CSFLAGS_' + x.upper(), None)
            if csflags:
                self.external_refs.append(csflags[0][3:])
                continue

            try:
                y = get(x)
            except Errors.WafError:
                self.dotnet_refs.append(x)
                continue

            y.post()
            tsk = getattr(y, 'cs_task', None) or getattr(y, 'link_task', None)
            if tsk:
                self.projects.append(y)


    def get_property_from_tg(self):
        pg = self.properties
        tg = self.tg

        pg['OutputPath'] = tg.path.get_bld().abspath()
        pg['AssemeblyName'] = tg.change_ext('').name
        pg['ProjectGuid'] = tg.project_guid()
        pg['OutputType'] = getattr(tg, 'bintype', 'library')
        pg['Platform'] = getattr(tg, 'platform', 'anycpu')
        pg['Configuration'] = getattr(tg, 'csdebug', self.env.CSDEBUG) or 'Release'


    def write_source(self, project):
        item_group = XML.Element('ItemGroup', {'Label': 'Source'})
        tg = self.tg

        for s in tg.cs_task.inputs:
            e = XML.Element('Compile', {'Include': s.path_from(tg.path)})
            item_group.append(e)

        project.insert(len(project) - 1, item_group)


    def write_property_group(self, project):
        property_group = self.findfirst(project, "./ns:PropertyGroup");
        if not property_group:
            property_group = XML.Element('PropertyGroup')
            project.insert(1, property_group)

        for k, v in self.properties:
            p = self.get_property_element(property_group, k)
            p.text = v


    def get_property_element(self, element, prop):
        p = self.findfirst(element, './ns:%s' % prop)
        if not p:
            p = XML.SubElement(element, prop)

        return p


    def findfirst(self, element, path):
        return element.find(path, namespaces={'ns': self.xml_namespace})


    def write_dotnet_refs(self, project):
        pass

    def write_ext_refs(self, project):
        pass

    def write_packages(self, project):
        pass

    def write_project(self, project):
        pass
