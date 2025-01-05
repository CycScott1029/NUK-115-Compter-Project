from Load_Instruction import read_instructions, parse_instruction
from MIPS_instruction import MIPS_Instruction

class MIPS_Simulator:
    def __init__(self, file_path):
        self.instruction_memory = read_instructions(file_path)
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

        self.program_counter = 0
        self.cycles = 0
        self.end = False

    def IF(self):
        """
        Instruction Fetch
        """
        # If the ID stage is stalling (bubble insertion), don't fetch a new instruction
        if (self.pipeline_registers["IF/ID"] 
            and getattr(self.pipeline_registers["IF/ID"]["instruction"], 'stall', False)):
            return

        # Check if we're out of instructions.
        if self.program_counter >= len(self.instruction_memory):
            self.instruction_in_stages["IF"] = None
            return

        instruction_text = self.instruction_memory[self.program_counter]
        instruction = parse_instruction(instruction_text)

        # Load the new instruction into IF/ID
        self.pipeline_registers["IF/ID"] = {
            "instruction": instruction
        }

        # Update stage info and increment PC
        self.instruction_in_stages["IF"] = instruction.raw_instruction
        self.program_counter += 1

    def ID(self):
        if self.pipeline_registers["IF/ID"] is None:
            self.instruction_in_stages["ID"] = None
            return

        instruction = self.pipeline_registers["IF/ID"]["instruction"]

        # --------------------------------------------------
        # 1) Detect load-use hazard with the instruction in ID/EX
        # --------------------------------------------------
        hazard_detected = False
        if self.pipeline_registers["ID/EX"]:
            prev_instr = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instr.opcode == "lw" and prev_instr.RegWrite == 1:
                # lw writes to 'rt' if RegDst=0, else 'rd'
                lw_dest = prev_instr.rt if (prev_instr.RegDst == 0) else prev_instr.rd
                # If current instruction in ID needs lw_dest for rs or rt => STALL
                if lw_dest in [instruction.rs, instruction.rt]:
                    hazard_detected = True

        if hazard_detected:
            # Mark a stall
            instruction.stall = True  
            # Insert a bubble into EX (so no new instruction goes there this cycle)
            self.pipeline_registers["ID/EX"] = None  
            # Do NOT clear IF/ID => we decode the same instruction next cycle
            print(f"[Cycle {self.cycles}] ID: Stalling on load-use hazard for {instruction.raw_instruction}")
            self.instruction_in_stages["ID"] = instruction.raw_instruction
            return

        # If no hazard -> proceed

        # If the instruction was previously stalled, you can reset or just proceed
        if instruction.stall:
            instruction.stall = False  # optional to clear
            self.instruction_in_stages["ID"] = instruction.raw_instruction
            return

        # --------------------------------------------------
        # 2) Normal decode
        # --------------------------------------------------
        rs_val = self.register_file.get(instruction.rs, 0)
        rt_val = self.register_file.get(instruction.rt, 0)

        # Set control signals
        self.set_control_signals(instruction)

        write_reg = instruction.rd if instruction.RegDst else instruction.rt

        # Move the current instruction + data into ID/EX
        self.pipeline_registers["ID/EX"] = {
            "instruction": instruction,
            "rs_val": rs_val,
            "rt_val": rt_val,
            "write_reg": write_reg,
            "immediate": instruction.immediate
        }

        # Clear IF/ID
        self.pipeline_registers["IF/ID"] = None
        self.instruction_in_stages["ID"] = instruction.raw_instruction

    def EX(self):
        """
        Execute / ALU stage + Forwarding
        """
        if self.pipeline_registers["ID/EX"] is None:
            self.instruction_in_stages["EX"] = None
            return

        id_ex = self.pipeline_registers["ID/EX"]
        instruction = id_ex["instruction"]

        # If we are stalling or have a bubble, skip
        if instruction.stall:
            self.instruction_in_stages["EX"] = instruction.raw_instruction
            return

        rs_val = id_ex["rs_val"]
        rt_val = id_ex["rt_val"]
        imm = id_ex["immediate"]
        write_reg = id_ex["write_reg"]  # The register we plan to write in WB stage

        # ---- Forwarding Logic ----
        # 1) Forward from EX/MEM if needed
        # 2) If not forwarded from EX/MEM, forward from MEM/WB

        # Forward from EX/MEM
        ex_mem = self.pipeline_registers["EX/MEM"]
        if ex_mem and ex_mem["instruction"].RegWrite and not ex_mem["instruction"].stall:
            # The register that EX/MEM is writing to:
            ex_mem_dest = ex_mem["write_reg"]
            # Make sure it is not $0 and is the same as our current rs or rt
            if ex_mem_dest == instruction.rs and ex_mem_dest != '0':
                rs_val = ex_mem["alu_result"] if ex_mem["alu_result"] is not None else rs_val
                instruction.forwarded = True
            if ex_mem_dest == instruction.rt and ex_mem_dest != '0':
                rt_val = ex_mem["alu_result"] if ex_mem["alu_result"] is not None else rt_val
                instruction.forwarded = True

        # Forward from MEM/WB
        mem_wb = self.pipeline_registers["MEM/WB"]
        if mem_wb and mem_wb["instruction"].RegWrite and not mem_wb["instruction"].stall:
            mem_wb_dest = mem_wb["write_reg"]
            # If MEM/WB had a lw, the data is in mem_data; otherwise it's alu_result
            # Decide what data to forward
            data_to_forward = (mem_wb["mem_data"] if mem_wb["mem_data"] is not None
                               else mem_wb["alu_result"])

            if mem_wb_dest == instruction.rs and mem_wb_dest != '0':
                rs_val = data_to_forward
                instruction.forwarded = True
            if mem_wb_dest == instruction.rt and mem_wb_dest != '0':
                rt_val = data_to_forward
                instruction.forwarded = True

        # ---- ALU Operation ----
        alu_result = None
        branch_taken = False
        branch_target = None

        if instruction.opcode in ["add", "sub", "and", "or"]:
            if instruction.opcode == "add":
                alu_result = rs_val + rt_val
            elif instruction.opcode == "sub":
                alu_result = rs_val - rt_val
            elif instruction.opcode == "and":
                alu_result = rs_val & rt_val
            elif instruction.opcode == "or":
                alu_result = rs_val | rt_val

        elif instruction.opcode == "lw" or instruction.opcode == "sw":
            alu_result = rs_val + imm

        elif instruction.opcode == "beq":
            branch_taken = (rs_val == rt_val)
            # Typical MIPS branch target = PC + (immediate << 2)
            # For simplicity, we skip the shift, or do it your way:
            branch_target = self.program_counter + imm

        if branch_taken:
            # flush the instructions that entered IF & ID in the last 2 cycles
            self.pipeline_registers["IF/ID"] = None
            self.pipeline_registers["ID/EX"] = None
            self.program_counter = branch_target
            self.instruction_in_stages["EX"] = instruction.raw_instruction
            return

        # Save EX results
        self.pipeline_registers["EX/MEM"] = {
            "instruction": instruction,
            "alu_result": alu_result,
            "branch_taken": branch_taken,
            "branch_target": branch_target,
            "rs_val": rs_val,
            "rt_val": rt_val,
            "write_reg": write_reg
        }

        # Clear ID/EX
        self.pipeline_registers["ID/EX"] = None
        self.instruction_in_stages["EX"] = instruction.raw_instruction

    def MEM(self):
        """
        Memory Access
        """
        if self.pipeline_registers["EX/MEM"] is None:
            self.instruction_in_stages["MEM"] = None
            return

        ex_mem = self.pipeline_registers["EX/MEM"]
        instruction = ex_mem["instruction"]
        alu_result = ex_mem["alu_result"]
        rs_val = ex_mem["rs_val"]
        rt_val = ex_mem["rt_val"]
        write_reg = ex_mem["write_reg"]

        if instruction.stall:
            self.instruction_in_stages["MEM"] = instruction.raw_instruction
            return

        mem_data = None
        if instruction.opcode == "lw":
            mem_data = self.data_memory.get(alu_result, 0)

        elif instruction.opcode == "sw":
            # Typically sw $rt, offset($rs)
            # base = rs, store the contents of rt
            self.data_memory[alu_result] = rt_val

        # Branches do not need any memory op; R-type does not need it either

        self.pipeline_registers["MEM/WB"] = {
            "instruction": instruction,
            "alu_result": alu_result,
            "mem_data": mem_data,       # only valid if lw
            "write_reg": write_reg
        }

        # Clear EX/MEM
        self.pipeline_registers["EX/MEM"] = None
        self.instruction_in_stages["MEM"] = instruction.raw_instruction

    def WB(self):
        """
        Write Back
        """
        if self.pipeline_registers["MEM/WB"] is None:
            self.instruction_in_stages["WB"] = None
            return

        mem_wb = self.pipeline_registers["MEM/WB"]
        instruction = mem_wb["instruction"]
        alu_result = mem_wb["alu_result"]
        mem_data = mem_wb["mem_data"]
        write_reg = mem_wb["write_reg"]

        if instruction.stall:
            self.instruction_in_stages["WB"] = instruction.raw_instruction
            return

        # If instruction writes to a register
        if instruction.RegWrite and write_reg != '0':
            if instruction.opcode == "lw":
                # Write mem_data to register
                self.register_file[f'${write_reg}'] = mem_data
            else:
                # R-type or other instructions => write alu_result
                self.register_file[f'${write_reg}'] = alu_result

        # Clear MEM/WB
        self.pipeline_registers["MEM/WB"] = None
        self.instruction_in_stages["WB"] = instruction.raw_instruction

    def set_control_signals(self, instruction: MIPS_Instruction):
        """
        Sets the control signals in the instruction object.
        You can expand this logic for 'and', 'or', 'addi', etc.
        """
        op = instruction.opcode

        # Reset all signals
        instruction.RegDst = 0
        instruction.ALUSrc = 0
        instruction.MemToReg = 0
        instruction.RegWrite = 0
        instruction.MemRead = 0
        instruction.MemWrite = 0
        instruction.Branch = 0

        if op in ["add", "sub", "and", "or"]:
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
        # etc. for other instructions

    def display(self):
        """
        Print pipeline stages each cycle.
        """
        print(f"\n--- Cycle {self.cycles} ---")
        # Gather instructions at each stage
        for stage in ["IF", "ID", "EX", "MEM", "WB"]:
            if self.instruction_in_stages[stage] is not None:
                print(f"{self.instruction_in_stages[stage]}: {stage}")

    def pipeline_empty(self):
        """
        Check if all pipeline registers are empty (None).
        """
        return all(self.pipeline_registers[reg] is None for reg in self.pipeline_registers)

    def run(self):
        """
        Run one cycle of the pipeline.
        """
        self.cycles += 1
        # Standard pipeline order
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()

        self.display()

        # End if we've fetched all instructions AND the pipeline is drained
        if self.program_counter >= len(self.instruction_memory) and self.pipeline_empty():
            self.end = True

        return self.end

if __name__ == "__main__":
    sim = MIPS_Simulator(file_path="./inputs/test3.txt")
    while not sim.run():
        pass