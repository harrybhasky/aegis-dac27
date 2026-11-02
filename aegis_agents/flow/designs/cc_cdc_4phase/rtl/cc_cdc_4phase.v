// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// pulp-platform/common_cells e73baaec + tech_cells_generic v0.2.14 (tc_sync). Copyright ETH Zurich and University of Bologna.
// Licensed under the Solderpad Hardware License v0.51 (see LICENSE, http://solderpad.org/licenses/SHL-0.51).
// Top: cc_cdc_4phase_w8 (Aegis shim that fixes the widths, see shims/).
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
module cc_spill_register_flushable_FA928 (
	clk_i,
	rst_ni,
	clr_i,
	valid_i,
	flush_i,
	ready_o,
	data_i,
	valid_o,
	ready_i,
	data_o
);
	parameter [0:0] Bypass = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire clr_i;
	input wire valid_i;
	input wire flush_i;
	output wire ready_o;
	input wire [7:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [7:0] data_o;
	generate
		if (Bypass) begin : gen_bypass
			assign valid_o = valid_i;
			assign ready_o = ready_i;
			assign data_o = data_i;
		end
		else begin : gen_spill_reg
			reg [7:0] a_data_q;
			reg a_full_q;
			wire a_fill;
			wire a_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_data_q <= 8'b00000000;
				else if (clr_i)
					a_data_q <= 8'b00000000;
				else if (a_fill)
					a_data_q <= data_i;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_full_q <= 1'sb0;
				else if (clr_i)
					a_full_q <= 1'sb0;
				else if (a_fill || a_drain)
					a_full_q <= a_fill;
			reg [7:0] b_data_q;
			reg b_full_q;
			wire b_fill;
			wire b_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					b_data_q <= 8'b00000000;
				else if (clr_i)
					b_data_q <= 8'b00000000;
				else if (b_fill)
					b_data_q <= a_data_q;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					b_full_q <= 1'sb0;
				else if (clr_i)
					b_full_q <= 1'sb0;
				else if (b_fill || b_drain)
					b_full_q <= b_fill;
			assign a_fill = (valid_i && ready_o) && !flush_i;
			assign a_drain = (a_full_q && !b_full_q) || flush_i;
			assign b_fill = (a_drain && !ready_i) && !flush_i;
			assign b_drain = (b_full_q && ready_i) || flush_i;
			assign ready_o = !a_full_q || !b_full_q;
			assign valid_o = a_full_q | b_full_q;
			assign data_o = (b_full_q ? b_data_q : a_data_q);
		end
	endgenerate
endmodule
module cc_spill_register_ECE79 (
	clk_i,
	rst_ni,
	clr_i,
	valid_i,
	ready_o,
	data_i,
	valid_o,
	ready_i,
	data_o
);
	parameter [0:0] Bypass = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire clr_i;
	input wire valid_i;
	output wire ready_o;
	input wire [7:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [7:0] data_o;
	cc_spill_register_flushable_FA928 #(.Bypass(Bypass)) spill_register_flushable_i(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.clr_i(clr_i),
		.valid_i(valid_i),
		.flush_i(1'b0),
		.ready_o(ready_o),
		.data_i(data_i),
		.valid_o(valid_o),
		.ready_i(ready_i),
		.data_o(data_o)
	);
endmodule
module cc_cdc_4phase_9E8E5 (
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
	parameter [0:0] Decoupled = 1'b1;
	parameter [0:0] SendResetMsg = 1'b0;
	parameter [7:0] ResetMsg = 8'b00000000;
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
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_4phase.sv:65:5 - cc_cdc_4phase.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	cc_cdc_4phase_src_FC1FE #(
		.SyncStages(SyncStages),
		.Decoupled(Decoupled),
		.SendResetMsg(SendResetMsg),
		.ResetMsg(ResetMsg)
	) i_src(
		.rst_ni(src_rst_ni),
		.clk_i(src_clk_i),
		.data_i(src_data_i),
		.valid_i(src_valid_i),
		.ready_o(src_ready_o),
		.async_req_o(async_req),
		.async_ack_i(async_ack),
		.async_data_o(async_data)
	);
	cc_cdc_4phase_dst_D7794 #(
		.SyncStages(SyncStages),
		.Decoupled(Decoupled)
	) i_dst(
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
module cc_cdc_4phase_src_FC1FE (
	rst_ni,
	clk_i,
	data_i,
	valid_i,
	ready_o,
	async_req_o,
	async_ack_i,
	async_data_o
);
	reg _sv2v_0;
	parameter [31:0] SyncStages = 2;
	parameter [0:0] Decoupled = 1'b1;
	parameter [0:0] SendResetMsg = 1'b0;
	parameter [7:0] ResetMsg = 8'b00000000;
	input wire rst_ni;
	input wire clk_i;
	input wire [7:0] data_i;
	input wire valid_i;
	output reg ready_o;
	output wire async_req_o;
	input wire async_ack_i;
	output wire [7:0] async_data_o;
	(* dont_touch = "true" *) reg req_src_d;
	(* dont_touch = "true" *) reg req_src_q;
	(* dont_touch = "true" *) reg [7:0] data_src_d;
	(* dont_touch = "true" *) reg [7:0] data_src_q;
	(* dont_touch = "true" *) wire ack_synced;
	reg [1:0] state_d;
	reg [1:0] state_q;
	localparam [0:0] ReqSrcResetValue = (SendResetMsg ? 1'b1 : 1'b0);
	localparam [7:0] DataSrcResetValue = (SendResetMsg ? ResetMsg : 8'b00000000);
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_4phase.sv:135:5 - cc_cdc_4phase_src.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_ack_i),
		.serial_o(ack_synced)
	);
	always @(*) begin
		if (_sv2v_0)
			;
		ready_o = 1'b0;
		case (state_q)
			2'd0: ready_o = Decoupled;
			2'd2: ready_o = !Decoupled && (ack_synced == 1'b0);
			default: ready_o = 1'b0;
		endcase
	end
	always @(*) begin
		if (_sv2v_0)
			;
		state_d = state_q;
		req_src_d = 1'b0;
		data_src_d = data_src_q;
		case (state_q)
			2'd0:
				if (valid_i) begin
					data_src_d = data_i;
					req_src_d = 1'b1;
					state_d = 2'd1;
				end
			2'd1: begin
				req_src_d = 1'b1;
				if (ack_synced == 1'b1) begin
					req_src_d = 1'b0;
					state_d = 2'd2;
				end
			end
			2'd2:
				if (ack_synced == 1'b0)
					state_d = 2'd0;
			default: state_d = 2'd0;
		endcase
	end
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			state_q <= 2'd0;
		else
			state_q <= state_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			req_src_q <= ReqSrcResetValue;
		else
			req_src_q <= req_src_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			data_src_q <= DataSrcResetValue;
		else
			data_src_q <= data_src_d;
	assign async_req_o = req_src_q;
	assign async_data_o = data_src_q;
	initial _sv2v_0 = 0;
endmodule
module cc_cdc_4phase_dst_D7794 (
	rst_ni,
	clk_i,
	data_o,
	valid_o,
	ready_i,
	async_req_i,
	async_ack_o,
	async_data_i
);
	reg _sv2v_0;
	parameter [31:0] SyncStages = 2;
	parameter [0:0] Decoupled = 1'b1;
	input wire rst_ni;
	input wire clk_i;
	output wire [7:0] data_o;
	output wire valid_o;
	input wire ready_i;
	input wire async_req_i;
	output wire async_ack_o;
	input wire [7:0] async_data_i;
	(* dont_touch = "true" *) reg ack_dst_d;
	(* dont_touch = "true" *) reg ack_dst_q;
	(* dont_touch = "true" *) wire req_synced;
	reg data_valid;
	wire output_ready;
	reg [1:0] state_d;
	reg [1:0] state_q;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_4phase.sv:240:5 - cc_cdc_4phase_dst.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_req_i),
		.serial_o(req_synced)
	);
	always @(*) begin
		if (_sv2v_0)
			;
		data_valid = 1'b0;
		case (state_q)
			2'd0: data_valid = req_synced;
			2'd1: data_valid = 1'b1;
			default: data_valid = 1'b0;
		endcase
	end
	always @(*) begin
		if (_sv2v_0)
			;
		state_d = state_q;
		ack_dst_d = 1'b0;
		case (state_q)
			2'd0:
				if (req_synced == 1'b1) begin
					if (output_ready == 1'b1)
						state_d = 2'd2;
					else
						state_d = 2'd1;
				end
			2'd1:
				if (output_ready == 1'b1) begin
					state_d = 2'd2;
					ack_dst_d = 1'b1;
				end
			2'd2: begin
				ack_dst_d = 1'b1;
				if (req_synced == 1'b0) begin
					ack_dst_d = 1'b0;
					state_d = 2'd0;
				end
			end
			default: state_d = 2'd0;
		endcase
	end
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			state_q <= 2'd0;
		else
			state_q <= state_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			ack_dst_q <= 1'b0;
		else
			ack_dst_q <= ack_dst_d;
	generate
		if (Decoupled) begin : gen_decoupled
			localparam [0:0] sv2v_uu_i_spill_register_ext_clr_i_0 = 1'sb0;
			cc_spill_register_ECE79 #(.Bypass(1'b0)) i_spill_register(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.clr_i(sv2v_uu_i_spill_register_ext_clr_i_0),
				.valid_i(data_valid),
				.ready_o(output_ready),
				.data_i(async_data_i),
				.valid_o(valid_o),
				.ready_i(ready_i),
				.data_o(data_o)
			);
		end
		else begin : gen_not_decoupled
			assign valid_o = data_valid;
			assign output_ready = ready_i;
			assign data_o = async_data_i;
		end
	endgenerate
	assign async_ack_o = ack_dst_q;
	initial _sv2v_0 = 0;
endmodule
module cc_cdc_4phase_w8 (
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
	cc_cdc_4phase_9E8E5 #(
		.Decoupled(1'b1),
		.SendResetMsg(1'b0),
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
