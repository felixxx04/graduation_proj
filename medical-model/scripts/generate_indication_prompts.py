"""生成 DeepSeek 适应症补充提示词 — 分批脚本

为1815种药物分批生成提示词，每批50种药物。
生成的提示词文件保存在 data/deepseek_prompts/indication_batches/prompts/ 目录下。
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

BATCH_DIR = "data/deepseek_prompts/indication_batches"
PROMPT_DIR = os.path.join(BATCH_DIR, "prompts")
os.makedirs(PROMPT_DIR, exist_ok=True)

# 读取分批文件
batch_files = sorted([f for f in os.listdir(BATCH_DIR) if f.startswith("batch_") and f.endswith(".json")])

PROMPT_HEADER = """你是一个药学知识专家。请为以下每种药物补充完整的适应症(indications)列表。

要求:
1. 每种药物列出其所有常见适应症,包括 On Label(官方批准)和 Off Label(临床常用但未正式批准)
2. 适应症使用英文小写描述,如 "pain", "fever", "hypertension", "type 2 diabetes mellitus" 等
3. 适应症应具体且可匹配,避免过于笼统(如 "various infections" 应拆分为 "bacterial infection", "urinary tract infection" 等具体适应症)
4. 如果药物有 indications_raw,请在原始基础上扩充,不要遗漏原始适应症
5. 对于组合药物(如 Amlodipine-Valsartan),列出每个成分的适应症
6. 格式为 JSON,每项包含 generic_name 和 indications 数组

输入药物列表:
"""

PROMPT_EXAMPLE = """

请输出 JSON 格式如下:
[
  {
    "generic_name": "Acyclovir",
    "indications": [
      {"condition": "herpes simplex virus infection", "type": "On Label"},
      {"condition": "varicella zoster virus infection", "type": "On Label"},
      {"condition": "herpes labialis", "type": "Off Label"}
    ]
  },
  ...
]

注意: 只输出JSON,不要输出其他解释文本。"""

for batch_file in batch_files:
    batch_path = os.path.join(BATCH_DIR, batch_file)
    batch_num = batch_file.replace("batch_", "").replace(".json", "")

    with open(batch_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    # 构建药物列表
    drug_lines = []
    for d in batch:
        raw = d["indications_raw"] if d["indications_raw"] != "NONE" else "(无原始适应症数据)"
        drug_lines.append(f"{d['name']} | {d['class']} | indications_raw: {raw}")

    drug_list = "\n".join(drug_lines)
    prompt = PROMPT_HEADER + drug_list + PROMPT_EXAMPLE

    prompt_path = os.path.join(PROMPT_DIR, f"prompt_{batch_num}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"Batch {batch_num}: {len(batch)} drugs → {prompt_path}")

print(f"\nDone! Generated {len(batch_files)} prompt files.")
print(f"每批50种药物, 共37批, 覆盖全部1815种药物")