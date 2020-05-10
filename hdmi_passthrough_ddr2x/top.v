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
wire clk_shift;
wire clk_shift_half;
wire clk_pixel;
clk_75_375_187m5_75
clock_instance
(
  .locked(locked),
	.clkin(gpdi_in[3]),
	.clkout0(clk_shift),
	.clkout1(clk_shift_half),
	.clkout2(clk_pixel)
);

reg rst = 0;
reg [3:0] q_r;
reg [3:0] q_g;
reg [3:0] q_b;
reg [3:0] q_clk;

reg [3:0] d_r;
reg [3:0] d_g;
reg [3:0] d_b;
reg [3:0] d_clk;


// Input DDR2x
parameter d_delay = 0;
wire [2:0] gpdi_in_z;

DELAYF #(
  .DEL_VALUE(d_delay),
)
delay_in2(
  .A(gpdi_in[2]),
  .LOADN(1),
  .MOVE(0),
  .DIRECTION(0),
  .Z(gpdi_in_z[2])
);

IDDRX2F iddr2x_r(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D(gpdi_in_z[2]),
  .RST(rst),
  .Q0(q_r[0]),
  .Q1(q_r[1]),
  .Q2(q_r[2]),
  .Q3(q_r[3]),
);

DELAYF #(
  .DEL_VALUE(d_delay),
)
delay_in1(
  .A(gpdi_in[1]),
  .LOADN(1),
  .MOVE(0),
  .DIRECTION(0),
  .Z(gpdi_in_z[1])
);
IDDRX2F iddr2x_g(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D(gpdi_in_z[1]),
  .RST(rst),
  .Q0(q_g[0]),
  .Q1(q_g[1]),
  .Q2(q_g[2]),
  .Q3(q_g[3]),
);

DELAYF #(
  .DEL_VALUE(d_delay),
)
delay_in0(
  .A(gpdi_in[0]),
  .LOADN(1),
  .MOVE(0),
  .DIRECTION(0),
  .Z(gpdi_in_z[0])
);
IDDRX2F iddr2x_b(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D(gpdi_in_z[0]),
  .RST(rst),
  .Q0(q_b[0]),
  .Q1(q_b[1]),
  .Q2(q_b[2]),
  .Q3(q_b[3]),
);

// Output DDR2x to primary
ODDRX2F oddr2x_r(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(~shift_r[0]),
  .D1(~shift_r[1]),
  .D2(~shift_r[2]),
  .D3(~shift_r[3]),
  .RST(rst),
  .Q(gpdi_out[2]),
);

ODDRX2F oddr2x_g(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(~shift_g[0]),
  .D1(~shift_g[1]),
  .D2(~shift_g[2]),
  .D3(~shift_g[3]),
  .RST(rst),
  .Q(gpdi_out[1]),
);

ODDRX2F oddr2x_b(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_b[0]),
  .D1(shift_b[1]),
  .D2(shift_b[2]),
  .D3(shift_b[3]),
  .RST(rst),
  .Q(gpdi_out[0]),
);

ODDRX2F oddr2x_clk(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_clk[0]),
  .D1(shift_clk[1]),
  .D2(shift_clk[2]),
  .D3(shift_clk[3]),
  .RST(rst),
  .Q(gpdi_out[3]),
);

// Output DDR2x to secondary
ODDRX2F oddr2x_r_second(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_r_second[0]),
  .D1(shift_r_second[1]),
  .D2(shift_r_second[2]),
  .D3(shift_r_second[3]),
  .RST(rst),
  .Q(gpdi_out_secondary[2]),
);

ODDRX2F oddr2x_g_second(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_g_second[0]),
  .D1(shift_g_second[1]),
  .D2(shift_g_second[2]),
  .D3(shift_g_second[3]),
  .RST(rst),
  .Q(gpdi_out_secondary[1]),
);

ODDRX2F oddr2x_b_second(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_b_second[0]),
  .D1(shift_b_second[1]),
  .D2(shift_b_second[2]),
  .D3(shift_b_second[3]),
  .RST(rst),
  .Q(gpdi_out_secondary[0]),
);

ODDRX2F oddr2x_clk_second(
  .SCLK(clk_shift_half),
  .ECLK(clk_shift),
  .D0(shift_clk_second[0]),
  .D1(shift_clk_second[1]),
  .D2(shift_clk_second[2]),
  .D3(shift_clk_second[3]),
  .RST(rst),
  .Q(gpdi_out_secondary[3]),
);



reg [9:0] shift_r,   shift_r_second = 0;
reg [9:0] shift_g,   shift_g_second = 0;
reg [9:0] shift_b,   shift_b_second = 0;
reg [9:0] shift_clk, shift_clk_second = 0;
always @(posedge clk_shift_half) begin
  shift_r   <= {shift_r[5:0],   q_r};
  shift_g   <= {shift_g[5:0],   q_g};
  shift_b   <= {shift_b[5:0],   ~q_b};

  shift_r_second <= shift_r;
  shift_g_second <= shift_g;
  shift_b_second <= shift_b;
  shift_clk_second <= shift_clk;

  // This isn't really correct...
  shift_clk <= {shift_clk[5:0], clk_pixel, clk_pixel, clk_pixel, clk_pixel};
end


endmodule



module clk_75_375_187m5_75
(
    input clkin, // 75 MHz, 0 deg
    output clkout0, // 375 MHz, 0 deg
    output clkout1, // 187.5 MHz, 0 deg
    output clkout2, // 75 MHz, 0 deg
    output locked
);
(* FREQUENCY_PIN_CLKI="75" *)
(* FREQUENCY_PIN_CLKOP="375" *)
(* FREQUENCY_PIN_CLKOS="187.5" *)
(* FREQUENCY_PIN_CLKOS2="75" *)
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
        .CLKOP_DIV(2),
        .CLKOP_CPHASE(0),
        .CLKOP_FPHASE(0),
        .CLKOS_ENABLE("ENABLED"),
        .CLKOS_DIV(4),
        .CLKOS_CPHASE(0),
        .CLKOS_FPHASE(0),
        .CLKOS2_ENABLE("ENABLED"),
        .CLKOS2_DIV(10),
        .CLKOS2_CPHASE(0),
        .CLKOS2_FPHASE(0),
        .FEEDBK_PATH("CLKOP"),
        .CLKFB_DIV(5)
    ) pll_i (
        .RST(1'b0),
        .STDBY(1'b0),
        .CLKI(clkin),
        .CLKOP(clkout0),
        .CLKOS(clkout1),
        .CLKOS2(clkout2),
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
