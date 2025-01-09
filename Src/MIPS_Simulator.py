from MIPS_instruction import MIPS_Instruction
from Load_Instruction import read_instructions, parse_instruction
import os
import sys

class MIPS_Simulator:
    def __init__(self, file_path):
        self.instruction_memory = read_instructions(file_path) # List of instructions
        self.register_file = {}
        self.register_file["$0"] = 0
        for i in range(1, 32):
            self.register_file[f'${i}'] = 1
        self.data_memory = {address: 1 for address in range(0, 4096, 4)}

        # Pipeline registers
        self.pipeline_registers = {
            "IF/ID": None,
            "ID/EX": None,
            "EX/MEM": None,
            "MEM/WB": None
        }

        # Stages tracking for printing
        self.instruction_in_stages = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None
        }

        self.predict_branch_result = False # Predict always taken for now
        self.branch_result = ''
        self.branch_from = 0
        self.program_counter = 1
        self.cycles = 1
        self.stall = False
        self.end = False
    
    def IF(self):
        # Handle stall
        if self.stall or self.pipeline_registers['IF/ID'] or self.program_counter > len(self.instruction_memory):
            return
        
        # Read instruction from pc (minus 1 because instruction store in a list which index start with 0)
        _instruction = self.instruction_memory[self.program_counter - 1]
        parsed_instruction = None

        if _instruction:
            # Parse instruction
            parsed_instruction = parse_instruction(_instruction) 
            # Update program counter
            if parsed_instruction.opcode == 'beq':
                    self.branch_from = self.program_counter
                    if self.predict_branch_result:
                        self.program_counter = parsed_instruction.immediate + self.program_counter + 1
                    else:
                        self.program_counter = self.program_counter + 1
            else:
                self.program_counter = self.program_counter + 1

        self.instruction_in_stages['IF'] = parsed_instruction
        self.pipeline_registers['IF/ID'] = parsed_instruction
        
            

    def ID(self):
        # Handle stall
        if self.stall or self.pipeline_registers['ID/EX']:
            return
        
        # Read instruction
        _instruction = self.pipeline_registers['IF/ID']
        self.pipeline_registers['IF/ID'] = None
        self.instruction_in_stages['IF'] = None

        if _instruction:
            # Generate control signals
            self.set_control_signals(_instruction)

            # Read value from registers
            _instruction.rs_value = self.register_file[_instruction.rs]
            _instruction.rt_value = self.register_file[_instruction.rt]

        self.instruction_in_stages['ID'] = _instruction
        self.pipeline_registers['ID/EX'] = _instruction

    def EX(self):
        # Handle stall
        if self.stall or self.pipeline_registers['EX/MEM']:
            return
        
        # Read instruction
        _instruction = self.pipeline_registers['ID/EX']
        self.pipeline_registers['ID/EX'] = None
        self.instruction_in_stages['ID'] = None

        if _instruction:
            # Perform arithmetic calculation
            if _instruction.opcode == 'add':
                _instruction.result = _instruction.rs_value + _instruction.rt_value
            elif _instruction.opcode == 'sub':
                _instruction.result = _instruction.rs_value - _instruction.rt_value
            elif _instruction.opcode == 'beq':
                if _instruction.rs_value == _instruction.rt_value:
                    self.branch_result = True
                else:
                    self.branch_result = False
            
            # Validate prediction
            if _instruction.opcode == 'beq':
                if self.branch_result != self.predict_branch_result:
                    # Flush
                    self.pipeline_registers['ID/EX'] = None
                    self.pipeline_registers['IF/ID'] = None
                    if self.branch_result:
                        self.program_counter = _instruction.immediate + self.branch_from + 1
                    else:
                        self.program_counter = self.branch_from + 1
        
        self.instruction_in_stages['EX'] = _instruction
        self.pipeline_registers['EX/MEM'] = _instruction
        
        
    
    def MEM(self):
        # Read instruction
        _instruction = self.pipeline_registers['EX/MEM']
        self.pipeline_registers['EX/MEM'] = None
        self.instruction_in_stages['EX'] = None

        if _instruction:
            # Perform data movement
            if _instruction.opcode == 'lw':
                _instruction.result = self.data_memory[_instruction.rt_value * 4 + _instruction.immediate]
            elif _instruction.opcode == 'sw':
                self.data_memory[_instruction.rt_value * 4 + _instruction.immediate] = _instruction.rs_value

        self.instruction_in_stages['MEM'] = _instruction
        self.pipeline_registers['MEM/WB'] = _instruction

    def WB(self):
        # Read instruction
        _instruction = self.pipeline_registers['MEM/WB']
        self.pipeline_registers['MEM/WB'] = None
        self.instruction_in_stages['MEM'] = None

        if _instruction:
            # Write back to registers
            if _instruction.opcode == 'lw':
                self.register_file[_instruction.rs] = _instruction.result
            elif _instruction.opcode in ['add', 'sub']:
                self.register_file[_instruction.rd] = _instruction.result

        self.instruction_in_stages['WB'] = _instruction
        
    def display(self):
        print(f"Cycle: {self.cycles}")
        print(' ')
        display_sequence = ['WB', 'MEM', 'EX', 'ID', 'IF']
        for stage in display_sequence:
            output = ""
            signals = ""
            if self.instruction_in_stages[stage]:
                output += str(self.instruction_in_stages[stage].opcode) + " " + stage + " "
                if stage in ['WB', 'MEM', 'EX']:
                    signals +=  str(self.instruction_in_stages[stage].MemToReg) + str(self.instruction_in_stages[stage].RegWrite) + " "
                    if stage in ['MEM', 'EX']:
                        signals += str(self.instruction_in_stages[stage].MemWrite) + str(self.instruction_in_stages[stage].MemRead) + str(self.instruction_in_stages[stage].Branch) + " "
                        if stage == 'EX':
                            signals += str(self.instruction_in_stages[stage].ALUSrc) + str(self.instruction_in_stages[stage].RegDst)
                output += signals[::-1]
            if output != "":
                print(output)
        print(' ')
        print('--------')
        print(' ')

    def hazard_handler(self):
        self.stall = False

        if self.pipeline_registers['ID/EX']:
            checks = ['EX/MEM', 'MEM/WB']
            for pipReg in checks:
                if self.pipeline_registers[pipReg] and self.pipeline_registers[pipReg].opcode == 'lw':
                    if self.pipeline_registers['ID/EX'].rs == self.pipeline_registers[pipReg].rt:
                        if pipReg == 'MEM/WB':
                            self.pipeline_registers['ID/EX'].rs_value = self.pipeline_registers[pipReg].result
                            self.stall = True
                        else:
                            self.stall = True
                    elif self.pipeline_registers['ID/EX'].rt == self.pipeline_registers[pipReg].rt:
                        if pipReg == 'MEM/WB':
                            self.pipeline_registers['ID/EX'].rt_value = self.pipeline_registers[pipReg].result
                            self.stall = True
                        else:
                            self.stall = True
                elif self.pipeline_registers[pipReg] and self.pipeline_registers[pipReg].opcode in ['add', 'sub']:
                    if self.pipeline_registers['ID/EX'].rs == self.pipeline_registers[pipReg].rd:
                        self.pipeline_registers['ID/EX'].rs_value = self.pipeline_registers[pipReg].result
                        self.stall = True
                    elif self.pipeline_registers['ID/EX'].rt == self.pipeline_registers[pipReg].rd:
                        self.pipeline_registers['ID/EX'].rt_value = self.pipeline_registers[pipReg].result
                        self.stall = True


    def set_control_signals(self, instruction: MIPS_Instruction):
        op = instruction.opcode

        if op in ["add", "sub"]:
            instruction.RegDst = 1
            instruction.ALUSrc = 0
            instruction.MemToReg = 0
            instruction.RegWrite = 1
            instruction.MemRead = 0
            instruction.MemWrite = 0
            instruction.Branch = 0
            instruction.ALUOp = op
        elif op == "lw":
            instruction.RegDst = 0
            instruction.ALUSrc = 1
            instruction.MemToReg = 1
            instruction.RegWrite = 1
            instruction.MemRead = 1
            instruction.MemWrite = 0
            instruction.Branch = 0
            instruction.ALUOp = "add"
        elif op == "sw":
            instruction.RegDst = 0
            instruction.ALUSrc = 1
            instruction.MemToReg = 0
            instruction.RegWrite = 0
            instruction.MemRead = 0
            instruction.MemWrite = 1
            instruction.Branch = 0
            instruction.ALUOp = "add"
        elif op == "beq":
            instruction.RegDst = 0
            instruction.ALUSrc = 0
            instruction.MemToReg = 0
            instruction.RegWrite = 0
            instruction.MemRead = 0
            instruction.MemWrite = 0
            instruction.Branch = 1
            instruction.ALUOp = "sub"

    def run(self):
        if self.program_counter > len(self.instruction_memory) and all(stage is None for stage in self.pipeline_registers.values()):
            self.end = True
            return True
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()
        self.display()
        self.hazard_handler()
        self.cycles += 1
        return False

if __name__ == "__main__":
        for filename in os.listdir("./inputs/"):
            file_path = os.path.join("./inputs/", filename)
            with open(f'output{filename}', 'w') as file:
                original_stdout = sys.stdout
                sys.stdout = file
                
                print(f'Load test instruction from {filename}')
                Sim = MIPS_Simulator(file_path=file_path)
                while not Sim.run():
                    pass

                sys.stdout = original_stdout