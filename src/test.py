import re
import sys

class MIPS_Pipeline:
    def __init__(self):
        # 32 registers and 32 word memory
        self.registers = [1] * 32
        self.registers[0] = 0
        self.memory = [1] * 32

        # control_signals
        self.control_signals = {
                "RegDst": 0,
                "ALUSrc": 0,
                "MemtoReg": 0,
                "RegWrite": 0,
                "MemRead": 0,
                "MemWrite": 0,
                "Branch": 0,
                "ALUOp": "00",
        }
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
        self.instructions = instructions

    def IF(self):
        """
        Fetch the instruction from instruction memory
        Update the next address of instruction
        """
            
    def ID(self):
        """
        Decode R-format, I-format, and Branch instructions
        Setting control signals
        """

    def EX(self):
        """
        Execute the instruction
        """

    def MEM(self):
        """
        Memory access stage
        """

    def WB(self):
        """
        Write back stage
        """

    def detect_hazard(self):
        """
        Detect if data hazard occurs
        Return True if hazard is detected, else False
        """
                    
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

                if (self.pipeline_instructions["IF"] is not None):
                    self.ID()
                    stages["ID"] = self.pipeline_instructions["ID"]
                    self.pipeline_instructions["IF"] = None

            # Fetch new instruction if IF stage is free and not stalled
            if self.pipeline_instructions["IF"] is None and self.pc < max_line:
                self.IF()
                stages["IF"] = self.pipeline_instructions["IF"]

            # Output the current pipeline state in sorted stage order
            output = [f"{stage}:{instruction}" for stage, instruction in stages.items() ] #if instruction is not None]
            print(f"cycle:{self.cycle} | " + " | ".join(output))

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
    "beq 2, 3, 1", 
    "add 4, 2, 3",   
    "sw 4, 24(0)",   
]

if __name__ == "__main__":
    mips = MIPS_Pipeline()
    mips.load_instructions(instructions)
    mips.run()
