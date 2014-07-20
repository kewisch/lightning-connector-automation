#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Portions Copyright (C) Philipp Kewisch, 2013

import argparse
import logging
import tempfile
import traceback
import stat
import re
import sys
import os

from obmtool.runner import ObmRunner
from obmtool.config import config
from obmtool.report import JUnitReport
import obmtool.utils

from manifestparser import TestManifest
import jsbridge
import mozmill
import mozmill.logger
import mozmill.report
import mozinfo
import mozversion

def createRunner(args):
  return ObmRunner.create(binary=args.thunderbird, profile_args={
                            'userName': args.user,
                            'password': args.password,
                            'serverUri': args.server,
                            'tbVersion': args.tbversion,
                            'binary': args.thunderbird,
                            'addons': args.extension,
                            'cachePath': args.cachePath,
                            'preferences': args.preferences,
                            'reset': args.reset
                          })

def parseArgs():
  home = os.path.expanduser("~")
  filename = ".obmtoolrc" if os.name == "posix" else "obmtool.ini"
  defaultconfig = os.path.join(home, filename)

  # When adding new arguments, DO NOT USE the config dict yet. See config file loading below.
  parser = argparse.ArgumentParser(description="Start Thunderbird with a preconfigured OBM setup")
  parser.add_argument('-t', '--thunderbird', type=str, help="The Thunderbird version (17,24,...), or a path to the binary.") # default: defaults.tbversion
  parser.add_argument('-l', '--lightning', type=str, help="The path to the Lightning XPI")
  parser.add_argument('-o', '--obm', type=str, help="The path to the OBM XPI")
  parser.add_argument('-u', '--user', type=str, help="The OBM user to set up") # default: defaults.user
  parser.add_argument('-s', '--server', type=str, help="The sync services URI") # default: defaults.server
  parser.add_argument('-e', '--extension', type=str, nargs='+', default=[], help="An additional extension to install, can be specified multiple times")
  parser.add_argument('-p', '--pref', type=str, nargs='+', default=[], metavar='key=value', help="Additional preferences to set, can be specified multiple times. Value can be a string, integer or true|false.")
  parser.add_argument('-r', '--reset', action='store_true', help="Reset the currently used profile before starting") # default: defaults.reset
  parser.add_argument('-c', '--config', default=None, help="Config file to use (default: %s)" % defaultconfig)
  parser.add_argument('-m', '--mozmill', type=str, nargs='+', default=[], help="Run a specific mozmill test")
  parser.add_argument('--format', type=str, default='pprint-color', metavar='[pprint|pprint-color|json|xunit]', help="Mozmill output format (default: pprint-color)")
  parser.add_argument('--logfile', type=str, default=None, help="Log mozmill events to a file in addition to the console")
  parser.add_argument('-v', '--verbose', action='store_true', help="Show more information about whats going on") # default: defaults.verbose
  args = parser.parse_args()

  # Set up logging
  if args.verbose:
    logging.basicConfig(level=logging.INFO)

  # Read user config, this needs to be done fairly early
  if not args.config:
    args.config = defaultconfig
  if not os.path.exists(args.config):
    print "Config file %s does not exist" % os.path.abspath(args.config)
    sys.exit(1)
  mode = os.stat(args.config)[stat.ST_MODE]
  logging.info("Reading configuration from %s" % os.path.abspath(args.config))
  config.readUserFile(args.config)

  # Protect from footgun
  if config.get("defaults", "password") and mode & (stat.S_IRGRP | stat.S_IWOTH | stat.S_ISUID | stat.S_ISGID) != 0:
    print "Attempt to read config file %s that contains a password and has too open permissions. Change mode to 0600 or equivalent." % args.config
    sys.exit(1)

  # Set up defaults that are taken from the config file, these need to be
  # merged after we load the right config file
  configdefaults = {
    "thunderbird": config.get("defaults", "tbversion"),
    "user": config.get("defaults", "user"),
    "password": config.get("defaults", "password"),
    "server": config.get("defaults", "server"),
    "reset": config.get("defaults", "reset"),
    "verbose": config.get("defaults", "verbose")
  }
  for k in configdefaults:
    if not k in args.__dict__ or args.__dict__[k] is None:
      args.__dict__[k] = configdefaults[k]


  # Set up the Thunderbird version and path
  try:
    # First check if a version number was passed and get the path from the config
    args.tbversion = int(args.thunderbird)
    args.thunderbird = os.path.expanduser(config.require("paths", "thunderbird-%s" % args.tbversion))
    args.thunderbird = obmtool.utils.fixBinaryPath(args.thunderbird)
  except ValueError:
    # Otherwise it was probably a path. Keep the path in args.thunderbird and
    # get the version from Thunderbird's application.ini
    args.thunderbird = obmtool.utils.fixBinaryPath(os.path.expanduser(args.thunderbird))
    tbversion = mozversion.get_version(args.thunderbird)['application_version']
    args.tbversion = int(tbversion.split(".")[0])

  # Set up default lightning xpi based on either passed token (i.e tb3) or
  # passed thunderbird version
  if args.lightning and not os.path.exists(args.lightning):
    args.lightning = config.get("paths", "lightning-%s" % args.lightning)
    if args.lightning is None:
      print "Invalid path to Lightning XPI"
      sys.exit()
  if args.lightning is None:
    args.lightning = config.require("paths", "lightning-tb%d" % args.tbversion)

  # Set up default obm xpi based on either passed token (i.e next-tb17) or
  # default version in prefs (i.e obmversion=next-tb24)
  if args.obm is None:
    args.obm = config.require("defaults", "obmversion")
  if args.obm and not os.path.exists(args.obm):
    args.obm = config.require("paths", "obm-%s" % args.obm)

  logging.info("Using Lighting from %s" % args.lightning)
  logging.info("Using OBM from %s" % args.obm)

  # Set up a path for the profile, either from config or using /tmp
  args.cachePath = config.get("paths", "profileCache", None)
  if args.cachePath is None:
    args.cachePath = tempfile.gettempdir()

  # Expand user path for later use
  args.obm = os.path.expanduser(args.obm)
  args.lightning = os.path.expanduser(args.lightning)
  args.cachePath = os.path.expanduser(args.cachePath)

  # Add extra addons from prefs and passed options
  extensions = filter(bool, re.split("[,\n]", config.get("profile", "extensions", "")))
  extensions.extend(args.extension)
  extensions.append(args.obm)
  extensions.append(args.lightning)
  if args.mozmill:
    extensions.extend(mozmill.ADDONS)

  args.extension = map(os.path.expanduser, extensions)

  # Add extra preferences specified on commandline
  extraprefs = {}
  preferences = config.getAll("preferences")
  preferences.extend([x.split("=", 2) for x in args.pref])
  for k, v in preferences:
    lv = v.lower()
    if lv == "true":
      v = True
    elif lv == "false":
      v = False
    else:
      try: v = int(v)
      except: pass
    extraprefs[k] = v

  if args.mozmill:
    # Set up jsbridge port
    args.jsbridge_port = jsbridge.find_port()

    # Add testing prefs
    extraprefs['extensions.jsbridge.port'] = args.jsbridge_port
    extraprefs['focusmanager.testmode'] = True

    # TODO main window controller will timeout finding the main window since
    # the sync takes so long.
    extraprefs['extensions.obm.syncOnStart'] = False

    # Set up mozinfo for our current configuration
    mozinfo.update(obmtool.utils.setupMozinfo(args))

  # Set up extra preferences in the profile
  args.preferences = extraprefs

  # For the following args we need the runner already
  runner = createRunner(args)

  # Add extra certificates from the prefs
  for cert in filter(bool, re.split("[,\n]", config.get("profile", "certificates", ""))):
    host,port = cert.split(":")
    runner.profile.overrides.addEntry(host, int(port))

  # Add extra signons from the prefs
  for signon in filter(bool, re.split("[,\n]", config.get("profile", "signons", ""))):
    hostname,realm,user,password = signon.split("|")
    runner.profile.signons.addEntry(hostname, realm, user, password)

  # Need to flush profile after adding certs/signons
  runner.profile.flush()

  return runner, args

def run(runner, args):
  print "Profile for Thunderbird %d created in %s" % (args.tbversion, runner.profile.profile)

  # Set the console title
  sys.stdout.write("\x1b]2;%s\x07" % runner.profile.profileName)

  if args.verbose:
    print runner.profile.summary()

  if args.mozmill:
    run_mozmill(wrap_mozmill_runner(runner, args), args)
  else:
    run_thunderbird(runner, args)

def wrap_mozmill_runner(runner, args):
  handlers = []
  level = "DEBUG" if args.verbose else "INFO"
  llevel = logging.DEBUG if args.verbose else logging.INFO

  if args.format == "xunit":
    # Output to logfile as xunit
    class Testrun(object):
      report_type = 'obm-mozmill'
    reportHandler = JUnitReport(args.logfile, Testrun())
    handlers.append(reportHandler)

    # Also output to the console
    logformat = "pprint-color" if sys.stdout.isatty() else "pprint"
    loghandler = mozmill.logger.LoggerListener(format=logformat, console_level=level)
    loghandler.logger.setLevel(llevel)
    handlers.append(loghandler)
  else:
    # Otherwise set up the combined console/file logger
    loghandler = mozmill.logger.LoggerListener(format=args.format,console_level=level,
                                               file_level=level, log_file=args.logfile)
    loghandler.logger.setLevel(llevel)
    handlers.append(loghandler)

  return mozmill.MozMill(runner, args.jsbridge_port, handlers=handlers)

def run_mozmill(runner, args):
  tests = []
  for test in args.mozmill:
    testpath = os.path.expanduser(test)
    realpath = os.path.realpath(testpath)

    if not os.path.exists(testpath):
      raise Exception("Not a valid test file/directory: %s" % test)

    root,ext = os.path.splitext(testpath)
    if ext == ".ini":
        # This is a test manifest, use the parser instead
        manifest = TestManifest(manifests=[testpath], strict=False)
        print mozinfo.info
        tests.extend(manifest.active_tests(**mozinfo.info))
    else:
      def testname(t):
        if os.path.isdir(realpath):
          return os.path.join(test, os.path.relpath(t, testpath))
        return test

      tests.extend([{'name': testname(t), 'path': t }
                    for t in mozmill.collect_tests(testpath)])

  if args.verbose and len(tests):
    print "Running these tests:"
    print "\t" + "\n\t".join(map(lambda x: x['path'], tests))

  exception = None
  try:
    runner.run(tests, True)
  except:
    exception_type, exception, tb = sys.exc_info()

  results = runner.finish(fatal=exception is not None)

  if exception:
      traceback.print_exception(exception_type, exception, tb)
  if exception or results.fails:
      sys.exit(1)

def run_thunderbird(runner, args):
  if not os.path.exists(runner.profile.connectorLog):
    fp = open(runner.profile.connectorLog, "a")
    fp.close()
  logfile = open(runner.profile.connectorLog)
  restartMode = config.get("defaults", "restart", False)
  try:
    while True:
      print "Starting Thunderbird..."
      runner.start()
      logfile.seek(os.stat(runner.profile.connectorLog)[6])

      while runner.is_running():
        where = logfile.tell()
        line = logfile.readline()
        if line:
          print "Connector:",line.rstrip()
        else:
          runner.wait(1)
          logfile.seek(where)

      if restartMode is True or restartMode == "prompt":
        raw_input("\nRestart? (Ctrl-C to cancel)")
      elif restartMode == "auto":
        continue
      else: # restartMode is False or unset
        break

  except KeyboardInterrupt:
    print "\nCleaning up..."
    runner.cleanup()
  finally:
    logfile.close()

if __name__ == "__main__":
  runner, args = parseArgs()
  run(runner, args)
