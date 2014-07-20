import base64
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import virtualenv
import signal

from ctypes import *
from ctypes.util import find_library

class SECItem(Structure):
    _fields_ = [('type',c_uint),('data',c_void_p),('len',c_uint)]

class NSS(object):
    def __init__(self, profilePath, password="", nssPath=None):
        if not nssPath:
            nssPath = find_library("nss3")

        self.libnss = CDLL(nssPath)
        self.libnss.NSS_InitReadWrite.argtypes = [c_char_p]
        self.libnss.PK11_GetInternalKeySlot.restype = c_void_p
        self.libnss.PK11_NeedUserInit.argtypes = [c_void_p]
        self.libnss.PK11_InitPin.argtypes = [c_void_p, c_char_p, c_char_p]
        self.libnss.PK11_CheckUserPassword.argtypes = [c_void_p, c_char_p]
        self.libnss.PK11_IsLoggedIn.argtypes = [c_void_p, c_void_p]
        self.libnss.PK11_Authenticate.argtypes = [c_void_p, c_int, c_void_p]
        self.libnss.PK11_FreeSlot.argtypes = [c_void_p]

        self.initNSS(profilePath, password)


    def _checkNSS(self, err):
        if err != 0:
            raise Exception("NSS error %d" % self.libnss.PORT_GetError())

    def initNSS(self, profilePath, password=""):
        if self.libnss.NSS_InitReadWrite(profilePath) != 0:
            raise Exception("NSS Initialization error %d" % self.libnss.PORT_GetError())

        slot = self.libnss.PK11_GetInternalKeySlot()
        if self.libnss.PK11_NeedUserInit(slot):
            self._checkNSS(self.libnss.PK11_InitPin(slot, "", ""))
        else:
            self._checkNSS(self.libnss.PK11_CheckUserPassword(slot, password))

        if not self.libnss.PK11_IsLoggedIn(slot, None):
            self._checkNSS(self.libnss.PK11_Authenticate(slot, True, 0))

        self.libnss.PK11_FreeSlot(slot)

    def decryptString(self, data, base64encoded=True):
        reply = SECItem()
        request = SECItem()

        if base64encoded:
            data = base64.b64decode(data)

        request.data = cast(c_char_p(data), c_void_p)
        request.len = len(data)
        reply.data = 0
        reply.len = 0

        self._checkNSS(self.libnss.PK11SDR_Decrypt(byref(request),byref(reply),0))
        return string_at(reply.data, reply.len)

    def encryptString(self, data, base64encode=True):
      reply = SECItem()
      request = SECItem()
      keyid = SECItem()

      keyid.type = 0
      keyid.data = 0
      keyid.len = 0
      request.data = cast(c_char_p(data), c_void_p)
      request.len = len(data)

      self._checkNSS(self.libnss.PK11SDR_Encrypt(byref(keyid), byref(request),byref(reply), 0))
      result = string_at(reply.data, reply.len)
      return base64.b64encode(result) if base64encode else result

    def shutdown(self):
        self.libnss.NSS_Shutdown()
        self.libnss = None

class NSSSession(object):
    def __init__(self, binPath, profilePath, password=None):
        self.venvDir = tempfile.mkdtemp()
        self.leafName = os.path.basename(__file__)
        self.binDir = os.path.join(self.venvDir, 'bin')
        self.profilePath = profilePath
        self.password = password
        self.subproc = None

        # create the virtualenv
        virtualenv.create_environment(self.venvDir,
            site_packages=True,
            never_download=True,
            no_pip=True,
            no_setuptools=True
        )

        # copy libraries
        if sys.platform == "linux2":
            dllfiles = "*.so"
        elif sys.platform == "darwin":
            dllfiles = "*.dylib"
        elif sys.platform == "win32":
            dllfiles = "*.dll"

        files = glob.glob(os.path.join(binPath, dllfiles))
        if not len(files):
            raise Exception("Could not find libraries in " + binPath)

        for filename in files:
            shutil.copy(filename, self.binDir)

        # copy our script
        shutil.copy(__file__, self.binDir)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        if exc_type is None:
            shutil.rmtree(self.venvDir)
        else:
            print "NSSSession: An exception occurred, leaving directory at",self.venvDir

    @staticmethod
    def childprocess(profilePath):
        nss = None
        signal.signal(signal.SIGTERM, lambda signum,frame: nss.shutdown() if nss else None)
        while True:
            args = sys.stdin.readline().rstrip().split(" ")
            if len(args) < 1:
                continue
            # init password if not set
            if args[0] == "password":
                nss = NSS(profilePath, args[1])
                sys.stdout.write("ok\n")
            elif not nss:
                nss = NSS(profilePath)

            # now the real commands
            if args[0] == "encrypt":
                sys.stdout.write(nss.encryptString(args[1]) + "\n")
            elif args[0] == "decrypt":
                if not nss: nss = NSS(profilePath)
                sys.stdout.write(nss.decryptString(args[1]) + "\n")

            sys.stdout.flush()

    def start(self):
        if not self.subproc:
            executable = os.path.basename(sys.executable)
            self.subproc = subprocess.Popen([os.path.join(self.binDir, executable),
                                             os.path.join(self.binDir, self.leafName),
                                             os.path.abspath(self.profilePath)],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            cwd=self.binDir,
                                            bufsize=0)
            if self.password:
                self._command('password', self.password)

    def stop(self):
        if self.subproc:
            try:
                self.subproc.kill()
            except OSError:
                pass
            self.subproc = None


    def encrypt(self, data):
        return self._command("encrypt", data)
    def decrypt(self, data):
        return self._command("decrypt", data)

    def _command(self, *args):
        if not self.subproc:
            self.start()

        self.subproc.stdin.write(" ".join(args) + "\n")
        return self.subproc.stdout.readline().rstrip()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        profilePath = sys.argv[1]
        NSSSession.childprocess(profilePath)
