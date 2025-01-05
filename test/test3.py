"""
GPT 生成
"""
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

        # Flags
        self.beq = 0
        self.stall = 0

    def load_instructions(self, instructions):
        self.instructions = instructions

    def IF(self):
        """
        Fetch the instruction from instruction memory
        Update the next address of instruction
        """
        if self.pcount < len(self.instructions):
            instruction = self.instructions[self.pcount]
            op, *args = instruction.split()
            self.pipeline_instructions["IF"] = f"{op}"

            # Pass instruction to next stage
            self.pipeline_registers["IF/ID"] = {"instruction": instruction}

    def ID(self):
        """
        Decode R-format, I-format, and Branch instructions
        Setting control signals
        """
        if "instruction" in self.pipeline_registers["IF/ID"]:
            instruction = self.pipeline_registers["IF/ID"]["instruction"]
            op, *args = instruction.split()

            # Add to ID
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
                rs, rt, offset = map(str, args[0:3])
                rs = int(rs.strip(','))
                rt = int(rt.strip(','))
                offset = int(offset)
                if self.registers[rs] == self.registers[rt]:
                    self.pc += offset
                    self.beq = 1  # Branch taken
                else:
                    self.beq = 0  # Branch not taken
                return

            # ALUSrc = 0 Using registers(R-f)；ALUSrc = 1 Using immediate value(I-f)
            if control_signals["ALUSrc"] == 0:
                rd, rs, rt = map(str, args[0:3])
                rd = int(rd.strip(','))
                rs = int(rs.strip(','))
                rt = int(rt.strip(','))
                result = {"rd": rd, "rs": rs, "rt": rt}
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

            # Add to EX
            self.pipeline_instructions["EX"] = f"{op}"

            # Forwarding logic
            if control_signals["ALUOp"] == "10":
                rd = result["rd"]
                rs = result["rs"]
                rt = result["rt"]
                rs_value = self.registers[rs]
                rt_value = self.registers[rt]

                if "result" in self.pipeline_registers["MEM/WB"]:
                    if rs == self.pipeline_registers["MEM/WB"]["result"].get("rd", -1):
                        rs_value = self.pipeline_registers["MEM/WB"]["result"]["value"]
                    if rt == self.pipeline_registers["MEM/WB"]["result"].get("rd", -1):
                        rt_value = self.pipeline_registers["MEM/WB"]["result"]["value"]

                if op == "add":
                    result = {"rd": rd, "value": rs_value + rt_value}
                elif op == "sub":
                    result = {"rd": rd, "value": rs_value - rt_value}
            else:
                rt = result["rt"]
                offset = result["offset"]
                rs = result["rs"]
                result = {"rt": rt, "offset": self.registers[rs] + offset}

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
            control_signals = self.pipeline_registers["EX/MEM"]["control_signals"]

            # Add to MEM
            self.pipeline_instructions["MEM"] = f"{op}"

            if control_signals["MemRead"]:
                value = self.memory[result["offset"]]
                rt = result["rt"]
                result = {"rt": rt, "value": value}
                self.pipeline_registers["MEM/WB"] = {
                    "op": op,
                    "result": result,
                    "control_signals": control_signals,
                }
            elif control_signals["MemWrite"]:
                rt = result["rt"]
                offset = result["offset"]
                self.memory[offset] = self.registers[rt]
                self.pipeline_registers["MEM/WB"] = {
                    "op": op,
                    "control_signals": control_signals,
                }
            elif control_signals["RegWrite"]:
                self.pipeline_registers["MEM/WB"] = self.pipeline_registers["EX/MEM"]

    def WB(self):
        """
        Write back stage
        """
        if "op" in self.pipeline_registers["MEM/WB"]:
            op = self.pipeline_registers["MEM/WB"]["op"]
            control_signals = self.pipeline_registers["MEM/WB"]["control_signals"]

            # Add to WB
            self.pipeline_instructions["WB"] = f"{op}"

            if control_signals["RegWrite"]:
                if control_signals["MemtoReg"]:
                    rt = int(self.pipeline_registers["MEM/WB"]["result"]["rt"])
                    value = self.pipeline_registers["MEM/WB"]["result"]["value"]
                    self.registers[rt] = value
                else:
                    rd = self.pipeline_registers["MEM/WB"]["result"]["rd"]
                    result = self.pipeline_registers["MEM/WB"]["result"]["value"]
                    self.registers[rd] = result

    def step(self):
        """
        Calculate cycle and execute pipeline
        """
        self.cycle += 1

        if self.pipeline_instructions["MEM"] is not None:
            self.WB()
            self.pipeline_instructions["MEM"] = None
            self.pc += 1

        if self.pipeline_instructions["EX"] is not None:
            self.MEM()
            self.pipeline_instructions["EX"] = None

        if self.pipeline_instructions["ID"] is not None:
            self.EX()
            self.pipeline_instructions["ID"] = None

        if self.pipeline_instructions["IF"] is not None:
            self.ID()
            self.pipeline_instructions["IF"] = None

        if self.pipeline_instructions["IF"] is None:
            self.IF()

        print(f"cycle:{self.cycle}:{self.pipeline_instructions}")
        self.pipeline_instructions["WB"] = None

        if self.pcount < len(self.instructions):
            self.pcount += 1

    def run(self):
        """
        Run the pipeline until all instructions are executed
        """
        while self.pc < len(self.instructions):
            self.step()

    def print_state(self):
        """
        Print the current state of the pipeline
        """
        print("Registers:", self.registers)
        print("Memory:", self.memory)

# Example usage:
instructions = [
    "lw 2, 8(0)",
    "lw 3, 16(0)",
    "beq 20, 21, 1",
    "add 4, 2, 3",
    "sw 4, 24(0)",
]

mips = MIPS_Pipeline()
mips.load_instructions(instructions)
mips.run()
