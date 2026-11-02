#!/usr/bin/env python3
"""
Create flow/designs/<name>/ (design.json, rtl/, <name>.sdc) for the benchmark suites.

  python3 bench/setup_designs.py [--suite cdc|drrtl|all] [--calibrate] [--only NAME ...]

Suites
  cdc    multi-clock / CDC designs from open-source projects (see benchmarks/README.md for
         sources and licenses). Clock periods are calibrated per domain (--calibrate):
         each clock gets period = ratio x its critical-path delay at a relaxed constraint,
         so every domain violates and per-domain scoring is exercised.
  drrtl  the 20 Dr. RTL designs (rtl_dataset, v0), single clock at 0.1 ns on Nangate45,
         the same protocol as Dr. RTL (DC + Nangate45 + 0.1 ns), synthesized here with
         Yosys/ABC + OpenSTA.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BENCH = os.path.abspath(os.path.join(ROOT, "..", "benchmarks"))
M = os.path.join(BENCH, "multiclock")
CONV = os.path.join(M, "converted")   # sv2v output of the SystemVerilog CDC primitives (see convert.sh there)
LIB = "pdk/nangate45.lib"

# name: (top, [files], {clock_port: relaxed_period_ns}, extra verilog wrapper or None, groups, resets)
CDC = {
    "async_fifo": ("async_fifo", [M + "/async_fifo/rtl/" + f for f in
                                  ("async_fifo.v", "fifomem.v", "rptr_empty.v", "wptr_full.v", "sync_r2w.v", "sync_w2r.v", "sync_ptr.v")],
                   {"wclk": 5, "rclk": 7}, None, [["wclk"], ["rclk"]], None),
    "afifo": ("afifo", [M + "/wb2axip/rtl/afifo.v"], {"i_wclk": 5, "i_rclk": 7}, None, [["i_wclk"], ["i_rclk"]], None),
    "axis_async_fifo": ("axis_async_fifo_bench", [M + "/verilog-axis/rtl/axis_async_fifo.v"], {"s_clk": 5, "m_clk": 7},
                        """module axis_async_fifo_bench (
  input s_clk, input s_rst, input [7:0] s_axis_tdata, input s_axis_tvalid, output s_axis_tready, input s_axis_tlast,
  input s_axis_tuser, input m_clk, input m_rst, output [7:0] m_axis_tdata, output m_axis_tvalid, input m_axis_tready,
  output m_axis_tlast, output m_axis_tuser, output [5:0] s_status_depth, output [5:0] m_status_depth,
  output s_status_overflow, output s_status_bad_frame, output s_status_good_frame,
  output m_status_overflow, output m_status_bad_frame, output m_status_good_frame);
  axis_async_fifo #(.DEPTH(32), .DATA_WIDTH(8), .KEEP_ENABLE(0), .LAST_ENABLE(1), .ID_ENABLE(0), .DEST_ENABLE(0),
                    .USER_ENABLE(1), .USER_WIDTH(1), .FRAME_FIFO(1), .DROP_BAD_FRAME(1), .DROP_WHEN_FULL(0)) u (
    .s_clk(s_clk), .s_rst(s_rst), .s_axis_tdata(s_axis_tdata), .s_axis_tkeep(1'b1), .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready), .s_axis_tlast(s_axis_tlast), .s_axis_tid(8'd0), .s_axis_tdest(8'd0),
    .s_axis_tuser(s_axis_tuser), .m_clk(m_clk), .m_rst(m_rst), .m_axis_tdata(m_axis_tdata), .m_axis_tkeep(),
    .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready), .m_axis_tlast(m_axis_tlast), .m_axis_tid(),
    .m_axis_tdest(), .m_axis_tuser(m_axis_tuser), .s_pause_req(1'b0), .s_pause_ack(), .m_pause_req(1'b0), .m_pause_ack(),
    .s_status_depth(s_status_depth), .s_status_depth_commit(), .s_status_overflow(s_status_overflow),
    .s_status_bad_frame(s_status_bad_frame), .s_status_good_frame(s_status_good_frame),
    .m_status_depth(m_status_depth), .m_status_depth_commit(), .m_status_overflow(m_status_overflow),
    .m_status_bad_frame(m_status_bad_frame), .m_status_good_frame(m_status_good_frame));
endmodule
""", [["s_clk"], ["m_clk"]], [{"port": "s_rst", "active_low": False}, {"port": "m_rst", "active_low": False}]),
    "axil_cdc": ("axil_cdc", [M + "/verilog-axi/rtl/" + f for f in ("axil_cdc.v", "axil_cdc_rd.v", "axil_cdc_wr.v")],
                 {"s_clk": 5, "m_clk": 7}, None, [["s_clk"], ["m_clk"]],
                 [{"port": "s_rst", "active_low": False}, {"port": "m_rst", "active_low": False}]),
    "eth_mac_1g_fifo": ("eth_mac_1g_fifo_bench", [M + "/verilog-ethernet/rtl/" + f for f in (
        "eth_mac_1g_fifo.v", "eth_mac_1g.v", "axis_gmii_rx.v", "axis_gmii_tx.v", "lfsr.v")] +
        [M + "/verilog-axis/rtl/axis_async_fifo.v", M + "/verilog-axis/rtl/axis_async_fifo_adapter.v",
         M + "/verilog-axis/rtl/axis_adapter.v"],
        {"rx_clk": 8, "tx_clk": 8, "logic_clk": 6}, """module eth_mac_1g_fifo_bench (
  input rx_clk, input rx_rst, input tx_clk, input tx_rst, input logic_clk, input logic_rst,
  input [7:0] tx_axis_tdata, input tx_axis_tvalid, output tx_axis_tready, input tx_axis_tlast, input tx_axis_tuser,
  output [7:0] rx_axis_tdata, output rx_axis_tvalid, input rx_axis_tready, output rx_axis_tlast, output rx_axis_tuser,
  input [7:0] gmii_rxd, input gmii_rx_dv, input gmii_rx_er, output [7:0] gmii_txd, output gmii_tx_en, output gmii_tx_er,
  output tx_error_underflow, output tx_fifo_overflow, output tx_fifo_bad_frame, output tx_fifo_good_frame,
  output rx_error_bad_frame, output rx_error_bad_fcs, output rx_fifo_overflow, output rx_fifo_bad_frame,
  output rx_fifo_good_frame, input [7:0] cfg_ifg, input cfg_tx_enable, input cfg_rx_enable);
  eth_mac_1g_fifo #(.TX_FIFO_DEPTH(64), .RX_FIFO_DEPTH(64), .TX_FRAME_FIFO(1), .RX_FRAME_FIFO(1)) u (
    .rx_clk(rx_clk), .rx_rst(rx_rst), .tx_clk(tx_clk), .tx_rst(tx_rst), .logic_clk(logic_clk), .logic_rst(logic_rst),
    .tx_axis_tdata(tx_axis_tdata), .tx_axis_tkeep(1'b1), .tx_axis_tvalid(tx_axis_tvalid), .tx_axis_tready(tx_axis_tready),
    .tx_axis_tlast(tx_axis_tlast), .tx_axis_tuser(tx_axis_tuser), .rx_axis_tdata(rx_axis_tdata), .rx_axis_tkeep(),
    .rx_axis_tvalid(rx_axis_tvalid), .rx_axis_tready(rx_axis_tready), .rx_axis_tlast(rx_axis_tlast),
    .rx_axis_tuser(rx_axis_tuser), .gmii_rxd(gmii_rxd), .gmii_rx_dv(gmii_rx_dv), .gmii_rx_er(gmii_rx_er),
    .gmii_txd(gmii_txd), .gmii_tx_en(gmii_tx_en), .gmii_tx_er(gmii_tx_er), .rx_clk_enable(1'b1), .tx_clk_enable(1'b1),
    .rx_mii_select(1'b0), .tx_mii_select(1'b0), .tx_error_underflow(tx_error_underflow),
    .tx_fifo_overflow(tx_fifo_overflow), .tx_fifo_bad_frame(tx_fifo_bad_frame), .tx_fifo_good_frame(tx_fifo_good_frame),
    .rx_error_bad_frame(rx_error_bad_frame), .rx_error_bad_fcs(rx_error_bad_fcs), .rx_fifo_overflow(rx_fifo_overflow),
    .rx_fifo_bad_frame(rx_fifo_bad_frame), .rx_fifo_good_frame(rx_fifo_good_frame), .cfg_ifg(cfg_ifg),
    .cfg_tx_enable(cfg_tx_enable), .cfg_rx_enable(cfg_rx_enable));
endmodule
""", [["rx_clk"], ["tx_clk"], ["logic_clk"]],
        [{"port": p, "active_low": False} for p in ("rx_rst", "tx_rst", "logic_rst")]),
    "drrtl_fifo_2clk": ("fifo", [BENCH + "/Dr_RTL/rtl_dataset/FIFO.v0.v"], {"clk_in": 5, "clk_out": 7}, None,
                   [["clk_in"], ["clk_out"]], [{"port": "rst", "active_low": True}]),
    # CDC protocol primitives (handshake / pulse / req-ack / reset-sequencing), added 2026-10-08
    "cc_cdc_2phase": ("cc_cdc_2phase_bench", [CONV + "/cc_cdc_2phase/cc_cdc_2phase.v"],
        {"src_clk_i": 5, "dst_clk_i": 7}, """module cc_cdc_2phase_bench (
  input wire src_rst_ni,
  input wire src_clk_i,
  input wire [7:0] src_data_i,
  input wire src_valid_i,
  output wire src_ready_o,
  input wire dst_rst_ni,
  input wire dst_clk_i,
  output wire [7:0] dst_data_o,
  output wire dst_valid_o,
  input wire dst_ready_i
);
  cc_cdc_2phase_w8 u (.src_rst_ni(src_rst_ni), .src_clk_i(src_clk_i), .src_data_i(src_data_i),
    .src_valid_i(src_valid_i), .src_ready_o(src_ready_o), .dst_rst_ni(dst_rst_ni), .dst_clk_i(dst_clk_i),
    .dst_data_o(dst_data_o), .dst_valid_o(dst_valid_o), .dst_ready_i(dst_ready_i));
endmodule
""",
        [["src_clk_i"], ["dst_clk_i"]], [{"port": "src_rst_ni", "active_low": True}, {"port": "dst_rst_ni", "active_low": True}]),
    "cc_cdc_4phase": ("cc_cdc_4phase_bench", [CONV + "/cc_cdc_4phase/cc_cdc_4phase.v"],
        {"src_clk_i": 5, "dst_clk_i": 7}, """module cc_cdc_4phase_bench (
  input wire src_rst_ni,
  input wire src_clk_i,
  input wire [7:0] src_data_i,
  input wire src_valid_i,
  output wire src_ready_o,
  input wire dst_rst_ni,
  input wire dst_clk_i,
  output wire [7:0] dst_data_o,
  output wire dst_valid_o,
  input wire dst_ready_i
);
  cc_cdc_4phase_w8 u (.src_rst_ni(src_rst_ni), .src_clk_i(src_clk_i), .src_data_i(src_data_i),
    .src_valid_i(src_valid_i), .src_ready_o(src_ready_o), .dst_rst_ni(dst_rst_ni), .dst_clk_i(dst_clk_i),
    .dst_data_o(dst_data_o), .dst_valid_o(dst_valid_o), .dst_ready_i(dst_ready_i));
endmodule
""",
        [["src_clk_i"], ["dst_clk_i"]], [{"port": "src_rst_ni", "active_low": True}, {"port": "dst_rst_ni", "active_low": True}]),
    "cc_cdc_fifo_gray": ("cc_cdc_fifo_gray_bench", [CONV + "/cc_cdc_fifo_gray/cc_cdc_fifo_gray.v"],
        {"src_clk_i": 5, "dst_clk_i": 7}, """module cc_cdc_fifo_gray_bench (
  input wire src_rst_ni,
  input wire src_clk_i,
  input wire [7:0] src_data_i,
  input wire src_valid_i,
  output wire src_ready_o,
  input wire dst_rst_ni,
  input wire dst_clk_i,
  output wire [7:0] dst_data_o,
  output wire dst_valid_o,
  input wire dst_ready_i
);
  cc_cdc_fifo_gray_w8 u (.src_rst_ni(src_rst_ni), .src_clk_i(src_clk_i), .src_data_i(src_data_i),
    .src_valid_i(src_valid_i), .src_ready_o(src_ready_o), .dst_rst_ni(dst_rst_ni), .dst_clk_i(dst_clk_i),
    .dst_data_o(dst_data_o), .dst_valid_o(dst_valid_o), .dst_ready_i(dst_ready_i));
endmodule
""",
        [["src_clk_i"], ["dst_clk_i"]], [{"port": "src_rst_ni", "active_low": True}, {"port": "dst_rst_ni", "active_low": True}]),
    "cc_cdc_fifo_2phase": ("cc_cdc_fifo_2phase_bench", [CONV + "/cc_cdc_fifo_2phase/cc_cdc_fifo_2phase.v"],
        {"src_clk_i": 5, "dst_clk_i": 7}, """module cc_cdc_fifo_2phase_bench (
  input wire src_rst_ni,
  input wire src_clk_i,
  input wire [7:0] src_data_i,
  input wire src_valid_i,
  output wire src_ready_o,
  input wire dst_rst_ni,
  input wire dst_clk_i,
  output wire [7:0] dst_data_o,
  output wire dst_valid_o,
  input wire dst_ready_i
);
  cc_cdc_fifo_2phase_w8 u (.src_rst_ni(src_rst_ni), .src_clk_i(src_clk_i), .src_data_i(src_data_i),
    .src_valid_i(src_valid_i), .src_ready_o(src_ready_o), .dst_rst_ni(dst_rst_ni), .dst_clk_i(dst_clk_i),
    .dst_data_o(dst_data_o), .dst_valid_o(dst_valid_o), .dst_ready_i(dst_ready_i));
endmodule
""",
        [["src_clk_i"], ["dst_clk_i"]], [{"port": "src_rst_ni", "active_low": True}, {"port": "dst_rst_ni", "active_low": True}]),
    "cc_cdc_reset_ctrlr": ("cc_cdc_reset_ctrlr_bench", [CONV + "/cc_cdc_reset_ctrlr/cc_cdc_reset_ctrlr.v"],
        {"a_clk_i": 5, "b_clk_i": 7}, """module cc_cdc_reset_ctrlr_bench (
  input wire a_clk_i,
  input wire a_rst_ni,
  input wire a_clear_i,
  output wire a_clear_o,
  input wire a_clear_ack_i,
  output wire a_isolate_o,
  input wire a_isolate_ack_i,
  input wire b_clk_i,
  input wire b_rst_ni,
  input wire b_clear_i,
  output wire b_clear_o,
  input wire b_clear_ack_i,
  output wire b_isolate_o,
  input wire b_isolate_ack_i
);
  cc_cdc_reset_ctrlr_cfg u (.a_clk_i(a_clk_i), .a_rst_ni(a_rst_ni), .a_clear_i(a_clear_i),
    .a_clear_o(a_clear_o), .a_clear_ack_i(a_clear_ack_i), .a_isolate_o(a_isolate_o),
    .a_isolate_ack_i(a_isolate_ack_i), .b_clk_i(b_clk_i), .b_rst_ni(b_rst_ni), .b_clear_i(b_clear_i),
    .b_clear_o(b_clear_o), .b_clear_ack_i(b_clear_ack_i), .b_isolate_o(b_isolate_o),
    .b_isolate_ack_i(b_isolate_ack_i));
endmodule
""",
        [["a_clk_i"], ["b_clk_i"]], [{"port": "a_rst_ni", "active_low": True}, {"port": "b_rst_ni", "active_low": True}]),
    "cc_cdc_2phase_clearable": ("cc_cdc_2phase_clearable_bench", [CONV + "/cc_cdc_2phase_clearable/cc_cdc_2phase_clearable.v"],
        {"src_clk_i": 5, "dst_clk_i": 7}, """module cc_cdc_2phase_clearable_bench (
  input wire src_rst_ni,
  input wire src_clk_i,
  input wire src_clear_i,
  output wire src_clear_pending_o,
  input wire [7:0] src_data_i,
  input wire src_valid_i,
  output wire src_ready_o,
  input wire dst_rst_ni,
  input wire dst_clk_i,
  input wire dst_clear_i,
  output wire dst_clear_pending_o,
  output wire [7:0] dst_data_o,
  output wire dst_valid_o,
  input wire dst_ready_i
);
  cc_cdc_2phase_clearable_w8 u (.src_rst_ni(src_rst_ni), .src_clk_i(src_clk_i), .src_clear_i(src_clear_i),
    .src_clear_pending_o(src_clear_pending_o), .src_data_i(src_data_i), .src_valid_i(src_valid_i),
    .src_ready_o(src_ready_o), .dst_rst_ni(dst_rst_ni), .dst_clk_i(dst_clk_i), .dst_clear_i(dst_clear_i),
    .dst_clear_pending_o(dst_clear_pending_o), .dst_data_o(dst_data_o), .dst_valid_o(dst_valid_o),
    .dst_ready_i(dst_ready_i));
endmodule
""",
        [["src_clk_i"], ["dst_clk_i"]], [{"port": "src_rst_ni", "active_low": True}, {"port": "dst_rst_ni", "active_low": True}]),
    "prim_fifo_async": ("prim_fifo_async_bench", [CONV + "/prim_fifo_async/prim_fifo_async.v"],
        {"clk_wr_i": 5, "clk_rd_i": 7}, """module prim_fifo_async_bench (
  input wire clk_wr_i,
  input wire rst_wr_ni,
  input wire wvalid_i,
  output wire wready_o,
  input wire [7:0] wdata_i,
  output wire [2:0] wdepth_o,
  input wire clk_rd_i,
  input wire rst_rd_ni,
  output wire rvalid_o,
  input wire rready_i,
  output wire [7:0] rdata_o,
  output wire [2:0] rdepth_o
);
  prim_fifo_async_w8 u (.clk_wr_i(clk_wr_i), .rst_wr_ni(rst_wr_ni), .wvalid_i(wvalid_i), .wready_o(wready_o),
    .wdata_i(wdata_i), .wdepth_o(wdepth_o), .clk_rd_i(clk_rd_i), .rst_rd_ni(rst_rd_ni), .rvalid_o(rvalid_o),
    .rready_i(rready_i), .rdata_o(rdata_o), .rdepth_o(rdepth_o));
endmodule
""",
        [["clk_wr_i"], ["clk_rd_i"]], [{"port": "rst_wr_ni", "active_low": True}, {"port": "rst_rd_ni", "active_low": True}]),
    "prim_sync_reqack": ("prim_sync_reqack_bench", [CONV + "/prim_sync_reqack/prim_sync_reqack.v"],
        {"clk_src_i": 5, "clk_dst_i": 7}, """module prim_sync_reqack_bench (
  input wire clk_src_i,
  input wire rst_src_ni,
  input wire clk_dst_i,
  input wire rst_dst_ni,
  input wire req_chk_i,
  input wire src_req_i,
  output wire src_ack_o,
  output wire dst_req_o,
  input wire dst_ack_i
);
  prim_sync_reqack_cfg u (.clk_src_i(clk_src_i), .rst_src_ni(rst_src_ni), .clk_dst_i(clk_dst_i),
    .rst_dst_ni(rst_dst_ni), .req_chk_i(req_chk_i), .src_req_i(src_req_i), .src_ack_o(src_ack_o),
    .dst_req_o(dst_req_o), .dst_ack_i(dst_ack_i));
endmodule
""",
        [["clk_src_i"], ["clk_dst_i"]], [{"port": "rst_src_ni", "active_low": True}, {"port": "rst_dst_ni", "active_low": True}]),
    "prim_sync_reqack_data": ("prim_sync_reqack_data_bench", [CONV + "/prim_sync_reqack_data/prim_sync_reqack_data.v"],
        {"clk_src_i": 5, "clk_dst_i": 7}, """module prim_sync_reqack_data_bench (
  input wire clk_src_i,
  input wire rst_src_ni,
  input wire clk_dst_i,
  input wire rst_dst_ni,
  input wire req_chk_i,
  input wire src_req_i,
  output wire src_ack_o,
  output wire dst_req_o,
  input wire dst_ack_i,
  input wire [7:0] data_i,
  output wire [7:0] data_o
);
  prim_sync_reqack_data_w8 u (.clk_src_i(clk_src_i), .rst_src_ni(rst_src_ni), .clk_dst_i(clk_dst_i),
    .rst_dst_ni(rst_dst_ni), .req_chk_i(req_chk_i), .src_req_i(src_req_i), .src_ack_o(src_ack_o),
    .dst_req_o(dst_req_o), .dst_ack_i(dst_ack_i), .data_i(data_i), .data_o(data_o));
endmodule
""",
        [["clk_src_i"], ["clk_dst_i"]], [{"port": "rst_src_ni", "active_low": True}, {"port": "rst_dst_ni", "active_low": True}]),
    "prim_pulse_sync": ("prim_pulse_sync_bench", [CONV + "/prim_pulse_sync/prim_pulse_sync.v"],
        {"clk_src_i": 5, "clk_dst_i": 7}, """module prim_pulse_sync_bench (
  input wire clk_src_i,
  input wire rst_src_ni,
  input wire src_pulse_i,
  input wire clk_dst_i,
  input wire rst_dst_ni,
  output wire dst_pulse_o
);
  prim_pulse_sync_cfg u (.clk_src_i(clk_src_i), .rst_src_ni(rst_src_ni), .src_pulse_i(src_pulse_i),
    .clk_dst_i(clk_dst_i), .rst_dst_ni(rst_dst_ni), .dst_pulse_o(dst_pulse_o));
endmodule
""",
        [["clk_src_i"], ["clk_dst_i"]], [{"port": "rst_src_ni", "active_low": True}, {"port": "rst_dst_ni", "active_low": True}]),
    "prim_reg_cdc": ("prim_reg_cdc_bench", [CONV + "/prim_reg_cdc/prim_reg_cdc.v"],
        {"clk_src_i": 5, "clk_dst_i": 7}, """module prim_reg_cdc_bench (
  input wire clk_src_i,
  input wire rst_src_ni,
  input wire clk_dst_i,
  input wire rst_dst_ni,
  input wire src_regwen_i,
  input wire src_we_i,
  input wire src_re_i,
  input wire [7:0] src_wd_i,
  output wire src_busy_o,
  output wire [7:0] src_qs_o,
  input wire [7:0] dst_ds_i,
  input wire [7:0] dst_qs_i,
  input wire dst_update_i,
  output wire dst_we_o,
  output wire dst_re_o,
  output wire dst_regwen_o,
  output wire [7:0] dst_wd_o
);
  prim_reg_cdc_w8 u (.clk_src_i(clk_src_i), .rst_src_ni(rst_src_ni), .clk_dst_i(clk_dst_i),
    .rst_dst_ni(rst_dst_ni), .src_regwen_i(src_regwen_i), .src_we_i(src_we_i), .src_re_i(src_re_i),
    .src_wd_i(src_wd_i), .src_busy_o(src_busy_o), .src_qs_o(src_qs_o), .dst_ds_i(dst_ds_i),
    .dst_qs_i(dst_qs_i), .dst_update_i(dst_update_i), .dst_we_o(dst_we_o), .dst_re_o(dst_re_o),
    .dst_regwen_o(dst_regwen_o), .dst_wd_o(dst_wd_o));
endmodule
""",
        [["clk_src_i"], ["clk_dst_i"]], [{"port": "rst_src_ni", "active_low": True}, {"port": "rst_dst_ni", "active_low": True}]),
    "apbxclk": ("apbxclk_bench", [M + "/wb2axip/rtl/apbxclk.v"],
        {"S_APB_PCLK": 5, "M_APB_PCLK": 7}, """module apbxclk_bench (
  input wire S_APB_PCLK,
  input wire S_PRESETn,
  input wire S_APB_PSEL,
  input wire S_APB_PENABLE,
  output wire S_APB_PREADY,
  input wire [7:0] S_APB_PADDR,
  input wire S_APB_PWRITE,
  input wire [7:0] S_APB_PWDATA,
  input wire S_APB_PWSTRB,
  input wire [2:0] S_APB_PPROT,
  output wire [7:0] S_APB_PRDATA,
  output wire S_APB_PSLVERR,
  input wire M_APB_PCLK,
  output wire M_PRESETn,
  output wire M_APB_PSEL,
  output wire M_APB_PENABLE,
  input wire M_APB_PREADY,
  output wire [7:0] M_APB_PADDR,
  output wire M_APB_PWRITE,
  output wire [7:0] M_APB_PWDATA,
  output wire M_APB_PWSTRB,
  output wire [2:0] M_APB_PPROT,
  input wire [7:0] M_APB_PRDATA,
  input wire M_APB_PSLVERR
);
  apbxclk #(.C_APB_ADDR_WIDTH(8), .C_APB_DATA_WIDTH(8), .OPT_REGISTERED(1)) u (.S_APB_PCLK(S_APB_PCLK),
    .S_PRESETn(S_PRESETn), .S_APB_PSEL(S_APB_PSEL), .S_APB_PENABLE(S_APB_PENABLE), .S_APB_PREADY(S_APB_PREADY),
    .S_APB_PADDR(S_APB_PADDR), .S_APB_PWRITE(S_APB_PWRITE), .S_APB_PWDATA(S_APB_PWDATA),
    .S_APB_PWSTRB(S_APB_PWSTRB), .S_APB_PPROT(S_APB_PPROT), .S_APB_PRDATA(S_APB_PRDATA),
    .S_APB_PSLVERR(S_APB_PSLVERR), .M_APB_PCLK(M_APB_PCLK), .M_PRESETn(M_PRESETn), .M_APB_PSEL(M_APB_PSEL),
    .M_APB_PENABLE(M_APB_PENABLE), .M_APB_PREADY(M_APB_PREADY), .M_APB_PADDR(M_APB_PADDR),
    .M_APB_PWRITE(M_APB_PWRITE), .M_APB_PWDATA(M_APB_PWDATA), .M_APB_PWSTRB(M_APB_PWSTRB),
    .M_APB_PPROT(M_APB_PPROT), .M_APB_PRDATA(M_APB_PRDATA), .M_APB_PSLVERR(M_APB_PSLVERR));
endmodule
""",
        [["S_APB_PCLK"], ["M_APB_PCLK"]], [{"port": "S_PRESETn", "active_low": True}]),
    "wbxclk": ("wbxclk_bench", [M + "/wb2axip/rtl/" + f for f in ("wbxclk.v", "afifo.v")],
        {"i_wb_clk": 5, "i_xclk_clk": 7}, """module wbxclk_bench (
  input wire i_wb_clk,
  input wire i_reset,
  input wire i_wb_cyc,
  input wire i_wb_stb,
  input wire i_wb_we,
  input wire [7:0] i_wb_addr,
  input wire [7:0] i_wb_data,
  input wire i_wb_sel,
  output wire o_wb_stall,
  output wire o_wb_ack,
  output wire [7:0] o_wb_data,
  output wire o_wb_err,
  input wire i_xclk_clk,
  output wire o_xclk_cyc,
  output wire o_xclk_stb,
  output wire o_xclk_we,
  output wire [7:0] o_xclk_addr,
  output wire [7:0] o_xclk_data,
  output wire o_xclk_sel,
  input wire i_xclk_stall,
  input wire i_xclk_ack,
  input wire [7:0] i_xclk_data,
  input wire i_xclk_err
);
  wbxclk #(.AW(8), .DW(8), .LGFIFO(3)) u (.i_wb_clk(i_wb_clk), .i_reset(i_reset), .i_wb_cyc(i_wb_cyc),
    .i_wb_stb(i_wb_stb), .i_wb_we(i_wb_we), .i_wb_addr(i_wb_addr), .i_wb_data(i_wb_data), .i_wb_sel(i_wb_sel),
    .o_wb_stall(o_wb_stall), .o_wb_ack(o_wb_ack), .o_wb_data(o_wb_data), .o_wb_err(o_wb_err),
    .i_xclk_clk(i_xclk_clk), .o_xclk_cyc(o_xclk_cyc), .o_xclk_stb(o_xclk_stb), .o_xclk_we(o_xclk_we),
    .o_xclk_addr(o_xclk_addr), .o_xclk_data(o_xclk_data), .o_xclk_sel(o_xclk_sel), .i_xclk_stall(i_xclk_stall),
    .i_xclk_ack(i_xclk_ack), .i_xclk_data(i_xclk_data), .i_xclk_err(i_xclk_err));
endmodule
""",
        [["i_wb_clk"], ["i_xclk_clk"]], [{"port": "i_reset", "active_low": False}]),
    "axixclk": ("axixclk_bench", [M + "/wb2axip/rtl/" + f for f in ("axixclk.v", "afifo.v")],
        {"S_AXI_ACLK": 5, "M_AXI_ACLK": 7}, """module axixclk_bench (
  input wire S_AXI_ACLK,
  input wire S_AXI_ARESETN,
  input wire [1:0] S_AXI_AWID,
  input wire [5:0] S_AXI_AWADDR,
  input wire [7:0] S_AXI_AWLEN,
  input wire [2:0] S_AXI_AWSIZE,
  input wire [1:0] S_AXI_AWBURST,
  input wire S_AXI_AWLOCK,
  input wire [3:0] S_AXI_AWCACHE,
  input wire [2:0] S_AXI_AWPROT,
  input wire [3:0] S_AXI_AWQOS,
  input wire S_AXI_AWVALID,
  output wire S_AXI_AWREADY,
  input wire [7:0] S_AXI_WDATA,
  input wire S_AXI_WSTRB,
  input wire S_AXI_WLAST,
  input wire S_AXI_WVALID,
  output wire S_AXI_WREADY,
  output wire [1:0] S_AXI_BID,
  output wire [1:0] S_AXI_BRESP,
  output wire S_AXI_BVALID,
  input wire S_AXI_BREADY,
  input wire [1:0] S_AXI_ARID,
  input wire [5:0] S_AXI_ARADDR,
  input wire [7:0] S_AXI_ARLEN,
  input wire [2:0] S_AXI_ARSIZE,
  input wire [1:0] S_AXI_ARBURST,
  input wire S_AXI_ARLOCK,
  input wire [3:0] S_AXI_ARCACHE,
  input wire [2:0] S_AXI_ARPROT,
  input wire [3:0] S_AXI_ARQOS,
  input wire S_AXI_ARVALID,
  output wire S_AXI_ARREADY,
  output wire [1:0] S_AXI_RID,
  output wire [7:0] S_AXI_RDATA,
  output wire [1:0] S_AXI_RRESP,
  output wire S_AXI_RLAST,
  output wire S_AXI_RVALID,
  input wire S_AXI_RREADY,
  input wire M_AXI_ACLK,
  output wire M_AXI_ARESETN,
  output wire [1:0] M_AXI_AWID,
  output wire [5:0] M_AXI_AWADDR,
  output wire [7:0] M_AXI_AWLEN,
  output wire [2:0] M_AXI_AWSIZE,
  output wire [1:0] M_AXI_AWBURST,
  output wire M_AXI_AWLOCK,
  output wire [3:0] M_AXI_AWCACHE,
  output wire [2:0] M_AXI_AWPROT,
  output wire [3:0] M_AXI_AWQOS,
  output wire M_AXI_AWVALID,
  input wire M_AXI_AWREADY,
  output wire [7:0] M_AXI_WDATA,
  output wire M_AXI_WSTRB,
  output wire M_AXI_WLAST,
  output wire M_AXI_WVALID,
  input wire M_AXI_WREADY,
  input wire [1:0] M_AXI_BID,
  input wire [1:0] M_AXI_BRESP,
  input wire M_AXI_BVALID,
  output wire M_AXI_BREADY,
  output wire [1:0] M_AXI_ARID,
  output wire [5:0] M_AXI_ARADDR,
  output wire [7:0] M_AXI_ARLEN,
  output wire [2:0] M_AXI_ARSIZE,
  output wire [1:0] M_AXI_ARBURST,
  output wire M_AXI_ARLOCK,
  output wire [3:0] M_AXI_ARCACHE,
  output wire [2:0] M_AXI_ARPROT,
  output wire [3:0] M_AXI_ARQOS,
  output wire M_AXI_ARVALID,
  input wire M_AXI_ARREADY,
  input wire [1:0] M_AXI_RID,
  input wire [7:0] M_AXI_RDATA,
  input wire [1:0] M_AXI_RRESP,
  input wire M_AXI_RLAST,
  input wire M_AXI_RVALID,
  output wire M_AXI_RREADY
);
  axixclk #(.C_S_AXI_ID_WIDTH(2), .C_S_AXI_DATA_WIDTH(8), .C_S_AXI_ADDR_WIDTH(6), .LGFIFO(3)) u (
    .S_AXI_ACLK(S_AXI_ACLK), .S_AXI_ARESETN(S_AXI_ARESETN), .S_AXI_AWID(S_AXI_AWID),
    .S_AXI_AWADDR(S_AXI_AWADDR), .S_AXI_AWLEN(S_AXI_AWLEN), .S_AXI_AWSIZE(S_AXI_AWSIZE),
    .S_AXI_AWBURST(S_AXI_AWBURST), .S_AXI_AWLOCK(S_AXI_AWLOCK), .S_AXI_AWCACHE(S_AXI_AWCACHE),
    .S_AXI_AWPROT(S_AXI_AWPROT), .S_AXI_AWQOS(S_AXI_AWQOS), .S_AXI_AWVALID(S_AXI_AWVALID),
    .S_AXI_AWREADY(S_AXI_AWREADY), .S_AXI_WDATA(S_AXI_WDATA), .S_AXI_WSTRB(S_AXI_WSTRB),
    .S_AXI_WLAST(S_AXI_WLAST), .S_AXI_WVALID(S_AXI_WVALID), .S_AXI_WREADY(S_AXI_WREADY), .S_AXI_BID(S_AXI_BID),
    .S_AXI_BRESP(S_AXI_BRESP), .S_AXI_BVALID(S_AXI_BVALID), .S_AXI_BREADY(S_AXI_BREADY),
    .S_AXI_ARID(S_AXI_ARID), .S_AXI_ARADDR(S_AXI_ARADDR), .S_AXI_ARLEN(S_AXI_ARLEN),
    .S_AXI_ARSIZE(S_AXI_ARSIZE), .S_AXI_ARBURST(S_AXI_ARBURST), .S_AXI_ARLOCK(S_AXI_ARLOCK),
    .S_AXI_ARCACHE(S_AXI_ARCACHE), .S_AXI_ARPROT(S_AXI_ARPROT), .S_AXI_ARQOS(S_AXI_ARQOS),
    .S_AXI_ARVALID(S_AXI_ARVALID), .S_AXI_ARREADY(S_AXI_ARREADY), .S_AXI_RID(S_AXI_RID),
    .S_AXI_RDATA(S_AXI_RDATA), .S_AXI_RRESP(S_AXI_RRESP), .S_AXI_RLAST(S_AXI_RLAST),
    .S_AXI_RVALID(S_AXI_RVALID), .S_AXI_RREADY(S_AXI_RREADY), .M_AXI_ACLK(M_AXI_ACLK),
    .M_AXI_ARESETN(M_AXI_ARESETN), .M_AXI_AWID(M_AXI_AWID), .M_AXI_AWADDR(M_AXI_AWADDR),
    .M_AXI_AWLEN(M_AXI_AWLEN), .M_AXI_AWSIZE(M_AXI_AWSIZE), .M_AXI_AWBURST(M_AXI_AWBURST),
    .M_AXI_AWLOCK(M_AXI_AWLOCK), .M_AXI_AWCACHE(M_AXI_AWCACHE), .M_AXI_AWPROT(M_AXI_AWPROT),
    .M_AXI_AWQOS(M_AXI_AWQOS), .M_AXI_AWVALID(M_AXI_AWVALID), .M_AXI_AWREADY(M_AXI_AWREADY),
    .M_AXI_WDATA(M_AXI_WDATA), .M_AXI_WSTRB(M_AXI_WSTRB), .M_AXI_WLAST(M_AXI_WLAST),
    .M_AXI_WVALID(M_AXI_WVALID), .M_AXI_WREADY(M_AXI_WREADY), .M_AXI_BID(M_AXI_BID), .M_AXI_BRESP(M_AXI_BRESP),
    .M_AXI_BVALID(M_AXI_BVALID), .M_AXI_BREADY(M_AXI_BREADY), .M_AXI_ARID(M_AXI_ARID),
    .M_AXI_ARADDR(M_AXI_ARADDR), .M_AXI_ARLEN(M_AXI_ARLEN), .M_AXI_ARSIZE(M_AXI_ARSIZE),
    .M_AXI_ARBURST(M_AXI_ARBURST), .M_AXI_ARLOCK(M_AXI_ARLOCK), .M_AXI_ARCACHE(M_AXI_ARCACHE),
    .M_AXI_ARPROT(M_AXI_ARPROT), .M_AXI_ARQOS(M_AXI_ARQOS), .M_AXI_ARVALID(M_AXI_ARVALID),
    .M_AXI_ARREADY(M_AXI_ARREADY), .M_AXI_RID(M_AXI_RID), .M_AXI_RDATA(M_AXI_RDATA), .M_AXI_RRESP(M_AXI_RRESP),
    .M_AXI_RLAST(M_AXI_RLAST), .M_AXI_RVALID(M_AXI_RVALID), .M_AXI_RREADY(M_AXI_RREADY));
endmodule
""",
        [["S_AXI_ACLK"], ["M_AXI_ACLK"]], [{"port": "S_AXI_ARESETN", "active_low": True}]),

}


def sdc_text(periods, groups, uncertainty=0.0, io_clock=None):
    t = ["create_clock -name %s -period %.4f [get_ports %s]" % (c, p, c) for c, p in periods.items()]
    if io_clock:
        # Dr. RTL constrains input->output paths to one period (set_max_delay 0.1); zero I/O delays
        # against the clock do the same and keep those paths in the clock's domain
        t.append("set_input_delay 0 -clock %s [delete_from_list [all_inputs] [get_ports %s]]" % (io_clock, io_clock))
        t.append("set_output_delay 0 -clock %s [all_outputs]" % io_clock)
    if len(groups) > 1:
        t.append("set_clock_groups -asynchronous " + " ".join("-group {%s}" % " ".join(g) for g in groups))
    if uncertainty:
        t.append("set_clock_uncertainty %.3f [all_clocks]" % uncertainty)
    return "\n".join(t) + "\n"


def write_design(name, top, files, periods, wrapper, groups, resets, margin=0.05, extra=None, io_clock=None):
    d = os.path.join(ROOT, "flow", "designs", name)
    rd = os.path.join(d, "rtl")
    shutil.rmtree(rd, ignore_errors=True)
    os.makedirs(rd)
    rtl = []
    for f in files:
        shutil.copy(f, rd)
        rtl.append(os.path.relpath(os.path.join(rd, os.path.basename(f)), ROOT))
    if wrapper:
        open(os.path.join(rd, "bench_top.v"), "w").write(wrapper)
        rtl.append(os.path.relpath(os.path.join(rd, "bench_top.v"), ROOT))
    open(os.path.join(d, name + ".sdc"), "w").write(sdc_text(periods, groups, io_clock=io_clock))
    cfg = {"top": top, "rtl": rtl, "sdc": os.path.relpath(os.path.join(d, name + ".sdc"), ROOT), "liberty": LIB,
           "annotations": None, "weights": None, "margin": margin, "budget": 10, "rho": 0.8, "dispatch": 3,
           "theta": 0.5, "phi": 32, "smax": 80, "n_max": 5, "groups": groups}
    if resets:
        cfg["resets"] = resets
    cfg.update(extra or {})
    json.dump(cfg, open(os.path.join(d, "design.json"), "w"), indent=1)
    return d


def _periods(sdc):
    out = {}
    for line in open(sdc):
        mm = re.match(r"create_clock -name (\S+) -period (\S+)", line)
        if mm:
            out[mm.group(1)] = float(mm.group(2))
    return out


def calibrate(name, ratio=0.75, timing=True, relax=None):
    """Relaxed STA -> per-clock critical delay -> period = ratio x delay (rounded to 10 ps)."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from aegis_common import load_design, which
    D = load_design(name)
    if relax:   # start from relaxed periods so the measured delay is the critical-path delay
        cfg = json.load(open(os.path.join(ROOT, "flow", "designs", name, "design.json")))
        open(D["sdc"], "w").write(sdc_text(relax, cfg["groups"]))
    out = os.path.join(ROOT, "flow", "work", name, "calib")
    sta = which("sta", ["~/karuppu/.tools/OpenSTA/build/sta"])
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "aegis_sta.py"), "--rtl"] + D["rtl"] +
                       ["--top", D["top"], "--sdc", D["sdc"], "--liberty", D["liberty"], "--out", out, "--margin", "0",
                        "--sta", sta] + (["--abc-delay-ps", str(int(1000 * min(_periods(D["sdc"]).values()))), "--abc-timing"]
                                         if timing else []), capture_output=True, text=True)
    if r.returncode != 0:
        print("calibration STA failed for", name, (r.stderr or r.stdout)[-800:])
        return None
    m = json.load(open(os.path.join(out, "metrics.json")))
    periods = {}
    for line in open(D["sdc"]):
        mm = re.match(r"create_clock -name (\S+) -period (\S+)", line)
        if mm:
            periods[mm.group(1)] = float(mm.group(2))
    new = {}
    for p in m["per_domain"]:
        c = p["clock"]
        if c in periods and p["wns_ns"] is not None:
            delay = periods[c] - p["wns_ns"]
            new[c] = max(0.05, round(ratio * delay, 2))
    for c in periods:
        new.setdefault(c, periods[c])
    open(D["sdc"], "w").write(sdc_text(new, json.load(open(os.path.join(ROOT, "flow", "designs", name, "design.json")))["groups"]))
    cfgp = os.path.join(ROOT, "flow", "designs", name, "design.json")
    cfg = json.load(open(cfgp))
    cfg["abc_delay_ps"] = int(round(1000 * min(new.values())))
    json.dump(cfg, open(cfgp, "w"), indent=1)
    return new


DRRTL_CFG = os.path.join(BENCH, "Dr_RTL", "syn_flow", "design_all.json")


def drrtl_designs():
    cfg = json.load(open(DRRTL_CFG))
    files = {re.sub(r"\.v0\.s?v$", "", f): os.path.join(BENCH, "Dr_RTL", "rtl_dataset", f)
             for f in os.listdir(os.path.join(BENCH, "Dr_RTL", "rtl_dataset"))}
    out = {}
    for name, (top, clk, rst, ext) in cfg.items():
        if name in files:
            out["drrtl_" + name.lower()] = (top, [files[name]], clk, rst)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="all")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--ratio", type=float, default=0.75)
    ap.add_argument("--only", nargs="*", help="set up only these designs (others are left untouched)")
    a = ap.parse_args()
    if a.suite in ("cdc", "all"):
        for name, (top, files, periods, wrapper, groups, resets) in CDC.items():
            if a.only and name not in a.only:
                continue
            write_design(name, top, files, periods, wrapper, groups, resets)
            new = calibrate(name, a.ratio) if a.calibrate else periods
            print("cdc  %-18s top=%-24s clocks=%s" % (name, top, new))
    if a.suite in ("drrtl", "all"):
        for name, (top, files, clk, rst) in drrtl_designs().items():
            if a.only and name not in a.only:
                continue
            write_design(name, top, files, {clk: 0.1}, None, [[clk]],
                         [{"port": rst, "active_low": bool(re.search(r"(_n|n)$", rst)) or rst in ("nReset",)}],
                         margin=0.0, extra={"suite": "drrtl", "abc_delay_ps": 100}, io_clock=clk)
            print("dr   %-22s top=%-28s clk=%s" % (name, top, clk))


if __name__ == "__main__":
    main()
