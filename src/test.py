"""
GPT 生成
"""
class MIPS_Pipeline:
    def __init__(self):
        self.registers = [1] * 32
        self.registers[0] = 0
        self.memory = [1] * 32
        self.pipeline_instructions = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }
        self.pipeline_registers = {
            "IF/ID": None,
            "ID/EX": None,
            "EX/MEM": None,
            "MEM/WB": None,
        }
        self.pc = 0
        self.instructions = []
        self.cycles = 0
        self.stall = False

    def load_instructions(self, instructions):
        self.instructions = instructions

    def IF(self):
        if self.stall:
            return  # Stall prevents fetching
        if self.pc < len(self.instructions):
            self.pipeline_registers["IF/ID"] = {"instruction": self.instructions[self.pc]}
            self.pc += 1
        else:
            self.pipeline_registers["IF/ID"] = None

    def ID(self):
        if self.pipeline_registers["IF/ID"] is None:
            self.pipeline_registers["ID/EX"] = None
            return

        instruction = self.pipeline_registers["IF/ID"]["instruction"]
        op, *args = instruction.split()

        # Strip trailing commas from arguments
        args = [arg.strip(',') for arg in args]

        control_signals = {"RegWrite": False, "MemRead": False, "MemWrite": False, "ALUSrc": False}
        if op in ["add", "sub"]:
            control_signals["RegWrite"] = True
        elif op == "lw":
            control_signals["RegWrite"] = True
            control_signals["MemRead"] = True
            control_signals["ALUSrc"] = True
        elif op == "sw":
            control_signals["MemWrite"] = True
            control_signals["ALUSrc"] = True

        self.pipeline_registers["ID/EX"] = {"op": op, "args": args, "control": control_signals}

    def EX(self):
        if self.pipeline_registers["ID/EX"] is None:
            self.pipeline_registers["EX/MEM"] = None
            return

        stage = self.pipeline_registers["ID/EX"]
        op = stage["op"]
        args = stage["args"]
        result = None

        if op == "add":
            rd = int(args[0])
            rs = int(args[1])
            rt = int(args[2])
            result = {"rd": rd, "value": self.registers[rs] + self.registers[rt]}
        elif op == "sub":
            rd = int(args[0])
            rs = int(args[1])
            rt = int(args[2])
            result = {"rd": rd, "value": self.registers[rs] - self.registers[rt]}
        elif op in ["lw", "sw"]:
            rt = int(args[0])
            offset, base = args[1].split('(')
            base = int(base.strip(')'))
            offset = int(offset)
            address = self.registers[base] + offset
            result = {"address": address, "reg": rt}

        self.pipeline_registers["EX/MEM"] = {"op": op, "result": result, "control": stage["control"]}

    def MEM(self):
        if self.pipeline_registers["EX/MEM"] is None:
            self.pipeline_registers["MEM/WB"] = None
            return

        stage = self.pipeline_registers["EX/MEM"]
        op = stage["op"]
        result = stage["result"]

        if stage["control"]["MemRead"]:
            value = self.memory[result["address"]]
            result["value"] = value
        elif stage["control"]["MemWrite"]:
            self.memory[result["address"]] = self.registers[result["reg"]]

        self.pipeline_registers["MEM/WB"] = {"op": op, "result": result, "control": stage["control"]}

    def WB(self):
        if self.pipeline_registers["MEM/WB"] is None:
            return

        stage = self.pipeline_registers["MEM/WB"]
        op = stage["op"]
        result = stage["result"]

        if stage["control"]["RegWrite"]:
            if op == "add" or op == "sub":
                rd = result["rd"]
                self.registers[rd] = result["value"]
            elif op == "lw":
                rt = result["reg"]
                self.registers[rt] = result["value"]

    def detect_hazards(self):
        # Simple hazard detection: Stall if dependencies exist
        ex_stage = self.pipeline_registers["ID/EX"]
        mem_stage = self.pipeline_registers["EX/MEM"]

        if ex_stage and mem_stage:
            ex_op = ex_stage["op"]
            mem_op = mem_stage["op"]

            if mem_op == "lw" and ex_op in ["add", "sub"]:
                if ex_stage["args"][1] == mem_stage["result"]["reg"] or ex_stage["args"][2] == mem_stage["result"]["reg"]:
                    self.stall = True
                    return

        self.stall = False

    def step(self):
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()
        self.detect_hazards()

        self.cycles += 1
        self.print_pipeline()

    def print_pipeline(self):
        print(f"Cycle {self.cycles}")
        for stage, content in self.pipeline_registers.items():
            print(f"{stage}: {content}")
        print("-" * 40)

    def run(self):
        while self.pc < len(self.instructions) or any(self.pipeline_registers.values()):
            self.step()

# Example usage
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

pipeline = MIPS_Pipeline()
pipeline.load_instructions(instructions)
pipeline.run()
