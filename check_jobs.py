import json
data = json.load(open('run_data.json', encoding='utf-8-sig'))
for j in data['jobs']:
    print(j['name'] + ': ' + j['conclusion'])