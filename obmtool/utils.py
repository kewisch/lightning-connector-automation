# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Portions Copyright (C) Philipp Kewisch, 2014

import os
import os.path
import zipfile
import iniparse
import xml.dom.minidom

import mozinfo
import mozversion

if mozinfo.isMac:
    from plistlib import readPlist

def setupMozinfo(args):
  info = {
    "test_enabled": True,
    "crashreporter": True,
    "appname": "thunderbird"
  }

  info.update(setupExtensionInfo(args.obm, "obm"))
  info.update(setupExtensionInfo(args.lightning, "lightning"))

  tbversion = mozversion.get_version(args.thunderbird)['application_version']
  info.update(createVersionProps(tbversion, "tb"))

  return info

def setupExtensionInfo(path, prefix):
  root, ext = os.path.splitext(path)
  if os.path.isdir(path):
    installRDF = open(os.path.join(path, "install.rdf")).read()
  elif ext.lower() == ".xpi":
    with zipfile.ZipFile(path) as zippi:
      installRDF = zippi.open("install.rdf").read()

  dom = xml.dom.minidom.parseString(installRDF)
  version = dom.getElementsByTagNameNS("*", "version")[0].firstChild.nodeValue
  return createVersionProps(version, prefix)

def createVersionProps(version, prefix):
  def tryConvert(x):
    try:
      return int(x)
    except:
      return x

  info = {}
  vlist = map(tryConvert, version.split("."))

  info[prefix + '_version'] = version
  info[prefix + '_major'] = vlist[0]
  info[prefix + '_minor'] = vlist[1]
  if len(vlist) > 2:
    info[prefix + '_maintenance'] = vlist[2]

  return info

def fixBinaryPath(binary):
  if mozinfo.isMac:
    plist = '%s/Contents/Info.plist' % binary
    if not os.path.isfile(plist):
      raise Exception('%s/Contents/Info.plist not found' % binary)

    binary = os.path.join(binary, 'Contents/MacOS/',
                          readPlist(plist)['CFBundleExecutable'])
  return binary
