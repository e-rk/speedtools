#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from pathlib import Path

import setuptools
import setuptools.command.build
from setuptools import Command
from setuptools.errors import ExecError


class build_ksy(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build_lib = None
        self.editable_mode = False

    def initialize_options(self):
        self.files = {}
        self.package = []
        self.compiler = None

    def finalize_options(self):
        self.set_undefined_options("build_py", ("build_lib", "build_lib"))
        self.packages = self.distribution.packages
        for package in self.packages:
            package_path = Path(*(package.split(".")))
            for source_file in Path(package_path, "specs").glob("*.ksy"):
                build_file = Path(self.build_lib, package_path, source_file.name)
                self.files[build_file] = source_file

    def run(self):
        for build, source in self.files.items():
            target_path = (
                Path(build.parent, "parsers")
                if not self.editable_mode
                else Path(source.parent.parent, "parsers")
            )
            args = [
                "--outdir",
                str(target_path),
                "-t",
                "python",
                "--python-package",
                "speedtools.parsers",
                str(source),
            ]
            try:
                self.spawn(["ksc"] + args)
            except ExecError:
                self.spawn(["kaitai-struct-compiler.bat"] + args)

    def get_output_mapping(self):
        mapping = {}
        for key, value in self.files.items():
            mapping[str(key)] = str(value)
        return mapping

    def get_outputs(self):
        return list(map(str, self.files.keys()))

    def get_source_files(self):
        return list(map(str, self.files.values()))


setuptools.command.build.build.sub_commands.append(("build_ksy", None))

setuptools.setup(cmdclass={"build_ksy": build_ksy})
