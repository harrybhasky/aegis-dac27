module prim_fifo_async_bench (
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
