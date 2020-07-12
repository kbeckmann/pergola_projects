from nmigen import *
from nmigen.back.pysim import Simulator, Active
from nmigen.back import cxxrtl
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *
from nmigen_boards.resources import *
from nmigen.build import *

from .. import Applet
from ...gateware.uart import UART


class UARTApplet(Applet, applet_name="uart"):
    description = "UART loopback"
    help = "UART loopback"

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--baudrate", default=115200, type=int,
            help="Baudrate")

        parser.add_argument(
            "--stopbits", default=1, type=int,
            help="Number of stop bits. Add more if your receiver is glitching.")

    def __init__(self, args):
        self.baudrate = args.baudrate
        self.stopbits = args.stopbits

    def elaborate(self, platform):
        leds = [platform.request("led", i) for i in range(8)]
        btn = platform.request("button", 0)

        # Uncomment to use pmod1 instead

        # platform.add_resources([
        #     UARTResource("pmod1_uart", 0,
        #         rx="L1", tx="P2",
        #         attrs=Attrs(IO_TYPE="LVCMOS33", PULLUP=1)
        #     ),
        # ])

        # uart_pins = platform.request("pmod1_uart", 0)
        uart_pins = platform.request("uart", 0)

        m = Module()

        m.submodules.uart = uart = UART(
            divisor=round(platform.default_clk_frequency / self.baudrate),
            stopbits=self.stopbits
        )

        m.d.comb += uart.rx_i.eq(uart_pins.rx)
        m.d.comb += uart_pins.tx.o.eq(uart.tx_o)

        m.d.comb += leds[0].o.eq(uart.rx_rdy)
        m.d.comb += leds[1].o.eq(uart.rx_ack)
        m.d.comb += leds[2].o.eq(uart.rx_ovf)
        m.d.comb += leds[3].o.eq(uart.rx_err)
        m.d.comb += leds[4].o.eq(uart.tx_ack)
        m.d.comb += leds[5].o.eq(uart.tx_rdy)

        with m.If(~uart.rx_err & uart.rx_rdy & ~uart.rx_ack):
            m.d.sync += [
                uart.tx_rdy.eq(1),
                uart.tx_data.eq(uart.rx_data),
                uart.rx_ack.eq(1)
            ]
        with m.Elif(uart.tx_ack):
            m.d.sync += uart.tx_rdy.eq(0)
            m.d.sync += uart.rx_rdy.eq(0)
            m.d.sync += uart.rx_ack.eq(0)

        return m
