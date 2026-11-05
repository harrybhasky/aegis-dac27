`ifndef VERILATOR
module testbench;
  reg [4095:0] vcdfile;
  reg clock;
`else
module testbench(input clock, output reg genclock);
  initial genclock = 1;
`endif
  reg genclock = 1;
  reg [31:0] cycle = 0;
  reg [0:0] PI_s_pause_req;
  reg [0:0] PI_m_rst;
  reg [0:0] PI_s_axis_tuser;
  reg [7:0] PI_s_axis_tdest;
  reg [0:0] PI_s_axis_tkeep;
  reg [0:0] PI_m_clk;
  reg [0:0] PI_m_pause_req;
  reg [7:0] PI_s_axis_tid;
  reg [0:0] PI_m_axis_tready;
  reg [0:0] PI_s_clk;
  reg [0:0] PI_s_axis_tlast;
  reg [0:0] PI_s_axis_tvalid;
  reg [7:0] PI_s_axis_tdata;
  reg [0:0] PI_s_rst;
  aegis_formal_top UUT (
    .s_pause_req(PI_s_pause_req),
    .m_rst(PI_m_rst),
    .s_axis_tuser(PI_s_axis_tuser),
    .s_axis_tdest(PI_s_axis_tdest),
    .s_axis_tkeep(PI_s_axis_tkeep),
    .m_clk(PI_m_clk),
    .m_pause_req(PI_m_pause_req),
    .s_axis_tid(PI_s_axis_tid),
    .m_axis_tready(PI_m_axis_tready),
    .s_clk(PI_s_clk),
    .s_axis_tlast(PI_s_axis_tlast),
    .s_axis_tvalid(PI_s_axis_tvalid),
    .s_axis_tdata(PI_s_axis_tdata),
    .s_rst(PI_s_rst)
  );
`ifndef VERILATOR
  initial begin
    if ($value$plusargs("vcd=%s", vcdfile)) begin
      $dumpfile(vcdfile);
      $dumpvars(0, testbench);
    end
    #5 clock = 0;
    while (genclock) begin
      #5 clock = 0;
      #5 clock = 1;
    end
  end
`endif
  initial begin
`ifndef VERILATOR
    #1;
`endif
    UUT.aegis_init = 1'b1;
    UUT.chk.f_ok = 8'b00000000;
    UUT.chk.past_ptr = 6'b000000;
    // UUT.dut.$auto$async2sync.\cc:253:execute$554  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:253:execute$556  = 1'b1;
    UUT.dut.drop_frame_reg = 1'b0;
    UUT.dut.\m_axis_pipe_reg[0]  = 10'b0000000000;
    UUT.dut.\m_axis_pipe_reg[1]  = 10'b0000000001;
    UUT.dut.m_axis_tvalid_pipe_reg = 2'b00;
    UUT.dut.m_drop_frame_reg = 1'b0;
    UUT.dut.m_frame_reg = 1'b0;
    UUT.dut.m_rst_sync2_reg = 1'b1;
    UUT.dut.m_rst_sync3_reg = 1'b1;
    UUT.dut.m_terminate_frame_reg = 1'b0;
    UUT.dut.mark_frame_reg = 1'b0;
    UUT.dut.rd_ptr_gray_reg = 6'b000000;
    UUT.dut.rd_ptr_gray_sync1_reg = 6'b000000;
    UUT.dut.rd_ptr_gray_sync2_reg = 6'b000000;
    UUT.dut.rd_ptr_reg = 6'b000000;
    UUT.dut.s_frame_reg = 1'b0;
    UUT.dut.s_rst_sync2_reg = 1'b1;
    UUT.dut.s_rst_sync3_reg = 1'b1;
    UUT.dut.wr_ptr_commit_reg = 6'b000000;
    UUT.dut.wr_ptr_commit_sync_reg = 6'b000000;
    UUT.dut.wr_ptr_gray_reg = 6'b000000;
    UUT.dut.wr_ptr_reg = 6'b000000;
    UUT.dut.wr_ptr_sync_commit_reg = 6'b000000;
    UUT.dut.wr_ptr_update_ack_sync1_reg = 1'b0;
    UUT.dut.wr_ptr_update_ack_sync2_reg = 1'b0;
    UUT.dut.wr_ptr_update_reg = 1'b0;
    UUT.dut.wr_ptr_update_sync1_reg = 1'b0;
    UUT.dut.wr_ptr_update_sync2_reg = 1'b0;
    UUT.dut.wr_ptr_update_sync3_reg = 1'b0;
    UUT.dut.wr_ptr_update_valid_reg = 1'b0;
    UUT.dut.mem[5'b00000] = 10'b0000000001;

    // state 0
    PI_s_pause_req = 1'b0;
    PI_m_rst = 1'b1;
    PI_s_axis_tuser = 1'b1;
    PI_s_axis_tdest = 8'b00000000;
    PI_s_axis_tkeep = 1'b0;
    PI_m_clk = 1'b0;
    PI_m_pause_req = 1'b0;
    PI_s_axis_tid = 8'b00000000;
    PI_m_axis_tready = 1'b0;
    PI_s_clk = 1'b0;
    PI_s_axis_tlast = 1'b1;
    PI_s_axis_tvalid = 1'b0;
    PI_s_axis_tdata = 8'b00000000;
    PI_s_rst = 1'b1;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b1;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b1;
      PI_s_axis_tvalid <= 1'b0;
      PI_s_axis_tdata <= 8'b00000000;
      PI_s_rst <= 1'b0;
    end

    // state 2
    if (cycle == 1) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b1;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b1;
      PI_s_axis_tvalid <= 1'b0;
      PI_s_axis_tdata <= 8'b00000000;
      PI_s_rst <= 1'b0;
    end

    // state 3
    if (cycle == 2) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b1;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b1;
      PI_s_axis_tvalid <= 1'b0;
      PI_s_axis_tdata <= 8'b01100001;
      PI_s_rst <= 1'b0;
    end

    // state 4
    if (cycle == 3) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b0;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b0;
      PI_s_axis_tvalid <= 1'b1;
      PI_s_axis_tdata <= 8'b00000000;
      PI_s_rst <= 1'b0;
    end

    // state 5
    if (cycle == 4) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b1;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b0;
      PI_s_axis_tvalid <= 1'b1;
      PI_s_axis_tdata <= 8'b01100000;
      PI_s_rst <= 1'b0;
    end

    // state 6
    if (cycle == 5) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b1;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b1;
      PI_s_axis_tvalid <= 1'b1;
      PI_s_axis_tdata <= 8'b00000000;
      PI_s_rst <= 1'b0;
    end

    // state 7
    if (cycle == 6) begin
      PI_s_pause_req <= 1'b0;
      PI_m_rst <= 1'b0;
      PI_s_axis_tuser <= 1'b0;
      PI_s_axis_tdest <= 8'b00000000;
      PI_s_axis_tkeep <= 1'b0;
      PI_m_clk <= 1'b0;
      PI_m_pause_req <= 1'b0;
      PI_s_axis_tid <= 8'b00000000;
      PI_m_axis_tready <= 1'b0;
      PI_s_clk <= 1'b0;
      PI_s_axis_tlast <= 1'b0;
      PI_s_axis_tvalid <= 1'b0;
      PI_s_axis_tdata <= 8'b00000000;
      PI_s_rst <= 1'b0;
    end

    genclock <= cycle < 7;
    cycle <= cycle + 1;
  end
endmodule
