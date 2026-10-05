"""Matched inverse experts with or without additional fine onset evidence."""
import torch
from torch import nn

from .temporal import TemporalExpert, pack_features

MODEL_POLICY = {'version':'onset-ablation-v1', 'modes':1,
                'onsetChannels':[64,64,128,128], 'kernel':5, 'strides':[2,2,2],
                'fusion':'coarse256-onset256-linear256-GELU',
                'control':'replace-onset-input-with-zero; identical-architecture',
                'loss':'unchanged-temporal-acoustic-energy'}


class OnsetExpert(TemporalExpert):
    def __init__(self, spec, use_onset=True):
        super().__init__(spec, modes=1, encoder_kind='temporal')
        self.use_onset = bool(use_onset)
        self.onset_encoder = nn.Sequential(
            nn.Conv1d(64,64,5,stride=2,padding=2),nn.GELU(),
            nn.Conv1d(64,128,5,stride=2,padding=2),nn.GELU(),
            nn.Conv1d(128,128,5,stride=2,padding=2),nn.GELU(),nn.Flatten(1),
            nn.Linear(128*16,256),nn.GELU())
        self.fusion = nn.Sequential(nn.Linear(512,256),nn.GELU())

    def forward(self, features, onset):
        relative, absolute, scalars = pack_features(features)
        if onset.shape != (len(features),64,128) or not torch.isfinite(onset).all():
            raise ValueError('Onset evidence must be finite B x 64 x 128')
        if not self.use_onset:
            onset = torch.zeros_like(onset)
        coarse = self.encoder(torch.cat((self.relative(relative),self.absolute(absolute),scalars),-1))
        hidden = self.fusion(torch.cat((coarse,self.onset_encoder(onset)),-1))
        return {'continuous':self.numeric_heads[0](hidden).sigmoid()[:,None],
                'categorical':[head(hidden)[:,None] for head in self.category_heads[0]],
                'mode_logits':self.mode_head(hidden)}


def epoch(model, shard, onset, ids, weights, mean, std, batch_size, device, optimizer=None):
    from .temporal import acoustic_energy, mixture_loss
    total, count = 0., 0
    model.train(optimizer is not None)
    with torch.set_grad_enabled(optimizer is not None):
        for batch in ids.split(batch_size):
            coarse = (shard['features'][batch].to(device)-mean)/std
            fine = onset[batch].to(device)
            labels = {key:shard[key][batch].to(device) for key in ('continuous','categorical')}
            pred = model(coarse, fine)
            loss,_ = mixture_loss(acoustic_energy(pred,labels,model.spec),pred['mode_logits'],weights[batch].to(device))
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite onset training loss')
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),5.,error_if_nonfinite=True)
                optimizer.step()
            total += float(loss.detach())*len(batch)
            count += len(batch)
    return total/count


def fit(model, shard, onset, mean, std, weights, output, metadata, epochs=90, batch_size=128, device='cpu'):
    import json
    from pathlib import Path
    import time
    from .data import _json_write, file_hash
    if epochs < 1 or batch_size < 1:
        raise ValueError('Positive training budget required')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'training.json').exists() or (output/'best.pt').exists():
        raise FileExistsError('Training output already exists')
    model.to(device)
    mean,std=mean.to(device),std.to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,epochs,eta_min=.0001)
    report={'complete':False,'metadata':metadata,'history':[],
            'bestEpoch':None,'bestValidation':None,'parameters':sum(p.numel() for p in model.parameters())}
    started=time.monotonic()
    for i in range(1,epochs+1):
        ids=shard['train'][torch.randperm(len(shard['train']))]
        train_loss=epoch(model,shard,onset,ids,weights['train'],mean,std,batch_size,device,optimizer)
        val_loss=epoch(model,shard,onset,shard['val'],weights['val'],mean,std,batch_size,device)
        row={'epoch':i,'train':train_loss,'validation':val_loss,'seconds':time.monotonic()-started,
             'learningRate':optimizer.param_groups[0]['lr']}
        report['history'].append(row)
        scheduler.step()
        if report['bestValidation'] is None or val_loss < report['bestValidation']:
            report.update(bestEpoch=i,bestValidation=val_loss)
            torch.save({'metadata':metadata,'model':{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                        'epoch':i,'validation':val_loss},output/'best.pt')
        report['checkpointSha256']=file_hash(output/'best.pt')
        report['complete']=i==epochs
        _json_write(output/'training.json',report)
        print(json.dumps({'engine':model.spec['name'],'onset':model.use_onset,**row}),flush=True)
    return report
