"""Retrievable secrets: per-user Windows DPAPI, or OS keychain. No plaintext fallback."""
import ctypes
from ctypes import wintypes
import hashlib
import os
import sys
import threading
from .paths import data_dir

_LOCK = threading.RLock()
SERVICE = "org.xengagement.assistant"
PUBLIC_SECRET_NAMES = {"x_client_secret", "x_bearer_token", "ai_api_key"}

class SecretStore:
    def __init__(self, directory=None):
        self.directory = directory or data_dir() / "secrets"

    def _path(self, name):
        return self.directory / (hashlib.sha256(name.encode()).hexdigest() + ".bin")

    @staticmethod
    def _crypt(value, decrypt=False):
        class Blob(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]
        buffer = ctypes.create_string_buffer(value)
        source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        output = Blob()
        crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
            raise RuntimeError("Windows could not unlock secure storage for this user.")
        try:
            return ctypes.string_at(output.data, output.size)
        finally:
            kernel.LocalFree(output.data)

    @staticmethod
    def _keyring():
        import keyring
        backend = keyring.get_keyring()
        module = type(backend).__module__.lower()
        if not any(part in module for part in ("secretservice", "macos", "kwallet")):
            raise RuntimeError("An OS keychain is required. Install/unlock the system keychain; plaintext storage is disabled.")
        return keyring

    def get(self, name):
        with _LOCK:
            if sys.platform == "win32":
                path = self._path(name)
                return self._crypt(path.read_bytes(), True).decode() if path.exists() else ""
            return self._keyring().get_password(SERVICE, name) or ""

    def set(self, name, value):
        with _LOCK:
            if not value:
                return self.delete(name)
            if sys.platform == "win32":
                self.directory.mkdir(parents=True, exist_ok=True)
                path = self._path(name)
                temporary = path.with_suffix(".tmp")
                temporary.write_bytes(self._crypt(value.encode()))
                temporary.replace(path)
            else:
                self._keyring().set_password(SERVICE, name, value)

    def delete(self, name):
        with _LOCK:
            if sys.platform == "win32":
                self._path(name).unlink(missing_ok=True)
            else:
                ring = self._keyring()
                if ring.get_password(SERVICE, name):
                    ring.delete_password(SERVICE, name)

    def masked(self, name):
        value = self.get(name)
        return ("????????????" + value[-4:]) if len(value) > 4 else ("????????" if value else "")

store = SecretStore()
