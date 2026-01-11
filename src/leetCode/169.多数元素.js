/**
 * @param {number[]} nums
 * @return {number}
 */
var majorityElement = function(nums) {
    nums.sort((a, b) => a - b);
    const l = Math.floor(nums.length/2);
    let i = 0;
    while (nums[i] != nums[i+l]){
        i++
    }
    return nums[i];
};
