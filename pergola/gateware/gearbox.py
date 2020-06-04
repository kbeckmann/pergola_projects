from nmigen import *
from nmigen.back.pysim import Simulator, Active
from nmigen.lib.fifo import AsyncFIFOBuffered

from ..util.test import FHDLTestCase


class Gearbox(Elaboratable):
    def __init__(self, width_in, width_out, domain_in, domain_out, depth=3):
        self.width_in = width_in
        self.width_out = width_out
        self.depth = depth
        self.domain_in = domain_in
        self.domain_out = domain_out

        self.data_in = Signal(width_in)
        self.data_out = Signal(width_out)

        self.ctr_in = Signal(range(width_out))
        self.ctr_out = Signal(range(width_in))

    def elaborate(self, platform):
        m = Module()

        width_in = self.width_in
        width_out = self.width_out
        depth = self.depth
        domain_in = self.domain_in
        domain_out = self.domain_out

        data_in = self.data_in
        data_out = self.data_out

        ctr_in = self.ctr_in
        ctr_out = self.ctr_out

        fifo_width = width_in * width_out

        fifo_data_in = Signal(fifo_width)
        fifo_data_out = Signal(fifo_width)

        m.submodules.fifo = fifo = AsyncFIFOBuffered(
            width=fifo_width,
            depth=depth,
            exact_depth=True,
            w_domain=domain_in,
            r_domain=domain_out,
        )

        with m.If(ctr_in == (width_out - 1)):
            m.d[domain_in] += ctr_in.eq(0)
        with m.Else():
            m.d[domain_in] += ctr_in.eq(ctr_in + 1)

        with m.If(ctr_out == (width_in - 1)):
            m.d[domain_out] += ctr_out.eq(0)
        with m.Else():
            m.d[domain_out] += ctr_out.eq(ctr_out + 1)

        m.d.comb += fifo.w_data.eq(fifo_data_in)
        m.d[domain_in] += fifo.w_en.eq(fifo.w_rdy & (ctr_in == (width_out - 1)))
        m.d[domain_in] += fifo_data_in.eq(Cat(fifo_data_in[width_in:], data_in))

        m.d[domain_out] += fifo.r_en.eq(fifo.r_rdy & (ctr_out == (width_in - 1)))
        with m.If(ctr_out == 0):
            m.d[domain_out] += fifo_data_out.eq(fifo.r_data)
        with m.Else():
            m.d[domain_out] += fifo_data_out.eq(fifo_data_out[width_out:])

        m.d.comb += data_out.eq(fifo_data_out[:width_out])

        return m


class GearboxTest(FHDLTestCase):
    def test_gearbox(self):
        m = Module()

        m.submodules.gearbox = gearbox = Gearbox(
            width_in=3,
            width_out=2,
            domain_in="slow",
            domain_out="fast",
            depth=3,
        )

        m.d.comb += gearbox.data_in.eq(0b101)

        sim = Simulator(m)

        sim.add_clock(1/2e6, domain="slow")
        sim.add_clock(1/3e6, domain="fast")

        def process_slow():
            yield Active()
            for i in range(100):
                # yield gearbox.data_in.eq(i)
                yield

        # sim.add_sync_process(process, domain="fast")
        sim.add_sync_process(process_slow, domain="slow")
        with sim.write_vcd("gearbox.vcd"):
            sim.run()

