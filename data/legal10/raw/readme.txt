TREC 2010 Legal Track Learning Task Results and Toolkit

Relevance assessments:
  -- the file qrels.t10legallearn.gz contains the relevance assessments

Toolkit:
  -- download the files:
       dolegal10
       calc1.c
       calc2.c

  -- uncompress the qrels file:
       gunzip qrels.t10legallearn.gz

  -- on a *nix system, type:

       ./dolegal10 qrels.t10legallearn RUNNAME

     where qrels.t10legallearn is the uncompressed version of the relevance assessments
     and RUNNAME is a learning task run, in the format given in the guidelines

  -- the result will be a RUNNAME.sum and RUNNAME.table files

  -- You may use Linux or MacOS or Cygwin on Windows to run the toolkit.  It has
     been tested on Fedora and Ubuntu Linux.
