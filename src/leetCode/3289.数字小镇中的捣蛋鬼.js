/*
 * @lc app=leetcode.cn id=3289 lang=javascript
 *
 * [3289] 数字小镇中的捣蛋鬼
 */

// @lc code=start
/**
 * @param {number[]} nums
 * @return {number[]}
 */
var getSneakyNumbers = function (nums) {
  const set = new Set();
  const res = [];
  nums.forEach((num) => {
    if (set.has(num)) {
      res.push(num);
    } else {
      set.add(num);
    }
  });
	return res;
};
// @lc code=end
