"""Regression tests for Markdown image embedding and identity-based link rewriting."""

from pathlib import Path
import unittest
from urllib.parse import quote

from src.notion_export.markdown import (
    embed_image_links,
    is_image_target,
    rewrite_local_links,
    split_link_target,
)


class SplitLinkTargetTests(unittest.TestCase):
    def test_plain_target_and_surrounding_whitespace(self):
        self.assertEqual(split_link_target("  folder/image.png  "), ("folder/image.png", "", False))
        self.assertEqual(split_link_target(""), ("", "", False))

    def test_three_markdown_title_delimiters(self):
        for title in (' "图片标题"', " '图片标题'", " (图片标题)"):
            with self.subTest(title=title):
                self.assertEqual(
                    split_link_target("folder/image.png" + title),
                    ("folder/image.png", title, False),
                )

    def test_angle_brackets_preserve_spaces_and_title(self):
        self.assertEqual(
            split_link_target('  <folder/a b.png>  "说明"  '),
            ("folder/a b.png", '  "说明"', True),
        )
        self.assertEqual(split_link_target("<folder/a b.png>"), ("folder/a b.png", "", True))

    def test_parentheses_without_separating_space_belong_to_path(self):
        self.assertEqual(split_link_target("folder/image(1).png"), ("folder/image(1).png", "", False))

    def test_unclosed_delimiters_are_not_invented(self):
        for target in ("<folder/image.png", 'folder/image.png "unfinished'):
            with self.subTest(target=target):
                self.assertEqual(split_link_target(target), (target, "", False))


class ImageTargetTests(unittest.TestCase):
    def test_supported_image_formats_and_case(self):
        for extension in ("png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif", "ico", "apng"):
            for spelling in (extension, extension.upper()):
                with self.subTest(extension=spelling):
                    self.assertTrue(is_image_target("images/封面." + spelling))

    def test_query_fragment_and_encoded_extension(self):
        for target in (
            "https://example.test/image.PNG?download=1#preview",
            "https://example.test/image%2Epng?filename=other.pdf",
            "images/a%20b.jpg#thumbnail",
            "//cdn.example.test/picture.webp",
            "/assets/picture.svg",
            "../assets/picture.png",
        ):
            with self.subTest(target=target):
                self.assertTrue(is_image_target(target))

    def test_unsupported_schemes_and_invalid_urls(self):
        for target in (
            "", "#image.png", "?image.png", "mailto:image.png", "ftp://example.test/image.png",
            "file:///tmp/image.png", "data:image/png;base64,abc", "javascript:image.png",
            "C:/images/image.png", "images/a:b.png", "http://[broken/image.png",
        ):
            with self.subTest(target=target):
                self.assertFalse(is_image_target(target))

    def test_extension_must_belong_to_path(self):
        for target in (
            "https://example.test/download?filename=image.png", "document.md#image.png",
            "https://image.png/", "folder.png/document.pdf", "image.png.txt", "image",
        ):
            with self.subTest(target=target):
                self.assertFalse(is_image_target(target))


class EmbedImageLinksTests(unittest.TestCase):
    def test_image_links_become_inline_images_and_keep_titles(self):
        before = '文字 [封面](images/a.png "标题")、[背面](<images/b b.JPG>) 结束。'
        after = '文字 ![封面](images/a.png "标题")、![背面](<images/b b.JPG>) 结束。'
        self.assertEqual(embed_image_links(before), after)

    def test_image_property_labels_in_both_languages(self):
        for label in ("图片: ", "图像：", "image: ", "Images： ", "  IMAGE : "):
            with self.subTest(label=label):
                self.assertEqual(
                    embed_image_links(label + "https://example.test/a.png\n"),
                    label + "![图片](https://example.test/a.png)\n",
                )

    def test_property_angle_brackets_and_title_are_preserved(self):
        self.assertEqual(
            embed_image_links('图片：<images/my picture.png> "封面"\n'),
            '图片：![图片](<images/my picture.png> "封面")\n',
        )

    def test_standalone_images_preserve_whitespace_and_line_endings(self):
        self.assertEqual(
            embed_image_links("  image.png  \r\n\thttps://example.test/a.jpg\nlast.webp"),
            "  ![图片](image.png)  \r\n\t![图片](https://example.test/a.jpg)\n![图片](last.webp)",
        )

    def test_prose_urls_other_properties_and_nonimage_links_stay_unchanged(self):
        markdown = (
            "请打开 https://example.test/image.png\n"
            "链接: https://example.test/image.png\n"
            "[文档](guide.md) [下载](https://example.test/file?name=image.png)\n"
            "图片: https://example.test/document.pdf\n"
            "image with spaces.png\n"
        )
        self.assertEqual(embed_image_links(markdown), markdown)

    def test_existing_images_and_clickable_images_stay_unchanged(self):
        markdown = '![原图](a.png "说明")\n[![缩略图](a.png)](https://example.test/full.png)\n'
        self.assertEqual(embed_image_links(markdown), markdown)

    def test_fenced_and_inline_code_stay_unchanged(self):
        markdown = (
            "`[示例](a.png)`\n"
            "```markdown\n[示例](a.png)\n图片: a.png\nhttps://example.test/a.png\n```\n"
            "~~~\n[示例](a.png)\n图片：a.png\n~~~\n"
        )
        self.assertEqual(embed_image_links(markdown), markdown)

    def test_only_links_outside_code_are_embedded(self):
        self.assertEqual(
            embed_image_links("[第一张](a.png) `[代码](b.png)` [第二张](c.png)\n"),
            "![第一张](a.png) `[代码](b.png)` ![第二张](c.png)\n",
        )

    def test_multiple_backtick_inline_code_preserves_image_examples(self):
        for markdown in (
            "``[示例](a.png) `literal` ``",
            "```[示例](a.png) ``literal`` ```",
        ):
            with self.subTest(markdown=markdown):
                self.assertEqual(embed_image_links(markdown), markdown)

    def test_long_fences_are_not_closed_by_shorter_fences(self):
        for fence in ("````", "~~~~"):
            markdown = (
                f"{fence}markdown\n{fence[:3]}\n[示例](a.png)\n"
                f"图片：a.png\nhttps://example.test/a.png\n{fence}\n"
            )
            with self.subTest(fence=fence):
                self.assertEqual(embed_image_links(markdown), markdown)

    def test_unclosed_fences_protect_images_until_end_of_document(self):
        for fence in ("```", "~~~", "````"):
            markdown = f"{fence}markdown\n[示例](a.png)\n图片：a.png\nhttps://example.test/a.png"
            with self.subTest(fence=fence):
                self.assertEqual(embed_image_links(markdown), markdown)

    def test_indented_code_preserves_image_links_properties_and_bare_urls(self):
        for indent in ("    ", "\t"):
            markdown = (
                f"{indent}[示例](a.png)\n{indent}图片：a.png\n"
                f"{indent}https://example.test/a.png\n"
            )
            with self.subTest(indent=repr(indent)):
                self.assertEqual(embed_image_links(markdown), markdown)

    def test_normal_images_after_long_code_blocks_and_spans_are_embedded(self):
        code_block = "````markdown\n```\n[代码](a.png)\n````\n"
        code_span = "``[代码](b.png) `literal` ``"
        markdown = code_block + "[正文](c.png)\n" + code_span + " [正文](d.png)\n"
        expected = code_block + "![正文](c.png)\n" + code_span + " ![正文](d.png)\n"
        self.assertEqual(embed_image_links(markdown), expected)

    def test_escaped_link_examples_and_even_backslashes(self):
        self.assertEqual(embed_image_links(r"\[示例](a.png)"), r"\[示例](a.png)")
        self.assertEqual(embed_image_links(r"\\\[示例](a.png)"), r"\\\[示例](a.png)")
        self.assertEqual(embed_image_links(r"\\[图片](a.png)"), r"\\![图片](a.png)")

    def test_image_path_with_parentheses(self):
        self.assertEqual(embed_image_links("[封面](images/a(1).png)"), "![封面](images/a(1).png)")

    def test_conversion_is_idempotent(self):
        markdown = (
            '[封面](a.png "说明")\n图片：<my image.jpg>\nhttps://example.test/b.webp\n'
            '![原图](c.gif)\n[![缩略图](d.png)](https://example.test)\n`[示例](e.png)`\n'
        )
        converted = embed_image_links(markdown)
        self.assertNotEqual(converted, markdown)
        self.assertEqual(embed_image_links(converted), converted)


class RewriteLocalLinksTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("Raw Folder/Source 11111111111111111111111111111111.md")
        self.target = Path("Raw Folder/Target 22222222222222222222222222222222.md")
        self.paths = {
            self.source: Path("导入/源页面.md"),
            self.target: Path("导入/目标页面.md"),
            Path("Assets/a b.png"): Path("附件/a-b.png"),
        }

    def rewrite(self, markdown):
        return rewrite_local_links(markdown, self.source, self.paths)

    def test_relative_target_uses_full_source_identity(self):
        target = quote(self.target.name)
        self.assertEqual(self.rewrite(f"[目标]({target})"), (f"[目标]({quote('目标页面.md')})", 1))

    def test_root_absolute_target_stays_root_absolute(self):
        self.assertEqual(
            self.rewrite(f"[目标](/{quote(self.target.as_posix())})"),
            (f"[目标](/{quote('导入/目标页面.md')})", 1),
        )

    def test_parent_directory_normalization_and_backslashes(self):
        for target in ("../Assets/a%20b.png", "../Raw%20Folder/../Assets/a%20b.png", r"..\Assets\a%20b.png"):
            with self.subTest(target=target):
                self.assertEqual(
                    self.rewrite(f"![图片]({target})"),
                    (f"![图片](../{quote('附件/a-b.png')})", 1),
                )

    def test_query_fragment_and_title_survive_rewrite(self):
        target = quote(self.target.name)
        self.assertEqual(
            self.rewrite(f'[目标](<{target}?download=1&name=a%20b#heading> "可选标题")'),
            (f'[目标](<{quote("目标页面.md")}?download=1&name=a%20b#heading> "可选标题")', 1),
        )

    def test_single_quoted_and_parenthesized_titles_survive_rewrite(self):
        for title in (" '标题'", " (标题)"):
            with self.subTest(title=title):
                self.assertEqual(
                    self.rewrite(f"[目标]({quote(self.target.name)}{title})"),
                    (f"[目标]({quote('目标页面.md')}{title})", 1),
                )

    def test_encoded_hash_and_question_mark_remain_part_of_filename(self):
        old = Path("Raw Folder/a#b?c.md")
        self.paths[old] = Path("导入/new#file?.md")
        self.assertEqual(
            self.rewrite("[特殊字符](a%23b%3Fc.md#section?view=1)"),
            (f"[特殊字符]({quote('new#file?.md')}#section?view=1)", 1),
        )

    def test_reference_destinations_are_rewritten_and_titles_preserved(self):
        markdown = (
            f'[文字][page]\n![图片][asset]\n\n[page]: <{quote(self.target.name)}> "页面"\n'
            '  [asset]: ../Assets/a%20b.png "图片"\n'
        )
        expected = (
            f'[文字][page]\n![图片][asset]\n\n[page]: <{quote("目标页面.md")}> "页面"\n'
            f'  [asset]: ../{quote("附件/a-b.png")} "图片"\n'
        )
        self.assertEqual(self.rewrite(markdown), (expected, 2))

    def test_inline_and_fenced_code_are_not_rewritten(self):
        target = quote(self.target.name)
        markdown = (
            f'`[目标]({target})`\n```md\n[目标]({target})\n[ref]: {target}\n```\n'
            f'~~~md\n[目标]({target})\n[ref]: {target}\n~~~\n'
        )
        self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_multiple_backtick_inline_code_preserves_local_link_examples(self):
        target = quote(self.target.name)
        for markdown in (
            f"``[示例]({target}) `literal` ``",
            f"```[示例]({target}) ``literal`` ```",
        ):
            with self.subTest(markdown=markdown):
                self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_long_fences_preserve_inline_and_reference_links(self):
        target = quote(self.target.name)
        for fence in ("````", "~~~~"):
            markdown = f"{fence}markdown\n{fence[:3]}\n[示例]({target})\n[ref]: {target}\n{fence}\n"
            with self.subTest(fence=fence):
                self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_unclosed_fences_preserve_links_until_end_of_document(self):
        target = quote(self.target.name)
        for fence in ("```", "~~~", "````"):
            markdown = f"{fence}markdown\n[示例]({target})\n[ref]: {target}"
            with self.subTest(fence=fence):
                self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_indented_code_preserves_local_link_examples(self):
        target = quote(self.target.name)
        for indent in ("    ", "\t"):
            markdown = f"{indent}[示例]({target})\n{indent}[ref]: {target}\n"
            with self.subTest(indent=repr(indent)):
                self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_normal_links_after_long_code_blocks_and_spans_are_rewritten(self):
        target = quote(self.target.name)
        code_block = f"````markdown\n```\n[代码]({target})\n````\n"
        code_span = f"``[代码]({target}) `literal` ``"
        markdown = code_block + f"[正文]({target})\n" + code_span + f" [正文]({target})\n"
        expected = (
            code_block + f"[正文]({quote('目标页面.md')})\n"
            + code_span + f" [正文]({quote('目标页面.md')})\n"
        )
        self.assertEqual(self.rewrite(markdown), (expected, 2))

    def test_replacement_lengths_do_not_move_code_protection(self):
        target = quote(self.target.name)
        markdown = f"[一]({target}) `[代码]({target})` [二]({target})"
        expected = f"[一]({quote('目标页面.md')}) `[代码]({target})` [二]({quote('目标页面.md')})"
        self.assertEqual(self.rewrite(markdown), (expected, 2))

    def test_external_urls_anchors_and_queries_stay_unchanged(self):
        for target in (
            "https://example.test/Target.md", "HTTP://example.test/a.png", "//example.test/a.png",
            "mailto:user@example.test", "data:image/png;base64,abc", "custom+app:page.md",
            "#heading", "?download=1", "",
        ):
            with self.subTest(target=target):
                markdown = f"[目标]({target})"
                self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_unknown_page_does_not_fall_back_to_matching_basename(self):
        markdown = f"[未导入页面](../Elsewhere/{quote(self.target.name)})"
        self.assertEqual(self.rewrite(markdown), (markdown, 0))

    def test_non_csv_source_does_not_guess_cleaned_target(self):
        self.assertEqual(self.rewrite("[目标](Target.md)"), ("[目标](Target.md)", 0))

    def test_unchanged_paths_preserve_original_encoding_and_do_not_count(self):
        source = Path("source.md")
        paths = {source: source, Path("a b.png"): Path("a b.png")}
        markdown = '![图](<a%20b.png> "标题")'
        self.assertEqual(rewrite_local_links(markdown, source, paths), (markdown, 0))

    def test_csv_cleaned_name_fallback_accepts_only_unique_destination(self):
        source = Path("Tables/list.csv")
        old = Path("Assets/Card Photo 33333333333333333333333333333333.png")
        paths = {source: Path("表格/list.md"), old: Path("附件/Card-Photo.png")}
        self.assertEqual(
            rewrite_local_links("[卡图](../Assets/Card-Photo.png)", source, paths),
            (f"[卡图](../{quote('附件/Card-Photo.png')})", 1),
        )

    def test_csv_ambiguous_cleaned_names_stay_unchanged(self):
        source = Path("Tables/list.csv")
        paths = {
            source: Path("表格/list.md"),
            Path("Assets/Card Photo 33333333333333333333333333333333.png"): Path("附件/Card-Photo.png"),
            Path("Assets/Card Photo 44444444444444444444444444444444.png"): Path("附件/Card-Photo-2.png"),
        }
        markdown = "[卡图](../Assets/Card-Photo.png)"
        self.assertEqual(rewrite_local_links(markdown, source, paths), (markdown, 0))

    def test_csv_exact_identity_wins_even_when_cleaned_names_are_ambiguous(self):
        source = Path("Tables/list.csv")
        old = Path("Assets/Card Photo 33333333333333333333333333333333.png")
        paths = {
            source: Path("表格/list.md"),
            old: Path("附件/Card-Photo.png"),
            Path("Assets/Card Photo 44444444444444444444444444444444.png"): Path("附件/Card-Photo-2.png"),
        }
        self.assertEqual(
            rewrite_local_links(f"[卡图](../{quote(old.as_posix())})", source, paths),
            (f"[卡图](../{quote('附件/Card-Photo.png')})", 1),
        )


class CodeBoundaryTests(unittest.TestCase):
    def test_escaped_backticks_do_not_hide_normal_images_or_links(self):
        self.assertEqual(
            embed_image_links(r"\`[图片](a.png)\`"),
            r"\`![图片](a.png)\`",
        )
        source = Path("source.md")
        paths = {source: source, Path("old.md"): Path("new.md")}
        self.assertEqual(
            rewrite_local_links(r"\`[页面](old.md)\`", source, paths),
            (r"\`[页面](new.md)\`", 1),
        )

    def test_dedented_paragraph_after_code_is_converted(self):
        content = "    [代码](a.png)\n\n[正文](b.png)\n"
        self.assertEqual(
            embed_image_links(content),
            "    [代码](a.png)\n\n![正文](b.png)\n",
        )


if __name__ == "__main__":
    unittest.main()
