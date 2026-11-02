---
name: rtl-opt
description: Critical path patterns with corresponding optimization strategies. Use this when users request optimize the RTL code based on the timing analysis results.
license: Complete terms in LICENSE.txt
---



This file organizes the skills into **High-confidence**, **Medium-confidence**, **Low-confidence**, and **Do not use**. Each skill is written in the format:

`<pattern, strategy, example>`

For every example, both **before** and **after** Verilog snippets are included.

**Entry IDs are stable.** Entries 1–47 are the original seed library. Entries 48 onward (including the CDC contract-bound section, 61–64) were added in this revision; each new entry carries **Source**, **AEGIS notes**, and **Verified** fields. New entries start in Medium-confidence or Do not use and should move up only after the Librarian has observed them succeed.

**AEGIS rules that override any entry below:**

- Never edit immutable-tier logic (synchronizer chains, reset synchronizers, launch flops of crossings, `ASYNC_REG`/keep attributes, clock dividers, clock gating, clock muxes, capacity parameters). Contract-bound logic may be edited, but its CDC contracts are re-proven.
- Never change cycle latency. Any rewrite labeled *sequential-unsafe* is skipped; entries 12, 34, 37, 38, and 53 are therefore in Do not use.
- Every new entry's before/after example must be proven equivalent before it is added (see the changelog).

---

## High-confidence

### 1. `<repeated comparisons / repeated control checks, pre-compute shared condition wires and reuse them, example>`
- **Pattern**: repeated `(state == X)`, `(cmd == Y)`, `(count == Z)` or repeated shared condition fragments across branches.
- **Strategy**: extract named wires once, then reuse them in `always` / `assign` logic. Very safe and consistently effective for FSM decode, counters, and control fanout.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    if (state == IDLE && cmd == START)
      next_state = START;
    else if (state == IDLE && cmd == STOP)
      next_state = STOP;
    else
      next_state = state;
  end

  // AFTER
  wire state_is_idle = (state == IDLE);
  wire cmd_is_start  = (cmd == START);
  wire cmd_is_stop   = (cmd == STOP);
  wire go_start      = state_is_idle & cmd_is_start;
  wire go_stop       = state_is_idle & cmd_is_stop;

  always @(*) begin
    if (go_start)
      next_state = START;
    else if (go_stop)
      next_state = STOP;
    else
      next_state = state;
  end
  ```

### 2. `<shared sub-conditions reused in multiple branches, build hierarchical shared condition wires before final checks, example>`
- **Pattern**: multiple branches share a common prefix such as `state == DATA && sck == HIGH`.
- **Strategy**: factor the shared prefix into one wire, then attach the remaining branch-local tests.
- **Example**:
  ```verilog
  // BEFORE
  assign fire_done  = (state == DATA) && (sck == HIGH) && (count == MAX);
  assign fire_shift = (state == DATA) && (sck == HIGH) && (count > THRESH);

  // AFTER
  wire state_is_data = (state == DATA);
  wire sck_is_high   = (sck == HIGH);
  wire data_and_sck  = state_is_data & sck_is_high;
  wire count_is_max  = (count == MAX);
  wire count_is_gt   = (count > THRESH);

  assign fire_done  = data_and_sck & count_is_max;
  assign fire_shift = data_and_sck & count_is_gt;
  ```

### 3. `<FSM / opcode / instruction decode used in many places, one-hot pre-decode encoded values before downstream logic, example>`
- **Pattern**: FSM-heavy control, instruction decoders, opcode/state checks fanning out widely.
- **Strategy**: generate one-hot-style boolean decode signals such as `state_is_*` / `op_is_*`, then use them directly.
- **Example**:
  ```verilog
  // BEFORE
  assign do_add = (opcode == 4'b0001) && valid;
  assign do_sub = (opcode == 4'b0010) && valid;
  assign do_and = (opcode == 4'b0011) && valid;

  // AFTER
  wire op_is_add = (opcode == 4'b0001);
  wire op_is_sub = (opcode == 4'b0010);
  wire op_is_and = (opcode == 4'b0011);

  assign do_add = op_is_add & valid;
  assign do_sub = op_is_sub & valid;
  assign do_and = op_is_and & valid;
  ```

### 4. `<one-hot or bit-encoded state with direct bit meaning, replace full equality with direct bit indexing, example>`
- **Pattern**: one-hot state or representation where a specific bit directly denotes the condition.
- **Strategy**: replace a full equality comparator with direct bit access when encoding guarantees equivalence.
- **Example**:
  ```verilog
  // BEFORE
  wire is_state_5 = (State == 6'b100000);

  // AFTER
  wire is_state_5 = State[5];
  ```

### 5. `<repeated arithmetic / repeated partial products / repeated shared expressions, common subexpression elimination to a named wire, example>`
- **Pattern**: same add/mul/compare subtree appears in multiple outputs or branches.
- **Strategy**: compute once and reuse everywhere.
- **Example**:
  ```verilog
  // BEFORE
  assign out_a = (x + y) + z;
  assign out_b = (x + y) + w;

  // AFTER
  wire [W-1:0] xy_sum = x + y;
  assign out_a = xy_sum + z;
  assign out_b = xy_sum + w;
  ```

### 6. `<shared arithmetic across module instances, hoist common subexpression upward and fan out result, example>`
- **Pattern**: identical intermediate arithmetic is recomputed in sibling instances or branches.
- **Strategy**: move the common computation to the parent or earlier stage and distribute the shared result.
- **Example**:
  ```verilog
  // BEFORE
  child0 u0(.prod_in(a * b), .c(c0));
  child1 u1(.prod_in(a * b), .c(c1));

  // AFTER
  wire [W-1:0] shared_mul = a * b;
  child0 u0(.prod_in(shared_mul), .c(c0));
  child1 u1(.prod_in(shared_mul), .c(c1));
  ```

### 7. `<high-fanout control or registered signals, duplicate register/signal copies and split fanout cones, example>`
- **Pattern**: reset/enable/state-derived signals with many loads.
- **Strategy**: create duplicated copies, ideally aligned with consumer cones.
- **AEGIS notes**: synthesis can merge identical registers back together (Yosys `opt_merge` does this for identical cells), so mark the copies `(* keep *)` and confirm in the post-synthesis netlist that they survived. Much of the benefit is in routing delay, which post-synthesis STA does not model, so the gain may only appear after placement. Never apply this to synchronizer flops (entry 60).
- **Example**:
  ```verilog
  // BEFORE
  reg en;
  always @(posedge clk) en <= en_next;
  // en drives many distant loads

  // AFTER
  reg en_a, en_b;
  always @(posedge clk) begin
    en_a <= en_next;
    en_b <= en_next;
  end
  // split loads between en_a and en_b
  ```

### 8. `<high-fanout combinational condition wire, replicate equivalent local wires for separate consumers, example>`
- **Pattern**: a decoded combinational signal drives many separate cones.
- **Strategy**: replicate equivalent combinational wires so synthesis can localize logic and reduce loading.
- **AEGIS notes**: identical combinational logic is normally merged by synthesis, so this usually has no effect unless the copies are kept. Check the post-synthesis netlist before crediting a gain to it.
- **Example**:
  ```verilog
  // BEFORE
  wire state_is_data = (state == DATA);
  assign cnt_en   = state_is_data & cnt_req;
  assign out_en   = state_is_data & out_req;
  assign flag_set = state_is_data & flag_req;

  // AFTER
  wire state_is_data_cnt  = (state == DATA);
  wire state_is_data_out  = (state == DATA);
  wire state_is_data_flag = (state == DATA);

  assign cnt_en   = state_is_data_cnt  & cnt_req;
  assign out_en   = state_is_data_out  & out_req;
  assign flag_set = state_is_data_flag & flag_req;
  ```

### 9. `<wide adder / deep carry chain, carry-select style split into blocks, example>`
- **Pattern**: ripple-carry dominated arithmetic path, especially wide adders.
- **Strategy**: split into blocks, precompute upper block for carry-in 0/1, then select.
- **Revision note**: the previous example indexed an expression (`(...)[16]`), which is not legal Verilog. The corrected example below is proven equivalent to `a + b` with SymbiYosys.
- **Example**:
  ```verilog
  // BEFORE
  wire [31:0] sum = a + b;

  // AFTER
  wire [16:0] lo        = {1'b0, a[15:0]} + {1'b0, b[15:0]};
  wire [15:0] sum_lo    = lo[15:0];
  wire        carry_lo  = lo[16];
  wire [15:0] sum_hi_c0 = a[31:16] + b[31:16];
  wire [15:0] sum_hi_c1 = a[31:16] + b[31:16] + 16'd1;
  wire [15:0] sum_hi    = carry_lo ? sum_hi_c1 : sum_hi_c0;
  wire [31:0] sum       = {sum_hi, sum_lo};
  ```

### 10. `<counter decrement / borrow chain with predictable structure, pre-compute borrow or lookahead-style signals, example>`
- **Pattern**: decrement or borrow propagation dominates delay.
- **Strategy**: use carry-lookahead / borrow-lookahead style restructuring rather than serial borrow propagation.
- **Example**:
  ```verilog
  // BEFORE
  wire [3:0] dec = a - 4'd1;

  // AFTER
  wire b0 = ~a[0];
  wire b1 = b0 & ~a[1];
  wire b2 = b1 & ~a[2];
  wire [3:0] dec;
  assign dec[0] = ~a[0];
  assign dec[1] = a[1] ^ b0;
  assign dec[2] = a[2] ^ b1;
  assign dec[3] = a[3] ^ b2;
  ```

### 11. `<simple compare against power-of-two threshold / one-hot boundary, simplify wide comparison into bit-select or MSB check, example>`
- **Pattern**: checks like `count >= 32`, direct one-hot state recognition, fixed-point truncation by shift.
- **Strategy**: replace full comparator or arithmetic shift with direct bit inspection / slicing when semantics are guaranteed.
- **Example**:
  ```verilog
  // BEFORE
  wire limit_reached = (data_count >= 6'd32);
  wire [15:0] trunc = full_result >>> 8;

  // AFTER
  wire limit_reached = data_count[5];
  wire [15:0] trunc = full_result[23:8];
  ```

---

## Medium-confidence

### 13. `<nested ternary / nested mux / branch-dependent data path, compute candidate branch values in parallel and select late, example>`
- **Pattern**: `sel1 ? (sel2 ? a : b) : (sel2 ? c : d)` and similar nested selection structures.
- **Strategy**: precompute branch values unconditionally, then use one late select.
- **Example**:
  ```verilog
  // BEFORE
  assign out = sel1 ? (sel2 ? a : b) : (sel2 ? c : d);

  // AFTER
  wire [W-1:0] r_a = a;
  wire [W-1:0] r_b = b;
  wire [W-1:0] r_c = c;
  wire [W-1:0] r_d = d;
  assign out = sel1 ? (sel2 ? r_a : r_b) : (sel2 ? r_c : r_d);
  ```

### 14. `<arithmetic gated by control, compute both arithmetic branches and mux result at the end, example>`
- **Pattern**: `full ? ptr : ptr + 1`, `en ? a+b : c+d`, branch-local arithmetic mixed with control.
- **Strategy**: move control after arithmetic so arithmetic can proceed in parallel.
- **Example**:
  ```verilog
  // BEFORE
  assign ptr_n = full ? ptr : (ptr + 1'b1);

  // AFTER
  wire [W-1:0] ptr_hold = ptr;
  wire [W-1:0] ptr_inc  = ptr + 1'b1;
  assign ptr_n = full ? ptr_hold : ptr_inc;
  ```

### 15. `<sel ? (A+B) : (C+D) style arithmetic mux, move muxes before adder when equivalence is clear, example>`
- **Pattern**: a final mux chooses between two arithmetic sums/products that share structure.
- **Strategy**: restructure to `(sel?A:C) + (sel?B:D)` to reduce adder count/depth.
- **AEGIS notes**: this saves an adder but puts the select mux in front of it. Use it when the operands arrive late and `sel` is early; when `sel` is the late signal, use entry 52 (the inverse).
- **Example**:
  ```verilog
  // BEFORE
  assign out = sel ? (A + B) : (C + D);

  // AFTER
  wire [W-1:0] x = sel ? A : C;
  wire [W-1:0] y = sel ? B : D;
  assign out = x + y;
  ```

### 16. `<deep if-else / default-then-override control chain, flatten into explicit parallel conditions with single-level selection, example>`
- **Pattern**: long control ladders where priority is known and preserved explicitly.
- **Strategy**: build mutually exclusive select wires and use a flat selection structure.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    out = v0;
    if (cond1)
      out = v1;
    else if (cond2)
      out = v2;
    else if (cond3)
      out = v3;
  end

  // AFTER
  wire sel1 = cond1;
  wire sel2 = !cond1 & cond2;
  wire sel3 = !cond1 & !cond2 & cond3;
  assign out = sel1 ? v1 : sel2 ? v2 : sel3 ? v3 : v0;
  ```

### 17. `<large case statement with structured outputs, replace with direct AND-OR equations or flattened decode logic, example>`
- **Pattern**: case branches map encoded states/opcodes to simple output patterns.
- **Strategy**: convert case decode into predecoded booleans feeding direct equations.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    case (state)
      IDLE:  next = START;
      START: next = DATA;
      DATA:  next = STOP;
      STOP:  next = IDLE;
    endcase
  end

  // AFTER
  wire state_is_idle  = (state == IDLE);
  wire state_is_start = (state == START);
  wire state_is_data  = (state == DATA);
  wire state_is_stop  = (state == STOP);

  assign next[0] = state_is_idle | state_is_data;
  assign next[1] = state_is_start | state_is_data;
  ```

### 18. `<wide OR/AND/XOR reduction, restructure linear logic into balanced tree, example>`
- **Pattern**: long reduction chains or unbalanced boolean logic depth.
- **Strategy**: group terms into a binary or hierarchical tree to reduce depth.
- **Example**:
  ```verilog
  // BEFORE
  wire any_set = a | b | c | d | e | f | g | h;

  // AFTER
  wire or01 = a | b;
  wire or23 = c | d;
  wire or45 = e | f;
  wire or67 = g | h;
  wire or0123 = or01 | or23;
  wire or4567 = or45 | or67;
  wire any_set = or0123 | or4567;
  ```

### 19. `<wide mux tree or wide selection network, rebalance into multi-level 2:1 tree, example>`
- **Pattern**: flat or poorly structured 8:1 / 16:1 mux logic.
- **Strategy**: implement an explicit balanced selection tree.
- **Example**:
  ```verilog
  // BEFORE
  assign out = sel[2] ? (sel[1] ? (sel[0] ? d7 : d6) : (sel[0] ? d5 : d4)) :
                       (sel[1] ? (sel[0] ? d3 : d2) : (sel[0] ? d1 : d0));

  // AFTER
  wire l10 = sel[0] ? d1 : d0;
  wire l11 = sel[0] ? d3 : d2;
  wire l12 = sel[0] ? d5 : d4;
  wire l13 = sel[0] ? d7 : d6;
  wire l20 = sel[1] ? l11 : l10;
  wire l21 = sel[1] ? l13 : l12;
  assign out = sel[2] ? l21 : l20;
  ```

### 20. `<multi-operand addition, rebalance serial add chain into tree, example>`
- **Pattern**: `a+b+c+d` in a long arithmetic chain.
- **Strategy**: split into pairwise adds then final combine.
- **Example**:
  ```verilog
  // BEFORE
  wire [31:0] sum = a + b + c + d;

  // AFTER
  wire [31:0] sum_ab = a + b;
  wire [31:0] sum_cd = c + d;
  wire [31:0] sum = sum_ab + sum_cd;
  ```

### 21. `<large lookup / ROM / decoder, split into hierarchical sub-decoders or subtables, example>`
- **Pattern**: monolithic case or LUT such as 8b/10b encode/decode, instruction decode, large table lookup.
- **Strategy**: factor into structured hierarchy such as major-opcode then sub-decode.
- **Example**:
  ```verilog
  // BEFORE
  assign data_out = lut_256[data_in];

  // AFTER
  wire [3:0] hi = data_in[7:4];
  wire [3:0] lo = data_in[3:0];
  wire [W-1:0] hi_dec = lut_hi[hi];
  wire [W-1:0] lo_dec = lut_lo[lo];
  assign data_out = combine(hi_dec, lo_dec);
  ```

### 22. `<GF / XOR-heavy datapath / crypto logic, rebalance XOR/AND computation into explicit stages, example>`
- **Pattern**: serial XOR chains in AES/GF/error-correction style logic.
- **Strategy**: precompute lower-level XORs in parallel, then combine with a balanced tree.
- **Example**:
  ```verilog
  // BEFORE
  wire y = x0 ^ x1 ^ x2 ^ x3 ^ x4 ^ x5;

  // AFTER
  wire x01 = x0 ^ x1;
  wire x23 = x2 ^ x3;
  wire x45 = x4 ^ x5;
  wire y = (x01 ^ x23) ^ x45;
  ```

### 23. `<fixed constant multiplication, replace multiply with shift-add decomposition, example>`
- **Pattern**: multiply by compile-time constant.
- **Strategy**: rewrite as shifts and adds when it reduces critical depth or resource pressure.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] prod = x * 9'd257;

  // AFTER
  wire [W-1:0] prod = (x << 8) + x;
  ```

### 24. `<comparison after mux selection, convert mux-then-compare into compare-then-mux, example>`
- **Pattern**: select a source and then compare it to a threshold.
- **Strategy**: do the comparisons in parallel first, then mux the boolean result.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] selected = sel ? a : b;
  wire result = (selected > threshold);

  // AFTER
  wire a_gt = (a > threshold);
  wire b_gt = (b > threshold);
  wire result = sel ? a_gt : b_gt;
  ```

### 25. `<FSM with multiple related outputs, group states by shared output behavior before final decode, example>`
- **Pattern**: multiple FSM outputs depend on overlapping sets of states.
- **Strategy**: precompute state groups and derive outputs from those groups.
- **Example**:
  ```verilog
  // BEFORE
  assign active = (state == READ) | (state == WRITE) | (state == START);

  // AFTER
  wire state_is_read  = (state == READ);
  wire state_is_write = (state == WRITE);
  wire state_is_start = (state == START);
  wire state_group_rw = state_is_read | state_is_write;
  assign active = state_group_rw | state_is_start;
  ```

### 26. `<CPU / multi-cycle controller with timing-state decode, pre-decode machine-cycle and timing-state bits, example>`
- **Pattern**: CPU-style control with `MCycle`, `TState`, instruction groups, microstate families.
- **Strategy**: add a layer of pre-decoded boolean timing/state signals.
- **Example**:
  ```verilog
  // BEFORE
  assign is_fetch_t2 = (MCycle == 3'd1) && (TState == 3'd2);

  // AFTER
  wire mc_is_1 = (MCycle == 3'd1);
  wire ts_is_2 = (TState == 3'd2);
  wire is_fetch_t2 = mc_is_1 & ts_is_2;
  ```

### 27. `<long combinational expression with unclear synthesis boundary, add explicit intermediate wires to guide mapping, example>`
- **Pattern**: deeply nested expressions or mixed-width arithmetic where structure is hard for the tool to exploit.
- **Strategy**: add named staging wires at logical boundaries.
- **Example**:
  ```verilog
  // BEFORE
  wire [31:0] out = ((a * b) + c) >> sh;

  // AFTER
  wire [31:0] stage1 = a * b;
  wire [31:0] stage2 = stage1 + c;
  wire [31:0] out = stage2 >> sh;
  ```

### 28. `<mixed-width arithmetic or truncation boundaries, make width extension/truncation explicit in named wires, example>`
- **Pattern**: hidden casts, implicit sign extension, mixed-width arithmetic.
- **Strategy**: isolate width conversions explicitly so synthesis has clearer boundaries.
- **Example**:
  ```verilog
  // BEFORE
  wire [15:0] sum_ext = a + b;

  // AFTER
  wire [15:0] a_ext = {8'b0, a[7:0]};
  wire [15:0] b_ext = {8'b0, b[7:0]};
  wire [15:0] sum_ext = a_ext + b_ext;
  ```

### 48. `<counter or state compared against a constant on the critical path, register a lookahead flag computed from the next value, example>`
- **Pattern**: `cnt == MAX`, `ptr == LIMIT`, `state == X` evaluated from a register and feeding a long downstream path (wrap, done, full/empty flags).
- **Strategy**: compute the comparison on the *next* value and register it alongside the counter, so the flag comes straight from a flip-flop. Cycle behavior is unchanged.
- **AEGIS notes**: amenability *sequential-safe* (no latency change). The flag's reset value must equal the comparison evaluated on the counter's reset value, and every update of the counter must go through the same next-value wire. If the counter is a CDC pointer (contract-bound tier), its contract is re-proven as usual.
- **Source**: standard practice (registered full/empty flags in asynchronous FIFOs). New in this revision; not yet validated in AEGIS runs.
- **Verified**: example proven equivalent with SymbiYosys (PDR).
- **Example**:
  ```verilog
  // BEFORE
  localparam [7:0] MAX = 8'd199;
  reg [7:0] cnt;
  always @(posedge clk or negedge rst_n)
    if (!rst_n)  cnt <= 8'd0;
    else if (en) cnt <= (cnt == MAX) ? 8'd0 : cnt + 8'd1;
  assign wrap = en & (cnt == MAX);

  // AFTER
  localparam [7:0] MAX = 8'd199;
  reg  [7:0] cnt;
  reg        cnt_is_max;
  wire [7:0] cnt_next = cnt_is_max ? 8'd0 : cnt + 8'd1;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      cnt        <= 8'd0;
      cnt_is_max <= (8'd0 == MAX);
    end else if (en) begin
      cnt        <= cnt_next;
      cnt_is_max <= (cnt_next == MAX);
    end
  assign wrap = en & cnt_is_max;
  ```

### 49. `<FSM output decoded from the state register feeds a long path, register the output from next_state instead of adding a cycle, example>`
- **Pattern**: Moore outputs such as `busy = (state == RUN) | (state == DONE)` decoded after the state register and driving datapath enables.
- **Strategy**: register the output from `state_next`, so it is available directly from a flip-flop with the same cycle timing as the decoded version. This moves the decode in front of the register instead of adding latency, unlike entry 12.
- **AEGIS notes**: amenability *sequential-safe*. The output register's reset value must equal the decode of the reset state. It lengthens the path into the output register, so use it only when the next-state logic has slack.
- **Source**: standard FSM coding practice (registered Moore outputs). New in this revision; not yet validated in AEGIS runs.
- **Verified**: example proven equivalent with SymbiYosys (PDR).
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk or negedge rst_n)
    if (!rst_n) state <= IDLE;
    else        state <= state_next;
  assign busy = (state == RUN) | (state == DONE);

  // AFTER
  reg busy_r;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      state  <= IDLE;
      busy_r <= 1'b0;                 // = decode of IDLE
    end else begin
      state  <= state_next;
      busy_r <= (state_next == RUN) | (state_next == DONE);
    end
  assign busy = busy_r;
  ```

### 50. `<one input arrives much later than the others (it is the critical path's startpoint), Shannon-expand on the late signal and select last, example>`
- **Pattern**: the timing report shows one startpoint dominating a cone, and that signal enters early in a deep expression.
- **Strategy**: compute the function twice, once with the late signal fixed to 1 and once fixed to 0, then use the late signal only as the final mux select. The late signal then passes through one mux instead of the whole cone. Entry 14 is the arithmetic special case.
- **AEGIS notes**: amenability *combinational*. Use the Phase 2 startpoint to identify the late signal. Area roughly doubles for the expanded cone, so apply it to small cones or single-bit late signals.
- **Source**: standard logic-synthesis technique (Shannon expansion / cofactoring). New in this revision; not yet validated in AEGIS runs.
- **Verified**: both examples proven equivalent with SymbiYosys.
- **Example**:
  ```verilog
  // BEFORE
  assign y  = ((a & late) | b) ^ (c & ~late) ^ d;
  assign y2 = (x + (late ? p : q)) > t;           // 16-bit operands

  // AFTER
  wire y_late1 = (a | b) ^ d;                     // late = 1
  wire y_late0 = b ^ c ^ d;                       // late = 0
  assign y = late ? y_late1 : y_late0;

  wire [15:0] sum_p = x + p;
  wire [15:0] sum_q = x + q;
  wire        y2_p  = sum_p > t;
  wire        y2_q  = sum_q > t;
  assign y2 = late ? y2_p : y2_q;
  ```

### 51. `<logic after a register is critical while the logic before it has slack, retime the register forward across the logic without changing latency, example>`
- **Pattern**: inputs are registered and immediately feed a deep cone (adder plus compare), while the path into those registers is short.
- **Strategy**: move the register to the other side of part of the logic: register the intermediate result instead of the inputs. Total latency stays the same; delay moves from the downstream stage to the upstream one.
- **AEGIS notes**: amenability *sequential-safe*. The new register's reset value must equal the logic evaluated on the old registers' reset values, and its width must equal the expression's context width (here 16 bits, so overflow is dropped exactly as before). Keep the original registers if anything else reads them. Never retime across a synchronizer, I/O register, memory register, or a register with an enable unless the enable is carried onto the new register (see entry 54).
- **Source**: ChipVerify timing-closure notes (retiming and its boundary constraints); AMD UltraFast methodology also recommends balancing logic between registers. New in this revision; not yet validated in AEGIS runs.
- **Verified**: example proven equivalent with SymbiYosys (k-induction).
- **Example**:
  ```verilog
  // BEFORE
  reg [15:0] a_r, b_r;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin a_r <= 16'd0; b_r <= 16'd0; end
    else        begin a_r <= a;     b_r <= b;     end
  assign gt = (a_r + b_r) > thresh;

  // AFTER
  reg [15:0] sum_r;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) sum_r <= 16'd0;                   // = 16'd0 + 16'd0
    else        sum_r <= a + b;
  assign gt = sum_r > thresh;
  ```

### 52. `<shared operator whose operand muxes sit on the critical path (late select), unshare: duplicate the operator and select the results, example>`
- **Pattern**: `(sel ? a : c) + (sel ? b : d)`, where `sel` arrives late. This is the shared form that entry 15 produces.
- **Strategy**: compute both operations in parallel and select the result last, so `sel` passes through one mux instead of a mux plus the operator. Use entry 15 instead when the operands arrive late and `sel` is early.
- **AEGIS notes**: amenability *combinational*. Costs one extra operator of area.
- **Source**: AMD synthesis guidance that resource sharing trades timing for area (Vivado exposes it as a synthesis option); recalled from memory, not re-checked against the current document. New in this revision; not yet validated in AEGIS runs.
- **Verified**: example proven equivalent with SymbiYosys.
- **Example**:
  ```verilog
  // BEFORE
  wire [15:0] op_x = sel ? a : c;
  wire [15:0] op_y = sel ? b : d;
  assign y = op_x + op_y;

  // AFTER
  wire [15:0] sum_ab = a + b;
  wire [15:0] sum_cd = c + d;
  assign y = sel ? sum_ab : sum_cd;
  ```

---

## CDC contract-bound logic

These entries apply to the **contract-bound tier**: logic that produces or consumes a clock-domain crossing but is not itself a synchronizer, such as Gray-pointer counters, full/empty logic, handshake state machines, and capture registers. AEGIS may rewrite this logic, but every candidate must still prove the crossing's contracts (G1/G2 for Gray pointers, H1–H3 for handshakes, P1–P2 for pulse synchronizers, Q1–Q2 and D1 for qualifier buses) and pass the structural rules.

Rules for this tier:

- The value sequence on the crossing signal must not change: it stays registered (rule R4), and a Gray pointer still steps by exactly one code per increment.
- Synchronizer flops, the register that launches the crossing, and capacity parameters (FIFO depth, pointer width) are immutable and are never part of the edit.
- Logic after the last synchronizer stage in the destination domain is ordinary logic. The general entries above apply there, and entries 63 and 64 target it directly.
- Handshake, pulse, and qualifier-bus logic has little to optimize beyond general next-state techniques (entries 1–4, 16). Do not touch *when* data loads, *when* a request or qualifier toggles, or how long data is held (entry 61 is not the same thing: it keeps the sequence and only changes how it is computed). See entry 65.

All four examples below are proven equivalent to their originals with SymbiYosys. For entries 61 and 62, the rewritten pointer logic was also proven to satisfy the Gray contract G1/G2 and rule R4.

### 61. `<Gray-coded pointer that converts Gray to binary, increments, and converts back every cycle, keep a binary register beside the Gray register, example>`
- **Pattern**: the pointer is stored only in Gray form, so each update runs a Gray-to-binary XOR chain, an incrementer, and a binary-to-Gray conversion in series.
- **Strategy**: keep a binary register that increments directly, and register its Gray encoding as the crossing pointer. The Gray value sequence is unchanged; the XOR chain leaves the critical path, at the cost of one extra register bank.
- **AEGIS notes**: amenability *sequential-safe*. The binary and Gray registers must reset to matching values (0 and 0). Contract G1/G2 and rule R4 still hold, because the Gray register is still the crossing launch flop.
- **Source**: standard asynchronous-FIFO design practice. New in this revision; not yet validated in AEGIS runs.
- **Verified**: equivalent (SymbiYosys, PDR); Gray contract G1/G2 proven and rule R4 passed on the rewritten logic.
- **Example**:
  ```verilog
  // BEFORE
  reg  [4:0] g;                               // Gray pointer, crosses to the other domain
  wire [4:0] b      = g2b(g);                 // serial XOR chain
  wire [4:0] b_next = b + {4'd0, inc};
  always @(posedge clk or negedge rst_n)
    if (!rst_n) g <= 5'd0;
    else        g <= b_next ^ (b_next >> 1);
  assign wptr = g;

  // AFTER
  reg  [4:0] bin, g;
  wire [4:0] bin_next = bin + {4'd0, inc};
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin bin <= 5'd0;     g <= 5'd0; end
    else        begin bin <= bin_next; g <= bin_next ^ (bin_next >> 1); end
  assign wptr = g;
  ```

### 62. `<pointer increment gated by the registered full/empty flag, compute the increment and both flag comparisons speculatively and select by the increment condition, example>`
- **Pattern**: `inc = winc & ~wfull` feeds the adder, which feeds the Gray conversion, which feeds the full comparison: the flag sits at both ends of one long path.
- **Strategy**: compute the incremented pointer, its Gray code, and the full comparison for both outcomes (increment and hold) unconditionally, then select all three with `inc` at the register inputs. This is entry 14 applied to FIFO pointer logic.
- **AEGIS notes**: amenability *combinational*. Recompute the hold-case Gray code from the binary register rather than reusing the Gray register; reusing it is also correct, but its proof needs an invariant that plain k-induction cannot find (PDR can).
- **Source**: standard speculative-computation technique. New in this revision; not yet validated in AEGIS runs.
- **Verified**: equivalent (SymbiYosys, PDR); Gray contract G1/G2 proven and rule R4 passed on the rewritten logic.
- **Example**:
  ```verilog
  // BEFORE
  wire [4:0] wbin_next  = wbin + {4'd0, (winc & ~wfull)};
  wire [4:0] wgray_next = (wbin_next >> 1) ^ wbin_next;
  wire       wfull_next = (wgray_next == {~wq2_rptr[4:3], wq2_rptr[2:0]});
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wptr <= 0; wfull <= 1'b0; end
    else begin wbin <= wbin_next; wptr <= wgray_next; wfull <= wfull_next; end

  // AFTER
  wire [4:0] bin_inc   = wbin + 1'b1;
  wire [4:0] gray_inc  = (bin_inc >> 1) ^ bin_inc;
  wire [4:0] gray_hold = (wbin >> 1) ^ wbin;
  wire [4:0] full_pat  = {~wq2_rptr[4:3], wq2_rptr[2:0]};
  wire       full_inc  = (gray_inc  == full_pat);
  wire       full_hold = (gray_hold == full_pat);
  wire       inc       = winc & ~wfull;
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wptr <= 0; wfull <= 1'b0; end
    else begin
      wbin  <= inc ? bin_inc  : wbin;
      wptr  <= inc ? gray_inc : gray_hold;
      wfull <= inc ? full_inc : full_hold;
    end
  ```

### 63. `<full or empty computed by converting synchronized Gray pointers to binary before comparing, compare directly in the Gray domain, example>`
- **Pattern**: `g2b(wptr) == (g2b(rptr_sync) ^ MSB)` or `g2b(a) == g2b(b)`: two serial XOR chains in front of an equality compare.
- **Strategy**: Gray coding is a one-to-one mapping, so equality can be tested on the Gray codes directly. For the full condition, flipping the binary MSB corresponds to inverting the top **two** Gray bits.
- **AEGIS notes**: amenability *combinational*. Applies only to equality tests; ordering comparisons and fill levels still need binary (entry 64). On the destination side this is ordinary logic after the synchronizer; on the source side it is contract-bound and G1/G2 are re-proven.
- **Source**: standard asynchronous-FIFO design practice. New in this revision; not yet validated in AEGIS runs.
- **Verified**: equivalent (SymbiYosys).
- **Example**:
  ```verilog
  // BEFORE
  wire [4:0] wb = g2b(wgnext);
  wire [4:0] rb = g2b(rq2);
  assign full = (wb == (rb ^ 5'b10000));

  // AFTER
  assign full = (wgnext == {~rq2[4:3], rq2[2:0]});
  ```

### 64. `<Gray-to-binary conversion on the critical path (fill level, almost-full), replace the serial XOR chain with a log-depth prefix XOR, example>`
- **Pattern**: `b[i] = b[i+1] ^ g[i]` written as a loop, giving a chain as long as the pointer.
- **Strategy**: compute the prefix XOR in log2(W) stages of shift-and-XOR.
- **AEGIS notes**: amenability *combinational*. Synthesis may already rebalance the XOR chain, so credit a gain only if the post-synthesis netlist shows one. Same tier rules as entry 63.
- **Source**: standard prefix-computation technique. New in this revision; not yet validated in AEGIS runs.
- **Verified**: equivalent for 8 bits (SymbiYosys).
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    b[7] = g[7];
    for (i = 6; i >= 0; i = i - 1) b[i] = b[i+1] ^ g[i];
  end

  // AFTER
  wire [7:0] t1 = g  ^ (g  >> 1);
  wire [7:0] t2 = t1 ^ (t1 >> 2);
  wire [7:0] t4 = t2 ^ (t2 >> 4);
  assign b = t4;
  ```

---

## Low-confidence

### 29. `<aggressive arithmetic branch parallelization, compute all arithmetic branches and late-select across complex arithmetic, example>`
- **Pattern**: several arithmetic branches with overflow, signedness, or truncation subtleties.
- **Strategy**: compute everything in parallel and mux at the end. SEC failures are common.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    if (sel)
      out = a + b;
    else
      out = c - d;
  end

  // AFTER
  wire [W-1:0] br0 = a + b;
  wire [W-1:0] br1 = c - d;
  assign out = sel ? br0 : br1;
  ```

### 30. `<control flattening around arithmetic-heavy paths, rewrite state/control logic to expose arithmetic in parallel, example>`
- **Pattern**: arithmetic embedded inside a complex control structure.
- **Strategy**: flatten control and let arithmetic branches surface as parallel computations.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    case (state)
      S0: out = a + b;
      S1: out = a - b;
      default: out = v0;
    endcase
  end

  // AFTER
  wire [W-1:0] v1 = a + b;
  wire [W-1:0] v2 = a - b;
  assign out = (state == S0) ? v1 :
               (state == S1) ? v2 : v0;
  ```

### 31. `<arithmetic chain tree balancing with carry/overflow sensitivity, rebalance addition/subtraction structure, example>`
- **Pattern**: long arithmetic chain where operator ordering affects carry or signed behavior.
- **Strategy**: rebalance the arithmetic tree only when overflow, carry, saturation, and truncation behavior are proven unchanged.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] y = ((a + b) + c) + d;

  // AFTER
  wire [W-1:0] t0 = a + b;
  wire [W-1:0] t1 = c + d;
  wire [W-1:0] y = t0 + t1;
  ```

### 32. `<aggressive mux tree restructuring when synthesis already optimizes muxes well, explicitly force custom mux hierarchy, example>`
- **Pattern**: wide mux path without a clearly demonstrated structural issue.
- **Strategy**: manually rewrite the mux network. May help occasionally, but often not worth it.
- **Example**:
  ```verilog
  // BEFORE
  assign y = s1 ? (s0 ? d3 : d2) : (s0 ? d1 : d0);

  // AFTER
  wire m0 = s0 ? d1 : d0;
  wire m1 = s0 ? d3 : d2;
  assign y = s1 ? m1 : m0;
  ```

### 33. `<explicit wire decomposition solely for hoped timing gain, split expression into many named wires without structural change, example>`
- **Pattern**: deep expression where no real algebraic or architectural change is introduced.
- **Strategy**: add intermediate wires just to “help synthesis.” Improvement is often negligible.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] y = a + b + c + d;

  // AFTER
  wire [W-1:0] t0 = a + b;
  wire [W-1:0] t1 = t0 + c;
  wire [W-1:0] y = t1 + d;
  ```

---

## Do not use

### 12. `<FSM outputs driving long downstream logic, register or pipeline the boundary signal when extra latency is architecturally acceptable, example>`
- **Pattern**: state decode or module input launches a long path into datapath/control logic.
- **Strategy**: register the boundary signal to break the path, but only when the extra cycle is explicitly acceptable and validated.
- **AEGIS notes**: moved to Do not use in this revision. Registering the signal adds a cycle of latency, so the candidate fails sequential equivalence by construction (confirmed: the entry 12 example is non-equivalent under SymbiYosys) and is labeled *sequential-unsafe*. Latency-preserving alternatives: entries 48 and 49.
- **Example**:
  ```verilog
  // BEFORE
  wire state_is_data = (next_state == DATA);
  assign data_en = state_is_data & ready;

  // AFTER (DO NOT USE IN AEGIS)
  reg state_is_data_r;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      state_is_data_r <= 1'b0;
    else
      state_is_data_r <= (next_state == DATA);
  end
  assign data_en = state_is_data_r & ready;
  ```

### 34. `<registering decode/control outputs to break timing when architectural latency is uncertain, insert sequential boundary speculatively, example>`
- **Pattern**: tempting long control path, but no clear proof that an extra cycle is legal.
- **Strategy**: add a register only as a last resort.
- **AEGIS notes**: moved to Do not use in this revision. Registering the signal adds a cycle of latency, so the candidate fails sequential equivalence by construction (confirmed: the entry 12 example is non-equivalent under SymbiYosys) and is labeled *sequential-unsafe*. Latency-preserving alternatives: entries 48 and 49.
- **Example**:
  ```verilog
  // BEFORE
  assign out = sel ? a : b;

  // AFTER (DO NOT USE IN AEGIS)
  reg sel_r;
  always @(posedge clk) begin
    sel_r <= sel;
  end
  assign out = sel_r ? a : b;
  ```

### 35. `<count-up to count-down rewrite or reverse counter direction, change counter direction to simplify terminal detect, example>`
- **Pattern**: `count == MAX` is on the critical path and zero-detect looks cheaper.
- **Strategy**: do **not** rewrite count-up logic into count-down logic just to get zero-detect.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk) begin
    if (en)
      count <= count + 1'b1;
  end
  wire hit_max = (count == MAX_COUNT);

  // AFTER (DO NOT USE)
  always @(posedge clk) begin
    if (en)
      count <= count - 1'b1;
  end
  wire hit_max = (count == 0);
  ```

### 36. `<priority if-else chain flattened into parallel AND-OR without guaranteed mutual exclusivity, remove priority semantics, example>`
- **Pattern**: if-else or priority case where multiple inputs may be simultaneously true.
- **Strategy**: do **not** flatten into parallel logic unless mutual exclusion is formally guaranteed.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) begin
    if (req0)
      grant = 2'b00;
    else if (req1)
      grant = 2'b01;
    else
      grant = 2'b11;
  end

  // AFTER (DO NOT USE)
  assign grant[0] = req1;
  assign grant[1] = ~req0 & ~req1;
  ```

### 37. `<pre-registering mux selector / control selector on active data path, add register to selector to shorten mux path, example>`
- **Pattern**: selector signal is on the critical path of a mux network.
- **Strategy**: do **not** register the selector unless the design explicitly allows the control to arrive one cycle later.
- **Example**:
  ```verilog
  // BEFORE
  assign out = sel ? a : b;

  // AFTER (DO NOT USE)
  reg sel_r;
  always @(posedge clk) sel_r <= sel;
  assign out = sel_r ? a : b;
  ```

### 38. `<control-signal pre-registration across module boundary for timing only, insert control pipeline stage without protocol redesign, example>`
- **Pattern**: cross-module control signal is long and timing-critical.
- **Strategy**: do **not** add a register stage casually.
- **Example**:
  ```verilog
  // BEFORE
  child u0(.req(req), .ack(ack));

  // AFTER (DO NOT USE)
  reg req_r;
  always @(posedge clk) req_r <= req;
  child u0(.req(req_r), .ack(ack));
  ```

### 39. `<operand width reduction / interface width reduction for speed, narrow datapath or module inputs to reduce logic, example>`
- **Pattern**: a wide module input or intermediate result appears over-provisioned.
- **Strategy**: do **not** shrink widths unless numerical equivalence is proved.
- **Example**:
  ```verilog
  // BEFORE
  module foo(input [2*W-1:0] in_data, output [W-1:0] out_data);

  // AFTER (DO NOT USE)
  module foo(input [W-1:0] in_data, output [W-1:0] out_data);
  ```

### 40. `<algebraic restructuring that changes arithmetic corner behavior, rewrite expression form without proof of overflow/signed equivalence, example>`
- **Pattern**: trying to simplify arithmetic by changing grouping or fused operations.
- **Strategy**: do **not** apply algebraic rewrites casually.
- **Example**:
  ```verilog
  // BEFORE
  assign y = (a - b) + c;

  // AFTER (DO NOT USE)
  assign y = a + (c - b);
  ```

### 41. `<fused subtract-multiply / aggressive arithmetic fusion, collapse arithmetic stages into a new combined structure, example>`
- **Pattern**: subtract/multiply/add chain with timing pressure.
- **Strategy**: do **not** fuse or reorder aggressively unless you have a strong formal proof.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] t = a - b;
  assign y = t * c;

  // AFTER (DO NOT USE)
  assign y = (a * c) - (b * c);
  ```

### 42. `<changing LFSR feedback or polynomial structure, rewrite feedback network for timing, example>`
- **Pattern**: LFSR or scrambler feedback path is critical.
- **Strategy**: do **not** alter the feedback polynomial/structure.
- **Example**:
  ```verilog
  // BEFORE
  assign feedback = lfsr[7] ^ lfsr[5];

  // AFTER (DO NOT USE)
  assign feedback = lfsr[7] ^ lfsr[6];
  ```

### 43. `<modifying memory array addressing / decode architecture from RTL timing path, rewrite memory indexing or address decode casually, example>`
- **Pattern**: address decode or array access appears on the critical path.
- **Strategy**: do **not** casually rewrite memory addressing.
- **Example**:
  ```verilog
  // BEFORE
  assign rd_data = mem[addr];

  // AFTER (DO NOT USE)
  assign rd_data = (addr_sel ? mem[addr_hi] : mem[addr_lo]);
  ```

### 44. `<optimizing pure register self-loop / constraint-only paths as if they were RTL logic problems, rewrite RTL for clock-to-q/setup-only reports, example>`
- **Pattern**: path is mostly register-to-register constraint behavior rather than meaningful combinational logic.
- **Strategy**: do **not** attack these with RTL rewrites.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk)
    q <= d;

  // AFTER (DO NOT USE)
  // arbitrary RTL restructuring here does not solve a clocking/physical constraint path
  always @(posedge clk)
    q <= d;
  ```

### 45. `<expression simplification that removes helpful intermediate boundaries, inline everything into one direct expression, example>`
- **Pattern**: rewriting to “clean up” code by removing named intermediates.
- **Strategy**: do **not** assume fewer wires means better timing.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] t0 = a + b;
  wire [W-1:0] y  = t0 + c;

  // AFTER (DO NOT USE)
  wire [W-1:0] y = a + b + c;
  ```

### 46. `<restructured comparison ordering that changes corner-case evaluation semantics, reorder sign/magnitude checks for early exit, example>`
- **Pattern**: comparisons with signed, bounded, or asymmetric behavior.
- **Strategy**: do **not** reorder the logical test sequence unless equivalence is proven for all corners.
- **Example**:
  ```verilog
  // BEFORE
  assign sat = (x > POS_LIM) || (x < NEG_LIM);

  // AFTER (DO NOT USE)
  assign sat = x[W-1] ? (x < NEG_LIM) : (x > POS_LIM);
  ```

### 47. `<aggressive tree balancing on paths labeled combinational_depth without understanding arithmetic semantics, mechanically rebalance everything, example>`
- **Pattern**: timing report says “combinational depth” and the response is blanket tree balancing.
- **Strategy**: do **not** rebalance blindly, especially on arithmetic-heavy logic.
- **Example**:
  ```verilog
  // BEFORE
  wire [W-1:0] y = (((a + b) + c) + d) + e;

  // AFTER (DO NOT USE)
  wire [W-1:0] t0 = a + b;
  wire [W-1:0] t1 = c + d;
  wire [W-1:0] y  = (t0 + t1) + e;
  ```

### 53. `<long arithmetic path, insert pipeline stages to split it, example>`
- **Pattern**: multiplier, divider, or wide adder too slow for the clock period. Timing guides recommend pipelining it as the first fix.
- **Strategy**: do **not** use in AEGIS. Pipelining adds cycles of latency, so the candidate fails sequential equivalence by construction and the change is labeled *sequential-unsafe*. Use latency-preserving alternatives instead: entries 9, 20, 23, 50, or 51.
- **Source**: ChipVerify timing-closure notes (pipeline insertion); AMD UltraFast methodology.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk) product <= a * b;

  // AFTER (DO NOT USE: adds one cycle of latency)
  always @(posedge clk) begin
    pp_lo   <= a[7:0] * b;
    pp_hi   <= a[15:8] * b;
    product <= pp_lo + (pp_hi << 8);
  end
  ```

### 54. `<retiming or moving logic across a boundary register (synchronizer, I/O, memory, enabled, or feedback register), example>`
- **Pattern**: retiming (entry 51) applied to a register that marks a boundary.
- **Strategy**: do **not** retime across synchronizer flops (immutable tier), I/O registers (interface timing is fixed), memory read/write registers, registers with an enable unless the enable is replicated onto the new register, or registers in a feedback loop whose reset values cannot be matched. Moving logic in front of the first synchronizer flop also breaks structural rule R4.
- **Source**: ChipVerify timing-closure notes (retiming boundary constraints).
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk_dst) begin
    sync1 <= req_src;           // crossing from another clock domain
    sync2 <= sync1;
  end
  assign go = sync2 & armed;

  // AFTER (DO NOT USE: logic now sits in front of the synchronizer)
  always @(posedge clk_dst) begin
    sync1 <= req_src & armed_q;
    sync2 <= sync1;
  end
  assign go = sync2;
  ```

### 55. `<high fanout or a slow gate on the critical path, insert buffers or instantiate larger library cells in RTL, example>`
- **Pattern**: report shows a heavily loaded net or a weak cell (for example `INV_X1`) on the critical path.
- **Strategy**: do **not** fix this in RTL. Buffering and gate sizing are done by synthesis and physical design, which redo them anyway; hard-coded cells tie the RTL to one library and block those tools. For RTL-level fanout reduction use entries 7 and 8.
- **Source**: ChipVerify timing-closure notes (buffer insertion, gate sizing).
- **Example**:
  ```verilog
  // BEFORE
  assign en_all = state_is_run & ready;

  // AFTER (DO NOT USE)
  BUF_X4  u_buf0 (.A(en_raw), .Z(en_all));
  NAND2_X2 u_n0  (.A1(state_is_run), .A2(ready), .ZN(en_raw_n));
  ```

### 56. `<violations that look like constraint problems, fix them by editing SDC (false paths, multicycle paths, clock uncertainty, I/O delays), example>`
- **Pattern**: paths between asynchronous clocks, static configuration paths, or pessimistic uncertainty and I/O delays.
- **Strategy**: do **not** edit constraints inside the optimization loop. AEGIS hashes the SDC; constraint issues go to the Phase 0/Phase 1 constraint-audit report for a human to fix. Paths between asynchronous clocks are excluded by Phase 2 before any rewrite is attempted. Relates to entry 44.
- **Source**: ChipVerify timing-closure notes (constraint refinement).
- **Example**:
  ```verilog
  // BEFORE (SDC unchanged; violation reported on clk_a -> clk_b)

  // AFTER (DO NOT USE: constraint edit made to "close" timing)
  // set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]
  // set_multicycle_path 2 -setup -to [get_pins result_reg*/D]
  ```

### 57. `<case statements and decoders, add full_case / parallel_case pragmas or X default assignments to let synthesis simplify, example>`
- **Pattern**: decoders or muxes where some encodings are believed unreachable.
- **Strategy**: do **not** use. These pragmas and X assignments make synthesis and simulation disagree, and an equivalence checker may treat the X differently from silicon. If encodings are truly one-hot or mutually exclusive, express that structurally (entries 3, 4, 17).
- **Source**: standard RTL coding guidance.
- **Example**:
  ```verilog
  // BEFORE
  always @(*) case (sel)
    2'd0: y = a;  2'd1: y = b;  2'd2: y = c;  default: y = d;
  endcase

  // AFTER (DO NOT USE)
  always @(*) begin
    y = 'x;
    case (sel) // synopsys full_case parallel_case
      2'd0: y = a;  2'd1: y = b;  2'd2: y = c;
    endcase
  end
  ```

### 58. `<reset network has high fanout, remove resets from datapath registers, example>`
- **Pattern**: a reset drives many datapath flops. FPGA methodology (AMD UltraFast) recommends resetting only what needs it, because unneeded resets cost routing and block efficient mapping.
- **Strategy**: do **not** apply this in AEGIS. Removing a reset changes post-reset behavior, so equivalence checking under a reset assumption can fail, and it can create reset-domain-crossing issues. Reset synchronizers are in the immutable tier. Leave reset architecture to the designer.
- **Source**: AMD UltraFast design methodology (reset guidance), recalled from memory; marked FPGA-specific.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk or negedge rst_n)
    if (!rst_n) data_r <= '0;
    else        data_r <= data_in;

  // AFTER (DO NOT USE)
  always @(posedge clk)
    data_r <= data_in;
  ```

### 59. `<register with an enable on the critical path, convert the enable into a gated or derived clock, example>`
- **Pattern**: enable logic in front of a register bank looks slow.
- **Strategy**: do **not** create clock gating or derived clocks in RTL. Clock-generation logic is in the immutable tier, a new clock invalidates the SDC, and RTL clock gating risks glitches. Clock gating is inserted by the synthesis tool with proper cells when wanted.
- **Source**: standard RTL coding guidance; AEGIS clock-generation lock.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk) if (en) q <= d;

  // AFTER (DO NOT USE)
  assign gclk = clk & en;
  always @(posedge gclk) q <= d;
  ```

### 60. `<synchronizer output has high fanout, duplicate synchronizer flops to split the load, example>`
- **Pattern**: entry 7 (register duplication) applied to a synchronizer chain.
- **Strategy**: do **not** duplicate synchronizer flops. Two copies sampling the same metastable first stage can resolve to different values, so downstream logic sees the same crossing disagree with itself. Synchronizers are in the immutable tier; leave fanout buffering of the final stage to synthesis, or duplicate logic further downstream.
- **Source**: standard CDC design guidance; AEGIS immutable tier.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk_dst) begin
    sync1 <= async_in;
    sync2 <= sync1;
  end

  // AFTER (DO NOT USE)
  always @(posedge clk_dst) begin
    sync1   <= async_in;
    sync2_a <= sync1;     // two copies may resolve differently
    sync2_b <= sync1;
  end
  ```

### 65. `<handshake, qualifier, or pulse logic on the critical path, shorten it by changing when data loads, when a request toggles, or how long data is held, example>`
- **Pattern**: the data-load enable, busy counter, or capture enable around a crossing looks like removable control logic.
- **Strategy**: do **not** use. Each of these is a CDC obligation, and the contracts reject the result: loading data while a request is high (H1), raising a new request before the acknowledge returns low (H3), replacing a toggle with a raw pulse (P1), shortening or removing the hold window (Q1/Q2), or removing the destination capture enable (D1). These correspond to mutation classes M5–M9. Optimize the surrounding next-state logic instead, using the general entries.
- **Source**: AEGIS contract tier and mutation suite.
- **Example**:
  ```verilog
  // BEFORE
  always @(posedge clk or negedge rst_n)
    if (!rst_n)                          begin req <= 1'b0; data <= '0; end
    else if (!req && !ack_sync && send)  begin data <= din; req <= 1'b1; end
    else if (req && ack_sync)            req <= 1'b0;

  // AFTER (DO NOT USE: data can change during a transfer, violates H1)
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin req <= 1'b0; data <= '0; end
    else begin
      if (send) data <= din;
      if (!req && !ack_sync && send) req <= 1'b1;
      else if (req && ack_sync)      req <= 1'b0;
    end
  ```

---

## Practical usage notes

- Start with **High-confidence** skills first, especially: condition pre-computation, one-hot pre-decode, CSE, and fanout reduction by duplication.
- Use **Medium-confidence** skills when the timing root cause is clear and equivalence reasoning is still local.
- Treat **Low-confidence** skills as targeted experiments, one at a time.
- Treat **Do not use** as strong default prohibitions unless you have very strong design-specific proof.
- In general, prefer **pre-computation over restructuring** and **local simplification over architectural rewrites**.
- **Late versus early signals**: use the Phase 2 startpoint to decide direction. A late select favors computing branches in parallel (entries 14, 50, 52); late operands with an early select favor sharing (entry 15).
- **Latency-preserving sequential fixes first**: before any registering idea, try a lookahead flag (48), a registered FSM output from `state_next` (49), or forward retiming (51). Each keeps cycle behavior identical, so equivalence checking can prove it.
- **No latches**: when flattening or rewriting a combinational `always` block (entries 16, 17, 30), assign every output on every path, or synthesis infers a latch.
- **Duplication needs `keep`**: duplicated registers or wires (entries 7, 8) can be merged back by synthesis; check the post-synthesis netlist.
- **Tool-level and constraint fixes are out of scope**: buffering, gate sizing, and SDC edits (entries 55, 56) belong to synthesis, physical design, or the constraint-audit report.

---

