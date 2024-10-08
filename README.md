# About

This project provides data extraction utilities for the following Need for Speed 4 HS asset files:
- tracks
- cars

Additionally, Blender addon is provided to directly import track and car data.

# Setup (Blender addon version)

> **Warning**: The addon requires Blender 4.2 or newer. Use v0.16.0 release of the plugin if you have to use older Blender releases.

1. Create new empty Blender project
2. Open the __Scripting__ tab
3. Copy-paste the following two commands into the Blender console:
   ```
   import sys, subprocess
   subprocess.call([sys.executable, "-m", "pip", "install", "speedtools"])
   ```
   This command will install the [`speedtools`][1] package to your Blender Python installation.

   > **Note**: Python installation that comes with Blender is completely separate from the global Python installation on your system. For this reason, it is necessary to use the Blender scripting console to install the package correctly.
4. Copy and paste the content of [this][2] file to the Blender scripting window.
5. Click the __▶__ button.
6. You should see `Track resources` and `Car resources` under `File > Import`.

Until I figure out a better way to install Blender addons, this must suffice.

# Setup (command line version)

Install the package from PyPI:
```
pip install speedtools
```

Currently, the command line version does not provide any useful functionality.

# Development dependencies

To develop the project the following dependencies must be installed on your system:
* [Kaitai Struct compiler][3]

Make sure the binary directories are in your `PATH`.

# Re-make project

This tool is a part of the re-make project. The project source code is available [here][4].

[1]: https://pypi.org/project/speedtools/
[2]: https://github.com/e-rk/speedtools/blob/master/speedtools/blender/io_nfs4_import.py
[3]: https://kaitai.io/
[4]: https://github.com/e-rk/velocity
