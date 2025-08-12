import os
import sys

mac_options = ""
if sys.platform == "darwin":
    mac_options = "--windowed --noupx"
    print('it is Mac, so shut up and do it')

cwd = os.path.abspath(os.getcwd())
cmd = r"cd %s; pyinstaller --clean pyinstaller.spec --noconfirm --workpath %s --distpath %s %s" % (
               os.path.join(".", "package", "pyinstaller"),
               os.path.join(".", "build-" + sys.platform),
               os.path.join(".", "dist-" + sys.platform),
               mac_options
        )

if sys.platform.startswith("darwin"):
    if "arm64" in sys.argv:
        os.putenv("PYMCA_PYINSTALLER_TARGET_ARCH", "arm64")
    elif "universal2" in sys.argv:
        os.putenv("PYMCA_PYINSTALLER_TARGET_ARCH", "universal2")
    elif "x86_64" in sys.argv:
        os.putenv("PYMCA_PYINSTALLER_TARGET_ARCH", "x86_64")
    else:
        # let PyInstaller choose according to platform
        pass

if sys.platform.startswith("win"):
    cmd = cmd.replace(";", "&")    
result = os.system(cmd)

os.chdir(cwd)
if result:
    print("Unsuccessful command <%s>" % cmd)
sys.exit(result)
