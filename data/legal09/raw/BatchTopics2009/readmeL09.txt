TREC 2009 Legal Track: Batch Task Evaluation Topics

Revision History
- 2009-June-15 (st) - updated based on last year's readme files 

Contents:
 File List
 Relevance Judgments: Sources
 Relevance Judgments: Syntax
 Number of Relevance Judgments By Topic
 Boolean Strings Syntax
 Topic File Structure
 .K, .Kh and .append files
 Further Information
 
File list for BatchTopics2009.zip:
 readmeL09.txt   (this file)
 fullL09.xml     (official topic file for participants)
 shortL09.xml    (topic file excluding background complaint fields)
 qrelsL09.pass1  (relevance judgments from past use of the topics)
 qrelsL09.pass1_probs  (qrels with probability column for use with l07_eval)
 refL09B.K       (K values for reference Boolean run)
 refL09B.Kh      (Kh values for reference Boolean run)
 refL09B.eval    (l07_eval output for reference Boolean run)
 refL09B.append  (example file for appending K and Kh values to a run submission)
 estRelL09.append (estimated number of relevant documents based on past sampling)
 complaints\     (subdirectory with the background complaint files)

Additional background files (for optional reference):
 TREC2006_COMPLAINT_A_ProductPlacement.4.2Version.DOC       6-15
 TREC2006_COMPLAINT_B_campaigncontributions.4.2version.doc 16-24	
 TREC2006_COMPLAINT_C_CaliforniaAntitrust.4.2Version.doc   25-33
 TREC2006_COMPLAINT_D_Securities.4.2Version.doc            34-41
 TREC2006_COMPLAINT_E_SurgicalDevice.4.2Version.doc        42-51
 TREC2007_ComplaintA_v1.doc  (background on requests 52-68)
 TREC2007_ComplaintB_v1.doc  (background on requests 69-78)
 TREC2007_ComplaintC_v1.doc  (background on requests 79-88)
 TREC2007_ComplaintD_v1.doc  (background on requests 89-101)
 TREC2008_ComplaintF_part1_v1.doc   (background for 105-129)
 TREC2008_ComplaintF_part2_v1.doc               ""
 TREC2008_ComplaintF_part3_v1.doc               ""
 TREC2008_ComplaintG_v1.doc         (background for 130-141)
 TREC2008_ComplaintH_v1.doc         (background for 142-151)
 TREC2008_ComplaintI_v1.pdf         (background for 102-104)

Note: the text from the .doc or .pdf (complaint) files is already 
      replicated in the fullL09.xml topic file for the applicable topics.

Note: further judging guidelines for 3 of the topics (102, 103 and 104)
  is available at 
  http://trec.nist.gov/data/legal/08/LegalInteractive_TopicGuidelines_2008.pdf


Relevance Judgments: Sources (qrelsL09.pass1 and qrelsL09.pass1_probs)

The past judgments included in qrelsL09.pass1 and qrelsL09.pass1_probs
are from the following sources:

For topics 7 and 51, included are the judgments from the 
2006 Ad Hoc task and the residual judgments from the 
2007 Interactive and Relevance Feedback task.

For topics 80 and 89, included are the judgments from the 
2007 Ad Hoc task and the residual judgments from the 
2008 Relevance Feedback task.

For topics 102, 103 and 104, included are the post-adjudication
judgments from the 2008 Interactive task.

For topics 105, 138 and 145, included are the judgments from
the 2008 Ad Hoc task.

For the sampling probabilities (the 5th column in qrelsL09.pass1_probs),
when two different years are combined, the probabilities were set
to "1.0" for the judgments from the earlier year and 
the residual sampling probabilities were preserved for the judgments
from the later (residual) year.  Mathematically, this approach
simulates sampling from the later residual pool with the original
judgments added back in.

For cases of two years of judgments being used, just residual
judgments were used from the later year, and hence there are
no documents with two different judgments for the same topic
in qrelsL09.pass1 or qrelsL09.pass1_probs.


Relevance Judgments: Syntax (qrelsL09.pass1 and qrelsL09.pass1_probs)

The qrelsL09.pass1 uses the syntax understood by the trec_eval utility.

The qrelsL09.pass1_probs uses the syntax understood by the l07_eval utility.

For both qrelsL09.pass1 and qrelsL09.pass1_probs,
the first 4 columns are the same:

The 1st column is the topic number (from 6 to 151).
The 2nd column is always a 0.
The 3rd column is the document identifier (e.g. tmw65c00).
The 4th column is the relevance judgment: 
  2 for "highly relevant", 1 for "relevant", 0 for "non-relevant", 
  -1 for "gray" and -2 for "gray".
  (In the assessor system, -1 was "unsure" (the default setting for all documents) 
  and -2 was "unjudged" (the intended label for gray documents).)

  Note: the "highly relevant" category was only available to assessors
  for topics judged in the 2008 Ad Hoc or Relevance Feedback tasks.

qrelsL09.pass1_probs lists one additional column:

The 5th column is the probability the document had of being selected
for assessment from the pool of submitted documents. 

Details on using the l07_eval utility for estimating scores from sampling
are posted in the resultsRF08.zip file at 
 http://trec.nist.gov/data/legal08.html
.


Number of Relevance Judgments By Topic

The following list shows for each of the 10 topics:
 -the count of the number of relevance judgments in the provided qrels files
  (including "gray" documents)
 -the number judged relevant
 -the number judged non-relevant

Topic 7: count=1269, rel=307, non=951
Topic 51: count=1361, rel=88, non=1259
Topic 80: count=1879, rel=734, non=1139
Topic 89: count=874, rel=201, non=607
Topic 102: count=4500, rel=1548, non=2887
Topic 103: count=6500, rel=2981, non=3440
Topic 104: count=2500, rel=92, non=2391
Topic 105: count=701, rel=156, non=540
Topic 138: count=600, rel=125, non=472
Topic 145: count=499, rel=200, non=297


Boolean Strings Syntax:

- AND, OR, NOT, () : As usual

- BUT NOT:  (x BUT NOT y) means same thing as (x AND (NOT (y)))

- x : Match this word exactly (case-insensitive).

- x! : Truncation - matches all strings that begin with substring x.

- !x : Truncation - matches all strings that end with substring x.

- x?y : Single-character wildcard - matches all strings that 
  begin with substring x, end with substring y, 
  and have exactly one-character in between x and y

- x*y : Muliple-character wildcard - matches all strings that 
  begin with substring x, end with substring y,
  and have 0 or more characters between x and y

- "x", "x y", "x y z", etc. : Phrase - match this string or sequence
  of words exactly (case-insensitive).

- "y x!", "x! y", etc. : If ! is used internal to a phrase, then do
  the truncated match on the words with !, and exact match on the
  others.  (The * and ? wildcard operators may also be used inside a
  phrase.)

- w/k: Proximity - x w/k y means match "x a b ... c y" 
  or "y a b ... c x" if "a b ... c" contains k or fewer words

- x w/k1 y w/k2 z: Chained proximity - a match requires the same
  occurrence of y to satisfy x w/k1 y and y w/k2 z

- dt: : just search the <dt> metadata field (document type).
  Note: this syntax is used in one negotiation history query 
  but not in an offical final query.

- ~k: same as w/k (used in .doc files)

- x*: same as x! (used in .doc files)

- [Symbol for Quotation Mark]: indicates that the actual quotation
  mark character should be matched (Unicode value 0x0022); 
  this notation is used to distinguish from the phrase operator


Topic file structure (fullL09.xml). 
   The following layout shows all the elements
   used in the file and their relationships:

<?xml version="1.0" encoding="ISO-8859-1"?> 
<TrecLegalProductionRequest>
  <ProductionRequest>
    <RequestNumber></RequestNumber>
    <RequestText></RequestText>
    <BooleanQuery>
      <FinalQuery></FinalQuery>
      <NegotiationHistory>
        <ProposalByDefendant></ProposalByDefendant>
	<RejoinderByPlaintiff></RejoinderByPlaintiff>
        <Defendant2></Defendant2>
        <Plaintiff2></Plaintiff2>
        <Defendant3></Defendant3>
        <Consensus1></Consensus1>
      </NegotiationHistory>
    </BooleanQuery>
    <FinalB></FinalB>
    <RequestSource></RequestSource>
    <Instruction>
      <P></P>
      <P></P>
      ...
    </Instruction>
    <Definition>
      <P></P>
      <P></P>
      ...
    </Definition>
    <Complaint>
      <ComplaintNumber></ComplaintNumber>
      <Date></Date>
      <Court></Court>
      <Plaintiff></Plaintiff>
      <Defendant></Defendant>
      <Introduction>
        <P></P>
	<P></P>
	...
      </Introduction>
      <Party>
        <PlaintiffParty></PlaintiffParty>
	<DefendantParty></DefendantParty>
	<Coconspirator></Coconspirator>
      </Party>
      <Jurisdiction>
        <P></P>
	<P></P>
	...
      </Jurisdiction>
      <Background>
        <P></P>
	<P></P>
	...
      </Background>
      <CauseOfAction>
        <P></P>
	<P></P>
	...
      </CauseOfAction>
      <RequestedRelief>
        <P></P>
	<P></P>
	...
      </RequestedRelief>
    </Complaint>
  </ProductionRequest>
</TrecLegalProductionRequest>

The meaning of each element is explained as follows:

- <TrecLegalProductionRequest>: the root element of the XML file;

- <ProductionRequest>: request element. One request element
  corresponds to one request (topic). Each request element has 8-12
  subelements:

  - <RequestNumber>: a number uniquely identifying the request, which
    ranges between 102 and 151 inclusively. It is the same as the topic
    number in a traditional TREC evaluation;

  - <RequestText>: a brief description of the subject of the documents
    that are relevant to the request. It has a function similar to the
    <Description> field in a traditional TREC topic;

  - <BooleanQuery>: the intermediary and final query negotiation
    results, expressed as Boolean queries. Under this element,
    <FinalQuery> shows the final negotiated query, while
    <NegotiationHistory> contains the query proposed by the defendant
    (<ProposalByDefendant>) the query rejoindered by the plaintiff
    (<RejoinderByPlaintiff>), and possibly additional negotiation history
    (as noted below).

  - <Defendant2>, <Plaintiff2>, <Defendant3>: (new to 2008)
    Additional negotiation history.  Topics may have none, some or all 3
    of these elements.

  - <Consensus1>: (new to 2008)
    Original negotiated query before it was found that the FinalB value
    would be outside the 100..100000 range.  Only included if the
    <FinalQuery> differs from the original consensus query.

  - <FinalB>: (new to 2007) specifies the number of records matching
    the final negotiated boolean query (as per the reference boolean
    run "refL08B").

  - <RequestSource>: (new to 2007) specifies the corresponding
    complaint (F, G, H or I) and its request number in the 
    complaint .doc file; e.g. 2008-G-1 is the 1st request in 
    the complaint G .doc file
    
  - <Instruction>: describing the possession and entirety requirement
    of the responsive documents for the request;

  - <Definition>: defining particular terms in the context of TREC
    legal track.

  - <Complaint>: the hypothetical complaint that generated the topics
    in the form of requests to produce.  This element has several
    optional elements, some of which are: <ComplaintNumber> specifies
    the case number of the complaint; <Date> specifies the date when
    the complaint is filed; <Court> specifies the court where the
    complaint is filed; <Plaintiff> specifies the plaintiff's name in
    the case; <Defendant> specifies the defendant's name in the case;
    <Introduction> briefly introduce the case; <Party> gives
    additional information of the parties involved in the case;
    <Jurisdiction> describes the jurisdiction and venue of the case;
    <Background> provides the context that the case arises;
    <CauseOfAction> describes the legal claims that plaintiff is
    making against defendant in the case and <RequestedRelief>
    describes the remedy that plaintiff is seeking, including for
    example monetary compensation.

Entities: Be aware that in xml formatting, entities are used to
represent characters with a special meaning in xml, in particular:
   &amp; for &
   &lt; for <
   &gt; for >

Short form of topic file (shortL09.xml):

  shortL09.xml is the same as fullL09.xml except that the
  Instruction, Definition and Complaint elements are removed
  for convenience.  shortL09.xml is ~10,000 bytes, 
  compared to fullL09.xml which is ~200,000 bytes.


.K, .Kh and .append files

As explained in the Batch task guidelines at
http://trec-legal.umiacs.umd.edu/ , K and Kh values
must be appended to each run file for submission to
allow for set-based evaluation with the F1 measure.
If you wish to use the B values as your K and Kh values,
you can just append the refL09B.append file to your
run submission as follows (Windows Command Prompt syntax):

  copy runname runname.orig
  type refL09B.append >>runname
  gzip runname

(On Unix, replace 'copy' with 'cp' and 'type' with 'cat'.
Note however that we have not tested this syntax on Unix.)

Another example .append file is estRelL09.append.
For its K values, it uses the estimated number of relevant
documents based on the qrelsL09.pass1_probs file.
For its Kh values, if the topic included some highly
relevant judgments, then it uses the estimated number of
highly relevant documents based on the qrelsL09.pass1_probs 
file; otherwise, it estimates Kh as 14% of the K value
(based on the approximate ratio of highly relevant to
relevant documents in the 2008 Ad Hoc task).

(Of course, ideally, you would develop your own algorithm for 
setting K and Kh optimally for each topic and not use
the provided .append files at all, except as an example of
the submission syntax.)

You can check your submission file syntax before submitting
by using the check_legal.pl script (to appear) at
  http://trec.nist.gov/act_part/tools.html .
The (anticipated) syntax for checking a run named 'runname' is
  perl check_legal.pl batch runname
After it runs (which can take a few minutes) any errors
will be logged in the runname.errlog file.

The provided .K and .Kh files are examples for use with the 
Kfile option of the l07_eval utility (version 2.1 or later).


Further information of the track can be
found at its web site: http://trec-legal.umiacs.umd.edu/
