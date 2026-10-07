#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/*
==> ../submissions.joined/DUTHlrgA <==
200 3.1131864.J0J3TR2N0RG3S14J0YZZGLYEO0TKDI5BA 1 0.998028 DUTHlrgA  100 1
*/

/*  R numbers
200 2543.52
201 2366.28
202 4615.27
203 4944.23
204 6361.83
205 67438.43
206 929.09
207 20929.17
*/

int n, b, top, batch, rel, oldtop, Rel[5][3];
double score, auc, rels, nrels, estrel, bestF, Nrels[1000000], Rels[1000000], Estrel[1000000];

stats(){
   int i,j,k;
   rels = nrels = 0;
   for (i=1;i<=4;i++) {
      if (Rel[i][0] || Rel[i][1]) {
         rels += (double)Rel[i][1]/(Rel[i][0]+Rel[i][1])*(Rel[i][-1]+Rel[i][0]+Rel[i][1]);
         nrels += (double)Rel[i][0]/(Rel[i][0]+Rel[i][1])*(Rel[i][-1]+Rel[i][0]+Rel[i][1]);
      }
   }
}

double errcalc(double a, double b) {
   if (b > a) return errcalc(b,a);
   return 100 - 100 * (a - b)/a;
}

doit(){
   stats();
   if (oldtop) {
      int i,j,bn=0,bnest=0;
      double P,R,F,estP,estR,estF,bF=0,bestF=0, bFest=0;
      for (i=1;i<=n;i++) {
         P = Rels[i]/i;
         R = Rels[i]/Rels[n];
         F = 2/(1/P+1/R);
         estP = Estrel[i]/i;
         estR = Estrel[i]/Estrel[n];
         estF = 2/(1/estP+1/estR);
         if (F > bF) {
            bF = F;
            bn = i;
         }
         if (estF > bestF) {
            bestF = estF;
            bFest = F;
            bnest = i;
         }
      }
      printf("%d Rel %0.0lf estRel %0.0lf acc %0.1lf%% possible F1 %0.1lf%% estimated %0.1lf%% actual F1 %0.1lf%% Ferr %0.1lf%% %d %d %0.1lf%% AUC %0.1lf%%\n",
        oldtop,Rels[n],Estrel[n],errcalc(Rels[n],Estrel[n]),100*bF,100*bestF,100*bFest,errcalc(bestF,bFest),bn,bnest,errcalc(bn,bnest),
        100*auc/(Rels[n]*Nrels[n]));
   }
   bestF = 0;
   estrel = 0;
   n = 0;
   oldtop = top;
   memset(Rel,0,sizeof(Rel));
   auc = 0;
}

main(){
   while (4 == scanf("%d%*s%*s%lf%*s%d%d",&top,&score,&batch,&rel)) {
      if (top != oldtop) doit();
      if (batch == 100) b = 1;
      else if (batch == 1000) b = 2;
      else if (batch == 10000) b = 3;
      else if (batch == 1000000) b = 4;
      else printf("oops\n");
      Rel[b][rel]++;
      n++;
      estrel += score;
      Estrel[n] = estrel;
      stats();
//printf("rels %lg nrels %lg\n",rels, nrels);
      Rels[n] = rels;
      Nrels[n] = nrels;
      auc += (Nrels[n]-Nrels[n-1])*Rels[n-1];
   }
   doit();
}
