/**
 * @param {character[][]} boxGrid
 * @return {character[][]}
 */
var rotateTheBox = function(boxGrid) {
        if (boxGrid.length === 0) return [];
        boxGrid.forEach(v=>{
                let tag = 0
                for(let i=0;i<v.length;i++){
                        if(v[i] === '.'){
                                v.splice(i,1)
                                v.splice(tag,0,".")
                        }else if(v[i] === '*'){
                                tag = i + 1
                        }
                }

        })
        let ary = Array.from({ length: boxGrid[0].length }).map(v=>[])
        boxGrid.forEach((v,i)=>{
                v.forEach((vv,ii)=>{
                        ary[ii].unshift(vv)
                })
        })
        return ary
};
