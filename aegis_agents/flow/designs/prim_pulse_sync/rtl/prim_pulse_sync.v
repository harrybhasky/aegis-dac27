// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// lowRISC/opentitan 0cd56ca0 (hw/ip/prim, hw/ip/prim_generic). Copyright lowRISC contributors (OpenTitan project).
// Licensed under the Apache License, Version 2.0 (see LICENSE). SPDX-License-Identifier: Apache-2.0
// Top: prim_pulse_sync_cfg (Aegis shim that fixes the widths, see shims/).
module prim_flop (
	clk_i,
	rst_ni,
	d_i,
	q_o
);
	parameter signed [31:0] Width = 1;
	parameter [Width - 1:0] ResetValue = 0;
	input clk_i;
	input rst_ni;
	input [Width - 1:0] d_i;
	output reg [Width - 1:0] q_o;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			q_o <= ResetValue;
		else
			q_o <= d_i;
endmodule
module prim_flop_2sync (
	clk_i,
	rst_ni,
	d_i,
	q_o
);
	reg _sv2v_0;
	parameter signed [31:0] Width = 16;
	parameter [Width - 1:0] ResetValue = 1'sb0;
	parameter [0:0] EnablePrimCdcRand = 1;
	input clk_i;
	input rst_ni;
	input [Width - 1:0] d_i;
	output wire [Width - 1:0] q_o;
	reg [Width - 1:0] d_o;
	wire [Width - 1:0] intq;
	wire unused_sig;
	assign unused_sig = EnablePrimCdcRand;
	always @(*) begin
		if (_sv2v_0)
			;
		d_o = d_i;
	end
	prim_flop #(
		.Width(Width),
		.ResetValue(ResetValue)
	) u_sync_1(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.d_i(d_o),
		.q_o(intq)
	);
	prim_flop #(
		.Width(Width),
		.ResetValue(ResetValue)
	) u_sync_2(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.d_i(intq),
		.q_o(q_o)
	);
	initial _sv2v_0 = 0;
endmodule
module prim_pulse_sync (
	clk_src_i,
	rst_src_ni,
	src_pulse_i,
	clk_dst_i,
	rst_dst_ni,
	dst_pulse_o
);
	input wire clk_src_i;
	input wire rst_src_ni;
	input wire src_pulse_i;
	input wire clk_dst_i;
	input wire rst_dst_ni;
	output wire dst_pulse_o;
	reg src_level;
	always @(posedge clk_src_i or negedge rst_src_ni)
		if (!rst_src_ni)
			src_level <= 1'b0;
		else
			src_level <= src_level ^ src_pulse_i;
	wire dst_level;
	prim_flop_2sync #(.Width(1)) prim_flop_2sync(
		.d_i(src_level),
		.clk_i(clk_dst_i),
		.rst_ni(rst_dst_ni),
		.q_o(dst_level)
	);
	reg dst_level_q;
	always @(posedge clk_dst_i or negedge rst_dst_ni)
		if (!rst_dst_ni)
			dst_level_q <= 1'b0;
		else
			dst_level_q <= dst_level;
	assign dst_pulse_o = dst_level_q ^ dst_level;
endmodule
module prim_pulse_sync_cfg (
	clk_src_i,
	rst_src_ni,
	src_pulse_i,
	clk_dst_i,
	rst_dst_ni,
	dst_pulse_o
);
	input wire clk_src_i;
	input wire rst_src_ni;
	input wire src_pulse_i;
	input wire clk_dst_i;
	input wire rst_dst_ni;
	output wire dst_pulse_o;
	prim_pulse_sync u_sync(
		.clk_src_i(clk_src_i),
		.rst_src_ni(rst_src_ni),
		.src_pulse_i(src_pulse_i),
		.clk_dst_i(clk_dst_i),
		.rst_dst_ni(rst_dst_ni),
		.dst_pulse_o(dst_pulse_o)
	);
endmodule
