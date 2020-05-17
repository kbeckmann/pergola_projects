`default_nettype none

module top(
	input wire clk_16mhz,
	input wire btn,
	output wire[7:0] led
);

	reg [25:0] counter = 0;
	
	/* This clock is _always_ ticking */
	always @(posedge clk_16mhz) begin
		counter    <= counter + 1;
		led        <= btn ? counter[25:25-7] : 8'hFF;
	end

endmodule
