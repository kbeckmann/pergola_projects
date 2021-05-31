from nmigen import *

from enum import IntEnum

class Opcodes(IntEnum):
    READ = 0
    WRITE = 1
    WRITE_R0_ADD = 2
    WFI = 3
    JMP = 4

class Asm():
    def READ(addr, value):
        return (Opcodes.READ << 64) | (value << 32) | addr

    def WRITE(addr, value):
        return (Opcodes.WRITE << 64) | (value << 32) | addr

    def WRITE_R0_ADD(addr, value):
        return (Opcodes.WRITE_R0_ADD << 64) | (value << 32) | addr

    def WFI(irq):
        return (Opcodes.WFI << 64) | irq

    def JMP(rom_addr):
        return (Opcodes.JMP << 64) | rom_addr

class BusController(Elaboratable):
    def __init__(self, bus, irq, program):
        self.bus = bus
        self.irq = irq
        self.program = program

        self.rom = Memory(width=3+32+32, depth=len(self.program), init=self.program)
        self.pc = Signal(range(len(self.program)))
        self.r0 = Signal(32)

    def elaborate(self, platform):
        bus = self.bus
        irq = self.irq

        rom = self.rom
        pc = self.pc
        r0 = self.r0

        m = Module()

        m.submodules.mem_rd = mem_rd = rom.read_port()

        m.d.comb += [
            mem_rd.addr.eq(pc)
        ]

        # Decode
        with m.Switch(mem_rd.data[64:]):
            with m.Case(Opcodes.READ):
                with m.FSM():
                    with m.State("INIT"):
                        # One clock cycle with deasserted bus signals
                        m.next = "READ"
                    with m.State("READ"):
                        m.d.comb += [
                            bus.cyc.eq(1),
                            bus.stb.eq(1),
                            bus.adr.eq(mem_rd.data[:32]),
                        ]
                        with m.If(bus.ack):
                            m.d.sync += [
                                r0.eq(bus.dat_r),
                                pc.eq(pc + 1)
                            ]
                            m.next = "INIT"
            with m.Case(Opcodes.WRITE):
                with m.FSM():
                    with m.State("INIT"):
                        # One clock cycle with deasserted bus signals
                        m.next = "WRITE"
                    with m.State("WRITE"):
                        m.d.comb += [
                            bus.cyc.eq(1),
                            bus.stb.eq(1),
                            bus.adr.eq(mem_rd.data[:32]),
                            bus.dat_w.eq(mem_rd.data[32:64]),
                            bus.sel.eq(0b1111),
                            bus.we.eq(0b1),
                        ]
                        with m.If(bus.ack):
                            m.next = "INIT"
                            m.d.sync += pc.eq(pc + 1)

            with m.Case(Opcodes.WRITE_R0_ADD):
                with m.FSM():
                    with m.State("INIT"):
                        # One clock cycle with deasserted bus signals
                        m.next = "WRITE"
                    with m.State("WRITE"):
                        m.d.comb += [
                            bus.cyc.eq(1),
                            bus.stb.eq(1),
                            bus.adr.eq(mem_rd.data[:32]),
                            bus.dat_w.eq(mem_rd.data[32:64] + r0),
                            bus.sel.eq(0b1111),
                            bus.we.eq(0b1),
                        ]
                        with m.If(bus.ack):
                            m.next = "INIT"
                            m.d.sync += pc.eq(pc + 1)

            with m.Case(Opcodes.JMP):
                m.d.sync += pc.eq(mem_rd.data[:8])

            with m.Case(Opcodes.WFI):
                with m.If((self.irq & mem_rd.data[:8]) == mem_rd.data[:8]):
                    m.d.sync += pc.eq(pc + 1)

            with m.Case():
                m.d.sync += pc.eq(pc + 1)




        return m
