from nmigen import *
from nmigen.back.pysim import Simulator, Active
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *

from .. import Applet


class Blinky(Elaboratable):
    def __init__(self, led, btn):
        self.led = led
        self.btn = btn
        self.blink = Signal()
        self.timer = Signal(24)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)
        m.d.comb += self.led.eq(self.blink)

        with m.If(self.btn):
            m.d.comb += self.blink.eq(1)
        with m.Else():
            m.d.comb += self.blink.eq(self.timer[-1])

        return m


class BlinkyTest(FHDLTestCase):
    def test_blinky(self):
        btn = Signal()
        led = Signal()
        m = Module()
        blinky = m.submodules.blinky = Blinky(led, btn)

        sim = Simulator(m)
        sim.add_clock(1e-6)
        def process():
            yield Active()
            assert (yield blinky.timer) == 0
            yield
            assert (yield blinky.timer) == 1
            yield
            assert (yield blinky.timer) == 2
            yield
            assert (yield blinky.timer) == 3
            yield

        sim.add_sync_process(process)
        with sim.write_vcd("blinky.vcd"):
            sim.run()

    def test_blinky_formal(self):
        btn = Signal()
        led = Signal()

        m = Module()
        m.submodules.blinky = Blinky(led, btn)

        # If the button is pressed, the led should always be on
        m.d.comb += Assert(btn.implies(led))

        self.assertFormal(m, depth=10)


class BlinkyApplet(Applet, applet_name="blinky"):
    description = "Blinks some LEDs"
    help = "Blinks some LEDs"

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        led = platform.request("led", 0)
        btn = platform.request("button", 0)

        m = Module()

        m.submodules.blinky = Blinky(led.o, btn)

        return m
