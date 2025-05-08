from pathlib import Path
import json
import shutil

with open('random30.dates') as f:
    dates = f.readlines()

morning_files = ['naive.txt', 'topk.txt', 'by_company.txt']
closing_files = [
    'base_on_only_market_info.txt',
    'base_on_morning_truth.txt',
    'base_on_naive_morning.txt',
    'base_on_topk_morning.txt',
    'base_on_by_company.txt',
    'by_company.txt'
]
filename_map = {
    'morning': morning_files,
    'closing': closing_files,
}
backbone = 'chatgpt'

for date in dates:
    for scenario in filename_map:
        for filename in filename_map[scenario]:
            src = Path(f'../generated_report/{backbone}/{date.strip()}/{scenario}/{filename}')
            dst = Path(f'./corpus/{backbone}_{date.strip()}_{scenario}_{filename}')
            if not dst.parent.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            print(f'Copied {src} to {dst}')

        src = Path(f'../sample/{date.strip()}/{scenario}_segments.json')
        dst = Path(f'./corpus/human_{date.strip()}_{scenario}.txt')
        with open(src) as f:
            segments = json.load(f)
        human_transcript = ''.join([s['segment'] for s in segments])
        with open(dst, 'w') as f:
            f.write(human_transcript)
