// Test SoC for AEGIS Phase 1: async FIFO, handshake, pulse sync, divider, bad crossing.
module sync2 #(parameter W = 1) (input clk, input rst_n, input [W-1:0] d, output [W-1:0] q);
  (* ASYNC_REG = "TRUE" *) reg [W-1:0] s1;
  (* ASYNC_REG = "TRUE" *) reg [W-1:0] s2;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin s1 <= {W{1'b0}}; s2 <= {W{1'b0}}; end
    else        begin s1 <= d;         s2 <= s1;         end
  assign q = s2;
endmodule

module wptr_full #(parameter AW = 3) (input wclk, input wrst_n, input winc, input [AW:0] wq2_rptr,
                                       output reg [AW:0] wptr, output reg wfull, output [AW-1:0] waddr);
  reg  [AW:0] wbin;
  wire [AW:0] wbin_next  = wbin + {{AW{1'b0}}, (winc & ~wfull)};
  wire [AW:0] wgray_next = (wbin_next >> 1) ^ wbin_next;
  wire        wfull_next = (wgray_next == {~wq2_rptr[AW:AW-1], wq2_rptr[AW-2:0]});
  assign waddr = wbin[AW-1:0];
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wptr <= 0; wfull <= 1'b0; end
    else begin wbin <= wbin_next; wptr <= wgray_next; wfull <= wfull_next; end
endmodule

module rptr_empty #(parameter AW = 3) (input rclk, input rrst_n, input rinc, input [AW:0] rq2_wptr,
                                        output reg [AW:0] rptr, output reg rempty, output [AW-1:0] raddr);
  reg  [AW:0] rbin;
  wire [AW:0] rbin_next  = rbin + {{AW{1'b0}}, (rinc & ~rempty)};
  wire [AW:0] rgray_next = (rbin_next >> 1) ^ rbin_next;
  wire        rempty_next = (rgray_next == rq2_wptr);
  assign raddr = rbin[AW-1:0];
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rptr <= 0; rempty <= 1'b1; end
    else begin rbin <= rbin_next; rptr <= rgray_next; rempty <= rempty_next; end
endmodule

module fifomem #(parameter DW = 8, parameter AW = 3) (input wclk, input wen, input [AW-1:0] waddr, input [AW-1:0] raddr,
                                                     input [DW-1:0] wdata, output [DW-1:0] rdata);
  reg [DW-1:0] mem [0:(1<<AW)-1];
  always @(posedge wclk) if (wen) mem[waddr] <= wdata;
  assign rdata = mem[raddr];
endmodule

module hs_src (input clk, input rst_n, input send, input [7:0] din, input ack_sync,
               output reg req, output reg [7:0] data);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)                          begin req <= 1'b0; data <= 8'd0; end
    else if (!req && !ack_sync && send)  begin data <= din; req <= 1'b1; end
    else if (req && ack_sync)            req <= 1'b0;
endmodule

module hs_dst (input clk, input rst_n, input req_sync, input [7:0] data_in,
               output reg ack, output reg [7:0] dout);
  reg req_d;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin req_d <= 1'b0; ack <= 1'b0; dout <= 8'd0; end
    else begin
      req_d <= req_sync;
      if (req_sync && !req_d) begin dout <= data_in; ack <= 1'b1; end
      else if (!req_sync)     ack <= 1'b0;
    end
endmodule

module clkdiv (input clk, input rst_n, output clk_out);
  reg div_q;
  always @(posedge clk or negedge rst_n) if (!rst_n) div_q <= 1'b0; else div_q <= ~div_q;
  assign clk_out = div_q;
endmodule

module soc (input clk_w, input clk_r, input clk_x, input rst_n,
            input winc, input rinc, input [7:0] wdata, input send, input [7:0] din, input pulse,
            output [7:0] rdata, output wfull, output rempty, output [7:0] hs_out, output reg pulse_seen,
            output reg [7:0] slow_q, output reg bad_q, output reg [7:0] aux_q);
  localparam AW = 3;
  wire [AW:0] wptr, rptr, wq2_rptr, rq2_wptr;
  wire [AW-1:0] waddr, raddr;
  wptr_full  #(.AW(AW)) u_wptr (.wclk(clk_w), .wrst_n(rst_n), .winc(winc), .wq2_rptr(wq2_rptr), .wptr(wptr), .wfull(wfull), .waddr(waddr));
  rptr_empty #(.AW(AW)) u_rptr (.rclk(clk_r), .rrst_n(rst_n), .rinc(rinc), .rq2_wptr(rq2_wptr), .rptr(rptr), .rempty(rempty), .raddr(raddr));
  sync2 #(.W(AW+1)) u_s_w2r (.clk(clk_r), .rst_n(rst_n), .d(wptr), .q(rq2_wptr));
  sync2 #(.W(AW+1)) u_s_r2w (.clk(clk_w), .rst_n(rst_n), .d(rptr), .q(wq2_rptr));
  fifomem #(.DW(8), .AW(AW)) u_mem (.wclk(clk_w), .wen(winc & ~wfull), .waddr(waddr), .raddr(raddr), .wdata(wdata), .rdata(rdata));

  wire req, ack, req_sync, ack_sync; wire [7:0] hs_data;
  hs_src u_hs_src (.clk(clk_w), .rst_n(rst_n), .send(send), .din(din), .ack_sync(ack_sync), .req(req), .data(hs_data));
  sync2  u_s_req  (.clk(clk_r), .rst_n(rst_n), .d(req), .q(req_sync));
  sync2  u_s_ack  (.clk(clk_w), .rst_n(rst_n), .d(ack), .q(ack_sync));
  hs_dst u_hs_dst (.clk(clk_r), .rst_n(rst_n), .req_sync(req_sync), .data_in(hs_data), .ack(ack), .dout(hs_out));

  reg tgl; wire tgl_sync; reg tgl_d;
  always @(posedge clk_w or negedge rst_n) if (!rst_n) tgl <= 1'b0; else if (pulse) tgl <= ~tgl;
  sync2 u_s_tgl (.clk(clk_r), .rst_n(rst_n), .d(tgl), .q(tgl_sync));
  always @(posedge clk_r or negedge rst_n)
    if (!rst_n) begin tgl_d <= 1'b0; pulse_seen <= 1'b0; end
    else begin tgl_d <= tgl_sync; pulse_seen <= tgl_sync ^ tgl_d; end

  wire clk_div;
  clkdiv u_div (.clk(clk_w), .rst_n(rst_n), .clk_out(clk_div));
  reg [7:0] fast_q;
  always @(posedge clk_w or negedge rst_n) if (!rst_n) fast_q <= 8'd0; else fast_q <= wdata + din;
  always @(posedge clk_div or negedge rst_n) if (!rst_n) slow_q <= 8'd0; else slow_q <= fast_q ^ din;

  // deliberately unsynchronized crossing: wfull (clk_w) used directly in clk_r
  always @(posedge clk_r or negedge rst_n) if (!rst_n) bad_q <= 1'b0; else bad_q <= wfull & rinc;
  // third clock with no SDC exception towards clk_w
  always @(posedge clk_x or negedge rst_n) if (!rst_n) aux_q <= 8'd0; else aux_q <= fast_q + 8'd1;
endmodule
