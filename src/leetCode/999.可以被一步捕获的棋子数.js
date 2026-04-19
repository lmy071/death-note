/*
 * @lc app=leetcode.cn id=999 lang=javascript
 *
 * [999] 可以被一步捕获的棋子数
 */

// @lc code=start
/**
 * @param {character[][]} board
 * @return {number}
 */
var numRookCaptures = function(board) {
		const ll = board[0].length
    for (let index = 0; index < board.length; index++) {
			for (let i = 0; i < ll; i++) {
				if(board[index][i] === 'R'){
					let flag = true

					while(flag){
						if(board[index][i] === 'B'){
							break;
						}else if(board[index][i] === 'p'){
							res++
							break;
						}else {
							i--
						}
					}

				}
			}
		}
};
// @lc code=end
