var puredata_modules = {
    "snow": `
#N canvas 583 85 857 606 12;
#X obj 166 272 *~;
#X obj 157 182 inlet~;
#X obj 166 312 outlet~;
#X obj 251 207 sig~ 1;
#X connect 0 0 2 0;
#X connect 1 0 0 0;
#X connect 1 0 0 1;
#X connect 3 0 0 1;
`
}