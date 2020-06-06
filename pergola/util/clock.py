from nmigen import *
from nmigen.utils import log2_int

class ClockDividerInterface:
    def __init__(self, divisor, cd_out, cd_in="sync"):
        self.divisor = int(divisor)
        self.cd_out = cd_out
        self.cd_in = cd_in

        self.clk = Signal()

class ClockDividerNPOT(Elaboratable, ClockDividerInterface):
    def __init__(self, divisor, cd_out, cd_in="sync"):
        super().__init__(divisor=divisor, cd_out=cd_out, cd_in=cd_in)

    def elaborate(self, platform):
        divisor = self.divisor
        cd_out = self.cd_out
        cd_in = self.cd_in
        clk = self.clk

        m = Module()

        m.domains += ClockDomain(cd_out)

        if divisor % 2 == 0:
            divisor //= 2
            counter = Signal(range(divisor))

            with m.If(counter == (divisor - 1)):
                m.d[cd_in] += counter.eq(0)
                m.d[cd_in] += clk.eq(~clk)
            with m.Else():
                m.d[cd_in] += counter.eq(counter + 1)
    
            m.d.comb += ClockSignal(cd_out).eq(clk)
        else:
            counter = Signal(range(divisor))

            with m.If(counter == (divisor - 1)):
                m.d[cd_in] += counter.eq(0)
            with m.Else():
                m.d[cd_in] += counter.eq(counter + 1)
            
            m.d.comb += clk.eq(counter <= divisor // 2)

            clk_r = Signal()
            m.d[cd_in] += clk_r.eq(clk)
            m.d.comb += ClockSignal(cd_out).eq(clk_r)

        return m


class ClockDividerPOT(Elaboratable, ClockDividerInterface):
    def __init__(self, divisor, cd_out, cd_in="sync"):
        super().__init__(divisor=divisor, cd_out=cd_out, cd_in=cd_in)

    def elaborate(self, platform):
        divisor = self.divisor
        cd_out = self.cd_out
        cd_in = self.cd_in
        clk = self.clk

        divisor_bits = log2_int(divisor)

        m = Module()

        m.domains += ClockDomain(cd_out)

        cd_temp = "_{}_{}".format(cd_out, 0)
        m.domains += ClockDomain(cd_temp, local=True)
        m.d.comb += ClockSignal(cd_temp).eq(ClockSignal(cd_in))

        for i in range(divisor_bits):
            cd_cur = "_{}_{}".format(cd_out, i)
            cd_next = "_{}_{}".format(cd_out, i + 1)
            m.domains += ClockDomain(cd_next, local=True)
            m.d[cd_cur] += ClockSignal(cd_next).eq(~ClockSignal(cd_next))

        cd_last = "_{}_{}".format(cd_out, divisor_bits)
        m.d.comb += ClockSignal(cd_out).eq(ClockSignal(cd_last))

        return m

class ClockDivider(Elaboratable, ClockDividerInterface):
    def __init__(self, divisor, cd_out, cd_in="sync"):
        super().__init__(divisor=divisor, cd_out=cd_out, cd_in=cd_in)

    def elaborate(self, platform):
        m = Module()

        r = (self.divisor - 1).bit_length()
        if (1 << r) != self.divisor:
            m.submodules.divider = divider = ClockDividerNPOT(
                divisor=self.divisor,
                cd_out=self.cd_out,
                cd_in=self.cd_in)
        else:
            m.submodules.divider = divider = ClockDividerPOT(
                divisor=self.divisor,
                cd_out=self.cd_out,
                cd_in=self.cd_in)

        m.d.comb += self.clk.eq(divider.clk)

        return m