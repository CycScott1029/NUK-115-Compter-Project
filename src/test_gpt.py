"""
學長的code 改 python，沒驗證對不對
"""
class MIPS_Pipeline:
    def __init__(self):
        # 初始化寄存器和記憶體
        self.memory = [1] * 32
        self.registers = [1] * 32
        self.registers[0] = 0  # $0 永遠是 0

        # 初始化控制訊號
        self.IF_PCSrc = 0
        self.EX_ALUOP0 = self.EX_ALUOP1 = self.EX_RegDst = 0
        self.EX_ALUSrc = self.EX_Branch = self.EX_RegWrite = 0
        self.EX_MemRead = self.EX_MemWrite = self.EX_MemtoReg = 0
        self.rs = self.rt = self.rd = self.sign_extend = 0

        self.MEM_Branch = self.MEM_MemRead = self.MEM_MemWrite = 0
        self.MEM_RegWrite = self.MEM_MemtoReg = self.MEM_Result = 0
        self.WriteData = self.Zero = self.MEM_Destination = 0

        self.WB_RegWrite = self.WB_MemtoReg = self.WB_Result = 0
        self.ReadData = self.WB_Destination = 0

        # 初始化流水線控制
        self.cycle = 1
        self.stall_count = 0
        self.line = 0
        self.instructions = []

        self.IF_over = self.ID_over = self.EX_over = False
        self.MEM_over = self.WB_over = False
        self.beq_confirm = False

        self.cycle_tracker = [["0"] * 4 for _ in range(5)]

    def load_instructions(self, instructions):
        self.instructions = instructions

    def output_result(self):
        print(f"需要花 {self.cycle} 個 cycles")
        print(" ".join(f"${i}" for i in range(32)))
        print(" ".join(f" {reg} " for reg in self.registers))
        print(" ".join(f"W{i}" for i in range(32)))
        print(" ".join(f" {mem} " for mem in self.memory))

    def IF(self):
        if self.line < len(self.instructions):
            instruction = self.instructions[self.line].strip()
            if self.stall_count > 0:
                self.ID_over = False
                return

            self.cycle_tracker[0] = instruction[:3]
            self.line += 1
            self.IF_over = True
            self.ID_over = False

    def ID(self):
        if self.stall_count > 0:
            self.ID_over = False
            return

        instruction = self.instructions[self.line - 1].strip()
        parts = instruction.split()
        if len(parts) == 3:  # I-format
            if parts[0] == "lw":
                self.EX_RegDst = 0
                self.EX_ALUSrc = 1
                self.EX_Branch = 0
                self.EX_MemRead = 1
                self.EX_RegWrite = 1
                self.EX_MemtoReg = 1

        elif len(parts) == 4:  # R-format
            self.EX_RegDst = 1
            self.EX_ALUSrc = 0
            self.EX_Branch = 0
            self.EX_MemRead = 0
            self.EX_RegWrite = 1
            self.EX_MemtoReg = 0

        self.ID_over = True
        self.EX_over = False

    def EX(self):
        self.MEM_Result = self.rs + self.sign_extend if self.EX_ALUSrc else self.rs + self.rt
        self.Zero = int(self.MEM_Result == 0)

        if self.EX_Branch and self.Zero:
            self.line += self.sign_extend
            self.beq_confirm = True

        self.EX_over = True
        self.MEM_over = False

    def MEM(self):
        if self.MEM_MemRead:
            self.ReadData = self.memory[self.MEM_Result]
        elif self.MEM_MemWrite:
            self.memory[self.MEM_Result] = self.WriteData

        self.WB_RegWrite = self.MEM_RegWrite
        self.WB_Destination = self.MEM_Destination
        self.WB_MemtoReg = self.MEM_MemtoReg
        self.WB_Result = self.MEM_Result

        self.MEM_over = True
        self.WB_over = False

    def WB(self):
        if self.WB_RegWrite:
            if self.WB_MemtoReg:
                self.registers[self.WB_Destination] = self.ReadData
            else:
                self.registers[self.WB_Destination] = self.WB_Result

        self.WB_over = True

    def run(self):
        max_line = len(self.instructions)
        while True:
            if not self.WB_over:
                self.WB()
            if not self.MEM_over:
                self.MEM()
            if not self.EX_over:
                self.EX()
            if not self.ID_over or self.stall_count > 0:
                self.ID()
            if self.line == max_line:
                self.IF_over = True
            else:
                self.IF()

            self.stall_count = max(0, self.stall_count - 1)
            if all([self.IF_over, self.ID_over, self.EX_over, self.MEM_over, self.WB_over]):
                break
            self.cycle += 1

        self.output_result()

if __name__ == "__main__":
    instructions = [
        "add 1, 2, 3",  # $1 = $2 + $3
        "sub 4, 1, 2",  # $4 = $1 - $2
        "lw 5, 0(1)",   # $5 = Memory[$1 + 0]
        "sw 5, 4(2)",   # Memory[$2 + 4] = $5
        "beq 1, 2, 8"   # If $1 == $2, jump to instruction at index 8
    ]

    mips = MIPS_Pipeline()
    mips.load_instructions(instructions)
    mips.run()
