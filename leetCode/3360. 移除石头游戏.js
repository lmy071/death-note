/**
 * @param {number} n
 * @return {boolean}
 */
var canAliceWin = function(n) {
    let res = false
    let leng = 10
    while (n > 0 && leng > 0){
        n = n - leng
        if(n >= 0) res = !res
        leng--
    }
    return  res

};
