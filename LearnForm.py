import os

# const value
maxcount = 20

class MIPS_Simulator:
    def __init__(self, file_path):
        # Decode instructions
        self.instruction_memory = self.load_file(file_path) 
        # 32 registers and 32 word memory
        self.register = [1] * 32
        self.register[0] = 0
        self.memory = [1] * 32

        # 5 pipeline stage
        self.stage = ["IF ", "ID ", "EX ", "MEM", "WB "]
        self.pipeline_stage = []
        self.pipeline_stages = []

        # Supported instructions
        self.strmap = ["lw", "sw", "add", "sub", "beq"]

        # cycle_count
        self.cycle = 4
        self.counter = 0
        self.position = 0

        # 暫存上一步與上上步的指令資訊
        self.prenum = 0
        self.pprenum = 0
        # 暫存上一步與上上步的指令資訊
        self.prestr = ""
        self.pprestr = ""

    def load_file(self, file_path):
        """
        Load MIPS instructions from the given file.
        """
        instructions = []
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:  
                        continue
                    opcode, rest = line.split(" ", 1)
                    parts = rest.replace(",", "").replace("(", " ").replace(")", "").split()
                    parts = [part.replace('$', '') for part in parts]
                    formatted_instruction = f"{opcode} {' '.join(parts)}"
                    instructions.append(formatted_instruction)
                return instructions
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
        return None

    def parse_instruction(self):
        """
        Convert inst format
        """
        parsed_instructions = []
        
        for instruction in self.instruction_memory:
            parts = instruction.split()
            op_code = parts[0]  
            args = parts[1:]    

            instruction_dict = {"op": op_code}
            for idx, arg in enumerate(args):
                try:
                    instruction_dict[str(idx)] = int(arg) 
                except ValueError:
                    instruction_dict[str(idx)] = arg 
            parsed_instructions.append(instruction_dict)
        return parsed_instructions

    
    def piplined_handler(self):
        # turn inst_mem format to 'op','0','1','2'
        self.instruction_memory = self.parse_instruction()
        
        # prapare piplined stages
        max_stages = maxcount
        while max_stages > 0:
            max_stages -= 1
            self.pipeline_stages.append(list(self.stage))
            self.stage.insert(0, "   ")

        # loop inst
        inst_count = len(self.instruction_memory)
        i = 0
        while i < inst_count:
        #for i in range(inst_count):
            self.pipeline_stage.append(self.instruction_memory[i]["op"])
            # lw 
            if(self.instruction_memory[i]["op"] == "lw"):
                self.register[self.instruction_memory[i]["0"]] = self.memory[int(self.register[self.instruction_memory[i]["2"]] + self.instruction_memory[i]["1"] / 4 )]
                self.ppstr = self.prestr
                self.ppnum = self.prenum
                self.prestr = "lw"
                self.prenum = self.instruction_memory[i]["0"]

            # sw
            elif(self.instruction_memory[i]["op"]== "sw"):
                self.memory[int(self.register[self.instruction_memory[i]["2"]] + self.instruction_memory[i]["1"] / 4)] = self.register[self.instruction_memory[i]["0"]]
                self.ppstr = self.prestr
                self.ppnum = self.prenum
                self.prestr = ""

            # add
            elif(self.instruction_memory[i]["op"]== "add"):
                # handle data_Hazard
                if(self.prestr == "lw") and ((self.prenum == self.instruction_memory[i]["1"]) or (self.prenum == self.instruction_memory[i]["2"])):
                    self.cycle += 1
                    for j in range(self.counter,maxcount):
                        self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                    self.position += 1
                # add operate
                self.register[self.instruction_memory[i]["0"]] = self.register[self.instruction_memory[i]["1"]] + self.register[self.instruction_memory[i]["2"]]
                self.ppstr = self.prestr
                self.ppnum = self.prenum
                self.prestr = "r"
                self.prenum = self.instruction_memory[i]["0"]
            # sub
            elif(self.instruction_memory[i]["op"]== "sub"):
                # handle data_Hazard
                if(self.prestr == "lw") and ((self.prenum == self.instruction_memory[i]["1"]) or (self.prenum == self.instruction_memory[i]["2"])):            
                    for j in range(self.counter,maxcount):
                        self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                    self.position += 1
                    self.cycle += 1
                # sub operate
                self.register[self.instruction_memory[i]["0"]] = self.register[self.instruction_memory[i]["1"]] - self.register[self.instruction_memory[i]["2"]]
                self.ppstr = self.prestr
                self.ppnum = self.prenum
                self.prestr = "r"
                self.prenum = self.instruction_memory[i]["0"]

            # beq
            elif(self.instruction_memory[i]["op"]== "beq"):
                # 前項指令導致的 target reg = source reg
                if (self.prenum == self.instruction_memory[i]["0"] or self.prenum == self.instruction_memory[i]["1"]):
                    if(self.prestr == "lw"):
                        for j in range(self.counter,maxcount):
                            self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                        
                        for j in range(self.counter,maxcount):
                            self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                        
                        self.position += 2
                        self.cycle += 2
                    
                    elif (self.prestr == "r"):
                        
                        for j in range(self.counter,maxcount):
                            self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                        
                        self.position += 1
                        self.cycle += 1
                
                # 前前項指令導致的 target reg = source reg
                elif ((self.ppnum == self.instruction_memory[i]["0"]) or (self.ppnum == self.instruction_memory[i]["1"])) and (self.ppstr == "lw"):
                    self.cycle += 1
                    
                    for j in range(self.counter,maxcount):
                        self.pipeline_stages[j].insert(self.position + 2, self.pipeline_stages[j][self.position+1])
                    self.position += 1
                        
                # beq rs == rt 
                if (self.register[self.instruction_memory[i]["0"]] == self.register[self.instruction_memory[i]["1"]]):
                    self.cycle += 1
                    self.position += 1
                    self.counter += 1
                    self.pipeline_stages[self.counter].pop()
                    self.pipeline_stages[self.counter].pop()
                    self.pipeline_stages[self.counter].pop()
                    self.pipeline_stages[self.counter].pop()
                    # strs.push_back(strmap[inst[i + 1][0]]);
                    self.pipeline_stage.append(self.strmap[i+1])
                    i += self.instruction_memory[i]["2"]
                self.ppstr = self.prestr
                self.ppnum = self.prenum
                self.prestr = ""
            self.cycle += 1
            self.counter += 1
            self.position += 1
            i += 1
        # 通過填充確保管線同步
        for i in range(maxcount):
            size = len(self.pipeline_stages[i])
            while size < self.cycle :
                self.pipeline_stages[i].append("   ")
                size = len(self.pipeline_stages[i])

        # 模擬輸出每個週期的結果
        stages = self.pipeline_stages
        stage = self.pipeline_stage
        output = []
        for i in range(self.cycle):
            output.append(f"cycle {i+1}")
            for j in range(self.counter):
                if stages[j][i] != "   ":
                    if stage[j] in ["lw", "sw", "add", "sub", "beq"]:
                        output_line = f"  {stage[j]}: {stages[j][i]}"
                        if stages[j][i] == "EX ":
                            if stage[j] == "lw":
                                output_line += " 01 010 11"
                            elif stage[j] == "sw":
                                output_line += " x1 010 1x"
                            elif stage[j] in ["add", "sub"]:
                                output_line += " 10 000 10"
                            else:
                                output_line += " x0 100 0x"
                        elif stages[j][i] == "MEM":
                            if stage[j] == "lw":
                                output_line += " 010 11"
                            elif stage[j] == "sw":
                                output_line += " 001 0x"
                            elif stage[j] in ["add", "sub"]:
                                output_line += " 000 10"
                            else:
                                output_line += " 100 0x"
                        elif stages[j][i] == "WB ":
                            if stage[j] == "lw":
                                output_line += " 11"
                            elif stage[j] == "sw":
                                output_line += " 0x"
                            elif stage[j] in ["add", "sub"]:
                                output_line += " 10"
                            else:
                                output_line += " 0x"
                        output.append(output_line)
                    else:
                        output.append(f"{stage[j]}: {stages[j][i]}")

        for line in output:
            print(line)
        # 輸出暫存器和記憶體的最終狀態
        output = []
        output.append(f"\n{self.cycle} cycles\n")

        # print register
        output.append("\n$1  $2  $3  $4  $5  $6  $7  $8  $9  $10 $11 $12 $13 $14 $15 $16 "
                    "$17 $18 $19 $20 $21 $22 $23 $24 $25 $26 $27 $28 $29 $30 $31 $32\n")
        output.append(self.register)

        # print memory
        output.append("\nw1  w2  w3  w4  w5  w6  w7  w8  w9  w10 w11 w12 w13 w14 w15 w16 "
                    "w17 w18 w19 w20 w21 w22 w23 w24 w25 w26 w27 w28 w29 w30 w31 w32\n")
        output.append(self.memory)

        # 輸出管線階段對應
        output.append("\n\n  1   2   3   4   5   6   7   8   9   10  11  12  13  14  "
                    "15  16  17  18  19  20\n")

        # print(stage)
        # print(stages)
        str = ""
        for i in range(self.counter):
            for j in range(len(stages[i])):
                str += f"{stages[i][j]} "
            str += "\n"
        print("\n\n1   2   3   4   5   6   7   8   9   10  11  12  13  14  "
                    "15  16  17  18  19  20")
        print(str)
        # formatted_output = "".join(output)
        # print(formatted_output)

        # 將結果輸出到檔案
        # with open("output.txt", "w") as file:
        #     file.writelines(output)

    def run(self):
        """
        Run the MIPS simulator and print parsed instructions.
        """
        self.piplined_handler()

if __name__ == "__main__":
    # 確保 output 資料夾存在
    os.makedirs("output", exist_ok=True)

    # 四組檔案路徑
    file_paths = ["./inputs/test3.txt", "./inputs/test4.txt", "./inputs/test5.txt", "./inputs/test6.txt"]

    for file_path in file_paths:
        # 取得輸入檔案名稱
        input_file_name = os.path.basename(file_path)
        # 設定對應的輸出檔案路徑
        output_file = f"./output/{input_file_name}"

        # 初始化 MIPS 模擬器
        mips = MIPS_Simulator(file_path)

        # 捕捉輸出
        from io import StringIO
        import sys

        # 暫時重定向 stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()

        # 執行模擬器
        mips.run()

        # 恢復 stdout
        sys.stdout = old_stdout

        # 將結果寫入對應的輸出檔案
        with open(output_file, "w") as f:
            f.write(buffer.getvalue())

        print(f"Output written to {output_file}")