from nmigen import *
from nmigen.back.pysim import Simulator
from nmigen.utils import bits_for

from enum import IntEnum

from ...util.test import FHDLTestCase
from .wb import get_layout

class Opcodes(IntEnum):
    MOV_R0    = 0
    ADD_R0    = 1
    READ      = 2
    WRITE_R0  = 3
    WRITE_IMM = 4
    WFI       = 5
    JMP       = 6

class Asm():
    # R0 <- value
    def MOV_R0(value):
        return (Opcodes.MOV_R0 << 32) | (value & 0xffffffff)

    # R0 <- R0 + value
    def ADD_R0(value):
        return (Opcodes.ADD_R0 << 32) | (value & 0xffffffff)

    # R0 <- *addr
    def READ(addr):
        return (Opcodes.READ << 32) | (addr & 0xffffffff)

    # *addr <- R0
    def WRITE_R0(addr):
        return (Opcodes.WRITE_R0 << 32) | (addr & 0xffffffff)

    # *R0 <- value
    def WRITE_IMM(value):
        return (Opcodes.WRITE_IMM << 32) | (value & 0xffffffff)

    # wait for all bits in irq to be simultaneously asserted
    def WFI(irq):
        return (Opcodes.WFI << 32) | (irq & 0xff)

    # pc <- rom_addr
    def JMP(rom_addr):
        return (Opcodes.JMP << 32) | (rom_addr & 0xffffffff)

class BusController(Elaboratable):
    def __init__(self, bus, irq, program, immediate_width=32, bus_timeout=100):
        self.bus = bus
        self.irq = irq
        self.program = program
        self.immediate_width = immediate_width
        self.bus_timeout = bus_timeout

        self.opcode_width = bits_for(max(Opcodes).value)
        self.instruction_width = self.opcode_width + self.immediate_width

        self.rom = Memory(width=self.instruction_width, depth=len(self.program), init=self.program)
        self.pc = Signal(range(len(self.program)))
        self.r0 = Signal(immediate_width)
        self.tmo_ctr = Signal(range(bus_timeout + 1), reset=bus_timeout)

    def elaborate(self, platform):
        bus = self.bus
        irq = self.irq

        rom = self.rom
        pc = self.pc
        r0 = self.r0
        tmo_ctr = self.tmo_ctr

        m = Module()

        m.submodules.mem_rd = mem_rd = rom.read_port()

        # Fetch
        opcode = Signal(self.opcode_width)
        value = Signal(self.immediate_width)
        m.d.comb += [
            mem_rd.addr.eq(pc),
            opcode     .eq(mem_rd.data[self.immediate_width:]),
            value      .eq(mem_rd.data[:self.immediate_width]),
        ]

        # Decode, Execute, Bus/Memory, Write-back
        fetching = Signal(reset=1)
        with m.If(fetching == 1):
            m.d.sync += fetching.eq(0)
        with m.Else():
            with m.Switch(opcode):
                with m.Case(Opcodes.MOV_R0):
                    m.d.sync += r0.eq(value)
                    m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

                with m.Case(Opcodes.ADD_R0):
                    m.d.sync += r0.eq(r0 + value)
                    m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

                with m.Case(Opcodes.READ):
                    with m.FSM(name="read"):
                        with m.State("INIT"):
                            # One clock cycle with deasserted bus signals
                            m.next = "READ"
                        with m.State("READ"):
                            m.d.comb += [
                                bus.cyc.eq(1),
                                bus.stb.eq(1),
                                bus.adr.eq(value),
                            ]
                            with m.If(bus.ack):
                                m.d.sync += r0.eq(bus.dat_r)
                                m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]
                                m.next = "INIT"

                with m.Case(Opcodes.WRITE_R0):
                    with m.FSM(name="write_r0"):
                        with m.State("INIT"):
                            # One clock cycle with deasserted bus signals
                            m.next = "WRITE"
                        with m.State("WRITE"):
                            m.d.comb += [
                                bus.cyc.eq(1),
                                bus.stb.eq(1),
                                bus.adr.eq(value),
                                bus.dat_w.eq(r0),
                                bus.sel.eq(0b1111),
                                bus.we.eq(0b1),
                            ]
                            m.d.sync += tmo_ctr.eq(tmo_ctr - 1)
                            with m.If(bus.ack | (tmo_ctr == 0)):
                                m.next = "INIT"
                                m.d.sync += [
                                    tmo_ctr.eq(self.bus_timeout),
                                    pc.eq(pc + 1),
                                    fetching.eq(1)
                                ]

                with m.Case(Opcodes.WRITE_IMM):
                    with m.FSM(name="write_imm"):
                        with m.State("INIT"):
                            # One clock cycle with deasserted bus signals
                            m.next = "WRITE"
                        with m.State("WRITE"):
                            m.d.comb += [
                                bus.cyc.eq(1),
                                bus.stb.eq(1),
                                bus.adr.eq(r0),
                                bus.dat_w.eq(value),
                                bus.sel.eq(0b1111),
                                bus.we.eq(0b1),
                            ]
                            with m.If(bus.ack):
                                m.next = "INIT"
                                m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

                with m.Case(Opcodes.JMP):
                    m.d.sync += [pc.eq(value), fetching.eq(1)]

                with m.Case(Opcodes.WFI):
                    with m.If((irq & value[:8]) == value[:8]):
                        m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

                with m.Case():
                    m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

        return m

class BusControllerTest(FHDLTestCase):

    def test_basic(self):
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

        sim = Simulator(m)
        sim.add_clock(1/10e6, domain="sync")

        def process():
            for i in range(1000):
                yield

        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd"):
            sim.run()
