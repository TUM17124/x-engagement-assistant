# Dependency licensing review

The project's original code remains MIT. No code from an incompatible third-party application was copied into this upgrade.

Direct runtime components use permissive or compatible licenses: FastAPI (MIT), Starlette/Uvicorn/HTTPX (BSD), Jinja2 (BSD), python-dotenv (BSD), python-multipart (Apache-2.0), itsdangerous (BSD), keyring (MIT), Python (PSF), SQLite (public domain), and Tauri/plugins (MIT or Apache-2.0). TLS certificate data may carry MPL-2.0 terms; retain its notices.

PyInstaller is a build tool with a bootloader distribution exception; its exception permits distributing bundled applications under their own licenses. Pillow is also a runtime dependency for local media previews and derivatives. PyJWT and cryptography provide JWT signature verification; their resolved notices are included. Build tools do not change this project's MIT license.

Upstream references: [PyInstaller license and exception](https://pyinstaller.org/en/stable/license.html), [Tauri licensing](https://github.com/tauri-apps/tauri/blob/dev/LICENSE_MIT).

Dependencies and transitive licenses can change. Review the resolved package-lock.json, Cargo.lock, and Python package metadata when updating a release; preserve upstream notices. This review is an engineering compatibility check, not a legal opinion.
