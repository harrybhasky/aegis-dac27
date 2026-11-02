// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// pulp-platform/common_cells e73baaec + tech_cells_generic v0.2.14 (tc_sync). Copyright ETH Zurich and University of Bologna.
// Licensed under the Solderpad Hardware License v0.51 (see LICENSE, http://solderpad.org/licenses/SHL-0.51).
// Top: cc_cdc_fifo_2phase_w8 (Aegis shim that fixes the widths, see shims/).
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
module cc_cdc_2phase_src_A050B_17156 (
	rst_ni,
	clk_i,
	data_i,
	valid_i,
	ready_o,
	async_req_o,
	async_ack_i,
	async_data_o
);
	parameter [31:0] data_t_PtrWidth = 0;
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	input wire [data_t_PtrWidth - 1:0] data_i;
	input wire valid_i;
	output wire ready_o;
	output wire async_req_o;
	input wire async_ack_i;
	output wire [data_t_PtrWidth - 1:0] async_data_o;
	(* dont_touch = "true" *) reg req_src_q;
	(* dont_touch = "true" *) wire ack_synced;
	(* dont_touch = "true" *) reg [data_t_PtrWidth - 1:0] data_src_q;
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
	function automatic [data_t_PtrWidth - 1:0] sv2v_cast_C253D;
		input reg [data_t_PtrWidth - 1:0] inp;
		sv2v_cast_C253D = inp;
	endfunction
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			data_src_q <= sv2v_cast_C253D(1'sb0);
		else if (src_accept)
			data_src_q <= data_i;
	assign ready_o = req_src_q == ack_synced;
	assign async_req_o = req_src_q;
	assign async_data_o = data_src_q;
endmodule
module cc_cdc_2phase_dst_7C168_C7BBC (
	rst_ni,
	clk_i,
	data_o,
	valid_o,
	ready_i,
	async_req_i,
	async_ack_o,
	async_data_i
);
	parameter [31:0] data_t_PtrWidth = 0;
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	output wire [data_t_PtrWidth - 1:0] data_o;
	output wire valid_o;
	input wire ready_i;
	input wire async_req_i;
	output wire async_ack_o;
	input wire [data_t_PtrWidth - 1:0] async_data_i;
	(* dont_touch = "true" *) wire req_synced;
	(* dont_touch = "true" *) reg req_synced_q1;
	(* dont_touch = "true" *) reg ack_dst_q;
	(* dont_touch = "true" *) reg [data_t_PtrWidth - 1:0] data_dst_q;
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
	function automatic [data_t_PtrWidth - 1:0] sv2v_cast_C253D;
		input reg [data_t_PtrWidth - 1:0] inp;
		sv2v_cast_C253D = inp;
	endfunction
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			data_dst_q <= sv2v_cast_C253D(1'sb0);
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
module cc_cdc_fifo_2phase_B407B (
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
	parameter [31:0] LogDepth = 3;
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
	localparam [31:0] PtrWidth = LogDepth + 1;
	wire [((2 ** LogDepth) * 8) - 1:0] async_data;
	wire async_wptr_req;
	wire async_wptr_ack;
	wire [PtrWidth - 1:0] async_wptr_data;
	wire async_rptr_req;
	wire async_rptr_ack;
	wire [PtrWidth - 1:0] async_rptr_data;
	cc_cdc_fifo_2phase_src_A0E38 #(
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_src(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_data_i(src_data_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.async_data_o(async_data),
		.async_wptr_req_o(async_wptr_req),
		.async_wptr_ack_i(async_wptr_ack),
		.async_wptr_data_o(async_wptr_data),
		.async_rptr_req_i(async_rptr_req),
		.async_rptr_ack_o(async_rptr_ack),
		.async_rptr_data_i(async_rptr_data)
	);
	cc_cdc_fifo_2phase_dst_A48EA #(
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_dst(
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i),
		.async_data_i(async_data),
		.async_wptr_req_i(async_wptr_req),
		.async_wptr_ack_o(async_wptr_ack),
		.async_wptr_data_i(async_wptr_data),
		.async_rptr_req_o(async_rptr_req),
		.async_rptr_ack_i(async_rptr_ack),
		.async_rptr_data_o(async_rptr_data)
	);
endmodule
module cc_cdc_fifo_2phase_src_A0E38 (
	src_rst_ni,
	src_clk_i,
	src_data_i,
	src_valid_i,
	src_ready_o,
	async_data_o,
	async_wptr_req_o,
	async_wptr_ack_i,
	async_wptr_data_o,
	async_rptr_req_i,
	async_rptr_ack_o,
	async_rptr_data_i
);
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	output wire [((2 ** LogDepth) * 8) - 1:0] async_data_o;
	output wire async_wptr_req_o;
	input wire async_wptr_ack_i;
	output wire [LogDepth:0] async_wptr_data_o;
	input wire async_rptr_req_i;
	output wire async_rptr_ack_o;
	input wire [LogDepth:0] async_rptr_data_i;
	localparam [31:0] PtrWidth = LogDepth + 1;
	localparam [PtrWidth - 1:0] PtrFull = 1 << LogDepth;
	wire [LogDepth - 1:0] fifo_widx;
	wire fifo_write;
	reg [((2 ** LogDepth) * 8) - 1:0] fifo_data_q;
	reg [PtrWidth - 1:0] src_wptr_q;
	wire [PtrWidth - 1:0] src_rptr;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_fifo_2phase.sv:167:5 - cc_cdc_fifo_2phase_src.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	assign fifo_widx = src_wptr_q[LogDepth - 1:0];
	assign fifo_write = src_valid_i && src_ready_o;
	assign async_data_o = fifo_data_q;
	genvar _gv_i_4;
	generate
		for (_gv_i_4 = 0; _gv_i_4 < (2 ** LogDepth); _gv_i_4 = _gv_i_4 + 1) begin : gen_word
			localparam i = _gv_i_4;
			always @(posedge src_clk_i or negedge src_rst_ni)
				if (!src_rst_ni)
					fifo_data_q[i * 8+:8] <= 8'b00000000;
				else if (fifo_write && (fifo_widx == i))
					fifo_data_q[i * 8+:8] <= src_data_i;
		end
	endgenerate
	always @(posedge src_clk_i or negedge src_rst_ni)
		if (!src_rst_ni)
			src_wptr_q <= 1'sb0;
		else if (fifo_write)
			src_wptr_q <= src_wptr_q + 1;
	assign src_ready_o = (src_wptr_q ^ src_rptr) != PtrFull;
	cc_cdc_2phase_src_A050B_17156 #(
		.data_t_PtrWidth(PtrWidth),
		.SyncStages(SyncStages)
	) i_cdc_wptr_src(
		.rst_ni(src_rst_ni),
		.clk_i(src_clk_i),
		.data_i(src_wptr_q),
		.valid_i(1'b1),
		.ready_o(),
		.async_req_o(async_wptr_req_o),
		.async_ack_i(async_wptr_ack_i),
		.async_data_o(async_wptr_data_o)
	);
	cc_cdc_2phase_dst_7C168_C7BBC #(
		.data_t_PtrWidth(PtrWidth),
		.SyncStages(SyncStages)
	) i_cdc_rptr_dst(
		.rst_ni(src_rst_ni),
		.clk_i(src_clk_i),
		.data_o(src_rptr),
		.valid_o(),
		.ready_i(1'b1),
		.async_req_i(async_rptr_req_i),
		.async_ack_o(async_rptr_ack_o),
		.async_data_i(async_rptr_data_i)
	);
endmodule
module cc_cdc_fifo_2phase_dst_A48EA (
	dst_rst_ni,
	dst_clk_i,
	dst_data_o,
	dst_valid_o,
	dst_ready_i,
	async_data_i,
	async_wptr_req_i,
	async_wptr_ack_o,
	async_wptr_data_i,
	async_rptr_req_o,
	async_rptr_ack_i,
	async_rptr_data_o
);
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	input wire [((2 ** LogDepth) * 8) - 1:0] async_data_i;
	input wire async_wptr_req_i;
	output wire async_wptr_ack_o;
	input wire [LogDepth:0] async_wptr_data_i;
	output wire async_rptr_req_o;
	input wire async_rptr_ack_i;
	output wire [LogDepth:0] async_rptr_data_o;
	localparam [31:0] PtrWidth = LogDepth + 1;
	localparam [PtrWidth - 1:0] PtrEmpty = 1'sb0;
	wire [LogDepth - 1:0] fifo_ridx;
	wire [7:0] fifo_rdata;
	wire [PtrWidth - 1:0] dst_wptr;
	reg [PtrWidth - 1:0] dst_rptr_q;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_fifo_2phase.sv:263:5 - cc_cdc_fifo_2phase_dst.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	assign fifo_ridx = dst_rptr_q[LogDepth - 1:0];
	assign fifo_rdata = async_data_i[fifo_ridx * 8+:8];
	assign dst_data_o = fifo_rdata;
	always @(posedge dst_clk_i or negedge dst_rst_ni)
		if (!dst_rst_ni)
			dst_rptr_q <= 1'sb0;
		else if (dst_valid_o && dst_ready_i)
			dst_rptr_q <= dst_rptr_q + 1;
	assign dst_valid_o = (dst_rptr_q ^ dst_wptr) != PtrEmpty;
	cc_cdc_2phase_dst_7C168_C7BBC #(
		.data_t_PtrWidth(PtrWidth),
		.SyncStages(SyncStages)
	) i_cdc_wptr_dst(
		.rst_ni(dst_rst_ni),
		.clk_i(dst_clk_i),
		.data_o(dst_wptr),
		.valid_o(),
		.ready_i(1'b1),
		.async_req_i(async_wptr_req_i),
		.async_ack_o(async_wptr_ack_o),
		.async_data_i(async_wptr_data_i)
	);
	cc_cdc_2phase_src_A050B_17156 #(
		.data_t_PtrWidth(PtrWidth),
		.SyncStages(SyncStages)
	) i_cdc_rptr_src(
		.rst_ni(dst_rst_ni),
		.clk_i(dst_clk_i),
		.data_i(dst_rptr_q),
		.valid_i(1'b1),
		.ready_o(),
		.async_req_o(async_rptr_req_o),
		.async_ack_i(async_rptr_ack_i),
		.async_data_o(async_rptr_data_o)
	);
endmodule
module cc_cdc_fifo_2phase_w8 (
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
	cc_cdc_fifo_2phase_B407B #(
		.LogDepth(3),
		.SyncStages(2)
	) i_cdc(
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
