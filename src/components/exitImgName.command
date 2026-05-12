#!/bin/bash
# ============================================================
# 图片重命名工具 (macOS) – 固定根目录 /Users/lm/Documents/Data/Img
# 递归将该目录及其所有子文件夹中的图片重命名为：
# 「文件夹名 + 创建日期(YYYY-MM-DD)」 + 扩展名
# 重名自动追加 a...z → aa...zz（文件自身不会再导致重名）
# ============================================================

workdir="/Users/lm/Documents/Data/Img"

if [ ! -d "$workdir" ]; then
    osascript -e 'display notification "目录不存在：'"$workdir"'" with title "图片重命名失败"'
    exit 1
fi

echo "正在处理目录：$workdir"
cd "$workdir" || {
    osascript -e 'display notification "无法进入目录：'"$workdir"'" with title "图片重命名失败"'
    exit 1
}

extensions=("jpg" "jpeg" "png" "gif" "bmp" "tiff" "tif" "webp" "heic" "heif")

find_args=()
for ext in "${extensions[@]}"; do
    find_args+=(-iname "*.$ext" -o)
done
unset 'find_args[${#find_args[@]}-1]'

# 后缀序列逻辑已改为动态生成 -1, -2, -3...

renamed=0
skipped=0

while IFS= read -r -d '' file; do
    dir=$(dirname "$file")

    if [ "$dir" = "." ]; then
        base=$(basename "$workdir")
    else
        base=$(basename "$dir")
    fi

    cdate=$(stat -f "%SB" -t "%Y-%m-%d" "$file" 2>/dev/null)
    if [ -z "$cdate" ]; then
        echo "⚠️  无法获取创建日期，跳过：$file"
        ((skipped++))
        continue
    fi

    ext="${file##*.}"
    target_dir="$dir"
    fname=$(basename "$file")

    # 1. 检查是否已经满足命名格式：[文件夹名][日期](-数字).扩展名
    # 使用正则匹配：精确匹配 base+cdate，后面可选 -数字，最后匹配 .ext
    if [[ "$fname" == "${base}${cdate}.${ext}" ]] || [[ "$fname" =~ ^"${base}${cdate}"-[0-9]+\."${ext}"$ ]]; then
        echo "⏭  已符合格式，跳过：$fname"
        continue
    fi

    newname=""
    # 2. 尝试不带数字后缀
    candidate="${base}${cdate}.${ext}"
    if [ ! -e "$target_dir/$candidate" ] || [ "$fname" = "$candidate" ]; then
        newname="$candidate"
    else
        # 3. 尝试 -1, -2, -3... 依次递增
        i=1
        while :; do
            candidate="${base}${cdate}-${i}.${ext}"
            if [ ! -e "$target_dir/$candidate" ] || [ "$fname" = "$candidate" ]; then
                newname="$candidate"
                break
            fi
            ((i++))
        done
    fi

    if [ -z "$newname" ]; then
        echo "❌ 无法分配可用文件名，跳过：$file"
        ((skipped++))
        continue
    fi

    # 再次确认名字是否有变化（理论上前面的 check 已经处理了，这里做二次保险）
    if [ "$fname" = "$newname" ]; then
        continue
    fi

    mv -n "$file" "$target_dir/$newname"
    echo "✔  $file → $target_dir/$newname"
    ((renamed++))
done < <(find . -type f \( "${find_args[@]}" \) -print0)

osascript -e 'display notification "重命名完成：'"$renamed"' 个文件，跳过 '"$skipped"' 个" with title "图片重命名工具"'
echo "完成：重命名 $renamed 个文件，跳过 $skipped 个文件。"
