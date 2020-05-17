module top
(
	input wire btn,
	inout [3:0] gpdi_in,
	inout [3:0] gpdi_out,
	inout [3:0] gpdi_out_secondary,
);

// gpdi_out[1] is inverted
// gpdi_out[2] is inverted
// gpdi_out[3] is inverted
// gpdi_in[0] is inverted
// gpdi_in[3] is inverted
assign gpdi_out[2:0] = {~gpdi_in[2], ~gpdi_in[1], ~gpdi_in[0]};
// assign gpdi_out[2:0] = {~gpdi_in[2], btn ^ gpdi_in[1], gpdi_in[0]};
// assign gpdi_out[2:0] = {~gpdi_in[2], blink[25] ^ gpdi_in[1], gpdi_in[0]};
assign gpdi_out_secondary[2:0] = {gpdi_in[2], gpdi_in[1], ~gpdi_in[0]};

OLVDS OLVDS_clock1 (.A(clk_recovery), .Z(gpdi_out[3]));
OLVDS OLVDS_clock2 (.A(clk_recovery), .Z(gpdi_out_secondary[3]));

// // clock generator
wire clk_data;
wire clk_recovery;
clk_75_75
clock_instance
(
	.clkin(~gpdi_in[3]),
	.clkout0(clk_recovery)
);

reg [26:0] blink;
always @(posedge clk_recovery)
  blink <= blink+1;

endmodule



module clk_75_75
(
    input clkin, // 75 MHz, 0 deg
    output clkout0, // 75 MHz, 0 deg
    output locked
);
(* FREQUENCY_PIN_CLKI="75" *)
(* FREQUENCY_PIN_CLKOP="75" *)
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
        .CLKOP_DIV(8),
        .CLKOP_CPHASE(4),
        .CLKOP_FPHASE(0),
        .FEEDBK_PATH("CLKOP"),
        .CLKFB_DIV(1)
    ) pll_i (
        .RST(1'b0),
        .STDBY(1'b0),
        .CLKI(clkin),
        .CLKOP(clkout0),
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
