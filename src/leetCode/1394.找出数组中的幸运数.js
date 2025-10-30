/*
 * @lc app=leetcode.cn id=1394 lang=javascript
 *
 * [1394] 找出数组中的幸运数
 */

// @lc code=start
/**
 * @param {number[]} arr
 * @return {number}
 */
var findLucky = function(arr) {
	const freq = new Map();
	for (const num of arr) {
		freq.set(num, (freq.get(num) || 0) + 1);
	}
	let lucky = -1;
	for (const [num, count] of freq.entries()) {
		if (num === count) {
			lucky = Math.max(lucky, num);
		}
	}
	return lucky;
};
// @lc code=end

