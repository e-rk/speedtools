# Format specs files
This directory contains [Kaitai Struct](https://kaitai.io/) declarative descriptions of file formats used by NFSHS. See the project's [User Guide](https://doc.kaitai.io/user_guide.html) to learn how to use the specs files.

The specs can be quite conveniently developed using the [Web IDE](https://ide.kaitai.io/). Here are some points to look out for:
- It is not possible to unpack RefPack compressed data in the Web IDE. The decompressed FSH data should be written to disk and parsed as a separate file.

# License
The specs files are distributed under the terms of Creative Commons CC0-1.0.

# File format references
The project was not made in a vacuum. It is based on previous work of numerous people who took lots of time to reverse-engineer the file fromats and share their findings.

The following resources were used:
- [UNOFFICIAL NEED FOR SPEED III FILE FORMAT SPECIFICATIONS - Version 1.0](https://sites.google.com/site/2torcs/labs/need-for-speed-3---hot-pursuit/nfs3-the-unofficial-file-format-descriptions)
- T3ED documentation by Denis Auroux and Vitaly Kootin
- Source code of [LWO2FRD](https://github.com/OpenNFS/OpenNFS/files/6658908/FRD.2.LWO.zip) by KROM
- Source code of [OpenNFS](https://github.com/OpenNFS/OpenNFS) by Amrik Sadhra
- Source code of FHSTool by Denis Auroux
- [NFS Modder's Corner](https://nfsmodderscorner.blogspot.com/p/need-for-speed-high-stakes.html) by AJ_Lethal
- RefPack description on [Niotso Wiki](http://wiki.niotso.org/RefPack)
- and probably many others
