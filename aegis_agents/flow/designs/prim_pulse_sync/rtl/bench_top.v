module prim_pulse_sync_bench (
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
