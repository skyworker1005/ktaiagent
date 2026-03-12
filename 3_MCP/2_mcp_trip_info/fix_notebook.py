import json
import sys

filename = r'c:/Users/aidan/OneDrive - Daun Lee/Daun/패스트캠퍼스/KT_AI_Academy/260311_실습자료/3_MCP/2_mcp_trip_info/trip_info_client.ipynb'

with open(filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

for cell in data['cells']:
    if cell['cell_type'] == 'code' and any('async def wiki_poi_search' in line for line in cell['source']):
        new_source = []
        for line in cell['source']:
            if 'arguments = {"text" : wiki_text}' in line:
                new_source.append(line.replace('wiki_text', 'text'))
            elif 'return llm.invoke(prompt)' in line:
                new_source.append('    result = await llm.ainvoke(prompt)\n')
                new_source.append('    return result.content\n')
            else:
                new_source.append(line)
        cell['source'] = new_source

with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Notebook updated successfully.")
