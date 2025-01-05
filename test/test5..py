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
        self.pcount = 0
        self.cycle = 0
        # Instruction memory
        self.instructions = []

        #flags
        self.stall = False

    def load_instructions(self, instructions):
        self.instructions = instructions

    def IF(self):
        """
        Fetch the instruction from instruction memory
        Update the next address of instruction
        """
        # Fetch the instruction
        instruction = self.instructions[self.pc]
        # add op to IF
        op, *args = instruction.split()
        self.pipeline_instructions["IF"] = f"{op}"

        # instruction to next stage
        self.pipeline_registers["IF/ID"] = {"instruction": instruction}
            
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
                    print("Hazard")
                    self.stall = True
                    self.pc -= 1
                    return
                offset = int(offset)
                if self.registers[rs] == self.registers[rt]:
                    # 重取 pc 進入 IF stage
                    self.pc += offset
                return
            
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
            else: 
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

    def detect_hazard(self):
        """
        Detect if data hazard occurs
        Return True if hazard is detected, else False
        """
        if "result" in self.pipeline_registers["ID/EX"]:
            # Get current instruction in ID stage
            id_instruction = self.pipeline_registers["IF/ID"].get("instruction", "")
            if not id_instruction:
                return False

            op, *args = id_instruction.split()
            current_registers = []

            # 分辨 op 因為不同 op 切分方式是不同的
            if op in ["add", "sub", "beq"]:
                rs, rt = map(lambda x: int(x.strip(",")), args[:2])
                current_registers.extend([rs, rt])
            elif op in ["lw", "sw"]:
                rt, offset_rs = args
                rs = int(offset_rs.strip(')').split('(')[1])
                rt = int(rt.strip(","))
                current_registers.extend([rs, rt])

            # Compare with registers in ID/EX stage
            ex_result = self.pipeline_registers["ID/EX"].get("result", {})
            ex_registers = [ex_result.get("rd"), ex_result.get("rt")]

            for reg in current_registers:
                if reg in ex_registers:
                    return True

        return False
                
    def run(self):
        """
        Run the pipeline until all instructions are executed
        """
        max_line = len(self.instructions)
        while True :
            if self.cycle > 10 : return
            self.cycle += 1

            if (self.pipeline_instructions["MEM"] is not None) and self.stall != True:
                self.WB()
                self.pipeline_instructions["MEM"] = None
                self.pc += 1 
                # End loop
                if self.pc > max_line: return

            if (self.pipeline_instructions["EX"] is not None) and self.stall != True:
                self.MEM()
                self.pipeline_instructions["EX"] = None

            if (self.pipeline_instructions["ID"] is not None) and self.stall != True:
                self.EX()
                self.pipeline_instructions["ID"] = None

            if (self.pipeline_instructions["IF"] is not None) and self.stall != True:
                self.ID()
                if self.stall != True:
                    self.pipeline_instructions["IF"] = None

            if (self.pipeline_instructions["IF"] is None) and self.stall != True:
                self.IF()
                self.pc += 1

            # 解除 stall
            self.stall = False

            print(f"cycle:{self.cycle}:{self.pipeline_instructions}")
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

mips = MIPS_Pipeline()
mips.load_instructions(instructions)
mips.run()
