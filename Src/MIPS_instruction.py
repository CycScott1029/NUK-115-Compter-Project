class MIPS_Instruction:
    def __init__(self, instruction_data):
        self.raw_instruction = instruction_data.get("operation")  # Original operation
        self.opcode = instruction_data.get("operation")  # Operation code as the operation name
        self.rs = instruction_data.get("rs")  # Source register 1
        self.rt = instruction_data.get("rt")  # Source register 2
        self.rd = instruction_data.get("rd")  # Destination register
        self.immediate = instruction_data.get("immediate")  # Immediate value or address

        # value
        self.rs_value = None
        self.rt_value = None
        self.result = None
        # control signals
        self.RegDst = 0
        self.ALUSrc = 0
        self.MemToReg = 0
        self.RegWrite = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.ALUOp = 0
        # instruction metadata
        self.stage = "IF"
        self.stall = False
        self.forwarded = False

    def __str__(self):
        return f"Instruction: {self.raw_instruction}, rs: {self.rs}, rt: {self.rt}, rd: {self.rd}, immediate: {self.immediate}"
