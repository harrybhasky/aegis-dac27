// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// pulp-platform/common_cells e73baaec + tech_cells_generic v0.2.14 (tc_sync). Copyright ETH Zurich and University of Bologna.
// Licensed under the Solderpad Hardware License v0.51 (see LICENSE, http://solderpad.org/licenses/SHL-0.51).
// Top: cc_cdc_2phase_w8 (Aegis shim that fixes the widths, see shims/).
module tc_sync (
	clk_i,
	rst_ni,
	serial_i,
	serial_o
);
	parameter [31:0] Stages = 2;
	parameter [0:0] ResetValue = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire serial_i;
	output wire serial_o;
	(* dont_touch = "true" *) (* async_reg = "true" *) reg [Stages - 1:0] reg_q;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			reg_q <= {Stages {ResetValue}};
		else
			reg_q <= {reg_q[Stages - 2:0], serial_i};
	assign serial_o = reg_q[Stages - 1];
endmodule
module cc_cdc_2phase_4722D (
	src_rst_ni,
	src_clk_i,
	src_data_i,
	src_valid_i,
	src_ready_o,
	dst_rst_ni,
	dst_clk_i,
	dst_data_o,
	dst_valid_o,
	dst_ready_i
);
	parameter [31:0] SyncStages = 2;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	(* dont_touch = "true" *) wire async_req;
	(* dont_touch = "true" *) wire async_ack;
	(* dont_touch = "true" *) wire [7:0] async_data;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase.sv:67:5 - cc_cdc_2phase.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	cc_cdc_2phase_src_F82F4 #(.SyncStages(SyncStages)) i_src(
		.rst_ni(src_rst_ni),
		.clk_i(src_clk_i),
		.data_i(src_data_i),
		.valid_i(src_valid_i),
		.ready_o(src_ready_o),
		.async_req_o(async_req),
		.async_ack_i(async_ack),
		.async_data_o(async_data)
	);
	cc_cdc_2phase_dst_64F12 #(.SyncStages(SyncStages)) i_dst(
		.rst_ni(dst_rst_ni),
		.clk_i(dst_clk_i),
		.data_o(dst_data_o),
		.valid_o(dst_valid_o),
		.ready_i(dst_ready_i),
		.async_req_i(async_req),
		.async_ack_o(async_ack),
		.async_data_i(async_data)
	);
endmodule
module cc_cdc_2phase_src_F82F4 (
	rst_ni,
	clk_i,
	data_i,
	valid_i,
	ready_o,
	async_req_o,
	async_ack_i,
	async_data_o
);
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	input wire [7:0] data_i;
	input wire valid_i;
	output wire ready_o;
	output wire async_req_o;
	input wire async_ack_i;
	output wire [7:0] async_data_o;
	(* dont_touch = "true" *) reg req_src_q;
	(* dont_touch = "true" *) wire ack_synced;
	(* dont_touch = "true" *) reg [7:0] data_src_q;
	wire src_accept;
	assign src_accept = valid_i && ready_o;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase.sv:127:5 - cc_cdc_2phase_src.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_ack_i),
		.serial_o(ack_synced)
	);
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			req_src_q <= 1'b0;
		else if (src_accept)
			req_src_q <= ~req_src_q;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			data_src_q <= 8'b00000000;
		else if (src_accept)
			data_src_q <= data_i;
	assign ready_o = req_src_q == ack_synced;
	assign async_req_o = req_src_q;
	assign async_data_o = data_src_q;
endmodule
module cc_cdc_2phase_dst_64F12 (
	rst_ni,
	clk_i,
	data_o,
	valid_o,
	ready_i,
	async_req_i,
	async_ack_o,
	async_data_i
);
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	output wire [7:0] data_o;
	output wire valid_o;
	input wire ready_i;
	input wire async_req_i;
	output wire async_ack_o;
	input wire [7:0] async_data_i;
	(* dont_touch = "true" *) wire req_synced;
	(* dont_touch = "true" *) reg req_synced_q1;
	(* dont_touch = "true" *) reg ack_dst_q;
	(* dont_touch = "true" *) reg [7:0] data_dst_q;
	wire dst_accept;
	wire dst_data_load;
	assign dst_accept = valid_o && ready_i;
	assign dst_data_load = (req_synced != req_synced_q1) && !valid_o;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase.sv:178:5 - cc_cdc_2phase_dst.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_req_i),
		.serial_o(req_synced)
	);
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			ack_dst_q <= 1'b0;
		else if (dst_accept)
			ack_dst_q <= ~ack_dst_q;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			data_dst_q <= 8'b00000000;
		else if (dst_data_load)
			data_dst_q <= async_data_i;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			req_synced_q1 <= 1'b0;
		else
			req_synced_q1 <= req_synced;
	assign valid_o = ack_dst_q != req_synced_q1;
	assign data_o = data_dst_q;
	assign async_ack_o = ack_dst_q;
endmodule
module cc_cdc_2phase_w8 (
	src_rst_ni,
	src_clk_i,
	src_data_i,
	src_valid_i,
	src_ready_o,
	dst_rst_ni,
	dst_clk_i,
	dst_data_o,
	dst_valid_o,
	dst_ready_i
);
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	cc_cdc_2phase_4722D #(.SyncStages(2)) i_cdc(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_data_i(src_data_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i)
	);
endmodule
