module top
(
	input wire btn,
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
// assign gpdi_out[2:0] = {~gpdi_in[2], ~gpdi_in[1], ~gpdi_in[0]};
// assign gpdi_out[2:0] = {~gpdi_in[2], btn ^ gpdi_in[1], gpdi_in[0]};
// assign gpdi_out[2:0] = {~gpdi_in[2], blink[25] ^ gpdi_in[1], gpdi_in[0]};
// assign gpdi_out_secondary[2:0] = {gpdi_in[2], gpdi_in[1], ~gpdi_in[0]};

wire [3:0] gpdi_in_fixed =  {~gpdi_in[3], gpdi_in[2], gpdi_in[1], ~gpdi_in[0]};
wire [2:0] gpdi_out_fixed;
assign gpdi_out[2:0] = {~gpdi_out_fixed[2], ~gpdi_out_fixed[1], ~gpdi_out_fixed[0]};


OLVDS OLVDS_clock1 (.A(clk_25MHz), .Z(gpdi_out[3]));
OLVDS OLVDS_clock2 (.A(clk_25MHz), .Z(gpdi_out_secondary[3]));

// // clock generator
wire locked;
wire clk_250MHz;
wire clk_25MHz;
clk_25_250_25
// clk_25_125_25
clock_instance
(
  .locked(locked),
	.clkin(gpdi_in_fixed[3]),
	.clkout0(clk_250MHz),
	.clkout1(clk_25MHz)
);

// reg [26:0] blink;
// always @(posedge clk_250MHz)
//   blink <= blink+1;
// assign led = locked ? blink[25:25-7] : 0;


reg [9:0] shift_r,   shift_r_r = 0;
reg [9:0] shift_g,   shift_g_r = 0;
reg [9:0] shift_b,   shift_b_r = 0;
reg [9:0] shift_clk, shift_clk_r = 0;
always @(posedge clk_250MHz) begin
  shift_r   <= {shift_r[8:0],   gpdi_in_fixed[2]};
  shift_g   <= {shift_g[8:0],   gpdi_in_fixed[1]};
  shift_b   <= {shift_b[8:0],   gpdi_in_fixed[0]};
  shift_clk <= {shift_clk[8:0], clk_25MHz};
  if ((shift_clk[1] == 0) & (shift_clk[0] == 1)) begin
    // clk_25MHz rises
    shift_b_r <= shift_b;
  end
end

assign gpdi_out_fixed = {shift_r[0], shift_g[0], ~shift_b[0]};
assign gpdi_out_secondary[2:0] = {shift_r[0], shift_g[0], shift_b[0]};

// assign led = shift_b_r[7:0];


endmodule

module clk_25_250_25
(
    input clkin, // 25 MHz, 0 deg
    output clkout0, // 250 MHz, 0 deg
    output clkout1, // 25 MHz, 0 deg
    output locked
);
(* FREQUENCY_PIN_CLKI="25" *)
(* FREQUENCY_PIN_CLKOP="250" *)
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
        .CLKOP_DIV(2),
        .CLKOP_CPHASE(0),
        .CLKOP_FPHASE(0),
        .CLKOS_ENABLE("ENABLED"),
        .CLKOS_DIV(20),
        .CLKOS_CPHASE(0),
        .CLKOS_FPHASE(10),
        .FEEDBK_PATH("CLKOP"),
        .CLKFB_DIV(10)
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
