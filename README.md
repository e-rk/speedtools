# About

This project provides data extraction utilities for the following Need for Speed 4 HS asset files:
- tracks
- cars

Additionally, Blender addon is provided to directly import track and car data.

# Setup (Blender addon version)

1. Open Blender and open the __Scripting__ tab
2. In console, type paste the following two commands:
   ```
   import sys, subprocess
   subprocess.call([sys.executable, "-m", "pip", "install", "speedtools"])
   ```
   This command will install the `speedtools` package to your Blender Python installation.

   > **Note**: Python installation that comes with Blender is completely separate from the global Python installation on your system. For this reason, it is necessary to use the Blender scripting console to install the package correctly.
3. Copy and paste the content of [this](https://github.com/e-rk/speedtools/blob/master/speedtools/blender/io_nfs4_import.py) file to the Blender scripting window.
4. Click the __▶__ button.
5. You should see `Track resources` and `Car resources` under `File>Import`.

Until I figure out a better way to install Blender addons, this must suffice.

# Setup (command line version)

Install the package from PyPI:
```
pip install speedtools
```

Currently, the command line version does not provide any useful functionality.

# Known issues and limitations

* Some tracks are not imported with correct textures
* Tested only with PC tracks