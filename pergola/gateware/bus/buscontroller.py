from nmigen import *

from enum import IntEnum

class Opcodes(IntEnum):
    NOP = 0
    MOV_R0 = 1
    ADD_R0 = 2
    READ = 3
    WRITE_R0 = 4
    WRITE_IMM = 5
    WFI = 6
    JMP = 7

class Asm():
    # nop
    def NOP():
        return (Opcodes.NOP << 32)

    # R0 <- value
    def MOV_R0(value):
        return (Opcodes.MOV_R0 << 32) | value

    # R0 <- R0 + value
    def ADD_R0(value):
        return (Opcodes.ADD_R0 << 32) | value

    # R0 <- *addr
    def READ(addr):
        return (Opcodes.READ << 32) | addr

    # addr <- R0
    def WRITE_R0(addr):
        return (Opcodes.WRITE_R0 << 32) | addr

    # *R0 <- value
    def WRITE_IMM(value):
        return (Opcodes.WRITE_IMM << 32) | value

    # wait for all bits in irq to be simultaneously asserted
    def WFI(irq):
        return (Opcodes.WFI << 32) | irq

    # pc <- rom_addr
    def JMP(rom_addr):
        return (Opcodes.JMP << 32) | rom_addr

class BusController(Elaboratable):
    def __init__(self, bus, irq, program):
        self.bus = bus
        self.irq = irq
        self.program = program

        self.rom = Memory(width=3+32, depth=len(self.program), init=self.program)
        self.pc = Signal(range(len(self.program)))
        self.r0 = Signal(32)

        for x in program:
            print(hex(x))

    def elaborate(self, platform):
        bus = self.bus
        irq = self.irq

        rom = self.rom
        pc = self.pc
        r0 = self.r0

        m = Module()

        m.submodules.mem_rd = mem_rd = rom.read_port()

        opcode = Signal(3)
        value = Signal(32)
        m.d.comb += [
            opcode.eq(mem_rd.data[32:]),
            value.eq(mem_rd.data[:32]),
        ]

        m.d.comb += mem_rd.addr.eq(pc)

        # Decode & Execute

        foo = Signal(8)

        ready = Signal()
        m.d.sync += ready.eq(1)

        fetching = Signal()
        with m.If(fetching == 1):
            m.d.sync += fetching.eq(0)
        with m.Else():
            with m.Switch(opcode):
                with m.Case(Opcodes.NOP):
                    m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

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
                    m.d.sync += foo.eq(foo + 1)
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
                            with m.If(bus.ack):
                                m.next = "INIT"
                                m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

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
                    with m.If((self.irq & value[:8]) == value[:8]):
                        m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

                with m.Case():
                    m.d.sync += [pc.eq(pc + 1), fetching.eq(1)]

        return m
