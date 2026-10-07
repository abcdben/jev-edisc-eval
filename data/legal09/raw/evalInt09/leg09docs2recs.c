/*
 * leg09docs2recs.c (convert Int09 docid runs into recordid runs)
 *                 (needs the input docs to be sorted)
 *
 * Revision History:
 *  2010-05-24 - st - released as version 1.0
 *  2010-04-30 - st - created
 *
 * Author list:
 *  st - Stephen Tomlinson
 */

/*
 * This is free software.  If you modify the source, 
 * please update the last modified date and last author code in
 * LEG09DOCS2RECS_VERSION below.
 */
#define LEG09DOCS2RECS_VERSION "v1.0 (2010-05-24 st)"

/*
 * Input: Int09 document-based run
 * Output: message-based run
 * (TODO: list inputs and outputs in more detail)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int bStartsWith(char *szLine, char *szPrefix);
void *pMalloc(int nNumBytes, char *szMsg);
char *pStrdup(char *p, char *szMsg);
char *pGetLine(char *szLine, int nMaxLineLength, FILE *fp);

/* good place for a breakpoint when debugging */
void vExit(int v) {
	printf("Exiting (%d)\n", v);
	exit(v);
}

int main(int argc, char *argv[]) {
	int nMaxLineLength = 2048;
	int i;
	char *szLine = NULL;
	char *szTopic = NULL;
	char *szQ0 = NULL;
	char *szDocid = NULL;
	char *szRank = NULL;
	char *szRSV = NULL;
	char *szRun = NULL;
	FILE *fpIn = NULL;
	FILE *fpOut = NULL;
	char *pLine;
	size_t nNumItems;
	char *szPrevRec = NULL;
	char *szInRunname = NULL;
	char *szInDir = NULL;
	char *szOutDir = NULL;
	char *szInFilename = NULL;
	char *szOutFilename = NULL;
	char *szRec = NULL;
	int cmp;
	int nNumDocids = 0;
	int nNumRecs = 0;
	int nNumDel = 0;
	char *p = NULL;

	/* display version information */
	printf("leg09docs2recs version: \"%s\"\n", LEG09DOCS2RECS_VERSION);
#ifdef __DATE__
#ifdef __TIME__
	printf(" compiled %s %s\n", __DATE__, __TIME__);
#endif
#endif
	printf("\n");

	/* display usage if wrong number of arguments specified */
	if (argc < 2) {
		printf("Usage: %s\n"
			" in=inputRunname\n"
			" indir=inputDir\\\n"
			" outdir=outputDir\\\n"
			"Note: outputname will be same as inputname\n"
			"\n"
		, argv[0]);
		vExit(-1);
	}

	/* get arguments */
	for (i = 1; i < argc; i++) {
		if (bStartsWith(argv[i], "in=")) {
			szInRunname = argv[i] + 3;
		} else if (bStartsWith(argv[i], "indir=")) {
			szInDir = argv[i] + 6;
		} else if (bStartsWith(argv[i], "outdir=")) {
			szOutDir = argv[i] + 7;
		} else {
			printf("Error: unrecognized argument \"%s\"\n",
				argv[i]);
			vExit(-1);
		}
	}

	if (!szInRunname) {
		printf("Error: need input runname\n");
		vExit(-1);
	}
	if (!szInDir) {
		printf("Error: need input dir\n");
		vExit(-1);
	}
	if (!szOutDir) {
		printf("Error: need output dir\n");
		vExit(-1);
	}

	/* display arguments */
	printf("szInRunname \"%s\"\n", szInRunname);

	/* allocate line and filename holders */
	szLine = (char *)pMalloc(nMaxLineLength, "szLine");
	szTopic = (char *)pMalloc(nMaxLineLength, "szTopic");
	szQ0 = (char *)pMalloc(nMaxLineLength, "szQ0");
	szDocid = (char *)pMalloc(nMaxLineLength, "szDocid");
	szRank = (char *)pMalloc(nMaxLineLength, "szRank");
	szRSV = (char *)pMalloc(nMaxLineLength, "szRSV");
	szRun = (char *)pMalloc(nMaxLineLength, "szRun");
	szPrevRec = (char *)pMalloc(nMaxLineLength, "szPrevRec");
	szInFilename = (char *)pMalloc(nMaxLineLength, "szInFilename");
	szOutFilename = (char *)pMalloc(nMaxLineLength, "szOutFilename");
	szRec = (char *)pMalloc(nMaxLineLength, "szRec");
	strcpy(szPrevRec, "");

	/* open input file */
	sprintf(szInFilename, "%s%s", szInDir, szInRunname);
	printf("Opening %s\n", szInFilename);
	fpIn = fopen(szInFilename, "r");
	if (fpIn == NULL) {
		printf("Error: can't open input file \"%s\"\n",
				szInFilename);
		vExit(-1);
	}

	/* open output file */
	sprintf(szOutFilename, "%s%s",
		szOutDir, szInRunname);
	printf("Open %s for output\n", szOutFilename);
	fpOut = fopen(szOutFilename, "w");
	if (fpOut == NULL) {
		printf("Error: can't open output file \"%s\"\n",
				szOutFilename);
		vExit(-1);
	}

	/* for each topic in the input list file */
	for (;;) {
		/* get topic information from list file */
		/* 201	Q0	0.7.47.100781.1	0	0	runname */
		pLine = pGetLine(szLine, nMaxLineLength, fpIn);
		if (pLine == NULL) break; /* EOF */
		if (strcmp(szLine, "") == 0) continue; /* skip blank lines */
		if (szLine[0] == '#') continue; /* skip comments */
		nNumItems = sscanf(szLine, "%s %s %s %s %s %s", 
			szTopic, szQ0, szDocid, szRank, szRSV, szRun);
		if (nNumItems != 6) {
			printf("Error: input line format incorrect\n");
			printf("\"%s\"\n", szLine);
			vExit(-1);
		}
		nNumDocids++;
		/* convert docid to recordid */
		strcpy(szRec, szDocid);
		p = szRec;
		for (i = 0; i < 3; i++) {
			p = strstr(p, ".");
			if (p == NULL) {
				printf("Error: need at least 3 dots "
					"in id \"%s\"\n", szDocid);
				vExit(-1);
			}
			p++;
		}
		p = strstr(p, ".");
		if (p != NULL) {
			*p = '\0';
			p++;
			p = strstr(p, ".");
			if (p != NULL) {
				printf("Error: need at most 4 dots "
					"in id \"%s\"\n", szDocid);
				vExit(-1);
			}
		}
		/* check if duplicate of previous record */
		cmp = strcmp(szPrevRec, szRec);
		if (cmp < 0) {
			strcpy(szPrevRec, szRec);
			fprintf(fpOut, "%s\t%s\t%s\t%s\t%s\t%s\n",
				szTopic, "Q0", szRec, szRank, szRSV, szRun);
			nNumRecs++;
		} else if (cmp > 0) {
			printf("Error: docids out of order: \"%s\" \"%s\"\n",
				szPrevRec, szRec);
			vExit(-1);
		} else {
			nNumDel++;
		}
	}
	fclose(fpIn);
	fpIn = NULL;

	if (fpOut != NULL) {
		fclose(fpOut);
		fpOut = NULL;
	}
	if ((nNumDel + nNumRecs) != nNumDocids) {
		printf("Error: doesn't add up (%d docids, %d recs, %d del).",
			nNumDocids, nNumRecs, nNumDel);
		vExit(-1);
	}

	printf("Successful exit (%d docids, %d recs, %d del).",
		nNumDocids, nNumRecs, nNumDel);
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

/* end of leg09docs2recs.c */
