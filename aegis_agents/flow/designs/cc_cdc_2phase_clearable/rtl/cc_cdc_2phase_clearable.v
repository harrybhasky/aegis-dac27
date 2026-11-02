// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// pulp-platform/common_cells e73baaec + tech_cells_generic v0.2.14 (tc_sync). Copyright ETH Zurich and University of Bologna.
// Licensed under the Solderpad Hardware License v0.51 (see LICENSE, http://solderpad.org/licenses/SHL-0.51).
// Top: cc_cdc_2phase_clearable_w8 (Aegis shim that fixes the widths, see shims/).
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
module cc_spill_register_flushable_2B505 (
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
	input wire [1:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [1:0] data_o;
	generate
		if (Bypass) begin : gen_bypass
			assign valid_o = valid_i;
			assign ready_o = ready_i;
			assign data_o = data_i;
		end
		else begin : gen_spill_reg
			reg [1:0] a_data_q;
			reg a_full_q;
			wire a_fill;
			wire a_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_data_q <= 2'b00;
				else if (clr_i)
					a_data_q <= 2'b00;
				else if (a_fill)
					a_data_q <= data_i;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_full_q <= 1'sb0;
				else if (clr_i)
					a_full_q <= 1'sb0;
				else if (a_fill || a_drain)
					a_full_q <= a_fill;
			reg [1:0] b_data_q;
			reg b_full_q;
			wire b_fill;
			wire b_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					b_data_q <= 2'b00;
				else if (clr_i)
					b_data_q <= 2'b00;
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
module cc_spill_register_5A952 (
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
	input wire [1:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [1:0] data_o;
	cc_spill_register_flushable_2B505 #(.Bypass(Bypass)) spill_register_flushable_i(
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
module cc_cdc_4phase_src_0A8DA (
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
	parameter [1:0] ResetMsg = 2'b00;
	input wire rst_ni;
	input wire clk_i;
	input wire [1:0] data_i;
	input wire valid_i;
	output reg ready_o;
	output wire async_req_o;
	input wire async_ack_i;
	output wire [1:0] async_data_o;
	(* dont_touch = "true" *) reg req_src_d;
	(* dont_touch = "true" *) reg req_src_q;
	(* dont_touch = "true" *) reg [1:0] data_src_d;
	(* dont_touch = "true" *) reg [1:0] data_src_q;
	(* dont_touch = "true" *) wire ack_synced;
	reg [1:0] state_d;
	reg [1:0] state_q;
	localparam [0:0] ReqSrcResetValue = (SendResetMsg ? 1'b1 : 1'b0);
	localparam [1:0] DataSrcResetValue = (SendResetMsg ? ResetMsg : 2'b00);
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
module cc_cdc_4phase_dst_AC62C (
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
	output wire [1:0] data_o;
	output wire valid_o;
	input wire ready_i;
	input wire async_req_i;
	output wire async_ack_o;
	input wire [1:0] async_data_i;
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
			cc_spill_register_5A952 #(.Bypass(1'b0)) i_spill_register(
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
module cc_cdc_reset_ctrlr_half (
	clk_i,
	rst_ni,
	clear_i,
	isolate_o,
	isolate_ack_i,
	clear_o,
	clear_ack_i,
	async_next_phase_o,
	async_req_o,
	async_ack_i,
	async_next_phase_i,
	async_req_i,
	async_ack_o
);
	reg _sv2v_0;
	parameter [31:0] SyncStages = 2;
	parameter [0:0] ClearOnAsyncReset = 1'b1;
	input wire clk_i;
	input wire rst_ni;
	input wire clear_i;
	output wire isolate_o;
	input wire isolate_ack_i;
	output wire clear_o;
	input wire clear_ack_i;
	output wire [1:0] async_next_phase_o;
	output wire async_req_o;
	input wire async_ack_i;
	input wire [1:0] async_next_phase_i;
	input wire async_req_i;
	output wire async_ack_o;
	reg [3:0] initiator_state_d;
	reg [3:0] initiator_state_q;
	localparam [3:0] InitiatorStateResetValue = (ClearOnAsyncReset ? 4'd1 : 4'd0);
	reg [1:0] initiator_clear_seq_phase;
	reg initiator_phase_transition_req;
	wire initiator_phase_transition_ack;
	reg initiator_isolate_out;
	reg initiator_clear_out;
	localparam [31:0] ResetSyncStages = (SyncStages > 2 ? SyncStages : 2);
	always @(*) begin
		if (_sv2v_0)
			;
		initiator_state_d = initiator_state_q;
		initiator_phase_transition_req = 1'b0;
		initiator_isolate_out = 1'b0;
		initiator_clear_out = 1'b0;
		initiator_clear_seq_phase = 2'd0;
		case (initiator_state_q)
			4'd0:
				if (clear_i)
					initiator_state_d = 4'd1;
			4'd1: begin
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd1;
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b0;
				if (initiator_phase_transition_ack && isolate_ack_i)
					initiator_state_d = 4'd4;
				else if (initiator_phase_transition_ack)
					initiator_state_d = 4'd3;
				else if (isolate_ack_i)
					initiator_state_d = 4'd2;
			end
			4'd3: begin
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b0;
				initiator_clear_seq_phase = 2'd1;
				if (isolate_ack_i)
					initiator_state_d = 4'd4;
			end
			4'd2: begin
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd1;
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b0;
				if (initiator_phase_transition_ack)
					initiator_state_d = 4'd4;
			end
			4'd4: begin
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b1;
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd2;
				if (initiator_phase_transition_ack && clear_ack_i)
					initiator_state_d = 4'd7;
				else if (initiator_phase_transition_ack)
					initiator_state_d = 4'd6;
				else if (clear_ack_i)
					initiator_state_d = 4'd5;
			end
			4'd6: begin
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b1;
				initiator_clear_seq_phase = 2'd2;
				if (clear_ack_i)
					initiator_state_d = 4'd7;
			end
			4'd5: begin
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd2;
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b1;
				if (initiator_phase_transition_ack)
					initiator_state_d = 4'd7;
			end
			4'd7: begin
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b0;
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd3;
				if (initiator_phase_transition_ack)
					initiator_state_d = 4'd8;
			end
			4'd8: begin
				initiator_isolate_out = 1'b1;
				initiator_clear_out = 1'b0;
				initiator_phase_transition_req = 1'b1;
				initiator_clear_seq_phase = 2'd0;
				if (initiator_phase_transition_ack)
					initiator_state_d = 4'd0;
			end
			default: initiator_state_d = 4'd1;
		endcase
	end
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			initiator_state_q <= InitiatorStateResetValue;
		else
			initiator_state_q <= initiator_state_d;
	cc_cdc_4phase_src_0A8DA #(
		.SyncStages(ResetSyncStages),
		.Decoupled(0),
		.SendResetMsg(ClearOnAsyncReset),
		.ResetMsg(2'd1)
	) i_state_transition_cdc_src(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.data_i(initiator_clear_seq_phase),
		.valid_i(initiator_phase_transition_req),
		.ready_o(initiator_phase_transition_ack),
		.async_req_o(async_req_o),
		.async_ack_i(async_ack_i),
		.async_data_o(async_next_phase_o)
	);
	reg [1:0] receiver_phase_d;
	reg [1:0] receiver_phase_q;
	wire [1:0] receiver_effective_phase;
	wire [1:0] receiver_next_phase;
	wire receiver_phase_req;
	reg receiver_phase_ack;
	reg receiver_phase_pending_d;
	reg receiver_phase_pending_q;
	reg receiver_phase_done_d;
	reg receiver_phase_done_q;
	wire receiver_capture_phase;
	reg receiver_isolate_out;
	reg receiver_clear_out;
	cc_cdc_4phase_dst_AC62C #(
		.SyncStages(ResetSyncStages),
		.Decoupled(0)
	) i_state_transition_cdc_dst(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.data_o(receiver_next_phase),
		.valid_o(receiver_phase_req),
		.ready_i(receiver_phase_ack),
		.async_req_i(async_req_i),
		.async_ack_o(async_ack_o),
		.async_data_i(async_next_phase_i)
	);
	assign receiver_capture_phase = (receiver_phase_req && !receiver_phase_pending_q) && !receiver_phase_done_q;
	always @(*) begin
		if (_sv2v_0)
			;
		receiver_phase_d = receiver_phase_q;
		receiver_phase_pending_d = receiver_phase_pending_q;
		receiver_phase_done_d = receiver_phase_done_q;
		if (!receiver_phase_req)
			receiver_phase_done_d = 1'b0;
		if (receiver_capture_phase) begin
			receiver_phase_d = receiver_next_phase;
			receiver_phase_pending_d = 1'b1;
		end
		if (receiver_phase_ack) begin
			receiver_phase_pending_d = 1'b0;
			receiver_phase_done_d = 1'b1;
		end
	end
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			receiver_phase_q <= 2'd0;
		else
			receiver_phase_q <= receiver_phase_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			receiver_phase_pending_q <= 1'b0;
		else
			receiver_phase_pending_q <= receiver_phase_pending_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			receiver_phase_done_q <= 1'b0;
		else
			receiver_phase_done_q <= receiver_phase_done_d;
	assign receiver_effective_phase = receiver_phase_q;
	always @(*) begin
		if (_sv2v_0)
			;
		receiver_isolate_out = 1'b0;
		receiver_clear_out = 1'b0;
		receiver_phase_ack = 1'b0;
		(* full_case, parallel_case *)
		case (receiver_effective_phase)
			2'd0: begin
				receiver_clear_out = 1'b0;
				receiver_isolate_out = 1'b0;
				receiver_phase_ack = receiver_phase_req && receiver_phase_pending_q;
			end
			2'd1: begin
				receiver_clear_out = 1'b0;
				receiver_isolate_out = 1'b1;
				receiver_phase_ack = (receiver_phase_req && receiver_phase_pending_q) && isolate_ack_i;
			end
			2'd2: begin
				receiver_clear_out = 1'b1;
				receiver_isolate_out = 1'b1;
				receiver_phase_ack = (receiver_phase_req && receiver_phase_pending_q) && clear_ack_i;
			end
			2'd3: begin
				receiver_clear_out = 1'b0;
				receiver_isolate_out = 1'b1;
				receiver_phase_ack = receiver_phase_req && receiver_phase_pending_q;
			end
			default: begin
				receiver_clear_out = 1'b0;
				receiver_isolate_out = 1'b0;
				receiver_phase_ack = 1'b0;
			end
		endcase
		if (receiver_capture_phase)
			receiver_isolate_out = 1'b1;
	end
	assign clear_o = initiator_clear_out || receiver_clear_out;
	assign isolate_o = initiator_isolate_out || receiver_isolate_out;
	initial _sv2v_0 = 0;
endmodule
module cc_cdc_2phase_clearable_22145 (
	src_rst_ni,
	src_clk_i,
	src_clear_i,
	src_clear_pending_o,
	src_data_i,
	src_valid_i,
	src_ready_o,
	dst_rst_ni,
	dst_clk_i,
	dst_clear_i,
	dst_clear_pending_o,
	dst_data_o,
	dst_valid_o,
	dst_ready_i
);
	parameter [31:0] SyncStages = 3;
	parameter [0:0] ClearOnAsyncReset = 1;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire src_clear_i;
	output wire src_clear_pending_o;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	input wire dst_clear_i;
	output wire dst_clear_pending_o;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	(* dont_touch = "true" *) wire async_payload_req;
	(* dont_touch = "true" *) wire async_payload_ack;
	(* dont_touch = "true" *) wire [7:0] async_payload_data;
	(* dont_touch = "true" *) wire async_reset_src2dst_req;
	(* dont_touch = "true" *) wire async_reset_dst2src_ack;
	(* dont_touch = "true" *) wire [1:0] async_reset_src2dst_next_phase;
	(* dont_touch = "true" *) wire async_reset_dst2src_req;
	(* dont_touch = "true" *) wire async_reset_src2dst_ack;
	(* dont_touch = "true" *) wire [1:0] async_reset_dst2src_next_phase;
	generate
		if (ClearOnAsyncReset) begin : gen_elaboration_assertion
			if (SyncStages < 3) begin : genblk1
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:108:7 - cc_cdc_2phase_clearable.gen_elaboration_assertion.genblk1\n msg: ", "The clearable 2-phase CDC with async reset", "synchronization requires at least 3 synchronizer stages for the FIFO.");
			end
		end
		else begin : gen_elaboration_assertion
			if (SyncStages < 2) begin : gen_elaboration_assertion
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:112:7 - cc_cdc_2phase_clearable.gen_elaboration_assertion.gen_elaboration_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
			end
		end
	endgenerate
	cc_cdc_2phase_clearable_src_34FBB #(
		.SyncStages(SyncStages),
		.ClearOnAsyncReset(ClearOnAsyncReset)
	) i_src(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_clear_i(src_clear_i),
		.src_clear_pending_o(src_clear_pending_o),
		.src_data_i(src_data_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.async_payload_req_o(async_payload_req),
		.async_payload_ack_i(async_payload_ack),
		.async_payload_data_o(async_payload_data),
		.async_reset_next_phase_o(async_reset_src2dst_next_phase),
		.async_reset_req_o(async_reset_src2dst_req),
		.async_reset_ack_i(async_reset_dst2src_ack),
		.async_reset_next_phase_i(async_reset_dst2src_next_phase),
		.async_reset_req_i(async_reset_dst2src_req),
		.async_reset_ack_o(async_reset_src2dst_ack)
	);
	cc_cdc_2phase_clearable_dst_489A0 #(
		.SyncStages(SyncStages),
		.ClearOnAsyncReset(ClearOnAsyncReset)
	) i_dst(
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_clear_i(dst_clear_i),
		.dst_clear_pending_o(dst_clear_pending_o),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i),
		.async_payload_req_i(async_payload_req),
		.async_payload_ack_o(async_payload_ack),
		.async_payload_data_i(async_payload_data),
		.async_reset_next_phase_o(async_reset_dst2src_next_phase),
		.async_reset_req_o(async_reset_dst2src_req),
		.async_reset_ack_i(async_reset_src2dst_ack),
		.async_reset_next_phase_i(async_reset_src2dst_next_phase),
		.async_reset_req_i(async_reset_src2dst_req),
		.async_reset_ack_o(async_reset_dst2src_ack)
	);
endmodule
module cc_cdc_2phase_clearable_dst_489A0 (
	dst_rst_ni,
	dst_clk_i,
	dst_clear_i,
	dst_clear_pending_o,
	dst_data_o,
	dst_valid_o,
	dst_ready_i,
	async_payload_req_i,
	async_payload_ack_o,
	async_payload_data_i,
	async_reset_next_phase_o,
	async_reset_req_o,
	async_reset_ack_i,
	async_reset_next_phase_i,
	async_reset_req_i,
	async_reset_ack_o
);
	parameter [31:0] SyncStages = 2;
	parameter [0:0] ClearOnAsyncReset = 1;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	input wire dst_clear_i;
	output wire dst_clear_pending_o;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	input wire async_payload_req_i;
	output wire async_payload_ack_o;
	input wire [7:0] async_payload_data_i;
	output wire [1:0] async_reset_next_phase_o;
	output wire async_reset_req_o;
	input wire async_reset_ack_i;
	input wire [1:0] async_reset_next_phase_i;
	input wire async_reset_req_i;
	output wire async_reset_ack_o;
	wire dst_clear_req;
	reg dst_clear_ack_q;
	wire dst_isolate_req;
	reg dst_isolate_ack_q;
	wire dst_valid;
	generate
		if (ClearOnAsyncReset) begin : gen_elaboration_assertion
			if (SyncStages < 3) begin : genblk1
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:209:7 - cc_cdc_2phase_clearable_dst.gen_elaboration_assertion.genblk1\n msg: ", "The clearable 2-phase CDC with async reset", "synchronization requires at least 3 synchronizer stages for the FIFO.");
			end
		end
		else begin : gen_elaboration_assertion
			if (SyncStages < 2) begin : gen_sync_stage_assertion
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:213:7 - cc_cdc_2phase_clearable_dst.gen_elaboration_assertion.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
			end
		end
	endgenerate
	localparam [31:0] ResetSyncStages = (SyncStages > 2 ? SyncStages - 1 : 2);
	cc_cdc_reset_ctrlr_half #(
		.SyncStages(ResetSyncStages),
		.ClearOnAsyncReset(ClearOnAsyncReset)
	) i_cdc_reset_ctrlr_half(
		.clk_i(dst_clk_i),
		.rst_ni(dst_rst_ni),
		.clear_i(dst_clear_i),
		.clear_o(dst_clear_req),
		.clear_ack_i(dst_clear_ack_q),
		.isolate_o(dst_isolate_req),
		.isolate_ack_i(dst_isolate_ack_q),
		.async_next_phase_o(async_reset_next_phase_o),
		.async_req_o(async_reset_req_o),
		.async_ack_i(async_reset_ack_i),
		.async_next_phase_i(async_reset_next_phase_i),
		.async_req_i(async_reset_req_i),
		.async_ack_o(async_reset_ack_o)
	);
	cc_cdc_2phase_dst_clearable_728DA #(.SyncStages(SyncStages)) i_dst(
		.rst_ni(dst_rst_ni),
		.clk_i(dst_clk_i),
		.clear_i(dst_clear_req),
		.data_o(dst_data_o),
		.valid_o(dst_valid),
		.ready_i(dst_ready_i & !dst_isolate_req),
		.async_req_i(async_payload_req_i),
		.async_ack_o(async_payload_ack_o),
		.async_data_i(async_payload_data_i)
	);
	assign dst_valid_o = dst_valid & !dst_isolate_req;
	always @(posedge dst_clk_i or negedge dst_rst_ni)
		if (!dst_rst_ni)
			dst_isolate_ack_q <= 1'b0;
		else
			dst_isolate_ack_q <= dst_isolate_req;
	always @(posedge dst_clk_i or negedge dst_rst_ni)
		if (!dst_rst_ni)
			dst_clear_ack_q <= 1'b0;
		else
			dst_clear_ack_q <= dst_clear_req;
	assign dst_clear_pending_o = dst_isolate_req;
endmodule
module cc_cdc_2phase_clearable_src_34FBB (
	src_rst_ni,
	src_clk_i,
	src_clear_i,
	src_clear_pending_o,
	src_data_i,
	src_valid_i,
	src_ready_o,
	async_payload_req_o,
	async_payload_ack_i,
	async_payload_data_o,
	async_reset_next_phase_o,
	async_reset_req_o,
	async_reset_ack_i,
	async_reset_next_phase_i,
	async_reset_req_i,
	async_reset_ack_o
);
	parameter [31:0] SyncStages = 2;
	parameter [0:0] ClearOnAsyncReset = 1;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire src_clear_i;
	output wire src_clear_pending_o;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	output wire async_payload_req_o;
	input wire async_payload_ack_i;
	output wire [7:0] async_payload_data_o;
	output wire [1:0] async_reset_next_phase_o;
	output wire async_reset_req_o;
	input wire async_reset_ack_i;
	input wire [1:0] async_reset_next_phase_i;
	input wire async_reset_req_i;
	output wire async_reset_ack_o;
	wire src_clear_req;
	reg src_clear_ack_q;
	wire src_ready;
	wire src_isolate_req;
	reg src_isolate_ack_q;
	generate
		if (ClearOnAsyncReset) begin : gen_elaboration_assertion
			if (SyncStages < 3) begin : genblk1
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:298:7 - cc_cdc_2phase_clearable_src.gen_elaboration_assertion.genblk1\n msg: ", "The clearable 2-phase CDC with async reset", "synchronization requires at least 3 synchronizer stages for the FIFO.");
			end
		end
		else begin : gen_elaboration_assertion
			if (SyncStages < 2) begin : gen_sync_stage_assertion
				initial $display("Error [elaboration] ../common_cells/src/cc_cdc_2phase_clearable.sv:302:7 - cc_cdc_2phase_clearable_src.gen_elaboration_assertion.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
			end
		end
	endgenerate
	localparam [31:0] ResetSyncStages = (SyncStages > 2 ? SyncStages - 1 : 2);
	cc_cdc_reset_ctrlr_half #(
		.SyncStages(ResetSyncStages),
		.ClearOnAsyncReset(ClearOnAsyncReset)
	) i_cdc_reset_ctrlr_half(
		.clk_i(src_clk_i),
		.rst_ni(src_rst_ni),
		.clear_i(src_clear_i),
		.clear_o(src_clear_req),
		.clear_ack_i(src_clear_ack_q),
		.isolate_o(src_isolate_req),
		.isolate_ack_i(src_isolate_ack_q),
		.async_next_phase_o(async_reset_next_phase_o),
		.async_req_o(async_reset_req_o),
		.async_ack_i(async_reset_ack_i),
		.async_next_phase_i(async_reset_next_phase_i),
		.async_req_i(async_reset_req_i),
		.async_ack_o(async_reset_ack_o)
	);
	cc_cdc_2phase_src_clearable_E2C10 #(.SyncStages(SyncStages)) i_src(
		.rst_ni(src_rst_ni),
		.clk_i(src_clk_i),
		.clear_i(src_clear_req),
		.data_i(src_data_i),
		.valid_i(src_valid_i & !src_isolate_req),
		.ready_o(src_ready),
		.async_req_o(async_payload_req_o),
		.async_ack_i(async_payload_ack_i),
		.async_data_o(async_payload_data_o)
	);
	assign src_ready_o = src_ready & !src_isolate_req;
	always @(posedge src_clk_i or negedge src_rst_ni)
		if (!src_rst_ni)
			src_isolate_ack_q <= 1'b0;
		else
			src_isolate_ack_q <= src_isolate_req;
	always @(posedge src_clk_i or negedge src_rst_ni)
		if (!src_rst_ni)
			src_clear_ack_q <= 1'b0;
		else
			src_clear_ack_q <= src_clear_req;
	assign src_clear_pending_o = src_isolate_req;
endmodule
module cc_cdc_2phase_src_clearable_E2C10 (
	rst_ni,
	clk_i,
	clear_i,
	data_i,
	valid_i,
	ready_o,
	async_req_o,
	async_ack_i,
	async_data_o
);
	reg _sv2v_0;
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	input wire clear_i;
	input wire [7:0] data_i;
	input wire valid_i;
	output wire ready_o;
	output wire async_req_o;
	input wire async_ack_i;
	output wire [7:0] async_data_o;
	(* dont_touch = "true" *) reg req_src_d;
	(* dont_touch = "true" *) reg req_src_q;
	(* dont_touch = "true" *) wire ack_synced;
	(* dont_touch = "true" *) reg [7:0] data_src_d;
	(* dont_touch = "true" *) reg [7:0] data_src_q;
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_ack_i),
		.serial_o(ack_synced)
	);
	always @(*) begin
		if (_sv2v_0)
			;
		data_src_d = data_src_q;
		req_src_d = req_src_q;
		if (clear_i)
			req_src_d = 1'b0;
		else if (valid_i && ready_o) begin
			req_src_d = ~req_src_q;
			data_src_d = data_i;
		end
	end
	always @(posedge clk_i) data_src_q <= data_src_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			req_src_q <= 1'b0;
		else
			req_src_q <= req_src_d;
	assign ready_o = req_src_q == ack_synced;
	assign async_req_o = req_src_q;
	assign async_data_o = data_src_q;
	initial _sv2v_0 = 0;
endmodule
module cc_cdc_2phase_dst_clearable_728DA (
	rst_ni,
	clk_i,
	clear_i,
	data_o,
	valid_o,
	ready_i,
	async_req_i,
	async_ack_o,
	async_data_i
);
	reg _sv2v_0;
	parameter [31:0] SyncStages = 2;
	input wire rst_ni;
	input wire clk_i;
	input wire clear_i;
	output wire [7:0] data_o;
	output wire valid_o;
	input wire ready_i;
	input wire async_req_i;
	output wire async_ack_o;
	input wire [7:0] async_data_i;
	(* dont_touch = "true" *) (* async_reg = "true" *) reg ack_dst_d;
	(* dont_touch = "true" *) (* async_reg = "true" *) reg ack_dst_q;
	(* dont_touch = "true" *) (* async_reg = "true" *) wire req_synced;
	(* dont_touch = "true" *) (* async_reg = "true" *) reg req_synced_q1;
	(* dont_touch = "true" *) reg [7:0] data_dst_d;
	(* dont_touch = "true" *) reg [7:0] data_dst_q;
	tc_sync #(.Stages(SyncStages)) i_sync(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.serial_i(async_req_i),
		.serial_o(req_synced)
	);
	always @(*) begin
		if (_sv2v_0)
			;
		ack_dst_d = ack_dst_q;
		if (clear_i)
			ack_dst_d = 1'b0;
		else if (valid_o && ready_i)
			ack_dst_d = ~ack_dst_q;
	end
	always @(*) begin
		if (_sv2v_0)
			;
		data_dst_d = data_dst_q;
		if ((req_synced != req_synced_q1) && !valid_o)
			data_dst_d = async_data_i;
	end
	always @(posedge clk_i) data_dst_q <= data_dst_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			ack_dst_q <= 1'b0;
		else
			ack_dst_q <= ack_dst_d;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			req_synced_q1 <= 1'b0;
		else
			req_synced_q1 <= req_synced;
	assign valid_o = ack_dst_q != req_synced_q1;
	assign data_o = data_dst_q;
	assign async_ack_o = ack_dst_q;
	initial _sv2v_0 = 0;
endmodule
module cc_cdc_2phase_clearable_w8 (
	src_rst_ni,
	src_clk_i,
	src_clear_i,
	src_clear_pending_o,
	src_data_i,
	src_valid_i,
	src_ready_o,
	dst_rst_ni,
	dst_clk_i,
	dst_clear_i,
	dst_clear_pending_o,
	dst_data_o,
	dst_valid_o,
	dst_ready_i
);
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire src_clear_i;
	output wire src_clear_pending_o;
	input wire [7:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	input wire dst_clear_i;
	output wire dst_clear_pending_o;
	output wire [7:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	cc_cdc_2phase_clearable_22145 #(
		.SyncStages(3),
		.ClearOnAsyncReset(1'b1)
	) i_cdc(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_clear_i(src_clear_i),
		.src_clear_pending_o(src_clear_pending_o),
		.src_data_i(src_data_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_clear_i(dst_clear_i),
		.dst_clear_pending_o(dst_clear_pending_o),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i)
	);
endmodule
