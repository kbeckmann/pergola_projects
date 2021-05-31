'''
Simple wishbone slave/target
'''

from nmigen import *
from nmigen.hdl.rec import Direction

class WishboneSlave(Elaboratable):
    def __init__(self, addr_width=32, data_width=32, granularity=32):
        self.addr_width = addr_width
        self.data_width = data_width
        self.granularity = granularity

        layout = [
            ("adr",   addr_width, Direction.FANOUT),
            ("dat_w", data_width, Direction.FANOUT),
            ("dat_r", data_width, Direction.FANIN),
            ("sel",   data_width // granularity, Direction.FANOUT),
            ("cyc",   1, Direction.FANOUT),
            ("stb",   1, Direction.FANOUT),
            ("we",    1, Direction.FANOUT),
            ("ack",   1, Direction.FANIN),
        ]

        self.bus = Record(layout=layout)
    
    def elaborate(self, platform):
        m = Module()

        m.d.comb += wrapper.cs.eq(0)
        m.d.comb += wrapper.we.eq(wb.we)
        m.d.comb += wrapper.addr.eq(wb.adr[2:8])

        ack_r = Signal()

        with m.If(wb.stb & wb.cyc & (wb.adr[8:] == (MPRJ_BASE_ADR >> 8))):
            m.d.comb += wrapper.cs.eq(1)
            m.d.comb += wb.dat_r.eq(wrapper.read_data)
            m.d.comb += wrapper.write_data.eq(wb.dat_w)
            m.d.sync += wb.ack.eq(ack_r)
            m.d.sync += ack_r.eq(0)
        with m.Else():
            m.d.sync += ack_r.eq(1)

        return m


