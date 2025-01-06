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
        # 檢查是否已取完所有指令
        if self.program_counter >= len(self.instruction_memory):
            self.instruction_in_stages["IF"] = None
            return

        # 如果 ID 階段因 hazard 而 stall，保持 PC 和 IF/ID 不變
        if (self.pipeline_registers["IF/ID"] 
            and getattr(self.pipeline_registers["IF/ID"]["instruction"], 'stall', False)):
            self.instruction_in_stages["IF"] = None
            return  # 停止抓取新指令，保持當前狀態

        # 抓取當前 PC 對應的指令
        instruction_text = self.instruction_memory[self.program_counter]
        instruction = parse_instruction(instruction_text)

        # 更新 IF/ID pipeline register，僅當無效或可更新時覆蓋
        self.pipeline_registers["IF/ID"] = {
            "instruction": instruction
        }

        # 更新這個 cycle 的 IF stage 資訊，並遞增 PC
        self.instruction_in_stages["IF"] = instruction.raw_instruction
        self.program_counter += 1  # 僅在沒有 stall 時更新 PC
    def ID(self):
        if self.pipeline_registers["IF/ID"] is None:
            self.instruction_in_stages["ID"] = None
            return

        instruction = self.pipeline_registers["IF/ID"]["instruction"]

        # -----------------------------
        # 1) Detect hazard
        # -----------------------------
        hazard_detected = False

        # (A) 原先的 load-use hazard 偵測 (若 ID/EX 是 lw，且當前指令用到相同 rs/rt)
        if self.pipeline_registers["ID/EX"]:
            prev_instr = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instr.opcode == "lw" and prev_instr.RegWrite == 1:
                lw_dest = prev_instr.rt if (prev_instr.RegDst == 0) else prev_instr.rd
                if lw_dest in [instruction.rs, instruction.rt]:
                    hazard_detected = True

        # (B) 你提供的幾種 hazard 偵測情況 (1~4)
        #    注意此處我們沿用同一個 hazard_detected flag，只要任一情況為 True，就 stall

        # 取得 current_instr (本程式中就是 instruction)
        current_instr = instruction

        # 情況1: ID/EX 是 lw，且下一個指令是 add、sub 或 beq，需要 rs、rt
        if self.pipeline_registers.get("ID/EX") is not None:
            prev_instr = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instr.opcode == "lw":
                lw_rd = prev_instr.rt if prev_instr.RegDst == 0 else prev_instr.rd
                if current_instr.opcode in ["add", "sub"]:
                    if lw_rd in [current_instr.rs, current_instr.rt]:
                        hazard_detected = True
                elif current_instr.opcode == "beq":
                    if lw_rd in [current_instr.rs, current_instr.rt]:
                        hazard_detected = True

        # 情況2: EX/MEM 是 lw，且下一個指令是 beq，需要 rs、rt
        if self.pipeline_registers.get("EX/MEM") is not None:
            prev_instr = self.pipeline_registers["EX/MEM"]["instruction"]
            if prev_instr.opcode == "lw":
                lw_rd = prev_instr.rt if prev_instr.RegDst == 0 else prev_instr.rd
                if current_instr.opcode == "beq":
                    if lw_rd in [current_instr.rs, current_instr.rt]:
                        hazard_detected = True

        # 情況3: ID/EX 是 add，且下一個指令是 beq，需要 rs、rt
        if self.pipeline_registers.get("ID/EX") is not None:
            prev_instr = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instr.opcode == "add":
                add_rd = prev_instr.rd
                if current_instr.opcode == "beq":
                    if add_rd in [current_instr.rs, current_instr.rt]:
                        hazard_detected = True

        # 情況4: ID/EX 是 sub，且下一個指令是 beq，需要 rs、rt
        if self.pipeline_registers.get("ID/EX") is not None:
            prev_instr = self.pipeline_registers["ID/EX"]["instruction"]
            if prev_instr.opcode == "sub":
                sub_rd = prev_instr.rd
                if current_instr.opcode == "beq":
                    if sub_rd in [current_instr.rs, current_instr.rt]:
                        hazard_detected = True

        # (C) 若偵測到 hazard => stall
        if hazard_detected:
            instruction.stall = True
            # 插入 bubble：清空 ID/EX，保持該指令在 ID 階段
            self.pipeline_registers["ID/EX"] = None
            print(f"[Cycle {self.cycles}] ID: Stalling on hazard for {instruction.raw_instruction}")
            self.instruction_in_stages["ID"] = instruction.raw_instruction
            return

        # 若本輪指令原本是 stall，這裡可以清除
        if instruction.stall:
            instruction.stall = False
            self.instruction_in_stages["ID"] = instruction.raw_instruction
            return

        # --------------------------------------------------
        # 3) 正常解碼
        # --------------------------------------------------
        rs_val = self.register_file.get(instruction.rs, 0)
        rt_val = self.register_file.get(instruction.rt, 0)

        # 設定控制訊號
        self.set_control_signals(instruction)

        write_reg = instruction.rd if instruction.RegDst else instruction.rt

        # 將目前指令與相關資料搬到 ID/EX
        self.pipeline_registers["ID/EX"] = {
            "instruction": instruction,
            "rs_val": rs_val,
            "rt_val": rt_val,
            "write_reg": write_reg,
            "immediate": instruction.immediate
        }

        # 清除 IF/ID
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

        # 如果被 stall 或是一個 bubble，就不進行進一步運算
        if instruction.stall:
            self.instruction_in_stages["EX"] = instruction.raw_instruction
            return

        rs_val = id_ex["rs_val"]
        rt_val = id_ex["rt_val"]
        imm = id_ex["immediate"]
        write_reg = id_ex["write_reg"]  # 將在 WB 寫回的目標暫存器

        # ---- Forwarding Logic ----
        # 從 EX/MEM 轉傳
        ex_mem = self.pipeline_registers["EX/MEM"]
        if ex_mem and ex_mem["instruction"].RegWrite and not ex_mem["instruction"].stall:
            ex_mem_dest = ex_mem["write_reg"]
            # 如果 EX/MEM 要寫的暫存器 == 我們現在這條指令的 rs 或 rt，就 forward
            if ex_mem_dest == instruction.rs and ex_mem_dest != '0':
                rs_val = ex_mem["alu_result"] if ex_mem["alu_result"] is not None else rs_val
                instruction.forwarded = True
            if ex_mem_dest == instruction.rt and ex_mem_dest != '0':
                rt_val = ex_mem["alu_result"] if ex_mem["alu_result"] is not None else rt_val
                instruction.forwarded = True

        # 從 MEM/WB 轉傳
        mem_wb = self.pipeline_registers["MEM/WB"]
        if mem_wb and mem_wb["instruction"].RegWrite and not mem_wb["instruction"].stall:
            mem_wb_dest = mem_wb["write_reg"]
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

        elif instruction.opcode in ["lw", "sw"]:
            alu_result = rs_val + imm

        elif instruction.opcode == "beq":
            branch_taken = (rs_val == rt_val)
            # 這裡簡化處理分支目標，假設 imm 直接加到 PC
            branch_target = self.program_counter + imm

        if branch_taken:
            # flush IF/ID & ID/EX
            self.pipeline_registers["IF/ID"] = None
            self.pipeline_registers["ID/EX"] = None
            self.program_counter = branch_target
            self.instruction_in_stages["EX"] = instruction.raw_instruction
            return

        # EX 結果存入 EX/MEM
        self.pipeline_registers["EX/MEM"] = {
            "instruction": instruction,
            "alu_result": alu_result,
            "branch_taken": branch_taken,
            "branch_target": branch_target,
            "rs_val": rs_val,
            "rt_val": rt_val,
            "write_reg": write_reg
        }

        # 清空 ID/EX
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
            # sw $rt, offset($rs) => data_memory[rs+offset] = rt_val
            self.data_memory[alu_result] = rt_val

        # 更新 MEM/WB
        self.pipeline_registers["MEM/WB"] = {
            "instruction": instruction,
            "alu_result": alu_result,
            "mem_data": mem_data,
            "write_reg": write_reg
        }

        # 清空 EX/MEM
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

        # 若指令需要寫回暫存器 (RegWrite)
        if instruction.RegWrite and write_reg != '0':
            if instruction.opcode == "lw":
                self.register_file[f'${write_reg}'] = mem_data
            else:
                self.register_file[f'${write_reg}'] = alu_result

        # 清空 MEM/WB
        self.pipeline_registers["MEM/WB"] = None
        self.instruction_in_stages["WB"] = instruction.raw_instruction

    def set_control_signals(self, instruction: MIPS_Instruction):
        """
        設定控制訊號
        """
        op = instruction.opcode

        # 先重置所有控制訊號
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
        # 其他指令可自行擴充

    def display(self):
        """
        每個 cycle 印出 pipeline 階段
        """
        print(f"\n--- Cycle {self.cycles} ---")
        for stage in ["IF", "ID", "EX", "MEM", "WB"]:
            if self.instruction_in_stages[stage] is not None:
                print(f"{self.instruction_in_stages[stage]}: {stage}")

    def pipeline_empty(self):
        """
        確認所有 pipeline 暫存器是否皆為 None
        """
        return all(self.pipeline_registers[reg] is None for reg in self.pipeline_registers)

    def run(self):
        """
        執行單一個 clock cycle
        """
        self.cycles += 1
        # pipeline 順序：WB -> MEM -> EX -> ID -> IF
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()

        self.display()

        # 若已取完所有指令且 pipeline 皆清空，表示結束
        if self.program_counter >= len(self.instruction_memory) and self.pipeline_empty():
            self.end = True

        return self.end

if __name__ == "__main__":
    sim = MIPS_Simulator(file_path="./inputs/test3.txt")
    while not sim.run():
        pass