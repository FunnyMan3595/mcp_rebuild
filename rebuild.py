#!/usr/bin/env python
# mcp_rebuild - A Python script for safe and easy rebuilding of MCP projects.
# Copyright (c) 2011 FunnyMan3595 (Charlie Nolan)
# This code is made avilable under the MIT license.  See LICENSE for the full
# details.

import itertools, os, os.path, platform, shutil, subprocess, sys, tarfile, \
       zipfile

import settings

# Exit codes.
# Negative: Failure before compiling.
negative = itertools.count(-1, -1) # Returns 1, 2, 3, etc.
UNCONFIGURED       = negative.next()
BUNDLE_MISSING     = negative.next()
UNSAFE_DELETE      = negative.next()
BAD_BUNDLE         = negative.next()
SRC_INSTALL_FAILED = negative.next()
# Positive: Failure during or after compiling.
positive = itertools.count(1)      # Returns -1, -2, -3, etc.
RECOMPILE_FAILED   = positive.next()
BIN_INSTALL_FAILED = positive.next()
REOBFUSCATE_FAILED = positive.next()
PACKAGE_FAILED     = positive.next()

if settings.UNCONFIGURED:
    print "mcp_rebuild has not been configured properly!"
    print "Edit config.py and try again."
    sys.exit(UNCONFIGURED)

# Convenience functions.  These make the settings settings easier to work with.
absolute = lambda rawpath: os.path.abspath(os.path.expanduser(rawpath))
relative = lambda relpath: absolute(os.path.join(BASE, relpath))

# See settings.py for documenation on what these do.
BASE = absolute(settings.BASE)
USER = relative(settings.USER)
TARGET = relative(settings.TARGET)
SOURCE_BUNDLE = relative(settings.SOURCE_BUNDLE)

# Most of this script assumes it's in the MCP directory, so let's go there.
os.chdir(BASE)

# Create the project directory and force it to be seen as a category.
if not os.path.exists(USER):
    os.makedirs(USER)

    # Touch the CATEGORY file.
    with open(os.path.join(USER, "CATEGORY"), "w") as catfile:
        catfile.write("This is a placeholder file to mark this directory as a "
                      "category, not a project.")

# Create the package directory.
if not os.path.exists(TARGET):
    os.makedirs(TARGET)


# MCP's src directory, the directory MCP will compile from.
# THIS WILL BE NUKED FROM ORBIT EACH RUN.  All contents will be lost.
# A clean copy will then be restored from SOURCE_BUNDLE.  If SOURCE_BUNDLE does
# not exist, the script will offer to create it from a clean MCP_SRC.
# Be EXTREMELY careful if you change this, and don't 'y' out of the run-time
# confirmation without inspecting it!
# The _REL version is used for bundling, to avoid storing absolute paths.
MCP_SRC_REL = "src"
MCP_SRC = relative(MCP_SRC_REL)
# The obvious subdirectories.
MCP_SRC_CLIENT = os.path.join(MCP_SRC, "minecraft")
MCP_SRC_SERVER = os.path.join(MCP_SRC, "minecraft_server")


# MCP's bin directory, the directory MCP will obfuscate from.
MCP_BIN = relative("bin")
# The obvious subdirectories.
MCP_BIN_CLIENT = os.path.join(MCP_BIN, "minecraft")
MCP_BIN_SERVER = os.path.join(MCP_BIN, "minecraft_server")

# MCP's reobf directory, the directory MCP will place reobfuscated classes in.
MCP_REOBF = relative("reobf")
# The obvious subdirectories.
MCP_REOBF_CLIENT = os.path.join(MCP_REOBF, "minecraft")
MCP_REOBF_SERVER = os.path.join(MCP_REOBF, "minecraft_server")

# Detect whether the script is running under windows.
WINDOWS = (platform.system() == "Windows")

# How to recompile with MCP.
if WINDOWS:
    RECOMPILE = relative("recompile.bat")
else:
    RECOMPILE = relative("recompile.sh")

# How to reobfuscate with MCP.
if WINDOWS:
    REOBFUSCATE = relative("reobfuscate.bat")
else:
    REOBFUSCATE = relative("reobfuscate.sh")


# This class is used to represent a user project, also known as a subdirectory
# of USER.  The format is described in the README.
class Project(object):
    def __init__(self, directory):
        self.dir = directory

        self.name = self.get_config("PROJECT_NAME") \
                    or os.path.basename(directory)
        self.version = self.get_config("VERSION")
        self.package_name = self.get_config("PACKAGE_NAME")
        self.hide_source = self.get_config("HIDE_SOURCE", is_boolean=True)
        self.package_command = self.get_config("PACKAGE_COMMAND")

    def get_config(self, setting, is_boolean=False):
        filename = os.path.join(self.dir, "conf", setting)
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
                if os.path.sep != "/":
                    obfuscated = obfuscated.replace("/", os.path.sep)
                    plain = plain.replace("/", os.path.sep)
                obfuscation[plain] = obfuscated

        return obfuscation

    @staticmethod
    def collect_projects(root, projects):
        """Collects all the active projects under root into projects."""
        for (dir, subdirs, files) in os.walk(root, followlinks=True):
            if "DISABLED" in files:
                # This project or category has been disabled.  Skip it.
                del subdirs[:]
                print "Disabled project or category at %s." % dir
            elif "CATEGORY" in files:
                # This is a category, not a project.  Continue normally.
                pass
                print "Found category at %s, recursing." % dir
            else:
                # This is a project.  Create it, but do not continue into
                # subdirectories.
                projects.append(Project(dir))
                del subdirs[:]
                print "Found project at %s." % dir

    def copy_files(self, source, dest, failcode):
        for (source_dir, subdirs, files) in os.walk(source, followlinks=True):
            dest_dir = os.path.join(dest, os.path.relpath(source_dir, source))
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            for file in files:
                try:
                    shutil.copy2(os.path.join(source_dir, file), dest_dir)
                except shutil.WindowsError:
                    pass # Windows doesn't like copying access time.

    def install(self):
        """Installs this project into MCP's source."""
        did_something = False

        src = os.path.join(self.dir, "src")
        if os.path.isdir(src):
            # Common code into both sides first, so it can be overridden.
            common = os.path.join(src, "common")
            if os.path.isdir(common) and os.listdir(common):
                self.copy_files(common, MCP_SRC_CLIENT, SRC_INSTALL_FAILED)
                self.copy_files(common, MCP_SRC_SERVER, SRC_INSTALL_FAILED)
                did_something = True

            # Then client code.
            client = os.path.join(src, "client")
            if os.path.isdir(client) and os.listdir(client):
                self.copy_files(client, MCP_SRC_CLIENT, SRC_INSTALL_FAILED)
                did_something = True

            # And finally server code.
            server = os.path.join(src, "server")
            if os.path.isdir(server) and os.listdir(server):
                self.copy_files(server, MCP_SRC_SERVER, SRC_INSTALL_FAILED)
                did_something = True

        return did_something

    def install_precompiled(self):
        """Installs this project's precompiled code into MCP's classes.

           This code will not be included in the project's package, as it's
           assumed to be libraries or similar code needed for reobfuscation,
           but not part of the mod itself.

           I use this with a deobfuscated-but-still-compiled copy of
           IC2 (which I compile against) so that it reobfuscates happily
           without having to actually solve decompilation issues.
        """
        did_something = False

        bin = os.path.join(self.dir, "bin")
        if os.path.isdir(bin):
            # Common classes into both sides first, so it can be overridden.
            common = os.path.join(bin, "common")
            if os.path.isdir(common) and os.listdir(common):
                self.copy_files(common, MCP_BIN_CLIENT, BIN_INSTALL_FAILED)
                self.copy_files(common, MCP_BIN_SERVER, BIN_INSTALL_FAILED)
                did_something = True

            # Then client classes.
            client = os.path.join(bin, "client")
            if os.path.isdir(client) and os.listdir(client):
                self.copy_files(client, MCP_BIN_CLIENT, BIN_INSTALL_FAILED)
                did_something = True

            # And finally server classes.
            server = os.path.join(bin, "server")
            if os.path.isdir(server) and os.listdir(server):
                self.copy_files(server, MCP_BIN_SERVER, BIN_INSTALL_FAILED)
                did_something = True

        return did_something

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

        filename += ".zip"

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
        """Build a list of class files from the matching list of .java files.

           This method does understand Minecraft's obfuscation.
        """
        if server:
            obfuscation = cls.server_obfuscation
        else:
            obfuscation = cls.client_obfuscation

        classes = []
        for file in files:
            identifier, ext = os.path.splitext(file)

            if ext.lower() != ".java":
                continue

            # If it's one of Minecraft's classes, pass it through the
            # obfuscation map to get the correct identifier for the .class file
            if identifier in obfuscation:
                identifier = obfuscation[identifier]

            prefix = os.path.join("net", "minecraft", "src", "")
            if identifier.startswith(prefix):
                identifier = identifier[len(prefix):]
            classes.append(identifier + ".class")

        return classes

    def zip(self, archive_name, files=None, clean=False):
        if clean:
            mode = "w"
        else:
            mode = "a"

        with zipfile.ZipFile(archive_name, mode) as archive:
            if files is None:
                for dir, subdirs, files in os.walk(".", followlinks=True):
                    for file in files:
                        archive.write(os.path.join(dir, file))
            else:
                for file in files:
                    archive.write(file)

    def package(self):
        """Packages this project's files."""
        def call_or_die(cmd, shell=False):
            exit = subprocess.call(cmd, shell=shell)
            if exit != 0:
                print "Command failed: %s" % cmd
                print "Failed to package project %s.  Aborting." % project.name
                sys.exit(PACKAGE_FAILED)

        if project.package_command is not None:
            call_or_die(project.package_command, shell=True)
            return True
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

            # Package up the client files.
            os.chdir(MCP_REOBF_CLIENT)
            client_package = self.get_package_file()
            client_created = False
            if client_classes:
                if os.path.exists(client_package):
                    os.remove(client_package)
                self.zip(client_package, client_classes, clean=True)
                client_created = True

            # And then the server files.
            os.chdir(MCP_REOBF_SERVER)
            server_package = self.get_package_file(server=True)
            server_created = False
            if server_classes:
                if os.path.exists(server_package):
                    os.remove(server_package)
                self.zip(server_package, server_classes, clean=True)
                server_created = True

            # If we haven't created either package yet, we won't, so bail out.
            if not (client_created or server_created):
                print "Nothing to package."
                return False


            ## Collect and package resource files.
            # Common first, so they can be overridden.
            common_resources = os.path.join(self.dir, "resources", "common")
            if os.path.isdir(common_resources):
                # To package these, we just change to the appropriate directory
                # and let the shell and zip command find everything in it.
                os.chdir(common_resources)
                if client_created:
                    self.zip(client_package)
                if server_created:
                    self.zip(server_package)

            client_resources = os.path.join(self.dir, "resources", "client")
            if os.path.isdir(client_resources):
                os.chdir(client_resources)
                if client_created:
                    self.zip(client_package)

            server_resources = os.path.join(self.dir, "resources", "server")
            if os.path.isdir(server_resources):
                os.chdir(server_resources)
                if server_created:
                    self.zip(server_package)


            ## Collect and package source files
            # Unless we shouldn't, in which case we're done.
            if self.hide_source:
                return True

            # Common first, so they can be overridden.
            common_source = os.path.join(self.dir, "src", "common")
            if os.path.isdir(common_source) and os.listdir(common_source):
                # To package these, we just change to the appropriate directory
                # and let the shell and zip command find everything in it.
                os.chdir(common_source)
                if client_created:
                    self.zip(client_package)
                if server_created:
                    self.zip(server_package)

            client_source = os.path.join(self.dir, "src", "client")
            if os.path.isdir(client_source) and os.listdir(client_source):
                os.chdir(client_source)
                if client_created:
                    self.zip(client_package)

            server_source = os.path.join(self.dir, "src", "server")
            if os.path.isdir(server_source) and os.listdir(server_source):
                os.chdir(server_source)
                if server_created:
                    self.zip(server_package)

            return True


print "STEP 1: Cleaning MCP's source directory."
if not os.path.exists(SOURCE_BUNDLE):
    # We want this without a newline at the end, and print doesn't want to do
    # that, even with a trailing comma.  *shrug*
    sys.stdout.write("Source bundle not found.  Is MCP's source directory clean? (y/N) ")
    answer = sys.stdin.readline().lower()
    if answer.startswith("y"):
        print "Creating source bundle..."
        with tarfile.open(SOURCE_BUNDLE, "w:bz2") as archive:
            archive.add(MCP_SRC_REL)
        print "Bundle created.  No need to clean the source directory."
    else:
        print "Clean MCP's source directory and run this script again."
        sys.exit(BUNDLE_MISSING)
else:
    if os.path.exists(MCP_SRC):
        print "Nuking MCP's source directory from orbit..."
        print "Please confirm that this path is correct.  All contents will be"
        print "destroyed and a clean version will be restored from the bundle:"
        print MCP_SRC
        # We want this without a newline at the end, and print doesn't want to
        # do that, even with a trailing comma.  *shrug*
        sys.stdout.write("Are you sure it's safe to delete this directory and its contents? (y/N) ")
        answer = sys.stdin.readline().lower()
        if not answer.startswith("y"):
            print "Unable to safely clean MCP's source directory.  Aborting."
            sys.exit(UNSAFE_DELETE)
        shutil.rmtree(MCP_SRC)
    else:
        print "MCP's source directory is missing; no need to delete it."
    print "Restoring source bundle..."
    with tarfile.open(SOURCE_BUNDLE, "r:bz2") as archive:
        archive.extractall()
    print "Bundle restored; MCP's source directory is now clean."

print
print "STEP 2: Installing projects."

projects = []
if not os.path.isdir(USER):
    print "No user directory found.  Leaving source clean."
else:
    Project.collect_projects(USER, projects)
    count = 0
    for project in projects:
        if project.install():
            count += 1
    print "%d project(s) installed." % count

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

Project.load_obfuscation()
package_count = 0
for project in projects:
    print "Packaging %s..." % project.name
    os.chdir(BASE)
    if project.package():
        package_count += 1

print "%d project(s) compiled and packaged successfully." % package_count
