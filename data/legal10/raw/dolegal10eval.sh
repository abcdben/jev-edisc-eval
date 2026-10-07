#!/bin/bash

#
# TREC 2010 Legal Task Learning Track Evaluation
#
# Usage:  
#   ./dolegal10eval qrel-file run-file.gz
# Or:
#   ./dolegal10eval qrel-file run-file.gz
#
# Output:
#   run-file.table
#   run-file.sum

gcc -O2 -o /tmp/calc1 calc1.c -lm
gcc -O2 -o /tmp/calc2 calc2.c -lm
export B=`echo $2 | sed -e 's/.gz//'`
(zcat $B.gz || cat $B) | dos2unix | sed -e 's/	/ /g' -e 's/  */ /g' -e 's/ Q0 /:/' | sort > /tmp/pre
join /tmp/pre $1 | sed -e 's/:/ /' | sort -k1,1 -k3,3n -k2,2 > /tmp/joined
/tmp/calc1 < /tmp/joined > $B.table
/tmp/calc2 < /tmp/joined > /tmp/summary
rm -f $B.sum

for TOP in `cut -d' ' -f1 /tmp/summary` ; do
  echo " Topic:" $TOP >> $B.sum
  echo "  Relevant Docs:   " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f3` >> $B.sum
  echo "   Rel Estimate:   " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f5` >> $B.sum
  echo "   Rel Accuracy:   " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f7` >> $B.sum
  echo "  F1:              " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f15` >> $B.sum
  echo "   F1 Estimate:    " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f12` >> $B.sum
  echo "   F1 Accuracy:    " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f17` >> $B.sum
  echo "  Best cutoff:     " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f18` >> $B.sum
  echo "   Cutoff Estimate:" `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f19` >> $B.sum
  echo "   Cutoff Accuracy:" `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f20` >> $B.sum
  echo "  Hypothetical F1: " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f10` >> $B.sum
  echo "  ROC AUC:         " `grep "^$TOP" /tmp/summary |  head -1 | cut -d' ' -f22` >> $B.sum
  echo >> $B.sum
done
