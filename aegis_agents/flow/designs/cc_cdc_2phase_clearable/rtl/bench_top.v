module cc_cdc_2phase_clearable_bench (
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
