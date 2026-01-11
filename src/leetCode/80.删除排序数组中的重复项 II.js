/**
 * @param {number[]} nums
 * @return {number}
 */
var removeDuplicates = function(nums) {
    let num = 1
    for (let i = 1; i < nums.length; i++) {
        if(nums[i] === nums[i-1]) {
                ++num
        }else {
            if(num>2){
                nums.splice(i-num,num -2)
                i = i - num + 2
                num = 1
            }else {
                num = 1

            }
        }

        if(i === nums.length-1 && num>2){
            nums.splice(i-num+1,num -2)
        }
    }
    return nums.length
};
