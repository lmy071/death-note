/**
 * @param {number[]} nums
 * @return {number[]}
 */
var maxValue = function(nums) {
    let n = nums.length;
    const preMax = Array.from({length:n}).map(num => nums[num])
    preMax[0] = nums[0];
    for (let i = 1; i < n; i++) {
        preMax[i] = Math.max(preMax[i - 1], nums[i]);
    }
    const  ans = Array.from({length:n}).map(num => nums[num])
    let sufMin = Number.MAX_SAFE_INTEGER;
    for (let i = n - 1; i >= 0; i--) {
        ans[i] = preMax[i] <= sufMin ? preMax[i] : ans[i + 1];
        sufMin = Math.min(sufMin, nums[i]);
    }
    return ans;
};