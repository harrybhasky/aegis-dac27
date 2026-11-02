module prim_reg_cdc_bench (
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
