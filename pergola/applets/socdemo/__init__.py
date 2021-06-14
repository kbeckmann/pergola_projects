from nmigen import *

from .. import Applet
from ...gateware.bus.buscontroller import Asm, BusController
from ...gateware.bus.wb import get_layout


class SOCDemoApplet(Applet, applet_name="socdemo"):
    help = "SOC demo"
    description = """

    """

    @classmethod
    def add_run_arguments(cls, parser):
        pass

    def __init__(self, args):
        pass

    def elaborate(self, platform):
 
        m = Module()

        wb = Record(get_layout())
        irq = Signal()

        m.submodules.buscontroller = buscontroller = BusController(
            bus=wb,
            irq=irq,
            program=[
                Asm.MOV_R0(0),
                Asm.ADD_R0(1),
                Asm.WRITE_R0(0),
                Asm.JMP(1),
            ],
        )

        leds = Cat([platform.request("led", i) for i in range(8)])
        m.d.comb += leds.eq(buscontroller.r0[16:])

        o32 = Cat([platform.request("pmod", i, dir="o") for i in range(4)])
        m.d.comb += o32.eq(buscontroller.r0)

        return m
