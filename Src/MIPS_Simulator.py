from Load_Instruction import read_instructions, parse_instruction
from MIPS_instruction import MIPS_Instruction

class MIPS_Simulator:
    def __init__(self, file_path):
        self.instruction_memory = read_instructions(file_path)
        self.register_file = {f'${i}': 0 for i in range(32)}
        self.data_memory = {i: 0 for i in range(0, 4096, 4)} # 4KB memory
        
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
        
        # pipeline indicator
        self.program_counter = 0
        self.cycles = 0
        self.end = False
        
        # branch prediction
        self.branch_predictor = "not_taken"
        self.predicted_pc = None
    
    def IF(self):
        if self.pipeline_registers["IF/ID"] and self.pipeline_registers["IF/ID"]["instruction"].stall:
            print(f"[Cycle {self.cycles}] IF: Instruction stalled (PC = {self.program_counter})")
            return
        
        # Check if the program counter is valid (not None and within instruction memory bounds)
        if self.program_counter is None or self.program_counter >= len(self.instruction_memory):
            self.instruction_in_stages["IF"] = None
            self.end = True
            return

        instruction_text = self.instruction_memory[self.program_counter]
        instruction = parse_instruction(instruction_text)

        if instruction.opcode in {"beq", "j"}:
            self.predicted_pc = self.program_counter + 1  # Update PC for branch instructions
        
        self.pipeline_registers["IF/ID"] = {
            "instruction": instruction,
            "pc": self.program_counter
        }

        self.program_counter = self.predicted_pc
        self.instruction_in_stages["IF"] = instruction.raw_instruction


    def ID(self):
        if self.pipeline_registers["IF/ID"] is None:
            self.instruction_in_stages["ID"] = None
            return

        instruction = self.pipeline_registers["IF/ID"]["instruction"]

        # Handle stalls in ID stage
        if instruction.stall:
            self.instruction_in_stages["ID"] = instruction.raw_instruction
            return
        
        rs_val = self.register_file.get(instruction.rs, 0)
        rt_val = self.register_file.get(instruction.rt, 0)

        # Detect hazards and stalls
        stall = False
        if self.pipeline_registers["ID/EX"]:
            prev_instruction = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instruction.rd in {instruction.rs, instruction.rt}:
                if prev_instruction.opcode == "lw":
                    stall = True
                    instruction.stall = True
                    print(f"[Cycle {self.cycles}] ID: Stalling due to load-use hazard on {instruction.raw_instruction}")
                    return

        # Update control signals
        if instruction.opcode == "add" or instruction.opcode == "sub":
            instruction.RegDst = 1
            instruction.ALUSrc = 0
            instruction.MemToReg = 0
            instruction.RegWrite = 1
            instruction.MemRead = 0
            instruction.MemWrite = 0
            instruction.Branch = 0
            instruction.ALUOp = instruction.opcode
        elif instruction.opcode == "lw":
            instruction.RegDst = 0
            instruction.ALUSrc = 1
            instruction.MemToReg = 1
            instruction.RegWrite = 1
            instruction.MemRead = 1
            instruction.MemWrite = 0
            instruction.Branch = 0
            instruction.ALUOp = "add"
        elif instruction.opcode == "sw":
            instruction.RegDst = 0
            instruction.ALUSrc = 1
            instruction.MemToReg = 0
            instruction.RegWrite = 0
            instruction.MemRead = 0
            instruction.MemWrite = 1
            instruction.Branch = 0
            instruction.ALUOp = "add"
        elif instruction.opcode == "beq":
            instruction.RegDst = 0
            instruction.ALUSrc = 0
            instruction.MemToReg = 0
            instruction.RegWrite = 0
            instruction.MemRead = 0
            instruction.MemWrite = 0
            instruction.Branch = 1
            instruction.ALUOp = "sub"

        self.pipeline_registers["ID/EX"] = {
            "instruction": instruction,
            "rs_val": rs_val,
            "rt_val": rt_val,
            "rd": instruction.rd,
            "immediate": instruction.immediate,
            "stall": stall,
            "pc": self.pipeline_registers["IF/ID"]["pc"]
        }

        self.pipeline_registers["IF/ID"] = None
        self.instruction_in_stages["ID"] = instruction.raw_instruction

    def EX(self):
        if self.pipeline_registers["ID/EX"] is None:
            self.instruction_in_stages["EX"] = None
            return

        instruction = self.pipeline_registers["ID/EX"]["instruction"]

        if instruction.stall:
            self.instruction_in_stages["EX"] = instruction.raw_instruction
            return
        
        rs_val = self.pipeline_registers["ID/EX"]["rs_val"]
        rt_val = self.pipeline_registers["ID/EX"]["rt_val"]
        imm = self.pipeline_registers["ID/EX"]["immediate"]

        alu_result = None
        branch_target = None
        branch_taken = False

        if instruction.opcode in {"add", "sub", "and", "or"}:
            alu_result = rs_val + rt_val if instruction.opcode == "add" else (
                rs_val - rt_val if instruction.opcode == "sub" else (
                    rs_val & rt_val if instruction.opcode == "and" else rs_val | rt_val
                )
            )
        elif instruction.opcode in {"lw", "sw"}:
            alu_result = rs_val + imm
        elif instruction.opcode in {"beq", "bne"}:
            branch_target = self.pipeline_registers["ID/EX"]["pc"] + (imm << 2)
            branch_taken = (rs_val == rt_val) if instruction.opcode == "beq" else (rs_val != rt_val)

        self.pipeline_registers["EX/MEM"] = {
            "instruction": instruction,
            "alu_result": alu_result,
            "branch_target": branch_target,
            "branch_taken": branch_taken,
            "rs_val": rs_val,
            "rt_val": rt_val,
        }

        if branch_taken:
            self.program_counter = branch_target

        self.pipeline_registers["ID/EX"] = None
        self.instruction_in_stages["EX"] = instruction.raw_instruction


    def MEM(self):
        if self.pipeline_registers["EX/MEM"] is None:
            self.instruction_in_stages["MEM"] = None
            return

        # Fetch the instruction and metadata from EX/MEM pipeline register
        instruction = self.pipeline_registers["EX/MEM"]["instruction"]
        alu_result = self.pipeline_registers["EX/MEM"]["alu_result"]

        # Check if the instruction is stalled
        if instruction.stall:
            # If stalled, retain the instruction in the MEM stage without processing it
            self.instruction_in_stages["MEM"] = instruction.raw_instruction
            print(f"[Cycle {self.cycles}] MEM: Instruction stalled, not processing memory operation")
            return

        # Handle memory operations for lw and sw
        if instruction.opcode == "lw":
            # Load word from data memory at the address given by ALU result
            loaded_data = self.data_memory.get(alu_result, 0)  # Default to 0 if address is out of range
            print(f"[Cycle {self.cycles}] MEM: Loaded data {loaded_data} from memory address {alu_result}")
            # Pass the loaded data to the MEM/WB pipeline register
            self.pipeline_registers["MEM/WB"] = {
                "instruction": instruction,
                "data": loaded_data
            }
        elif instruction.opcode == "sw":
            # Store word to data memory at the address given by ALU result
            self.data_memory[alu_result] = self.pipeline_registers["EX/MEM"]["rs_val"]
            print(f"[Cycle {self.cycles}] MEM: Stored data {self.pipeline_registers['EX/MEM']['rs_val']} "
                f"to memory address {alu_result}")
            # No data is passed to MEM/WB for store instructions
            self.pipeline_registers["MEM/WB"] = None

        # Clear EX/MEM register after processing
        self.pipeline_registers["EX/MEM"] = None
        self.instruction_in_stages["MEM"] = instruction.raw_instruction

    def WB(self):
        if self.pipeline_registers["MEM/WB"] is None:
            self.instruction_in_stages["WB"] = None
            return

        # Fetch the instruction and metadata from MEM/WB pipeline register
        instruction = self.pipeline_registers["MEM/WB"]["instruction"]

        # Check if the instruction is stalled
        if instruction.stall:
            # If stalled, retain the instruction in the WB stage without performing write-back
            self.instruction_in_stages["WB"] = instruction.raw_instruction
            print(f"[Cycle {self.cycles}] WB: Instruction stalled, not writing back to register file")
            return

        # Write-back operation
        if instruction.RegWrite:
            # If it's a load instruction (lw), we write the loaded data from memory
            if instruction.opcode == "lw":
                data_to_write = self.pipeline_registers["MEM/WB"]["data"]
                print(f"[Cycle {self.cycles}] WB: Writing data {data_to_write} to register ${instruction.rd}")
                self.register_file[f'${instruction.rd}'] = data_to_write
            # For other instructions (add, sub, etc.), we write the ALU result
            else:
                print(f"[Cycle {self.cycles}] WB: Writing result {instruction.result} to register ${instruction.rd}")
                self.register_file[f'${instruction.rd}'] = instruction.result

        # Clear MEM/WB register after writing back
        self.pipeline_registers["MEM/WB"] = None
        self.instruction_in_stages["WB"] = instruction.raw_instruction

    def display(self):
        print(f"\n--- Cycle {self.cycles} ---")

        # Collect instructions per cycle
        instructions_per_cycle = {
            "IF": [],
            "ID": [],
            "EX": [],
            "MEM": [],
            "WB": []
        }

        # Iterate over the stages of the pipeline
        for stage in ["IF", "ID", "EX", "MEM", "WB"]:
            # Check if there is an instruction in the current stage
            if self.instruction_in_stages[stage]:
                instruction = self.instruction_in_stages[stage]
                instruction_data = self.pipeline_registers.get(f"{stage}/ID", None)

                # Collect the instructions for each cycle
                instructions_per_cycle[stage].append(instruction)

                # For each stage, print control signals in binary, excluding ALUOp
                if instruction_data:
                    if stage == "EX":
                        control_signals = [
                            instruction_data["instruction"].RegDst,
                            instruction_data["instruction"].ALUSrc,
                            instruction_data["instruction"].MemToReg,
                            instruction_data["instruction"].RegWrite,
                            instruction_data["instruction"].MemRead,
                            instruction_data["instruction"].MemWrite,
                            instruction_data["instruction"].Branch
                        ]
                        # Print 7-digit control signals for EX stage
                        control_signals_bin = ''.join([str(signal) for signal in control_signals])
                        print(f"    Control Signals (binary): {control_signals_bin}")

                    elif stage == "MEM":
                        control_signals = [
                            instruction_data["instruction"].MemToReg,
                            instruction_data["instruction"].RegWrite,
                            instruction_data["instruction"].MemRead,
                            instruction_data["instruction"].MemWrite
                        ]
                        # Print 5-digit control signals for MEM stage
                        control_signals_bin = ''.join([str(signal) for signal in control_signals])
                        print(f"    Control Signals (binary): {control_signals_bin}")

                    elif stage == "WB":
                        control_signals = [
                            instruction_data["instruction"].RegWrite,
                            instruction_data["instruction"].MemToReg
                        ]
                        # Print 2-digit control signals for WB stage
                        control_signals_bin = ''.join([str(signal) for signal in control_signals])
                        print(f"    Control Signals (binary): {control_signals_bin}")

        # Now print the instructions in order for each cycle (for the current cycle)
        for stage in ["IF", "ID", "EX", "MEM", "WB"]:
            for instruction in instructions_per_cycle[stage]:
                print(f"{instruction}: {stage}")

    def run(self):
        self.cycles += 1
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()
        self.display()
        return self.end
        

if __name__ == "__main__":
    Sim = MIPS_Simulator(file_path="./inputs/test3.txt")
    while not Sim.run():
        pass