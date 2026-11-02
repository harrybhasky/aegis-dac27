module cc_cdc_reset_ctrlr_bench (
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
