//This file was generated from (Academic) UPPAAL 4.1.20-stratego-9 (rev. 67D95DBCE6B8B4ED), January 2022

/*

*/
strategy term = control: A<> positive || negative

/*

*/
strategy max = maxE (final_gas) [t<=200] : <> positive under term

/*

*/
strategy step_strat = minE (steps) [t<=200] : <> positive under term

/*

*/
strategy both = maxE (-12*steps+final_gas) [t<=200] : <> positive under term

/*

*/
E[#<=30; 100] (max: final_gas)  under max

/*

*/
E[#<=30; 100] (max: final_gas)  under step_strat

/*

*/
E[#<=30; 100] (max: final_gas)  under both

/*

*/
E[#<=30; 100] (max: steps)  under max

/*

*/
E[#<=30; 100] (max: steps)  under step_strat

/*

*/
E[#<=30; 100] (max: steps)  under both

/*

*/
E[#<=30; 100] (min: e)  under max

/*

*/
E[#<=30; 100] (min: e)  under step_strat

/*

*/
E[#<=30; 100] (min: e)  under both

/*

*/
simulate 100 [#<=60] {e, positive, negative} under max

/*

*/
simulate 100 [#<=60] {e, positive, negative} under step_strat

/*

*/
simulate 100 [#<=60] {e, positive, negative} under both
