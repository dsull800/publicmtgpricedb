TRUNCATE TABLE public.precomputed_ebay_prices;



INSERT INTO public.precomputed_ebay_prices (cardname,carddate,avge,med)
SELECT A.cardname,A.carddate,A.avge,A.med FROM
(SELECT cardname,carddate,AVG(pshipq) as AVGE,percentile_cont(0.5) WITHIN GROUP (ORDER BY pshipq) as MED
            FROM (SELECT DISTINCT title,cardname,carddate,(price+shipping)/COALESCE(availablequant,cardquantity,maybecardquantity,1) as pshipq FROM public.transactions
            WHERE possiblybad IS FALSE
            AND ismisprint IS NULL
            AND cardname IN(
			SELECT ebayname.cardname FROM 
 ((SELECT DISTINCT(cardname) FROM public.transactions) AS ebayname 
 INNER JOIN 
 (SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM public.tourninfo) AS pio 
 INNER JOIN 
 (SELECT DISTINCT(cardname) FROM public.moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
 as overalltourn ON ebayname.cardname=overalltourn.cardname)
			)
            AND isfoil IS FALSE
            AND (cardlanguage='english' or cardlanguage IS NULL)
            AND (cardset IS NULL OR cardset NOT IN('LEA','LEB','U'))
            AND (isemblem IS NULL OR isemblem IS FALSE)
            AND (lotis IS FALSE OR lotis IS NULL)
            AND (COALESCE(shipping/price,0)<3)
            AND (isboosterbox IS NULL OR isboosterbox IS FALSE)
            AND cardspecial IS NULL
            AND issleeve IS NULL
            AND isdeck IS NULL
            AND isplaymat IS NULL
            AND isultra IS NULL
            AND (istoken IS NULL OR istoken IS FALSE)
            AND (iscommanderdeck IS NULL OR iscommanderdeck IS FALSE)
            AND isgraded IS NULL
            AND (othercards IS NULL OR transplit IS TRUE)
            AND saletype IN('normal')
            AND price+shipping<100) as foo WHERE pshipq<50 
            GROUP BY carddate,cardname ORDER BY carddate ASC) AS A;

TRUNCATE TABLE public.precomputed_pioneer;

INSERT INTO public.precomputed_pioneer (entrydate,cardname,ratio)
SELECT entrydate1 as entrydate,cardname0,SUM(cardquant)/AVG(aggcount) as ratio FROM(
SELECT DISTINCT cardname0,entrydate1,cardquant,aggcount,tourntitle FROM
(SELECT cardname as cardname0,entrydate as entrydate0,cardquant,tourntitle FROM public.tourninfo 
WHERE cardname IN(SELECT ebayname.cardname FROM 
 ((SELECT DISTINCT(cardname) FROM public.transactions) AS ebayname 
 INNER JOIN 
 (SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM public.tourninfo) AS pio 
 INNER JOIN 
 (SELECT DISTINCT(cardname) FROM public.moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
 as overalltourn ON ebayname.cardname=overalltourn.cardname))) AS foo1,
(SELECT entrydate as entrydate1,SUM(cardquant) as aggcount FROM public.tourninfo GROUP BY entrydate) AS bar
WHERE entrydate0=entrydate1) AS foo
GROUP BY cardname0,entrydate1;
    
TRUNCATE TABLE public.precomputed_modern;

INSERT INTO public.precomputed_modern (entrydate,cardname,ratio)
SELECT entrydate1 as entrydate,cardname0,SUM(cardquant)/AVG(aggcount) as ratio FROM(
SELECT DISTINCT cardname0,entrydate1,cardquant,aggcount,tourntitle FROM
(SELECT cardname as cardname0,entrydate as entrydate0,cardquant,tourntitle FROM public.moderntourninfo 
WHERE cardname IN(SELECT ebayname.cardname FROM 
 ((SELECT DISTINCT(cardname) FROM public.transactions) AS ebayname 
 INNER JOIN 
 (SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM public.tourninfo) AS pio 
 INNER JOIN 
 (SELECT DISTINCT(cardname) FROM public.moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
 as overalltourn ON ebayname.cardname=overalltourn.cardname))) AS foo1,
(SELECT entrydate as entrydate1,SUM(cardquant) as aggcount FROM public.moderntourninfo GROUP BY entrydate) AS bar
WHERE entrydate0=entrydate1) AS foo
GROUP BY cardname0,entrydate1;
    
TRUNCATE TABLE public.precomputed_standard;

INSERT INTO public.precomputed_standard (entrydate,cardname,ratio)
SELECT entrydate1 as entrydate,cardname0 as cardname,SUM(cardquant)/AVG(aggcount) as ratio FROM(
SELECT DISTINCT cardname0,entrydate1,cardquant,aggcount,tourntitle FROM
(SELECT cardname as cardname0,entrydate as entrydate0,cardquant,tourntitle FROM public.standardtourninfo WHERE cardname 
IN(SELECT ebayname.cardname FROM 
 ((SELECT DISTINCT(cardname) FROM public.transactions) AS ebayname 
 INNER JOIN 
 (SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM public.tourninfo) AS pio 
 INNER JOIN 
 (SELECT DISTINCT(cardname) FROM public.moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
 as overalltourn ON ebayname.cardname=overalltourn.cardname))) AS foo1,
(SELECT entrydate as entrydate1,SUM(cardquant) as aggcount FROM public.standardtourninfo GROUP BY entrydate) AS bar
WHERE entrydate0=entrydate1) AS foo
GROUP BY cardname0,entrydate1;

DROP TABLE IF EXISTS newtotalgoatbot;

CREATE TABLE newtotalgoatbot AS SELECT id,gcp.card_id,date,price,cardname,cardset FROM goatbot_card_prices as gcp 
INNER JOIN goatbot_card_defs as gcd ON gcp.card_id=gcd.card_id WHERE foil is FALSE AND rarity 
IN('Rare','Mythic') AND cardname IN(SELECT ebayname.cardname FROM 
((SELECT DISTINCT(cardname) FROM public.transactions) AS ebayname 
INNER JOIN 
(SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM public.tourninfo) AS pio 
INNER JOIN 
(SELECT DISTINCT(cardname) FROM public.moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
as overalltourn ON ebayname.cardname=overalltourn.cardname));



TRUNCATE TABLE actual_total_goatbot;

INSERT INTO actual_total_goatbot (id,card_id,date,price,cardname,cardset)
SELECT A.id,A.card_id,A.date,A.price,A.cardname,A.cardset FROM
((SELECT id,card_id,date,price,cardname,cardset FROM public.newtotalgoatbot WHERE cardname IN(SELECT cardname FROM public.newtotalgoatbot)) as A
INNER JOIN (SELECT cardname,MIN(card_id) as min_id FROM public.newtotalgoatbot GROUP BY cardname) AS B ON A.cardname=B.cardname AND A.card_id=B.min_id);

