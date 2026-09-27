"""Optional: reproduce the Bitext projection from the upstream public CSV."""
import csv,io,json,urllib.request
from pathlib import Path
URL='https://raw.githubusercontent.com/bitext/customer-support-llm-chatbot-training-dataset/main/data/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv'
if __name__=='__main__':
 with urllib.request.urlopen(URL,timeout=120) as r:raw=r.read().decode('utf-8-sig')
 rows=[{'source_row':i+2,'flags':r['flags'],'text':r['instruction'],'category':r['category'],'intent':r['intent']} for i,r in enumerate(csv.DictReader(io.StringIO(raw)))]
 dest=Path(__file__).resolve().parent/'data/bitext_intents.jsonl'
 dest.write_text('\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in rows)+'\n')
 print(f'Downloaded {len(rows)} rows. For exact reproduction, use the included snapshot and its recorded hash; the upstream main branch may change.')
