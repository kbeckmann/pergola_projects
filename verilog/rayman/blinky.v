//`default_nettype none

module control(
	input [5:0] instruction,
	output wire regdst,
	output wire jal,
	output wire jmp,
	output wire branch,
	output wire bne,
	output wire memread,
	output wire memtoreg,
	output wire [2:0] aluop,
	output wire memwrite,
	output wire alusrc,
	output wire regwrite,
);

wire [13:0] out;
assign {regdst, jal, jmp, branch, bne, memread, memtoreg, aluop, memwrite, alusrc, regwrite} = out;

always @(*) begin
	case (instruction)
		6'b000100 : begin out = 13'b00010000010000; end
		6'b000101 : begin out = 13'b00011000010000; end
		6'b000011 : begin out = 13'b01100000000010; end
		6'b000010 : begin out = 13'b00100000000000; end
		6'b001000 : begin out = 13'b00000000000110; end
		6'b001010 : begin out = 13'b00000001110110; end
		6'b001100 : begin out = 13'b00000001000110; end
		6'b001101 : begin out = 13'b00000001010110; end
		6'b100011 : begin out = 13'b00000110000110; end
		6'b101011 : begin out = 13'b00000000001100; end
		6'b111111 : begin out = 13'b00000000000001; end
		6'b000000 : begin out = 13'b10000000100010; end
		default   : begin out = 13'b11111111111111; end
	endcase
end

endmodule



module top(
	input wire clk_16mhz,
	input wire btn,
	output wire[7:0] led
);

wire regdst, jal, jmp, branch, bne, memread, memtoreg, memwrite, alusrc, regwrite;
wire [2:0] aluop;
reg [5:0] instruction;

always @(posedge clk_16mhz) begin
	instruction <= {instruction, btn};
end

control
mycontrol(instruction, regdst, jal, jmp, branch, bne, memread, memtoreg, aluop, memwrite, alusrc, regwrite);

wire [13:0]out;
reg  [13:0]out_r;
assign out = {regdst, jal, jmp, branch, bne, memread, memtoreg, aluop, memwrite, alusrc, regwrite};
assign led = out_r[0];

reg [4:0] counter;
always @(posedge clk_16mhz) begin
	counter <= counter + 1;
	if (counter == 13) begin
		out_r <= out;
		counter <= 0;
	end else begin
		out_r <= {0, out_r[13:1]};
	end
end



endmodule
