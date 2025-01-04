from Load_Instruction import read_instructions, parse_instruction
from Pipeline_Inspector import PipelineInspector

class MIPS_Simulator:
    def __init__(self, file_path):
        self.instruction_memory = self.load_instruction(file_path)
        self.register_file = {f'${i}': 0 for i in range(32)}
        self.data_memory = {}
        self.instruction_in_stages = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None
        }
        self.pipeline_registers = {
            "IF/ID": None,
            "ID/EX": None,
            "EX/MEM": None,
            "MEM/WB": None
        }
        self.controls = {
            "RegDst": False,
            "ALUSrc": False,
            "Branch ": False,
            "MemRead": False,
            "MemWrite": False,
            "RegWrite": False,
            "MemtoReg": False
        }
        self.inspector = PipelineInspector()
        self.program_counter = 0
        self.cycles = 0

    def load_instruction(file_path):
        parsed_inst = []
        instructions = read_instructions(file_path)

        for instruction in instructions:
            parsed_inst.append(parse_instruction(instruction))
        
        return parsed_inst
    
    def IF(self):
        pass

    def ID(self):
        pass

    def EX(self):
        pass

    def MEM(self):
        pass

    def WB(self):
        pass

    def run(self):
        pass


if __name__ == "__main__":
    Sim = MIPS_Simulator(file_path="./inputs/test3.txt")
    Sim.run()