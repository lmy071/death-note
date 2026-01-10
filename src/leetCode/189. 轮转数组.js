/** * @param {number[]} nums * @param {number} k * @return {void} Do not return anything, modify nums in-place instead. */
var rotate = function (nums, k) {
  let kk = k;
  if (k > nums.length) {
    kk = k%(nums.length );
  }
  const n = nums.splice(nums.length - kk , kk);
  nums.unshift(...n);
};
rotate([1,2,3], 4);
