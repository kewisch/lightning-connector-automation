import sqlite3
import uuid
import time
from base64 import b64encode,b64decode
import sys
import math
import os
import re
import csv

class SignonFileEntry(object):
  def __init__(self, hostname="", httpRealm="", user="", password=""):
    self.hostname = hostname
    self.httpRealm = httpRealm
    self.user = user
    self.password = password

  def __hash__(self):
    return ("%s (%s)" % (self.hostname, self.httpRealm)).__hash__()
  def __eq__(self, other):
    return self.__hash__() == other.__hash__()

  def __str__(self):
    return "\n".join([
      "%s (%s)" % (self.hostname, self.httpRealm),
      "",
      "~%s" % b64encode(self.user),
      "*",
      "~%s" % b64encode(self.password),
      "",
      "---",
      "."
    ])

class Signons3File(object):
  def __init__(self, path="signons3.txt"):
    self.path = path
    self.entries = set()
    self.read()

  def add(self, entry):
    self.entries.add(entry)

  def addEntry(self, hostname, httpRealm, user, password):
    self.add(SignonFileEntry(hostname, httpRealm, user, password))

  def read(self, fp=None):
    if fp is None:
      if os.path.exists(self.path):
        fp = open(self.path)
      else:
        return

    [HEADER, REJECT, REALM, USERFIELD, USERVAL,
     PASSFIELD, PASSVAL, ACTIONURL, FILLER] = [1,2,3,4,5,6,7,8,9]

    state = HEADER
    entry = SignonFileEntry()
    processEntry = False

    for line in fp:
      line = line.rstrip()
      if state == HEADER:
        formatVersion = line
        state += 1
      elif state == REJECT:
        if line == ".":
          state += 1
          continue
        # disabled hosts
      elif state == REALM:
        res = re.match(r'^(.+?)( \((.*)\))?$', line)
        if res and len(res.groups()) == 3:
          entry.hostname = res.group(1)
          entry.httpRealm = res.group(3)
        state += 1
      elif state == USERFIELD:
        if line == ".":
          state = REALM
          continue
        # user field name
        state += 1
      elif state == USERVAL:
        entry.user = b64decode(line[1:])
        state += 1
      elif state == PASSFIELD:
        # password field name
        state += 1
      elif state == PASSVAL:
        entry.password = b64decode(line[1:])
        state += 1
      elif state == ACTIONURL:
        # form action url
        state += 1
      elif state == FILLER:
        # filler ---
        processEntry = True
        state += 1

      if processEntry:
        self.add(entry)
        entry = SignonFileEntry()
        state = USERFIELD
        processEntry = False

  def write(self, fp=None):
    if fp is None:
      fp = open(self.path, "w")

    fp.write("\n".join(["#2e", "."]) + "\n")
    fp.write("\n".join(map(str, self.entries)))
    fp.close()

class SignonsSQLFile:
  def __init__(self, path="signons.sqlite"):
    self.conn = sqlite3.connect(path)

    c = self.conn.cursor()
    c.execute("PRAGMA user_version")
    version = c.fetchone()
    c.close()
    if version is None or version[0] == 0:
      self.initSchema()

  def close(self):
    self.conn.close()
  def __del__(self):
    self.close()

  def initSchema(self):
    c = self.conn.cursor()
    c.executescript("""
      CREATE TABLE moz_logins (
        id                  INTEGER PRIMARY KEY,
        hostname            TEXT NOT NULL,
        httpRealm           TEXT,
        formSubmitURL       TEXT,
        usernameField       TEXT NOT NULL,
        passwordField       TEXT NOT NULL,
        encryptedUsername   TEXT NOT NULL,
        encryptedPassword   TEXT NOT NULL,
        guid                TEXT,
        encType             INTEGER,
        timeCreated         INTEGER,
        timeLastUsed        INTEGER,
        timePasswordChanged INTEGER,
        timesUsed           INTEGER
      );

      CREATE TABLE moz_disabledHosts (
        id                  INTEGER PRIMARY KEY,
        hostname            TEXT UNIQUE ON CONFLICT REPLACE
      );

      CREATE TABLE moz_deleted_logins (
        id                  INTEGER PRIMARY KEY,
        guid                TEXT,
        timeDeleted         INTEGER
      );

      CREATE INDEX moz_logins_hostname_index ON moz_logins (hostname);
      CREATE INDEX moz_logins_hostname_formSubmitURL_index ON moz_logins (hostname, formSubmitURL);
      CREATE INDEX moz_logins_hostname_httpRealm_index ON moz_logins (hostname, httpRealm);
      CREATE INDEX moz_logins_guid_index ON moz_logins (guid);
      CREATE INDEX moz_logins_encType_index ON moz_logins (encType);

      PRAGMA user_version = 5;
      """)
    self.conn.commit()
    c.close()

  def addLoginEntry(self, hostname, httpRealm, user, password):
    c = self.conn.cursor()
    now = math.floor(time.time() * 1000)
    params = dict()

    # Explicit args
    params['hostname'] = hostname
    params['httpRealm'] = httpRealm
    params['usernameField'] = user
    params['passwordField'] = password

    # automatic args
    params['formSubmitURL'] = ''
    params['usernameField'] = ''
    params['passwordField'] = ''
    params['encryptedUsername'] = b64encode(user)
    params['encryptedPassword'] = b64encode(password)
    params['guid'] = "{%s}" % str(uuid.uuid4())
    params['encType'] = 0 # standard base64. Will be upgraded on startup.
    params['timeCreated'] = now
    params['timeLastUsed'] = now
    params['timePasswordChanged'] = now
    params['timesUsed'] = 1

    c.execute("""INSERT INTO moz_logins
                   (hostname, httpRealm, formSubmitURL, usernameField,
                    passwordField, encryptedUsername, encryptedPassword, guid,
                    encType, timeCreated, timeLastUsed, timePasswordChanged,
                    timesUsed)
                  VALUES (:hostname, :httpRealm, :formSubmitURL,
                          :usernameField, :passwordField, :encryptedUsername,
                          :encryptedPassword, :guid, :encType, :timeCreated,
                          :timeLastUsed, :timePasswordChanged, :timesUsed)
               """, params)
    self.conn.commit()
    c.close()

if __name__ == "__main__":
  sfile = Signons3File()
  if len(sys.argv) == 1:
    sfile.write(sys.stdout)
  elif len(sys.argv) > 4:
    sfile = Signons3File()
    args = sys.argv[1:]
    sfile.addLoginEntry(*args)

