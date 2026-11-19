import hashlib,json
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .domain_validation import validate_parameters
FEATURES=['temperature','humidity','particles']
def calculate(records,parameters):
    p=validate_parameters(parameters)
    if len(records)<p['min_samples']:raise ValueError('样本数少于核心点最少邻居数')
    X=np.array([[r['values'][f] for f in FEATURES] for r in records],float)
    scaler=StandardScaler().fit(X)
    if np.any(scaler.var_==0):raise ValueError('特征含常量列，无法解释标准化密度，请更换数据')
    model=DBSCAN(eps=p['eps'],min_samples=p['min_samples']).fit(scaler.transform(X));labels=model.labels_;core=set(model.core_sample_indices_)
    unique=sorted(set(labels)-{-1});clusters=[]
    for label in unique:
        ids=np.where(labels==label)[0];center=X[ids].mean(axis=0)
        clusters.append({'cluster':int(label),'count':len(ids),'center':{f:float(v) for f,v in zip(FEATURES,center)}})
    rows=[{'reference':r['reference'],'cluster':int(labels[i]),'kind':'噪声' if labels[i]<0 else ('核心' if i in core else '边界'),**r['values']} for i,r in enumerate(records)]
    return {'summary':[{'label':'密度分区','value':len(unique)},{'label':'噪声占比','value':float(np.mean(labels==-1))},{'label':'核心微站','value':len(core)},{'label':'观测数','value':len(records)}],'clusters':clusters,'standardization':{'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist()},'rows':rows,'columns':['reference','cluster','kind',*FEATURES],'chart':[{'label':'分区 '+str(c['cluster']),'value':c['count']} for c in clusters]+[{'label':'噪声','value':int(sum(labels==-1))}],'explanation':'特征空间中的密度连通分区，编号无顺序；噪声不是污染判定，参数改变后分区可变。','checksum':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),'seed':42}
