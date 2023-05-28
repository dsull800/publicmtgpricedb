

%let analyname='Overgrown Tomb';

PROC SQL;
	CREATE TABLE WORK.transquery AS
	SELECT DISTINCT cardname,title,carddate,shipping,price,cardquantity,maybecardquantity
	FROM A1.transactions
	WHERE possiblybad="0" 
/*	AND cardname IN(SELECT DISTINCT(cardname) FROM A1.tourninfo)*/
	AND cardname=&analyname
	AND isfoil="0"
	AND (cardlanguage='english' or cardlanguage IS NULL)
	AND cardset NOT IN('LEA','LEB','U')
	AND (isemblem IS NULL OR isemblem="0")
	AND (lotis="0" OR lotis IS NULL)
	AND (isboosterbox IS NULL OR isboosterbox="0")
	AND cardspecial IS NULL
	AND issleeve IS NULL
	AND isdeck IS NULL
	AND isplaymat IS NULL
	AND isultra IS NULL
	AND (istoken IS NULL OR istoken="0")
	AND (iscommanderdeck IS NULL OR iscommanderdeck="0")
	AND isgraded IS NULL
	AND (othercards IS NULL OR transplit="1")
	AND saletype IN('normal','italic')
	/*try without saletype*/
	ORDER BY carddate;
QUIT;

PROC SQL;
ALTER TABLE WORK.transquery ADD pshipq real;
QUIT;

PROC SQL;
UPDATE WORK.transquery SET pshipq=(price+shipping)/COALESCE(cardquantity,maybecardquantity,1);
QUIT;

PROC SQL;
CREATE TABLE WORK.fintransquery AS
SELECT cardname,carddate,AVG(pshipq) as avge,MEDIAN(pshipq) as median,SUM(COALESCE(cardquantity,maybecardquantity,1)) as VLM FROM WORK.transquery
WHERE cardname=&analyname
GROUP BY carddate, cardname
ORDER BY cardname,carddate ASC;
QUIT;

data work.fintransquery;
set work.fintransquery;
minavgemed=MIN(avge,median);
carddatenew=input(carddate,anydtdte32.);
FORMAT carddatenew yymmdd10.;
run;

proc expand data=work.fintransquery out=work.fintransquery to=day method=join extrapolate;
id carddatenew;
run;

PROC SQL;
CREATE table work.aggtourns AS
SELECT cardname1 as cardname,entrydate1 as entrydate,SUM(cardquant) as intersum,SUM(cardquant)/AVG(aggcount) as ratio FROM(
SELECT DISTINCT cardname1,entrydate1,cardquant,aggcount,tourntitle FROM
(SELECT cardname as cardname0,entrydate as entrydate0,cardquant,tourntitle FROM A1.tourninfo) AS foo1,
(SELECT cardname as cardname1,entrydate as entrydate1,SUM(cardquant) as aggcount FROM A1.tourninfo 
WHERE cardname1 IN(SELECT DISTINCT cardname FROM A1.tourninfo) GROUP BY entrydate) AS bar
WHERE entrydate0=entrydate1 AND cardname0=cardname1) AS foo
GROUP BY cardname1,entrydate1;
QUIT;

data tourncard;
set work.aggtourns;
WHERE cardname=&analyname;
carddatenew=input(entrydate,anydtdte32.);
FORMAT carddatenew yymmdd10.;
run;

PROC SORT DATA = tourncard OUT = tourncard NODUPKEY;
     BY carddatenew;
	 run;

proc expand data=tourncard out=tourncard to=day method=join extrapolate;
id carddatenew;
run;

proc sql;
SELECT min(carddatenew) into :minebaydate
FROM work.fintransquery;
run; 

data goatprices;
set A1.totalgoatbot;
WHERE cardname=&analyname;
carddatenew=input(carddate,anydtdte32.);
FORMAT carddatenew yymmdd10.;
run;

proc sql;
select max(cardtype)
into :maxcardtype
from work.goatprices
where cardname=&analyname;
%put &maxcardtype;
run;

/*need to sort goatprices by cardtype and then remerge*/

%macro example2;

%do i=0 %to &maxcardtype;

data goatprices&i(rename=(price=price&i));
set goatprices;
WHERE cardtype=&i;
run;

PROC SORT DATA = work.goatprices&i OUT = work.goatprices&i NODUPKEY;
BY carddatenew;
run;

proc expand data=work.goatprices&i out=work.goatprices&i to=day method=join extrapolate;
id carddatenew;
run;

%if &i=0 %then %do;
data mergeconcat;
set work.goatprices&i;
run;
%end
%else %do;
data mergeconcat;
merge work.mergeconcat work.goatprices&i;
by carddatenew;
run;
%end

%end;
%mend;
%example2;


data mergeconcat(drop=cardtype id);
merge work.tourncard work.fintransquery work.mergeconcat;
by carddatenew;
where carddatenew>=&minebaydate;
run;



/*ods graphics on;*/
/*proc arima data=work.mergeconcat plots(only)=(forecast(forecast));*/
/*identify var=minavgemed(1) crosscorr=(ratio price carddatenew);*/
/*estimate p=1 q=1 input=( 1 $ ratio 1 $ price) method=ml;*/
/*forecast lead=0 id=carddatenew out=fore2;*/
/*run;*/






