"""Reproducible CPU training. Test set is evaluated only after validation selection."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
import argparse,collections,copy,hashlib,json,random,time
from pathlib import Path
import numpy as np
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score,f1_score,classification_report,confusion_matrix
from model import IntentBiLSTM,tokenize,encode,batch_tensor,ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--epochs',type=int,default=12);args=parser.parse_args()
    random.seed(42);np.random.seed(42);torch.manual_seed(42);torch.set_num_threads(2)
    raw=[json.loads(l) for l in (ROOT/'data/bitext_intents.jsonl').read_text().splitlines()]
    groups={};conflicts=set()
    for r in raw:
        key=' '.join(tokenize(r['text']))
        if key in groups and groups[key]['intent']!=r['intent']:conflicts.add(key)
        groups.setdefault(key,r)
    rows=[r for key,r in groups.items() if key not in conflicts]
    labels=sorted({r['intent'] for r in rows});label_id={s:i for i,s in enumerate(labels)}
    tr,rest=train_test_split(rows,test_size=.30,random_state=42,stratify=[r['intent'] for r in rows])
    va,te=train_test_split(rest,test_size=.5,random_state=42,stratify=[r['intent'] for r in rest])
    supplement=[json.loads(l) for l in (ROOT/'data/supplement.jsonl').read_text().splitlines()]
    test_keys={' '.join(tokenize(r['text'])) for r in va+te}
    supplement=[r for r in supplement if ' '.join(tokenize(r['text'])) not in test_keys]
    tr=tr+supplement
    freq=collections.Counter(t for r in tr for t in tokenize(r['text']))
    vocab={'<pad>':0,'<unk>':1}
    for t,n in freq.most_common(7998):
        if n>=2:vocab[t]=len(vocab)
    for name,split in [('train',tr),('validation',va),('test',te)]:
        (ROOT/f'data/{name}.jsonl').write_text('\n'.join(json.dumps(r) for r in split)+'\n')
    def prep(rs):return [(encode(r['text'],vocab),label_id[r['intent']]) for r in rs]
    trains,vals,tests=map(prep,(tr,va,te))
    model=IntentBiLSTM(len(vocab),len(labels));opt=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001);lossfn=torch.nn.CrossEntropyLoss()
    def infer(ds):
        model.eval();out=[]
        with torch.inference_mode():
            for start in range(0,len(ds),128):
                b=ds[start:start+128];x,l=batch_tensor([s for s,_ in b]);out.append(model(x,l).softmax(-1).numpy())
        return np.concatenate(out)
    history=[];best=-1;wait=0;t0=time.perf_counter()
    for epoch in range(args.epochs):
        model.train();random.shuffle(trains);total=0
        for start in range(0,len(trains),128):
            b=trains[start:start+128];x,l=batch_tensor([s for s,_ in b]);y=torch.tensor([y for _,y in b]);opt.zero_grad();loss=lossfn(model(x,l),y);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=loss.item()*len(b)
        vp=infer(vals);vy=np.array([y for _,y in vals]);score=f1_score(vy,vp.argmax(1),average='macro')
        rec={'epoch':epoch+1,'loss':total/len(trains),'validation_macro_f1':float(score)};history.append(rec);print(json.dumps(rec),flush=True)
        if score>best+.0001:best=score;best_state=copy.deepcopy(model.state_dict());wait=0
        else:wait+=1
        if wait>=3:break
    model.load_state_dict(best_state);vp=infer(vals);vy=np.array([y for _,y in vals]);threshold=.95
    for t in np.arange(.55,.951,.025):
        sort=np.sort(vp,axis=1);keep=(sort[:,-1]>=t)&(sort[:,-1]-sort[:,-2]>=.15)
        if keep.sum() and np.mean(vp.argmax(1)[keep]==vy[keep])>=.98:threshold=float(round(t,3));break
    tp=infer(tests);ty=np.array([y for _,y in tests]);pred=tp.argmax(1);sort=np.sort(tp,axis=1)
    coverage=np.array([sum(t in vocab for t in tokenize(r['text']))/max(1,len(tokenize(r['text']))) for r in te])
    accepted=(sort[:,-1]>=threshold)&(sort[:,-1]-sort[:,-2]>=.15)&(coverage>=.5)
    metrics={'source_rows':len(raw),'deduplicated_rows':len(rows),'removed_rows':len(raw)-len(rows),'conflicting_normalized_texts':len(conflicts),'train_samples':len(tr),'authored_supplement_samples':len(supplement),'validation_samples':len(va),'test_samples':len(te),'vocabulary_size':len(vocab),'classes':len(labels),'parameters':sum(p.numel() for p in model.parameters()),'epochs_run':len(history),'selected_epoch':max(history,key=lambda r:r['validation_macro_f1'])['epoch'],'training_seconds':round(time.perf_counter()-t0,2),'test_accuracy':float(accuracy_score(ty,pred)),'macro_f1':float(f1_score(ty,pred,average='macro')),'accepted_coverage':float(accepted.mean()),'accepted_accuracy':float((pred[accepted]==ty[accepted]).mean()) if accepted.any() else None,'threshold':threshold,'classification_report':classification_report(ty,pred,target_names=labels,output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(ty,pred).tolist(),'labels':labels,'history':history,'dataset_sha256':hashlib.sha256((ROOT/'data/bitext_intents.jsonl').read_bytes()).hexdigest(),'torch_version':torch.__version__,'seed':42}
    metadata={'vocabulary':vocab,'labels':labels,'threshold':threshold,'max_length':40,'embedding_dim':64,'hidden_size':64,'dataset':'Bitext Customer Support 27K','source_git_blob':'404649b80bb5ec57463d7ce7e17bc48e63b01fbc'}
    torch.save(model.state_dict(),ROOT/'models/intent_bilstm.pt')
    (ROOT/'models/metadata.json').write_text(json.dumps(metadata,indent=2))
    (ROOT/'reports/metrics.json').write_text(json.dumps(metrics,indent=2))
    (ROOT/'reports/test_predictions.jsonl').write_text('\n'.join(json.dumps({'text':r['text'],'true':r['intent'],'predicted':labels[p],'confidence':float(probs.max()),'accepted':bool(a)}) for r,p,probs,a in zip(te,pred,tp,accepted))+'\n')
    print(json.dumps({k:v for k,v in metrics.items() if k not in ['history','classification_report','confusion_matrix']},indent=2),flush=True)
if __name__=='__main__':main()
