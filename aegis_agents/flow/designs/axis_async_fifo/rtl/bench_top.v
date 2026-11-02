module axis_async_fifo_bench (
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
