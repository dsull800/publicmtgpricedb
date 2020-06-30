%let analyname='Brazen Borrower';

PROC SQL;
	CREATE TABLE WORK.transquery AS
	SELECT DISTINCT cardname,title,carddate,shipping,price,cardquantity,maybecardquantity
	FROM A1.transactions
	WHERE possiblybad="0" 
	AND cardname IN(SELECT DISTINCT(cardname) FROM A1.tourninfo)
	AND isfoil="0"
	AND (cardlanguage='english' or cardlanguage IS NULL)
	AND cardset NOT IN('LEA','LEB','U')
	AND isemblem IS NULL
	AND (lotis="0" OR lotis IS NULL)
	AND isboosterbox IS NULL
	AND cardspecial IS NULL
	AND issleeve IS NULL
	AND isdeck IS NULL
	AND isplaymat IS NULL
	AND isultra IS NULL
	AND istoken IS NULL
	AND iscommanderdeck IS NULL
	AND isgraded IS NULL
	AND (othercards IS NULL OR othercards='Hour of Devastation;' OR transplit="1")
	AND saletype IN('normal')/*,'italic')
	/*try without saletype*/
	ORDER BY cardname, carddate;
QUIT;

PROC SQL;
ALTER TABLE WORK.transquery ADD pshipq real;
QUIT;

PROC SQL;
UPDATE WORK.transquery SET pshipq=(price+shipping)/COALESCE(cardquantity,maybecardquantity,1);
QUIT;

/*COALESCE(cardquantity,maybecardquantity,1)*/

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
(SELECT cardname as cardname0,entrydate as entrydate0,cardquant,tourntitle FROM A1.tourninfo) AS foo,
(SELECT cardname as cardname1,entrydate as entrydate1,SUM(cardquant) as aggcount FROM A1.tourninfo 
WHERE cardname1 IN(SELECT DISTINCT cardname FROM work.transquery) GROUP BY entrydate) AS bar
WHERE entrydate0=entrydate1 AND cardname0=cardname1) AS foo
GROUP BY cardname1,entrydate1;
QUIT;

data tourncard;
set work.aggtourns;
WHERE cardname=&analyname;
carddatenew=input(entrydate,anydtdte32.);
FORMAT carddatenew yymmdd10.;
run;

proc expand data=tourncard out=tourncard to=day method=join extrapolate;
id carddatenew;
run;

PROC SORT DATA = tourncard OUT = tourncard NODUPKEY;
     BY carddatenew;
	 run;

proc sql;
SELECT min(carddatenew) into :minebaydate
FROM work.fintransquery;
run; 

proc sgplot data=tourncard;
WHERE carddatenew>=&minebaydate AND carddatenew<=&maxebaydate;
series x=carddatenew y=ratio;
run;

proc sgplot data=work.fintransquery;
/*scatter x=carddatenew y=avge /markerattrs=(symbol=plus);*/
/*scatter x=carddatenew y=median /markerattrs=(symbol=circlefilled);*/
/*scatter x=carddatenew y=minavgemed /markerattrs=(symbol=plus);*/
series x=carddatenew y=minavgemed;
run;

data goatprices;
set A1.goatbot;
WHERE cardname=&analyname;
carddatenew=input(carddate,anydtdte32.);
FORMAT carddatenew yymmdd10.;
run;

proc expand data=work.goatprices out=work.goatprices to=day method=join extrapolate;
id carddatenew;
run;

proc sql;
SELECT max(carddatenew) into :maxebaydate
FROM work.goatprices;
run; 


PROC SORT DATA = goatprices OUT = goatprices NODUPKEY;
     BY carddatenew;
	 run;

proc sgplot data=goatprices;
WHERE carddatenew>=&minebaydate AND carddatenew<=&maxebaydate;
series x=carddatenew y=price;
run;


data greaterthan;
set work.fintransquery;
WHERE (avge>=14 OR median>=14);
run;


data mergeconcat;
merge work.tourncard work.fintransquery work.goatprices;
by carddatenew;
WHERE carddatenew>=&minebaydate AND carddatenew<=&maxebaydate;
run;

ods graphics on;
proc arima data=work.mergeconcat plots(only)=(forecast(forecast));
identify var=minavgemed(1) crosscorr=(ratio price);
estimate p=1 q=1 input=( 1 $ ratio 1 $ price) method=ml;
forecast lead=0 id=carddatenew out=fore2;
run;






