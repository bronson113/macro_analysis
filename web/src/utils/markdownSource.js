export function buildMarkdownUrl(basePath, filename, cacheBuster) {
  return `${basePath}${filename}?t=${cacheBuster}`;
}
