/**
 * @param {number} n
 * @return {number}
 */
var totalMoney = function(n) {
    const y = Math.floor(n / 7);
    const f = 28
    const e = 21 + 7 * y
    const all = Math.floor((f+e)*y/2)

    const yy = n % 7
    const ff = y+1;
    const ee = y + yy
    const alll = Math.floor((ff+ee)*yy/2)
    return all + alll;

};
