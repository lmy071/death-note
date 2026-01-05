/**
 * @param {number[]} nums
 * @return {number}
 */
var removeDuplicates = function(nums) {
    let k = nums.length
    for (let i = 1; i < nums.length; i++) {
        if(nums[i] == nums[i-1]){
            nums.splice(i, 1)
            i--
            k--
        }
    }
    return  k
};
