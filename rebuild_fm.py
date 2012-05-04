#!/usr/bin/env python
# rebuild.py - A Python script for safe and easy rebuilding of MCP projects.
# Copyright (c) 2011 FunnyMan3595 (Charlie Nolan)
# This code is made avilable under the MIT license.  The full text of the
# license can be found at the end of this file.

# The point of rebuild.py is to allow you to store your code outside of MCP's
# dangerous src/ directory while allowing you to easily install it to MCP,
# recompile, reobfuscate, and package your projects into individual mods.

# To use rebuild.py:
# 1. Create a new MCP directory, with both client and server files..
# 2. If applicable, install ModLoader and Forge.
# 3. Run decompile.sh to produce a clean src/ directory for MCP.
# 4. Place rebuild.py in your MCP directory.
# 5. Edit rebuild.py to configure it.  Configuration settings are located near
#    the beginning of the file.  You'll want to change USER and TARGET, at
#    least.  BASE might also be worth changing.
# 6. Run rebuild.py once, and tell it that MCP's source directory is clean.
#    This causes rebuild.py to record a "clean state" that it will reset MCP's
#    source directory to before each compilation.
# 7. Create one or more projects in your USER directory.  The format for a
#    project can be found just after the configuration settings.
# 8. Run rebuild.py to build your projects.
# 9. Fix the inevitable errors and return to step 8 until it actually *does*
#    work.

import itertools, os, os.path, shutil, subprocess, sys

# Seriously, configure it.  You'll be much happier if you set USER and TARGET
# to something specific to you before commenting this out.  And you need to be
# here to read the documentation anyway.
print "rebuild.py has not been configured properly!  Please edit it and adjust"
print "the configuration settings."
sys.exit(3595)

# Base MCP directory.  If you want to be able to run this script from another
# directory, be sure to set this.
BASE = os.path.abspath(".")
# (Yes, os.getcwd() would work identically here for the default behaviour, but
#  this format is a bit more intuitive if you decide to modify it.)

# Base directory for your projects.  DO NOT use one of MCP's own subdirectories
# for this!
# The format of this directory's contents is described just after the config
# settings.
USER = os.path.join(BASE, "user_src")
os.makedirs(USER)

# Where your projects' packages will go when they are created.  MCP's
# subdirectories could be used here, but are not recommended.
TARGET = os.path.join(BASE, "user_target")
os.makedirs(TARGET)

# Original source bundle, used to reset to a clean state before installing
# user files.
# Technically, this doesn't have to be a true "bundle".  Using a directory here
# would work, provided you use a matching BUNDLE_CMD and EXTRACT command.
# Version control would also work, just make sure it's not stored in MCP_SRC.
SOURCE_BUNDLE = os.path.join(BASE, "source.tbz2")

# MCP's src directory; this probably shouldn't be changed.
# This is the directory MCP will compile from.
# THIS WILL BE NUKED FROM ORBIT EACH RUN.  All contents will be lost.
# A clean copy will then be restored from SOURCE_BUNDLE.  If SOURCE_BUNDLE does
# not exist, the script will offer to create it from a clean MCP_SRC.
MCP_SRC = os.path.join(BASE, "src")
# The obvious subdirectories.
MCP_SRC_CLIENT = os.path.join(MCP_SRC, "minecraft")
MCP_SRC_SERVER = os.path.join(MCP_SRC, "minecraft_server")

# How to create the bundle.
BUNDLE_CMD = "tar -cvjf %(SOURCE_BUNDLE)s %(MCP_SRC)s" % vars()

# How to extract the bundle.
EXTRACT_CMD = "tar -xvjf %(SOURCE_BUNDLE)s" % vars()

# MCP's bin directory; this probably shouldn't be changed.
# This is the directory MCP will obfuscate from.
MCP_BIN = os.path.join(BASE, "bin")
# The obvious subdirectories.
MCP_BIN_CLIENT = os.path.join(MCP_BIN, "minecraft")
MCP_BIN_SERVER = os.path.join(MCP_BIN, "minecraft_server")

# MCP's reobf directory; this probably shouldn't be changed.
# This is the directory MCP will place reobfuscated classes in.
MCP_REOBF = os.path.join(BASE, "reobf")
# The obvious subdirectories.
MCP_REOBF_CLIENT = os.path.join(MCP_REOBF, "minecraft")
MCP_REOBF_SERVER = os.path.join(MCP_REOBF, "minecraft_server")

# How to recompile with MCP; this probably shouldn't be changed.
RECOMPILE = os.path.join(BASE, "recompile.sh")

# How to reobfuscate with MCP; this probably shouldn't be changed.
REOBFUSCATE = os.path.join(BASE, "reobfuscate.sh")

# Exit codes; these probably shouldn't be changed.
# Negative: Failure before compiling.
negative = itertools.count(-1, -1) # Returns 1, 2, 3, etc.
BUNDLE_MISSING     = negative.next()
BAD_BUNDLE         = negative.next()
SRC_INSTALL_FAILED = negative.next()
# Positive: Failure during or after compiling.
positive = itertools.count(1)      # Returns -1, -2, -3, etc.
RECOMPILE_FAILED   = positive.next()
BIN_INSTALL_FAILED = positive.next()
REOBFUSCATE_FAILED = positive.next()



# This class is used to represent a user project, also known as a subdirectory
# of USER.  Each project should have the following form, with all pieces
# optional:
#
# $PROJECT_NAME/
#   CATEGORY - If present, this directory is treated as a category which can
#              contain projects (or other categories) and not a project itself.
#   DISABLED - If present, this project or category will be skipped by
#              rebuild.py.  Useful for "turning off" projects that won't
#              compile right now.
#   src/
#     client/ - Client-specific source files go here.
#     server/ - Server-specific source files go here.
#     common/ - Shared source files go here.  Most of your code should be here.
#   bin/
#     client/ - Pre-compiled files needed by the client during reobfuscation go
#               here.  They will not be included in the client package.
#     server/ - Pre-compiled files needed by the server during reobfuscation go
#               here.  They will not be included in the server package.
#     common/ - Pre-compiled files needed by both client and server during
#               reobfuscation go here.  They will not be included in either
#               package.
#   resources/
#     client/ - Resources to pack into the client .jar go here.
#               (GUI resources belong here.)
#     server/ - Resources to pack into the server .jar go here.
#     common/ - Resources to pack into both .jars go here.
#   conf/
#     PROJECT_NAME    - Overrides the directory's name for the project.
#     VERSION         - A version number to include in the package name.
#     PACKAGE_NAME    - Overrides the default "Name" or "Name-version"
#                       name for the project's package.  The server tag and
#                       .jar extension will be applied after this.
#     HIDE_SOURCE     - If present, rebuild.py will not include the project's
#                       source in its package.
#     PACKAGE_COMMAND - An alternative command for building the project's
#                       package.  Only a single line is supported, so complex
#                       packaging should reference a script here.

class Project(object):
    def __init__(self, directory):
        self.dir = directory

        self.name = get_config("PROJECT_NAME") or os.path.basename(directory)
        self.version = get_config("VERSION")
        self.package_name = get_config("PACKAGE_NAME")
        self.hide_source = get_config("HIDE_SOURCE", is_boolean=True)
        self.package_command = get_config("PACKAGE_COMMAND")

    def get_config(self, setting, is_boolean=False):
        filename = os.path.join(directory, "conf", setting)
        exists = os.path.isfile(filename)

        if is_boolean:
            return exists
        elif not exists:
            return None
        else:
            return open(filename).read().strip()

    @classmethod
    def load_obfuscation(cls):
        cls.client_obfuscation = cls._load_obfuscation("conf/client.srg")
        cls.server_obfuscation = cls._load_obfuscation("conf/server.srg")

    @classmethod
    def _load_obfuscation(cls, filename):
        obfuscation = {}

        lines = open(os.path.join(BASE, filename)).readlines()
        for line in lines:
            if line.startswith("CL:"):
                prefix, obfuscated, plain = line.split()
                obfuscation[plain] = obfuscated

        return obfuscation

    @staticmethod
    def collect_projects(root, projects):
        """Collects all the active projects under root into projects."""
        for (dir, subdirs, files) in os.walk(root, followlinks=True):
            if "DISABLED" in files:
                # This project or category has been disabled.  Skip it.
                del subdirs[:]
            elif "CATEGORY" in files:
                # This is a category, not a project.  Continue normally.
                pass
            else:
                # This is a project.  Create it, but do not continue into
                # subdirectories.
                projects.append(Project(dir))
                del subdirs[:]

    def copy_files(self, source, dest, failcode):
        exit = subprocess.call("cp -r %s/* %s" % (source, dest))
        if exit != 0:
            print "While processing project %s:" % self.name
            print "Unable to copy files from %s to %s.  Aborting." %
                                          (source, dest)
            sys.exit(failcode)

    def install(self):
        """Installs this project into MCP's source."""
        src = os.path.join(self.dir, "src")
        if os.path.isdir(src):
            # Common code into both sides first, so it can be overridden.
            common = os.path.join(src, "common")
            if os.path.isdir(common):
                self.copy_files(common, MCP_SRC_CLIENT, SRC_INSTALL_FAILED)
                self.copy_files(common, MCP_SRC_SERVER, SRC_INSTALL_FAILED)

            # Then client code.
            client = os.path.join(src, "client")
            if os.path.isdir(client):
                self.copy_files(client, MCP_SRC_CLIENT, SRC_INSTALL_FAILED)

            # And finally server code.
            server = os.path.join(src, "server")
            if os.path.isdir(server):
                self.copy_files(server, MCP_SRC_SERVER, SRC_INSTALL_FAILED)

    def install_precompiled(self):
        """Installs this project's precompiled code into MCP's classes.

           This code will not be included in the project's package, as it's
           assumed to be libraries or similar code needed for reobfuscation,
           but not part of the mod itself.

           I use this with a deobfuscated-but-still-compiled copy of
           IC2 (which I compile against) so that it reobfuscates happily
           without having to actually solve decompilation issues.
        """
        bin = os.path.join(self.dir, "bin")
        if os.path.isdir(bin):
            # Common classes into both sides first, so it can be overridden.
            common = os.path.join(bin, "common")
            if os.path.isdir(common):
                self.copy_files(common, MCP_BIN_CLIENT, BIN_INSTALL_FAILED)
                self.copy_files(common, MCP_BIN_SERVER, BIN_INSTALL_FAILED)

            # Then client classes.
            client = os.path.join(bin, "client")
            if os.path.isdir(client):
                self.copy_files(client, MCP_BIN_CLIENT, BIN_INSTALL_FAILED)

            # And finally server classes.
            server = os.path.join(bin, "server")
            if os.path.isdir(server):
                self.copy_files(server, MCP_BIN_SERVER, BIN_INSTALL_FAILED)

    def get_package_file(self, server=False):
        if self.package_name is not None:
            filename = self.package_name
        else:
            if self.version is not None:
                filename = "%s-%s" % (self.name, self.version)
            else:
                filename = "%s" % self.name

        if server:
            filename += "-server"

        filename += ".jar"

        return os.path.join(TARGET, filename)

    @staticmethod
    def collect_files(root):
        all_files = set()
        if not os.path.isdir(root):
            return all_files

        for (dir, subdirs, files) in os.walk(root, followlinks=True):
            for file in files:
                full_name = os.path.join(dir, file)
                relative_name = os.path.relpath(full_name, root)
                all_files.add(relative_name)

        return all_files

    @classmethod
    def map_to_class(cls, files, server=False):
        # TODO

    def package(self):
        """Packages this project's files."""
        def call_or_die(cmd, shell):
            exit = subprocess.call(cmd, shell=shell)
            if exit != 0:
                print "Command failed: %s" % cmd
                print "Failed to package project %s.  Aborting." % project.name
                sys.exit(PROJECT_PACKAGE_FAILED)

        if project.package_command is not None:
            call_or_die(project.package_command, shell=True)
        else:
            ## Collect and package the matching .class files for this project.
            # Start by building a list of all of the source files of each type.
            client_dir = os.path.join(self.dir, "src", "client")
            client_sources = self.collect_files(client_dir)

            server_dir = os.path.join(self.dir, "src", "server")
            server_sources = self.collect_files(server_dir)

            common_dir = os.path.join(self.dir, "src", "common")
            common_sources = self.collect_files(common_dir)

            # Common sources just get added to both sides.
            client_sources.update(common_sources)
            server_sources.update(common_sources)

            # Translate the source files into their matching class files,
            # taking obfuscation into account.
            client_classes = self.map_to_class(client_sources)
            server_classes = self.map_to_class(server_sources, server=True)

            # Move into the right directory for jar-ing the classes.
            os.chdir(MCP_REOBF_CLIENT)

            # Package up the client files.
            client_package = self.get_package_file()
            client_created = False
            if client_classes:
                call_or_die(["jar", "-cf", client_package] + client_classes)
                client_created = True

            # And then the server files.
            server_package = self.get_package_file(server=True)
            server_created = False
            if server_classes:
                call_or_die(["jar", "-cf", server_package] + server_classes)


            ## Collect and package resource files.
            # TODO

            ## Collect and package source files
            # Unless we shouldn't, in which case we're done.
            if self.hide_source:
                return

            # TODO


print "STEP 1: Cleaning MCP's source directory."
if not os.path.exists(SOURCE_BUNDLE):
    print "Source bundle not found.  Is MCP's source directory clean? (y/N)",
    answer = sys.stdin.readline()
    if answer.lower().startswith("y"):
        print "Creating source bundle..."
        exit = subprocess.call(BUNDLE_CMD, shell=True)
        if exit != 0:
            print "Bundle failed with exit code %d." % exit
            print "Unable to create bundle.  Aborting."
            sys.exit(BUNDLE_MISSING)
        print "Bundle created.  No need to clean the source directory."
    else:
        print "Clean MCP's source directory and run this script again."
        sys.exit(BUNDLE_MISSING)
else:
    print "Nuking MCP's source directory from orbit..."
    shutil.rmtree(MCP_SRC)
    print "Restoring source bundle..."
    exit = subprocess.call(EXTRACT_CMD, shell=True)
    if exit != 0:
        print "Extract failed with exit code %d." % exit
        print "Unable to extract source bundle.  Aborting."
        sys.exit(BAD_BUNDLE)
    print "Bundle restored; MCP's source directory is now clean."

print
print "STEP 2: Installing projects."

projects = []
if not os.path.isdir(USER):
    print "No user directory found.  Leaving source clean."
else:
    Project.collect_projects(USER, projects)
    for project in projects:
        project.install()
    print "%d project(s) installed." % len(projects)

print
print "STEP 3: Recompiling and reobfuscating."

exit = subprocess.call(RECOMPILE, shell=True)
if exit != 0:
    print "Recompile failed.  Aborting."
    sys.exit(RECOMPILE_FAILED)

# Install pre-compiled code.
count = 0
for project in projects:
    if project.install_precompiled():
        count += 1

print "Installed precompiled files for %d project(s)." % count

exit = subprocess.call(REOBFUSCATE, shell=True)
if exit != 0:
    print "Reobfuscate failed.  Aborting."
    sys.exit(REOBFUSCATE_FAILED)

print "Recompiled and reobfuscated successfully."
print
print "STEP 4: Packaging projects."

for project in projects:
    print "Packaging %s..." % project.name
    project.package()

print "%d projects packaged successfully."

# LICENSE:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
