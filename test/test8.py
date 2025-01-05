"""
GPT 生成
"""
import os
from typing import List, Dict

class MIPSInstruction:
    def __init__(self, instruction: str):
        parts = instruction.split()
        self.opcode = parts[0]
        self.operands = parts[1:]

class PipelinedMIPSSimulator:
    def __init__(self):
        self.registers = [1] * 32
        self.memory = [1] * 32
        self.cycles = 0
        self.pipeline = {"IF": None, "ID": None, "EX": None, "MEM": None, "WB": None}
        self.forwarding = {"EX_MEM": None, "MEM_WB": None}
        self.stalls = 0

    def load_instructions(self, filepath: str) -> List[MIPSInstruction]:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        return [MIPSInstruction(line.strip()) for line in lines if line.strip()]

    def simulate(self, instructions: List[MIPSInstruction]):
        instruction_pointer = 0
        while instruction_pointer < len(instructions) or any(self.pipeline.values()):
            self.cycles += 1
            self.resolve_hazards()
            self.advance_pipeline(instructions, instruction_pointer)
            if self.pipeline["IF"] is None and instruction_pointer < len(instructions):
                self.pipeline["IF"] = instructions[instruction_pointer]
                instruction_pointer += 1

    def resolve_hazards(self):
        # Data Hazard: Implement forwarding and stalling
        if self.pipeline["EX"] and self.pipeline["ID"]:
            ex_instr = self.pipeline["EX"]
            id_instr = self.pipeline["ID"]

            if ex_instr.opcode in ["add", "sub", "lw"] and id_instr.opcode in ["add", "sub", "lw"]:
                ex_dest = ex_instr.operands[0].replace(',', '')
                id_src1 = id_instr.operands[1].replace(',', '')
                id_src2 = id_instr.operands[2].replace(',', '') if len(id_instr.operands) > 2 else None

                if ex_dest in [id_src1, id_src2]:
                    self.stalls += 1
                    self.pipeline["WB"] = self.pipeline["MEM"]
                    self.pipeline["MEM"] = self.pipeline["EX"]
                    self.pipeline["EX"] = None  # Stall EX stage

        # Control Hazard: Predict not taken and resolve
        if self.pipeline["ID"] and self.pipeline["ID"].opcode == "beq":
            beq_instr = self.pipeline["ID"]
            src1 = int(self.registers[int(beq_instr.operands[0].replace(',', '').strip()[1:])])
            src2 = int(self.registers[int(beq_instr.operands[1].replace(',', '').strip()[1:])])

            if src1 == src2:  # Branch taken
                self.pipeline = {"IF": None, "ID": None, "EX": None, "MEM": None, "WB": None}
                self.stalls += 2


    def advance_pipeline(self, instructions: List[MIPSInstruction], instruction_pointer: int):
        # Move stages WB -> MEM -> EX -> ID -> IF
        self.pipeline["WB"] = self.pipeline["MEM"]
        self.pipeline["MEM"] = self.pipeline["EX"]
        self.pipeline["EX"] = self.pipeline["ID"]
        self.pipeline["ID"] = self.pipeline["IF"]
        self.pipeline["IF"] = None

        # Execute each stage
        if self.pipeline["WB"]:
            self.write_back(self.pipeline["WB"])
        if self.pipeline["MEM"]:
            self.memory_access(self.pipeline["MEM"])
        if self.pipeline["EX"]:
            self.execute_instruction(self.pipeline["EX"])
        if self.pipeline["ID"]:
            self.decode_instruction(self.pipeline["ID"])

    def decode_instruction(self, instruction: MIPSInstruction):
        # Placeholder for decoding logic
        pass

    def execute_instruction(self, instruction: MIPSInstruction):
        # Placeholder for ALU operation
        pass

    def memory_access(self, instruction: MIPSInstruction):
        # Placeholder for memory read/write
        pass

    def write_back(self, instruction: MIPSInstruction):
        # Placeholder for write-back logic
        pass

    def output_results(self, output_filepath: str):
        with open(output_filepath, 'w') as f:
            f.write(f"Total Cycles: {self.cycles}\n")
            f.write(f"Stalls: {self.stalls}\n")
            f.write(f"Registers: {self.registers}\n")
            f.write(f"Memory: {self.memory}\n")

if __name__ == "__main__":
    simulator = PipelinedMIPSSimulator()
    input_filepath = "inputs/test3.txt"
    output_filepath = "outputs/result.txt"

    if not os.path.exists("outputs"):
        os.makedirs("outputs")

    instructions = simulator.load_instructions(input_filepath)
    simulator.simulate(instructions)
    simulator.output_results(output_filepath)

    print(f"Simulation completed. Results saved to {output_filepath}.")
