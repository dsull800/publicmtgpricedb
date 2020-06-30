const Nightmare = require('nightmare')
const axios = require('axios');
const cheerio = require('cheerio');


const { Pool, Client } = require('pg')
const pool = new Pool({

})
// pool.query('SELECT NOW()', (err, res) => {
//   console.log(err, res)
//   pool.end()
// })


String.prototype.replaceAll = function(str1, str2, ignore)
{
    return this.replace(new RegExp(str1.replace(/([\/\,\!\\\^\$\{\}\[\]\(\)\.\*\+\?\|\<\>\-\&])/g,"\\$&"),(ignore?"gi":"g")),(typeof(str2)=="string")?str2.replace(/\$/g,"$$$$"):str2);
}

const client = new Client({

})
client.connect()
// client.query("SELECT MAX(carddate) FROM public.goatbot WHERE cardname='Thoughtseize'", (err, res) => {
//   console.log(res['rows'][0]['max'])
// client.end()
// })
const sleep = (milliseconds) => {
    return new Promise(resolve => setTimeout(resolve, milliseconds))
   }

client.query("SELECT DISTINCT(name) FROM public.cards WHERE rarity IN('mythic','rare') AND name IN('Gisela, the Broken Blade') AND name NOT IN(SELECT DISTINCT(cardname) FROM public.totalgoatbot) AND setcode IN(SELECT code FROM public.sets WHERE type IN ('expansion','core') and releasedate>=(SELECT releasedate FROM public.sets WHERE mcmname='Return to Ravnica'))",
(err, res) => {
var index=0;

function myLoop() {         //  create a loop function
  setTimeout(function() {   //  call a 3s setTimeout when the loop is called


      item = res['rows'][index]

     var cardname = item['name']

     var cardname1=item['name'].replaceAll(" ","-");
     var cardname2=cardname1.replaceAll("'","");
     var cardname3=cardname2.replaceAll(",","");

     console.log(cardname3)


     const url='https://www.goatbots.com/card/ajax_card?search_name='+cardname3;

     const nightmare = Nightmare({ show: false });


     nightmare
          .goto(url)
          .wait('body')
          .evaluate(()=>document.querySelector('body').innerHTML)
          .end()
          .then(response=>{
              var parsedresponse=JSON.parse(response)
              for(let cardtypecount=0;cardtypecount<parsedresponse[1].length;cardtypecount++){
              for(let item of Object.entries(parsedresponse[1][cardtypecount].reverse())){
              // parsedresponse[1][0].reverse().forEach(function(item){
                // console.log(item)

                item=item[1]

                var msec=Date.parse(item[0])
                var carddate=new Date(msec)
                var carddate=carddate.toISOString().slice(0,10)
                
                
                
                  const text = 'INSERT INTO public.totalgoatbot(cardname,carddate,price,cardtype) VALUES($1,$2,$3,$4)'
                    const values = [cardname,carddate,item[1],cardtypecount]
                    // callback
                    client.query(text, values, (err, res2) => {
                      if (err) {
                        console.log(err.stack)
                      } else {
                        // console.log('worked')
                        // { name: 'brianc', email: 'brian.m.carlson@gmail.com' }
                      }
                    })
              };
              };


          }).catch(err=>{
              console.log('somethingbadhappened');
          });



    index++;                    //  increment the counter
    if (index < res['rows'].length) {           //  if the counter < 10, call the loop function
      myLoop();             //  ..  again which will trigger another
    }                       //  ..  setTimeout()
},40000)
}

myLoop();

});







