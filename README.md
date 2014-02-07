Welcome to obmtool
==================

This tool allows you to easily start Thunderbird with a preconfigured
Lightning and OBM connector. It relieves you of all the initial steps,
including extension installation, setting up accounts, passwords and
certificate overrides.


Setup
=====

The tool has not been packaged as a python package yet, so you will
have to first install a few dependencies:

    pip install M2Crypto iniparse mozrunner mozprofile mozmill

Now you will need to copy the obmtoolrc file to ~/.obmtoolrc and make
any modifications you need. You also need to create the profileCache
directory.

defaults section
----------------

This section holds defaults for command line options:

    # The default OBM user to set up
    user=kewisch

    # The URL of the OBM server to use
    server=https://myobm.obm.org/obm-sync/services

    # The default Thunderbird version to start
    tbversion=24

    # The obm version to start, an alias from the [paths] section.
    obmversion=next-tb24

    # If true, verbose output will be used
    verbose=True

    # If true, the profile will be reset on each startup
    reset=True

    # Sets the behavior after Thunderbird quits.
    # prompt - In the console, prompt the user if a restart should be done
    # auto   - Automatically restart Thunderbird
    # False  - (default) Exit after Thunderbird has been quitted
    restart=prompt

paths section
-------------
This section contains a few aliases that can be used either in the
[defaults] section or on the commandline. The first part (lightning,
obm, thunderbird) is used as a prefix, the second part (i.e next-tb24)
is the alias that can be used on the commandline.

    # Location of various Lightning installations. Can be an .xpi file
    # or a path to an unpacked extension.
    lightning-tb24=~/releases/ltn26/lightning-mac.xpi
    lightning-tb17=~/releases/obm/lightning-1.9.24obm-tb-mac.xpi
    lightning-tb10=~/releases/obm/lightning-1.2.3.24obm-tb-mac.xpi
    lightning-tb3=~/releases/obm/lightning-1.0b2.25obm-tb-mac.xpi

    # Location of various OBM Lightning Connector packages. Can be an
    # .xpi file or a path to an unpacked extension.
    obm-next-tb24=~/obm/tb24/lightning-connector-pkewisch/build/stage
    obm-next-tb17=~/obm/tb17/lightning-connector-pkewisch/build/stage

    # Location of various Thunderbird packages. On mac this is the
    # path to Thunderbird.app, on other platforms the path containing
    # Thunderbird's executables.
    thunderbird-24=~/mozilla/tbesr24/Thunderbird.app
    thunderbird-17=~/mozilla/tbesr17/Thunderbird.app
    thunderbird-10=~/mozilla/tbesr10/Thunderbird.app
    thunderbird-3=~/mozilla/tb31/Thunderbird.app

    # Cache directory for profiles. You need to create this directory.
    profileCache=~/.obmtool/cache


profile section
---------------


    # Comma separated list of extra hosts to create SSL certificate
    # exceptions for. The OBM sync server will be added automatically.
    certificates=vm.obm.org:443,vm.obm.org:143

    # Extra password database entries, using signons.txt format.
    signons=obm-obm-obm|obm-obm-obm|userb|userb

    # Extra extensions to install, whitespace separated. Multiple
    # lines can be used as long as the continuation line starts
    # with a whitespace.
    extensions=
     ~/mozilla/dist-extensions/ics-inspector-0.8.xpi
     ~/mozilla/dist-extensions/obmdeveloper-0.1.xpi


preferences section
-------------------

This section contains any extra preferences to set. Many debugging
preferences are already set by the application, but you might want to
set some extra preferences


Usage
=====
Most usage is explained using obmtool --help. Note you can use aliases
from the [paths] section for the options -t, -l and -o.

    usage: obmtool [-h] [-t TBVERSION] [-l LIGHTNING] [-o OBM] [-u USER]
                   [-s SERVER] [-e EXTENSION [EXTENSION ...]]
                   [-p key=value [key=value ...]] [-m MOZMILL [MOZMILL ...]]
                   [--format [json|pprint|pprint-color]] [--logfile LOGFILE] [-v]

    Start Thunderbird with a preconfigured OBM setup

    optional arguments:
      -h, --help            show this help message and exit
      -t TBVERSION, --tbversion TBVERSION
                            The Thunderbird version to start (17,24,...)
      -l LIGHTNING, --lightning LIGHTNING
                            The path to the Lightning XPI
      -o OBM, --obm OBM     The path to the OBM XPI
      -u USER, --user USER  The OBM user to set up
      -s SERVER, --server SERVER
                            The sync services URI
      -e EXTENSION [EXTENSION ...], --extension EXTENSION [EXTENSION ...]
                            An additional extension to install, can be specified
                            multiple times
      -p key=value [key=value ...], --pref key=value [key=value ...]
                            Additional preferences to set, can be specified
                            multiple times. Value can be a string, integer or
                            true|false.
      -m MOZMILL [MOZMILL ...], --mozmill MOZMILL [MOZMILL ...]
                            Run a specific mozmill test
      --format [json|pprint|pprint-color]
                            Mozmill output format (default: pprint-color)
      --logfile LOGFILE     Log mozmill events to a file in addition to the
                            console
      -v, --verbose         Show more information about whats going on

Running MozMill Tests
=====================

With obmtool you can run MozMill tests. Initial setup will occur using the
configuration and arguments provided. To use obmtool in mozmill mode, pass a
test file or directory to the -m option. When passing a directory, all files
beginning with "test\_" will be processed. See the next section for examples.

NOTE: Running multiple tests, either via directory or passing multiple -m
options does not work yet.

Examples
========

Start with Thunderbird 24, the corresponding Lightning version, the
connector from the next-tb24 alias, with usera:

    obmtool -t 24 -o next-tb24 -u usera

Example of how to use a custom Lightning package, using mostly
default values:

    obmtool -t 24 -l ~/releases/lightning-2.6.1-custom.xpi

Run a specific mozmill test by its filename on Thunderbird 24 with userb.

    obmtool -t 24 -u userb -m ~/tests/test_create_event.js

Run all mozmill tests in the ~/tests directory, using the same options.

    obmtool -t 24 -u userb -m ~/tests

Roadmap
=======

* Package as python package with setup.py
* Allow passing http urls to -l or -o, possibly with a configurable
  prefix (i.e for getting a package from jenkins)
* Some more commandline options, i.e devtools debugger port, common
  obm settings like proactive sync.
