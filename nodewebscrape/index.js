const Nightmare = require('nightmare')
const axios = require('axios');
const cheerio = require('cheerio');
// var Promise = require("bluebird");
// var bhttp = require("bhttp");

const nightmare = Nightmare({ show: true })

const url='https://www.mtgtop8.com/search';

const selector='tr.hover_tr'

// Nightmare.action('evaluateloop',(name, options, parent, win, renderer, done)=>{console.log(name)})

nightmare
    .goto(url)
    .wait(5000)
    .uncheck('input[name="compet_check[R]"]')
    .select('select','PI')
    .click('input[value="Search"]')
    .wait(5000)
    .evaluate(function() {
    	evaluateinner = function(docstuff) {
            let searchResults = [];

            const Nav_PN_no = document.querySelector('div.Nav_PN_no').innerText

            const results =  docstuff.querySelectorAll('tr.hover_tr');

            results.forEach(function(result) {
                    let row = {
                                    'html':result.innerHTML,
                              }
                    searchResults.push(row);
            });
            return [searchResults,Nav_PN_no];
    }

    return evaluateinner(document)
})
.then(function(result) {
    if (result[1]!='next'){
        
    }
})
    .end()
    // .evaluateloop()
    .then(function(result) {
        console.log(nightmare)
            })
    .catch(function(e)  {
            console.log(e);
    });




//create a while loop in the evaluate part that calls a function that takes as input the tr html array and nav_PN_no <next> and checks whether it does something on submit?
//if nav_PN_no.innertext='next':
	//while loop condition becomes false


    // .then(response=>{
    //     console.log(response[0].innerHTML);
    // }).catch(err=>{
    //     console.log(err);
    // })


// let getData=html=>{
//     data=[];
//     const $=cheerio.load(html);
//     $('table.itemlist tr td:nth-child(3)').each((i,elem)=>{
//         data.push({
//             title:$(elem).text(),
//             link:$(elem).find('a.storylink').attr('href')
//         });
//     });
//     return data;
// }
