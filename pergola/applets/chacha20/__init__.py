from nmigen import *
from nmigen.build import *

from .. import Applet
from ...gateware.crypto.chacha20 import ChaCha20Cipher
from ...gateware.crypto.chacha20_fsm1 import ChaChaFSM1
from ...gateware.crypto.chacha20_fsm2 import ChaChaFSM2
from ...gateware.uart import UART
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

from struct import pack, unpack

from pergola.gateware.crypto import chacha20_fsm1


class ChaCha20ExampleApplet(Applet, applet_name="chacha20"):
    help = "ChaCha20 example"
    description = "ChaCha20 example"
    impl_map = {
        "fsm1": ChaChaFSM1,
        "fsm2": ChaChaFSM2
    }

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--implementation", default="fsm1", type=str,
            choices=ChaCha20ExampleApplet.impl_map.keys())

    def __init__(self, args):
        self.implementation = self.impl_map[args.implementation]

    def elaborate(self, platform):
        m = Module()

        m.submodules.chacha20 = chacha20 = ChaCha20Cipher(self.implementation)

        baudrate = 115200
        uart_pins = platform.request("uart", 0)
        m.submodules.uart = uart = UART(
            divisor=round(platform.default_clk_frequency / baudrate),
        )
        m.d.comb += uart.rx_i.eq(uart_pins.rx)
        m.d.comb += uart_pins.tx.o.eq(uart.tx_o)

        leds = Cat([platform.request("led", i) for i in range(8)])

        m.d.comb += leds.eq(chacha20.o_stream[0])

        key = bytes([i for i in range(32)])
        nonce = bytes([(i*16 + i) for i in range(12)])

        key_words = unpack("<8I", key)
        nonce_words = unpack("<3I", nonce)

        ctr = Signal(8)
        with m.FSM() as fsm:
            with m.State("INIT"):
                m.d.sync += [
                    chacha20.i_en.eq(1),
                    [chacha20.i_key[i].eq(key_words[i]) for i in range(len(key_words))],
                    [chacha20.i_nonce[i].eq(nonce_words[i]) for i in range(len(nonce_words))],
                ]
                m.next = "RUN"
            with m.State("RUN"):
                with m.If(chacha20.o_ready):
                    m.next = "PRINT"
            with m.State("PRINT"):
                # Print the block in hex
                with m.If(uart.tx_ack):
                    hex_out = Signal(8)
                    with m.Switch(ctr):
                        for i in range(64 * 2):
                            with m.Case(i):
                                data = chacha20.o_stream[i // 4 // 2]
                                j = ((i // 2) % 4) * 8
                                val = data[j+4:j+8] if i % 2 == 0 else data[j:j+4]
                                m.d.comb += hex_out.eq(Mux(val < 10, 0x30 + val, 0x41 - 10 + val))
                        with m.Case(128):
                            m.d.comb += hex_out.eq(0x0d)
                        with m.Case(129):
                            m.d.comb += hex_out.eq(0x0a)
                    m.d.sync += [
                        uart.tx_rdy.eq(1),
                        uart.tx_data.eq(hex_out),
                        ctr.eq(ctr + 1)
                    ]

        return m
