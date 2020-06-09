import os
import subprocess

from nmigen import *
from nmigen.build import *
from nmigen_boards.resources import *

from .pergola import PergolaPlatform


__all__ = ["VerilatorPlatform"]


class VerilatorPlatform(PergolaPlatform):
    # Skip the synth step
    _trellis_command_templates = [
        r"""
        {{invoke_tool("yosys")}}
            {{quiet("-q")}}
            {{get_override("yosys_opts")|options}}
            -l {{name}}.rpt
            {{name}}.ys
        """,
        r"""
        {{invoke_tool("nextpnr-ecp5")}}
            {{quiet("--quiet")}}
            {{get_override("nextpnr_opts")|options}}
            --log {{name}}.tim
            {{platform._nextpnr_device_options[platform.device]}}
            --package {{platform._nextpnr_package_options[platform.package]|upper}}
            --speed {{platform.speed}}
            --json {{name}}.json
            --lpf {{name}}.lpf
            --textcfg {{name}}.config
        """
    ]