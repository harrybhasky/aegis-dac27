// Plain Verilog-2005 produced by sv2v 0.0.13 from upstream SystemVerilog (see SOURCE.txt; do not edit).
// lowRISC/opentitan 0cd56ca0 (hw/ip/prim, hw/ip/prim_generic). Copyright lowRISC contributors (OpenTitan project).
// Licensed under the Apache License, Version 2.0 (see LICENSE). SPDX-License-Identifier: Apache-2.0
// Top: prim_sync_reqack_data_w8 (Aegis shim that fixes the widths, see shims/).
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
module prim_sync_reqack (
	clk_src_i,
	rst_src_ni,
	clk_dst_i,
	rst_dst_ni,
	req_chk_i,
	src_req_i,
	src_ack_o,
	dst_req_o,
	dst_ack_i
);
	reg _sv2v_0;
	parameter [0:0] EnRstChks = 1'b0;
	parameter [0:0] EnRzHs = 1'b0;
	input clk_src_i;
	input rst_src_ni;
	input clk_dst_i;
	input rst_dst_ni;
	input wire req_chk_i;
	input wire src_req_i;
	output reg src_ack_o;
	output reg dst_req_o;
	input wire dst_ack_i;
	wire unused_req_chk;
	assign unused_req_chk = req_chk_i;
	generate
		if (EnRzHs) begin : gen_rz_hs_protocol
			reg src_fsm_d;
			reg src_fsm_q;
			reg dst_fsm_d;
			reg dst_fsm_q;
			wire src_ack;
			wire dst_ack;
			wire src_req;
			wire dst_req;
			always @(*) begin : src_fsm
				if (_sv2v_0)
					;
				src_fsm_d = src_fsm_q;
				src_ack_o = 1'b0;
				(* full_case, parallel_case *)
				case (src_fsm_q)
					1'b0:
						if (!src_ack && src_req_i)
							src_fsm_d = 1'b1;
					1'b1: begin
						src_ack_o = src_ack;
						if (!src_req_i || src_ack)
							src_fsm_d = 1'b0;
					end
					default:
						;
				endcase
			end
			prim_flop_2sync #(.Width(1)) ack_sync(
				.clk_i(clk_src_i),
				.rst_ni(rst_src_ni),
				.d_i(dst_ack),
				.q_o(src_ack)
			);
			always @(posedge clk_src_i or negedge rst_src_ni)
				if (!rst_src_ni)
					src_fsm_q <= 1'b0;
				else
					src_fsm_q <= src_fsm_d;
			assign src_req = src_fsm_q;
			always @(*) begin : dst_fsm
				if (_sv2v_0)
					;
				dst_fsm_d = dst_fsm_q;
				dst_req_o = 1'b0;
				(* full_case, parallel_case *)
				case (dst_fsm_q)
					1'b0:
						if (dst_req) begin
							dst_req_o = 1'b1;
							if (dst_ack_i)
								dst_fsm_d = 1'b1;
						end
					1'b1:
						if (!dst_req)
							dst_fsm_d = 1'b0;
					default:
						;
				endcase
			end
			prim_flop_2sync #(.Width(1)) req_sync(
				.clk_i(clk_dst_i),
				.rst_ni(rst_dst_ni),
				.d_i(src_req),
				.q_o(dst_req)
			);
			always @(posedge clk_dst_i or negedge rst_dst_ni)
				if (!rst_dst_ni)
					dst_fsm_q <= 1'b0;
				else
					dst_fsm_q <= dst_fsm_d;
			assign dst_ack = dst_fsm_q;
		end
		else begin : gen_nrz_hs_protocol
			reg src_fsm_ns;
			reg src_fsm_cs;
			reg dst_fsm_ns;
			reg dst_fsm_cs;
			reg src_req_d;
			reg src_req_q;
			wire src_ack;
			reg dst_ack_d;
			reg dst_ack_q;
			wire dst_req;
			wire src_handshake;
			wire dst_handshake;
			assign src_handshake = src_req_i & src_ack_o;
			assign dst_handshake = dst_req_o & dst_ack_i;
			prim_flop_2sync #(.Width(1)) req_sync(
				.clk_i(clk_dst_i),
				.rst_ni(rst_dst_ni),
				.d_i(src_req_q),
				.q_o(dst_req)
			);
			prim_flop_2sync #(.Width(1)) ack_sync(
				.clk_i(clk_src_i),
				.rst_ni(rst_src_ni),
				.d_i(dst_ack_q),
				.q_o(src_ack)
			);
			always @(*) begin : src_fsm
				if (_sv2v_0)
					;
				src_fsm_ns = src_fsm_cs;
				src_req_d = src_req_q;
				src_ack_o = 1'b0;
				(* full_case, parallel_case *)
				case (src_fsm_cs)
					1'd0: begin
						src_req_d = src_req_i;
						src_ack_o = src_ack;
						if (src_handshake)
							src_fsm_ns = 1'd1;
					end
					1'd1: begin
						src_req_d = ~src_req_i;
						src_ack_o = ~src_ack;
						if (src_handshake)
							src_fsm_ns = 1'd0;
					end
					default:
						;
				endcase
			end
			always @(*) begin : dst_fsm
				if (_sv2v_0)
					;
				dst_fsm_ns = dst_fsm_cs;
				dst_req_o = 1'b0;
				dst_ack_d = dst_ack_q;
				(* full_case, parallel_case *)
				case (dst_fsm_cs)
					1'd0: begin
						dst_req_o = dst_req;
						dst_ack_d = dst_ack_i;
						if (dst_handshake)
							dst_fsm_ns = 1'd1;
					end
					1'd1: begin
						dst_req_o = ~dst_req;
						dst_ack_d = ~dst_ack_i;
						if (dst_handshake)
							dst_fsm_ns = 1'd0;
					end
					default:
						;
				endcase
			end
			always @(posedge clk_src_i or negedge rst_src_ni)
				if (!rst_src_ni) begin
					src_fsm_cs <= 1'd0;
					src_req_q <= 1'b0;
				end
				else begin
					src_fsm_cs <= src_fsm_ns;
					src_req_q <= src_req_d;
				end
			always @(posedge clk_dst_i or negedge rst_dst_ni)
				if (!rst_dst_ni) begin
					dst_fsm_cs <= 1'd0;
					dst_ack_q <= 1'b0;
				end
				else begin
					dst_fsm_cs <= dst_fsm_ns;
					dst_ack_q <= dst_ack_d;
				end
		end
	endgenerate
	initial _sv2v_0 = 0;
endmodule
module prim_sync_reqack_data (
	clk_src_i,
	rst_src_ni,
	clk_dst_i,
	rst_dst_ni,
	req_chk_i,
	src_req_i,
	src_ack_o,
	dst_req_o,
	dst_ack_i,
	data_i,
	data_o
);
	parameter [31:0] Width = 1;
	parameter [0:0] EnRstChks = 1'b0;
	parameter [0:0] DataSrc2Dst = 1'b1;
	parameter [0:0] DataReg = 1'b0;
	parameter [0:0] EnRzHs = 1'b0;
	input clk_src_i;
	input rst_src_ni;
	input clk_dst_i;
	input rst_dst_ni;
	input wire req_chk_i;
	input wire src_req_i;
	output wire src_ack_o;
	output wire dst_req_o;
	input wire dst_ack_i;
	input wire [Width - 1:0] data_i;
	output wire [Width - 1:0] data_o;
	prim_sync_reqack #(
		.EnRstChks(EnRstChks),
		.EnRzHs(EnRzHs)
	) u_prim_sync_reqack(
		.clk_src_i(clk_src_i),
		.rst_src_ni(rst_src_ni),
		.clk_dst_i(clk_dst_i),
		.rst_dst_ni(rst_dst_ni),
		.req_chk_i(req_chk_i),
		.src_req_i(src_req_i),
		.src_ack_o(src_ack_o),
		.dst_req_o(dst_req_o),
		.dst_ack_i(dst_ack_i)
	);
	generate
		if ((DataSrc2Dst == 1'b0) && (DataReg == 1'b1)) begin : gen_data_reg
			wire data_we;
			wire [Width - 1:0] data_d;
			reg [Width - 1:0] data_q;
			assign data_we = dst_req_o & dst_ack_i;
			assign data_d = data_i;
			always @(posedge clk_dst_i or negedge rst_dst_ni)
				if (!rst_dst_ni)
					data_q <= 1'sb0;
				else if (data_we)
					data_q <= data_d;
			assign data_o = data_q;
		end
		else begin : gen_no_data_reg
			assign data_o = data_i;
		end
	endgenerate
endmodule
module prim_sync_reqack_data_w8 (
	clk_src_i,
	rst_src_ni,
	clk_dst_i,
	rst_dst_ni,
	req_chk_i,
	src_req_i,
	src_ack_o,
	dst_req_o,
	dst_ack_i,
	data_i,
	data_o
);
	input wire clk_src_i;
	input wire rst_src_ni;
	input wire clk_dst_i;
	input wire rst_dst_ni;
	input wire req_chk_i;
	input wire src_req_i;
	output wire src_ack_o;
	output wire dst_req_o;
	input wire dst_ack_i;
	input wire [7:0] data_i;
	output wire [7:0] data_o;
	prim_sync_reqack_data #(
		.Width(8),
		.EnRstChks(1'b0),
		.DataSrc2Dst(1'b0),
		.DataReg(1'b1),
		.EnRzHs(1'b0)
	) u_sync(
		.clk_src_i(clk_src_i),
		.rst_src_ni(rst_src_ni),
		.clk_dst_i(clk_dst_i),
		.rst_dst_ni(rst_dst_ni),
		.req_chk_i(req_chk_i),
		.src_req_i(src_req_i),
		.src_ack_o(src_ack_o),
		.dst_req_o(dst_req_o),
		.dst_ack_i(dst_ack_i),
		.data_i(data_i),
		.data_o(data_o)
	);
endmodule
