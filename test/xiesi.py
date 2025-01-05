import re
import sys

class MIPS_Pipeline:
    def __init__(self):
        # 32 registers and 32 word memory
        self.registers = [1] * 32
        self.registers[0] = 0
        self.memory = [1] * 32

        # Pipeline stage
        self.pipeline_instructions = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }
        # Pipeline registers
        self.pipeline_registers = {
            "IF/ID": {},
            "ID/EX": {},
            "EX/MEM": {},
            "MEM/WB": {},
        }
        # Program counter
        self.pc = 0
        self.cycle = 0
        self.WB_over = 0
        #flags
        self.stall = False
        # Instruction memory
        self.instructions = []

    def load_instructions(self, instructions):
        """
        測試用
        """
        self.instructions = instructions

    def load_instructions_from_file(self, filename):
        """
        Load instructions from a file and format them for the pipeline
        """
        try:
            with open(filename, 'r') as file:
                lines = [line.strip() for line in file if line.strip()]
                formatted_instructions = []
                for line in lines:
                    # Remove `$` symbols and whitespace, format properly
                    formatted_line = re.sub(r'\$(\d+)', r'\1', line)  # Remove `$`
                    formatted_line = re.sub(r'\s*,\s*', ', ', formatted_line)  # Ensure consistent comma spacing
                    formatted_instructions.append(formatted_line)
                self.instructions = formatted_instructions
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except Exception as e:
            print(f"Error: {e}")

    def IF(self):
        """
        Fetch the instruction from instruction memory
        Update the next address of instruction
        """
        if self.stall == True:
            self.stall = False
        else:
            # Fetch the instruction
            instruction = self.instructions[self.pc]
            # add op to IF
            op, *args = instruction.split()
            self.pipeline_instructions["IF"] = f"{op}"
            self.pipeline_registers["IF/ID"] = {"instruction": instruction}
            self.pc += 1
            
    def ID(self):
        """
        Decode R-format, I-format, and Branch instructions
        Setting control signals
        """
        if "instruction" in self.pipeline_registers["IF/ID"]:
            instruction = self.pipeline_registers["IF/ID"]["instruction"]
            op, *args = instruction.split()

            # add to ID
            self.pipeline_instructions["ID"] = f"{op}"

            # Initialize default control signals
            control_signals = {
                "RegDst": 0,
                "ALUSrc": 0,
                "MemtoReg": 0,
                "RegWrite": 0,
                "MemRead": 0,
                "MemWrite": 0,
                "Branch": 0,
                "ALUOp": "00",
            }
            
            # R-format instructions
            if op in ["add", "sub"]:  
                control_signals["RegDst"] = 1
                control_signals["ALUSrc"] = 0
                control_signals["RegWrite"] = 1
                control_signals["ALUOp"] = "10" 

            # I-format instructions
            elif op in ["lw", "sw"]:  
                control_signals["ALUSrc"] = 1
                if op == "lw":
                    control_signals["MemRead"] = 1
                    control_signals["MemtoReg"] = 1
                    control_signals["RegWrite"] = 1
                elif op == "sw":
                    control_signals["MemWrite"] = 1

            # Branch instruction
            elif op == "beq":  
                control_signals["Branch"] = 1
                control_signals["ALUOp"] = "01"

            # beq
            if control_signals["Branch"] == 1:
                rs, rt, offset = map(str, args[0:3])
                rs= int(rs.strip(','))
                rt = int(rt.strip(','))
                
                # detect_hazard
                if self.detect_hazard():
                    self.stall = True
                    self.pipeline_registers["ID/EX"]={
                        "op": op,
                        "result": None,
                        "control_signals": control_signals,
                    }
                    return
                
                offset = int(offset)
                if self.registers[rs] == self.registers[rt]:
                    # 重取 pc 進入 IF stage
                    self.pc += offset
                
            
            # ALUSrc = 0 Using registers(R-f)；ALUSrc = 1 Using immediate value(I-f)
            if control_signals["ALUSrc"] == 0:
                rd, rs, rt = map(str, args[0:3])
                rd = int(rd.strip(','))
                rs = int(rs.strip(','))
                rt = int(rt.strip(','))
                result = {"rd":rd, "rs": rs, "rt": rt}

            # I-f have 'lw' and 'sw', setting mem address to the next stage 
            else: 
                rt, offset_rs = args
                rt = int(rt.strip(','))
                offset, rs = offset_rs.strip(')').split('(')
                rs = int(rs)
                offset = int(offset)
                result = {"rt": rt, "offset": offset, "rs": rs}

            self.pipeline_registers["ID/EX"] = {
                "op": op,
                "result": result,
                "control_signals": control_signals,
            }

    def EX(self):
        """
        Execute the instruction
        """
        # debug show
        # print(self.pipeline_registers["ID/EX"])

        if "op" in self.pipeline_registers["ID/EX"]:
            op = self.pipeline_registers["ID/EX"]["op"]
            result = self.pipeline_registers["ID/EX"]["result"]
            control_signals = self.pipeline_registers["ID/EX"]["control_signals"]
            
            # add to EX
            self.pipeline_instructions["EX"] = f"{op}"

            # R-f only have 'add' and 'sub', ALUop = "10",sent 'rd' and value to the next stage
            if control_signals["ALUOp"] == "10":
                rd =  result["rd"]
                rt =  result["rt"]
                rs =  result["rs"]
                if op == "add":
                    result = {"rd":rd, "value":self.registers[rs] + self.registers[rt]}
                elif op == "sub":
                    result = {"rd":rd, "value":self.registers[rs] - self.registers[rt]}
            
            # I-f have 'lw' and 'sw', setting mem address to the next stage 
            elif op == "lw" and op == "sw": 
                rt = result["rt"]
                offset = result["offset"]
                rs = result["rs"]
                result = {"rt":rt, "offset":self.registers[rs] + offset}

            # Pass results to the next stage
            self.pipeline_registers["EX/MEM"] = {
                "op": op,
                "result": result,
                "control_signals": control_signals,
            }

    def MEM(self):
        """
        Memory access stage
        """
        # debug show
        # print(f"stage:MEM:{self.pipeline_registers['EX/MEM']}")

        if "op" in self.pipeline_registers["EX/MEM"]:
            op = self.pipeline_registers["EX/MEM"]["op"]
            result = self.pipeline_registers["EX/MEM"]["result"]
            control_signals = self.pipeline_registers["EX/MEM"]["control_signals"]

            # add to MEM
            self.pipeline_instructions["MEM"] = f"{op}"
            
            # Lw
            # print(f"MEMRead:{control_signals['MemRead']}") # 幹 control_signals 設錯
            if control_signals["MemRead"]:  
                value = self.memory[result["offset"]]
                rt = result["rt"]
                result = {"rt":rt,"value":value}
                self.pipeline_registers["MEM/WB"] = {
                    "op": op,
                    "result": result,
                    "control_signals": control_signals,
                }

            # Sw
            elif control_signals["MemWrite"]:  
                rt = result["rt"]
                offset = result["offset"]
                self.memory[offset] = self.registers[rt]
                # 確保完整性，後面要問 op
                self.pipeline_registers["MEM/WB"] = {
                    "op": op,
                    "control_signals": control_signals,
                }

             # 'add' and 'sub'
            elif control_signals["RegWrite"]: 
                self.pipeline_registers["MEM/WB"] = self.pipeline_registers["EX/MEM"]

    def WB(self):
        """
        Write back stage
        """
        # debug show
        # print(f"stage:WB:{self.pipeline_registers['MEM/WB']}")

        if "op" in self.pipeline_registers["MEM/WB"]:
            op = self.pipeline_registers["MEM/WB"]["op"]
            control_signals = self.pipeline_registers["MEM/WB"]["control_signals"]
        
            # add to WB
            self.pipeline_instructions["WB"] = f"{op}"

            if control_signals["RegWrite"]:
                # lw
                if control_signals["MemtoReg"]:
                    rt = int(self.pipeline_registers["MEM/WB"]["result"]["rt"])
                    value = self.pipeline_registers["MEM/WB"]["result"]["value"] 
                    self.registers[rt] = value
                    
                # 'add' and 'sub'
                else:
                    rd = (self.pipeline_registers["MEM/WB"]["result"]["rd"])
                    result = self.pipeline_registers["MEM/WB"]["result"]["value"]
                    self.registers[rd] = result
        
        self.WB_over += 1

    def detect_hazard(self):
        """
        Detect if data hazard occurs.
        Return True if hazard is detected, else False.

        偵測與上一階段 (ID/EX)、再上一階段 (EX/MEM) 或再上一階段 (MEM/WB) 的依存性，
        包含特殊情況：beq 需要等待前面若是 lw 指令的資料先寫回 (WB) 才能在 EX 階段正確比對。
        """

        # 1. 先取得正在 ID 階段的指令
        id_instruction = self.pipeline_registers["IF/ID"].get("instruction", "")
        if not id_instruction:
            # 若當前沒有指令在 ID 階段就不需要檢測
            return False

        # 2. 解析當前 ID 階段指令，取得其 op 與使用的來源暫存器 (sources)、目的暫存器 (dest)
        op, *args = id_instruction.split()
        current_src = []
        current_dest = None  # 對於 lw、add、sub 之類有目的暫存器的指令

        # 依不同指令取出 source/dest
        if op in ["add", "sub"]:
            # add rd, rs, rt -> 格式通常可能為: add 1, 2, 3
            # 這裡假設指令格式為: add rs, rt, rd
            # or 可能實作相反都可以，看你 parse 規則如何
            rs, rt, rd = map(lambda x: int(x.strip(",")), args[:3])
            current_src.extend([rs, rt])
            current_dest = rd

        elif op == "beq":
            # beq rs, rt, label -> 需要 rs, rt 作 EX 階段比對
            rs, rt = map(lambda x: int(x.strip(",")), args[:2])
            current_src.extend([rs, rt])

        elif op in ["lw"]:
            # lw rt, offset(rs) -> rt = Memory[ rs + offset ]
            # 例如: lw 2, 0(1)  => rs=1, rt=2
            rt, offset_rs = args
            rs = int(offset_rs.strip(')').split('(')[1])
            rt = int(rt.strip(","))
            current_src.append(rs)  # lw 的來源是記憶體地址，需要 rs
            current_dest = rt

        elif op in ["sw"]:
            # sw rt, offset(rs)
            rt, offset_rs = args
            rs = int(offset_rs.strip(')').split('(')[1])
            rt = int(rt.strip(","))
            current_src.extend([rs, rt])
            # sw 不需要寫回暫存器，故沒有 dest

        else:
            # 不在此範圍的指令，暫不考慮 Hazard
            return False

        # ------------------------------------------
        # 3. 依序取出上一階段 (ID/EX)、再上一階段 (EX/MEM)、再上一階段 (MEM/WB) 的指令資訊
        #    一般 5-stage pipeline:
        #       IF -> ID -> EX -> MEM -> WB
        #    所以 ID/EX 代表上一條指令正在做 EX，
        #    EX/MEM 代表更前一條指令剛做完 EX, 正在 MEM，
        #    MEM/WB 代表再前一條指令剛做完 MEM, 正在 WB。
        #    若發現相依性，需要 Stall 或 Forwarding。
        #    這裡僅先偵測到 Hazard，就回傳 True。
        # ------------------------------------------

        # 分別取得上一指令 (ID/EX)、更上一指令 (EX/MEM)、更上一指令 (MEM/WB) 的「目的暫存器」與「是否為 lw」
        # 以判斷是否需要等資料寫回 (尤其是 beq 對 lw 的依存需要等到 WB)

        # 方便起見，我們寫個輔助函式
        def parse_stage_info(stage_name):
            stage_inst = self.pipeline_registers.get(stage_name, {}).get("instruction", "")
            if not stage_inst:
                return None, None, None  # (op, is_lw, dest)
            s_op, *s_args = stage_inst.split()

            s_is_lw = (s_op == "lw")
            s_dest = None
            if s_op in ["add", "sub"]:
                # 假設格式 add rs, rt, rd
                rs_s, rt_s, rd_s = map(lambda x: int(x.strip(",")), s_args[:3])
                s_dest = rd_s
            elif s_op == "lw":
                rt_s, offset_rs_s = s_args
                rt_s = int(rt_s.strip(","))
                s_dest = rt_s
            elif s_op in ["beq", "sw"]:
                # beq / sw 沒有 dest
                s_dest = None

            return s_op, s_is_lw, s_dest

        # 取得各階段信息
        ex_op,  ex_is_lw,  ex_dest  = parse_stage_info("ID/EX")   # 正在 EX 階段指令的目的暫存器
        mem_op, mem_is_lw, mem_dest = parse_stage_info("EX/MEM")  # 正在 MEM 階段指令的目的暫存器
        wb_op,  wb_is_lw,  wb_dest  = parse_stage_info("MEM/WB")  # 正在 WB 階段指令的目的暫存器

        #
        # 4. Hazard 檢測邏輯：
        #
        #   4.1 若當前 ID 階段指令之 source registers (current_src) 與
        #       EX 階段指令 (ex_dest)、MEM 階段指令 (mem_dest)、WB 階段指令 (wb_dest)
        #       有相同暫存器，則可能產生 Data Hazard。
        #
        #       - 若上指令是 lw，資料要到 MEM 階段才會可用 (若有 forwarding)，
        #         或到 WB 時才真正寫回暫存器 (若沒有 forwarding)。
        #       - 假設這裡不考慮任何 forwarding，則只要 source == dest 就需要停頓。
        #         特別是 `beq` 依賴 lw 的情況，必須等到 lw 寫回 (WB) 後才可以正確做比較。
        #
        #   4.2 若當前 ID 階段指令會寫入某目的暫存器 (current_dest)，
        #       而上階段指令 (或更早階段) 同時也會寫到同一暫存器 (ex_dest, mem_dest, wb_dest)，
        #       通常不會構成讀後寫 (RAW) 的 Hazard，但可能會有寫後寫 (WAW) 問題，
        #       不過在典型的 5-stage MIPS pipeline 中，一次只會有一個寫回；WAW 在單發射 pipeline 中不會發生。
        #       這裡通常不需要特別處理。
        #

        # -- 檢測與 EX 階段指令是否有 Data Hazard --
        if ex_dest is not None and ex_dest in current_src:
            # 若上一階段（EX）目的暫存器 == 當前指令來源暫存器
            # 如果上一階段的指令是 lw，那麼資料尚未可用 (沒有 forwarding 就會有 hazard)
            # 或者任何指令會在 EX->MEM->WB 才能寫回，而現在 ID 階段就要用，會產生 hazard。
            return True

        # -- 檢測與 MEM 階段指令是否有 Data Hazard --
        if mem_dest is not None and mem_dest in current_src:
            # 如果 MEM 階段指令是 lw，且沒有 forwarding，資料要到 WB 才可用
            # 現在當前 ID 階段就要用，必須 stall。
            return True

        # -- 檢測與 WB 階段指令是否有 Data Hazard --
        if wb_dest is not None and wb_dest in current_src:
            # 即使到 WB 階段要寫回暫存器，若我們假設下一個 cycle 才能讀到，
            # 則當前指令在 ID 階段還沒辦法取得最新資料。
            return True

        #
        # 4.3 特殊情況：beq & lw
        #     若當前指令是 beq，且它的來源暫存器來自於正在進行的 lw，
        #     則需要等到 lw 寫回 (WB) 才能知道正確的分支結果 (沒有 forwarding)。
        #     但上面已經涵蓋了當 lw 還沒寫回時與 source 相同就會 hazard，
        #     所以這裡如果要“特別”檢查，也可以再根據需求加強判斷條件。
        #
        #     範例：上一條指令 lw $t0, 0($t1) (結果到 $t0，要到 WB 才寫回)
        #           當前指令 beq $t0, $t2, Label
        #           需要比較 $t0 和 $t2，但 $t0 還沒寫回，會出錯，需要 stall。
        #
        #     如果上面對於 ex_dest, mem_dest, wb_dest 都一律 hazard，就已經能 cover 了。
        #

        # 如果都沒有偵測到 hazard，則回傳 False
        return False
                    
    def run(self):
        """
        Run the pipeline until all instructions are executed
        """
        max_line = len(self.instructions)
        while True:
            if self.cycle > 10: return
            # Terminate if all instructions have completed WB
            if self.WB_over == max_line:
                self.output_result()
                break

            self.cycle += 1
            stages = {"IF": None, "ID": None, "EX": None, "MEM": None, "WB": None}  # 初始化階段輸出

            # Proceed stages if not stalled
            if not self.stall:
                if self.pipeline_instructions["MEM"] is not None:
                    self.WB()
                    stages["WB"] = self.pipeline_instructions["WB"]
                    self.pipeline_instructions["MEM"] = None

                if self.pipeline_instructions["EX"] is not None:
                    self.MEM()
                    stages["MEM"] = self.pipeline_instructions["MEM"]
                    self.pipeline_instructions["EX"] = None

                if self.pipeline_instructions["ID"] is not None:
                    self.EX()
                    stages["EX"] = self.pipeline_instructions["EX"]
                    self.pipeline_instructions["ID"] = None

                if self.pipeline_instructions["IF"] is not None:
                    self.ID()
                    stages["ID"] = self.pipeline_instructions["ID"]
                    self.pipeline_instructions["IF"] = None

            # Fetch new instruction if IF stage is free and not stalled
            if self.pipeline_instructions["IF"] is None and self.pc < max_line:
                self.IF()
                stages["IF"] = self.pipeline_instructions["IF"]

            # Output the current pipeline state in sorted stage order
            output = [f"{stage}:{instruction}" for stage, instruction in stages.items() if instruction is not None]
            print(f"cycle:{self.cycle} | " + " | ".join(output))

            # Reset WB stage to prevent duplicate executions
            self.pipeline_instructions["WB"] = None



    def output_result(self):
        print(f"需要花 {self.cycle} 個 cycles")
        print(" ".join(f"${i}" for i in range(32)))
        print(" ".join(f" {reg} " for reg in self.registers))
        print(" ".join(f"W{i}" for i in range(32)))
        print(" ".join(f" {mem} " for mem in self.memory))

# Example usage:
instructions = [
    "lw 2, 8(0)",  
    "lw 3, 16(0)",  
    "beq 2, 3, 1", # 因為 rs, rt 使用到前面將更新的值會發生data_Hatard 所以要stall，等前面WB
    "add 4, 2, 3",   
    "sw 4, 24(0)",   
]

if __name__ == "__main__":
    input_file = "./inputs/test3.txt"
    # user_input = input("Run File Name: ")
    # print(f"You entered: {user_input}")
    # input_file = f"./inputs/{user_input}.txt"
    mips = MIPS_Pipeline()
    mips.load_instructions_from_file(input_file)
    mips.run()
