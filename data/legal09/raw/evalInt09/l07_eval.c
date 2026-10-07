/*
 * l07_eval.c (Evaluation Program for TREC 2007 Legal Track)
 *
 * Revision History:
 *  2010-05-15 - st - released as version 2.6
 *  2010-05-15 - st - add est_pool, est_pool_ret, est_K-pool_ret
 *  2010-05-15 - st - fix20100515 that estopt=1 should ignore probD
 *  2010-01-04 - st - add prels=5 option (version 2.5)
 *  2009-10-13 - st - internal version 2.4 (TREC 2009 Legal Track Notebook)
 *  2009-10-12 - st - add LAM measure from TREC Spam Filtering Track
 *  2009-10-04 - st - released as version 2.3 (TREC 2009 Legal Track)
 *  2009-08-18 - st - add maxRelLevel option
 *  2009-08-15 - st - fix20090815 skip empty topics
 *  2009-08-09 - st - fix relsubset to not include grays in oldrel09
 *  2009-01-31 - st - MAX_RET_PER_TOPIC 1500000->7000000
 *  2009-01-31 - st - add raw K-rel_ret, K-nonrel_ret, K-gray_ret, K-jg_ret
 *  2008-10-05 - st - released as version 2.1 (TREC 2008 Legal Track)
 *  2008-10-04 - st - reduce K to min(K, ret)
 *  2008-10-04 - st - add measures at depth 50000, 75000, 100000
 *  2008-10-04 - st - just skip topic if dEstR is 0.0
 *  2008-09-06 - st - heuristic for NTCIR topic ids
 *  2008-08-19 - st - allow K values of 0
 *  2008-08-18 - st - add outResidK option
 *  2008-08-16 - st - heuristic for CLEF topic ids
 *  2008-08-01 - st - add retroK diagnostic option
 *  2008-05-30 - st - add residCap
 *  2008-05-19 - st - released as version 2.0 (for L07 usage only)
 *  2008-05-19 - st - allow extra topics in B and Kfile
 *  2008-05-03 - st - fix20080503 for prec scores when estopt=0
 *  2008-05-03 - st - fix F1 for when K > ret
 *  2008-03-25 - st - add outRelNums option
 *  2008-03-23 - st - fix getFMeasure to use square of beta
 *  2008-03-21 - st - add est_K-F1, est_K-Jaccard, etc.
 *  2008-03-14 - st - add est_R-Recall, est_R-Prec, hiEstR
 *  2008-03-10 - st - fix20080310 for GS30 and GS30J when no rel ret
 *  2008-02-15 - st - add runids option
 *  2008-02-10 - st - add num_qrels, num_nonrel, num_gray
 *  2008-02-10 - st - fix20080210 for bpref when no known non-relevant
 *  2007-12-27 - st - add assumeGrayNon option
 *  2007-10-11 - st - added cast to malloc for Unix compilation (lz)
 *  2007-10-08 - st - released as version 1.0 (for L07 usage only)
 *  2007-10-06 - st - started estHTML option to show more calculation details
 *  2007-10-06 - st - add residQrels option to remove old judged from qrels
 *  2007-10-04 - st - add out6 for Interactive results
 *  2007-10-02 - st - finalize measures for L07 main task release
 *  2007-09-01 - st - fix outResid B values to B_resid values
 *  2007-08-28 - st - add estopt, outResid options
 *  2007-06-16 - st - first version based on previous st evalex utility
 *
 * Author list:
 *  st - Stephen Tomlinson
 *
 * Acknowledgements:
 *  Chris Buckley (Sabir): authored trec_eval 8.0 output format upon which
 *    l07_eval output format is based  ( http://trec.nist.gov/trec_eval/ )
 *  Le Zhao (CMU): reported cast fix for Unix compilation (Oct 11/07)
 *  Charlie Zhao (UMKC): reported Unix compilation syntax (Oct 12/07):
 *    gcc -lm -o l07_eval l07_eval.c
 */

/*
 * This is free software.  If you modify the source, 
 * please update the last modified date and last author code in
 * L07_EVAL_VERSION below.
 */
#define L07_EVAL_VERSION "v2.6 (2010-05-15 st)"

/*
 * Input: run file, qrels file
 * Output: trec_eval and L07 scores for each topic
 * (TODO: list inputs and outputs in more detail)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <math.h> /* pow */

#define MAX_STRING_LENGTH	2048
#define MAX_QRELS_PER_QUERY	1000000
#define	MAX_DOCID_SIZE		20
#define	DOCNO_DATA_SIZE		(MAX_QRELS_PER_QUERY * MAX_DOCID_SIZE)
#define	MAX_RET_PER_TOPIC	7000000

#define	L07_NUM_TE8_STRS	1
#define	L07_NUM_TE8_INTS	3
#define	L07_NUM_TE8_LISTED_DOUBLES  24
#define L07_NUM_TE8_B_DOUBLES 11
#define	L07_NUM_TE8_DERIVED_DOUBLES  (30 + L07_NUM_TE8_B_DOUBLES)
#define	L07_NUM_TE8_DOUBLES (L07_NUM_TE8_LISTED_DOUBLES + \
		L07_NUM_TE8_DERIVED_DOUBLES)
#define L07_BSTART (L07_NUM_TE8_DOUBLES - L07_NUM_TE8_B_DOUBLES)
#define L07_NUM_EST_DOUBLES 104

typedef struct {
	char *l07_aszStr[L07_NUM_TE8_STRS];
	int l07_anScore[L07_NUM_TE8_INTS];
	double l07_adScore[L07_NUM_TE8_DOUBLES];
	double l07_adEstScore[L07_NUM_EST_DOUBLES];
} L07TE8;

/* prefixes used for te8's 3 int values */
/* this list must be in same order as in te8 output */
const char *g_L07_aszTE8IntPrefix[L07_NUM_TE8_INTS] = {
	"num_ret",
	"num_rel",
	"num_rel_ret"
};

/* must be in same order as g_L07_aszTE8IntPrefix */
typedef enum {
	L07_TE8_RETRIEVED, 
	L07_TE8_NUM_RELEVANT, L07_TE8_RELEVANT_RETRIEVED
} L07TE8IntType;

typedef enum {
	L07_TE8_TOPIC
} L07TE8StrType;

/* prefixes used for te8's 24 precision measures */
/* this list must be in same order as in te8 output */
const char *g_L07_aszTE8MeasurePrefix[L07_NUM_TE8_DOUBLES] = {
	"map",
	"R-prec",
	"bpref",
	"recip_rank",
	"ircl_prn.0.00",
	"ircl_prn.0.10",
	"ircl_prn.0.20",
	"ircl_prn.0.30",
	"ircl_prn.0.40",
	"ircl_prn.0.50",
	"ircl_prn.0.60",
	"ircl_prn.0.70",
	"ircl_prn.0.80",
	"ircl_prn.0.90",
	"ircl_prn.1.00",
	"P5 ",
	"P10 ",
	"P15 ",
	"P20 ",
	"P30 ",
	"P100 ",
	"P200 ",
	"P500 ",
	"P1000 ",
	":S1:",
	":S5:",
	":S10:",
	":SINF:",
	":GS10:",
	":GS30:",
	":S1Judged:",
	":S5Judged:",
	":S10Judged:",
	":GS10J:",
	":GS30J:",
	":mapJudged:",
	":ret_judged:",
	":FirstRelRank:",
	":LogAP1:", /* original GMAP definition */
	":LogAP2:", /* trec_eval 8.0 GMAP definition */
	":LinLogAP1:", /* based on original GMAP definition */
	":LinLogAP2:", /* based on trec_eval 8.0 GMAP definition */
	":FirstUnjudged:",
	":UJ1:",
	":UJ5:",
	":UJ10:",
	":UJ50:",
	":UJ100:",
	":UJ1000:",
	":RecallInf:",
	":num_qrels:",  /* number of docids in qrels for topic, includes gray */
	":num_rel:",    /* same as num_rel above, repeated for convenience */
	":num_nonrel:", /* number of non-relevant in qrels for topic */
	":num_gray:",   /* number of gray in qrels for topic */
	/* must be last (L07_NUM_TE8_B_DOUBLES) */
	":B:",
	":judgedB:",
	":relB:",
	":precB:", /* pctrelB */
	":recallB:",
	":retrievedB:",
	":pctretB:",
	":pctjudgedB:",
	":precOfJudgedB:",
	":SFirstJudgedB:",
	":SLastJudgedB:",
};

#define L07_TE8_MAP	0
#define L07_TE8_RP	1
#define L07_TE8_BP	2
#define L07_TE8_RR	3 /* index of recip_rank above */
#define L07_TE8_R0	4
#define L07_TE8_P5	15
#define L07_TE8_P10	16
#define L07_TE8_P15	17
#define L07_TE8_P20	18
#define L07_TE8_P30	19
#define L07_TE8_P100	20
#define L07_TE8_P200	21
#define L07_TE8_P500	22
#define L07_TE8_P1000	23
#define L07_TE8_S1	(L07_NUM_TE8_LISTED_DOUBLES+0)
#define L07_TE8_S5	(L07_NUM_TE8_LISTED_DOUBLES+1)
#define L07_TE8_S10	(L07_NUM_TE8_LISTED_DOUBLES+2)
#define L07_TE8_SINF	(L07_NUM_TE8_LISTED_DOUBLES+3)
#define L07_TE8_FRS	(L07_NUM_TE8_LISTED_DOUBLES+4)
#define L07_TE8_FRS30	(L07_NUM_TE8_LISTED_DOUBLES+5)
#define L07_TE8_S1J	(L07_NUM_TE8_LISTED_DOUBLES+6)
#define L07_TE8_S5J	(L07_NUM_TE8_LISTED_DOUBLES+7)
#define L07_TE8_S10J	(L07_NUM_TE8_LISTED_DOUBLES+8)
#define L07_TE8_FRSJ	(L07_NUM_TE8_LISTED_DOUBLES+9)
#define L07_TE8_FRS30J	(L07_NUM_TE8_LISTED_DOUBLES+10)
#define L07_TE8_MAPJ	(L07_NUM_TE8_LISTED_DOUBLES+11)
#define L07_TE8_RETJ	(L07_NUM_TE8_LISTED_DOUBLES+12)
#define L07_TE8_FIRSTRANK	(L07_NUM_TE8_LISTED_DOUBLES+13)
#define L07_TE8_LOG1	(L07_NUM_TE8_LISTED_DOUBLES+14)
#define L07_TE8_LOG2	(L07_NUM_TE8_LISTED_DOUBLES+15)
#define L07_TE8_LINLOG1	(L07_NUM_TE8_LISTED_DOUBLES+16)
#define L07_TE8_LINLOG2	(L07_NUM_TE8_LISTED_DOUBLES+17)
#define L07_TE8_FIRSTUNJUDGED	(L07_NUM_TE8_LISTED_DOUBLES+18)
#define L07_TE8_UJ1	(L07_NUM_TE8_LISTED_DOUBLES+19)
#define L07_TE8_UJ5	(L07_NUM_TE8_LISTED_DOUBLES+20)
#define L07_TE8_UJ10	(L07_NUM_TE8_LISTED_DOUBLES+21)
#define L07_TE8_UJ50	(L07_NUM_TE8_LISTED_DOUBLES+22)
#define L07_TE8_UJ100	(L07_NUM_TE8_LISTED_DOUBLES+23)
#define L07_TE8_UJ1000	(L07_NUM_TE8_LISTED_DOUBLES+24)
#define L07_TE8_RECINF	(L07_NUM_TE8_LISTED_DOUBLES+25)
#define L07_TE8_NUMQRELS	(L07_NUM_TE8_LISTED_DOUBLES+26)
#define L07_TE8_NUMREL	(L07_NUM_TE8_LISTED_DOUBLES+27)
#define L07_TE8_NUMNONREL	(L07_NUM_TE8_LISTED_DOUBLES+28)
#define L07_TE8_NUMGRAY	(L07_NUM_TE8_LISTED_DOUBLES+29)
/* leave to last */
#define L07_TE8_B		(L07_BSTART+0)
#define L07_TE8_JUDGEDB	(L07_BSTART+1)
#define L07_TE8_RELEVANTB	(L07_BSTART+2)
#define L07_TE8_PRECB	(L07_BSTART+3)
#define L07_TE8_RECALLB	(L07_BSTART+4)
#define L07_TE8_RETB	(L07_BSTART+5)
#define L07_TE8_PCTRETB	(L07_BSTART+6)
#define L07_TE8_PCTJUDB	(L07_BSTART+7)
#define L07_TE8_PRECJUDB	(L07_BSTART+8)
#define L07_TE8_SFIRSTJB	(L07_BSTART+9)
#define L07_TE8_SLASTJB	(L07_BSTART+10)

const char *g_L07_aszEstPrefix[L07_NUM_EST_DOUBLES] = {
	":est_rel:",
	":est_nonrel:",
	":est_gray:",
	":est_rel_ret:",
	":est_non_ret:",
	":est_gray_ret:",
	":est_P_set:", /* full retrieval set */
	":est_R_set:",
	":est_gray_set:",
	":est_PB:",
	":est_RB:",
	":est_gray_B:",
	":est_gray_5:",
	":est_P5:",
	":est_P10:",
	":est_P100:",
	":est_P1000:",
	":est_P5000:",
	":est_P10000:",
	":est_P15000:",
	":est_P20000:",
	":est_P25000:",
	":est_P50000:",
	":est_P75000:",
	":est_P100000:",
	":est_R5:",
	":est_R10:",
	":est_R100:",
	":est_R1000:",
	":est_R5000:",
	":est_R10000:",
	":est_R15000:",
	":est_R20000:",
	":est_R25000:",
	":est_R50000:",
	":est_R75000:",
	":est_R100000:",
	":est_MP2nd5000:", /* marginal precision 5001-10000 */
	":est_MP3rd5000:",
	":est_MP4th5000:",
	":est_MP5th5000:",
	":est_MP2nd25000:", /* marginal precision 25001-50000 */
	":est_MP3rd25000:",
	":est_MP4th25000:",
	":MJ1st5000:", /* marginal number judged */
	":MJ2nd5000:",
	":MJ3rd5000:",
	":MJ4th5000:",
	":MJ5th5000:",
	":MJ1st25000:",
	":MJ2nd25000:",
	":MJ3rd25000:",
	":MJ4th25000:",
	":est_MJ1st5000:",
	":est_MJ2nd5000:",
	":est_MJ3rd5000:",
	":est_MJ4th5000:",
	":est_MJ5th5000:",
	":est_MJ1st25000:",
	":est_MJ2nd25000:",
	":est_MJ3rd25000:",
	":est_MJ4th25000:",
	":est_R-Ceil:",
	":est_R-Prec:",	/* R-Precision */
	":est_R-Recall:",
	":est_R-F1:",
	":est_R-Gray:",
	":K:",
	":est_K-Prec:",
	":est_K-Recall:",
	":est_K-Gray:",
	":est_K-Jaccard:", /* overlap or positive accuracy */
	":est_K-FalseNeg:", /* percentage false negatives */
	":est_K-FalsePos:", /* percentage false positives */
	":est_K-rel_ret:",	/* R+ */
	":est_K-nonrel_ret:",	/* N+ */
	":est_K-rel_missed:",	/* R- */
	":est_K-F32:", /* F-measure, beta=32 emphasizes recall */
	":est_K-F16:",
	":est_K-F8:",
	":est_K-F4:",
	":est_K-F2:",
	":est_K-F1:", /* balanced F-measure */
	":est_K-F0.5:",
	":est_K-F0.25:",
	":est_K-F0.125:",
	":est_K-F0.0625:",
	":est_K-F0.03125:",  /* beta<1 emphasizes precision */
	":est_K-ProjR-P:", /* projected R-Precision of top-K */
	":est_K-ProjR-R:", /* projected R-Recall of top-K */
	":est_K-ProjR-Gray:",
	":K-rel_ret:",     /* raw relevant retrieved at K */
	":K-nonrel_ret:",  /* raw non-relevant retrieved at K */
	":K-gray_ret:",    /* raw gray retrieved at K */
	":K-jg_ret:",      /* raw judged or gray at K (sum of previous 3) */
	":est_K-Fallout:",
	":epsilon:",   /* used for smoothing fnr, fpr, lam, DOR */
	":est_K-fnr:", /* false negative rate (ham misclassification (hm%)) */
	":est_K-fpr:", /* false positive rate (spam misclassification (sm%)) */
	":est_K-lam:", /* logistic average misclassification percentage (LAM) */
	":est_K-DOR:", /* diagnostic odds ratio */
	":est_pool:",     /* sum of est_rel, est_non, est_gray */
	":est_pool_ret:", /* sum of est_rel_ret, est_non_ret, est_gray_ret */
	":est_K-pool_ret:",
};
#define L07_EST_R		0
#define L07_EST_N		1
#define L07_EST_G		2
#define L07_EST_RRET		3
#define L07_EST_NRET		4
#define L07_EST_GRET		5
#define L07_EST_PREC_INF	6
#define L07_EST_RECALL_INF	7
#define L07_EST_GRAY_INF	8
#define L07_EST_PREC_B	9
#define L07_EST_RECALL_B	10
#define L07_EST_GRAY_B	11
#define L07_EST_GRAY_5	12
#define L07_EST_P5	13
#define L07_EST_P10	14
#define L07_EST_P100	15
#define L07_EST_P1000	16
#define L07_EST_P5000	17
#define L07_EST_P10000	18
#define L07_EST_P15000	19
#define L07_EST_P20000	20
#define L07_EST_P25000	21
#define L07_EST_P50000	22
#define L07_EST_P75000	23
#define L07_EST_P100000	24
#define L07_EST_R5	25
#define L07_EST_R10	26
#define L07_EST_R100	27
#define L07_EST_R1000	28
#define L07_EST_R5000	29
#define L07_EST_R10000	30
#define L07_EST_R15000	31
#define L07_EST_R20000	32
#define L07_EST_R25000	33
#define L07_EST_R50000	34
#define L07_EST_R75000	35
#define L07_EST_R100000	36
#define L07_EST_MP_5001_10000	37
#define L07_EST_MP_10001_15000	38
#define L07_EST_MP_15001_20000	39
#define L07_EST_MP_20001_25000	40
#define L07_EST_MP_25001_50000	41
#define L07_EST_MP_50001_75000	42
#define L07_EST_MP_75001_100000	43
#define L07_MJ_1_5000	44
#define L07_MJ_5001_10000	45
#define L07_MJ_10001_15000	46
#define L07_MJ_15001_20000	47
#define L07_MJ_20001_25000	48
#define L07_MJ_1_25000	49
#define L07_MJ_25001_50000	50
#define L07_MJ_50001_75000	51
#define L07_MJ_75001_100000	52
#define L07_EST_MJ_1_5000	53
#define L07_EST_MJ_5001_10000	54
#define L07_EST_MJ_10001_15000	55
#define L07_EST_MJ_15001_20000	56
#define L07_EST_MJ_20001_25000	57
#define L07_EST_MJ_1_25000	58
#define L07_EST_MJ_25001_50000	59
#define L07_EST_MJ_50001_75000	60
#define L07_EST_MJ_75001_100000	61
#define L07_EST_R_CEIL		62
#define L07_EST_R_PREC		63
#define L07_EST_R_RECALL	64
#define L07_EST_R_F1		65
#define L07_EST_R_GRAY		66
#define L07_K			67
#define L07_EST_K_PREC		68
#define L07_EST_K_RECALL	69
#define L07_EST_K_GRAY		70
#define L07_EST_K_JACCARD	71
#define L07_EST_K_FALSENEG	72
#define L07_EST_K_FALSEPOS	73
#define L07_EST_K_REL_RET	74
#define L07_EST_K_NONREL_RET	75
#define L07_EST_K_REL_MISSED	76
#define L07_EST_K_F32		77
#define L07_EST_K_F16		78
#define L07_EST_K_F8		79
#define L07_EST_K_F4		80
#define L07_EST_K_F2		81
#define L07_EST_K_F1		82
#define L07_EST_K_F0_5		83
#define L07_EST_K_F0_25		84
#define L07_EST_K_F0_125	85
#define L07_EST_K_F0_0625	86
#define L07_EST_K_F0_03125	87
#define L07_EST_K_PROJ_R_P	88
#define L07_EST_K_PROJ_R_R	89
#define L07_EST_K_PROJ_R_G	90
#define L07_K_REL_RET		91
#define L07_K_NONREL_RET	92
#define L07_K_GRAY_RET		93
#define L07_K_JG_RET		94
#define L07_EST_K_FALLOUT	95
#define L07_EPSILON		96
#define L07_EST_K_FNR		97
#define L07_EST_K_FPR		98
#define L07_EST_K_LAM		99
#define L07_EST_K_DOR		100
#define L07_EST_POOL		101
#define L07_EST_POOL_RET	102
#define L07_EST_K_POOL_RET	103

typedef struct {
	double l7m_dEstPrecK;
	double l7m_dEstRecallK;
	double l7m_dEstGrayK;
	double l7m_dEstJaccardK;
	double l7m_dEstFalseNegK;
	double l7m_dEstFalsePosK;
	double l7m_dEstRelRetK;
	double l7m_dEstNonrelRetK;
	double l7m_dEstRelMissedK;
	double l7m_dEstF32K;
	double l7m_dEstF16K;
	double l7m_dEstF8K;
	double l7m_dEstF4K;
	double l7m_dEstF2K;
	double l7m_dEstF1K;
	double l7m_dEstF0_5K;
	double l7m_dEstF0_25K;
	double l7m_dEstF0_125K;
	double l7m_dEstF0_0625K;
	double l7m_dEstF0_03125K;
	int l7m_nRawRelRetK;
	int l7m_nRawNonrelRetK;
	int l7m_nRawGrayRetK;
	int l7m_nRawJudgedOrGrayRetK;
	double l7m_dEstFalloutK;
	double l7m_dEpsilon;
	double l7m_dEstFnrK;
	double l7m_dEstFprK;
	double l7m_dEstLamK;
	double l7m_dEstDorK;
	double l7m_dEstPool;
	double l7m_dEstPoolRet;
	double l7m_dEstPoolRetK;
} L07MeasuresAtK;

typedef struct {
	int l7s_nRawRelRetK;
	int l7s_nRawNonrelRetK;
	int l7s_nRawGrayRetK;
	int l7s_nRawJudgedOrGrayRetK;
} L07SumsAtK;

/* globals (so we don't need to rewrite qsort) */
char **g_aszDocnos;
int *g_anHiRanks;

int bStartsWith(char *szLine, char *szPrefix);
void *pMalloc(int nNumBytes, char *szMsg);
char *pStrdup(char *p, char *szMsg);
char *pGetLine(char *szLine, int nMaxLineLength, FILE *fp);
int nGetInt(char *szTopic);
void vSumToK(char *acRelString, double *adProb,
	     int nArraySize, int nNumRet,
	     double *pdEstRret, double *pdEstNret, double *pdEstUret,
	     int *pnNumJudged, int nEstOpts, L07SumsAtK *pSums);
void vGetPRUatK(char *acRelString, double *adProb, int nNumRet, int nK,
		double *pdEstPrecK, double *pdEstRecallK, double *pdEstGrayK,
		double dEstR, double dEstN, int nEstOpts, double dEpsilon);
void vGetMeasuresAtK(char *acRelString, double *adProb, int nNumRet, int nK,
		double dEstR, double dEstN, int nEstOpts, double dEpsilon, 
		L07MeasuresAtK *pK);
double dGetFMeasure(double dBeta, double dPrecK, double dRecallK);
double dLogit(double dX);
double dLogitInverse(double dX);
double dLogitAverage(double dX, double dY);
void vGetMarginalPrec(char *acRelString, double *adProb, int nNumRet, 
		int nKlo, int nKhi,
		int *pnNumJudged, double *pdEstNumJudged,
		double *pdEstMargPrec, int nEstOpts);
int fnCompareDocnos( const void *arg1, const void *arg2 );
int fnCompareHiRanks( const void *arg1, const void *arg2 );
int nBinSearchForDocno( char *szDocno, int *anIndex, int nSize );
void printDocno( FILE *fpOut2, char *szDocno, int *pnPos );

#define L07_MAX(a,b)	(((a)>(b)) ? (a) : (b))
#define L07_MIN(a,b)	(((a)<(b)) ? (a) : (b))

/* good place for a breakpoint when debugging */
void vExit(int v) {
	printf("Exiting (%d)\n", v);
	exit(v);
}

int main( int argc, char *argv[] ) {
	char *szQrelsFilename = NULL;
	char *szRunFilename = NULL;
	char *szOutFilename = NULL;
	char *szOutFilename2 = NULL;
	char *szOutFilename5 = NULL;
	char *szOutResidFilename = NULL;
	char *szOutResidKFilename = NULL;
	char *szOutFilename6 = NULL;
	char *szOutRelNumsFilename = NULL;
	int bJudgedOnly = 0;
	int nDisplayNum = 30;
	int nM1000 = 1000;
	int nMinRelLevel = 1;
	int nMaxRelLevel = 0;
	char *szPrecBFilename = NULL;
	char *szKValuesFilename = NULL;
	int nEstOpts = 0;
	FILE *fpQrels = NULL;
	FILE *fpRun = NULL;
	FILE *fpOut = NULL;
	FILE *fpOut2 = NULL;
	FILE *fpOut5 = NULL;
	FILE *fpOutResid = NULL;
	FILE *fpOutResidK = NULL;
	FILE *fpOut6 = NULL;
	FILE *fpOutRelNums = NULL;
	FILE *fpHTML = NULL;
	int nQNumQrels;
	char *szQNumQrels = NULL;
	int nQNumQrelsPrev = -1;
	char *szQNumQrelsPrev = NULL;
	char *szQ0 = NULL;
	char *szDocno = NULL;
	char *szRank = NULL;
	char *szRSV = NULL;
	char *szRunID = NULL;
	int nNumItems;
	int nNumRet = -1;
	int nNumRetJudged = -1;
	int nNumResidOut = -1;
	int nNumResidOutK = -1;
	int nNumRetJudgedOrGray = -1;
	int i;
	char *pRunLine;
	char *szLine = NULL;
	int bQrelsLineLeftover = 0;
	char *szQrelsLine = NULL;
	int bRunLineLeftover = 0;
	char *szRunLine = NULL;
	char *szNTCIRType = NULL;
	char *ptrQrels;
	char *pNextDocno;
	char *pNextRunid;
	int nDocnoDataSize;
	int nRunidDataSize;
	int nNumQrels;
	int nRelevanceJudgement; 
		/* 0 not relevant, 1 relevant, 2 highly relevant */
		/* 3 is "partially relevant" (NTCIR-3), which means
		 * higher numbers aren't always stronger relevance
		 */
	int nHiRank;
	int nQueryID;
	char *szQueryID = NULL;
	int nDocnoLen;
	int nRunidLen;
	int nQNumTop;
	char *szQNumTop = NULL;
	int nDocnoIndex;
	char cRel;
	char *acRelString = NULL;
	double *adProb = NULL;
	int nNumQueries = 0;
	int nNumRelevantQrels; /* includes highly relevant */
	int nNumNonRelevantQrels;
	int nNumGrayQrels;
	int nMinRN;
	int nNumHighlyRelevantQrels;
	int nNumRelevantQrelsSum = 0;
	int nNumNonRelevantQrelsSum = 0;
	int nRelevant; /* include highly relevant */
	int nHighlyRelevant;
	int nJudgedNonRelevant;
	int nRetGray;
	int nFirstRelevantRank;
	int nFirstRelevantRankJudged;
	double dAvgPrec;
	double dPrecSum;
	double dPrecSumJ;
	double dAvgPrecSum = 0.0;
	double dMRR;
	double dMRRSum = 0.0;
	int nPos;
	int j;
	int bNTCIR = 0;
	int nNumRel;
	int bRel;
	double dSum;
	double dScore;
	int nNumRel5;
	int nNumRel10;
	int nNumRel15;
	int nNumRel20;
	int nNumRel30;
	int nNumRel100;
	int nNumRel200;
	int nNumRel500;
	int nNumRel1000;
	int nNumUnjudged1;
	int nNumUnjudged5;
	int nNumUnjudged10;
	int nNumUnjudged50;
	int nNumUnjudged100;
	int nNumUnjudged1000;
	int bJudged;
	double dPrec;
	double dRec;
	double dMaxPrec0;
	double dMaxPrec10;
	double dMaxPrec20;
	double dMaxPrec30;
	double dMaxPrec40;
	double dMaxPrec50;
	double dMaxPrec60;
	double dMaxPrec70;
	double dMaxPrec80;
	double dMaxPrec90;
	double dMaxPrec100;
	double dFRS; /* GS10 or GenS10 */
	double dFRS30;
	double dS1;
	double dS5;
	double dS10;
	double dSInf;
	double dFirstUnjudgedRank;
	double dFirstUnjudgedAndNotGrayRank;
	double dFRSJ;
	double dFRS30J;
	double dS1J;
	double dS5J;
	double dS10J;
	double dAvgPrecJ;
	double dGenRel10;
	int nNumNonRel;
	int nB;
	double dB;
	int nNumRelB;
	int nNumJudgedB;
	L07TE8 *pE = NULL;
	L07TE8 *pESum = NULL;
	double dMinFirstUnjudgedRank;
	double dMinFirstUnjudgedAndNotGrayRank;
	int nMinUnjudgedTopic;
	int nMinUnjudgedAndNotGrayTopic;
	char **aszTopicsB = NULL;
	int *anB = NULL;
	int nNumB = 0;
	char **aszTopicsK = NULL;
	int *anK = NULL;
	int *anKr = NULL; /* resid K */
	int nNumK = 0;
	int bJudged1;
	int nSFirstJudgedB;
	int nSLastJudgedB;
	int nRetB;
	int nProbD = 0;
	double dProb = 0.0;
	double dEstR;
	double dEstN;
	double dEstU;
	double dEstPool;
	int nLimR;
	int nLimN;
	int nLimU;
	double dEstRret;
	double dEstNret;
	double dEstUret;
	double dEstPoolRet;
	double dEstPrecInf;
	double dEstRecallInf; 
	double dEstGrayInf;
	double dEstPrecB;
	double dEstRecallB;
	double dEstGrayB;
	int nK;
	double dEstPrecK;
	double dEstRecallK;
	double dEstGrayK;
	int nNumJudgedInf;
	int nKlo;
	int nKhi;
	int nNumJudgedK;
	double dEstNumJudgedK;
	double dEstMargPrec;
	char *asDocnoData = NULL;
	char *asRunidData = NULL;
	char *acRelevanceJudgement = NULL;
	char **aszRunids = NULL;
	int *anQrelsIndex = NULL;
	int *anHiRankIndex = NULL;
	char *acFound = NULL;
	double *adQrelsProb = NULL;
	int nMaxLineLength = MAX_STRING_LENGTH;
	int *abQrelsRelSubset = NULL;
	int *abQrelsNonSubset = NULL;
	int nRelSubsetNum = 0;
	int nNumRandRels;
	int nNumRandNons;
	FILE *fpRelSubset = NULL;
	FILE *fpNonSubset = NULL;
	char *szOldRel07Name = "oldrel09";
	char *szOldNon07Name = "oldnon09";
	int r;
	int bResidQrels = 0;
	int bEstHTML = 0;
	int bAssumeGrayNon = 0;
	int bRunids = 0;
	int nRCeil;
	double dKvR;
	int bHiEstR = 0;
	int nHiEstR = -1;
	int nNumFilteredQueries = 0;
	int nBindex = -1;
	int nKindex = -1;
	int nKresidIndex = -1;
	L07MeasuresAtK sK;
	L07MeasuresAtK *pK = &sK;
	int bUseRforK = 0;
	int nResidCap = 0;
	int bRetroK = 0;
	int nBestKSum = 0;
	double dBestF1KSum = 0.0;
	double dEpsilon = 0.5; /* same as used by TREC Spam Filtering */
	int nPrelsFields = 0;

	/* display usage if wrong number of arguments specified */
	printf("l07_eval %s\n", L07_EVAL_VERSION);
	if ( argc < 4 ) {
		printf( "Usage: %s "
				"run=RunFilename "
				"q=qrelsFilename "
				"out=oldOutFilename "
				"out2=oldOutFilename2 "
				"[out5=evalOutFilename] "
				"[out6=InteractiveResultsFilename] "
				"[ntcir] "
				"[judgedOnly] "
				"[stringDisplay=30] "
				"[M1000=1000] "
				"[MinRelLevel=2] "
				"[precB=Bvalues.txt] "
				"[Kfile=Kvalues.txt] "
				"[probD=6910912] "
				"[estopt=0] "
				"[relsubset=25] "
				"[residQrels] "
				"[estHTML] "
				"[assumeGrayNon] "
				"[runids] "
				"[hiEstR=25000] "
				"[useRforK] "
				"[residCap=100000] "
				"[retroK] "
				"[epsilon=0.5] "
				"[prels=5] "
				"\n"
		" e.g. args might be 'run=refL07B q=qrelsL07.probs "
			"out=ignore1 out2=ignore2 out5=refL07B.eval "
			"stringDisplay=100 M1000=25000 probD=6910912 "
			"precB=b07_first43.txt Kfile=refL07B.K'\n"
		, argv[0]);
		vExit(-1);
	} /* if */

	/* get arguments */
	for ( i = 1; i < argc; i++ ) {
		if ( bStartsWith( argv[i], "run=" ) ) {
			szRunFilename = argv[i] + 4;
		} else if ( bStartsWith( argv[i], "q=" ) ) {
			szQrelsFilename = argv[i] + 2;
		} else if ( bStartsWith( argv[i], "out=" ) ) {
			szOutFilename = argv[i] + 4;
		} else if ( bStartsWith( argv[i], "out2=" ) ) {
			szOutFilename2 = argv[i] + 5;
		} else if ( bStartsWith( argv[i], "out5=" ) ) {
			szOutFilename5 = argv[i] + 5;
		} else if ( bStartsWith( argv[i], "out6=" ) ) {
			szOutFilename6 = argv[i] + 5;
		} else if ( bStartsWith( argv[i], "outResid=" ) ) {
			szOutResidFilename = argv[i] + 9;
		} else if ( bStartsWith( argv[i], "outResidK=" ) ) {
			szOutResidKFilename = argv[i] + 10;
		} else if ( bStartsWith( argv[i], "outRelNums=" ) ) {
			szOutRelNumsFilename = argv[i] + 11;
		} else if ( strcmp( argv[i], "ntcir" ) == 0 ) {
			bNTCIR = 1;
		} else if ( strcmp( argv[i], "judgedOnly" ) == 0 ) {
			bJudgedOnly = 1;
		} else if ( bStartsWith( argv[i], "stringDisplay=" ) ) {
			nDisplayNum = atoi(argv[i] + 14);
		} else if ( bStartsWith( argv[i], "M1000=" ) ) {
			nM1000 = atoi(argv[i] + 6);
		} else if ( bStartsWith( argv[i], "MinRelLevel=" ) ) {
			nMinRelLevel = atoi(argv[i] + 12);
		} else if ( bStartsWith( argv[i], "MaxRelLevel=" ) ) {
			nMaxRelLevel = atoi(argv[i] + 12);
		} else if ( bStartsWith( argv[i], "precB=" ) ) {
			szPrecBFilename = argv[i] + 6;
		} else if ( bStartsWith( argv[i], "Kfile=" ) ) {
			szKValuesFilename = argv[i] + 6;
		} else if ( bStartsWith( argv[i], "probD=" ) ) {
			nProbD = atoi(argv[i] + 6);
		} else if ( bStartsWith( argv[i], "estopt=" ) ) {
			nEstOpts = atoi(argv[i] + 7);
		} else if ( bStartsWith( argv[i], "relsubset=" ) ) {
			nRelSubsetNum = atoi(argv[i] + 10);
		} else if ( strcmp( argv[i], "residQrels" ) == 0 ) {
			bResidQrels = 1;
		} else if ( strcmp( argv[i], "estHTML" ) == 0 ) {
			bEstHTML = 1;
		} else if ( strcmp( argv[i], "assumeGrayNon" ) == 0 ) {
			bAssumeGrayNon = 1;
		} else if ( strcmp( argv[i], "runids" ) == 0 ) {
			bRunids = 1;
		} else if ( bStartsWith( argv[i], "hiEstR=" ) ) {
			nHiEstR = atoi(argv[i] + 7);
			bHiEstR = 1;
		} else if ( strcmp( argv[i], "useRforK" ) == 0 ) {
			bUseRforK = 1;
		} else if ( bStartsWith( argv[i], "residCap=" ) ) {
			nResidCap = atoi(argv[i] + 9);
		} else if ( strcmp( argv[i], "retroK" ) == 0 ) {
			bRetroK = 1;
		} else if ( bStartsWith( argv[i], "epsilon=" ) ) {
			dEpsilon = atof(argv[i] + 8);
		} else if ( bStartsWith( argv[i], "prels=" ) ) {
			nPrelsFields = atoi(argv[i] + 6);
		} else {
			printf( "Error: don't recognize argument \"%s\"\n",
				argv[i] );
			vExit(-1);
		}
	}

	/* display arguments */
	printf( "      szRunFilename: ***%s***\n", szRunFilename );
	printf( "    szQrelsFilename: ***%s***\n", szQrelsFilename );
	printf( "      szOutFilename: ***%s***\n", szOutFilename );
	printf( "      szOutFilename2: ***%s***\n", szOutFilename2 );
	if (szOutFilename5) {
		printf( "      szOutFilename5: ***%s***\n", szOutFilename5 );
	}
	if (szOutResidFilename) {
		printf("szOutResidFilename: ***%s***\n", szOutResidFilename);
	}
	if (szOutResidKFilename) {
		printf("szOutResidKFilename: ***%s***\n", szOutResidKFilename);
	}
	if (szOutFilename6) {
		printf( "      szOutFilename6: ***%s***\n", szOutFilename6 );
	}
	if (szOutRelNumsFilename) {
		printf("szOutRelNumsFilename: ***%s***\n", 
				szOutRelNumsFilename);
	}
	if (bJudgedOnly) {
		printf( "judgedOnly\n" );
	}
	printf("nDisplayNum: %d (length of rel string line)\n", nDisplayNum);
	printf("nM1000: %d\n", nM1000);
	printf("nMinRelLevel: %d\n", nMinRelLevel);
	if (nMaxRelLevel) {
		printf("nMaxRelLevel: %d\n", nMaxRelLevel);
	}
	if (szPrecBFilename) {
		printf("precBfilename=***%s***\n", szPrecBFilename);
	}
	if (szKValuesFilename) {
		printf("KvaluesFilename=***%s***\n", szKValuesFilename);
	}
	if (nProbD) {
		printf("probD: %d\n", nProbD);
	}
	printf("nEstOpts: %d\n", nEstOpts);
	printf("nRelSubsetNum: %d\n", nRelSubsetNum);
	printf("bResidQrels: %d\n", bResidQrels);
	printf("bEstHTML: %d\n", bEstHTML);
	printf("bAssumeGrayNon: %d\n", bAssumeGrayNon);
	printf("bRunids: %d\n", bRunids);
	if (bHiEstR) {
		printf("nHiEstR: %d\n", nHiEstR);
	}
	if (bUseRforK) {
		printf("bUseRforK: %d\n", bUseRforK);
		if (szKValuesFilename) {
			printf("Error: can't use both Kfile and useRforK\n");
			vExit(-1);
		}
	}
	if (nResidCap) {
		printf("nResidCap: %d\n", nResidCap);
	}
	if (bRetroK) {
		printf("bRetroK: %d\n", bRetroK);
	}
	printf("dEpsilon: %lf\n", dEpsilon);
	if (nPrelsFields) {
		printf("nPrelsFields: %d\n", nPrelsFields);
	}

	/* allocate string holders, etc. */
	szQNumQrels = (char *)pMalloc(nMaxLineLength, "szQNumQrels");
	szQNumQrelsPrev = (char *)pMalloc(nMaxLineLength, "szQNumQrelsPrev");
	szQ0 = (char *)pMalloc(nMaxLineLength, "szQ0");
	szRank = (char *)pMalloc(nMaxLineLength, "szRank");
	szDocno = (char *)pMalloc(nMaxLineLength, "szDocno");
	szRSV = (char *)pMalloc(nMaxLineLength, "szRSV");
	szRunID = (char *)pMalloc(nMaxLineLength, "szRunID");
	szLine = (char *)pMalloc(nMaxLineLength, "szLine");
	szQrelsLine = (char *)pMalloc(nMaxLineLength, "szQrelsLine");
	szRunLine = (char *)pMalloc(nMaxLineLength, "szRunLine");
	szNTCIRType = (char *)pMalloc(nMaxLineLength, "szNTCIRType");
	szQueryID = (char *)pMalloc(nMaxLineLength, "szQueryID");
	szQNumTop = (char *)pMalloc(nMaxLineLength, "szQNumTop");
	acRelString = (char *)pMalloc(sizeof(char) * MAX_RET_PER_TOPIC, 
			"acRelString");
	pE = (L07TE8 *)pMalloc(sizeof(L07TE8), "pE");
	pESum = (L07TE8 *)pMalloc(sizeof(L07TE8), "pESum");
	g_aszDocnos = (char **)pMalloc(sizeof(char *) * MAX_QRELS_PER_QUERY,
			"g_aszDocnos");
	asDocnoData = (char *)pMalloc(sizeof(char) * DOCNO_DATA_SIZE,
			"asDocnoData");
	acRelevanceJudgement = (char *)pMalloc(
			sizeof(char) * MAX_QRELS_PER_QUERY, 
			"acRelevanceJudgement");
	if (bRunids) {
		aszRunids = (char **)pMalloc(
			sizeof(char *) * MAX_QRELS_PER_QUERY, "aszRunids");
		g_anHiRanks = (int *)pMalloc(
			sizeof(int) * MAX_QRELS_PER_QUERY, "g_anHiRanks");
		asRunidData = (char *)pMalloc(sizeof(char) * DOCNO_DATA_SIZE,
			"asRunidData");
		anHiRankIndex = (int *)pMalloc(
			sizeof(int) * MAX_QRELS_PER_QUERY, "anHiRankIndex");
	} else {
		g_anHiRanks = NULL;
	}
	anQrelsIndex = (int *)pMalloc(sizeof(int) * MAX_QRELS_PER_QUERY, 
			"anQrelsIndex");
	acFound = (char *)pMalloc(sizeof(char) * MAX_QRELS_PER_QUERY,
			"acFound");
	adQrelsProb = (double *)pMalloc(sizeof(double) * MAX_QRELS_PER_QUERY, 
			"adQrelsProb");
	if (nRelSubsetNum) {
		abQrelsRelSubset = 
			(int *)pMalloc(sizeof(int) * MAX_QRELS_PER_QUERY, 
			"abQrelsRelSubset");
		abQrelsNonSubset = 
			(int *)pMalloc(sizeof(int) * MAX_QRELS_PER_QUERY, 
			"abQrelsNonSubset");
	}

	if (szPrecBFilename) {
		char *ptr;
		int nBValue;
		int nMaxTopicsB = 200000;
		FILE *fpB = fopen(szPrecBFilename, "r");
		if (fpB == NULL) {
			printf("Error: can't open %s\n", szPrecBFilename);
			vExit(-1);
		}
		aszTopicsB = (char **)pMalloc(nMaxTopicsB * sizeof(char *),
				"aszTopicsB");
		anB = (int *)pMalloc(nMaxTopicsB * sizeof(int), "anB");
		for (;;) {
			ptr = pGetLine(szLine, MAX_STRING_LENGTH, fpB);
			if (ptr == NULL) break; /* EOF */
			if (szLine[0] == '#') {
				continue;
			}
			nNumItems = sscanf( szLine, "%s %d",
			    szQueryID, &nBValue);
			if (nNumItems != 2) {
				printf("Error: cannot parse B line \"%s\"\n",
					szLine);
				vExit(-1);
			}
			if (nNumB >= nMaxTopicsB) {
				printf("Error: recompile with more B topics\n");
				vExit(-1);
			}
			aszTopicsB[nNumB] = strdup(szQueryID);
			anB[nNumB] = nBValue;
			nNumB++;
		}
		aszTopicsB[nNumB] = strdup("_inf_");
		fclose(fpB);
		printf("Loaded %d B values from %s\n", nNumB, szPrecBFilename);
		/* for (i = 0; i < nNumB; i++) {
		 *	printf("(%d): \"%s\" %d\n", i+1, aszTopicsB[i], anB[i]);
		 * }
		 * printf("\n");
		 */
	}
	if (szKValuesFilename) {
		char *ptr;
		int nKValue;
		int nMaxTopicsK = 200000;
		FILE *fpK = fopen(szKValuesFilename, "r");
		if (fpK == NULL) {
			printf("Error: can't open %s\n", szKValuesFilename);
			vExit(-1);
		}
		aszTopicsK = (char **)pMalloc(nMaxTopicsK * sizeof(char *),
				"aszTopicsK");
		anK = (int *)pMalloc(nMaxTopicsK * sizeof(int), "anK");
		for (;;) {
			ptr = pGetLine(szLine, MAX_STRING_LENGTH, fpK);
			if (ptr == NULL) break; /* EOF */
			if (szLine[0] == '#') {
				continue;
			}
			nNumItems = sscanf( szLine, "%s %d",
			    szQueryID, &nKValue);
			if (nNumItems != 2) {
				printf("Error: cannot parse K line \"%s\"\n",
					szLine);
				vExit(-1);
			}
			if (nNumK >= nMaxTopicsK) {
				printf("Error: recompile with more K topics\n");
				vExit(-1);
			}
			aszTopicsK[nNumK] = strdup(szQueryID);
			anK[nNumK] = nKValue;
			nNumK++;
		}
		aszTopicsK[nNumK] = strdup("_inf_");
		fclose(fpK);
		printf("Loaded %d K values from %s\n", nNumK, 
				szKValuesFilename);
		/* for (i = 0; i < nNumK; i++) {
		 *	printf("(%d): \"%s\" %d\n", i+1, aszTopicsK[i], anK[i]);
		 * }
		 * printf("\n");
		 */
	}
	if (nProbD) {
		adProb = (double *)pMalloc(MAX_RET_PER_TOPIC * sizeof(double),
				"adProb");  /* lz */
	}

	fpRun = fopen( szRunFilename, "r" );
	if (fpRun == NULL) {
		printf( "Error: can't open %s\n", szRunFilename );
		vExit(-1);
	}
	fpQrels = fopen( szQrelsFilename, "r" );
	if (fpQrels == NULL) {
		printf( "Error: can't open %s\n", szQrelsFilename );
		vExit(-1);
	}
	fpOut = fopen( szOutFilename, "w" );
	if (fpOut == NULL) {
		printf( "Error: can't open %s for writing\n", szOutFilename );
		vExit(-1);
	}
	fpOut2 = fopen( szOutFilename2, "w" );
	if (fpOut2 == NULL) {
		printf( "Error: can't open %s for writing\n", szOutFilename2 );
		vExit(-1);
	}
	if (szOutFilename5) {
		fpOut5 = fopen( szOutFilename5, "w" );
		if (fpOut5 == NULL) {
			printf( "Error: can't open %s for writing\n", 
					szOutFilename5 );
			vExit(-1);
		}
		if (bEstHTML) {
			fpHTML = fpOut5;
			fprintf(fpHTML,
				"<HTML>\n"
				"<HEAD>\n"
				"<TITLE>%s</TITLE>\n"
				"</HEAD>\n"
				"<H1>%s</H1>\n"
				"<PRE>\n"
				, szOutFilename5, szOutFilename5);
		}
		fprintf(fpOut5, "# l07_eval output\n");
		fprintf(fpOut5, "# results file: %s\n", szRunFilename);
		fprintf(fpOut5, "# qrels file: %s\n", szQrelsFilename);
		if (bEstHTML) {
			fprintf(fpHTML, "</PRE>\n");
		}
	}
	if (szOutResidFilename) {
		fpOutResid = fopen(szOutResidFilename, "w");
		if (fpOutResid == NULL) {
			printf("Error: can't open %s for writing\n", 
					szOutResidFilename);
			vExit(-1);
		}
	}
	if (szOutResidKFilename) {
		fpOutResidK = fopen(szOutResidKFilename, "w");
		if (fpOutResidK == NULL) {
			printf("Error: can't open file %s for writing\n", 
					szOutResidKFilename);
			vExit(-1);
		}
		if (!nNumK) {
			printf("Error: need Kfile with outResidK\n");
			vExit(-1);
		}
		anKr = (int *)pMalloc(nNumK * sizeof(int), "anKr");
		for (i = 0; i < nNumK; i++) {
			anKr[i] = 0;
		}
	}
	if (szOutFilename6) {
		fpOut6 = fopen( szOutFilename6, "w" );
		if (fpOut6 == NULL) {
			printf( "Error: can't open %s for writing\n", 
					szOutFilename6 );
			vExit(-1);
		}
		fprintf(fpOut6, "# l07_eval output (Interactive Task)\n");
	}
	if (szOutRelNumsFilename) {
		fpOutRelNums = fopen(szOutRelNumsFilename, "w");
		if (fpOutRelNums == NULL) {
			printf("Error: can't open %s for writing\n", 
					szOutRelNumsFilename);
			vExit(-1);
		}
	}
	if (nRelSubsetNum) {
		fpRelSubset = fopen(szOldRel07Name, "w");
		if (fpRelSubset == NULL) {
			printf("Error: can't open %s for writing\n",
				szOldRel07Name);
			vExit(-1);
		}
		fpNonSubset = fopen(szOldNon07Name, "w");
		if (fpNonSubset == NULL) {
			printf("Error: can't open %s for writing\n",
				szOldNon07Name);
			vExit(-1);
		}
	}
	memset(pESum, 0, sizeof(L07TE8));
	dMinFirstUnjudgedRank = 99999999.0;
	dMinFirstUnjudgedAndNotGrayRank = 99999999.0;
	nMinUnjudgedTopic = 0;
	nMinUnjudgedAndNotGrayTopic = 0;

	/* for each query */
	for (;;) {
		if (nNumRet == 0 && nQNumTop < nQueryID) {
			/* no results were found for the qrels of last time */
			/* we assume there was a gap in the qrels and 
			 * should try again; it's actually common to
			 * have qrel gaps, e.g. if discarded topics,
			 * or if filtered qrels to particular language, etc.
			 */
			goto ReadTopicFromRunFile;
		}

		/* load qrels */
		nNumQrels = 0;
		pNextDocno = asDocnoData;
		pNextRunid = asRunidData;
		nDocnoDataSize = 0;
		nRunidDataSize = 0;
		nNumRelevantQrels = 0;
		nNumHighlyRelevantQrels = 0;
		nNumNonRelevantQrels = 0;
		nNumGrayQrels = 0;
		dEstR = 0.0;
		dEstN = 0.0;
		dEstU = 0.0;
		dEstPool = 0.0;
		for (;;) {
			/* if line from last time, get it, else get next line */
			if (bQrelsLineLeftover) {
				bQrelsLineLeftover = 0;
			} else {
				ptrQrels = pGetLine(szQrelsLine, 
					MAX_STRING_LENGTH, fpQrels);
				if (ptrQrels == NULL) break; /* EOF */
			}
			if (nProbD) {
				/* extra arguments in qrels lines */
				if (nPrelsFields == 5) {
					/* used in TREC 2009 Web Ad Hoc */
					nNumItems = sscanf( szQrelsLine,
					    "%s %s %d %s %lf",
					    szQNumQrels,
					    szDocno, &nRelevanceJudgement,
					    szNTCIRType,
					    &dProb);
					if (nNumItems != 5) {
					    printf( "Error: expected 5 fields "
						    "but just got %ld items "
						    "in \"%s\"\n", nNumItems,
						    szQrelsLine);
					    vExit(-1);
					}
				} else if (nPrelsFields != 0) {
					printf("Error: unsupported prels "
						"format (prels=%d)\n",
						nPrelsFields);
					vExit(-1);
				} else if (bRunids) {
					nNumItems = sscanf( szQrelsLine,
					    "%s %s %s %d %lf %d %s",
					    szQNumQrels, szNTCIRType,
					    szDocno, &nRelevanceJudgement,
					    &dProb, &nHiRank, szRunID);
					if (nNumItems != 7) {
					    printf( "Error: expected 7 but "
						    "just got %ld items "
						    "in \"%s\"\n", nNumItems,
						    szQrelsLine);
					    vExit(-1);
					}
					if (nHiRank < 1) {
						printf("Error: hiRank must "
							"be >=1 in \"%s\"\n",
							szQrelsLine);
						vExit(-1);
					}
				} else {
					/* TREC Legal Track 2007-2009 */
					nNumItems = sscanf( szQrelsLine,
					    "%s %s %s %d %lf",
					    szQNumQrels, szNTCIRType,
					    szDocno, &nRelevanceJudgement,
					    &dProb);
					if (nNumItems != 5) {
					    printf( "Error: expected 5 but "
						    "just got %ld items "
						    "in \"%s\"\n", nNumItems,
						    szQrelsLine);
					    vExit(-1);
					}
				}
				if (dProb <= 0.0 || dProb > 1.0) {
				    printf( "Error: prob %lf must be in (0,1] "
					    "in \"%s\"\n", dProb,
					    szQrelsLine);
				    vExit(-1);
				}
			} else {
				nNumItems = sscanf( szQrelsLine,
				    "%s %s %s %d",
				    szQNumQrels, szNTCIRType,
				    szDocno, &nRelevanceJudgement);
				if (nNumItems != 4) {
				    printf( "Error: expected 4 but "
					    "just got %ld items "
					    "in \"%s\"\n", nNumItems,
					    szQrelsLine);
				    vExit(-1);
				}
			}
			if (bAssumeGrayNon) {
				if (nRelevanceJudgement < 0) {
					nRelevanceJudgement = 0;
				}
			}
			if (nRelevanceJudgement >= 1 &&
					nRelevanceJudgement < nMinRelLevel) {
				nRelevanceJudgement = 0;
			}
			if (nMaxRelLevel) {
				/* this is for getting separate relsubsets
				 * for ordinary relevant and high relevant.
				 * but user has to be careful not to use
				 * the subset of "non-relevant" does which
				 * actually includes filteredd high relevant
				 */
				if (nRelevanceJudgement > nMaxRelLevel) {
					nRelevanceJudgement = 0;
				}
			}
			nQNumQrels = nGetInt(szQNumQrels);
			if (bNTCIR) {
				if (*szNTCIRType == 'C') {
					if (nRelevanceJudgement != 0) {
						printf( "Error: C not 0\n" );
						vExit(-1);
					}
				} else if (*szNTCIRType == 'B' && 
						nRelevanceJudgement != 0) {
					/* partially relevant */
					nRelevanceJudgement = 3;
				} else if (*szNTCIRType == 'S' && 
						nRelevanceJudgement != 0) {
					/* highly relevant */
					nRelevanceJudgement = 2;
				}
			}
			if (nQNumQrelsPrev == -1) {
				nQNumQrelsPrev = nQNumQrels;
				strcpy(szQNumQrelsPrev, szQNumQrels);
			} else if (strcmp(szQNumQrelsPrev, szQNumQrels) != 0) {
				nQNumQrelsPrev = nQNumQrels;
				strcpy(szQNumQrelsPrev, szQNumQrels);
				bQrelsLineLeftover = 1;
				break;
			}
			nQueryID = nQNumQrels;
			strcpy(szQueryID, szQNumQrels);

			if (nNumQrels >= MAX_QRELS_PER_QUERY) {
				printf( "Recompile with more space "
					"for qrels array\n" );
				vExit(-1);
			}

			nDocnoLen = strlen(szDocno);
			if ((nDocnoLen + nDocnoDataSize + 1) < 
					DOCNO_DATA_SIZE) {
				strcpy(pNextDocno, szDocno);
				g_aszDocnos[nNumQrels] = pNextDocno;
				acRelevanceJudgement[nNumQrels] = 
					(char)nRelevanceJudgement;
				if (bRunids) {
					nRunidLen = strlen(szRunID);
					if ((nRunidLen + nRunidDataSize + 1) >=
							DOCNO_DATA_SIZE) {
						printf( 
						"Recompile with more space "
						"for runids\n" );
						vExit(-1);
					}
					strcpy(pNextRunid, szRunID);
					aszRunids[nNumQrels] = pNextRunid;
					g_anHiRanks[nNumQrels] = nHiRank;
				}
				acFound[nNumQrels] = (char)0; /* init */
				if (nRelevanceJudgement > 0) {
					nNumRelevantQrels++;
					if (nRelevanceJudgement == 2) {
						nNumHighlyRelevantQrels++;
					}
					if (nProbD) {
						dEstR += (1.0 / dProb);
					}
				} else if (nRelevanceJudgement == 0) {
					nNumNonRelevantQrels++;
					if (nProbD) {
						dEstN += (1.0 / dProb);
					}
				} else {
					nNumGrayQrels++;
					if (nProbD) {
						dEstU += (1.0 / dProb);
					}
				}
				if (nProbD) {
					adQrelsProb[nNumQrels] = dProb;
				}
				pNextDocno += (nDocnoLen + 1);
				if (bRunids) {
					pNextRunid += (nRunidLen + 1);
				}
			} else {
				printf( "Recompile with more space "
						"for qrels\n" );
				vExit(-1);
			}
			nNumQrels++;
		}
		if (nProbD) {
			nLimR = nProbD - nNumNonRelevantQrels;
			nLimN = nProbD - nNumRelevantQrels;
			nLimU = nProbD - 
				(nNumRelevantQrels + nNumNonRelevantQrels);
			if (nEstOpts != 1) { /* fix20100515 */
				if (dEstR > (double)nLimR) {
					dEstR = (double)nLimR;
				}
				if (dEstN > (double)nLimN) {
					dEstN = (double)nLimN;
				}
				if (dEstU > (double)nLimU) {
					dEstU = (double)nLimU;
				}
			}
			dEstPool = dEstR + dEstN + dEstU;
			if (dEstR < 0.0) {
				printf("Error: estR negative (%lf) "
					"in topic %s\n",
					dEstR, szQueryID);
				vExit(-1);
			}
			if (bHiEstR && dEstR > (double)nHiEstR) {
				printf("Skipping topic %s "
					"(estR=%6.4lf > hiEstR (%d))\n",
					szQueryID, dEstR, nHiEstR);
				nNumFilteredQueries++;
				continue;
			}
		}
		if (nRelSubsetNum) {
			printf(" Topic %s (%d rel, %d nonrel)\n",
				szQueryID, 
				nNumRelevantQrels, 
				nNumNonRelevantQrels);
			/* initialize subset list */
			for (i = 0; i < nNumQrels; i++) {
				abQrelsRelSubset[i] = 0;
				abQrelsNonSubset[i] = 0;
			}
			nNumRandRels = nRelSubsetNum;
			if (nNumRandRels > nNumRelevantQrels) {
				nNumRandRels = nNumRelevantQrels;
			}
			printf("  Picking %d random rels\n", nNumRandRels);
			if (nNumRelevantQrels > RAND_MAX) {
				/* below code would need altering */
				printf("Error: nNumRelevantQrels > RAND_MAX\n");
				vExit(-1);
			}
			i = 0;
			for (;;) {
				if (i == nNumRandRels) {
					break;
				}
				r = rand() % nNumRelevantQrels;
				if (abQrelsRelSubset[r]) {
					/* already picked this one */
					continue;
				}
				abQrelsRelSubset[r] = 1;
				i++;
			}
			r = 0;
			j = 0;
			for (i = 0; i < nNumQrels; i++) {
				if (acRelevanceJudgement[i] != 1 &&
					  acRelevanceJudgement[i] != 2) {
					continue;
				}
				if (abQrelsRelSubset[r]) {
					fprintf(fpRelSubset, 
					  "%s\tQ0\t%s\t%d\t%d\t%s\n",
					  szQueryID, 
					  g_aszDocnos[i],
					  j,
					  nNumRandRels - j,
					  szOldRel07Name);
					j++;
				}
				r++;
			}
			if (j != nNumRandRels) {
				printf("Error: j != nNumRandRels\n");
				vExit(-1);
			}
			/* same as above, but for nonrels */
			nNumRandNons = nRelSubsetNum;
			if (nNumRandNons > nNumNonRelevantQrels) {
				nNumRandNons = nNumNonRelevantQrels;
			}
			printf("  Picking %d random non-rels\n", nNumRandNons);
			if (nNumNonRelevantQrels > RAND_MAX) {
				/* below code would need altering */
				printf("Error: "
					"nNumNonRelevantQrels > RAND_MAX\n");
				vExit(-1);
			}
			i = 0;
			for (;;) {
				if (i == nNumRandNons) {
					break;
				}
				r = rand() % nNumNonRelevantQrels;
				if (abQrelsNonSubset[r]) {
					/* already picked this one */
					continue;
				}
				abQrelsNonSubset[r] = 1;
				i++;
			}
			r = 0;
			j = 0;
			for (i = 0; i < nNumQrels; i++) {
				if (acRelevanceJudgement[i] != 0) {
					continue;
				}
				if (abQrelsNonSubset[r]) {
					fprintf(fpNonSubset, 
					  "%s\tQ0\t%s\t%d\t%d\t%s\n",
					  szQueryID, 
					  g_aszDocnos[i],
					  j,
					  nNumRandNons - j,
					  szOldNon07Name);
					j++;
				}
				r++;
			}
			if (j != nNumRandNons) {
				printf("Error: j != nNumRandNons\n");
				vExit(-1);
			}
		}

		/* qsort pointers to qrels */
		for (i = 0; i < nNumQrels; i++ ) {
			anQrelsIndex[i] = i;
		}
		qsort(anQrelsIndex, nNumQrels, sizeof(int), fnCompareDocnos);

ReadTopicFromRunFile:
		/* load topic results from run file */
		nNumRet = 0;
		nNumRetJudged = 0;
		nRelevant = 0;
		nHighlyRelevant = 0;
		nJudgedNonRelevant = 0;
		nRetGray = 0;
		dPrecSum = 0.0;
		dPrecSumJ = 0.0;
		nFirstRelevantRank = 0;
		nFirstRelevantRankJudged = 0;
		nNumResidOut = 0;
		nNumRetJudgedOrGray = 0;
		for (;;) {
			/* if line from last time, get it, else get next line */
			if (bRunLineLeftover) {
				bRunLineLeftover = 0;
			} else {
				pRunLine = pGetLine(szRunLine, 
					MAX_STRING_LENGTH, fpRun);
				if (pRunLine == NULL) break; /* EOF */
			}

			if (!bResidQrels) {
				/* normal case */
				/* 251 0 FR940114-2-00049       1   29 MYTREC-328-cTREC/490583/281094:s */
				nNumItems = sscanf( szRunLine,
				    "%s %s %s %s %s %s",
				    szQNumTop, szQ0,
				    szDocno, szRank,
				    szRSV, szRunID );
				if (nNumItems != 6) {
				    printf( "Error: expected 6 but "
					    "just got %ld items "
					    "in \"%s\"\n", nNumItems,
					    szRunLine);
				    vExit(-1);
				}
			} else {
				/* residual qrels case (L07 RF task) */
				/* 7 0 aai42e00 0 1.000000000000 */
				nNumItems = sscanf(szRunLine,
				    "%s %s %s",
				    szQNumTop, szQ0, szDocno);
				if (nNumItems != 3) {
				    printf( "Error: expected 3 but "
					    "just got %ld items "
					    "in \"%s\"\n", nNumItems,
					    szRunLine);
				    vExit(-1);
				}
				strcpy(szRank, "");
				strcpy(szRSV, "");
				strcpy(szRunID, "");
			}
			nQNumTop = nGetInt(szQNumTop);
		
			if (nQNumTop < nQueryID) {
				/* if nNumRet == 0, assume it's the
				 * case of gaps in the qrels,
				 * so we want to skip over the
				 * top results for nQNumTop
				 */
				if (nNumRet != 0) {
					bRunLineLeftover = 1;
					nKresidIndex = -1;
				}
				break;
			} else if (nQNumTop > nQueryID) {
				bRunLineLeftover = 1;
				nKresidIndex = -1;
				break;
			}
			if (nNumRet >= MAX_RET_PER_TOPIC) {
				printf("Error: recompile with new "
					"MAX_RET_PER_TOPIC\n");
				vExit(-1);
			}
			if (nM1000 && nNumRet >= nM1000) {
				/* exclude docs past first M */
				continue;
			}
			if (fpOutResidK && nKresidIndex == -1) {
				nKresidIndex++;
				while (nKresidIndex < nNumK) {
					if (strcmp(aszTopicsK[nKresidIndex],
							szQNumTop) == 0) {
						break;
					}
					nKresidIndex++;
				}
				if (nKresidIndex == nNumK) {
					printf("Error: can't find K value for "
						"%s\n", szQNumTop);
					vExit(-1);
				}
			}
			/* is docno in qrels? */
			nDocnoIndex = nBinSearchForDocno(szDocno, anQrelsIndex,
				nNumQrels);
			if (nDocnoIndex == -1) {
				if (bJudgedOnly) { /* exclude unjudged */
					continue;
				}
				cRel = '-'; /* assumed non-rel */
			} else if (acRelevanceJudgement[
					anQrelsIndex[nDocnoIndex]] == (char)-1
				    || acRelevanceJudgement[
					anQrelsIndex[nDocnoIndex]] == 
					(char)-2) {
				if (bJudgedOnly) { /* exclude unjudged */
					continue;
				}
				cRel = 'U'; /* L07 gray */
				nRetGray++;
			} else if (((signed char)(acRelevanceJudgement[
					anQrelsIndex[nDocnoIndex]])) > 0) {
				if (acRelevanceJudgement[
					    anQrelsIndex[nDocnoIndex]] == 2) {
					cRel = 'H'; /* judged highly relevant */
					nHighlyRelevant++;
				} else if (acRelevanceJudgement[
					    anQrelsIndex[nDocnoIndex]] == 3) {
					cRel = 'P'; /* partially relevant */
				} else {
					cRel = 'R'; /* judged relevant */
				}
				nRelevant++;
				if (nRelevant == 1) {
					nFirstRelevantRank = nNumRet + 1;
					nFirstRelevantRankJudged = 
						nNumRetJudged + 1;
				}
				dPrecSum += nRelevant / (nNumRet + 1.0);
				dPrecSumJ += nRelevant / (nNumRetJudged + 1.0);
			} else {
				cRel = 'N'; /* judged non-relevant */
				nJudgedNonRelevant++;
			}
			acRelString[nNumRet] = cRel;
			if (nDocnoIndex != -1) {
				acFound[anQrelsIndex[nDocnoIndex]] = (char)1;
			}
			if (nProbD) {
				if (nDocnoIndex != -1) {
					adProb[nNumRet] = 
					 adQrelsProb[anQrelsIndex[nDocnoIndex]];
				} else {
					adProb[nNumRet] = 0.0;
				}
			}

			/* normal case */
			fprintf( fpOut, "%s\t%c\t%s\t%s\t%s\t%s\n",
				szQueryID, cRel, szDocno, 
				szRank, szRSV, szRunID );
			if (0 && bEstHTML) {
				if (nDocnoIndex != -1) {
					fprintf(fpHTML, "%6d %c %s",
						nNumRet+1, cRel, szDocno);
					if (bRunids) {
						int r = 
						  anQrelsIndex[nDocnoIndex];
						fprintf(fpHTML, 
							" (%s-%d %6.4lf)",
							aszRunids[r],
							g_anHiRanks[r],
							1.0 / adQrelsProb[r]);
					}
					fprintf(fpHTML, "\n");
				}
			}
			nNumRet++;
			if (cRel != '-' && cRel != 'U') {
				nNumRetJudged++;
			}
			if (cRel != '-') {
				nNumRetJudgedOrGray++;
			}
			if (fpOutResid && (cRel == '-') &&
				((nResidCap == 0 && /* year 2007 RF task */
				  (nNumResidOut < 25000 || 
				   (nNumResidOut < 127525 &&
				    strcmp(szQueryID, "27") == 0) ||
				   (nNumResidOut < 38723 &&
				    strcmp(szQueryID, "37") == 0)))
				 || (nResidCap != 0 && /* year 2008 */
				  nNumResidOut < nResidCap)
				 )) {
				/* filtered old judged (and old gray) */
				if (!bResidQrels) {
				  fprintf(fpOutResid,
					"%s\t%s\t%s\t%s\t%s\t%s\n",
					szQueryID, szQ0, szDocno, 
					szRank, szRSV, szRunID);
				} else {
				  /* bResidQrels case */
				  fprintf(fpOutResid, "%s\n", szRunLine);
				}
				if (fpOutResidK &&
					  nNumRet <= anK[nKresidIndex]) {
					anKr[nKresidIndex] += 1;
				}
				nNumResidOut++;
			}
			if (fpOut6) {
				if (nNumRet == 1) {
					fprintf(fpOut6, "---\n"
						"Topic %s\n",
						szQueryID);
				}
				if (cRel != '-') {
				  fprintf( fpOut6, "%s\t%c\t%s\t%d\t%d\t%s\n",
					szQueryID, cRel, szDocno, 
					nNumRetJudgedOrGray, 
					100 - nNumRetJudgedOrGray, 
					szRunID );
				}
			}
		}
		if (nNumRelevantQrels == 0 || 
			  (nNumRet == 0)) { /* fix20090815, skip topic */
			if (pRunLine == NULL) break;
			continue;
		}

		memset(pE, 0, sizeof(L07TE8));
		pE->l07_aszStr[L07_TE8_TOPIC] = szQueryID;
		pE->l07_anScore[L07_TE8_RETRIEVED] = nNumRet;
		pE->l07_anScore[L07_TE8_NUM_RELEVANT] = 
				nNumRelevantQrels;
		pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED] = 
				nRelevant;
		if (nNumRelevantQrels > 0) {
			dAvgPrec = dPrecSum / nNumRelevantQrels;
			dAvgPrecJ = dPrecSumJ / nNumRelevantQrels;
		} else {
			dAvgPrec = 0.0;
			dAvgPrecJ = 0.0;
		}
		pE->l07_adScore[L07_TE8_RETJ] = nNumRetJudged;

		pE->l07_adScore[L07_TE8_NUMQRELS] = nNumQrels;
		pE->l07_adScore[L07_TE8_NUMREL] = nNumRelevantQrels;
		pE->l07_adScore[L07_TE8_NUMNONREL] = nNumNonRelevantQrels;
		pE->l07_adScore[L07_TE8_NUMGRAY] = nNumGrayQrels;

		/* verify dAvgPrec */
		nNumRel = 0;
		dSum = 0.0;
		for (i = 0; i < nNumRet; i++) {
			bRel = (acRelString[i] == 'R' || acRelString[i] == 'H' 
					|| acRelString[i] == 'P');
			if (bRel) {
				nNumRel++;
				dSum += (nNumRel / (double)(i + 1));
			}
		}
		dScore = dSum / nNumRelevantQrels;
		if (dScore != dAvgPrec) {
			printf("Error: dAvgPrec=%lf, dScore=%lf, R=%d\n",
				dAvgPrec, dScore, nNumRelevantQrels);
			vExit(-1);
		}
		pE->l07_adScore[L07_TE8_MAP] = dScore;
		pE->l07_adScore[L07_TE8_MAPJ] = dAvgPrecJ;

		/* R-Prec */
		nNumRel = 0;
		for (i = 0; i < nNumRet; i++) {
			bRel = (acRelString[i] == 'R' || acRelString[i] == 'H');
			if (bRel) {
				nNumRel++;
			}
			if ((i + 1) == nNumRelevantQrels) {
				break;
			}
		}
		dScore = nNumRel / (double)nNumRelevantQrels;
		pE->l07_adScore[L07_TE8_RP] = dScore;

		/* Precision@n */
		nNumRel5 = 0;
		nNumRel10 = 0;
		nNumRel15 = 0;
		nNumRel20 = 0;
		nNumRel30 = 0;
		nNumRel100 = 0;
		nNumRel200 = 0;
		nNumRel500 = 0;
		nNumRel1000 = 0;
		dGenRel10 = 0.0;
		nNumRel = 0;
		for (i = 0; i < nNumRet; i++) {
			bRel = (acRelString[i] == 'R' || acRelString[i] == 'H');
			if (bRel) {
				if (i < 5) {nNumRel5++;}
				if (i < 10) {nNumRel10++;}
				if (i < 15) {nNumRel15++;}
				if (i < 20) {nNumRel20++;}
				if (i < 30) {nNumRel30++;}
				if (i < 100) {nNumRel100++;}
				if (i < 200) {nNumRel200++;}
				if (i < 500) {nNumRel500++;}
				if (i < 1000) {nNumRel1000++;}
				if (i < 10) {
					dGenRel10 += (1.0 + 1/(pow(2.0,i+1.0)));
				}
				nNumRel++;
			}
		}
		pE->l07_adScore[L07_TE8_P5] = nNumRel5 / 5.0;
		pE->l07_adScore[L07_TE8_P10] = nNumRel10 / 10.0;
		pE->l07_adScore[L07_TE8_P15] = nNumRel15 / 15.0;
		pE->l07_adScore[L07_TE8_P20] = nNumRel20 / 20.0;
		pE->l07_adScore[L07_TE8_P30] = nNumRel30 / 30.0;
		pE->l07_adScore[L07_TE8_P100] = nNumRel100 / 100.0;
		pE->l07_adScore[L07_TE8_P200] = nNumRel200 / 200.0;
		pE->l07_adScore[L07_TE8_P500] = nNumRel500 / 500.0;
		pE->l07_adScore[L07_TE8_P1000] = nNumRel1000 / 1000.0;
		pE->l07_adScore[L07_TE8_RECINF] = 
				nNumRel / (double)nNumRelevantQrels;
		/* Interpolated Precision */
		nNumRel = 0;
		dMaxPrec0 = 0.0;
		dMaxPrec10 = 0.0;
		dMaxPrec20 = 0.0;
		dMaxPrec30 = 0.0;
		dMaxPrec40 = 0.0;
		dMaxPrec50 = 0.0;
		dMaxPrec60 = 0.0;
		dMaxPrec70 = 0.0;
		dMaxPrec80 = 0.0;
		dMaxPrec90 = 0.0;
		dMaxPrec100 = 0.0;
		for (i = 0; i < nNumRet; i++) {
			bRel = (acRelString[i] == 'R' || acRelString[i] == 'H');
			if (bRel) {
				nNumRel++;
				dPrec = nNumRel / (double)(i+1);
				dRec = nNumRel / (double)nNumRelevantQrels;
				if (dRec >= 0.0) {
					dMaxPrec0 = L07_MAX(dMaxPrec0, dPrec);}
				if (dRec > 0.09999) {
					dMaxPrec10 = L07_MAX(dMaxPrec10, dPrec);}
				if (dRec > 0.19999) {
					dMaxPrec20 = L07_MAX(dMaxPrec20, dPrec);}
				if (dRec > 0.29999) {
					dMaxPrec30 = L07_MAX(dMaxPrec30, dPrec);}
				if (dRec > 0.39999) {
					dMaxPrec40 = L07_MAX(dMaxPrec40, dPrec);}
				if (dRec > 0.49999) {
					dMaxPrec50 = L07_MAX(dMaxPrec50, dPrec);}
				if (dRec > 0.59999) {
					dMaxPrec60 = L07_MAX(dMaxPrec60, dPrec);}
				if (dRec > 0.69999) {
					dMaxPrec70 = L07_MAX(dMaxPrec70, dPrec);}
				if (dRec > 0.79999) {
					dMaxPrec80 = L07_MAX(dMaxPrec80, dPrec);}
				if (dRec > 0.89999) {
					dMaxPrec90 = L07_MAX(dMaxPrec90, dPrec);}
				if (dRec > 0.99999) {
					dMaxPrec100 = L07_MAX(dMaxPrec100, 
						dPrec);}
			}
		}
		pE->l07_adScore[L07_TE8_R0] = dMaxPrec0;
		pE->l07_adScore[L07_TE8_R0+1] = dMaxPrec10;
		pE->l07_adScore[L07_TE8_R0+2] = dMaxPrec20;
		pE->l07_adScore[L07_TE8_R0+3] = dMaxPrec30;
		pE->l07_adScore[L07_TE8_R0+4] = dMaxPrec40;
		pE->l07_adScore[L07_TE8_R0+5] = dMaxPrec50;
		pE->l07_adScore[L07_TE8_R0+6] = dMaxPrec60;
		pE->l07_adScore[L07_TE8_R0+7] = dMaxPrec70;
		pE->l07_adScore[L07_TE8_R0+8] = dMaxPrec80;
		pE->l07_adScore[L07_TE8_R0+9] = dMaxPrec90;
		pE->l07_adScore[L07_TE8_R0+10] = dMaxPrec100;

		dAvgPrecSum += dAvgPrec;
		nNumRelevantQrelsSum += nNumRelevantQrels;
		nNumNonRelevantQrelsSum += nNumNonRelevantQrels;
		if (nFirstRelevantRank > 0) {
			dMRR = 1.0 / (double)nFirstRelevantRank;
		} else {
			dMRR = 0.0;
		}
		pE->l07_adScore[L07_TE8_RR] = dMRR;
		dFRS = 0.0;
		dFRS30 = 0.0; /* fix20080310 */
		dS1 = 0.0;
		dS5 = 0.0;
		dS10 = 0.0;
		dSInf = 0.0;
		dFRSJ = 0.0;
		dFRS30J = 0.0; /* fix20080310 */
		dS1J = 0.0;
		dS5J = 0.0;
		dS10J = 0.0;
		if (nFirstRelevantRank > 0) {
			/* FRS = 1.08^(1-rank) */
			dFRS = pow(1.08, 1.0 - nFirstRelevantRank);
			dFRS30 = pow(1.024, 1.0 - nFirstRelevantRank);
			if (nFirstRelevantRank == 1) {dS1 = 1.0;}
			if (nFirstRelevantRank <= 5) {dS5 = 1.0;}
			if (nFirstRelevantRank <= 10) {dS10 = 1.0;}
			dSInf = 1.0;
			dFRSJ = pow(1.08, 1.0 - nFirstRelevantRankJudged);
			dFRS30J = pow(1.024, 1.0 - nFirstRelevantRankJudged);
			if (nFirstRelevantRankJudged == 1) {dS1J = 1.0;}
			if (nFirstRelevantRankJudged <= 5) {dS5J = 1.0;}
			if (nFirstRelevantRankJudged <= 10) {dS10J = 1.0;}
		}
		pE->l07_adScore[L07_TE8_FRS] = dFRS;
		pE->l07_adScore[L07_TE8_FRS30] = dFRS30;
		pE->l07_adScore[L07_TE8_S1] = dS1;
		pE->l07_adScore[L07_TE8_S5] = dS5;
		pE->l07_adScore[L07_TE8_S10] = dS10;
		pE->l07_adScore[L07_TE8_SINF] = dSInf;
		pE->l07_adScore[L07_TE8_FRSJ] = dFRSJ;
		pE->l07_adScore[L07_TE8_FRS30J] = dFRS30J;
		pE->l07_adScore[L07_TE8_S1J] = dS1J;
		pE->l07_adScore[L07_TE8_S5J] = dS5J;
		pE->l07_adScore[L07_TE8_S10J] = dS10J;
		pE->l07_adScore[L07_TE8_FIRSTRANK] = 
				nFirstRelevantRank;

		/* GMAP */
		{
			double cdLinLogAvgPrecMin1 = log(0.00001);
			double cdLinLogAvgPrecMax1 = log(1.00001);
			double dLog1 = log(dAvgPrec + 0.00001);
			double dLog2 = log(L07_MAX(dAvgPrec,0.00001));
			double dLAP1 = 
				(dLog1 - cdLinLogAvgPrecMin1) /
				(cdLinLogAvgPrecMax1 - cdLinLogAvgPrecMin1);
			double dLAP2 = 
				(dLog2 - cdLinLogAvgPrecMin1) / 
				(0.0 - log(0.00001));
			pE->l07_adScore[L07_TE8_LOG1] = dLog1;
			pE->l07_adScore[L07_TE8_LOG2] = dLog2;
			pE->l07_adScore[L07_TE8_LINLOG1] = dLAP1;
			pE->l07_adScore[L07_TE8_LINLOG2] = dLAP2;
		}

		/* bpref (from http://trec.nist.gov/pubs/trec15/appendices/CE.MEASURES06.pdf ) */
		nNumRel = 0;
		dSum = 0.0;
		nNumNonRel = 0;
		nMinRN = nNumRelevantQrels;
		if (nNumNonRelevantQrels < nMinRN) {
			nMinRN = nNumNonRelevantQrels;
		}
		if (nMinRN == 0) {
			/* fix20080210: prevent division by zero if 
			 * no non-relevants
			 */
			nMinRN = 1;
		}
		for (i = 0; i < nNumRet; i++) {
			bRel = (acRelString[i] == 'R' || acRelString[i] == 'H');
			if (bRel) {
				nNumRel++;
				dSum += ((nMinRN - nNumNonRel) /
					(double)nMinRN);
			} else if (acRelString[i] != '-' && 
					acRelString[i] != 'U') {
				nNumNonRel++;
				if (nNumNonRel == nNumRelevantQrels) {
					break;
				}
			}
		}
		dScore = dSum / nNumRelevantQrels;
		/*pE->l07_adScore[L07_TE8_BPCORR] = dScore;*/
		pE->l07_adScore[L07_TE8_BP] = dScore;

		/* FirstUnjudgedRank */
		dFirstUnjudgedRank = nM1000 + 1;
		for (i = 0; i < nNumRet; i++) {
			if (acRelString[i] == '-' || acRelString[i] == 'U') {
				dFirstUnjudgedRank = i + 1;
				break;
			}
		}
		dFirstUnjudgedAndNotGrayRank = nM1000 + 1;
		for (i = 0; i < nNumRet; i++) {
			if (acRelString[i] == '-') {
				dFirstUnjudgedAndNotGrayRank = i + 1;
				break;
			}
		}
		pE->l07_adScore[L07_TE8_FIRSTUNJUDGED] = dFirstUnjudgedRank;

		/* Unjudged@n */
		nNumUnjudged1 = 0;
		nNumUnjudged5 = 0;
		nNumUnjudged10 = 0;
		nNumUnjudged50 = 0;
		nNumUnjudged100 = 0;
		nNumUnjudged1000 = 0;
		for (i = 0; i < nNumRet; i++) {
			bJudged = (acRelString[i] != '-' && 
					acRelString[i] != 'U');
			if (!bJudged) {
				if (i <	1) {nNumUnjudged1++;}
				if (i < 5) {nNumUnjudged5++;}
				if (i < 10) {nNumUnjudged10++;}
				if (i < 50) {nNumUnjudged50++;}
				if (i < 100) {nNumUnjudged100++;}
				if (i < 1000) {nNumUnjudged1000++;}
			}
		}
		pE->l07_adScore[L07_TE8_UJ1] = nNumUnjudged1 / 1.0;
		pE->l07_adScore[L07_TE8_UJ5] = nNumUnjudged5 / 5.0;
		pE->l07_adScore[L07_TE8_UJ10] = nNumUnjudged10 / 10.0;
		pE->l07_adScore[L07_TE8_UJ50] = nNumUnjudged50 / 50.0;
		pE->l07_adScore[L07_TE8_UJ100] = nNumUnjudged100 / 100.0;
		pE->l07_adScore[L07_TE8_UJ1000] = nNumUnjudged1000 / 1000.0;

		if (szPrecBFilename) {
			for (;;) {
				nBindex++;
				if (nBindex > nNumB) {
					printf("Error: "
					 "can't find B value for topic"
					 " %s in %s\n",
					 pE->l07_aszStr[L07_TE8_TOPIC],
					 szPrecBFilename);
					vExit(-1);
				}
				if (strcmp(
					 pE->l07_aszStr[L07_TE8_TOPIC],
					 aszTopicsB[nBindex]) == 0) {
					break; /* found B */
				}
			}
			nB = anB[nBindex];
			if (nB <= 0) {
				printf("Error: topic %s "
					"has non-positive B value %d\n",
					aszTopicsB[nBindex],
					nB);
				vExit(-1);
			}
			/* Precision@B */
			dB = (double)nB;
			nNumRelB = 0;
			nNumJudgedB = 0;
			bJudged1 = 0;
			nSFirstJudgedB = 0;
			nSLastJudgedB = 0;
			for (i = 0; i < nNumRet; i++) {
				bRel = (acRelString[i] == 'R' || 
						acRelString[i] == 'H');
				if (bRel) {
					if (i < nB) {nNumRelB++;}
				}
				bJudged = (acRelString[i] != '-' && 
					acRelString[i] != 'U');
				if (bJudged) {
					if (i <	nB) {
						nNumJudgedB++;
						if (!bJudged1) {
							if (bRel) {
							  nSFirstJudgedB = 1;
							}
							bJudged1 = 1;
						}
						if (bRel) {
							nSLastJudgedB = 1;
						} else {
							nSLastJudgedB = 0;
						}
					}
				}
			}
			pE->l07_adScore[L07_TE8_B] = dB;
			pE->l07_adScore[L07_TE8_JUDGEDB] = 
					nNumJudgedB;
			pE->l07_adScore[L07_TE8_RELEVANTB] = 
					nNumRelB;
			pE->l07_adScore[L07_TE8_PRECB] = 
					nNumRelB / dB;
			pE->l07_adScore[L07_TE8_RECALLB] = 
					nNumRelB / (double)nNumRelevantQrels;

			nRetB = nB; /* min(B,ret) */
			if (nNumRet < nB) {
				nRetB = nNumRet;
			}
			pE->l07_adScore[L07_TE8_RETB] = nRetB;
			pE->l07_adScore[L07_TE8_PCTRETB] = nRetB / dB;
			if (nRetB) {
				pE->l07_adScore[L07_TE8_PCTJUDB] = 
					nNumJudgedB / (double)nRetB;
			} else {
				pE->l07_adScore[L07_TE8_PCTJUDB] = 1.0;
			}
			if (nNumJudgedB) {
				pE->l07_adScore[L07_TE8_PRECJUDB] = 
					nNumRelB / (double)nNumJudgedB;
			} else {
				pE->l07_adScore[L07_TE8_PRECJUDB] = 
					0.0;
			}
			pE->l07_adScore[L07_TE8_SFIRSTJB] = 
					nSFirstJudgedB;
			pE->l07_adScore[L07_TE8_SLASTJB] = 
					nSLastJudgedB;
		}

		if (nProbD) {
			pE->l07_adEstScore[L07_EST_R] = dEstR;
			pE->l07_adEstScore[L07_EST_N] = dEstN;
			pE->l07_adEstScore[L07_EST_G] = dEstU;
			pE->l07_adEstScore[L07_EST_POOL] = dEstPool;

			vSumToK(acRelString, adProb, 
				nNumRet, nNumRet, 
				&dEstRret, &dEstNret, &dEstUret,
				&nNumJudgedInf, nEstOpts, NULL);
			dEstPoolRet = dEstRret + dEstNret + dEstUret;
			pE->l07_adEstScore[L07_EST_RRET] = dEstRret;
			pE->l07_adEstScore[L07_EST_NRET] = dEstNret;
			pE->l07_adEstScore[L07_EST_GRET] = dEstUret;
			pE->l07_adEstScore[L07_EST_POOL_RET] = dEstPoolRet;

			if (fpOutRelNums) {
				/* printed tabbed for use in chart software */
				fprintf(fpOutRelNums, "%s\t%6.4lf\t%6.4lf\n",
					pE->l07_aszStr[L07_TE8_TOPIC],
					dEstRret, dEstR - dEstRret);
			}

			vGetPRUatK(acRelString, adProb, 
				nNumRet, nNumRet, 
				&dEstPrecInf, &dEstRecallInf, &dEstGrayInf,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_PREC_INF] = dEstPrecInf;
			pE->l07_adEstScore[L07_EST_RECALL_INF] = dEstRecallInf;
			pE->l07_adEstScore[L07_EST_GRAY_INF] = dEstGrayInf;

			nK = 5;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P5] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R5] = dEstRecallK;
			pE->l07_adEstScore[L07_EST_GRAY_5] = dEstGrayK;

			nK = 10;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P10] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R10] = dEstRecallK;

			nK = 100;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P100] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R100] = dEstRecallK;

			nK = 1000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P1000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R1000] = dEstRecallK;

			nK = 5000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P5000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R5000] = dEstRecallK;

			nK = 10000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P10000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R10000] = dEstRecallK;

			nK = 15000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P15000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R15000] = dEstRecallK;

			nK = 20000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P20000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R20000] = dEstRecallK;

			nK = 25000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P25000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R25000] = dEstRecallK;

			nK = 50000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P50000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R50000] = dEstRecallK;

			nK = 75000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P75000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R75000] = dEstRecallK;

			nK = 100000;
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nK, 
				&dEstPrecK, &dEstRecallK, &dEstGrayK,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_P100000] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_R100000] = dEstRecallK;

			/* Est. R-Precision, R-Recall, etc. */
			/* For R, we use the ceiling of dEstR (i.e. round up)
			 * e.g. if dEstR=123.001, then nRCeil=124
			 *      if dEstR=123.000, then nRCeil=123
			 */
			nRCeil = (int)dEstR;
			if ((double)nRCeil < dEstR) {
				nRCeil++;
			}
			vGetMeasuresAtK(acRelString, adProb, 
				nNumRet, nRCeil, dEstR, dEstN, nEstOpts, 
				dEpsilon, pK);
			pE->l07_adEstScore[L07_EST_R_CEIL] = (double)nRCeil;
			pE->l07_adEstScore[L07_EST_R_PREC] = pK->l7m_dEstPrecK;
			pE->l07_adEstScore[L07_EST_R_RECALL] = 
					pK->l7m_dEstRecallK;
			pE->l07_adEstScore[L07_EST_R_F1] = pK->l7m_dEstF1K;
			pE->l07_adEstScore[L07_EST_R_GRAY] = pK->l7m_dEstGrayK;

			/* measures at depth K */
			/* get K from Kfile if specified, else use num_ret */
			if (szKValuesFilename) {
				for (;;) {
					nKindex++;
					if (nKindex > nNumK) {
						printf("Error: "
						 "can't find K value for topic"
						 " %s in %s\n",
						 pE->l07_aszStr[L07_TE8_TOPIC],
						 szKValuesFilename);
						vExit(-1);
					}
					if (strcmp(
						 pE->l07_aszStr[L07_TE8_TOPIC],
						 aszTopicsK[nKindex]) == 0) {
						break; /* found K */
					}
				}
				nK = anK[nKindex];
				if (nK < 0) {
					printf("Error: Kfile topic %s "
						"has negative value %d\n",
						aszTopicsK[nKindex],
						nK);
					vExit(-1);
				} else if (nK > nNumRet) {
					printf("Warning: K (%d) exceeds "
						"the number retrieved (%d) "
						"for topic %s.  "
						"(Reducing K to %d)\n",
						nK, nNumRet, 
						pE->l07_aszStr[L07_TE8_TOPIC],
						nNumRet);
					nK = nNumRet; 
				}
			} else if (bUseRforK) {
				nK = nRCeil;
			} else {
				nK = nNumRet;
			}
			vGetMeasuresAtK(acRelString, adProb, 
				nNumRet, nK, dEstR, dEstN, nEstOpts,
				dEpsilon, pK);
			pE->l07_adEstScore[L07_K] = (double)nK;
			pE->l07_adEstScore[L07_EST_K_PREC] = pK->l7m_dEstPrecK;
			pE->l07_adEstScore[L07_EST_K_RECALL] = 
					pK->l7m_dEstRecallK;
			pE->l07_adEstScore[L07_EST_K_GRAY] = pK->l7m_dEstGrayK;
			pE->l07_adEstScore[L07_EST_K_JACCARD] = 
					pK->l7m_dEstJaccardK;
			pE->l07_adEstScore[L07_EST_K_FALSENEG] = 
					pK->l7m_dEstFalseNegK;
			pE->l07_adEstScore[L07_EST_K_FALSEPOS] = 
					pK->l7m_dEstFalsePosK;
			pE->l07_adEstScore[L07_EST_K_REL_RET] = 
					pK->l7m_dEstRelRetK;
			pE->l07_adEstScore[L07_EST_K_NONREL_RET] = 
					pK->l7m_dEstNonrelRetK;
			pE->l07_adEstScore[L07_EST_K_REL_MISSED] = 
					pK->l7m_dEstRelMissedK;
			pE->l07_adEstScore[L07_EST_K_POOL_RET] = 
					pK->l7m_dEstPoolRetK;
			pE->l07_adEstScore[L07_EST_K_F32] = pK->l7m_dEstF32K;
			pE->l07_adEstScore[L07_EST_K_F16] = pK->l7m_dEstF16K;
			pE->l07_adEstScore[L07_EST_K_F8] = pK->l7m_dEstF8K;
			pE->l07_adEstScore[L07_EST_K_F4] = pK->l7m_dEstF4K;
			pE->l07_adEstScore[L07_EST_K_F2] = pK->l7m_dEstF2K;
			pE->l07_adEstScore[L07_EST_K_F1] = pK->l7m_dEstF1K;
			pE->l07_adEstScore[L07_EST_K_F0_5] = pK->l7m_dEstF0_5K;
			pE->l07_adEstScore[L07_EST_K_F0_25] = 
						pK->l7m_dEstF0_25K;
			pE->l07_adEstScore[L07_EST_K_F0_125] = 
						pK->l7m_dEstF0_125K;
			pE->l07_adEstScore[L07_EST_K_F0_0625] = 
						pK->l7m_dEstF0_0625K;
			pE->l07_adEstScore[L07_EST_K_F0_03125] = 
						pK->l7m_dEstF0_03125K;
			pE->l07_adEstScore[L07_K_REL_RET] = 
					(double)pK->l7m_nRawRelRetK;
			pE->l07_adEstScore[L07_K_NONREL_RET] = 
					(double)pK->l7m_nRawNonrelRetK;
			pE->l07_adEstScore[L07_K_GRAY_RET] = 
					(double)pK->l7m_nRawGrayRetK;
			pE->l07_adEstScore[L07_K_JG_RET] = 
					(double)pK->l7m_nRawJudgedOrGrayRetK;
			pE->l07_adEstScore[L07_EST_K_FALLOUT] = 
					pK->l7m_dEstFalloutK;
			pE->l07_adEstScore[L07_EPSILON] = pK->l7m_dEpsilon;
			pE->l07_adEstScore[L07_EST_K_FNR] = pK->l7m_dEstFnrK;
			pE->l07_adEstScore[L07_EST_K_FPR] = pK->l7m_dEstFprK;
			pE->l07_adEstScore[L07_EST_K_LAM] = pK->l7m_dEstLamK;
			pE->l07_adEstScore[L07_EST_K_DOR] = pK->l7m_dEstDorK;

			if (bRetroK) {
				/* retrospectively determine what the best K
				 * would have been
				 */
				/* init bestK, F1@K */
				int nBestK = 0;
				double dBestF1K = 0.0;
				/* for each rel rank retrieved */
				for (i = 0; i < nNumRet; i++) {
					bRel = (acRelString[i] == 'R' || 
						acRelString[i] == 'H');
					if (bRel) {
						/* compute F1@rank */
						nK = i + 1;
						vGetMeasuresAtK(acRelString, 
							adProb, nNumRet, nK, 
							dEstR, dEstN,
							nEstOpts, dEpsilon,
							pK);
						/* if better than prev best */
						if (pK->l7m_dEstF1K > 
								dBestF1K) {
							nBestK = nK;
							dBestF1K = 
							  pK->l7m_dEstF1K;
						}
					}
				}
				/* just report to stdout */
				printf("topic %s, best K=%d, F1=%lf\n",
					pE->l07_aszStr[L07_TE8_TOPIC],
					nBestK, dBestF1K);
				nBestKSum += nBestK;
				dBestF1KSum += dBestF1K;
			}

			/* project to depth-R */
			dKvR = nK / (double)nRCeil;
			dEstPrecK = pK->l7m_dEstPrecK;
			dEstRecallK = pK->l7m_dEstRecallK;
			dEstGrayK = pK->l7m_dEstGrayK;
			if (nK < nRCeil) {
				dEstPrecK *= dKvR;
				dEstGrayK *= dKvR;
			} else if (nK > nRCeil) {
				dEstRecallK /= dKvR;
			}
			pE->l07_adEstScore[L07_EST_K_PROJ_R_P] = dEstPrecK;
			pE->l07_adEstScore[L07_EST_K_PROJ_R_R] = dEstRecallK;
			pE->l07_adEstScore[L07_EST_K_PROJ_R_G] = dEstGrayK;

			nKlo = 0;
			nKhi = 5000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_MJ_1_5000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_1_5000] =
					dEstNumJudgedK;

			nKlo = 5000;
			nKhi = 10000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_5001_10000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_5001_10000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_5001_10000] =
					dEstNumJudgedK;

			nKlo = 10000;
			nKhi = 15000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_10001_15000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_10001_15000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_10001_15000] =
					dEstNumJudgedK;

			nKlo = 15000;
			nKhi = 20000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_15001_20000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_15001_20000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_15001_20000] =
					dEstNumJudgedK;

			nKlo = 20000;
			nKhi = 25000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_20001_25000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_20001_25000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_20001_25000] =
					dEstNumJudgedK;

			nKlo = 0;
			nKhi = 25000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_MJ_1_25000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_1_25000] =
					dEstNumJudgedK;

			nKlo = 25000;
			nKhi = 50000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_25001_50000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_25001_50000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_25001_50000] =
					dEstNumJudgedK;

			nKlo = 50000;
			nKhi = 75000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_50001_75000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_50001_75000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_50001_75000] =
					dEstNumJudgedK;

			nKlo = 75000;
			nKhi = 100000;
			vGetMarginalPrec(acRelString, adProb, 
				nNumRet, nKlo, nKhi,
				&nNumJudgedK, &dEstNumJudgedK,
				&dEstMargPrec, nEstOpts);
			pE->l07_adEstScore[L07_EST_MP_75001_100000] =
					dEstMargPrec;
			pE->l07_adEstScore[L07_MJ_75001_100000] =
					(double)nNumJudgedK;
			pE->l07_adEstScore[L07_EST_MJ_75001_100000] =
					dEstNumJudgedK;

		}
		if (nProbD && szPrecBFilename) {
			vGetPRUatK(acRelString, adProb, 
				nNumRet, nB, 
				&dEstPrecB, &dEstRecallB, &dEstGrayB,
				dEstR, dEstN, nEstOpts, dEpsilon);
			pE->l07_adEstScore[L07_EST_PREC_B] = dEstPrecB;
			pE->l07_adEstScore[L07_EST_RECALL_B] = dEstRecallB;
			pE->l07_adEstScore[L07_EST_GRAY_B] = dEstGrayB;
		}

		dMRRSum += dMRR;
		for (i = 0; i < L07_NUM_TE8_INTS; i++) {
			pESum->l07_anScore[i] += pE->l07_anScore[i];
		}
		for (i = 0; i < L07_NUM_TE8_DOUBLES; i++) {
			pESum->l07_adScore[i] += pE->l07_adScore[i];
		}
		if (nProbD) {
		  for (i = 0; i < L07_NUM_EST_DOUBLES; i++) {
			pESum->l07_adEstScore[i] += pE->l07_adEstScore[i];
		  }
		}
		if (dFirstUnjudgedRank < dMinFirstUnjudgedRank) {
			dMinFirstUnjudgedRank = dFirstUnjudgedRank;
			nMinUnjudgedTopic = nQueryID;
		}
		if (dFirstUnjudgedAndNotGrayRank < 
				dMinFirstUnjudgedAndNotGrayRank) {
			dMinFirstUnjudgedAndNotGrayRank = 
					dFirstUnjudgedAndNotGrayRank;
			nMinUnjudgedAndNotGrayTopic = nQueryID;
		}

		fprintf( fpOut2, "Query %ld\n", nQueryID );
		fprintf( fpOut2, " Average Precision: %0.4lf\n", dAvgPrec );
		fprintf( fpOut2, " Mean Reciprocal Rank of First Relevant: "
				"%0.4lf\n", dMRR );

		fprintf( fpOut2, "      " );
		for (j = 1; j <= 50; j++) {
			fprintf( fpOut2, "%d", j % 10 );
		}
		fprintf( fpOut2, "\n" );
		for (i = 0; i < nNumRet; i += 50 ) {
			int iNumCols = 50;
			if ((nNumRet - i) < iNumCols) {
				iNumCols = nNumRet - i;
			}
			fprintf( fpOut2, "%4ld: ", i+1 );
			for (j = 0; j < iNumCols; j++) {
				fprintf( fpOut2, "%c", acRelString[i+j] );
			}
			fprintf( fpOut2, "\n" );
		}
		fprintf( fpOut2, " Highly Relevants Not Found: %ld of %ld\n",
			nNumHighlyRelevantQrels - nHighlyRelevant, 
			nNumHighlyRelevantQrels);
		if (nNumHighlyRelevantQrels != nHighlyRelevant) {
			fprintf( fpOut2, "  " );
			nPos = 2;
			for (i = 0; i < nNumQrels; i++) {
				if (acRelevanceJudgement[i] == 2 && 
						!acFound[i]) {
					printDocno(fpOut2, g_aszDocnos[i], 
							&nPos);
				}
			}
			fprintf( fpOut2, "\n" );
		}
		fprintf( fpOut2, " Other Relevants Not Found: %ld of %ld\n",
			(nNumRelevantQrels - nRelevant) - 
				(nNumHighlyRelevantQrels - nHighlyRelevant),
			nNumRelevantQrels - nNumHighlyRelevantQrels);
		fprintf( fpOut2, "  " );
		nPos = 2;
		for (i = 0; i < nNumQrels; i++) {
			if (acRelevanceJudgement[i] != 0 &&
					acRelevanceJudgement[i] != 2 
					&& !acFound[i]) {
				printDocno(fpOut2, g_aszDocnos[i], &nPos);
			}
		}
		fprintf( fpOut2, "\n\n" );
		if (bEstHTML) {
			fprintf(fpHTML,
				"<HR>\n"
				"<H2>Topic %s</H2>\n"
				, pE->l07_aszStr[L07_TE8_TOPIC]);
		}
		if (bEstHTML) {
			fprintf(fpHTML,
				"<H3>Relevant Documents Not Retrieved "
					"(by Depth %d)</H3>\n"
				"<PRE>\n",
				nM1000);
			/* qsort by nHiRank */
			if (bRunids) {
				for (i = 0; i < nNumQrels; i++ ) {
					anHiRankIndex[i] = i;
				}
				qsort(anHiRankIndex, nNumQrels, sizeof(int), 
						fnCompareHiRanks);
			}
			for (i = 0; i < nNumQrels; i++) {
				if (bRunids) {
					r = anHiRankIndex[i];
				} else {
					r = i;
				}
				if (acRelevanceJudgement[r] > 0 && 
						!acFound[r]) {
					fprintf(fpHTML, 
						"<A HREF=\"http://legacy.library.ucsf.edu/tid/%s\">%s</A>", 
						g_aszDocnos[r], g_aszDocnos[r]);
					if (bRunids) {
						fprintf(fpHTML,
							" (%s-%d wgt=%6.4lf)",
							aszRunids[r],
							g_anHiRanks[r],
							1.0 / adQrelsProb[r]);
					}
					fprintf(fpHTML, "\n");
				}
			}
			fprintf(fpHTML, "</PRE>\n");
			fprintf(fpHTML,
				"<H3>Relevant Documents Retrieved "
					"(by Depth %d)</H3>\n"
				"<PRE>\n",
				nM1000);
			for (i = 0; i < nNumQrels; i++) {
				if (bRunids) {
					r = anHiRankIndex[i];
				} else {
					r = i;
				}
				if (acRelevanceJudgement[r] > 0 && 
						acFound[r]) {
					fprintf(fpHTML, 
						"<A HREF=\"http://legacy.library.ucsf.edu/tid/%s\">%s</A>", 
						g_aszDocnos[r], g_aszDocnos[r]);
					if (bRunids) {
						fprintf(fpHTML,
							" (%s-%d wgt=%6.4lf)",
							aszRunids[r],
							g_anHiRanks[r],
							1.0 / adQrelsProb[r]);
					}
					fprintf(fpHTML, "\n");
				}
			}
			fprintf(fpHTML, "</PRE>\n");
		}
		if (fpOut5) {
			if (bEstHTML) {
				fprintf(fpHTML,	"<PRE>\n");
			}
			for (i = 0; i < L07_NUM_TE8_INTS; i++) {
				fprintf(fpOut5, "%-15s\t%s\t%d\n",
					g_L07_aszTE8IntPrefix[i],
					pE->l07_aszStr[L07_TE8_TOPIC],
					pE->l07_anScore[i]);
			}
			for (i = 0; i < L07_NUM_TE8_DOUBLES; i++) {
				if (i >= L07_BSTART && !szPrecBFilename) {
					continue;
				}
				fprintf(fpOut5, "%-15s\t%s\t%6.4lf\n",
					g_L07_aszTE8MeasurePrefix[i],
					pE->l07_aszStr[L07_TE8_TOPIC],
					pE->l07_adScore[i]);
			}
			if (nProbD) {
				for (i = 0; i < L07_NUM_EST_DOUBLES; i++) {
				    fprintf(fpOut5, "%-15s\t%s\t%6.4lf\n",
					g_L07_aszEstPrefix[i],
					pE->l07_aszStr[L07_TE8_TOPIC],
					pE->l07_adEstScore[i]);
				}
			}
			fprintf(fpOut5, "%-15s\t%s\t", ":relstring:",
				pE->l07_aszStr[L07_TE8_TOPIC]);
			for (i = 0; i < nNumRet; i++) {
				if (i == nDisplayNum) {
					break;
				}
				if (i % 10 == 0 && i > 0) {
					fprintf(fpOut5, " / ");
				}
				fprintf(fpOut5, "%c", acRelString[i]);
			}
			fprintf(fpOut5, "\n");
			if (bEstHTML) {
				fprintf(fpHTML,	"</PRE>\n");
			}
		}
		if (fpOut6 && nNumRetJudgedOrGray > 0) {
			fprintf(fpOut6,
				"Retrieved: %d\n"
				"Relevant retrieved: %d\n"
				"Non-relevant retrieved: %d\n"
				"Unjudged (gray) retrieved: %d\n"
				"Known relevant: %d\n"
				"Precision of judged: %5.3lf "
					"(%d / (%d + %d))  [topic %s]\n"
				"Recall: %5.3lf (%d / %d)  [topic %s]\n"
				"Interactive'07 Score: %3.1lf "
					"(%d - 0.5 * %d)  [topic %s]\n",
				nNumRetJudgedOrGray,
				pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED],
				nJudgedNonRelevant,
				nRetGray,
				pE->l07_anScore[L07_TE8_NUM_RELEVANT],
				pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED] /
				  (double)
				  (pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED] +
				   nJudgedNonRelevant),
				 pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED],
				 pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED],
				 nJudgedNonRelevant,
				 szQueryID,
				pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED] /
				  (double)pE->l07_anScore[L07_TE8_NUM_RELEVANT],
				 pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED],
				 pE->l07_anScore[L07_TE8_NUM_RELEVANT],
				 szQueryID,
				pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED] - 
				  0.5 * nJudgedNonRelevant,
				 pE->l07_anScore[L07_TE8_RELEVANT_RETRIEVED],
				 nJudgedNonRelevant,
				 szQueryID);
		}
		nNumQueries++;
		if (ptrQrels == NULL) break;
	}

	/* average over all queries */
	if (nNumQueries > 0) {
		fprintf( fpOut2, "%ld queries\n", nNumQueries );
		fprintf( fpOut2, " AvgP: Average Precision: %0.4lf\n", 
				dAvgPrecSum / nNumQueries );
		fprintf( fpOut2, " MRR: Mean Reciprocal Rank of First Relevant: "
				"%0.4lf\n", dMRRSum / nNumQueries );
		fprintf( fpOut2, " QRELS info:\n" );
		fprintf( fpOut2, "  Number Relevant per query: %0.2lf "
				"(includes Highly Relevants)\n",
				nNumRelevantQrelsSum / 
					(double)nNumQueries );
		fprintf( fpOut2, "  Number Judged Non-Relevant per query: "
				"%0.2lf\n",
				nNumNonRelevantQrelsSum / 
					(double)nNumQueries );
		if (fpOut5) {
			char *szAll = "all";
			if (bEstHTML) {
				fprintf(fpHTML,	"<PRE>\n");
			}
			fprintf(fpOut5, "%-15s\t%s\t%d\n",
				"num_q", szAll, nNumQueries);
			for (i = 0; i < L07_NUM_TE8_INTS; i++) {
				fprintf(fpOut5, "%-15s\t%s\t%d\n",
					g_L07_aszTE8IntPrefix[i],
					szAll,
					pESum->l07_anScore[i]);
			}
			for (i = 0; i < L07_NUM_TE8_DOUBLES; i++) {
				if (i >= L07_BSTART && !szPrecBFilename) {
					continue;
				}
				fprintf(fpOut5, "%-15s\t%s\t%6.4lf\n",
					g_L07_aszTE8MeasurePrefix[i],
					szAll,
					pESum->l07_adScore[i] / nNumQueries);
				if (i == 0) {
				  double dGMAP = 
					  exp(pESum->l07_adScore[
					    L07_TE8_LOG2] / 
					  nNumQueries);
				  fprintf(fpOut5, "%-15s\t%s\t%6.4lf\n",
					"gm_ap", szAll, dGMAP);
				}
			}
			if (nProbD) {
			    for (i = 0; i < L07_NUM_EST_DOUBLES; i++) {
				fprintf(fpOut5, "%-15s\t%s\t%6.4lf\n",
					g_L07_aszEstPrefix[i],
					szAll,
					pESum->l07_adEstScore[i] /
						nNumQueries);
			    }
			}
			fprintf(fpOut5, "# min judged or gray depth %d "
					"(topic %d)\n",
				(int)(dMinFirstUnjudgedAndNotGrayRank - 0.999),
				nMinUnjudgedAndNotGrayTopic);
			if (bEstHTML) {
				fprintf(fpHTML,	"</PRE>\n");
			}
		}
		if (bRetroK) {
			double dAvgBestK = nBestKSum / (double)nNumQueries;
			double dAvgBestF1K = dBestF1KSum / nNumQueries;
			printf("%d topics: best avg K=%lf, F1=%lf\n",
				nNumQueries, dAvgBestK, dAvgBestF1K);
		}
	}
	if (bEstHTML) {
		fprintf(fpHTML,
			"</BODY>\n"
			"</HTML>\n");
		/* don't fclose fpHTML as it is copy of another one */
	}
	fclose(fpRun);
	fclose(fpQrels);
	fclose(fpOut);
	fclose(fpOut2);
	if (fpOut5) {
		fclose(fpOut5);
		printf("Eval output written to %s\n", szOutFilename5);
	}
	if (fpOutResid) {
		fclose(fpOutResid);
		printf("Residual output written to %s\n", szOutResidFilename);
	}
	if (fpOutResidK) {
		for (i = 0; i < nNumK; i++) {
			fprintf(fpOutResidK, "%s %d\n",
				aszTopicsK[i], anKr[i]);
			if (anKr[i] == 0) {
				printf("Warning: Kr of 0\n");
			}
		}
		fclose(fpOutResidK);
		printf("Residual K output written to %s\n", 
				szOutResidKFilename);
	}
	if (fpOutRelNums) {
		fclose(fpOutRelNums);
	}
	if (adProb) {
		free(adProb);
	}
	if (fpRelSubset) {
		fclose(fpRelSubset);
	}
	if (fpNonSubset) {
		fclose(fpNonSubset);
	}

	return 0;
}

int bStartsWith(char *szLine, char *szPrefix) {
	char *pLine = szLine;
	char *pPrefix = szPrefix;
	while (*pPrefix && *pLine && *pLine == *pPrefix) {
		pLine++;
		pPrefix++;
	}
	return (*pPrefix == '\0');
}

void *pMalloc(int nNumBytes, char *szMsg) {
	void *p = (void *)malloc(nNumBytes);
	if (p == NULL) {
		printf("Error allocating %d bytes: \"%s\"\n",
			nNumBytes, szMsg);
		vExit(-1);
	}
	return p;
}

char *pStrdup(char *p, char *szMsg) {
	int nLen = strlen(p);
	char *pDup = (char *)pMalloc(nLen + 1, szMsg);
	strcpy(pDup, p);
	return pDup;
}

char *pGetLine(char *szLine, int nMaxLineLength, FILE *fp) {
	char *pLine = fgets(szLine, nMaxLineLength, fp);
	if (pLine != NULL) {
		/* remove trailing whitespace */
		int nSrcLen = strlen(szLine);
		int nLastNonWhitespaceIndex = nSrcLen - 1;
		while (nLastNonWhitespaceIndex >= 0 && 
				(szLine[nLastNonWhitespaceIndex] <= ' ')) {
			nLastNonWhitespaceIndex--;
		}
		szLine[nLastNonWhitespaceIndex + 1] = '\0';
	}
	return pLine;
}

int fnCompareDocnos( const void *arg1, const void *arg2 ) {
	return (strcmp(g_aszDocnos[*((int *)arg1)], 
			g_aszDocnos[*((int *)arg2)]));
}

int fnCompareHiRanks( const void *arg1, const void *arg2 ) {
	int nHiRank1 = g_anHiRanks[*((int *)arg1)];
	int nHiRank2 = g_anHiRanks[*((int *)arg2)];
	if (nHiRank1 < nHiRank2) {
		return -1;
	} else if (nHiRank1 > nHiRank2) {
		return 1;
	} else {
		return 0;
	}
}

int nBinSearchForDocno( char *szDocno, int *anIndex, int nSize ) {
	int nLo = -1;
	int nHi = nSize;
	int nMid;
	int nCmp = -1;

	while ((nHi - nLo) > 1) {
		nMid = (nLo + nHi) / 2;
		nCmp = strcmp( g_aszDocnos[anIndex[nMid]], szDocno );
		if (nCmp == 0) {
			break;
		} else if (nCmp < 0) {
			nLo = nMid;
		} else {
			nHi = nMid;
		}
	}

	if (nCmp == 0) {
		return nMid;
	} else {
		return -1;
	}
}

void printDocno( FILE *fpOut2, char *szDocno, int *pnPos ) {
	int nDocnoLen = strlen(szDocno) + 1;
	if ((*pnPos + nDocnoLen) > 72) {
		fprintf( fpOut2, "\n  " );
		*pnPos = 2;
	}
	fprintf( fpOut2, "%s ", szDocno );
	*pnPos += nDocnoLen;
}

/* like atoi, but skip prefix */
/* also, some things won't work on non-integer ids, so stop on those */
int nGetInt(char *szTopic) {
	char *p = szTopic;
	int n;
	if (bStartsWith(szTopic, "10.2452/")) {
		/* heuristic to skip CLEF prefixes */
		p += strlen("10.2452/");
	}
	if (bStartsWith(szTopic, "ACLIA1-")) {
		/* heuristic to skip NTCIR-7 prefixes */
		p += strlen("ACLIA1-");
	}
	while (*p < '0' || *p > '9') {
		p++;
	}
	n = atoi(p);
	while (*p >= '0' && *p <= '9') {
		p++;
	}
	if (*p == '.') {
		/* heuristic that might suffice for QA topics */
		n *= 100;
		n += atoi(p+1);
	}
	return n;
}

void vSumToK(char *acRelString, double *adProb,
	     int nArraySize, int nNumRet,
	     double *pdEstRret, double *pdEstNret, double *pdEstUret,
	     int *pnNumJudged, int nEstOpts, L07SumsAtK *pSums) {
	int i;
	int bRel;
	int nNumRret = 0;
	int nNumNret = 0;
	int nNumUret = 0; /* gray count */
	double dEstRret = 0.0;
	double dEstNret = 0.0;
	double dEstUret = 0.0;
	int nLimRret;
	int nLimNret;
	int nLimUret;

	for (i = 0; i < nArraySize; i++) {
		if (i >= nNumRet) {
			break;
		}
		bRel = (acRelString[i] == 'R' || acRelString[i] == 'H');
		if (bRel) {
			nNumRret++;
			dEstRret += (1.0 / adProb[i]);
		} else if (acRelString[i] == 'N') {
			nNumNret++;
			dEstNret += (1.0 / adProb[i]);
		} else if (acRelString[i] == 'U') {
			nNumUret++; /* gray doc */
			dEstUret += (1.0 / adProb[i]);
		}
	}
	nLimRret = i - nNumNret;
	nLimNret = i - nNumRret;
	nLimUret = i - (nNumNret + nNumRret);
	if (dEstRret > (double)nLimRret && nEstOpts != 1) {
		dEstRret = (double)nLimRret;
	}
	if (dEstNret > (double)nLimNret && nEstOpts != 1) {
		dEstNret = (double)nLimNret; /* fix20080503 */
	}
	if (dEstUret > (double)nLimUret && nEstOpts != 1) {
		dEstUret = (double)nLimUret;
	}
	*pdEstRret = dEstRret;
	*pdEstNret = dEstNret;
	*pdEstUret = dEstUret;
	*pnNumJudged = (nNumRret + nNumNret);
	if (pSums != NULL) {
		pSums->l7s_nRawRelRetK = nNumRret;
		pSums->l7s_nRawNonrelRetK = nNumNret;
		pSums->l7s_nRawGrayRetK = nNumUret;
		pSums->l7s_nRawJudgedOrGrayRetK =
			nNumRret + nNumNret + nNumUret;
	}
}

void vGetPRUatK(char *acRelString, double *adProb, int nNumRet, int nK,
		double *pdEstPrecK, double *pdEstRecallK, double *pdEstGrayK,
		double dEstR, double dEstN, int nEstOpts, double dEpsilon) {
	L07MeasuresAtK sK;
	L07MeasuresAtK *pK = &sK;

	vGetMeasuresAtK(acRelString, adProb, nNumRet, nK,
		dEstR, dEstN, nEstOpts, dEpsilon, pK);
	*pdEstPrecK = pK->l7m_dEstPrecK;
	*pdEstRecallK = pK->l7m_dEstRecallK;
	*pdEstGrayK = pK->l7m_dEstGrayK;
}

/* output measures to pK */
void vGetMeasuresAtK(char *acRelString, double *adProb, int nNumRet, int nK,
		double dEstR, double dEstN, int nEstOpts, double dEpsilon,
		L07MeasuresAtK *pK) {
	double dEstRk; /* rel retrieved at k */
	double dEstNk; /* nonrel retrieved at k */
	double dEstUk; /* gray retrieved at k */
	double dEstMk; /* missed rel at k */
	double dEstRkplusNk;
	double dEstRkplusNkplusUk;
	double dEstNkplusMk;
	double dEstRkplusNkplusMk;
	int nRetK;
	int nNumJudged;
	L07SumsAtK sSums;
	L07SumsAtK *pSums = &sSums;

	/* initialize outputs */
	memset(pK, 0, sizeof(L07MeasuresAtK));

	/* get nRetK */
	nRetK = nK; /* will override with min(k,ret) */
	if (nNumRet < nK) {
		nRetK = nNumRet;
	}

	/* get estimated numbers of rel, nonrel, gray at depth K */
	vSumToK(acRelString, adProb, 
		nNumRet, nK, &dEstRk, &dEstNk, &dEstUk, 
		&nNumJudged, nEstOpts, pSums);
	dEstMk = dEstR - dEstRk;
	if (dEstMk < -0.00005) {
		/* integrity check */
		printf("Error: dEstMk less than zero (%lf)\n", dEstMk);
		vExit(-1);
	} else if (dEstMk < 0.0) {
		/* sometimes slightly less than zero happens, presumably
		 * because rels are summed in different order;
		 * change to zero to prevent unwanted minus signs (-0.0000)
		 */
		dEstMk = 0.0;
	}
	pK->l7m_nRawRelRetK = pSums->l7s_nRawRelRetK;
	pK->l7m_nRawNonrelRetK = pSums->l7s_nRawNonrelRetK;
	pK->l7m_nRawGrayRetK = pSums->l7s_nRawGrayRetK;
	pK->l7m_nRawJudgedOrGrayRetK = pSums->l7s_nRawJudgedOrGrayRetK;

	/* get recall at K */
	pK->l7m_dEstRecallK = dEstRk / dEstR;

	/* get precision at K */
	dEstRkplusNk = dEstRk + dEstNk;
	if (dEstRkplusNk == 0.0) {
		pK->l7m_dEstPrecK = 0.0;
	} else {
		pK->l7m_dEstPrecK = (dEstRk / dEstRkplusNk) *
			(nRetK / (double)nK);
	}

	/* get fallout at K */
	if (dEstN > 0.0) {
		pK->l7m_dEstFalloutK = dEstNk / dEstN;
	} else {
		pK->l7m_dEstFalloutK = 0.0;
	}

	/* get gray percentage at K */
	dEstRkplusNkplusUk = dEstRkplusNk + dEstUk;
	if (dEstRkplusNkplusUk == 0.0) {
		pK->l7m_dEstGrayK = 0.0;
	} else {
		pK->l7m_dEstGrayK = (dEstUk / dEstRkplusNkplusUk) *
			(nRetK / (double)nK);
	}

	/* save rel_ret, nonrel_ret and rel_missed at K */
	/* (these are the 3 inputs to the Jaccard measure) */
	pK->l7m_dEstRelRetK = dEstRk;
	pK->l7m_dEstNonrelRetK = dEstNk;
	pK->l7m_dEstRelMissedK = dEstMk;
	pK->l7m_dEstPoolRetK = dEstRk + dEstNk + dEstUk;

	/* get Jaccard (positive accuracy or overlap) */
	dEstRkplusNkplusMk = dEstRkplusNk + dEstMk;
	if (dEstRkplusNkplusMk == 0.0) {
		pK->l7m_dEstJaccardK = 0.0;
	} else {
		pK->l7m_dEstJaccardK = dEstRk / dEstRkplusNkplusMk;
	}

	/* partition the errors into false negatives and false positives */
	/* (adds to 100% except when there are no errors) */
	dEstNkplusMk = dEstNk + dEstMk;
	if (dEstNkplusMk == 0.0) {
		pK->l7m_dEstFalseNegK = 0.0;
		pK->l7m_dEstFalsePosK = 0.0;
	} else {
		pK->l7m_dEstFalseNegK = dEstMk / dEstNkplusMk;
		pK->l7m_dEstFalsePosK = dEstNk / dEstNkplusMk;
	}

	/* epsilon for hm% (fnr), sm% (fpr), lam%, DOR */
	pK->l7m_dEpsilon = dEpsilon;

	/* fnr = false negative rate (hm% ~= 1 - recall) */
	/* include epsilon so lam inputs are not 0 or 1 */
	/* also covers numerical issue of dEstRk slightly exceeding dEstR */
	pK->l7m_dEstFnrK = (dEpsilon + dEstR - dEstRk) /
		(2.0*dEpsilon + dEstR);
	
	/* fpr = false positive rate (sm% ~= fallout)*/
	/* include epsilon so lam inputs are not 0 or 1 */
	pK->l7m_dEstFprK = (dEpsilon + dEstNk) / (2.0*dEpsilon + dEstN);

	/* lam = logistic average misclassification percentage */
	pK->l7m_dEstLamK = dLogitAverage(pK->l7m_dEstFnrK, pK->l7m_dEstFprK);

	/* DOR = diagnostic odds ratio (same ranking as lam on each topic?) */
	pK->l7m_dEstDorK = 
		((dEpsilon + dEstRk) * (dEpsilon + dEstN - dEstNk)) /
		((dEpsilon + dEstNk) * (dEpsilon + dEstR - dEstRk));

	/* get F-measures */
	pK->l7m_dEstF32K = dGetFMeasure(32.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF16K = dGetFMeasure(16.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF8K = dGetFMeasure(8.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF4K = dGetFMeasure(4.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF2K = dGetFMeasure(2.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF1K = dGetFMeasure(1.0, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF0_5K = dGetFMeasure(0.5, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF0_25K = dGetFMeasure(0.25, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF0_125K = dGetFMeasure(0.125, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF0_0625K = dGetFMeasure(0.0625, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
	pK->l7m_dEstF0_03125K = dGetFMeasure(0.03125, 
			pK->l7m_dEstPrecK, pK->l7m_dEstRecallK);
}

double dGetFMeasure(double dBeta, double dPrecK, double dRecallK) {
	double dF;
	double dBetaSquared = dBeta * dBeta;
	double dDenom = dBetaSquared * dPrecK + dRecallK;

	if (dDenom == 0.0) {
		dF = 0.0;
	} else {
		dF = (1.0 + dBetaSquared) * dPrecK * dRecallK / dDenom;
	}
	return dF;
}

double dLogit(double dX) {
	double dRatio;
	double dLogitX;
	if (dX <= 0.0 || dX >= 1.0) {
		printf("Error: illegal logit input %lf\n", dX);
		vExit(-1);
	}
	dRatio = dX / (1.0 - dX);
	dLogitX = log(dRatio);
	return dLogitX;
}

double dLogitInverse(double dX) {
	double dInv;
	dInv = 1.0 / (1.0 + exp(-dX));
	return dInv;
}

double dLogitAverage(double dX, double dY) {
	int nNumValues = 2;
	double dSum = 0.0;
	double dAvgLogit;
	double dAvg;
	dSum += dLogit(dX);
	dSum += dLogit(dY);
	dAvgLogit = dSum / nNumValues;
	dAvg = dLogitInverse(dAvgLogit);
	return dAvg;
}

void vGetMarginalPrec(char *acRelString, double *adProb, int nNumRet, 
		int nKlo, int nKhi,
		int *pnNumJudged, double *pdEstNumJudged,
		double *pdEstMargPrec, int nEstOpts) {
	double dEstRkLo;
	double dEstNkLo;
	double dEstUkLo;
	double dEstRkHi;
	double dEstNkHi;
	double dEstUkHi;
	int nRetKlo;
	int nRetKhi;
	int nNumJudgedLo;
	int nNumJudgedHi;
	double dEstMargR;
	double dEstMargN;
	double dEstMargRplusN;

	nRetKlo = nKlo; /* will override with min(k,ret) */
	if (nNumRet < nKlo) {
		nRetKlo = nNumRet;
	}
	vSumToK(acRelString, adProb, 
		nNumRet, nKlo, &dEstRkLo, &dEstNkLo, &dEstUkLo,
		&nNumJudgedLo, nEstOpts, NULL);

	nRetKhi = nKhi; /* will override with min(k,ret) */
	if (nNumRet < nKhi) {
		nRetKhi = nNumRet;
	}
	vSumToK(acRelString, adProb, 
		nNumRet, nKhi, &dEstRkHi, &dEstNkHi, &dEstUkHi,
		&nNumJudgedHi, nEstOpts, NULL);

	dEstMargR = dEstRkHi - dEstRkLo;
	dEstMargN = dEstNkHi - dEstNkLo;
	dEstMargRplusN = dEstMargR + dEstMargN;

	if (dEstMargRplusN == 0.0) {
		*pdEstMargPrec = 0.0;
	} else {
		*pdEstMargPrec = (dEstMargR / dEstMargRplusN) *
			((nRetKhi - nRetKlo) / (double)(nKhi - nKlo));
	}
	*pnNumJudged = nNumJudgedHi - nNumJudgedLo;
	*pdEstNumJudged = dEstMargRplusN;
}

/* end of l07_eval.c */
