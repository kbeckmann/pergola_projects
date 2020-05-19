from nmigen import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

class PLLApplet(Applet, applet_name="pll"):
    help = "Blinky with PLL"
    description = """
    Blinky with PLL

    You can measure the LEDs frequencies using a cheap multimeter to verify.
    (f_blink = f / 2**16)
    LED0:  976.6 Hz
    LED2:  488.3 Hz
    LED4: 4394.5 Hz
    LED6: 1757.8 Hz

    """

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
        led1 = platform.request("led", 0)
        led2 = platform.request("led", 2)
        led3 = platform.request("led", 4)
        led4 = platform.request("led", 6)

        timer1 = Signal(16)
        timer2 = Signal(16)
        timer3 = Signal(16)
        timer4 = Signal(16)

        m = Module()

        m.submodules.pll = ECP5PLL([
            ECP5PLLConfig("sync", 64),
            ECP5PLLConfig("fast", 32, phase=13),
            ECP5PLLConfig("fast2", 210, error=100),
            ECP5PLLConfig("fast3", 114, error=2),
        ])

        m.d.sync += timer1.eq(timer1 + 1)
        m.d.fast += timer2.eq(timer2 + 1)
        m.d.fast2 += timer3.eq(timer3 + 1)
        m.d.fast3 += timer4.eq(timer4 + 1)

        m.d.comb += led1.o.eq(timer1[-1])
        m.d.comb += led2.o.eq(timer2[-1])
        m.d.comb += led3.o.eq(timer3[-1])
        m.d.comb += led4.o.eq(timer4[-1])


        return m
