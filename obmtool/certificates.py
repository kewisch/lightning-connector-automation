import socket
import ssl
from M2Crypto import X509
import base64
import struct
import binascii
import logging
import os

class CertOverrideEntry:
  SHA256_OID = "OID.2.16.840.1.101.3.4.2.1"

  @staticmethod
  def fromHost(host, port, certtype='U', ssl_version=None):
    logging.info("Getting certificate from %s:%d" % (host, port))
    if ssl_version is None:
      cert = ssl.get_server_certificate((host, port))
    else:
      cert = ssl.get_server_certificate((host, port), ssl_version=ssl_version)
    x509 = X509.load_cert_string(cert.encode('ascii', 'ignore'))
    return CertOverrideEntry(host, port, x509=x509, certtype=certtype)

  def __init__(self, host, port, fingerprint=None, certtype='U', issuerSerialHash=None, x509=None):
    self.host = host
    self.port = port
    self.certtype = certtype
    self.issuerSerialHash = issuerSerialHash
    self.fingerprint = fingerprint
    if x509:
      issuer = x509.get_issuer().as_der()
      serial = x509.get_serial_number()
      packed = struct.pack(">LLLLB", 0, 0, len(str(serial)), len(issuer), serial) + issuer
      self.issuerSerialHash = self._splitBy('  ', 64, base64.b64encode(packed))
      self.fingerprint = self._splitBy(':', 2, x509.get_fingerprint('sha256'))

  def _splitBy(self, c, l, s):
    return c.join([ s[i:i+l] for i in xrange(0, len(s), l) ])

  def __hash__(self):
    return ("%s:%s" % (self.host, self.port)).__hash__()
  def __eq__(self, other):
    return self.__hash__() == other.__hash__()

  def __str__(self):
    return "%s:%s\t%s\t%s\t%s\t%s" % (
        self.host, self.port,
        CertOverrideEntry.SHA256_OID,
        self.fingerprint, self.certtype,
        self.issuerSerialHash
     )

class CertOverrideFile(object):
  HEADER = "# PSM Certificate Override Settings file\n# This is a generated file!  Do not edit."

  def __init__(self, path):
    self.entries = set()
    self.path = path
    self.read()

  def write(self):
    fp = open(self.path, "w")
    fp.write(CertOverrideFile.HEADER + "\n")
    fp.write("\n".join(map(str, self.entries)))
    fp.close()

  def read(self, fp=None):
    if fp is None:
      if os.path.exists(self.path):
        fp = open(self.path)
      else:
        return

    for line in fp:
      if line[0] == "#":
        continue

      [hostport,oid,fingerprint,certtype,h1,h2,h3] = line.split()
      [host,port] = hostport.split(":")
      entry = CertOverrideEntry(host, port, fingerprint,
                                certtype, "  ".join([h1,h2,h3]))
      self.add(entry)

  def add(self, entry):
    self.entries.add(entry)

  def addEntry(self, host, port):
    self.entries.add(CertOverrideEntry.fromHost(host, port))

  def __str__(self):
    return CertOverrideFile.HEADER + "\n" + "\n".join(map(str, self.entries))
