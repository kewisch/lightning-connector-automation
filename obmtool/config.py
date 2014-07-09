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
    self.userFilePath = None

  def readDefaultFile(self):
    fullpath = os.path.join(os.path.dirname(__file__), "..", "obmtoolrc")
    if os.path.exists(fullpath):
      self.defaultConfig = INIConfig(open(fullpath))

  def readUserFile(self, userFilePath=None):
    self.userFilePath = userFilePath
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

  @staticmethod
  def correctType(val):
    lval = val.lower() if isinstance(val, basestring) else val
    if lval in ("true", "false"):
      return lval == "true"

    try:
      return int(val)
    except (ValueError, TypeError):
      pass

    try:
      return float(val)
    except (ValueError, TypeError):
      pass

    return val

  def get(self, section, key, defaultValue=None, exception=False):
    val = None
    if section in self.userConfig and key in self.userConfig[section]:
      val = self.userConfig[section][key].decode("string_escape")
    elif section in self.defaultConfig and key in self.defaultConfig[section]:
      val = self.defaultConfig[section][key].decode("string_escape")
    else:
      if exception:
        raise ConfigMissingException(section, key)
      else:
        val = defaultValue

    return ObmToolConfig.correctType(val)

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
