"""Shared preprocessing, BiLSTM architecture and inference."""
import json,re,unicodedata
from pathlib import Path
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence
ROOT=Path(__file__).resolve().parent
MAX_LENGTH=40

def tokenize(text):
    text=unicodedata.normalize('NFKC',text).lower().replace('’',"'")
    text=re.sub(r'\{\{.*?\}\}', ' entity ', text)
    text=re.sub(r'\b(?:sa[- ]?)?\d+\b', ' entity ', text)
    return re.findall(r"[a-z]+(?:'[a-z]+)?",text)

def encode(text,vocab):
    return [vocab.get(t,1) for t in tokenize(text)[:MAX_LENGTH]] or [1]

def batch_tensor(sequences):
    lengths=torch.tensor([len(s) for s in sequences],dtype=torch.long)
    x=torch.zeros((len(sequences),int(lengths.max())),dtype=torch.long)
    for i,s in enumerate(sequences):x[i,:len(s)]=torch.tensor(s)
    return x,lengths

class IntentBiLSTM(nn.Module):
    def __init__(self,vocab_size,classes,embedding_dim=64,hidden_size=64):
        super().__init__()
        self.embedding=nn.Embedding(vocab_size,embedding_dim,padding_idx=0)
        self.lstm=nn.LSTM(embedding_dim,hidden_size,batch_first=True,bidirectional=True)
        self.head=nn.Sequential(nn.Dropout(.3),nn.Linear(hidden_size*2,64),nn.ReLU(),nn.Dropout(.2),nn.Linear(64,classes))
    def forward(self,x,lengths):
        packed=pack_padded_sequence(self.embedding(x),lengths.cpu(),batch_first=True,enforce_sorted=False)
        _,(hidden,_)=self.lstm(packed)
        return self.head(torch.cat([hidden[-2],hidden[-1]],dim=1))

class Predictor:
    def __init__(self,path=None):
        torch.set_num_threads(2)
        path=Path(path or ROOT/'models')
        self.meta=json.loads((path/'metadata.json').read_text())
        self.vocab=self.meta['vocabulary'];self.labels=self.meta['labels']
        self.model=IntentBiLSTM(len(self.vocab),len(self.labels))
        self.model.load_state_dict(torch.load(path/'intent_bilstm.pt',map_location='cpu',weights_only=True))
        self.model.eval()
    @torch.inference_mode()
    def predict(self,text):
        ids=encode(text,self.vocab);x,l=batch_tensor([ids])
        p=self.model(x,l).softmax(-1)[0];v,ix=p.topk(3)
        known=sum(t in self.vocab for t in tokenize(text))/max(1,len(tokenize(text)))
        accepted=bool(v[0]>=self.meta['threshold'] and v[0]-v[1]>=.15 and known>=.5)
        return {'intent':self.labels[ix[0]],'confidence':round(float(v[0]),5),'accepted':accepted,'known_ratio':round(known,3),'alternatives':[{'intent':self.labels[i],'confidence':round(float(s),5)} for s,i in zip(v,ix)]}
