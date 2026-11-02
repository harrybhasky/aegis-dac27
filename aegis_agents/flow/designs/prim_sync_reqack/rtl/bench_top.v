module prim_sync_reqack_bench (
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
