/*
 * l07_sort.c (Sort Program for TREC 2007 Legal Track)
 *
 * Revision History:
 *  2008-10-05 - st - released as version 2.1
 *  2008-08-10 - st - increase nMaxLines to 20 million
 *  2008-08-09 - st - add some sort time optimizations
 *  2008-08-09 - st - add kExtract option
 *  2008-08-09 - st - add spaceParam, increase default to 250MB
 *  2008-05-19 - st - released as version 2.0 (for consistency with l07_eval)
 *  2008-05-17 - st - renamed sortlines.c as l07_sort.c for public release
 *  2007-08-04 - st - L07 check on if run files in order
 *  2007-04-28 - st - add docid order as tie-breaker, for ref Boolean run
 *  2006-04-30 - st - support lists of files
 *  2006-02-21 - st - use rank to break ties
 *  2006-01-06 - st - started for SIGIR'06, just do minimum needed for paper
 *
 * Author list:
 *  st - Stephen Tomlinson
 */

/*
 * This is free software.  If you modify the source, 
 * please update the last modified date and last author code in
 * L07_SORT_VERSION below.
 */
#define L07_SORT_VERSION "v2.1 (2008-10-05 st)"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h> /* isspace */

#define MAX_LINE_LENGTH	1024

int g_bScoreTies;
int g_bRankTies;
int g_bDocidTies;
int g_bTrecEvalOrdering;
int g_bJustCheckInput;
int g_nSpaceParam;
int g_bKExtract;
int g_bScoresBackwards;

char *pGetLine( char *szLine, int nMaxLineLength, FILE *fp, int bEOFOkay );
static int fnCompLines( const void *arg1, const void *arg2 );
void vProcessFile(char *szInFilename, char *szInputDir, char *szOutputDir,
		  char *pSpace);
int bBlankLine(char *szLine);
double dGetRsv(char *sz0);

int main(int argc, char *argv[]) {
	int nNumFiles = 0;
	char szLine[MAX_LINE_LENGTH];
	char *ptr;
	int i;
	char *szListFilename = NULL;
	char *szOutputDir = NULL;
	char *szInputDir = NULL;
	char *pSpace = NULL;
	FILE *fpList = NULL;

	printf("l07_sort %s\n", L07_SORT_VERSION);
	g_nSpaceParam = 250000000; /* default */
	if (argc < 4) {
		printf( "Usage: \n"
			"in=ListFilename (list input files one per line)\n"
			"inDir=inputDirectory (include trailing slash)\n"
			"outDir=outputDirectory (overwrites old files)\n"
			"trecevalOrder\n"
			"justCheckInput\n"
			"spaceParam=%d (bytes of RAM to use)\n"
			"kExtract (moves K and Kh values to separate files)\n"
			"\n"
			"Example: l07_sort in=list.txt inDir=c:\\orig\\ "
				"outDir=c:\\sorted\\ trecevalOrder\n",
			g_nSpaceParam
			);
		exit(-1);
	}
	g_bTrecEvalOrdering = 0;
	g_bJustCheckInput = 0;
	g_bKExtract = 0;
	for (i = 1; i < argc; i++) {
		if (strncmp(argv[i], "in=", 3) == 0) {
			szListFilename = argv[i] + 3;
		} else if (strncmp(argv[i], "outDir=", 7) == 0) {
			szOutputDir = argv[i] + 7;
		} else if (strncmp(argv[i], "inDir=", 6) == 0) {
			szInputDir = argv[i] + 6;
		} else if (strcmp(argv[i], "trecevalOrder") == 0) {
			g_bTrecEvalOrdering = 1;
			printf("Using trec_eval ordering\n");
		} else if (strcmp(argv[i], "justCheckInput") == 0) {
			g_bJustCheckInput = 1;
			printf("Just check input ordering, skip sorts\n");
		} else if (strncmp(argv[i], "spaceParam=", 11) == 0) {
			g_nSpaceParam = atoi(argv[i] + 11);
		} else if (strcmp(argv[i], "kExtract") == 0) {
			g_bKExtract = 1;
			printf("Extracting K and Kh values to "
				".K and .Kh files\n");
		} else {
			printf( "Unrecognized option: \"%s\"\n",
				argv[i] );
			exit(-1);
		}
	}

	fpList = fopen(szListFilename, "r");
	if (fpList == NULL) {
		printf("Error: can't open list file \"%s\"\n",
			szListFilename);
		exit(-1);
	}

	printf("Allocating %d bytes of RAM (spaceParam)\n",
		g_nSpaceParam);
	pSpace = malloc(g_nSpaceParam);
	if (pSpace == NULL) {
		printf("Error: can't allocate %d bytes\n", g_nSpaceParam);
		exit(-1);
	}

	for (;;) {
		ptr = pGetLine(szLine, MAX_LINE_LENGTH, fpList, 1);
		if (ptr == NULL) {
			break;
		}
		printf("Processing file %d (%s)\n", nNumFiles+1, szLine);
		vProcessFile(szLine, szInputDir, szOutputDir, pSpace);
		nNumFiles++;
	}

	free(pSpace);
	fclose(fpList);
	printf("Processed %d files.\n", nNumFiles);
	return 0;
}

void vProcessFile(char *szInFilename, char *szInputDir, char *szOutputDir,
		  char *pSpace) {
	int nMaxLines =  20123456;
	int nMaxSpace = g_nSpaceParam;
	char *p = pSpace;
	int nSpaceUsed = 0;
	char *ptr;
	int nLen;
	int nNumLines = 0;
	char **aszPtrs = (char **)malloc(nMaxLines * sizeof(char *));
	int i;
	FILE *fpIn = NULL;
	FILE *fpOut = NULL;
	int nNumTies = 0;
	int nNumWrong = 0;
	int nNumOK = 0;
	int nCmp;
	char szLine[MAX_LINE_LENGTH];
	char szKFilename[MAX_LINE_LENGTH];
	int bFoundK = 0;
	int bReportedScoresBackwards = 0;

	sprintf(szLine, "%s%s", szInputDir, szInFilename);
	printf(" Opening \"%s\" for reading\n", szLine);
	fpIn = fopen(szLine, "r");
	if (fpIn == NULL) {
		printf("Error: can't open file \"%s\"\n", szLine);
		exit(-1);
	}

	for (;;) {
		ptr = pGetLine(szLine, MAX_LINE_LENGTH, fpIn, 1);
		if (ptr == NULL) {
			break;
		}
		if (g_bKExtract && bBlankLine(szLine)) {
			bFoundK = 1;
			break;
		}
		if (nNumLines >= nMaxLines) {
			printf("Recompile with more lines\n");
			exit(-1);
		}
		nLen = strlen(szLine);
		strcpy(p, szLine);
		aszPtrs[nNumLines] = p;
		p += (nLen + 1);
		nSpaceUsed += (nLen + 1);
		if (nSpaceUsed > (nMaxSpace - MAX_LINE_LENGTH)) {
			printf("Rerun with higher spaceParam setting\n");
			exit(-1);
		}
		nNumLines++;
	}
	
	printf(" %d lines read (%d chars saved)\n", nNumLines, nSpaceUsed);

	if (g_bKExtract && !bFoundK) {
		printf("Error: K/Kh values not found\n");
		exit(-1);
	}
	if (g_bKExtract) {
		int nNumItems;
		int nPrevTopicID = -1;
		int nTopicID;
		double dKSum = 0.0;
		double dK;
		int nNumKLines = 0;
		int nNumKLinesPrev;
		/* write .K file */
		sprintf(szKFilename, "%s%s.K", szOutputDir, szInFilename);
		if (!g_bJustCheckInput) {
			fpOut = fopen(szKFilename, "w");
			if (fpOut == NULL) {
				printf("Error: can't open \"%s\"\n", szKFilename);
				exit(-1);
			}
		}
		for (;;) {
			ptr = pGetLine(szLine, MAX_LINE_LENGTH, fpIn, 1);
			if (ptr == NULL) {
				break;
			}
			if (bBlankLine(szLine)) {
				continue;
			}
			nNumItems = sscanf(szLine, "%d %lf", &nTopicID, &dK);
			if (nNumItems != 2) {
				printf("Error: invalid K/Kh line\n");
				exit(-1);
			}
			if (nTopicID < nPrevTopicID) {
				break;
			}
			nPrevTopicID = nTopicID;
			if (!g_bJustCheckInput) {
				fprintf(fpOut, "%s\n", szLine);
			}
			dKSum += dK;
			nNumKLines++;
		}
		if (!g_bJustCheckInput) {
			fclose(fpOut);
		}
		if (nNumKLines == 0) {
			printf("Error: K lines empty\n");
			exit(-1);
		}
		printf("   Avg K=%lf (%d topics)\n", 
			dKSum / nNumKLines, nNumKLines);
		nNumKLinesPrev = nNumKLines;
		/* write .Kh file */
		sprintf(szKFilename, "%s%s.Kh", szOutputDir, szInFilename);
		if (!g_bJustCheckInput) {
			fpOut = fopen(szKFilename, "w");
			if (fpOut == NULL) {
				printf("Error: can't open \"%s\"\n", szKFilename);
				exit(-1);
			}
			/* write 1st Kh line read above */
			fprintf(fpOut, "%s\n", szLine);
		}
		nPrevTopicID = nTopicID;
		dKSum = dK;
		nNumKLines = 1;
		/* write rest of Kh lines */
		for (;;) {
			ptr = pGetLine(szLine, MAX_LINE_LENGTH, fpIn, 1);
			if (ptr == NULL) {
				break;
			}
			if (bBlankLine(szLine)) {
				continue;
			}
			nNumItems = sscanf(szLine, "%d %lf", &nTopicID, &dK);
			if (nNumItems != 2) {
				printf("Error: invalid K/Kh line\n");
				exit(-1);
			}
			if (nTopicID < nPrevTopicID) {
				printf("Error: desc topic id in Kh section\n");
				exit(-1);
			}
			nPrevTopicID = nTopicID;
			if (!g_bJustCheckInput) {
				fprintf(fpOut, "%s\n", szLine);
			}
			dKSum += dK;
			nNumKLines++;
		}
		if (!g_bJustCheckInput) {
			fclose(fpOut);
		}
		printf("   Avg Kh=%lf (%d topics)\n", 
			dKSum / nNumKLines, nNumKLines);
	}
	if (!g_bJustCheckInput) {
		fclose(fpIn);
	}

	/* first pass: check if any rows out of order */
	g_bScoresBackwards = 0;
	for (i = 1; i < nNumLines; i++) {
		nCmp = fnCompLines(&(aszPtrs[i-1]), &(aszPtrs[i]));
		if (nCmp == -1) {
			nNumOK++;
		} else if (nCmp == 0) {
			if (nNumTies == 0) {
				printf("ERROR: Lines %d and %d are tied:\n",
					i, i+1);
				printf("\"%s\"\n\"%s\"\n",
					aszPtrs[i-1], aszPtrs[i]);
			}
			nNumTies++;
		} else {
			if (g_bScoresBackwards && !bReportedScoresBackwards ||
					nNumWrong == 0) {
				printf("Lines %d and %d out of order:\n",
					i, i+1);
				printf("\"%s\"\n\"%s\"\n",
					aszPtrs[i-1], aszPtrs[i]);
				if (g_bScoresBackwards && 
						!bReportedScoresBackwards) {
					printf(" more than just docids "
						"out of order\n");
					bReportedScoresBackwards = 1;
				}
			}
			nNumWrong++;
		}
	}
	printf(" %d out of order, %d ties\n", 
			nNumWrong, nNumTies);

	if (g_bJustCheckInput) {
		printf(" Skipping sort and output\n");
		goto EndOutput;
	} else if (nNumWrong && !g_bScoresBackwards) {
		/* just sort ranges where docids backwards (perf opt) */
		int iRsvPrev = 0;
		int nMaxNumSortLines = 0;
		int nNumSortLines;
		double dRsv;
		double dRsvPrev;
		printf(" optimization: just sort ranges of tied rsv\n");
		dRsvPrev = dGetRsv(aszPtrs[0]);
		for (i = 1; i <= nNumLines; i++) {
			/* get rsv of line */
			if (i < nNumLines) { 
				dRsv = dGetRsv(aszPtrs[i]);
				/* if rsv same as prev, continue */
				if (dRsv == dRsvPrev) {
					continue;
				}
			}
			nNumSortLines = i - iRsvPrev;
			if (nNumSortLines > 1) {
				if (nNumSortLines > nMaxNumSortLines) {
					nMaxNumSortLines = nNumSortLines;
					printf(" Sorting %d lines "
						"(of %d so far)\n",
						nNumSortLines, i+1);
				}
				qsort(aszPtrs + iRsvPrev, nNumSortLines, 
						sizeof(char *), fnCompLines);
			}
			iRsvPrev = i;
			dRsvPrev = dRsv;
		}
	} else if (nNumWrong) {
		printf(" Sorting %d lines.\n", nNumLines);
		g_bScoreTies = 0;
		g_bRankTies = 0;
		g_bDocidTies = 0;
		qsort(aszPtrs, nNumLines, sizeof(char *), fnCompLines);
		printf(" Done sorting.\n");
		if (g_bScoreTies) {
			printf(" There were ties in the rsv scores.\n");
		}
		if (g_bRankTies) {
			printf(" WARNING: rank ties means sort non-deterministic\n");
		}
		if (g_bDocidTies) {
			printf(" ERROR: docid ties means input invalid\n");
		}
	} else {
		printf(" Skipping sort.\n");
	}

	/* verify sorting worked */
	if (nNumWrong > 0) {
		printf(" Verifying sort order\n");
		nNumWrong = 0;
		nNumOK = 0;
		nNumTies = 0;
		g_bScoresBackwards = 0;
		for (i = 1; i < nNumLines; i++) {
			nCmp = fnCompLines(&(aszPtrs[i-1]), &(aszPtrs[i]));
			if (nCmp == -1) {
				nNumOK++;
			} else if (nCmp == 0) {
				if (nNumTies == 0) {
					printf("ERROR: Lines %d and %d are tied:\n",
					i, i+1);
					printf("\"%s\"\n\"%s\"\n",
						aszPtrs[i-1], aszPtrs[i]);
				}
				nNumTies++;
			} else {
				if (g_bScoresBackwards && !bReportedScoresBackwards ||
						nNumWrong == 0) {
					printf("Lines %d and %d out of order:\n",
						i, i+1);
					printf("\"%s\"\n\"%s\"\n",
						aszPtrs[i-1], aszPtrs[i]);
					if (g_bScoresBackwards && 
							!bReportedScoresBackwards) {
						printf(" more than just docids "
							"out of order\n");
						bReportedScoresBackwards = 1;
					}
				}
				nNumWrong++;
			}
		}
		if (nNumWrong > 0) {
			printf("ERROR: still out of order, "
				"implementation error\n");
			exit(-1);
		}
	}

	sprintf(szLine, "%s%s", szOutputDir, szInFilename);
	printf(" Writing to %s\n", szLine);
	fpOut = fopen(szLine, "w");
	if (fpOut == NULL) {
		printf("Error: can't open \"%s\"\n", szLine);
		exit(-1);
	}
	for (i = 0; i < nNumLines; i++) {
		fprintf(fpOut, "%s\n", aszPtrs[i]);
	}
	fclose(fpOut);

EndOutput:
	free(aszPtrs);

	printf(" Processed %s successfully (%d lines)\n", 
		szInFilename, nNumLines);
}

int bBlankLine(char *szLine) {
	char *p = szLine;
	while (*p) {
		if (*p >= ' ') {
			return 0;
		}
		p++;
	}
	return 1;
}

double dGetRsv(char *sz0) {
	int nNumItems;
	int nTopicNum0;
	char szDummy1[MAX_LINE_LENGTH];
	char szDocid0[MAX_LINE_LENGTH];
	double dScore0;
	int nRank0;
	char szDummy5[MAX_LINE_LENGTH];
	/* 301	Q0	FBIS3-98	386	  0.1632	smart11_base */
	nNumItems = sscanf(sz0, "%d %s %s %d %lf %s",
		&nTopicNum0, szDummy1, szDocid0, &nRank0, &dScore0, szDummy5);
	if (nNumItems != 6) {
		printf("ErrorR: just %d items on line \"%s\"\n",
			nNumItems, sz0);
		exit(-1);
	}
	return dScore0;
}

static int fnCompLines(const void *arg0, const void *arg1) {
	char *sz0 = *(char **)arg0;
	char *sz1 = *(char **)arg1;
	int nNumItems;
	int nTopicNum0;
	int nTopicNum1;
	char szDummy1[MAX_LINE_LENGTH];
	char szDocid0[MAX_LINE_LENGTH];
	char szDocid1[MAX_LINE_LENGTH];
	double dScore0;
	double dScore1;
	int nRank0;
	int nRank1;
	char szDummy5[MAX_LINE_LENGTH];

	/* slight perf optimization, avoid sscanf when different topic */
	nTopicNum0 = atoi(sz0);
	nTopicNum1 = atoi(sz1);
	if (nTopicNum0 < nTopicNum1) {
		return -1;
	} else if (nTopicNum0 > nTopicNum1) {
		g_bScoresBackwards = 1;
		return 1;
	}

	/* 301	Q0	FBIS3-98	386	  0.1632	smart11_base */
	nNumItems = sscanf(sz0, "%d %s %s %d %lf %s",
		&nTopicNum0, szDummy1, szDocid0, &nRank0, &dScore0, szDummy5);
	if (nNumItems != 6) {
		printf("Error: just %d items on line \"%s\"\n",
			nNumItems, sz0);
		exit(-1);
	}
	nNumItems = sscanf(sz1, "%d %s %s %d %lf %s",
		&nTopicNum1, szDummy1, szDocid1, &nRank1, &dScore1, szDummy5);
	if (nNumItems != 6) {
		printf("Error: just %d items on line \"%s\"\n",
			nNumItems, sz1);
		exit(-1);
	}
	if (nTopicNum0 < nTopicNum1) {
		return -1;
	} else if (nTopicNum0 > nTopicNum1) {
		g_bScoresBackwards = 1;
		return 1;
	} else if (dScore0 > dScore1) {
		return -1;
	} else if (dScore0 < dScore1) {
		g_bScoresBackwards = 1;
		return 1;
	} else if (g_bTrecEvalOrdering) {
		/* descending docid */
		int nCmp;
		g_bScoreTies = 1;
		nCmp = strcmp(szDocid0, szDocid1);
		if (nCmp == 0) {
			g_bDocidTies = 1;
		} else if (nCmp < 0) {
			nCmp = 1;
		} else if (nCmp > 0) {
			nCmp = -1;
		}
		return nCmp;
	} else {
		g_bScoreTies = 1;
		if (nRank0 < nRank1) {
			return -1;
		} else if (nRank0 > nRank1) {
			return 1;
		} else {
			/* ascending docid */
			int nCmp;
			g_bRankTies = 1;
			nCmp = strcmp(szDocid0, szDocid1);
			if (nCmp == 0) {
				g_bDocidTies = 1;
			} else if (nCmp < 0) {
				nCmp = -1;
			} else if (nCmp > 0) {
				nCmp = 1;
			}
			return nCmp;
		}
	}
}

/*
 * Get line, remove trailing whitespace first.
 */
char *pGetLine( char *szLine, int nMaxLineLength, FILE *fp, int bEOFOkay ) {
	char *ptr = fgets( szLine, nMaxLineLength, fp );
	if ( ptr != NULL ) {
		int nSrcLen = strlen( szLine );
		int nLastNonWhitespaceIndex = nSrcLen - 1;
		while ( nLastNonWhitespaceIndex >= 0 && 
				isspace(szLine[nLastNonWhitespaceIndex]) ) {
			nLastNonWhitespaceIndex--;
		}
		szLine[ nLastNonWhitespaceIndex + 1 ] = '\0';
	}
	if ( !bEOFOkay && ptr == NULL ) {
		printf( "Error: Unexpected EOF\n" );
		exit(-1);
	}
	return ptr;
}

/* end of l07_sort.c */
