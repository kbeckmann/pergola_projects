from nmigen import *
from enum import IntEnum

class AccessFlags(IntEnum):
    R  = 1 << 0
    W  = 1 << 1

class BusWrapper(Elaboratable):

    def __init__(self, address_width=8, io_width=32, signals_r=[], signals_w=[]):
        self.address_width = address_width
        self.io_width = io_width

        self.cs         = Signal()
        self.we         = Signal()
        self.addr       = Signal(address_width)
        self.write_data = Signal(io_width)
        self.read_data  = Signal(io_width)

        self.endpoints_r = dict()
        self.endpoints_w = dict()
        self.add_endpoints(AccessFlags.R, signals_r)
        self.add_endpoints(AccessFlags.W, signals_w)

    def add_endpoints(self, flags: AccessFlags, signals: list[Signal], start=None):
        endpoints = self.endpoints_r if flags == AccessFlags.R else self.endpoints_w

        if start == None:
            start = len(endpoints)

        for s in signals:
            assert(self.io_width >= len(s))

        offset = 0
        for v in signals:
            assert((start + offset) not in endpoints)

            if isinstance(v, Array):
                offset += self.add_endpoints(flags, v, start + offset)
            else:
                endpoints.update({start + offset : v})
                offset += 1
        return offset

    def __repr__(self):
        lines = [f"Addr\tFlags\tName"]
        def print_endpoints(endpoints, type):
            l = []
            for i, v in endpoints.items():
                if isinstance(v, Signal):
                    name = v.name
                elif isinstance(v, Cat):
                    name = "_".join([part.name for part in v.parts])
                else:
                    # Create a name from a Slice()
                    name = f"{v.value.name}_{v.start}_{v.stop - 1}"
                l.append(f"{i:02x}\t{type}\t{name}")
            return l
        lines += print_endpoints(self.endpoints_r, "R")
        lines += print_endpoints(self.endpoints_w, "W")
        return "\n".join(lines)

    def elaborate(self, platform):
        m = Module()

        addr = self.addr
        read_data = self.read_data
        write_data = self.write_data

        with m.If(self.cs):
            with m.If(self.we):
                with m.Switch(addr):
                    for k, v in self.endpoints_w.items():
                        with m.Case(k):
                            m.d.sync += v.eq(write_data)
            with m.Else(): # ~we
                with m.Switch(addr):
                    for k, v in self.endpoints_r.items():
                        with m.Case(k):
                            # TODO: Maybe change to sync?
                            m.d.comb += read_data.eq(v)

        return m
