# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Portions Copyright (C) Philipp Kewisch, 2013

from mozprofile.profile import ThunderbirdProfile
from mozprofile.addons import AddonManager
from urlparse import urlparse
import os.path
import sys
import time

from certificates import CertOverrideFile, CertOverrideEntry
from signons import Signons3File, SignonFileEntry

class ObmProfile(ThunderbirdProfile):
  def __init__(self, userName, serverUri, lightningXPI, obmXPI,
               tbVersion, cachePath="profileCache", *args, **kwargs):
    self.profileName = "%s-tb%d-%s" % (userName, tbVersion, time.strftime("%Y-%m-%d", time.localtime()))
    profilePath = os.path.join(cachePath, self.profileName)

    super(ObmProfile, self).__init__(profile=profilePath, *args, **kwargs)
    self.userName = userName
    self.serverUri = serverUri
    self.lightningXPI = lightningXPI
    self.obmXPI = obmXPI
    self.tbVersion = tbVersion

    self.signons = Signons3File(path=os.path.join(profilePath, "signons3.txt"))
    self.overrides = CertOverrideFile(os.path.join(profilePath,"cert_override.txt"))

    self.initProfile()
    self.flush()

  def flush(self):
    self.overrides.write()
    self.signons.write()

  @property
  def connectorLog(self):
    absProfilePath = os.path.abspath(self.profile)
    return os.path.join(absProfilePath, "obm-connector-log.txt")

  def initProfile(self):
    absProfilePath = os.path.abspath(self.profile)
    serverUri = urlparse(self.serverUri)
    userEmail = "%s@%s" % (self.userName, serverUri.hostname)

    prefs = {
      'toolkit.telemetry.prompted': 2,
      'toolkit.telemetry.rejected': True,
      'shell.checkDefaultClient': False,
      'general.warnOnAboutConfig': False,
      'javascript.options.showInConsole': True,
      'browser.dom.window.dump.enabled': True,

      'mail.account.account1.identities': 'id1',
      'mail.account.account1.server': 'server1',
      'mail.accountmanager.accounts': 'account1',
      'mail.accountmanager.accounts': 'account1',
      'mail.accountmanager.defaultaccount': 'account1',
      'mail.server.server1.check_new_mail': True,
      'mail.server.server1.directory': os.path.join(absProfilePath, "ImapMail", serverUri.hostname),
      'mail.server.server1.directory-rel': '[ProfD]ImapMail/%s' % serverUri.hostname,
      'mail.server.server1.hostname': serverUri.hostname,
      'mail.server.server1.login_at_startup': True,
      'mail.server.server1.name': userEmail,
      'mail.server.server1.socketType': 2,
      'mail.server.server1.type': "imap",
      'mail.server.server1.userName': userEmail,
      'mail.smtpserver.smtp1.authMethod': 3,
      'mail.smtpserver.smtp1.description': serverUri.hostname,
      'mail.smtpserver.smtp1.hostname': serverUri.hostname,
      'mail.smtpserver.smtp1.port': 25,
      'mail.smtpserver.smtp1.try_ssl': 0,
      'mail.smtpserver.smtp1.username': userEmail,
      'mail.smtpservers': 'smtp1',
      'mail.identity.id1.fullName': self.userName,
      'mail.identity.id1.smtpServer': 'smtp1',
      'mail.identity.id1.useremail': userEmail,
      'mail.rights.version': 1,
      'mail.shell.checkDefaultClient': False,
      'mail.spotlight.firstRunDone': True,
      'mailnews.mark_message_read.auto': False,

      'calendar.debug.log': True,
      'calendar.debug.log.verbose': True,

      'extensions.obm.server': self.serverUri,
      'extensions.obm.extensionUpgrade24': True,
      'extensions.obm.firstsync': False,
      'extensions.obm.connector.lastVersion': self.tbVersion,
      'extensions.obm.log.level': -1,
    }

    # Create a new profile
    self.create_new_profile()
    self.set_preferences(prefs.items(), 'prefs.js')

    # Install addons, Lightning and OBM
    self.addon_manager.install_from_path(self.lightningXPI)
    self.addon_manager.install_from_path(self.obmXPI)

    # Add saved passwords
    self.signons.addEntry(
      hostname="obm-obm-obm",
      httpRealm="obm-obm-obm",
      user=self.userName, password=self.userName
    )
    self.signons.addEntry(
      hostname="imap://%s" % serverUri.hostname,
      httpRealm="imap://%s" % serverUri.hostname,
      user=userEmail, password=self.userName
    )
    self.signons.addEntry(
      hostname="smtp://%s" % serverUri.hostname,
      httpRealm="smtp://%s" % serverUri.hostname,
      user=userEmail, password=self.userName
    )

    # Create certificate overrides
    self.overrides.add(CertOverrideEntry.fromHost(serverUri.hostname, 443))
    hackedEntry = CertOverrideEntry.fromHost(serverUri.hostname, 443)
    hackedEntry.port = 143
    self.overrides.add(hackedEntry)
