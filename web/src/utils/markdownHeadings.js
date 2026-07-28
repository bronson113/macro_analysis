export function getNestedMarkdownHeadingLevel(markdownLevel) {
  return Math.min(6, markdownLevel + 2);
}
