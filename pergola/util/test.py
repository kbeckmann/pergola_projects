"""
This file was copied and modified from the nMigen source code
nmigen/test/utils.py

Copyright (C) 2011-2019 M-Labs Limited

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Other authors retain ownership of their contributions. If a submission can
reasonably be considered independently copyrightable, it's yours and we
encourage you to claim it with appropriate copyright notices. This submission
then falls under the "otherwise noted" category. All submissions are strongly
encouraged to use the two-clause BSD license reproduced above.

"""


import os
import re
import shutil
import subprocess
import textwrap
import traceback
import unittest
import warnings
from contextlib import contextmanager

from nmigen.hdl.ast import *
from nmigen.hdl.ir import *
from nmigen.back import rtlil
from nmigen._toolchain import require_tool


__all__ = ["FHDLTestCase"]


class FHDLTestCase(unittest.TestCase):
    def assertRepr(self, obj, repr_str):
        if isinstance(obj, list):
            obj = Statement.cast(obj)
        def prepare_repr(repr_str):
            repr_str = re.sub(r"\s+",   " ",  repr_str)
            repr_str = re.sub(r"\( (?=\()", "(", repr_str)
            repr_str = re.sub(r"\) (?=\))", ")", repr_str)
            return repr_str.strip()
        self.assertEqual(prepare_repr(repr(obj)), prepare_repr(repr_str))

    @contextmanager
    def assertRaises(self, exception, msg=None):
        with super().assertRaises(exception) as cm:
            yield
        if msg is not None:
            # WTF? unittest.assertRaises is completely broken.
            self.assertEqual(str(cm.exception), msg)

    @contextmanager
    def assertRaisesRegex(self, exception, regex=None):
        with super().assertRaises(exception) as cm:
            yield
        if regex is not None:
            # unittest.assertRaisesRegex also seems broken...
            self.assertRegex(str(cm.exception), regex)

    @contextmanager
    def assertWarns(self, category, msg=None):
        with warnings.catch_warnings(record=True) as warns:
            yield
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].category, category)
        if msg is not None:
            self.assertEqual(str(warns[0].message), msg)

    def assertFormal(self, spec, mode="bmc", depth=1):
        """
        mode: bmc, prove
        """

        caller, *_ = traceback.extract_stack(limit=2)
        spec_root, _ = os.path.splitext(caller.filename)
        spec_dir = os.path.dirname(spec_root)
        spec_name = "{}_{}".format(
            os.path.basename(spec_root).replace("test_", "spec_"),
            caller.name.replace("test_", "")
        )

        # The sby -f switch seems not fully functional when sby is reading from stdin.
        if os.path.exists(os.path.join(spec_dir, spec_name)):
            shutil.rmtree(os.path.join(spec_dir, spec_name))

        config = textwrap.dedent("""\
        [options]
        mode {mode}
        depth {depth}
        wait on

        [engines]
        smtbmc

        [script]
        read_ilang top.il
        prep

        [file top.il]
        {rtlil}
        """).format(
            mode=mode,
            depth=depth,
            rtlil=rtlil.convert(Fragment.get(spec, platform="formal"))
        )
        f=open(os.path.join(spec_dir, spec_name + '.script'), "w")
        f.write(config)
        f.close()
        with subprocess.Popen([require_tool("sby"), "-f", "-d", spec_name], cwd=spec_dir,
                              universal_newlines=True,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(config)
            if proc.returncode != 0:
                self.fail("Formal verification failed:\n" + stdout)
