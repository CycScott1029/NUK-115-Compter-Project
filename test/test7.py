"""
GPT 生成
"""
class MIPS_Pipeline:
    def __init__(self):
        # Initialize pipeline resources
        self.registers = [0] * 32  # 32 general-purpose registers
        self.memory = [0] * 32     # Memory for load/store instructions
        self.instructions = []     # List of instructions to execute

        # Initialize pipeline stages
        self.pipeline_stages = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None
        }

        # Initialize intermediate registers for pipeline stages
        self.intermediate_registers = {
            "IF/ID": None,
            "ID/EX": None,
            "EX/MEM": None,
            "MEM/WB": None
        }

        # State variables
        self.pc = 0                 # Program counter
        self.clock_cycle = 0        # Track cycles
        self.stall = False          # Flag for stalls
        self.hazard_detected = False  # Track hazards

    def load_instructions(self, instructions):
        """ Load a list of instructions into the instruction memory. """
        self.instructions = instructions

    def fetch(self):
        """ Instruction Fetch stage (IF). """
        if self.pc < len(self.instructions):
            instruction = self.instructions[self.pc]
            self.intermediate_registers["IF/ID"] = instruction
            self.pipeline_stages["IF"] = instruction.split()[0]  # Save the opcode
            self.pc += 1
        else:
            self.intermediate_registers["IF/ID"] = None
            self.pipeline_stages["IF"] = None

    def decode(self):
        """ Instruction Decode stage (ID). """
        instruction = self.intermediate_registers["IF/ID"]
        if instruction:
            op, *args = instruction.split()
            self.pipeline_stages["ID"] = op

            # Hazard detection
            if self.detect_hazard(op, args):
                self.stall = True
                return

            # Prepare control signals and operands for the EX stage
            self.intermediate_registers["ID/EX"] = self.prepare_execution(op, args)
        else:
            self.pipeline_stages["ID"] = None

    def execute(self):
        """ Execute stage (EX). """
        if self.intermediate_registers["ID/EX"]:
            operation = self.intermediate_registers["ID/EX"]
            result = self.perform_operation(operation)
            self.intermediate_registers["EX/MEM"] = result
            self.pipeline_stages["EX"] = operation["op"]
        else:
            self.pipeline_stages["EX"] = None

    def memory_access(self):
        """ Memory access stage (MEM). """
        if self.intermediate_registers["EX/MEM"]:
            operation = self.intermediate_registers["EX/MEM"]
            result = self.perform_memory_operation(operation)
            self.intermediate_registers["MEM/WB"] = result
            self.pipeline_stages["MEM"] = operation["op"]
        else:
            self.pipeline_stages["MEM"] = None

    def write_back(self):
        """ Write-back stage (WB). """
        if self.intermediate_registers["MEM/WB"]:
            operation = self.intermediate_registers["MEM/WB"]
            self.perform_write_back(operation)
            self.pipeline_stages["WB"] = operation["op"]
        else:
            self.pipeline_stages["WB"] = None

    def detect_hazard(self, op, args):
        """ Detect hazards and return True if a stall is needed. """
        if op in ["add", "sub", "lw"]:
            # Check if current instruction depends on results not yet written back
            if self.pipeline_stages["EX"] == "lw":
                if args[1] in self.intermediate_registers["ID/EX"]["result"]:
                    return True
        return False

    def prepare_execution(self, op, args):
        """ Prepare the operands and control signals for execution. """
        if op == "add":
            rd, rs, rt = map(int, args)
            return {"op": "add", "rd": rd, "rs": rs, "rt": rt}
        elif op == "lw":
            rt, offset_base = args
            offset, base = map(int, offset_base.strip(')').split('('))
            return {"op": "lw", "rt": int(rt.strip(',')), "offset": offset, "base": base}
        elif op == "sw":
            rt, offset_base = args
            offset, base = map(int, offset_base.strip(')').split('('))
            return {"op": "sw", "rt": int(rt.strip(',')), "offset": offset, "base": base}
        return {}

    def perform_operation(self, operation):
        """ Perform ALU operations in the execute stage. """
        if operation["op"] == "add":
            rd = operation["rd"]
            rs = operation["rs"]
            rt = operation["rt"]
            value = self.registers[rs] + self.registers[rt]
            return {"op": "add", "rd": rd, "value": value}
        elif operation["op"] == "lw":
            base = operation["base"]
            offset = operation["offset"]
            rt = operation["rt"]
            address = self.registers[base] + offset
            return {"op": "lw", "rt": rt, "address": address}
        elif operation["op"] == "sw":
            base = operation["base"]
            offset = operation["offset"]
            rt = operation["rt"]
            address = self.registers[base] + offset
            return {"op": "sw", "rt": rt, "address": address}

    def perform_memory_operation(self, operation):
        """ Handle memory access for lw and sw instructions. """
        if operation["op"] == "lw":
            address = operation["address"]
            rt = operation["rt"]
            value = self.memory[address]
            return {"op": "lw", "rt": rt, "value": value}
        elif operation["op"] == "sw":
            address = operation["address"]
            rt = operation["rt"]
            self.memory[address] = self.registers[rt]
        return operation

    def perform_write_back(self, operation):
        """ Write the results back to the register file. """
        if operation["op"] == "add":
            rd = operation["rd"]
            self.registers[rd] = operation["value"]
        elif operation["op"] == "lw":
            rt = operation["rt"]
            self.registers[rt] = operation["value"]

    def run(self):
        """ Execute the pipeline until all instructions are processed. """
        while True:
            self.clock_cycle += 1
            print(f"Cycle {self.clock_cycle}: {self.pipeline_stages}")

            self.write_back()
            self.memory_access()
            self.execute()
            self.decode()
            self.fetch()

            # Check for termination
            if not any(self.pipeline_stages.values()):
                break

        print(f"Execution completed in {self.clock_cycle} cycles.")

# Example usage
instructions = [
    "lw 2, 0(1)",
    "lw 3, 4(1)",
    "add 4, 2, 3",
    "sw 4, 8(1)"
]

pipeline = MIPS_Pipeline()
pipeline.load_instructions(instructions)
pipeline.run()
