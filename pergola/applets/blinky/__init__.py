from nmigen import *
from .. import Applet

class Blinky(Applet, applet_name="blinky"):
    description = "Blinks some LEDs"
    help = "Blinks some LEDs"

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
        led   = platform.request("led", 0)
        btn   = platform.request("button", 0)
        timer = Signal(24)

        m = Module()

        m.d.sync += timer.eq(timer + 1)
        m.d.comb += led.o.eq(self.blink)

        with m.If(btn):
            m.d.comb += self.blink.eq(1)
        with m.Else():
            m.d.comb += self.blink.eq(timer[-1])

        return m

