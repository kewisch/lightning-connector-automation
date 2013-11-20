# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Portions Copyright (C) Philipp Kewisch, 2013

from .exceptions import ConfigMissingException
from iniparse import INIConfig
import os.path

class ObmToolConfig(object):
  def __init__(self):
    self.defaultConfig = {}
    self.userConfig = {}
    self.dirty = False

  def readDefaultFile(self):
    fullpath = os.path.join(os.path.dirname(__file__), "..", "crutoolrc")
    if os.path.exists(fullpath):
      self.defaultConfig = INIConfig(open(fullpath))

  @property
  def userFilePath(self):
    home = os.path.expanduser("~")
    filename = ".obmtoolrc" if os.name == "posix" else "obmtool.ini"
    return os.path.join(home, filename)

  def readUserFile(self):
    if os.path.exists(self.userFilePath):
      self.dirty = False
      self.userConfig = INIConfig(open(self.userFilePath))

  def saveUserFile(self):
    if self.dirty:
      f = open(self.userFilePath, "w")
      print >>f, self.userConfig
      f.close()

  def getAll(self, section, defaultValue=None, exception=False):
    if section in self.userConfig:
      return [[x,self.userConfig[section][x]] for x in self.userConfig[section]]
    elif section in self.defaultConfig:
      return [[x,self.defaultConfig[section][x]] for x in self.defaultConfig[section]]
    elif exception:
      raise ConfigMissingException(section, None)
    else:
      return defaultValue

  def get(self, section, key, defaultValue=None, exception=False):
    if section in self.userConfig and key in self.userConfig[section]:
      return self.userConfig[section][key].decode("string_escape")
    elif section in self.defaultConfig and key in self.defaultConfig[section]:
      return self.defaultConfig[section][key].decode("string_escape")
    else:
      if exception:
        raise ConfigMissingException(section, key)
      else:
        return defaultValue

  def set(self, section, key, value):
    self.dirty = True
    self.userConfig[section][key] = value.encode("string_escape")

  def require(self, section, key):
    return self.get(section, key, exception=True)

  def format(self, section, key, data):
    return self.get(section, key, "").decode('utf-8').format(**data)

# our global instance
config = ObmToolConfig()
config.readDefaultFile()
config.readUserFile()
