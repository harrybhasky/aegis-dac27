module eth_mac_1g_fifo_bench (
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
