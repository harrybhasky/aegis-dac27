// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// pulp-platform/common_cells e73baaec + tech_cells_generic v0.2.14 (tc_sync). Copyright ETH Zurich and University of Bologna.
// Licensed under the Solderpad Hardware License v0.51 (see LICENSE, http://solderpad.org/licenses/SHL-0.51).
// Top: cc_cdc_fifo_gray_w8 (Aegis shim that fixes the widths, see shims/).
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
module cc_binary_to_gray (
	a_i,
	z_o
);
	parameter [31:0] Width = 1;
	input wire [Width - 1:0] a_i;
	output wire [Width - 1:0] z_o;
	wire [Width:0] a_ext;
	assign a_ext = {1'b0, a_i};
	assign z_o = a_i ^ a_ext[Width:1];
endmodule
module cc_gray_to_binary (
	a_i,
	z_o
);
	parameter [31:0] Width = 1;
	input wire [Width - 1:0] a_i;
	output wire [Width - 1:0] z_o;
	genvar _gv_i_1;
	generate
		for (_gv_i_1 = 0; _gv_i_1 < Width; _gv_i_1 = _gv_i_1 + 1) begin : genblk1
			localparam i = _gv_i_1;
			assign z_o[i] = ^a_i[Width - 1:i];
		end
	endgenerate
endmodule
module cc_spill_register_flushable_74AFC_A0C1F (
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
	parameter [31:0] data_t_data_t_data_t_data_t_Width = 0;
	parameter [0:0] Bypass = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire clr_i;
	input wire valid_i;
	input wire flush_i;
	output wire ready_o;
	input wire [data_t_data_t_data_t_data_t_Width - 1:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [data_t_data_t_data_t_data_t_Width - 1:0] data_o;
	function automatic [data_t_data_t_data_t_data_t_Width - 1:0] sv2v_cast_1704A;
		input reg [data_t_data_t_data_t_data_t_Width - 1:0] inp;
		sv2v_cast_1704A = inp;
	endfunction
	generate
		if (Bypass) begin : gen_bypass
			assign valid_o = valid_i;
			assign ready_o = ready_i;
			assign data_o = data_i;
		end
		else begin : gen_spill_reg
			reg [data_t_data_t_data_t_data_t_Width - 1:0] a_data_q;
			reg a_full_q;
			wire a_fill;
			wire a_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_data_q <= sv2v_cast_1704A(1'sb0);
				else if (clr_i)
					a_data_q <= sv2v_cast_1704A(1'sb0);
				else if (a_fill)
					a_data_q <= data_i;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					a_full_q <= 1'sb0;
				else if (clr_i)
					a_full_q <= 1'sb0;
				else if (a_fill || a_drain)
					a_full_q <= a_fill;
			reg [data_t_data_t_data_t_data_t_Width - 1:0] b_data_q;
			reg b_full_q;
			wire b_fill;
			wire b_drain;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					b_data_q <= sv2v_cast_1704A(1'sb0);
				else if (clr_i)
					b_data_q <= sv2v_cast_1704A(1'sb0);
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
module cc_spill_register_32099_32952 (
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
	parameter [31:0] data_t_data_t_data_t_Width = 0;
	parameter [0:0] Bypass = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire clr_i;
	input wire valid_i;
	output wire ready_o;
	input wire [data_t_data_t_data_t_Width - 1:0] data_i;
	output wire valid_o;
	input wire ready_i;
	output wire [data_t_data_t_data_t_Width - 1:0] data_o;
	cc_spill_register_flushable_74AFC_A0C1F #(
		.data_t_data_t_data_t_data_t_Width(data_t_data_t_data_t_Width),
		.Bypass(Bypass)
	) spill_register_flushable_i(
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
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray (
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
	parameter [31:0] Width = 1;
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [Width - 1:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [Width - 1:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	wire [((2 ** LogDepth) * Width) - 1:0] async_data;
	wire [LogDepth:0] async_wptr;
	wire [LogDepth:0] async_rptr;
	cc_cdc_fifo_gray_src_8DE5D_42D78 #(
		.data_t_Width(Width),
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_src(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_data_i(src_data_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.async_data_o(async_data),
		.async_wptr_o(async_wptr),
		.async_rptr_i(async_rptr)
	);
	cc_cdc_fifo_gray_dst_634C5_8AD5C #(
		.data_t_Width(Width),
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_dst(
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i),
		.async_data_i(async_data),
		.async_wptr_i(async_wptr),
		.async_rptr_o(async_rptr)
	);
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_src_8DE5D_42D78 (
	src_rst_ni,
	src_clk_i,
	src_data_i,
	src_valid_i,
	src_ready_o,
	async_data_o,
	async_wptr_o,
	async_rptr_i
);
	parameter [31:0] data_t_Width = 0;
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [data_t_Width - 1:0] src_data_i;
	input wire src_valid_i;
	output wire src_ready_o;
	output wire [((2 ** LogDepth) * data_t_Width) - 1:0] async_data_o;
	output wire [LogDepth:0] async_wptr_o;
	input wire [LogDepth:0] async_rptr_i;
	wire [LogDepth - 1:0] src_widx;
	wire src_write;
	assign src_write = src_valid_i & src_ready_o;
	cc_cdc_fifo_gray_src_data_958AB_791C1 #(
		.data_t_data_t_Width(data_t_Width),
		.LogDepth(LogDepth)
	) i_src_data(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_data_i(src_data_i),
		.src_widx_i(src_widx),
		.src_write_i(src_write),
		.async_data_o(async_data_o)
	);
	cc_cdc_fifo_gray_src_ptr #(
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_src_ptr(
		.src_rst_ni(src_rst_ni),
		.src_clk_i(src_clk_i),
		.src_valid_i(src_valid_i),
		.src_ready_o(src_ready_o),
		.src_widx_o(src_widx),
		.async_wptr_o(async_wptr_o),
		.async_rptr_i(async_rptr_i)
	);
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_dst_634C5_8AD5C (
	dst_rst_ni,
	dst_clk_i,
	dst_data_o,
	dst_valid_o,
	dst_ready_i,
	async_data_i,
	async_wptr_i,
	async_rptr_o
);
	parameter [31:0] data_t_Width = 0;
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [data_t_Width - 1:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	input wire [((2 ** LogDepth) * data_t_Width) - 1:0] async_data_i;
	input wire [LogDepth:0] async_wptr_i;
	output wire [LogDepth:0] async_rptr_o;
	wire dst_valid;
	wire dst_ready;
	wire [LogDepth - 1:0] dst_ridx;
	cc_cdc_fifo_gray_dst_ptr #(
		.LogDepth(LogDepth),
		.SyncStages(SyncStages)
	) i_dst_ptr(
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_ready_i(dst_ready),
		.dst_valid_o(dst_valid),
		.dst_ridx_o(dst_ridx),
		.async_wptr_i(async_wptr_i),
		.async_rptr_o(async_rptr_o)
	);
	cc_cdc_fifo_gray_dst_data_B9321_E8751 #(
		.data_t_data_t_Width(data_t_Width),
		.LogDepth(LogDepth)
	) i_dst_data(
		.dst_rst_ni(dst_rst_ni),
		.dst_clk_i(dst_clk_i),
		.dst_data_o(dst_data_o),
		.dst_valid_o(dst_valid_o),
		.dst_ready_i(dst_ready_i),
		.dst_valid_i(dst_valid),
		.dst_ready_o(dst_ready),
		.dst_ridx_i(dst_ridx),
		.async_data_i(async_data_i)
	);
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_src_data_958AB_791C1 (
	src_rst_ni,
	src_clk_i,
	src_data_i,
	src_widx_i,
	src_write_i,
	async_data_o
);
	parameter [31:0] data_t_data_t_Width = 0;
	reg _sv2v_0;
	parameter [31:0] LogDepth = 3;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire [data_t_data_t_Width - 1:0] src_data_i;
	input wire [LogDepth - 1:0] src_widx_i;
	input wire src_write_i;
	output wire [((2 ** LogDepth) * data_t_data_t_Width) - 1:0] async_data_o;
	reg [((2 ** LogDepth) * data_t_data_t_Width) - 1:0] data_d;
	reg [((2 ** LogDepth) * data_t_data_t_Width) - 1:0] data_q;
	always @(*) begin
		if (_sv2v_0)
			;
		data_d = data_q;
		data_d[src_widx_i * data_t_data_t_Width+:data_t_data_t_Width] = src_data_i;
	end
	always @(posedge src_clk_i or negedge src_rst_ni)
		if (!src_rst_ni)
			data_q <= 1'sb0;
		else if (src_write_i)
			data_q <= data_d;
	assign async_data_o = data_q;
	initial _sv2v_0 = 0;
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_src_ptr (
	src_rst_ni,
	src_clk_i,
	src_valid_i,
	src_ready_o,
	src_widx_o,
	async_wptr_o,
	async_rptr_i
);
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire src_rst_ni;
	input wire src_clk_i;
	input wire src_valid_i;
	output wire src_ready_o;
	output wire [LogDepth - 1:0] src_widx_o;
	output wire [LogDepth:0] async_wptr_o;
	input wire [LogDepth:0] async_rptr_i;
	localparam [31:0] PtrWidth = LogDepth + 1;
	localparam [PtrWidth - 1:0] PtrFull = 1 << LogDepth;
	reg [PtrWidth - 1:0] wptr_q;
	wire [PtrWidth - 1:0] wptr_d;
	wire [PtrWidth - 1:0] wptr_bin;
	wire [PtrWidth - 1:0] wptr_next;
	wire [PtrWidth - 1:0] rptr;
	wire [PtrWidth - 1:0] rptr_bin;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_fifo_gray.sv:324:5 - cc_cdc_fifo_gray_src_ptr.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	genvar _gv_i_2;
	generate
		for (_gv_i_2 = 0; _gv_i_2 < PtrWidth; _gv_i_2 = _gv_i_2 + 1) begin : gen_sync
			localparam i = _gv_i_2;
			tc_sync #(.Stages(SyncStages)) i_sync(
				.clk_i(src_clk_i),
				.rst_ni(src_rst_ni),
				.serial_i(async_rptr_i[i]),
				.serial_o(rptr[i])
			);
		end
	endgenerate
	cc_gray_to_binary #(.Width(PtrWidth)) i_rptr_g2b(
		.a_i(rptr),
		.z_o(rptr_bin)
	);
	assign wptr_next = wptr_bin + 1;
	cc_gray_to_binary #(.Width(PtrWidth)) i_wptr_g2b(
		.a_i(wptr_q),
		.z_o(wptr_bin)
	);
	cc_binary_to_gray #(.Width(PtrWidth)) i_wptr_b2g(
		.a_i(wptr_next),
		.z_o(wptr_d)
	);
	always @(posedge src_clk_i or negedge src_rst_ni)
		if (!src_rst_ni)
			wptr_q <= 1'sb0;
		else if (src_valid_i & src_ready_o)
			wptr_q <= wptr_d;
	assign src_widx_o = wptr_bin[LogDepth - 1:0];
	assign async_wptr_o = wptr_q;
	assign src_ready_o = (wptr_bin ^ rptr_bin) != PtrFull;
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_dst_ptr (
	dst_rst_ni,
	dst_clk_i,
	dst_ready_i,
	dst_valid_o,
	dst_ridx_o,
	async_wptr_i,
	async_rptr_o
);
	parameter [31:0] LogDepth = 3;
	parameter [31:0] SyncStages = 2;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	input wire dst_ready_i;
	output wire dst_valid_o;
	output wire [LogDepth - 1:0] dst_ridx_o;
	input wire [LogDepth:0] async_wptr_i;
	output wire [LogDepth:0] async_rptr_o;
	localparam [31:0] PtrWidth = LogDepth + 1;
	localparam [PtrWidth - 1:0] PtrEmpty = 1'sb0;
	reg [PtrWidth - 1:0] rptr_q;
	wire [PtrWidth - 1:0] rptr_d;
	wire [PtrWidth - 1:0] rptr_bin;
	wire [PtrWidth - 1:0] rptr_next;
	wire [PtrWidth - 1:0] wptr;
	wire [PtrWidth - 1:0] wptr_bin;
	generate
		if (SyncStages < 2) begin : gen_sync_stage_assertion
			initial $display("Error [elaboration] ../common_cells/src/cc_cdc_fifo_gray.sv:378:5 - cc_cdc_fifo_gray_dst_ptr.gen_sync_stage_assertion\n msg: ", "A minimum of 2 synchronizer stages is required for proper functionality.");
		end
	endgenerate
	assign rptr_next = rptr_bin + 1;
	cc_gray_to_binary #(.Width(PtrWidth)) i_rptr_g2b(
		.a_i(rptr_q),
		.z_o(rptr_bin)
	);
	cc_binary_to_gray #(.Width(PtrWidth)) i_rptr_b2g(
		.a_i(rptr_next),
		.z_o(rptr_d)
	);
	always @(posedge dst_clk_i or negedge dst_rst_ni)
		if (!dst_rst_ni)
			rptr_q <= 1'sb0;
		else if (dst_valid_o & dst_ready_i)
			rptr_q <= rptr_d;
	assign dst_ridx_o = rptr_bin[LogDepth - 1:0];
	assign async_rptr_o = rptr_q;
	genvar _gv_i_3;
	generate
		for (_gv_i_3 = 0; _gv_i_3 < PtrWidth; _gv_i_3 = _gv_i_3 + 1) begin : gen_sync
			localparam i = _gv_i_3;
			tc_sync #(.Stages(SyncStages)) i_sync(
				.clk_i(dst_clk_i),
				.rst_ni(dst_rst_ni),
				.serial_i(async_wptr_i[i]),
				.serial_o(wptr[i])
			);
		end
	endgenerate
	cc_gray_to_binary #(.Width(PtrWidth)) i_wptr_g2b(
		.a_i(wptr),
		.z_o(wptr_bin)
	);
	assign dst_valid_o = (wptr_bin ^ rptr_bin) != PtrEmpty;
endmodule
(* no_ungroup *) (* no_boundary_optimization *) module cc_cdc_fifo_gray_dst_data_B9321_E8751 (
	dst_rst_ni,
	dst_clk_i,
	dst_data_o,
	dst_valid_o,
	dst_ready_i,
	dst_valid_i,
	dst_ready_o,
	dst_ridx_i,
	async_data_i
);
	parameter [31:0] data_t_data_t_Width = 0;
	parameter [31:0] LogDepth = 3;
	input wire dst_rst_ni;
	input wire dst_clk_i;
	output wire [data_t_data_t_Width - 1:0] dst_data_o;
	output wire dst_valid_o;
	input wire dst_ready_i;
	input wire dst_valid_i;
	output wire dst_ready_o;
	input wire [LogDepth - 1:0] dst_ridx_i;
	input wire [((2 ** LogDepth) * data_t_data_t_Width) - 1:0] async_data_i;
	wire [data_t_data_t_Width - 1:0] dst_data;
	assign dst_data = async_data_i[dst_ridx_i * data_t_data_t_Width+:data_t_data_t_Width];
	localparam [0:0] sv2v_uu_i_spill_register_ext_clr_i_0 = 1'sb0;
	cc_spill_register_32099_32952 #(.data_t_data_t_data_t_Width(data_t_data_t_Width)) i_spill_register(
		.clk_i(dst_clk_i),
		.rst_ni(dst_rst_ni),
		.clr_i(sv2v_uu_i_spill_register_ext_clr_i_0),
		.valid_i(dst_valid_i),
		.ready_o(dst_ready_o),
		.data_i(dst_data),
		.valid_o(dst_valid_o),
		.ready_i(dst_ready_i),
		.data_o(dst_data_o)
	);
endmodule
module cc_cdc_fifo_gray_w8 (
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
	cc_cdc_fifo_gray #(
		.Width(8),
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
