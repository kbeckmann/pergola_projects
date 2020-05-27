from nmigen import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

class DelayFApplet(Applet, applet_name="delayf"):
    help = "DELAYF example"
    description = """
    Outputs two 100MHz signals where the second
    is delayed using the DELAYF block.
    The delay is changed in periodically.
    Observe with an oscilloscope.
    """

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
        pmod1 = platform.request("pmod", 0, dir="o")

        timer = Signal(28)

        m = Module()

        m.submodules.pll2 = ECP5PLL([
            ECP5PLLConfig("sync", 100),
        ])        

        m.domains += ClockDomain("shifted")
        m.submodules.clkdiv2 = Instance("DELAYF",
            i_A=ClockSignal("sync"),
            i_LOADN=1,
            i_MOVE=timer[-9],
            i_DIRECTION=timer[-1],

            o_Z=ClockSignal(domain="shifted"),

            p_DEL_MODE="USER_DEFINED",
            p_DEL_VALUE=0
        )

        m.d.sync += timer.eq(timer + 1)

        m.d.comb += pmod1.eq(Cat(
            ClockSignal("sync"),
            ClockSignal("shifted"),
        ))

        return m
