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
        # Instruction memory
        self.instructions = []

        #flags
        self.beq = 0

    def load_instructions(self, instructions):
        self.instructions = instructions

    def IF(self):
        """
        Fetch the instruction from instruction memory
        Update the next address of instruction
        """
        if self.pc < len(self.instructions):
            instruction = self.instructions[self.pc]
            self.pipeline_registers["IF/ID"] = {"instruction": instruction}
            print(f"pc:{self.pc}, {instruction}")
            self.pc += 1
            
    def ID(self):
        """
        Decode R-format, I-format, and Branch instructions
        Setting control signals
        """
        if "instruction" in self.pipeline_registers["IF/ID"]:
            instruction = self.pipeline_registers["IF/ID"]["instruction"]
            op, *args = instruction.split()

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
                offset = int(offset)
                if self.registers[rs] == self.registers[rt]:
                    self.pc += offset
                self.beq = 1
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
        if "op" in self.pipeline_registers["ID/EX"]:
            op = self.pipeline_registers["ID/EX"]["op"]
            result = self.pipeline_registers["ID/EX"]["result"]
            control_signals = self.pipeline_registers["ID/EX"]["control_signals"]
            
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
        if "op" in self.pipeline_registers["EX/MEM"]:
            op = self.pipeline_registers["EX/MEM"]["op"]
            result = self.pipeline_registers["EX/MEM"]["result"]
            control_signals = self.pipeline_registers["ID/EX"]["control_signals"]
            # Lw
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

             # 'add' and 'sub'
            elif control_signals["RegWrite"]: 
                self.pipeline_registers["MEM/WB"] = self.pipeline_registers["EX/MEM"]


    def WB(self):
        """
        Write back stage
        """
        if "op" in self.pipeline_registers["MEM/WB"]:
            control_signals = self.pipeline_registers["ID/EX"]["control_signals"]

            if control_signals["RegWrite"]:
                # lw
                if control_signals["MemtoReg"]:
                    rt = int(self.pipeline_registers["MEM/WB"]["result"]["rt"])
                    value = self.pipeline_registers["MEM/WB"]["result"]["value"] 
                    print(f"lw:{self.registers[rt]}]={value}")
                    self.registers[rt] = value
                    
                # 'add' and 'sub'
                else:
                    rd = (self.pipeline_registers["MEM/WB"]["result"]["rd"])
                    result = self.pipeline_registers["MEM/WB"]["result"]["value"]
                    self.registers[rd] = result


    def step(self):
        """
        
        """
        self.IF()
        self.ID()
        
        if self.beq == 1:
            self.beq = 0
            return
        
        self.EX()
        self.MEM()
        self.WB()
        
    def run(self):
        """
        Run the pipeline until all instructions are executed
        """
        while self.pc < len(self.instructions):
            self.step()
            self.print_state()

    def print_state(self):
        """
        Print the current state of the pipeline
        """
        print("Registers:", self.registers)
        print("Memory:", self.memory)
        
    def output_result(self):
        print(f"需要花 {self.cycle} 個 cycles")
        print(" ".join(f"${i}" for i in range(32)))
        print(" ".join(f" {reg} " for reg in self.registers))
        print(" ".join(f"W{i}" for i in range(32)))
        print(" ".join(f" {mem} " for mem in self.memory))

# Example usage:
instructions = [
    "lw 2, 8(0)",  # $1 = $2 + $3
    "lw 3, 16(0)",  # $4 = $1 - $2
    "beq 2, 3, 1",
    "add 4, 2, 3",   # $1 = Memory[$1 + 0]
    "sw 4, 24(0)",   # Memory[$2 + 4] = $5
]
# lw $2, 8($0)
# lw $3, 16($0) 
# beq $2, $3, 1
# add $4, $2, $3
# sw $4, 24($0)

mips = MIPS_Pipeline()
mips.load_instructions(instructions)
mips.run()
