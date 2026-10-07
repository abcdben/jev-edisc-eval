"""Matplotlib figures for the article and the gallery: the finish-the-passage spectrum (verbatim_spectrum.png) and the Jev code-name
swap (codename_swap.png). Reads results/contam/summary.json and results/jev_probe/summary.json; writes under results/contam/article/.
Recovered from the original /tmp script on 2026-10-06 and extended with the Big Thorium row (present only when its probes were merged).

    .venv/bin/python scripts/article/matplotlib_figs.py
"""
import os, pathlib
os.chdir(pathlib.Path(__file__).resolve().parents[2])
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
S=json.load(open('results/contam/summary.json'))
J=json.load(open('results/jev_probe/summary.json'))
M=[('gpt-5.6-luna','GPT-5.6 Luna (small)','#8ec5ec'),('gpt-5.6-terra','GPT-5.6 Terra (mid)','#2f7fc1'),('gpt-5.6-sol','GPT-5.6 Sol (large)','#17375e')]
plt.rcParams.update({'font.family':'Helvetica Neue','font.size':11,'axes.edgecolor':'#d9dce3','axes.labelcolor':'#333','xtick.color':'#555','ytick.color':'#222'})

# ---- verbatim spectrum
rows=[('veridian','Veridian (invented, 2026)  ·  FLOOR')]+([('bigthorium','Big Thorium (Relativity demo)  ·  PUBLIC, INVENTED')] if all('bigthorium' in S['verbatim'][m] for m,_,_ in M) else [])+[('endo','Endo e-mails (published after cutoff)'),('mnk','Mallinckrodt e-mails'),('jebbush','Jeb Bush e-mails'),('enron','Enron e-mails'),('cuad','CUAD contracts'),('canon','Founding documents  ·  CEILING')]
fig,ax=plt.subplots(figsize=(10.2,4.9+0.45*(len(rows)-7)),dpi=110)
ax.set_facecolor('#fafaf8')
vmin=min(S['verbatim'][m][ 'veridian']['lcs_f_mean'] for m,_,_ in M); vmax=max(S['verbatim'][m]['veridian']['lcs_f_mean'] for m,_,_ in M)
ax.axvspan(vmin,vmax,color='#9bbf8a',alpha=.25,lw=0)
ax.text((vmin+vmax)/2,len(rows)-0.45,'floor band\n(Veridian, three models)',ha='center',va='bottom',fontsize=8.5,color='#4a7a3a')
for i,(c,lab) in enumerate(rows):
    y=len(rows)-1-i
    ax.axhline(y,color='#e4e6ea',lw=.8,zorder=0)
    for m,name,col in M:
        v=S['verbatim'][m][c]; x=v['lcs_f_mean']
        ax.plot(x,y,'o',ms=9,color=col,mec='white',mew=1,zorder=3)
        if v['frac_run_ge15']>0:
            ax.annotate(f"{v['frac_run_ge15']*100:.0f}%",(x,y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=7.5,color=col)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([lab for _,lab in rows][::-1],fontsize=10.5)
ax.set_xlim(0,1); ax.set_ylim(-0.6,len(rows)-0.2)
ax.set_xlabel('overlap between the model\'s next 60 words and the real next 60 words (0 = none · 1 = every word)')
for s in ('top','right','left'): ax.spines[s].set_visible(False)
ax.tick_params(axis='y',length=0)
h=[plt.Line2D([],[],marker='o',ls='',color=col,ms=8,label=name) for _,name,col in M]
ax.legend(handles=h,loc='upper right',frameon=False,fontsize=9.5,ncol=1)
fig.suptitle('Finish the passage: how much of the real continuation each model reproduced, by collection',x=0.01,ha='left',fontsize=12,fontweight='bold',color='#222')
fig.text(0.01,0.905,'Mean over the screened windows per collection (60 each; Big Thorium 48, rules-only), answered items only. Small %: share of windows with an exact 15+-word run.',fontsize=9,color='#666')
fig.tight_layout(rect=(0,0,1,0.9))
fig.savefig('results/contam/article/verbatim_spectrum.png',facecolor='white'); plt.close(fig)

# ---- T1 code-name swap: Jev vs LLMs
mats=[('enron','Enron'),('jebbush','Jeb Bush'),('mnk','Mallinckrodt'),('endo','Endo')]
sys_=[('jev@base','Jev (decision model)','#2e8b57'),('gpt-5.6-luna','GPT-5.6 Luna','#8ec5ec'),('gpt-5.6-terra','GPT-5.6 Terra','#2f7fc1'),('gpt-5.6-sol','GPT-5.6 Sol','#17375e')]
fig,axes=plt.subplots(1,2,figsize=(10.2,4.4),dpi=110,sharey=True)
for ax,(key,title) in zip(axes,[('signal','Real matter name vs. fictional twin\n(a case-aware reader should say "relevant" more often for the real one)'),('decoy','Real but off-topic name vs. fictional twin\n(a case-aware reader should not favour the real one)')]):
    ax.set_facecolor('#fafaf8'); ax.axvline(0,color='#333',lw=1)
    for i,(mk,ml) in enumerate(mats):
        y=len(mats)-1-i; ax.axhline(y,color='#e4e6ea',lw=.8,zorder=0)
        for j,(sk,sl,col) in enumerate(sys_):
            v=J['t1'][mk]['models'][sk][key]; d=v['diff']*100; lo,hi=[x*100 for x in v['diff_ci']]
            yy=y+0.27-0.18*j
            ax.plot([lo,hi],[yy,yy],color=col,lw=1.6,alpha=.85); ax.plot(d,yy,'o',color=col,ms=7,mec='white',mew=.8,zorder=3)
    ax.set_yticks(range(len(mats))); ax.set_yticklabels([l for _,l in mats][::-1],fontsize=10.5)
    ax.set_xlim(-90,100); ax.set_title(title,fontsize=9.5,loc='left',color='#333')
    ax.set_xlabel('percentage-point change in "relevant" calls, real minus fictional (95% CI)',fontsize=9)
    for s in ('top','right','left'): ax.spines[s].set_visible(False)
    ax.tick_params(axis='y',length=0)
h=[plt.Line2D([],[],marker='o',ls='',color=col,ms=7,label=sl) for _,sl,col in sys_]
fig.legend(handles=h,loc='lower center',ncol=4,frameon=False,fontsize=9,bbox_to_anchor=(0.5,0.0))
fig.suptitle('Code-name swap: same document, one name changed, request never names it',x=0.01,ha='left',fontsize=12,fontweight='bold',color='#222')
fig.tight_layout(rect=(0,0.06,1,0.93))
fig.savefig('results/contam/article/codename_swap.png',facecolor='white'); plt.close(fig)
print('ok')