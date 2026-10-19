/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var targetIndices = function(nums, target) {
    nums.sort((a, b) => a - b);
    let ary  = []
    for (let i = 0; i < nums.length; i++) {
        if(nums[i] === target) {
            ary.push(i)
        }else if(nums[i] > target) {
            break
        }
    }
    return ary
};
