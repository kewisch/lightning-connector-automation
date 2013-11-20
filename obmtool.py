#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Portions Copyright (C) Philipp Kewisch, 2013

import argparse
import logging
import tempfile
import re
import sys
import os

from obmtool.runner import ObmRunner
from obmtool.config import config

def createRunner(args):
  binary = os.path.expanduser(config.require("paths", "thunderbird-%s" % args.tbversion))
  return ObmRunner.create(binary=binary, profile_args={
                            'userName': args.user,
                            'serverUri': args.server,
                            'lightningXPI': args.lightning,
                            'obmXPI': args.obm,
                            'tbVersion': args.tbversion,
                            'addons': args.extension,
                            'cachePath': args.cachePath
                          })

def parseArgs():
  parser = argparse.ArgumentParser(description="Start Thunderbird with a preconfigured OBM setup")
  parser.add_argument('-t', '--tbversion', type=int, default=config.get("defaults", "tbversion"), help="The Thunderbird version to start (17,24,...)")
  parser.add_argument('-l', '--lightning', type=str, help="The path to the Lightning XPI")
  parser.add_argument('-o', '--obm', type=str, help="The path to the OBM XPI")
  parser.add_argument('-u', '--user', type=str, default=config.get("defaults", "user"), help="The OBM user to set up")
  parser.add_argument('-s', '--server', type=str, default=config.get("defaults", "server"),  help="The sync services URI")
  parser.add_argument('-e', '--extension', type=str, nargs='+', default=[], help="An additional extension to install, can be specified multiple times")
  parser.add_argument('-p', '--pref', type=str, nargs='+', default=[], help="Additional preferences to set, can be specified multiple times.")
  parser.add_argument('-v', '--verbose', action='store_true', default=config.get("defaults", "verbose"), help="Show more information about whats going on")
  args = parser.parse_args()

  # Set up logging
  if args.verbose:
    logging.basicConfig(level=logging.INFO)

  # Set up default lightning xpi based on either passed token (i.e tb3) or
  # passed tbversion
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

  args.obm = os.path.expanduser(args.obm)
  args.lightning = os.path.expanduser(args.lightning)
  args.cachePath = os.path.expanduser(args.cachePath)

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

  # Add extra addons from prefs and passed options
  extensions = filter(bool, re.split("[,\n]", config.get("profile", "extensions", "")))
  extensions.extend(args.extension)
  for extension in extensions:
    runner.profile.addon_manager.install_from_path(os.path.expanduser(extension))

  # Add extra preferences specified on commandline
  extraprefs = {}
  preferences = config.getAll("preferences")
  preferences.extend([x.split("=", 2) for x in args.pref])
  for k, v in preferences:
    lv = v.lower()
    if lv == "true": v = True
    elif lv == "false": v = False
    try: v = int(v)
    except: pass
    extraprefs[k] = v
  runner.profile.set_preferences(extraprefs.items(), "prefs.js")

  return runner, args

def run(runner, args):
  print "Profile for Thunderbird %d created in %s" % (args.tbversion, runner.profile.profile)

  # Set the console title
  sys.stdout.write("\x1b]2;%s\x07" % runner.profile.profileName)

  if args.verbose:
    print runner.profile.summary()

  # Run it, showing obm-connector-log
  if not os.path.exists(runner.profile.connectorLog):
    fp = open(runner.profile.connectorLog, "a")
    fp.close()
  logfile = open(runner.profile.connectorLog)
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

      raw_input("Restart? (Ctrl-C to cancel)")
  except KeyboardInterrupt:
    print "\nCleaning up..."
    runner.cleanup()
  finally:
    logfile.close()

if __name__ == "__main__":
  runner, args = parseArgs()
  run(runner, args)
