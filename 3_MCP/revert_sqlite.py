import json

filename = r'c:/Users/aidan/OneDrive - Daun Lee/Daun/패스트캠퍼스/KT_AI_Academy/260311_실습자료/3_MCP/3_mcp_opensource.ipynb'

with open(filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Restore the sqlite client cell to original
for cell in data['cells']:
    if cell['cell_type'] == 'code' and any('"sqlite": {' in line for line in cell['source']):
        cell['source'] = [
            'client = MultiServerMCPClient({\n',
            '    "sqlite": {\n',
            '        "transport": "stdio",\n',
            '        "command": "npx",\n',
            '        # "args": ["-y", "mcp-sqlite", db_path + \'/w3schools.db\'],   # npx가 mcp-sqlite를 실행, 인자로 DB 파일 경로\n',
            '             "args": ["-y", "@anthropic-ai/mcp-server-sqlite", db_path + \'/w3schools.db\'],\n',
            '    }\n',
            '})'
        ]

with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Reverted to original.")
