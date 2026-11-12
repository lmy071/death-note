/**
 * @param {number[]} nums
 * @return {number}
 */
var longestMonotonicSubarray = function(nums) {
    let u = 1;
    let d = 1
    let r = 1
    for (let i = 1; i < nums.length; i++) {
        if(nums[i] <= nums[i-1] ){
            r = Math.max(r,u)
            u = 1
        }else{
            u++
        }
        if (nums[i] >= nums[i-1]){
            r = Math.max(r,d)
            d = 1
        }else{
            d++
        }
    }
    return Math.max(r,Math.max(u,d))
};