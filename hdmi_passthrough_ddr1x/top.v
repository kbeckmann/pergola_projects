module top
(
	// input wire btn,
	// output wire[7:0] led,
	inout [3:0] gpdi_in,
	inout [3:0] gpdi_out,
	inout [3:0] gpdi_out_secondary,
);

// gpdi_out[1] is inverted
// gpdi_out[2] is inverted
// gpdi_out[3] is inverted
// gpdi_in[0] is inverted
// gpdi_in[3] is inverted

// clock generator
wire locked;
wire clk_125MHz;
wire clk_25MHz;
clk_25_125_25
clock_instance
(
  .locked(locked),
	.clkin(~gpdi_in[3]),
	.clkout0(clk_125MHz),
	.clkout1(clk_25MHz)
);

reg rst = 0;
reg [1:0] q_r;
reg [1:0] q_g;
reg [1:0] q_b;
reg [1:0] q_clk;

reg [1:0] d_r;
reg [1:0] d_g;
reg [1:0] d_b;
reg [1:0] d_clk;


// Input DDR1x
IDDRX1F iddr1x_r(
  .SCLK(clk_125MHz),
  .D(gpdi_in[2]),
  .RST(rst),
  .Q0(q_r[0]),
  .Q1(q_r[1]),
);

IDDRX1F iddr1x_g(
  .SCLK(clk_125MHz),
  .D(gpdi_in[1]),
  .RST(rst),
  .Q0(q_g[0]),
  .Q1(q_g[1]),
);

IDDRX1F iddr1x_b(
  .SCLK(clk_125MHz),
  .D(gpdi_in[0]),
  .RST(rst),
  .Q0(q_b[0]),
  .Q1(q_b[1]),
);

// Output DDR1x to primary
ODDRX1F oddr1x_r(
  .SCLK(clk_125MHz),
  .D0(~shift_r[0]),
  .D1(~shift_r[1]),
  .RST(rst),
  .Q(gpdi_out[2]),
);

ODDRX1F oddr1x_g(
  .SCLK(clk_125MHz),
  .D0(~shift_g[0]),
  .D1(~shift_g[1]),
  .RST(rst),
  .Q(gpdi_out[1]),
);

ODDRX1F oddr1x_b(
  .SCLK(clk_125MHz),
  .D0(shift_b[0]),
  .D1(shift_b[1]),
  .RST(rst),
  .Q(gpdi_out[0]),
);

ODDRX1F oddr1x_clk(
  .SCLK(clk_125MHz),
  .D0(shift_clk[0]),
  .D1(shift_clk[1]),
  .RST(rst),
  .Q(gpdi_out[3]),
);

// Output DDR1x to secondary
ODDRX1F oddr1x_r_second(
  .SCLK(clk_125MHz),
  .D0(shift_r[0]),
  .D1(shift_r[1]),
  .RST(rst),
  .Q(gpdi_out_secondary[2]),
);

ODDRX1F oddr1x_g_second(
  .SCLK(clk_125MHz),
  .D0(shift_g[0]),
  .D1(shift_g[1]),
  .RST(rst),
  .Q(gpdi_out_secondary[1]),
);

ODDRX1F oddr1x_b_second(
  .SCLK(clk_125MHz),
  .D0(shift_b[0]),
  .D1(shift_b[1]),
  .RST(rst),
  .Q(gpdi_out_secondary[0]),
);

ODDRX1F oddr1x_clk_second(
  .SCLK(clk_125MHz),
  .D0(shift_clk[0]),
  .D1(shift_clk[1]),
  .RST(rst),
  .Q(gpdi_out_secondary[3]),
);



reg [9:0] shift_r,   shift_r_r = 0;
reg [9:0] shift_g,   shift_g_r = 0;
reg [9:0] shift_b,   shift_b_r = 0;
reg [9:0] shift_clk, shift_clk_r = 0;
always @(posedge clk_125MHz) begin
  shift_r   <= {shift_r[7:0],   q_r};
  shift_g   <= {shift_g[7:0],   q_g};
  shift_b   <= {shift_b[7:0],   ~q_b};
  shift_clk <= {shift_clk[7:0], clk_25MHz, clk_25MHz};
end


endmodule


module clk_25_125_25
(
    input clkin, // 25 MHz, 0 deg
    output clkout0, // 125 MHz, 0 deg
    output clkout1, // 25 MHz, 0 deg
    output locked
);
(* FREQUENCY_PIN_CLKI="25" *)
(* FREQUENCY_PIN_CLKOP="125" *)
(* FREQUENCY_PIN_CLKOS="25" *)
(* ICP_CURRENT="12" *) (* LPF_RESISTOR="8" *) (* MFG_ENABLE_FILTEROPAMP="1" *) (* MFG_GMCREF_SEL="2" *)
EHXPLLL #(
        .PLLRST_ENA("DISABLED"),
        .INTFB_WAKE("DISABLED"),
        .STDBY_ENABLE("DISABLED"),
        .DPHASE_SOURCE("DISABLED"),
        .OUTDIVIDER_MUXA("DIVA"),
        .OUTDIVIDER_MUXB("DIVB"),
        .OUTDIVIDER_MUXC("DIVC"),
        .OUTDIVIDER_MUXD("DIVD"),
        .CLKI_DIV(1),
        .CLKOP_ENABLE("ENABLED"),
        .CLKOP_DIV(5),
        .CLKOP_CPHASE(2),
        .CLKOP_FPHASE(0),
        .CLKOS_ENABLE("ENABLED"),
        .CLKOS_DIV(25),
        .CLKOS_CPHASE(2),
        .CLKOS_FPHASE(0),
        .FEEDBK_PATH("CLKOP"),
        .CLKFB_DIV(5)
    ) pll_i (
        .RST(1'b0),
        .STDBY(1'b0),
        .CLKI(clkin),
        .CLKOP(clkout0),
        .CLKOS(clkout1),
        .CLKFB(clkout0),
        .CLKINTFB(),
        .PHASESEL0(1'b0),
        .PHASESEL1(1'b0),
        .PHASEDIR(1'b1),
        .PHASESTEP(1'b1),
        .PHASELOADREG(1'b1),
        .PLLWAKESYNC(1'b0),
        .ENCLKOP(1'b0),
        .LOCK(locked)
	);
endmodule
