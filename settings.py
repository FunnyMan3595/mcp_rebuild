#!/usr/bin/env python

# All (current) configuration settings take the form of paths to specific files
# or directories.  Aside from BASE itself, all paths are assumed to be relative
# to BASE unless specified as absolute.

# Windows examples:
# BASE = r"C:\MCP"
# USER = r"mcp_rebuild\My Projects"
# TARGET = r"Z:\My Mods"
# SOURCE_BUNDLE = r"mcp_rebuild\source.tbz2"
#
# This set of configs uses a MCP directory at C:\MCP, looks for the user's
# projects in C:\MCP\mcp_rebuild\My Projects, puts completed packages in
# Z:\My Mods, and keeps a pristine copy of C:\MCP\src in
# C:\MCP\mcp_rebuild\source.tbz2.
#
# Note: Cygwin users should be able to use either Windows or Cygwin-style paths
#       (e.g. /cygdrive/c/you/get/the/idea).  Send in a bug reportif you have
#       any problems, the GitHub page is listed in the README.

# Linux examples:
# BASE = r".."
# USER = r"~/mcp_projects"
# TARGET = r"/var/www/minecraft/bleeding_edge"
# SORUCE_BUNDLE = r".source.tbz2"
#
# This set of configs assumes that rebuild.sh is located in a subdirectory of
# MCP's root.  The source bundle is stored as a hidden file in MCP's root,
# projects are read out of the mcp_projects directory in your $HOME, and
# packages are placed directly onto the minecraft/bleeding_edge directory of
# your website.  (Assuming, of course, you have a suitably-configured webserver
# and write permissions on that directory.)


# Base MCP directory.  If you leave mcp_rebuild in a subdirectory of MCP, you
# can leave this alone.
BASE = r".."

# Base directory for your projects.  DO NOT use one of MCP's own subdirectories
# for this!  Hanging out with mcp_rebuild is fine, MCP just likes to eat its
# own directory contents.
# The format of this directory's contents is described in the README.
USER = r"mcp_rebuild/projects"

# Where your projects' packages will go when they are created.  MCP's
# subdirectories could be used here (since you can always rerun mcp_rebuild), but are not recommended.
TARGET = r"mcp_rebuild/packages"

# Original source bundle, used to reset MCP's source directory to a clean state
# before installing user files.
SOURCE_BUNDLE = r"mcp_rebuild/source.tbz2"

# Okay, I lied a little.  This one's not a path.  Just set it False once you've
# configured the rest.
UNCONFIGURED = True
