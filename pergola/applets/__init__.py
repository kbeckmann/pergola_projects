# This is based on https://github.com/whitequark/Glasgow/blob/master/software/glasgow/applet/__init__.py
from nmigen import *

class Applet(Elaboratable):
    all = {}

    # Applet may override these and add arguments to the parser
    @classmethod
    def add_build_arguments(cls, parser):
        pass

    @classmethod
    def add_run_arguments(cls, parser):
        pass

    @classmethod
    def add_test_arguments(cls, parser):
        pass

    def __init_subclass__(cls, applet_name, **kwargs):
        super().__init_subclass__(**kwargs)

        if applet_name in cls.all:
            raise ValueError("Applet {!r} already exists".format(applet_name))

        cls.all[applet_name] = cls
        cls.applet_name = applet_name

    help = "applet help missing"
    description = "applet description missing"

    async def run(self):
        pass

from . import blinky
from . import delayf
from . import hdmi
from . import hdmi_splitter
from . import pll
from . import radio_tx
from . import xdr
