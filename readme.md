# Vapoursynth Toolset Installer for Ubuntu
Vapoursynth Toolset Installer is a python script that automates downloading, compiling and installing all dependencies and many plugins for vapoursynth and vapoursynth edit. Currently it does not include encoders like `x264` and tools like `mkvtoolnix`.
## Usage
First run `sudo apt install -y python3-pip`, then download this repo as zip, and run `python3 install.py`.

```
python3 install.py [-d folder] [--plugins-only] [package1 package2 ...]
```
If no options given will install all packages available in `package_info.json`.

`-d` specifies the folder, where the script downloads all code.

`--plugins-only` installs all vapoursynth plugins only.

`package1 package2 ...` specifies the packages to install, instead of installing everything.

## Not Yet Supported
Here is a list of known plugins with build issues. They will be added once the issues are resolved. If you have found a unlisted installable plugin, please write an issue or make a PR.

`vs-vmaf`, `vs-vsf`, `vs-xyvsf`, `vs-svp1`, `vs-svp2`, `vs-vcfreq`, `vs-vcmod`, `vs-vcmove`, `vs-avsreader`, `vs-znedi3`

## Compatibility
This script is only tested on Ubuntu 18.04 and 19+, and there are known build issues with 16.04. It will definitely not work on any non-debian derivatives.
